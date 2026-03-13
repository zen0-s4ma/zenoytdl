from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.config.validation import SemanticValidationError, ensure_semantic_valid


@pytest.mark.e2e
def test_e2e_invalid_configuration_is_blocked_before_execution_or_compilation() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito5/invalid/unknown-profile"))

    with pytest.raises(SemanticValidationError, match="Validación semántica fallida"):
        ensure_semantic_valid(bundle)


@pytest.mark.e2e
def test_e2e_valid_configuration_passes_semantic_gate() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito5/valid/semantic-ok"))

    report = ensure_semantic_valid(bundle)

    assert report.ok is True
