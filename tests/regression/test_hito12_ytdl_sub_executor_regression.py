import os
from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.executor import execute_compiled_batch


@pytest.mark.regression
def test_hito12_executor_regression_stable_classification_and_traces(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/multi"))
    compiled = compile_bundle_to_artifacts(bundle, tmp_path / "compiled")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake = fake_bin / "ytdl-sub"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$*\" == *science_channel* ]]; then\n"
        "  echo \"science-fail\" 1>&2\n"
        "  exit 23\n"
        "fi\n"
        "echo \"tech-ok:$*\"\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)

    results = execute_compiled_batch(
        compiled,
        env_overrides={"PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"},
        timeout_seconds=5,
    )

    by_sub = {item.job.subscription_id: item for item in results}

    assert by_sub["tech_channel"].ok is True
    assert by_sub["science_channel"].ok is False
    assert by_sub["science_channel"].error_type.value == "non_zero_exit"
    assert "science-fail" in by_sub["science_channel"].stderr
