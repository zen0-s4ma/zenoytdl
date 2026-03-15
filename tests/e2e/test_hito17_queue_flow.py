from pathlib import Path

import pytest

from src.persistence import QueueJobEnvelope, SQLiteOperationalState


@pytest.mark.e2e
def test_hito17_e2e_queue_creation_and_full_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    state = SQLiteOperationalState(db_path)
    state.init_schema()

    envelopes = (
        QueueJobEnvelope(
            job_id="job-validation-1",
            queue_kind="validation",
            priority=100,
            subscription_id="sub-1",
            profile_id="profile-1",
            payload={"config_signature": "cfg-1"},
        ),
        QueueJobEnvelope(
            job_id="job-sync-1",
            queue_kind="sync",
            priority=70,
            subscription_id="sub-1",
            profile_id="profile-1",
            payload={"mode": "delta"},
        ),
        QueueJobEnvelope(
            job_id="job-maint-1",
            queue_kind="maintenance",
            priority=30,
            profile_id="profile-ops",
            payload={"operation": "vacuum"},
        ),
    )

    for envelope in envelopes:
        state.enqueue_job(envelope)

    state.transition_queue_job_status(job_id="job-validation-1", next_status="running")
    state.transition_queue_job_status(job_id="job-validation-1", next_status="completed")

    queue = state.list_queue_jobs()

    assert [job.job_id for job in queue] == [
        "job-validation-1",
        "job-sync-1",
        "job-maint-1",
    ]
    assert queue[0].status == "completed"
    assert queue[1].status == "queued"
    assert queue[2].status == "queued"
    assert queue[0].signature
