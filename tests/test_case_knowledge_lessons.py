from __future__ import annotations

from pathlib import Path
import pytest

from aios_habit.workspace_case_authorization import (
    ActorContext,
    RoleGrant,
    WorkspaceCaseAuthorization,
    trusted_local_actor,
)
from aios_habit.workspace_case_models import (
    CASE_PRIVACY_LOCAL_ONLY,
    CASE_PROVENANCE_UNKNOWN,
    CASE_SCOPE_GENERAL,
    CASE_STATUS_DRAFT,
    EXPERT_DECISION_CONFIRMED,
    EXPERT_DECISION_NEEDS_MORE_EVIDENCE,
    EXPERT_DECISION_REJECTED,
    LESSON_STATUS_APPROVED,
    LESSON_STATUS_CANDIDATE,
    LESSON_STATUS_REVOKED,
    CaseEvidenceReference,
    CaseRecord,
)
from aios_habit.workspace_case_repository import WorkspaceCaseRepository
from aios_habit.workspace_case_service import CaseValidationError, WorkspaceCaseService


def _create_sample_case_with_review(
    service: WorkspaceCaseService,
    *,
    decision: str = EXPERT_DECISION_CONFIRMED,
    case_id: str = "CASE-US3-001",
) -> tuple[str, str]:
    trace_id = f"trace-{case_id}"
    case = CaseRecord(
        case_id=case_id,
        conversation_id=f"conv-{case_id}",
        assistant_message_id=f"msg-{case_id}",
        trace_id=trace_id,
        evidence_digest="a" * 64,
        title="Hồ sơ thử nghiệm US3 bài học kinh nghiệm",
        created_by="local_admin",
        owner_id="local_admin",
        scope=CASE_SCOPE_GENERAL,
    )
    ref = CaseEvidenceReference(
        reference_id=f"REF-{case_id}",
        case_id=case_id,
        trace_id=trace_id,
        evidence_node_id="library:sop-1:v1",
        citation_id="[1]",
        source_locator="docs/sop.pdf",
        source_title="Quy trình chuẩn",
        reference_digest="b" * 64,
        provenance_status=CASE_PROVENANCE_UNKNOWN,
        privacy_label=CASE_PRIVACY_LOCAL_ONLY,
    )
    service.store.create_case_with_evidence(case, [ref])

    req = service.request_expert_review(
        case_id,
        claim_digest=case.evidence_digest,
        question="Xác nhận nguyên nhân gốc BOWSKEW do jig lệch?",
        required_scope=CASE_SCOPE_GENERAL,
    )

    review = service.record_expert_review(
        req.request_id,
        decision=decision,
        rationale="Đã kiểm tra góc quét trên JIG 04 và xác nhận lệch 2.1 mrad.",
    )
    return case_id, review.review_id


def test_lesson_extraction_contract(tmp_path: Path) -> None:
    db_path = tmp_path / "workspace_cases.sqlite"
    repo = WorkspaceCaseRepository(db_path)
    service = WorkspaceCaseService(repo, actor_context=trusted_local_actor())

    # 1. Setup confirmed review
    case_id, review_id = _create_sample_case_with_review(service, decision=EXPERT_DECISION_CONFIRMED)

    # 2. Propose candidate lesson
    lesson = service.propose_lesson(
        case_id,
        review_id,
        title="Lệch góc quét do đệm JIG 04 bị mòn",
        content="Khi gặp sai số BOWSKEW 4 BEAM vượt ngưỡng 2.0 mrad, cần kiểm tra đệm JIG 04 trước khi thay mô tơ đa giác.",
    )

    assert lesson.lesson_id.startswith("LES-")
    assert lesson.case_id == case_id
    assert lesson.review_id == review_id
    assert lesson.claim_digest == "a" * 64
    assert lesson.evidence_digest == "a" * 64
    assert lesson.status == LESSON_STATUS_CANDIDATE
    assert lesson.version == 1
    assert lesson.created_by == "local_admin"
    assert lesson.approved_by is None

    # 3. Candidate lesson must NOT appear in normal approved search
    results = service.search_approved_lessons("BOWSKEW")
    assert len(results) == 0

    # 4. Attempting to propose lesson from a non-confirmed review must fail
    case_id_rej, review_id_rej = _create_sample_case_with_review(
        service, decision=EXPERT_DECISION_REJECTED, case_id="CASE-US3-REJ"
    )
    with pytest.raises(CaseValidationError, match="LESSON_PROPOSE_CONFIRMED_REVIEW_REQUIRED"):
        service.propose_lesson(
            case_id_rej,
            review_id_rej,
            title="Bài học từ chối",
            content="Nội dung không hợp lệ vì review bị từ chối.",
        )


