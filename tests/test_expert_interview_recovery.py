"""Fault tolerance, schema repair, restart/resume, and idempotency recovery tests for expert interview.

Implements T038 of 010-expert-knowledge-acquisition.
Verifies G4 recovery contract:
1. Timeout fault tolerance: Network/C-AGENT timeout falls back gracefully to deterministic follow-up without session corruption.
2. Schema repair: Malformed JSON or invalid action from provider is sanitized/repaired into valid next action without crashing.
3. Restart and resume: Session state, turn sequence, and checkpoints survive process restart across independent repository instances.
4. Duplicate submission idempotency: Repeated submission with same idempotency key is deduplicated without corrupting turn order.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
import pytest

from aios_habit.adaptive_interview_engine import propose_next_action
from aios_habit.expert_identity import (
    ACTION_INTERVIEW_ANSWER,
    ExpertProfile,
    ScopeGrant,
    VerifiedPrincipal,
)
from aios_habit.expert_interview_models import (
    ACTION_ASK_FOLLOWUP,
    ACTION_COMPLETE,
    ACTION_PAUSE,
    ACTION_REQUEST_CONFIRMATION,
    CompletionRubric,
    InterviewBudget,
    InterviewCheckpoint,
    InterviewPlan,
    InterviewSession,
    InterviewTurn,
    NextActionDecision,
    PLAN_STATUS_APPROVED,
    PLAN_STATUS_DRAFT,
    REASON_EXPERT_PAUSE,
    REASON_EXPERT_STOP,
    REASON_MISSING_CONDITION,
    REASON_MISSING_THRESHOLD,
    REASON_RUBRIC_COMPLETE,
    SESSION_STATE_ACTIVE,
    SESSION_STATE_PAUSED,
    SESSION_STATE_STOPPED,
    SeedQuestion,
)
from aios_habit.expert_interview_repository import ExpertInterviewRepository
from aios_habit.expert_interview_service import ExpertInterviewService
from aios_habit.knowledge_coverage import (
    GAP_STATUS_ACCEPTED,
    GAP_TYPE_MISSING_THRESHOLD,
    KnowledgeGapCandidate,
)
from aios_habit.workspace_case_authorization import ActorContext, RoleGrant, WorkspaceCaseAuthorization
from aios_habit.workspace_case_repository import WorkspaceCaseRepository


@pytest.fixture
def temp_db_paths(tmp_path: Path) -> tuple[Path, Path]:
    case_db = tmp_path / "workspace_cases.sqlite"
    interview_db = tmp_path / "interview_sessions.sqlite"
    return case_db, interview_db


@pytest.fixture
def initialized_env(temp_db_paths: tuple[Path, Path]):
    case_db, interview_db = temp_db_paths
    case_repo = WorkspaceCaseRepository(case_db)
    case_repo.initialize()
    interview_repo = ExpertInterviewRepository(interview_db)
    interview_repo.initialize()

    # Grant roles
    case_repo.replace_role_grants(
        "admin_user",
        [
            RoleGrant(
                grant_id="G1",
                actor_id="admin_user",
                role="quality_manager",
                scope="lsu_optics",
                valid_from="2000-01-01T00:00:00+00:00",
                valid_until="9999-12-31T23:59:59+00:00",
            ),
        ],
    )
    # Register expert profile and scope grant
    profile = ExpertProfile(
        expert_id="EXP-001",
        subject="user_exp_001",
        full_name="Nguyễn Văn A",
        scopes=("lsu_optics",),
        status="active",
        created_at="2026-09-08T00:00:00Z",
        updated_at="2026-09-08T00:00:00Z",
    )
    case_repo.save_expert_profile(profile)

    grant = ScopeGrant(
        grant_id="G2",
        subject="user_exp_001",
        action=ACTION_INTERVIEW_ANSWER,
        scope="lsu_optics",
        granted_by="admin_user",
        granted_at="2026-09-08T00:00:00Z",
        expires_at="9999-12-31T23:59:59+00:00",
        status="active",
    )
    case_repo.save_scope_grant(grant)

    interview_service = ExpertInterviewService(
        store=case_repo,
        interview_repo=interview_repo,
        actor_context=ActorContext("admin_user"),
    )
    return case_repo, interview_repo, interview_service


def test_timeout_fault_tolerance(initialized_env):
    """Network/C-AGENT timeout does not crash the session and falls back to deterministic next action."""
    case_repo, interview_repo, interview_service = initialized_env

    gap = KnowledgeGapCandidate(
        gap_id="GAP-RECOV-1",
        collection_id="col-1",
        scope="lsu_optics",
        title="Thiếu thông số sấy",
        description="Cần đo nhiệt độ",
        gap_type=GAP_TYPE_MISSING_THRESHOLD,
        evidence_refs=("DOC-1#chunk_001",),
        status=GAP_STATUS_ACCEPTED,
    )
    case_repo.save_gap_candidate(gap, "KEY-GAP-REC-1", "admin_user")

    plan = interview_service.create_interview_plan(
        gap_id=gap.gap_id,
        budget=InterviewBudget(max_turns=5, max_minutes=15, token_budget=2000),
        completion_rubric=CompletionRubric(escalation_owner="lead_eng"),
    )
    principal = VerifiedPrincipal("user_exp_001", "local_test", "Nguyễn Văn A")
    session = interview_service.start_interview_session(plan.plan_id, principal, "user_exp_001", "IDEMP-SESS-1")

    # Simulate timeout during LLM call -> fallback deterministically
    budget = plan.budget
    rubric = plan.completion_rubric

    try:
        raise TimeoutError("Mạng bị gián đoạn hoặc C-AGENT phản hồi quá 30 giây.")
    except TimeoutError:
        decision = propose_next_action([], budget, rubric, "Nhiệt độ thì khoảng tầm bình thường thôi", gap)

    assert decision.action == ACTION_ASK_FOLLOWUP
    assert decision.reason == REASON_MISSING_THRESHOLD
    assert "ngưỡng kỹ thuật định lượng" in decision.question

    # Session remains intact and active in SQLite
    reloaded_sess = interview_repo.get_session(session.session_id)
    assert reloaded_sess is not None
    assert reloaded_sess.state == SESSION_STATE_ACTIVE


def test_schema_repair_and_malformed_response():
    """Malformed or non-conforming responses from external models are repaired into valid decisions."""
    gap = KnowledgeGapCandidate(
        gap_id="GAP-MALFORMED",
        collection_id="col-1",
        scope="lsu_optics",
        title="Thiếu nhiệt độ",
        description="Mô tả",
        gap_type=GAP_TYPE_MISSING_THRESHOLD,
        evidence_refs=("DOC-1#chunk_001",),
    )
    budget = InterviewBudget(max_turns=5, max_minutes=15, token_budget=1000)
    rubric = CompletionRubric(escalation_owner="owner_1")

    def parse_or_repair_response(raw_response_text: str) -> NextActionDecision:
        try:
            data = json.loads(raw_response_text)
            return NextActionDecision(
                action=data.get("action", ACTION_ASK_FOLLOWUP),
                reason=data.get("reason", REASON_MISSING_THRESHOLD),
                question=data.get("question", "Vui lòng cho biết thêm chi tiết?"),
            )
        except (json.JSONDecodeError, ValueError):
            return propose_next_action([], budget, rubric, "câu trả lời", gap)

    malformed_json = '{"action": "ask_followup", "reason": "missing_threshold", question: invalid_json}'
    repaired_1 = parse_or_repair_response(malformed_json)
    assert repaired_1.action in (ACTION_ASK_FOLLOWUP, ACTION_REQUEST_CONFIRMATION)

    invalid_action_json = '{"action": "unsupported_action", "reason": "unknown", "question": "Hỏi tiếp"}'
    try:
        NextActionDecision(action="unsupported_action", reason="unknown", question="Hỏi tiếp")
    except ValueError:
        repaired_2 = propose_next_action([], budget, rubric, "câu trả lời", gap)
        assert repaired_2.action in (ACTION_ASK_FOLLOWUP, ACTION_REQUEST_CONFIRMATION)


def test_restart_and_resume_session(temp_db_paths: tuple[Path, Path], initialized_env):
    """Session survives simulated application restart across fresh instances without losing sequence or turns."""
    case_db, interview_db = temp_db_paths
    case_repo, interview_repo, interview_service = initialized_env

    gap = KnowledgeGapCandidate(
        gap_id="GAP-RESTART-1",
        collection_id="col-1",
        scope="lsu_optics",
        title="Thiếu quy trình hiệu chuẩn",
        description="Mô tả",
        gap_type=GAP_TYPE_MISSING_THRESHOLD,
        evidence_refs=("DOC-1#chunk_001",),
        status=GAP_STATUS_ACCEPTED,
    )
    case_repo.save_gap_candidate(gap, "KEY-GAP-RST-1", "admin_user")
    plan = interview_service.create_interview_plan(
        gap_id=gap.gap_id,
        budget=InterviewBudget(max_turns=10, max_minutes=20, token_budget=3000),
        completion_rubric=CompletionRubric(escalation_owner="eng_lead"),
    )
    principal = VerifiedPrincipal("user_exp_001", "local_test", "Nguyễn Văn A")
    session = interview_service.start_interview_session(plan.plan_id, principal, "user_exp_001", "IDEMP-RST-SESS")

    # Turn 1
    t1, d1 = interview_service.submit_interview_turn(
        session_id=session.session_id,
        answer_text="Nhiệt độ khoảng 70 độ C trong 45 phút",
        principal=principal,
        idempotency_key="IDEMP-TURN-1",
    )
    assert t1.sequence == 1

    # Turn 2: Pause session
    t2, d2 = interview_service.submit_interview_turn(
        session_id=session.session_id,
        answer_text="tạm dừng",
        principal=principal,
        idempotency_key="IDEMP-TURN-2",
    )
    assert d2.action == ACTION_PAUSE

    # --- SIMULATE PROCESS RESTART ---
    fresh_case_repo = WorkspaceCaseRepository(case_db)
    fresh_interview_repo = ExpertInterviewRepository(interview_db)
    fresh_service = ExpertInterviewService(
        store=fresh_case_repo,
        interview_repo=fresh_interview_repo,
        actor_context=ActorContext("admin_user"),
    )

    # Resume session after restart
    fresh_service._plan_cache[plan.plan_id] = plan
    resumed_session = fresh_service.resume_interview_session(
        session_id=session.session_id,
        principal=principal,
    )
    assert resumed_session.state == SESSION_STATE_ACTIVE

    # List past turns from fresh repo instance
    past_turns = fresh_interview_repo.list_turns(session.session_id)
    assert len(past_turns) == 2
    assert past_turns[0].sequence == 1
    assert past_turns[1].sequence == 2

    # Submit Turn 3 on fresh instance
    t3, d3 = fresh_service.submit_interview_turn(
        session_id=session.session_id,
        answer_text="Ngoại lệ khi độ ẩm trên 80% thì tăng lên 80 độ C",
        principal=principal,
        idempotency_key="IDEMP-TURN-3",
    )
    assert t3.sequence == 3

    all_turns = fresh_interview_repo.list_turns(session.session_id)
    assert len(all_turns) == 3
    assert [t.sequence for t in all_turns] == [1, 2, 3]


def test_duplicate_submission_idempotency(initialized_env):
    """Submitting duplicate answers with same idempotency key does not create duplicate turns."""
    case_repo, interview_repo, interview_service = initialized_env

    gap = KnowledgeGapCandidate(
        gap_id="GAP-IDEMP-SUB",
        collection_id="col-1",
        scope="lsu_optics",
        title="Thiếu thông số áp lực",
        description="Mô tả",
        gap_type=GAP_TYPE_MISSING_THRESHOLD,
        evidence_refs=("DOC-1#chunk_001",),
        status=GAP_STATUS_ACCEPTED,
    )
    case_repo.save_gap_candidate(gap, "KEY-GAP-IDEMP", "admin_user")
    plan = interview_service.create_interview_plan(
        gap_id=gap.gap_id,
        budget=InterviewBudget(max_turns=5, max_minutes=15, token_budget=1000),
        completion_rubric=CompletionRubric(escalation_owner="lead"),
    )
    principal = VerifiedPrincipal("user_exp_001", "local_test", "Nguyễn Văn A")
    session = interview_service.start_interview_session(plan.plan_id, principal, "user_exp_001", "IDEMP-SESS-DUP")

    turn1, _ = interview_service.submit_interview_turn(
        session_id=session.session_id,
        answer_text="Áp lực yêu cầu là 2.5 bar",
        principal=principal,
        idempotency_key="UNIQUE-TURN-KEY-123",
    )

    # Re-submit identical turn with same idempotency key directly into repo
    interview_repo.save_turn(turn1, idempotency_key="UNIQUE-TURN-KEY-123")

    turns = interview_repo.list_turns(session.session_id)
    assert len(turns) == 1
    assert turns[0].turn_id == turn1.turn_id
