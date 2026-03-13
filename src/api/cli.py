import argparse
import json
import os

from src.config.bootstrap import ConfigBootstrapError, ensure_minimal_config
from src.config.runtime_env import load_runtime_env
from src.domain.runtime import BootstrapReport
from src.integration.dependencies import detect_binary
from src.persistence.sqlite_health import sqlite_smoke_check


def build_bootstrap_report(config: str, state_db: str) -> BootstrapReport:
    ensure_minimal_config(config)
    runtime_context = load_runtime_env(dict(os.environ))

    return BootstrapReport(
        runtime_workspace=runtime_context["workspace"],
        runtime_log_level=runtime_context["log_level"],
        config_loaded=True,
        sqlite_ready=sqlite_smoke_check(state_db),
        ytdl_sub=detect_binary("ytdl-sub"),
        ffmpeg=detect_binary("ffmpeg"),
        ffprobe=detect_binary("ffprobe"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(prog="zenoytdl")
    parser.add_argument("--config", required=True, help="Ruta de configuración mínima YAML")
    parser.add_argument("--state-db", default=".tmp/state.sqlite", help="Ruta de SQLite de estado")
    args = parser.parse_args()

    try:
        report = build_bootstrap_report(args.config, args.state_db)
    except ConfigBootstrapError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    payload = {
        "ok": report.ok,
        "runtime": {
            "workspace": report.runtime_workspace,
            "log_level": report.runtime_log_level,
        },
        "config_loaded": report.config_loaded,
        "sqlite_ready": report.sqlite_ready,
        "dependencies": {
            "ytdl-sub": {
                "available": report.ytdl_sub.available,
                "detail": report.ytdl_sub.detail,
            },
            "ffmpeg": {
                "available": report.ffmpeg.available,
                "detail": report.ffmpeg.detail,
            },
            "ffprobe": {
                "available": report.ffprobe.available,
                "detail": report.ffprobe.detail,
            },
        },
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
