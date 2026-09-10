from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
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
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = 3").fetchone()[0] == 1


def test_migrate_v2_to_v3_creates_expert_tables_and_preserves_data(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    # First migrate to v2
    migrate_store(path, target_version=2)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        connection.execute(
            """
            INSERT INTO cases (case_id, conversation_id, assistant_message_id, trace_id, evidence_digest, title, status, created_at, created_by, updated_at)
            VALUES ('CASE-V2', 'CONV-V2', 'MSG-V2', 'TRC-V2', 'DIG-V2', 'Case V2 Title', 'in_progress', '2026-09-01T00:00:00+00:00', 'local_admin', '2026-09-01T00:00:00+00:00')
            """
        )
        connection.commit()

    # Migrate to v3
    result = migrate_store(path, target_version=3)
    assert result.from_version == 2
    assert result.to_version == 3
    assert result.migrated is True
    assert result.backup_path is not None and result.backup_path.exists()

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        # Check v2 data preserved
        row = connection.execute("SELECT title, status FROM cases WHERE case_id = 'CASE-V2'").fetchone()
        assert row[0] == "Case V2 Title"
        assert row[1] == "in_progress"
        # Check expert tables exist
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "expert_requests" in tables
        assert "expert_reviews" in tables


def test_migration_v3_fault_restores_v2_snapshot(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path, target_version=2)

    def fail(stage: str, version: int) -> None:
        if stage == "after_migration" and version == 3:
            raise RuntimeError("v3 migration synthetic fault")

    with pytest.raises(WorkspaceCaseMigrationError, match="MIGRATION_FAILED"):
        migrate_store(path, target_version=3, fault_injector=fail)

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"


def test_migrate_v3_to_v4_creates_lesson_tables_and_preserves_data(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    # First migrate to v3
    migrate_store(path, target_version=3)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        connection.execute(
            """
            INSERT INTO cases (case_id, conversation_id, assistant_message_id, trace_id, evidence_digest, title, status, created_at, created_by, updated_at)
            VALUES ('CASE-V3', 'CONV-V3', 'MSG-V3', 'TRC-V3', 'DIG-V3', 'Case V3 Title', 'in_progress', '2026-09-02T00:00:00+00:00', 'local_admin', '2026-09-02T00:00:00+00:00')
            """
        )
        connection.commit()

    # Migrate to v4
    result = migrate_store(path, target_version=4)
    assert result.from_version == 3
    assert result.to_version == 4
    assert result.migrated is True
    assert result.backup_path is not None and result.backup_path.exists()

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        # Check v3 data preserved
        row = connection.execute("SELECT title, status FROM cases WHERE case_id = 'CASE-V3'").fetchone()
        assert row[0] == "Case V3 Title"
        assert row[1] == "in_progress"
        # Check lesson table exists
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "case_lessons" in tables
        # Check quality manager role grant exists
        grants = {r[0] for r in connection.execute("SELECT role FROM role_grants WHERE actor_id='local_admin'")}
        assert "quality_manager" in grants


def test_migration_v4_fault_restores_v3_snapshot(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path, target_version=3)

    def fail(stage: str, version: int) -> None:
        if stage == "after_migration" and version == 4:
            raise RuntimeError("v4 migration synthetic fault")

    with pytest.raises(WorkspaceCaseMigrationError, match="MIGRATION_FAILED"):
        migrate_store(path, target_version=4, fault_injector=fail)

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"


def test_migrate_v4_to_v5_creates_artifact_tables_and_preserves_data(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path, target_version=4)

    # Insert a case and lesson in v4
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO cases (case_id, conversation_id, assistant_message_id, trace_id, evidence_digest, title, status, created_at, created_by, updated_at)
            VALUES ('CASE-V4', 'CONV-1', 'MSG-1', 'TR-1', 'DIG-1', 'Case V4 Title', 'in_progress', '2026-09-06T00:00:00Z', 'local_admin', '2026-09-06T00:00:00Z')
            """
        )
        connection.commit()

    # Migrate to v5
    result = migrate_store(path, target_version=5)
    assert result.from_version == 4
    assert result.to_version == 5
    assert result.migrated is True
    assert result.backup_path is not None and result.backup_path.exists()

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        # Check v4 data preserved
        row = connection.execute("SELECT title, status FROM cases WHERE case_id = 'CASE-V4'").fetchone()
        assert row[0] == "Case V4 Title"
        assert row[1] == "in_progress"
        # Check artifact table exists
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "case_artifacts" in tables


def test_migration_v5_fault_restores_v4_snapshot(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path, target_version=4)

    def fail(stage: str, version: int) -> None:
        if stage == "after_migration" and version == 5:
            raise RuntimeError("v5 migration synthetic fault")

    with pytest.raises(WorkspaceCaseMigrationError, match="MIGRATION_FAILED"):
        migrate_store(path, target_version=5, fault_injector=fail)

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"


def test_migrate_v5_to_v6_creates_expert_tables_and_preserves_data(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path, target_version=5)

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO cases (case_id, conversation_id, assistant_message_id, trace_id, evidence_digest, title, status, created_at, created_by, updated_at)
            VALUES ('CASE-V5', 'CONV-5', 'MSG-5', 'TR-5', 'DIG-5', 'Case V5 Title', 'in_progress', '2026-09-08T00:00:00Z', 'local_admin', '2026-09-08T00:00:00Z')
            """
        )
        connection.commit()

    # Migrate to v6
    result = migrate_store(path, target_version=6)
    assert result.migrated is True
    assert result.to_version == 6

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 6
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        # Check v5 data preserved
        row = connection.execute("SELECT title, status FROM cases WHERE case_id = 'CASE-V5'").fetchone()
        assert row[0] == "Case V5 Title"
        assert row[1] == "in_progress"
        # Check expert tables exist
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "expert_profiles" in tables
        assert "expert_scope_grants" in tables


def test_migration_v6_fault_restores_v5_snapshot(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path, target_version=5)

    def fail(stage: str, version: int) -> None:
        if stage == "after_migration" and version == 6:
            raise RuntimeError("v6 migration synthetic fault")

    with pytest.raises(WorkspaceCaseMigrationError, match="MIGRATION_FAILED"):
        migrate_store(path, target_version=6, fault_injector=fail)

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"


def test_migrate_v6_to_v7_creates_gap_tables_and_preserves_data(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path, target_version=6)

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO cases (case_id, conversation_id, assistant_message_id, trace_id, evidence_digest, title, status, created_at, created_by, updated_at)
            VALUES ('CASE-V6', 'CONV-6', 'MSG-6', 'TR-6', 'DIG-6', 'Case V6 Title', 'in_progress', '2026-09-08T00:00:00Z', 'local_admin', '2026-09-08T00:00:00Z')
            """
        )
        connection.execute(
            """
            INSERT INTO expert_profiles (expert_id, subject, full_name, scopes_json, status, created_at, updated_at)
            VALUES ('EXP-6', 'SUBJ-6', 'Chuyên gia V6', '["lsu_optical_assembly"]', 'active', '2026-09-08T00:00:00Z', '2026-09-08T00:00:00Z')
            """
        )
        connection.commit()

    # Migrate to v7
    result = migrate_store(path, target_version=7)
    assert result.migrated is True
    assert result.to_version == 7

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 7
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        # Check v6 data preserved
        row = connection.execute("SELECT title, status FROM cases WHERE case_id = 'CASE-V6'").fetchone()
        assert row[0] == "Case V6 Title"
        assert row[1] == "in_progress"
        exp_row = connection.execute("SELECT full_name FROM expert_profiles WHERE expert_id = 'EXP-6'").fetchone()
        assert exp_row[0] == "Chuyên gia V6"
        # Check gap and coverage tables exist
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "knowledge_gap_events" in tables
        assert "coverage_runs" in tables


def test_migration_v7_fault_restores_v6_snapshot(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path, target_version=6)

    def fail(stage: str, version: int) -> None:
        if stage == "after_migration" and version == 7:
            raise RuntimeError("v7 migration synthetic fault")

    with pytest.raises(WorkspaceCaseMigrationError, match="MIGRATION_FAILED"):
        migrate_store(path, target_version=7, fault_injector=fail)

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 6
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"


def test_migrate_v7_to_v8_creates_transcript_columns_and_preserves_data(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path, target_version=7)

    # Migrate to v8
    result = migrate_store(path, target_version=8)
    assert result.migrated is True
    assert result.to_version == 8

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 8
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "interview_transcripts" in tables
        columns = {str(r[1]) for r in connection.execute("PRAGMA table_info(interview_transcripts)")}
        assert "transcript_locator" in columns
        assert "transcript_digest" in columns


def test_migration_v8_fault_restores_v7_snapshot(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path, target_version=7)

    def fail(stage: str, version: int) -> None:
        if stage == "after_migration" and version == 8:
            raise RuntimeError("v8 migration synthetic fault")

    with pytest.raises(WorkspaceCaseMigrationError, match="MIGRATION_FAILED"):
        migrate_store(path, target_version=8, fault_injector=fail)

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 7
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"


def test_migrate_v7_to_v8_migrates_legacy_transcripts_to_local_only(tmp_path):
    import json
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path, target_version=7)

    # Insert a table and row simulating legacy transcript in v7 store
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS interview_transcripts (
                receipt_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                audio_path TEXT NOT NULL,
                audio_digest TEXT NOT NULL,
                engine_name TEXT NOT NULL,
                engine_version TEXT NOT NULL,
                segments_json TEXT NOT NULL DEFAULT '',
                full_text TEXT NOT NULL DEFAULT '',
                all_critical_tokens_json TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE
            )
            """
        )
        legacy_segments = json.dumps([{"segment_id": "SEG-LEGACY-1", "text": "Đoạn chép cũ bí mật", "start_time": 0.0, "end_time": 1.0}])
        legacy_full_text = "Đoạn chép cũ bí mật cần được di chuyển ra ngoài SQLite"
        connection.execute(
            """
            INSERT INTO interview_transcripts (
                receipt_id, session_id, audio_path, audio_digest,
                engine_name, engine_version, segments_json, full_text,
                all_critical_tokens_json, state, created_at, idempotency_key
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "RCP-LEGACY-1",
                "SESS-LEGACY-1",
                "local_cases/audio.wav",
                "dig_legacy",
                "mock",
                "1.0",
                legacy_segments,
                legacy_full_text,
                "[]",
                "draft",
                "2026-09-08T00:00:00Z",
                "IDEMP-LEGACY-1",
            ),
        )
        connection.commit()

    # Migrate to v8
    result = migrate_store(path, target_version=8)
    assert result.migrated is True
    assert result.to_version == 8

    # Verify that in SQLite, raw text has been purged and locator/digest populated
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT * FROM interview_transcripts WHERE receipt_id = 'RCP-LEGACY-1'").fetchone()
        assert row is not None
        assert row["segments_json"] == "", "Legacy segments_json must be cleared in SQLite"
        assert row["full_text"] == "", "Legacy full_text must be cleared in SQLite"
        assert row["transcript_locator"] != "", "transcript_locator must be populated"
        assert row["transcript_digest"] != "", "transcript_digest must be populated"

        # Verify the file on disk in local_only/transcripts
        target_file = Path(row["transcript_locator"])
        assert target_file.exists()
        file_data = json.loads(target_file.read_text(encoding="utf-8"))
        assert file_data["full_text"] == legacy_full_text
        assert len(file_data["segments"]) == 1
        assert file_data["segments"][0]["text"] == "Đoạn chép cũ bí mật"


def test_migrate_v7_to_v8_sanitizes_transcript_filename(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path, target_version=7)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE interview_transcripts (
                receipt_id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
                audio_path TEXT NOT NULL, audio_digest TEXT NOT NULL,
                engine_name TEXT NOT NULL, engine_version TEXT NOT NULL,
                segments_json TEXT NOT NULL DEFAULT '', full_text TEXT NOT NULL DEFAULT '',
                all_critical_tokens_json TEXT NOT NULL, state TEXT NOT NULL,
                created_at TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE
            )
            """
        )
        connection.execute(
            """
            INSERT INTO interview_transcripts VALUES
            ('../../RCP:unsafe', '..\\SESS/unsafe', 'local_cases/audio.wav', 'digest',
             'manual', '1', '[]', 'Nội dung cũ', '[]', 'draft',
             '2026-09-08T00:00:00Z', 'IDEMP-UNSAFE')
            """
        )
        connection.commit()

    migrate_store(path, target_version=8)

    with sqlite3.connect(path) as connection:
        locator = Path(
            connection.execute(
                "SELECT transcript_locator FROM interview_transcripts WHERE receipt_id = '../../RCP:unsafe'"
            ).fetchone()[0]
        )
    transcripts_dir = (tmp_path / "local_only" / "transcripts").resolve()
    assert locator.resolve().parent == transcripts_dir
    assert ".." not in locator.name
    assert "/" not in locator.name and "\\" not in locator.name


