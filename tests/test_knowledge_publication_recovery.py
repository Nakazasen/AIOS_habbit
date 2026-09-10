"""Fault recovery and concurrency tests for knowledge publication.

Implements T068 of Goal 010-expert-knowledge-acquisition.
Tests:
- Writer lease busy handling (process/thread contention).
- Ingestion interruption and automatic rollback from point-in-time backup.
"""
from __future__ import annotations

import sqlite3
import tempfile
from dataclasses import replace
from pathlib import Path
import pytest
from unittest.mock import patch

from aios_habit.controlled_knowledge_artifact import (
    ARTIFACT_STATUS_APPROVED,
    ARTIFACT_TYPE_SOP,
    ControlledKnowledgeArtifact,
    DecisionRecord,
)
from aios_habit.knowledge_publication import (
    KnowledgePublisher,
    LibraryWriterBusyError,
    PublicationAcceptanceError,
    seal_publication_package,
)
from aios_habit.workspace_chat_store import (
    COLLECTION_INDEX_BASENAME,
    LibraryWriterLease,
    collection_runtime_layout,
    sqlite_quick_check,
)


def make_approved_artifact(artifact_id: str = "ART-REC-01") -> ControlledKnowledgeArtifact:
    artifact = ControlledKnowledgeArtifact(
        artifact_id=artifact_id,
        artifact_type=ARTIFACT_TYPE_SOP,
        title="Quy trình sấy keo",
        scope="say_keo",
        version="1.0",
        content_markdown="# Quy trình sấy keo\nNhiệt độ 65 độ C.",
        claim_ids=("CLM-01",),
        claim_map={"CLM-01": "Nhiệt độ 65 độ C."},
        status=ARTIFACT_STATUS_APPROVED,
        created_by="engineer_a",
    )
    decision = DecisionRecord(
        decision_id="DEC-01", subject_id=artifact_id, subject_digest=artifact.digest,
        subject_version=artifact.version, decision="confirm", recorded_name="qa_lead",
        machine_ref="MAY-QC", confidence="high", rationale="Đạt chuẩn kỹ thuật",
        checked_source_refs=("CLM-01",), responsibility_acknowledged=True,
    )
    return replace(artifact, decisions=(decision,))


def test_writer_lease_busy_blocks_publication_safely():
    """Test invariant: When LibraryWriterLease is held by another process, publication fails closed without corruption."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        backup_dir = Path(tmpdir) / "backups"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=backup_dir)

        artifact = make_approved_artifact("ART-BUSY-01")
        pkg = seal_publication_package(
            artifact=artifact,
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="lead_reviewer",
        )

        runtime_dir, _ = collection_runtime_layout(pkg.target_collection_id, base_dir)
        runtime_dir.mkdir(parents=True, exist_ok=True)

        # External process acquires the lease first
        external_lease = LibraryWriterLease(runtime_dir)
        acquired = external_lease.acquire(owner="external_indexing_job")
        assert acquired is True

        try:
            with pytest.raises(LibraryWriterBusyError, match="cập nhật"):
                publisher.publish_package(pkg, actor="lead_reviewer")
        finally:
            external_lease.release()


def test_writer_lease_busy_blocks_revocation_safely():
    """Test invariant: Revocation fails closed when writer lease is busy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        backup_dir = Path(tmpdir) / "backups"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=backup_dir)

        runtime_dir, _ = collection_runtime_layout("knowledge", base_dir)
        runtime_dir.mkdir(parents=True, exist_ok=True)
        sqlite_file = runtime_dir / COLLECTION_INDEX_BASENAME
        import sqlite3
        conn = sqlite3.connect(sqlite_file)
        conn.execute("CREATE TABLE published_documents (doc_id TEXT PRIMARY KEY)")
        conn.commit()
        conn.close()

        external_lease = LibraryWriterLease(runtime_dir)
        external_lease.acquire(owner="backup_runner")

        try:
            with pytest.raises(LibraryWriterBusyError, match="cập nhật"):
                publisher.revoke_publication(
                    "PKG-01",
                    "knowledge",
                    "Thu hồi",
                    "lead",
                    record_responsibility=lambda: None,
                )
        finally:
            external_lease.release()


