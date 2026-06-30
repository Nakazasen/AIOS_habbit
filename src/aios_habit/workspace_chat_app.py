import streamlit as st
import uuid
from datetime import datetime
from aios_habit.workspace_chat_store import (
    init_chat_store,
    load_notebooks,
    load_conversations,
    load_conversation,
    save_conversation,
    rename_conversation,
    load_messages,
    save_message,
    load_temporary_sources,
    save_temporary_source
)
from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
    ChatMessage,
    TemporaryConversationSource
)
from aios_habit.workspace_chat_ui import (
    get_vietnamese_labels,
    render_notebook_header,
    render_notebook_card,
    render_chat_bubble,
    render_right_result_panel
)

# Tự động khởi tạo kho lưu trữ
init_chat_store()

# Khởi tạo trạng thái phiên làm việc riêng (không dùng chung key với Case Cockpit cũ)
if "wsc_active_notebook_id" not in st.session_state:
    st.session_state.wsc_active_notebook_id = None
if "wsc_active_conversation_id" not in st.session_state:
    st.session_state.wsc_active_conversation_id = None
if "wsc_show_save_placeholder" not in st.session_state:
    st.session_state.wsc_show_save_placeholder = False
if "wsc_show_explain_placeholder" not in st.session_state:
    st.session_state.wsc_show_explain_placeholder = False

def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        try:
            st.experimental_rerun()
        except AttributeError:
            pass

def open_notebook_callback(notebook_id: str):
    st.session_state.wsc_active_notebook_id = notebook_id
    st.session_state.wsc_active_conversation_id = None
    st.session_state.wsc_show_save_placeholder = False
    st.session_state.wsc_show_explain_placeholder = False
    safe_rerun()

active_nb_id = st.session_state.wsc_active_notebook_id

if active_nb_id is None:
    # MÀN HÌNH 1: Sổ tài liệu của tôi
    render_notebook_header()
    notebooks = load_notebooks()
    for nb in notebooks:
        conv_count = len(load_conversations(nb.id))
        render_notebook_card(nb, conv_count, open_notebook_callback)
