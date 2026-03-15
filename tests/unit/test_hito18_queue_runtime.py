from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.core import CoreCacheSystem, QueueRuntime, QueueRuntimeConfig, RetryPolicy
from src.integration.ytdl_sub.compiler import CompiledSubscriptionArtifact
from src.integration.ytdl_sub.executor import (
    ExecutedJobResult,
    ExecutionErrorType,
    ExecutionJobUnit,
    FailureSeverity,
    PreparedExecutionCommand,
)
from src.persistence import QueueJobEnvelope, SQLiteOperationalState


@pytest.mark.unit
def test_hito18_retry_backoff_policy_is_exponential_and_capped() -> None:
    policy = RetryPolicy(base_seconds=4, max_seconds=20)

    assert policy.compute_delay_seconds(attempt_number=1) == 4
    assert policy.compute_delay_seconds(attempt_number=2) == 8
    assert policy.compute_delay_seconds(attempt_number=3) == 16
    assert policy.compute_delay_seconds(attempt_number=4) == 20


@pytest.mark.unit
def test_hito18_runtime_applies_subscription_concurrency_limits(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()

    state.enqueue_job(
        QueueJobEnvelope(
            job_id="job-a",
            queue_kind="sync",
            priority=100,
            subscription_id="sub-1",
            payload={"compilation_signature": "sig-a"},
        )
    )
    state.enqueue_job(
        QueueJobEnvelope(
            job_id="job-b",
            queue_kind="sync",
            priority=90,
            subscription_id="sub-1",
            payload={"compilation_signature": "sig-b"},
        )
    )

    runtime = QueueRuntime(
        state=state,
        cache=CoreCacheSystem(),
        config=QueueRuntimeConfig(max_workers=2, max_concurrent_by_subscription=1),
        now_provider=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    selected = runtime._select_runnable(state.list_runnable_queue_jobs())

    assert [job.job_id for job in selected] == ["job-a"]


@pytest.mark.unit
def test_hito18_runtime_moves_recoverable_failure_to_retry_pending(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    state.enqueue_job(
        QueueJobEnvelope(
            job_id="job-retry",
            queue_kind="sync",
            priority=100,
            subscription_id="sub-1",
            payload={"compilation_signature": "sig-r"},
            max_attempts=3,
        )
    )

    runtime = QueueRuntime(
        state=state,
        cache=CoreCacheSystem(),
        now_provider=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    runtime._execute_single = lambda *args, **kwargs: _failed_result(
        severity=FailureSeverity.RECOVERABLE
    )
    report = runtime.step(artifacts_by_signature={"sig-r": _artifact(tmp_path, "sub-1", "sig-r")})

    job = state.get_queue_job("job-retry")
    assert report.retry_jobs == ("job-retry",)
    assert job is not None and job.status == "retry_pending"
    assert job.attempts == 1


@pytest.mark.unit
def test_hito18_runtime_moves_non_recoverable_failure_to_dead_letter(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    state.enqueue_job(
        QueueJobEnvelope(
            job_id="job-dead",
            queue_kind="sync",
            priority=100,
            subscription_id="sub-1",
            payload={"compilation_signature": "sig-d"},
            max_attempts=3,
        )
    )

    runtime = QueueRuntime(
        state=state,
        cache=CoreCacheSystem(),
        now_provider=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    runtime._execute_single = lambda *args, **kwargs: _failed_result(
        severity=FailureSeverity.NON_RECOVERABLE
    )

    report = runtime.step(artifacts_by_signature={"sig-d": _artifact(tmp_path, "sub-1", "sig-d")})

    job = state.get_queue_job("job-dead")
    dead_letters = state.list_dead_letters()
    assert report.dead_letter_jobs == ("job-dead",)
    assert job is not None and job.status == "dead_letter"
    assert len(dead_letters) == 1
    assert dead_letters[0].job_id == "job-dead"


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


def _failed_result(*, severity: FailureSeverity) -> ExecutedJobResult:
    return ExecutedJobResult(
        job=ExecutionJobUnit(
            job_id="job",
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
        exit_code=1,
        stdout="",
        stderr="boom",
        status="failed",
        error_type=ExecutionErrorType.NON_ZERO_EXIT,
        severity=severity,
        error_message="boom",
    )