def test_interrupted_ingest_leaves_library_usable():
    """Test invariant: If quick_check fails after ingest, automatic rollback restores working backup copy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        backup_dir = Path(tmpdir) / "backups"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=backup_dir)

        artifact = make_approved_artifact("ART-FAIL-01")
        pkg = seal_publication_package(
            artifact=artifact,
            acceptance_questions=["Câu hỏi không khớp nội dung xyz12345?"],
            sealed_by="lead_reviewer",
        )

        # Simulation: acceptance test will fail because question keywords are not in document
        with pytest.raises(PublicationAcceptanceError, match="không đạt yêu cầu"):
            publisher.publish_package(pkg, actor="lead_reviewer")

        # Verify that library sqlite exists and is usable after rollback
        runtime_dir, _ = collection_runtime_layout(pkg.target_collection_id, base_dir)
        sqlite_file = runtime_dir / COLLECTION_INDEX_BASENAME
        assert sqlite_file.exists()
        assert sqlite_quick_check(sqlite_file) is True


def test_publication_mid_operation_exception_cleans_up_and_restores_backup():
    """Test invariant: Unexpected exception during indexing triggers complete rollback of doc file and restores SQLite."""
    import sqlite3
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        backup_dir = Path(tmpdir) / "backups"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=backup_dir)

        artifact = make_approved_artifact("ART-EXCEPTION-01")
        pkg = seal_publication_package(
            artifact=artifact,
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="lead_reviewer",
        )

        # Inject synthetic exception in index_rag_chunks simulating disk full or indexing crash
        with patch("aios_habit.knowledge_publication.index_rag_chunks", side_effect=sqlite3.OperationalError("disk I/O error")):
            with pytest.raises(sqlite3.OperationalError, match="disk I/O error"):
                publisher.publish_package(pkg, actor="lead_reviewer")

        runtime_dir, _ = collection_runtime_layout(pkg.target_collection_id, base_dir)
        sqlite_file = runtime_dir / COLLECTION_INDEX_BASENAME
        # Database must still exist and be valid
        assert sqlite_file.exists()
        assert sqlite_quick_check(sqlite_file) is True

        # Published markdown file must have been unlinked
        docs_dir = runtime_dir / "published_docs"
        if docs_dir.exists():
            matched_files = list(docs_dir.glob(f"*{artifact.artifact_id}*.md"))
            assert len(matched_files) == 0, f"Published doc must be removed on rollback: {matched_files}"

        # Lease must be free and acquirable
        lease = LibraryWriterLease(runtime_dir)
        assert lease.acquire(owner="checker") is True
        lease.release()
def test_publication_pre_indexing_connect_failure_cleans_up_and_restores_backup():
    """Test invariant: If sqlite3.connect or schema creation fails after doc is written, doc is unlinked and lease released."""
    import sqlite3
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        backup_dir = Path(tmpdir) / "backups"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=backup_dir)

        artifact = make_approved_artifact("ART-CONNECT-FAIL-01")
        pkg = seal_publication_package(
            artifact=artifact,
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="lead_reviewer",
        )

        with patch("sqlite3.connect", side_effect=sqlite3.OperationalError("unable to open database file")):
            with pytest.raises(sqlite3.OperationalError, match="unable to open database file"):
                publisher.publish_package(pkg, actor="lead_reviewer")

        runtime_dir, _ = collection_runtime_layout(pkg.target_collection_id, base_dir)
        # Published markdown file must have been unlinked
        docs_dir = runtime_dir / "published_docs"
        if docs_dir.exists():
            matched_files = list(docs_dir.glob(f"*{artifact.artifact_id}*.md"))
            assert len(matched_files) == 0, f"Orphaned doc must be cleaned up on connect error: {matched_files}"

        # Lease must be released
        lease = LibraryWriterLease(runtime_dir)
        assert lease.acquire(owner="checker") is True
        lease.release()


def test_knowledge_publisher_init_supports_interview_repo_kwarg():
    """Test invariant: KnowledgePublisher accepts interview_repo kwarg for seamless UI compatibility."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        backup_dir = Path(tmpdir) / "backups"
        sentinel_repo = object()
        pub = KnowledgePublisher(base_dir=base_dir, backup_dir=backup_dir, interview_repo=sentinel_repo)
        assert pub.interview_repo is sentinel_repo


