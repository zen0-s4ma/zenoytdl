from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.core.cache_system import CachedCorePipeline, CoreCacheSystem


@pytest.mark.regression
def test_hito16_regression_expected_hits_invalidations_and_functional_equality(
    tmp_path: Path,
) -> None:
    source = Path("tests/fixtures/hito11/valid/single")
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    for file_name in ("general.yaml", "profiles.yaml", "subscriptions.yaml", "ytdl-sub-conf.yaml"):
        (cfg_dir / file_name).write_text(
            (source / file_name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    cache = CoreCacheSystem()
    pipeline = CachedCorePipeline(cache)

    bundle_v1 = load_parsed_config_bundle(cfg_dir)
    run1 = pipeline.compile(bundle_v1, tmp_path / "compiled")
    run2 = pipeline.compile(bundle_v1, tmp_path / "compiled")

    ytdl_conf = cfg_dir / "ytdl-sub-conf.yaml"
    ytdl_conf.write_text(
        ytdl_conf.read_text(encoding="utf-8").replace("--dry-run", "--download-archive"),
        encoding="utf-8",
    )

    bundle_v2 = load_parsed_config_bundle(cfg_dir)
    run3 = pipeline.compile(bundle_v2, tmp_path / "compiled")

    assert [item.compilation_signature for item in run1.artifacts] == [
        item.compilation_signature for item in run2.artifacts
    ]
    assert [item.compilation_signature for item in run1.artifacts] != [
        item.compilation_signature for item in run3.artifacts
    ]

    metrics = cache.metrics_snapshot()["config_compilation"]
    assert metrics["hits"] == 1
    assert metrics["misses"] == 2
