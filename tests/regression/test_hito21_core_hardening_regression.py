from __future__ import annotations

from pathlib import Path

import pytest

from src.core import CoreCacheSystem, QueueRuntime, QueueRuntimeConfig
from src.persistence import SQLiteOperationalState


@pytest.mark.regression
def test_hito21_regression_rejects_non_positive_queue_runtime_limits(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()

    with pytest.raises(ValueError):
        QueueRuntime(
            state=state,
            cache=CoreCacheSystem(),
            config=QueueRuntimeConfig(max_workers=0, max_concurrent_by_subscription=1),
        )


@pytest.mark.regression
def test_hito21_regression_keeps_operacion_comandos_documented() -> None:
    content = Path("docs/operacion-comandos.md").read_text(encoding="utf-8")
    assert "Verificación específica Hito 21" in content
    assert "test_hito21_core_hardening" in content
