from pathlib import Path

import pytest

from src.config import load_parsed_config_bundle
from src.config.effective_resolution import resolve_effective_config_for_subscription


@pytest.mark.unit
def test_allowed_policy_accepts_override() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito7/valid/controlled"))

    resolved = resolve_effective_config_for_subscription(bundle, "strict-ok")

    assert resolved.resolved_options["video_container"] == "mkv"
    assert any(
        item.field == "video_container"
        and item.policy == "allowed"
        and item.accepted is True
        and item.reason_code == "OVERRIDE_ACCEPTED"
        for item in resolved.override_decisions
    )


@pytest.mark.unit
def test_restricted_policy_accepts_only_allowed_value() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito7/valid/controlled"))

    resolved = resolve_effective_config_for_subscription(bundle, "strict-ok")

    assert resolved.resolved_options["quality_profile"] == "balanced"
    assert any(
        item.field == "quality_profile" and item.accepted is True and item.policy == "restricted"
        for item in resolved.override_decisions
    )


@pytest.mark.unit
def test_forbidden_policy_rejects_override_with_reason() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito7/valid/controlled"))

    resolved = resolve_effective_config_for_subscription(bundle, "strict-ok")

    assert resolved.resolved_options["media_type"] == "video"
    assert any(
        item.field == "media_type"
        and item.accepted is False
        and item.reason_code == "OVERRIDE_POLICY_FORBIDDEN"
        for item in resolved.override_decisions
    )


@pytest.mark.unit
def test_rejection_messages_include_stable_reason_codes() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito7/valid/controlled"))

    resolved = resolve_effective_config_for_subscription(bundle, "strict-ok")

    assert any(
        item.field == "unknown_toggle"
        and item.reason_code == "OVERRIDE_FIELD_NOT_SUPPORTED"
        and item.accepted is False
        for item in resolved.override_decisions
    )
    assert any(
        item.field == "max_duration_seconds"
        and item.reason_code == "OVERRIDE_RESTRICTED_MIN_VALUE"
        and item.accepted is False
        for item in resolved.override_decisions
    )
