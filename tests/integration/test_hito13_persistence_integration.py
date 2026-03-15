from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.persisted_executor import execute_batch_with_operational_state
from src.persistence.sqlite_state import SQLiteOperationalState
from tests.helpers.fake_ytdl_sub import make_path_with_fake_binary, write_fake_ytdl_sub


@pytest.mark.integration
def test_hito13_integration_executor_plus_sqlite_persistence_keeps_consistent_state(
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
            '    raise SystemExit(29)\n'
            'print("ok:" + args)\n'
            'raise SystemExit(0)\n'
        ),
    )

    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    subscription_sources = {
        item.name: ("channel", item.sources[0])
        for item in bundle.subscriptions
    }

    results, persisted = execute_batch_with_operational_state(
        compiled,
        state=state,
        config_signature=bundle.signature,
        subscription_sources=subscription_sources,
        env_overrides={"PATH": make_path_with_fake_binary(fake_bin)},
        timeout_seconds=5,
    )

    assert len(results) == 2
    assert len(persisted) == 2

    tech_state = state.get_subscription_state("tech_channel")
    science_state = state.get_subscription_state("science_channel")

    assert tech_state["runs"][0]["status"] == "success"
    assert tech_state["runs"][0]["config_signature"] == bundle.signature
    assert science_state["runs"][0]["status"] == "failed"
    assert science_state["runs"][0]["error_type"] == "non_zero_exit"
