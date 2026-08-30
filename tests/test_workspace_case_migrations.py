from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from aios_habit.workspace_case_migrations import (
    CURRENT_SCHEMA_VERSION,
    WorkspaceCaseMigrationError,
    migrate_store,
)


def _create_legacy_gate1_database(path):
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE cases (
                case_id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,
                assistant_message_id TEXT NOT NULL, trace_id TEXT NOT NULL,
                evidence_digest TEXT NOT NULL, title TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL, created_by TEXT NOT NULL
            );
            CREATE TABLE case_evidence_references (
                reference_id TEXT PRIMARY KEY, case_id TEXT NOT NULL,
                trace_id TEXT NOT NULL, evidence_node_id TEXT NOT NULL,
                citation_id TEXT NOT NULL, source_locator TEXT NOT NULL,
                source_title TEXT NOT NULL, reference_digest TEXT NOT NULL,
                provenance_status TEXT NOT NULL, privacy_label TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE case_audit_events (
                event_id TEXT PRIMARY KEY, case_id TEXT NOT NULL,
                event_type TEXT NOT NULL, created_at TEXT NOT NULL
            );
            INSERT INTO cases VALUES (
                'CASE-LEGACY', 'CONV-1', 'MSG-1', 'trace-1', 'digest-1',
                'Hồ sơ cũ', 'draft', '2026-08-30T00:00:00+00:00', 'Workspace Chat'
            );
            INSERT INTO case_evidence_references VALUES (
                'REF-LEGACY', 'CASE-LEGACY', 'trace-1', 'NODE-1', '[E1]',
                'docs/process.pdf', 'Quy trình', 'ref-digest-1', 'unknown',
                'local_only', '2026-08-30T00:00:00+00:00'
            );
            INSERT INTO case_audit_events VALUES (
                'AUDIT-LEGACY', 'CASE-LEGACY', 'case_created',
                '2026-08-30T00:00:00+00:00'
            );
            """
        )


def test_migrate_legacy_gate1_database_preserves_records_and_is_idempotent(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    _create_legacy_gate1_database(path)

    result = migrate_store(path)
    second = migrate_store(path)

    assert result.from_version == 1
    assert result.to_version == CURRENT_SCHEMA_VERSION
    assert result.backup_path is not None and result.backup_path.exists()
    assert second.migrated is False
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == CURRENT_SCHEMA_VERSION
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT evidence_digest FROM cases").fetchone()[0] == "digest-1"
        assert connection.execute("SELECT reference_digest FROM case_evidence_references").fetchone()[0] == "ref-digest-1"
        assert connection.execute("SELECT COUNT(*) FROM case_activities").fetchone()[0] == 1


def test_migration_fault_restores_legacy_snapshot(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    _create_legacy_gate1_database(path)

    def fail(stage: str, version: int) -> None:
        if stage == "after_migration" and version == CURRENT_SCHEMA_VERSION:
            raise RuntimeError("synthetic fault")

    with pytest.raises(WorkspaceCaseMigrationError, match="MIGRATION_FAILED"):
        migrate_store(path, fault_injector=fail)

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert connection.execute("SELECT case_id FROM cases").fetchone()[0] == "CASE-LEGACY"
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    assert not path.with_name(f"{path.name}-wal").exists()
    assert not path.with_name(f"{path.name}-shm").exists()


def test_migration_rejects_unknown_future_version_without_exposing_path(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION + 10}")

    with pytest.raises(WorkspaceCaseMigrationError, match="UNSUPPORTED_SCHEMA_VERSION") as caught:
        migrate_store(path)

    assert str(path) not in str(caught.value)


def test_migration_rejects_checksum_mismatch(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path)
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE schema_migrations SET checksum = 'tampered' WHERE version = 2")
        connection.commit()

    with pytest.raises(WorkspaceCaseMigrationError, match="MIGRATION_CHECKSUM_MISMATCH"):
        migrate_store(path)


def test_concurrent_migration_rechecks_version_under_write_lock(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    _create_legacy_gate1_database(path)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: migrate_store(path), range(2)))

    assert sum(result.migrated for result in results) == 1
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == CURRENT_SCHEMA_VERSION
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = 2").fetchone()[0] == 1
