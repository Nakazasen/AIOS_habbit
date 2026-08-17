import streamlit as st
from typing import List, Dict, Any, Callable, Optional
from aios_habit.workspace_chat_models import DocumentNotebook, WorkspaceConversation, ChatMessage, TemporaryConversationSource

def get_vietnamese_labels():
    return {
        "notebooks_title": "Sổ tài liệu của tôi",
        "open_notebook": "Mở sổ",
        "conversations": "Cuộc trò chuyện",
        "create_conversation": "Tạo cuộc trò chuyện mới",
        "temp_sources": "Nguồn tạm trong cuộc trò chuyện",
        "not_saved_longterm": "Chưa lưu lâu dài",
        "only_this_conversation": "Chỉ dùng trong cuộc trò chuyện này",
        "main_answer": "Tóm tắt nguồn đang dùng",
        "proven_sources": "Nguồn đang bật cho câu hỏi",
        "to_check": "Cần kiểm tra lại",
        "next_actions": "Việc nên làm tiếp",
        "save_to_case": "Lưu vào hồ sơ",
        "explain_conclusion": "Xem đoạn xem trước sẽ dùng ở bước sau",
        # Phase 2H labels
        "ai_action": "Hỏi",
        "source_check": "Kiểm tra",
        "ai_not_answered": "AI chưa trả lời",
        "ai_answered": "AI đã trả lời",
        "insufficient_context": "Thiếu ngữ cảnh",
        "sources_sent": "Nguồn gửi cùng câu hỏi",
        "quick_paste": "Dán nhanh nhiều nguồn",
        "quick_paste_add": "Thêm làm 1 nguồn",
        "question_placeholder": "Nhập câu hỏi bạn muốn AI hỗ trợ...",
    }

PRIVACY_CHOICE_SENDABLE = "Có thể gửi nội dung tới AI bên ngoài"
PRIVACY_CHOICE_LOCAL_ONLY = "Chỉ dùng trên máy / không gửi AI"
PRIVACY_FIELD_LABEL = "Nguồn này được dùng thế nào?"
PRIVACY_HELP_COPY = "Chỉ chọn gửi AI ngoài khi nội dung được phép chia sẻ. Bạn vẫn cần bấm Hỏi để gửi."
PRIVACY_EDITOR_LABEL = "Quyền riêng tư nguồn"
PRIVACY_SENDABLE_STATUS = "Nội dung có thể gửi AI ngoài khi bạn bấm Hỏi"
PRIVACY_BLOCKED_STATUS = "Nguồn này sẽ không được gửi AI"
PRIVACY_SAVE_BUTTON = "Lưu lựa chọn"
PRIVACY_SAVED_FEEDBACK = "Đã cập nhật quyền riêng tư nguồn."
PRIVACY_AI_HARD_BLOCK_COPY = "Có nguồn không được gửi AI. Hãy tắt nguồn đó hoặc đổi lựa chọn quyền riêng tư."
PRIVACY_SENDABLE_LABELS = {"cloud_safe", "public"}
NOTEBOOK_ARCHIVE_ACTION = "Lưu trữ sổ"
NOTEBOOK_ARCHIVE_CONFIRM_COPY = "Sổ này sẽ được ẩn khỏi danh sách chính. Dữ liệu bên trong không bị xóa."
NOTEBOOK_ARCHIVE_CONFIRM_ACTION = "Xác nhận lưu trữ"
NOTEBOOK_ARCHIVE_CANCEL_ACTION = "Hủy"
NOTEBOOK_ARCHIVED_SECTION = "Sổ đã lưu trữ"
NOTEBOOK_ARCHIVED_EMPTY_COPY = "Chưa có sổ đã lưu trữ."
NOTEBOOK_RESTORE_ACTION = "Khôi phục sổ"
NOTEBOOK_ARCHIVE_SUCCESS = "Đã lưu trữ sổ."
NOTEBOOK_RESTORE_SUCCESS = "Đã khôi phục sổ."
NOTEBOOK_ARCHIVE_FAILURE = "Không thể lưu trữ sổ. Vui lòng thử lại."
NOTEBOOK_RESTORE_FAILURE = "Không thể khôi phục sổ. Vui lòng thử lại."
NOTEBOOK_MISSING_COPY = "Không tìm thấy sổ này. Danh sách đã được cập nhật."
NOTEBOOK_NO_DELETE_COPY = "Không xóa dữ liệu trong Phase 2I."

