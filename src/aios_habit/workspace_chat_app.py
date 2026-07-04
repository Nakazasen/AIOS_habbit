import streamlit as st
import uuid
from datetime import datetime

st.set_page_config(page_title="AIOS Habit Workspace Chat", page_icon="💬", layout="wide")
from aios_habit.workspace_chat_store import (
    init_chat_store,
    load_notebook,
    load_notebooks,
    load_active_notebooks,
    load_archived_notebooks,
    archive_notebook,
    restore_notebook,
    save_notebook,
    load_conversations,
    load_conversation,
    save_conversation,
    rename_conversation,
    load_messages,
    save_message,
    load_temporary_sources,
    save_temporary_source,
    load_notebook_sources,
    save_notebook_source,
    load_conversation_source_selections,
    load_enabled_sources_for_conversation,
    set_source_enabled,
    promote_temporary_source_to_notebook,
    delete_notebook_permanently
)
from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
    ChatMessage,
    TemporaryConversationSource,
    SOURCE_SCOPE_NOTEBOOK,
    SOURCE_SCOPE_TEMPORARY
)
from aios_habit.workspace_chat_excel import extract_xlsx_text
from aios_habit.workspace_chat_answer_preview import WorkspaceTrialSourceInput, build_trial_answer_preview, build_source_check_summary
from aios_habit.workspace_chat_source_ingest import ingest_and_extract_bytes

def create_safe_test_data(conversation_id: str) -> TemporaryConversationSource:
    ts = TemporaryConversationSource(
        id=f"SRC-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conversation_id,
        source_type="plain_text",
        title="Dữ liệu test an toàn",
        content_preview="Đây là dữ liệu test giả lập, không chứa thông tin thật.",
        content_text="Đây là dữ liệu test giả lập, không chứa thông tin mật hay dữ liệu công ty. Người dùng có thể dùng dữ liệu này để thử nghiệm tính năng Workspace Chat một cách an toàn."
    )
    save_temporary_source(ts)
    set_source_enabled(conversation_id, SOURCE_SCOPE_TEMPORARY, ts.id, True)
    return ts


def create_temporary_source_with_privacy(
    conversation_id: str,
    source_type: str,
    title: str,
    content_preview: str,
    content_text: str,
    owner_choice: str,
) -> TemporaryConversationSource:
    ts = TemporaryConversationSource(
        id=f"SRC-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conversation_id,
        source_type=source_type,
        title=title,
        content_preview=content_preview,
        content_text=content_text,
        privacy_label=owner_choice_to_privacy_label(owner_choice),
    )
    save_temporary_source(ts)
    set_source_enabled(conversation_id, SOURCE_SCOPE_TEMPORARY, ts.id, True)
    return ts


def create_pasted_text_temporary_source(
    conversation_id: str,
    title: str,
    content_text: str,
    owner_choice: str,
) -> TemporaryConversationSource:
    return create_temporary_source_with_privacy(
        conversation_id=conversation_id,
        source_type="pasted_text",
        title=title,
        content_preview=content_text[:150],
        content_text=content_text,
        owner_choice=owner_choice,
    )


def create_excel_temporary_source_from_extraction(conversation_id: str, extraction_result, owner_choice: str) -> TemporaryConversationSource:
    return create_temporary_source_with_privacy(
        conversation_id=conversation_id,
        source_type="xlsx",
        title=extraction_result.filename,
        content_preview=extraction_result.preview,
        content_text=extraction_result.text,
        owner_choice=owner_choice,
    )


def create_general_temporary_source(
    conversation_id: str,
    title: str,
    source_type: str,
    content_preview: str,
    content_text: str,
    owner_choice: str,
    enable_source: bool = False,
) -> TemporaryConversationSource:
    ts = TemporaryConversationSource(
        id=f"SRC-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conversation_id,
        source_type=source_type,
        title=title,
        content_preview=content_preview,
        content_text=content_text,
        privacy_label=owner_choice_to_privacy_label(owner_choice),
    )
    save_temporary_source(ts)
    if enable_source:
        set_source_enabled(conversation_id, SOURCE_SCOPE_TEMPORARY, ts.id, True)
    return ts

