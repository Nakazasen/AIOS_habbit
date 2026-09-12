"""Vietnamese Workspace Chat memory UI helpers (Goal 011)."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from aios_habit.workspace_memory_models import (
    CorrectionLessonCandidate,
    WorkspaceMemoryRecallItem,
    WorkspaceMemoryRecallRequest,
)
from aios_habit.workspace_memory_service import (
    append_memory_decision,
    apply_conflict_choice,
    default_decisions_path,
    find_near_duplicates,
    fold_vi,
    get_workspace_memory_enabled_preference,
    make_memory_decision,
    preview_memory_decision,
    read_effective_memory,
    recall_workspace_memory,
    tokenize,
)

PENDING_COMMAND_KEY = "wsc_memory_pending"
PENDING_CONFLICT_KEY = "wsc_memory_conflict"
LEASE_BUSY_MESSAGE = "Không ghi được vì sổ việc đang được máy khác cập nhật. Hãy thử lại sau."
REMEMBER_SUCCESS = "Đã nhớ bài học. AIOS sẽ dùng lại khi câu hỏi liên quan."
FORGET_SUCCESS = "Đã quên bài học. AIOS ngừng dùng nội dung này ngay."
CORRECTION_SUCCESS = "Đã lưu bài học từ phần sửa của bạn."
EMPTY_STATEMENT = "Hãy nhập nội dung bài học trước khi xác nhận."
SCOPE_REQUIRED = "Hãy nêu phạm vi áp dụng trước khi xác nhận."
NOT_FOUND_FORGET_ERROR = "Không tìm thấy bài học phù hợp để quên. Hãy kiểm tra lại nội dung bài học."


def why_memory_panel_title() -> str:
    return "Vì sao AIOS nhớ điều này?"


def memory_toggle_label() -> str:
    return "Cho AIOS ghi nhớ để hỗ trợ tôi tốt hơn"


def memory_toggle_help() -> str:
    return "AIOS chỉ lưu bài học khi bạn xác nhận. Lựa chọn này được giữ trên máy này."


def memory_toggle_status(enabled: bool) -> str:
    return "Đang bật ghi nhớ" if enabled else "Đang tắt ghi nhớ"


def correction_action_label() -> str:
    return "Sửa để AIOS học"


def format_why_memory_lines(items: Sequence[WorkspaceMemoryRecallItem]) -> tuple[str, ...]:
    lines: list[str] = []
    for item in items:
        lines.append(f"{item.title} — nguồn {item.source_kind}, đã xác nhận.")
        if item.applies_when:
            lines.append(f"Áp dụng khi: {item.applies_when}")
        lines.append(f"Căn cứ: {len(item.evidence_refs)} mục bằng chứng.")
    return tuple(lines)


def remember_preview_text(statement: str, scope: str) -> str:
    preview = preview_memory_decision(
        action="confirm",
        statement=statement,
        scope=scope,
        evidence_refs=("user_confirm",),
    )
    return (
        f"Xem trước nội dung sẽ nhớ trong phạm vi {preview['scope']}: {preview['statement']}. "
        "Chưa lưu cho đến khi bạn bấm xác nhận."
    )


def forget_preview_text(statement: str) -> str:
    return (
        f"Xem trước: AIOS sẽ ngừng dùng bài học “{statement.strip()}”. "
        "Lịch sử quyết định vẫn được giữ. Bấm xác nhận để quên."
    )


def confirm_cancelled_message() -> str:
    return "Đã hủy. Không ghi gì vào sổ việc."


def remember_command_prefixes() -> tuple[str, ...]:
    return ("Hãy nhớ:", "Hay nho:")


def forget_command_prefixes() -> tuple[str, ...]:
    return ("Hãy quên:", "Hay quen:")


def parse_memory_command(text: str) -> dict[str, str] | None:
    raw = (text or "").strip()
    for prefix in ("Hãy nhớ:", "Hãy nhớ"):
        if raw.startswith(prefix):
            return {"action": "confirm", "statement": raw[len(prefix):].strip()}
    for prefix in ("Hãy quên:", "Hãy quên"):
        if raw.startswith(prefix):
            return {"action": "forget", "statement": raw[len(prefix):].strip()}
    return None


def correction_preview_text(candidate: CorrectionLessonCandidate) -> str:
    return (
        f"Bài học đề xuất: {candidate.statement}. Áp dụng khi: {candidate.applies_when}. "
        "Chưa dùng cho câu hỏi khác cho đến khi bạn xác nhận."
    )


def conflict_choice_labels() -> dict[str, str]:
    return {
        "merge": "Gộp thành một bài học",
        "replace": "Thay bài học cũ",
        "keep_both": "Giữ cả hai và cảnh báo",
        "cancel": "Hủy, không lưu",
    }


def queue_memory_command_if_present(text: str) -> bool:
    if not get_workspace_memory_enabled_preference():
        return False
    parsed = parse_memory_command(text)
    if not parsed or not parsed.get("statement"):
        return False
    try:
        import streamlit as st
    except Exception:
        return False
    st.session_state[PENDING_COMMAND_KEY] = parsed
    return True


def _safe_error(exc: BaseException) -> str:
    text = str(exc)
    if "lease" in text.lower() or "bận" in text or "đang được" in text:
        return LEASE_BUSY_MESSAGE
    return "Không ghi được sổ việc lúc này. Hãy thử lại."


def _resolve_forget_target(statement: str, scope: str, path: Path) -> tuple[str, str] | None:
    """Resolve one active memory in the current scope, or refuse ambiguity."""
    records = [record for record in read_effective_memory(path) if record.get("scope") == scope]
    normalized = fold_vi(statement)
    exact = [
        record
        for record in records
        if str(record.get("source_id") or "") == statement
        or fold_vi(str(record.get("statement") or "")) == normalized
    ]
    if len(exact) == 1:
        return str(exact[0]["source_id"]), str(exact[0]["scope"])
    if len(exact) > 1:
        return None

    statement_tokens = tokenize(statement)
    scored = [
        (
            len(statement_tokens)
            if statement_tokens
            and statement_tokens.issubset(tokenize(str(record.get("statement") or "")))
            else 0,
            record,
        )
        for record in records
    ]
    best_overlap = max((score for score, _ in scored), default=0)
    best = [record for score, record in scored if score == best_overlap and score > 0]
    if len(best) != 1:
        return None
    return str(best[0]["source_id"]), str(best[0]["scope"])


def _scope_for(workspace_id: str) -> str:
    value = (workspace_id or "default").strip() or "default"
    return f"workspace:{value}"


def render_workspace_memory_panel(items: Sequence[WorkspaceMemoryRecallItem] | None = None, *, locale: str = "vi") -> None:
    if not get_workspace_memory_enabled_preference():
        return
    try:
        import streamlit as st
    except Exception:
        return
    st.caption(why_memory_panel_title())
    if not items:
        st.caption("Chưa có bài học đã xác nhận cho câu hỏi này.")
        return
    for line in format_why_memory_lines(items):
        st.caption(line)


def render_workspace_memory_workspace(
    *,
    conversation_id: str,
    last_question: str = "",
    last_assistant_id: str = "",
    last_trace_id: str = "",
    workspace_id: str = "default",
    collection_id: str = "tri_thuc",
    locale: str = "vi",
) -> None:
    if not get_workspace_memory_enabled_preference():
        return
    try:
        import streamlit as st
    except Exception:
        return

    items: tuple[WorkspaceMemoryRecallItem, ...] = ()
    question = (last_question or "").strip()
    if question and parse_memory_command(question) is None:
        try:
            result = recall_workspace_memory(
                WorkspaceMemoryRecallRequest(
                    question=question,
                    workspace_id=workspace_id or "default",
                    collection_id=collection_id or "tri_thuc",
                    provider_mode="local",
                    include_local_only=True,
                )
            )
            items = result.items
        except Exception:
            items = ()
    render_workspace_memory_panel(items, locale=locale)
    _render_pending_command(workspace_id=workspace_id)
    if last_assistant_id:
        _render_correction_form(
            message_id=last_assistant_id,
            trace_id=last_trace_id or None,
            workspace_id=workspace_id,
        )


def _render_pending_command(*, workspace_id: str) -> None:
    try:
        import streamlit as st
    except Exception:
        return
    pending = st.session_state.get(PENDING_COMMAND_KEY)
    if not isinstance(pending, dict):
        return
    action = str(pending.get("action") or "")
    statement = str(pending.get("statement") or "").strip()
    scope = _scope_for(workspace_id)
    path = default_decisions_path()
    if action == "confirm":
        st.info(remember_preview_text(statement, scope))
    else:
        st.info(forget_preview_text(statement))

    conflict = st.session_state.get(PENDING_CONFLICT_KEY)
    if action == "confirm" and isinstance(conflict, dict):
        st.warning("Đã có bài học gần giống. Hãy chọn cách xử lý trước khi lưu.")
        labels = conflict_choice_labels()
        choice = st.radio(
            "Cách xử lý bài học trùng",
            options=list(labels),
            format_func=lambda key: labels[key],
            key="wsc_memory_conflict_choice",
        )
        apply_col, cancel_col = st.columns(2)
        with apply_col:
            if st.button("Áp dụng lựa chọn", key="wsc_memory_conflict_apply"):
                candidate = CorrectionLessonCandidate(
                    candidate_id="cmd_dup",
                    statement=statement,
                    applies_when=scope,
                    does_not_apply_when="",
                    message_ref="user_confirm",
                )
                try:
                    stored = apply_conflict_choice(choice, candidate, path=path, scope=scope)
                except Exception as exc:
                    st.session_state.wsc_action_error = _safe_error(exc)
                    return
                st.session_state.pop(PENDING_COMMAND_KEY, None)
                st.session_state.pop(PENDING_CONFLICT_KEY, None)
                st.session_state.wsc_action_message = (
                    confirm_cancelled_message() if stored is None else REMEMBER_SUCCESS
                )
                st.rerun()
        with cancel_col:
            if st.button("Hủy", key="wsc_memory_conflict_cancel"):
                st.session_state.pop(PENDING_COMMAND_KEY, None)
                st.session_state.pop(PENDING_CONFLICT_KEY, None)
                st.session_state.wsc_action_message = confirm_cancelled_message()
                st.rerun()
        return

    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("Xác nhận", key="wsc_memory_confirm"):
            if not statement:
                st.session_state.wsc_action_error = EMPTY_STATEMENT
                return
            try:
                if action == "confirm":
                    hits = find_near_duplicates(statement, scope, path)
                    if hits:
                        st.session_state[PENDING_CONFLICT_KEY] = {"statement": statement, "scope": scope}
                        st.rerun()
                    decision = make_memory_decision(
                        action="confirm",
                        statement=statement,
                        scope=scope,
                        evidence_refs=("user_confirm",),
                        applies_when=scope,
                    )
                    append_memory_decision(decision, path=path)
                    st.session_state.wsc_action_message = REMEMBER_SUCCESS
                else:
                    target_memory_id = pending.get("memory_id")
                    target_scope = scope
                    if not target_memory_id:
                        resolved = _resolve_forget_target(statement, scope, path)
                        if resolved is not None:
                            target_memory_id, target_scope = resolved

                    if not target_memory_id:
                        st.session_state.wsc_action_error = NOT_FOUND_FORGET_ERROR
                        st.session_state.pop(PENDING_COMMAND_KEY, None)
                        st.rerun()
                        return

                    decision = make_memory_decision(
                        action="forget",
                        statement=statement,
                        scope=target_scope,
                        evidence_refs=("user_confirm",),
                        memory_id=target_memory_id,
                    )
                    append_memory_decision(decision, path=path)
                    st.session_state.wsc_action_message = FORGET_SUCCESS
                st.session_state.pop(PENDING_COMMAND_KEY, None)
                st.rerun()
            except Exception as exc:
                st.session_state.wsc_action_error = _safe_error(exc)
    with cancel_col:
        if st.button("Hủy", key="wsc_memory_cancel"):
            st.session_state.pop(PENDING_COMMAND_KEY, None)
            st.session_state.pop(PENDING_CONFLICT_KEY, None)
            st.session_state.wsc_action_message = confirm_cancelled_message()
            st.rerun()


def _render_correction_form(*, message_id: str, trace_id: str | None, workspace_id: str) -> None:
    try:
        import streamlit as st
    except Exception:
        return
    corr_conflict_key = f"wsc_corr_conflict_{message_id}"
    pending_conflict = st.session_state.get(corr_conflict_key)
    with st.expander(correction_action_label(), expanded=bool(pending_conflict)):
        if isinstance(pending_conflict, dict):
            st.warning("Đã có bài học gần trùng hoặc mâu thuẫn. Hãy chọn cách xử lý trước khi lưu.")
            labels = conflict_choice_labels()
            choice = st.radio(
                "Cách xử lý bài học trùng",
                options=list(labels),
                format_func=lambda key: labels[key],
                key=f"wsc_corr_choice_{message_id}",
            )
            apply_col, cancel_col = st.columns(2)
            with apply_col:
                if st.button("Áp dụng lựa chọn", key=f"wsc_corr_apply_{message_id}"):
                    candidate = CorrectionLessonCandidate(
                        candidate_id=pending_conflict["candidate_id"],
                        statement=pending_conflict["statement"],
                        applies_when=pending_conflict["applies_when"],
                        does_not_apply_when=pending_conflict.get("does_not_apply_when", ""),
                        message_ref=pending_conflict["message_ref"],
                        trace_ref=pending_conflict.get("trace_ref"),
                    )
                    path = default_decisions_path()
                    scope = pending_conflict["scope"]
                    try:
                        stored = apply_conflict_choice(choice, candidate, path=path, scope=scope)
                        st.session_state.pop(corr_conflict_key, None)
                        if stored is None:
                            st.session_state.wsc_action_message = confirm_cancelled_message()
                        else:
                            st.session_state.wsc_action_message = CORRECTION_SUCCESS
                        st.rerun()
                    except Exception as exc:
                        st.session_state.wsc_action_error = _safe_error(exc)
            with cancel_col:
                if st.button("Hủy lựa chọn", key=f"wsc_corr_cancel_conflict_{message_id}"):
                    st.session_state.pop(corr_conflict_key, None)
                    st.session_state.wsc_action_message = confirm_cancelled_message()
                    st.rerun()
            return

        statement = st.text_area(
            "Phần sửa cần nhớ",
            key=f"wsc_corr_statement_{message_id}",
            height=80,
        )
        applies_when = st.text_input(
            "Áp dụng khi",
            key=f"wsc_corr_applies_{message_id}",
        )
        does_not_apply = st.text_input(
            "Không áp dụng khi",
            key=f"wsc_corr_negative_{message_id}",
        )
        if statement.strip() and applies_when.strip():
            candidate = CorrectionLessonCandidate(
                candidate_id=f"corr_{message_id}",
                statement=statement.strip(),
                applies_when=applies_when.strip(),
                does_not_apply_when=does_not_apply.strip(),
                message_ref=message_id,
                trace_ref=trace_id,
            )
            st.caption(correction_preview_text(candidate))
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("Xác nhận bài học", key=f"wsc_corr_confirm_{message_id}"):
                if not statement.strip():
                    st.session_state.wsc_action_error = EMPTY_STATEMENT
                    return
                if not applies_when.strip():
                    st.session_state.wsc_action_error = SCOPE_REQUIRED
                    return
                candidate = CorrectionLessonCandidate(
                    candidate_id=f"corr_{message_id}",
                    statement=statement.strip(),
                    applies_when=applies_when.strip(),
                    does_not_apply_when=does_not_apply.strip(),
                    message_ref=message_id,
                    trace_ref=trace_id,
                )
                path = default_decisions_path()
                scope = _scope_for(workspace_id)
                try:
                    hits = find_near_duplicates(candidate.statement, scope, path)
                    if hits:
                        st.session_state[corr_conflict_key] = {
                            "candidate_id": candidate.candidate_id,
                            "statement": candidate.statement,
                            "applies_when": candidate.applies_when,
                            "does_not_apply_when": candidate.does_not_apply_when,
                            "message_ref": candidate.message_ref,
                            "trace_ref": candidate.trace_ref,
                            "scope": scope,
                        }
                    else:
                        append_memory_decision(
                            candidate.to_decision(
                                actor_label="người dùng",
                                scope=scope,
                                evidence_refs=(message_id,),
                            ),
                            path=path,
                        )
                        st.session_state.wsc_action_message = CORRECTION_SUCCESS
                    st.rerun()
                except Exception as exc:
                    st.session_state.wsc_action_error = _safe_error(exc)
        with cancel_col:
            if st.button("Hủy bài học", key=f"wsc_corr_cancel_{message_id}"):
                st.session_state.pop(corr_conflict_key, None)
                st.session_state.wsc_action_message = confirm_cancelled_message()
                st.rerun()
