from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.config.effective_resolution import resolve_effective_configs
from src.integration.ytdl_sub.contract import (
    IntegrationContractError,
    MissingFieldPolicy,
    parse_integration_contract,
    prepare_translation,
)


@pytest.mark.unit
def test_hito9_contract_parses_all_required_blocks() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito9/valid/full-mapping"))

    contract = parse_integration_contract(bundle.raw_documents["ytdl-sub-conf.yaml"])

    assert contract.integration_version == 1
    assert contract.preset_mapping["profile_tv"] == "tv_show"
    assert contract.field_mapping["quality_profile"] == "quality"
    assert contract.translation_rules["quality_profile"].required is True
    assert contract.compatibility.min_ytdl_sub_version == "2024.10"
    assert contract.fallback_policy.on_missing_field == MissingFieldPolicy.REJECT
    assert contract.validation.abort_on_partial_translation is True
    assert contract.invocation.mode.value == "sub"


@pytest.mark.unit
def test_hito9_contract_rejects_missing_version() -> None:
    with pytest.raises(IntegrationContractError, match="integration_version"):
        parse_integration_contract({"preset_mapping": {}, "field_mapping": {"x": "y"}})


@pytest.mark.unit
def test_hito9_translation_applies_mapping_and_rules() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito9/valid/full-mapping"))
    effective = resolve_effective_configs(bundle)[0]
    contract = parse_integration_contract(bundle.raw_documents["ytdl-sub-conf.yaml"])

    prepared = prepare_translation(contract, effective)

    assert prepared.is_valid is True
    assert prepared.preset == "tv_show"
    assert prepared.mapped_fields["quality"] == "bv*+ba/b"
    assert prepared.mapped_fields["media_type"] == "video"


@pytest.mark.unit
def test_hito9_translation_rejects_partial_when_abort_enabled() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito9/invalid/partial-translation"))
    effective = resolve_effective_configs(bundle)[0]
    contract = parse_integration_contract(bundle.raw_documents["ytdl-sub-conf.yaml"])

    prepared = prepare_translation(contract, effective)

    assert prepared.is_valid is False
    assert prepared.mapped_fields == {}
    assert any(issue.reason_code == "TRANSLATION_RULE_UNMAPPED_VALUE" for issue in prepared.issues)