NOTEBOOK_DELETE_ACTION = "Xóa vĩnh viễn sổ"
NOTEBOOK_DELETE_WARNING = "Hành động này sẽ xóa vĩnh viễn sổ và toàn bộ dữ liệu bên trong. Không thể khôi phục."
NOTEBOOK_DELETE_PROMPT = "Nhập chính xác tên sổ để xác nhận xóa"
NOTEBOOK_DELETE_ACK = "Tôi hiểu dữ liệu sẽ bị xóa vĩnh viễn"
NOTEBOOK_DELETE_CONFIRM = "Xác nhận xóa vĩnh viễn"
NOTEBOOK_DELETE_SUCCESS = "Đã xóa vĩnh viễn sổ."
NOTEBOOK_DELETE_WRONG_TITLE = "Không thể xóa sổ vì tên xác nhận chưa đúng."
NOTEBOOK_DELETE_FAILURE = "Không thể xóa sổ. Vui lòng thử lại."


def privacy_label_is_sendable(privacy_label: str) -> bool:
    if privacy_label is None:
        return False
    return privacy_label.strip().lower() in PRIVACY_SENDABLE_LABELS


def owner_choice_to_privacy_label(owner_choice: str) -> str:
    if owner_choice == PRIVACY_CHOICE_LOCAL_ONLY:
        return "local_only"
    return "cloud_safe"


def privacy_label_to_owner_choice(privacy_label: str) -> str:
    if privacy_label_is_sendable(privacy_label):
        return PRIVACY_CHOICE_SENDABLE
    return PRIVACY_CHOICE_LOCAL_ONLY


def render_privacy_choice(key: str, privacy_label: str = "machine_only") -> str:
    choices = [PRIVACY_CHOICE_SENDABLE, PRIVACY_CHOICE_LOCAL_ONLY]
    initial_choice = privacy_label_to_owner_choice(privacy_label)
    return st.radio(
        PRIVACY_FIELD_LABEL,
        choices,
        index=choices.index(initial_choice),
        key=key,
        help=PRIVACY_HELP_COPY,
    )

def render_notebook_header():
    st.title("📚 Sổ tài liệu của tôi")
    st.write("Quản lý các tài liệu, hồ sơ và thực hiện hỏi đáp riêng biệt theo từng sổ công việc.")

