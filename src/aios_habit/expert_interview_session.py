"""In-app expert interview session (backend, no UI).

Wires the deterministic golden-question pipeline of the KNOWLEDGE-ENRICH-PILOT
ticket (golden_question_generator + golden_question_scorer + GoldenAnswer
schema) into a runnable session:

    knowledge gap -> golden questions (generated + scored, no LLM)
      -> session asks question by question
      -> expert answers fill the standard causal form (GoldenAnswer)
      -> answers are written to STAGING only
        (local_cases/staging_enrichment.sqlite, same store and same
        production-write refusal as golden_answer_importer).

Nothing here touches the production DB or the production index. Reviewer
status stays "cho_chuyen_gia_phan_hoi"; expert confirmation and any merge to
the real store are separate future work.

This module is UI-agnostic on purpose: the chat UI (item 4 of the ticket,
pending user approval) will call start_session / answer_question /
unanswered_questions / complete_session. All user-facing strings are
Vietnamese.

Python 3.11 compatible: no PEP 701 multiline f-strings, no `type` statements.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from aios_habit.golden_answer_importer import (
    assert_not_production,
    dedup_key,
    init_staging_db,
    normalize_answer_text,
)
from aios_habit.golden_question_generator import (
    PhenomenonContext,
    default_gap_for_phenomenon,
    generate_candidates,
)
from aios_habit.golden_question_schema import (
    REVIEWER_STATUS_PENDING,
    GoldenAnswer,
    GoldenQuestion,
    GoldenSchemaError,
)
from aios_habit.golden_question_scorer import select_top_k

import os as _os

# Session states.
SESSION_ACTIVE = "active"
SESSION_COMPLETED = "completed"
SESSION_ABANDONED = "abandoned"

SESSION_STATES = (SESSION_ACTIVE, SESSION_COMPLETED, SESSION_ABANDONED)

DEFAULT_QUESTIONS_PER_SESSION = 3
DEFAULT_MIN_SCORE = 55.0

DEFAULT_STAGING_NAME = "staging_enrichment.sqlite"


class InterviewSessionError(ValueError):
    """Raised when a session cannot start, accept an answer, or complete."""


def default_staging_path() -> Path:
    """Staging sqlite path (same convention as golden_answer_importer)."""
    base = _os.environ.get("AIOS_LOCAL_CASES_DIR", "")
    root = Path(base) if base else Path.cwd() / "local_cases"
    return root / DEFAULT_STAGING_NAME


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ExpertInterviewSession:
    """One in-app expert interview session (in memory; answers live in staging).

    The session is UI-agnostic: questions are plain GoldenQuestion objects,
    answers are validated GoldenAnswer objects. State transitions:
    active -> completed | abandoned.
    """

    session_id: str
    batch_id: str
    error_code: str
    error_group: str
    phenomenon: str
    case_ids: tuple
    gap_id: str
    status: str = SESSION_ACTIVE
    created_at: str = field(default_factory=_utc_now_iso)
    completed_at: str = ""
    questions: List[GoldenQuestion] = field(default_factory=list)
    answers: Dict[str, GoldenAnswer] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in SESSION_STATES:
            raise InterviewSessionError(
                "Trạng thái phiên phỏng vấn không hợp lệ: %s." % self.status
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "batch_id": self.batch_id,
            "error_code": self.error_code,
            "error_group": self.error_group,
            "phenomenon": self.phenomenon,
            "case_ids": list(self.case_ids),
            "gap_id": self.gap_id,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "questions": [q.to_dict() for q in self.questions],
            "answers": {qid: a.to_dict() for qid, a in self.answers.items()},
        }


def start_session(
    ctx: PhenomenonContext,
    questions_per_session: int = DEFAULT_QUESTIONS_PER_SESSION,
    min_score: float = DEFAULT_MIN_SCORE,
) -> ExpertInterviewSession:
    """Build a session from a knowledge gap / phenomenon context.

    Reuses the pilot's deterministic generator + scorer: generate_candidates
    (no LLM) then select_top_k. The gap is the first declared gap of the
    context, falling back to default_gap_for_phenomenon().
    """
    if questions_per_session <= 0:
        raise InterviewSessionError("Số câu hỏi mỗi phiên phải lớn hơn 0.")
    gaps = list(ctx.gaps) or [default_gap_for_phenomenon(ctx)]
    ctx_with_gaps = PhenomenonContext(
        batch_id=ctx.batch_id,
        error_code=ctx.error_code,
        phenomenon=ctx.phenomenon,
        case_ids=ctx.case_ids,
        error_group=ctx.error_group,
        model_line_station=ctx.model_line_station,
        gaps=tuple(gaps),
        hypotheses=ctx.hypotheses,
        hypothesis_source_note=ctx.hypothesis_source_note,
    )
    candidates = generate_candidates(ctx_with_gaps, start_index=1)
    selection = select_top_k(
        ctx_with_gaps,
        candidates,
        k=questions_per_session,
        min_score=min_score,
    )
    if not selection.selected:
        raise InterviewSessionError(
            "Không sinh được câu hỏi nào đạt ngưỡng điểm %.1f cho hiện tượng '%s'."
            % (min_score, ctx.phenomenon[:60])
        )
    gap_id = gaps[0].gap_id
    return ExpertInterviewSession(
        session_id="IS-%s" % uuid.uuid4().hex[:8].upper(),
        batch_id=ctx.batch_id,
        error_code=ctx.error_code,
        error_group=ctx.error_group,
        phenomenon=ctx.phenomenon,
        case_ids=tuple(ctx.case_ids),
        gap_id=gap_id,
        questions=list(selection.selected),
    )


def unanswered_questions(session: ExpertInterviewSession) -> List[GoldenQuestion]:
    """Questions of the session that have no validated answer yet."""
    return [q for q in session.questions if q.question_id not in session.answers]


def answer_question(
    session: ExpertInterviewSession,
    question_id: str,
    answer_payload: Dict[str, Any],
) -> GoldenAnswer:
    """Record one answer in the session.

    The payload goes through full GoldenAnswer validation (vague "answered"
    forms without causality/evidence are REJECTED by the schema). The answer
    is held in memory only; staging persistence happens in complete_session().
    """
    if session.status != SESSION_ACTIVE:
        raise InterviewSessionError(
            "Phiên đã ở trạng thái '%s', không nhận thêm đáp án." % session.status
        )
    question = None
    for q in session.questions:
        if q.question_id == question_id:
            question = q
            break
    if question is None:
        raise InterviewSessionError(
            "Câu hỏi '%s' không thuộc phiên phỏng vấn %s." % (question_id, session.session_id)
        )
    payload = dict(answer_payload or {})
    # Prefill the traceability fields from the session so the UI only asks
    # the expert for the investigation content.
    payload.setdefault("answer_id", "GA-%s-%s" % (question_id, session.session_id))
    payload.setdefault("question_id", question_id)
    payload.setdefault("gap_id", question.target_gap_id)
    payload.setdefault("case_ids", list(question.target_case_ids))
    payload.setdefault("error_code", session.error_code)
    payload.setdefault("error_group", session.error_group)
    payload.setdefault("phenomenon", session.phenomenon)
    payload.setdefault("question_loai", question.loai_cau_hoi)
    try:
        answer = GoldenAnswer.from_dict(payload)
    except GoldenSchemaError as exc:
        raise InterviewSessionError("Đáp án không đạt form nhân quả chuẩn: %s" % exc)
    if answer.reviewer_status != REVIEWER_STATUS_PENDING:
        raise InterviewSessionError(
            "Đáp án trong phiên phỏng vấn phải giữ reviewer_status "
            "'cho_chuyen_gia_phan_hoi'."
        )
    session.answers[question_id] = answer
    return answer


def abandon_session(session: ExpertInterviewSession) -> None:
    """Mark the session abandoned; partial answers stay in memory only."""
    if session.status == SESSION_COMPLETED:
        raise InterviewSessionError("Phiên đã hoàn thành, không thể hủy.")
    session.status = SESSION_ABANDONED


def _store_answer_staging(
    conn: sqlite3.Connection, answer: GoldenAnswer, batch_id: str
) -> Dict[str, Any]:
    """Insert one validated answer into staging (dedup by content SHA)."""
    key = dedup_key(answer.question_id, answer.answer_text)
    row = conn.execute(
        "SELECT answer_id FROM staging_answers WHERE answer_sha = ?", (key,)
    ).fetchone()
    if row:
        return {"answer_id": row[0], "dedup": True}
    conn.execute(
        """
        INSERT INTO staging_answers
            (answer_id, question_id, batch_id, answer_sha, payload_json,
             enrichment_label, reviewer_status, version, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            answer.answer_id,
            answer.question_id,
            batch_id,
            key,
            json.dumps(answer.to_dict(), ensure_ascii=False),
            answer.enrichment_label,
            answer.reviewer_status,
            1,
            _utc_now_iso(),
        ),
    )
    return {"answer_id": answer.answer_id, "dedup": False}


