from pathlib import Path

import pytest

from src.config.yaml_contract import ContractValidationError, load_contract_bundle


@pytest.mark.integration
def test_contract_validates_cross_file_consistency_for_valid_bundle() -> None:
    bundle = load_contract_bundle(Path("tests/fixtures/contract/valid/with-optionals"))

    assert "cache.yaml" in bundle.optional_files
    assert "queues.yaml" in bundle.optional_files
    assert "logging.yaml" in bundle.optional_files
    assert bundle.general["default_profile"] == "audio-archive"


@pytest.mark.integration
@pytest.mark.parametrize(
    "fixture_dir, expected_error",
    [
        ("missing-default-profile", "default_profile"),
        ("unknown-profile-reference", "subscriptions.yaml.profile"),
        ("missing-profile-mapping", "quality_profile"),
    ],
)
def test_contract_rejects_inconsistent_bundles(fixture_dir: str, expected_error: str) -> None:
    with pytest.raises(ContractValidationError, match=expected_error):
        load_contract_bundle(Path("tests/fixtures/contract/invalid") / fixture_dir)
