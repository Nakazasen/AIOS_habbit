"""UI glue: in-chat expert interview session + per-suggestion feedback widgets.

Wires existing backends into the chat answer area WITHOUT changing them:
- ``expert_interview_session``: start / answer / complete a golden-question
  session (deterministic, no LLM).
- ``suggestion_feedback.record_feedback_strict``: per-suggestion rating.
- ``self_improvement``: consult_lessons / lesson creation / repetition metric.

Rendering follows the artifact-card pattern: chat actions emit markdown
carrying an HTML metadata comment; ``workspace_chat_ui`` parses the comment
and calls the widget renderers below with the real streamlit module. Every
widget function takes an ``st``-like object as its first argument so tests
can pass a fake.

Python 3.11 compatible: no PEP 701 multiline f-strings, no ``type`` statements.
"""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from aios_habit.golden_question_schema import M4_BRANCHES

# ---------------------------------------------------------------------------
# Metadata markers embedded in the assistant markdown
# ---------------------------------------------------------------------------

_INTERVIEW_TAG = "aios_interview_session"
_SUGGESTION_TAG = "aios_suggestion"

_INTERVIEW_RE = re.compile(
    r"<!--\s*aios_interview_session\s*:\s*(\{.*?\})\s*-->", re.DOTALL
)
_SUGGESTION_RE = re.compile(
    r"<!--\s*aios_suggestion\s*:\s*(\{.*?\})\s*-->", re.DOTALL
)


def interview_marker(session_id: str) -> str:
    """HTML comment marker a chat action embeds to open the interview widget."""
    return "<!-- %s: %s -->" % (
        _INTERVIEW_TAG,
        json.dumps({"session_id": str(session_id)}, ensure_ascii=False),
    )


def suggestion_marker(suggestion_id: str, expert: str = "") -> str:
    """HTML comment marker a chat action embeds under a suggestion card."""
    return "<!-- %s: %s -->" % (
        _SUGGESTION_TAG,
        json.dumps(
            {"suggestion_id": str(suggestion_id), "expert": str(expert or "")},
            ensure_ascii=False,
        ),
    )


def extract_interview_session_id(content: str) -> str:
    """Session id from the interview marker, or "" when absent/invalid."""
    match = _INTERVIEW_RE.search(str(content or ""))
    if not match:
        return ""
    try:
        return str(json.loads(match.group(1)).get("session_id", "")).strip()
    except (ValueError, AttributeError):
        return ""


def extract_suggestion_markers(content: str) -> List[Dict[str, str]]:
    """All suggestion markers in reading order: [{suggestion_id, expert}]."""
    found: List[Dict[str, str]] = []
    for match in _SUGGESTION_RE.finditer(str(content or "")):
        try:
            data = json.loads(match.group(1))
        except ValueError:
            continue
        sid = str(data.get("suggestion_id", "")).strip()
        if sid:
            found.append(
                {"suggestion_id": sid, "expert": str(data.get("expert", "") or "")}
            )
    return found


def strip_interactive_markers(content: str) -> str:
    """Remove interview/suggestion markers before rendering the markdown."""
    text = _INTERVIEW_RE.sub("", str(content or ""))
    text = _SUGGESTION_RE.sub("", text)
    return text.strip()


# ---------------------------------------------------------------------------
# In-memory session registry (Streamlit runs in one process; sessions are
# intentionally NOT persisted — answers go to the staging sqlite on completion)
# ---------------------------------------------------------------------------


class InterviewSessionStore:
    """Tiny bounded registry of live ExpertInterviewSession objects."""

    def __init__(self, capacity: int = 20) -> None:
        self._capacity = max(1, int(capacity))
        self._sessions: "OrderedDict[str, Any]" = OrderedDict()

    def put(self, session: Any) -> None:
        sid = str(getattr(session, "session_id", "") or "").strip()
        if not sid:
            raise ValueError("Phiên phỏng vấn thiếu session_id.")
        self._sessions.pop(sid, None)
        self._sessions[sid] = session
        while len(self._sessions) > self._capacity:
            self._sessions.popitem(last=False)

    def get(self, session_id: str) -> Optional[Any]:
        return self._sessions.get(str(session_id or "").strip())

    def drop(self, session_id: str) -> None:
        self._sessions.pop(str(session_id or "").strip(), None)

    def clear(self) -> None:
        self._sessions.clear()