def complete_session(
    session: ExpertInterviewSession,
    staging_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Finish the session: every question must be answered, then persist
    all answers to the STAGING sqlite only (never production).

    Returns a report dict: session_id, staging_path, stored answer ids,
    dedup-skipped count.
    """
    if session.status != SESSION_ACTIVE:
        raise InterviewSessionError(
            "Phiên đã ở trạng thái '%s', không thể hoàn thành lại." % session.status
        )
    missing = unanswered_questions(session)
    if missing:
        raise InterviewSessionError(
            "Còn %d câu chưa có đáp án (%s); hoàn thành khi mọi câu đã trả lời."
            % (len(missing), ", ".join(q.question_id for q in missing))
        )
    path = Path(staging_path) if staging_path else default_staging_path()
    assert_not_production(path)
    conn = init_staging_db(path)
    stored: List[str] = []
    deduped = 0
    try:
        with conn:
            for q in session.questions:
                answer = session.answers[q.question_id]
                result = _store_answer_staging(conn, answer, session.batch_id)
                stored.append(result["answer_id"])
                if result["dedup"]:
                    deduped += 1
    finally:
        conn.close()
    session.status = SESSION_COMPLETED
    session.completed_at = _utc_now_iso()
    return {
        "session_id": session.session_id,
        "status": session.status,
        "staging_path": str(path),
        "stored_answer_ids": stored,
        "dedup_skipped": deduped,
    }


def session_summary(session: ExpertInterviewSession) -> Dict[str, Any]:
    """Compact, UI-friendly progress view of the session."""
    return {
        "session_id": session.session_id,
        "error_code": session.error_code,
        "error_group": session.error_group,
        "phenomenon": session.phenomenon,
        "status": session.status,
        "total_questions": len(session.questions),
        "answered": len(session.answers),
        "remaining_question_ids": [q.question_id for q in unanswered_questions(session)],
    }
