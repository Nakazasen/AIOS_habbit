"""Data models for expert interview planning, sessions, turns, and checkpoints.

Implements T025, T030 of 010-expert-knowledge-acquisition.
Follows ADR-0009 and data-model.md.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Optional

# Plan statuses
PLAN_STATUS_DRAFT = "draft"
PLAN_STATUS_APPROVED = "approved"
PLAN_STATUS_SCHEDULED = "scheduled"
PLAN_STATUS_IN_PROGRESS = "in_progress"
PLAN_STATUS_CLOSED = "closed"
PLAN_STATUS_CANCELLED = "cancelled"

ALLOWED_PLAN_STATUSES = {
    PLAN_STATUS_DRAFT,
    PLAN_STATUS_APPROVED,
    PLAN_STATUS_SCHEDULED,
    PLAN_STATUS_IN_PROGRESS,
    PLAN_STATUS_CLOSED,
    PLAN_STATUS_CANCELLED,
}

# Session states
SESSION_STATE_READY = "ready"
SESSION_STATE_ACTIVE = "active"
SESSION_STATE_PAUSED = "paused"
SESSION_STATE_AWAITING_CONFIRMATION = "awaiting_confirmation"
SESSION_STATE_COMPLETED = "completed"
SESSION_STATE_STOPPED = "stopped"
SESSION_STATE_BLOCKED = "blocked"

ALLOWED_SESSION_STATES = {
    SESSION_STATE_READY,
    SESSION_STATE_ACTIVE,
    SESSION_STATE_PAUSED,
    SESSION_STATE_AWAITING_CONFIRMATION,
    SESSION_STATE_COMPLETED,
    SESSION_STATE_STOPPED,
    SESSION_STATE_BLOCKED,
}

# Consent states
CONSENT_NOT_REQUESTED = "not_requested"
CONSENT_DECLINED = "declined"
CONSENT_GRANTED = "granted"
CONSENT_WITHDRAWN = "withdrawn"

ALLOWED_CONSENT_STATES = {
    CONSENT_NOT_REQUESTED,
    CONSENT_DECLINED,
    CONSENT_GRANTED,
    CONSENT_WITHDRAWN,
}

# Turn answer states
ANSWER_STATE_ANSWERED = "answered"
ANSWER_STATE_UNKNOWN = "unknown"
ANSWER_STATE_UNCERTAIN = "uncertain"
ANSWER_STATE_SKIPPED = "skipped"
ANSWER_STATE_CORRECTED = "corrected"

ALLOWED_ANSWER_STATES = {
    ANSWER_STATE_ANSWERED,
    ANSWER_STATE_UNKNOWN,
    ANSWER_STATE_UNCERTAIN,
    ANSWER_STATE_SKIPPED,
    ANSWER_STATE_CORRECTED,
}

# Next action verbs and reasons
ACTION_ASK_FOLLOWUP = "ask_followup"
ACTION_REQUEST_CONFIRMATION = "request_confirmation"
ACTION_COMPLETE = "complete"
ACTION_PAUSE = "pause"
ACTION_ESCALATE = "escalate"

ALLOWED_NEXT_ACTIONS = {
    ACTION_ASK_FOLLOWUP,
    ACTION_REQUEST_CONFIRMATION,
    ACTION_COMPLETE,
    ACTION_PAUSE,
    ACTION_ESCALATE,
}

REASON_MISSING_CONDITION = "missing_condition"
REASON_MISSING_THRESHOLD = "missing_threshold"
REASON_MISSING_EXCEPTION = "missing_exception"
REASON_MISSING_EXAMPLE = "missing_example"
REASON_MISSING_COUNTEREXAMPLE = "missing_counterexample"
REASON_UNCERTAIN = "uncertain"
REASON_MISSING_SOURCE = "missing_source"
REASON_CONTRADICTION = "contradiction"
REASON_RUBRIC_COMPLETE = "rubric_complete"

ALLOWED_ACTION_REASONS = {
    REASON_MISSING_CONDITION,
    REASON_MISSING_THRESHOLD,
    REASON_MISSING_EXCEPTION,
    REASON_MISSING_EXAMPLE,
    REASON_MISSING_COUNTEREXAMPLE,
    REASON_UNCERTAIN,
    REASON_MISSING_SOURCE,
    REASON_CONTRADICTION,
    REASON_RUBRIC_COMPLETE,
}


class InterviewPlanError(ValueError):
    """Validation failure in interview plan structure or invariants."""


class InterviewSessionError(ValueError):
    """Validation failure in interview session or state transitions."""


@dataclass(frozen=True)
class SeedQuestion:
    """Foundational seed question derived from an identified knowledge gap."""
    question_id: str
    text: str
    target_gap_id: str
    expected_aspects: tuple[str, ...] = ()
    suggested_order: int = 1

    def __post_init__(self) -> None:
        if not self.question_id.strip():
            raise InterviewPlanError("Mã câu hỏi nền không được để trống.")
        if not self.text.strip():
            raise InterviewPlanError("Nội dung câu hỏi nền không được để trống.")
        if not self.target_gap_id.strip():
            raise InterviewPlanError("Khoảng trống mục tiêu của câu hỏi nền không được để trống.")


@dataclass(frozen=True)
class InterviewBudget:
    """Strict finite budget boundaries for interview sessions to prevent runaway loops."""
    max_turns: int = 10
    max_minutes: int = 30
    token_budget: int = 4000

    def __post_init__(self) -> None:
        if not isinstance(self.max_turns, int) or self.max_turns <= 0:
            raise InterviewPlanError("Số lượt phỏng vấn tối đa (max_turns) phải là số nguyên dương hữu hạn.")
        if not isinstance(self.max_minutes, int) or self.max_minutes <= 0:
            raise InterviewPlanError("Thời gian tối đa (max_minutes) phải là số nguyên dương hữu hạn.")
        if not isinstance(self.token_budget, int) or self.token_budget <= 0:
            raise InterviewPlanError("Ngân sách token (token_budget) phải là số nguyên dương hữu hạn.")


@dataclass(frozen=True)
class CompletionRubric:
    """Objective criteria for session completion, stopping, and escalation."""
    required_aspects: tuple[str, ...] = ("threshold", "unit", "exceptions")
    min_grounded_claims: int = 1
    allow_unknown: bool = True
    stop_on_repeated_unknowns: int = 2
    escalation_owner: str = ""

    def __post_init__(self) -> None:
        if not self.escalation_owner or not self.escalation_owner.strip():
            raise InterviewPlanError("Người tiếp nhận xử lý leo thang (escalation_owner) không được để trống.")
        if self.min_grounded_claims < 0:
            raise InterviewPlanError("Số luận điểm tối thiểu có căn cứ không được là số âm.")
        if self.stop_on_repeated_unknowns <= 0:
            raise InterviewPlanError("Số lần không rõ liên tiếp để dừng phải là số dương.")


def _compute_digest(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class InterviewPlan:
    """Versioned plan binding knowledge gaps to verified experts, rubric, and finite budget."""
    plan_id: str
    version: int
    gap_ids: tuple[str, ...]
    required_scope: str
    eligible_expert_ids: tuple[str, ...]
    seed_questions: tuple[SeedQuestion, ...]
    budget: InterviewBudget
    completion_rubric: CompletionRubric
    status: str
    created_by: str
    created_at: str
    digest: str = ""

    def __post_init__(self) -> None:
        if not self.plan_id.strip():
            raise InterviewPlanError("Mã kế hoạch phỏng vấn không được để trống.")
        if self.version < 1:
            raise InterviewPlanError("Phiên bản kế hoạch phải lớn hơn hoặc bằng 1.")
        if not self.gap_ids:
            raise InterviewPlanError("Kế hoạch phỏng vấn phải gán ít nhất một khoảng trống tri thức.")
        if not self.required_scope.strip():
            raise InterviewPlanError("Công đoạn yêu cầu (required_scope) không được để trống.")
        if not self.eligible_expert_ids:
            raise InterviewPlanError("Kế hoạch phỏng vấn phải có ít nhất một chuyên gia đủ điều kiện.")
        if not self.created_by.strip():
            raise InterviewPlanError("Người tạo kế hoạch không được để trống.")
        if self.status not in ALLOWED_PLAN_STATUSES:
            raise InterviewPlanError(f"Trạng thái kế hoạch '{self.status}' không hợp lệ.")

        computed_digest = self.calculate_digest()
        if self.digest and self.digest != computed_digest:
            raise InterviewPlanError("Mã kiểm tra nội dung (digest) của kế hoạch không khớp.")
        if not self.digest:
            object.__setattr__(self, "digest", computed_digest)

    def calculate_digest(self) -> str:
        payload = {
            "plan_id": self.plan_id,
            "version": self.version,
            "gap_ids": list(self.gap_ids),
            "required_scope": self.required_scope,
            "eligible_expert_ids": list(self.eligible_expert_ids),
            "seed_questions": [
                {
                    "question_id": q.question_id,
                    "text": q.text,
                    "target_gap_id": q.target_gap_id,
                    "expected_aspects": list(q.expected_aspects),
                    "suggested_order": q.suggested_order,
                }
                for q in self.seed_questions
            ],
            "budget": asdict(self.budget),
            "completion_rubric": {
                "required_aspects": list(self.completion_rubric.required_aspects),
                "min_grounded_claims": self.completion_rubric.min_grounded_claims,
                "allow_unknown": self.completion_rubric.allow_unknown,
                "stop_on_repeated_unknowns": self.completion_rubric.stop_on_repeated_unknowns,
                "escalation_owner": self.completion_rubric.escalation_owner,
            },
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at,
        }
        return _compute_digest(payload)


@dataclass(frozen=True)
class InterviewSession:
    """Active or checkpointed interview session binding a plan, expert, and principal."""
    session_id: str
    plan_id: str
    expert_id: str
    principal_subject_id: str
    state: str = SESSION_STATE_READY
    consent_state: str = CONSENT_NOT_REQUESTED
    checkpoint_seq: int = 0
    last_turn_digest: str = ""
    started_at: str = ""
    updated_at: str = ""
    ended_at: Optional[str] = None
    stop_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise InterviewSessionError("Mã phiên phỏng vấn không được để trống.")
        if not self.plan_id.strip():
            raise InterviewSessionError("Mã kế hoạch liên kết không được để trống.")
        if not self.expert_id.strip():
            raise InterviewSessionError("Mã chuyên gia liên kết không được để trống.")
        if not self.principal_subject_id.strip():
            raise InterviewSessionError("Định danh người dùng xác thực không được để trống.")
        if self.state not in ALLOWED_SESSION_STATES:
            raise InterviewSessionError(f"Trạng thái phiên '{self.state}' không hợp lệ.")
        if self.consent_state not in ALLOWED_CONSENT_STATES:
            raise InterviewSessionError(f"Trạng thái đồng ý '{self.consent_state}' không hợp lệ.")


@dataclass(frozen=True)
class InterviewTurn:
    """Individual question-and-answer exchange within an interview session."""
    turn_id: str
    session_id: str
    sequence: int
    question_text: str
    answer_text: str
    question_reason: str
    trigger_refs: tuple[str, ...] = ()
    answer_confidence: float = 1.0
    answer_state: str = ANSWER_STATE_ANSWERED
    payload_digest: str = ""
    created_at: str = ""
    supersedes_turn_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.turn_id.strip():
            raise InterviewSessionError("Mã lượt phỏng vấn không được để trống.")
        if not self.session_id.strip():
            raise InterviewSessionError("Mã phiên liên kết không được để trống.")
        if self.sequence < 1:
            raise InterviewSessionError("Thứ tự lượt phỏng vấn phải lớn hơn hoặc bằng 1.")
        if not self.question_text.strip():
            raise InterviewSessionError("Nội dung câu hỏi không được để trống.")
        if self.answer_state not in ALLOWED_ANSWER_STATES:
            raise InterviewSessionError(f"Trạng thái câu trả lời '{self.answer_state}' không hợp lệ.")

        computed_digest = self.calculate_digest()
        if self.payload_digest and self.payload_digest != computed_digest:
            raise InterviewSessionError("Mã kiểm tra nội dung (payload_digest) của lượt phỏng vấn không khớp.")
        if not self.payload_digest:
            object.__setattr__(self, "payload_digest", computed_digest)

    def calculate_digest(self) -> str:
        payload = {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "sequence": self.sequence,
            "question_text": self.question_text,
            "answer_text": self.answer_text,
            "question_reason": self.question_reason,
            "trigger_refs": list(self.trigger_refs),
            "answer_confidence": self.answer_confidence,
            "answer_state": self.answer_state,
            "created_at": self.created_at,
            "supersedes_turn_id": self.supersedes_turn_id,
        }
        return _compute_digest(payload)


@dataclass(frozen=True)
class InterviewCheckpoint:
    """Append-only snapshot of session state enabling safe resume."""
    checkpoint_id: str
    session_id: str
    sequence: int
    state: str
    snapshot_json: str
    digest: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.checkpoint_id.strip():
            raise InterviewSessionError("Mã điểm kiểm tra không được để trống.")
        if not self.session_id.strip():
            raise InterviewSessionError("Mã phiên trong điểm kiểm tra không được để trống.")


@dataclass(frozen=True)
class NextActionDecision:
    """Strict schema-validated decision from Gemini adaptive interviewer."""
    action: str
    reason: str
    question: str = ""
    trigger_refs: tuple[str, ...] = ()
    expected_evidence: tuple[str, ...] = ()
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.action not in ALLOWED_NEXT_ACTIONS:
            raise InterviewSessionError(f"Hành động tiếp theo '{self.action}' không hợp lệ.")
        if self.reason not in ALLOWED_ACTION_REASONS:
            raise InterviewSessionError(f"Lý do câu hỏi '{self.reason}' không hợp lệ.")
        if self.action == ACTION_ASK_FOLLOWUP and not self.question.strip():
            raise InterviewSessionError("Câu hỏi làm rõ không được để trống khi action='ask_followup'.")
