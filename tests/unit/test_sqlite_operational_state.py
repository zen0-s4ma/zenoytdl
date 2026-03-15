import sqlite3
from pathlib import Path

import pytest

from src.persistence.sqlite_state import (
    SCHEMA_VERSION,
    ExecutionPersistenceEnvelope,
    SQLiteOperationalState,
)


@pytest.mark.unit
def test_hito13_schema_and_initial_migration_are_created(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    state = SQLiteOperationalState(db_path)

    state.init_schema()

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        user_version = conn.execute("PRAGMA user_version").fetchone()[0]

    assert {
        "subscriptions",
        "execution_runs",
        "known_items",
        "run_events",
        "postprocessing_state",
        "run_metrics",
        "queue_backlog",
        "cache_index",
    }.issubset(tables)
    assert user_version == SCHEMA_VERSION


@pytest.mark.unit
def test_hito13_repository_records_and_reads_subscription_state(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    state.upsert_subscription(
        subscription_id="tech_channel",
        profile_id="podcast_profile",
        source_kind="channel",
        source_value="https://example.invalid/tech",
        config_signature="cfg-signature",
    )

    record = state.record_execution(
        ExecutionPersistenceEnvelope(
            job_id="job-1",
            subscription_id="tech_channel",
            profile_id="podcast_profile",
            status="success",
            error_type="none",
            severity="none",
            exit_code=0,
            error_message=None,
            stdout="ok",
            stderr="",
            command_payload={"args": ["ytdl-sub", "sub"]},
            config_signature="cfg-signature",
            effective_signature="eff-signature",
            translation_signature="tr-signature",
            compilation_signature="comp-signature",
            artifact_yaml_path="/tmp/artifact.yaml",
            metadata_json_path="/tmp/metadata.json",
            started_at="2026-01-01T00:00:00+00:00",
            finished_at="2026-01-01T00:00:01+00:00",
            duration_ms=1000,
            known_item_identifier="tech_channel::comp-signat",
            known_item_signature="comp-signature",
        )
    )

    snapshot = state.get_subscription_state("tech_channel")

    assert record.to_dict()["status"] == "success"
    assert snapshot["subscription"]["config_signature"] == "cfg-signature"
    assert snapshot["runs"][0]["compilation_signature"] == "comp-signature"
    assert snapshot["known_items"][0]["item_identifier"] == "tech_channel::comp-signat"


@pytest.mark.unit
def test_hito13_serialization_of_run_state_is_stable(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    state.upsert_subscription(
        subscription_id="science_channel",
        profile_id="video_profile",
        source_kind="channel",
        source_value="https://example.invalid/science",
        config_signature="cfg-v1",
    )

    run = state.record_execution(
        ExecutionPersistenceEnvelope(
            job_id="job-stable",
            subscription_id="science_channel",
            profile_id="video_profile",
            status="failed",
            error_type="non_zero_exit",
            severity="recoverable",
            exit_code=17,
            error_message="boom",
            stdout="",
            stderr="boom",
            command_payload={"args": ["ytdl-sub", "sub", "--artifact", "x"]},
            config_signature="cfg-v1",
            effective_signature="eff-v1",
            translation_signature="tr-v1",
            compilation_signature="comp-v1",
            artifact_yaml_path="/tmp/a.yaml",
            metadata_json_path="/tmp/m.json",
            started_at="2026-01-01T00:00:00+00:00",
            finished_at="2026-01-01T00:00:02+00:00",
            duration_ms=2000,
            known_item_identifier="science_channel::comp-v1",
            known_item_signature="comp-v1",
        )
    )

    assert run.to_dict() == {
        "run_id": 1,
        "job_id": "job-stable",
        "subscription_id": "science_channel",
        "profile_id": "video_profile",
        "status": "failed",
        "error_type": "non_zero_exit",
        "severity": "recoverable",
        "exit_code": 17,
        "config_signature": "cfg-v1",
        "effective_signature": "eff-v1",
        "translation_signature": "tr-v1",
        "compilation_signature": "comp-v1",
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:02+00:00",
        "duration_ms": 2000,
    }
