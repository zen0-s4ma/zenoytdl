from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from src.api import CoreAPI, SyncRequest
from src.persistence import SQLiteOperationalState


@pytest.mark.e2e
def test_hito20_e2e_controlled_end_to_end_flow_stays_deterministic(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    api = CoreAPI(state=state)

    config_dir = "tests/fixtures/hito11/valid/single"
    output_root = str(tmp_path / "compiled")

    validation = api.validate_config(config_dir=config_dir)
    sync = api.trigger_sync(
        SyncRequest(config_dir=config_dir, output_root=output_root, priority=99)
    )
    queue = api.get_queue()

    assert validation["ok"] is True
    assert sync["data"]["sync"]["total_enqueued"] == 1
    assert queue["data"]["counts"]["queue_jobs"] == 1


@pytest.mark.e2e
def test_hito20_e2e_real_ytdl_sub_binary_check_when_available() -> None:
    binary = shutil.which("ytdl-sub")
    if binary is None:
        pytest.skip("ytdl-sub no disponible en PATH del entorno de prueba")

    completed = subprocess.run(
        [binary, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.strip() or completed.stderr.strip()
