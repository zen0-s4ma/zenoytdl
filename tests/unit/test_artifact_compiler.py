import json
from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.compiler import (
    ArtifactCompilationError,
    compile_bundle_to_artifacts,
    compile_translated_batch,
)
from src.integration.ytdl_sub.translator import translate_bundle_to_ytdl_sub_model


@pytest.mark.unit
def test_hito11_compiler_generates_yaml_and_metadata_with_stable_layout(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    translated = translate_bundle_to_ytdl_sub_model(bundle)

    compiled = compile_translated_batch(translated, tmp_path)

    assert len(compiled.artifacts) == 1
    artifact = compiled.artifacts[0]
    assert artifact.layout_name.startswith("tech_channel--")
    assert artifact.artifact_yaml_path.exists()
    assert artifact.metadata_json_path.exists()

    metadata = json.loads(artifact.metadata_json_path.read_text(encoding="utf-8"))
    assert metadata["subscription_id"] == "tech_channel"
    assert metadata["translation_signature"] == artifact.translation_signature
    assert metadata["effective_signature"] == artifact.effective_signature


@pytest.mark.unit
def test_hito11_compiler_recompile_without_changes_reuses_artifacts(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    translated = translate_bundle_to_ytdl_sub_model(bundle)

    first = compile_translated_batch(translated, tmp_path)
    second = compile_translated_batch(translated, tmp_path)

    assert first.artifacts[0].layout_name == second.artifacts[0].layout_name
    assert second.artifacts[0].reused_previous is True
    assert first.artifacts[0].compilation_signature == second.artifacts[0].compilation_signature


@pytest.mark.unit
def test_hito11_compiler_clean_stale_previous_outputs(tmp_path: Path) -> None:
    stale = tmp_path / "obsolete--deadbeef"
    stale.mkdir(parents=True)
    (stale / "artifact.yaml").write_text("dummy: true\n", encoding="utf-8")

    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    translated = translate_bundle_to_ytdl_sub_model(bundle)

    compiled = compile_translated_batch(translated, tmp_path, clean_stale=True)

    assert stale in compiled.cleaned_paths
    assert stale.exists() is False


@pytest.mark.unit
def test_hito11_compiler_rejects_non_invocable_translation(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito10/invalid/ambiguous-preset"))
    translated = translate_bundle_to_ytdl_sub_model(bundle)

    with pytest.raises(ArtifactCompilationError, match="traducción inválida"):
        compile_translated_batch(translated, tmp_path)


@pytest.mark.unit
def test_hito11_compiler_supports_batch_per_subscription(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/multi"))

    compiled = compile_bundle_to_artifacts(bundle, tmp_path)

    assert [item.subscription_id for item in compiled.artifacts] == [
        "science_channel",
        "tech_channel",
    ]
    assert compiled.index_path.exists()
