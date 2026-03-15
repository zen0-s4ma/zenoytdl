from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.core import CoreCacheSystem, QueueRuntime
from src.integration.ytdl_sub.compiler import CompiledSubscriptionArtifact
from src.integration.ytdl_sub.executor import (
    ExecutedJobResult,
    ExecutionErrorType,
    ExecutionJobUnit,
    FailureSeverity,
    PreparedExecutionCommand,
)
from src.persistence import QueueJobEnvelope, SQLiteOperationalState


@pytest.mark.e2e
def test_hito18_e2e_queue_populated_workers_and_final_states(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()

    for job_id, sig in (("ok-job", "sig-ok"), ("retry-job", "sig-r"), ("dead-job", "sig-d")):
        state.enqueue_job(
            QueueJobEnvelope(
                job_id=job_id,
                queue_kind="sync",
                priority=50,
                subscription_id=f"sub-{job_id}",
                payload={"compilation_signature": sig},
                max_attempts=2,
            )
        )

    runtime = QueueRuntime(
        state=state,
        cache=CoreCacheSystem(),
        now_provider=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    executed = {"retry-job": 0}

    def fake_execute(job, **kwargs):
        if job.job_id == "ok-job":
            return _mk_result(job.job_id, ok=True)
        if job.job_id == "retry-job":
            executed["retry-job"] += 1
            return _mk_result(job.job_id, ok=executed["retry-job"] >= 2)
        return _mk_result(job.job_id, ok=False, recoverable=False)

    runtime._execute_single = fake_execute

    runtime.step(
        artifacts_by_signature={
            "sig-ok": _artifact(tmp_path, "sub-ok-job", "sig-ok"),
            "sig-r": _artifact(tmp_path, "sub-retry-job", "sig-r"),
            "sig-d": _artifact(tmp_path, "sub-dead-job", "sig-d"),
        }
    )
    state.transition_queue_job_status(job_id="retry-job", next_status="queued")
    runtime.step(artifacts_by_signature={"sig-r": _artifact(tmp_path, "sub-retry-job", "sig-r")})

    jobs = {j.job_id: j for j in state.list_queue_jobs()}
    assert jobs["ok-job"].status == "completed"
    assert jobs["retry-job"].status == "completed"
    assert jobs["dead-job"].status == "dead_letter"
    assert len(state.list_dead_letters()) == 1


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


def _mk_result(job_id: str, *, ok: bool, recoverable: bool = True) -> ExecutedJobResult:
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
        exit_code=0 if ok else 1,
        stdout="ok" if ok else "",
        stderr="" if ok else "boom",
        status="success" if ok else "failed",
        error_type=ExecutionErrorType.NONE if ok else ExecutionErrorType.NON_ZERO_EXIT,
        severity=(
            FailureSeverity.NONE
            if ok
            else (
                FailureSeverity.RECOVERABLE
                if recoverable
                else FailureSeverity.NON_RECOVERABLE
            )
        ),
        error_message=None if ok else "boom",
    )
