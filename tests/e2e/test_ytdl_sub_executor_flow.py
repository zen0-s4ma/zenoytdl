from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.executor import ExecutionErrorType, execute_compiled_artifact
from tests.helpers.fake_ytdl_sub import make_path_with_fake_binary, write_fake_ytdl_sub


@pytest.mark.e2e
def test_hito12_e2e_valid_config_to_controlled_execution_result(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    compiled = compile_bundle_to_artifacts(bundle, tmp_path / "compiled")

    fake_bin = tmp_path / "bin"
    write_fake_ytdl_sub(
        fake_bin,
        (
            'import sys\n'
            'print("ok:" + " ".join(sys.argv[1:]))\n'
            'print("trace:stderr", file=sys.stderr)\n'
            'raise SystemExit(0)\n'
        ),
    )

    result = execute_compiled_artifact(
        compiled.artifacts[0],
        work_unit_id="job-h12-e2e-success",
        global_args=("--simulate",),
        env_overrides={"PATH": make_path_with_fake_binary(fake_bin)},
        timeout_seconds=5,
    )

    assert result.ok is True
    assert result.job.job_id == "job-h12-e2e-success"
    assert result.error_type == ExecutionErrorType.NONE
    assert "ok:" in result.stdout
    assert "trace:stderr" in result.stderr


@pytest.mark.e2e
def test_hito12_e2e_controlled_failed_execution_classifies_non_zero_exit(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    compiled = compile_bundle_to_artifacts(bundle, tmp_path / "compiled")

    fake_bin = tmp_path / "bin"
    write_fake_ytdl_sub(
        fake_bin,
        (
            'import sys\n'
            'print("boom", file=sys.stderr)\n'
            'raise SystemExit(17)\n'
        ),
    )

    result = execute_compiled_artifact(
        compiled.artifacts[0],
        work_unit_id="job-h12-e2e-fail",
        env_overrides={"PATH": make_path_with_fake_binary(fake_bin)},
        timeout_seconds=5,
    )

    assert result.ok is False
    assert result.exit_code == 17
    assert result.error_type == ExecutionErrorType.NON_ZERO_EXIT
    assert "boom" in result.stderr
