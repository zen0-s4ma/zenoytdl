from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.translator import translate_bundle_to_ytdl_sub_model


@pytest.mark.e2e
def test_hito10_e2e_yaml_to_effective_to_translated_ytdl_sub_model() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito10/valid/base-bridge"))

    translated = translate_bundle_to_ytdl_sub_model(bundle)
    payload = [item.to_dict() for item in translated]

    assert payload[0]["is_valid"] is True
    assert payload[0]["ytdl_sub_model"]["subscription"]["preset_bridge"] == "tv_show"
    assert payload[0]["prepared_translation"]["is_valid"] is True
