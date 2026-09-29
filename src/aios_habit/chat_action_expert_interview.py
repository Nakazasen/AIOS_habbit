"""Builtin chat action: preview the expert interview flow for a topic.

Wires the `expert_interview*` cluster (TOOL-1 inventory: reachable only through
the interview screen of the workspace case UI) into the chat through the
`chat_action` framework:

- `WorkspaceCaseRepository.list_gap_candidates` maps the free-text topic to the
  knowledge gaps already stored in the local case store.
- `ExpertInterviewRepository.list_sessions` + `get_interview_plan` +
  `list_turns` read the plans, sessions and turns behind those gaps.
- `adaptive_interview_engine.propose_next_action` (deterministic fallback, no
  gateway client) previews the next question of the latest matched session;
  `generate_seed_questions` previews the seed questions when no session exists.

Read-only: lists what is already stored, runs the engine in memory, and never
creates a gap/plan/session/turn. A missing case store is never initialized.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple

from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    BLOCK_TABLE,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    normalize_text,
    register_action,
)

ACTION_NAME = "phong_van_chuyen_gia"
ACTION_TITLE = "Phỏng vấn chuyên gia"

_HINTS = (
    "phỏng vấn chuyên gia",
    "chạy phỏng vấn chuyên gia",
)

# Connectors stripped from the topic tail: "về quy trình hàn" -> "quy trình hàn".
_TOPIC_CONNECTORS = (
    "về việc",
    "về chủ đề",
    "với chủ đề",
    "chủ đề",
    "về",
    "cho",
)

_PUNCTUATION = " \t\r\n.,:;!?…\"'“”‘’()[]"

_MAX_SESSIONS = 10
_MAX_TURNS = 6
_MAX_SEED_QUESTIONS = 8

_SESSION_STATE_LABELS = {
    "ready": "Sẵn sàng",
    "active": "Đang chạy",
    "paused": "Tạm dừng",
    "awaiting_confirmation": "Chờ xác nhận",
    "completed": "Hoàn tất",
    "stopped": "Đã dừng",
    "blocked": "Đang chặn",
}

# Sessions whose flow can still propose a next question.
_OPEN_SESSION_STATES = ("ready", "active", "paused", "awaiting_confirmation")

_ACTION_LABELS = {
    "ask_followup": "Hỏi làm rõ thêm",
    "request_confirmation": "Xin xác nhận",
    "complete": "Hoàn tất phiên",
    "pause": "Tạm dừng phiên",
    "escalate": "Chuyển người xử lý",
}


@dataclass(frozen=True)
class _SessionEntry:
    """One stored session joined with its plan and gap metadata."""

    session: Any
    plan: Any
    gap_ids: Tuple[str, ...]
    gap_titles: Tuple[str, ...]
    seed_texts: Tuple[str, ...]

    @property
    def updated_at(self) -> str:
        return str(self.session.updated_at or self.session.started_at or "")


def _message(text: str) -> ChatActionOutcome:
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=ACTION_TITLE,
        blocks=(ChatActionBlock(BLOCK_MARKDOWN, text=text),),
    )


def _default_case_db_path() -> Path:
    from aios_habit.workspace_case_repository import default_workspace_cases_db_path

    return default_workspace_cases_db_path()


def _topic_from_question(question: str) -> str:
    """Extract the free-text topic typed after the hint (keeps typed accents)."""
    raw = str(question or "")
    lowered = raw.lower()
    for hint in _HINTS:
        index = lowered.find(hint)
        if index >= 0:
            return _clean_topic(raw[index + len(hint) :])
    normalized = normalize_text(raw)
    for hint in _HINTS:
        normalized_hint = normalize_text(hint)
        index = normalized.find(normalized_hint)
        if index >= 0:
            return _clean_topic(normalized[index + len(normalized_hint) :])
    return ""


def _clean_topic(tail: str) -> str:
    cleaned = str(tail or "").strip(_PUNCTUATION)
    changed = True
    while changed and cleaned:
        changed = False
        lowered = cleaned.lower()
        for connector in _TOPIC_CONNECTORS:
            if lowered == connector:
                return ""
            if lowered.startswith(connector + " "):
                cleaned = cleaned[len(connector) :].strip(_PUNCTUATION)
                changed = True
                break
    return cleaned


def _matches(topic_norm: str, text: Any) -> bool:
    return bool(topic_norm) and topic_norm in normalize_text(str(text or ""))


def _excerpt(text: Any, limit: int = 160) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _session_row(index: int, entry: _SessionEntry, turn_count: Any) -> Tuple[str, ...]:
    session = entry.session
    topic = " · ".join(entry.gap_titles) if entry.gap_titles else "Chưa gắn chủ đề"
    state = _SESSION_STATE_LABELS.get(str(session.state), str(session.state or "—"))
    updated = str(entry.updated_at)[:16].replace("T", " ")
    return (
        str(index),
        str(session.session_id)[:12],
        str(session.expert_id),
        state,
        topic,
        str(turn_count),
        updated or "—",
    )


def _next_question_note(entry: _SessionEntry, turns: Sequence[Any], gap: Any) -> str:
    plan = entry.plan
    if plan is None or gap is None:
        return "Chưa đủ kế hoạch/khoảng trống để động cơ thích ứng gợi ý câu hỏi tiếp theo."
    history = [
        {
            "sequence": turn.sequence,
            "question_text": turn.question_text,
            "answer_text": turn.answer_text,
            "state": turn.answer_state,
        }
        for turn in turns
    ]
    latest_answer = history[-1]["answer_text"] if history else ""
    try:
        from aios_habit.adaptive_interview_engine import propose_next_action

        decision = propose_next_action(
            history,
            plan.budget,
            plan.completion_rubric,
            latest_answer,
            gap,
            gateway_client=None,
        )
    except Exception:
        return "Chưa chạy được động cơ thích ứng để gợi ý câu hỏi tiếp theo."
    label = _ACTION_LABELS.get(str(decision.action), str(decision.action))
    question = str(decision.question or "").strip()
    if decision.action == "ask_followup" and question:
        return f"Câu hỏi tiếp theo (động cơ thích ứng gợi ý): {question}"
    if question:
        return f"Đề xuất của động cơ thích ứng — {label}: {question}"
    return f"Đề xuất của động cơ thích ứng — {label}."


def _seed_table(gap: Any) -> ChatActionBlock:
    from aios_habit.adaptive_interview_engine import generate_seed_questions

    seeds = generate_seed_questions(gap)
    rows = []
    for seed in seeds[:_MAX_SEED_QUESTIONS]:
        aspects = ", ".join(str(item) for item in seed.expected_aspects)
        rows.append((str(seed.suggested_order), str(seed.text), aspects or "—"))
    return ChatActionBlock(
        BLOCK_TABLE,
        headers=("#", "Câu hỏi mồi", "Khía cạnh cần khai thác"),
        rows=rows,
        caption=f"Chủ đề: {gap.title} — chưa có phiên nào, bộ câu hỏi mồi (chưa mở phiên).",
    )


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    topic = _topic_from_question(request.question)
    topic_norm = normalize_text(topic)
    raw_path = str(request.context.get("case_db_path") or "").strip()
    db_path = Path(raw_path) if raw_path else _default_case_db_path()
    if not db_path.exists():
        return _message(
            "Máy này chưa có sổ hồ sơ phỏng vấn nên chưa xem được phiên nào. "
            "Hãy mở mục Phỏng vấn chuyên gia trong workspace để tạo phiên trước nhé."
        )

    try:
        from aios_habit.expert_interview_repository import ExpertInterviewRepository
        from aios_habit.workspace_case_repository import WorkspaceCaseRepository

        case_repo = WorkspaceCaseRepository(db_path)
        interview_repo = ExpertInterviewRepository(db_path)
        gaps = list(case_repo.list_gap_candidates())
        gap_by_id = {gap.gap_id: gap for gap in gaps}
        session_entries = []
        for session in interview_repo.list_sessions():
            plan = interview_repo.get_interview_plan(session.plan_id)
            gap_ids = tuple(plan.gap_ids) if plan is not None else ()
            session_entries.append(
                _SessionEntry(
                    session=session,
                    plan=plan,
                    gap_ids=gap_ids,
                    gap_titles=tuple(
                        gap_by_id[gid].title for gid in gap_ids if gid in gap_by_id
                    ),
                    seed_texts=tuple(q.text for q in plan.seed_questions) if plan is not None else (),
                )
            )
    except Exception:
        return _message("Chưa đọc được hồ sơ phỏng vấn lúc này. Bạn thử lại sau nhé.")

    matched_gaps = [
        gap
        for gap in gaps
        if _matches(topic_norm, gap.title)
        or _matches(topic_norm, gap.description)
        or _matches(topic_norm, gap.scope)
    ]
    if not topic_norm:
        matched_gaps = [gap for gap in gaps if str(gap.status) == "accepted"]
    matched_gap_ids = {gap.gap_id for gap in matched_gaps}

    def _entry_matches(entry: _SessionEntry) -> bool:
        if not topic_norm:
            return True
        if any(gid in matched_gap_ids for gid in entry.gap_ids):
            return True
        if _matches(topic_norm, entry.session.expert_id):
            return True
        return any(_matches(topic_norm, text) for text in entry.gap_titles) or any(
            _matches(topic_norm, text) for text in entry.seed_texts
        )

    matched_sessions = [entry for entry in session_entries if _entry_matches(entry)]
    matched_sessions.sort(key=lambda entry: entry.updated_at, reverse=True)

    if not matched_sessions and not matched_gaps:
        if topic:
            return _message(
                f"Chưa tìm thấy chủ đề “{topic}” trong hồ sơ phỏng vấn chuyên gia. "
                f"Hiện có {len(gaps)} khoảng trống tri thức và {len(session_entries)} phiên đã lưu; "
                "hãy mở mục Phỏng vấn chuyên gia trong workspace để tạo kế hoạch trước nhé."
            )
        return _message(
            "Hồ sơ chưa có phiên phỏng vấn chuyên gia nào. "
            "Hãy mở mục Phỏng vấn chuyên gia trong workspace để tạo kế hoạch và phiên đầu tiên nhé."
        )

    blocks = []
    if topic:
        blocks.append(
            ChatActionBlock(
                BLOCK_MARKDOWN,
                text=f"Các phiên phỏng vấn liên quan tới “{topic}” — chỉ đọc, không mở phiên mới.",
            )
        )
    else:
        blocks.append(
            ChatActionBlock(
                BLOCK_MARKDOWN,
                text="Các phiên phỏng vấn chuyên gia đã lưu — chỉ đọc, không mở phiên mới.",
            )
        )

    if matched_sessions:
        rows = []
        for index, entry in enumerate(matched_sessions[:_MAX_SESSIONS], start=1):
            try:
                turn_count = len(interview_repo.list_turns(entry.session.session_id))
            except Exception:
                turn_count = "—"
            rows.append(_session_row(index, entry, turn_count))
        caption = ""
        if len(matched_sessions) > _MAX_SESSIONS:
            caption = f"Hiện {_MAX_SESSIONS}/{len(matched_sessions)} phiên gần nhất."
        blocks.append(
            ChatActionBlock(
                BLOCK_TABLE,
                headers=("#", "Phiên", "Chuyên gia", "Trạng thái", "Chủ đề", "Số lượt", "Cập nhật"),
                rows=rows,
                caption=caption,
            )
        )

        latest = matched_sessions[0]
        state = str(latest.session.state)
        if state in _OPEN_SESSION_STATES:
            try:
                turns = list(interview_repo.list_turns(latest.session.session_id))
            except Exception:
                turns = []
            if turns:
                lines = []
                for turn in turns[-_MAX_TURNS:]:
                    lines.append(f"**Hỏi:** {_excerpt(turn.question_text, 200)}")
                    lines.append(f"**Đáp:** {_excerpt(turn.answer_text) or '(chưa trả lời)'}")
                blocks.append(
                    ChatActionBlock(
                        BLOCK_MARKDOWN,
                        text=(
                            f"Diễn biến phiên gần nhất “{str(latest.session.session_id)[:12]}” "
                            f"({_MAX_TURNS} lượt cuối):\n\n" + "\n\n".join(lines)
                        ),
                    )
                )
            gap = gap_by_id.get(latest.gap_ids[0]) if latest.gap_ids else None
            blocks.append(
                ChatActionBlock(
                    BLOCK_MARKDOWN,
                    text=_next_question_note(latest, turns, gap),
                )
            )
        else:
            blocks.append(
                ChatActionBlock(
                    BLOCK_MARKDOWN,
                    text=(
                        f"Phiên “{str(latest.session.session_id)[:12]}” đang ở trạng thái "
                        f"{_SESSION_STATE_LABELS.get(state, state)} nên không còn câu hỏi tiếp theo."
                    ),
                )
            )
    else:
        rows = [
            (gap.gap_id[:12], gap.title, str(gap.scope), str(gap.status))
            for gap in matched_gaps[:_MAX_SEED_QUESTIONS]
        ]
        blocks.append(
            ChatActionBlock(
                BLOCK_TABLE,
                headers=("Khoảng trống", "Chủ đề", "Phạm vi", "Trạng thái"),
                rows=rows,
                caption="Khoảng trống tri thức khớp chủ đề (chưa có phiên phỏng vấn nào).",
            )
        )
        blocks.append(_seed_table(matched_gaps[0]))

    return ChatActionOutcome(action=ACTION_NAME, title=ACTION_TITLE, blocks=tuple(blocks))


def register() -> ChatAction:
    return register_action(
        ChatAction(
            name=ACTION_NAME,
            title=ACTION_TITLE,
            hints=_HINTS,
            handler=_handler,
            description=(
                "Xem các phiên phỏng vấn chuyên gia đã lưu theo chủ đề và câu hỏi tiếp theo "
                "(nối nhóm module expert_interview*, chỉ đọc)."
            ),
        )
    )


register()
