import json
import os
import subprocess
import sys

import pytest


@pytest.mark.regression
def test_hito0_regression_bootstrap_in_clean_flow(tmp_path) -> None:
    db_path = tmp_path / "state.sqlite"
    env = {**os.environ, "PATH": f"tests/fixtures/bin:{os.environ.get('PATH', '')}"}

    command = [
        sys.executable,
        "-m",
        "src.api.cli",
        "--config",
        "tests/fixtures/clean/minimal.yaml",
        "--state-db",
        str(db_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["runtime"]["workspace"]
    assert payload["runtime"]["log_level"] in {"DEBUG", "INFO", "WARNING", "ERROR"}
    assert payload["dependencies"]["ffprobe"]["available"] is True
