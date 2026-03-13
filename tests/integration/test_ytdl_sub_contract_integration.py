from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.contract import prepare_translation_batch_from_bundle


@pytest.mark.integration
def test_hito9_integration_prepares_translation_from_effective_config_and_contract() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito9/valid/full-mapping"))

    prepared = prepare_translation_batch_from_bundle(bundle)

    assert len(prepared) == 1
    assert prepared[0].is_valid is True
    assert prepared[0].mapped_fields["url"] == "techchannel_source"


@pytest.mark.integration
def test_hito9_integration_detects_missing_preset_mapping() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito9/invalid/missing-preset"))

    prepared = prepare_translation_batch_from_bundle(bundle)

    assert prepared[0].is_valid is False
    assert any(issue.reason_code == "PRESET_MAPPING_MISSING" for issue in prepared[0].issues)
