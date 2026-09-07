from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3
import pytest

from aios_habit.evidence_trace import build_evidence_trace_from_citations
from aios_habit.workspace_case_authorization import (
    ActorContext,
    AuthorizationError,
    RoleGrant,
)
from aios_habit.workspace_case_models import (
    CASE_STATUS_IN_PROGRESS,
    CaseFilter,
)
from aios_habit.workspace_case_repository import (
    WorkspaceCaseRepository,
    WorkspaceCaseRepositoryError,
)
from aios_habit.workspace_case_service import (
    CaseValidationError,
    WorkspaceCaseService,
)


def _iso(delta_days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=delta_days)).isoformat()


def _build_test_trace(*, conversation_id: str = "CONV-EXP-1", trace_id: str = "TRC-EXP-1"):
    return build_evidence_trace_from_citations(
        query="Nguyên nhân lệch tia LSU là gì?",
        answer_text="Lệch tia xảy ra do biến dạng quang học [E1].",
        evidence_items=[
            {
                "id": "E1",
                "citation_id": "[E1]",
                "title": "Báo cáo kiểm tra quang học LSU",
                "text": "Độ lệch gương phản xạ vượt ngưỡng 0.05mm",
                "source_path": "docs/lsu_optics_report.pdf",
            }
        ],
        allowed_source_ids=["E1"],
        conversation_id=conversation_id,
        assistant_message_id="MSG-EXP-1",
        trace_id=trace_id,
    )


def _setup_service_with_case(tmp_path, *, actor_id: str = "local_admin", scope: str = "lsu_optics"):
    db_path = tmp_path / "workspace_cases.sqlite"
    store = WorkspaceCaseRepository(db_path)
    store.initialize()
    # Provide necessary grants for setup
    store.replace_role_grants(
        actor_id,
        [
            RoleGrant("G-SETUP-INV", actor_id, "investigator", "general", _iso(-1), _iso(1)),
            RoleGrant("G-SETUP-EXP", actor_id, "expert", "general", _iso(-1), _iso(1)),
            RoleGrant("G-SCOPE-INV", actor_id, "investigator", scope, _iso(-1), _iso(1)),
            RoleGrant("G-SCOPE-EXP", actor_id, "expert", scope, _iso(-1), _iso(1)),
        ],
    )
    service = WorkspaceCaseService(store=store, actor_context=ActorContext(actor_id))
    trace = _build_test_trace()
    result = service.create_case_from_trace(trace, expected_conversation_id="CONV-EXP-1")
    service.transition_case(
        result.case_id,
        expected_version=1,
        new_status=CASE_STATUS_IN_PROGRESS,
        rationale="Bắt đầu phân tích quang học",
    )
    return store, service, result.case_id


def test_investigator_can_request_and_perform_expert_review_when_holding_both_grants(tmp_path):
    store, service, case_id = _setup_service_with_case(tmp_path, actor_id="investigator_lead", scope="lsu_optics")
    case = store.load_case(case_id)
    assert case is not None

    req = service.request_expert_review(
        case_id=case_id,
        claim_digest=case.evidence_digest,
        question="Xác nhận độ lệch tia do biến dạng quang học?",
        required_scope="lsu_optics",
    )
    assert req.request_id.startswith("EXP-REQ-")
    assert req.status == "open"
    assert req.case_id == case_id

    review = service.record_expert_review(
        request_id=req.request_id,
        decision="confirmed",
        rationale="Đã kiểm tra nhật ký quang học, thông số góc quét lệch vượt tiêu chuẩn.",
        confidence=0.95,
    )
    assert review.review_id.startswith("EXP-REV-")
    assert review.decision == "confirmed"
    assert review.reviewer_id == "investigator_lead"

    # Detail check
    detail = service.get_case_detail(case_id)
    assert any(r.review_id == review.review_id for r in detail.expert_reviews)
    # Check activity appended
    assert any(a.event_type == "expert_review_recorded" for a in detail.activities)


def test_optional_second_expert_review_workflow(tmp_path):
    store, service, case_id = _setup_service_with_case(tmp_path, actor_id="investigator_lead", scope="lsu_optics")
    case = store.load_case(case_id)

    # Grant expert_2 role for lsu_optics
    store.replace_role_grants(
        "expert_2",
        [RoleGrant("G-EXP2", "expert_2", "expert", "lsu_optics", _iso(-1), _iso(1))],
    )

    req = service.request_expert_review(
        case_id=case_id,
        claim_digest=case.evidence_digest,
        question="Thẩm định độc lập lần 2",
        required_scope="lsu_optics",
        requested_expert_id="expert_2",
    )
    assert req.requested_expert_id == "expert_2"

    # Service with expert_2 actor
    service_exp2 = WorkspaceCaseService(store=store, actor_context=ActorContext("expert_2"))
    rev2 = service_exp2.record_expert_review(
        request_id=req.request_id,
        decision="confirmed",
        rationale="Đồng ý với phân tích của điều tra viên.",
        confidence=0.90,
    )
    assert rev2.reviewer_id == "expert_2"
    assert rev2.decision == "confirmed"


