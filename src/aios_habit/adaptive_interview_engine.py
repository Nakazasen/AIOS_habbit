"""Adaptive interview engine for seed question generation, state transitions, and follow-up logic.

Implements T027, T030, T033, T034 of 010-expert-knowledge-acquisition.
Follows ADR-0009 and data-model.md.
"""
from __future__ import annotations

import re
from typing import Iterable, Sequence
from uuid import uuid4

from aios_habit.expert_interview_models import (
    ACTION_ASK_FOLLOWUP,
    ACTION_COMPLETE,
    ACTION_ESCALATE,
    ACTION_PAUSE,
    ACTION_REQUEST_CONFIRMATION,
    ANSWER_STATE_ANSWERED,
    ANSWER_STATE_CORRECTED,
    ANSWER_STATE_SKIPPED,
    ANSWER_STATE_UNCERTAIN,
    ANSWER_STATE_UNKNOWN,
    CompletionRubric,
    InterviewBudget,
    InterviewPlanError,
    InterviewSessionError,
    NextActionDecision,
    REASON_CONTRADICTION,
    REASON_MISSING_CONDITION,
    REASON_MISSING_EXAMPLE,
    REASON_MISSING_EXCEPTION,
    REASON_MISSING_SOURCE,
    REASON_MISSING_THRESHOLD,
    REASON_RUBRIC_COMPLETE,
    REASON_UNCERTAIN,
    SESSION_STATE_ACTIVE,
    SESSION_STATE_AWAITING_CONFIRMATION,
    SESSION_STATE_BLOCKED,
    SESSION_STATE_COMPLETED,
    SESSION_STATE_PAUSED,
    SESSION_STATE_READY,
    SESSION_STATE_STOPPED,
    SeedQuestion,
)
from aios_habit.knowledge_coverage import (
    GAP_TYPE_CONFLICT,
    GAP_TYPE_MISSING_CONDITION,
    GAP_TYPE_MISSING_THRESHOLD,
    GAP_TYPE_STALE_KNOWLEDGE,
    KnowledgeGapCandidate,
)

# Valid finite state transitions
VALID_SESSION_TRANSITIONS: dict[str, set[str]] = {
    SESSION_STATE_READY: {SESSION_STATE_ACTIVE, SESSION_STATE_BLOCKED, "cancelled"},
    SESSION_STATE_ACTIVE: {
        SESSION_STATE_PAUSED,
        SESSION_STATE_AWAITING_CONFIRMATION,
        SESSION_STATE_COMPLETED,
        SESSION_STATE_STOPPED,
        SESSION_STATE_BLOCKED,
    },
    SESSION_STATE_PAUSED: {SESSION_STATE_ACTIVE, SESSION_STATE_STOPPED, "cancelled"},
    SESSION_STATE_AWAITING_CONFIRMATION: {
        SESSION_STATE_ACTIVE,
        SESSION_STATE_COMPLETED,
        SESSION_STATE_STOPPED,
        SESSION_STATE_BLOCKED,
    },
    SESSION_STATE_COMPLETED: set(),
    SESSION_STATE_STOPPED: set(),
    SESSION_STATE_BLOCKED: set(),
}


def validate_session_transition(current_state: str, next_state: str) -> None:
    """Validate lifecycle transitions of an interview session."""
    allowed = VALID_SESSION_TRANSITIONS.get(current_state, set())
    if next_state not in allowed:
        raise InterviewSessionError(
            f"Chuyển tiếp trạng thái phiên không hợp lệ: không thể chuyển từ '{current_state}' sang '{next_state}'."
        )


def detect_leading_question(text: str) -> bool:
    """Detect if question is leading, coercive, or assumes unconfirmed facts."""
    leading_patterns = (
        r"chắc chắn là",
        r"phải không",
        r"đúng là do",
        r"có phải là do",
        r"không thể nào khác",
        r"rõ ràng là",
        r"bắt buộc phải",
        r"tất nhiên là",
        r"hiển nhiên là",
    )
    lower = text.lower()
    return any(re.search(pat, lower) for pat in leading_patterns)


def detect_semantic_duplicate(new_question: str, past_questions: Sequence[str]) -> bool:
    """Detect semantic duplication against previously asked questions."""
    def _tokenize(s: str) -> set[str]:
        words = re.findall(r"\w+", s.lower())
        return set(words)

    new_tokens = _tokenize(new_question)
    if not new_tokens:
        return False

    for past in past_questions:
        past_tokens = _tokenize(past)
        if not past_tokens:
            continue
        intersection = new_tokens & past_tokens
        union = new_tokens | past_tokens
        jaccard = len(intersection) / len(union)
        if jaccard >= 0.85:
            return True
    return False


