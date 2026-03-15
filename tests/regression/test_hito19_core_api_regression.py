from pathlib import Path

import pytest

from src.api import CoreAPI, SyncRequest
from src.persistence import SQLiteOperationalState


@pytest.mark.regression
def test_hito19_regression_api_contract_codes_payloads_and_side_effects(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / 'state.sqlite')
    state.init_schema()
    api = CoreAPI(state=state)

    config_dir = 'tests/fixtures/hito11/valid/single'
    output_root = str(tmp_path / 'compiled')

    profiles = api.list_profiles(config_dir=config_dir)
    subscriptions = api.list_subscriptions(config_dir=config_dir)
    validation = api.validate_config(config_dir=config_dir)
    resolved = api.resolve_effective_config(config_dir=config_dir)
    sync = api.trigger_sync(SyncRequest(config_dir=config_dir, output_root=output_root))
    queue = api.get_queue()

    assert profiles['ok'] is True
    assert subscriptions['ok'] is True
    assert validation['data']['validation']['ok'] is True
    assert resolved['data']['resolved']['effective_configs']
    assert sync['data']['sync']['total_enqueued'] == 1
    assert queue['data']['counts']['queue_jobs'] == 1
