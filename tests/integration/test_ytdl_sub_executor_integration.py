import os
from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.executor import ExecutionErrorType, execute_compiled_batch


def _write_fake_ytdl_sub(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env bash\n"
        "echo \"stdout:$*\"\n"
        "echo \"stderr:ok\" 1>&2\n"
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


@pytest.mark.integration
def test_hito12_integration_compiler_plus_executor_consumes_compiled_artifacts(
    tmp_path: Path,
) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/multi"))
    compiled = compile_bundle_to_artifacts(bundle, tmp_path / "compiled")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_fake_ytdl_sub(fake_bin / "ytdl-sub")

    results = execute_compiled_batch(
        compiled,
        global_args=("--dry-run",),
        env_overrides={"PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"},
        timeout_seconds=5,
    )

    assert len(results) == 2
    assert all(result.error_type == ExecutionErrorType.NONE for result in results)
    assert all("--artifact" in result.stdout for result in results)
