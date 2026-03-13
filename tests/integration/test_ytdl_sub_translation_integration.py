from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.translator import translate_bundle_to_ytdl_sub_model


@pytest.mark.integration
def test_hito10_integration_translates_effective_config_to_ytdl_sub_model() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito10/valid/base-bridge"))

    translated = translate_bundle_to_ytdl_sub_model(bundle)

    assert len(translated) == 1
    assert translated[0].is_valid is True
    assert translated[0].ytdl_sub_model["subscription"]["preset"] == "tv_show"


@pytest.mark.integration
def test_hito10_integration_rejects_ambiguous_preset_translation() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito10/invalid/ambiguous-preset"))

    translated = translate_bundle_to_ytdl_sub_model(bundle)

    assert translated[0].is_valid is False
    assert any(issue.reason_code == "PRESET_AMBIGUOUS" for issue in translated[0].issues)
