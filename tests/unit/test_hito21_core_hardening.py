from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.core import CoreCacheSystem, QueueRuntime, QueueRuntimeConfig
from src.persistence import QueueJobEnvelope, SQLiteOperationalState


@pytest.mark.unit
def test_hito21_queue_runtime_rejects_invalid_runtime_config(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()

    with pytest.raises(ValueError, match="QueueRuntimeConfig inválida"):
        QueueRuntime(
            state=state,
            cache=CoreCacheSystem(),
            config=QueueRuntimeConfig(max_workers=0, max_concurrent_by_subscription=1),
        )

    with pytest.raises(ValueError, match="QueueRuntimeConfig inválida"):
        QueueRuntime(
            state=state,
            cache=CoreCacheSystem(),
            config=QueueRuntimeConfig(max_workers=1, max_concurrent_by_subscription=0),
        )


@pytest.mark.unit
def test_hito21_queue_runtime_processes_one_job_when_max_workers_is_one(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()

    for idx in range(2):
        state.enqueue_job(
            QueueJobEnvelope(
                job_id=f"job-{idx}",
                queue_kind="sync",
                priority=100 - idx,
                subscription_id=f"sub-{idx}",
                payload={"compilation_signature": f"sig-{idx}"},
            )
        )

    runtime = QueueRuntime(
        state=state,
        cache=CoreCacheSystem(),
        config=QueueRuntimeConfig(max_workers=1, max_concurrent_by_subscription=1),
        now_provider=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    selected = runtime._select_runnable(state.list_runnable_queue_jobs())

    assert [job.job_id for job in selected] == ["job-0"]


@pytest.mark.unit
def test_hito21_final_core_example_bundle_is_complete() -> None:
    base = Path("examples/core-final")
    expected = (
        "general.yaml",
        "profiles.yaml",
        "subscriptions.yaml",
        "ytdl-sub-conf.yaml",
        "cache.yaml",
        "queues.yaml",
        "logging.yaml",
    )
    missing = [name for name in expected if not (base / name).is_file()]
    assert missing == []
