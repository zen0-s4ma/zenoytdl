from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PersistedRunRecord:
    run_id: int
    job_id: str
    subscription_id: str
    profile_id: str
    status: str
    error_type: str
    severity: str
    exit_code: int | None
    config_signature: str
    effective_signature: str
    translation_signature: str
    compilation_signature: str
    started_at: str
    finished_at: str
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "job_id": self.job_id,
            "subscription_id": self.subscription_id,
            "profile_id": self.profile_id,
            "status": self.status,
            "error_type": self.error_type,
            "severity": self.severity,
            "exit_code": self.exit_code,
            "config_signature": self.config_signature,
            "effective_signature": self.effective_signature,
            "translation_signature": self.translation_signature,
            "compilation_signature": self.compilation_signature,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
        }


@dataclass(frozen=True)
class ExecutionPersistenceEnvelope:
    job_id: str
    subscription_id: str
    profile_id: str
    status: str
    error_type: str
    severity: str
    exit_code: int | None
    error_message: str | None
    stdout: str
    stderr: str
    command_payload: dict[str, Any]
    config_signature: str
    effective_signature: str
    translation_signature: str
    compilation_signature: str
    artifact_yaml_path: str
    metadata_json_path: str
    started_at: str
    finished_at: str
    duration_ms: int
    known_item_identifier: str
    known_item_signature: str
    decision_reason: str | None = None
    discard_reason: str | None = None
    failure_reason: str | None = None


@dataclass(frozen=True)
class AntiRedownloadDecision:
    action: str
    reason: str
    known_item_found: bool
    previous_status: str | None