_STORE = InterviewSessionStore()


def store_session(session: Any) -> None:
    _STORE.put(session)


def get_session(session_id: str) -> Optional[Any]:
    return _STORE.get(session_id)


def drop_session(session_id: str) -> None:
    _STORE.drop(session_id)


# ---------------------------------------------------------------------------
# Completion note that survives st.rerun
# ---------------------------------------------------------------------------


def _completed_message_key(session_id: str) -> str:
    return "wsc_iv_completed_" + re.sub(r"\W+", "_", str(session_id or ""))


def _remember_completion(st: Any, session_id: str, message: str) -> None:
    """Keep the success note in session_state so it survives st.rerun.

    ``complete_session()`` drops the session from the store, so the next
    render can no longer tell "just completed" from "long expired". Without
    this, the rerun below erases the st.success output and the screen only
    shows "expired from memory" even though the answers were stored.
    """
    state = getattr(st, "session_state", None)
    if state is None:
        return
    try:
        state[_completed_message_key(session_id)] = str(message or "")
    except Exception:
        pass


def _completed_message(st: Any, session_id: str) -> str:
    state = getattr(st, "session_state", None)
    if state is None:
        return ""
    try:
        return str(state.get(_completed_message_key(session_id), "") or "")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Interview answer: field spec + pure submit logic (UI calls the backend)
# ---------------------------------------------------------------------------

# (payload key, Vietnamese label, widget kind)
ANSWER_FIELDS: Tuple[Tuple[str, str, str], ...] = (
    ("answer_text", "Nội dung điều tra", "area"),
    ("hypotheses", "Giả thuyết nguyên nhân (mỗi dòng một giả thuyết)", "area"),
    ("causal_mechanism", "Cơ chế gây lỗi", "area"),
    ("m4_branches", "Nhóm 4M", "multiselect"),
    ("evidence_to_collect", "Bằng chứng cần thu thập (mỗi dòng một ý)", "area"),
    ("confirm_criteria", "Tiêu chí xác nhận", "area"),
)

_MISSING_HINTS = (
    (("hypotheses", "causal_mechanism"), "nguyên nhân"),
    (("evidence_to_collect", "confirm_criteria"), "bằng chứng"),
    (("m4_branches",), "nhóm 4M"),
)


def _lines(value: Any) -> List[str]:
    return [line.strip() for line in str(value or "").splitlines() if line.strip()]


def build_answer_payload(values: Dict[str, Any]) -> Dict[str, Any]:
    """Map widget values to the GoldenAnswer payload (traceability fields are
    prefilled by ``answer_question`` itself, so the UI only asks for the
    investigation content)."""
    branches = [
        str(item)
        for item in (values.get("m4_branches") or [])
        if str(item) in M4_BRANCHES
    ]
    payload = {
        "answer_text": str(values.get("answer_text") or ""),
        "answer_state": "answered",
        "confidence": 0.8,
        "hypotheses": _lines(values.get("hypotheses")),
        "causal_mechanism": str(values.get("causal_mechanism") or "").strip(),
        "m4_branches": branches,
        "evidence_to_collect": _lines(values.get("evidence_to_collect")),
        "confirm_criteria": str(values.get("confirm_criteria") or "").strip(),
    }
    discriminate_notes = str(values.get("discriminate_notes") or "").strip()
    if discriminate_notes:
        payload["discriminate_notes"] = discriminate_notes
    return payload


def missing_parts_hint(exc_text: str) -> str:
    """Friendly 'còn thiếu phần ...' reminder from a backend rejection."""
    low = str(exc_text or "").lower()
    parts = [
        label
        for keywords, label in _MISSING_HINTS
        if any(keyword in low for keyword in keywords)
    ]
    if "answer_text" in low or "20 ký tự" in low:
        parts.append("nội dung điều tra (ít nhất 20 ký tự)")
    if parts:
        return (
            "Còn thiếu phần %s — bổ sung rồi gửi lại nhé. Chi tiết: %s"
            % (" / ".join(parts), str(exc_text or "").strip())
        )
    return "Đáp án chưa đạt: %s" % str(exc_text or "").strip()


