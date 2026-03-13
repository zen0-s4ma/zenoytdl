from pathlib import Path

import pytest

from src.config.config_loader import MissingDataError, load_parsed_config_bundle


@pytest.mark.e2e
@pytest.mark.parametrize(
    "fixture_dir, expected_profiles, expected_subscriptions",
    [
        ("minimal", 1, 1),
        ("medium", 2, 2),
        ("complex", 3, 3),
    ],
)
def test_e2e_config_folder_to_typed_model_flow(
    fixture_dir: str,
    expected_profiles: int,
    expected_subscriptions: int,
) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito4/valid") / fixture_dir)

    assert len(bundle.profiles) == expected_profiles
    assert len(bundle.subscriptions) == expected_subscriptions
    assert bundle.signature
    assert len(bundle.signature) == 64


@pytest.mark.e2e
def test_e2e_invalid_incomplete_bundle_fails_with_clear_error() -> None:
    with pytest.raises(MissingDataError, match="sources"):
        load_parsed_config_bundle(Path("tests/fixtures/hito4/invalid/missing-required"))
