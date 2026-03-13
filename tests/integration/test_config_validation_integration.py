from pathlib import Path

import pytest

from src.config.config_loader import MissingDataError, load_parsed_config_bundle
from src.config.validation import validate_parsed_config_bundle


@pytest.mark.integration
def test_validation_cross_file_references_between_general_profiles_and_subscriptions() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito5/invalid/unknown-profile"))

    report = validate_parsed_config_bundle(bundle)

    codes = {issue.code for issue in report.issues}
    assert "GENERAL_DEFAULT_PROFILE_UNKNOWN" in codes
    assert "SUBSCRIPTION_PROFILE_UNKNOWN" in codes


@pytest.mark.integration
def test_validation_checks_required_files_before_execution_stage() -> None:
    with pytest.raises(MissingDataError, match="ytdl-sub-conf.yaml"):
        load_parsed_config_bundle(Path("tests/fixtures/hito5/invalid/missing-required-file"))
