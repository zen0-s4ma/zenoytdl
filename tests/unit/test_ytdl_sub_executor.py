import json
import os
from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts
from src.integration.ytdl_sub.executor import (
    ExecutionErrorType,
    ExecutionPreparationError,
    build_execution_command,
    execute_compiled_artifact,
    prepare_execution_job,
)


@pytest.mark.unit
def test_hito12_executor_builds_command_from_compiled_artifact(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    compiled = compile_bundle_to_artifacts(bundle, tmp_path / "compiled")
    artifact = compiled.artifacts[0]
    job = prepare_execution_job(artifact)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_runner = fake_bin / "ytdl-sub"
    fake_runner.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    fake_runner.chmod(0o755)

    command = build_execution_command(
        job,
        global_args=("--verbose",),
        env_overrides={"PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"},
        timeout_seconds=12.5,
        temporary_root=tmp_path / "tmp-runtime",
    )

    assert command.args[1] == "sub"
    assert command.args[2] == "--artifact"
    assert command.args[3] == str(artifact.artifact_yaml_path)
    assert "--verbose" in command.args
    assert command.timeout_seconds == 12.5
    assert command.temporary_dir.exists()


@pytest.mark.unit
def test_hito12_executor_classifies_invalid_compiled_artifact(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    compiled = compile_bundle_to_artifacts(bundle, tmp_path / "compiled")
    artifact = compiled.artifacts[0]

    artifact.metadata_json_path.write_text("{}", encoding="utf-8")

    result = execute_compiled_artifact(artifact)

    assert result.error_type == ExecutionErrorType.INVALID_COMPILED_ARTIFACT
    assert result.exit_code is None
    assert result.ok is False


@pytest.mark.unit
def test_hito12_executor_rejects_invalid_invocation_block(tmp_path: Path) -> None:
    bad_artifact = tmp_path / "artifact.yaml"
    bad_metadata = tmp_path / "metadata.json"

    bad_artifact.write_text(
        'subscription:\n  invocation:\n    binary: ""\n    mode: "sub"\n',
        encoding="utf-8",
    )
    bad_metadata.write_text(json.dumps({"profile_id": "p1"}), encoding="utf-8")

    from src.integration.ytdl_sub.executor import ExecutionJobUnit

    job = ExecutionJobUnit(
        job_id="job-1",
        subscription_id="sub-1",
        profile_id="p1",
        compilation_signature="a" * 64,
        artifact_dir=tmp_path,
        artifact_yaml_path=bad_artifact,
        metadata_json_path=bad_metadata,
    )

    with pytest.raises(ExecutionPreparationError, match="invocation.binary inválido"):
        build_execution_command(job)