def render_notebook_card(
    nb: DocumentNotebook,
    conv_count: int,
    on_open: Callable[[str], None],
    on_archive_request: Callable[[str], None] = None,
    on_archive_confirm: Callable[[str], None] = None,
    on_archive_cancel: Callable[[str], None] = None,
    archive_pending: bool = False,
    on_delete_request: Callable[[str], None] = None,
    on_delete_confirm: Callable[[str, str, bool], None] = None,
    on_delete_cancel: Callable[[str], None] = None,
    delete_pending: bool = False,
):
    labels = get_vietnamese_labels()
    with st.container():
        st.markdown(f"### 📂 {nb.title}")
        st.write(nb.description or "Không có mô tả.")
        st.write(f"Số cuộc trò chuyện: `{conv_count}`")
        if st.button(f"{labels['open_notebook']} {nb.title}", key=f"open_nb_{nb.id}"):
            on_open(nb.id)
        if on_archive_request is not None:
            if archive_pending:
                st.warning(NOTEBOOK_ARCHIVE_CONFIRM_COPY)
                st.info(NOTEBOOK_NO_DELETE_COPY)
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button(NOTEBOOK_ARCHIVE_CONFIRM_ACTION, key=f"confirm_archive_nb_{nb.id}"):
                        on_archive_confirm(nb.id)
                with cancel_col:
                    if st.button(NOTEBOOK_ARCHIVE_CANCEL_ACTION, key=f"cancel_archive_nb_{nb.id}"):
                        on_archive_cancel(nb.id)
            elif st.button(NOTEBOOK_ARCHIVE_ACTION, key=f"archive_nb_{nb.id}"):
                on_archive_request(nb.id)

        # Danger zone
        st.write("---")
        st.markdown("**Vùng nguy hiểm**")
        if on_delete_request is not None:
            if delete_pending:
                st.error(NOTEBOOK_DELETE_WARNING)
                confirm_title = st.text_input(
                    NOTEBOOK_DELETE_PROMPT,
                    placeholder=f"Để trống hoặc nhập: {nb.title}",
                    key=f"delete_confirm_title_active_{nb.id}"
                )
                ack = st.checkbox(
                    NOTEBOOK_DELETE_ACK,
                    key=f"delete_confirm_ack_active_{nb.id}"
                )
                title_ok = (
                    not confirm_title
                    or confirm_title.strip().lower() == nb.title.strip().lower()
                )
                btn_disabled = not (title_ok and ack)

                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button(
                        NOTEBOOK_DELETE_CONFIRM,
                        key=f"confirm_delete_nb_{nb.id}",
                        disabled=btn_disabled
                    ):
                        effective_title = confirm_title.strip() if confirm_title.strip() else nb.title
                        on_delete_confirm(nb.id, effective_title, ack)
                with cancel_col:
                    if st.button(
                        "Hủy",
                        key=f"cancel_delete_nb_{nb.id}"
                    ):
                        on_delete_cancel(nb.id)
            else:
                if st.button(NOTEBOOK_DELETE_ACTION, key=f"delete_nb_active_{nb.id}"):
                    on_delete_request(nb.id)
        st.write("---")


def render_archived_notebook_card(
    nb: DocumentNotebook,
    conv_count: int,
    on_restore: Callable[[str], None],
    on_delete_request: Callable[[str], None] = None,
    on_delete_confirm: Callable[[str, str, bool], None] = None,
    on_delete_cancel: Callable[[str], None] = None,
    delete_pending: bool = False,
):
    with st.container():
        st.markdown(f"### 📦 {nb.title}")
        st.write(nb.description or "Không có mô tả.")
        st.write(f"Số cuộc trò chuyện: `{conv_count}`")
        st.caption(NOTEBOOK_NO_DELETE_COPY)
        if st.button(NOTEBOOK_RESTORE_ACTION, key=f"restore_nb_{nb.id}"):
            on_restore(nb.id)

        # Danger zone
        st.write("---")
        st.markdown("**Vùng nguy hiểm**")
        if on_delete_request is not None:
            if delete_pending:
                st.error(NOTEBOOK_DELETE_WARNING)
                confirm_title = st.text_input(
                    NOTEBOOK_DELETE_PROMPT,
                    placeholder=f"Để trống hoặc nhập: {nb.title}",
                    key=f"delete_confirm_title_archive_{nb.id}"
                )
                ack = st.checkbox(
                    NOTEBOOK_DELETE_ACK,
                    key=f"delete_confirm_ack_archive_{nb.id}"
                )
                title_ok = (
                    not confirm_title
                    or confirm_title.strip().lower() == nb.title.strip().lower()
                )
                btn_disabled = not (title_ok and ack)

                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button(
                        NOTEBOOK_DELETE_CONFIRM,
                        key=f"confirm_delete_nb_archive_{nb.id}",
                        disabled=btn_disabled
                    ):
                        effective_title = confirm_title.strip() if confirm_title.strip() else nb.title
                        on_delete_confirm(nb.id, effective_title, ack)
                with cancel_col:
                    if st.button(
                        "Hủy",
                        key=f"cancel_delete_nb_archive_{nb.id}"
                    ):
                        on_delete_cancel(nb.id)
            else:
                if st.button(NOTEBOOK_DELETE_ACTION, key=f"delete_nb_archive_{nb.id}"):
                    on_delete_request(nb.id)
        st.write("---")

