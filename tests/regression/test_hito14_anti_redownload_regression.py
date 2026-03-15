from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.persisted_executor import execute_batch_with_operational_state
from src.persistence.sqlite_state import SQLiteOperationalState
from tests.helpers.fake_ytdl_sub import make_path_with_fake_binary, write_fake_ytdl_sub


@pytest.mark.regression
def test_hito14_regression_canonical_duplicate_never_reprocessed_as_new(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    compiled = compile_bundle_to_artifacts(bundle, tmp_path / "compiled")

    fake_bin = tmp_path / "bin"
    counter_file = tmp_path / "invocations.log"
    write_fake_ytdl_sub(
        fake_bin,
        (
            'import os\n'
            'counter = os.environ["INVOCATION_COUNTER"]\n'
            'with open(counter, "a", encoding="utf-8") as fh:\n'
            '    fh.write("1\\n")\n'
            'raise SystemExit(0)\n'
        ),
    )

    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    sub = bundle.subscriptions[0]
    env = {
        "PATH": make_path_with_fake_binary(fake_bin),
        "INVOCATION_COUNTER": str(counter_file),
    }

    first, _ = execute_batch_with_operational_state(
        compiled,
        state=state,
        config_signature=bundle.signature,
        subscription_sources={sub.name: ("channel", sub.sources[0])},
        env_overrides=env,
        timeout_seconds=5,
    )
    second, _ = execute_batch_with_operational_state(
        compiled,
        state=state,
        config_signature=bundle.signature,
        subscription_sources={sub.name: ("channel", sub.sources[0])},
        env_overrides=env,
        timeout_seconds=5,
    )

    snapshot = state.get_subscription_state(sub.name)

    assert first[0].status == "success"
    assert second[0].status == "discarded"
    assert counter_file.read_text(encoding="utf-8").count("1") == 1
    assert snapshot["known_items"][0]["last_status"] == "discarded"
    assert snapshot["events"][-1]["detail"]["discard_reason"] == "duplicate_already_processed"
