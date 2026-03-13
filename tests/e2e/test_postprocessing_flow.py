from pathlib import Path

import pytest

from src.config import ensure_semantic_valid, load_parsed_config_bundle
from src.config.effective_resolution import resolve_effective_configs, serialize_effective_configs


@pytest.mark.e2e
def test_e2e_postprocessing_from_yaml_to_effective_artifact_ready_payload() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito8/valid/full-flow"))
    ensure_semantic_valid(bundle)

    effective = resolve_effective_configs(bundle)
    payload = serialize_effective_configs(effective)

    assert "effective_configs" in payload
    assert payload["effective_configs"][0]["postprocessings"]
