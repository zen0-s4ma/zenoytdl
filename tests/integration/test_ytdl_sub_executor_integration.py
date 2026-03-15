from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.executor import ExecutionErrorType, execute_compiled_batch
from tests.helpers.fake_ytdl_sub import make_path_with_fake_binary, write_fake_ytdl_sub


def _success_script() -> str:
    return (
        'import sys\n'
        'print("stdout:" + " ".join(sys.argv[1:]))\n'
        'print("stderr:ok", file=sys.stderr)\n'
        'raise SystemExit(0)\n'
    )


@pytest.mark.integration
def test_hito12_integration_compiler_plus_executor_consumes_compiled_artifacts(
    tmp_path: Path,
) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/multi"))
    compiled = compile_bundle_to_artifacts(bundle, tmp_path / "compiled")

    fake_bin = tmp_path / "bin"
    write_fake_ytdl_sub(fake_bin, _success_script())

    results = execute_compiled_batch(
        compiled,
        global_args=("--dry-run",),
        env_overrides={"PATH": make_path_with_fake_binary(fake_bin)},
        timeout_seconds=5,
    )

    assert len(results) == 2
    assert all(result.error_type == ExecutionErrorType.NONE for result in results)
    assert all("--artifact" in result.stdout for result in results)