def test_lesson_lifecycle_promotion_and_search(tmp_path: Path) -> None:
    db_path = tmp_path / "workspace_cases.sqlite"
    repo = WorkspaceCaseRepository(db_path)
    service = WorkspaceCaseService(repo, actor_context=trusted_local_actor())

    case_id, review_id = _create_sample_case_with_review(service, decision=EXPERT_DECISION_CONFIRMED)
    lesson = service.propose_lesson(
        case_id,
        review_id,
        title="Quy trình hiệu chuẩn cảm biến Iris",
        content="Cần vệ sinh gương phản xạ số 2 bằng cồn 99% trước khi đo baseline.",
    )

    # Edit lesson
    updated = service.update_lesson(
        lesson.lesson_id,
        expected_version=1,
        title="Quy trình hiệu chuẩn cảm biến Iris LSU",
        content="Cần vệ sinh gương phản xạ số 2 bằng cồn 99% và để khô 5 phút trước khi đo baseline.",
    )
    assert updated.version == 2
    assert updated.title == "Quy trình hiệu chuẩn cảm biến Iris LSU"

    # Approve (promote) lesson
    approved = service.approve_lesson(lesson.lesson_id, expected_version=2)
    assert approved.status == LESSON_STATUS_APPROVED
    assert approved.version == 3
    assert approved.approved_by == "local_admin"
    assert approved.approved_at is not None

    # Now search finds the lesson
    search_hits = service.search_approved_lessons("Iris LSU")
    assert len(search_hits) == 1
    assert search_hits[0].lesson_id == lesson.lesson_id
    assert search_hits[0].title == "Quy trình hiệu chuẩn cảm biến Iris LSU"

    # Search by keyword in content
    content_hits = service.search_approved_lessons("gương phản xạ")
    assert len(content_hits) == 1
    assert content_hits[0].lesson_id == lesson.lesson_id

    # Revoke lesson
    revoked = service.revoke_lesson(
        lesson.lesson_id,
        expected_version=3,
        reason="Quy trình đã được thay thế bởi bản cập nhật SOP 2026-09.",
    )
    assert revoked.status == LESSON_STATUS_REVOKED
    assert revoked.version == 4
    assert revoked.revocation_reason == "Quy trình đã được thay thế bởi bản cập nhật SOP 2026-09."

    # Revoked lesson immediately disappears from search
    after_revoke_hits = service.search_approved_lessons("Iris LSU")
    assert len(after_revoke_hits) == 0


def test_lesson_optimistic_concurrency_conflict(tmp_path: Path) -> None:
    db_path = tmp_path / "workspace_cases.sqlite"
    repo = WorkspaceCaseRepository(db_path)
    service = WorkspaceCaseService(repo, actor_context=trusted_local_actor())

    case_id, review_id = _create_sample_case_with_review(service, decision=EXPERT_DECISION_CONFIRMED)
    lesson = service.propose_lesson(
        case_id,
        review_id,
        title="Bài học đồng thời",
        content="Kiểm tra xung đột version.",
    )

    # Attempt to update with wrong expected version
    with pytest.raises(CaseValidationError, match="CONCURRENT_UPDATE_CONFLICT"):
        service.update_lesson(
            lesson.lesson_id,
            expected_version=99,
            title="Tiêu đề sửa sai version",
            content="Nội dung mới.",
        )


def test_lesson_activity_chain_and_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "workspace_cases.sqlite"
    repo = WorkspaceCaseRepository(db_path)
    service = WorkspaceCaseService(repo, actor_context=trusted_local_actor())

    case_id, review_id = _create_sample_case_with_review(service, decision=EXPERT_DECISION_CONFIRMED)
    lesson = service.propose_lesson(
        case_id,
        review_id,
        title="Bài học bền vững sau khởi động lại",
        content="Dữ liệu bài học phải toàn vẹn khi đóng mở kết nối.",
    )
    service.approve_lesson(lesson.lesson_id, expected_version=1)

    # Verify activity chain
    assert repo.verify_activity_chain(case_id) is True

    # Reconnect repo and service
    repo2 = WorkspaceCaseRepository(db_path)
    service2 = WorkspaceCaseService(repo2, actor_context=trusted_local_actor())

    detail = service2.get_case_detail(case_id)
    assert len(detail.lessons) == 1
    assert detail.lessons[0].lesson_id == lesson.lesson_id
    assert detail.lessons[0].status == LESSON_STATUS_APPROVED
    assert detail.lessons[0].title == "Bài học bền vững sau khởi động lại"

    # Search approved works on reopened DB
    results = service2.search_approved_lessons("bền vững")
    assert len(results) == 1
    assert results[0].lesson_id == lesson.lesson_id