def submit_interview_answer(
    session: Any, question_id: str, values: Dict[str, Any]
) -> Tuple[bool, str]:
    """Validate one answer through the backend.

    Returns (ok, message_vi). ``ok=False`` means the expert must fix the
    answer (the message names the missing parts); ``ok=True`` with a
    non-empty message means the session just completed.
    """
    from aios_habit.expert_interview_session import (
        InterviewSessionError,
        answer_question,
        complete_session,
        unanswered_questions,
    )

    try:
        answer_question(session, question_id, build_answer_payload(values))
    except InterviewSessionError as exc:
        return False, "⚠️ " + missing_parts_hint(str(exc))
    remaining = unanswered_questions(session)
    if remaining:
        return True, ""
    try:
        report = complete_session(session)
    except InterviewSessionError as exc:
        return False, "Chưa hoàn thành được phiên: %s" % exc
    drop_session(session.session_id)
    stored = report.get("stored_answer_ids") or []
    return (
        True,
        "✅ Đã lưu nháp chờ duyệt (phiên %s, %d đáp án)."
        % (session.session_id, len(stored)),
    )


def render_interview_widget(st: Any, session_id: str) -> None:
    """Render the current question + answer fields right under the question."""
    from aios_habit.expert_interview_session import (
        SESSION_COMPLETED,
        session_summary,
        unanswered_questions,
    )
    from aios_habit.golden_question_schema import LOAI_DISCRIMINATOR

    session = get_session(session_id)
    if session is None:
        completed = _completed_message(st, session_id)
        if completed:
            # Session finished and left the store: show the completion note
            # instead of "expired from memory".
            st.success(completed)
            return
        st.info(
            "Phiên phỏng vấn đã hết hạn trong bộ nhớ. "
            "Mở phiên mới bằng lệnh “mở phiên phỏng vấn <mã lỗi>”."
        )
        return
    if str(getattr(session, "status", "")) == SESSION_COMPLETED:
        st.success(
            "✅ Phiên %s đã hoàn thành — đáp án đã lưu nháp chờ duyệt."
            % session.session_id
        )
        return
    remaining = unanswered_questions(session)
    if not remaining:
        ok, message = submit_interview_answer(session, "", {})
        if ok and message:
            _remember_completion(st, session.session_id, message)
        if message:
            (st.success if ok else st.warning)(message)
        return
    question = remaining[0]
    summary = session_summary(session)
    st.markdown(
        "**Câu %d/%d:** %s"
        % (int(summary["answered"]) + 1, int(summary["total_questions"]), question.text)
    )
    key_base = "wsc_iv_%s_%s" % (
        re.sub(r"\W+", "_", str(session.session_id)),
        re.sub(r"\W+", "_", str(question.question_id)),
    )
    values: Dict[str, Any] = {}
    for payload_key, label, kind in ANSWER_FIELDS:
        field_key = key_base + "_" + payload_key
        if kind == "multiselect":
            values[payload_key] = st.multiselect(
                label, options=list(M4_BRANCHES), key=field_key
            )
        else:
            values[payload_key] = st.text_area(label, key=field_key)
    # Discriminator questions require one extra field (backend rejects without it).
    if str(getattr(question, "loai_cau_hoi", "")) == LOAI_DISCRIMINATOR:
        values["discriminate_notes"] = st.text_area(
            "Cách phân biệt với giả thuyết khác",
            key=key_base + "_discriminate_notes",
        )
    if st.button("Gửi đáp án", key=key_base + "_send"):
        ok, message = submit_interview_answer(
            session, question.question_id, values
        )
        if not ok:
            st.warning(message)
        else:
            if message:
                # Non-empty message means the session just completed:
                # remember the note so it survives the st.rerun below
                # (the session has already been dropped from the store).
                _remember_completion(st, session.session_id, message)
                st.success(message)
            if hasattr(st, "rerun"):
                st.rerun()


