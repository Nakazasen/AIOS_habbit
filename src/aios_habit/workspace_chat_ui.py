import streamlit as st
from typing import List, Dict, Any, Callable
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
        "ai_action": "Hỏi AI với nguồn đang bật",
        "source_check": "Kiểm tra nguồn trước",
        "ai_not_answered": "AI chưa trả lời",
        "ai_answered": "AI đã trả lời",
        "insufficient_context": "Thiếu ngữ cảnh",
        "sources_sent": "Nguồn gửi cùng câu hỏi",
        "quick_paste": "Dán nhanh nhiều nguồn",
        "quick_paste_add": "Thêm làm 1 nguồn",
        "question_placeholder": "Nhập câu hỏi bạn muốn AI hỗ trợ...",
    }

def render_notebook_header():
    st.title("📚 Sổ tài liệu của tôi")
    st.write("Quản lý các tài liệu, hồ sơ và thực hiện hỏi đáp riêng biệt theo từng sổ công việc.")

def render_notebook_card(nb: DocumentNotebook, conv_count: int, on_open: Callable[[str], None]):
    labels = get_vietnamese_labels()
    with st.container():
        st.markdown(f"### 📂 {nb.title}")
        st.write(nb.description or "Không có mô tả.")
        st.write(f"Số cuộc trò chuyện: `{conv_count}`")
        if st.button(f"{labels['open_notebook']} {nb.title}", key=f"open_nb_{nb.id}"):
            on_open(nb.id)
        st.write("---")

def render_chat_bubble(msg: ChatMessage):
    if msg.role == "user":
        with st.chat_message("user"):
            st.write(msg.content)
    elif msg.role == "assistant":
        with st.chat_message("assistant"):
            st.write(msg.content)
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
        for src in proven_sources:
            st.write(f"- {src}")
    else:
        st.write("Chưa có nguồn nào đang bật cho cuộc trò chuyện này.")

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

def render_source_summary(enabled_notebook_count: int, enabled_temp_count: int):
    st.subheader("Nguồn đang bật")
    total = enabled_notebook_count + enabled_temp_count
    if total == 0:
        st.write("Chưa có nguồn nào đang bật.")
    else:
        st.write(f"Tổng số nguồn đang bật: {total}")
        st.write(f"- Số nguồn trong sổ đang bật: {enabled_notebook_count}")
        st.write(f"- Số nguồn tạm đang bật: {enabled_temp_count}")
    st.info("Nguồn đang bật là những nguồn bạn đã chọn cho câu hỏi.")

def render_notebook_source_list(
    sources: List[Any],
    selections: Dict[str, bool],
    on_toggle: Callable[[str, bool], None],
    conversation_id: str
):
    st.subheader("Nguồn trong sổ")
    st.info("Nguồn trong sổ được giữ lại để dùng trong nhiều cuộc trò chuyện.")

    if not sources:
        st.write("Chưa có nguồn trong sổ.")
        return

    for s in sources:
        st.markdown(f"**{s.title}**")
        if s.content_preview:
            with st.expander("Xem trước nguồn", expanded=False):
                st.caption(f"Preview: {s.content_preview}")
        elif not getattr(s, "content_text", ""):
            st.warning("Nguồn chưa có nội dung để gửi")

        privacy_label = getattr(s, "privacy_label", "")
        if privacy_label is None or privacy_label.strip().lower() not in {"machine_only", "cloud_allowed"}:
            st.error("Nguồn này chỉ được dùng trên máy")

        content = getattr(s, "content_text", "")
        if content and len(content) > 4000:
            st.warning("Nội dung có thể bị rút gọn để tránh quá dài")

        status_lbl = render_source_status(getattr(s, "extraction_status", ""))
        if status_lbl:
            st.write(f"Trạng thái: {status_lbl}")

        widget_key = f"wsc_source_notebook_{conversation_id}_{s.id}"
        is_enabled = selections.get(s.id, False)

        st.checkbox(
            "Bật nguồn này cho cuộc trò chuyện",
            value=is_enabled,
            key=widget_key,
            on_change=lambda s_id=s.id, key=widget_key: on_toggle(s_id, st.session_state[key])
        )
        st.write(f"Trạng thái hoạt động: {'Đang bật cho cuộc trò chuyện' if is_enabled else 'Đang tắt'}")
        st.write("---")

