import json
from pathlib import Path

import pytest

from src.config import load_parsed_config_bundle
from src.config.effective_resolution import resolve_effective_configs, serialize_effective_configs


@pytest.mark.regression
def test_hito8_regression_snapshot_full_flow() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito8/valid/full-flow"))

    payload = serialize_effective_configs(resolve_effective_configs(bundle))
    expected = json.loads(
        Path("tests/fixtures/hito8/snapshots/full-flow-effective.json").read_text(encoding="utf-8")
    )

    assert payload == expected


@pytest.mark.regression
@pytest.mark.parametrize(
    "fixture_dir",
    [
        "tests/fixtures/hito8/valid/pattern-metadata-text",
        "tests/fixtures/hito8/valid/pattern-metadata-images",
        "tests/fixtures/hito8/valid/pattern-embed-metadata",
        "tests/fixtures/hito8/valid/pattern-export-info-json",
        "tests/fixtures/hito8/valid/pattern-max-duration",
    ],
)
def test_hito8_regression_supported_types_have_stable_effective_shape(fixture_dir: str) -> None:
    bundle = load_parsed_config_bundle(Path(fixture_dir))

    payload = serialize_effective_configs(resolve_effective_configs(bundle))

    effective_item = payload["effective_configs"][0]
    assert len(effective_item["postprocessings"]) >= 1
    assert "effective_signature" in effective_item