# ---------------------------------------------------------------------------
# Suggestion cards: emit (log + lesson note + marker) and feedback widget
# ---------------------------------------------------------------------------


def lesson_note_line(situation_text: str) -> str:
    """One-line 'lưu ý' when the situation resembles a criticized mistake."""
    from aios_habit.self_improvement import consult_lessons

    try:
        lessons = consult_lessons(str(situation_text or ""))
    except Exception:
        return ""
    if not lessons:
        return ""
    top = lessons[0]
    return (
        "💡 Lưu ý: tình huống này từng bị chê vì “%s” — cách đúng là “%s”."
        % (top.get("loi_truoc_day", ""), top.get("cach_sua", ""))
    )


def emit_suggestion_card(
    suggestion_id: str,
    title: str,
    content: str,
    *,
    context: str = "",
    source: str = "chat",
) -> str:
    """Log a suggestion (idempotent) and return its chat markdown + marker.

    When the situation matches a past lesson, a one-line reminder is
    prepended BEFORE the suggestion, per the approved UI proposal.
    """
    from aios_habit import suggestion_feedback as _sf

    sid = str(suggestion_id or "").strip()
    if not sid:
        raise ValueError("Thiếu mã gợi ý.")
    body = str(content or "").strip()
    ctx = str(context or "").strip()
    if _sf.get_suggestion(sid) is None:
        _sf.log_suggestion(sid, body, context=ctx, source=source)
    lines: List[str] = []
    note = lesson_note_line((body + "\n" + ctx).strip())
    if note:
        lines.append(note)
        lines.append("")
    lines.append("**💡 %s**" % str(title or "Gợi ý").strip())
    if body:
        lines.append(body)
    lines.append(suggestion_marker(sid))
    return "\n\n".join(lines)


def save_suggestion_feedback(
    suggestion_id: str,
    expert: str,
    verdict: str,
    ly_do: str,
    nguyen_nhan_that: str,
    noi_dung_nan_lai: str,
    *,
    situation_text: str = "",
) -> Tuple[bool, str]:
    """Rate one suggestion through the backend (strict: missing fields raise).

    On 'sai' / 'một phần' this also grows the improvement loop in the
    background: the lesson is stored and a repetition event is recorded.
    Returns (ok, message_vi).
    """
    from aios_habit.suggestion_feedback import (
        SuggestionFeedbackStrictError,
        get_suggestion,
        record_feedback_strict,
    )
    from aios_habit.self_improvement import (
        ImprovementError,
        LessonStore,
        consult_lessons,
        lesson_from_suggestion_feedback,
        record_repetition_event,
    )

    sid = str(suggestion_id or "").strip()
    verdict = str(verdict or "").strip()
    verdict_vi = {"dung": "đúng", "mot_phan": "một phần", "sai": "sai"}.get(verdict, "")
    if not sid:
        return False, "Thiếu mã gợi ý."
    if not verdict_vi:
        return False, "Đánh giá phải là: đúng / một phần / sai."
    suggestion = get_suggestion(sid) or {}
    situation = str(
        situation_text
        or ("%s || %s" % (suggestion.get("content", ""), suggestion.get("context", "")))
    ).strip()
    repeated = False
    if verdict in ("sai", "mot_phan") and situation:
        try:
            repeated = bool(consult_lessons(situation))
        except Exception:
            repeated = False
    try:
        record_feedback_strict(
            sid,
            str(expert or "chuyen_gia"),
            verdict,
            ly_do=str(ly_do or ""),
            nguyen_nhan_that=str(nguyen_nhan_that or ""),
            noi_dung_nan_lai=str(noi_dung_nan_lai or ""),
        )
    except SuggestionFeedbackStrictError as exc:
        return False, "⚠️ %s" % exc
    if verdict in ("sai", "mot_phan"):
        try:
            lesson = lesson_from_suggestion_feedback(
                {
                    "suggestion_id": sid,
                    "verdict": verdict,
                    "reason": str(ly_do or ""),
                    "true_cause": str(nguyen_nhan_that or ""),
                    "correction": str(noi_dung_nan_lai or ""),
                },
                situation,
            )
            LessonStore().add(lesson)
        except ImprovementError as exc:
            return True, "Đã ghi nhận đánh giá. (Chưa tạo được bài học: %s)" % exc
        try:
            record_repetition_event(sid, verdict, repeated)
        except Exception:
            pass
    return True, "Đã ghi nhận đánh giá “%s” cho gợi ý." % verdict_vi


