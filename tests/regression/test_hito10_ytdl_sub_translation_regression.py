import json
from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.translator import translate_bundle_to_ytdl_sub_model


@pytest.mark.regression
def test_hito10_translation_regression_snapshot_stable() -> None:
    fixture = Path("tests/fixtures/hito10/valid/base-bridge")
    snapshot = Path("tests/fixtures/hito10/snapshots/translated-model.json")

    bundle = load_parsed_config_bundle(fixture)
    translated = [item.to_dict() for item in translate_bundle_to_ytdl_sub_model(bundle)]

    expected = json.loads(snapshot.read_text(encoding="utf-8"))
    assert translated == expected
