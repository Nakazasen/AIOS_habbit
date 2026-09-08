"""Tests for Controlled Knowledge Artifacts (SOPs, Lessons Learned) and approval workflow.

Implements T059 of Goal 010-expert-knowledge-acquisition.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from aios_habit.controlled_knowledge_artifact import (
    APPROVAL_ACTION_APPROVE,
    APPROVAL_ACTION_REJECT,
    APPROVAL_ACTION_REQUEST_CHANGE,
    APPROVAL_ACTION_REVOKE,
    ARTIFACT_STATUS_APPROVED,
    ARTIFACT_STATUS_CANDIDATE,
    ARTIFACT_STATUS_CHANGES_REQUESTED,
    ARTIFACT_STATUS_REJECTED,
    ARTIFACT_STATUS_REVOKED,
    ARTIFACT_TYPE_LESSON,
    ARTIFACT_TYPE_SOP,
    ConflictedClaimArtifactError,
    ControlledArtifactError,
    ControlledKnowledgeArtifact,
    SelfApprovalDeniedError,
    StaleArtifactDigestError,
    generate_artifact_diff,
    generate_candidate_lesson,
    generate_candidate_sop,
)
from aios_habit.expert_interview_repository import ExpertInterviewRepository
from aios_habit.expert_interview_service import ExpertInterviewService
from aios_habit.knowledge_claim_extractor import (
    CLAIM_STATUS_CANDIDATE,
    CLAIM_STATUS_CONFIRMED,
    CLAIM_STATUS_CONFLICTED,
    KnowledgeClaim,
)
from aios_habit.workspace_case_repository import WorkspaceCaseRepository


def make_sample_claim(claim_id: str, scope: str, statement: str, status: str = CLAIM_STATUS_CONFIRMED) -> KnowledgeClaim:
    return KnowledgeClaim(
        claim_id=claim_id,
        statement=statement,
        scope=scope,
        source_refs=(f"turn:{claim_id}",),
        validity_conditions=("Áp suất 3.5 bar", "Nhiệt độ 65 độ C"),
        confidence=0.95,
        status=status,
    )


def test_generate_candidate_sop_and_lesson_success():
    """Test generating SOP and Lesson Learned candidates in Vietnamese with provenance mapping."""
    claim1 = make_sample_claim("CLM-01", "ep_khuon", "Cài đặt áp lực máy ép ở mức 3.5 bar trong 12 giây.")
    claim2 = make_sample_claim("CLM-02", "ep_khuon", "Kiểm tra nhiệt độ khuôn duy trì ổn định 65 độ C.")

    # 1. SOP
    sop = generate_candidate_sop(
        artifact_id="ART-SOP-001",
        title="Quy trình vận hành máy ép khuôn",
        scope="ep_khuon",
        claims=[claim1, claim2],
        created_by="engineer_a",
    )
    assert sop.artifact_id == "ART-SOP-001"
    assert sop.artifact_type == ARTIFACT_TYPE_SOP
    assert sop.status == ARTIFACT_STATUS_CANDIDATE
    assert "CLM-01" in sop.claim_ids
    assert "CLM-02" in sop.claim_ids
    assert "CLM-01" in sop.claim_map
    assert "QUY TRÌNH THAO TÁC CHUẨN" in sop.content_markdown
    assert "PROVENANCE MAP" in sop.content_markdown
    assert len(sop.digest) == 64

    # 2. Lesson
    lesson = generate_candidate_lesson(
        artifact_id="ART-LES-001",
        title="Xử lý biến động nhiệt độ khuôn",
        scope="ep_khuon",
        claims=[claim1, claim2],
        created_by="engineer_a",
    )
    assert lesson.artifact_id == "ART-LES-001"
    assert lesson.artifact_type == ARTIFACT_TYPE_LESSON
    assert lesson.status == ARTIFACT_STATUS_CANDIDATE
    assert "BÀI HỌC KINH NGHIỆM VẬN HÀNH" in lesson.content_markdown


def test_cannot_generate_artifact_from_conflicted_claim():
    """Test invariant: Cannot generate artifact from unresolved conflicted claim."""
    claim_ok = make_sample_claim("CLM-01", "ep_khuon", "Áp suất 3.5 bar.")
    claim_conflict = make_sample_claim("CLM-02", "ep_khuon", "Áp suất 5.0 bar.", status=CLAIM_STATUS_CONFLICTED)

    with pytest.raises(ConflictedClaimArtifactError, match="xung đột chưa giải quyết"):
        generate_candidate_sop(
            artifact_id="ART-SOP-ERR",
            title="Quy trình lỗi",
            scope="ep_khuon",
            claims=[claim_ok, claim_conflict],
            created_by="engineer_a",
        )


def test_self_approval_denied():
    """Test invariant: Self-approval policy strictly blocks author from approving own artifact."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_approval.sqlite"
        repo = ExpertInterviewRepository(database_path=db_path)
        case_repo = WorkspaceCaseRepository(database_path=db_path)
        service = ExpertInterviewService(store=case_repo, interview_repo=repo)

        claim = make_sample_claim("CLM-01", "ep_khuon", "Áp suất 3.5 bar.")
        sop = generate_candidate_sop(
            artifact_id="ART-SOP-100",
            title="Quy trình ép nhựa",
            scope="ep_khuon",
            claims=[claim],
            created_by="expert_phuong",
        )
        service.create_controlled_artifact(sop, idempotency_key="idemp_art_100")

        # Tác giả "expert_phuong" cố tình tự duyệt -> bị từ chối
        with pytest.raises(SelfApprovalDeniedError, match="không được phép tự phê duyệt"):
            service.submit_artifact_approval(
                approval_id="APP-01",
                artifact_id="ART-SOP-100",
                action=APPROVAL_ACTION_APPROVE,
                actor_id="expert_phuong",
                expected_digest=sop.digest,
                reason="Tự xác nhận quy trình đúng",
                idempotency_key="idemp_app_01",
            )