def test_migration_v8_rollback_removes_new_transcript_files(tmp_path):
    path = tmp_path / "workspace_cases.sqlite"
    migrate_store(path, target_version=7)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE interview_transcripts (
                receipt_id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
                audio_path TEXT NOT NULL, audio_digest TEXT NOT NULL,
                engine_name TEXT NOT NULL, engine_version TEXT NOT NULL,
                segments_json TEXT NOT NULL DEFAULT '', full_text TEXT NOT NULL DEFAULT '',
                all_critical_tokens_json TEXT NOT NULL, state TEXT NOT NULL,
                created_at TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE
            )
            """
        )
        connection.execute(
            """
            INSERT INTO interview_transcripts VALUES
            ('RCP-ROLLBACK', 'SESS-ROLLBACK', 'local_cases/audio.wav', 'digest',
             'manual', '1', '[]', 'Không được để lại tệp mồ côi', '[]', 'draft',
             '2026-09-08T00:00:00Z', 'IDEMP-ROLLBACK')
            """
        )
        connection.commit()

    def fail(stage: str, version: int) -> None:
        if stage == "after_migration" and version == 8:
            raise RuntimeError("v8 migration synthetic fault")

    with pytest.raises(WorkspaceCaseMigrationError, match="MIGRATION_FAILED"):
        migrate_store(path, target_version=8, fault_injector=fail)

    transcripts_dir = tmp_path / "local_only" / "transcripts"
    assert not list(transcripts_dir.glob("*.json"))


def test_migrate_v7_to_v8_migrates_legacy_transcripts_on_memory_db():
    import json
    from aios_habit.workspace_case_migrations import _apply_v8

    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE interview_transcripts (
            receipt_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            audio_path TEXT NOT NULL,
            audio_digest TEXT NOT NULL,
            engine_name TEXT NOT NULL,
            engine_version TEXT NOT NULL,
            segments_json TEXT NOT NULL DEFAULT '',
            full_text TEXT NOT NULL DEFAULT '',
            all_critical_tokens_json TEXT NOT NULL,
            state TEXT NOT NULL,
            created_at TEXT NOT NULL,
            idempotency_key TEXT NOT NULL UNIQUE
        )
        """
    )
    legacy_segments = json.dumps([{"segment_id": "SEG-MEM-1", "text": "Bộ nhớ tạm", "start_time": 0.0, "end_time": 1.0}])
    legacy_full_text = "Nội dung bí mật trong bộ nhớ tạm"
    conn.execute(
        """
        INSERT INTO interview_transcripts (
            receipt_id, session_id, audio_path, audio_digest,
            engine_name, engine_version, segments_json, full_text,
            all_critical_tokens_json, state, created_at, idempotency_key
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "RCP-MEM-1", "SESS-MEM-1", "local_cases/audio.wav", "dig_mem",
            "mock", "1.0", legacy_segments, legacy_full_text, "[]", "draft",
            "2026-09-08T00:00:00Z", "IDEMP-MEM-1",
        ),
    )
    conn.commit()

    _apply_v8(conn)

    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM interview_transcripts WHERE receipt_id = 'RCP-MEM-1'").fetchone()
    assert row is not None
    assert row["segments_json"] == ""
    assert row["full_text"] == ""
    assert row["transcript_locator"] != ""
    assert row["transcript_digest"] != ""
    target_file = Path(row["transcript_locator"])
    assert target_file.exists()
    conn.close()
