import json
import subprocess
import sys

import pytest


@pytest.mark.e2e
def test_cli_bootstrap_reports_dependencies_with_fake_binaries(tmp_path) -> None:
    db_path = tmp_path / "state.sqlite"
    import os

    env = {**os.environ, "PATH": f"tests/fixtures/bin:{os.environ.get('PATH', '')}"}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.api.cli",
            "--config",
            "tests/fixtures/clean/minimal.yaml",
            "--state-db",
            str(db_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["ok"] is True
    assert payload["sqlite_ready"] is True
    assert payload["runtime"]["log_level"] == "INFO"
    assert payload["runtime"]["workspace"]
    assert payload["dependencies"]["ytdl-sub"]["available"] is True
    assert payload["dependencies"]["ffmpeg"]["available"] is True
