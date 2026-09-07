"""Library backup, integrity verification, and safe restoration for shared library.

Adheres to specs/008-evidence-case-loop/spec.md (US11) and
specs/008-evidence-case-loop/tasks.md (T054, T055).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aios_habit.workspace_chat_store import (
    COLLECTION_INDEX_BASENAME,
    COLLECTION_RUNTIME_DIRNAME,
    DEFAULT_COLLECTION_ID,
    LibraryWriterLease,
    _backup_sqlite,
    collection_runtime_layout,
    load_collection,
    sqlite_quick_check,
)


@dataclass
class LibraryBackupManifest:
    backup_id: str
    collection_id: str
    created_at: str
    created_by: str
    storage_root: str
    files: Dict[str, str]  # filename -> sha256
    total_bytes: int
    note: str = ""
    manifest_digest: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _is_forbidden_backup_file(filename: str) -> bool:
    """Ensure sensitive secrets or unrelated databases are strictly excluded."""
    lowered = filename.lower()
    if lowered.startswith(".env") or "token" in lowered or "secret" in lowered or ".key" in lowered:
        return True
    if lowered.endswith(".sqlite") and lowered != COLLECTION_INDEX_BASENAME.lower():
        return True
    return False


def create_library_backup(
    collection_id: str = DEFAULT_COLLECTION_ID,
    *,
    backup_root: Optional[Path] = None,
    note: str = "",
    actor: str = "local_admin",
    local_fallback_root: Optional[Path] = None,
) -> Tuple[Path, LibraryBackupManifest]:
    """
    Creates a verified, point-in-time backup of the specified collection.
    Backs up library.sqlite using sqlite backup API and computes SHA-256 checksums.
    Strictly forbids including secrets or non-library databases.
    """
    if local_fallback_root is None:
        local_fallback_root = Path("local_cases/workspace_chat")
    if backup_root is None:
        backup_root = Path("local_cases/library_backups")

    runtime_dir, _ = collection_runtime_layout(collection_id, local_fallback_root)
    source_sqlite = runtime_dir / COLLECTION_INDEX_BASENAME
    if not source_sqlite.exists():
        raise FileNotFoundError(
            f"Không tìm thấy tệp dữ liệu thư viện tại: {source_sqlite}. Vui lòng tạo thư viện trước khi sao lưu."
        )

    # Acquire writer lease to ensure quiet state during snapshot initiation
    lease = LibraryWriterLease(runtime_dir)
    if not lease.acquire(owner=actor):
        raise ValueError(LibraryWriterLease.format_busy_message(runtime_dir))

    backup_id = f"BAK-{uuid.uuid4().hex[:10].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()
    dest_dir = backup_root / f"backup_{collection_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{backup_id}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        dest_sqlite = dest_dir / COLLECTION_INDEX_BASENAME
        _backup_sqlite(source_sqlite, dest_sqlite)

        # Integrity verification on backup copy
        if not sqlite_quick_check(dest_sqlite):
            shutil.rmtree(dest_dir, ignore_errors=True)
            raise ValueError("Bản sao lưu cơ sở dữ liệu không vượt qua kiểm tra toàn vẹn (PRAGMA quick_check).")

        files_map: Dict[str, str] = {
            COLLECTION_INDEX_BASENAME: _compute_file_sha256(dest_sqlite),
        }
        total_size = dest_sqlite.stat().st_size

        # Backup collection metadata if available
        collection = load_collection(collection_id)
        if collection:
            meta_path = dest_dir / "collection.json"
            meta_json = json.dumps(asdict(collection), indent=2, ensure_ascii=False)
            meta_path.write_text(meta_json, encoding="utf-8")
            files_map["collection.json"] = _compute_file_sha256(meta_path)
            total_size += meta_path.stat().st_size

        # Verify no forbidden files accidentally placed
        for fname in files_map:
            if _is_forbidden_backup_file(fname):
                shutil.rmtree(dest_dir, ignore_errors=True)
                raise ValueError(f"Phát hiện tệp cấm trong thư mục sao lưu: {fname}")

        # Build manifest
        manifest_core = {
            "backup_id": backup_id,
            "collection_id": collection_id,
            "created_at": now_iso,
            "created_by": actor,
            "storage_root": str(runtime_dir),
            "files": files_map,
            "total_bytes": total_size,
            "note": note.strip(),
        }
        encoded_core = json.dumps(manifest_core, sort_keys=True, ensure_ascii=False).encode("utf-8")
        manifest_digest = hashlib.sha256(encoded_core).hexdigest()

        manifest = LibraryBackupManifest(
            backup_id=backup_id,
            collection_id=collection_id,
            created_at=now_iso,
            created_by=actor,
            storage_root=str(runtime_dir),
            files=files_map,
            total_bytes=total_size,
            note=note.strip(),
            manifest_digest=manifest_digest,
        )

        manifest_file = dest_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return dest_dir, manifest
    finally:
        lease.release()


def verify_library_backup(backup_dir: Path) -> Tuple[bool, str]:
    """
    Verifies the integrity of a library backup:
    - manifest.json exists and digest matches.
    - All files listed in manifest exist and SHA-256 match.
    - library.sqlite passes SQLite quick_check.
    """
    p = Path(backup_dir)
    manifest_file = p / "manifest.json"
    if not manifest_file.exists():
        return False, "Không tìm thấy tệp thông tin sao lưu (manifest.json)."

    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        saved_digest = data.get("manifest_digest", "")
        core_dict = {
            "backup_id": data["backup_id"],
            "collection_id": data["collection_id"],
            "created_at": data["created_at"],
            "created_by": data["created_by"],
            "storage_root": data["storage_root"],
            "files": data["files"],
            "total_bytes": data["total_bytes"],
            "note": data.get("note", ""),
        }
        calc_digest = hashlib.sha256(
            json.dumps(core_dict, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

        if saved_digest != calc_digest:
            return False, "Mã kiểm tra toàn vẹn (manifest digest) không khớp với nội dung bản sao lưu."

        files_map = data.get("files", {})
        if COLLECTION_INDEX_BASENAME not in files_map:
            return False, f"Bản sao lưu thiếu tệp cơ sở dữ liệu chính ({COLLECTION_INDEX_BASENAME})."

        for fname, expected_hash in files_map.items():
            fpath = p / fname
            if not fpath.exists():
                return False, f"Thiếu tệp tin trong gói sao lưu: {fname}."
            actual_hash = _compute_file_sha256(fpath)
            if actual_hash != expected_hash:
                return False, f"Tệp tin {fname} bị sai biệt mã kiểm tra SHA-256 (dữ liệu có thể đã bị thay đổi)."

        sqlite_path = p / COLLECTION_INDEX_BASENAME
        if not sqlite_quick_check(sqlite_path):
            return False, "Cơ sở dữ liệu sao lưu không vượt qua kiểm tra toàn vẹn SQLite (quick_check lỗi)."

        return True, "Bản sao lưu hoàn toàn hợp lệ và toàn vẹn."
    except Exception as err:
        return False, f"Lỗi đọc thông tin bản sao lưu: {err}."


def restore_library_backup(
    backup_dir: Path,
    target_runtime_dir: Path,
    *,
    actor: str = "local_admin",
) -> bool:
    """
    Restores library from a verified backup into target runtime directory.
    Fails closed if backup integrity verification fails (target remains untouched).
    Acquires LibraryWriterLease on target directory during file replacement.
    """
    is_valid, reason = verify_library_backup(backup_dir)
    if not is_valid:
        raise ValueError(f"Không thể khôi phục vì bản sao lưu không hợp lệ: {reason}")

    target_path = Path(target_runtime_dir)
    target_path.mkdir(parents=True, exist_ok=True)

    lease = LibraryWriterLease(target_path)
    if not lease.acquire(owner=actor):
        raise ValueError(LibraryWriterLease.format_busy_message(target_path))

    staging_file = target_path / f".{COLLECTION_INDEX_BASENAME}.restore_{uuid.uuid4().hex}.tmp"
    final_file = target_path / COLLECTION_INDEX_BASENAME
    backup_sqlite = Path(backup_dir) / COLLECTION_INDEX_BASENAME

    try:
        _backup_sqlite(backup_sqlite, staging_file)
        if not sqlite_quick_check(staging_file):
            staging_file.unlink(missing_ok=True)
            raise ValueError("Kiểm tra toàn vẹn tệp khôi phục tạm thời thất bại.")

        # Atomic replace
        os.replace(staging_file, final_file)

        if not sqlite_quick_check(final_file):
            final_file.unlink(missing_ok=True)
            raise ValueError("Kiểm tra toàn vẹn tệp khôi phục chính thức thất bại.")

        return True
    finally:
        staging_file.unlink(missing_ok=True)
        lease.release()