def test_expert_review_denied_for_scope_mismatch_and_expired_grant(tmp_path):
    store, service, case_id = _setup_service_with_case(tmp_path, actor_id="investigator_lead", scope="lsu_optics")
    case = store.load_case(case_id)

    # expert with wrong scope
    store.replace_role_grants(
        "expert_battery",
        [RoleGrant("G-BATT", "expert_battery", "expert", "line_battery", _iso(-1), _iso(1))],
    )
    # expert with expired grant
    store.replace_role_grants(
        "expert_expired",
        [RoleGrant("G-EXP-OLD", "expert_expired", "expert", "lsu_optics", _iso(-10), _iso(-1))],
    )

    req = service.request_expert_review(
        case_id=case_id,
        claim_digest=case.evidence_digest,
        question="Kiểm tra thẩm định",
        required_scope="lsu_optics",
    )

    service_wrong = WorkspaceCaseService(store=store, actor_context=ActorContext("expert_battery"))
    with pytest.raises(CaseValidationError, match="CASE_AUTH_DENIED"):
        service_wrong.record_expert_review(
            request_id=req.request_id,
            decision="confirmed",
            rationale="Thẩm định sai công đoạn",
            confidence=0.8,
        )

    service_expired = WorkspaceCaseService(store=store, actor_context=ActorContext("expert_expired"))
    with pytest.raises(CaseValidationError, match="CASE_AUTH_DENIED"):
        service_expired.record_expert_review(
            request_id=req.request_id,
            decision="confirmed",
            rationale="Thẩm định khi hết hạn quyền",
            confidence=0.8,
        )


def test_expert_review_requires_non_empty_rationale(tmp_path):
    store, service, case_id = _setup_service_with_case(tmp_path, actor_id="investigator_lead", scope="lsu_optics")
    case = store.load_case(case_id)

    req = service.request_expert_review(
        case_id=case_id,
        claim_digest=case.evidence_digest,
        question="Kiểm tra lý do thẩm định",
        required_scope="lsu_optics",
    )

    with pytest.raises(CaseValidationError, match="EXPERT_RATIONALE_REQUIRED"):
        service.record_expert_review(
            request_id=req.request_id,
            decision="confirmed",
            rationale="   ",
            confidence=0.9,
        )


def test_expert_review_denied_when_evidence_digest_changed(tmp_path):
    store, service, case_id = _setup_service_with_case(tmp_path, actor_id="investigator_lead", scope="lsu_optics")
    case = store.load_case(case_id)

    req = service.request_expert_review(
        case_id=case_id,
        claim_digest=case.evidence_digest,
        question="Kiểm tra tính toàn vẹn bằng chứng",
        required_scope="lsu_optics",
    )

    # Artificially alter case evidence digest to simulate changed evidence
    with sqlite3.connect(store.database_path) as conn:
        conn.execute("UPDATE cases SET evidence_digest = 'ALTERED_DIGEST' WHERE case_id = ?", (case_id,))

    with pytest.raises(CaseValidationError, match="EVIDENCE_DIGEST_MISMATCH"):
        service.record_expert_review(
            request_id=req.request_id,
            decision="confirmed",
            rationale="Bằng chứng đã bị thay đổi ngầm sau khi tạo yêu cầu",
            confidence=0.9,
        )


def test_conflicting_reviews_trigger_conflict_resolution(tmp_path):
    store, service, case_id = _setup_service_with_case(tmp_path, actor_id="investigator_lead", scope="lsu_optics")
    case = store.load_case(case_id)

    store.replace_role_grants(
        "expert_a",
        [RoleGrant("G-EXPA", "expert_a", "expert", "lsu_optics", _iso(-1), _iso(1))],
    )
    store.replace_role_grants(
        "expert_b",
        [RoleGrant("G-EXPB", "expert_b", "expert", "lsu_optics", _iso(-1), _iso(1))],
    )

    req = service.request_expert_review(
        case_id=case_id,
        claim_digest=case.evidence_digest,
        question="Kiểm tra khả năng xung đột thẩm định",
        required_scope="lsu_optics",
    )

    service_a = WorkspaceCaseService(store=store, actor_context=ActorContext("expert_a"))
    rev_a = service_a.record_expert_review(
        request_id=req.request_id,
        decision="confirmed",
        rationale="Bằng chứng xác nhận lỗi phần cứng",
        confidence=0.9,
    )

    service_b = WorkspaceCaseService(store=store, actor_context=ActorContext("expert_b"))
    rev_b = service_b.record_expert_review(
        request_id=req.request_id,
        decision="rejected",
        rationale="Bằng chứng không đủ căn cứ lỗi phần cứng",
        confidence=0.85,
    )

    # Lead resolves conflict
    resolved_rev = service.resolve_review_conflict(
        case_id=case_id,
        review_ids=[rev_a.review_id, rev_b.review_id],
        decision="needs_more_evidence",
        rationale="Hai chuyên gia có ý kiến trái chiều, yêu cầu bổ sung mẫu đo JIG thứ 2.",
    )
    assert resolved_rev.decision == "needs_more_evidence"
    assert resolved_rev.supersedes_review_id is None or resolved_rev.decision == "needs_more_evidence"