def render_temporary_source_list(
    sources: List[Any],
    selections: Dict[str, bool],
    on_toggle: Callable[[str, bool], None],
    on_promote: Callable[[str], None],
    conversation_id: str
):
    st.subheader("Nguồn tạm trong cuộc trò chuyện")
    st.info("Nguồn tạm chỉ thuộc cuộc trò chuyện hiện tại.")

    if not sources:
        st.write("Chưa có nguồn tạm trong cuộc trò chuyện này.")
        return

    for s in sources:
        st.markdown(f"**{s.title}**")
        if s.content_preview:
            with st.expander("Xem trước nguồn", expanded=False):
                st.caption(f"Preview: {s.content_preview}")
        elif not getattr(s, "content_text", ""):
            st.warning("Nguồn chưa có nội dung để gửi")

        privacy_label = getattr(s, "privacy_label", "")
        if privacy_label is None or privacy_label.strip().lower() not in {"machine_only", "cloud_allowed"}:
            st.error("Nguồn này chỉ được dùng trên máy")

        content = getattr(s, "content_text", "")
        if content and len(content) > 4000:
            st.warning("Nội dung có thể bị rút gọn để tránh quá dài")

        status_lbl = render_source_status(getattr(s, "status", ""))
        if status_lbl:
            st.write(f"Trạng thái: {status_lbl}")

        widget_key = f"wsc_source_temporary_{conversation_id}_{s.id}"
        is_enabled = selections.get(s.id, False)

        st.checkbox(
            "Bật nguồn này cho cuộc trò chuyện",
            value=is_enabled,
            key=widget_key,
            on_change=lambda s_id=s.id, key=widget_key: on_toggle(s_id, st.session_state[key])
        )
        st.write(f"Trạng thái hoạt động: {'Đang bật cho cuộc trò chuyện' if is_enabled else 'Đang tắt'}")

        is_promoted = s.long_term_saved or s.status == "added_to_notebook"
        if is_promoted:
            st.write("Đã thêm vào sổ tài liệu")
        else:
            promote_key = f"wsc_promote_temporary_{conversation_id}_{s.id}"
            if st.button("Thêm vào sổ tài liệu", key=promote_key):
                on_promote(s.id)
        st.write("---")


# --- Phase 2H: New render helpers ---

def render_ai_source_context_summary(enabled_count: int):
    """Compact AI source context summary shown near the question area."""
    if enabled_count > 0:
        st.info(f"AI sẽ dùng {enabled_count} nguồn đang bật.")
    else:
        st.warning("Chưa có nguồn nào đang bật.")


def render_source_check_panel(source_titles: List[str], source_previews: List[str]):
    """Renders local source check panel OUTSIDE chat history.
    Badge: AI chưa trả lời. Never saved as ChatMessage(role='assistant')."""
    st.warning("🔍 **AI chưa trả lời**")
    st.caption("Đây chỉ là danh sách nguồn và đoạn xem trước sẽ dùng nếu bạn hỏi AI.")
    if not source_titles:
        st.write("Chưa có nguồn để kiểm tra. Hãy bật nguồn hoặc dán thêm dữ liệu.")
        return
    st.write(f"Nguồn đang bật: {len(source_titles)}")
    for i, title in enumerate(source_titles):
        preview = source_previews[i] if i < len(source_previews) else ""
        st.markdown(f"**{title}**")
        if preview:
            st.caption(preview)


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
    if reason == "no_sources":
        st.write("Hãy bật nguồn hoặc dán thêm dữ liệu trước khi hỏi AI.")
    elif reason == "empty_content":
        st.write("Nguồn đang bật chưa có nội dung để hỏi AI.")
    else:
        st.write("Hãy bật nguồn hoặc dán thêm dữ liệu trước khi hỏi AI.")


def render_privacy_block_message():
    """Renders friendly privacy block message."""
    st.error("Có nguồn không được gửi AI. Hãy tắt nguồn đó rồi thử lại.")


def render_source_changed_message():
    """Renders source-set-changed warning."""
    st.warning("Nguồn đang bật đã thay đổi. Hãy xem lại danh sách rồi bấm Hỏi AI lần nữa.")
