from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from aios_habit.library_backup import (
    LibraryBackupManifest,
    create_library_backup,
    restore_library_backup,
    verify_library_backup,
)
import aios_habit.workspace_chat_store as store
from aios_habit.workspace_chat_store import (
    COLLECTION_INDEX_BASENAME,
    COLLECTION_RUNTIME_DIRNAME,
    DEFAULT_COLLECTION_ID,
    LibraryWriterLease,
    collection_runtime_layout,
    ensure_default_collection,
    load_collection,
    relocate_collection_storage,
    sqlite_quick_check,
)


def _init_sample_library(runtime_dir: Path) -> Path:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    db_file = runtime_dir / COLLECTION_INDEX_BASENAME
    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS sample_chunks (id TEXT PRIMARY KEY, content TEXT);")
        conn.execute(
            "INSERT OR REPLACE INTO sample_chunks (id, content) VALUES ('C1', 'Nội dung quy chuẩn thử nghiệm.');"
        )
        conn.commit()
    return db_file


def test_storage_relocation_and_revert_local(tmp_path: Path):
    local_fallback = tmp_path / "local_chat"
    shared_root = tmp_path / "shared_company_drive" / "knowledge"

    ensure_default_collection()
    coll = load_collection(DEFAULT_COLLECTION_ID)
    assert coll is not None

    # Populate local library
    runtime_dir, _ = collection_runtime_layout(
        DEFAULT_COLLECTION_ID, local_fallback
    )
    _init_sample_library(runtime_dir)

    # Relocate to shared folder
    relocate_collection_storage(
        DEFAULT_COLLECTION_ID,
        str(shared_root),
        local_fallback_root=local_fallback,
    )
    updated_coll = load_collection(DEFAULT_COLLECTION_ID)
    assert updated_coll is not None
    assert updated_coll.storage_root == str(shared_root)

    dest_runtime, _ = collection_runtime_layout(
        DEFAULT_COLLECTION_ID, local_fallback
    )
    assert dest_runtime == shared_root / COLLECTION_RUNTIME_DIRNAME
    dest_sqlite = dest_runtime / COLLECTION_INDEX_BASENAME
    assert dest_sqlite.exists()
    assert sqlite_quick_check(dest_sqlite)

    # Verify private files were not moved to shared destination
    assert not (dest_runtime / "workspace_cases.sqlite").exists()
    assert not (dest_runtime / "line_events.sqlite").exists()

    # Revert back to local
    relocate_collection_storage(
        DEFAULT_COLLECTION_ID,
        "",
        local_fallback_root=local_fallback,
    )
    reverted_coll = load_collection(DEFAULT_COLLECTION_ID)
    assert reverted_coll is not None
    assert reverted_coll.storage_root == ""
    rev_runtime, _ = collection_runtime_layout(
        DEFAULT_COLLECTION_ID, local_fallback
    )
    assert rev_runtime == local_fallback / "collections" / DEFAULT_COLLECTION_ID


def test_library_writer_lease_concurrency_and_busy_message(tmp_path: Path):
    runtime_dir = tmp_path / "shared_dir"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    lease1 = LibraryWriterLease(runtime_dir)
    lease2 = LibraryWriterLease(runtime_dir)

    # Machine 1 acquires lock
    assert lease1.acquire(owner="machine_a") is True
    info1 = lease1.get_lease_info()
    assert info1 is not None
    assert info1["owner"] == "machine_a"

    # Machine 2 attempts to acquire lock -> must fail closed
    assert lease2.acquire(owner="machine_b") is False

    # Format polite Vietnamese busy explanation
    busy_msg = LibraryWriterLease.format_busy_message(runtime_dir)
    assert "machine_a" in busy_msg
    assert "Thư viện hiện đang được cập nhật bởi máy" in busy_msg
    assert "Vui lòng chờ máy trên hoàn tất" in busy_msg

    # Machine 1 releases lock
    lease1.release()

    # Machine 2 can now acquire lock
    assert lease2.acquire(owner="machine_b") is True
    info2 = lease2.get_lease_info()
    assert info2 is not None
    assert info2["owner"] == "machine_b"
    lease2.release()


def test_concurrent_readers_during_writer_lease(tmp_path: Path):
    runtime_dir = tmp_path / "runtime"
    db_file = _init_sample_library(runtime_dir)

    lease = LibraryWriterLease(runtime_dir)
    assert lease.acquire(owner="writer_process") is True

    # Concurrent reader opens database and queries
    with sqlite3.connect(f"file:{db_file}?mode=ro", uri=True) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM sample_chunks WHERE id = 'C1'")
        row = cursor.fetchone()
        assert row is not None
        assert "Nội dung quy chuẩn" in row[0]

    lease.release()


