"""Controlled Knowledge Publication to Shared Knowledge Library.

Implements T060, T061, T062, T063, T064, T065 of Goal 010-expert-knowledge-acquisition.
Fail-closed invariants:
1. Only approved artifacts with verified digest can be sealed into a PublicationPackage.
2. Unapproved, conflicted, or revoked artifacts are strictly barred from publication.
3. Every publication must create a verified library backup and acquire LibraryWriterLease.
4. SQLite quick_check and retrieval acceptance tests must PASS before marking as published.
5. Ingestion failures or busy locks must leave library fully usable (atomic rollback).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from aios_habit.controlled_knowledge_artifact import (
    ARTIFACT_STATUS_APPROVED,
    ARTIFACT_STATUS_REVOKED,
    ControlledKnowledgeArtifact,
)
from aios_habit.library_backup import create_library_backup
from aios_habit.rag_ingest import RAGChunk
from aios_habit.rag_search import create_rag_search_schema, index_rag_chunks, search_rag_chunks
from aios_habit.workspace_chat_models import DEFAULT_COLLECTION_ID
from aios_habit.workspace_chat_store import (
    COLLECTION_INDEX_BASENAME,
    LibraryWriterLease,
    collection_runtime_layout,
    sqlite_quick_check,
)

# Package Statuses
PACKAGE_STATUS_SEALED = "sealed"
PACKAGE_STATUS_PUBLISHED = "published"
PACKAGE_STATUS_REVOKED = "revoked"
PACKAGE_STATUS_SUPERSEDED = "superseded"

VALID_PACKAGE_STATUSES = {
    PACKAGE_STATUS_SEALED,
    PACKAGE_STATUS_PUBLISHED,
    PACKAGE_STATUS_REVOKED,
    PACKAGE_STATUS_SUPERSEDED,
}


class PublicationError(Exception):
    """Base exception for knowledge publication."""
    pass


class UnapprovedArtifactPublicationError(PublicationError):
    """Raised when attempting to publish an unapproved, candidate, or rejected artifact."""
    pass


class StalePackageDigestError(PublicationError):
    """Raised when package digest does not match expected payload."""
    pass


class LibraryWriterBusyError(PublicationError):
    """Raised when LibraryWriterLease cannot be acquired because another writer is busy."""
    pass


class PublicationAcceptanceError(PublicationError):
    """Raised when SQLite quick_check or retrieval acceptance test fails."""
    pass


@dataclass(frozen=True)
class PublicationPackage:
    """Immutable, sealed publication bundle ready for ingest into knowledge library."""

    package_id: str
    artifact_id: str
    artifact_digest: str
    artifact_type: str
    title: str
    scope: str
    version: str
    content_markdown: str
    claim_ids: Tuple[str, ...]
    acceptance_questions: Tuple[str, ...]
    target_collection_id: str = DEFAULT_COLLECTION_ID
    sealed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sealed_by: str = ""
    status: str = PACKAGE_STATUS_SEALED

    def __post_init__(self) -> None:
        if not self.package_id.strip():
            raise ValueError("Mã gói xuất bản (package_id) không được để trống.")
        if not self.artifact_id.strip():
            raise ValueError("Mã tài liệu liên kết không được để trống.")
        if not self.artifact_digest.strip():
            raise ValueError("Mã băm tài liệu không được để trống.")
        if not self.title.strip():
            raise ValueError("Tiêu đề gói xuất bản không được để trống.")
        if not self.content_markdown.strip():
            raise ValueError("Nội dung gói xuất bản không được để trống.")
        if not self.acceptance_questions:
            raise ValueError("Gói xuất bản bắt buộc phải có ít nhất 1 câu hỏi kiểm tra nghiệm thu (acceptance_questions).")
        if self.status not in VALID_PACKAGE_STATUSES:
            raise ValueError(f"Trạng thái gói '{self.status}' không hợp lệ.")

    @property
    def package_digest(self) -> str:
        """Compute deterministic payload digest."""
        payload = f"{self.package_id}:{self.artifact_id}:{self.artifact_digest}:{self.version}:{self.target_collection_id}:{','.join(sorted(self.claim_ids))}:{','.join(self.acceptance_questions)}:{self.content_markdown}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PublicationReceipt:
    """Tamper-evident audit receipt of successful publication into knowledge library."""

    receipt_id: str
    package_id: str
    package_digest: str
    backup_id: str
    quick_check_status: str
    acceptance_results: Dict[str, bool]
    published_at: str
    published_by: str
    state: str = "published"
    rollback_manifest_digest: Optional[str] = None


def seal_publication_package(
    artifact: ControlledKnowledgeArtifact,
    acceptance_questions: Sequence[str],
    sealed_by: str,
    target_collection_id: str = DEFAULT_COLLECTION_ID,
) -> PublicationPackage:
    """Seal an approved artifact into an immutable PublicationPackage.

    Implements T060, T061.
    """
    if artifact.status != ARTIFACT_STATUS_APPROVED:
        raise UnapprovedArtifactPublicationError(
            f"Chỉ tài liệu đã được phê duyệt chính thức (approved) mới được phép niêm phong xuất bản. Trạng thái hiện tại: '{artifact.status}'."
        )

    matching_confirmations = [
        decision
        for decision in artifact.decisions
        if decision.decision == "confirm"
        and decision.subject_id == artifact.artifact_id
        and decision.subject_digest == artifact.digest
        and decision.subject_version == artifact.version
        and decision.responsibility_acknowledged
    ]
    if not matching_confirmations:
        raise UnapprovedArtifactPublicationError(
            f"Tài liệu '{artifact.artifact_id}' chưa có biên bản phê duyệt hợp lệ trong hệ thống."
        )

    if not acceptance_questions:
        raise ValueError("Phải cung cấp ít nhất một câu hỏi nghiệm thu truy xuất cho gói xuất bản.")

    package_id = f"PKG-{artifact.artifact_id}-V{artifact.version.replace('.', '_')}"

    return PublicationPackage(
        package_id=package_id,
        artifact_id=artifact.artifact_id,
        artifact_digest=artifact.digest,
        artifact_type=artifact.artifact_type,
        title=artifact.title,
        scope=artifact.scope,
        version=artifact.version,
        content_markdown=artifact.content_markdown,
        claim_ids=artifact.claim_ids,
        acceptance_questions=tuple(acceptance_questions),
        target_collection_id=target_collection_id,
        sealed_by=sealed_by,
        status=PACKAGE_STATUS_SEALED,
    )


class KnowledgePublisher:
    """Governs safe, verified ingestion of sealed PublicationPackages into shared library."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        backup_dir: Optional[Path] = None,
        interview_repo: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        self.base_dir = Path(base_dir or Path.cwd() / "local_cases" / "workspace_chat")
        self.backup_dir = Path(backup_dir or Path.cwd() / "local_cases" / "library_backups")
        self.interview_repo = interview_repo or kwargs.get("interview_repo")

    def list_published_documents(self, collection_id: str) -> List[Dict[str, str]]:
        """List current library entries for a user-facing revoke history."""
        runtime_dir, _ = collection_runtime_layout(collection_id, self.base_dir)
        sqlite_file = runtime_dir / COLLECTION_INDEX_BASENAME
        if not sqlite_file.exists():
            return []
        conn = sqlite3.connect(sqlite_file)
        conn.row_factory = sqlite3.Row
        try:
            if conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='published_documents'"
            ).fetchone() is None:
                return []
            rows = conn.execute(
                "SELECT doc_id, title, version, published_at FROM published_documents ORDER BY published_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def publish_package(
        self,
        package: PublicationPackage,
        actor: str,
    ) -> Tuple[PublicationPackage, PublicationReceipt]:
        """Publish sealed package into knowledge library with backup, lease, quick check, and acceptance.

        Implements T062, T063, T064.
        """
        if package.status != PACKAGE_STATUS_SEALED:
            raise PublicationError(f"Chỉ gói ở trạng thái 'sealed' mới có thể xuất bản. Trạng thái hiện tại: '{package.status}'.")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", package.artifact_id) or not re.fullmatch(
            r"[A-Za-z0-9._-]+", package.version
        ):
            raise PublicationError("Mã nội dung hoặc phiên bản chứa ký tự không an toàn.")

        runtime_dir, _ = collection_runtime_layout(package.target_collection_id, self.base_dir)
        runtime_dir.mkdir(parents=True, exist_ok=True)
        sqlite_file = runtime_dir / COLLECTION_INDEX_BASENAME

        lease = LibraryWriterLease(runtime_dir)
        if not lease.acquire(owner=actor):
            raise LibraryWriterBusyError(LibraryWriterLease.format_busy_message(runtime_dir))

        try:
            self._ensure_library_database(sqlite_file)
            try:
                backup_path, manifest = create_library_backup(
                    collection_id=package.target_collection_id,
                    backup_root=self.backup_dir,
                    note=f"Tự động sao lưu trước khi xuất bản gói {package.package_id}",
                    actor=actor,
                    local_fallback_root=self.base_dir,
                    lease=lease,
                )
            except ValueError as exc:
                if "cập nhật" in str(exc).lower() or "tiến trình" in str(exc).lower():
                    raise LibraryWriterBusyError(str(exc)) from exc
                raise

            docs_dir = runtime_dir / "published_docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            doc_file = docs_dir / (
                f"{package.artifact_id}_{package.version}_{package.package_digest[:12]}.md"
            )
            if doc_file.resolve().parent != docs_dir.resolve():
                raise PublicationError("Đường dẫn tài liệu xuất bản không an toàn.")

            with tempfile.TemporaryDirectory(prefix="publication_", dir=runtime_dir) as staging_name:
                staging_dir = Path(staging_name)
                staging_sqlite = staging_dir / COLLECTION_INDEX_BASENAME
                staging_doc = staging_dir / doc_file.name
                previous_doc = staging_dir / f"previous_{doc_file.name}"
                shutil.copy2(sqlite_file, staging_sqlite)
                if doc_file.exists():
                    shutil.copy2(doc_file, previous_doc)
                staging_doc.write_text(package.content_markdown, encoding="utf-8")

                conn = sqlite3.connect(staging_sqlite)
                try:
                    self._upsert_package(conn, package, doc_file)
                finally:
                    conn.close()

                if not sqlite_quick_check(staging_sqlite):
                    raise PublicationAcceptanceError(
                        "Kiểm tra toàn vẹn SQLite (quick_check) thất bại sau khi nạp tài liệu. Thư viện cũ được giữ nguyên."
                    )

                acceptance_results = self._run_acceptance(staging_sqlite, package)
                if not all(acceptance_results.values()):
                    raise PublicationAcceptanceError(
                        f"Bộ câu hỏi kiểm tra nghiệm thu truy xuất không đạt yêu cầu: {acceptance_results}. Thư viện cũ được giữ nguyên."
                    )

                doc_replaced = False
                database_replaced = False
                try:
                    os.replace(staging_doc, doc_file)
                    doc_replaced = True
                    os.replace(staging_sqlite, sqlite_file)
                    database_replaced = True
                    if not sqlite_quick_check(sqlite_file):
                        raise PublicationAcceptanceError(
                            "Kiểm tra toàn vẹn tệp thư viện chính thức thất bại. Đã khôi phục bản dùng được gần nhất."
                        )
                except Exception:
                    if database_replaced:
                        self._restore_database(backup_path / COLLECTION_INDEX_BASENAME, sqlite_file)
                    if doc_replaced:
                        if previous_doc.exists():
                            os.replace(previous_doc, doc_file)
                        else:
                            doc_file.unlink(missing_ok=True)
                    raise

            # Publication success: Create receipt
            receipt = PublicationReceipt(
                receipt_id=f"RCP-{package.package_id}-{int(datetime.now(timezone.utc).timestamp())}",
                package_id=package.package_id,
                package_digest=package.package_digest,
                backup_id=manifest.backup_id,
                quick_check_status="PASS",
                acceptance_results=acceptance_results,
                published_at=datetime.now(timezone.utc).isoformat(),
                published_by=actor,
                state="published",
            )

            published_package = PublicationPackage(
                package_id=package.package_id,
                artifact_id=package.artifact_id,
                artifact_digest=package.artifact_digest,
                artifact_type=package.artifact_type,
                title=package.title,
                scope=package.scope,
                version=package.version,
                content_markdown=package.content_markdown,
                claim_ids=package.claim_ids,
                acceptance_questions=package.acceptance_questions,
                target_collection_id=package.target_collection_id,
                sealed_at=package.sealed_at,
                sealed_by=package.sealed_by,
                status=PACKAGE_STATUS_PUBLISHED,
            )

            return published_package, receipt

        finally:
            lease.release()

    @staticmethod
    def _ensure_library_database(sqlite_file: Path) -> None:
        if sqlite_file.exists():
            return
        sqlite_file.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(sqlite_file)
        try:
            create_rag_search_schema(conn)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS published_documents (doc_id TEXT PRIMARY KEY, title TEXT, content TEXT, digest TEXT, scope TEXT, version TEXT, published_at TEXT)"
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _upsert_package(conn: sqlite3.Connection, package: PublicationPackage, doc_file: Path) -> None:
        create_rag_search_schema(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS published_documents (
                doc_id TEXT PRIMARY KEY, title TEXT, content TEXT, digest TEXT,
                scope TEXT, version TEXT, published_at TEXT
            )
            """
        )
        if KnowledgePublisher._table_exists(conn, "chunk_fts"):
            conn.execute("DELETE FROM chunk_fts WHERE chunk_id LIKE ?", (f"{package.package_id}_%",))
        conn.execute("DELETE FROM chunk_metadata WHERE document_id = ?", (package.package_id,))
        conn.execute(
            """
            INSERT INTO published_documents (doc_id, title, content, digest, scope, version, published_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(doc_id) DO UPDATE SET title=excluded.title, content=excluded.content,
                digest=excluded.digest, scope=excluded.scope, version=excluded.version,
                published_at=excluded.published_at
            """,
            (
                package.package_id, package.title, package.content_markdown,
                package.package_digest, package.scope, package.version,
            ),
        )
        paragraphs = [p.strip() for p in package.content_markdown.split("\n\n") if p.strip()]
        chunks = [
            RAGChunk(
                chunk_id=f"{package.package_id}_c{idx + 1}",
                document_id=package.package_id,
                element_ids=[f"elem_{package.package_id}_c{idx + 1}"],
                text=paragraph,
                source_title=package.title,
                source_path=str(doc_file),
                relative_path=f"published_docs/{doc_file.name}",
                citation_label=f"{package.title} p.{idx + 1}",
                file_type="markdown",
                element_types=["paragraph"],
                page_numbers=[idx + 1],
                sheet_names=[], slide_numbers=[], section_labels=[package.scope],
                row_ranges=[], cell_ranges=[], privacy_mode="local_only",
                source_hash=package.package_digest, chunk_index=idx,
            )
            for idx, paragraph in enumerate(paragraphs or [package.content_markdown])
        ]
        index_rag_chunks(conn, chunks)

    @staticmethod
    def _run_acceptance(sqlite_file: Path, package: PublicationPackage) -> Dict[str, bool]:
        conn = sqlite3.connect(sqlite_file)
        try:
            return {
                question: any(
                    result.document_id == package.package_id or package.package_id in result.chunk_id
                    for result in search_rag_chunks(conn, query=question, limit=5)
                )
                for question in package.acceptance_questions
            }
        finally:
            conn.close()

    @staticmethod
    def _restore_database(source: Path, target: Path) -> None:
        restore_file = target.with_name(f".{target.name}.{uuid.uuid4().hex}.restore")
        try:
            shutil.copy2(source, restore_file)
            os.replace(restore_file, target)
        finally:
            restore_file.unlink(missing_ok=True)

    @staticmethod
    def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
            (table_name,),
        ).fetchone() is not None

    def revoke_publication(
        self,
        package_id: str,
        collection_id: str = DEFAULT_COLLECTION_ID,
        reason: str = "Thu hồi tài liệu đã xuất bản",
        actor: str = "local_admin",
        *,
        record_responsibility: Callable[[], None],
    ) -> PublicationReceipt:
        """Revoke a published package from the library collection.

        Implements T065.
        """
        runtime_dir, _ = collection_runtime_layout(collection_id, self.base_dir)
        sqlite_file = runtime_dir / COLLECTION_INDEX_BASENAME

        # Step 1: Acquire lease BEFORE modifying or backing up
        lease = LibraryWriterLease(runtime_dir)
        if not lease.acquire(owner=actor):
            raise LibraryWriterBusyError(LibraryWriterLease.format_busy_message(runtime_dir))

        try:
            if not sqlite_file.exists():
                raise PublicationError("Không tìm thấy tài liệu đã xuất bản để thu hồi.")

            existing_row = False
            conn = sqlite3.connect(sqlite_file)
            try:
                if self._table_exists(conn, "published_documents"):
                    existing_row = conn.execute(
                        "SELECT 1 FROM published_documents WHERE doc_id = ?",
                        (package_id,),
                    ).fetchone() is not None
            finally:
                conn.close()
            targets = self._publication_document_targets(runtime_dir, package_id)
            if not existing_row and not targets:
                raise PublicationError("Không tìm thấy tài liệu đã xuất bản để thu hồi.")

            # Step 2: Backup before revocation while holding lease
            try:
                backup_path, manifest = create_library_backup(
                    collection_id=collection_id,
                    backup_root=self.backup_dir,
                    note=f"Sao lưu trước khi thu hồi gói {package_id}: {reason}",
                    actor=actor,
                    local_fallback_root=self.base_dir,
                    lease=lease,
                )
            except ValueError as exc:
                if "cập nhật" in str(exc).lower() or "tiến trình" in str(exc).lower():
                    raise LibraryWriterBusyError(str(exc)) from exc
                raise

            with tempfile.TemporaryDirectory(prefix="revocation_", dir=runtime_dir) as staging_name:
                staging_dir = Path(staging_name)
                staging_sqlite = staging_dir / COLLECTION_INDEX_BASENAME
                shutil.copy2(sqlite_file, staging_sqlite)
                conn = sqlite3.connect(staging_sqlite)
                try:
                    if self._table_exists(conn, "published_documents"):
                        conn.execute(
                            "DELETE FROM published_documents WHERE doc_id = ?",
                            (package_id,),
                        )
                    if self._table_exists(conn, "chunk_fts"):
                        conn.execute("DELETE FROM chunk_fts WHERE chunk_id LIKE ?", (f"{package_id}%",))
                    if self._table_exists(conn, "chunk_metadata"):
                        conn.execute("DELETE FROM chunk_metadata WHERE document_id = ?", (package_id,))
                    remaining = None
                    if self._table_exists(conn, "published_documents"):
                        remaining = conn.execute(
                            "SELECT 1 FROM published_documents WHERE doc_id = ?",
                            (package_id,),
                        ).fetchone()
                    conn.commit()
                finally:
                    conn.close()
                if existing_row and remaining is not None:
                    raise PublicationError("Chưa xóa được dữ liệu tài liệu khi thu hồi.")
                if not sqlite_quick_check(staging_sqlite):
                    raise PublicationError("Kiểm tra toàn vẹn SQLite thất bại sau khi thu hồi tài liệu.")

                moved_files: List[Tuple[Path, Path]] = []
                database_replaced = False
                try:
                    for source in targets:
                        held = staging_dir / f"held_{len(moved_files)}_{source.name}"
                        try:
                            os.replace(source, held)
                        except Exception as unlink_err:
                            raise RuntimeError(
                                f"Không thể xóa tệp tài liệu đã xuất bản '{source.name}' khi thu hồi: {unlink_err}"
                            ) from unlink_err
                        moved_files.append((source, held))
                    leftover_targets = [source for source, _held in moved_files if source.exists()]
                    if leftover_targets:
                        raise PublicationError("Chưa xóa được tệp tài liệu khi thu hồi.")
                    os.replace(staging_sqlite, sqlite_file)
                    database_replaced = True
                    if not sqlite_quick_check(sqlite_file):
                        raise PublicationError(
                            "Kiểm tra toàn vẹn SQLite thất bại sau khi thu hồi tài liệu. Đã khôi phục bản cũ."
                        )
                    record_responsibility()
                except Exception:
                    if database_replaced:
                        self._restore_database(backup_path / COLLECTION_INDEX_BASENAME, sqlite_file)
                    for source, held in reversed(moved_files):
                        if held.exists():
                            os.replace(held, source)
                    raise

            return PublicationReceipt(
                receipt_id=f"REV-{package_id}-{int(datetime.now(timezone.utc).timestamp())}",
                package_id=package_id,
                package_digest="",
                backup_id=manifest.backup_id,
                quick_check_status="PASS",
                acceptance_results={},
                published_at=datetime.now(timezone.utc).isoformat(),
                published_by=actor,
                state="revoked",
            )
        finally:
            lease.release()

    @staticmethod
    def _publication_document_targets(runtime_dir: Path, package_id: str) -> List[Path]:
        docs_dir = runtime_dir / "published_docs"
        if not docs_dir.exists() or not package_id.startswith("PKG-") or "-V" not in package_id:
            return []
        artifact_id, encoded_version = package_id[4:].rsplit("-V", 1)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", artifact_id) or not re.fullmatch(
            r"[A-Za-z0-9_-]+", encoded_version
        ):
            return []
        version = encoded_version.replace("_", ".")
        legacy_file = docs_dir / f"{artifact_id}_{version}.md"
        immutable_files = sorted(docs_dir.glob(f"{artifact_id}_{version}_*.md"))
        if legacy_file.exists():
            immutable_files.append(legacy_file)
        return immutable_files
