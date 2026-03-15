from pathlib import Path

import pytest

from src.persistence import QueueJobEnvelope, SQLiteOperationalState


@pytest.mark.integration
def test_hito17_integration_queue_persists_and_orders_jobs_by_priority(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()

    state.enqueue_job(
        QueueJobEnvelope(
            job_id="job-low",
            queue_kind="sync",
            priority=10,
            subscription_id="sub-a",
            profile_id="profile-a",
            payload={"segment": "all"},
        )
    )
    state.enqueue_job(
        QueueJobEnvelope(
            job_id="job-high",
            queue_kind="download",
            priority=90,
            subscription_id="sub-a",
            profile_id="profile-a",
            resource_kind="item",
            resource_id="vid-1",
            payload={"segment": "delta"},
        )
    )

    jobs = state.list_queue_jobs()

    assert [job.job_id for job in jobs] == ["job-high", "job-low"]
    assert jobs[0].queue_kind == "download"
    assert jobs[1].queue_kind == "sync"


@pytest.mark.integration
def test_hito17_integration_queue_deduplicates_active_jobs_by_signature(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()

    first, created_first = state.enqueue_job(
        QueueJobEnvelope(
            job_id="job-a",
            queue_kind="maintenance",
            priority=50,
            profile_id="profile-maint",
            payload={"operation": "cleanup", "target": "tmp"},
        )
    )
    second, created_second = state.enqueue_job(
        QueueJobEnvelope(
            job_id="job-b",
            queue_kind="maintenance",
            priority=50,
            profile_id="profile-maint",
            payload={"target": "tmp", "operation": "cleanup"},
        )
    )

    assert created_first is True
    assert created_second is False
    assert second.job_id == first.job_id
    assert len(state.list_queue_jobs()) == 1
