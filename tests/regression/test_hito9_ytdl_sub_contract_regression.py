import json
from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.contract import prepare_translation_batch_from_bundle


@pytest.mark.regression
def test_hito9_contract_regression_snapshot_stable() -> None:
    fixture = Path("tests/fixtures/hito9/valid/full-mapping")
    snapshot = Path("tests/fixtures/hito9/snapshots/prepared-translation.json")

    bundle = load_parsed_config_bundle(fixture)
    prepared = [item.to_dict() for item in prepare_translation_batch_from_bundle(bundle)]

    expected = json.loads(snapshot.read_text(encoding="utf-8"))
    assert prepared == expected
