from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.integration.ytdl_sub.compiler import CompiledArtifactBatch
from src.integration.ytdl_sub.executor import (
    ExecutedJobResult,
    ExecutionErrorType,
    FailureSeverity,
    PreparedExecutionCommand,
    execute_compiled_artifact,
    prepare_execution_job,
)
from src.persistence.sqlite_state import (
    ExecutionPersistenceEnvelope,
    PersistedRunRecord,
    SQLiteOperationalState,
)


def execute_batch_with_operational_state(
    batch: CompiledArtifactBatch,
    *,
    state: SQLiteOperationalState,
    config_signature: str,
    subscription_sources: dict[str, tuple[str, str]],
    global_args: tuple[str, ...] = (),
    env_overrides: dict[str, str] | None = None,
    timeout_seconds: float = 300.0,
) -> tuple[ExecutedJobResult, tuple[PersistedRunRecord, ...]]:
    """Ejecuta el batch con anti-redescarga y persiste estado operativo en SQLite."""
    state.init_schema()

    artifact_by_signature = {item.compilation_signature: item for item in batch.artifacts}
    for artifact in batch.artifacts:
        source_kind, source_value = subscription_sources[artifact.subscription_id]
        state.upsert_subscription(
            subscription_id=artifact.subscription_id,
            profile_id=_read_profile_id(artifact.metadata_json_path.read_text(encoding="utf-8")),
            source_kind=source_kind,
            source_value=source_value,
            config_signature=config_signature,
        )

    results: list[ExecutedJobResult] = []
    persisted: list[PersistedRunRecord] = []
    for artifact in batch.artifacts:
        started_at = _utc_now()
        item_identifier = f"{artifact.subscription_id}::{artifact.compilation_signature[:12]}"
        decision = state.decide_anti_redownload(
            subscription_id=artifact.subscription_id,
            item_identifier=item_identifier,
            item_signature=artifact.compilation_signature,
        )

        if decision.action == "discard":
            result = _build_discarded_result(
                artifact=artifact,
                reason=decision.reason,
                previous_status=decision.previous_status,
            )
        else:
            result = execute_compiled_artifact(
                artifact,
                work_unit_id=f"batch::{artifact.subscription_id}::{artifact.compilation_signature[:8]}",
                global_args=global_args,
                env_overrides=env_overrides,
                timeout_seconds=timeout_seconds,
                temporary_root=batch.output_root / ".tmp_exec",
            )
        results.append(result)

        finished_at = _utc_now()
        artifact = artifact_by_signature[result.job.compilation_signature]
        envelope = ExecutionPersistenceEnvelope(
            job_id=result.job.job_id,
            subscription_id=result.job.subscription_id,
            profile_id=result.job.profile_id,
            status=result.status,
            error_type=result.error_type.value,
            severity=result.severity.value,
            exit_code=result.exit_code,
            error_message=result.error_message,
            stdout=result.stdout,
            stderr=result.stderr,
            command_payload=result.command.to_dict(),
            config_signature=config_signature,
            effective_signature=artifact.effective_signature,
            translation_signature=artifact.translation_signature,
            compilation_signature=artifact.compilation_signature,
            artifact_yaml_path=str(artifact.artifact_yaml_path),
            metadata_json_path=str(artifact.metadata_json_path),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(0, _diff_ms(started_at, finished_at)),
            known_item_identifier=item_identifier,
            known_item_signature=artifact.compilation_signature,
            decision_reason=decision.reason,
            discard_reason=decision.reason if result.status == "discarded" else None,
            failure_reason=(
                _failure_reason(result)
                if result.status == "failed"
                else None
            ),
        )
        persisted.append(state.record_execution(envelope))

    return tuple(results), tuple(persisted)


def _build_discarded_result(
    *,
    artifact,
    reason: str,
    previous_status: str | None,
) -> ExecutedJobResult:
    job = prepare_execution_job(
        artifact,
        work_unit_id=f"batch::{artifact.subscription_id}::{artifact.compilation_signature[:8]}::discard",
    )
    command = PreparedExecutionCommand(
        binary="",
        binary_path="",
        args=tuple(),
        cwd=artifact.output_dir,
        env={},
        timeout_seconds=0.0,
        temporary_dir=Path(artifact.output_dir),
        invocation_metadata={
            "decision": "discard",
            "reason": reason,
            "previous_status": previous_status,
        },
    )
    return ExecutedJobResult(
        job=job,
        command=command,
        exit_code=None,
        stdout="",
        stderr="",
        status="discarded",
        error_type=ExecutionErrorType.NONE,
        severity=FailureSeverity.NONE,
        error_message=f"Elemento descartado: {reason}",
    )


def _read_profile_id(metadata_json: str) -> str:
    import json

    payload = json.loads(metadata_json)
    profile_id = payload.get("profile_id")
    if not isinstance(profile_id, str) or not profile_id:
        raise ValueError("metadata.profile_id inválido para persistencia")
    return profile_id


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _diff_ms(started_at: str, finished_at: str) -> int:
    started = datetime.fromisoformat(started_at)
    finished = datetime.fromisoformat(finished_at)
    return int((finished - started).total_seconds() * 1000)


def _failure_reason(result: ExecutedJobResult) -> str:
    return f"{result.error_type.value}:{result.error_message or ''}"