def test_failed_republish_same_artifact_version_keeps_previous_file_and_database():
    """A failed replacement must not destroy the last usable published version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        publisher = KnowledgePublisher(
            base_dir=base_dir,
            backup_dir=Path(tmpdir) / "backups",
        )
        artifact = make_approved_artifact("ART-REPLACE-01")
        original = seal_publication_package(
            artifact=artifact,
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="lead_reviewer",
        )
        publisher.publish_package(original, actor="lead_reviewer")

        replacement = type(original)(
            **{
                **original.__dict__,
                "content_markdown": "# Quy trình sấy keo\nNội dung thay thế chưa hoàn tất.",
            }
        )
        runtime_dir, _ = collection_runtime_layout(original.target_collection_id, base_dir)
        live_database = runtime_dir / COLLECTION_INDEX_BASENAME
        real_replace = __import__("os").replace

        def fail_database_replacement(source, target):
            source_path = Path(source)
            if source_path.name == COLLECTION_INDEX_BASENAME and Path(target) == live_database:
                raise OSError("synthetic snapshot replace failure")
            return real_replace(source, target)

        with patch(
            "aios_habit.knowledge_publication.os.replace",
            side_effect=fail_database_replacement,
        ):
            with pytest.raises(OSError, match="synthetic snapshot replace failure"):
                publisher.publish_package(replacement, actor="lead_reviewer")

        doc_files = list((runtime_dir / "published_docs").glob("ART-REPLACE-01_1.0_*.md"))
        assert len(doc_files) == 1
        doc_file = doc_files[0]
        assert doc_file.read_text(encoding="utf-8") == original.content_markdown
        conn = sqlite3.connect(runtime_dir / COLLECTION_INDEX_BASENAME)
        try:
            stored = conn.execute(
                "SELECT content FROM published_documents WHERE doc_id = ?",
                (original.package_id,),
            ).fetchone()
            assert stored == (original.content_markdown,)
        finally:
            conn.close()
        lease = LibraryWriterLease(runtime_dir)
        assert lease.acquire(owner="checker") is True
        lease.release()


def test_republish_keeps_every_database_snapshot_bound_to_an_existing_document():
    """The old and new SQLite snapshots must each point to an immutable file that exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=Path(tmpdir) / "backups")
        original = seal_publication_package(
            artifact=make_approved_artifact("ART-SNAPSHOT-01"),
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="Người xác nhận",
        )
        publisher.publish_package(original, actor="Người xác nhận")
        replacement = type(original)(
            **{**original.__dict__, "content_markdown": "# Quy trình sấy keo\nNhiệt độ mới là 70 độ C."}
        )
        runtime_dir, _ = collection_runtime_layout(original.target_collection_id, base_dir)
        live_database = runtime_dir / COLLECTION_INDEX_BASENAME
        real_replace = __import__("os").replace
        observed_paths: list[str] = []

        def inspect_database_transition(source, target):
            if Path(source).name == COLLECTION_INDEX_BASENAME and Path(target) == live_database:
                for database in (live_database, Path(source)):
                    conn = sqlite3.connect(database)
                    try:
                        relative_path = conn.execute(
                            "SELECT relative_path FROM chunk_metadata WHERE document_id = ? LIMIT 1",
                            (original.package_id,),
                        ).fetchone()[0]
                    finally:
                        conn.close()
                    observed_paths.append(relative_path)
                    assert (runtime_dir / relative_path).exists()
            return real_replace(source, target)

        with patch("aios_habit.knowledge_publication.os.replace", side_effect=inspect_database_transition):
            publisher.publish_package(replacement, actor="Người xác nhận")

        assert len(observed_paths) == 2
        assert observed_paths[0] != observed_paths[1]
        conn = sqlite3.connect(live_database)
        try:
            active_path = conn.execute(
                "SELECT relative_path FROM chunk_metadata WHERE document_id = ? LIMIT 1",
                (original.package_id,),
            ).fetchone()[0]
        finally:
            conn.close()
        assert active_path == observed_paths[1]
        assert (runtime_dir / active_path).exists()


