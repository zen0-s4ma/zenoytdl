from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 3


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


@dataclass(frozen=True)
class RetentionPurgeDecision:
    item_identifier: str
    item_signature: str
    publication_at: str | None
    fallback_at: str
    storage_path: str | None
    criterion_used: str

@dataclass(frozen=True)
class QueueJobEnvelope:
    job_id: str
    queue_kind: str
    priority: int
    subscription_id: str | None = None
    profile_id: str | None = None
    resource_kind: str | None = None
    resource_id: str | None = None
    payload: dict[str, Any] | None = None
    status: str = "queued"
    attempts: int = 0
    max_attempts: int = 1
    scheduled_at: str | None = None
    signature: str | None = None


@dataclass(frozen=True)
class QueueJobRecord:
    job_id: str
    queue_kind: str
    status: str
    priority: int
    signature: str
    subscription_id: str | None
    profile_id: str | None
    resource_kind: str | None
    resource_id: str | None
    payload: dict[str, Any]
    attempts: int
    max_attempts: int
    scheduled_at: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class QueueDeadLetterRecord:
    job_id: str
    signature: str
    queue_kind: str
    subscription_id: str | None
    profile_id: str | None
    attempts: int
    max_attempts: int
    error_type: str
    error_message: str
    failed_at: str


_ACTIVE_QUEUE_STATES = frozenset({"queued", "scheduled", "running", "waiting", "retry_pending"})

