from pathlib import Path

import pytest

from src.persistence import QueueJobEnvelope, SQLiteOperationalState


@pytest.mark.regression
def test_hito17_regression_canonical_queue_snapshot(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()

    canonical = (
        QueueJobEnvelope(
            job_id="job-001",
            queue_kind="validation",
            priority=100,
            subscription_id="sub-alpha",
            profile_id="profile-main",
            payload={"step": "validate"},
        ),
        QueueJobEnvelope(
            job_id="job-002",
            queue_kind="compilation",
            priority=90,
            subscription_id="sub-alpha",
            profile_id="profile-main",
            payload={"step": "compile"},
        ),
        QueueJobEnvelope(
            job_id="job-003",
            queue_kind="sync",
            priority=70,
            subscription_id="sub-alpha",
            profile_id="profile-main",
            payload={"step": "sync"},
        ),
        QueueJobEnvelope(
            job_id="job-004",
            queue_kind="download",
            priority=60,
            subscription_id="sub-alpha",
            profile_id="profile-main",
            resource_kind="item",
            resource_id="video-77",
            payload={"step": "download"},
        ),
        QueueJobEnvelope(
            job_id="job-005",
            queue_kind="postprocessing",
            priority=50,
            subscription_id="sub-alpha",
            profile_id="profile-main",
            resource_kind="item",
            resource_id="video-77",
            payload={"step": "post"},
        ),
        QueueJobEnvelope(
            job_id="job-006",
            queue_kind="maintenance",
            priority=20,
            profile_id="profile-ops",
            payload={"step": "cleanup"},
        ),
    )

    for envelope in canonical:
        state.enqueue_job(envelope)

    snapshot = state.list_queue_jobs()

    assert [job.job_id for job in snapshot] == [
        "job-001",
        "job-002",
        "job-003",
        "job-004",
        "job-005",
        "job-006",
    ]
    assert all(job.status == "queued" for job in snapshot)
    assert all(len(job.signature) == 64 for job in snapshot)
