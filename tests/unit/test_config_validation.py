from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.config.validation import (
    SemanticValidationError,
    ensure_semantic_valid,
    validate_parsed_config_bundle,
)


@pytest.mark.unit
def test_validation_accepts_semantic_valid_bundle() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito5/valid/semantic-ok"))

    report = validate_parsed_config_bundle(bundle)

    assert report.ok is True
    assert report.error_count == 0
    assert report.issues == ()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("fixture_dir", "expected_code", "expected_path"),
    [
        (
            "missing-element-type",
            "ELEMENT_TYPE_INVALID",
            "profiles.yaml.profiles[0].element_type",
        ),
        (
            "extensibility",
            "EXTENSION_KEY_NOT_ALLOWED",
            "profiles.yaml.profiles[0].custom_rule",
        ),
        (
            "media-dependent",
            "SUBSCRIPTION_SHORTS_DURATION_REQUIRED",
            "subscriptions.yaml.subscriptions[0].max_duration_seconds",
        ),
    ],
)
def test_validation_reports_specific_rule_errors(
    fixture_dir: str,
    expected_code: str,
    expected_path: str,
) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito5/invalid") / fixture_dir)

    report = validate_parsed_config_bundle(bundle)

    assert report.ok is False
    assert any(
        issue.code == expected_code and issue.path == expected_path
        for issue in report.issues
    )


@pytest.mark.unit
def test_validation_raises_actionable_error_with_stable_fingerprint() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito5/invalid/mixed-sources"))

    with pytest.raises(SemanticValidationError, match="fingerprint="):
        ensure_semantic_valid(bundle)
