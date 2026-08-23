import streamlit as st
import time
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
    if status == "unavailable":
        return "BGE-M3 chưa sẵn sàng"
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
    if prep_status == "unavailable":
        return "BGE-M3 chưa sẵn sàng"
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


def render_source_library_summary(notebook_count: int, temporary_count: int, enabled_count: int) -> None:
    """Keep the sidebar informative without hiding source-management actions in it."""
    st.subheader("📚 Tóm tắt tài liệu")
    st.caption(f"Trong sổ: {notebook_count} · Chỉ chat này: {temporary_count}")
    st.caption(f"Đang bật cho câu hỏi: {enabled_count}")
    st.info("Quản lý, thay thế hoặc xóa tài liệu ở khu vực **Tài liệu đang dùng** trong màn chat.")


def render_preparation_progress_bar(
    summary: Optional[Dict[str, Any]],
    on_retry_all_failed: Optional[Callable[[], None]] = None,
) -> None:
    """Renders compact single-line BGE-M3 preparation progress banner."""
    if not summary or summary.get("total", 0) <= 0:
        return
    text = summary.get("summary_text", "")
    if not text:
        return
    failed = summary.get("failed", 0)
    processing = summary.get("processing", 0)
    pending = summary.get("pending", 0)

    if failed > 0:
        col_txt, col_btn = st.columns([3, 1])
        with col_txt:
            st.warning(f"📊 **Tiến độ BGE-M3:** {text}")
        with col_btn:
            if on_retry_all_failed is not None:
                if st.button("🔄 Thử lại các lỗi", key="wsc_retry_all_failed_sources", use_container_width=True):
                    on_retry_all_failed()
    elif processing > 0 or pending > 0:
        st.info(f"📊 **Tiến độ BGE-M3:** {text}")
    else:
        st.success(f"📊 **Tiến độ BGE-M3:** {text}")