def test_create_and_verify_library_backup(tmp_path: Path):
    local_fallback = tmp_path / "local_chat"
    backup_root = tmp_path / "backups"

    ensure_default_collection()
    runtime_dir, _ = collection_runtime_layout(
        DEFAULT_COLLECTION_ID, local_fallback
    )
    _init_sample_library(runtime_dir)

    # Create backup
    backup_dir, manifest = create_library_backup(
        collection_id=DEFAULT_COLLECTION_ID,
        backup_root=backup_root,
        note="Bản sao lưu kiểm thử US11",
        actor="engineer_test",
        local_fallback_root=local_fallback,
    )

    assert backup_dir.exists()
    assert manifest.backup_id.startswith("BAK-")
    assert manifest.collection_id == DEFAULT_COLLECTION_ID
    assert manifest.created_by == "engineer_test"
    assert manifest.manifest_digest != ""
    assert COLLECTION_INDEX_BASENAME in manifest.files

    # Verify backup integrity
    ok, message = verify_library_backup(backup_dir)
    assert ok is True
    assert "toàn vẹn" in message


def test_verify_corrupted_backup_fails(tmp_path: Path):
    local_fallback = tmp_path / "local_chat"
    backup_root = tmp_path / "backups"

    ensure_default_collection()
    runtime_dir, _ = collection_runtime_layout(
        DEFAULT_COLLECTION_ID, local_fallback
    )
    _init_sample_library(runtime_dir)

    backup_dir, _ = create_library_backup(
        collection_id=DEFAULT_COLLECTION_ID,
        backup_root=backup_root,
        actor="engineer_test",
        local_fallback_root=local_fallback,
    )

    # Tamper with the sqlite file
    sqlite_file = backup_dir / COLLECTION_INDEX_BASENAME
    with open(sqlite_file, "ab") as f:
        f.write(b"CORRUPTED_BYTES")

    # Verification must detect hash mismatch
    ok, message = verify_library_backup(backup_dir)
    assert ok is False
    assert "sai biệt mã kiểm tra" in message or "quick_check" in message


def test_restore_library_backup_fail_closed_on_corrupted(tmp_path: Path):
    local_fallback = tmp_path / "local_chat"
    backup_root = tmp_path / "backups"
    target_runtime = tmp_path / "target_runtime"

    ensure_default_collection()
    runtime_dir, _ = collection_runtime_layout(
        DEFAULT_COLLECTION_ID, local_fallback
    )
    _init_sample_library(runtime_dir)

    # Create original target database
    _init_sample_library(target_runtime)

    backup_dir, _ = create_library_backup(
        collection_id=DEFAULT_COLLECTION_ID,
        backup_root=backup_root,
        local_fallback_root=local_fallback,
    )

    # Tamper with backup manifest
    manifest_file = backup_dir / "manifest.json"
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest_data["manifest_digest"] = "invalid_digest_12345"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    # Restore must fail closed, target runtime must remain intact
    with pytest.raises(ValueError) as exc_info:
        restore_library_backup(backup_dir, target_runtime)

    assert "Không thể khôi phục vì bản sao lưu không hợp lệ" in str(exc_info.value)
    # Check target database still intact
    target_sqlite = target_runtime / COLLECTION_INDEX_BASENAME
    assert target_sqlite.exists()
    assert sqlite_quick_check(target_sqlite)


def test_restore_library_backup_happy_path(tmp_path: Path):
    local_fallback = tmp_path / "local_chat"
    backup_root = tmp_path / "backups"
    target_runtime = tmp_path / "target_runtime"

    ensure_default_collection()
    runtime_dir, _ = collection_runtime_layout(
        DEFAULT_COLLECTION_ID, local_fallback
    )
    db_file = runtime_dir / COLLECTION_INDEX_BASENAME
    runtime_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS source_data (k TEXT, v TEXT);")
        conn.execute("INSERT OR REPLACE INTO source_data VALUES ('version', '2026.09.06');")
        conn.commit()

    backup_dir, manifest = create_library_backup(
        collection_id=DEFAULT_COLLECTION_ID,
        backup_root=backup_root,
        local_fallback_root=local_fallback,
    )

    # Restore to target runtime
    success = restore_library_backup(backup_dir, target_runtime)
    assert success is True

    restored_sqlite = target_runtime / COLLECTION_INDEX_BASENAME
    assert restored_sqlite.exists()
    assert sqlite_quick_check(restored_sqlite)

    with sqlite3.connect(restored_sqlite) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT v FROM source_data WHERE k = 'version'")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "2026.09.06"
