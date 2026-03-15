from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.core.cache_system import CachedCorePipeline, CoreCacheSystem


@pytest.mark.integration
def test_hito16_integration_cache_wraps_validation_translation_and_compilation(
    tmp_path: Path,
) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    cache = CoreCacheSystem()
    pipeline = CachedCorePipeline(cache)

    v1 = pipeline.validate(bundle)
    t1 = pipeline.translate(bundle)
    c1 = pipeline.compile(bundle, tmp_path / "compiled")

    v2 = pipeline.validate(bundle)
    t2 = pipeline.translate(bundle)
    c2 = pipeline.compile(bundle, tmp_path / "compiled")

    assert v1.to_dict() == v2.to_dict()
    assert [item.translation_signature for item in t1] == [
        item.translation_signature for item in t2
    ]
    assert [item.compilation_signature for item in c1.artifacts] == [
        item.compilation_signature for item in c2.artifacts
    ]

    metrics = cache.metrics_snapshot()
    assert metrics["validation"] == {"hits": 1, "misses": 1}
    assert metrics["translation"] == {"hits": 1, "misses": 1}
    assert metrics["config_compilation"] == {"hits": 1, "misses": 1}
