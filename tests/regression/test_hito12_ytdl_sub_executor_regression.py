from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.executor import execute_compiled_batch
from tests.helpers.fake_ytdl_sub import make_path_with_fake_binary, write_fake_ytdl_sub


@pytest.mark.regression
def test_hito12_executor_regression_stable_classification_and_traces(tmp_path: Path) -> None:
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
            '    raise SystemExit(23)\n'
            'print("tech-ok:" + args)\n'
            'raise SystemExit(0)\n'
        ),
    )

    results = execute_compiled_batch(
        compiled,
        env_overrides={"PATH": make_path_with_fake_binary(fake_bin)},
        timeout_seconds=5,
    )

    by_sub = {item.job.subscription_id: item for item in results}

    assert by_sub["tech_channel"].ok is True
    assert by_sub["science_channel"].ok is False
    assert by_sub["science_channel"].error_type.value == "non_zero_exit"
    assert "science-fail" in by_sub["science_channel"].stderr
