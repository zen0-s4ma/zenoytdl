from __future__ import annotations

from pathlib import Path

import pytest

from src.api import CoreAPI
from src.api.core_api import CoreAPIError
from src.persistence import SQLiteOperationalState


@pytest.mark.integration
def test_hito21_integration_core_api_handles_invalid_subscription_name_with_stable_error(
    tmp_path: Path,
) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    api = CoreAPI(state=state)

    with pytest.raises(CoreAPIError) as exc_info:
        api.get_subscription(config_dir="tests/fixtures/hito11/valid/single", subscription_name=" ")

    exc = exc_info.value
    assert getattr(exc, "code", None) == "API_INVALID_PAYLOAD"
    assert "subscription_name no puede ser vacío" in str(exc)
