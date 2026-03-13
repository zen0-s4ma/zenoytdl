from pathlib import Path

import pytest

from src.config.runtime_env import load_runtime_env, resolve_log_level, resolve_workspace


@pytest.mark.unit
def test_resolve_workspace_prefers_explicit_value(tmp_path) -> None:
    workspace = resolve_workspace(str(tmp_path), env={})
    assert workspace == tmp_path


@pytest.mark.unit
def test_resolve_workspace_uses_env_when_explicit_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(Path.cwd())
    workspace = resolve_workspace(None, env={"ZENOYTDL_WORKSPACE": "relative/work"})
    assert workspace.is_absolute()
    assert str(workspace).endswith("relative/work")


@pytest.mark.unit
def test_resolve_log_level_falls_back_to_info_for_unknown_value() -> None:
    assert resolve_log_level(None, env={"ZENOYTDL_LOG_LEVEL": "trace"}) == "INFO"


@pytest.mark.unit
def test_load_runtime_env_returns_minimal_runtime_context() -> None:
    runtime = load_runtime_env({"ZENOYTDL_WORKSPACE": "/tmp/zeno", "ZENOYTDL_LOG_LEVEL": "warning"})
    assert runtime["workspace"] == "/tmp/zeno"
    assert runtime["log_level"] == "WARNING"
