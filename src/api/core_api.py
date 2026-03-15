from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import (
    EffectiveResolutionError,
    load_parsed_config_bundle,
    resolve_effective_config_for_subscription,
    resolve_effective_configs,
    serialize_effective_configs,
)
from src.core import CachedCorePipeline, CoreCacheSystem, QueueRuntime
from src.domain import JobPriority
from src.integration.ytdl_sub.compiler import CompiledArtifactBatch
from src.persistence import QueueJobEnvelope, QueueJobRecord, SQLiteOperationalState


class CoreAPIError(ValueError):
    def __init__(self, *, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
        }


@dataclass(frozen=True)
class SyncRequest:
    config_dir: str
    output_root: str
    priority: int = int(JobPriority.NORMAL)
    max_attempts: int = 3


@dataclass(frozen=True)
class RetryRequest:
    job_ids: tuple[str, ...] | None = None


class CoreAPI:
    """Frontera programática estable del core para Hito 19."""

    def __init__(
        self,
        *,
        state: SQLiteOperationalState,
        cache: CoreCacheSystem | None = None,
        queue_runtime: QueueRuntime | None = None,
    ) -> None:
        self.state = state
        self.cache = cache or CoreCacheSystem()
        self.pipeline = CachedCorePipeline(self.cache)
        self.queue_runtime = queue_runtime or QueueRuntime(state=state, cache=self.cache)

    def list_profiles(self, *, config_dir: str) -> dict[str, Any]:
        bundle = load_parsed_config_bundle(config_dir)
        profiles = [
            {
                "name": item.name,
                "media_type": item.media_type,
                "quality_profile": item.quality_profile,
            }
            for item in bundle.profiles
        ]
        return _ok(
            {
                "profiles": profiles,
                "count": len(profiles),
                "config_signature": bundle.signature,
            }
        )

    def get_profile(self, *, config_dir: str, profile_name: str) -> dict[str, Any]:
        if not profile_name.strip():
            raise CoreAPIError(
                code="API_INVALID_PAYLOAD",
                message="profile_name no puede ser vacío",
            )
        bundle = load_parsed_config_bundle(config_dir)
        normalized = profile_name.strip().lower()
        for item in bundle.profiles:
            if item.name.lower() == normalized:
                return _ok(
                    {
                        "profile": {
                            "name": item.name,
                            "media_type": item.media_type,
                            "quality_profile": item.quality_profile,
                        }
                    }
                )

        raise CoreAPIError(
            code="API_NOT_FOUND",
            message=f"Perfil no encontrado: {profile_name}",
        )

    def list_subscriptions(self, *, config_dir: str) -> dict[str, Any]:
        bundle = load_parsed_config_bundle(config_dir)
        subscriptions = [
            {
                "name": item.name,
                "profile": item.profile,
                "enabled": item.enabled,
                "sources": list(item.sources),
                "schedule": {"mode": item.schedule.mode, "every_hours": item.schedule.every_hours},
            }
            for item in bundle.subscriptions
        ]
        return _ok(
            {
                "subscriptions": subscriptions,
                "count": len(subscriptions),
                "config_signature": bundle.signature,
            }
        )

    def get_subscription(self, *, config_dir: str, subscription_name: str) -> dict[str, Any]:
        if not subscription_name.strip():
            raise CoreAPIError(
                code="API_INVALID_PAYLOAD",
                message="subscription_name no puede ser vacío",
            )
        bundle = load_parsed_config_bundle(config_dir)
        normalized = subscription_name.strip().lower()
        for item in bundle.subscriptions:
            if item.name.lower() == normalized:
                return _ok(
                    {
                        "subscription": {
                            "name": item.name,
                            "profile": item.profile,
                            "enabled": item.enabled,
                            "sources": list(item.sources),
                            "schedule": {
                                "mode": item.schedule.mode,
                                "every_hours": item.schedule.every_hours,
                            },
                        }
                    }
                )
        raise CoreAPIError(
            code="API_NOT_FOUND",
            message=f"Suscripción no encontrada: {subscription_name}",
        )

    def validate_config(self, *, config_dir: str) -> dict[str, Any]:
        bundle = load_parsed_config_bundle(config_dir)
        report = self.pipeline.validate(bundle)
        return _ok({"validation": report.to_dict()})

    def resolve_effective_config(
        self,
        *,
        config_dir: str,
        subscription_name: str | None = None,
    ) -> dict[str, Any]:
        bundle = load_parsed_config_bundle(config_dir)
        if subscription_name is None:
            configs = resolve_effective_configs(bundle)
            return _ok({"resolved": serialize_effective_configs(configs)})
        try:
            resolved = resolve_effective_config_for_subscription(bundle, subscription_name)
        except EffectiveResolutionError as exc:
            raise CoreAPIError(code="API_NOT_FOUND", message=str(exc)) from exc
        return _ok({"resolved": resolved.to_dict()})

    def get_queue(self, *, include_terminal: bool = True) -> dict[str, Any]:
        jobs = [
            _serialize_queue_job(job)
            for job in self.state.list_queue_jobs(include_terminal=include_terminal)
        ]
        dead_letters = [_serialize_dead_letter(item) for item in self.state.list_dead_letters()]
        return _ok(
            {
                "queue_jobs": jobs,
                "dead_letters": dead_letters,
                "counts": {
                    "queue_jobs": len(jobs),
                    "dead_letters": len(dead_letters),
                },
            }
        )

    def trigger_sync(self, payload: SyncRequest) -> dict[str, Any]:
        self._validate_sync_payload(payload)
        bundle = load_parsed_config_bundle(payload.config_dir)
        batch = self.pipeline.compile(bundle, Path(payload.output_root))
        enqueued = self._enqueue_batch_jobs(
            batch,
            priority=payload.priority,
            max_attempts=payload.max_attempts,
        )
        return _ok(
            {
                "sync": {
                    "artifacts": [item.to_dict() for item in batch.artifacts],
                    "enqueued_jobs": enqueued,
                    "total_enqueued": len(enqueued),
                }
            }
        )

    def process_queue_step(
        self,
        *,
        config_dir: str,
        output_root: str,
        timeout_seconds: float = 300.0,
    ) -> dict[str, Any]:
        bundle = load_parsed_config_bundle(config_dir)
        batch = self.pipeline.compile(bundle, Path(output_root))
        artifacts = {item.compilation_signature: item for item in batch.artifacts}
        report = self.queue_runtime.step(
            artifacts_by_signature=artifacts,
            timeout_seconds=timeout_seconds,
        )
        return _ok(
            {
                "queue_step": {
                    "claimed_jobs": list(report.claimed_jobs),
                    "completed_jobs": list(report.completed_jobs),
                    "retry_jobs": list(report.retry_jobs),
                    "dead_letter_jobs": list(report.dead_letter_jobs),
                    "skipped_jobs": list(report.skipped_jobs),
                }
            }
        )

    def get_history(self, *, config_dir: str) -> dict[str, Any]:
        bundle = load_parsed_config_bundle(config_dir)
        snapshots: list[dict[str, Any]] = []
        for sub in bundle.subscriptions:
            self.state.upsert_subscription(
                subscription_id=sub.name,
                profile_id=sub.profile,
                source_kind="channel",
                source_value=sub.sources[0],
                config_signature=bundle.signature,
            )
            snapshots.append(
                self.pipeline.get_recent_subscription_state(
                    state=self.state,
                    subscription_id=sub.name,
                )
            )
        return _ok({"history": snapshots, "count": len(snapshots)})

    def purge_history(
        self,
        *,
        subscription_id: str,
        max_items: int,
        profile_id: str = "api",
    ) -> dict[str, Any]:
        if max_items <= 0:
            raise CoreAPIError(
                code="API_INVALID_PAYLOAD",
                message="max_items debe ser > 0",
            )
        purged = self.state.apply_retention_policy(
            subscription_id=subscription_id,
            profile_id=profile_id,
            max_items=max_items,
            triggering_run_id=0,
        )
        return _ok({"purged": [item.item_identifier for item in purged], "count": len(purged)})

    def purge_cache(self, *, scope: str | None = None) -> dict[str, Any]:
        self.cache.purge(scope=scope)
        return _ok(
            {
                "cache": {
                    "purged_scope": scope or "*",
                    "metrics": self.cache.metrics_snapshot(),
                }
            }
        )

    def retry_failed_jobs(self, payload: RetryRequest) -> dict[str, Any]:
        job_ids = self._resolve_retry_candidates(payload)
        retried: list[dict[str, Any]] = []

        for job_id in job_ids:
            job = self.state.get_queue_job(job_id)
            if job is None:
                continue
            if job.status == "retry_pending":
                updated = self.state.transition_queue_job_status(
                    job_id=job_id,
                    next_status="queued",
                )
                retried.append({"job_id": updated.job_id, "mode": "reactivate"})
                continue
            if job.status == "dead_letter":
                new_job = self._requeue_dead_letter(job)
                retried.append({"job_id": new_job.job_id, "mode": "new_job", "retry_of": job_id})

        return _ok({"retried": retried, "count": len(retried)})

    def _resolve_retry_candidates(self, payload: RetryRequest) -> tuple[str, ...]:
        if payload.job_ids is not None:
            if not payload.job_ids:
                raise CoreAPIError(
                    code="API_INVALID_PAYLOAD",
                    message="job_ids no puede ser vacío cuando se especifica",
                )
            return tuple(job_id.strip() for job_id in payload.job_ids if job_id.strip())

        jobs = self.state.list_queue_jobs(include_terminal=True)
        return tuple(job.job_id for job in jobs if job.status in {"retry_pending", "dead_letter"})

    def _requeue_dead_letter(self, job: QueueJobRecord) -> QueueJobRecord:
        retry_token = hashlib.sha1(f"{job.job_id}:{job.attempts}".encode("utf-8")).hexdigest()[:8]
        new_id = f"{job.job_id}::retry::{retry_token}"
        envelope = QueueJobEnvelope(
            job_id=new_id,
            queue_kind=job.queue_kind,
            priority=job.priority,
            subscription_id=job.subscription_id,
            profile_id=job.profile_id,
            resource_kind=job.resource_kind,
            resource_id=job.resource_id,
            payload={**job.payload, "retry_of": job.job_id},
            max_attempts=job.max_attempts,
        )
        created, _ = self.state.enqueue_job(envelope)
        return created

    def _enqueue_batch_jobs(
        self,
        batch: CompiledArtifactBatch,
        *,
        priority: int,
        max_attempts: int,
    ) -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []
        for artifact in batch.artifacts:
            job_id = f"sync::{artifact.subscription_id}::{artifact.compilation_signature[:10]}"
            record, is_new = self.queue_runtime.enqueue_execution_job(
                job_id=job_id,
                artifact=artifact,
                priority=priority,
                max_attempts=max_attempts,
            )
            created.append(
                {
                    "job_id": record.job_id,
                    "subscription_id": record.subscription_id,
                    "signature": record.signature,
                    "created": is_new,
                }
            )
        return created

    def _validate_sync_payload(self, payload: SyncRequest) -> None:
        if payload.priority < 0:
            raise CoreAPIError(
                code="API_INVALID_PAYLOAD",
                message="priority debe ser >= 0",
                details={"priority": payload.priority},
            )
        if payload.max_attempts <= 0:
            raise CoreAPIError(
                code="API_INVALID_PAYLOAD",
                message="max_attempts debe ser > 0",
                details={"max_attempts": payload.max_attempts},
            )
        if not payload.config_dir.strip() or not payload.output_root.strip():
            raise CoreAPIError(
                code="API_INVALID_PAYLOAD",
                message="config_dir y output_root son obligatorios",
            )


def _serialize_queue_job(job: QueueJobRecord) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "queue_kind": job.queue_kind,
        "status": job.status,
        "priority": job.priority,
        "signature": job.signature,
        "subscription_id": job.subscription_id,
        "profile_id": job.profile_id,
        "resource_kind": job.resource_kind,
        "resource_id": job.resource_id,
        "payload": dict(job.payload),
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "scheduled_at": job.scheduled_at,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _serialize_dead_letter(dead: Any) -> dict[str, Any]:
    return {
        "job_id": dead.job_id,
        "signature": dead.signature,
        "queue_kind": dead.queue_kind,
        "subscription_id": dead.subscription_id,
        "profile_id": dead.profile_id,
        "attempts": dead.attempts,
        "max_attempts": dead.max_attempts,
        "error_type": dead.error_type,
        "error_message": dead.error_message,
        "failed_at": dead.failed_at,
    }


def _ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "data": data}
