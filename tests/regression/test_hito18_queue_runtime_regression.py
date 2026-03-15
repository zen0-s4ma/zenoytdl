from pathlib import Path

import pytest

from src.persistence import QueueJobEnvelope, SQLiteOperationalState


@pytest.mark.regression
def test_hito18_regression_mixed_outcome_snapshot(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()

    state.enqueue_job(
        QueueJobEnvelope(
            job_id="mix-success",
            queue_kind="sync",
            priority=100,
            subscription_id="sub-a",
            payload={"segment": "ok"},
        )
    )
    state.enqueue_job(
        QueueJobEnvelope(
            job_id="mix-retry",
            queue_kind="sync",
            priority=80,
            subscription_id="sub-b",
            payload={"segment": "retry"},
            max_attempts=3,
        )
    )
    state.enqueue_job(
        QueueJobEnvelope(
            job_id="mix-dead",
            queue_kind="sync",
            priority=70,
            subscription_id="sub-c",
            payload={"segment": "dead"},
            max_attempts=1,
        )
    )

    state.claim_queue_job(job_id="mix-success")
    state.complete_queue_job(job_id="mix-success")

    state.claim_queue_job(job_id="mix-retry")
    state.schedule_queue_retry(job_id="mix-retry", scheduled_at="2026-01-01T00:00:10+00:00")

    state.claim_queue_job(job_id="mix-dead")
    state.dead_letter_queue_job(
        job_id="mix-dead",
        error_type="non_recoverable",
        error_message="boom",
    )

    snapshot = {job.job_id: job.status for job in state.list_queue_jobs()}
    assert snapshot == {
        "mix-success": "completed",
        "mix-retry": "retry_pending",
        "mix-dead": "dead_letter",
    }
    assert [d.job_id for d in state.list_dead_letters()] == ["mix-dead"]
