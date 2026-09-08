"""Tests for knowledge publication to shared library, sealing, acceptance, and revocation.

Implements T067 of Goal 010-expert-knowledge-acquisition.
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
import pytest

from aios_habit.rag_search import search_rag_chunks

from aios_habit.controlled_knowledge_artifact import (
    ARTIFACT_STATUS_APPROVED,
    ARTIFACT_STATUS_CANDIDATE,
    ARTIFACT_STATUS_REVOKED,
    ARTIFACT_TYPE_SOP,
    ArtifactApproval,
    ControlledKnowledgeArtifact,
)
from aios_habit.knowledge_publication import (
    KnowledgePublisher,
    PACKAGE_STATUS_PUBLISHED,
    PACKAGE_STATUS_REVOKED,
    PACKAGE_STATUS_SEALED,
    PublicationAcceptanceError,
    PublicationError,
    PublicationPackage,
    UnapprovedArtifactPublicationError,
    seal_publication_package,
)


def make_approved_artifact(artifact_id: str = "ART-SOP-01") -> ControlledKnowledgeArtifact:
    approval = ArtifactApproval(
        approval_id="APP-01",
        artifact_id=artifact_id,
        artifact_digest="dig_123",
        action="approve",
        actor_id="qa_lead",
        scope="say_keo",
        reason="Đạt chuẩn kỹ thuật vận hành",
    )
    return ControlledKnowledgeArtifact(
        artifact_id=artifact_id,
        artifact_type=ARTIFACT_TYPE_SOP,
        title="Quy trình sấy keo",
        scope="say_keo",
        version="1.0",
        content_markdown="# Quy trình sấy keo\nNhiệt độ sấy tối ưu 65 độ C trong 45 phút.",
        claim_ids=("CLM-01",),
        claim_map={"CLM-01": "Nhiệt độ sấy tối ưu 65 độ C trong 45 phút."},
        status=ARTIFACT_STATUS_APPROVED,
        created_by="engineer_a",
        approvals=(approval,),
    )


def test_seal_unapproved_artifact_fails():
    """Test invariant: Cannot seal an artifact that is not approved or has no approvals."""
    unapproved = ControlledKnowledgeArtifact(
        artifact_id="ART-CAND",
        artifact_type=ARTIFACT_TYPE_SOP,
        title="Nháp quy trình",
        scope="say_keo",
        version="1.0",
        content_markdown="# Nháp",
        claim_ids=("CLM-01",),
        status=ARTIFACT_STATUS_CANDIDATE,
    )

    with pytest.raises(UnapprovedArtifactPublicationError, match="Chỉ tài liệu đã được phê duyệt"):
        seal_publication_package(
            artifact=unapproved,
            acceptance_questions=["Nhiệt độ bao nhiêu?"],
            sealed_by="engineer_a",
        )


def test_seal_approved_artifact_success():
    """Test sealing an approved artifact into an immutable PublicationPackage."""
    artifact = make_approved_artifact("ART-SOP-SEAL")
    pkg = seal_publication_package(
        artifact=artifact,
        acceptance_questions=["Nhiệt độ sấy keo tối ưu là bao nhiêu?"],
        sealed_by="lead_reviewer",
    )

    assert pkg.package_id == "PKG-ART-SOP-SEAL-V1_0"
    assert pkg.status == PACKAGE_STATUS_SEALED
    assert pkg.artifact_id == "ART-SOP-SEAL"
    assert len(pkg.package_digest) == 64
    assert len(pkg.acceptance_questions) == 1


def test_publish_package_success():
    """Test successful publication with backup, quick check, and acceptance receipt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        backup_dir = Path(tmpdir) / "backups"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=backup_dir)

        artifact = make_approved_artifact("ART-SOP-PUB")
        pkg = seal_publication_package(
            artifact=artifact,
            acceptance_questions=["Nhiệt độ sấy keo tối ưu là bao nhiêu?"],
            sealed_by="lead_reviewer",
        )

        published_pkg, receipt = publisher.publish_package(pkg, actor="lead_reviewer")

        assert published_pkg.status == PACKAGE_STATUS_PUBLISHED
        assert receipt.quick_check_status == "PASS"
        assert receipt.state == "published"
        assert receipt.backup_id.startswith("BAK-")
        assert receipt.acceptance_results["Nhiệt độ sấy keo tối ưu là bao nhiêu?"] is True

        # Check published markdown exists
        doc_path = base_dir / "collections" / "tri_thuc" / "published_docs" / "ART-SOP-PUB_1.0.md"
        assert doc_path.exists()
        assert "Nhiệt độ sấy tối ưu 65 độ C" in doc_path.read_text(encoding="utf-8")

        # Verify real RAG search query retrieves the newly published knowledge
        db_path = base_dir / "collections" / "tri_thuc" / "library.sqlite"
        conn = sqlite3.connect(db_path)
        try:
            results = search_rag_chunks(conn, query="Nhiệt độ sấy keo tối ưu", limit=5)
            assert len(results) > 0
            assert any(r.document_id == pkg.package_id for r in results)
            assert "65 độ C" in results[0].text
        finally:
            conn.close()


def test_unapproved_status_package_rejected():
    """Test invariant: Cannot publish a package that is not in sealed status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        publisher = KnowledgePublisher(base_dir=Path(tmpdir) / "chat", backup_dir=Path(tmpdir) / "bak")
        pkg = PublicationPackage(
            package_id="PKG-01",
            artifact_id="ART-01",
            artifact_digest="dig_1",
            artifact_type=ARTIFACT_TYPE_SOP,
            title="SOP Test",
            scope="say_keo",
            version="1.0",
            content_markdown="Content",
            claim_ids=("C1",),
            acceptance_questions=("Q1",),
            status=PACKAGE_STATUS_REVOKED,
        )

        with pytest.raises(PublicationError, match="Chỉ gói ở trạng thái 'sealed'"):
            publisher.publish_package(pkg, actor="lead")


def test_revoke_published_package():
    """Test revoking a published package generates backup and removes document."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "workspace_chat"
        backup_dir = Path(tmpdir) / "backups"
        publisher = KnowledgePublisher(base_dir=base_dir, backup_dir=backup_dir)

        artifact = make_approved_artifact("ART-SOP-REV")
        pkg = seal_publication_package(
            artifact=artifact,
            acceptance_questions=["Nhiệt độ sấy keo là bao nhiêu?"],
            sealed_by="lead_reviewer",
        )
        publisher.publish_package(pkg, actor="lead_reviewer")

        # Now revoke
        receipt = publisher.revoke_publication(
            package_id=pkg.package_id,
            collection_id=pkg.target_collection_id,
            reason="Quy trình lỗi thời do thay máy sấy mới",
            actor="lead_reviewer",
        )

        assert receipt.state == "revoked"
        assert receipt.package_id == pkg.package_id

        # Verify real RAG search query no longer retrieves the revoked document
        db_path = base_dir / "collections" / "tri_thuc" / "library.sqlite"
        conn = sqlite3.connect(db_path)
        try:
            results = search_rag_chunks(conn, query="Nhiệt độ sấy keo", limit=5)
            assert not any(r.document_id == pkg.package_id for r in results)
        finally:
            conn.close()