def render_document_manager(
    notebook_sources: List[Any],
    temporary_sources: List[Any],
    selections_map: Dict[tuple, bool],
    conversation_id: str,
    on_toggle_source: Callable[[str, str, bool], None],
    on_delete_source: Callable[[str, str], None],
    on_delete_sources: Callable[[str, List[str]], None],
    on_promote_temporary: Callable[[str], None],
    on_privacy_save: Callable[[str, str, str], None],
    undo_expires_at: float = 0,
    on_undo_delete: Optional[Callable[[], None]] = None,
    preparation_summary: Optional[Dict[str, Any]] = None,
    on_retry_source: Optional[Callable[[str, str], None]] = None,
    on_retry_all_failed: Optional[Callable[[], None]] = None,
) -> None:
    """Render the owner-facing document manager in the chat column."""
    st.subheader("📚 Tài liệu đang dùng")
    st.caption("Bật/tắt nguồn cho câu hỏi, xem nội dung, thay thế hoặc xóa tài liệu ở đây.")
    st.info("Muốn thay thế một tài liệu: mở **➕ Thêm nguồn** phía trên, tải bản cùng tên và chọn **Thay thế bản cũ**. Bản cũ chỉ bị xóa khi bản mới đọc thành công.")

    if preparation_summary:
        render_preparation_progress_bar(preparation_summary, on_retry_all_failed=on_retry_all_failed)

    def render_undo_control() -> None:
        seconds_remaining = max(0, int(undo_expires_at - time.time()))
        if seconds_remaining <= 0 or on_undo_delete is None:
            return
        undo_col, _ = st.columns(2)
        with undo_col:
            st.warning(f"Đã xóa tài liệu. Bạn có thể khôi phục trong {seconds_remaining} giây.")
            if st.button("↩️ Khôi phục", key=f"wsc_source_undo_{conversation_id}", use_container_width=True):
                on_undo_delete()

    if undo_expires_at > time.time() and on_undo_delete is not None:
        if hasattr(st, "fragment"):
            st.fragment(run_every=1.0)(render_undo_control)()
        else:
            render_undo_control()

    def render_group(scope: str, heading: str, explanation: str, sources: List[Any]) -> None:
        st.markdown(f"#### {heading}")
        st.caption(explanation)
        if not sources:
            st.info("Chưa có tài liệu trong nhóm này.")
            return

        group_label = "tài liệu của sổ" if scope == "notebook" else "nguồn tạm của cuộc trò chuyện"
        enable_col, disable_col = st.columns(2)
        with enable_col:
            if st.button(
                f"Bật toàn bộ {len(sources)} {group_label}",
                key=f"wsc_document_enable_all_{scope}_{conversation_id}",
                use_container_width=True,
            ):
                for source in sources:
                    on_toggle_source(scope, source.id, True)
                    st.session_state[f"wsc_document_toggle_{scope}_{conversation_id}_{source.id}"] = True
                st.session_state.wsc_action_message = f"Đã bật {len(sources)} {group_label}."
                __safe_rerun()
        with disable_col:
            if st.button(
                f"Tắt toàn bộ {len(sources)} {group_label}",
                key=f"wsc_document_disable_all_{scope}_{conversation_id}",
                use_container_width=True,
            ):
                for source in sources:
                    on_toggle_source(scope, source.id, False)
                    st.session_state[f"wsc_document_toggle_{scope}_{conversation_id}_{source.id}"] = False
                st.session_state.wsc_action_message = f"Đã tắt {len(sources)} {group_label}."
                __safe_rerun()

        confirm_key = f"wsc_bulk_delete_confirm_{scope}_{conversation_id}"
        if st.session_state.get(confirm_key, False):
            st.warning(
                f"Xác nhận xóa {len(sources)} tài liệu? "
                + ("Thao tác này ảnh hưởng mọi cuộc trò chuyện trong sổ." if scope == "notebook" else "Chỉ cuộc trò chuyện hiện tại bị ảnh hưởng.")
            )
            cancel_col, execute_col = st.columns(2)
            with cancel_col:
                if st.button("Hủy", key=f"wsc_bulk_delete_cancel_{scope}_{conversation_id}"):
                    st.session_state[confirm_key] = False
                    __safe_rerun()
            with execute_col:
                if st.button("Xác nhận xóa", key=f"wsc_bulk_delete_execute_{scope}_{conversation_id}", type="primary"):
                    st.session_state[confirm_key] = False
                    on_delete_sources(scope, [source.id for source in sources])
        else:
            label = "🗑️ Xóa tài liệu của cả sổ" if scope == "notebook" else "🗑️ Xóa nguồn tạm của cuộc trò chuyện"
            if st.button(label, key=f"wsc_bulk_delete_request_{scope}_{conversation_id}", use_container_width=True):
                st.session_state[confirm_key] = True
                __safe_rerun()

        for source in sources:
            enabled = selections_map.get((scope, source.id), False)
            icon = get_source_icon(getattr(source, "title", ""), getattr(source, "source_type", ""))
            status_map = preparation_summary.get("statuses", {}) if preparation_summary else {}
            error_map = preparation_summary.get("errors", {}) if preparation_summary else {}
            item_status = status_map.get(f"{scope}:{source.id}", "ready")
            item_error = error_map.get(f"{scope}:{source.id}", "")

            left_col, action_col = st.columns([3, 2])
            with left_col:
                st.markdown(f"{icon} **{source.title}**")
                state = "Đang bật" if enabled else "Đang tắt"
                location = "Trong sổ tài liệu" if scope == "notebook" else "Chỉ trong cuộc trò chuyện này"
                st.caption(f"{location} · {state}")

                # BGE-M3 readiness status badge
                if item_status == "ready":
                    st.caption("🟢 **BGE-M3:** Sẵn sàng")
                elif item_status == "processing":
                    st.caption("⏳ **BGE-M3:** Đang đọc nội dung…")
                elif item_status == "pending":
                    st.caption("⏱️ **BGE-M3:** Đang chờ trong hàng đợi")
                elif item_status == "failed":
                    err_info = f" ({item_error})" if item_error else ""
                    st.caption(f"🔴 **BGE-M3:** Lỗi đọc tài liệu{err_info}")
                elif item_status == "unavailable":
                    st.caption("⚪ **BGE-M3:** Chưa khả dụng")

            with action_col:
                if item_status == "failed" and on_retry_source is not None:
                    if st.button("🔄 Thử lại", key=f"wsc_retry_src_{scope}_{conversation_id}_{source.id}", use_container_width=True):
                        on_retry_source(scope, source.id)

                individual_confirm_key = f"wsc_document_delete_confirm_{scope}_{source.id}"
                if st.session_state.get(individual_confirm_key, False):
                    if st.button("Xác nhận xóa", key=f"wsc_document_delete_execute_{scope}_{source.id}", type="primary", use_container_width=True):
                        st.session_state[individual_confirm_key] = False
                        on_delete_source(scope, source.id)
                    if st.button("Hủy", key=f"wsc_document_delete_cancel_{scope}_{source.id}", use_container_width=True):
                        st.session_state[individual_confirm_key] = False
                        __safe_rerun()
                elif st.button("🗑️ Xóa", key=f"wsc_document_delete_request_{scope}_{source.id}", use_container_width=True):
                    st.session_state[individual_confirm_key] = True
                    __safe_rerun()

            toggle_key = f"wsc_document_toggle_{scope}_{conversation_id}_{source.id}"
            st.checkbox(
                "Dùng tài liệu này khi trả lời",
                value=enabled,
                key=toggle_key,
                on_change=lambda sc=scope, sid=source.id, key=toggle_key, default=enabled: on_toggle_source(sc, sid, st.session_state.get(key, default)),
            )
            with st.expander("Xem nội dung và tùy chọn", expanded=False):
                st.write(getattr(source, "content_preview", "") or "Chưa có nội dung xem trước.")
                choice = render_privacy_choice(f"wsc_document_privacy_{scope}_{conversation_id}_{source.id}", getattr(source, "privacy_label", ""))
                if st.button(PRIVACY_SAVE_BUTTON, key=f"wsc_document_privacy_save_{scope}_{conversation_id}_{source.id}"):
                    on_privacy_save(scope, source.id, choice)
                if scope == "temporary" and not getattr(source, "long_term_saved", False):
                    if st.button("Lưu vào Sổ tài liệu", key=f"wsc_document_promote_{conversation_id}_{source.id}"):
                        on_promote_temporary(source.id)
            st.divider()

    render_group(
        "temporary",
        "Nguồn tạm của cuộc trò chuyện này",
        "Chỉ dùng trong chat đang mở. Xóa ở đây không ảnh hưởng các chat khác hay lịch sử tin nhắn.",
        temporary_sources,
    )
    render_group(
        "notebook",
        "Tài liệu của sổ",
        "Dùng được trong mọi cuộc trò chuyện của sổ. Xóa ở đây sẽ gỡ tài liệu khỏi tất cả các chat trong sổ.",
        notebook_sources,
    )


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