def render_suggestion_widget(st: Any, suggestion_id: str, expert: str = "") -> None:
    """Three small rating buttons under a suggestion; 'một phần'/'sai' opens
    the 3 mandatory fields inline (still inside the chat)."""
    from aios_habit import suggestion_feedback as _sf

    sid = str(suggestion_id or "").strip()
    if not sid:
        return
    try:
        if _sf.get_feedback(sid):
            st.caption("Đã ghi nhận đánh giá cho gợi ý này. Cảm ơn chuyên gia.")
            return
    except Exception:
        pass
    key_base = "wsc_sg_" + re.sub(r"\W+", "_", sid)
    verdict_key = key_base + "_verdict"
    session_state = getattr(st, "session_state", None)
    if session_state is None:
        return

    def _get_state(name: str, default: Any = "") -> Any:
        try:
            return session_state.get(name, default)
        except Exception:
            return default

    def _set_state(name: str, value: Any) -> None:
        try:
            session_state[name] = value
        except Exception:
            pass

    st.markdown("**Chấm gợi ý này:**")
    columns = st.columns(3)
    pressed: Optional[str] = None
    buttons = (
        ("👍 Đúng", "dung"),
        ("😐 Một phần", "mot_phan"),
        ("👎 Sai", "sai"),
    )
    for column, (label, verdict_value) in zip(columns, buttons):
        with column:
            if st.button(label, key=key_base + "_" + verdict_value):
                pressed = verdict_value
    if pressed:
        _set_state(verdict_key, pressed)
    chosen = str(_get_state(verdict_key, "") or "")
    if chosen == "dung":
        ok, message = save_suggestion_feedback(sid, expert, "dung", "", "", "")
        (st.success if ok else st.warning)(message)
        _set_state(verdict_key, "")
        if ok and hasattr(st, "rerun"):
            st.rerun()
        return
    if chosen in ("mot_phan", "sai"):
        ly_do = st.text_input("Lý do", key=key_base + "_ly_do")
        nguyen_nhan = st.text_input("Nguyên nhân thật", key=key_base + "_nn")
        nan_lai = st.text_input("Nắn lại thế nào", key=key_base + "_sua")
        if st.button("Lưu đánh giá", key=key_base + "_save"):
            ok, message = save_suggestion_feedback(
                sid, expert, chosen, ly_do, nguyen_nhan, nan_lai
            )
            if ok:
                st.success(message)
                _set_state(verdict_key, "")
                if hasattr(st, "rerun"):
                    st.rerun()
            else:
                st.warning(message)


def repetition_metric_line() -> str:
    """One-line 'tỉ lệ lặp lại lỗi' metric for the review report."""
    from aios_habit.self_improvement import improvement_overview

    try:
        overview = improvement_overview()
    except Exception:
        return ""
    rates = overview.get("ti_le_lap_lai_theo_ky") or []
    if not rates:
        return "_Chưa có dữ liệu vòng cải thiện — hãy chấm vài gợi ý để bắt đầu._"
    latest = rates[-1]
    trend_vi = {
        "giam_dan": "đang giảm dần ✅",
        "khong_giam": "chưa giảm ⚠️",
        "khong_du_du_lieu": "chưa đủ dữ liệu",
    }.get(str(overview.get("xu_huong") or ""), "")
    return (
        "📉 **Tỉ lệ lặp lại lỗi:** %s%% (kỳ %s: %d lượt bị chê, %d lượt lặp lại) "
        "— xu hướng %s."
        % (
            round(float(latest.get("ti_le", 0.0)) * 100, 1),
            latest.get("ky", "—"),
            int(latest.get("tong", 0)),
            int(latest.get("lap_lai", 0)),
            trend_vi,
        )
    )