_QUEUE_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "queued": frozenset({"scheduled", "running", "cancelled"}),
    "scheduled": frozenset({"running", "waiting", "retry_pending", "cancelled"}),
    "running": frozenset(
        {"waiting", "completed", "failed", "retry_pending", "cancelled", "dead_letter"}
    ),
    "waiting": frozenset({"scheduled", "running", "retry_pending", "cancelled"}),
    "retry_pending": frozenset({"queued", "scheduled", "cancelled", "dead_letter"}),
    "completed": frozenset(),
    "failed": frozenset({"retry_pending", "dead_letter", "cancelled"}),
    "cancelled": frozenset(),
    "dead_letter": frozenset(),
}



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
                    publication_at TEXT,
                    storage_path TEXT,
                    retention_sort_at TEXT NOT NULL,
                    retention_criterion TEXT NOT NULL,
                    is_purged INTEGER NOT NULL DEFAULT 0,
                    purged_at TEXT,
                    purge_reason TEXT,
                    purge_run_id INTEGER,
                    UNIQUE(subscription_id, item_identifier),
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions(subscription_id),
                    FOREIGN KEY (last_run_id) REFERENCES execution_runs(id),
                    FOREIGN KEY (purge_run_id) REFERENCES execution_runs(id)
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
                    job_id TEXT NOT NULL UNIQUE,
                    queue_kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    signature TEXT NOT NULL,
                    subscription_id TEXT,
                    profile_id TEXT,
                    resource_kind TEXT,
                    resource_id TEXT,
                    payload_json TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    scheduled_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_queue_backlog_order
                ON queue_backlog(status, priority DESC, created_at ASC);

                CREATE INDEX IF NOT EXISTS idx_queue_backlog_signature
                ON queue_backlog(signature);

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

                CREATE TABLE IF NOT EXISTS queue_dead_letter (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    queue_kind TEXT NOT NULL,
                    subscription_id TEXT,
                    profile_id TEXT,
                    attempts INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    failed_at TEXT NOT NULL
                );
                """
            )
            self._migrate_known_items_for_v2(conn)
            self._migrate_queue_backlog_for_v3(conn)
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
                    last_status,
                    publication_at,
                    storage_path,
                    retention_sort_at,
                    retention_criterion,
                    is_purged,
                    purged_at,
                    purge_reason,
                    purge_run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL, NULL)
                ON CONFLICT(subscription_id, item_identifier) DO UPDATE SET
                    item_signature=excluded.item_signature,
                    last_seen_at=excluded.last_seen_at,
                    last_run_id=excluded.last_run_id,
                    last_status=excluded.last_status,
                    publication_at=excluded.publication_at,
                    storage_path=excluded.storage_path,
                    retention_sort_at=excluded.retention_sort_at,
                    retention_criterion=excluded.retention_criterion,
                    is_purged=0,
                    purged_at=NULL,
                    purge_reason=NULL,
                    purge_run_id=NULL
                """,
                (
                    envelope.subscription_id,
                    envelope.known_item_identifier,
                    envelope.known_item_signature,
                    envelope.finished_at,
                    envelope.finished_at,
                    run_id,
                    envelope.status,
                    _extract_publication_at(envelope.command_payload),
                    _extract_storage_path(envelope.command_payload),
                    _select_retention_sort_at(envelope.command_payload, envelope.finished_at),
                    _select_retention_criterion(envelope.command_payload),
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
                SELECT
                    item_identifier,
                    item_signature,
                    last_status,
                    first_seen_at,
                    last_seen_at,
                    publication_at,
                    retention_sort_at,
                    retention_criterion,
                    is_purged,
                    purged_at,
                    purge_reason
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
                    "publication_at": row["publication_at"],
                    "retention_sort_at": row["retention_sort_at"],
                    "retention_criterion": row["retention_criterion"],
                    "is_purged": bool(row["is_purged"]),
                    "purged_at": row["purged_at"],
                    "purge_reason": row["purge_reason"],
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
                  AND is_purged = 0
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

    def apply_retention_policy(
        self,
        *,
        subscription_id: str,
        profile_id: str,
        max_items: int,
        triggering_run_id: int,
        reason: str = "max_items_exceeded",
    ) -> tuple[RetentionPurgeDecision, ...]:
        if max_items <= 0:
            raise ValueError("max_items debe ser mayor que cero")

        with self._connect() as conn:
            active_rows = conn.execute(
                """
                SELECT
                    item_identifier,
                    item_signature,
                    publication_at,
                    first_seen_at,
                    retention_sort_at,
                    retention_criterion,
                    storage_path
                FROM known_items
                WHERE subscription_id = ?
                  AND is_purged = 0
                ORDER BY
                    retention_sort_at DESC,
                    first_seen_at DESC,
                    item_identifier DESC
                """,
                (subscription_id,),
            ).fetchall()

            if len(active_rows) <= max_items:
                return tuple()

            purge_rows = active_rows[max_items:]
            purged_at = _utc_now()
            decisions: list[RetentionPurgeDecision] = []

            for row in purge_rows:
                storage_path = row["storage_path"]
                if isinstance(storage_path, str) and storage_path:
                    storage = Path(storage_path)
                    if storage.exists() and storage.is_file():
                        storage.unlink()

                conn.execute(
                    """
                    UPDATE known_items
                    SET
                        is_purged = 1,
                        purged_at = ?,
                        purge_reason = ?,
                        purge_run_id = ?
                    WHERE subscription_id = ? AND item_identifier = ?
                    """,
                    (purged_at, reason, triggering_run_id, subscription_id, row["item_identifier"]),
                )
                detail = {
                    "reason": reason,
                    "max_items": max_items,
                    "criterion": row["retention_criterion"],
                    "retention_sort_at": row["retention_sort_at"],
                    "publication_at": row["publication_at"],
                    "storage_path": row["storage_path"],
                    "profile_id": profile_id,
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
                        triggering_run_id,
                        subscription_id,
                        "purge",
                        row["item_identifier"],
                        _stable_json(detail),
                        purged_at,
                    ),
                )
                decisions.append(
                    RetentionPurgeDecision(
                        item_identifier=str(row["item_identifier"]),
                        item_signature=str(row["item_signature"]),
                        publication_at=row["publication_at"],
                        fallback_at=str(row["retention_sort_at"]),
                        storage_path=row["storage_path"],
                        criterion_used=str(row["retention_criterion"]),
                    )
                )

            conn.commit()
            return tuple(decisions)


    def enqueue_job(self, envelope: QueueJobEnvelope) -> tuple[QueueJobRecord, bool]:
        if (
            envelope.subscription_id is None
            and envelope.profile_id is None
            and envelope.resource_id is None
        ):
            raise ValueError("queue job debe asociarse a subscription_id, profile_id o resource_id")
        payload = envelope.payload or {}
        signature = envelope.signature or sign_queue_job(
            queue_kind=envelope.queue_kind,
            subscription_id=envelope.subscription_id,
            profile_id=envelope.profile_id,
            resource_kind=envelope.resource_kind,
            resource_id=envelope.resource_id,
            payload=payload,
        )
        now = _utc_now()
        with self._connect() as conn:
            existing = conn.execute(
                f"""
                SELECT *
                FROM queue_backlog
                WHERE signature = ?
                  AND status IN ({','.join('?' for _ in _ACTIVE_QUEUE_STATES)})
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
                """,
                (signature, *_ACTIVE_QUEUE_STATES),
            ).fetchone()
            if existing is not None:
                return (_row_to_queue_job(existing), False)

            conn.execute(
                """
                INSERT INTO queue_backlog(
                    job_id, queue_kind, status, priority, signature,
                    subscription_id, profile_id, resource_kind, resource_id, payload_json,
                    attempts, max_attempts, scheduled_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    envelope.job_id,
                    envelope.queue_kind,
                    envelope.status,
                    envelope.priority,
                    signature,
                    envelope.subscription_id,
                    envelope.profile_id,
                    envelope.resource_kind,
                    envelope.resource_id,
                    _stable_json(payload),
                    envelope.attempts,
                    envelope.max_attempts,
                    envelope.scheduled_at,
                    now,
                    now,
                ),
            )
            conn.commit()

        return (
            QueueJobRecord(
                job_id=envelope.job_id,
                queue_kind=envelope.queue_kind,
                status=envelope.status,
                priority=envelope.priority,
                signature=signature,
                subscription_id=envelope.subscription_id,
                profile_id=envelope.profile_id,
                resource_kind=envelope.resource_kind,
                resource_id=envelope.resource_id,
                payload=payload,
                attempts=envelope.attempts,
                max_attempts=envelope.max_attempts,
                scheduled_at=envelope.scheduled_at,
                created_at=now,
                updated_at=now,
            ),
            True,
        )

    def transition_queue_job_status(self, *, job_id: str, next_status: str) -> QueueJobRecord:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM queue_backlog WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(f"job no encontrado: {job_id}")
            current_status = str(row["status"])
            allowed = _QUEUE_ALLOWED_TRANSITIONS.get(current_status, frozenset())
            if next_status not in allowed:
                raise ValueError(f"transición inválida: {current_status} -> {next_status}")
            updated_at = _utc_now()
            scheduled_at = row["scheduled_at"]
            if next_status in {"queued", "running", "completed", "dead_letter", "cancelled"}:
                scheduled_at = None
            conn.execute(
                """
                UPDATE queue_backlog
                SET status = ?, scheduled_at = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (next_status, scheduled_at, updated_at, job_id),
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM queue_backlog WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return _row_to_queue_job(updated)

    def list_queue_jobs(self, *, include_terminal: bool = True) -> tuple[QueueJobRecord, ...]:
        with self._connect() as conn:
            if include_terminal:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM queue_backlog
                    ORDER BY priority DESC, created_at ASC
                    """
                ).fetchall()
            else:
                rows = conn.execute(
                    f"""
                    SELECT *
                    FROM queue_backlog
                    WHERE status IN ({','.join('?' for _ in _ACTIVE_QUEUE_STATES)})
                    ORDER BY priority DESC, created_at ASC
                    """,
                    tuple(_ACTIVE_QUEUE_STATES),
                ).fetchall()
        return tuple(_row_to_queue_job(row) for row in rows)

    def get_queue_job(self, job_id: str) -> QueueJobRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM queue_backlog WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        return _row_to_queue_job(row)

    def list_runnable_queue_jobs(self, *, now: str | None = None) -> tuple[QueueJobRecord, ...]:
        now_value = now or _utc_now()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM queue_backlog
                WHERE status IN ('queued', 'scheduled', 'retry_pending')
                  AND (scheduled_at IS NULL OR scheduled_at <= ?)
                ORDER BY priority DESC, created_at ASC
                """,
                (now_value,),
            ).fetchall()
        return tuple(_row_to_queue_job(row) for row in rows)

    def claim_queue_job(self, *, job_id: str) -> QueueJobRecord | None:
        now = _utc_now()
        with self._connect() as conn:
            updated = conn.execute(
                """
                UPDATE queue_backlog
                SET status = 'running', updated_at = ?
                WHERE job_id = ?
                  AND status IN ('queued', 'scheduled', 'retry_pending')
                  AND (scheduled_at IS NULL OR scheduled_at <= ?)
                """,
                (now, job_id, now),
            )
            if updated.rowcount == 0:
                return None
            conn.commit()
            row = conn.execute("SELECT * FROM queue_backlog WHERE job_id = ?", (job_id,)).fetchone()
        return _row_to_queue_job(row)

    def complete_queue_job(self, *, job_id: str) -> QueueJobRecord:
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE queue_backlog
                SET status = 'completed', scheduled_at = NULL, updated_at = ?
                WHERE job_id = ?
                """,
                (now, job_id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM queue_backlog WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(f"job no encontrado: {job_id}")
        return _row_to_queue_job(row)

    def schedule_queue_retry(
        self,
        *,
        job_id: str,
        scheduled_at: str,
    ) -> QueueJobRecord:
        now = _utc_now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT attempts FROM queue_backlog WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"job no encontrado: {job_id}")
            attempts = int(row["attempts"]) + 1
            conn.execute(
                """
                UPDATE queue_backlog
                SET status = 'retry_pending', attempts = ?, scheduled_at = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (attempts, scheduled_at, now, job_id),
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM queue_backlog WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return _row_to_queue_job(updated)

    def dead_letter_queue_job(
        self,
        *,
        job_id: str,
        error_type: str,
        error_message: str,
    ) -> QueueJobRecord:
        now = _utc_now()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM queue_backlog WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(f"job no encontrado: {job_id}")
            attempts = int(row["attempts"]) + 1
            conn.execute(
                """
                UPDATE queue_backlog
                SET status = 'dead_letter', attempts = ?, scheduled_at = NULL, updated_at = ?
                WHERE job_id = ?
                """,
                (attempts, now, job_id),
            )
            conn.execute(
                """
                INSERT INTO queue_dead_letter(
                    job_id, signature, queue_kind, subscription_id, profile_id,
                    attempts, max_attempts, error_type, error_message, failed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["job_id"],
                    row["signature"],
                    row["queue_kind"],
                    row["subscription_id"],
                    row["profile_id"],
                    attempts,
                    row["max_attempts"],
                    error_type,
                    error_message,
                    now,
                ),
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM queue_backlog WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return _row_to_queue_job(updated)

    def list_dead_letters(self) -> tuple[QueueDeadLetterRecord, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    job_id,
                    signature,
                    queue_kind,
                    subscription_id,
                    profile_id,
                    attempts,
                    max_attempts,
                    error_type,
                    error_message,
                    failed_at
                FROM queue_dead_letter
                ORDER BY id ASC
                """
            ).fetchall()
        return tuple(
            QueueDeadLetterRecord(
                job_id=str(row["job_id"]),
                signature=str(row["signature"]),
                queue_kind=str(row["queue_kind"]),
                subscription_id=row["subscription_id"],
                profile_id=row["profile_id"],
                attempts=int(row["attempts"]),
                max_attempts=int(row["max_attempts"]),
                error_type=str(row["error_type"]),
                error_message=str(row["error_message"]),
                failed_at=str(row["failed_at"]),
            )
            for row in rows
        )


    def _migrate_queue_backlog_for_v3(self, conn: sqlite3.Connection) -> None:
        existing = {
            row[1]
            for row in conn.execute("PRAGMA table_info(queue_backlog)").fetchall()
            if len(row) > 1
        }
        if "job_id" in existing:
            return

        conn.executescript(
            """
            ALTER TABLE queue_backlog RENAME TO queue_backlog_legacy;

            CREATE TABLE queue_backlog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL UNIQUE,
                queue_kind TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL,
                signature TEXT NOT NULL,
                subscription_id TEXT,
                profile_id TEXT,
                resource_kind TEXT,
                resource_id TEXT,
                payload_json TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                max_attempts INTEGER NOT NULL,
                scheduled_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_queue_backlog_order
            ON queue_backlog(status, priority DESC, created_at ASC);

            CREATE INDEX IF NOT EXISTS idx_queue_backlog_signature
            ON queue_backlog(signature);
            """
        )

        legacy_rows = conn.execute(
            """
            SELECT
                subscription_id,
                dedupe_key,
                state,
                priority,
                attempts,
                max_attempts,
                created_at,
                updated_at
            FROM queue_backlog_legacy
            """
        ).fetchall()
        for row in legacy_rows:
            payload = {"legacy_dedupe_key": row["dedupe_key"]}
            signature = sign_queue_job(
                queue_kind="maintenance",
                subscription_id=row["subscription_id"],
                profile_id=None,
                resource_kind=None,
                resource_id=None,
                payload=payload,
            )
            conn.execute(
                """
                INSERT INTO queue_backlog(
                    job_id, queue_kind, status, priority, signature, subscription_id, profile_id,
                    resource_kind, resource_id, payload_json, attempts, max_attempts,
                    scheduled_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    f"legacy::{row['subscription_id']}::{row['dedupe_key']}",
                    "maintenance",
                    row["state"],
                    row["priority"],
                    signature,
                    row["subscription_id"],
                    _stable_json(payload),
                    row["attempts"],
                    row["max_attempts"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
        conn.execute("DROP TABLE queue_backlog_legacy")

    def _migrate_known_items_for_v2(self, conn: sqlite3.Connection) -> None:
        existing = {
            row[1]
            for row in conn.execute("PRAGMA table_info(known_items)").fetchall()
            if len(row) > 1
        }
        migration_columns = (
            ("publication_at", "TEXT"),
            ("storage_path", "TEXT"),
            ("retention_sort_at", "TEXT NOT NULL DEFAULT ''"),
            ("retention_criterion", "TEXT NOT NULL DEFAULT 'fallback_finished_at'"),
            ("is_purged", "INTEGER NOT NULL DEFAULT 0"),
            ("purged_at", "TEXT"),
            ("purge_reason", "TEXT"),
            ("purge_run_id", "INTEGER"),
        )
        for name, ddl in migration_columns:
            if name not in existing:
                conn.execute(f"ALTER TABLE known_items ADD COLUMN {name} {ddl}")
        conn.execute(
            """
            UPDATE known_items
            SET
                retention_sort_at = COALESCE(NULLIF(retention_sort_at, ''), last_seen_at),
                retention_criterion = COALESCE(
                    NULLIF(retention_criterion, ''),
                    'fallback_finished_at'
                )
            """
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




def sign_queue_job(
    *,
    queue_kind: str,
    subscription_id: str | None,
    profile_id: str | None,
    resource_kind: str | None,
    resource_id: str | None,
    payload: dict[str, Any],
) -> str:
    canonical = {
        "queue_kind": queue_kind,
        "subscription_id": subscription_id,
        "profile_id": profile_id,
        "resource_kind": resource_kind,
        "resource_id": resource_id,
        "payload": payload,
    }
    return hashlib.sha256(
        json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _row_to_queue_job(row: sqlite3.Row) -> QueueJobRecord:
    return QueueJobRecord(
        job_id=str(row["job_id"]),
        queue_kind=str(row["queue_kind"]),
        status=str(row["status"]),
        priority=int(row["priority"]),
        signature=str(row["signature"]),
        subscription_id=row["subscription_id"],
        profile_id=row["profile_id"],
        resource_kind=row["resource_kind"],
        resource_id=row["resource_id"],
        payload=json.loads(str(row["payload_json"])),
        attempts=int(row["attempts"]),
        max_attempts=int(row["max_attempts"]),
        scheduled_at=row["scheduled_at"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )
def _extract_publication_at(command_payload: dict[str, Any]) -> str | None:
    retention = command_payload.get("retention")
    if isinstance(retention, dict):
        publication_at = retention.get("publication_at")
        if isinstance(publication_at, str) and publication_at:
            return publication_at
    return None


def _extract_storage_path(command_payload: dict[str, Any]) -> str | None:
    retention = command_payload.get("retention")
    if isinstance(retention, dict):
        storage_path = retention.get("storage_path")
        if isinstance(storage_path, str) and storage_path:
            return storage_path
    return None


def _select_retention_sort_at(command_payload: dict[str, Any], finished_at: str) -> str:
    publication_at = _extract_publication_at(command_payload)
    if publication_at:
        return publication_at
    return finished_at


def _select_retention_criterion(command_payload: dict[str, Any]) -> str:
    if _extract_publication_at(command_payload):
        return "publication_at"
    return "fallback_finished_at"
