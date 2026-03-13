from pathlib import Path

import pytest

from src.config import ensure_semantic_valid, load_parsed_config_bundle
from src.config.effective_resolution import resolve_effective_configs


@pytest.mark.e2e
def test_e2e_override_policy_acceptance_and_rejection() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito7/valid/controlled"))
    ensure_semantic_valid(bundle)

    resolved = resolve_effective_configs(bundle)

    assert len(resolved) == 1
    decisions = {item.field: item for item in resolved[0].override_decisions}
    assert decisions["quality_profile"].accepted is True
    assert decisions["media_type"].accepted is False
