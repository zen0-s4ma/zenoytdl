from pathlib import Path

import pytest

from src.config.config_loader import (
    CoercionError,
    MissingDataError,
    ParsedGeneral,
    YAMLSyntaxError,
    load_parsed_config_bundle,
)


@pytest.mark.unit
def test_parser_by_file_and_defaults_for_minimal_bundle() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito4/valid/minimal"))

    assert isinstance(bundle.general, ParsedGeneral)
    assert bundle.general.log_level == "INFO"
    assert bundle.general.dry_run is False
    assert bundle.general.library_dir == bundle.general.workspace / "library"
    assert bundle.subscriptions[0].enabled is True
    assert bundle.subscriptions[0].schedule.mode == "manual"


@pytest.mark.unit
def test_parser_handles_type_coercion_error() -> None:
    with pytest.raises(CoercionError, match="dry_run"):
        load_parsed_config_bundle(Path("tests/fixtures/hito4/invalid/invalid-coercion"))


@pytest.mark.unit
def test_parser_fails_with_yaml_syntax_error() -> None:
    with pytest.raises(YAMLSyntaxError, match="general.yaml"):
        load_parsed_config_bundle(Path("tests/fixtures/hito4/invalid/broken-yaml"))


@pytest.mark.unit
def test_parser_fails_when_required_data_is_missing() -> None:
    with pytest.raises(MissingDataError, match="sources"):
        load_parsed_config_bundle(Path("tests/fixtures/hito4/invalid/missing-required"))
