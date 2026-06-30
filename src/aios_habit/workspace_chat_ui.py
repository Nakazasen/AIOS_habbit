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
        "main_answer": "Trả lời chính",
        "proven_sources": "Nguồn chứng minh",
        "to_check": "Ý cần kiểm lại",
        "next_actions": "Việc nên làm tiếp",
        "save_to_case": "Lưu vào hồ sơ",
        "explain_conclusion": "Xem vì sao AIOS kết luận như vậy"
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
        st.write("Chưa ghi nhận nguồn chứng minh.")
        
    st.subheader(f"⚠️ {labels['to_check']}")
    if to_check_items:
        for item in to_check_items:
            st.warning(item)
    else:
        st.write("Mọi thông tin đều đã được đối chiếu.")
        
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
