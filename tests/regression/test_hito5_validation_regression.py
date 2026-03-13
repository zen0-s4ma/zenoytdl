from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.config.validation import validate_parsed_config_bundle


@pytest.mark.regression
def test_hito5_regression_invalid_corpus_still_fails_with_expected_codes() -> None:
    expected = {
        "missing-element-type": {"ELEMENT_TYPE_INVALID"},
        "unknown-profile": {"GENERAL_DEFAULT_PROFILE_UNKNOWN", "SUBSCRIPTION_PROFILE_UNKNOWN"},
        "media-dependent": {"SUBSCRIPTION_SHORTS_DURATION_REQUIRED"},
        "extensibility": {"EXTENSION_KEY_NOT_ALLOWED"},
        "mixed-sources": {"SUBSCRIPTION_SOURCE_KIND_MIXED"},
    }

    for fixture_name, expected_codes in expected.items():
        bundle = load_parsed_config_bundle(Path("tests/fixtures/hito5/invalid") / fixture_name)
        report = validate_parsed_config_bundle(bundle)
        codes = {issue.code for issue in report.issues}
        assert expected_codes.issubset(codes)


@pytest.mark.regression
def test_hito5_regression_report_serialization_is_stable() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito5/invalid/extensibility"))

    report = validate_parsed_config_bundle(bundle)
    payload = report.to_dict()

    assert payload["ok"] is False
    assert payload["error_count"] == len(payload["issues"])
    assert len(payload["issue_fingerprint"]) == 64
