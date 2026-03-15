from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from src.core.cache_system import CoreCacheSystem
from src.integration.ytdl_sub.compiler import CompiledSubscriptionArtifact
from src.integration.ytdl_sub.executor import (
    ExecutedJobResult,
    FailureSeverity,
    execute_compiled_artifact,
)
from src.persistence.sqlite_state import QueueJobEnvelope, QueueJobRecord, SQLiteOperationalState


@dataclass(frozen=True)
class RetryPolicy:
    base_seconds: int = 5
    max_seconds: int = 120

    def compute_delay_seconds(self, *, attempt_number: int) -> int:
        if attempt_number <= 0:
            raise ValueError("attempt_number debe ser >= 1")
        delay = self.base_seconds * (2 ** (attempt_number - 1))
        return min(delay, self.max_seconds)


@dataclass(frozen=True)
class QueueRuntimeConfig:
    max_workers: int = 2
    max_concurrent_by_subscription: int = 1


@dataclass(frozen=True)
class QueueStepReport:
    claimed_jobs: tuple[str, ...]
    completed_jobs: tuple[str, ...]
    retry_jobs: tuple[str, ...]
    dead_letter_jobs: tuple[str, ...]
    skipped_jobs: tuple[str, ...]


class QueueRuntime:
    """Gestor operativo del backlog persistido para Hito 18 (single-process)."""

    def __init__(
        self,
        *,
        state: SQLiteOperationalState,
        cache: CoreCacheSystem,
        config: QueueRuntimeConfig | None = None,
        retry_policy: RetryPolicy | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.state = state
        self.cache = cache
        self.config = config or QueueRuntimeConfig()
        self.retry_policy = retry_policy or RetryPolicy()
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def enqueue_execution_job(
        self,
        *,
        job_id: str,
        artifact: CompiledSubscriptionArtifact,
        priority: int,
        max_attempts: int = 3,
    ) -> tuple[QueueJobRecord, bool]:
        envelope = QueueJobEnvelope(
            job_id=job_id,
            queue_kind="sync",
            priority=priority,
            subscription_id=artifact.subscription_id,
            payload={
                "artifact_yaml_path": str(artifact.artifact_yaml_path),
                "metadata_json_path": str(artifact.metadata_json_path),
                "compilation_signature": artifact.compilation_signature,
                "output_dir": str(artifact.output_dir),
            },
            max_attempts=max_attempts,
        )
        return self.state.enqueue_job(envelope)

    def step(
        self,
        *,
        artifacts_by_signature: dict[str, CompiledSubscriptionArtifact],
        global_args: tuple[str, ...] = (),
        env_overrides: dict[str, str] | None = None,
        timeout_seconds: float = 300.0,
    ) -> QueueStepReport:
        now_iso = self._now_iso()
        runnable = self.state.list_runnable_queue_jobs(now=now_iso)
        selected = self._select_runnable(runnable)

        claimed: list[str] = []
        completed: list[str] = []
        retried: list[str] = []
        dead: list[str] = []
        skipped: list[str] = []

        for job in selected:
            claimed_job = self.state.claim_queue_job(job_id=job.job_id)
            if claimed_job is None:
                skipped.append(job.job_id)
                continue
            claimed.append(job.job_id)

            cache_scope = "queue_execution_result"
            cache_key = claimed_job.signature
            if self.cache.get(
                scope=cache_scope,
                key=cache_key,
                context=_queue_cache_context(claimed_job),
            ) == "completed":
                self.state.complete_queue_job(job_id=claimed_job.job_id)
                completed.append(claimed_job.job_id)
                continue

            result = self._execute_single(
                claimed_job,
                artifacts_by_signature=artifacts_by_signature,
                global_args=global_args,
                env_overrides=env_overrides,
                timeout_seconds=timeout_seconds,
            )

            if result.status == "success":
                self.state.complete_queue_job(job_id=claimed_job.job_id)
                self.cache.put(
                    scope=cache_scope,
                    key=cache_key,
                    context=_queue_cache_context(claimed_job),
                    value="completed",
                )
                completed.append(claimed_job.job_id)
                continue

            if _is_recoverable(result) and (claimed_job.attempts + 1) < claimed_job.max_attempts:
                attempt_number = claimed_job.attempts + 1
                delay_seconds = self.retry_policy.compute_delay_seconds(
                    attempt_number=attempt_number
                )
                retry_at = self._now_provider() + timedelta(seconds=delay_seconds)
                self.state.schedule_queue_retry(
                    job_id=claimed_job.job_id,
                    scheduled_at=retry_at.isoformat(timespec="seconds"),
                )
                retried.append(claimed_job.job_id)
                continue

            self.state.dead_letter_queue_job(
                job_id=claimed_job.job_id,
                error_type=result.error_type.value,
                error_message=result.error_message or "error no detallado",
            )
            dead.append(claimed_job.job_id)

        return QueueStepReport(
            claimed_jobs=tuple(claimed),
            completed_jobs=tuple(completed),
            retry_jobs=tuple(retried),
            dead_letter_jobs=tuple(dead),
            skipped_jobs=tuple(skipped),
        )

    def _execute_single(
        self,
        job: QueueJobRecord,
        *,
        artifacts_by_signature: dict[str, CompiledSubscriptionArtifact],
        global_args: tuple[str, ...],
        env_overrides: dict[str, str] | None,
        timeout_seconds: float,
    ) -> ExecutedJobResult:
        compilation_signature = str(job.payload.get("compilation_signature", ""))
        artifact = artifacts_by_signature.get(compilation_signature)
        if artifact is None:
            raise KeyError(f"No existe artefacto para firma {compilation_signature}")

        return execute_compiled_artifact(
            artifact,
            work_unit_id=f"queue::{job.job_id}::{job.attempts + 1}",
            global_args=global_args,
            env_overrides=env_overrides,
            timeout_seconds=timeout_seconds,
            temporary_root=Path(artifact.output_dir) / ".tmp_exec",
        )

    def _select_runnable(
        self,
        candidates: tuple[QueueJobRecord, ...],
    ) -> tuple[QueueJobRecord, ...]:
        selected: list[QueueJobRecord] = []
        running_count_by_sub: dict[str, int] = {}

        for job in candidates:
            if len(selected) >= self.config.max_workers:
                break
            sub_id = job.subscription_id
            if sub_id is None:
                selected.append(job)
                continue
            current = running_count_by_sub.get(sub_id, 0)
            if current >= self.config.max_concurrent_by_subscription:
                continue
            selected.append(job)
            running_count_by_sub[sub_id] = current + 1

        return tuple(selected)

    def _now_iso(self) -> str:
        return self._now_provider().isoformat(timespec="seconds")


def _is_recoverable(result: ExecutedJobResult) -> bool:
    return result.severity == FailureSeverity.RECOVERABLE


def _queue_cache_context(job: QueueJobRecord):
    from src.core.cache_system import CacheContext

    attempts_marker = f"{job.signature}:{job.attempts}"
    return CacheContext(
        file_fingerprint=attempts_marker,
        content_hash=attempts_marker,
        config_signature=attempts_marker,
        ytdl_sub_conf_signature=attempts_marker,
    )
