from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.api import CoreAPI, SyncRequest
from src.core import CoreCacheSystem, QueueRuntime
from src.integration.ytdl_sub.executor import (
    ExecutedJobResult,
    ExecutionErrorType,
    ExecutionJobUnit,
    FailureSeverity,
    PreparedExecutionCommand,
)
from src.persistence import ExecutionPersistenceEnvelope, SQLiteOperationalState


@pytest.mark.integration
def test_hito20_integration_consolidates_core_flow_without_new_semantics(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()

    cache = CoreCacheSystem()
    runtime = QueueRuntime(
        state=state,
        cache=cache,
        now_provider=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    api = CoreAPI(state=state, cache=cache, queue_runtime=runtime)

    config_dir = "tests/fixtures/hito11/valid/single"
    output_root = str(tmp_path / "compiled")

    assert api.validate_config(config_dir=config_dir)["data"]["validation"]["ok"] is True
    resolved = api.resolve_effective_config(config_dir=config_dir)
    assert resolved["data"]["resolved"]["effective_configs"]

    first_sync = api.trigger_sync(
        SyncRequest(config_dir=config_dir, output_root=output_root, priority=50)
    )
    second_sync = api.trigger_sync(
        SyncRequest(config_dir=config_dir, output_root=output_root, priority=50)
    )
    assert first_sync["data"]["sync"]["total_enqueued"] == 1
    assert second_sync["data"]["sync"]["enqueued_jobs"][0]["created"] is False

    runtime._execute_single = lambda job, **kwargs: _ok_result(job.job_id)
    step = api.process_queue_step(config_dir=config_dir, output_root=output_root)
    assert step["data"]["queue_step"]["completed_jobs"]

    artifact = first_sync["data"]["sync"]["artifacts"][0]
    sub_id = artifact["subscription_id"]
    signature = artifact["compilation_signature"]
    item_id = f"{sub_id}::{signature[:12]}"

    state.upsert_subscription(
        subscription_id=sub_id,
        profile_id="profile_tv",
        source_kind="channel",
        source_value="https://example.invalid/channel",
        config_signature="cfg-h20",
    )
    run = state.record_execution(
        ExecutionPersistenceEnvelope(
            job_id="h20-run-1",
            subscription_id=sub_id,
            profile_id="profile_tv",
            status="success",
            error_type="none",
            severity="none",
            exit_code=0,
            error_message=None,
            stdout="ok",
            stderr="",
            command_payload={"args": ["ytdl-sub", "sub"]},
            config_signature="cfg-h20",
            effective_signature="eff-h20",
            translation_signature="tr-h20",
            compilation_signature=signature,
            artifact_yaml_path="/tmp/artifact.yaml",
            metadata_json_path="/tmp/metadata.json",
            started_at="2026-01-01T00:00:00+00:00",
            finished_at="2026-01-01T00:00:01+00:00",
            duration_ms=1000,
            known_item_identifier=item_id,
            known_item_signature=signature,
            decision_reason="new_item",
        )
    )

    anti = state.decide_anti_redownload(
        subscription_id=sub_id,
        item_identifier=item_id,
        item_signature=signature,
    )
    assert anti.action == "discard"

    purged = state.apply_retention_policy(
        subscription_id=sub_id,
        profile_id="profile_tv",
        max_items=1,
        triggering_run_id=run.run_id,
    )
    assert purged == ()

    cache_before = cache.metrics_snapshot()
    api.purge_cache(scope="compile")
    cache_after = cache.metrics_snapshot()
    assert "config_compilation" in cache_before
    assert cache_after["config_compilation"]["hits"] >= 0


def _ok_result(job_id: str) -> ExecutedJobResult:
    return ExecutedJobResult(
        job=ExecutionJobUnit(
            job_id=job_id,
            subscription_id="sub",
            profile_id="profile",
            compilation_signature="sig",
            artifact_dir=Path("."),
            artifact_yaml_path=Path("artifact.yaml"),
            metadata_json_path=Path("metadata.json"),
        ),
        command=PreparedExecutionCommand(
            binary="ytdl-sub",
            binary_path="/bin/ytdl-sub",
            args=("/bin/ytdl-sub", "sub"),
            cwd=Path("."),
            env={},
            timeout_seconds=1,
            temporary_dir=Path("."),
            invocation_metadata={},
        ),
        exit_code=0,
        stdout="ok",
        stderr="",
        status="success",
        error_type=ExecutionErrorType.NONE,
        severity=FailureSeverity.NONE,
        error_message=None,
    )
