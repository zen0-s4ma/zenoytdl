from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.config.effective_resolution import resolve_effective_configs
from src.integration.ytdl_sub.contract import parse_integration_contract
from src.integration.ytdl_sub.translator import translate_effective_config_to_ytdl_sub_model


@pytest.mark.unit
def test_hito10_translator_resolves_base_and_bridge_and_excludes_internal_only() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito10/valid/base-bridge"))
    effective = resolve_effective_configs(bundle)[0]
    contract = parse_integration_contract(bundle.raw_documents["ytdl-sub-conf.yaml"])

    translated = translate_effective_config_to_ytdl_sub_model(contract, effective)

    assert translated.is_valid is True
    assert translated.preset_base == "tv_show"
    assert translated.preset_bridge == "tv_show"
    assert translated.ytdl_sub_model["subscription"]["options"]["quality"] == "bv*+ba/b"
    assert "schedule_mode" not in translated.ytdl_sub_model["subscription"]["options"]
    assert translated.ytdl_sub_model["meta"]["internal_only_excluded"] == ["schedule_mode"]


@pytest.mark.unit
def test_hito10_translator_applies_preset_fallback_when_profile_mapping_is_missing() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito10/valid/fallback-preset"))
    effective = resolve_effective_configs(bundle)[0]
    contract = parse_integration_contract(bundle.raw_documents["ytdl-sub-conf.yaml"])

    translated = translate_effective_config_to_ytdl_sub_model(contract, effective)

    assert translated.is_valid is True
    assert translated.preset_base == "tv_show"


@pytest.mark.unit
def test_hito10_translator_rejects_ambiguous_preset_mapping() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito10/invalid/ambiguous-preset"))
    effective = resolve_effective_configs(bundle)[0]
    contract = parse_integration_contract(bundle.raw_documents["ytdl-sub-conf.yaml"])

    translated = translate_effective_config_to_ytdl_sub_model(contract, effective)

    assert translated.is_valid is False
    assert translated.ytdl_sub_model == {}
    assert any(issue.reason_code == "PRESET_AMBIGUOUS" for issue in translated.issues)


@pytest.mark.unit
def test_hito10_translator_rejects_partial_prepared_translation() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito10/invalid/partial-translation"))
    effective = resolve_effective_configs(bundle)[0]
    contract = parse_integration_contract(bundle.raw_documents["ytdl-sub-conf.yaml"])

    translated = translate_effective_config_to_ytdl_sub_model(contract, effective)

    assert translated.is_valid is False
    assert translated.ytdl_sub_model == {}
    assert any(
        issue.reason_code == "TRANSLATION_PARTIAL_OR_REJECTED"
        for issue in translated.issues
    )
