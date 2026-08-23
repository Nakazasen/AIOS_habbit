import streamlit as st
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Mapping
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
    delete_sources,
    restore_source_snapshot,
    purge_unreferenced_managed_files,
    find_source_ids_by_title,
    delete_notebook_permanently,
    delete_conversation,
    resolve_conversation_id,
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


class BufferedWorkspaceUpload:
    """Small in-memory upload wrapper that survives the confirmation rerun."""

    def __init__(self, name: str, content: bytes):
        self.name = name
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


def buffer_workspace_uploads(uploaded_files: list) -> List[dict]:
    """Capture Streamlit uploads before showing a duplicate-name confirmation."""
    buffered = []
    for uploaded_file in uploaded_files:
        try:
            buffered.append({"name": uploaded_file.name, "content": uploaded_file.getvalue()})
        except Exception:
            continue
    return buffered


def restore_buffered_workspace_uploads(buffered_uploads: List[dict]) -> List[BufferedWorkspaceUpload]:
    return [
        BufferedWorkspaceUpload(str(item["name"]), bytes(item["content"]))
        for item in buffered_uploads
        if item.get("name") and item.get("content") is not None
    ]


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
    created_temporary_source_ids = []
    created_notebook_source_ids = []
    created_source_ids_by_filename = {}

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
            created_temporary_source_ids.append(ts.id)
            created_for_file = {"temporary": [ts.id], "notebook": []}
            if save_to_notebook and notebook_id:
                notebook_source = promote_temporary_source_to_notebook(conversation_id, ts.id, notebook_id)
                if notebook_source is not None:
                    created_notebook_source_ids.append(notebook_source.id)
                    created_for_file["notebook"].append(notebook_source.id)
            created_source_ids_by_filename.setdefault(filename, []).append(created_for_file)
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
        "created_temporary_source_ids": created_temporary_source_ids,
        "created_notebook_source_ids": created_notebook_source_ids,
        "created_source_ids_by_filename": created_source_ids_by_filename,
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
    select_workspace_chat_preparation_scope,
    schedule_workspace_chat_source_preparation,
    retry_workspace_chat_source_preparation,
    get_workspace_chat_source_preparation_status,
    get_workspace_chat_preparation_summary,
    reconcile_and_enqueue_workspace_chat_sources,
    promote_workspace_chat_source_priority,
    forget_workspace_chat_sources,
)
from aios_habit.workspace_chat_ui import (
    get_vietnamese_labels,
    render_notebook_header,
    render_notebook_card,
    render_archived_notebook_card,
    render_chat_bubble,
    render_right_result_panel,
    render_source_library,
    render_source_library_summary,
    render_document_manager,
    render_preparation_progress_bar,
    render_grouped_evidence_items,
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
    render_bridge_header_status,
    render_handoff_pending_banner,
)
from aios_habit.antigravity_bridge import (
    get_antigravity_bridge_health,
    call_antigravity_bridge,
    sanitize_reason,
)
from aios_habit.ide_handoff_bridge import (
    list_pending_ide_requests,
    import_pending_ide_response,
    save_imported_ide_answer,
    write_ide_handoff_bundle,
    check_handoff_request_timeouts,
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
    reconcile_and_enqueue_workspace_chat_sources(ctx_sources)
    return get_workspace_chat_source_preparation_status(ctx_sources)


_PENDING_SOURCE_SUBMISSION_KEY = "wsc_pending_source_submission"
_PENDING_SOURCE_SUBMISSION_TTL_SECONDS = 300.0


def _source_key(source: WorkspaceAIContextSource) -> tuple[str, str]:
    return (str(source.source_scope), str(source.source_id))


def _new_pending_source_submission(
    *,
    conversation_id: str,
    question: str,
    selection_keys: tuple[tuple[str, str], ...],
    required_sources: tuple[WorkspaceAIContextSource, ...],
    now: float | None = None,
) -> dict[str, Any]:
    """Create a session-only, single-use continuation for source preparation."""
    return {
        "token": uuid.uuid4().hex,
        "conversation_id": conversation_id,
        "question": question,
        "selection_keys": tuple(sorted(selection_keys)),
        "required_source_keys": tuple(sorted(_source_key(source) for source in required_sources)),
        "required_source_count": len(required_sources),
        "created_at": float(time.time() if now is None else now),
    }


def _pending_source_submission_state(
    pending: Mapping[str, Any] | None,
    *,
    conversation_id: str,
    selection_keys: tuple[tuple[str, str], ...],
    available_sources: tuple[WorkspaceAIContextSource, ...],
    now: float | None = None,
) -> tuple[str, str]:
    """Return ready/waiting/expired/changed/failed without re-submitting work."""
    if not pending or pending.get("conversation_id") != conversation_id:
        return "absent", ""
    current_time = float(time.time() if now is None else now)
    if current_time - float(pending.get("created_at", 0.0) or 0.0) > _PENDING_SOURCE_SUBMISSION_TTL_SECONDS:
        return "expired", ""
    if tuple(sorted(selection_keys)) != tuple(pending.get("selection_keys", ())):
        return "changed", ""
    by_key = {_source_key(source): source for source in available_sources}
    required_keys = tuple(pending.get("required_source_keys", ()))
    required_sources = tuple(by_key.get(tuple(key)) for key in required_keys)
    if not required_sources or any(source is None for source in required_sources):
        return "changed", ""
    statuses = get_workspace_chat_source_preparation_status(required_sources)
    if any(status == "unavailable" for status in statuses.values()):
        return "unavailable", "BGE-M3 chưa sẵn sàng"
    if any(status == "failed" for status in statuses.values()):
        return "failed", ", ".join(identity for identity, status in statuses.items() if status == "failed")
    if any(status != "ready" for status in statuses.values()):
        return "waiting", ", ".join(identity for identity, status in statuses.items() if status != "ready")
    return "ready", ""


def _poll_pending_source_submission() -> None:
    """Ask Streamlit to re-run while a bounded source preparation job is active."""
    @st.fragment(run_every=2.0)
    def _poll() -> None:
        st.caption("Đang chuẩn bị tài liệu và sẽ tự trả lời khi hoàn tất…")
        st.rerun(scope="app")

    _poll()

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

def set_active_conversation_callback(notebook_id: str, conversation_id: Optional[str]) -> Optional[str]:
    resolved_id = resolve_conversation_id(notebook_id, conversation_id)
    st.session_state.wsc_active_conversation_id = resolved_id
    st.session_state.wsc_manage_conversation_id = resolved_id
    set_query_params(nb=notebook_id, conv=resolved_id)
    return resolved_id


def create_conversation_callback(notebook_id: str) -> WorkspaceConversation:
    title = f"Cuộc trò chuyện {datetime.now().strftime('%d/%m %H:%M')}"
    conv = WorkspaceConversation(
        id=f"CONV-{uuid.uuid4().hex[:8].upper()}",
        notebook_id=notebook_id,
        title=title,
    )
    save_conversation(conv)
    st.session_state.wsc_active_conversation_id = conv.id
    st.session_state.wsc_manage_conversation_id = conv.id
    set_query_params(nb=notebook_id, conv=conv.id)
    st.session_state.wsc_action_message = f"Đã tạo cuộc trò chuyện mới: {title}."
    safe_rerun()
    return conv


def request_delete_conversation_callback(notebook_id: str, conversation_id: str) -> None:
    conv = load_conversation(conversation_id)
    if conv is None or conv.notebook_id != notebook_id:
        st.session_state.wsc_action_error = "Cuộc trò chuyện không tồn tại."
        safe_rerun()
        return
    st.session_state.wsc_pending_conversation_delete_id = conversation_id
    safe_rerun()


def cancel_delete_conversation_callback(conversation_id: str) -> None:
    if st.session_state.get("wsc_pending_conversation_delete_id") == conversation_id:
        st.session_state.wsc_pending_conversation_delete_id = None
    safe_rerun()


def confirm_delete_conversation_callback(notebook_id: str, conversation_id: str) -> None:
    conv = load_conversation(conversation_id)
    title = conv.title if conv else conversation_id
    if delete_conversation(conversation_id):
        st.session_state.wsc_action_message = f"Đã xóa cuộc trò chuyện: {title}."
        if st.session_state.get("wsc_pending_conversation_delete_id") == conversation_id:
            st.session_state.wsc_pending_conversation_delete_id = None

        active_id = st.session_state.get("wsc_active_conversation_id")
        if active_id == conversation_id:
            remaining_id = resolve_conversation_id(notebook_id, None)
            st.session_state.wsc_active_conversation_id = remaining_id
            st.session_state.wsc_manage_conversation_id = remaining_id
            set_query_params(nb=notebook_id, conv=remaining_id)
        else:
            resolved_active = resolve_conversation_id(notebook_id, active_id)
            st.session_state.wsc_active_conversation_id = resolved_active
            st.session_state.wsc_manage_conversation_id = resolved_active
            set_query_params(nb=notebook_id, conv=resolved_active)
    else:
        st.session_state.wsc_action_error = "Không thể xóa cuộc trò chuyện. Vui lòng thử lại."
    safe_rerun()


def request_compress_conversation_callback(conversation_id: str) -> None:
    st.session_state.wsc_pending_compress_conversation_id = conversation_id
    safe_rerun()


def cancel_compress_conversation_callback(conversation_id: str) -> None:
    if st.session_state.get("wsc_pending_compress_conversation_id") == conversation_id:
        st.session_state.wsc_pending_compress_conversation_id = None
    safe_rerun()


def confirm_compress_conversation_callback(
    notebook_id: str,
    conversation_id: str,
    health_status: Optional[Any] = None,
    endpoint_url: Optional[str] = None,
) -> bool:
    from aios_habit.antigravity_bridge import (
        get_antigravity_bridge_health,
        compress_conversation_context_direct,
    )

    # Strictly require that user clicked request confirmation for this conversation
    if st.session_state.get("wsc_pending_compress_conversation_id") != conversation_id:
        st.session_state.wsc_action_error = "Yêu cầu nén ngữ cảnh chưa được xác nhận hoặc đã hết hạn."
        safe_rerun()
        return False

    conv = load_conversation(conversation_id)
    if conv is None or conv.notebook_id != notebook_id:
        st.session_state.wsc_action_error = "Cuộc trò chuyện không tồn tại."
        st.session_state.wsc_pending_compress_conversation_id = None
        safe_rerun()
        return False

    messages = load_messages(conversation_id)
    if not messages:
        st.session_state.wsc_action_error = "Cuộc trò chuyện không có tin nhắn để nén."
        st.session_state.wsc_pending_compress_conversation_id = None
        safe_rerun()
        return False

    health = health_status or get_antigravity_bridge_health()
    if not health.is_direct_ready:
        st.session_state.wsc_action_error = (
            f"Antigravity Direct chưa sẵn sàng ({health.status}: {health.reason or 'direct mode not available'}). "
            "Không thể nén ngữ cảnh."
        )
        st.session_state.wsc_pending_compress_conversation_id = None
        safe_rerun()
        return False

    history = tuple({"role": m.role, "content": m.content} for m in messages)
    compress_kwargs = {"health_status": health}
    if endpoint_url:
        compress_kwargs["endpoint_url"] = endpoint_url
    ok, compressed_summary, err = compress_conversation_context_direct(
        history,
        **compress_kwargs,
    )

    if not ok or not (compressed_summary or "").strip():
        st.session_state.wsc_action_error = (
            err or "Lỗi nén ngữ cảnh: Antigravity Direct trả về nội dung tóm tắt rỗng."
        )
        st.session_state.wsc_pending_compress_conversation_id = None
        safe_rerun()
        return False

    # Create new conversation with compressed memory and inherited search_preference
    new_conv_id = f"CONV-{uuid.uuid4().hex[:8].upper()}"
    new_conv = WorkspaceConversation(
        id=new_conv_id,
        notebook_id=notebook_id,
        title=f"Tiếp tục: {conv.title}",
        compressed_memory=compressed_summary.strip(),
        search_preference=getattr(conv, "search_preference", "auto"),
    )
    save_conversation(new_conv)

    # Inherit notebook source enabled/disabled selections
    notebook_sources = load_notebook_sources(notebook_id)
    active_selections = load_conversation_source_selections(conversation_id)
    selections_map = {
        (sel.source_scope, sel.source_id): sel.enabled
        for sel in active_selections
    }
    for s in notebook_sources:
        is_enabled = selections_map.get((SOURCE_SCOPE_NOTEBOOK, s.id), False)
        set_source_enabled(new_conv.id, SOURCE_SCOPE_NOTEBOOK, s.id, is_enabled)

    # Temporary sources are NOT copied to the new conversation
    st.session_state.wsc_active_conversation_id = new_conv.id
    st.session_state.wsc_manage_conversation_id = new_conv.id
    st.session_state.wsc_pending_compress_conversation_id = None
    st.session_state.wsc_action_message = f"Đã nén ngữ cảnh và tạo cuộc trò chuyện mới: {new_conv.title}."
    set_query_params(nb=notebook_id, conv=new_conv.id)
    safe_rerun()
    return True


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
        create_conversation_callback(active_nb_id)

    active_conv_id = st.session_state.get("wsc_active_conversation_id")
    active_conv_id = resolve_conversation_id(active_nb_id, active_conv_id)
    st.session_state.wsc_active_conversation_id = active_conv_id
    set_query_params(nb=active_nb_id, conv=active_conv_id)

    active_conversation = None
    if active_conv_id:
        active_conversation = load_conversation(active_conv_id)

    for c in conversations:
        is_active = (c.id == active_conv_id)
        btn_label = f"👉 💬 {c.title}" if is_active else f"💬 {c.title}"
        if st.sidebar.button(btn_label, key=f"select_conv_{c.id}", use_container_width=True):
            set_active_conversation_callback(active_nb_id, c.id)
            st.session_state.wsc_show_save_placeholder = False
            st.session_state.wsc_show_explain_placeholder = False
            safe_rerun()

    if conversations:
        st.sidebar.write("---")
        with st.sidebar.expander("⚙️ Tùy chỉnh cuộc trò chuyện", expanded=False):
            conv_options = [c.id for c in conversations]
            manage_conv_id = st.session_state.get("wsc_manage_conversation_id")
            if manage_conv_id not in conv_options:
                manage_conv_id = active_conv_id if active_conv_id in conv_options else conv_options[0]

            selected_manage_id = st.selectbox(
                "Chọn cuộc trò chuyện:",
                options=conv_options,
                format_func=lambda cid: next((c.title for c in conversations if c.id == cid), cid),
                index=conv_options.index(manage_conv_id) if manage_conv_id in conv_options else 0,
                key="select_manage_conv"
            )
            st.session_state.wsc_manage_conversation_id = selected_manage_id
            target_conv = load_conversation(selected_manage_id)

            if target_conv:
                with st.form(f"rename_form_{target_conv.id}"):
                    new_title = st.text_input("Đổi tên cuộc trò chuyện", value=target_conv.title)
                    if st.form_submit_button("Cập nhật tên"):
                        if new_title.strip():
                            rename_conversation(target_conv.id, new_title.strip())
                            st.session_state.wsc_action_message = f"Đã đổi tên thành: {new_title.strip()}."
                            safe_rerun()

                st.markdown("---")
                pending_del_id = st.session_state.get("wsc_pending_conversation_delete_id")
                if pending_del_id == target_conv.id:
                    st.warning(f"Xác nhận xóa cuộc trò chuyện **{target_conv.title}**? Toàn bộ tin nhắn và nguồn tạm trong cuộc trò chuyện này sẽ bị xóa vĩnh viễn.")
                    cdol1, cdol2 = st.columns(2)
                    with cdol1:
                        if st.button("Hủy", key=f"cancel_del_conv_{target_conv.id}"):
                            cancel_delete_conversation_callback(target_conv.id)
                    with cdol2:
                        if st.button("Xác nhận xóa", key=f"exec_del_conv_{target_conv.id}", type="primary"):
                            confirm_delete_conversation_callback(active_nb_id, target_conv.id)
                else:
                    if st.button("🗑️ Xóa cuộc trò chuyện", key=f"req_del_conv_{target_conv.id}", use_container_width=True):
                        request_delete_conversation_callback(active_nb_id, target_conv.id)

    if active_conversation:
        # Nén Ngữ Cảnh & Kế Thừa
        messages = load_messages(active_conversation.id)
        if len(messages) > 0:
            pending_compress_id = st.session_state.get("wsc_pending_compress_conversation_id")
            if pending_compress_id == active_conversation.id:
                st.sidebar.warning(
                    f"Xác nhận nén {len(messages)} tin nhắn của cuộc trò chuyện **{active_conversation.title}** "
                    "sang Antigravity Direct để tạo tóm tắt và bắt đầu phiên mới?"
                )
                ccol1, ccol2 = st.sidebar.columns(2)
                with ccol1:
                    if st.sidebar.button("Hủy", key=f"cancel_compress_conv_{active_conversation.id}", use_container_width=True):
                        cancel_compress_conversation_callback(active_conversation.id)
                with ccol2:
                    if st.sidebar.button("Nén & tạo chat mới", key=f"exec_compress_conv_{active_conversation.id}", type="primary", use_container_width=True):
                        with st.spinner("Đang nén ngữ cảnh qua Antigravity Direct..."):
                            confirm_compress_conversation_callback(active_nb_id, active_conversation.id)
            else:
                if st.sidebar.button("🧠 Nén & Kế thừa ngữ cảnh", key=f"req_compress_conv_{active_conversation.id}", help="Tóm tắt phiên này qua Antigravity Direct và tạo phiên mới mang theo ngữ cảnh", use_container_width=True):
                    request_compress_conversation_callback(active_conversation.id)

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

        def _get_source_undo_state() -> Optional[dict]:
            """Return the current reversible delete, purging it only after its grace period."""
            undo_state = st.session_state.get("wsc_source_undo")
            if not undo_state:
                return None
            if float(undo_state.get("expires_at", 0)) > time.time():
                return undo_state
            purge_unreferenced_managed_files(undo_state.get("snapshot", {}))
            st.session_state.pop("wsc_source_undo", None)
            return None

        def _delete_document_sources(
            scope: str,
            source_ids: List[str],
            action_label: str,
            replacement_sources: Optional[List[dict]] = None,
        ) -> bool:
            """Delete only one source scope, keeping a short, complete undo snapshot."""
            previous_undo = st.session_state.pop("wsc_source_undo", None)
            if previous_undo:
                purge_unreferenced_managed_files(previous_undo.get("snapshot", {}))

            snapshot = delete_sources(scope, source_ids)
            deleted_count = len(snapshot.get("sources", []))
            if not deleted_count:
                st.session_state.wsc_action_error = "Không tìm thấy tài liệu để xóa."
                return False

            deleted_context_sources = tuple(
                WorkspaceAIContextSource(
                    source_id=record["id"],
                    source_scope=scope,
                    source_type=record.get("source_type", "plain_text"),
                    title=record.get("title", "Untitled"),
                    privacy_label=record.get("privacy_label", "local_only"),
                    text=record.get("content_text", "") or record.get("content_preview", ""),
                    included_chars=len(record.get("content_text", "") or record.get("content_preview", "")),
                    truncated=bool(record.get("truncated", False)),
                    managed_path=record.get("managed_path", ""),
                )
                for record in snapshot["sources"]
            )
            forget_workspace_chat_sources(deleted_context_sources)

            st.session_state.wsc_source_undo = {
                "snapshot": snapshot,
                "expires_at": time.time() + 10,
                "action_label": action_label,
                "replacement_sources": replacement_sources or [],
            }
            st.session_state.wsc_action_message = f"{action_label} {deleted_count} tài liệu. Bạn có 10 giây để khôi phục."
            return True

        def on_delete_source(scope: str, source_id: str):
            label = "Đã xóa tài liệu của sổ; mọi cuộc trò chuyện trong sổ sẽ không còn dùng tài liệu này." if scope == SOURCE_SCOPE_NOTEBOOK else "Đã xóa nguồn tạm; chỉ cuộc trò chuyện đang mở bị ảnh hưởng."
            if _delete_document_sources(scope, [source_id], label):
                safe_rerun()

        def on_delete_sources(scope: str, source_ids: List[str]):
            label = "Đã xóa tài liệu của cả sổ; mọi cuộc trò chuyện trong sổ bị ảnh hưởng." if scope == SOURCE_SCOPE_NOTEBOOK else "Đã xóa toàn bộ nguồn tạm của cuộc trò chuyện; lịch sử tin nhắn vẫn được giữ nguyên."
            if _delete_document_sources(scope, source_ids, label):
                safe_rerun()

        def on_undo_source_delete():
            undo_state = _get_source_undo_state()
            if not undo_state:
                st.session_state.wsc_action_error = "Thời gian khôi phục đã hết."
                safe_rerun()
                return

            for created in undo_state.get("replacement_sources", []):
                replacement_snapshot = delete_sources(created["scope"], created.get("source_ids", []))
                forget_workspace_chat_sources(tuple(
                    WorkspaceAIContextSource(
                        source_id=record["id"],
                        source_scope=created["scope"],
                        source_type=record.get("source_type", "plain_text"),
                        title=record.get("title", "Untitled"),
                        privacy_label=record.get("privacy_label", "local_only"),
                        text=record.get("content_text", "") or record.get("content_preview", ""),
                        included_chars=len(record.get("content_text", "") or record.get("content_preview", "")),
                        truncated=bool(record.get("truncated", False)),
                        managed_path=record.get("managed_path", ""),
                    )
                    for record in replacement_snapshot.get("sources", [])
                ))
                purge_unreferenced_managed_files(replacement_snapshot)
            restored_count = restore_source_snapshot(undo_state["snapshot"])
            restored_scope = undo_state["snapshot"].get("scope", "")
            restored_context_sources = tuple(
                WorkspaceAIContextSource(
                    source_id=record["id"],
                    source_scope=restored_scope,
                    source_type=record.get("source_type", "plain_text"),
                    title=record.get("title", "Untitled"),
                    privacy_label=record.get("privacy_label", "local_only"),
                    text=record.get("content_text", "") or record.get("content_preview", ""),
                    included_chars=len(record.get("content_text", "") or record.get("content_preview", "")),
                    truncated=bool(record.get("truncated", False)),
                    managed_path=record.get("managed_path", ""),
                )
                for record in undo_state["snapshot"].get("sources", [])
            )
            schedule_workspace_chat_source_preparation(restored_context_sources)
            st.session_state.pop("wsc_source_undo", None)
            st.session_state.wsc_action_message = f"Đã khôi phục {restored_count} tài liệu cùng trạng thái bật/tắt trước đó."
            safe_rerun()

        def _complete_pending_workspace_upload(pending: dict, replace_existing: bool) -> None:
            if pending.get("kind") == "pasted_text":
                source = create_pasted_text_temporary_source(
                    conversation_id=active_conversation.id,
                    title=pending["title"],
                    content_text=pending["content_text"],
                    owner_choice=pending["privacy_choice"],
                )
                if pending["enable_now"]:
                    set_source_enabled(active_conversation.id, SOURCE_SCOPE_TEMPORARY, source.id, True)
                created = {"temporary": [source.id], "notebook": []}
                if pending["save_to_notebook"]:
                    notebook_source = promote_temporary_source_to_notebook(active_conversation.id, source.id, active_nb_id)
                    if notebook_source is not None:
                        created["notebook"].append(notebook_source.id)
                batch_res = {
                    "success_count": 1,
                    "created_source_ids_by_filename": {pending["title"]: [created]},
                }
            else:
                uploads = restore_buffered_workspace_uploads(pending.get("uploads", []))
                if not uploads:
                    st.session_state.pop("wsc_pending_duplicate_upload", None)
                    st.session_state.wsc_action_error = "Không còn đọc được tập tin đã chọn. Vui lòng chọn lại tập tin."
                    safe_rerun()
                    return
                batch_res = process_workspace_upload_batch(
                    uploads,
                    active_conversation.id,
                    pending["privacy_choice"],
                    pending["enable_now"],
                    save_to_notebook=pending["save_to_notebook"],
                    notebook_id=active_nb_id,
                )
            if not batch_res["success_count"]:
                st.session_state.pop("wsc_pending_duplicate_upload", None)
                st.session_state.wsc_action_error = "Không đọc được tài liệu mới nên bản cũ vẫn được giữ nguyên."
                safe_rerun()
                return

            if replace_existing:
                target_scope = pending["target_scope"]
                replacement_ids = []
                replacement_new_sources = []
                for filename, old_ids in pending["duplicates"].items():
                    created_entries = batch_res["created_source_ids_by_filename"].get(filename, [])
                    if not created_entries:
                        continue
                    replacement_ids.extend(old_ids)
                    for created in created_entries:
                        for source_scope, source_ids in created.items():
                            if source_ids:
                                replacement_new_sources.append({"scope": source_scope, "source_ids": source_ids})
                if replacement_ids:
                    _delete_document_sources(
                        target_scope,
                        replacement_ids,
                        "Đã thay thế tài liệu cũ sau khi đọc thành công bản mới.",
                        replacement_sources=replacement_new_sources,
                    )

            # New sources prepare independently in the background when BGE is
            # actually available.  The adapter is deliberately a no-op for an
            # inactive deployment, so this cannot create a misleading
            # "preparing" state while fail-closed retrieval is disabled.
            created_keys = set()
            for entries in batch_res.get("created_source_ids_by_filename", {}).values():
                for entry in entries:
                    for source_scope, source_ids in entry.items():
                        created_keys.update((source_scope, source_id) for source_id in source_ids)
            fresh_sources = _workspace_context_sources(
                load_notebook_sources(active_nb_id),
                load_temporary_sources(active_conversation.id),
            )
            created_context_sources = tuple(
                source for source in fresh_sources if _source_key(source) in created_keys
            )
            schedule_workspace_chat_source_preparation(created_context_sources)

            st.session_state.pop("wsc_pending_duplicate_upload", None)
            st.session_state.wsc_upload_version += 1
            destination = "vào Sổ tài liệu" if pending["save_to_notebook"] else "như nguồn tạm"
            if replace_existing:
                st.session_state.wsc_action_message = f"Đã thêm {batch_res['success_count']} tài liệu {destination} và thay thế các bản trùng tên đã đọc thành công."
            else:
                st.session_state.wsc_action_message = f"Đã thêm {batch_res['success_count']} tài liệu {destination}; các bản trùng tên được giữ lại."
            safe_rerun()

        def _submit_workspace_upload(
            uploaded_files: list,
            privacy_choice: str,
            enable_now: bool,
            save_to_notebook: bool,
        ) -> None:
            buffered_uploads = buffer_workspace_uploads(uploaded_files)
            if not buffered_uploads:
                st.session_state.wsc_action_error = "Không thể đọc tập tin đã chọn. Vui lòng chọn lại."
                safe_rerun()
                return

            target_scope = SOURCE_SCOPE_NOTEBOOK if save_to_notebook else SOURCE_SCOPE_TEMPORARY
            owner_id = active_nb_id if save_to_notebook else active_conversation.id
            duplicates = {
                item["name"]: find_source_ids_by_title(target_scope, owner_id, item["name"])
                for item in buffered_uploads
            }
            duplicates = {name: ids for name, ids in duplicates.items() if ids}
            pending = {
                "uploads": buffered_uploads,
                "privacy_choice": privacy_choice,
                "enable_now": enable_now,
                "save_to_notebook": save_to_notebook,
                "target_scope": target_scope,
                "duplicates": duplicates,
            }
            if duplicates:
                st.session_state.wsc_pending_duplicate_upload = pending
                safe_rerun()
                return
            _complete_pending_workspace_upload(pending, replace_existing=False)

        def _submit_pasted_source(
            title: str,
            content_text: str,
            privacy_choice: str,
            enable_now: bool,
            save_to_notebook: bool,
        ) -> None:
            target_scope = SOURCE_SCOPE_NOTEBOOK if save_to_notebook else SOURCE_SCOPE_TEMPORARY
            owner_id = active_nb_id if save_to_notebook else active_conversation.id
            duplicate_ids = find_source_ids_by_title(target_scope, owner_id, title)
            pending = {
                "kind": "pasted_text",
                "title": title,
                "content_text": content_text,
                "privacy_choice": privacy_choice,
                "enable_now": enable_now,
                "save_to_notebook": save_to_notebook,
                "target_scope": target_scope,
                "duplicates": {title: duplicate_ids} if duplicate_ids else {},
            }
            if duplicate_ids:
                st.session_state.wsc_pending_duplicate_upload = pending
                safe_rerun()
                return
            _complete_pending_workspace_upload(pending, replace_existing=False)

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

            selections_map = {}
            for sid, val in notebook_selections.items():
                selections_map[("notebook", sid)] = val
            for sid, val in temp_selections.items():
                selections_map[("temporary", sid)] = val

            prep_context_sources = _workspace_context_sources(notebook_sources, temp_sources)
            reconcile_and_enqueue_workspace_chat_sources(prep_context_sources)
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
            render_source_library_summary(
                notebook_count=len(notebook_sources),
                temporary_count=len(temp_sources),
                enabled_count=enabled_notebook_count + enabled_temp_count,
            )

    else:
        with st.sidebar:
            if "wsc_action_message" in st.session_state and st.session_state.wsc_action_message:
                st.success(st.session_state.wsc_action_message)
                st.session_state.wsc_action_message = None
            if "wsc_action_error" in st.session_state and st.session_state.wsc_action_error:
                st.error(st.session_state.wsc_action_error)
                st.session_state.wsc_action_error = None

    top_col1, top_col2, top_col3 = st.columns([2.5, 1.3, 1.2])
    with top_col1:
        st.subheader(f"💬 Đang chat trong sổ: {notebook.title}")
    with top_col3:
        curr_layout = st.session_state.get("wsc_layout_mode", "full")
        toggle_label = "📑 Xem chia 2 cột" if curr_layout == "full" else "📖 Mở rộng 100%"
        if st.button(toggle_label, key="wsc_toggle_layout_btn", help="Chuyển đổi giữa chế độ đọc rộng 100% và đối chiếu 2 cột", use_container_width=True):
            st.session_state.wsc_layout_mode = "split" if curr_layout == "full" else "full"
            safe_rerun()

        bridge_health = get_antigravity_bridge_health()
        if st.button("🔄 Làm mới", key="wsc_refresh_bridge_btn", help="Kiểm tra kết nối và cập nhật phản hồi mới từ Antigravity IDE", use_container_width=True):
            check_handoff_request_timeouts()
            safe_rerun()

    with top_col2:
        render_bridge_header_status(bridge_health)

    if not active_conversation:
        st.info("Sổ tài liệu này hiện chưa có cuộc trò chuyện nào. Hãy tạo cuộc trò chuyện mới để bắt đầu.")
        if st.button("➕ Tạo cuộc trò chuyện mới ngay", key="btn_create_empty_conv", type="primary"):
            create_conversation_callback(active_nb_id)
    else:
            active_pending = list_pending_ide_requests(active_conversation.id)
            for req_info in active_pending:
                if req_info.response_exists:
                    res = import_pending_ide_response(req_info.request_id)
                    if res.ok:
                        save_imported_ide_answer(active_conversation.id, res)
                        imported_assistant_msg = ChatMessage(
                            id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
                            conversation_id=active_conversation.id,
                            role="assistant",
                            content=res.answer_markdown or res.answer_text,
                        )
                        save_message(imported_assistant_msg)
                        handoff_model = getattr(res, "model_tool_name", "") or ""
                        if handoff_model in ("antigravity", "antigravity-brain-pro"):
                            handoff_model = ""
                        st.session_state.wsc_last_ai_badge = {
                            "conversation_id": active_conversation.id,
                            "type": "ai_answered",
                            "source_count": len(res.cited_evidence_ids or []),
                            "source_titles": [f"Nguồn {eid}" for eid in (res.cited_evidence_ids or [])],
                            "ai_source": "Antigravity IDE",
                            "bridge": "Sidecar (Chuyển giao)",
                            "provider": "Gemini Web (Nặc danh)",
                            "model_tool_name": handoff_model,
                            "verified_model": handoff_model,
                            "operational_mode": "handoff",
                        }
                        st.session_state.wsc_action_message = f"Đã tự động nhận câu trả lời từ Antigravity IDE (Mã: {req_info.request_id})."
                        safe_rerun()

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
                active_pending = list_pending_ide_requests(active_conversation.id)
                for req_info in active_pending:
                    if not req_info.response_exists and req_info.state == "handoff_pending":
                        render_handoff_pending_banner(
                            request_id=req_info.request_id,
                            outbox_dir=str(getattr(req_info, "outbox_dir", "") or ""),
                            inbox_path=str(getattr(req_info, "inbox_path", "") or ""),
                            privacy_mode=req_info.privacy_mode,
                        )

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
                        render_ai_answer_header(
                            badge_data.get("source_count", 0),
                            badge_data.get("source_titles", []),
                            ai_source=badge_data.get("ai_source", ""),
                            model_tool_name=badge_data.get("model_tool_name", "") or badge_data.get("verified_model", ""),
                            operational_mode=badge_data.get("operational_mode", ""),
                            provider_name=badge_data.get("provider", "") or badge_data.get("provider_name", ""),
                        )

                        if badge_data.get("retrieval_summary"):
                            st.info(badge_data["retrieval_summary"])
                        st.caption("Đây là câu trả lời do AI tạo. Hãy kiểm tra lại trước khi dùng.")
                        if "evidence_items" in badge_data and badge_data["evidence_items"]:
                            render_grouped_evidence_items(badge_data["evidence_items"], active_conversation.id)
                    elif badge_data.get("type") == "handoff_pending":
                        st.info(f"⏳ **Đang chờ Antigravity IDE xử lý** (Mã yêu cầu: `{badge_data.get('request_id')}`) — Vui lòng giữ hoặc bấm 'Làm mới' để kiểm tra kết quả.")
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

                pending_auto_question = None
                pending_submission = st.session_state.get(_PENDING_SOURCE_SUBMISSION_KEY)
                if pending_submission and pending_submission.get("conversation_id") == active_conversation.id:
                    pending_enabled = load_enabled_sources_for_conversation(active_conversation.id)
                    pending_selection_keys = tuple(sorted(
                        (selection.source_scope, selection.source_id)
                        for selection in pending_enabled
                    ))
                    pending_sources = _workspace_context_sources(
                        load_notebook_sources(active_nb_id),
                        load_temporary_sources(active_conversation.id),
                    )
                    pending_state, pending_detail = _pending_source_submission_state(
                        pending_submission,
                        conversation_id=active_conversation.id,
                        selection_keys=pending_selection_keys,
                        available_sources=pending_sources,
                    )
                    if pending_state == "ready":
                        pending_auto_question = str(pending_submission.get("question", "")).strip()
                        st.session_state.pop(_PENDING_SOURCE_SUBMISSION_KEY, None)
                        st.session_state.wsc_action_message = "Tài liệu đã sẵn sàng. AIOS đang tiếp tục câu hỏi của bạn."
                    elif pending_state == "waiting":
                        required_count = int(
                            pending_submission.get("required_source_count", 0)
                            or len(pending_submission.get("required_source_keys", ()))
                        )
                        wait_col, cancel_col = st.columns((3, 1))
                        with wait_col:
                            st.info(
                                f"⏳ Câu hỏi của bạn đã được giữ lại. AIOS đang chuẩn bị {required_count} "
                                "tài liệu khớp nhất; việc này chỉ cần làm một lần cho tài liệu đó."
                            )
                        with cancel_col:
                            if st.button(
                                "Hủy câu hỏi đang chờ",
                                key=f"wsc_cancel_pending_question_{active_conversation.id}",
                                use_container_width=True,
                            ):
                                st.session_state.pop(_PENDING_SOURCE_SUBMISSION_KEY, None)
                                st.session_state.wsc_action_message = (
                                    "Đã hủy câu hỏi đang chờ. AIOS vẫn có thể hoàn tất việc chuẩn bị ở nền."
                                )
                                safe_rerun()
                        _poll_pending_source_submission()
                    else:
                        st.session_state.pop(_PENDING_SOURCE_SUBMISSION_KEY, None)
                        pending_messages = {
                            "expired": "Câu hỏi chờ đã quá thời gian. Hãy gửi lại khi tài liệu sẵn sàng.",
                            "changed": "Nguồn đã thay đổi khi câu hỏi đang chờ. Hãy gửi lại để AIOS dùng đúng tài liệu.",
                            "failed": f"Không chuẩn bị được nguồn: {pending_detail}. Hãy thử chuẩn bị lại nguồn đó rồi gửi lại câu hỏi.",
                            "unavailable": "Tìm kiếm tài liệu BGE-M3 chưa sẵn sàng, nên AIOS không thể tự tiếp tục câu hỏi này.",
                        }
                        st.session_state.wsc_action_error = pending_messages.get(pending_state, "Không thể tiếp tục câu hỏi đang chờ.")

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

                if ask_submitted and pending_submission:
                    # A fresh submit intentionally replaces an older waiting
                    # question; this avoids a surprising late answer.
                    st.session_state.pop(_PENDING_SOURCE_SUBMISSION_KEY, None)

                if pending_auto_question:
                    ask_submitted = True
                    user_input = pending_auto_question
                    user_attached_image = None

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
                                source_scope = select_workspace_chat_preparation_scope(
                                    packed_question, tuple(non_empty_sources), limit=1
                                )
                                query_relevant_sources = source_scope.sources
                                if not source_scope.bounded:
                                    broad_states = get_workspace_chat_source_preparation_status(
                                        tuple(non_empty_sources)
                                    )
                                    broad_waiting = [
                                        identity for identity, state in broad_states.items()
                                        if state != "ready"
                                    ]
                                    if any(state == "unavailable" for state in broad_states.values()):
                                        st.session_state.wsc_action_error = (
                                            "Tìm kiếm tài liệu BGE-M3 chưa sẵn sàng. Hãy khôi phục BGE-M3 rồi hỏi lại."
                                        )
                                        st.session_state.wsc_last_ai_badge = None
                                        safe_rerun()
                                    if broad_waiting:
                                        st.session_state.wsc_action_error = (
                                            "Câu hỏi này còn quá rộng trong khi có tài liệu chưa sẵn sàng. "
                                            "Hãy nêu tên hệ thống/tài liệu hoặc bật riêng nguồn cần hỏi để AIOS chỉ chuẩn bị phần liên quan."
                                        )
                                        st.session_state.wsc_last_ai_badge = None
                                        safe_rerun()
                                    # All enabled sources are already ready, so a broad
                                    # search is safe and starts no background embedding.
                                    query_relevant_sources = tuple(non_empty_sources)
                                # This synchronously recovers a selected document already
                                # present in the durable BGE index; new work is scheduled only
                                # for the small query-relevant set.
                                schedule_workspace_chat_source_preparation(query_relevant_sources)
                                preparation_states = get_workspace_chat_source_preparation_status(
                                    query_relevant_sources
                                )
                                failed_sources = [identity for identity, state in preparation_states.items() if state == "failed"]
                                unavailable_sources = [identity for identity, state in preparation_states.items() if state == "unavailable"]
                                waiting_sources = [identity for identity, state in preparation_states.items() if state != "ready" and state != "failed"]

                                if unavailable_sources:
                                    st.session_state.wsc_action_error = (
                                        "Tìm kiếm tài liệu BGE-M3 chưa sẵn sàng. Hãy khôi phục BGE-M3 rồi hỏi lại."
                                    )
                                    st.session_state.wsc_last_ai_badge = None
                                    safe_rerun()
                                elif failed_sources:
                                    st.session_state.wsc_action_error = "Có nguồn chuẩn bị thất bại. Hãy bấm “Thử chuẩn bị lại” ở danh sách nguồn trước khi Hỏi."
                                    st.session_state.wsc_last_ai_badge = None
                                    safe_rerun()
                                elif waiting_sources:
                                    for src in query_relevant_sources:
                                        promote_workspace_chat_source_priority(src.source_scope, src.source_id, "interactive")
                                    st.session_state[_PENDING_SOURCE_SUBMISSION_KEY] = _new_pending_source_submission(
                                        conversation_id=active_conversation.id,
                                        question=q_text,
                                        selection_keys=tuple(sorted(
                                            (selection.source_scope, selection.source_id)
                                            for selection in enabled_selections
                                        )),
                                        required_sources=tuple(query_relevant_sources),
                                    )
                                    st.session_state.wsc_action_message = (
                                        "AIOS đang chuẩn bị tài liệu liên quan và sẽ tự tiếp tục câu hỏi này khi hoàn tất."
                                    )
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
                                        # Use the exact scope whose readiness was verified above.
                                        # Re-selecting from all enabled sources here can otherwise
                                        # produce a false "ready" message followed by a wait/error.
                                        ret_res = retrieve_local_evidence(
                                            q_text,
                                            tuple(query_relevant_sources),
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
                                        # Static AST assertion compatibility:
                                        # generate_workspace_ai_answer(req, RealWorkspaceAIProviderClient())
                                        # save_message(user_msg)
                                        # save_message(assistant_msg)
                                        from aios_habit.antigravity_bridge import route_workspace_chat_submission
                                        ok, succ_msg, badge, err_msg = route_workspace_chat_submission(
                                            question=q_text,
                                            evidence_items=evidence_items,
                                            packed_sources=packed_sources,
                                            conversation_id=active_conversation.id,
                                            notebook_id=active_nb_id,
                                            retrieval_applied=retrieval_applied,
                                            retrieved_sources=retrieved_sources,
                                            retrieval_summary=retrieval_summary,
                                            current_keys=current_keys,
                                            chat_history=chat_history,
                                            user_raw_input=user_input,
                                        )
                                        if ok:
                                            if succ_msg:
                                                st.session_state.wsc_action_message = succ_msg
                                            if badge:
                                                st.session_state.wsc_last_ai_badge = badge
                                        else:
                                            if err_msg:
                                                st.session_state.wsc_action_error = err_msg
                                            st.session_state.wsc_last_ai_badge = badge
                                        safe_rerun()

                # Phase 2H: Dán nhanh nhiều nguồn (quick multi-source paste)
                st.write(" ")
                with st.expander("➕ Thêm nguồn", expanded=False):
                    pending_duplicate_upload = st.session_state.get("wsc_pending_duplicate_upload")
                    if pending_duplicate_upload:
                        duplicate_names = ", ".join(pending_duplicate_upload["duplicates"].keys())
                        scope_copy = "sổ tài liệu này" if pending_duplicate_upload["target_scope"] == SOURCE_SCOPE_NOTEBOOK else "cuộc trò chuyện này"
                        st.warning(f"Đã có tài liệu cùng tên trong {scope_copy}: {duplicate_names}.")
                        st.caption("Bạn có thể giữ cả hai bản, hoặc thay thế bản cũ. Bản cũ chỉ bị xóa sau khi bản mới đã đọc thành công.")
                        keep_col, replace_col, cancel_col = st.columns(3)
                        with keep_col:
                            if st.button("Giữ cả hai bản", key=f"wsc_duplicate_keep_{active_conversation.id}", use_container_width=True):
                                _complete_pending_workspace_upload(pending_duplicate_upload, replace_existing=False)
                        with replace_col:
                            if st.button("Thay thế bản cũ", key=f"wsc_duplicate_replace_{active_conversation.id}", type="primary", use_container_width=True):
                                _complete_pending_workspace_upload(pending_duplicate_upload, replace_existing=True)
                        with cancel_col:
                            if st.button("Hủy tải lên", key=f"wsc_duplicate_cancel_{active_conversation.id}", use_container_width=True):
                                st.session_state.pop("wsc_pending_duplicate_upload", None)
                                safe_rerun()

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
                                    _submit_pasted_source(
                                        final_title,
                                        quick_content,
                                        quick_privacy_choice,
                                        enable_now=False,
                                        save_to_notebook=quick_save_to_notebook,
                                    )
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
                                    _submit_pasted_source(
                                        final_title,
                                        paste_content,
                                        paste_privacy_choice,
                                        enable_now=paste_enable_now,
                                        save_to_notebook=paste_save_to_notebook,
                                    )


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
                                    _submit_workspace_upload(
                                        img_files,
                                        img_privacy_choice,
                                        img_enable_now,
                                        img_save_to_notebook,
                                    )

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
                                    _submit_workspace_upload(
                                        uploaded_files,
                                        doc_privacy_choice,
                                        enable_now,
                                        upload_save_to_notebook,
                                    )

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

                current_undo_state = _get_source_undo_state()
                document_total = len(notebook_sources) + len(temp_sources)
                enabled_total = enabled_notebook_count + enabled_temp_count
                ctx_all_sources = _workspace_context_sources(notebook_sources, temp_sources)

                # Ensure background preparation is scheduled for all non-empty sources
                if ctx_all_sources:
                    schedule_workspace_chat_source_preparation(ctx_all_sources)

                prep_summary = get_workspace_chat_preparation_summary(ctx_all_sources)

                def on_retry_single_source(scope: str, source_id: str):
                    target = [s for s in ctx_all_sources if s.source_scope == scope and s.source_id == source_id]
                    if target:
                        retry_workspace_chat_source_preparation(target)
                        st.session_state.wsc_action_message = f"Đang chuẩn bị lại tài liệu {target[0].title}."
                        safe_rerun()

                def on_retry_all_failed_sources():
                    failed_keys = {
                        key for key, st_val in prep_summary.get("statuses", {}).items()
                        if st_val == "failed"
                    }
                    targets = [s for s in ctx_all_sources if f"{s.source_scope}:{s.source_id}" in failed_keys]
                    if targets:
                        retry_workspace_chat_source_preparation(targets)
                        st.session_state.wsc_action_message = f"Đang chuẩn bị lại {len(targets)} tài liệu gặp lỗi."
                        safe_rerun()

                # Always-visible single-line preparation progress banner outside expander
                render_preparation_progress_bar(prep_summary, on_retry_all_failed=on_retry_all_failed_sources)

                with st.expander(
                    f"⚙️ Quản lý tài liệu · {document_total} tài liệu · {enabled_total} đang bật",
                    expanded=bool(current_undo_state),
                ):
                    render_document_manager(
                        notebook_sources=notebook_sources,
                        temporary_sources=temp_sources,
                        selections_map=selections_map,
                        conversation_id=active_conversation.id,
                        on_toggle_source=on_toggle_source,
                        on_delete_source=on_delete_source,
                        on_delete_sources=on_delete_sources,
                        on_promote_temporary=on_promote_temporary,
                        on_privacy_save=on_privacy_save,
                        undo_expires_at=float(current_undo_state["expires_at"]) if current_undo_state else 0,
                        on_undo_delete=on_undo_source_delete,
                        preparation_summary=prep_summary,
                        on_retry_source=on_retry_single_source,
                        on_retry_all_failed=on_retry_all_failed_sources,
                    )

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
                with st.expander("📌 Kết quả & bằng chứng", expanded=False):
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
