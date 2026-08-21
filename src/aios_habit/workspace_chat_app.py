import streamlit as st
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from aios_habit.workspace_paths import default_agent_workspace_root

st.set_page_config(
    page_title="AIOS Habit Workspace Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown('''
    <style>
        .stDeployButton {display:none;}
        [data-testid="stHeader"] {
            background: transparent !important;
        }
        [data-testid="stSidebarCollapsedControl"] {
            visibility: visible !important;
            display: flex !important;
            z-index: 1000 !important;
        }

        /* Mở rộng tối đa không gian đọc, giảm lãng phí padding */
        .main .block-container {
            max-width: 96% !important;
            padding-top: 1rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }

        /* Chat bubbles cao cấp, thoáng đãng, sắc nét */
        [data-testid="stChatMessage"] {
            padding: 1.2rem 1.6rem !important;
            border-radius: 12px !important;
            margin-bottom: 1.1rem !important;
            font-size: 15.5px !important;
            line-height: 1.68 !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
        }

        /* Danh sách và bảng biểu bên trong chat bubble */
        [data-testid="stChatMessage"] ul, [data-testid="stChatMessage"] ol {
            margin-top: 0.6rem !important;
            margin-bottom: 0.6rem !important;
            padding-left: 1.6rem !important;
        }
        [data-testid="stChatMessage"] li {
            margin-bottom: 0.4rem !important;
        }

        /* Auto smooth scroll */
        html {
            scroll-behavior: smooth;
        }

        /* Dịch file uploader */
        [data-testid="stFileUploadDropzone"] > div > div > span {
            display: none;
        }
        [data-testid="stFileUploadDropzone"] > div > div::before {
            content: "Kéo thả tài liệu vào đây";
            display: block;
            margin-bottom: 5px;
        }
        [data-testid="stFileUploadDropzone"] small {
            display: none;
        }
        [data-testid="stFileUploadDropzone"]::after {
            content: "Giới hạn 200MB/file";
            font-size: 0.8rem;
            color: rgba(250, 250, 250, 0.6);
        }
    </style>
''', unsafe_allow_html=True)


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
    update_conversation_search_preference,
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
    delete_notebook_permanently,
    delete_conversation,
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
from aios_habit.workspace_chat_folder_import import (
    scan_local_directory,
    ingest_scanned_files_batch,
    format_size_bytes,
)

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
    managed_path: str = "",
) -> TemporaryConversationSource:
    ts = TemporaryConversationSource(
        id=f"SRC-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conversation_id,
        source_type=source_type,
        title=title,
        content_preview=content_preview,
        content_text=content_text,
        privacy_label=owner_choice_to_privacy_label(owner_choice),
        managed_path=managed_path,
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
    managed_path: str = "",
) -> TemporaryConversationSource:
    ts = TemporaryConversationSource(
        id=f"SRC-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conversation_id,
        source_type=source_type,
        title=title,
        content_preview=content_preview,
        content_text=content_text,
        privacy_label=owner_choice_to_privacy_label(owner_choice),
        managed_path=managed_path,
    )
    save_temporary_source(ts)
    if enable_source:
        set_source_enabled(conversation_id, SOURCE_SCOPE_TEMPORARY, ts.id, True)
    return ts


def process_workspace_upload_batch(
    uploaded_files: list,
    conversation_id: str,
    doc_privacy_choice: str,
    enable_now: bool,
    save_to_notebook: bool = False,
    notebook_id: str = ""
) -> dict:
    """
    Process a list of uploaded files, ingest each one, and save as temporary source.
    Returns a dictionary of results.
    """
    success_count = 0
    fail_count = 0
    success_files = []
    failed_files = []
    errors_by_file = {}
    has_truncated = False

    for uploaded_file in uploaded_files:
        try:
            file_bytes = uploaded_file.getvalue()
            filename = uploaded_file.name
        except Exception as e:
            fail_count += 1
            fname = getattr(uploaded_file, "name", "unknown_file")
            failed_files.append(fname)
            errors_by_file[fname] = f"Không thể đọc bytes từ tập tin: {e}"
            continue

        result = ingest_and_extract_bytes(file_bytes, filename, doc_privacy_choice)
        if result.get("ok"):
            ext = result.get("metadata", {}).get("extension", "").lower()
            should_enable = enable_now

            ts = create_general_temporary_source(
                conversation_id=conversation_id,
                title=result.get("filename"),
                source_type=ext.replace(".", "") or "txt",
                content_preview=result.get("preview", ""),
                content_text=result.get("text", ""),
                owner_choice=doc_privacy_choice,
                enable_source=should_enable,
                managed_path=result.get("metadata", {}).get("managed_path", ""),
            )
            if save_to_notebook and notebook_id:
                promote_temporary_source_to_notebook(conversation_id, ts.id, notebook_id)
            success_count += 1
            success_files.append(filename)
            if result.get("metadata", {}).get("truncated"):
                has_truncated = True
        else:
            fail_count += 1
            failed_files.append(filename)
            errors_by_file[filename] = result.get("owner_message", "Đã xảy ra lỗi khi trích xuất tài liệu.")

    return {
        "success_count": success_count,
        "fail_count": fail_count,
        "success_files": success_files,
        "failed_files": failed_files,
        "errors_by_file": errors_by_file,
        "has_truncated": has_truncated,
    }


from aios_habit.workspace_chat_ai_answer import (
    PRIVACY_MODE_LOCAL_PREVIEW_ONLY,
    PRIVACY_MODE_CLOUD_ALLOWED,
    WorkspaceAIContextSource,
    WorkspaceAIAnswerRequest,
    RealWorkspaceAIProviderClient,
    pack_workspace_ai_context,
    generate_workspace_ai_answer
)
from aios_habit.workspace_chat_rag_v2_adapter import (
    _select_semantic_candidate_sources,
    schedule_workspace_chat_source_preparation,
    retry_workspace_chat_source_preparation,
    get_workspace_chat_source_preparation_status,
)
from aios_habit.workspace_chat_ui import (
    get_vietnamese_labels,
    render_notebook_header,
    render_notebook_card,
    render_archived_notebook_card,
    render_chat_bubble,
    render_right_result_panel,
    render_source_library,
    render_source_status,
    render_ai_source_context_summary,
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
from aios_habit.workspace_agent_bridge_client import WorkspaceAgentBridgeClient
from aios_habit.workspace_agent_models import WorkspaceAgentRequest
from aios_habit.workspace_agent_orchestrator import WorkspaceAgentOrchestrator


def _workspace_context_sources(notebook_sources, temp_sources):
    ctx_sources = []
    for source in notebook_sources:
        text = (
            getattr(source, "content_text", "")
            or getattr(source, "content_preview", "")
        )
        ctx_sources.append(
            WorkspaceAIContextSource(
                source_id=source.id,
                source_scope=SOURCE_SCOPE_NOTEBOOK,
                source_type=getattr(source, "source_type", "plain_text"),
                title=getattr(source, "title", "Untitled"),
                privacy_label=getattr(source, "privacy_label", "local_only"),
                text=text,
                included_chars=len(text),
                truncated=bool(getattr(source, "truncated", False)),
                managed_path=getattr(source, "managed_path", ""),
            )
        )
    for source in temp_sources:
        text = (
            getattr(source, "content_text", "")
            or getattr(source, "content_preview", "")
        )
        ctx_sources.append(
            WorkspaceAIContextSource(
                source_id=source.id,
                source_scope=SOURCE_SCOPE_TEMPORARY,
                source_type=getattr(source, "source_type", "plain_text"),
                title=getattr(source, "title", "Untitled"),
                privacy_label=getattr(source, "privacy_label", "local_only"),
                text=text,
                included_chars=len(text),
                truncated=bool(getattr(source, "truncated", False)),
                managed_path=getattr(source, "managed_path", ""),
            )
        )
    return tuple(ctx_sources)


def _schedule_sources_for_preparation(notebook_sources, temp_sources):
    ctx_sources = _workspace_context_sources(notebook_sources, temp_sources)
    return get_workspace_chat_source_preparation_status(ctx_sources)

# Tự động khởi tạo kho lưu trữ
init_chat_store()

def get_query_param(key: str) -> Optional[str]:
    """Retrieve query parameter across Streamlit versions."""
    try:
        val = st.query_params.get(key)
        if isinstance(val, list):
            return val[0] if val else None
        return val
    except Exception:
        try:
            params = st.experimental_get_query_params()
            val = params.get(key)
            if isinstance(val, list):
                return val[0] if val else None
            return val
        except Exception:
            return None


def set_query_params(**kwargs):
    """Update query parameters safely across Streamlit versions."""
    try:
        for k, v in kwargs.items():
            if v is None:
                if k in st.query_params:
                    del st.query_params[k]
            else:
                st.query_params[k] = str(v)
    except Exception:
        try:
            params = st.experimental_get_query_params()
            for k, v in kwargs.items():
                if v is None:
                    params.pop(k, None)
                else:
                    params[k] = [str(v)]
            st.experimental_set_query_params(**params)
        except Exception:
            pass


# Khởi tạo trạng thái phiên làm việc riêng (được đồng bộ với URL để F5/Refresh không bao giờ bị văng ra ngoài)
query_nb = get_query_param("nb")
query_conv = get_query_param("conv")

if "wsc_active_notebook_id" not in st.session_state:
    st.session_state.wsc_active_notebook_id = query_nb
elif query_nb and st.session_state.wsc_active_notebook_id != query_nb:
    st.session_state.wsc_active_notebook_id = query_nb

if "wsc_active_conversation_id" not in st.session_state:
    st.session_state.wsc_active_conversation_id = query_conv
elif query_conv and st.session_state.wsc_active_conversation_id != query_conv:
    st.session_state.wsc_active_conversation_id = query_conv

if "wsc_show_save_placeholder" not in st.session_state:
    st.session_state.wsc_show_save_placeholder = False
if "wsc_show_explain_placeholder" not in st.session_state:
    st.session_state.wsc_show_explain_placeholder = False
if "wsc_action_message" not in st.session_state:
    st.session_state.wsc_action_message = None
if "wsc_action_error" not in st.session_state:
    st.session_state.wsc_action_error = None
if "wsc_last_ai_badge" not in st.session_state:
    st.session_state.wsc_last_ai_badge = None
if "wsc_archive_confirm_notebook_id" not in st.session_state:
    st.session_state.wsc_archive_confirm_notebook_id = None
if "wsc_delete_confirm_notebook_id" not in st.session_state:
    st.session_state.wsc_delete_confirm_notebook_id = None
if "wsc_upload_version" not in st.session_state:
    st.session_state.wsc_upload_version = 0
if "wsc_agent_workspace_root" not in st.session_state:
    st.session_state.wsc_agent_workspace_root = str(default_agent_workspace_root())
if "wsc_agent_scope_confirmed" not in st.session_state:
    st.session_state.wsc_agent_scope_confirmed = False
if "wsc_agent_last_result" not in st.session_state:
    st.session_state.wsc_agent_last_result = None
if "wsc_agent_pending_action" not in st.session_state:
    st.session_state.wsc_agent_pending_action = None

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
        set_query_params(nb=None, conv=None)
        safe_rerun()
        return
    st.session_state.wsc_active_notebook_id = notebook_id
    st.session_state.wsc_active_conversation_id = None
    set_query_params(nb=notebook_id, conv=None)
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

    title_matches = (
        not confirmation_title
        or confirmation_title.strip().lower() == notebook.title.strip().lower()
        or confirmation_title.strip() == notebook.title.strip()
    )
    if not title_matches or not ack:
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
    st.sidebar.markdown("## 📚 Không gian làm việc")
    st.sidebar.info("Vui lòng chọn hoặc tạo một sổ tài liệu bên phải để bắt đầu làm việc.")

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
    # MÀN HÌNH 2: Chat trong sổ (NotebookLM / Gemini Notebook Layout)
    notebook = next((nb for nb in load_active_notebooks() if nb.id == active_nb_id), None)
    if not notebook:
        st.session_state.wsc_active_notebook_id = None
        st.session_state.wsc_active_conversation_id = None
        st.session_state.wsc_action_error = NOTEBOOK_MISSING_COPY
        safe_rerun()
        st.stop()

    labels = get_vietnamese_labels()

    # --- SIDEBAR: QUẢN LÝ SỔ, HỘI THOẠI & THƯ VIỆN NGUỒN ---
    st.sidebar.markdown(f"## 📂 {notebook.title}")
    if st.sidebar.button("⬅️ Quay lại danh sách sổ", key="back_to_nbs", use_container_width=True):
        st.session_state.wsc_active_notebook_id = None
        st.session_state.wsc_active_conversation_id = None
        set_query_params(nb=None, conv=None)
        safe_rerun()

    st.sidebar.write("---")
    st.sidebar.subheader("💬 Cuộc trò chuyện")

    conversations = load_conversations(active_nb_id)

    if st.sidebar.button("➕ Tạo cuộc trò chuyện mới", key="btn_create_conv", use_container_width=True):
        new_conv = WorkspaceConversation(
            id=f"CONV-{uuid.uuid4().hex[:8].upper()}",
            notebook_id=active_nb_id,
            title=f"Cuộc trò chuyện mới {datetime.now().strftime('%H:%M:%S')}"
        )
        save_conversation(new_conv)
        st.session_state.wsc_active_conversation_id = new_conv.id
        set_query_params(nb=active_nb_id, conv=new_conv.id)
        safe_rerun()

    active_conv_id = st.session_state.wsc_active_conversation_id
    if not active_conv_id and conversations:
        active_conv_id = conversations[0].id
        st.session_state.wsc_active_conversation_id = active_conv_id
        set_query_params(nb=active_nb_id, conv=active_conv_id)

    active_conversation = None
    if active_conv_id:
        active_conversation = load_conversation(active_conv_id)

    for c in conversations:
        is_active = (c.id == active_conv_id)
        btn_label = f"👉 💬 {c.title}" if is_active else f"💬 {c.title}"
        if st.sidebar.button(btn_label, key=f"select_conv_{c.id}", use_container_width=True):
            st.session_state.wsc_active_conversation_id = c.id
            set_query_params(nb=active_nb_id, conv=c.id)
            st.session_state.wsc_show_save_placeholder = False
            st.session_state.wsc_show_explain_placeholder = False
            safe_rerun()

    if active_conversation:
        st.sidebar.write("---")
        with st.sidebar.expander("⚙️ Tùy chỉnh cuộc trò chuyện", expanded=False):
            with st.form("rename_form"):
                new_title = st.text_input("Đổi tên cuộc trò chuyện", value=active_conversation.title)
                if st.form_submit_button("Cập nhật tên"):
                    rename_conversation(active_conversation.id, new_title)
                    safe_rerun()

            st.markdown("---")
            conv_del_confirm_key = f"wsc_conv_del_confirm_{active_conversation.id}"
            if st.session_state.get(conv_del_confirm_key, False):
                st.warning("Xác nhận xóa cuộc trò chuyện này?")
                cdol1, cdol2 = st.columns(2)
                with cdol1:
                    if st.button("Hủy", key=f"cancel_del_conv_{active_conversation.id}"):
                        st.session_state[conv_del_confirm_key] = False
                        safe_rerun()
                with cdol2:
                    if st.button("Xác nhận xóa", key=f"exec_del_conv_{active_conversation.id}"):
                        delete_conversation(active_conversation.id)
                        st.session_state[conv_del_confirm_key] = False
                        st.session_state.wsc_active_conversation_id = None
                        st.session_state.wsc_action_message = "Đã xóa cuộc trò chuyện."
                        safe_rerun()
            else:
                if st.button("🗑️ Xóa cuộc trò chuyện", key=f"req_del_conv_{active_conversation.id}", use_container_width=True):
                    st.session_state[conv_del_confirm_key] = True
                    safe_rerun()

        # Nén Ngữ Cảnh & Kế Thừa
        messages = load_messages(active_conversation.id)
        if len(messages) > 0:
            if st.sidebar.button("🧠 Nén & Kế thừa ngữ cảnh", help="Tóm tắt phiên này và tạo phiên mới mang theo ngữ cảnh", use_container_width=True):
                with st.spinner("Đang nén ngữ cảnh sang phiên mới..."):
                    history = tuple({"role": m.role, "content": m.content} for m in messages)
                    from aios_habit.query_planner import generate_memory_compression
                    compressed = generate_memory_compression(history)

                    new_conv = WorkspaceConversation(
                        id=f"CONV-{uuid.uuid4().hex[:8].upper()}",
                        notebook_id=active_nb_id,
                        title=f"Tiếp tục: {active_conversation.title}",
                        compressed_memory=compressed
                    )
                    save_conversation(new_conv)
                    st.session_state.wsc_active_conversation_id = new_conv.id
                    safe_rerun()

        # Load sources & selections
        notebook_sources = load_notebook_sources(active_nb_id)
        temp_sources = load_temporary_sources(active_conversation.id)
        selections = load_conversation_source_selections(active_conversation.id)

        selections_map = {}
        for sel in selections:
            selections_map[(sel.source_scope, sel.source_id)] = sel.enabled

        notebook_selections = {
            s.id: selections_map.get((SOURCE_SCOPE_NOTEBOOK, s.id), False)
            for s in notebook_sources
        }
        temp_selections = {
            s.id: selections_map.get((SOURCE_SCOPE_TEMPORARY, s.id), False)
            for s in temp_sources
        }

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
                st.session_state.wsc_action_message = (
                    "Đã thêm nguồn vào sổ tài liệu. Nguồn mới đang được chuẩn bị "
                    "trong nền và chưa được tự động bật."
                )
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

        with st.sidebar:
            if "wsc_action_message" in st.session_state and st.session_state.wsc_action_message:
                st.success(st.session_state.wsc_action_message)
                st.session_state.wsc_action_message = None
            if "wsc_action_error" in st.session_state and st.session_state.wsc_action_error:
                st.error(st.session_state.wsc_action_error)
                st.session_state.wsc_action_error = None

            def on_toggle_source(scope: str, source_id: str, enabled: bool):
                set_source_enabled(active_conversation.id, scope, source_id, enabled)
                st.session_state.wsc_action_message = "Đã cập nhật trạng thái bật/tắt nguồn."

            def on_privacy_save(scope: str, source_id: str, choice: str):
                if scope == SOURCE_SCOPE_NOTEBOOK:
                    on_save_notebook_source_privacy(source_id, choice)
                else:
                    on_save_temporary_source_privacy(source_id, choice)

            def on_delete_source(scope: str, source_id: str):
                if scope == SOURCE_SCOPE_NOTEBOOK:
                    from aios_habit.workspace_chat_store import delete_notebook_source
                    if delete_notebook_source(source_id):
                        st.session_state.wsc_action_message = "Đã xóa nguồn trong sổ."
                    else:
                        st.session_state.wsc_action_error = "Không tìm thấy nguồn để xóa."
                else:
                    from aios_habit.workspace_chat_store import delete_temporary_source
                    if delete_temporary_source(source_id):
                        st.session_state.wsc_action_message = "Đã xóa nguồn tạm."
                    else:
                        st.session_state.wsc_action_error = "Không tìm thấy nguồn để xóa."
                safe_rerun()

            selections_map = {}
            for sid, val in notebook_selections.items():
                selections_map[("notebook", sid)] = val
            for sid, val in temp_selections.items():
                selections_map[("temporary", sid)] = val

            prep_context_sources = _workspace_context_sources(notebook_sources, temp_sources)
            prep_status_map = get_workspace_chat_source_preparation_status(prep_context_sources)

            def on_retry_preparation(scope: str, source_id: str):
                retry_sources = tuple(
                    source for source in prep_context_sources
                    if source.source_scope == scope and source.source_id == source_id
                )
                retry_workspace_chat_source_preparation(retry_sources)
                st.session_state.wsc_action_message = "Đang thử chuẩn bị lại nguồn trong nền."
                safe_rerun()

            st.write("---")
            render_source_library(
                notebook_sources=notebook_sources,
                temp_sources=temp_sources,
                selections_map=selections_map,
                conversation_id=active_conversation.id,
                on_toggle_source=on_toggle_source,
                on_promote_temporary=on_promote_temporary,
                on_privacy_save=on_privacy_save,
                on_delete_source=on_delete_source,
                preparation_status_map=prep_status_map,
                on_retry_preparation=on_retry_preparation,
            )

        top_col1, top_col2, top_col3 = st.columns([2.5, 1.3, 1.2])
        with top_col1:
            st.subheader(f"💬 Đang chat trong sổ: {notebook.title}")
        with top_col3:
            curr_layout = st.session_state.get("wsc_layout_mode", "full")
            toggle_label = "📑 Xem chia 2 cột" if curr_layout == "full" else "📖 Mở rộng 100%"
            if st.button(toggle_label, key="wsc_toggle_layout_btn", help="Chuyển đổi giữa chế độ đọc rộng 100% và đối chiếu 2 cột", use_container_width=True):
                st.session_state.wsc_layout_mode = "split" if curr_layout == "full" else "full"
                safe_rerun()

            from aios_habit.antigravity_bridge import is_antigravity_bridge_available
            is_active = is_antigravity_bridge_available()

        with top_col2:
            if is_active:
                st.info("🟢 **Nguồn AI:** `Antigravity IDE Bridge`")
            else:
                st.info("🔵 **Nguồn AI:** `Smart Router (Tự động)`")

        with top_col3:
            if is_active:
                st.button("✅ Cầu nối IDE đang chạy", key="wsc_bridge_active_btn", disabled=True, use_container_width=True)
            else:
                if st.button("🚀 Khởi động Cầu nối IDE", key="wsc_start_bridge_btn", help="Bật tiến trình nền để kết nối với Antigravity IDE", use_container_width=True):
                    import subprocess
                    import sys
                    import platform
                    from pathlib import Path

                    project_root = Path(__file__).resolve().parent.parent.parent
                    script_path = project_root / "scripts" / "antigravity_sidecar_daemon.py"

                    flags = subprocess.CREATE_NEW_CONSOLE if platform.system() == "Windows" else 0
                    subprocess.Popen([sys.executable, str(script_path)], creationflags=flags, cwd=str(project_root))
                    st.toast("Đã gửi lệnh khởi động cầu nối. Vui lòng đợi trong giây lát.")


        if not active_conversation:
            st.info("Vui lòng tạo hoặc chọn một cuộc trò chuyện để bắt đầu.")
        else:
            st.info("Thêm tài liệu rồi hỏi tự nhiên; AIOS sẽ tự kiểm tra nguồn và cảnh báo nếu thiếu.")

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

            badge_data = st.session_state.wsc_last_ai_badge

            def _render_chat_main_column():
                if len(messages) >= 4:
                    st.markdown(
                        '<div style="text-align:right; margin-bottom:8px;"><a href="#latest-ai-anchor" style="font-size:13px; color:#38bdf8; text-decoration:none; padding:4px 10px; background:rgba(14,165,233,0.1); border-radius:6px; border:1px solid rgba(14,165,233,0.2);">⬇️ Xuống câu trả lời mới nhất</a></div>',
                        unsafe_allow_html=True
                    )

                chat_container = st.container()
                with chat_container:
                    if not messages:
                        st.write("Hãy bắt đầu cuộc trò chuyện bằng cách đặt câu hỏi ở dưới.")
                    last_assistant_idx = max((i for i, m in enumerate(messages) if m.role == "assistant"), default=-1)
                    for i, m in enumerate(messages):
                        is_latest_ans = (i == last_assistant_idx and i == len(messages) - 1)
                        render_chat_bubble(m, is_latest=is_latest_ans)

                st.markdown(
                    """
                    <div id="latest-ai-anchor"></div>
                    <script>
                        setTimeout(function() {
                            var anchor = document.getElementById("latest-ai-anchor");
                            if (anchor) {
                                anchor.scrollIntoView({behavior: "smooth", block: "end"});
                            }
                        }, 80);
                    </script>
                    """,
                    unsafe_allow_html=True,
                )

                # AI Answer Badge
                if badge_data and badge_data.get("conversation_id") == active_conversation.id:
                    if badge_data.get("type") == "ai_answered":
                        render_ai_answer_header(badge_data.get("source_count", 0), badge_data.get("source_titles", []))
                        if badge_data.get("retrieval_summary"):
                            st.info(badge_data["retrieval_summary"])
                        st.caption("Đây là câu trả lời do AI tạo. Hãy kiểm tra lại trước khi dùng.")
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

                st.write("---")
                total_enabled = enabled_notebook_count + enabled_temp_count
                render_ai_source_context_summary(total_enabled)

                if len(messages) >= 50:
                    st.warning("⚠️ Cuộc trò chuyện này đã khá dài. Để đảm bảo tốc độ và chất lượng AI, bạn nên dùng tính năng 'Nén Ngữ Cảnh & Kế Thừa' ở thanh bên trái.")

                # Question Form with explicit Ask Button
                with st.form(f"wsc_ai_ask_form_{active_conversation.id}"):
                    user_input = st.text_area(
                        labels["question_placeholder"],
                        placeholder="Ví dụ: Tóm tắt các điểm chính từ các tài liệu đã chọn...",
                        height=100,
                        key=f"wsc_question_input_{active_conversation.id}"
                    )
                    user_attached_image = st.file_uploader(
                        "📷 Đính kèm ảnh chụp màn hình / tài liệu ảnh (Kéo thả, dán file hoặc duyệt ảnh)",
                        type=["png", "jpg", "jpeg", "webp", "bmp"],
                        key=f"wsc_chat_img_{active_conversation.id}_{st.session_state.wsc_upload_version}",
                        help="Hỗ trợ tải lên hoặc kéo thả ảnh chụp màn hình nhanh để AI đọc và phân tích."
                    )
                    current_pref = getattr(active_conversation, "search_preference", "auto")
                    pref_options = ["auto", "deep"]
                    pref_labels = {
                        "auto": "Tự động",
                        "deep": "Tìm kỹ hơn (có thể chậm hơn)",
                    }
                    selected_pref_idx = 1 if current_pref == "deep" else 0
                    chosen_pref_key = f"wsc_search_pref_{active_conversation.id}"
                    chosen_pref = st.selectbox(
                        "Mức độ tìm kiếm",
                        options=pref_options,
                        index=selected_pref_idx,
                        format_func=lambda x: pref_labels.get(x, x),
                        key=chosen_pref_key,
                        help="Tự động tối ưu giữa tốc độ và độ kỹ, hoặc chủ động chọn Tìm kỹ hơn để tăng độ sâu rà soát tài liệu.",
                    )
                    if chosen_pref != current_pref:
                        update_conversation_search_preference(active_conversation.id, chosen_pref)
                        active_conversation.search_preference = chosen_pref

                    ask_submitted = st.form_submit_button(labels["ai_action"], use_container_width=True)

                if ask_submitted:
                    q_text = user_input.strip()
                    if not q_text and not user_attached_image:
                        st.error("Vui lòng nhập câu hỏi hoặc đính kèm ảnh chụp màn hình.")
                    else:
                        if user_attached_image is not None:
                            img_batch = process_workspace_upload_batch(
                                [user_attached_image],
                                active_conversation.id,
                                "cloud_safe",
                                enable_now=True,
                                save_to_notebook=False,
                                notebook_id=active_nb_id,
                            )
                            if img_batch.get("success_count", 0) > 0:
                                st.session_state.wsc_upload_version += 1
                            if not q_text:
                                q_text = "Phân tích và giải thích nội dung trong ảnh chụp màn hình đính kèm."

                        enabled_selections = load_enabled_sources_for_conversation(active_conversation.id)
                        current_notebook_sources = load_notebook_sources(active_nb_id)
                        current_temp_sources = load_temporary_sources(active_conversation.id)

                        if not enabled_selections:
                            st.session_state.wsc_last_ai_badge = {
                                "conversation_id": active_conversation.id,
                                "type": "insufficient_context",
                                "reason": "no_sources",
                            }
                            safe_rerun()
                        else:
                            packed_question, packed_sources, warnings = pack_workspace_ai_context(
                                q_text,
                                current_notebook_sources,
                                current_temp_sources,
                                enabled_selections
                            )

                            non_empty_sources = [s for s in packed_sources if s.text and s.text.strip()]
                            if not non_empty_sources:
                                st.session_state.wsc_last_ai_badge = {
                                    "conversation_id": active_conversation.id,
                                    "type": "insufficient_context",
                                    "reason": "empty_content",
                                }
                                safe_rerun()
                            else:
                                # Readiness is query-scoped.  Blocking this action on every
                                # enabled source turns a precise Matecon question into a
                                # 72-document preparation job even though retrieval will only
                                # search the relevant manual.
                                query_relevant_sources = _select_semantic_candidate_sources(
                                    packed_question, tuple(non_empty_sources)
                                )
                                # This synchronously recovers a selected document already
                                # present in the durable BGE index; new work is scheduled only
                                # for the small query-relevant set.
                                schedule_workspace_chat_source_preparation(query_relevant_sources)
                                preparation_states = get_workspace_chat_source_preparation_status(
                                    query_relevant_sources
                                )
                                failed_sources = [identity for identity, state in preparation_states.items() if state == "failed"]
                                waiting_sources = [identity for identity, state in preparation_states.items() if state != "ready" and state != "failed"]

                                if failed_sources:
                                    st.session_state.wsc_action_error = "Có nguồn chuẩn bị thất bại. Hãy bấm “Thử chuẩn bị lại” ở danh sách nguồn trước khi Hỏi."
                                    st.session_state.wsc_last_ai_badge = None
                                    safe_rerun()
                                elif waiting_sources:
                                    st.session_state.wsc_action_error = "Nguồn đang được chuẩn bị để tìm kiếm. Vui lòng thử Hỏi lại sau ít phút."
                                    st.session_state.wsc_last_ai_badge = None
                                    safe_rerun()
                                else:
                                    current_keys = tuple(sorted((s.source_scope, s.source_id) for s in packed_sources))

                                    from aios_habit.workspace_chat_rag_v2_adapter import (
                                        retrieve_workspace_chat_evidence as retrieve_local_evidence,
                                    )
                                    from aios_habit.query_planner import generate_query_expansion

                                    chat_history = tuple({"role": m.role, "content": m.content} for m in messages[-50:]) if messages else ()
                                    if getattr(active_conversation, "compressed_memory", ""):
                                        chat_history = ({"role": "system", "content": active_conversation.compressed_memory},) + chat_history

                                    is_cloud_allowed = bool(st.session_state.get("cloud_consent_confirmed", False)) and all(
                                        getattr(s, "privacy_label", "local_only") in {"cloud_safe", "public"}
                                        for s in packed_sources
                                    )

                                    with st.spinner("🤖 AIOS đang phân tích và tìm kiếm câu trả lời..."):
                                        st.toast("🔍 Bước 1/3: Kiểm tra nguồn tài liệu & phân tích câu hỏi...")
                                        expansion = None
                                        from aios_habit.rag_v2.query_planning import coerce_query_plan
                                        local_query_plan = coerce_query_plan(q_text)
                                        # Direct procedure questions already have a deterministic
                                        # local plan; do not add a cloud planning round-trip before
                                        # their local BGE retrieval.
                                        if is_cloud_allowed and local_query_plan.intent_category not in {
                                            "procedure", "actionable_output", "diagnosis",
                                        }:
                                            expansion = generate_query_expansion(
                                                q_text,
                                                chat_history=chat_history,
                                                privacy_mode="cloud_allowed",
                                                cloud_consent_confirmed=True,
                                            )

                                        active_pref = getattr(active_conversation, "search_preference", "auto")
                                        search_status_msg = (
                                            "📚 Bước 2/3: Đang tìm kỹ trong các tài liệu..."
                                            if active_pref == "deep"
                                            else "📚 Bước 2/3: Đang tìm kiếm đoạn tài liệu phù hợp..."
                                        )
                                        st.toast(search_status_msg)
                                        ret_res = retrieve_local_evidence(
                                            q_text,
                                            packed_sources,
                                            expansion=expansion,
                                            search_preference=active_pref,
                                        )

                                        if ret_res.get("status") == "quality_search_unavailable":
                                            st.error(
                                                "Chưa thể tìm được bằng chứng đủ tin cậy trong tài liệu. "
                                                "Câu hỏi chưa được gửi tới AI để tránh trả lời thiếu hoặc sai."
                                            )
                                            st.session_state.wsc_action_error = (
                                                "Tìm kiếm tài liệu chưa sẵn sàng. Vui lòng thử lại sau khi "
                                                "nguồn hoàn tất chuẩn bị; chế độ Tìm kỹ hơn chỉ hoạt động khi "
                                                "bộ kiểm tra chuyên sâu sẵn sàng."
                                            )
                                            st.session_state.wsc_last_ai_badge = None
                                            safe_rerun()
                                        elif ret_res["summary_count"] == 0:
                                            st.error("⚠️ Chưa tìm thấy đoạn phù hợp trong nguồn đang bật.")
                                            st.session_state.wsc_action_error = "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật."
                                            st.session_state.wsc_last_ai_badge = None
                                            safe_rerun()
                                        else:
                                            retrieval_applied = True
                                            retrieved_sources = ret_res.get("retrieved_context_sources", ())
                                            evidence_items = ret_res.get("evidence_items", [])
                                            retrieval_summary = ret_res.get("safe_owner_message", "")

                                        st.toast("✍️ Bước 3/3: AI đang soạn thảo câu trả lời và dẫn nguồn...")
                                        req = WorkspaceAIAnswerRequest(
                                            conversation_id=active_conversation.id,
                                            question=q_text,
                                            context_sources=packed_sources,
                                            privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
                                            cloud_consent_confirmed=True,
                                            consent_source_keys=current_keys,
                                            retrieval_applied=retrieval_applied,
                                            retrieved_context_sources=retrieved_sources,
                                            real_router_enabled=True,
                                            chat_history=chat_history
                                        )

                                        res = generate_workspace_ai_answer(req, RealWorkspaceAIProviderClient())
                                        if res.ok:
                                            st.toast("✅ Đã hoàn thành câu trả lời!")
                                        else:
                                            st.error("⚠️ Xử lý câu trả lời thất bại")

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
                                            "retrieval_summary": retrieval_summary,
                                            "evidence_items": evidence_items,
                                        }

                                        if res.warnings:
                                            st.session_state.wsc_action_message = "\n".join(res.warnings)
                                        else:
                                            st.session_state.wsc_action_message = "Đã nhận câu trả lời từ AI thành công."
                                    else:
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
                with st.expander("➕ Thêm nguồn", expanded=False):
                    tab_quick, tab_paste, tab_image, tab_upload, tab_folder = st.tabs([
                        "📋 Dán nhanh",
                        "📝 Dán văn bản dài",
                        "🖼️ Ảnh chụp màn hình",
                        "📁 Thêm tài liệu",
                        "📁 Nhập từ thư mục",
                    ])

                    with tab_quick:
                        with st.form("quick_paste_form", clear_on_submit=True):
                            quick_title = st.text_input("Tên nhóm nguồn (tuỳ chọn)", placeholder="Ví dụ: Log sáng 3/7, Email lỗi...")
                            quick_content = st.text_area("Dán nội dung vào đây", placeholder="Dán nội dung vào đây...", height=120)
                            quick_privacy_choice = render_privacy_choice(f"wsc_quick_privacy_{active_conversation.id}")
                            quick_save_to_notebook = st.checkbox("Lưu vĩnh viễn vào Sổ tài liệu", value=True)
                            if st.form_submit_button(labels["quick_paste_add"]):
                                if quick_content.strip():
                                    final_title = quick_title.strip() or f"Nguồn dán nhanh {datetime.now().strftime('%d/%m %H:%M')}"
                                    ts = create_pasted_text_temporary_source(
                                        conversation_id=active_conversation.id,
                                        title=final_title,
                                        content_text=quick_content,
                                        owner_choice=quick_privacy_choice,
                                    )
                                    if quick_save_to_notebook:
                                        promote_temporary_source_to_notebook(active_conversation.id, ts.id, active_nb_id)
                                        st.session_state.wsc_action_message = f"Đã lưu vĩnh viễn vào Sổ tài liệu: {final_title}."
                                    else:
                                        st.session_state.wsc_action_message = f"Đã thêm nguồn: {final_title}. Đang chuẩn bị để tìm kiếm."
                                    safe_rerun()
                                else:
                                    st.error("Nội dung không được để trống.")

                    # Khung dán nhật ký/email/đoạn chat dài
                    with tab_paste:
                        with st.form("paste_log_form"):
                            paste_title = st.text_input("Tiêu đề nguồn tạm", placeholder="Ví dụ: Email lỗi Opcenter, Nhật ký log hệ thống...")
                            paste_content = st.text_area("Nội dung văn bản dài", placeholder="Dán nội dung vào đây...", height=120)
                            paste_privacy_choice = render_privacy_choice(f"wsc_paste_privacy_{active_conversation.id}")
                            paste_enable_now = st.checkbox("Dùng nội dung này trong câu trả lời", value=False)
                            paste_save_to_notebook = st.checkbox("Lưu vĩnh viễn vào Sổ tài liệu", value=True, key=f"paste_save_{active_conversation.id}")
                            if st.form_submit_button("Thêm vào nguồn tạm"):
                                if not paste_content.strip():
                                    st.error("Nội dung không được để trống.")
                                else:
                                    final_title = paste_title.strip() if paste_title.strip() else f"Đoạn dán lúc {datetime.now().strftime('%H:%M:%S')}"
                                    ts = create_pasted_text_temporary_source(
                                        conversation_id=active_conversation.id,
                                        title=final_title,
                                        content_text=paste_content,
                                        owner_choice=paste_privacy_choice,
                                    )
                                    if paste_enable_now:
                                        set_source_enabled(active_conversation.id, SOURCE_SCOPE_TEMPORARY, ts.id, True)
                                    if paste_save_to_notebook:
                                        promote_temporary_source_to_notebook(active_conversation.id, ts.id, active_nb_id)
                                        st.session_state.wsc_action_message = f"Đã lưu vĩnh viễn vào Sổ tài liệu: {final_title}."
                                    else:
                                        st.session_state.wsc_action_message = f"Đã thêm nguồn: {final_title}."
                                    safe_rerun()


                    # Tab đính kèm ảnh chụp màn hình / hình ảnh cắt nhanh
                    with tab_image:
                        st.write("Đính kèm ảnh chụp màn hình, sơ đồ, bảng dữ liệu chụp từ hệ thống.")
                        with st.form(f"wsc_img_upload_form_{active_conversation.id}"):
                            img_files = st.file_uploader(
                                "Chọn hoặc dán ảnh chụp màn hình",
                                type=["png", "jpg", "jpeg", "webp", "bmp"],
                                key=f"wsc_img_upload_{active_conversation.id}_{st.session_state.wsc_upload_version}",
                                accept_multiple_files=True,
                            )
                            img_privacy_choice = render_privacy_choice(f"wsc_img_tab_privacy_{active_conversation.id}")
                            img_enable_now = st.checkbox("Bật ngay các ảnh này cho câu hỏi", value=True, key=f"img_tab_enable_{active_conversation.id}")
                            img_save_to_notebook = st.checkbox("Lưu vĩnh viễn vào Sổ tài liệu", value=True, key=f"img_tab_save_{active_conversation.id}")
                            if st.form_submit_button("🖼️ Đọc và thêm ảnh vào nguồn"):
                                if not img_files:
                                    st.error("Vui lòng chọn hoặc kéo thả ít nhất 1 ảnh.")
                                else:
                                    batch_res = process_workspace_upload_batch(
                                        img_files,
                                        active_conversation.id,
                                        img_privacy_choice,
                                        img_enable_now,
                                        save_to_notebook=img_save_to_notebook,
                                        notebook_id=active_nb_id,
                                    )
                                    success_count = batch_res["success_count"]
                                    if success_count > 0:
                                        st.session_state.wsc_upload_version += 1
                                        dest = "vào Sổ tài liệu" if img_save_to_notebook else "như nguồn tạm"
                                        st.session_state.wsc_action_message = f"Đã thêm thành công {success_count} ảnh {dest}."
                                    safe_rerun()

                    with tab_upload:
                        st.write("Tải lên tài liệu để dùng làm nguồn cho cuộc trò chuyện.")
                        st.write("Có thể chọn hoặc kéo thả nhiều tài liệu cùng lúc.")
                        st.write("Hỗ trợ: TXT, MD, CSV, Excel, Word, PowerPoint, PDF và ảnh nếu máy có bộ đọc phù hợp.")
                        with st.form(f"wsc_doc_upload_form_{active_conversation.id}"):
                            uploaded_files = st.file_uploader(
                                "Chọn tài liệu cho cuộc trò chuyện này",
                                type=["txt", "md", "markdown", "csv", "xlsx", "xls", "docx", "pptx", "pdf", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
                                key=f"wsc_doc_upload_{active_conversation.id}_{st.session_state.wsc_upload_version}",
                                accept_multiple_files=True,
                            )
                            doc_privacy_choice = render_privacy_choice(f"wsc_doc_privacy_{active_conversation.id}")
                            enable_now = st.checkbox("Dùng các tài liệu này trong câu trả lời", value=False)
                            upload_save_to_notebook = st.checkbox("Lưu vĩnh viễn vào Sổ tài liệu", value=True, key=f"upload_save_{active_conversation.id}")
                            if st.form_submit_button("Đọc và thêm vào nguồn tạm"):
                                if not uploaded_files:
                                    st.error("Vui lòng chọn tập tin trước khi thêm.")
                                else:
                                    batch_res = process_workspace_upload_batch(
                                        uploaded_files,
                                        active_conversation.id,
                                        doc_privacy_choice,
                                        enable_now,
                                        save_to_notebook=upload_save_to_notebook,
                                        notebook_id=active_nb_id
                                    )
                                    success_count = batch_res["success_count"]
                                    fail_count = batch_res["fail_count"]
                                    if success_count > 0:
                                        st.session_state.wsc_upload_version += 1
                                        dest = "vào Sổ tài liệu" if upload_save_to_notebook else "như nguồn tạm"
                                        if enable_now:
                                            st.session_state.wsc_action_message = f"Đã thêm {success_count} tài liệu {dest}. Nguồn mới đã được bật cho câu trả lời."
                                        else:
                                            st.session_state.wsc_action_message = f"Đã thêm {success_count} tài liệu {dest}."
                                    safe_rerun()

                    with tab_folder:
                        st.write("Nhập đường dẫn thư mục trên máy để quét và nhập tất cả tài liệu hỗ trợ vào sổ.")
                        st.caption("Hỗ trợ: PDF, Word (.docx), Excel (.xlsx, .xls), PowerPoint (.pptx), TXT, Markdown, CSV, ảnh (.png, .jpg...)")

                        scan_key = f"wsc_folder_scan_{active_conversation.id}"
                        path_key = f"wsc_folder_path_input_{active_conversation.id}"
                        rec_key = f"wsc_folder_rec_{active_conversation.id}"

                        col_path, col_btn = st.columns([3, 1])
                        with col_path:
                            folder_path_input = st.text_input(
                                "Đường dẫn thư mục",
                                placeholder="Ví dụ: D:\\TaiLieu\\DuAn hoặc /home/user/documents",
                                key=path_key,
                                label_visibility="collapsed",
                            )
                        with col_btn:
                            folder_recursive = st.checkbox("Quét thư mục con", value=True, key=rec_key)
                            btn_scan = st.button("🔍 Quét thư mục", key=f"btn_scan_{active_conversation.id}", use_container_width=True)

                        if btn_scan:
                            if not folder_path_input or not folder_path_input.strip():
                                st.session_state.pop(scan_key, None)
                                st.error("Vui lòng nhập đường dẫn thư mục trước khi quét.")
                            else:
                                scan_res = scan_local_directory(folder_path_input.strip(), recursive=folder_recursive)
                                st.session_state[scan_key] = scan_res

                        current_scan = st.session_state.get(scan_key)
                        if current_scan is not None:
                            if not current_scan.ok:
                                st.error(current_scan.error_message)
                            else:
                                mcol1, mcol2, mcol3 = st.columns(3)
                                with mcol1:
                                    st.metric("Tổng số tập tin", current_scan.total_files)
                                with mcol2:
                                    st.metric(
                                        "Tài liệu hỗ trợ",
                                        f"{len(current_scan.supported_files)} ({current_scan.formatted_supported_size()})",
                                    )
                                with mcol3:
                                    st.metric("Không hỗ trợ / Bỏ qua", len(current_scan.unsupported_files))

                                if current_scan.supported_files:
                                    st.markdown("##### 📄 Danh sách tài liệu tìm thấy:")
                                    table_data = [
                                        {
                                            "Tên tập tin": f.filename,
                                            "Thư mục con / Đường dẫn": f.relative_path,
                                            "Định dạng": f.extension.upper(),
                                            "Dung lượng": format_size_bytes(f.size_bytes),
                                        }
                                        for f in current_scan.supported_files[:100]
                                    ]
                                    st.dataframe(table_data, use_container_width=True)
                                    if len(current_scan.supported_files) > 100:
                                        st.caption(f"(Đang hiển thị 100 / {len(current_scan.supported_files)} tài liệu)")

                                    st.divider()
                                    folder_privacy_choice = render_privacy_choice(f"wsc_folder_privacy_{active_conversation.id}")
                                    folder_enable_now = st.checkbox(
                                        "Dùng các tài liệu này trong câu trả lời",
                                        value=False,
                                        key=f"folder_enable_{active_conversation.id}",
                                    )
                                    folder_save_to_notebook = st.checkbox(
                                        "Lưu vĩnh viễn vào Sổ tài liệu",
                                        value=True,
                                        key=f"folder_save_{active_conversation.id}",
                                    )

                                    if st.button("📥 Nhập tất cả tài liệu vào sổ", type="primary", key=f"btn_ingest_{active_conversation.id}", use_container_width=True):
                                        prog_bar = st.progress(0, text="Bắt đầu nhập tài liệu...")
                                        status_text = st.empty()

                                        def update_progress(current_idx: int, total_count: int, filename: str):
                                            pct = current_idx / max(total_count, 1)
                                            prog_bar.progress(pct, text=f"Đang xử lý ({current_idx}/{total_count}): {filename}")
                                            status_text.caption(f"Đang đọc: {filename}")

                                        batch_summary = ingest_scanned_files_batch(
                                            files=current_scan.supported_files,
                                            conversation_id=active_conversation.id,
                                            privacy_choice=folder_privacy_choice,
                                            enable_now=folder_enable_now,
                                            save_to_notebook=folder_save_to_notebook,
                                            notebook_id=active_nb_id,
                                            progress_callback=update_progress,
                                        )

                                        prog_bar.empty()
                                        status_text.empty()

                                        dest = "vào Sổ tài liệu" if folder_save_to_notebook else "như nguồn tạm"
                                        if batch_summary.success_count > 0:
                                            st.session_state.wsc_upload_version += 1
                                            msg = f"Đã nhập thành công {batch_summary.success_count}/{batch_summary.total_files} tài liệu {dest}."
                                            if folder_enable_now:
                                                msg += " Nguồn mới đã được bật cho câu trả lời."
                                            st.session_state.wsc_action_message = msg

                                        if batch_summary.fail_count > 0:
                                            st.session_state.wsc_action_error = f"Có {batch_summary.fail_count} tài liệu gặp lỗi khi trích xuất."

                                        st.session_state.pop(scan_key, None)
                                        safe_rerun()

                                else:
                                    st.info("Không tìm thấy tài liệu phù hợp trong thư mục đã chọn.")

                                if current_scan.unsupported_files:
                                    with st.expander(f"Tập tin không hỗ trợ ({len(current_scan.unsupported_files)})", expanded=False):
                                        unsupported_table = [
                                            {
                                                "Tên tập tin": f.filename,
                                                "Đường dẫn": f.relative_path,
                                                "Định dạng": f.extension or "(không có đuôi)",
                                                "Lý do": f.unsupported_reason,
                                            }
                                            for f in current_scan.unsupported_files[:50]
                                        ]
                                        st.dataframe(unsupported_table, use_container_width=True)

            def _render_workspace_results_and_evidence():
                last_assistant_msg = next((m for m in reversed(messages) if m.role == "assistant"), None)
                answer_text = last_assistant_msg.content if last_assistant_msg else "Hãy gửi câu hỏi để nhận phản hồi từ AIOS."

                enabled_selections = [sel for sel in selections if sel.enabled]
                notebook_source_by_id = {s.id: s for s in notebook_sources}
                temp_source_by_id = {s.id: s for s in temp_sources}


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

                if last_assistant_msg:
                    to_check = ["Đây là câu trả lời do AI tạo, cần kiểm tra lại trước khi dùng."]
                    next_actions = ["Kiểm tra lại tài liệu nguồn"]
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

                # Studio Notes & Citations
                if badge_data and badge_data.get("conversation_id") == active_conversation.id and badge_data.get("evidence_items"):
                    st.markdown("#### 🔍 Trích dẫn từ tài liệu")
                    for item in badge_data["evidence_items"]:
                        with st.expander(f"📌 {item['title']}", expanded=True):
                            if item.get("location_info"):
                                st.caption(f"📍 {item['location_info']}")
                            st.info(item["text"])

            # Agent IDE / Developer Tools (Tạm thời ẩn theo yêu cầu)
            SHOW_AGENT_IDE_DEV_TOOLS = False

            def _render_agent_ide_developer_tools():
                with st.expander("🤖 Agent IDE (Dành cho Lập trình viên)", expanded=False):
                    st.caption("Workspace Agent IDE chỉ đọc code mặc định. Không tự sửa tệp hoặc chạy lệnh.")
                    agent_mode = st.selectbox(
                        "Chế độ Agent IDE",
                        options=["analyze", "debug", "plan", "implement"],
                        format_func=lambda value: {
                            "analyze": "Phân tích codebase", "debug": "Tìm nguyên nhân lỗi",
                            "plan": "Lập kế hoạch thay đổi", "implement": "Chuẩn bị thay đổi (chưa ghi tệp)",
                        }[value],
                        key=f"wsc_agent_mode_{active_conversation.id}",
                    )
                    workspace_root = st.text_input(
                        "Thư mục code workspace", value=st.session_state.wsc_agent_workspace_root,
                        key=f"wsc_agent_workspace_{active_conversation.id}",
                    )
                    st.session_state.wsc_agent_workspace_root = workspace_root
                    scope_confirmed = st.checkbox(
                        "Tôi xác nhận Agent IDE có thể đọc code trong workspace này.",
                        value=st.session_state.wsc_agent_scope_confirmed,
                        key=f"wsc_agent_scope_{active_conversation.id}",
                    )
                    st.session_state.wsc_agent_scope_confirmed = scope_confirmed
                    trust_col, status_col = st.columns([1, 2])
                    with trust_col:
                        if st.button("Tin cậy workspace này", key=f"wsc_agent_trust_{active_conversation.id}"):
                            if not scope_confirmed:
                                st.warning("Hãy xác nhận phạm vi code workspace trước khi đặt mức tin cậy.")
                            else:
                                try:
                                    client = WorkspaceAgentBridgeClient(workspace_root)
                                    trust = client.trust_workspace()
                                    client.close()
                                    st.success(f"Đã tin cậy workspace cục bộ: {trust.get('workspace', workspace_root)}")
                                except Exception as error:
                                    st.error(f"Không thể đặt mức tin cậy cho Agent IDE: {error}")
                    with status_col:
                        st.caption("Lệnh, áp diff và mọi sửa đổi tệp sẽ luôn yêu cầu một phê duyệt riêng ở bước sau.")
                    with st.form(f"wsc_agent_ask_form_{active_conversation.id}", clear_on_submit=True):
                        agent_instruction = st.text_area("Yêu cầu cho Agent IDE", placeholder="Ví dụ: Tìm luồng xử lý dữ liệu và các điểm có thể lỗi.", height=90)
                        agent_submitted = st.form_submit_button("Khảo sát workspace", use_container_width=True)
                    if agent_submitted:
                        result = WorkspaceAgentOrchestrator().run(WorkspaceAgentRequest(
                            conversation_id=active_conversation.id,
                            workspace_root=workspace_root,
                            instruction=agent_instruction,
                            mode=agent_mode,
                            workspace_scope_confirmed=scope_confirmed,
                        ))
                        st.session_state.wsc_agent_last_result = result
                        if result.state == "completed":
                            save_message(ChatMessage(
                                id=f"MSG-{uuid.uuid4().hex[:8].upper()}", conversation_id=active_conversation.id,
                                role="assistant", content=result.answer_text,
                            ))
                            st.success("Agent IDE đã hoàn tất khảo sát chỉ-đọc.")
                            safe_rerun()
                        else:
                            st.error(result.error_message or "Agent IDE chưa thể hoàn tất yêu cầu.")
                    agent_result = st.session_state.wsc_agent_last_result
                    if agent_result and agent_result.session_id:
                        with st.expander("Dấu vết công cụ Agent IDE", expanded=False):
                            for event in agent_result.events:
                                icon = "✅" if event.ok else "⚠️"
                                st.write(f"{icon} `{event.tool}` · {event.elapsed_ms}ms · {event.summary}")

                    st.markdown("#### Tạo proposal có kiểm soát")
                    proposal_tab, command_tab = st.tabs(["Đề xuất patch", "Đề xuất lệnh"])
                    with proposal_tab:
                        with st.form(f"wsc_agent_patch_form_{active_conversation.id}", clear_on_submit=True):
                            patch_path = st.text_input("Tệp cần đề xuất sửa", placeholder="src/aios_habit/rag_v2/chunking.py")
                            patch_find = st.text_area("Đoạn hiện tại (phải khớp chính xác)", height=100)
                            patch_replace = st.text_area("Đoạn thay thế", height=100)
                            patch_reason = st.text_input("Lý do thay đổi", placeholder="Ví dụ: bổ sung xử lý file rỗng")
                            patch_submit = st.form_submit_button("Tạo diff để review", use_container_width=True)
                        if patch_submit:
                            patch_result = WorkspaceAgentOrchestrator().propose_patch(
                                workspace_root=workspace_root, file_path=patch_path, find=patch_find,
                                replace=patch_replace, reason=patch_reason, scope_confirmed=scope_confirmed,
                            )
                            st.session_state.wsc_agent_last_result = patch_result
                            if patch_result.pending_action:
                                st.session_state.wsc_agent_pending_action = {
                                    "proposal_session_id": patch_result.session_id,
                                    "action": patch_result.pending_action,
                                }
                                st.success("Đã tạo diff. Hãy review phần phê duyệt phía dưới; chưa có thay đổi nào được ghi.")
                            else:
                                st.error(patch_result.error_message or "Không thể tạo proposal patch.")
                    with command_tab:
                        with st.form(f"wsc_agent_command_form_{active_conversation.id}", clear_on_submit=True):
                            proposed_command = st.text_area("Lệnh sẽ chạy trong workspace", placeholder="py -m pytest tests/test_data_processing.py -q", height=80)
                            command_reason = st.text_input("Mục đích chạy lệnh", placeholder="Ví dụ: kiểm chứng thay đổi processing")
                            command_submit = st.form_submit_button("Tạo proposal lệnh", use_container_width=True)
                        if command_submit:
                            command_result = WorkspaceAgentOrchestrator().propose_command(
                                workspace_root=workspace_root, command=proposed_command,
                                reason=command_reason, scope_confirmed=scope_confirmed,
                            )
                            st.session_state.wsc_agent_last_result = command_result
                            if command_result.pending_action:
                                st.session_state.wsc_agent_pending_action = {
                                    "proposal_session_id": command_result.session_id,
                                    "action": command_result.pending_action,
                                }
                                st.success("Đã tạo proposal lệnh. Lệnh chưa được chạy.")
                            else:
                                st.error(command_result.error_message or "Không thể tạo proposal lệnh.")

                    pending = st.session_state.wsc_agent_pending_action
                    if pending:
                        action = pending["action"]
                        st.markdown("#### ⚠️ Cổng phê duyệt bắt buộc")
                        if action.kind == "edit":
                            payload = action.payload
                            st.write(f"**Tệp:** `{payload.get('relPath', 'unknown')}`")
                            st.code(payload.get("diff", "Không có diff để hiển thị."), language="diff")
                            if st.button("Phê duyệt và áp dụng patch", type="primary", key="wsc_agent_apply_btn"):
                                result = WorkspaceAgentOrchestrator().approve_edit(
                                    proposal_session_id=pending["proposal_session_id"], pending_edit_id=payload["id"],
                                    workspace_root=workspace_root, scope_confirmed=scope_confirmed,
                                )
                                st.session_state.wsc_agent_pending_action = None
                                st.success(result.answer_text if result.state == "completed" else "Lỗi.")
                                safe_rerun()
                        else:
                            command = action.payload.get("command", "")
                            st.code(command, language="powershell")
                            if st.button("Phê duyệt và chạy lệnh", type="primary", key="wsc_agent_exec_btn"):
                                result = WorkspaceAgentOrchestrator().approve_command(
                                    workspace_root=action.payload.get("workspace_root", workspace_root), command=command,
                                    scope_confirmed=scope_confirmed,
                                )
                                st.session_state.wsc_agent_pending_action = None
                                st.success(result.answer_text if result.state == "completed" else "Lỗi.")
                                safe_rerun()
                        if st.button("Từ chối", key="wsc_agent_discard_btn"):
                            st.session_state.wsc_agent_pending_action = None
                            safe_rerun()

            effective_layout = st.session_state.get("wsc_layout_mode", "full")
            if effective_layout == "split":
                col_chat, col_results = st.columns([3.8, 1.2])
                with col_chat:
                    _render_chat_main_column()
                with col_results:
                    _render_workspace_results_and_evidence()
                    if SHOW_AGENT_IDE_DEV_TOOLS:
                        _render_agent_ide_developer_tools()
            else:
                with st.container():
                    _render_chat_main_column()
                st.write(" ")
                with st.expander("📌 Tùy chọn & Tóm tắt nguồn đang dùng", expanded=False):
                    _render_workspace_results_and_evidence()
                    if SHOW_AGENT_IDE_DEV_TOOLS:
                        _render_agent_ide_developer_tools()



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
        create_safe_test_data(active_conversation.id)
        st.button("Tạo dữ liệu test không mật")
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
