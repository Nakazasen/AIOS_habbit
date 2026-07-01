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
        "main_answer": "Bản xem trước câu trả lời",
        "proven_sources": "Nguồn đang bật cho cuộc trò chuyện",
        "to_check": "Điều owner cần kiểm tra",
        "next_actions": "Việc nên làm tiếp",
        "save_to_case": "Lưu vào hồ sơ",
        "explain_conclusion": "Xem đoạn xem trước sẽ dùng ở bước sau"
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
    if answer_text:
        st.info(answer_text)
    else:
        st.write("Chưa có câu trả lời.")

    st.subheader(f"📎 {labels['proven_sources']}")
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
    st.subheader("Nguồn đang dùng")
    total = enabled_notebook_count + enabled_temp_count
    if total == 0:
        st.write("Chưa có nguồn nào đang dùng.")
    else:
        st.write(f"Tổng số nguồn đang bật: {total}")
        st.write(f"- Số nguồn trong sổ đang bật: {enabled_notebook_count}")
        st.write(f"- Số nguồn tạm đang bật: {enabled_temp_count}")
    st.info("Nguồn đang dùng là những nguồn bạn đã bật cho cuộc trò chuyện này.")

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
            st.caption(f"Preview: {s.content_preview}")

        status_lbl = render_source_status(s.extraction_status)
        if status_lbl:
            st.write(f"Trạng thái: {status_lbl}")

        widget_key = f"wsc_source_notebook_{conversation_id}_{s.id}"
        is_enabled = selections.get(s.id, False)

        st.checkbox(
            "Dùng trong cuộc trò chuyện này",
            value=is_enabled,
            key=widget_key,
            on_change=lambda s_id=s.id, key=widget_key: on_toggle(s_id, st.session_state[key])
        )
        st.write(f"Trạng thái hoạt động: {'Dùng trong cuộc trò chuyện này' if is_enabled else 'Tạm không dùng'}")
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
            st.caption(f"Preview: {s.content_preview}")

        status_lbl = render_source_status(s.status)
        if status_lbl:
            st.write(f"Trạng thái: {status_lbl}")

        widget_key = f"wsc_source_temporary_{conversation_id}_{s.id}"
        is_enabled = selections.get(s.id, False)

        st.checkbox(
            "Dùng trong cuộc trò chuyện này",
            value=is_enabled,
            key=widget_key,
            on_change=lambda s_id=s.id, key=widget_key: on_toggle(s_id, st.session_state[key])
        )
        st.write(f"Trạng thái hoạt động: {'Dùng trong cuộc trò chuyện này' if is_enabled else 'Tạm không dùng'}")

        is_promoted = s.long_term_saved or s.status == "added_to_notebook"
        if is_promoted:
            st.write("Đã thêm vào sổ tài liệu")
        else:
            promote_key = f"wsc_promote_temporary_{conversation_id}_{s.id}"
            if st.button("Thêm vào sổ tài liệu", key=promote_key):
                on_promote(s.id)
        st.write("---")
