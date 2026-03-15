from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.api import CoreAPI, RetryRequest, SyncRequest
from src.core import CoreCacheSystem, QueueRuntime
from src.integration.ytdl_sub.executor import FailureSeverity
from src.persistence import SQLiteOperationalState


@pytest.mark.integration
def test_hito19_integration_api_connects_validation_resolution_queue_cache_and_retry(
    tmp_path: Path,
) -> None:
    state = SQLiteOperationalState(tmp_path / 'state.sqlite')
    state.init_schema()
    runtime = QueueRuntime(
        state=state,
        cache=CoreCacheSystem(),
        now_provider=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    api = CoreAPI(state=state, queue_runtime=runtime)

    validated = api.validate_config(config_dir='tests/fixtures/hito11/valid/single')
    assert validated['data']['validation']['ok'] is True

    resolved = api.resolve_effective_config(config_dir='tests/fixtures/hito11/valid/single')
    assert resolved['ok'] is True
    assert resolved['data']['resolved']['effective_configs']

    sync = api.trigger_sync(
        SyncRequest(
            config_dir='tests/fixtures/hito11/valid/single',
            output_root=str(tmp_path / 'compiled'),
            priority=70,
            max_attempts=2,
        )
    )
    assert sync['data']['sync']['total_enqueued'] == 1

    queued_job = state.list_queue_jobs()[0]
    state.claim_queue_job(job_id=queued_job.job_id)
    state.dead_letter_queue_job(
        job_id=queued_job.job_id,
        error_type=FailureSeverity.NON_RECOVERABLE.value,
        error_message='boom',
    )

    retried = api.retry_failed_jobs(RetryRequest())
    assert retried['ok'] is True
    assert retried['data']['count'] == 1

    cache_info = api.purge_cache(scope='validation')
    assert cache_info['ok'] is True

    queue_view = api.get_queue(include_terminal=True)
    assert queue_view['data']['counts']['dead_letters'] == 1
