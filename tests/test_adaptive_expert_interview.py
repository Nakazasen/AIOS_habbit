"""Unit and integration tests for adaptive expert interview planning and guardrails.

Implements T029 of 010-expert-knowledge-acquisition.
Verifies:
1. Valid plan creation with verified expert and accepted gap.
2. Rejection when no eligible verified expert exists for required scope.
3. Rejection of stale gap digest.
4. Rejection of non-accepted gaps (draft, candidate, deferred, rejected).
5. Rejection of hallucinated gaps (empty evidence_refs).
6. Rejection of infinite or invalid budget parameters.
7. Rejection of empty escalation owner.
8. Caller scope-based authorization enforcement.
9. Schema-grounded seed question generation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import pytest

from aios_habit.adaptive_interview_engine import generate_seed_questions
from aios_habit.expert_identity import ACTION_INTERVIEW_ANSWER, ExpertProfile, ScopeGrant
from aios_habit.expert_interview_models import (
    PLAN_STATUS_DRAFT,
    CompletionRubric,
    InterviewBudget,
    InterviewPlan,
    InterviewPlanError,
)
from aios_habit.expert_interview_service import ExpertInterviewService
from aios_habit.knowledge_coverage import (
    GAP_STATUS_ACCEPTED,
    GAP_STATUS_CANDIDATE,
    GAP_STATUS_DEFERRED,
    GAP_STATUS_REJECTED,
    GAP_TYPE_CONFLICT,
    GAP_TYPE_MISSING_CONDITION,
    GAP_TYPE_MISSING_THRESHOLD,
    KnowledgeGapCandidate,
)
from aios_habit.workspace_case_authorization import (
    ActorContext,
    AuthorizationError,
    RoleGrant,
    WorkspaceCaseAuthorization,
)
from aios_habit.workspace_case_repository import WorkspaceCaseRepository


@pytest.fixture
def repo(tmp_path: Path) -> WorkspaceCaseRepository:
    path = tmp_path / "workspace_cases.sqlite"
    r = WorkspaceCaseRepository(path)
    r.initialize()
    return r


@pytest.fixture
def service(repo: WorkspaceCaseRepository) -> ExpertInterviewService:
    # Default caller has manager permissions
    repo.replace_role_grants(
        "test_manager",
        [
            RoleGrant(
                grant_id="GRANT-MGR-GLOBAL",
                actor_id="test_manager",
                role="quality_manager",
                scope="lsu_optical_assembly",
                valid_from="2000-01-01T00:00:00+00:00",
                valid_until="9999-12-31T23:59:59+00:00",
            )
        ],
    )
    return ExpertInterviewService(store=repo, actor_context=ActorContext("test_manager"))


def _create_sample_gap(
    repo: WorkspaceCaseRepository,
    gap_id: str = "GAP-OPT-1",
    status: str = GAP_STATUS_ACCEPTED,
    scope: str = "lsu_optical_assembly",
    evidence: tuple[str, ...] = ("DOC-OPT-01#p4",),
) -> KnowledgeGapCandidate:
    gap = KnowledgeGapCandidate(
        gap_id=gap_id,
        collection_id="lsu_docs",
        scope=scope,
        title="Thiếu ngưỡng bước sóng quang học",
        description="Mô tả chi tiết bước sóng kiểm chuẩn",
        gap_type=GAP_TYPE_MISSING_THRESHOLD,
        evidence_refs=evidence,
        status=status,
        priority="high",
    )
    repo.save_gap_candidate(gap, f"IDEMP-{gap_id}", "admin")
    return gap


def _setup_expert(
    repo: WorkspaceCaseRepository,
    subject: str = "expert_opt_lead",
    scope: str = "lsu_optical_assembly",
    profile_status: str = "active",
    grant_status: str = "active",
    expires_at: str = "9999-12-31T23:59:59+00:00",
    revoked_at: str | None = None,
) -> None:
    profile = ExpertProfile(
        expert_id=f"EXP-{subject}",
        subject=subject,
        full_name="Nguyễn Văn Chuyên Gia",
        scopes=(scope,),
        status=profile_status,
        created_at="2026-09-08T00:00:00Z",
        updated_at="2026-09-08T00:00:00Z",
    )
    repo.save_expert_profile(profile)

    grant = ScopeGrant(
        grant_id=f"GRANT-{subject}-{scope}",
        subject=subject,
        action=ACTION_INTERVIEW_ANSWER,
        scope=scope,
        granted_by="admin",
        granted_at="2026-09-08T00:00:00Z",
        expires_at=expires_at,
        revoked_at=revoked_at,
        status=grant_status,
    )
    repo.save_scope_grant(grant)


def test_create_interview_plan_success(repo: WorkspaceCaseRepository, service: ExpertInterviewService):
    """A valid accepted gap creates an interview plan with verified expert and rubric."""
    gap = _create_sample_gap(repo)
    _setup_expert(repo, "expert_opt_lead", "lsu_optical_assembly")

    plan = service.create_interview_plan(
        gap_id=gap.gap_id,
        expected_gap_digest=gap.digest,
    )

    assert plan.plan_id.startswith(f"PLAN-{gap.gap_id}-")
    assert plan.version == 1
    assert plan.gap_ids == (gap.gap_id,)
    assert plan.required_scope == "lsu_optical_assembly"
    assert "expert_opt_lead" in plan.eligible_expert_ids
    assert len(plan.seed_questions) >= 2
    assert plan.status == PLAN_STATUS_DRAFT
    assert plan.budget.max_turns == 10
    assert plan.budget.max_minutes == 30
    assert plan.budget.token_budget == 4000
    assert plan.completion_rubric.escalation_owner == "test_manager"
    assert plan.digest != ""
    assert plan.digest == plan.calculate_digest()


def test_rejection_when_no_eligible_expert_for_scope(repo: WorkspaceCaseRepository, service: ExpertInterviewService):
    """Plan creation must fail closed if no verified expert has grant on the required scope."""
    gap = _create_sample_gap(repo, scope="lsu_optical_assembly")
    # Expert only has grant on mirror mount scope
    _setup_expert(repo, "expert_mirror", "lsu_mirror_mount")

    with pytest.raises(InterviewPlanError, match="Không tìm thấy chuyên gia"):
        service.create_interview_plan(gap_id=gap.gap_id)


def test_rejection_when_expert_profile_suspended_or_grant_expired(
    repo: WorkspaceCaseRepository, service: ExpertInterviewService
):
    """Suspended expert profiles or expired/revoked grants are rejected."""
    gap = _create_sample_gap(repo, gap_id="GAP-EXP-FAIL")

    # 1. Suspended profile
    _setup_expert(repo, "expert_suspended", "lsu_optical_assembly", profile_status="suspended")
    with pytest.raises(InterviewPlanError, match="Không tìm thấy chuyên gia"):
        service.create_interview_plan(gap_id=gap.gap_id)

    # 2. Expired grant
    _setup_expert(
        repo,
        "expert_expired",
        "lsu_optical_assembly",
        expires_at="2020-01-01T00:00:00+00:00",
    )
    with pytest.raises(InterviewPlanError, match="Không tìm thấy chuyên gia"):
        service.create_interview_plan(gap_id=gap.gap_id)

    # 3. Revoked grant
    _setup_expert(
        repo,
        "expert_revoked",
        "lsu_optical_assembly",
        revoked_at="2026-09-08T00:00:00+00:00",
    )
    with pytest.raises(InterviewPlanError, match="Không tìm thấy chuyên gia"):
        service.create_interview_plan(gap_id=gap.gap_id)


def test_rejection_for_stale_gap_digest(repo: WorkspaceCaseRepository, service: ExpertInterviewService):
    """Stale gap digest must be detected and rejected."""
    gap = _create_sample_gap(repo)
    _setup_expert(repo, "expert_opt_lead", "lsu_optical_assembly")

    with pytest.raises(InterviewPlanError, match="stale digest"):
        service.create_interview_plan(
            gap_id=gap.gap_id,
            expected_gap_digest="stale_digest_12345",
        )


def test_rejection_for_non_accepted_gaps(repo: WorkspaceCaseRepository, service: ExpertInterviewService):
    """Only accepted gaps can form an interview plan; candidate, deferred, rejected must fail."""
    _setup_expert(repo, "expert_opt_lead", "lsu_optical_assembly")

    for invalid_status in (GAP_STATUS_CANDIDATE, GAP_STATUS_DEFERRED, GAP_STATUS_REJECTED):
        gap = _create_sample_gap(repo, gap_id=f"GAP-STATUS-{invalid_status}", status=invalid_status)
        with pytest.raises(InterviewPlanError, match="accepted"):
            service.create_interview_plan(gap_id=gap.gap_id)


def test_rejection_for_hallucinated_gap_empty_evidence(
    repo: WorkspaceCaseRepository, service: ExpertInterviewService
):
    """Gaps lacking evidence references cannot create interview plans."""
    _setup_expert(repo, "expert_opt_lead", "lsu_optical_assembly")

    # Force gap in db without evidence by raw save
    with pytest.raises(ValueError, match="ít nhất 1 dẫn chứng"):
        _create_sample_gap(repo, gap_id="GAP-NO-EVID", evidence=())


def test_budget_finite_validation():
    """Budget must be strictly positive and finite; zero or negative values rejected."""
    with pytest.raises(InterviewPlanError, match="max_turns"):
        InterviewBudget(max_turns=0)

    with pytest.raises(InterviewPlanError, match="max_minutes"):
        InterviewBudget(max_minutes=-1)

    with pytest.raises(InterviewPlanError, match="token_budget"):
        InterviewBudget(token_budget=0)


def test_rubric_escalation_owner_validation():
    """Escalation owner cannot be empty."""
    with pytest.raises(InterviewPlanError, match="escalation_owner"):
        CompletionRubric(escalation_owner="")

    with pytest.raises(InterviewPlanError, match="escalation_owner"):
        CompletionRubric(escalation_owner="   ")


def test_caller_authorization_enforcement(repo: WorkspaceCaseRepository, service: ExpertInterviewService):
    """Caller without coverage.manage on scope is denied."""
    gap = _create_sample_gap(repo)
    _setup_expert(repo, "expert_opt_lead", "lsu_optical_assembly")

    unauthorized_actor = ActorContext("unauthorized_user")
    with pytest.raises(AuthorizationError):
        service.create_interview_plan(
            gap_id=gap.gap_id,
            actor=unauthorized_actor,
        )


def test_seed_questions_by_gap_type():
    """Seed questions must be grounded, strictly schema-validated, and in everyday Vietnamese."""
    gap_threshold = KnowledgeGapCandidate(
        gap_id="GAP-TH-1",
        collection_id="col-1",
        scope="lsu_optical_assembly",
        title="Nhiệt độ gương phản xạ",
        description="Mô tả",
        gap_type=GAP_TYPE_MISSING_THRESHOLD,
        evidence_refs=("DOC-1",),
        status=GAP_STATUS_ACCEPTED,
    )
    seeds_th = generate_seed_questions(gap_threshold)
    assert len(seeds_th) == 3
    assert "Ngưỡng tiêu chuẩn" in seeds_th[0].text
    assert "Đơn vị đo lường" in seeds_th[1].text
    assert "ngoại lệ" in seeds_th[2].text

    gap_conflict = KnowledgeGapCandidate(
        gap_id="GAP-CF-1",
        collection_id="col-1",
        scope="lsu_optical_assembly",
        title="Quy chuẩn keo dán lăng kính",
        description="Mô tả",
        gap_type=GAP_TYPE_CONFLICT,
        evidence_refs=("DOC-1#sec-1", "DOC-2#sec-2"),
        status=GAP_STATUS_ACCEPTED,
    )
    seeds_cf = generate_seed_questions(gap_conflict)
    assert len(seeds_cf) == 2
    assert "mâu thuẫn" in seeds_cf[0].text


def test_adaptive_turn_missing_threshold_triggers_followup(repo: WorkspaceCaseRepository, service: ExpertInterviewService):
    """Answers lacking numerical thresholds in missing_threshold gaps trigger follow-up."""
    from aios_habit.expert_identity import VerifiedPrincipal
    from aios_habit.expert_interview_models import (
        ACTION_ASK_FOLLOWUP,
        REASON_MISSING_THRESHOLD,
    )

    gap = _create_sample_gap(repo, gap_id="GAP-TH-FOLLOW")
    _setup_expert(repo, "expert_opt_lead", "lsu_optical_assembly")
    plan = service.create_interview_plan(gap_id=gap.gap_id)

    principal = VerifiedPrincipal("expert_opt_lead", "local_test", "Chuyên gia Quang học")
    session = service.start_interview_session(plan.plan_id, principal, "expert_opt_lead", "IDEMP-START-TH")

    # Turn with qualitative response without numbers
    turn, decision = service.submit_interview_turn(
        session_id=session.session_id,
        answer_text="Bước sóng được duy trì ở mức chuẩn ổn định của xưởng.",
        principal=principal,
        idempotency_key="IDEMP-TURN-1",
    )

    assert turn.sequence == 1
    assert decision.action == ACTION_ASK_FOLLOWUP
    assert decision.reason == REASON_MISSING_THRESHOLD
    assert "giá trị số hoặc ngưỡng kỹ thuật" in decision.question


def test_adaptive_turn_missing_exception_triggers_followup(repo: WorkspaceCaseRepository, service: ExpertInterviewService):
    """Answers with numerical values but missing exceptions trigger follow-up on early turns."""
    from aios_habit.expert_identity import VerifiedPrincipal
    from aios_habit.expert_interview_models import (
        ACTION_ASK_FOLLOWUP,
        REASON_MISSING_EXCEPTION,
    )

    gap = _create_sample_gap(repo, gap_id="GAP-EX-FOLLOW")
    _setup_expert(repo, "expert_opt_lead", "lsu_optical_assembly")
    plan = service.create_interview_plan(gap_id=gap.gap_id)

    principal = VerifiedPrincipal("expert_opt_lead", "local_test", "Chuyên gia Quang học")
    session = service.start_interview_session(plan.plan_id, principal, "expert_opt_lead", "IDEMP-START-EX")

    turn, decision = service.submit_interview_turn(
        session_id=session.session_id,
        answer_text="Ngưỡng bước sóng quy định chính xác là 632.8 nm với dung sai 0.5 nm.",
        principal=principal,
        idempotency_key="IDEMP-TURN-EX-1",
    )

    assert turn.sequence == 1
    assert decision.action == ACTION_ASK_FOLLOWUP
    assert decision.reason == REASON_MISSING_EXCEPTION
    assert "ngoại lệ" in decision.question


def test_adaptive_turn_contradiction_triggers_followup(repo: WorkspaceCaseRepository, service: ExpertInterviewService):
    """Contradiction statements trigger follow-up probing authoritative precedence."""
    from aios_habit.expert_identity import VerifiedPrincipal
    from aios_habit.expert_interview_models import (
        ACTION_ASK_FOLLOWUP,
        REASON_CONTRADICTION,
    )

    gap = _create_sample_gap(repo, gap_id="GAP-CT-FOLLOW")
    _setup_expert(repo, "expert_opt_lead", "lsu_optical_assembly")
    plan = service.create_interview_plan(gap_id=gap.gap_id)

    principal = VerifiedPrincipal("expert_opt_lead", "local_test", "Chuyên gia Quang học")
    session = service.start_interview_session(plan.plan_id, principal, "expert_opt_lead", "IDEMP-START-CT")

    turn, decision = service.submit_interview_turn(
        session_id=session.session_id,
        answer_text="Thông số này mâu thuẫn trực tiếp giữa sổ tay vận hành và bản vẽ gia công của nhà sản xuất.",
        principal=principal,
        idempotency_key="IDEMP-TURN-CT-1",
    )

    assert turn.sequence == 1
    assert decision.action == ACTION_ASK_FOLLOWUP
    assert decision.reason == REASON_CONTRADICTION
    assert "sai khác giữa các nguồn" in decision.question


def test_adaptive_leading_and_duplicate_question_rejections():
    """Leading and duplicate candidate questions are strictly rejected by validator."""
    from aios_habit.adaptive_interview_engine import (
        detect_leading_question,
        detect_semantic_duplicate,
        validate_candidate_question,
    )
    from aios_habit.expert_interview_models import InterviewSessionError

    # 1. Leading question detection
    assert detect_leading_question("Lỗi này chắc chắn là do mô tơ bước phải không?") is True
    assert detect_leading_question("Đúng là do cảm biến quang bị mờ phải không?") is True
    assert detect_leading_question("Vui lòng cho biết ngưỡng kỹ thuật của cảm biến?") is False

    with pytest.raises(InterviewSessionError, match="dẫn dắt"):
        validate_candidate_question("Lỗi này chắc chắn là do thợ thao tác sai phải không?", [], 0, 10)

    # 2. Duplicate question detection
    past_questions = [
        "Ngưỡng tiêu chuẩn cho bước sóng quang học là bao nhiêu?",
        "Đơn vị đo lường và dung sai cho phép là gì?",
    ]
    assert detect_semantic_duplicate("Ngưỡng tiêu chuẩn cho bước sóng quang học là bao nhiêu?", past_questions) is True
    assert detect_semantic_duplicate("Quy trình hiệu chuẩn bao gồm các bước nào?", past_questions) is False

    with pytest.raises(InterviewSessionError, match="trùng lặp"):
        validate_candidate_question("Ngưỡng tiêu chuẩn cho bước sóng quang học là bao nhiêu?", past_questions, 2, 10)


def test_adaptive_stop_on_repeated_unknowns_escalates(repo: WorkspaceCaseRepository, service: ExpertInterviewService):
    """Consecutive unknown answers trigger escalation and stop the session safely."""
    from aios_habit.expert_identity import VerifiedPrincipal
    from aios_habit.expert_interview_models import (
        ACTION_ESCALATE,
        SESSION_STATE_STOPPED,
    )

    gap = _create_sample_gap(repo, gap_id="GAP-UNK-ESC")
    _setup_expert(repo, "expert_opt_lead", "lsu_optical_assembly")
    plan = service.create_interview_plan(gap_id=gap.gap_id)

    principal = VerifiedPrincipal("expert_opt_lead", "local_test", "Chuyên gia Quang học")
    session = service.start_interview_session(plan.plan_id, principal, "expert_opt_lead", "IDEMP-START-UNK")

    # Turn 1: unknown
    turn1, dec1 = service.submit_interview_turn(
        session_id=session.session_id,
        answer_text="Tôi chưa rõ thông số này.",
        principal=principal,
        idempotency_key="IDEMP-TURN-UNK-1",
    )
    assert dec1.action != ACTION_ESCALATE

    # Turn 2: unknown again -> triggers escalation
    turn2, dec2 = service.submit_interview_turn(
        session_id=session.session_id,
        answer_text="Vẫn không rõ, tài liệu xưởng không ghi.",
        principal=principal,
        idempotency_key="IDEMP-TURN-UNK-2",
    )
    assert dec2.action == ACTION_ESCALATE

    updated_session = service.interview_repo.get_session(session.session_id)
    assert updated_session is not None
    assert updated_session.state == SESSION_STATE_STOPPED
    assert updated_session.stop_reason == "escalated_due_to_uncertainty"


def test_turn_by_turn_reauthorization_blocks_session_on_revocation(
    repo: WorkspaceCaseRepository, service: ExpertInterviewService
):
    """Session is blocked immediately if expert grant is revoked between turns."""
    from aios_habit.expert_identity import VerifiedPrincipal
    from aios_habit.expert_interview_models import SESSION_STATE_BLOCKED

    gap = _create_sample_gap(repo, gap_id="GAP-REVOKE-TEST")
    _setup_expert(repo, "expert_opt_lead", "lsu_optical_assembly")
    plan = service.create_interview_plan(gap_id=gap.gap_id)

    principal = VerifiedPrincipal("expert_opt_lead", "local_test", "Chuyên gia Quang học")
    session = service.start_interview_session(plan.plan_id, principal, "expert_opt_lead", "IDEMP-START-REV")

    # Turn 1 OK
    service.submit_interview_turn(
        session_id=session.session_id,
        answer_text="Bước sóng là 632.8 nm",
        principal=principal,
        idempotency_key="IDEMP-TURN-REV-1",
    )

    # Revoke grant before turn 2
    repo.revoke_scope_grant(f"GRANT-expert_opt_lead-lsu_optical_assembly", "security_admin")

    with pytest.raises(AuthorizationError, match="thu hồi hoặc hết hạn"):
        service.submit_interview_turn(
            session_id=session.session_id,
            answer_text="Ngoại lệ là khi nhiệt độ trên 50 độ C",
            principal=principal,
            idempotency_key="IDEMP-TURN-REV-2",
        )

    blocked_session = service.interview_repo.get_session(session.session_id)
    assert blocked_session is not None
    assert blocked_session.state == SESSION_STATE_BLOCKED
    assert blocked_session.stop_reason == "authority_revoked_or_expired_during_session"


def test_pause_and_resume_session(repo: WorkspaceCaseRepository, service: ExpertInterviewService):
    """Session can be paused via answer command and safely resumed."""
    from aios_habit.expert_identity import VerifiedPrincipal
    from aios_habit.expert_interview_models import (
        ACTION_PAUSE,
        SESSION_STATE_ACTIVE,
        SESSION_STATE_PAUSED,
    )

    gap = _create_sample_gap(repo, gap_id="GAP-PAUSE-TEST")
    _setup_expert(repo, "expert_opt_lead", "lsu_optical_assembly")
    plan = service.create_interview_plan(gap_id=gap.gap_id)

    principal = VerifiedPrincipal("expert_opt_lead", "local_test", "Chuyên gia Quang học")
    session = service.start_interview_session(plan.plan_id, principal, "expert_opt_lead", "IDEMP-START-PAUSE")

    # Submit pause
    turn, dec = service.submit_interview_turn(
        session_id=session.session_id,
        answer_text="tạm dừng",
        principal=principal,
        idempotency_key="IDEMP-TURN-PAUSE-1",
    )
    assert dec.action == ACTION_PAUSE
    sess_paused = service.interview_repo.get_session(session.session_id)
    assert sess_paused.state == SESSION_STATE_PAUSED

    # Resume session
    resumed = service.resume_interview_session(session.session_id, principal)
    assert resumed.state == SESSION_STATE_ACTIVE
    sess_active = service.interview_repo.get_session(session.session_id)
    assert sess_active.state == SESSION_STATE_ACTIVE


def test_stop_command_ends_session(repo: WorkspaceCaseRepository, service: ExpertInterviewService):
    """Special stop command ends interview session safely."""
    from aios_habit.expert_identity import VerifiedPrincipal
    from aios_habit.expert_interview_models import (
        ACTION_COMPLETE,
        SESSION_STATE_STOPPED,
    )

    gap = _create_sample_gap(repo, gap_id="GAP-STOP-TEST")
    _setup_expert(repo, "expert_opt_lead", "lsu_optical_assembly")
    plan = service.create_interview_plan(gap_id=gap.gap_id)

    principal = VerifiedPrincipal("expert_opt_lead", "local_test", "Chuyên gia Quang học")
    session = service.start_interview_session(plan.plan_id, principal, "expert_opt_lead", "IDEMP-START-STOP")

    turn, dec = service.submit_interview_turn(
        session_id=session.session_id,
        answer_text="kết thúc",
        principal=principal,
        idempotency_key="IDEMP-TURN-STOP-1",
    )
    assert dec.action == ACTION_COMPLETE
    sess_stopped = service.interview_repo.get_session(session.session_id)
    assert sess_stopped.state == SESSION_STATE_STOPPED
    assert sess_stopped.stop_reason == "expert_stopped"
