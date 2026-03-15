from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest


@pytest.mark.e2e
def test_hito21_e2e_cli_returns_structured_error_payload_for_invalid_config() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.api.cli",
            "--config",
            "tests/fixtures/clean/minimal.txt",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "CONFIG_BOOTSTRAP_ERROR"
    assert "Extensión no soportada" in payload["error"]["message"]


@pytest.mark.e2e
def test_hito21_e2e_cli_no_longer_emits_runpy_runtime_warning() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.api.cli",
            "--config",
            "tests/fixtures/clean/minimal.yaml",
        ],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": f"tests/fixtures/bin:{os.environ.get('PATH', '')}"},
    )

    assert completed.returncode == 0
    assert "RuntimeWarning" not in completed.stderr