def render_chat_bubble(msg: ChatMessage, is_latest: bool = False):
    if msg.role == "user":
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif msg.role == "assistant":
        with st.chat_message("assistant"):
            if is_latest:
                st.markdown(
                    '<div style="display:inline-flex; align-items:center; gap:6px; background:rgba(14,165,233,0.15); border:1px solid rgba(14,165,233,0.4); color:#38bdf8; font-size:12px; font-weight:600; padding:2px 10px; border-radius:9999px; margin-bottom:10px;">✨ Câu trả lời mới nhất</div>',
                    unsafe_allow_html=True,
                )
            st.markdown(msg.content)
    else:
        st.info(msg.content)


def render_right_result_panel(
    answer_text: str,
    proven_sources: List[str],
    to_check_items: List[str],
    next_actions: List[str],
    on_save_case: Callable[[], None],
    on_explain: Callable[[], None]
):
    labels = get_vietnamese_labels()
    st.subheader(f"💡 {labels['main_answer']}")
    if proven_sources:
        if len(proven_sources) <= 6:
            st.markdown("\n".join(f"- {src}" for src in proven_sources))
        else:
            items_html = "".join(f"<li style='margin-bottom:4px;'>{src}</li>" for src in proven_sources)
            st.markdown(
                f"<div style='max-height: 280px; overflow-y: auto; padding: 8px 12px; background: rgba(255,255,255,0.03); border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); font-size: 13.5px; line-height: 1.5;'>"
                f"<ul style='margin: 0; padding-left: 1.2rem;'>"
                f"{items_html}"
                f"</ul></div>",
                unsafe_allow_html=True,
            )
    else:
        st.write("Chưa có nguồn nào đang bật cho cuộc trò chuyện này.")


    with st.expander("⚙️ Tùy chọn", expanded=False):
        st.subheader(f"⚠️ {labels['to_check']}")
        if to_check_items:
            for item in to_check_items:
                st.warning(item)
        else:
            st.write("Chưa có mục cần kiểm tra.")

        st.subheader(f"🚀 {labels['next_actions']}")
        if next_actions:
            for act in next_actions:
                st.write(f"- {act}")
        else:
            st.write("Chưa có việc cần làm tiếp.")

        st.write("---")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(labels["save_to_case"], use_container_width=True):
                on_save_case()
        with col2:
            if st.button(labels["explain_conclusion"], use_container_width=True):
                on_explain()

def render_source_status(status: str) -> str:
    if status == "ready":
        return "Sẵn sàng"
    if status == "preview_only":
        return "Chỉ xem trước"
    if status == "failed":
        return "Lỗi"
    # Do not display enum/internal ID/scopes or technical ID:
    if status in ("notebook", "temporary", "conversation_only", "added_to_notebook"):
        return ""
    if status.startswith("SRC-") or status.startswith("CONV-") or status.startswith("SEL-"):
        return ""
    return ""

def __safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        try:
            st.experimental_rerun()
        except AttributeError:
            pass

def _format_prep_status(prep_status: str, extraction_status: str = "") -> str:
    if extraction_status in ("failed", "unsupported_no_local_ocr", "dependency_missing"):
        return "Lỗi đọc file"
    if prep_status in ("processing", "pending", "not_prepared"):
        return "Đang chuẩn bị..."
    if prep_status == "ready":
        return "Sẵn sàng"
    if prep_status == "failed":
        return "Chuẩn bị thất bại"
    return ""