else:
    # MÀN HÌNH 2: Chat trong sổ
    notebook = next((nb for nb in load_notebooks() if nb.id == active_nb_id), None)
    if not notebook:
        st.session_state.wsc_active_notebook_id = None
        safe_rerun()
        
    labels = get_vietnamese_labels()
    
    # Thanh điều hướng bên trái (Sidebar)
    st.sidebar.markdown(f"## 📂 {notebook.title}")
    if st.sidebar.button("⬅️ Quay lại danh sách sổ", key="back_to_nbs"):
        st.session_state.wsc_active_notebook_id = None
        st.session_state.wsc_active_conversation_id = None
        safe_rerun()
        
    st.sidebar.write("---")
    st.sidebar.subheader(labels["conversations"])
    
    # Danh sách các cuộc trò chuyện
    conversations = load_conversations(active_nb_id)
    
    if st.sidebar.button(labels["create_conversation"], key="btn_create_conv"):
        new_conv = WorkspaceConversation(
            id=f"CONV-{uuid.uuid4().hex[:8].upper()}",
            notebook_id=active_nb_id,
            title=f"Cuộc trò chuyện mới {datetime.now().strftime('%H:%M:%S')}"
        )
        save_conversation(new_conv)
        st.session_state.wsc_active_conversation_id = new_conv.id
        safe_rerun()
        
    active_conv_id = st.session_state.wsc_active_conversation_id
    if not active_conv_id and conversations:
        active_conv_id = conversations[0].id
        st.session_state.wsc_active_conversation_id = active_conv_id
        
    active_conversation = None
    if active_conv_id:
        active_conversation = load_conversation(active_conv_id)
        
    for c in conversations:
        is_active = (c.id == active_conv_id)
        btn_label = f"💬 {c.title}"
        if is_active:
            btn_label = f"👉 💬 {c.title}"
        if st.sidebar.button(btn_label, key=f"select_conv_{c.id}"):
            st.session_state.wsc_active_conversation_id = c.id
            st.session_state.wsc_show_save_placeholder = False
            st.session_state.wsc_show_explain_placeholder = False
            safe_rerun()
            
    if active_conversation:
        st.sidebar.write("---")
        with st.sidebar.form("rename_form"):
            new_title = st.text_input("Đổi tên cuộc trò chuyện", value=active_conversation.title)
            if st.form_submit_button("Cập nhật tên"):
                rename_conversation(active_conversation.id, new_title)
                safe_rerun()
                
        # Hiển thị Nguồn tạm dưới thanh bên
        st.sidebar.write("---")
        st.sidebar.subheader(labels["temp_sources"])
        temp_sources = load_temporary_sources(active_conversation.id)
        if temp_sources:
            for s in temp_sources:
                with st.sidebar.expander(f"📌 {s.title}", expanded=False):
                    st.caption(f"⚠️ {labels['not_saved_longterm']} ({labels['only_this_conversation']})")
                    st.write(f"**Xem trước:** {s.content_preview}...")
                    if len(s.content_text) > 150:
                        st.info("Nội dung dài đã được lưu trong nguồn tạm. Chỉ mở khi cần kiểm tra.")
                        st.text_area("Nội dung đầy đủ", value=s.content_text, height=150, disabled=True, key=f"full_text_{s.id}")
                    else:
                        st.write(s.content_text)
        else:
            st.sidebar.write("Chưa có nguồn tạm.")
            
    # Khu vực chính ở giữa
    st.subheader(f"💬 Đang chat trong sổ: {notebook.title}")
    
    if not active_conversation:
        st.info("Vui lòng tạo hoặc chọn một cuộc trò chuyện để bắt đầu.")
    else:
        # Hiển thị các thông báo thử nghiệm
        if st.session_state.wsc_show_save_placeholder:
            st.success("🎉 [Tính năng mô phỏng] Đã kích hoạt lưu cuộc trò chuyện này thành hồ sơ sự việc mới thành công!")
            if st.button("Đóng thông báo lưu"):
                st.session_state.wsc_show_save_placeholder = False
                safe_rerun()
        if st.session_state.wsc_show_explain_placeholder:
            st.info("🔍 [Tính năng mô phỏng] Gợi ý phân tích đối chiếu nguồn tài liệu: Các ý chính trong câu trả lời đều khớp hoàn toàn với nguồn tạm.")
            if st.button("Đóng thông báo phân tích"):
                st.session_state.wsc_show_explain_placeholder = False
                safe_rerun()

        # Chia cột: Cột chat ở giữa và cột kết quả bên phải
        col_chat, col_results = st.columns([3, 2])
        
        with col_chat:
            # Lịch sử chat
            messages = load_messages(active_conversation.id)
            chat_container = st.container()
            with chat_container:
                if not messages:
                    st.write("Hãy bắt đầu cuộc trò chuyện bằng cách đặt câu hỏi ở dưới.")
                for m in messages:
                    render_chat_bubble(m)
                    
            # Ô nhập câu hỏi của Streamlit
            user_input = st.chat_input("Nhập câu hỏi của bạn tại đây...")
            if user_input:
                user_msg = ChatMessage(
                    id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
                    conversation_id=active_conversation.id,
                    role="user",
                    content=user_input
                )
                save_message(user_msg)
                
                # Tạo câu trả lời an toàn
                temp_sources_list = load_temporary_sources(active_conversation.id)
                if temp_sources_list:
                    sources_str = ", ".join(f"'{s.title}'" for s in temp_sources_list)
                    ans_text = f"Đã ghi nhận câu hỏi liên quan đến các nguồn tạm: {sources_str}. Hệ thống sẽ sử dụng các nguồn tạm này để trả lời đầy đủ ở các phase sau."
                else:
                    ans_text = "Đã ghi nhận câu hỏi. Phase sau sẽ nối AI thật dựa trên nguồn trong sổ và nguồn tạm."
                    
                assistant_msg = ChatMessage(
                    id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
                    conversation_id=active_conversation.id,
                    role="assistant",
                    content=ans_text
                )
                save_message(assistant_msg)
                safe_rerun()
                
            # Khung dán nhật ký/email/đoạn chat dài
            st.write(" ")
            with st.expander("📝 Dán văn bản dài (log lỗi, email, hoặc đoạn chat...)"):
                with st.form("paste_log_form"):
                    paste_title = st.text_input("Tiêu đề nguồn tạm", placeholder="Ví dụ: Email lỗi Opcenter, Nhật ký log hệ thống...")
                    paste_content = st.text_area("Nội dung văn bản dài", placeholder="Dán nội dung vào đây...", height=120)
                    if st.form_submit_button("Thêm vào nguồn tạm"):
                        if paste_content.strip():
                            final_title = paste_title.strip() or f"Nguồn dán tay {datetime.now().strftime('%d/%m %H:%M')}"
                            ts = TemporaryConversationSource(
                                id=f"SRC-{uuid.uuid4().hex[:8].upper()}",
                                conversation_id=active_conversation.id,
                                source_type="pasted_text",
                                title=final_title,
                                content_preview=paste_content[:150],
                                content_text=paste_content
                            )
                            save_temporary_source(ts)
                            st.success(f"Đã lưu thành công nguồn tạm: {final_title}")
                            safe_rerun()
                        else:
                            st.error("Nội dung nguồn không được để trống.")
                            
        with col_results:
            # Hiển thị câu trả lời và nguồn chứng minh bên phải
            last_assistant_msg = next((m for m in reversed(messages) if m.role == "assistant"), None)
            answer_text = last_assistant_msg.content if last_assistant_msg else "Hãy gửi câu hỏi để nhận phản hồi từ AIOS."
            
            # Danh sách nguồn chứng minh được dùng
            temp_sources_list = load_temporary_sources(active_conversation.id)
            proven_sources = []
            if temp_sources_list:
                for s in temp_sources_list:
                    proven_sources.append(f"Nguồn tạm: {s.title} (Trạng thái: Chưa lưu lâu dài)")
            else:
                proven_sources = ["Không có nguồn tạm nào được đính kèm."]
                
            # Ý cần kiểm tra và hành động tiếp theo
            if last_assistant_msg:
                to_check = ["Cần kiểm tra xem nguồn dữ liệu tạm có khớp với sổ tài liệu chính không."]
                next_actions = ["Xác thực lại lỗi vận hành trong Opcenter", "Chạy kiểm chứng an toàn dữ liệu"]
            else:
                to_check = []
                next_actions = []
                
            def on_save_case_cb():
                st.session_state.wsc_show_save_placeholder = True
                
            def on_explain_cb():
                st.session_state.wsc_show_explain_placeholder = True
                
            render_right_result_panel(
                answer_text=answer_text,
                proven_sources=proven_sources,
                to_check_items=to_check,
                next_actions=next_actions,
                on_save_case=on_save_case_cb,
                on_explain=on_explain_cb
            )
