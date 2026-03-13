from pathlib import Path

import pytest

from src.config import ensure_semantic_valid, load_parsed_config_bundle
from src.config.effective_resolution import resolve_effective_configs


@pytest.mark.e2e
def test_e2e_yaml_parse_validate_and_resolve_effective_configs() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito6/medium"))
    ensure_semantic_valid(bundle)

    effective = resolve_effective_configs(bundle)

    assert effective[0].subscription_id == "podcast-es"
    assert effective[0].resolved_options["audio_language"] == "es"
    assert effective[0].resolved_options["source_kind"] == "channel"