def validate_candidate_question(
    question_text: str,
    past_questions: Sequence[str],
    turns_count: int,
    max_turns: int,
) -> None:
    """Enforce strict guardrails against leading, duplicate, or out-of-budget questions."""
    if not question_text or not question_text.strip():
        raise InterviewSessionError("Nội dung câu hỏi không được để trống.")
    if turns_count >= max_turns:
        raise InterviewSessionError("Đã đạt giới hạn số lượt phỏng vấn tối đa của ngân sách.")
    if detect_leading_question(question_text):
        raise InterviewSessionError("Câu hỏi vi phạm quy tắc: không được đặt câu hỏi dẫn dắt hoặc ép buộc chuyên gia.")
    if detect_semantic_duplicate(question_text, past_questions):
        raise InterviewSessionError("Câu hỏi bị trùng lặp ngữ nghĩa với câu hỏi trước đó trong phiên.")


def generate_seed_questions(gap: KnowledgeGapCandidate) -> tuple[SeedQuestion, ...]:
    """Generate structured seed questions grounded in the knowledge gap."""
    if not isinstance(gap, KnowledgeGapCandidate):
        raise InterviewPlanError("Khoảng trống tri thức không đúng định dạng.")

    questions: list[SeedQuestion] = []
    gap_type = gap.gap_type.lower()
    title = gap.title.strip()

    if gap_type in (GAP_TYPE_MISSING_THRESHOLD, "missing_threshold"):
        questions.append(
            SeedQuestion(
                question_id=f"SEED-{gap.gap_id}-1",
                text=f"Ngưỡng tiêu chuẩn hoặc giá trị thông số kỹ thuật quy định cho '{title}' là bao nhiêu?",
                target_gap_id=gap.gap_id,
                expected_aspects=("threshold", "target_value"),
                suggested_order=1,
            )
        )
        questions.append(
            SeedQuestion(
                question_id=f"SEED-{gap.gap_id}-2",
                text=f"Đơn vị đo lường và dung sai sai số cho phép đối với thông số '{title}' được quy định cụ thể như thế nào?",
                target_gap_id=gap.gap_id,
                expected_aspects=("unit", "tolerance"),
                suggested_order=2,
            )
        )
        questions.append(
            SeedQuestion(
                question_id=f"SEED-{gap.gap_id}-3",
                text=f"Những trường hợp ngoại lệ hoặc điều kiện môi trường nào yêu cầu kỹ thuật viên phải điều chỉnh thông số '{title}'?",
                target_gap_id=gap.gap_id,
                expected_aspects=("exceptions", "environment"),
                suggested_order=3,
            )
        )
    elif gap_type in (GAP_TYPE_CONFLICT, "conflict"):
        questions.append(
            SeedQuestion(
                question_id=f"SEED-{gap.gap_id}-1",
                text=f"Hiện có sự mâu thuẫn thông tin liên quan đến '{title}'. Quy trình thực tế tại xưởng hiện đang áp dụng theo tiêu chuẩn nào?",
                target_gap_id=gap.gap_id,
                expected_aspects=("current_practice", "standard"),
                suggested_order=1,
            )
        )
        questions.append(
            SeedQuestion(
                question_id=f"SEED-{gap.gap_id}-2",
                text=f"Căn cứ kỹ thuật hoặc tài liệu chính thức nào được dùng để phân định và giải quyết mâu thuẫn này?",
                target_gap_id=gap.gap_id,
                expected_aspects=("authoritative_source", "precedence"),
                suggested_order=2,
            )
        )
    elif gap_type in (GAP_TYPE_MISSING_CONDITION, "missing_condition"):
        questions.append(
            SeedQuestion(
                question_id=f"SEED-{gap.gap_id}-1",
                text=f"Điều kiện tiên quyết để bắt đầu thực hiện công đoạn liên quan đến '{title}' là gì?",
                target_gap_id=gap.gap_id,
                expected_aspects=("preconditions", "equipment_state"),
                suggested_order=1,
            )
        )
        questions.append(
            SeedQuestion(
                question_id=f"SEED-{gap.gap_id}-2",
                text=f"Tiêu chí nghiệm thu nào xác nhận công đoạn liên quan đến '{title}' đã hoàn thành đạt chuẩn?",
                target_gap_id=gap.gap_id,
                expected_aspects=("completion_criteria", "verification_method"),
                suggested_order=2,
            )
        )
    else:
        questions.append(
            SeedQuestion(
                question_id=f"SEED-{gap.gap_id}-1",
                text=f"Nội dung thao tác kỹ thuật và các bước thực hiện đối với '{title}' cụ thể như thế nào?",
                target_gap_id=gap.gap_id,
                expected_aspects=("procedure_steps", "tools"),
                suggested_order=1,
            )
        )
        questions.append(
            SeedQuestion(
                question_id=f"SEED-{gap.gap_id}-2",
                text=f"Dấu hiệu nhận biết bất thường và các bước xử lý ban đầu khi gặp sự cố đối với '{title}' là gì?",
                target_gap_id=gap.gap_id,
                expected_aspects=("abnormal_symptoms", "mitigation"),
                suggested_order=2,
            )
        )

    return tuple(questions)


