from pathlib import Path

import pytest

from src.domain import Job, JobKind, JobPriority, JobStatus, sign_job
from src.persistence import QueueJobEnvelope, SQLiteOperationalState


@pytest.mark.unit
def test_hito17_job_entity_supports_queue_states_priority_and_associations() -> None:
    job = Job(
        id="job-queue-1",
        job_kind=JobKind.DOWNLOAD,
        status=JobStatus.QUEUED,
        priority=int(JobPriority.HIGH),
        subscription_id="sub-news",
        profile_id="profile-main",
        resource_kind="item",
        resource_id="video-001",
        payload={"source": "sync", "attempt": 0},
    )

    assert job.signature is not None
    assert len(job.signature) == 64
    assert job.can_transition_to(JobStatus.SCHEDULED) is True
    assert job.can_transition_to(JobStatus.COMPLETED) is False


@pytest.mark.unit
def test_hito17_job_signature_is_stable_for_same_semantics() -> None:
    sig_a = sign_job(
        job_kind=JobKind.SYNC,
        subscription_id="sub-a",
        profile_id="profile-a",
        resource_kind="channel",
        resource_id="channel-1",
        payload={"phase": "incremental", "limit": 20},
    )
    sig_b = sign_job(
        job_kind=JobKind.SYNC,
        subscription_id="sub-a",
        profile_id="profile-a",
        resource_kind="channel",
        resource_id="channel-1",
        payload={"limit": 20, "phase": "incremental"},
    )

    assert sig_a == sig_b


@pytest.mark.unit
def test_hito17_job_requires_association_to_subscription_profile_or_resource() -> None:
    with pytest.raises(ValueError, match="asociarse"):
        Job(
            id="job-invalid",
            job_kind=JobKind.MAINTENANCE,
            status=JobStatus.QUEUED,
            payload={"operation": "vacuum"},
        )


@pytest.mark.unit
def test_hito17_state_transition_validation_in_persistence(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    _, created = state.enqueue_job(
        QueueJobEnvelope(
            job_id="q-job-1",
            queue_kind="validation",
            priority=80,
            subscription_id="sub-a",
            payload={"signature": "cfg-v1"},
        )
    )

    assert created is True
    state.transition_queue_job_status(job_id="q-job-1", next_status="scheduled")
    with pytest.raises(ValueError, match="transición inválida"):
        state.transition_queue_job_status(job_id="q-job-1", next_status="completed")
