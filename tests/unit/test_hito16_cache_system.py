from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.core.cache_system import CachedCorePipeline, CoreCacheSystem
from src.persistence.sqlite_state import ExecutionPersistenceEnvelope, SQLiteOperationalState


class FakeClock:
    def __init__(self, start: datetime) -> None:
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: int) -> None:
        self.current = self.current + timedelta(seconds=seconds)


@pytest.mark.unit
def test_hito16_cache_hit_miss_and_metrics_for_validation() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito5/valid/semantic-ok"))
    cache = CoreCacheSystem()
    pipeline = CachedCorePipeline(cache)

    first = pipeline.validate(bundle)
    second = pipeline.validate(bundle)

    assert first.to_dict() == second.to_dict()
    metrics = cache.metrics_snapshot()["validation"]
    assert metrics == {"hits": 1, "misses": 1}


@pytest.mark.unit
def test_hito16_cache_ttl_expiration_triggers_recompute() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito10/valid/base-bridge"))
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    cache = CoreCacheSystem(ttl_by_scope={"translation": 1}, now_provider=clock.now)
    pipeline = CachedCorePipeline(cache)

    first = pipeline.translate(bundle)
    clock.advance(2)
    second = pipeline.translate(bundle)

    assert [item.translation_signature for item in first] == [
        item.translation_signature for item in second
    ]
    metrics = cache.metrics_snapshot()["translation"]
    assert metrics == {"hits": 0, "misses": 2}


@pytest.mark.unit
def test_hito16_cache_invalidation_on_file_hash_config_and_manual_purge(tmp_path: Path) -> None:
    source = Path("tests/fixtures/hito10/valid/base-bridge")
    target = tmp_path / "cfg"
    target.mkdir(parents=True, exist_ok=True)
    for file_name in ("general.yaml", "profiles.yaml", "subscriptions.yaml", "ytdl-sub-conf.yaml"):
        (target / file_name).write_text(
            (source / file_name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    cache = CoreCacheSystem()
    pipeline = CachedCorePipeline(cache)

    bundle_v1 = load_parsed_config_bundle(target)
    first = pipeline.translate(bundle_v1)

    text = (target / "subscriptions.yaml").read_text(encoding="utf-8")
    (target / "subscriptions.yaml").write_text(
        text.replace("balanced", "high"),
        encoding="utf-8",
    )
    bundle_v2 = load_parsed_config_bundle(target)
    second = pipeline.translate(bundle_v2)

    assert [item.translation_signature for item in first] != [
        item.translation_signature for item in second
    ]

    cache.purge(scope="translation")
    third = pipeline.translate(bundle_v2)
    assert [item.translation_signature for item in second] == [
        item.translation_signature for item in third
    ]

    metrics = cache.metrics_snapshot()["translation"]
    assert metrics["misses"] >= 3


@pytest.mark.unit
def test_hito16_cache_invalidation_on_ytdl_sub_conf_and_error() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito10/valid/base-bridge"))
    cache = CoreCacheSystem()
    pipeline = CachedCorePipeline(cache)

    translated = pipeline.translate(bundle)
    key = f"translation::{bundle.signature}"
    cache.invalidate_error(scope="translation", key=key)
    translated_again = pipeline.translate(bundle)

    assert [item.translation_signature for item in translated] == [
        item.translation_signature for item in translated_again
    ]
    metrics = cache.metrics_snapshot()["translation"]
    assert metrics["misses"] >= 2


@pytest.mark.unit
def test_hito16_cache_metadata_resolution_hit_and_invalidation(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"profile_id":"p1"}', encoding="utf-8")
    cache = CoreCacheSystem()
    pipeline = CachedCorePipeline(cache)

    first = pipeline.resolve_metadata_profile_id(metadata)
    second = pipeline.resolve_metadata_profile_id(metadata)
    metadata.write_text('{"profile_id":"p2"}', encoding="utf-8")
    third = pipeline.resolve_metadata_profile_id(metadata)

    assert (first, second, third) == ("p1", "p1", "p2")
    assert cache.metrics_snapshot()["metadata_resolution"] == {"hits": 1, "misses": 2}


@pytest.mark.unit
def test_hito16_cache_recent_operational_state_invalidates_on_new_persisted_run(
    tmp_path: Path,
) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    state.upsert_subscription(
        subscription_id="sub-1",
        profile_id="profile-a",
        source_kind="channel",
        source_value="https://example.invalid/channel",
        config_signature="cfg-1",
    )

    state.record_execution(
        ExecutionPersistenceEnvelope(
            job_id="job-1",
            subscription_id="sub-1",
            profile_id="profile-a",
            status="success",
            error_type="none",
            severity="none",
            exit_code=0,
            error_message=None,
            stdout="",
            stderr="",
            command_payload={"retention": {}},
            config_signature="cfg-1",
            effective_signature="eff-1",
            translation_signature="tr-1",
            compilation_signature="cp-1",
            artifact_yaml_path="/tmp/a.yml",
            metadata_json_path="/tmp/m.json",
            started_at="2026-01-01T00:00:00+00:00",
            finished_at="2026-01-01T00:00:01+00:00",
            duration_ms=1000,
            known_item_identifier="sub-1::item-1",
            known_item_signature="sig-1",
        )
    )

    cache = CoreCacheSystem()
    pipeline = CachedCorePipeline(cache)

    snapshot1 = pipeline.get_recent_subscription_state(state=state, subscription_id="sub-1")
    snapshot2 = pipeline.get_recent_subscription_state(state=state, subscription_id="sub-1")

    state.record_execution(
        ExecutionPersistenceEnvelope(
            job_id="job-2",
            subscription_id="sub-1",
            profile_id="profile-a",
            status="success",
            error_type="none",
            severity="none",
            exit_code=0,
            error_message=None,
            stdout="",
            stderr="",
            command_payload={"retention": {}},
            config_signature="cfg-1",
            effective_signature="eff-1",
            translation_signature="tr-1",
            compilation_signature="cp-2",
            artifact_yaml_path="/tmp/a.yml",
            metadata_json_path="/tmp/m.json",
            started_at="2026-01-01T00:00:02+00:00",
            finished_at="2026-01-01T00:00:03+00:00",
            duration_ms=1000,
            known_item_identifier="sub-1::item-2",
            known_item_signature="sig-2",
        )
    )

    snapshot3 = pipeline.get_recent_subscription_state(state=state, subscription_id="sub-1")

    assert len(snapshot1["runs"]) == 1
    assert len(snapshot2["runs"]) == 1
    assert len(snapshot3["runs"]) == 2
    assert cache.metrics_snapshot()["operational_state_recent"] == {"hits": 1, "misses": 2}