def propose_next_action(
    turns_history: Sequence[dict[str, Any]],
    budget: InterviewBudget,
    rubric: CompletionRubric,
    latest_answer: str,
    gap: KnowledgeGapCandidate,
) -> NextActionDecision:
    """Deterministic next action evaluator with strict schema and privacy boundaries.

    Implements T033, T034, T035.
    Evaluates:
    - Turn count against budget.max_turns -> complete.
    - Repeated unknowns against rubric.stop_on_repeated_unknowns -> escalate.
    - Ambiguity / missing threshold -> ask_followup (missing_threshold).
    - Contradiction indicator -> ask_followup (contradiction).
    - Missing exception -> ask_followup (missing_exception).
    - Well-grounded complete response -> request_confirmation or complete.
    """
    turns_count = len(turns_history)
    if turns_count >= budget.max_turns:
        return NextActionDecision(
            action=ACTION_COMPLETE,
            reason=REASON_RUBRIC_COMPLETE,
            question="Phiên phỏng vấn đã hoàn tất theo giới hạn ngân sách lượt trao đổi.",
            expected_evidence=("summary",),
            confidence=1.0,
        )

    clean_ans = latest_answer.strip().lower()

    # Repeated unknown handling
    unknown_tokens = {"unknown", "không rõ", "không biết", "chưa rõ", "chưa nắm rõ"}
    is_unknown = any(tok in clean_ans for tok in unknown_tokens)

    if is_unknown:
        consecutive_unknowns = 1
        for past in reversed(turns_history[:-1]):
            past_ans = str(past.get("answer_text", "")).lower()
            if any(tok in past_ans for tok in unknown_tokens):
                consecutive_unknowns += 1
            else:
                break

        if consecutive_unknowns >= rubric.stop_on_repeated_unknowns:
            return NextActionDecision(
                action=ACTION_ESCALATE,
                reason=REASON_UNCERTAIN,
                question="Chuyên gia không nắm rõ thông tin này sau nhiều lần trao đổi. Phiên được chuyển cho người phụ trách giải quyết.",
                expected_evidence=("escalation_memo",),
                confidence=1.0,
            )
        return NextActionDecision(
            action=ACTION_ASK_FOLLOWUP,
            reason=REASON_MISSING_CONDITION,
            question="Nếu thông số này chưa rõ, quy trình có chỉ định tài liệu hoặc người phụ trách nào khác để tra cứu không?",
            trigger_refs=(f"TURN-{turns_count}",),
            expected_evidence=("reference_doc", "contact"),
            confidence=0.8,
        )

    # Contradiction detection
    contradiction_tokens = {"mâu thuẫn", "khác với", "không khớp", "trái ngược", "sai lệch"}
    if any(tok in clean_ans for tok in contradiction_tokens):
        return NextActionDecision(
            action=ACTION_ASK_FOLLOWUP,
            reason=REASON_CONTRADICTION,
            question="Có sự sai khác giữa các nguồn thông tin. Cơ sở kỹ thuật chính thức nào xác định phương án đúng?",
            trigger_refs=(f"TURN-{turns_count}",),
            expected_evidence=("standard_spec", "precedence_rule"),
            confidence=0.85,
        )

    # Missing threshold / units / numbers
    has_digits = bool(re.search(r"\d", clean_ans))
    if not has_digits and gap.gap_type in (GAP_TYPE_MISSING_THRESHOLD, "missing_threshold"):
        return NextActionDecision(
            action=ACTION_ASK_FOLLOWUP,
            reason=REASON_MISSING_THRESHOLD,
            question="Vui lòng cung cấp giá trị số hoặc ngưỡng kỹ thuật định lượng kèm đơn vị đo lường cụ thể?",
            trigger_refs=(f"TURN-{turns_count}",),
            expected_evidence=("numerical_threshold", "unit"),
            confidence=0.85,
        )

    # Missing exception check
    has_exception_words = any(w in clean_ans for w in ("ngoại lệ", "trừ khi", "nếu xảy ra", "tùy thuộc", "không áp dụng"))
    if not has_exception_words and turns_count <= 2:
        return NextActionDecision(
            action=ACTION_ASK_FOLLOWUP,
            reason=REASON_MISSING_EXCEPTION,
            question="Có trường hợp ngoại lệ hoặc điều kiện môi trường nào mà ngưỡng này không được áp dụng không?",
            trigger_refs=(f"TURN-{turns_count}",),
            expected_evidence=("exception_condition",),
            confidence=0.8,
        )

    # Sufficiently covered -> request confirmation
    return NextActionDecision(
        action=ACTION_REQUEST_CONFIRMATION,
        reason=REASON_RUBRIC_COMPLETE,
        question="Vui lòng kiểm tra và xác nhận lại toàn bộ thông số và điều kiện đã nêu trước khi hoàn tất.",
        trigger_refs=(f"TURN-{turns_count}",),
        expected_evidence=("confirmation",),
        confidence=0.95,
    )
