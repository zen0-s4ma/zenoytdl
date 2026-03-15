from __future__ import annotations

from datetime import datetime, timezone

from src.integration.ytdl_sub.compiler import CompiledArtifactBatch
from src.integration.ytdl_sub.executor import ExecutedJobResult, execute_compiled_batch
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
    """Ejecuta el batch Hito 12 y persiste el estado operativo en SQLite (Hito 13)."""
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

    started_at = _utc_now()
    results = execute_compiled_batch(
        batch,
        global_args=global_args,
        env_overrides=env_overrides,
        timeout_seconds=timeout_seconds,
    )
    finished_at = _utc_now()

    persisted: list[PersistedRunRecord] = []
    for result in results:
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
            known_item_identifier=f"{result.job.subscription_id}::{artifact.compilation_signature[:12]}",
            known_item_signature=artifact.compilation_signature,
        )
        persisted.append(state.record_execution(envelope))

    return results, tuple(persisted)


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
