from pathlib import Path

import pytest

from src.config import ensure_semantic_valid, load_parsed_config_bundle
from src.config.effective_resolution import resolve_effective_config_for_subscription


@pytest.mark.integration
def test_integration_inheritance_override_and_validation_traceability() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito7/valid/controlled"))
    report = ensure_semantic_valid(bundle)

    resolved = resolve_effective_config_for_subscription(bundle, "strict-ok")

    assert report.ok is True
    assert resolved.resolved_options["quality_profile"] == "balanced"
    assert resolved.value_origins["quality_profile"].endswith(":overrides")
    assert resolved.resolved_options["media_type"] == "video"
    assert any(
        item.field == "media_type" and item.accepted is False
        for item in resolved.override_decisions
    )