def test_stale_digest_approval_rejected():
    """Test invariant: Approval with outdated/tampered digest is rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_approval.sqlite"
        repo = ExpertInterviewRepository(database_path=db_path)
        case_repo = WorkspaceCaseRepository(database_path=db_path)
        service = ExpertInterviewService(store=case_repo, interview_repo=repo)

        claim = make_sample_claim("CLM-01", "ep_khuon", "Áp suất 3.5 bar.")
        sop = generate_candidate_sop(
            artifact_id="ART-SOP-101",
            title="Quy trình ép nhựa",
            scope="ep_khuon",
            claims=[claim],
            created_by="engineer_b",
        )
        service.create_controlled_artifact(sop, idempotency_key="idemp_art_101")

        with pytest.raises(StaleArtifactDigestError, match="Mã kiểm tra tài liệu không khớp"):
            service.submit_artifact_approval(
                approval_id="APP-02",
                artifact_id="ART-SOP-101",
                action=APPROVAL_ACTION_APPROVE,
                actor_id="qa_lead",
                expected_digest="tampered_or_stale_digest_12345678",
                reason="Phê duyệt dựa trên bản cũ",
                idempotency_key="idemp_app_02",
            )


def test_cannot_approve_artifact_when_claim_is_conflicted_in_repo():
    """Test invariant: Cannot approve artifact if any linked claim became conflicted in repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_approval.sqlite"
        repo = ExpertInterviewRepository(database_path=db_path)
        case_repo = WorkspaceCaseRepository(database_path=db_path)
        service = ExpertInterviewService(store=case_repo, interview_repo=repo)

        claim = make_sample_claim("CLM-CONF-01", "ep_khuon", "Áp suất 3.5 bar.", status=CLAIM_STATUS_CONFLICTED)
        repo.save_claim(claim, idempotency_key="idemp_c_conf")

        sop = ControlledKnowledgeArtifact(
            artifact_id="ART-SOP-CONF",
            artifact_type=ARTIFACT_TYPE_SOP,
            title="Quy trình xung đột",
            scope="ep_khuon",
            version="1.0",
            content_markdown="# SOP nội dung",
            claim_ids=("CLM-CONF-01",),
            created_by="engineer_b",
        )
        service.create_controlled_artifact(sop, idempotency_key="idemp_art_conf")

        with pytest.raises(ConflictedClaimArtifactError, match="xung đột chưa giải quyết"):
            service.submit_artifact_approval(
                approval_id="APP-03",
                artifact_id="ART-SOP-CONF",
                action=APPROVAL_ACTION_APPROVE,
                actor_id="qa_lead",
                expected_digest=sop.digest,
                reason="Thử duyệt quy trình có claim xung đột",
                idempotency_key="idemp_app_03",
            )