def render_bridge_header_status(health: Any):
    """Renders truthful bridge status badge in the app header."""
    status = getattr(health, "status", "unavailable") if health else "unavailable"
    mode = getattr(health, "mode", "none") if health else "none"
    reason = getattr(health, "reason", "") if health else ""

    if status == "direct_ready":
        st.info("🟢 **Cầu nối sẵn sàng** (Trực tiếp)")
    elif status in ("handoff_ready", "completed"):
        st.info("🟢 **Cầu nối sẵn sàng** (Chuyển giao)")
    elif status == "handoff_pending":
        st.warning("🟡 **Đang chờ Antigravity IDE xử lý** (Chuyển giao)")
    elif status == "failed":
        sanitized = reason or "Lỗi kết nối"
        st.error(f"🔴 **Cầu nối lỗi**: {sanitized}")
    else:
        st.info("⚪ **Cầu nối chưa kết nối**")


def render_ai_answer_header(
    source_count: int,
    source_titles: List[str],
    ai_source: str = "",
    model_tool_name: str = "",
    operational_mode: str = "",
    provider_name: str = "",
):
    """Renders truthful provenance badges separating Bridge, Provider, and Model."""
    mode_vn = "Chuyển giao" if operational_mode == "handoff" else "Trực tiếp" if operational_mode == "direct" else operational_mode
    mode_suffix = f" ({mode_vn})" if mode_vn else ""

    if ai_source and ("antigravity" in str(ai_source).lower() or str(ai_source) == "Antigravity IDE"):
        bridge_label = f"Sidecar{mode_suffix}"
        provider_label = provider_name or "Gemini Web (Nặc danh)"
        st.success(f"✅ **AI đã trả lời** · 🌉 **Cầu nối:** `{bridge_label}` · 🌐 **Nhà cung cấp:** `{provider_label}`")
    elif ai_source and ("smart_router" in str(ai_source).lower() or str(ai_source) == "Smart Router"):
        st.info("✅ **AI đã trả lời** · 🌐 **Nguồn AI:** `Smart Router (Tự động)`")
    else:
        st.success("✅ **AI đã trả lời**")

    # Group source titles to avoid repetitive headers
    title_counts: dict[str, int] = {}
    if source_titles:
        for t in source_titles:
            clean_t = str(t).strip()
            if clean_t:
                title_counts[clean_t] = title_counts.get(clean_t, 0) + 1

    distinct_doc_count = len(title_counts) if title_counts else source_count
    if title_counts and source_count > distinct_doc_count:
        st.write(f"Nguồn gửi cùng câu hỏi: {distinct_doc_count} tài liệu ({source_count} đoạn trích)")
    else:
        st.write(f"Nguồn gửi cùng câu hỏi: {source_count}")

    # Truthful Model Identity
    clean_model = model_tool_name.strip() if model_tool_name else ""
    if clean_model and clean_model not in ("antigravity-brain-pro", "gemini-pro", "antigravity", "auto", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-flash-lite"):
        st.caption(f"Mô hình: `{clean_model}`")
    elif operational_mode in ("direct", "handoff"):
        st.caption("Mô hình: `Gemini Web Stream (Chưa xác minh định danh)`")

    if title_counts:
        with st.expander("Xem nguồn gửi cùng câu hỏi", expanded=False):
            for title, count in title_counts.items():
                if count > 1:
                    st.write(f"- {title} · *({count} đoạn trích)*")
                else:
                    st.write(f"- {title}")
    st.caption("Đây là câu trả lời do AI tạo. Hãy kiểm tra lại trước khi dùng.")


def render_grouped_evidence_items(evidence_items: List[Dict[str, Any]], conversation_id: str) -> None:
    """Group multiple retrieved excerpts by source title/id to avoid redundant headers."""
    if not evidence_items:
        return
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in evidence_items:
        title = item.get("title", "Tài liệu không tên")
        grouped.setdefault(title, []).append(item)

    with st.expander(f"🔍 Chi tiết các đoạn trích sử dụng ({len(evidence_items)} đoạn từ {len(grouped)} tài liệu)"):
        for title, items in grouped.items():
            count_label = f"{len(items)} đoạn trích" if len(items) > 1 else "1 đoạn trích"
            st.markdown(f"📄 **{title}** · *{count_label}*")
            for idx, item in enumerate(items, 1):
                loc = item.get("location_info", "")
                loc_str = f" ({loc})" if loc else ""
                snippet_text = item.get("text", item.get("snippet", ""))
                st.caption(f"Đoạn {idx}{loc_str}:")
                st.text_area(
                    f"Đoạn {idx} từ {title}",
                    value=snippet_text,
                    height=80,
                    disabled=True,
                    key=f"wsc_evd_{conversation_id}_{item.get('evidence_id', idx)}_{idx}",
                    label_visibility="collapsed",
                )


def render_handoff_pending_banner(
    request_id: str,
    outbox_dir: str = "",
    inbox_path: str = "",
    privacy_mode: str = "",
    on_check_inbox: Optional[Callable[[str], None]] = None,
    on_cancel_request: Optional[Callable[[str], None]] = None,
):
    """Renders active pending banner when waiting for Antigravity IDE outbox/inbox processing."""
    with st.container():
        st.warning(f"⏳ **Đang chờ Antigravity IDE xử lý** (Mã yêu cầu: `{request_id}`)")
        guidance_text = "Gói yêu cầu đã được tạo và gửi vào hàng đợi xử lý.\n\n"
        if outbox_dir:
            guidance_text += f"- **Thư mục gửi đi (Outbox)**: `{outbox_dir}`\n"
        if inbox_path:
            guidance_text += f"- **Đường dẫn nhận kết quả (Inbox)**: `{inbox_path}`\n"
        guidance_text += "Vui lòng mở **Antigravity IDE**, xử lý yêu cầu và lưu kết quả phản hồi."
        st.markdown(guidance_text)

        if privacy_mode == "local_only":
            st.caption("🔒 **Bảo mật**: Dữ liệu chỉ dùng trên máy không được gửi ra ngoài.")

        if on_check_inbox is not None:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Kiểm tra kết quả phản hồi", key=f"wsc_check_inbox_{request_id}", use_container_width=True):
                    on_check_inbox(request_id)
            with col2:
                if on_cancel_request is not None and st.button("❌ Hủy yêu cầu", key=f"wsc_cancel_handoff_{request_id}", use_container_width=True):
                    on_cancel_request(request_id)


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
