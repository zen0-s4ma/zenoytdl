from pathlib import Path

import pytest

from src.config.yaml_contract import ContractValidationError, load_contract_bundle


@pytest.mark.unit
def test_contract_accepts_minimal_bundle_and_applies_defaults() -> None:
    bundle = load_contract_bundle(Path("tests/fixtures/contract/valid/minimal"))

    assert bundle.general["log_level"] == "INFO"
    assert bundle.general["execution"]["dry_run"] is False
    assert bundle.subscriptions["subscriptions"][0]["enabled"] is True
    assert bundle.ytdl_sub_conf["integration"]["provider"] == "ytdl-sub"
    assert bundle.ytdl_sub_conf["integration"]["binary"] == "ytdl-sub"


@pytest.mark.unit
def test_contract_requires_conditional_every_hours_when_interval_schedule() -> None:
    with pytest.raises(ContractValidationError, match="every_hours"):
        load_contract_bundle(Path("tests/fixtures/contract/invalid/missing-conditional-every-hours"))


@pytest.mark.unit
def test_contract_requires_mandatory_yaml_files() -> None:
    with pytest.raises(ContractValidationError, match="Falta archivo obligatorio"):
        load_contract_bundle(Path("tests/fixtures/contract/invalid/missing-required-file"))
