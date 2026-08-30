"""Versioned, recoverable migrations for the local Workspace case store."""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from aios_habit.workspace_case_models import CaseActivity


CURRENT_SCHEMA_VERSION = 2
FaultInjector = Callable[[str, int], None]


class WorkspaceCaseMigrationError(RuntimeError):
    """Safe migration error that never includes a system path."""


@dataclass(frozen=True)
class MigrationResult:
    from_version: int
    to_version: int
    migrated: bool
    backup_path: Optional[Path] = None


_MIGRATION_DESCRIPTIONS = {
    1: "gate1_cases_evidence_audit",
    2: "case_lifecycle_authorization_activity",
}
_MIGRATION_CHECKSUMS = {
    version: hashlib.sha256(description.encode("utf-8")).hexdigest()
    for version, description in _MIGRATION_DESCRIPTIONS.items()
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _call_fault(fault_injector: Optional[FaultInjector], stage: str, version: int) -> None:
    if fault_injector is not None:
        fault_injector(stage, version)


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _quick_check(connection: sqlite3.Connection) -> None:
    result = connection.execute("PRAGMA quick_check").fetchone()
    if result is None or str(result[0]).lower() != "ok":
        raise WorkspaceCaseMigrationError("CASE_STORE_INTEGRITY_FAILED")


def _infer_version(connection: sqlite3.Connection) -> int:
    declared = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if declared > CURRENT_SCHEMA_VERSION:
        raise WorkspaceCaseMigrationError("UNSUPPORTED_SCHEMA_VERSION")
    if declared == 0 and _table_exists(connection, "cases"):
        required = {"cases", "case_evidence_references", "case_audit_events"}
        if not all(_table_exists(connection, table) for table in required):
            raise WorkspaceCaseMigrationError("CASE_SCHEMA_INCONSISTENT")
        return 1
    return declared


def _verify_migration_history(connection: sqlite3.Connection, version: int) -> None:
    if not _table_exists(connection, "schema_migrations"):
        if version >= 2:
            raise WorkspaceCaseMigrationError("CASE_SCHEMA_INCONSISTENT")
        return
    rows = connection.execute(
        "SELECT version, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    for applied_version, checksum in rows:
        expected = _MIGRATION_CHECKSUMS.get(int(applied_version))
        if expected is None or checksum != expected:
            raise WorkspaceCaseMigrationError("MIGRATION_CHECKSUM_MISMATCH")
    if version >= 2 and {int(row[0]) for row in rows} != set(range(1, version + 1)):
        raise WorkspaceCaseMigrationError("CASE_SCHEMA_INCONSISTENT")


def _backup_database(source: Path, destination: Path) -> None:
    if destination.exists():
        destination.unlink()
    with closing(sqlite3.connect(source)) as source_connection, closing(sqlite3.connect(destination)) as backup_connection:
        source_connection.backup(backup_connection)
        _quick_check(backup_connection)


def _cleanup_sidecars(database_path: Path) -> None:
    for suffix in ("-wal", "-shm"):
        sidecar = database_path.with_name(f"{database_path.name}{suffix}")
        if sidecar.exists():
            sidecar.unlink()


def _restore_database(database_path: Path, backup_path: Optional[Path], existed_before: bool) -> None:
    _cleanup_sidecars(database_path)
    if backup_path is not None and backup_path.exists():
        shutil.copy2(backup_path, database_path)
    elif not existed_before and database_path.exists():
        database_path.unlink()
    _cleanup_sidecars(database_path)


def _apply_v1(connection: sqlite3.Connection) -> None:
    statements = (
        """
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            assistant_message_id TEXT NOT NULL,
            trace_id TEXT NOT NULL,
            evidence_digest TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        )
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS cases_trace_identity_unique
        ON cases (conversation_id, assistant_message_id, trace_id)
        """,
        """
        CREATE TABLE IF NOT EXISTS case_evidence_references (
            reference_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            trace_id TEXT NOT NULL,
            evidence_node_id TEXT NOT NULL,
            citation_id TEXT NOT NULL,
            source_locator TEXT NOT NULL,
            source_title TEXT NOT NULL,
            reference_digest TEXT NOT NULL,
            provenance_status TEXT NOT NULL,
            privacy_label TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS case_audit_events (
            event_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            event_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
    )
    for statement in statements:
        connection.execute(statement)


def _add_column(connection: sqlite3.Connection, table: str, definition: str) -> None:
    column = definition.split()[0]
    if column not in _column_names(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def _apply_v2(connection: sqlite3.Connection) -> None:
    for definition in (
        "case_type TEXT NOT NULL DEFAULT 'investigation'",
        "priority TEXT NOT NULL DEFAULT 'normal'",
        "owner_id TEXT NOT NULL DEFAULT 'local_admin'",
        "assignee_id TEXT",
        "scope TEXT NOT NULL DEFAULT 'general'",
        "version INTEGER NOT NULL DEFAULT 1",
        "updated_at TEXT NOT NULL DEFAULT ''",
        "activity_head_digest TEXT NOT NULL DEFAULT ''",
    ):
        _add_column(connection, "cases", definition)
    connection.execute("UPDATE cases SET updated_at = created_at WHERE updated_at = ''")
    statements = (
        """
        CREATE TABLE IF NOT EXISTS case_activities (
            event_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            event_type TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            previous_event_digest TEXT NOT NULL,
            event_digest TEXT NOT NULL UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS case_checklist_items (
            item_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            resolved_by TEXT,
            resolved_at TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS role_grants (
            grant_id TEXT PRIMARY KEY,
            actor_id TEXT NOT NULL,
            role TEXT NOT NULL,
            scope TEXT NOT NULL,
            valid_from TEXT NOT NULL,
            valid_until TEXT NOT NULL,
            revoked_at TEXT
        )
        """,
        "CREATE INDEX IF NOT EXISTS role_grants_actor_idx ON role_grants(actor_id)",
        """
        INSERT OR IGNORE INTO role_grants VALUES (
            'LOCAL-ADMIN-INVESTIGATOR', 'local_admin', 'investigator', 'general',
            '2000-01-01T00:00:00+00:00', '9999-12-31T23:59:59+00:00', NULL
        )
        """,
        """
        INSERT OR IGNORE INTO role_grants VALUES (
            'LOCAL-ADMIN-EXPERT', 'local_admin', 'expert', 'general',
            '2000-01-01T00:00:00+00:00', '9999-12-31T23:59:59+00:00', NULL
        )
        """,
        """
        INSERT OR IGNORE INTO role_grants VALUES (
            'LOCAL-ADMIN-ADMIN', 'local_admin', 'admin', 'general',
            '2000-01-01T00:00:00+00:00', '9999-12-31T23:59:59+00:00', NULL
        )
        """,
    )
    for statement in statements:
        connection.execute(statement)
    legacy_rows = connection.execute(
        """
        SELECT a.event_id, a.case_id, a.event_type, a.created_at,
               c.created_by, c.evidence_digest
        FROM case_audit_events a JOIN cases c ON c.case_id = a.case_id
        WHERE NOT EXISTS (SELECT 1 FROM case_activities x WHERE x.event_id = a.event_id)
        ORDER BY a.created_at, a.event_id
        """
    ).fetchall()
    for event_id, case_id, event_type, created_at, actor_id, payload_digest in legacy_rows:
        head = connection.execute(
            "SELECT activity_head_digest FROM cases WHERE case_id = ?", (case_id,)
        ).fetchone()[0]
        activity = CaseActivity.new(
            event_id=event_id,
            case_id=case_id,
            event_type=event_type,
            actor_id=actor_id,
            occurred_at=created_at,
            payload_digest=payload_digest,
            previous_event_digest=head,
        )
        connection.execute(
            "INSERT INTO case_activities VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            tuple(activity.__dict__.values()),
        )
        connection.execute(
            "UPDATE cases SET activity_head_digest = ? WHERE case_id = ?",
            (activity.event_digest, case_id),
        )


def _ensure_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def migrate_store(
    database_path: Path,
    target_version: int = CURRENT_SCHEMA_VERSION,
    *,
    fault_injector: Optional[FaultInjector] = None,
) -> MigrationResult:
    path = Path(database_path)
    if target_version < 0 or target_version > CURRENT_SCHEMA_VERSION:
        raise WorkspaceCaseMigrationError("UNSUPPORTED_SCHEMA_VERSION")
    path.parent.mkdir(parents=True, exist_ok=True)
    existed_before = path.exists()
    backup_path: Optional[Path] = None
    from_version: Optional[int] = None
    needs_history_bootstrap = False
    try:
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            _quick_check(connection)
            from_version = _infer_version(connection)
            _verify_migration_history(connection, from_version)
            if target_version < from_version:
                raise WorkspaceCaseMigrationError("SCHEMA_DOWNGRADE_NOT_ALLOWED")
            needs_history_bootstrap = from_version == 1 and not _table_exists(connection, "schema_migrations")
            if target_version == from_version and not needs_history_bootstrap:
                connection.rollback()
                return MigrationResult(from_version, target_version, False)

            if existed_before:
                backup_path = path.with_name(f"{path.stem}.backup-v{from_version}-to-v{target_version}.sqlite")
                _call_fault(fault_injector, "before_backup", from_version)
                _backup_database(path, backup_path)
                _call_fault(fault_injector, "after_backup", from_version)

            _ensure_migration_table(connection)
            if from_version == 1:
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations VALUES (?, ?, ?, ?)",
                    (1, _MIGRATION_DESCRIPTIONS[1], _MIGRATION_CHECKSUMS[1], _utc_now()),
                )
            for version in range(from_version + 1, target_version + 1):
                _call_fault(fault_injector, "before_migration", version)
                if version == 1:
                    _apply_v1(connection)
                elif version == 2:
                    _apply_v2(connection)
                connection.execute(
                    "INSERT INTO schema_migrations VALUES (?, ?, ?, ?)",
                    (version, _MIGRATION_DESCRIPTIONS[version], _MIGRATION_CHECKSUMS[version], _utc_now()),
                )
                connection.execute(f"PRAGMA user_version = {version}")
                _call_fault(fault_injector, "after_migration", version)
            if from_version == target_version == 1:
                connection.execute("PRAGMA user_version = 1")
            _quick_check(connection)
            connection.commit()
            _call_fault(fault_injector, "after_commit", target_version)
            _quick_check(connection)
        return MigrationResult(from_version, target_version, True, backup_path)
    except WorkspaceCaseMigrationError:
        if from_version is not None and (target_version != from_version or needs_history_bootstrap):
            _restore_database(path, backup_path, existed_before)
        raise
    except Exception as error:
        _restore_database(path, backup_path, existed_before)
        raise WorkspaceCaseMigrationError("MIGRATION_FAILED") from error