def test_sqlite_restore_never_runs_while_publication_connection_is_open():
    """Rollback must close SQLite before replacing its file on every platform."""
    with tempfile.TemporaryDirectory() as tmpdir:
        publisher = KnowledgePublisher(
            base_dir=Path(tmpdir) / "workspace_chat",
            backup_dir=Path(tmpdir) / "backups",
        )
        package = seal_publication_package(
            artifact=make_approved_artifact("ART-CLOSE-FIRST"),
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="lead_reviewer",
        )
        active_connection = None

        def fail_after_capturing_connection(conn, chunks):
            nonlocal active_connection
            active_connection = conn
            raise sqlite3.OperationalError("disk I/O error")

        real_copy = __import__("shutil").copy2

        def require_closed_connection(source, target):
            if active_connection is not None:
                with pytest.raises(sqlite3.ProgrammingError):
                    active_connection.execute("SELECT 1")
            return real_copy(source, target)

        with patch(
            "aios_habit.knowledge_publication.index_rag_chunks",
            side_effect=fail_after_capturing_connection,
        ), patch(
            "aios_habit.knowledge_publication.shutil.copy2",
            side_effect=require_closed_connection,
        ):
            with pytest.raises(sqlite3.OperationalError, match="disk I/O error"):
                publisher.publish_package(package, actor="lead_reviewer")
        assert active_connection is not None
        with pytest.raises(sqlite3.ProgrammingError):
            active_connection.execute("SELECT 1")


def test_revoke_index_delete_failure_rolls_back_and_releases_lease():
    """An index deletion error must remain visible and preserve DB, file, and lease."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=Path(tmpdir) / "backups")
        package = seal_publication_package(
            artifact=make_approved_artifact("ART-REVOKE-INDEX"),
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="lead_reviewer",
        )
        publisher.publish_package(package, actor="lead_reviewer")
        runtime_dir, _ = collection_runtime_layout(package.target_collection_id, base_dir)
        db_file = runtime_dir / COLLECTION_INDEX_BASENAME
        conn = sqlite3.connect(db_file)
        try:
            conn.execute(
                """
                CREATE TRIGGER fail_chunk_delete BEFORE DELETE ON chunk_metadata
                BEGIN SELECT RAISE(ABORT, 'synthetic index delete failure'); END
                """
            )
            conn.commit()
        finally:
            conn.close()

        with pytest.raises(sqlite3.IntegrityError, match="synthetic index delete failure"):
            publisher.revoke_publication(
                package.package_id,
                package.target_collection_id,
                record_responsibility=lambda: None,
            )

        conn = sqlite3.connect(db_file)
        try:
            assert conn.execute(
                "SELECT 1 FROM published_documents WHERE doc_id = ?", (package.package_id,)
            ).fetchone() == (1,)
            assert conn.execute(
                "SELECT 1 FROM chunk_metadata WHERE document_id = ?", (package.package_id,)
            ).fetchone() == (1,)
        finally:
            conn.close()
        assert list((runtime_dir / "published_docs").glob("ART-REVOKE-INDEX_1.0_*.md"))
        lease = LibraryWriterLease(runtime_dir)
        assert lease.acquire(owner="checker") is True
        lease.release()


def test_revoke_file_delete_failure_rolls_back_database_and_releases_lease():
    """A file deletion error must not leave the searchable database revoked."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=Path(tmpdir) / "backups")
        package = seal_publication_package(
            artifact=make_approved_artifact("ART-REVOKE-FILE"),
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="lead_reviewer",
        )
        publisher.publish_package(package, actor="lead_reviewer")
        runtime_dir, _ = collection_runtime_layout(package.target_collection_id, base_dir)
        doc_files = list((runtime_dir / "published_docs").glob("ART-REVOKE-FILE_1.0_*.md"))
        assert len(doc_files) == 1
        doc_file = doc_files[0]
        real_replace = __import__("os").replace

        def fail_target_replace(source, target):
            if Path(source) == doc_file:
                raise PermissionError("synthetic unlink failure")
            return real_replace(source, target)

        with patch("aios_habit.knowledge_publication.os.replace", side_effect=fail_target_replace):
            with pytest.raises(RuntimeError, match="synthetic unlink failure"):
                publisher.revoke_publication(
                    package.package_id,
                    package.target_collection_id,
                    record_responsibility=lambda: None,
                )

        conn = sqlite3.connect(runtime_dir / COLLECTION_INDEX_BASENAME)
        try:
            assert conn.execute(
                "SELECT 1 FROM published_documents WHERE doc_id = ?", (package.package_id,)
            ).fetchone() == (1,)
            assert conn.execute(
                "SELECT 1 FROM chunk_metadata WHERE document_id = ?", (package.package_id,)
            ).fetchone() == (1,)
        finally:
            conn.close()
        assert doc_file.exists()
        lease = LibraryWriterLease(runtime_dir)
        assert lease.acquire(owner="checker") is True
        lease.release()


