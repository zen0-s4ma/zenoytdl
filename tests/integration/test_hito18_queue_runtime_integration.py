from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.core import CoreCacheSystem, QueueRuntime, QueueRuntimeConfig
from src.integration.ytdl_sub.compiler import CompiledSubscriptionArtifact
from src.integration.ytdl_sub.executor import (
    ExecutedJobResult,
    ExecutionErrorType,
    ExecutionJobUnit,
    FailureSeverity,
    PreparedExecutionCommand,
)
from src.persistence import QueueJobEnvelope, SQLiteOperationalState


@pytest.mark.integration
def test_hito18_integration_workers_process_priority_retry_and_dead_letter(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()

    state.enqueue_job(
        QueueJobEnvelope(
            job_id="job-high",
            queue_kind="sync",
            priority=100,
            subscription_id="sub-a",
            payload={"compilation_signature": "sig-high"},
            max_attempts=3,
        )
    )
    state.enqueue_job(
        QueueJobEnvelope(
            job_id="job-low",
            queue_kind="sync",
            priority=10,
            subscription_id="sub-b",
            payload={"compilation_signature": "sig-low"},
            max_attempts=1,
        )
    )

    runtime = QueueRuntime(
        state=state,
        cache=CoreCacheSystem(),
        config=QueueRuntimeConfig(max_workers=2, max_concurrent_by_subscription=1),
        now_provider=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    calls = {"job-high": 0, "job-low": 0}

    def fake_execute(job, **kwargs):
        calls[job.job_id] += 1
        if job.job_id == "job-high" and calls[job.job_id] == 1:
            return _result(job.job_id, FailureSeverity.RECOVERABLE)
        if job.job_id == "job-low":
            return _result(job.job_id, FailureSeverity.NON_RECOVERABLE)
        return _success(job.job_id)

    runtime._execute_single = fake_execute

    r1 = runtime.step(
        artifacts_by_signature={
            "sig-high": _artifact(tmp_path, "sub-a", "sig-high"),
            "sig-low": _artifact(tmp_path, "sub-b", "sig-low"),
        }
    )
    assert r1.retry_jobs == ("job-high",)
    assert r1.dead_letter_jobs == ("job-low",)

    state.transition_queue_job_status(job_id="job-high", next_status="queued")
    r2 = runtime.step(artifacts_by_signature={"sig-high": _artifact(tmp_path, "sub-a", "sig-high")})
    assert r2.completed_jobs == ("job-high",)

    high = state.get_queue_job("job-high")
    low = state.get_queue_job("job-low")
    assert high is not None and high.status == "completed"
    assert low is not None and low.status == "dead_letter"
    assert len(state.list_dead_letters()) == 1


# helpers

def _artifact(tmp_path: Path, subscription_id: str, signature: str) -> CompiledSubscriptionArtifact:
    base = tmp_path / signature
    base.mkdir(parents=True, exist_ok=True)
    artifact_yaml = base / "artifact.yaml"
    artifact_yaml.write_text(
        "subscription:\n  invocation:\n    binary: ytdl-sub\n    mode: sub\n",
        encoding="utf-8",
    )
    metadata = base / "metadata.json"
    metadata.write_text(
        '{"profile_id":"profile-main","compilation_signature":"' + signature + '"}',
        encoding="utf-8",
    )
    return CompiledSubscriptionArtifact(
        subscription_id=subscription_id,
        output_dir=base,
        layout_name=base.name,
        artifact_yaml_path=artifact_yaml,
        metadata_json_path=metadata,
        compilation_signature=signature,
        effective_signature="eff-1",
        translation_signature="tr-1",
        reused_previous=False,
    )


def _success(job_id: str) -> ExecutedJobResult:
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


def _result(job_id: str, severity: FailureSeverity) -> ExecutedJobResult:
    payload = _success(job_id)
    return ExecutedJobResult(
        job=payload.job,
        command=payload.command,
        exit_code=1,
        stdout="",
        stderr="boom",
        status="failed",
        error_type=ExecutionErrorType.NON_ZERO_EXIT,
        severity=severity,
        error_message="boom",
    )
