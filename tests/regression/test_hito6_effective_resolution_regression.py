import json
from pathlib import Path

import pytest

from src.config import load_parsed_config_bundle
from src.config.effective_resolution import resolve_effective_configs, serialize_effective_configs


@pytest.mark.regression
def test_hito6_regression_effective_configs_match_canonical_snapshot() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito6/complex"))

    payload = serialize_effective_configs(resolve_effective_configs(bundle))
    snapshot_path = Path("tests/fixtures/hito6/snapshots/complex-effective.json")
    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert payload == expected


@pytest.mark.regression
def test_hito6_regression_equivalent_configs_keep_same_signature() -> None:
    bundle_a = load_parsed_config_bundle(Path("tests/fixtures/hito6/equivalent-a"))
    bundle_b = load_parsed_config_bundle(Path("tests/fixtures/hito6/equivalent-b"))

    payload_a = serialize_effective_configs(resolve_effective_configs(bundle_a))
    payload_b = serialize_effective_configs(resolve_effective_configs(bundle_b))

    assert payload_a == payload_b