def test_revoke_responsibility_failure_restores_searchable_library():
    """A failed responsibility record must roll back the library revocation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=Path(tmpdir) / "backups")
        package = seal_publication_package(
            artifact=make_approved_artifact("ART-REVOKE-DECISION"),
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="Người xác nhận",
        )
        publisher.publish_package(package, actor="Người xác nhận")
        runtime_dir, _ = collection_runtime_layout(package.target_collection_id, base_dir)

        def fail_responsibility_record():
            raise RuntimeError("synthetic decision persistence failure")

        with pytest.raises(RuntimeError, match="synthetic decision persistence failure"):
            publisher.revoke_publication(
                package.package_id,
                package.target_collection_id,
                record_responsibility=fail_responsibility_record,
            )

        conn = sqlite3.connect(runtime_dir / COLLECTION_INDEX_BASENAME)
        try:
            assert conn.execute(
                "SELECT 1 FROM published_documents WHERE doc_id = ?",
                (package.package_id,),
            ).fetchone() == (1,)
            assert conn.execute(
                "SELECT 1 FROM chunk_metadata WHERE document_id = ?",
                (package.package_id,),
            ).fetchone() == (1,)
        finally:
            conn.close()
        assert list((runtime_dir / "published_docs").glob("ART-REVOKE-DECISION_1.0_*.md"))


def test_concurrent_writes_second_writer_receives_busy_and_preserves_library():
    """T096: Concurrent writes fail closed with busy error and preserve existing library."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=Path(tmpdir) / "backups")

        pkg1 = seal_publication_package(
            artifact=make_approved_artifact("ART-CONC-01"),
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="writer_1",
        )
        publisher.publish_package(pkg1, actor="writer_1")

        pkg2 = seal_publication_package(
            artifact=make_approved_artifact("ART-CONC-02"),
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="writer_2",
        )

        runtime_dir, _ = collection_runtime_layout(pkg1.target_collection_id, base_dir)
        # Simulate writer 1 holding the lease concurrently
        lease = LibraryWriterLease(runtime_dir)
        assert lease.acquire(owner="writer_1") is True

        try:
            with pytest.raises(LibraryWriterBusyError, match="cập nhật"):
                publisher.publish_package(pkg2, actor="writer_2")
        finally:
            lease.release()

        # Verify package 1 is still intact and searchable
        conn = sqlite3.connect(runtime_dir / COLLECTION_INDEX_BASENAME)
        try:
            assert conn.execute(
                "SELECT 1 FROM published_documents WHERE doc_id = ?", (pkg1.package_id,)
            ).fetchone() == (1,)
        finally:
            conn.close()

        # Now writer 2 can succeed after lease is released
        publisher.publish_package(pkg2, actor="writer_2")
        conn = sqlite3.connect(runtime_dir / COLLECTION_INDEX_BASENAME)
        try:
            assert conn.execute(
                "SELECT 1 FROM published_documents WHERE doc_id = ?", (pkg1.package_id,)
            ).fetchone() == (1,)
            assert conn.execute(
                "SELECT 1 FROM published_documents WHERE doc_id = ?", (pkg2.package_id,)
            ).fetchone() == (1,)
        finally:
            conn.close()


