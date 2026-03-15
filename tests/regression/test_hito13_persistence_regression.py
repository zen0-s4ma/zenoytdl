import sqlite3
from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.persisted_executor import execute_batch_with_operational_state
from src.persistence.sqlite_state import SQLiteOperationalState
from tests.helpers.fake_ytdl_sub import make_path_with_fake_binary, write_fake_ytdl_sub


@pytest.mark.regression
def test_hito13_regression_sqlite_operational_state_matches_expected_reference(
    tmp_path: Path,
) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/multi"))
    compiled = compile_bundle_to_artifacts(bundle, tmp_path / "compiled")

    fake_bin = tmp_path / "bin"
    write_fake_ytdl_sub(
        fake_bin,
        (
            'import sys\n'
            'args = " ".join(sys.argv[1:])\n'
            'if "science_channel" in args:\n'
            '    print("science-fail", file=sys.stderr)\n'
            '    raise SystemExit(31)\n'
            'print("tech-ok:" + args)\n'
            'raise SystemExit(0)\n'
        ),
    )

    state_db = tmp_path / "state.sqlite"
    state = SQLiteOperationalState(state_db)
    subscription_sources = {
        item.name: ("channel", item.sources[0]) for item in bundle.subscriptions
    }

    execute_batch_with_operational_state(
        compiled,
        state=state,
        config_signature=bundle.signature,
        subscription_sources=subscription_sources,
        env_overrides={"PATH": make_path_with_fake_binary(fake_bin)},
        timeout_seconds=5,
    )

    with sqlite3.connect(state_db) as conn:
        sub_rows = conn.execute(
            "SELECT subscription_id, profile_id, config_signature "
            "FROM subscriptions ORDER BY subscription_id"
        ).fetchall()
        run_rows = conn.execute(
            "SELECT subscription_id, status, error_type, exit_code "
            "FROM execution_runs ORDER BY subscription_id"
        ).fetchall()
        item_rows = conn.execute(
            "SELECT subscription_id, last_status FROM known_items ORDER BY subscription_id"
        ).fetchall()
        metric_count = conn.execute("SELECT COUNT(*) FROM run_metrics").fetchone()[0]
        event_count = conn.execute("SELECT COUNT(*) FROM run_events").fetchone()[0]

    expected_profiles = {item.name: item.profile for item in bundle.subscriptions}
    assert sub_rows == [
        ("science_channel", expected_profiles["science_channel"], bundle.signature),
        ("tech_channel", expected_profiles["tech_channel"], bundle.signature),
    ]
    assert run_rows == [
        ("science_channel", "failed", "non_zero_exit", 31),
        ("tech_channel", "success", "none", 0),
    ]
    assert item_rows == [
        ("science_channel", "failed"),
        ("tech_channel", "success"),
    ]
    assert metric_count == 6
    assert event_count == 4