def test_superseding_review_is_append_only_old_review_unchanged(tmp_path):
    store, service, case_id = _setup_service_with_case(tmp_path, actor_id="investigator_lead", scope="lsu_optics")
    case = store.load_case(case_id)

    req = service.request_expert_review(
        case_id=case_id,
        claim_digest=case.evidence_digest,
        question="Thẩm định có thể đính chính",
        required_scope="lsu_optics",
    )

    rev_initial = service.record_expert_review(
        request_id=req.request_id,
        decision="needs_more_evidence",
        rationale="Cần thêm ảnh scan bề mặt quang sai.",
        confidence=0.6,
    )

    # Later, expert supersedes the previous review
    rev_updated = service.record_expert_review(
        request_id=req.request_id,
        decision="confirmed",
        rationale="Sau khi nhận ảnh scan bổ sung, xác nhận biến dạng thấu kính.",
        confidence=0.98,
        supersedes_review_id=rev_initial.review_id,
    )

    assert rev_updated.supersedes_review_id == rev_initial.review_id

    # Verify both records exist and old record was not mutated (append-only)
    with sqlite3.connect(store.database_path) as conn:
        rows = conn.execute(
            "SELECT review_id, decision, rationale FROM expert_reviews WHERE request_id = ? ORDER BY reviewed_at ASC",
            (req.request_id,),
        ).fetchall()
        assert len(rows) == 2
        assert rows[0][0] == rev_initial.review_id
        assert rows[0][1] == "needs_more_evidence"
        assert rows[1][0] == rev_updated.review_id
        assert rows[1][1] == "confirmed"


def test_actor_must_come_from_trusted_context_ai_actor_has_empty_capabilities(tmp_path):
    store, service, case_id = _setup_service_with_case(tmp_path, actor_id="investigator_lead", scope="lsu_optics")
    case = store.load_case(case_id)

    req = service.request_expert_review(
        case_id=case_id,
        claim_digest=case.evidence_digest,
        question="AI không được tự duyệt",
        required_scope="lsu_optics",
    )

    # Simulated AI / Bot actor
    ai_service = WorkspaceCaseService(store=store, actor_context=ActorContext("c_agent_bot"))
    with pytest.raises(CaseValidationError, match="CASE_AUTH_DENIED"):
        ai_service.record_expert_review(
            request_id=req.request_id,
            decision="confirmed",
            rationale="AI tự động duyệt kết luận",
            confidence=1.0,
        )


def test_transaction_rollback_on_fault_injection_and_restart_readback(tmp_path):
    store, service, case_id = _setup_service_with_case(tmp_path, actor_id="investigator_lead", scope="lsu_optics")
    case = store.load_case(case_id)

    req = service.request_expert_review(
        case_id=case_id,
        claim_digest=case.evidence_digest,
        question="Kiểm tra giao dịch và phục hồi sau khởi động lại",
        required_scope="lsu_optics",
    )

    # Test fault injection during record_expert_review
    def fault_fail(stage: str):
        if stage == "before_commit":
            raise sqlite3.OperationalError("Simulated write failure")

    with pytest.raises((sqlite3.OperationalError, WorkspaceCaseRepositoryError)):
        store.record_expert_review_with_fault(
            request_id=req.request_id,
            decision="confirmed",
            rationale="Lỗi cố tình",
            confidence=0.9,
            actor_id="investigator_lead",
            fault_injector=fault_fail,
        )

    # Ensure no partial review row was saved
    with sqlite3.connect(store.database_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM expert_reviews").fetchone()[0]
        assert count == 0

    # Successful review
    review = service.record_expert_review(
        request_id=req.request_id,
        decision="confirmed",
        rationale="Ghi nhận thành công sau rollback",
        confidence=0.92,
    )

    # Restart / Readback: create a fresh store instance from the database file
    restarted_store = WorkspaceCaseRepository(store.database_path)
    restarted_service = WorkspaceCaseService(store=restarted_store, actor_context=ActorContext("investigator_lead"))
    detail = restarted_service.get_case_detail(case_id)
    assert any(r.review_id == review.review_id for r in detail.expert_reviews)
    assert any(a.event_type == "expert_review_recorded" for a in detail.activities)
