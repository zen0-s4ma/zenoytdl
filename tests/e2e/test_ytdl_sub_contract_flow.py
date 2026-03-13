from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.integration.ytdl_sub.contract import prepare_translation_batch_from_bundle


@pytest.mark.e2e
def test_hito9_e2e_effective_plus_contract_produces_prepared_translation() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito9/valid/full-mapping"))

    prepared = prepare_translation_batch_from_bundle(bundle)
    payload = [item.to_dict() for item in prepared]

    assert payload[0]["preset"] == "tv_show"
    assert payload[0]["invocation"]["binary"] == "ytdl-sub"
    assert payload[0]["is_valid"] is True
