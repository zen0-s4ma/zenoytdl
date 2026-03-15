import json
from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import compile_bundle_to_artifacts


@pytest.mark.integration
def test_hito11_integration_translator_plus_compiler_preserves_execution_data(
    tmp_path: Path,
) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))

    compiled = compile_bundle_to_artifacts(bundle, tmp_path)

    artifact_yaml = compiled.artifacts[0].artifact_yaml_path.read_text(encoding="utf-8")
    metadata = json.loads(compiled.artifacts[0].metadata_json_path.read_text(encoding="utf-8"))

    assert 'binary: "ytdl-sub"' in artifact_yaml
    assert 'mode: "sub"' in artifact_yaml
    assert metadata["is_invocable"] is True
    assert metadata["compilation_signature"] == compiled.artifacts[0].compilation_signature


@pytest.mark.integration
def test_hito11_integration_index_contains_all_compiled_units(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/multi"))

    compiled = compile_bundle_to_artifacts(bundle, tmp_path)
    index_payload = json.loads(compiled.index_path.read_text(encoding="utf-8"))

    assert index_payload["layout_version"] == 1
    assert [item["subscription_id"] for item in index_payload["artifacts"]] == [
        "science_channel",
        "tech_channel",
    ]
