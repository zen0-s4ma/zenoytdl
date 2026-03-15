from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.core.cache_system import CachedCorePipeline, CoreCacheSystem


@pytest.mark.e2e
def test_hito16_e2e_repeat_same_case_reduces_recomputation_with_same_result(tmp_path: Path) -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito11/valid/single"))
    cache = CoreCacheSystem()
    pipeline = CachedCorePipeline(cache)

    batch_first = pipeline.compile(bundle, tmp_path / "compiled")
    batch_second = pipeline.compile(bundle, tmp_path / "compiled")

    first_signatures = [item.compilation_signature for item in batch_first.artifacts]
    second_signatures = [item.compilation_signature for item in batch_second.artifacts]

    assert first_signatures == second_signatures
    assert cache.metrics_snapshot()["config_compilation"] == {"hits": 1, "misses": 1}