def get_source_icon(title: str, source_type: str = "") -> str:
    title_lower = (title or "").lower()
    type_lower = (source_type or "").lower()
    if any(ext in title_lower for ext in [".xlsx", ".xls", ".csv"]) or "excel" in type_lower or "csv" in type_lower:
        return "📊"
    if ".pdf" in title_lower or "pdf" in type_lower:
        return "📑"
    if any(ext in title_lower for ext in [".docx", ".doc", ".pptx"]) or "doc" in type_lower:
        return "📘"
    if any(ext in title_lower for ext in [".txt", ".md", ".json", ".yaml", ".py"]) or "text" in type_lower:
        return "📝"
    return "📄"


def render_source_library(
    notebook_sources: List[Any],
    temp_sources: List[Any],
    selections_map: Dict[tuple, bool],
    conversation_id: str,
    on_toggle_source: Callable[[str, str, bool], None],
    on_promote_temporary: Callable[[str], None],
    on_privacy_save: Callable[[str, str, str], None],
    on_delete_source: Callable[[str, str], None] = lambda *a: None,
    widget_state: Optional[Dict[str, Any]] = None,
    preparation_status_map: Optional[Dict[str, str]] = None,
    on_retry_preparation: Optional[Callable[[str, str], None]] = None,
):
    st.subheader("📚 Thư viện nguồn")

    nb_count = len(notebook_sources)
    tmp_count = len(temp_sources)
    total_sources = nb_count + tmp_count
    enabled_count = sum(1 for val in selections_map.values() if val)

    st.caption(f"📁 **Trong sổ:** {nb_count} tài liệu · ⏱️ **Tạm thời:** {tmp_count}")
    st.write(f"Đang bật {enabled_count} nguồn cho câu hỏi.")

    all_items = []
    for s in notebook_sources:
        all_items.append({
            "scope": "notebook",
            "source": s,
            "enabled": selections_map.get(("notebook", s.id), False)
        })
    for s in temp_sources:
        all_items.append({
            "scope": "temporary",
            "source": s,
            "enabled": selections_map.get(("temporary", s.id), False)
        })

    if not all_items:
        st.write("Chưa có nguồn tài liệu.")
        return

    col_all, col_none = st.columns(2)
    with col_all:
        if st.button("🔘 Bật tất cả", key=f"wsc_select_all_{conversation_id}", use_container_width=True):
            for item in all_items:
                on_toggle_source(item["scope"], item["source"].id, True)
    with col_none:
        if st.button("⚪ Tắt tất cả", key=f"wsc_deselect_all_{conversation_id}", use_container_width=True):
            for item in all_items:
                on_toggle_source(item["scope"], item["source"].id, False)

    prep_map = preparation_status_map or {}

    for item in all_items:
        s = item["source"]
        scope = item["scope"]
        is_enabled = item["enabled"]

        icon = get_source_icon(getattr(s, "title", ""), getattr(s, "source_type", ""))
        st.markdown(f"{icon} **{s.title}**")

        scope_str = "Trong sổ" if scope == "notebook" else "Tạm trong cuộc trò chuyện"
        status_str = "Đã bật" if is_enabled else "Đã tắt"

        prep_st = prep_map.get(f"{scope}:{s.id}", "ready")
        ext_st = getattr(s, "extraction_status", "") or getattr(s, "status", "")
        prep_label = _format_prep_status(prep_st, ext_st)

        status_line = f"{scope_str} | {status_str}"
        if prep_label:
            status_line += f" | {prep_label}"
        st.caption(status_line)

        if prep_st == "failed" and on_retry_preparation is not None:
            if st.button("Thử chuẩn bị lại", key=f"wsc_retry_prepare_{scope}_{conversation_id}_{s.id}"):
                on_retry_preparation(scope, s.id)

        widget_key = f"wsc_toggle_{scope}_{conversation_id}_{s.id}"
        st.checkbox(
            "Bật nguồn này cho cuộc trò chuyện",
            value=is_enabled,
            key=widget_key,
            on_change=lambda sc=scope, sid=s.id, k=widget_key, default_val=is_enabled: on_toggle_source(sc, sid, st.session_state.get(k, default_val))
        )

        with st.expander("⚙️ Tùy chọn nguồn", expanded=False):
            privacy_label = getattr(s, "privacy_label", "")
            if not privacy_label_is_sendable(privacy_label):
                st.warning(PRIVACY_BLOCKED_STATUS)

            st.markdown("**Nội dung đọc được:**")
            if getattr(s, "content_preview", None):
                st.write(s.content_preview)
            else:
                st.write("Chưa có nội dung.")

            st.markdown("---")
            privacy_key = f"wsc_privacy_{scope}_{conversation_id}_{s.id}"
            owner_choice = render_privacy_choice(privacy_key, privacy_label)
            if st.button(PRIVACY_SAVE_BUTTON, key=f"wsc_save_privacy_{scope}_{conversation_id}_{s.id}"):
                on_privacy_save(scope, s.id, owner_choice)

            if scope == "temporary":
                is_promoted = getattr(s, "long_term_saved", False) or getattr(s, "status", "") == "added_to_notebook"
                if is_promoted:
                    st.caption("Đã thêm vào sổ tài liệu")
                else:
                    if st.button("Thêm vào sổ tài liệu", key=f"wsc_promote_{conversation_id}_{s.id}"):
                        on_promote_temporary(s.id)

            st.markdown("---")
            confirm_key = f"wsc_delete_confirm_{scope}_{s.id}"
            if st.session_state.get(confirm_key, False):
                st.warning("Xác nhận xóa nguồn này?")
                dcol1, dcol2 = st.columns(2)
                with dcol1:
                    if st.button("Hủy", key=f"wsc_del_cancel_{scope}_{s.id}"):
                        st.session_state[confirm_key] = False
                        __safe_rerun()
                with dcol2:
                    if st.button("Xác nhận xóa", key=f"wsc_del_exec_{scope}_{s.id}"):
                        st.session_state[confirm_key] = False
                        on_delete_source(scope, s.id)
            else:
                if st.button("Xóa", key=f"wsc_del_req_{scope}_{s.id}"):
                    st.session_state[confirm_key] = True
                    __safe_rerun()

        st.markdown("<hr style='margin: 4px 0; border: 0.5px solid rgba(255,255,255,0.08);'/>", unsafe_allow_html=True)


