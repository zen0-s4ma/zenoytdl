from __future__ import annotations

from pathlib import Path

_ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


def resolve_workspace(explicit_workspace: str | None, env: dict[str, str]) -> Path:
    raw_value = explicit_workspace or env.get("ZENOYTDL_WORKSPACE") or ".tmp/workspace"
    workspace = Path(raw_value).expanduser()
    if not workspace.is_absolute():
        workspace = Path.cwd() / workspace
    return workspace


def resolve_log_level(explicit_level: str | None, env: dict[str, str]) -> str:
    value = (explicit_level or env.get("ZENOYTDL_LOG_LEVEL") or "INFO").upper()
    if value not in _ALLOWED_LOG_LEVELS:
        return "INFO"
    return value


def load_runtime_env(env: dict[str, str]) -> dict[str, str]:
    return {
        "workspace": str(resolve_workspace(None, env)),
        "log_level": resolve_log_level(None, env),
    }
