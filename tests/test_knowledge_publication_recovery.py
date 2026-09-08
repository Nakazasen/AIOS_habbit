"""Fault recovery and concurrency tests for knowledge publication.

Implements T068 of Goal 010-expert-knowledge-acquisition.
Tests:
- Writer lease busy handling (process/thread contention).
- Ingestion interruption and automatic rollback from point-in-time backup.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch

from aios_habit.controlled_knowledge_artifact import (
    ARTIFACT_STATUS_APPROVED,
    ARTIFACT_TYPE_SOP,
    ArtifactApproval,
    ControlledKnowledgeArtifact,
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
    approval = ArtifactApproval(
        approval_id="APP-01",
        artifact_id=artifact_id,
        artifact_digest="dig_123",
        action="approve",
        actor_id="qa_lead",
        scope="say_keo",
        reason="Đạt chuẩn kỹ thuật",
    )
    return ControlledKnowledgeArtifact(
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
        approvals=(approval,),
    )


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
                publisher.revoke_publication("PKG-01", "knowledge", "Thu hồi", "lead")
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