# --- Phase 2H: New render helpers ---

def render_ai_source_context_summary(enabled_count: int):
    """Compact AI source context summary shown near the question area."""
    if enabled_count > 0:
        st.info(
            f"Có {enabled_count} nguồn đang bật. Khi bạn hỏi, hệ thống chỉ chuẩn bị "
            "và tìm trong các tài liệu liên quan đến câu hỏi."
        )
    else:
        st.warning("Chưa có nguồn nào đang bật.")


def render_ai_answer_header(source_count: int, source_titles: List[str]):
    """Renders 'AI đã trả lời' badge and source summary above the answer."""
    st.success("✅ **AI đã trả lời**")
    st.write(f"Nguồn gửi cùng câu hỏi: {source_count}")
    if source_titles:
        with st.expander("Xem nguồn gửi cùng câu hỏi", expanded=False):
            for title in source_titles:
                st.write(f"- {title}")
    st.caption("Đây là câu trả lời do AI tạo. Hãy kiểm tra lại trước khi dùng.")


def render_insufficient_context(reason: str = "no_sources"):
    """Renders 'Thiếu ngữ cảnh' badge with appropriate message."""
    st.error("⚠️ **Thiếu ngữ cảnh**")
    st.write("Chưa có nguồn phù hợp để trả lời.")


def render_privacy_block_message():
    """Renders friendly privacy block message."""
    st.error(PRIVACY_AI_HARD_BLOCK_COPY)


def render_source_changed_message():
    """Renders source-set-changed warning."""
    st.warning("Nguồn đang bật đã thay đổi. Hãy xem lại danh sách rồi bấm Hỏi AI lần nữa.")
