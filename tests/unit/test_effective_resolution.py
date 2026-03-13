from pathlib import Path

import pytest

from src.config import load_parsed_config_bundle
from src.config.effective_resolution import (
    EffectiveResolutionError,
    resolve_effective_config_for_subscription,
    resolve_effective_configs,
)


@pytest.mark.unit
def test_merge_precedence_general_profile_subscription_local() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito6/medium"))

    resolved = resolve_effective_config_for_subscription(bundle, "podcast-es")

    assert resolved.resolved_options["quality_profile"] == "archive"
    assert resolved.resolved_options["media_type"] == "audio"
    assert resolved.resolved_options["log_level"] == "WARNING"
    assert resolved.resolved_options["dry_run"] is True
    assert resolved.resolved_options["audio_language"] == "es"
    assert resolved.value_origins["media_type"].endswith(":local")
    assert resolved.value_origins["audio_language"].endswith(":local")


@pytest.mark.unit
def test_normalization_and_defaults_are_stable() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito6/minimal"))

    resolved = resolve_effective_config_for_subscription(bundle, "alpha")

    assert resolved.resolved_options["timezone"] == "UTC"
    assert resolved.resolved_options["schedule_mode"] == "manual"
    assert resolved.resolved_options["schedule_every_hours"] == 0
    assert resolved.resolved_options["source_count"] == 1


@pytest.mark.unit
def test_effective_signature_is_deterministic_for_equivalent_configs() -> None:
    a = load_parsed_config_bundle(Path("tests/fixtures/hito6/equivalent-a"))
    b = load_parsed_config_bundle(Path("tests/fixtures/hito6/equivalent-b"))

    ra = resolve_effective_config_for_subscription(a, "eq-sub")
    rb = resolve_effective_config_for_subscription(b, "eq-sub")

    assert ra.resolved_options == rb.resolved_options
    assert ra.effective_signature == rb.effective_signature


@pytest.mark.unit
def test_resolution_fails_for_unknown_subscription() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito6/minimal"))

    with pytest.raises(EffectiveResolutionError, match="Suscripción no encontrada"):
        resolve_effective_config_for_subscription(bundle, "missing-sub")


@pytest.mark.unit
def test_batch_resolution_returns_deterministic_order() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito6/complex"))

    effective = resolve_effective_configs(bundle)

    assert [item.subscription_id for item in effective] == ["docs-main", "shorts-fast"]