class SQLiteOperationalState:
    """Persistencia operativa mínima Hito 13 para estado y trazabilidad."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def init_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS subscriptions (
                    subscription_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    source_value TEXT NOT NULL,
                    config_signature TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS execution_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL UNIQUE,
                    subscription_id TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    exit_code INTEGER,
                    error_message TEXT,
                    stdout TEXT NOT NULL,
                    stderr TEXT NOT NULL,
                    command_json TEXT NOT NULL,
                    config_signature TEXT NOT NULL,
                    effective_signature TEXT NOT NULL,
                    translation_signature TEXT NOT NULL,
                    compilation_signature TEXT NOT NULL,
                    artifact_yaml_path TEXT NOT NULL,
                    metadata_json_path TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions(subscription_id)
                );

                CREATE TABLE IF NOT EXISTS known_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscription_id TEXT NOT NULL,
                    item_identifier TEXT NOT NULL,
                    item_signature TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    last_run_id INTEGER,
                    last_status TEXT NOT NULL,
                    UNIQUE(subscription_id, item_identifier),
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions(subscription_id),
                    FOREIGN KEY (last_run_id) REFERENCES execution_runs(id)
                );

                CREATE TABLE IF NOT EXISTS run_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    subscription_id TEXT NOT NULL,
                    event_kind TEXT NOT NULL,
                    item_identifier TEXT,
                    detail_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES execution_runs(id),
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions(subscription_id)
                );

                CREATE TABLE IF NOT EXISTS postprocessing_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    subscription_id TEXT NOT NULL,
                    item_identifier TEXT NOT NULL,
                    postprocessing_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    detail_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(subscription_id, item_identifier, postprocessing_id),
                    FOREIGN KEY (run_id) REFERENCES execution_runs(id),
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions(subscription_id)
                );

                CREATE TABLE IF NOT EXISTS run_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    captured_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES execution_runs(id)
                );

                CREATE TABLE IF NOT EXISTS queue_backlog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscription_id TEXT NOT NULL,
                    dedupe_key TEXT NOT NULL,
                    state TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    attempts INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(subscription_id, dedupe_key)
                );

                CREATE TABLE IF NOT EXISTS cache_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_scope TEXT NOT NULL,
                    cache_key TEXT NOT NULL,
                    cache_signature TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(cache_scope, cache_key)
                );
                """
            )
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            conn.commit()

    def upsert_subscription(
        self,
        *,
        subscription_id: str,
        profile_id: str,
        source_kind: str,
        source_value: str,
        config_signature: str,
    ) -> None:
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO subscriptions(
                    subscription_id,
                    profile_id,
                    source_kind,
                    source_value,
                    config_signature,
                    created_at,
                    updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(subscription_id) DO UPDATE SET
                    profile_id=excluded.profile_id,
                    source_kind=excluded.source_kind,
                    source_value=excluded.source_value,
                    config_signature=excluded.config_signature,
                    updated_at=excluded.updated_at
                """,
                (
                    subscription_id,
                    profile_id,
                    source_kind,
                    source_value,
                    config_signature,
                    now,
                    now,
                ),
            )
            conn.commit()

    def record_execution(self, envelope: ExecutionPersistenceEnvelope) -> PersistedRunRecord:
        with self._connect() as conn:
            run_id = conn.execute(
                """
                INSERT INTO execution_runs(
                    job_id,
                    subscription_id,
                    profile_id,
                    status,
                    error_type,
                    severity,
                    exit_code,
                    error_message,
                    stdout,
                    stderr,
                    command_json,
                    config_signature,
                    effective_signature,
                    translation_signature,
                    compilation_signature,
                    artifact_yaml_path,
                    metadata_json_path,
                    started_at,
                    finished_at,
                    duration_ms,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    envelope.job_id,
                    envelope.subscription_id,
                    envelope.profile_id,
                    envelope.status,
                    envelope.error_type,
                    envelope.severity,
                    envelope.exit_code,
                    envelope.error_message,
                    envelope.stdout,
                    envelope.stderr,
                    _stable_json(envelope.command_payload),
                    envelope.config_signature,
                    envelope.effective_signature,
                    envelope.translation_signature,
                    envelope.compilation_signature,
                    envelope.artifact_yaml_path,
                    envelope.metadata_json_path,
                    envelope.started_at,
                    envelope.finished_at,
                    envelope.duration_ms,
                    envelope.finished_at,
                ),
            ).lastrowid

            conn.execute(
                """
                INSERT INTO known_items(
                    subscription_id,
                    item_identifier,
                    item_signature,
                    first_seen_at,
                    last_seen_at,
                    last_run_id,
                    last_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(subscription_id, item_identifier) DO UPDATE SET
                    item_signature=excluded.item_signature,
                    last_seen_at=excluded.last_seen_at,
                    last_run_id=excluded.last_run_id,
                    last_status=excluded.last_status
                """,
                (
                    envelope.subscription_id,
                    envelope.known_item_identifier,
                    envelope.known_item_signature,
                    envelope.finished_at,
                    envelope.finished_at,
                    run_id,
                    envelope.status,
                ),
            )

            self._record_run_events(conn, run_id, envelope)
            self._record_postprocessing_state(conn, run_id, envelope)
            self._record_metrics(conn, run_id, envelope)
            conn.commit()

        return PersistedRunRecord(
            run_id=run_id,
            job_id=envelope.job_id,
            subscription_id=envelope.subscription_id,
            profile_id=envelope.profile_id,
            status=envelope.status,
            error_type=envelope.error_type,
            severity=envelope.severity,
            exit_code=envelope.exit_code,
            config_signature=envelope.config_signature,
            effective_signature=envelope.effective_signature,
            translation_signature=envelope.translation_signature,
            compilation_signature=envelope.compilation_signature,
            started_at=envelope.started_at,
            finished_at=envelope.finished_at,
            duration_ms=envelope.duration_ms,
        )

    def get_subscription_state(self, subscription_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            sub_row = conn.execute(
                """
                SELECT
                    subscription_id,
                    profile_id,
                    source_kind,
                    source_value,
                    config_signature,
                    updated_at
                FROM subscriptions
                WHERE subscription_id = ?
                """,
                (subscription_id,),
            ).fetchone()
            if sub_row is None:
                raise KeyError(f"Suscripción no encontrada en estado persistido: {subscription_id}")

            runs = conn.execute(
                """
                SELECT
                    id,
                    job_id,
                    status,
                    error_type,
                    severity,
                    exit_code,
                    config_signature,
                    effective_signature,
                    translation_signature,
                    compilation_signature,
                    finished_at,
                    duration_ms
                FROM execution_runs
                WHERE subscription_id = ?
                ORDER BY id ASC
                """,
                (subscription_id,),
            ).fetchall()

            items = conn.execute(
                """
                SELECT item_identifier, item_signature, last_status, first_seen_at, last_seen_at
                FROM known_items
                WHERE subscription_id = ?
                ORDER BY item_identifier ASC
                """,
                (subscription_id,),
            ).fetchall()
            events = conn.execute(
                """
                SELECT run_id, event_kind, item_identifier, detail_json, created_at
                FROM run_events
                WHERE subscription_id = ?
                ORDER BY id ASC
                """,
                (subscription_id,),
            ).fetchall()

        return {
            "subscription": {
                "subscription_id": sub_row["subscription_id"],
                "profile_id": sub_row["profile_id"],
                "source_kind": sub_row["source_kind"],
                "source_value": sub_row["source_value"],
                "config_signature": sub_row["config_signature"],
                "updated_at": sub_row["updated_at"],
            },
            "runs": [
                {
                    "run_id": row["id"],
                    "job_id": row["job_id"],
                    "status": row["status"],
                    "error_type": row["error_type"],
                    "severity": row["severity"],
                    "exit_code": row["exit_code"],
                    "config_signature": row["config_signature"],
                    "effective_signature": row["effective_signature"],
                    "translation_signature": row["translation_signature"],
                    "compilation_signature": row["compilation_signature"],
                    "finished_at": row["finished_at"],
                    "duration_ms": row["duration_ms"],
                }
                for row in runs
            ],
            "known_items": [
                {
                    "item_identifier": row["item_identifier"],
                    "item_signature": row["item_signature"],
                    "last_status": row["last_status"],
                    "first_seen_at": row["first_seen_at"],
                    "last_seen_at": row["last_seen_at"],
                }
                for row in items
            ],
            "events": [
                {
                    "run_id": row["run_id"],
                    "event_kind": row["event_kind"],
                    "item_identifier": row["item_identifier"],
                    "detail": json.loads(row["detail_json"]),
                    "created_at": row["created_at"],
                }
                for row in events
            ],
        }

    def decide_anti_redownload(
        self,
        *,
        subscription_id: str,
        item_identifier: str,
        item_signature: str,
    ) -> AntiRedownloadDecision:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT item_signature, last_status
                FROM known_items
                WHERE subscription_id = ? AND item_identifier = ?
                """,
                (subscription_id, item_identifier),
            ).fetchone()

        if row is None:
            return AntiRedownloadDecision(
                action="execute",
                reason="new_item",
                known_item_found=False,
                previous_status=None,
            )

        previous_status = str(row["last_status"])
        previous_signature = str(row["item_signature"])
        if previous_signature == item_signature and previous_status in {
            "success",
            "discarded_duplicate",
        }:
            return AntiRedownloadDecision(
                action="discard",
                reason="duplicate_already_processed",
                known_item_found=True,
                previous_status=previous_status,
            )

        if previous_signature == item_signature and previous_status == "failed":
            return AntiRedownloadDecision(
                action="execute",
                reason="retry_after_failure",
                known_item_found=True,
                previous_status=previous_status,
            )

        if previous_signature != item_signature:
            return AntiRedownloadDecision(
                action="execute",
                reason="item_signature_changed",
                known_item_found=True,
                previous_status=previous_status,
            )

        return AntiRedownloadDecision(
            action="execute",
            reason="state_allows_execution",
            known_item_found=True,
            previous_status=previous_status,
        )

    def _record_run_events(
        self,
        conn: sqlite3.Connection,
        run_id: int,
        envelope: ExecutionPersistenceEnvelope,
    ) -> None:
        now = envelope.finished_at
        event_detail = {
            "status": envelope.status,
            "error_type": envelope.error_type,
            "compilation_signature": envelope.compilation_signature,
            "decision_reason": envelope.decision_reason,
        }
        conn.execute(
            """
            INSERT INTO run_events(
                run_id,
                subscription_id,
                event_kind,
                item_identifier,
                detail_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                envelope.subscription_id,
                "synchronization",
                envelope.known_item_identifier,
                _stable_json(event_detail),
                now,
            ),
        )

        if envelope.status == "success":
            event_kind = "download"
            detail = {
                "stdout_size": len(envelope.stdout),
                "stderr_size": len(envelope.stderr),
                "decision_reason": envelope.decision_reason,
            }
        elif envelope.status == "discarded":
            event_kind = "discard"
            detail = {
                "discard_reason": envelope.discard_reason,
                "previous_state": envelope.decision_reason,
            }
        else:
            event_kind = "failure"
            detail = {
                "error_message": envelope.error_message or "",
                "failure_reason": envelope.failure_reason,
                "error_type": envelope.error_type,
            }

        conn.execute(
            """
            INSERT INTO run_events(
                run_id,
                subscription_id,
                event_kind,
                item_identifier,
                detail_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                envelope.subscription_id,
                event_kind,
                envelope.known_item_identifier,
                _stable_json(detail),
                now,
            ),
        )

    def _record_postprocessing_state(
        self,
        conn: sqlite3.Connection,
        run_id: int,
        envelope: ExecutionPersistenceEnvelope,
    ) -> None:
        state = "pending" if envelope.status == "success" else "skipped"
        conn.execute(
            """
            INSERT INTO postprocessing_state(
                run_id,
                subscription_id,
                item_identifier,
                postprocessing_id,
                state,
                detail_json,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(subscription_id, item_identifier, postprocessing_id) DO UPDATE SET
                run_id=excluded.run_id,
                state=excluded.state,
                detail_json=excluded.detail_json,
                updated_at=excluded.updated_at
            """,
            (
                run_id,
                envelope.subscription_id,
                envelope.known_item_identifier,
                "__base__",
                state,
                _stable_json({"from_run_id": run_id}),
                envelope.finished_at,
            ),
        )

    def _record_metrics(
        self,
        conn: sqlite3.Connection,
        run_id: int,
        envelope: ExecutionPersistenceEnvelope,
    ) -> None:
        metrics = {
            "duration_ms": float(envelope.duration_ms),
            "stdout_bytes": float(len(envelope.stdout.encode("utf-8"))),
            "stderr_bytes": float(len(envelope.stderr.encode("utf-8"))),
        }
        for metric_name, metric_value in metrics.items():
            conn.execute(
                """
                INSERT INTO run_metrics(run_id, metric_name, metric_value, captured_at)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, metric_name, metric_value, envelope.finished_at),
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
