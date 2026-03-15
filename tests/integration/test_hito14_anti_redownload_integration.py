from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.persisted_executor import execute_batch_with_operational_state
from src.persistence.sqlite_state import SQLiteOperationalState
from tests.helpers.fake_ytdl_sub import make_path_with_fake_binary, write_fake_ytdl_sub


@pytest.mark.integration
def test_hito14_integration_second_execution_is_discarded_from_persisted_state(
    tmp_path: Path,
) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    compiled = compile_bundle_to_artifacts(bundle, tmp_path / "compiled")

    fake_bin = tmp_path / "bin"
    call_counter = tmp_path / "calls.txt"
    write_fake_ytdl_sub(
        fake_bin,
        (
            'import os\n'
            'import sys\n'
            'counter = os.environ["CALL_COUNTER"]\n'
            'with open(counter, "a", encoding="utf-8") as fh:\n'
            '    fh.write("call\\n")\n'
            'print("downloaded")\n'
            'raise SystemExit(0)\n'
        ),
    )

    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    sub = bundle.subscriptions[0]
    env = {
        "PATH": make_path_with_fake_binary(fake_bin),
        "CALL_COUNTER": str(call_counter),
    }

    first_results, _ = execute_batch_with_operational_state(
        compiled,
        state=state,
        config_signature=bundle.signature,
        subscription_sources={sub.name: ("channel", sub.sources[0])},
        env_overrides=env,
        timeout_seconds=5,
    )
    second_results, _ = execute_batch_with_operational_state(
        compiled,
        state=state,
        config_signature=bundle.signature,
        subscription_sources={sub.name: ("channel", sub.sources[0])},
        env_overrides=env,
        timeout_seconds=5,
    )

    snapshot = state.get_subscription_state(sub.name)

    assert first_results[0].status == "success"
    assert second_results[0].status == "discarded"
    assert call_counter.read_text(encoding="utf-8").count("call") == 1
    assert [run["status"] for run in snapshot["runs"]] == ["success", "discarded"]
    assert snapshot["events"][-1]["event_kind"] == "discard"
    assert snapshot["events"][-1]["detail"]["discard_reason"] == "duplicate_already_processed"
