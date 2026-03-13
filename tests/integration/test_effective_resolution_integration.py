from pathlib import Path

import pytest

from src.config import ensure_semantic_valid, load_parsed_config_bundle
from src.config.effective_resolution import resolve_effective_configs, serialize_effective_configs


@pytest.mark.integration
def test_parser_validator_resolver_work_together() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito6/complex"))
    report = ensure_semantic_valid(bundle)

    effective = resolve_effective_configs(bundle)
    payload = serialize_effective_configs(effective)

    assert report.ok is True
    assert len(effective) == 2
    assert len(payload["batch_signature"]) == 64
    assert effective[0].value_origins["media_type"].startswith("subscriptions.yaml")
