from pathlib import Path

import pytest

from src.config.yaml_contract import ContractValidationError, load_contract_bundle


@pytest.mark.regression
@pytest.mark.parametrize(
    "fixture_dir",
    [
        "tests/fixtures/contract/valid/minimal",
        "tests/fixtures/contract/valid/with-optionals",
    ],
)
def test_hito3_regression_valid_bundles_remain_accepted(fixture_dir: str) -> None:
    bundle = load_contract_bundle(Path(fixture_dir))
    assert bundle.general
    assert bundle.profiles
    assert bundle.subscriptions
    assert bundle.ytdl_sub_conf


@pytest.mark.regression
@pytest.mark.parametrize(
    "fixture_dir",
    [
        "tests/fixtures/contract/invalid/missing-required-file",
        "tests/fixtures/contract/invalid/missing-default-profile",
        "tests/fixtures/contract/invalid/missing-conditional-every-hours",
        "tests/fixtures/contract/invalid/missing-profile-mapping",
        "tests/fixtures/contract/invalid/unknown-profile-reference",
    ],
)
def test_hito3_regression_invalid_bundles_remain_rejected(fixture_dir: str) -> None:
    with pytest.raises(ContractValidationError):
        load_contract_bundle(Path(fixture_dir))
