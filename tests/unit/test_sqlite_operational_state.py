import sqlite3
from pathlib import Path

import pytest

from src.persistence.sqlite_state import (
    SCHEMA_VERSION,
    ExecutionPersistenceEnvelope,
    QueueJobEnvelope,
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


@pytest.mark.unit
def test_hito14_duplicate_detection_uses_persisted_known_items(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    state.upsert_subscription(
        subscription_id="tech_channel",
        profile_id="podcast_profile",
        source_kind="channel",
        source_value="https://example.invalid/tech",
        config_signature="cfg-signature",
    )

    state.record_execution(
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
            decision_reason="new_item",
        )
    )

    decision = state.decide_anti_redownload(
        subscription_id="tech_channel",
        item_identifier="tech_channel::comp-signat",
        item_signature="comp-signature",
    )

    assert decision.action == "discard"
    assert decision.reason == "duplicate_already_processed"
    assert decision.previous_status == "success"


@pytest.mark.unit
def test_hito14_retry_after_failure_is_allowed(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    state.upsert_subscription(
        subscription_id="science_channel",
        profile_id="video_profile",
        source_kind="channel",
        source_value="https://example.invalid/science",
        config_signature="cfg-v1",
    )

    state.record_execution(
        ExecutionPersistenceEnvelope(
            job_id="job-failed",
            subscription_id="science_channel",
            profile_id="video_profile",
            status="failed",
            error_type="non_zero_exit",
            severity="recoverable",
            exit_code=29,
            error_message="boom",
            stdout="",
            stderr="boom",
            command_payload={"args": ["ytdl-sub", "sub"]},
            config_signature="cfg-v1",
            effective_signature="eff-v1",
            translation_signature="tr-v1",
            compilation_signature="comp-v1",
            artifact_yaml_path="/tmp/artifact.yaml",
            metadata_json_path="/tmp/metadata.json",
            started_at="2026-01-01T00:00:00+00:00",
            finished_at="2026-01-01T00:00:01+00:00",
            duration_ms=1000,
            known_item_identifier="science_channel::comp-v1",
            known_item_signature="comp-v1",
            decision_reason="new_item",
            failure_reason="non_zero_exit:boom",
        )
    )

    decision = state.decide_anti_redownload(
        subscription_id="science_channel",
        item_identifier="science_channel::comp-v1",
        item_signature="comp-v1",
    )

    assert decision.action == "execute"
    assert decision.reason == "retry_after_failure"
    assert decision.previous_status == "failed"


@pytest.mark.unit
def test_hito15_retention_selects_oldest_by_publication_date(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    state.upsert_subscription(
        subscription_id="tech_channel",
        profile_id="profile_tv",
        source_kind="channel",
        source_value="https://example.invalid/tech",
        config_signature="cfg-v1",
    )

    for idx, publication in enumerate(
        (
            "2026-01-01T00:00:00+00:00",
            "2026-01-02T00:00:00+00:00",
            "2026-01-03T00:00:00+00:00",
        ),
        start=1,
    ):
        state.record_execution(
            ExecutionPersistenceEnvelope(
                job_id=f"job-{idx}",
                subscription_id="tech_channel",
                profile_id="profile_tv",
                status="success",
                error_type="none",
                severity="none",
                exit_code=0,
                error_message=None,
                stdout="ok",
                stderr="",
                command_payload={
                    "args": ["ytdl-sub", "sub"],
                    "retention": {
                        "publication_at": publication,
                        "storage_path": str(tmp_path / f"item-{idx}.mkv"),
                    },
                },
                config_signature="cfg-v1",
                effective_signature="eff-v1",
                translation_signature="tr-v1",
                compilation_signature=f"comp-v{idx}",
                artifact_yaml_path="/tmp/a.yaml",
                metadata_json_path="/tmp/m.json",
                started_at=f"2026-01-0{idx}T00:00:00+00:00",
                finished_at=f"2026-01-0{idx}T00:00:01+00:00",
                duration_ms=1000,
                known_item_identifier=f"tech_channel::item-{idx}",
                known_item_signature=f"sig-{idx}",
                decision_reason="new_item",
            )
        )

    purged = state.apply_retention_policy(
        subscription_id="tech_channel",
        profile_id="profile_tv",
        max_items=2,
        triggering_run_id=3,
    )
    snapshot = state.get_subscription_state("tech_channel")

    assert [item.item_identifier for item in purged] == ["tech_channel::item-1"]
    assert purged[0].criterion_used == "publication_at"
    assert sorted(
        item["item_identifier"] for item in snapshot["known_items"] if item["is_purged"] is False
    ) == ["tech_channel::item-2", "tech_channel::item-3"]


@pytest.mark.unit
def test_hito15_retention_fallback_uses_finished_at_without_publication_date(
    tmp_path: Path,
) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    state.upsert_subscription(
        subscription_id="science_channel",
        profile_id="profile_tv",
        source_kind="channel",
        source_value="https://example.invalid/science",
        config_signature="cfg-v1",
    )

    state.record_execution(
        ExecutionPersistenceEnvelope(
            job_id="job-a",
            subscription_id="science_channel",
            profile_id="profile_tv",
            status="success",
            error_type="none",
            severity="none",
            exit_code=0,
            error_message=None,
            stdout="ok",
            stderr="",
            command_payload={"args": ["ytdl-sub", "sub"]},
            config_signature="cfg-v1",
            effective_signature="eff-v1",
            translation_signature="tr-v1",
            compilation_signature="comp-a",
            artifact_yaml_path="/tmp/a.yaml",
            metadata_json_path="/tmp/m.json",
            started_at="2026-01-01T00:00:00+00:00",
            finished_at="2026-01-01T00:00:01+00:00",
            duration_ms=1000,
            known_item_identifier="science_channel::a",
            known_item_signature="sig-a",
            decision_reason="new_item",
        )
    )
    state.record_execution(
        ExecutionPersistenceEnvelope(
            job_id="job-b",
            subscription_id="science_channel",
            profile_id="profile_tv",
            status="success",
            error_type="none",
            severity="none",
            exit_code=0,
            error_message=None,
            stdout="ok",
            stderr="",
            command_payload={"args": ["ytdl-sub", "sub"]},
            config_signature="cfg-v1",
            effective_signature="eff-v1",
            translation_signature="tr-v1",
            compilation_signature="comp-b",
            artifact_yaml_path="/tmp/a.yaml",
            metadata_json_path="/tmp/m.json",
            started_at="2026-01-02T00:00:00+00:00",
            finished_at="2026-01-02T00:00:01+00:00",
            duration_ms=1000,
            known_item_identifier="science_channel::b",
            known_item_signature="sig-b",
            decision_reason="new_item",
        )
    )

    purged = state.apply_retention_policy(
        subscription_id="science_channel",
        profile_id="profile_tv",
        max_items=1,
        triggering_run_id=2,
    )
    snapshot = state.get_subscription_state("science_channel")

    assert [item.item_identifier for item in purged] == ["science_channel::a"]
    assert purged[0].criterion_used == "fallback_finished_at"
    assert any(
        event["event_kind"] == "purge"
        and event["detail"]["criterion"] == "fallback_finished_at"
        and event["detail"]["reason"] == "max_items_exceeded"
        for event in snapshot["events"]
    )


@pytest.mark.unit
def test_hito17_schema_queue_backlog_has_persisted_job_model_columns(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()

    with sqlite3.connect(tmp_path / "state.sqlite") as conn:
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(queue_backlog)").fetchall()
            if len(row) > 1
        }

    assert {
        "job_id",
        "queue_kind",
        "status",
        "priority",
        "signature",
        "subscription_id",
        "profile_id",
        "resource_kind",
        "resource_id",
        "payload_json",
        "attempts",
        "max_attempts",
        "scheduled_at",
        "created_at",
        "updated_at",
    }.issubset(columns)


@pytest.mark.unit
def test_hito18_queue_claim_retry_and_dead_letter_lifecycle(tmp_path: Path) -> None:
    state = SQLiteOperationalState(tmp_path / "state.sqlite")
    state.init_schema()
    state.enqueue_job(
        QueueJobEnvelope(
            job_id="h18-job",
            queue_kind="sync",
            priority=90,
            subscription_id="sub-h18",
            payload={"segment": "all"},
            max_attempts=2,
        )
    )

    runnable = state.list_runnable_queue_jobs(now="2099-01-01T00:00:00+00:00")
    assert [job.job_id for job in runnable] == ["h18-job"]

    claimed = state.claim_queue_job(job_id="h18-job")
    assert claimed is not None and claimed.status == "running"

    retry = state.schedule_queue_retry(job_id="h18-job", scheduled_at="2099-01-01T01:00:00+00:00")
    assert retry.status == "retry_pending"
    assert retry.attempts == 1

    state.transition_queue_job_status(job_id="h18-job", next_status="queued")
    state.claim_queue_job(job_id="h18-job")
    dead = state.dead_letter_queue_job(
        job_id="h18-job", error_type="non_recoverable", error_message="boom"
    )
    assert dead.status == "dead_letter"

    dead_letters = state.list_dead_letters()
    assert len(dead_letters) == 1
    assert dead_letters[0].job_id == "h18-job"
