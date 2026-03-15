from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.persisted_executor import execute_batch_with_operational_state
from src.persistence.sqlite_state import SQLiteOperationalState
from tests.helpers.fake_ytdl_sub import make_path_with_fake_binary, write_fake_ytdl_sub


@pytest.mark.e2e
def test_hito13_e2e_execution_persists_complete_operational_footprint(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    compiled = compile_bundle_to_artifacts(bundle, tmp_path / "compiled")

    fake_bin = tmp_path / "bin"
    write_fake_ytdl_sub(
        fake_bin,
        (
            'import sys\n'
            'print("downloaded:" + " ".join(sys.argv[1:]))\n'
            'raise SystemExit(0)\n'
        ),
    )

    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    sub = bundle.subscriptions[0]
    results, _ = execute_batch_with_operational_state(
        compiled,
        state=state,
        config_signature=bundle.signature,
        subscription_sources={sub.name: ("channel", sub.sources[0])},
        env_overrides={"PATH": make_path_with_fake_binary(fake_bin)},
        timeout_seconds=5,
    )

    assert results[0].ok is True
    snapshot = state.get_subscription_state(sub.name)

    assert snapshot["subscription"]["subscription_id"] == sub.name
    assert snapshot["runs"][0]["status"] == "success"
    assert (
        snapshot["runs"][0]["compilation_signature"]
        == compiled.artifacts[0].compilation_signature
    )
    assert snapshot["known_items"][0]["last_status"] == "success"
