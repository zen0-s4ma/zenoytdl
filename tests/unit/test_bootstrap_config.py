import pytest

from src.config.bootstrap import ConfigBootstrapError, ensure_minimal_config


@pytest.mark.unit
def test_ensure_minimal_config_accepts_valid_yaml_fixture() -> None:
    path = ensure_minimal_config("tests/fixtures/clean/minimal.yaml")
    assert path.exists()


@pytest.mark.unit
def test_ensure_minimal_config_rejects_missing_file() -> None:
    with pytest.raises(ConfigBootstrapError):
        ensure_minimal_config("tests/fixtures/clean/nope.yaml")
