from pathlib import Path

import pytest

from src.api import CoreAPI, SyncRequest
from src.persistence import SQLiteOperationalState


@pytest.mark.regression
def test_hito20_regression_integral_suite_guards_cross_module_contracts(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    api = CoreAPI(state=state)

    config_dir = "tests/fixtures/hito11/valid/single"
    output_root = str(tmp_path / "compiled")

    assert api.list_profiles(config_dir=config_dir)["data"]["count"] >= 1
    assert api.list_subscriptions(config_dir=config_dir)["data"]["count"] >= 1
    assert api.validate_config(config_dir=config_dir)["data"]["validation"]["ok"] is True
    resolved = api.resolve_effective_config(config_dir=config_dir)
    assert resolved["data"]["resolved"]["effective_configs"]

    sync = api.trigger_sync(SyncRequest(config_dir=config_dir, output_root=output_root))
    assert sync["data"]["sync"]["total_enqueued"] == 1

    queue = api.get_queue()
    assert queue["data"]["counts"]["queue_jobs"] == 1

    history = api.get_history(config_dir=config_dir)
    assert history["data"]["count"] >= 1
