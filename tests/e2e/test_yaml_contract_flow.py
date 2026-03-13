from pathlib import Path

import pytest

from src.config.yaml_contract import ContractValidationError, load_contract_bundle


@pytest.mark.e2e
def test_e2e_contract_flow_accepts_only_complete_valid_bundle() -> None:
    valid_path = Path("tests/fixtures/contract/valid/minimal")
    invalid_path = Path("tests/fixtures/contract/invalid/missing-required-file")

    bundle = load_contract_bundle(valid_path)
    assert bundle.general["workspace"] == "/data/zenoytdl"

    with pytest.raises(ContractValidationError):
        load_contract_bundle(invalid_path)
