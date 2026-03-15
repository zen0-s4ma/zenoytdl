from pathlib import Path

import pytest

from src.api import CoreAPI, CoreAPIError, RetryRequest, SyncRequest
from src.core import CoreCacheSystem
from src.persistence import QueueJobEnvelope, SQLiteOperationalState


@pytest.mark.unit
def test_hito19_serialization_for_profiles_and_subscriptions(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / 'state.sqlite')
    state.init_schema()
    api = CoreAPI(state=state, cache=CoreCacheSystem())

    payload = api.list_profiles(config_dir='tests/fixtures/hito11/valid/single')
    assert payload['ok'] is True
    assert payload['data']['count'] == 1
    assert payload['data']['profiles'][0]['name'] == 'profile_tv'

    sub_payload = api.get_subscription(
        config_dir='tests/fixtures/hito11/valid/single',
        subscription_name='tech_channel',
    )
    assert sub_payload['ok'] is True
    assert sub_payload['data']['subscription']['profile'] == 'profile_tv'


@pytest.mark.unit
def test_hito19_payload_validation_for_sync_and_retry(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / 'state.sqlite')
    state.init_schema()
    api = CoreAPI(state=state)

    with pytest.raises(CoreAPIError, match='priority'):
        api.trigger_sync(SyncRequest(config_dir='x', output_root='y', priority=-1))

    with pytest.raises(CoreAPIError, match='job_ids no puede ser vacío'):
        api.retry_failed_jobs(RetryRequest(job_ids=tuple()))


@pytest.mark.unit
def test_hito19_queue_and_error_contract(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / 'state.sqlite')
    state.init_schema()
    state.enqueue_job(
        QueueJobEnvelope(
            job_id='job-1',
            queue_kind='sync',
            priority=10,
            subscription_id='sub-1',
            payload={'compilation_signature': 'sig-1'},
        )
    )
    api = CoreAPI(state=state)

    queue = api.get_queue()
    assert queue['ok'] is True
    assert queue['data']['counts']['queue_jobs'] == 1

    with pytest.raises(CoreAPIError) as exc:
        api.get_profile(config_dir='tests/fixtures/hito11/valid/single', profile_name='missing')
    assert exc.value.to_dict()['error']['code'] == 'API_NOT_FOUND'
