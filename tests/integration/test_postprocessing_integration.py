from pathlib import Path

import pytest

from src.config import ensure_semantic_valid, load_parsed_config_bundle
from src.config.effective_resolution import resolve_effective_configs


@pytest.mark.integration
def test_profile_subscription_overrides_and_postprocessings_integrate() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito8/valid/full-flow"))
    ensure_semantic_valid(bundle)

    resolved = resolve_effective_configs(bundle)
    by_sub = {item.subscription_id: item for item in resolved}

    assert by_sub["sub-video"].resolved_options["media_type"] == "video"
    assert len(by_sub["sub-video"].postprocessings) == 3
    assert by_sub["sub-shorts"].postprocessings[0].parameters["seconds"] == 90