def test_approval_lifecycle_and_actions():
    """Test full lifecycle: candidate -> request_change -> approved -> revoked."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_approval.sqlite"
        repo = ExpertInterviewRepository(database_path=db_path)
        case_repo = WorkspaceCaseRepository(database_path=db_path)
        service = ExpertInterviewService(store=case_repo, interview_repo=repo)

        claim = make_sample_claim("CLM-01", "ep_khuon", "Áp suất 3.5 bar.")
        repo.save_claim(claim, idempotency_key="idemp_c1")

        sop = generate_candidate_sop(
            artifact_id="ART-SOP-200",
            title="Quy trình ép mẫu",
            scope="ep_khuon",
            claims=[claim],
            created_by="technician_c",
        )
        service.create_controlled_artifact(sop, idempotency_key="idemp_art_200")

        # 1. Request changes
        art_req = service.submit_artifact_approval(
            approval_id="APP-R1",
            artifact_id="ART-SOP-200",
            action=APPROVAL_ACTION_REQUEST_CHANGE,
            actor_id="qa_lead",
            expected_digest=sop.digest,
            reason="Cần bổ sung thời gian ép",
            idempotency_key="idemp_app_r1",
        )
        assert art_req.status == ARTIFACT_STATUS_CHANGES_REQUESTED

        # 2. Approve after revision
        art_app = service.submit_artifact_approval(
            approval_id="APP-R2",
            artifact_id="ART-SOP-200",
            action=APPROVAL_ACTION_APPROVE,
            actor_id="qa_lead",
            expected_digest=art_req.digest,
            reason="Đã đạt chuẩn kỹ thuật",
            idempotency_key="idemp_app_r2",
        )
        assert art_app.status == ARTIFACT_STATUS_APPROVED
        assert len(art_app.approvals) == 2

        # 3. Revoke
        art_rev = service.submit_artifact_approval(
            approval_id="APP-R3",
            artifact_id="ART-SOP-200",
            action=APPROVAL_ACTION_REVOKE,
            actor_id="plant_manager",
            expected_digest=art_app.digest,
            reason="Thay đổi dây chuyền công nghệ mới",
            idempotency_key="idemp_app_r3",
        )
        assert art_rev.status == ARTIFACT_STATUS_REVOKED


def test_artifact_diff_generation():
    """Test generating unified diff and conflict decision points between two versions."""
    claim1 = make_sample_claim("CLM-01", "ep_khuon", "Áp suất 3.5 bar.")
    claim2 = make_sample_claim("CLM-02", "ep_khuon", "Nhiệt độ 65 độ C.")
    claim3 = make_sample_claim("CLM-03", "ep_khuon", "Thời gian làm mát 15 giây.")

    v1 = generate_candidate_sop("ART-DIFF-01", "SOP Ép", "ep_khuon", [claim1, claim2], "eng_a", version="1.0")
    v2 = generate_candidate_sop("ART-DIFF-01", "SOP Ép", "ep_khuon", [claim2, claim3], "eng_a", version="2.0")

    diff_report = generate_artifact_diff(v1, v2)
    assert diff_report.old_version == "1.0"
    assert diff_report.new_version == "2.0"
    assert "CLM-03" in diff_report.added_claim_ids
    assert "CLM-01" in diff_report.removed_claim_ids
    assert len(diff_report.content_diff) > 0
    assert len(diff_report.conflict_decision_items) > 0


def test_artifact_persistence_and_listing():
    """Test saving and querying artifacts in SQLite repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_repo.sqlite"
        repo = ExpertInterviewRepository(database_path=db_path)
        repo.initialize()

        claim = make_sample_claim("CLM-01", "ep_khuon", "Áp suất 3.5 bar.")
        sop = generate_candidate_sop("ART-SOP-300", "SOP Ép", "ep_khuon", [claim], "eng_a")

        repo.save_artifact(sop, idempotency_key="idemp_300")
        fetched = repo.get_artifact("ART-SOP-300")
        assert fetched is not None
        assert fetched.title == "SOP Ép"
        assert fetched.scope == "ep_khuon"

        # Query by scope and status
        assert len(repo.list_artifacts(scope="ep_khuon")) == 1
        assert len(repo.list_artifacts(scope="khac")) == 0
        assert len(repo.list_artifacts(status=ARTIFACT_STATUS_CANDIDATE)) == 1