def test_publication_disk_full_or_io_error_restores_usable_library_and_releases_lease():
    """T096: Simulated disk-full (ENOSPC) during publication rolls back and leaves library intact."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=Path(tmpdir) / "backups")

        original = seal_publication_package(
            artifact=make_approved_artifact("ART-DISKFULL-01"),
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="lead_reviewer",
        )
        publisher.publish_package(original, actor="lead_reviewer")

        replacement = seal_publication_package(
            artifact=make_approved_artifact("ART-DISKFULL-02"),
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="lead_reviewer",
        )

        real_replace = __import__("os").replace

        def simulate_disk_full(source, target):
            if COLLECTION_INDEX_BASENAME in str(source):
                raise OSError(28, "No space left on device")
            return real_replace(source, target)

        with patch("aios_habit.knowledge_publication.os.replace", side_effect=simulate_disk_full):
            with pytest.raises(OSError, match="No space left on device"):
                publisher.publish_package(replacement, actor="lead_reviewer")

        runtime_dir, _ = collection_runtime_layout(original.target_collection_id, base_dir)
        live_database = runtime_dir / COLLECTION_INDEX_BASENAME
        assert sqlite_quick_check(live_database) is True
        conn = sqlite3.connect(live_database)
        try:
            assert conn.execute(
                "SELECT 1 FROM published_documents WHERE doc_id = ?", (original.package_id,)
            ).fetchone() == (1,)
            assert conn.execute(
                "SELECT 1 FROM published_documents WHERE doc_id = ?", (replacement.package_id,)
            ).fetchone() is None
        finally:
            conn.close()

        # Lease is properly released
        lease = LibraryWriterLease(runtime_dir)
        assert lease.acquire(owner="checker") is True
        lease.release()


def test_publication_disconnected_storage_path_fails_safely_without_data_corruption():
    """T096: Disconnected or missing storage directory fails cleanly without corrupting previous state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=Path(tmpdir) / "backups")

        original = seal_publication_package(
            artifact=make_approved_artifact("ART-DISCONNECT-01"),
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="lead_reviewer",
        )
        publisher.publish_package(original, actor="lead_reviewer")

        replacement = seal_publication_package(
            artifact=make_approved_artifact("ART-DISCONNECT-02"),
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="lead_reviewer",
        )

        real_replace = __import__("os").replace

        def simulate_network_loss(source, target):
            raise PermissionError("The network path was not found")

        with patch("aios_habit.knowledge_publication.os.replace", side_effect=simulate_network_loss):
            with pytest.raises(PermissionError, match="network path"):
                publisher.publish_package(replacement, actor="lead_reviewer")

        runtime_dir, _ = collection_runtime_layout(original.target_collection_id, base_dir)
        live_database = runtime_dir / COLLECTION_INDEX_BASENAME
        assert sqlite_quick_check(live_database) is True

        lease = LibraryWriterLease(runtime_dir)
        assert lease.acquire(owner="checker") is True
        lease.release()

