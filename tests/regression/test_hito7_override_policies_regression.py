import json
from pathlib import Path

import pytest

from src.config import load_parsed_config_bundle
from src.config.effective_resolution import resolve_effective_configs, serialize_effective_configs


@pytest.mark.regression
def test_hito7_regression_snapshot_for_override_matrix() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito7/valid/controlled"))

    payload = serialize_effective_configs(resolve_effective_configs(bundle))
    expected = json.loads(
        Path("tests/fixtures/hito7/snapshots/controlled-effective.json").read_text(encoding="utf-8")
    )

    assert payload == expected


@pytest.mark.regression
@pytest.mark.parametrize(
    "fixture_dir",
    [
        "tests/fixtures/hito7/invalid/restricted-denied",
        "tests/fixtures/hito7/invalid/forbidden",
    ],
)
def test_hito7_regression_invalid_matrix_is_stable(fixture_dir: str) -> None:
    bundle = load_parsed_config_bundle(Path(fixture_dir))

    payload = serialize_effective_configs(resolve_effective_configs(bundle))

    decisions = payload["effective_configs"][0]["override_decisions"]
    assert any(item["accepted"] is False for item in decisions)
