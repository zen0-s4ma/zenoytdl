import argparse
import json

from src.config.bootstrap import ConfigBootstrapError, ensure_minimal_config
from src.domain.runtime import BootstrapReport
from src.integration.dependencies import detect_binary
from src.persistence.sqlite_health import sqlite_smoke_check


def build_bootstrap_report(config: str, state_db: str) -> BootstrapReport:
    ensure_minimal_config(config)

    return BootstrapReport(
        config_loaded=True,
        sqlite_ready=sqlite_smoke_check(state_db),
        ytdl_sub=detect_binary("ytdl-sub"),
        ffmpeg=detect_binary("ffmpeg"),
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
        },
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