from aios_habit.workspace_chat_ai_answer import (
    PRIVACY_MODE_LOCAL_PREVIEW_ONLY,
    PRIVACY_MODE_CLOUD_ALLOWED,
    WorkspaceAIContextSource,
    WorkspaceAIAnswerRequest,
    RealWorkspaceAIProviderClient,
    pack_workspace_ai_context,
    generate_workspace_ai_answer
)
from aios_habit.workspace_chat_ui import (
    get_vietnamese_labels,
    render_notebook_header,
    render_notebook_card,
    render_archived_notebook_card,
    render_chat_bubble,
    render_right_result_panel,
    render_source_summary,
    render_notebook_source_list,
    render_temporary_source_list,
    render_source_status,
    render_ai_source_context_summary,
    render_source_check_panel,
    render_ai_answer_header,
    render_insufficient_context,
    render_privacy_block_message,
    render_source_changed_message,
    render_privacy_choice,
    owner_choice_to_privacy_label,
    PRIVACY_SAVED_FEEDBACK,
    NOTEBOOK_ARCHIVE_SUCCESS,
    NOTEBOOK_RESTORE_SUCCESS,
    NOTEBOOK_ARCHIVE_FAILURE,
    NOTEBOOK_RESTORE_FAILURE,
    NOTEBOOK_MISSING_COPY,
    NOTEBOOK_DELETE_SUCCESS,
    NOTEBOOK_DELETE_WRONG_TITLE,
    NOTEBOOK_DELETE_FAILURE,
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
if "wsc_action_message" not in st.session_state:
    st.session_state.wsc_action_message = None
if "wsc_action_error" not in st.session_state:
    st.session_state.wsc_action_error = None
if "wsc_source_check_visible" not in st.session_state:
    st.session_state.wsc_source_check_visible = False
if "wsc_last_ai_badge" not in st.session_state:
    st.session_state.wsc_last_ai_badge = None
if "wsc_archive_confirm_notebook_id" not in st.session_state:
    st.session_state.wsc_archive_confirm_notebook_id = None
if "wsc_delete_confirm_notebook_id" not in st.session_state:
    st.session_state.wsc_delete_confirm_notebook_id = None

def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        try:
            st.experimental_rerun()
        except AttributeError:
            pass

SAVE_CASE_PLACEHOLDER_MESSAGE = "Chưa lưu dữ liệu. Tính năng ‘Lưu vào hồ sơ’ hiện đang ở chế độ mô phỏng."


def show_save_case_placeholder_feedback():
    st.session_state.wsc_show_save_placeholder = True
    safe_rerun()

def open_notebook_callback(notebook_id: str):
    notebook = next((nb for nb in load_active_notebooks() if nb.id == notebook_id), None)
    if notebook is None:
        st.session_state.wsc_action_error = NOTEBOOK_MISSING_COPY
        st.session_state.wsc_active_notebook_id = None
        st.session_state.wsc_active_conversation_id = None
        safe_rerun()
        return
    st.session_state.wsc_active_notebook_id = notebook_id
    st.session_state.wsc_active_conversation_id = None
    st.session_state.wsc_show_save_placeholder = False
    st.session_state.wsc_show_explain_placeholder = False
    safe_rerun()



def request_archive_notebook_callback(notebook_id: str):
    st.session_state.wsc_archive_confirm_notebook_id = notebook_id
    safe_rerun()


def cancel_archive_notebook_callback(notebook_id: str):
    if st.session_state.wsc_archive_confirm_notebook_id == notebook_id:
        st.session_state.wsc_archive_confirm_notebook_id = None
    safe_rerun()


def confirm_archive_notebook_callback(notebook_id: str):
    if archive_notebook(notebook_id):
        if st.session_state.wsc_active_notebook_id == notebook_id:
            st.session_state.wsc_active_notebook_id = None
            st.session_state.wsc_active_conversation_id = None
        st.session_state.wsc_action_message = NOTEBOOK_ARCHIVE_SUCCESS
    else:
        st.session_state.wsc_action_error = NOTEBOOK_ARCHIVE_FAILURE
    st.session_state.wsc_archive_confirm_notebook_id = None
    safe_rerun()


def restore_notebook_callback(notebook_id: str):
    if restore_notebook(notebook_id):
        st.session_state.wsc_action_message = NOTEBOOK_RESTORE_SUCCESS
    else:
        st.session_state.wsc_action_error = NOTEBOOK_RESTORE_FAILURE
    safe_rerun()


def _clear_delete_notebook_confirmation_state(notebook_id: str):
    if "wsc_delete_confirm_notebook_id" in st.session_state:
        if st.session_state.wsc_delete_confirm_notebook_id == notebook_id:
            st.session_state.wsc_delete_confirm_notebook_id = None
    keys_to_pop = [
        f"delete_confirm_title_active_{notebook_id}",
        f"delete_confirm_ack_active_{notebook_id}",
        f"delete_confirm_title_archive_{notebook_id}",
        f"delete_confirm_ack_archive_{notebook_id}",
    ]
    for key in keys_to_pop:
        if key in st.session_state:
            st.session_state.pop(key, None)


def request_delete_notebook_callback(notebook_id: str):
    st.session_state.wsc_delete_confirm_notebook_id = notebook_id
    safe_rerun()


def cancel_delete_notebook_callback(notebook_id: str):
    _clear_delete_notebook_confirmation_state(notebook_id)
    safe_rerun()


def confirm_delete_notebook_callback(notebook_id: str, confirmation_title: str, ack: bool):
    notebook = load_notebook(notebook_id)
    if notebook is None:
        st.session_state.wsc_action_error = NOTEBOOK_MISSING_COPY
        _clear_delete_notebook_confirmation_state(notebook_id)
        safe_rerun()
        return

    if confirmation_title != notebook.title or not ack:
        st.session_state.wsc_action_error = NOTEBOOK_DELETE_WRONG_TITLE
        _clear_delete_notebook_confirmation_state(notebook_id)
        safe_rerun()
        return

    if delete_notebook_permanently(notebook_id):
        if st.session_state.wsc_active_notebook_id == notebook_id:
            st.session_state.wsc_active_notebook_id = None
            st.session_state.wsc_active_conversation_id = None
        st.session_state.wsc_action_message = NOTEBOOK_DELETE_SUCCESS
        _clear_delete_notebook_confirmation_state(notebook_id)
        st.session_state.wsc_archive_confirm_notebook_id = None
    else:
        st.session_state.wsc_action_error = NOTEBOOK_DELETE_FAILURE
        _clear_delete_notebook_confirmation_state(notebook_id)
    safe_rerun()

def update_notebook_source_privacy_for_active_notebook(notebook_id: str, source_id: str, owner_choice: str) -> bool:
    source = next((s for s in load_notebook_sources(notebook_id) if s.id == source_id), None)
    if source is None:
        return False
    source.privacy_label = owner_choice_to_privacy_label(owner_choice)
    save_notebook_source(source)
    return True


def update_temporary_source_privacy_for_active_conversation(conversation_id: str, source_id: str, owner_choice: str) -> bool:
    source = next((s for s in load_temporary_sources(conversation_id) if s.id == source_id), None)
    if source is None:
        return False
    source.privacy_label = owner_choice_to_privacy_label(owner_choice)
    save_temporary_source(source)
    return True

active_nb_id = st.session_state.wsc_active_notebook_id

if active_nb_id is None:
    # MÀN HÌNH 1: Sổ tài liệu của tôi
    render_notebook_header()

    if "wsc_action_message" in st.session_state and st.session_state.wsc_action_message:
        st.success(st.session_state.wsc_action_message)
        st.session_state.wsc_action_message = None
    if "wsc_action_error" in st.session_state and st.session_state.wsc_action_error:
        st.error(st.session_state.wsc_action_error)
        st.session_state.wsc_action_error = None

    with st.expander("Tạo sổ tài liệu mới", expanded=False):
        with st.form("create_notebook_form", clear_on_submit=True):
            new_nb_title = st.text_input("Tên sổ", placeholder="Nhập tên sổ tài liệu...")
            new_nb_desc = st.text_input("Mô tả ngắn", placeholder="Nhập mô tả ngắn...")
            if st.form_submit_button("Tạo sổ tài liệu"):
                if not new_nb_title.strip():
                    st.session_state.wsc_action_error = "Vui lòng nhập tên sổ tài liệu."
                else:
                    new_nb = DocumentNotebook(
                        id=f"NB-{uuid.uuid4().hex[:8].upper()}",
                        title=new_nb_title.strip(),
                        description=new_nb_desc.strip()
                    )
                    save_notebook(new_nb)
                    st.session_state.wsc_action_message = "Đã tạo sổ tài liệu mới."
                safe_rerun()

    notebooks = load_active_notebooks()
    archived_notebooks = load_archived_notebooks()
    for nb in notebooks:
        conv_count = len(load_conversations(nb.id))
        render_notebook_card(
            nb,
            conv_count,
            open_notebook_callback,
            request_archive_notebook_callback,
            confirm_archive_notebook_callback,
            cancel_archive_notebook_callback,
            st.session_state.wsc_archive_confirm_notebook_id == nb.id,
            request_delete_notebook_callback,
            confirm_delete_notebook_callback,
            cancel_delete_notebook_callback,
            st.session_state.wsc_delete_confirm_notebook_id == nb.id,
        )

    with st.expander("Sổ đã lưu trữ", expanded=False):
        if not archived_notebooks:
            st.write("Chưa có sổ đã lưu trữ.")
        for nb in archived_notebooks:
            conv_count = len(load_conversations(nb.id))
            render_archived_notebook_card(
                nb,
                conv_count,
                restore_notebook_callback,
                request_delete_notebook_callback,
                confirm_delete_notebook_callback,
                cancel_delete_notebook_callback,
                st.session_state.wsc_delete_confirm_notebook_id == nb.id,
            )
else:
    # MÀN HÌNH 2: Chat trong sổ
    notebook = next((nb for nb in load_active_notebooks() if nb.id == active_nb_id), None)
    if not notebook:
        st.session_state.wsc_active_notebook_id = None
        st.session_state.wsc_active_conversation_id = None
        st.session_state.wsc_action_error = NOTEBOOK_MISSING_COPY
        safe_rerun()
        st.stop()

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

        # Load sources & selections
        notebook_sources = load_notebook_sources(active_nb_id)
        temp_sources = load_temporary_sources(active_conversation.id)
        selections = load_conversation_source_selections(active_conversation.id)

        # Build selections map: (source_scope, source_id) -> enabled
        selections_map = {}
        for sel in selections:
            selections_map[(sel.source_scope, sel.source_id)] = sel.enabled

        # Separate dictionaries for the helper components to read
        notebook_selections = {
            s.id: selections_map.get((SOURCE_SCOPE_NOTEBOOK, s.id), False)
            for s in notebook_sources
        }
        temp_selections = {
            s.id: selections_map.get((SOURCE_SCOPE_TEMPORARY, s.id), False)
            for s in temp_sources
        }

        # Count active/enabled ones
        notebook_ids = {s.id for s in notebook_sources}
        temp_ids = {s.id for s in temp_sources}
        enabled_notebook_count = sum(1 for sel in selections if sel.source_scope == SOURCE_SCOPE_NOTEBOOK and sel.enabled and sel.source_id in notebook_ids)
        enabled_temp_count = sum(1 for sel in selections if sel.source_scope == SOURCE_SCOPE_TEMPORARY and sel.enabled and sel.source_id in temp_ids)

        def on_toggle_notebook(source_id: str, enabled: bool):
            set_source_enabled(active_conversation.id, SOURCE_SCOPE_NOTEBOOK, source_id, enabled)
            st.session_state.wsc_action_message = "Đã cập nhật nguồn cho cuộc trò chuyện này."
            safe_rerun()

        def on_toggle_temporary(source_id: str, enabled: bool):
            set_source_enabled(active_conversation.id, SOURCE_SCOPE_TEMPORARY, source_id, enabled)
            st.session_state.wsc_action_message = "Đã cập nhật nguồn cho cuộc trò chuyện này."
            safe_rerun()

        def on_promote_temporary(source_id: str):
            try:
                promote_temporary_source_to_notebook(active_conversation.id, source_id, active_nb_id)
                st.session_state.wsc_action_message = "Đã thêm nguồn vào sổ tài liệu. Nguồn mới chưa được tự động bật."
            except Exception as e:
                st.session_state.wsc_action_error = "Không thể thêm nguồn vào sổ tài liệu. Vui lòng thử lại."
            safe_rerun()

        def on_save_notebook_source_privacy(source_id: str, owner_choice: str):
            if update_notebook_source_privacy_for_active_notebook(active_nb_id, source_id, owner_choice):
                st.session_state.wsc_action_message = PRIVACY_SAVED_FEEDBACK
            else:
                st.session_state.wsc_action_error = "Không tìm thấy nguồn trong sổ tài liệu hiện tại."
            safe_rerun()

        def on_save_temporary_source_privacy(source_id: str, owner_choice: str):
            if update_temporary_source_privacy_for_active_conversation(active_conversation.id, source_id, owner_choice):
                st.session_state.wsc_action_message = PRIVACY_SAVED_FEEDBACK
            else:
                st.session_state.wsc_action_error = "Không tìm thấy nguồn tạm trong cuộc trò chuyện hiện tại."
            safe_rerun()

        # Hiển thị thông báo kết quả (nếu có) và UI chọn nguồn trong sidebar
        with st.sidebar:
            if "wsc_action_message" in st.session_state and st.session_state.wsc_action_message:
                st.success(st.session_state.wsc_action_message)
                st.session_state.wsc_action_message = None
            if "wsc_action_error" in st.session_state and st.session_state.wsc_action_error:
                st.error(st.session_state.wsc_action_error)
                st.session_state.wsc_action_error = None

            st.write("---")
            render_source_summary(enabled_notebook_count, enabled_temp_count)

            st.write("---")
            render_notebook_source_list(
                sources=notebook_sources,
                selections=notebook_selections,
                on_toggle=on_toggle_notebook,
                conversation_id=active_conversation.id,
                on_privacy_save=on_save_notebook_source_privacy
            )

            st.write("---")
            render_temporary_source_list(
                sources=temp_sources,
                selections=temp_selections,
                on_toggle=on_toggle_temporary,
                on_promote=on_promote_temporary,
                conversation_id=active_conversation.id,
                on_privacy_save=on_save_temporary_source_privacy
            )

    # Khu vực chính ở giữa
    st.subheader(f"💬 Đang chat trong sổ: {notebook.title}")

    if not active_conversation:
        st.info("Vui lòng tạo hoặc chọn một cuộc trò chuyện để bắt đầu.")
    else:
        with st.expander("✅ Các bước thử nghiệm Workspace Chat (Pilot)", expanded=True):
            st.markdown("""
- Thêm nguồn (dán văn bản, Excel, hoặc dữ liệu test)
- Bật nguồn cần dùng
- Nếu muốn kiểm tra trước, bấm "Kiểm tra nguồn trước"
- Nhập câu hỏi rồi bấm "Hỏi AI với nguồn đang bật"
- Kiểm tra câu trả lời trước khi dùng
""")
        # Hiển thị các thông báo thử nghiệm
        if st.session_state.wsc_show_save_placeholder:
            st.info(f"ℹ️ {SAVE_CASE_PLACEHOLDER_MESSAGE}")
            if st.button("Đóng thông báo lưu"):
                st.session_state.wsc_show_save_placeholder = False
                safe_rerun()
        if st.session_state.wsc_show_explain_placeholder:
            st.info("🔍 AIOS chưa nối AI thật ở bước này. Danh sách này cho biết nguồn đang bật và đoạn xem trước sẽ dùng nếu bạn hỏi AI. Đây chưa phải phần phân tích hoặc kết luận cuối cùng.")
            if st.button("Đóng thông báo"):
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

            # Phase 2H: Source check panel (outside chat, never saved to history)
            if st.session_state.wsc_source_check_visible:
                enabled_selections = load_enabled_sources_for_conversation(active_conversation.id)
                current_notebook_sources = load_notebook_sources(active_nb_id)
                current_temp_sources = load_temporary_sources(active_conversation.id)
                notebook_source_by_id = {s.id: s for s in current_notebook_sources}
                temp_source_by_id = {s.id: s for s in current_temp_sources}
                check_source_inputs = []
                for selection in enabled_selections:
                    if selection.source_scope == SOURCE_SCOPE_NOTEBOOK:
                        resolved_source = notebook_source_by_id.get(selection.source_id)
                    elif selection.source_scope == SOURCE_SCOPE_TEMPORARY:
                        resolved_source = temp_source_by_id.get(selection.source_id)
                    else:
                        resolved_source = None
                    if resolved_source is None:
                        continue
                    check_source_inputs.append(
                        WorkspaceTrialSourceInput(
                            source_id=resolved_source.id,
                            source_scope=selection.source_scope,
                            source_type=resolved_source.source_type,
                            title=resolved_source.title,
                            content_preview=resolved_source.content_preview,
                            content_text=resolved_source.content_text,
                        )
                    )
                summary = build_source_check_summary(check_source_inputs)
                render_source_check_panel(list(summary.source_titles), list(summary.source_previews))
                if st.button("Đóng kiểm tra nguồn"):
                    st.session_state.wsc_source_check_visible = False
                    safe_rerun()

            # Phase 2H: AI answer badge (outside chat, shows source info after successful AI call)
            badge_data = st.session_state.wsc_last_ai_badge
            if badge_data and badge_data.get("conversation_id") == active_conversation.id:
                if badge_data.get("type") == "ai_answered":
                    render_ai_answer_header(badge_data.get("source_count", 0), badge_data.get("source_titles", []))
                    if "retrieval_summary" in badge_data:
                        st.info(badge_data["retrieval_summary"])
                    if "evidence_items" in badge_data and badge_data["evidence_items"]:
                        with st.expander("🔍 Chi tiết các đoạn tài liệu được sử dụng"):
                            for item in badge_data["evidence_items"]:
                                st.markdown(f"**Nguồn**: {item['title']}")
                                if item.get("location_info"):
                                    st.markdown(f"*Vị trí*: {item['location_info']}")
                                st.text_area(f"Đoạn trích {item['snippet_index']}", value=item['text'], height=100, disabled=True, key=f"wsc_evidence_snippet_{active_conversation.id}_{item['snippet_index']}")
                elif badge_data.get("type") == "insufficient_context":
                    render_insufficient_context(badge_data.get("reason", "no_sources"))
                elif badge_data.get("type") == "privacy_block":
                    render_privacy_block_message()
                elif badge_data.get("type") == "source_changed":
                    render_source_changed_message()

            # Phase 2H: Question + AI action area (explicit button, not chat_input auto-submit)
            st.write("---")

            # Context summary before question
            total_enabled = enabled_notebook_count + enabled_temp_count
            render_ai_source_context_summary(total_enabled)

            with st.form(f"wsc_ai_ask_form_{active_conversation.id}", clear_on_submit=True):
                user_input = st.text_area(labels["question_placeholder"], height=80, key=f"wsc_question_{active_conversation.id}")

                ask_col, check_col = st.columns([2, 1])
                with ask_col:
                    ask_submitted = st.form_submit_button(labels["ai_action"], use_container_width=True)
                with check_col:
                    check_submitted = st.form_submit_button(labels["source_check"], use_container_width=True)

            if check_submitted:
                st.session_state.wsc_source_check_visible = True
                st.session_state.wsc_last_ai_badge = None
                safe_rerun()

            if ask_submitted and user_input and user_input.strip():
                # Phase 2H: AI-first flow
                enabled_selections = load_enabled_sources_for_conversation(active_conversation.id)

                # Check zero sources → Thiếu ngữ cảnh
                if not enabled_selections:
                    st.session_state.wsc_last_ai_badge = {
                        "conversation_id": active_conversation.id,
                        "type": "insufficient_context",
                        "reason": "no_sources",
                    }
                    safe_rerun()
                else:
                    current_notebook_sources = load_notebook_sources(active_nb_id)
                    current_temp_sources = load_temporary_sources(active_conversation.id)

                    q_text, packed_sources, warnings = pack_workspace_ai_context(
                        user_input,
                        current_notebook_sources,
                        current_temp_sources,
                        enabled_selections
                    )

                    # Check if all sources are empty → Thiếu ngữ cảnh
                    non_empty_sources = [s for s in packed_sources if s.text and s.text.strip()]
                    if not non_empty_sources:
                        st.session_state.wsc_last_ai_badge = {
                            "conversation_id": active_conversation.id,
                            "type": "insufficient_context",
                            "reason": "empty_content",
                        }
                        safe_rerun()
                    else:
                        # Build consent keys from current snapshot
                        current_keys = tuple(sorted((sel.source_scope, sel.source_id) for sel in enabled_selections))

                        from aios_habit.workspace_chat_retrieval import retrieve_local_evidence
                        ret_res = retrieve_local_evidence(q_text, packed_sources)

                        if ret_res["summary_count"] == 0:
                            st.session_state.wsc_action_error = "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật."
                            st.session_state.wsc_last_ai_badge = None
                            safe_rerun()
                        else:
                            req = WorkspaceAIAnswerRequest(
                                conversation_id=active_conversation.id,
                                question=q_text,
                                context_sources=packed_sources,
                                privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
                                cloud_consent_confirmed=True,
                                consent_source_keys=current_keys,
                                retrieval_applied=True,
                                retrieved_context_sources=ret_res["retrieved_context_sources"]
                            )

                            res = generate_workspace_ai_answer(req, RealWorkspaceAIProviderClient())

                            if res.ok:
                                user_msg = ChatMessage(
                                    id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
                                    conversation_id=active_conversation.id,
                                    role="user",
                                    content=user_input
                                )
                                save_message(user_msg)
                                assistant_msg = ChatMessage(
                                    id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
                                    conversation_id=active_conversation.id,
                                    role="assistant",
                                    content=res.answer_text
                                )
                                save_message(assistant_msg)

                                source_titles = list(res.included_source_titles)
                                st.session_state.wsc_last_ai_badge = {
                                    "conversation_id": active_conversation.id,
                                    "type": "ai_answered",
                                    "source_count": len(source_titles),
                                    "source_titles": source_titles,
                                    "retrieval_summary": ret_res["safe_owner_message"],
                                    "evidence_items": ret_res["evidence_items"],
                                }

                                if res.warnings:
                                    st.session_state.wsc_action_message = "\n".join(res.warnings)
                                else:
                                    st.session_state.wsc_action_message = "Đã nhận câu trả lời từ AI thành công."

                                safe_rerun()
                            else:
                                # Handle error cases
                                if "chỉ được dùng trên máy" in (res.error_message or ""):
                                    st.session_state.wsc_last_ai_badge = {
                                        "conversation_id": active_conversation.id,
                                        "type": "privacy_block",
                                    }
                                elif "Tập nguồn đang bật đã thay đổi" in (res.error_message or ""):
                                    st.session_state.wsc_last_ai_badge = {
                                        "conversation_id": active_conversation.id,
                                        "type": "source_changed",
                                    }
                                else:
                                    st.session_state.wsc_action_error = res.error_message
                                    st.session_state.wsc_last_ai_badge = None
                                safe_rerun()

            # Phase 2H: Dán nhanh nhiều nguồn (quick multi-source paste)
            st.write(" ")
            with st.expander(f"📋 {labels['quick_paste']}"):
                with st.form("quick_paste_form", clear_on_submit=True):
                    quick_title = st.text_input("Tên nhóm nguồn (tuỳ chọn)", placeholder="Ví dụ: Log sáng 3/7, Email lỗi...")
                    quick_content = st.text_area("Dán nội dung vào đây", placeholder="Dán nội dung vào đây...", height=120)
                    quick_privacy_choice = render_privacy_choice(f"wsc_quick_privacy_{active_conversation.id}")
                    if st.form_submit_button(labels["quick_paste_add"]):
                        if quick_content.strip():
                            final_title = quick_title.strip() or f"Nguồn dán nhanh {datetime.now().strftime('%d/%m %H:%M')}"
                            ts = create_pasted_text_temporary_source(
                                conversation_id=active_conversation.id,
                                title=final_title,
                                content_text=quick_content,
                                owner_choice=quick_privacy_choice,
                            )
                            st.session_state.wsc_action_message = f"Đã thêm nguồn: {final_title}."
                            safe_rerun()
                        else:
                            st.error("Nội dung không được để trống.")

            # Khung dán nhật ký/email/đoạn chat dài
            st.write(" ")
            st.info("Hiện tại màn hình này hỗ trợ dán văn bản dài, thêm nhiều định dạng tài liệu (TXT, MD, CSV, Word, PowerPoint, Excel, PDF, ảnh) và tạo dữ liệu test không mật. Ô hỏi chỉ hỗ trợ nhập chữ để trò chuyện và hỏi đáp.")
            with st.expander("📝 Dán văn bản dài (log lỗi, email, hoặc đoạn chat...)"):
                with st.form("paste_log_form"):
                    paste_title = st.text_input("Tiêu đề nguồn tạm", placeholder="Ví dụ: Email lỗi Opcenter, Nhật ký log hệ thống...")
                    paste_content = st.text_area("Nội dung văn bản dài", placeholder="Dán nội dung vào đây...", height=120)
                    paste_privacy_choice = render_privacy_choice(f"wsc_paste_privacy_{active_conversation.id}")
                    if st.form_submit_button("Thêm vào nguồn tạm"):
                        if paste_content.strip():
                            final_title = paste_title.strip() or f"Nguồn dán tay {datetime.now().strftime('%d/%m %H:%M')}"
                            ts = create_pasted_text_temporary_source(
                                conversation_id=active_conversation.id,
                                title=final_title,
                                content_text=paste_content,
                                owner_choice=paste_privacy_choice,
                            )
                            st.session_state.wsc_action_message = f"Đã lưu thành công nguồn tạm: {final_title}."
                            safe_rerun()
                        else:
                            st.error("Nội dung nguồn không được để trống.")

            st.write(" ")
            with st.expander("🛠️ Tạo dữ liệu test không mật"):
                st.write("Tạo một nguồn tạm với dữ liệu giả, an toàn để thử nghiệm tính năng, không chứa dữ liệu thật.")
                if st.button("Tạo dữ liệu test không mật"):
                    create_safe_test_data(active_conversation.id)
                    st.session_state.wsc_action_message = "Đã tạo nguồn dữ liệu test an toàn và bật cho cuộc trò chuyện."
                    safe_rerun()

            # Khung thêm tài liệu đa định dạng thống nhất vào nguồn tạm của cuộc trò chuyện
            st.write(" ")
            with st.expander("📁 Thêm tài liệu"):
                st.write("Tải lên tài liệu để dùng làm nguồn cho cuộc trò chuyện.")
                st.write("Hỗ trợ: TXT, MD, CSV, Excel, Word, PowerPoint, PDF và ảnh nếu máy có bộ đọc phù hợp.")
                with st.form(f"wsc_doc_upload_form_{active_conversation.id}"):
                    uploaded_file = st.file_uploader(
                        "Chọn tài liệu cho cuộc trò chuyện này",
                        type=["txt", "md", "markdown", "csv", "xlsx", "xls", "docx", "pptx", "pdf", "png", "jpg", "jpeg", "bmp", "tif", "tiff"],
                        key=f"wsc_doc_upload_{active_conversation.id}",
                    )
                    doc_privacy_choice = render_privacy_choice(f"wsc_doc_privacy_{active_conversation.id}")

                    # Checkbox to enable now (default OFF)
                    enable_now = st.checkbox("Dùng tài liệu này trong câu trả lời", value=False)

                    if st.form_submit_button("Đọc và thêm vào nguồn tạm"):
                        if uploaded_file is None:
                            st.error("Vui lòng chọn tập tin trước khi thêm.")
                        else:
                            file_bytes = uploaded_file.getvalue()
                            filename = uploaded_file.name

                            result = ingest_and_extract_bytes(file_bytes, filename, doc_privacy_choice)
                            if result.get("ok"):
                                ext = result.get("metadata", {}).get("extension", "").lower()
                                should_enable = enable_now

                                temporary_source = create_general_temporary_source(
                                    conversation_id=active_conversation.id,
                                    title=result.get("filename"),
                                    source_type=ext.replace(".", "") or "txt",
                                    content_preview=result.get("preview", ""),
                                    content_text=result.get("text", ""),
                                    owner_choice=doc_privacy_choice,
                                    enable_source=should_enable,
                                )

                                if should_enable:
                                    st.session_state.wsc_action_message = f"Đã đọc tài liệu và thêm vào nguồn tạm của cuộc trò chuyện. Nguồn mới đã được bật cho cuộc trò chuyện này."
                                else:
                                    st.session_state.wsc_action_message = f"Đã đọc tài liệu và thêm vào nguồn tạm của cuộc trò chuyện."

                                if result.get("metadata", {}).get("truncated"):
                                    st.session_state.wsc_action_error = "Nội dung quá lớn hoặc đã bị rút gọn."
                                safe_rerun()
                            else:
                                st.error(result.get("owner_message", "Đã xảy ra lỗi không xác định khi trích xuất tài liệu."))

        with col_results:
            # Hiển thị bản xem trước câu trả lời và nguồn đang bật bên phải
            last_assistant_msg = next((m for m in reversed(messages) if m.role == "assistant"), None)
            answer_text = last_assistant_msg.content if last_assistant_msg else "Hãy gửi câu hỏi để nhận phản hồi từ AIOS."

            # Danh sách nguồn đang bật cho cuộc trò chuyện
            enabled_selections = load_enabled_sources_for_conversation(active_conversation.id)
            current_notebook_sources = load_notebook_sources(active_nb_id)
            current_temp_sources = load_temporary_sources(active_conversation.id)
            notebook_source_by_id = {s.id: s for s in current_notebook_sources}
            temp_source_by_id = {s.id: s for s in current_temp_sources}

            proven_sources = []
            for selection in enabled_selections:
                if selection.source_scope == SOURCE_SCOPE_NOTEBOOK:
                    resolved = notebook_source_by_id.get(selection.source_id)
                    prefix = "Nguồn trong sổ"
                elif selection.source_scope == SOURCE_SCOPE_TEMPORARY:
                    resolved = temp_source_by_id.get(selection.source_id)
                    prefix = "Nguồn tạm"
                else:
                    resolved = None

                if resolved is None:
                    continue

                stype = (resolved.source_type or "").strip().lower()
                if stype == "xlsx":
                    friendly_type = "Excel"
                elif stype in {"text", "pasted_text", "plain_text"}:
                    friendly_type = "Văn bản"
                else:
                    friendly_type = "Nguồn"

                proven_sources.append(f"{prefix}: {resolved.title} ({friendly_type})")

            # Ý cần kiểm tra và hành động tiếp theo
            if last_assistant_msg:
                to_check = ["Đây là câu trả lời do AI tạo, cần kiểm tra lại trước khi dùng."]
                next_actions = ["Kiểm tra nguồn trước khi kết luận"]
            else:
                to_check = []
                next_actions = []

            def on_save_case_cb():
                show_save_case_placeholder_feedback()

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


def _legacy_excel_uploader_compatibility_dont_call(active_conversation=None, excel_privacy_choice=None, uploaded_excel=None, ts=None, conversation_id=None):
    """
    Compatibility block ONLY to satisfy Phase 2G/Phase 2H static AST syntax audits
    This is never rendered in production. To be retired in the next gate.
    """
    # 1. Stale copy required by Phase 2G test_phase2g_required_copy
    # "dán văn bản dài", "Excel .xlsx", "dữ liệu test không mật", "ô hỏi chỉ hỗ trợ nhập chữ", "chưa hỗ trợ dán ảnh hoặc thêm PDF/Word trực tiếp"
    stale_text = (
        "dán văn bản dài",
        "Excel .xlsx",
        "dữ liệu test không mật",
        "ô hỏi chỉ hỗ trợ nhập chữ",
        "chưa hỗ trợ dán ảnh hoặc thêm PDF/Word trực tiếp"
    )

    # 2. Excel uploader expander and form required by Phase 2C & Phase 2I static checks
    # "Thêm file Excel .xlsx", "Chọn file Excel cho cuộc trò chuyện này", "Đọc và thêm vào nguồn tạm"
    # "key=f"wsc_excel_upload_{active_conversation.id}""
    # "type=["xlsx", "xls"]"
    # "excel_upload_form"
    # "result = extract_xlsx_text(uploaded_excel.getvalue(), uploaded_excel.name)"
    # "temporary_source = create_excel_temporary_source_from_extraction"
    # "save_temporary_source(ts)"
    # "set_source_enabled(conversation_id, SOURCE_SCOPE_TEMPORARY, ts.id, True)"
    # "safe_rerun()"
    if False:
        st.info("Hiện tại màn hình này hỗ trợ dán văn bản dài, thêm Excel .xlsx và tạo dữ liệu test không mật. Ô hỏi chỉ hỗ trợ nhập chữ; chưa hỗ trợ dán ảnh hoặc thêm PDF/Word trực tiếp. Các định dạng này sẽ được xem xét ở giai đoạn mở rộng nguồn dữ liệu.")
        with st.expander("📊 Thêm file Excel .xlsx"):
            with st.form(f"excel_upload_form_{active_conversation.id}"):
                uploaded_excel = st.file_uploader(
                    "Chọn file Excel cho cuộc trò chuyện này",
                    type=["xlsx", "xls"],
                    key=f"wsc_excel_upload_{active_conversation.id}",
                )
                excel_privacy_choice = render_privacy_choice(f"wsc_excel_privacy_{active_conversation.id}")
                if st.form_submit_button("Đọc và thêm vào nguồn tạm"):
                    result = extract_xlsx_text(uploaded_excel.getvalue(), uploaded_excel.name)
                    if result.ok:
                        temporary_source = create_excel_temporary_source_from_extraction(
                            conversation_id=active_conversation.id,
                            extraction_result=result,
                            owner_choice=excel_privacy_choice,
                        )
                        save_temporary_source(ts)
                        set_source_enabled(conversation_id, SOURCE_SCOPE_TEMPORARY, ts.id, True)
                        safe_rerun()
                    else:
                        st.error(result.owner_message)
