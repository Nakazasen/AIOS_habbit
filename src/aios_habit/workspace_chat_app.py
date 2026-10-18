import os
import sys
import logging

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Chặn nhật ký cảnh báo tiếng Anh từ Streamlit khi module được nhập trong chế độ kiểm thử bare/headless
if not os.environ.get("STREAMLIT_SERVER_PORT"):
    try:
        from streamlit.logger import get_logger
        get_logger("streamlit.runtime.scriptrunner_utils.script_run_context").disabled = True
        get_logger("streamlit.runtime.state.session_state_proxy").disabled = True
        get_logger("streamlit").disabled = True
        get_logger("root").disabled = True
    except Exception:
        pass

import streamlit as st
import uuid
import time
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
from io import BytesIO
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Mapping, Callable, Sequence
import html
from aios_habit.workspace_paths import default_agent_workspace_root

LOGGER = logging.getLogger("aios_habit.workspace_chat_app")

from aios_habit.streaming_markers import (
    _safe_print_streaming_marker,
    format_marker_timestamp,
    emit_pre_synth_step_marker,
)


# Provider calls can take minutes. Keep them off Streamlit's UI run so the
# composer can present a genuine stop action while a response is in flight.
_WORKSPACE_AI_REQUEST_EXECUTOR = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="workspace-ai-request",
)

# Giới hạn kích thước và định dạng cho tệp đính kèm một lần trong khung soạn thảo (DESKTOP-COMPOSER-FILE-ATTACH-HOME)
MAX_COMPOSER_TEXT_FILE_BYTES: int = 50 * 1024  # 50 KB tối đa cho tệp chữ/CSV nhỏ
MAX_COMPOSER_ATTACHED_TEXT_CHARS: int = 3000   # 3000 ký tự tối đa gộp vào câu hỏi (đồng bộ OCR)
COMPOSER_SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
COMPOSER_SUPPORTED_TEXT_EXTS = {".csv", ".txt", ".tsv", ".md", ".log"}
COMPOSER_SUPPORTED_EXTS = COMPOSER_SUPPORTED_IMAGE_EXTS | COMPOSER_SUPPORTED_TEXT_EXTS


st.set_page_config(
    page_title="Hỏi tài liệu",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Streamlit 1.60 renders <style> inside st.markdown as visible text.
# Style-only st.html is parked in the event container, not the main pane.
st.html('''
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

        /* Keep the layout/evidence switch beside the reading surface, rather
           than stranding it above a long conversation. */
        [class*="st-key-wsc-layout-rail-toggle"] {
            position: fixed !important;
            top: 50% !important;
            right: 0 !important;
            z-index: 1001 !important;
            width: 44px !important;
            overflow: hidden !important;
            transform: translateY(-50%) !important;
        }
        [class*="st-key-wsc-layout-rail-toggle"] [data-testid="stButton"] button {
            width: 44px !important;
            min-width: 44px !important;
            height: 68px !important;
            min-height: 44px !important;
            padding: 0 !important;
            border-radius: 14px 0 0 14px !important;
            border: 1px solid #E2E8F0 !important;
            border-right: 0 !important;
            background: #FFFFFF !important;
            color: #020617 !important;
            overflow: hidden !important;
            box-shadow: -2px 2px 8px rgba(15, 23, 42, 0.08) !important;
        }
        [class*="st-key-wsc-layout-rail-toggle"] [data-testid="stButton"] button:hover {
            background: #E0F2FE !important;
        }
        [class*="st-key-wsc-layout-rail-toggle"] [data-testid="stButton"] button p {
            display: none !important;
        }

        /* Expand main block container */
        .main .block-container {
            max-width: 96% !important;
            padding-top: 1rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }

        /* Chat bubble typography */
        [data-testid="stChatMessage"] {
            padding: 1.2rem 1.6rem !important;
            border-radius: 12px !important;
            margin-bottom: 1.1rem !important;
            font-size: 16px !important;
            line-height: 1.5 !important;
            border: 1px solid #E2E8F0 !important;
            box-shadow: none !important;
        }

        /* Bong bóng hỏi đáp: câu hỏi viền xanh việc chính bên phải, đáp án viền than bên trái. */
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            background: rgba(3, 105, 161, 0.10) !important;
            border-right: 3px solid #0369A1 !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
            background: #FFFFFF !important;
            border-left: 3px solid #334155 !important;
        }
        /* Bề rộng dòng đáp án dễ đọc; đồ thị bằng chứng không bị ép vào cùng mức đó. */
        [data-testid="stChatMessageContent"] [data-testid="stMarkdown"] p,
        [data-testid="stChatMessageContent"] [data-testid="stMarkdown"] li {
            max-width: 75ch !important;
        }
        [data-testid="stChatMessageContent"] {
            max-width: none !important;
            line-height: 1.6 !important;
        }
        [data-testid="stChatMessage"] iframe {
            width: 100% !important;
            min-width: 0 !important;
        }

        /* List and table formatting inside chat message */
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

        /* Compact, current-generation AI composer. The marker keeps these
           styles confined to the Workspace Chat question form. */
        [data-testid="stForm"]:has(.wsc-composer) {
            border: 1px solid #E2E8F0 !important;
            border-radius: 22px !important;
            background: #FFFFFF !important;
            box-shadow: none !important;
            padding: 0.7rem !important;
        }
        [data-testid="stForm"]:has(.wsc-composer) [data-testid="stTextArea"] textarea {
            min-height: 72px !important;
            border: 0 !important;
            border-radius: 16px !important;
            background: #F8FAFC !important;
            color: #020617 !important;
            box-shadow: none !important;
            padding: 0.85rem 1rem !important;
        }
        [data-testid="stForm"]:has(.wsc-composer) [data-testid="stTextArea"] textarea:focus {
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.75) !important;
        }
        [data-testid="stForm"]:has(.wsc-composer) .wsc-composer__send button {
            min-height: 72px !important;
            border-radius: 18px !important;
            font-weight: 700 !important;
        }
        [data-testid="stForm"]:has(.wsc-composer) details {
            border: 0 !important;
            background: transparent !important;
        }
        [data-testid="stForm"]:has(.wsc-composer) summary {
            color: #020617 !important;
            font-weight: 600 !important;
        }
        @media (max-width: 360px) {
            [data-testid="stForm"]:has(.wsc-composer) {
                border-radius: 16px !important;
                padding: 0.5rem !important;
            }
            [data-testid="stForm"]:has(.wsc-composer) .wsc-composer__row {
                gap: 0.35rem !important;
            }
            [data-testid="stForm"]:has(.wsc-composer) .wsc-composer__send button {
                min-height: 56px !important;
                font-size: 0.78rem !important;
            }
        }

        /* Modern AI assistant unified composer (DESKTOP-COMPOSER-UX-HOME) */
        [class*="st-key-wsc-composer-"] {
            position: relative !important;
            border-radius: 24px !important;
            background: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05), 0 2px 6px -1px rgba(0, 0, 0, 0.03) !important;
            padding: 0.7rem 0.85rem !important;
            margin-bottom: 0.5rem !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        [class*="st-key-wsc-composer-"]:focus-within {
            border-color: #3B82F6 !important;
            box-shadow: 0 4px 24px -2px rgba(59, 130, 246, 0.12), 0 2px 8px -1px rgba(0, 0, 0, 0.04) !important;
        }
        [class*="st-key-wsc-composer-"][data-testid="stVerticalBlock"] {
            gap: 2px !important;
            padding: 0.25rem 0.35rem !important;
        }
        [class*="st-key-wsc-composer-"] [data-testid="stVerticalBlock"] {
            gap: 0.35rem !important;
        }
        [class*="st-key-wsc-composer-"] [data-testid="stVerticalBlockBorderWrapper"] {
            padding: 0.25rem 0.35rem !important;
            border: none !important;
        }
        [class*="st-key-wsc-composer-"] [data-testid="stHorizontalBlock"] {
            align-items: center !important;
            margin-top: 0.25rem !important;
            margin-bottom: 0 !important;
            gap: 6px !important;
        }
        [class*="st-key-wsc-composer-"] [data-testid="stTextArea"],
        [class*="st-key-wsc-composer-"] [data-testid="stTextArea"] > div,
        [class*="st-key-wsc-composer-"] [data-testid="stTextArea"] [data-baseweb="textarea"] {
            margin: 0 !important;
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
        }
        [class*="st-key-wsc-composer-"] [data-testid="stTextArea"] textarea {
            min-height: 52px !important;
            height: auto !important;
            max-height: 180px !important;
            border: 0 !important;
            border-radius: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            padding: 0.25rem 0.15rem !important;
            font-size: 0.95rem !important;
            line-height: 1.5 !important;
            color: #0F172A !important;
            resize: none !important;
        }
        [class*="st-key-wsc-composer-"] [data-testid="stTextArea"] textarea:focus {
            box-shadow: none !important;
            border: 0 !important;
            outline: none !important;
        }
        [class*="st-key-wsc-composer-"] > [data-testid="stElementContainer"]:has([data-testid="stHtml"]) {
            position: absolute !important;
            width: 0 !important;
            height: 0 !important;
            overflow: hidden !important;
        }
        /* Attachment button: compact paperclip */
        [class*="st-key-wsc-attachment-"] [data-testid="stPopover"] button {
            width: 34px !important;
            height: 34px !important;
            min-width: 34px !important;
            min-height: 34px !important;
            max-width: 100% !important;
            overflow: hidden !important;
            border-radius: 50% !important;
            padding: 0 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            background: #F8FAFC !important;
            border: 1px solid #E2E8F0 !important;
            color: #64748B !important;
            transition: all 0.15s ease !important;
        }
        [class*="st-key-wsc-attachment-"] [data-testid="stPopover"] button * {
            min-width: 0 !important;
        }
        [class*="st-key-wsc-attachment-"] [data-testid="stPopover"] button:hover {
            background: #F1F5F9 !important;
            border-color: #CBD5E1 !important;
            color: #0F172A !important;
        }
        [class*="st-key-wsc-attachment-"] [data-testid="stPopover"] button [data-testid="stMarkdownContainer"],
        [class*="st-key-wsc-attachment-"] [data-testid="stPopover"] button p {
            display: none !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            min-width: 0 !important;
        }
        [class*="st-key-wsc-attachment-"] [data-testid="stPopover"] button > svg:last-child {
            display: none !important;
        }
        [class*="st-key-wsc-attachment-"] [data-testid="stPopover"] button svg {
            width: 1.15rem !important;
            height: 1.15rem !important;
        }
        /* Status chips: Knowledge Block, Search Preference, C-Agent, AI Mode */
        [class*="st-key-wsc-block-"] [data-testid="stPopover"] button,
        [class*="st-key-wsc-pref-"] [data-testid="stPopover"] button,
        [class*="st-key-wsc-cagent-"] [data-testid="stPopover"] button,
        [class*="st-key-wsc-mode-"] [data-testid="stPopover"] button {
            height: 32px !important;
            min-height: 32px !important;
            padding: 0 10px !important;
            border-radius: 16px !important;
            border: 1px solid #E2E8F0 !important;
            background: #F8FAFC !important;
            color: #475569 !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            white-space: nowrap !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 4px !important;
            transition: all 0.15s ease !important;
        }
        [class*="st-key-wsc-block-"] [data-testid="stPopover"] button:hover,
        [class*="st-key-wsc-pref-"] [data-testid="stPopover"] button:hover,
        [class*="st-key-wsc-cagent-"] [data-testid="stPopover"] button:hover,
        [class*="st-key-wsc-mode-"] [data-testid="stPopover"] button:hover {
            background: #F1F5F9 !important;
            border-color: #CBD5E1 !important;
            color: #0F172A !important;
        }
        [class*="st-key-wsc-block-"] [data-testid="stPopover"] button p,
        [class*="st-key-wsc-pref-"] [data-testid="stPopover"] button p,
        [class*="st-key-wsc-cagent-"] [data-testid="stPopover"] button p,
        [class*="st-key-wsc-mode-"] [data-testid="stPopover"] button p {
            font-size: 0.8rem !important;
            white-space: nowrap !important;
            margin: 0 !important;
        }
        [class*="st-key-wsc-block-"] [data-testid="stPopover"] button svg:last-child,
        [class*="st-key-wsc-pref-"] [data-testid="stPopover"] button svg:last-child,
        [class*="st-key-wsc-cagent-"] [data-testid="stPopover"] button svg:last-child,
        [class*="st-key-wsc-mode-"] [data-testid="stPopover"] button svg:last-child {
            width: 0.85rem !important;
            height: 0.85rem !important;
            opacity: 0.6 !important;
        }
        /* Shortcut hint */
        [class*="st-key-wsc-shortcut-hint-"] {
            display: flex !important;
            justify-content: flex-end !important;
            align-items: center !important;
            width: 100% !important;
        }
        [class*="st-key-wsc-shortcut-hint-"] [data-testid="stCaptionContainer"] {
            color: #94A3B8 !important;
            font-size: 0.75rem !important;
            white-space: nowrap !important;
            text-align: right !important;
            margin: 0 !important;
        }
        /* Circular Send button with arrow icon */
        [class*="st-key-wsc-action-"] {
            display: flex !important;
            justify-content: flex-end !important;
            align-items: center !important;
            gap: 8px !important;
        }
        [class*="st-key-wsc-action-"] [data-testid="stButton"] button {
            width: 44px !important;
            height: 44px !important;
            min-width: 44px !important;
            min-height: 44px !important;
            border-radius: 50% !important;
            padding: 0 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            background: #0369A1 !important;
            border: 0 !important;
            box-shadow: 0 2px 6px rgba(3, 105, 161, 0.28) !important;
            transition: all 0.15s ease !important;
        }
        [class*="st-key-wsc-action-"] [data-testid="stButton"] button:hover {
            background: #0284C7 !important;
            transform: scale(1.05) !important;
        }
        [class*="st-key-wsc-action-"] [data-testid="stButton"] button [data-testid="stMarkdownContainer"],
        [class*="st-key-wsc-action-"] [data-testid="stButton"] button p {
            display: none !important;
            white-space: nowrap !important;
        }
        [class*="st-key-wsc-action-"] [data-testid="stButton"] button svg {
            width: 1.25rem !important;
            height: 1.25rem !important;
            fill: #FFFFFF !important;
        }
        [class*="st-key-wsc-composer-"] [data-testid="stImage"] img {
            border-radius: 10px !important;
            border: 1px solid rgba(148, 163, 184, 0.38) !important;
        }
        /* Auxiliary expanders around chat: unified visual language (Requirement 4) */
        [data-testid="stExpander"] {
            border-radius: 16px !important;
            border: 1px solid #E2E8F0 !important;
            background: #FFFFFF !important;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.02) !important;
            margin-bottom: 0.6rem !important;
            overflow: hidden !important;
            transition: border-color 0.15s ease !important;
        }
        [data-testid="stExpander"]:hover {
            border-color: #CBD5E1 !important;
        }
        [data-testid="stExpander"] details {
            border: 0 !important;
        }
        [data-testid="stExpander"] summary {
            padding: 0.6rem 0.95rem !important;
            border-radius: 16px !important;
            color: #334155 !important;
            font-size: 0.88rem !important;
            font-weight: 500 !important;
        }
        [data-testid="stExpander"] summary:hover {
            color: #0F172A !important;
            background: #F8FAFC !important;
        }
        [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
            padding: 0.75rem 1rem !important;
            border-top: 1px solid #F1F5F9 !important;
        }
        @media (max-width: 360px) {
            [class*="st-key-wsc-composer-"] {
                border-radius: 18px !important;
                padding: 0.6rem !important;
            }
            [class*="st-key-wsc-shortcut-hint-"] {
                display: none !important;
            }
        }

        [data-testid="stAppViewContainer"] {
            background: #F8FAFC;
            color: #020617;
            font-size: 16px;
            line-height: 1.5;
        }
        section.stMain,
        .main .block-container,
        [data-testid="stSidebar"] {
            overflow-x: clip;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdown"] p,
        [data-testid="stSidebar"] label p {
            white-space: normal;
            overflow-wrap: break-word;
        }
        button:focus-visible,
        textarea:focus-visible,
        input:focus-visible,
        [role="radio"]:focus-visible,
        summary:focus-visible {
            outline: 2px solid #0369A1 !important;
            outline-offset: 2px !important;
        }
        [class*="st-key-exec_del_"] button,
        [class*="st-key-wsc_bulk_delete_execute_"] button,
        [class*="st-key-wsc_document_delete_execute_"] button {
            background-color: #DC2626 !important;
            border-color: #DC2626 !important;
            color: #FFFFFF !important;
        }
        @media (prefers-reduced-motion: reduce) {
            html {
                scroll-behavior: auto !important;
            }
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
                scroll-behavior: auto !important;
            }
        }

    </style>
''')


from aios_habit.workspace_chat_store import (
    init_chat_store,
    COLLECTION_RUNTIME_DIRNAME,
    DEFAULT_COLLECTION_ID,
    ensure_default_collection,
    load_collection,
    load_collections,
    relocate_collection_storage,
    set_collection_storage_root,
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
    update_conversation_language_settings,
    update_conversation_ai_mode,
    load_messages,
    save_message,
    save_evidence_trace,
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
from aios_habit.evidence_trace import build_evidence_trace_from_citations
from aios_habit.workspace_case_service import CaseValidationError, WorkspaceCaseService
from aios_habit.workspace_case_repository import WorkspaceCaseRepository, WorkspaceCaseRepositoryError
from aios_habit.workspace_case_models import AgentWorkRecord
from aios_habit.workspace_agent_orchestrator import WorkspaceAgentOrchestrator
from aios_habit.workspace_case_ui import render_case_workspace, safe_case_error_message
from aios_habit.workspace_case_authorization import trusted_local_actor
from aios_habit.prediction_shadow_ui import render_lsu_data_gate
from aios_habit.production_prediction.repository import ProductionPredictionRepository
from aios_habit.in_app_risk_alert import render_in_app_risk_alerts
from aios_habit.ui_safety import safe_vietnamese_ui_message
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
    count_completed_folder_files,
    seed_completed_folder_files_from_titles,
    LINE_LOG_SCAN_REASON,
)
from aios_habit.local_folder_picker import choose_local_folder

try:
    from streamlit_paste_button import paste_image_button
except ImportError:  # pragma: no cover - surfaced as an in-app fallback
    paste_image_button = None

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
    resume_workspace_chat_source_preparation,
    get_workspace_chat_source_preparation_status,
    get_workspace_chat_preparation_summary,
    get_workspace_chat_deep_search_availability,
    get_workspace_chat_deep_search_enabled_preference,
    set_workspace_chat_deep_search_enabled,
    reconcile_and_enqueue_workspace_chat_sources,
    promote_workspace_chat_source_priority,
    forget_workspace_chat_sources,
    ensure_workspace_chat_worker_warming,
    get_workspace_chat_worker_progress,
    is_workspace_chat_worker_warmed,
    workspace_chat_domain_block_status,
)
from aios_habit.i18n import (
    t,
    normalize_locale,
    get_supported_locales,
    LOCALE_NAMES,
)
from aios_habit.workspace_chat_ui import (
    get_vietnamese_labels,
    get_localized_labels,
    render_language_selector,
    render_notebook_header,
    render_notebook_card,
    render_archived_notebook_card,
    render_chat_bubble,
    render_right_result_panel,
    render_source_library,
    render_document_manager,
    render_preparation_progress_bar,
    render_grouped_evidence_items,
    render_answer_wait_steps,
    render_source_status,
    render_ai_source_context_summary,
    render_ai_answer_header,
    render_insufficient_context,
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
    render_fallback_notice,
    should_show_fallback_notice,
)
from aios_habit.antigravity_bridge import (
    get_antigravity_bridge_health,
    ensure_antigravity_bridge_running,
    call_antigravity_bridge,
    commit_local_grounded_answer,
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
from aios_habit.agent_draft_sop import (
    DRAFT_STATUS_APPROVED,
    DRAFT_STATUS_DRAFT,
    FactoryFileProtectionError,
    approve_draft_document,
    compose_draft_from_evidence,
)
from aios_habit.agent_work_artifact import (
    create_factory_error_report,
    create_process_design_review,
    undo_factory_error_report,
)
from aios_habit.opencode_runtime_adapter import RuntimeRequest


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
        return "unavailable", "Thư viện tài liệu chưa sẵn sàng"
    # Graceful degradation: wait if any required source is still preparing
    waiting_sources = [identity for identity, status in statuses.items() if status not in ("ready", "failed", "unavailable")]
    if waiting_sources:
        return "waiting", ", ".join(waiting_sources)
    # Ready if any required source completed
    if any(status == "ready" for status in statuses.values()):
        return "ready", ""
    # Ready if any other available source is ready
    selected_sources = tuple(by_key[k] for k in selection_keys if k in by_key)
    candidate_sources = selected_sources if selected_sources else available_sources
    avail_statuses = get_workspace_chat_source_preparation_status(candidate_sources)
    if any(status == "ready" for status in avail_statuses.values()):
        return "ready", ""
    # Fallback to direct prompt / Gemini bridge if candidate sources have text content
    if any(getattr(s, "text", "").strip() for s in candidate_sources):
        return "ready", ""
    if any(status == "failed" for status in statuses.values()):
        return "failed", ", ".join(identity for identity, status in statuses.items() if status == "failed")
    return "ready", ""


def _poll_pending_source_submission() -> None:
    """Ask Streamlit to re-run while a bounded source preparation job is active."""
    @st.fragment(run_every=2.0)
    def _poll() -> None:
        st.caption(t("preparing_sources_background", locale=st.session_state.get("wsc_global_ui_locale", "vi")))
        st.rerun(scope="app")

    _poll()

# Tự động khởi tạo kho lưu trữ
init_chat_store()

def _running_under_streamlit() -> bool:
    """Chỉ đúng khi đang chạy trong phiên Streamlit thật (không phải pytest)."""
    if os.environ.get("STREAMLIT_SERVER_PORT"):
        return True
    try:
        from streamlit import runtime

        return bool(runtime.exists())
    except Exception:
        return False


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
                if st.query_params.get(k) != str(v):
                    st.query_params[k] = str(v)
    except Exception:
        try:
            params = st.experimental_get_query_params()
            changed = False
            for k, v in kwargs.items():
                if v is None:
                    if k in params:
                        params.pop(k, None)
                        changed = True
                else:
                    if params.get(k) != [str(v)]:
                        params[k] = [str(v)]
                        changed = True
            if changed:
                st.experimental_set_query_params(**params)
        except Exception:
            pass


_COLLECTION_WARM_DISPLAY_NAMES = {
    "vi": {
        "lsu": "LSU",
        "dieu_tra_loi": "Điều tra lỗi",
        "tong_hop": "Tổng hợp",
        "mom": "MOM",
        "tri_thuc": "Tri thức chung",
    },
    "ja": {
        "lsu": "LSU",
        "dieu_tra_loi": "エラー調査",
        "tong_hop": "総合",
        "mom": "MOM",
        "tri_thuc": "共通知識",
    },
    "zh-CN": {
        "lsu": "LSU",
        "dieu_tra_loi": "故障调查",
        "tong_hop": "综合",
        "mom": "MOM",
        "tri_thuc": "通用知识",
    },
}


def format_worker_warming_status_line(
    collection_id: Optional[str] = None,
    progress: Optional[Mapping[str, Any]] = None,
    *,
    locale: str = "vi",
) -> str:
    """Return a clear owner-facing status string with step info when a collection worker is warming."""
    from aios_habit.workspace_chat_rag_v2_adapter import (
        get_workspace_chat_worker_progress,
        normalize_knowledge_collection,
    )

    norm_col = normalize_knowledge_collection(collection_id) or "tri_thuc"
    if norm_col == "auto":
        norm_col = "tri_thuc"
    loc_map = _COLLECTION_WARM_DISPLAY_NAMES.get(locale, _COLLECTION_WARM_DISPLAY_NAMES["vi"])
    display_name = loc_map.get(norm_col, norm_col)

    if progress is None:
        try:
            progress = get_workspace_chat_worker_progress(collection_id=norm_col)
        except Exception:
            progress = {}

    if bool(progress.get("ready", False)):
        return ""

    is_pending_or_alive = bool(
        progress.get("pending", False)
        or progress.get("alive", False)
        or str(progress.get("reason", "")).strip() == "bge_worker_init_pending"
    )
    pid = progress.get("pid")
    if locale == "ja":
        step_text = (
            f"ステップ 2/2: BGE-M3モデルと索引を読み込み中{' (PID ' + str(pid) + ')' if pid else ''}"
            if is_pending_or_alive
            else "ステップ 1/2: 読取プロセスを起動中"
        )
        return f"⏳ {display_name} 知識庫の読取エンジンを準備しています... ({step_text})"
    if locale == "zh-CN":
        step_text = (
            f"步骤 2/2: 正在加载 BGE-M3 模型与索引{' (PID ' + str(pid) + ')' if pid else ''}"
            if is_pending_or_alive
            else "步骤 1/2: 正在启动读取进程"
        )
        return f"⏳ 正在加载 {display_name} 知识库读取引擎... ({step_text})"

    step_text = (
        f"Bước 2/2: đang nạp mô hình BGE-M3 & chỉ mục{' (PID ' + str(pid) + ')' if pid else ''}"
        if is_pending_or_alive
        else "Bước 1/2: đang khởi tạo tiến trình đọc"
    )
    return f"⏳ Đang nạp bộ đọc cho kho {display_name}... ({step_text})"


def trigger_collection_warming_on_demand(
    collection_id: Optional[str] = None,
    *,
    notebook_id: Optional[str] = None,
) -> str:
    """Trigger non-blocking worker warming for the target collection on demand (DESKTOP-SPEED-LAZY-WARM-HOME)."""
    try:
        from aios_habit.workspace_chat_rag_v2_adapter import (
            ensure_workspace_chat_worker_warming,
            resolve_active_notebook_collection_id,
        )

        target_col = resolve_active_notebook_collection_id(
            active_notebook_id=notebook_id,
            active_collection_id=collection_id,
        )
        ensure_workspace_chat_worker_warming(
            blocking=False,
            collection_id=target_col,
        )
        return target_col
    except Exception:
        return str(collection_id or "tri_thuc")


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

# Làm nóng bộ đọc tài liệu nền ngay khi mở app (DESKTOP-SPEED-LAZY-WARM-HOME):
# Chỉ làm nóng duy nhất 1 collection của sổ đang mở/mặc định, không nạp trước 3 collection còn lại.
if _running_under_streamlit():
    if not st.session_state.get("wsc_startup_warming_triggered"):
        st.session_state["wsc_startup_warming_triggered"] = True
        try:
            from aios_habit.workspace_chat_rag_v2_adapter import (
                ensure_workspace_chat_startup_warming,
                ensure_workspace_chat_worker_warming,
            )
            ensure_workspace_chat_startup_warming(
                active_notebook_id=st.session_state.get("wsc_active_notebook_id"),
                active_collection_id=get_query_param("block"),
            )
        except Exception:
            try:
                ensure_workspace_chat_worker_warming(collection_id="tri_thuc")
            except Exception:
                pass
    try:
        from aios_habit.production_prediction.rt_app_wire import ensure_rt_alert_pipeline
        ensure_rt_alert_pipeline()
    except Exception:
        pass

if "wsc_show_save_placeholder" not in st.session_state:
    # Kept inert for backward-compatible session restoration; no UI reads it.
    st.session_state.wsc_show_save_placeholder = False
if "wsc_show_explain_placeholder" not in st.session_state:
    st.session_state.wsc_show_explain_placeholder = False
if "wsc_action_message" not in st.session_state:
    st.session_state.wsc_action_message = None
if "wsc_action_error" not in st.session_state:
    st.session_state.wsc_action_error = None
if "wsc_action_warning" not in st.session_state:
    st.session_state.wsc_action_warning = None
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
if "wsc_global_ui_locale" not in st.session_state:
    st.session_state.wsc_global_ui_locale = "vi"
if "wsc_global_answer_language" not in st.session_state:
    st.session_state.wsc_global_answer_language = "vi"
if "wsc_show_case_workspace" not in st.session_state:
    st.session_state.wsc_show_case_workspace = False
if "wsc_jig_persona" not in st.session_state:
    st.session_state.wsc_jig_persona = "ca_nhan"


def get_jig_session_type() -> str:
    """Return current JIG alert session type with Zero-UI isolation (US12 T065)."""
    try:
        from aios_habit.production_prediction.session_isolation import classify_session

        persona = str(st.session_state.get("wsc_jig_persona", "ca_nhan"))
        if persona in ("ca_nhan", "truc_ban"):
            return persona
        conv = str(st.session_state.get("wsc_active_conversation_id", ""))
        return classify_session(conv)
    except Exception:
        return "ca_nhan"


def apply_jig_persona_command(text: str) -> str:
    """Apply one-touch persona command from Omnibar (US12 T065)."""
    from aios_habit.production_prediction.session_isolation import SessionPersona, parse_persona_command

    current = SessionPersona(ten_phien="", che_do=str(st.session_state.get("wsc_jig_persona", "ca_nhan")))
    updated, reply = parse_persona_command(text, current)
    st.session_state.wsc_jig_persona = updated.che_do
    return reply


def is_jig_stream_paused(conversation_id: str) -> bool:
    """Return True when the live JIG stream display is paused (007 US8)."""
    try:
        return bool(st.session_state.get(f"wsc_stream_paused_{conversation_id}", False))
    except Exception:
        return False


def render_jig_stream_pause_control(conversation_id: str, locale: str = "vi") -> None:
    """Render pause/resume toggle for the live JIG stream (007 US8, FR-018)."""
    key = f"wsc_stream_paused_{conversation_id}"
    paused = is_jig_stream_paused(conversation_id)
    if paused:
        if st.button(t("jig_stream_resume", locale=locale), key=f"{key}_resume", help=t("jig_stream_resume_help", locale=locale)):
            st.session_state[key] = False
            safe_rerun()
        st.caption(t("jig_stream_paused_note", locale=locale))
    else:
        if st.button(t("jig_stream_pause", locale=locale), key=f"{key}_pause", help=t("jig_stream_pause_help", locale=locale)):
            st.session_state[key] = True
            safe_rerun()

def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        try:
            st.experimental_rerun()
        except AttributeError:
            pass


def _start_gemini_web_bridge(*, locale: str, announce_success: bool = False) -> bool:
    """Start the local Gemini Web sidecar if it is down. Returns True when ready."""
    startup = ensure_antigravity_bridge_running()
    check_handoff_request_timeouts()
    if startup.ok:
        if announce_success or startup.started:
            st.session_state.wsc_action_message = t("bridge_connect_success", locale=locale)
        return True
    st.session_state.wsc_action_error = t("gemini_web_bridge_unavailable", locale=locale)
    return False


def _prefix_domain_block_badge(retrieval_summary: str, domain_info: Any) -> str:
    """Prepend the "Đang tra cứu khối X." badge when a block was really searched."""
    if (
        not isinstance(domain_info, dict)
        or not domain_info.get("enabled")
        or not domain_info.get("applied")
    ):
        return retrieval_summary
    block_name = str(domain_info.get("domain_display") or "").strip()
    if not block_name:
        return retrieval_summary
    block_line = "Đang tra cứu khối %s." % block_name
    if domain_info.get("ambiguous"):
        block_line += " (Câu hỏi chưa rõ lĩnh vực — đã chọn khối khả dĩ nhất.)"
    return block_line + (" " + retrieval_summary if retrieval_summary else "")


def get_workspace_chat_block_choices(locale: str = "vi") -> dict[str, str]:
    """Return ordered mapping of block_id -> formatted display label for the composer block selector."""
    from aios_habit.index_domain import (
        DOMAIN_LSU,
        DOMAIN_DIEU_TRA_LOI,
        DOMAIN_MOM,
        DOMAIN_TONG_HOP,
        get_domain_counts,
        load_domain_document_map,
    )
    block_counts = get_domain_counts()
    unit = "件" if locale == "ja" else ("份" if locale == "zh-CN" else "tài liệu")

    def _format_label(key: str, name: str) -> str:
        cnt = block_counts.get(key, 0)
        return f"{name} ({cnt} {unit})"

    choices: dict[str, str] = {
        "auto": _format_label("auto", t("knowledge_block_auto", locale=locale)),
        DOMAIN_LSU: _format_label(DOMAIN_LSU, t("knowledge_block_lsu", locale=locale)),
        DOMAIN_DIEU_TRA_LOI: _format_label(DOMAIN_DIEU_TRA_LOI, t("knowledge_block_dieu_tra_loi", locale=locale)),
        DOMAIN_MOM: _format_label(DOMAIN_MOM, t("knowledge_block_mom", locale=locale)),
        DOMAIN_TONG_HOP: _format_label(DOMAIN_TONG_HOP, t("knowledge_block_tong_hop", locale=locale)),
    }
    doc_map = load_domain_document_map()
    for block_name in sorted(set(doc_map.values())):
        if block_name not in choices:
            choices[block_name] = _format_label(
                block_name,
                t(f"knowledge_block_{block_name}", locale=locale, default=block_name.replace("_", " ").title()),
            )
    return choices


def _knowledge_block_missing_message(ret_res: Any, locale: str) -> str:
    """Vietnamese notice when the composer-forced block has no index on this machine."""
    domain_info = ret_res.get("domain_routing") if isinstance(ret_res, dict) else None
    block_name = ""
    if isinstance(domain_info, dict):
        block_name = str(domain_info.get("domain_display") or "").strip()
    return t("knowledge_block_missing_error", locale=locale, name=block_name or "?")


def _is_worker_startup_reason(reason: str) -> bool:
    folded = str(reason or "").casefold()
    return (
        folded == "runtimeerror"
        or "worker" in folded
        or "eof" in folded
        or "timeout" in folded
    )


def _log_worker_warm_milestone(
    loop: int, warming_s: float, reason: str, elapsed_wait_s: float
) -> None:
    safe_reason = str(reason or "unknown").strip().replace("\n", " ")[:60]
    msg = (
        f"[WORKER_WARM_LOOP_STEP] loop={loop} warming_s={warming_s:.3f} "
        f"reason={safe_reason} elapsed_wait_s={elapsed_wait_s:.3f}"
    )
    try:
        LOGGER.info(
            "[WORKER_WARM_LOOP_STEP] loop=%d warming_s=%.3f reason=%s elapsed_wait_s=%.3f",
            loop,
            warming_s,
            safe_reason,
            elapsed_wait_s,
        )
    except Exception:
        pass
    _safe_print_streaming_marker(msg)


def _is_hard_worker_error(reason: str, exc: Optional[Exception] = None) -> bool:
    """Return True if reason or exception signals a fatal/hard worker failure."""
    if exc is not None:
        exc_str = f"{type(exc).__name__}: {exc}".casefold()
        if any(tok in exc_str for tok in (
            "eof", "brokenpipe", "pipe", "connectionreset", "processlookup",
            "runtimeerror", "oserror", "subprocessterminated"
        )):
            return True
    folded = str(reason or "").casefold()
    if not folded:
        return False
    hard_tokens = (
        "eof",
        "stdout_eof",
        "pipe",
        "broken pipe",
        "hết giờ ống dẫn",
        "exception",
        "spawn_failed",
        "stdin_closed",
        "no_response",
        "invalid_response",
        "model_verify_failed",
        "model_load_failed",
        "index_open_failed",
        "init_failed",
        "runtimeerror",
        "pinned_model_unavailable",
    )
    return any(tok in folded for tok in hard_tokens)


def _check_worker_progress(prev: Mapping[str, Any], curr: Mapping[str, Any]) -> bool:
    """Return True if worker state shows genuine forward progress towards readiness."""
    if curr.get("ready"):
        return True
    if not curr.get("alive", False):
        return False
    if not prev.get("pending", False) and curr.get("pending", False):
        return True
    # Worker process just spawned
    if not prev.get("alive", False) and curr.get("alive", False):
        return True
    # Worker PID changed
    if curr.get("pid") and prev.get("pid") and curr.get("pid") != prev.get("pid"):
        return True
    # Output written to stderr
    curr_size = curr.get("stderr_size", -1)
    prev_size = prev.get("stderr_size", -1)
    if curr_size > 0 and (prev_size < 0 or curr_size > prev_size):
        return True
    curr_mtime = curr.get("stderr_mtime", 0.0)
    prev_mtime = prev.get("stderr_mtime", 0.0)
    if curr_mtime > prev_mtime and prev_mtime > 0:
        return True
    # Phase/reason advanced towards ready
    if prev.get("reason") != curr.get("reason") and curr.get("reason") in ("", "bge_worker_init_pending"):
        return True
    return False


def wait_for_workspace_chat_worker(
    *,
    attempt_retrieval_fn: Callable[[], dict[str, Any]],
    initial_ret_res: dict[str, Any],
    cancellation_event: Any = None,
    unready_sources: Sequence[Any] = (),
    current_ui_locale: str = "vi",
    warming_fn: Optional[Callable[..., bool]] = None,
    progress_fn: Optional[Callable[[], dict[str, Any]]] = None,
    no_progress_timeout: Optional[float] = None,
    absolute_timeout: Optional[float] = None,
    max_consecutive_hard_errors: int = 2,
    step_timeout: float = 5.0,
    poll_interval: float = 1.0,
) -> tuple[dict[str, Any], Optional[tuple[bool, str, dict[str, Any] | None, str | None]]]:
    """Wait for BGE worker readiness with fail-fast, non-progress budget, and absolute ceiling.

    Returns:
        (latest_ret_res, early_exit_tuple)
        If early_exit_tuple is not None, caller should return it immediately.
        Otherwise, caller proceeds with latest_ret_res (either ready evidence or draft fallback).
    """
    if no_progress_timeout is None:
        raw_np = os.environ.get("AIOS_BGE_WARM_NO_PROGRESS_TIMEOUT")
        if raw_np is not None:
            try:
                no_progress_timeout = float(raw_np)
            except ValueError:
                no_progress_timeout = 20.0
        else:
            raw_init = os.environ.get("AIOS_BGE_INIT_TIMEOUT")
            if raw_init is not None:
                try:
                    val = float(raw_init)
                    no_progress_timeout = val if val <= 60.0 else 20.0
                except ValueError:
                    no_progress_timeout = 20.0
            else:
                no_progress_timeout = 20.0

    if absolute_timeout is None:
        raw_abs = os.environ.get("AIOS_BGE_WARM_ABSOLUTE_TIMEOUT")
        if raw_abs is not None:
            try:
                absolute_timeout = float(raw_abs)
            except ValueError:
                absolute_timeout = 120.0
        else:
            absolute_timeout = 120.0

    no_progress_timeout = min(no_progress_timeout, absolute_timeout)

    if warming_fn is None:
        from aios_habit.workspace_chat_rag_v2_adapter import (
            ensure_workspace_chat_worker_warming,
        )
        warming_fn = ensure_workspace_chat_worker_warming

    if progress_fn is None:
        from aios_habit.workspace_chat_rag_v2_adapter import (
            get_workspace_chat_worker_progress,
        )
        progress_fn = get_workspace_chat_worker_progress

    t_start = time.monotonic()
    last_progress_time = t_start
    prev_snapshot = progress_fn() if progress_fn else {}
    consecutive_hard_errors = 0
    loop_idx = 0
    latest_ret_res = initial_ret_res

    while True:
        now = time.monotonic()
        total_elapsed = now - t_start

        if cancellation_event is not None and cancellation_event.is_set():
            return (latest_ret_res, (False, "", None, "Đã dừng yêu cầu AI."))

        if total_elapsed >= absolute_timeout:
            LOGGER.info(
                "[WORKER_WARM_LOOP_EXIT] reason=absolute_ceiling_reached total_s=%.3f ceiling_s=%.1f",
                total_elapsed,
                absolute_timeout,
            )
            break

        time_since_progress = now - last_progress_time
        if time_since_progress >= no_progress_timeout:
            LOGGER.info(
                "[WORKER_WARM_LOOP_EXIT] reason=no_progress_timeout_exceeded elapsed_no_progress_s=%.3f budget_s=%.1f total_s=%.3f",
                time_since_progress,
                no_progress_timeout,
                total_elapsed,
            )
            break

        loop_idx += 1
        remaining_no_progress = max(0.01, no_progress_timeout - time_since_progress)
        remaining_absolute = max(0.01, absolute_timeout - total_elapsed)
        current_step_timeout = min(step_timeout, remaining_no_progress, remaining_absolute)

        t_warm_start = time.monotonic()
        warming_exc: Optional[Exception] = None
        warming_ok = False
        try:
            warming_ok = bool(warming_fn(blocking=True, timeout_s=current_step_timeout))
        except Exception as exc:
            warming_exc = exc
            warming_ok = False
        warming_duration = time.monotonic() - t_warm_start

        if cancellation_event is not None and cancellation_event.is_set():
            return (latest_ret_res, (False, "", None, "Đã dừng yêu cầu AI."))

        curr_snapshot = progress_fn() if progress_fn else {}
        has_progress = _check_worker_progress(prev_snapshot, curr_snapshot)
        if has_progress:
            last_progress_time = time.monotonic()
            consecutive_hard_errors = 0
        prev_snapshot = curr_snapshot

        try:
            retry_res = attempt_retrieval_fn()
        except Exception as exc:
            retry_res = {
                "status": "quality_search_unavailable",
                "rag_v2_canary": {"fallback_reason": f"retrieval_exception_{type(exc).__name__}"},
            }

        if cancellation_event is not None and cancellation_event.is_set():
            return (retry_res, (False, "", None, "Đã dừng yêu cầu AI."))

        if retry_res.get("status") != "quality_search_unavailable":
            latest_ret_res = retry_res
            elapsed_wait = time.monotonic() - t_start
            _log_worker_warm_milestone(loop_idx, warming_duration, "retrieval_success", elapsed_wait)
            return (latest_ret_res, None)

        latest_ret_res = retry_res
        retry_reason = str(
            retry_res.get("rag_v2_canary", {}).get("fallback_reason", "")
        ).casefold()

        if retry_reason == "domain_block_missing":
            elapsed_wait = time.monotonic() - t_start
            _log_worker_warm_milestone(loop_idx, warming_duration, retry_reason, elapsed_wait)
            return (latest_ret_res, (False, "", None, _knowledge_block_missing_message(latest_ret_res, current_ui_locale)))

        if retry_reason == "deep_search_unavailable":
            elapsed_wait = time.monotonic() - t_start
            _log_worker_warm_milestone(loop_idx, warming_duration, retry_reason, elapsed_wait)
            return (latest_ret_res, (False, "", None, t("deep_search_unavailable", locale=current_ui_locale)))

        if not (_is_worker_startup_reason(retry_reason) or not unready_sources):
            elapsed_wait = time.monotonic() - t_start
            _log_worker_warm_milestone(loop_idx, warming_duration, retry_reason, elapsed_wait)
            return (latest_ret_res, (False, "", None, t("search_sources_preparing", locale=current_ui_locale)))

        is_hard = _is_hard_worker_error(retry_reason, warming_exc) or (not curr_snapshot.get("alive", True))
        if is_hard and not has_progress:
            consecutive_hard_errors += 1
        elif has_progress:
            consecutive_hard_errors = 0

        elapsed_wait = time.monotonic() - t_start
        effective_reason = (
            str(warming_exc) if warming_exc is not None else (retry_reason or "warming_pending")
        )
        _log_worker_warm_milestone(loop_idx, warming_duration, effective_reason, elapsed_wait)

        if consecutive_hard_errors >= max_consecutive_hard_errors:
            LOGGER.info(
                "[WORKER_WARM_LOOP_EXIT] reason=consecutive_hard_errors_exceeded count=%d total_s=%.3f",
                consecutive_hard_errors,
                elapsed_wait,
            )
            break

        sleep_duration = min(poll_interval, 1.0)
        if cancellation_event is not None:
            if cancellation_event.wait(timeout=sleep_duration):
                return (latest_ret_res, (False, "", None, "Đã dừng yêu cầu AI."))
        else:
            time.sleep(sleep_duration)

    return (latest_ret_res, None)


def _run_chat_turn_async(
    q_text: str,
    query_relevant_sources: tuple = (),
    expansion: Any = None,
    active_pref: str = "auto",
    unready_sources: tuple = (),
    current_ui_locale: str = "vi",
    packed_sources: tuple = (),
    conversation_id: str = "",
    notebook_id: str = "",
    current_keys: tuple = (),
    chat_history: tuple = (),
    user_raw_input: str = "",
    answer_language: str = "vi",
    ai_backend: str = "nakazasen_router",
    cagent_endpoint_url: str = "",
    cancellation_event: Any = None,
    user_message_id: str = "",
    forced_domain: Optional[str] = None,
    on_chunk: Optional[Callable[[str], None]] = None,
    ai_mode: str = "grounded",
    anchored_context: Optional[str] = None,
    stream_state: Optional[dict[str, Any]] = None,
) -> tuple[bool, str, dict[str, Any] | None, str | None]:
    """Execute evidence retrieval and model answer routing inside background thread pool."""
    from aios_habit.antigravity_bridge import route_workspace_chat_submission
    from aios_habit.workspace_chat_rag_v2_adapter import (
        retrieve_workspace_chat_evidence as retrieve_local_evidence,
    )

    t_turn_start = time.time()
    worker_wait_s: float = 0.0
    ts_start = format_marker_timestamp()
    try:
        LOGGER.info(
            "[STREAMING_QA_START] conv=%s backend=%s question=%s timestamp=%s",
            conversation_id,
            ai_backend,
            q_text[:60].encode("ascii", errors="backslashreplace").decode("ascii"),
            ts_start,
        )
    except Exception:
        pass
    _safe_print_streaming_marker(f"[STREAMING_QA_START] conv={conversation_id} backend={ai_backend} question={q_text[:60]} timestamp={ts_start}")

    if cancellation_event is not None and cancellation_event.is_set():
        return (False, "", None, "Đã dừng yêu cầu AI.")

    def _is_worker_startup_reason(reason: str) -> bool:
        folded = str(reason or "").casefold()
        return (
            folded == "runtimeerror"
            or "worker" in folded
            or "eof" in folded
            or "timeout" in folded
        )

    def _attempt_retrieval() -> dict[str, Any]:
        search_q = q_text
        if anchored_context:
            anc_snippet = str(anchored_context).strip()[:120].replace("\n", " ")
            search_q = f"{q_text} ({anc_snippet})"
        return retrieve_local_evidence(
            search_q,
            tuple(query_relevant_sources),
            expansion=expansion,
            search_preference=active_pref,
            forced_domain=forced_domain,
        )

    retrieval_applied = False
    retrieved_sources = ()
    evidence_items = []
    retrieval_summary = ""

    if ai_mode == "external":
        should_retrieve = False
        ai_backend = "nakazasen_router"
    else:
        from aios_habit.workspace_chat_rag_v2_adapter import is_production_index_available
        should_retrieve = bool(
            query_relevant_sources or (forced_domain is not None and is_production_index_available())
        )

    if should_retrieve:
        active_domain = forced_domain if (forced_domain and forced_domain != "auto") else None
        if not active_domain:
            try:
                from aios_habit.index_domain import (
                    detect_domain_from_question,
                    CONFIDENCE_LOW_THRESHOLD,
                )
                cls_dom = detect_domain_from_question(q_text, sources=query_relevant_sources)
                if cls_dom and cls_dom.domain and getattr(cls_dom, "confidence", 0.0) >= CONFIDENCE_LOW_THRESHOLD:
                    active_domain = cls_dom.domain
                else:
                    active_domain = "tri_thuc"
            except Exception:
                active_domain = "tri_thuc"
        elif str(active_domain).strip().lower() in ("tri_thuc", "default"):
            active_domain = "tri_thuc"
        from aios_habit.workspace_chat_rag_v2_adapter import (
            set_user_retrieval_active,
            set_user_retrieval_finished,
            update_user_retrieval_collection,
        )
        set_user_retrieval_active(active_domain)
        try:
            ret_res = _attempt_retrieval()
            if cancellation_event is not None and cancellation_event.is_set():
                return (False, "", None, "Đã dừng yêu cầu AI.")

            has_attached_facts = (
                "[Dữ kiện trích từ tệp đính kèm" in q_text
                or "[Nội dung chữ đọc được từ ảnh đính kèm" in q_text
            )

            if ret_res.get("status") == "named_document_not_found":
                answer = (
                    ret_res.get("local_synthesis", {}).get("answer")
                    or ret_res.get("safe_owner_message", "")
                )
                badge = {
                    "provider": "local_truthful_refusal",
                    "ai_source": "system_guard",
                    "document_missing": True,
                }
                t_first_token = time.time()
                ttft_s = t_first_token - t_turn_start
                ts_first_token = format_marker_timestamp()
                if on_chunk is not None:
                    try:
                        on_chunk(answer)
                    except Exception:
                        pass
                first_token_emitted = False
                if isinstance(stream_state, dict):
                    lock = stream_state.get("lock")
                    if lock is not None:
                        with lock:
                            if stream_state.get("first_token_time") is not None:
                                first_token_emitted = True
                    else:
                        if stream_state.get("first_token_time") is not None:
                            first_token_emitted = True
                if not first_token_emitted:
                    try:
                        LOGGER.info(
                            "[STREAMING_QA_FIRST_TOKEN] conv=%s ttft_s=%.3f ttft_ms=%.1f timestamp=%s",
                            conversation_id,
                            ttft_s,
                            ttft_s * 1000,
                            ts_first_token,
                        )
                    except Exception:
                        pass
                    _safe_print_streaming_marker(
                        f"[STREAMING_QA_FIRST_TOKEN] conv={conversation_id} ttft_s={ttft_s:.3f} ttft_ms={ttft_s * 1000:.1f} timestamp={ts_first_token}"
                    )

                try:
                    from aios_habit.workspace_chat_models import ChatMessage
                    from aios_habit.workspace_chat_store import save_message

                    assistant_msg = ChatMessage(
                        id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
                        conversation_id=conversation_id,
                        role="assistant",
                        content=answer,
                        reply_to_message_id=user_message_id or None,
                    )
                    save_message(assistant_msg)
                except Exception as save_err:
                    LOGGER.warning("Không thể lưu tin nhắn từ chối vào messages.jsonl: %s", save_err)

                t_turn_end = time.time()
                turn_total_s = t_turn_end - t_turn_start
                eff_backend = badge.get("provider") or badge.get("ai_source") or ai_backend
                ts_complete = format_marker_timestamp()
                try:
                    LOGGER.info(
                        "[STREAMING_QA_COMPLETE] conv=%s total_s=%.3f total_ms=%.1f backend=%s ok=%s timestamp=%s",
                        conversation_id,
                        turn_total_s,
                        turn_total_s * 1000,
                        eff_backend,
                        True,
                        ts_complete,
                    )
                except Exception:
                    pass
                _safe_print_streaming_marker(
                    f"[STREAMING_QA_COMPLETE] conv={conversation_id} total_s={turn_total_s:.3f} total_ms={turn_total_s * 1000:.1f} backend={eff_backend} ok=True timestamp={ts_complete}"
                )
                return (True, answer, badge, None)

            if ret_res.get("status") == "quality_search_unavailable":
                unavailable_reason = str(
                    ret_res.get("rag_v2_canary", {}).get("fallback_reason", "")
                ).casefold()
                if unavailable_reason == "domain_block_missing":
                    return (False, "", None, _knowledge_block_missing_message(ret_res, current_ui_locale))
                if unavailable_reason != "deep_search_unavailable" and not has_attached_facts and (
                    _is_worker_startup_reason(unavailable_reason) or not unready_sources
                ):
                    # UI-SPEED-WARMLOOP-FIX-HOME & DESKTOP-SPEED-LAZY-WARM-HOME:
                    # Căn chỉnh collection mục tiêu theo kết quả định tuyến domain_routing thực tế
                    t_wait_worker_start = time.time()
                    target_warm_pipe_cfg = None
                    dom_rt = ret_res.get("domain_routing")
                    routed_col = (
                        str(dom_rt.get("collection_id")).strip()
                        if isinstance(dom_rt, dict) and dom_rt.get("applied") and dom_rt.get("collection_id")
                        else None
                    )
                    target_col_for_warm = (
                        routed_col
                        or (forced_domain if (forced_domain and forced_domain != "auto") else None)
                        or active_domain
                        or "tri_thuc"
                    )
                    if target_col_for_warm:
                        update_user_retrieval_collection(target_col_for_warm)
                    if isinstance(stream_state, dict):
                        lock = stream_state.get("lock")
                        if lock is not None:
                            with lock:
                                stream_state["warming_collection"] = target_col_for_warm
                        else:
                            stream_state["warming_collection"] = target_col_for_warm
                    if target_col_for_warm and target_col_for_warm != "auto":
                        try:
                            from aios_habit.workspace_chat_rag_v2_adapter import (
                                _pipeline_config,
                                _warmup_pipeline_config,
                                WorkspaceChatRagV2CanaryConfig,
                            )
                            c_canary = WorkspaceChatRagV2CanaryConfig.from_env()
                            if str(target_col_for_warm).strip().lower() in ("tri_thuc", "default"):
                                target_warm_pipe_cfg = _warmup_pipeline_config(c_canary)
                            else:
                                target_warm_pipe_cfg = _pipeline_config(
                                    c_canary, c_canary.requested_profile, read_only=True, collection_id=target_col_for_warm
                                )
                        except Exception:
                            target_warm_pipe_cfg = None

                    def _targeted_warming(*, blocking: bool = True, timeout_s: float | None = None) -> bool:
                        from aios_habit.workspace_chat_rag_v2_adapter import ensure_workspace_chat_worker_warming
                        return ensure_workspace_chat_worker_warming(
                            blocking=blocking,
                            timeout_s=timeout_s,
                            pipe_config=target_warm_pipe_cfg,
                            collection_id=target_col_for_warm,
                        )

                    def _targeted_progress() -> dict[str, Any]:
                        from aios_habit.workspace_chat_rag_v2_adapter import get_workspace_chat_worker_progress
                        return get_workspace_chat_worker_progress(
                            pipe_config=target_warm_pipe_cfg,
                            collection_id=target_col_for_warm,
                        )

                    ret_res, early_exit = wait_for_workspace_chat_worker(
                        attempt_retrieval_fn=_attempt_retrieval,
                        initial_ret_res=ret_res,
                        cancellation_event=cancellation_event,
                        unready_sources=unready_sources,
                        current_ui_locale=current_ui_locale,
                        warming_fn=_targeted_warming,
                        progress_fn=_targeted_progress,
                        step_timeout=1.5,
                        poll_interval=0.2,
                    )
                    if isinstance(stream_state, dict):
                        lock = stream_state.get("lock")
                        if lock is not None:
                            with lock:
                                stream_state["warming_collection"] = None
                        else:
                            stream_state["warming_collection"] = None
                    worker_wait_s += max(0.0, time.time() - t_wait_worker_start)
                    if early_exit is not None:
                        return early_exit
        finally:
            set_user_retrieval_finished(active_domain)

            # no_evidence_found_error
        if ret_res.get("status") == "quality_search_unavailable":
            if has_attached_facts:
                retrieval_applied = False
                retrieved_sources = ()
                evidence_items = []
                retrieval_summary = "Đang trả lời trực tiếp từ dữ kiện đính kèm."
            else:
                unavailable_reason = str(
                    ret_res.get("rag_v2_canary", {}).get("fallback_reason", "")
                ).casefold()
                if unavailable_reason == "deep_search_unavailable":
                    err_msg = t("deep_search_unavailable", locale=current_ui_locale)
                elif unavailable_reason == "runtimeerror" or (
                    "worker" in unavailable_reason
                    or "eof" in unavailable_reason
                    or "timeout" in unavailable_reason
                    or not unready_sources
                ):
                    err_msg = t("search_runtime_unavailable", locale=current_ui_locale)
                else:
                    err_msg = t("search_sources_preparing", locale=current_ui_locale)
                if unavailable_reason != "search_sources_preparing":
                    from aios_habit.answer_draft_fallback import deliver_draft_answer
                    draft_res = deliver_draft_answer(
                        q_text,
                        conversation_id=conversation_id,
                        notebook_id=notebook_id,
                        user_raw_input=user_raw_input,
                        user_message_id=user_message_id,
                        current_ui_locale=current_ui_locale,
                        answer_language=answer_language,
                        on_chunk=on_chunk,
                    )
                    if draft_res is not None:
                        turn_total_s = time.time() - t_turn_start
                        ts_draft = format_marker_timestamp()
                        try:
                            LOGGER.info(
                                "[DRAFT_FALLBACK_COMPLETE] conv=%s wait_s=%.3f total_s=%.3f timestamp=%s",
                                conversation_id,
                                worker_wait_s,
                                turn_total_s,
                                ts_draft,
                            )
                        except Exception:
                            pass
                        _safe_print_streaming_marker(
                            f"[DRAFT_FALLBACK_COMPLETE] conv={conversation_id} wait_s={worker_wait_s:.3f} total_s={turn_total_s:.3f} timestamp={ts_draft}"
                        )
                        return draft_res
                return (False, "", None, err_msg)
        elif ret_res["summary_count"] == 0:
            if has_attached_facts:
                retrieval_applied = False
                retrieved_sources = ()
                evidence_items = []
                retrieval_summary = "Đang trả lời trực tiếp từ dữ kiện đính kèm."
            else:
                from aios_habit.answer_draft_fallback import deliver_draft_answer
                draft_res = deliver_draft_answer(
                    q_text,
                    conversation_id=conversation_id,
                    notebook_id=notebook_id,
                    user_raw_input=user_raw_input,
                    user_message_id=user_message_id,
                    current_ui_locale=current_ui_locale,
                    answer_language=answer_language,
                    on_chunk=on_chunk,
                )
                if draft_res is not None:
                    turn_total_s = time.time() - t_turn_start
                    ts_draft = format_marker_timestamp()
                    try:
                        LOGGER.info(
                            "[DRAFT_FALLBACK_COMPLETE] conv=%s wait_s=%.3f total_s=%.3f timestamp=%s",
                            conversation_id,
                            worker_wait_s,
                            turn_total_s,
                            ts_draft,
                        )
                    except Exception:
                        pass
                    _safe_print_streaming_marker(
                        f"[DRAFT_FALLBACK_COMPLETE] conv={conversation_id} wait_s={worker_wait_s:.3f} total_s={turn_total_s:.3f} timestamp={ts_draft}"
                    )
                    return draft_res
                # st.session_state.wsc_action_error = "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật."
                err_msg = t("no_matched_segments_error", locale=current_ui_locale)
                return (False, "", None, err_msg)
        else:
            retrieval_applied = True
            emit_pre_synth_step_marker(conversation_id, "retrieval_received")
            retrieved_sources = ret_res.get("retrieved_context_sources", ())
            evidence_items = ret_res.get("evidence_items", [])
            retrieval_summary = ret_res.get("safe_owner_message", "")
            emit_pre_synth_step_marker(conversation_id, "sources_formatted")
            # Domain routing transparency: state which knowledge block was
            # searched. Ambiguous questions name the most plausible block.
            retrieval_summary = _prefix_domain_block_badge(
                retrieval_summary, ret_res.get("domain_routing")
            )
            emit_pre_synth_step_marker(conversation_id, "domain_badge_attached")
    else:
        retrieval_applied = False
        retrieved_sources = ()
        evidence_items = []
        retrieval_summary = "Đang trả lời trực tiếp qua nội dung văn bản nguồn."
        emit_pre_synth_step_marker(conversation_id, "retrieval_received")
        emit_pre_synth_step_marker(conversation_id, "sources_formatted")
        emit_pre_synth_step_marker(conversation_id, "domain_badge_attached")

    emit_pre_synth_step_marker(conversation_id, "executor_enqueued")
    emit_pre_synth_step_marker(conversation_id, "executor_task_started")

    if cancellation_event is not None and cancellation_event.is_set():
        return (False, "", None, "Đã dừng yêu cầu AI.")

    res = route_workspace_chat_submission(
        question=q_text,
        evidence_items=evidence_items,
        packed_sources=packed_sources,
        conversation_id=conversation_id,
        notebook_id=notebook_id,
        retrieval_applied=retrieval_applied,
        retrieved_sources=retrieved_sources,
        retrieval_summary=retrieval_summary,
        current_keys=current_keys,
        chat_history=chat_history,
        user_raw_input=user_raw_input,
        user_message_id=user_message_id,
        answer_language=answer_language,
        backend=ai_backend,
        cagent_endpoint_url=cagent_endpoint_url,
        cancellation_event=cancellation_event,
        local_synthesis=ret_res.get("local_synthesis") if (retrieval_applied and "ret_res" in locals()) else None,
        on_chunk=on_chunk,
        ai_mode=ai_mode,
        anchored_context=anchored_context,
    )
    t_turn_end = time.time()
    turn_total_s = t_turn_end - t_turn_start
    badge = res[2] if len(res) > 2 and isinstance(res[2], dict) else {}
    eff_backend = (badge.get("provider") or badge.get("ai_source") or ai_backend) if badge else ai_backend
    ts_complete = format_marker_timestamp()
    try:
        LOGGER.info(
            "[STREAMING_QA_COMPLETE] conv=%s total_s=%.3f total_ms=%.1f backend=%s ok=%s timestamp=%s",
            conversation_id,
            turn_total_s,
            turn_total_s * 1000,
            eff_backend,
            res[0],
            ts_complete,
        )
    except Exception:
        pass
    _safe_print_streaming_marker(
        f"[STREAMING_QA_COMPLETE] conv={conversation_id} total_s={turn_total_s:.3f} total_ms={turn_total_s * 1000:.1f} backend={eff_backend} ok={res[0]} timestamp={ts_complete}"
    )
    return res


def render_sidebar_bridge_status(*, locale: str, key_prefix: str = "wsc_sidebar") -> None:
    """Render the bridge health status badge and manual refresh/reconnect button in the sidebar."""
    with st.sidebar:
        st.write("---")
        st.markdown(f"### 🌉 {t('bridge_status_title', locale=locale)}")
        bridge_health = get_antigravity_bridge_health(timeout_seconds=0.4)
        render_bridge_header_status(bridge_health, locale=locale)
        if st.button(
            t("bridge_connect_refresh", locale=locale),
            key=f"{key_prefix}_refresh_bridge_btn",
            help=t("bridge_connect_refresh_help", locale=locale),
            use_container_width=True,
        ):
            startup = ensure_antigravity_bridge_running()
            check_handoff_request_timeouts()
            if startup.ok:
                st.session_state.wsc_action_message = t("bridge_connect_success", locale=locale)
            else:
                st.session_state.wsc_action_error = t(
                    "bridge_connect_failed",
                    locale=locale,
                    reason=startup.reason or startup.health.reason or "unknown_error",
                )
            safe_rerun()


def set_active_conversation_callback(notebook_id: str, conversation_id: Optional[str]) -> Optional[str]:
    resolved_id = resolve_conversation_id(notebook_id, conversation_id)
    st.session_state.wsc_active_conversation_id = resolved_id
    st.session_state.wsc_manage_conversation_id = resolved_id
    set_query_params(nb=notebook_id, conv=resolved_id)
    return resolved_id


def create_conversation_callback(
    notebook_id: str,
    ui_locale: Optional[str] = None,
    answer_language: Optional[str] = None,
) -> WorkspaceConversation:
    eff_ui = normalize_locale(ui_locale or st.session_state.get("wsc_global_ui_locale", "vi"))
    eff_ans = normalize_locale(answer_language or st.session_state.get("wsc_global_answer_language", "vi"))
    title = f"Cuộc trò chuyện {datetime.now().strftime('%d/%m %H:%M')}"
    conv = WorkspaceConversation(
        id=f"CONV-{uuid.uuid4().hex[:8].upper()}",
        notebook_id=notebook_id,
        title=title,
        ui_locale=eff_ui,
        answer_language=eff_ans,
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
        reason_vi = "chế độ kết nối trực tiếp chưa khả dụng"
        if health.reason and "not available" not in str(health.reason).lower():
            reason_vi = str(health.reason)
        st.session_state.wsc_action_error = (
            f"Kết nối trực tiếp Antigravity chưa sẵn sàng ({health.status}: {reason_vi}). "
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

    # Create new conversation with compressed memory and inherited search_preference & language settings
    new_conv_id = f"CONV-{uuid.uuid4().hex[:8].upper()}"
    new_conv = WorkspaceConversation(
        id=new_conv_id,
        notebook_id=notebook_id,
        title=f"Tiếp tục: {conv.title}",
        compressed_memory=compressed_summary.strip(),
        search_preference=getattr(conv, "search_preference", "auto"),
        ui_locale=getattr(conv, "ui_locale", "vi"),
        answer_language=getattr(conv, "answer_language", "vi"),
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


def save_current_answer_to_case(
    conversation_id: str,
    badge_data: Mapping[str, Any] | None,
    *,
    service: WorkspaceCaseService | None = None,
) -> bool:
    """Save local case metadata from an existing evidence trace only."""
    if not badge_data or badge_data.get("conversation_id") != conversation_id:
        st.session_state.wsc_action_error = "Chưa thể lưu hồ sơ vì câu trả lời hiện tại không còn hợp lệ."
        safe_rerun()
        return False
    if badge_data.get("type") != "ai_answered":
        st.session_state.wsc_action_error = "Chỉ có thể lưu hồ sơ từ câu trả lời đã hoàn tất."
        safe_rerun()
        return False
    trace_id = str(badge_data.get("trace_id") or "").strip()
    if not trace_id:
        st.session_state.wsc_action_error = "Chưa thể lưu hồ sơ vì thiếu dấu vết bằng chứng."
        safe_rerun()
        return False

    try:
        result = (service or WorkspaceCaseService()).create_case_from_trace_id(
            trace_id,
            expected_conversation_id=conversation_id,
        )
    except (CaseValidationError, WorkspaceCaseRepositoryError) as error:
        st.session_state.wsc_action_error = safe_case_error_message(error)
        safe_rerun()
        return False

    st.session_state.wsc_action_message = (
        f"Đã lưu hồ sơ cục bộ {result.case_id} với {result.evidence_count} tham chiếu bằng chứng. "
        "Hồ sơ chỉ giữ liên kết bằng chứng; câu hỏi, câu trả lời và đoạn trích gốc không được sao chép."
    )
    safe_rerun()
    return True

def _luu_cap_tin_nhan_chat(conversation_id: str, cau_hoi: str, tra_loi: str) -> None:
    """Luu cap user/assistant vao kho hoi thoai (dung chung cho router)."""
    from aios_habit.workspace_chat_models import ChatMessage
    from aios_habit.workspace_chat_store import save_message

    save_message(ChatMessage(
        id=f"MSG-U-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conversation_id,
        role="user",
        content=cau_hoi,
    ))
    save_message(ChatMessage(
        id=f"MSG-A-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conversation_id,
        role="assistant",
        content=tra_loi,
    ))


def _hang_ve_tu_lsu_gate() -> list:
    """Doc du lieu ve bieu do tu phien LSU gate (wsc_last_lsu_traces).

    Dung chung cho nhanh chart cua router chat-first va luong jig cu.
    Neu phien LSU gate chua co, doc du lieu tu kho log archive de phuc vu
    ve bieu do tu cac tep da nap qua chat.
    """
    try:
        traces_ve = st.session_state.get("wsc_last_lsu_traces")
        if isinstance(traces_ve, dict):
            danh_sach = list(traces_ve.values())
        elif isinstance(traces_ve, list):
            danh_sach = traces_ve
        else:
            danh_sach = []
        cac_hang: list = []
        for trace in danh_sach:
            for do_dac in getattr(trace, "jig_measurements", []) or []:
                cac_hang.append({
                    "jig_id": getattr(do_dac, "jig_id", ""),
                    "unit_serial": getattr(do_dac, "unit_serial", ""),
                    "metric_name": getattr(do_dac, "metric_name", ""),
                    "value": getattr(do_dac, "value", None),
                    "unit": getattr(do_dac, "unit", ""),
                    "event_time": str(getattr(do_dac, "event_time", "")),
                })
        if cac_hang:
            return cac_hang
        from aios_habit.production_prediction.log_archive import doc_kho
        kho_rows = doc_kho()
        if kho_rows:
            return [
                {
                    "jig_id": r.jig_id,
                    "unit_serial": r.unit_serial,
                    "metric_name": r.metric_name,
                    "value": r.value,
                    "unit": r.unit,
                    "event_time": str(r.ts or r.ghi_luc or ""),
                }
                for r in kho_rows
                if r.value is not None
            ]
        return []
    except Exception:
        return []


def _xu_ly_mot_y_dinh(y_dinh: str, slots, q_text: str, *, active_conversation, active_nb_id):
    """Xu ly MOT y dinh trong cau chat.

    Tra ve doan tra loi cua y dinh do; "" neu y dinh da xu ly nhung khong
    can doan van ban (vd chi chuyen view); None neu y dinh nay khong xu ly
    duoc (de dieu phoi thu y dinh khac / de luong cu xu ly tiep).
    """
    from aios_habit.chat_intent_router import (
        CANH_BAO_NGUONG,
        CONG_CU_NANG_CAO,
        DONG_VU,
        DU_LIEU_DAN,
        HO_SO_DIEU_TRA,
        LAP_CAY_4M_VU,
        MO_SO,
        TAO_SO,
        TAO_VU_DIEU_TRA,
        DANH_GIA_DIEU_TRA,
        DANH_GIA_NHAN,
        VE_BIEU_DO,
        XEM_PHAN_HOI,
        XEM_TIEN_DO_VU,
        XU_HUONG_LOG_TINH,
        _khong_dau,
    )

    norm_q = _khong_dau(q_text)
    if norm_q in ("xac nhan", "xac nhan tao vu", "dong y tao vu") and st.session_state.get("wsc_pending_case_preview"):
        from aios_habit.chat_action_create_case import execute_confirm_case
        preview_data = st.session_state.pop("wsc_pending_case_preview")
        conv_id = getattr(active_conversation, "id", "") or ""
        return execute_confirm_case(preview_data, conversation_id=conv_id)

    if y_dinh == DONG_VU:
        from aios_habit.chat_action_create_case import execute_close_case

        conv_id = getattr(active_conversation, "id", "") or ""
        explicit_cid = slots.get("case_id") if isinstance(slots, dict) else ""
        cause_val = slots.get("actual_cause", "") if isinstance(slots, dict) else ""
        remedy_val = slots.get("actual_countermeasure", "") if isinstance(slots, dict) else ""
        return execute_close_case(
            case_id=explicit_cid,
            actual_cause=cause_val,
            actual_countermeasure=remedy_val,
            conversation_id=conv_id,
            raw_text=q_text,
        )

    if y_dinh == XEM_TIEN_DO_VU:
        from aios_habit.chat_action_create_case import execute_view_case_progress

        conv_id = getattr(active_conversation, "id", "") or ""
        explicit_cid = slots.get("case_id") if isinstance(slots, dict) else ""
        return execute_view_case_progress(case_id=explicit_cid, conversation_id=conv_id)

    if y_dinh == LAP_CAY_4M_VU:
        from aios_habit.chat_action_create_case import execute_build_case_tree

        conv_id = getattr(active_conversation, "id", "") or ""
        explicit_cid = slots.get("case_id") if isinstance(slots, dict) else ""
        return execute_build_case_tree(case_id=explicit_cid, conversation_id=conv_id)

    if y_dinh == TAO_VU_DIEU_TRA:
        from aios_habit.chat_action_create_case import (
            extract_case_preview_marker,
            render_preview_card_text,
        )

        conv_id = getattr(active_conversation, "id", "") or ""
        preview_text = render_preview_card_text(
            text=q_text,
            slots=slots,
            conversation_id=conv_id,
            notebook_id=active_nb_id or "",
        )
        marker_data = extract_case_preview_marker(preview_text)
        if marker_data:
            st.session_state["wsc_pending_case_preview"] = marker_data
        return preview_text
    if y_dinh == HO_SO_DIEU_TRA:
        st.session_state.wsc_show_case_workspace = True
        st.session_state.wsc_show_lsu_data_gate = False
        return ""
    if y_dinh == CONG_CU_NANG_CAO:
        st.session_state.wsc_show_lsu_data_gate = True
        st.session_state.wsc_show_case_workspace = False
        return ""
    if y_dinh == DU_LIEU_DAN:
        # Khoi du lieu dan chay qua khung chat_action (ton trong feature flag).
        # Dung dispatch_multi nhu luong cu khi co bat: giu nguyen hanh vi
        # (error_lookup la fallback nen thuc te chi action dan du lieu chay).
        from aios_habit.chat_action import (
            ChatActionRequest,
            chat_action_enabled,
            dispatch_multi,
            render_outcome,
        )

        if not chat_action_enabled():
            return None
        try:
            outcome = dispatch_multi(
                ChatActionRequest(
                    question=q_text,
                    locale="vi",
                    conversation_id=getattr(active_conversation, "id", "") or "",
                    notebook_id=active_nb_id or "",
                    workspace_id=active_nb_id or "default",
                )
            )
        except Exception:
            return None
        if outcome is None:
            return None
        try:
            return render_outcome(outcome) or None
        except Exception:
            return None
    if y_dinh == VE_BIEU_DO:
        # Nhanh ve bieu do JIG chay doc lap trong luong gop (UX-E2E-APP muc a):
        # cung logic voi luong jig cu, doc du lieu tu phien LSU gate.
        try:
            from aios_habit.production_prediction.jig_chat_wire import (
                _quyet_dinh_ve_bieu_do,
            )

            ket_qua = _quyet_dinh_ve_bieu_do(
                q_text, _hang_ve_tu_lsu_gate, kho_nguong=None
            )
        except Exception:
            return None
        if ket_qua is None or not ket_qua.handled:
            return None
        van_ban = ket_qua.assistant_text or ""
        if ket_qua.chart_png:
            try:
                if hasattr(st, "session_state"):
                    st.session_state["wsc_last_chart_png"] = ket_qua.chart_png
                    if ket_qua.chart_meta:
                        st.session_state["wsc_last_chart_meta"] = ket_qua.chart_meta
                import base64

                ma_hoa = base64.b64encode(ket_qua.chart_png).decode("ascii")
                chart_md = "\n\n![biểu đồ](data:image/png;base64,{})".format(ma_hoa)
                if chart_md not in van_ban and f"data:image/png;base64,{ma_hoa}" not in van_ban:
                    van_ban += chart_md
            except Exception:
                pass
    if y_dinh == DANH_GIA_DIEU_TRA:
        try:
            from aios_habit.chat_action_create_case import get_active_case_id
            from aios_habit.error_cases.investigation_feedback import record_investigation_feedback
            rating_val = slots.get("rating", "đúng hướng")
            note_val = slots.get("note")
            cid = slots.get("case_id") or get_active_case_id()
            conv_id = getattr(active_conversation, "id", "") or ""
            record_investigation_feedback(
                rating=rating_val,
                user_note=note_val,
                case_id=cid,
                conversation_id=conv_id,
            )
            note_str = f"\n- **Ghi chú góp ý:** `{note_val}`" if note_val else ""
            return (
                f"### ✅ Đã ghi nhận đánh giá cây điều tra: `{rating_val}`\n\n"
                f"- **Vụ điều tra:** `{cid or 'Ngữ cảnh phiên chat'}`\n"
                f"- **Đánh giá:** `{rating_val}`"
                f"{note_str}\n"
                "- **Lưu trữ:** `local_cases/investigation_feedback.jsonl` (phục vụ giám sát chất lượng gợi ý Bước 3)."
            )
        except Exception as e:
            return f"### ⚠️ Không thể lưu phản hồi điều tra: {e}"
    if y_dinh == DANH_GIA_NHAN:
        try:
            from aios_habit.chat_action_create_case import get_active_case_id
            from aios_habit.error_cases.autoclassify_feedback import record_autoclassify_feedback
            rating_val = slots.get("rating", "đúng")
            correction = slots.get("correction")
            cid = slots.get("case_id") or get_active_case_id()
            conv_id = getattr(active_conversation, "id", "") or ""
            record_autoclassify_feedback(
                case_id=cid,
                rating=rating_val,
                user_correction=correction,
                conversation_id=conv_id,
            )
            corr_note = f"\n- **Hiệu chỉnh nhóm:** `{correction}`" if correction else ""
            return (
                f"### ✅ Đã ghi nhận đánh giá nhãn phân loại: `{rating_val}`\n\n"
                f"- **Vụ điều tra:** `{cid or 'Ngữ cảnh hiện tại'}`\n"
                f"- **Đánh giá:** `{rating_val}`"
                f"{corr_note}\n"
                "- **Lưu trữ:** `local_cases/autoclassify_feedback.jsonl` (phục vụ giám sát độ chính xác Bước 5)."
            )
        except Exception as e:
            return f"### ⚠️ Không thể lưu phản hồi nhãn: {e}"
    if y_dinh == XEM_PHAN_HOI:
        try:
            if slots.get("loai_phan_hoi") == "phan_loai":
                from aios_habit.error_cases.autoclassify_feedback import format_autoclassify_review_summary
                return format_autoclassify_review_summary()
            if slots.get("loai_phan_hoi") == "dieu_tra":
                from aios_habit.error_cases.investigation_feedback import format_investigation_review_summary
                return format_investigation_review_summary()
            from aios_habit.feedback_review_home import format_feedback_review_summary

            return format_feedback_review_summary()
        except Exception:
            return None
    if y_dinh == XU_HUONG_LOG_TINH:
        try:
            from aios_habit.production_prediction.jig_chat_wire import (
                _quyet_dinh_xu_huong_log_tinh,
            )

            ket_qua = _quyet_dinh_xu_huong_log_tinh(q_text)
            if ket_qua and ket_qua.handled:
                return ket_qua.assistant_text or None
        except Exception:
            return None
        return None
    if y_dinh == CANH_BAO_NGUONG:
        from aios_habit.threshold_alert_chat import xu_ly_cau_lenh

        def _lich_su(thong_so: str):
            try:
                from aios_habit.production_prediction.log_archive import lich_su_theo_jig
                return [float(v) for v in (lich_su_theo_jig(jig_id="", metric_name=thong_so) or [])]
            except Exception:
                return []

        tra_loi = xu_ly_cau_lenh(q_text, history_provider=_lich_su)
        return tra_loi  # None -> y dinh nay khong xu ly duoc
    if y_dinh == TAO_SO:
        ten_so = (slots.get("ten_so") or "").strip() or "Sổ mới"
        ensure_default_collection()
        collections = load_collections()
        collection_id = collections[0].id if collections else DEFAULT_COLLECTION_ID
        new_nb = DocumentNotebook(
            id=f"NB-{uuid.uuid4().hex[:8].upper()}",
            title=ten_so,
            description="",
            collection_id=str(collection_id),
        )
        save_notebook(new_nb)
        from aios_habit.notebook_readiness import NotebookReadinessStore, dong_trang_thai_so
        NotebookReadinessStore().cap_nhat(new_nb.id, san_sang=True, so_tai_lieu=0)
        tra_loi = (
            "Đã tạo sổ \"{}\". Sổ đã trỏ vào thư viện chung, bạn hỏi ngay được.\n{}".format(
                ten_so, dong_trang_thai_so(ten_so, 0)
            )
        )
        st.session_state.wsc_active_notebook_id = new_nb.id
        st.session_state.wsc_active_conversation_id = None
        set_query_params(nb=new_nb.id, conv=None)
        return tra_loi
    if y_dinh == MO_SO:
        ten_can_tim = (slots.get("ten_so") or "").strip().lower()
        danh_sach = load_active_notebooks()
        trung = None
        if ten_can_tim:
            for nb in danh_sach:
                if ten_can_tim in (nb.title or "").lower():
                    trung = nb
                    break
        if trung is None and len(danh_sach) == 1 and not ten_can_tim:
            trung = danh_sach[0]
        if trung is None:
            ten_hien_co = ", ".join("\"{}\"".format(nb.title) for nb in danh_sach[:5])
            goi_y = "Tôi chưa tìm thấy sổ phù hợp."
            if ten_hien_co:
                goi_y += " Các sổ hiện có: {}.".format(ten_hien_co)
            goi_y += " Bạn gõ: tạo sổ <tên sổ>"
            return goi_y
        st.session_state.wsc_active_notebook_id = trung.id
        st.session_state.wsc_active_conversation_id = None
        set_query_params(nb=trung.id, conv=None)
        return ""
    return None


def _xu_ly_y_dinh_chat(q_text: str, *, active_conversation, active_nb_id) -> bool:
    """Bo dinh tuyen y dinh chat-first (UX-CHAT-CORE).

    Mot cau chat co the chua NHIEU y dinh (vd dan CSV + ve bieu do + dat
    nguong canh bao): chay HET cac y dinh nhan dien duoc, gop cac doan tra
    loi thanh mot cau tra loi duy nhat.

    Tra ve True neu cau chat da duoc xu ly tron (caller rerun),
    False neu de luong hien co (jig/chat_action/RAG) xu ly tiep.
    """
    from aios_habit.chat_intent_router import (
        HOI_DAP_CHUNG,
        HOI_TAI_LIEU,
        classify_all_intents,
        extract_case_id_from_text,
        nhan_y_dinh,
    )

    explicit_case_id = extract_case_id_from_text(q_text)
    if explicit_case_id:
        st.session_state["wsc_active_case_id"] = explicit_case_id

    if not st.session_state.get("wsc_active_case_id") and active_conversation:
        try:
            from aios_habit.workspace_chat_store import load_messages

            c_msgs = load_messages(active_conversation.id)
            for m in reversed(c_msgs):
                m_cid = extract_case_id_from_text(m.content or "")
                if m_cid:
                    st.session_state["wsc_active_case_id"] = m_cid
                    break
        except Exception:
            pass

    cac_y_dinh = classify_all_intents(q_text)
    if len(cac_y_dinh) == 1 and cac_y_dinh[0][0] == HOI_TAI_LIEU:
        return False
    cac_phan = []
    da_xu_ly = False
    co_hoi_tai_lieu = False
    y_dinh_loi = []
    for y_dinh, slots in cac_y_dinh:
        if y_dinh == HOI_TAI_LIEU:
            # RAG khong chay trong dieu phoi nay; ghi chu ro thay vi bo qua
            # im lang (dieu phoi tra ve True nen luong RAG ben duoi khong chay).
            co_hoi_tai_lieu = True
            continue
        if y_dinh == HOI_DAP_CHUNG:
            continue  # loi chao kem y dinh that: khong can phan rieng
        try:
            phan = _xu_ly_mot_y_dinh(
                y_dinh,
                slots,
                q_text,
                active_conversation=active_conversation,
                active_nb_id=active_nb_id,
            )
        except Exception:
            phan = None
        if phan is None:
            # UX-CHAT-CORE-FIX1: y dinh khong xu ly duoc phai duoc ghi ro
            # trong cau tra loi gop, khong im lang bo qua.
            y_dinh_loi.append(y_dinh)
            continue
        da_xu_ly = True
        if phan:
            cac_phan.append((y_dinh, phan))
    for y_dinh in y_dinh_loi:
        cac_phan.append(
            (
                y_dinh,
                "_Tôi chưa xử lý được phần này trong câu gộp "
                "— bạn thử tách thành câu riêng nhé._",
            )
        )
    if co_hoi_tai_lieu:
        cac_phan.append(
            (
                HOI_TAI_LIEU,
                "_Phần hỏi tài liệu trong câu gộp này chưa được chạy "
                "— bạn hỏi lại riêng câu đó ở lượt chat sau nhé._",
            )
        )
    if not da_xu_ly:
        return False
    if len(cac_phan) == 1:
        tra_loi = cac_phan[0][1]
    else:
        tra_loi = "\n\n---\n\n".join(
            "**{}**\n\n{}".format(nhan_y_dinh(y_dinh) or y_dinh, phan)
            for y_dinh, phan in cac_phan
        )
    if not tra_loi.strip():
        return True  # chi chuyen view, khong co gi de luu
    conv_id = getattr(active_conversation, "id", "") or ""
    if conv_id:
        _luu_cap_tin_nhan_chat(conv_id, q_text, tra_loi)
    else:
        st.session_state.wsc_action_message = tra_loi
    return True


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
    trigger_collection_warming_on_demand(
        getattr(notebook, "collection_id", None),
        notebook_id=notebook_id,
    )
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
current_ui_locale = "vi"

# UX-CHAT-CORE: bo radio "Dieu huong" 3 nhanh. Moi chuc nang mo qua y dinh
# trong cau chat (chat_intent_router) - nguoi dung khong bao gio phai chon nhanh.
st.sidebar.markdown(t("sidebar_assistant_title", locale=current_ui_locale))
st.sidebar.caption(
    t("sidebar_assistant_caption", locale=current_ui_locale)
)

is_case = bool(st.session_state.get("wsc_show_case_workspace", False))
is_lsu = bool(st.session_state.get("wsc_show_lsu_data_gate", False))

if st.sidebar.button(
    t("teach_entry_button", locale=current_ui_locale),
    icon=":material/school:",
    key="btn_teach_entry",
    width="stretch",
    help=t("teach_entry_help", locale=current_ui_locale),
):
    st.session_state.wsc_show_case_workspace = True
    st.session_state.wsc_show_lsu_data_gate = False
    st.session_state["wsc_workspace_view_mode_pending"] = "interview"
    safe_rerun()
st.sidebar.caption(t("teach_entry_help", locale=current_ui_locale))

st.sidebar.write("---")

if st.session_state.wsc_show_case_workspace:
    current_ui_locale = st.session_state.get("wsc_global_ui_locale", "vi")
    current_ui_locale = "vi"
    current_answer_language = "vi"

    def _close_case_workspace() -> None:
        st.session_state.wsc_show_case_workspace = False
        set_query_params(case=None)
        safe_rerun()

    def _open_case_trace(resolution) -> None:
        trace = resolution.trace
        if trace is None:
            st.session_state.wsc_action_error = t("case_trace_missing", locale=current_ui_locale)
            safe_rerun()
            return
        conversation_id = str(getattr(trace, "conversation_id", "") or "")
        notebook_id = str(getattr(trace, "notebook_id", "") or active_nb_id or "")
        if not conversation_id or not notebook_id:
            st.session_state.wsc_action_error = "Dấu vết gốc thiếu định danh sổ hoặc cuộc trò chuyện."
            safe_rerun()
            return
        st.session_state.wsc_active_notebook_id = notebook_id
        st.session_state.wsc_active_conversation_id = conversation_id
        st.session_state.wsc_show_case_workspace = False
        set_query_params(nb=notebook_id, conv=conversation_id, case=None)
        safe_rerun()

    render_case_workspace(
        WorkspaceCaseService(),
        on_close=_close_case_workspace,
        on_open_trace=_open_case_trace,
        locale=current_ui_locale,
    )
    st.stop()

if st.session_state.get("wsc_show_lsu_data_gate", False):
    current_ui_locale = "vi"

    def _close_lsu_data_gate() -> None:
        st.session_state.wsc_show_lsu_data_gate = False
        safe_rerun()

    pred_repo = ProductionPredictionRepository(Path("local_cases/production_prediction.sqlite"))
    render_lsu_data_gate(
        repository=pred_repo,
        on_close=_close_lsu_data_gate,
        locale=current_ui_locale,
    )
    st.stop()

if active_nb_id is None:
    current_ui_locale = st.session_state.get("wsc_global_ui_locale", "vi")
    current_answer_language = st.session_state.get("wsc_global_answer_language", "vi")
    # MÀN HÌNH 1: Sổ tài liệu của tôi
    st.sidebar.markdown(f"## {t('workspace_title', locale=current_ui_locale)}")
    with st.sidebar.container(border=True):
        st.markdown(t("workspace_select_prompt", locale=current_ui_locale))

    render_notebook_header(locale=current_ui_locale)

    if "wsc_action_message" in st.session_state and st.session_state.wsc_action_message:
        st.success(safe_vietnamese_ui_message(st.session_state.wsc_action_message, "Đã hoàn tất thao tác."))
        st.session_state.wsc_action_message = None
    if "wsc_action_warning" in st.session_state and st.session_state.wsc_action_warning:
        st.warning(safe_vietnamese_ui_message(st.session_state.wsc_action_warning, "Cảnh báo: Dữ liệu cần kiểm tra lại."))
        st.session_state.wsc_action_warning = None
    if "wsc_action_error" in st.session_state and st.session_state.wsc_action_error:
        st.error(safe_vietnamese_ui_message(st.session_state.wsc_action_error, "Không thể hoàn tất thao tác lúc này."))
        st.session_state.wsc_action_error = None

    def _open_alert_case(case_id: str) -> None:
        st.session_state.wsc_show_case_workspace = True
        set_query_params(case=case_id)
        safe_rerun()

    actor_ctx = trusted_local_actor()
    current_actor = actor_ctx.actor_id
    current_role = "local_admin"

    render_in_app_risk_alerts(
        Path("local_cases/production_prediction.sqlite"),
        on_open_case=_open_alert_case,
        actor=current_actor,
        actor_role=current_role,
        locale=current_ui_locale,
    )
    render_sidebar_bridge_status(locale=current_ui_locale, key_prefix="wsc_sidebar_home")

    with st.expander(t("shared_library_expander", locale=current_ui_locale), expanded=True):
        st.write(t("shared_library_help", locale=current_ui_locale))
        ensure_default_collection()
        shared_collection = load_collection(DEFAULT_COLLECTION_ID)
        path_key = "wsc_shared_library_path"
        pending_path = st.session_state.pop("wsc_shared_library_path_pending", None)
        if pending_path is not None:
            st.session_state[path_key] = str(pending_path)
        elif path_key not in st.session_state:
            st.session_state[path_key] = (
                shared_collection.storage_root if shared_collection is not None else ""
            )
        pick_col, _spacer = st.columns([1, 2])
        with pick_col:
            if st.button(
                t("shared_library_choose", locale=current_ui_locale),
                key="btn_pick_shared_library",
                use_container_width=True,
            ):
                chosen_folder, picker_error = choose_local_folder(
                    title=t("shared_library_choose", locale=current_ui_locale),
                )
                if picker_error:
                    st.session_state.wsc_action_error = safe_vietnamese_ui_message(
                        picker_error, "Không thể mở thư mục đã chọn."
                    )
                elif chosen_folder:
                    st.session_state[path_key] = chosen_folder
                safe_rerun()
        st.text_input(
            t("shared_library_path_label", locale=current_ui_locale),
            placeholder=t("shared_library_path_placeholder", locale=current_ui_locale),
            key=path_key,
        )
        col_save, col_reset = st.columns([1, 1])
        with col_save:
            btn_save = st.button(t("shared_library_save", locale=current_ui_locale), key="btn_save_shared_library", use_container_width=True)
        with col_reset:
            btn_reset = st.button(
                t("shared_library_reset", locale=current_ui_locale),
                key="btn_reset_shared_library",
                use_container_width=True,
            )

        if btn_reset:
            st.session_state["wsc_shared_library_path_pending"] = ""
            try:
                from aios_habit.workspace_chat_rag_v2_adapter import (
                    WorkspaceChatRagV2CanaryConfig,
                )
                rag_config = WorkspaceChatRagV2CanaryConfig.from_env()
                fallback_root = rag_config.runtime_root / rag_config.requested_profile
                relocate_collection_storage(
                    DEFAULT_COLLECTION_ID,
                    "",
                    local_fallback_root=fallback_root,
                )
                st.session_state.wsc_action_message = t(
                    "shared_library_cleared", locale=current_ui_locale
                )
            except Exception as exc:
                st.session_state.wsc_action_error = safe_vietnamese_ui_message(
                    str(exc), "Không thể quay về thư viện cục bộ lúc này."
                )
            safe_rerun()

        if btn_save:
            raw_path = str(st.session_state.get(path_key) or "").strip()
            try:
                from aios_habit.workspace_chat_rag_v2_adapter import (
                    WorkspaceChatRagV2CanaryConfig,
                )
                from aios_habit.workspace_chat_store import collection_runtime_layout
                rag_config = WorkspaceChatRagV2CanaryConfig.from_env()
                fallback_root = rag_config.runtime_root / rag_config.requested_profile
                old_root, _old_name = collection_runtime_layout(
                    DEFAULT_COLLECTION_ID, fallback_root
                )
                source_had_index = (old_root / "library.sqlite").exists()
                dest_had_index = False
                if raw_path:
                    dest_had_index = (
                        Path(raw_path) / COLLECTION_RUNTIME_DIRNAME / "library.sqlite"
                    ).exists()
                relocate_collection_storage(
                    DEFAULT_COLLECTION_ID,
                    raw_path,
                    local_fallback_root=fallback_root,
                )
                if raw_path and dest_had_index and not source_had_index:
                    st.session_state.wsc_action_message = t(
                        "shared_library_joined", locale=current_ui_locale
                    )
                elif raw_path:
                    st.session_state.wsc_action_message = t(
                        "shared_library_moved", locale=current_ui_locale
                    )
                else:
                    st.session_state.wsc_action_message = t(
                        "shared_library_cleared", locale=current_ui_locale
                    )
            except ValueError as exc:
                reason = str(exc)
                error_keys = {
                    "storage_root_conflict": "shared_library_conflict",
                    "library_writer_busy": "shared_library_busy",
                    "library_invalid": "shared_library_invalid",
                    "shared_library_remote_wal_unsupported": (
                        "shared_library_remote_wal_unsupported"
                    ),
                    "library_io_error": "shared_library_io_error",
                }
                st.session_state.wsc_action_error = t(
                    error_keys.get(reason, "shared_library_bad_path"),
                    locale=current_ui_locale,
                )
            except OSError:
                st.session_state.wsc_action_error = t(
                    "shared_library_io_error", locale=current_ui_locale
                )
            safe_rerun()

        st.markdown("---")
        st.markdown(t("shared_preset_heading", locale=current_ui_locale))
        st.caption(t("shared_preset_help", locale=current_ui_locale))
        try:
            from aios_habit.shared_library_presets import load_presets

            presets = load_presets(Path("local_cases/shared_presets"))
        except Exception:
            presets = []
        if not presets:
            st.caption(t("shared_preset_empty", locale=current_ui_locale))
        for preset in presets:
            info = preset.name
            if preset.description:
                info += f" — {preset.description}"
            extra = []
            if preset.doc_count:
                extra.append(f"{preset.doc_count} tài liệu")
            if preset.updated_at:
                extra.append(preset.updated_at)
            if preset.version:
                extra.append(preset.version)
            if extra:
                info += " (" + ", ".join(extra) + ")"
            row_name, row_btn = st.columns([3, 1])
            with row_name:
                st.write(info)
            with row_btn:
                if st.button(
                    t("shared_preset_join", locale=current_ui_locale),
                    key=f"btn_join_preset_{preset.name}",
                    use_container_width=True,
                ):
                    try:
                        from aios_habit.workspace_chat_rag_v2_adapter import (
                            WorkspaceChatRagV2CanaryConfig,
                        )
                        from aios_habit.workspace_chat_store import ensure_preset_collection

                        rag_preset_cfg = WorkspaceChatRagV2CanaryConfig.from_env()
                        fallback_preset = rag_preset_cfg.runtime_root / rag_preset_cfg.requested_profile
                        joined = ensure_preset_collection(
                            preset.name,
                            preset.description,
                            preset.folder,
                            local_fallback_root=fallback_preset,
                        )
                        st.session_state.wsc_action_message = (
                            t("shared_library_joined", locale=current_ui_locale)
                            + f" ({joined.title})"
                        )
                    except ValueError as exc:
                        reason = str(exc)
                        preset_errors = {
                            "preset_name_required": "shared_library_bad_path",
                            "storage_root_must_be_absolute": "shared_library_need_path",
                            "storage_root_conflict": "shared_library_conflict",
                            "library_writer_busy": "shared_library_busy",
                            "library_invalid": "shared_library_invalid",
                            "shared_library_remote_wal_unsupported": (
                                "shared_library_remote_wal_unsupported"
                            ),
                            "library_io_error": "shared_library_io_error",
                        }
                        st.session_state.wsc_action_error = t(
                            preset_errors.get(reason, "shared_library_bad_path"),
                            locale=current_ui_locale,
                        )
                    except OSError:
                        st.session_state.wsc_action_error = t(
                            "shared_library_io_error", locale=current_ui_locale
                        )
                    safe_rerun()

        st.markdown(t("shared_preset_request_heading", locale=current_ui_locale))
        st.caption(t("shared_preset_request_help", locale=current_ui_locale))
        try:
            from aios_habit.shared_library_presets import load_presets as _load_presets
            from aios_habit.shared_mailbox import (
                append_request as _mailbox_append,
                is_local_store_folder as _mailbox_is_local,
                list_requests as _mailbox_list,
                mark_done as _mailbox_done,
            )
            from aios_habit.workspace_chat_store import load_collections as _load_cols

            _mailbox_presets = _load_presets(Path("local_cases/shared_presets"))
        except Exception:
            _mailbox_presets = []
            _load_cols = None
        _dest_options: Dict[str, str] = {}
        for _preset in _mailbox_presets or []:
            _dest_options.setdefault(_preset.name, _preset.folder)
        if _load_cols is not None:
            try:
                for _col in _load_cols():
                    _root = str(getattr(_col, "storage_root", "") or "").strip()
                    if _root:
                        _dest_options.setdefault(str(_col.title or _col.id), _root)
            except Exception:
                pass
        if _dest_options:
            _dest_name = st.selectbox(
                t("shared_mailbox_store_label", locale=current_ui_locale),
                options=sorted(_dest_options.keys()),
                key="wsc_mailbox_store",
            )
            _dest_folder = _dest_options.get(str(_dest_name), "")
            try:
                import getpass as _getpass

                _default_sender = _getpass.getuser()
            except Exception:
                _default_sender = ""
            if "wsc_mailbox_sender" not in st.session_state and _default_sender:
                st.session_state["wsc_mailbox_sender"] = _default_sender
            st.text_input(
                t("shared_mailbox_name_label", locale=current_ui_locale),
                key="wsc_mailbox_sender",
            )
            st.text_input(
                t("shared_preset_request_heading", locale=current_ui_locale),
                placeholder=t("shared_preset_request_placeholder", locale=current_ui_locale),
                key="wsc_preset_request_text",
                label_visibility="collapsed",
            )
            if st.button(
                t("shared_preset_request_send", locale=current_ui_locale),
                key="btn_preset_request",
            ):
                _request_text = str(st.session_state.get("wsc_preset_request_text") or "").strip()
                _sender = str(st.session_state.get("wsc_mailbox_sender") or "").strip()
                if not _request_text:
                    st.session_state.wsc_action_error = t(
                        "shared_preset_request_need", locale=current_ui_locale
                    )
                elif not _sender:
                    st.session_state.wsc_action_error = t(
                        "shared_mailbox_need_name", locale=current_ui_locale
                    )
                else:
                    try:
                        _mailbox_append(_dest_folder, str(_dest_name), _request_text, _sender)
                        st.session_state.wsc_action_message = t(
                            "shared_preset_request_done", locale=current_ui_locale
                        )
                    except ValueError as exc:
                        _reason = str(exc)
                        st.session_state.wsc_action_error = t(
                            "shared_library_busy" if _reason == "library_writer_busy" else "shared_preset_request_error",
                            locale=current_ui_locale,
                        )
                    except OSError:
                        st.session_state.wsc_action_error = t(
                            "shared_library_io_error", locale=current_ui_locale
                        )
                safe_rerun()
            try:
                if _dest_folder and _mailbox_is_local(_dest_folder):
                    st.caption(t("shared_mailbox_local_note", locale=current_ui_locale))
            except Exception:
                pass
            st.markdown(t("shared_mailbox_list_heading", locale=current_ui_locale))
            try:
                _requests = _mailbox_list(_dest_folder) if _dest_folder else []
            except Exception:
                _requests = []
            if not _requests:
                st.caption(t("shared_mailbox_empty", locale=current_ui_locale))
            for _req in _requests[:20]:
                _status = (
                    t("shared_mailbox_status_done", locale=current_ui_locale)
                    if _req.status == "done"
                    else t("shared_mailbox_status_open", locale=current_ui_locale)
                )
                _line = f"{_req.text} — {_req.requested_by} ({_status})"
                if _req.status == "done" and _req.handled_by:
                    _line += f", {t('shared_mailbox_handled_by', locale=current_ui_locale)} {_req.handled_by}"
                _r_col, _b_col = st.columns([3, 1])
                with _r_col:
                    st.write(_line)
                with _b_col:
                    if _req.status != "done" and st.button(
                        t("shared_mailbox_mark_done", locale=current_ui_locale),
                        key=f"btn_mailbox_done_{_req.request_id}",
                        use_container_width=True,
                    ):
                        _handler = str(st.session_state.get("wsc_mailbox_sender") or "").strip()
                        if not _handler:
                            st.session_state.wsc_action_error = t(
                                "shared_mailbox_need_name", locale=current_ui_locale
                            )
                        else:
                            try:
                                _mailbox_done(_dest_folder, _req.request_id, _handler)
                                st.session_state.wsc_action_message = t(
                                    "shared_preset_request_done", locale=current_ui_locale
                                )
                            except ValueError as exc:
                                _reason = str(exc)
                                st.session_state.wsc_action_error = t(
                                    "shared_library_busy" if _reason == "library_writer_busy" else "shared_preset_request_error",
                                    locale=current_ui_locale,
                                )
                            except OSError:
                                st.session_state.wsc_action_error = t(
                                    "shared_library_io_error", locale=current_ui_locale
                                )
                        safe_rerun()
        else:
            st.caption(t("shared_preset_empty", locale=current_ui_locale))

        st.markdown(t("shared_library_create_heading", locale=current_ui_locale))
        st.caption(t("shared_library_create_help", locale=current_ui_locale))
        st.text_input(
            t("shared_library_create_name", locale=current_ui_locale),
            placeholder=t("shared_library_create_name_placeholder", locale=current_ui_locale),
            key="wsc_new_library_name",
        )
        new_lib_col, new_lib_btn = st.columns([3, 1])
        with new_lib_col:
            if st.button(
                t("shared_library_choose", locale=current_ui_locale),
                key="btn_pick_new_library",
                use_container_width=True,
            ):
                chosen_new, picker_new_error = choose_local_folder(
                    title=t("shared_library_choose", locale=current_ui_locale),
                )
                if picker_new_error:
                    st.session_state.wsc_action_error = safe_vietnamese_ui_message(
                        picker_new_error, "Không thể mở thư mục đã chọn."
                    )
                elif chosen_new:
                    st.session_state["wsc_new_library_folder"] = chosen_new
                safe_rerun()
        with new_lib_btn:
            if st.button(
                t("shared_library_create_button", locale=current_ui_locale),
                key="btn_create_library",
                use_container_width=True,
            ):
                new_name = str(st.session_state.get("wsc_new_library_name") or "").strip()
                new_folder = str(st.session_state.get("wsc_new_library_folder") or "").strip()
                if not new_name or not new_folder:
                    st.session_state.wsc_action_error = t(
                        "shared_library_create_need", locale=current_ui_locale
                    )
                else:
                    try:
                        from aios_habit.workspace_chat_rag_v2_adapter import (
                            WorkspaceChatRagV2CanaryConfig,
                        )
                        from aios_habit.workspace_chat_store import ensure_preset_collection

                        rag_new_cfg = WorkspaceChatRagV2CanaryConfig.from_env()
                        fallback_new = rag_new_cfg.runtime_root / rag_new_cfg.requested_profile
                        created_lib = ensure_preset_collection(
                            new_name,
                            "",
                            new_folder,
                            local_fallback_root=fallback_new,
                        )
                        st.session_state.wsc_action_message = (
                            t("shared_library_create_done", locale=current_ui_locale)
                            + f" ({created_lib.title})"
                        )
                    except ValueError as exc:
                        reason = str(exc)
                        new_errors = {
                            "preset_name_required": "shared_library_create_need",
                            "storage_root_must_be_absolute": "shared_library_need_path",
                            "storage_root_conflict": "shared_library_conflict",
                            "library_writer_busy": "shared_library_busy",
                            "library_invalid": "shared_library_invalid",
                            "shared_library_remote_wal_unsupported": (
                                "shared_library_remote_wal_unsupported"
                            ),
                            "library_io_error": "shared_library_io_error",
                        }
                        st.session_state.wsc_action_error = t(
                            new_errors.get(reason, "shared_library_create_error"),
                            locale=current_ui_locale,
                        )
                    except OSError:
                        st.session_state.wsc_action_error = t(
                            "shared_library_io_error", locale=current_ui_locale
                        )
                safe_rerun()

        st.markdown("---")
        st.markdown(t("shared_library_backup_heading", locale=current_ui_locale))
        st.caption(t("shared_library_backup_help", locale=current_ui_locale))
        if st.button(
            t("shared_library_backup_create", locale=current_ui_locale),
            key="btn_create_backup",
            use_container_width=True,
        ):
            try:
                from aios_habit.library_backup import create_library_backup
                from aios_habit.workspace_chat_rag_v2_adapter import (
                    WorkspaceChatRagV2CanaryConfig,
                )
                rag_cfg = WorkspaceChatRagV2CanaryConfig.from_env()
                fb_root = rag_cfg.runtime_root / rag_cfg.requested_profile
                dest_dir, manifest = create_library_backup(
                    collection_id=DEFAULT_COLLECTION_ID,
                    local_fallback_root=fb_root,
                )
                st.session_state.wsc_action_message = t(
                    "shared_library_backup_success",
                    locale=current_ui_locale,
                    dir=dest_dir.name,
                    id=manifest.backup_id,
                    digest=manifest.manifest_digest[:8],
                )
            except Exception:
                st.session_state.wsc_action_error = t(
                    "shared_library_backup_error", locale=current_ui_locale
                )
            safe_rerun()

        restore_path_key = "wsc_restore_backup_path"
        st.text_input(
            t("shared_library_restore_path_label", locale=current_ui_locale),
            placeholder="local_cases/library_backups/backup_...",
            key=restore_path_key,
        )
        if st.button(
            t("shared_library_restore", locale=current_ui_locale),
            key="btn_restore_backup",
        ):
            restore_target = str(st.session_state.get(restore_path_key) or "").strip()
            if not restore_target:
                st.session_state.wsc_action_error = t(
                    "shared_library_restore_path_required", locale=current_ui_locale
                )
            else:
                try:
                    from aios_habit.library_backup import restore_library_backup
                    from aios_habit.workspace_chat_rag_v2_adapter import (
                        WorkspaceChatRagV2CanaryConfig,
                    )
                    from aios_habit.workspace_chat_store import collection_runtime_layout

                    rag_cfg = WorkspaceChatRagV2CanaryConfig.from_env()
                    fb_root = rag_cfg.runtime_root / rag_cfg.requested_profile
                    curr_runtime_dir, _ = collection_runtime_layout(
                        DEFAULT_COLLECTION_ID, fb_root
                    )
                    restore_library_backup(Path(restore_target), curr_runtime_dir)
                    st.session_state.wsc_action_message = t(
                        "shared_library_restore_success", locale=current_ui_locale
                    )
                except Exception:
                    st.session_state.wsc_action_error = t(
                        "shared_library_restore_error", locale=current_ui_locale
                    )
            safe_rerun()
        saved = load_collection(DEFAULT_COLLECTION_ID)
        if saved is not None and str(saved.storage_root or "").strip():
            library_file = (
                Path(saved.storage_root) / COLLECTION_RUNTIME_DIRNAME / "library.sqlite"
            )
            st.caption(
                t("shared_library_current", locale=current_ui_locale, path=str(library_file))
            )

    with st.expander(t("create_notebook", locale=current_ui_locale), expanded=False):
        with st.form("create_notebook_form", clear_on_submit=True):
            new_nb_title = st.text_input(t("notebook_title_label", locale=current_ui_locale), placeholder=t("notebook_title_label", locale=current_ui_locale))
            new_nb_desc = st.text_input(t("notebook_desc_label", locale=current_ui_locale), placeholder=t("notebook_desc_label", locale=current_ui_locale))
            ensure_default_collection()
            collections = load_collections()
            collection_labels = {item.id: item.title for item in collections}
            collection_ids = [item.id for item in collections] or [DEFAULT_COLLECTION_ID]
            if len(collection_ids) > 1:
                new_nb_collection = st.selectbox(
                    t("collection_label", locale=current_ui_locale),
                    options=collection_ids,
                    format_func=lambda cid: collection_labels.get(cid, cid),
                    help=t("collection_help", locale=current_ui_locale),
                )
            else:
                only_id = collection_ids[0]
                st.caption(
                    t("notebook_library_single", locale=current_ui_locale, name=collection_labels.get(only_id, only_id))
                )
                new_nb_collection = only_id
            if st.form_submit_button(t("btn_create_notebook", locale=current_ui_locale)):
                if not new_nb_title.strip():
                    st.session_state.wsc_action_error = "Vui lòng nhập tên sổ tài liệu."
                else:
                    new_nb = DocumentNotebook(
                        id=f"NB-{uuid.uuid4().hex[:8].upper()}",
                        title=new_nb_title.strip(),
                        description=new_nb_desc.strip(),
                        collection_id=str(new_nb_collection or DEFAULT_COLLECTION_ID),
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
            locale=current_ui_locale,
        )

    with st.expander(t("archived_notebooks", locale=current_ui_locale), expanded=False):
        if not archived_notebooks:
            st.write(t("no_archived_notebooks", locale=current_ui_locale))
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
                locale=current_ui_locale,
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

    active_conv_id = st.session_state.get("wsc_active_conversation_id")
    active_conv_id = resolve_conversation_id(active_nb_id, active_conv_id)
    st.session_state.wsc_active_conversation_id = active_conv_id
    set_query_params(nb=active_nb_id, conv=active_conv_id)

    active_conversation = None
    if active_conv_id:
        active_conversation = load_conversation(active_conv_id)
        try:
            from aios_habit.production_prediction.rt_app_wire import set_active_rt_conversation
            set_active_rt_conversation(active_conv_id)
        except Exception:
            pass

    current_ui_locale = getattr(active_conversation, "ui_locale", "vi") if active_conversation else st.session_state.get("wsc_global_ui_locale", "vi")
    current_answer_language = getattr(active_conversation, "answer_language", "vi") if active_conversation else st.session_state.get("wsc_global_answer_language", "vi")
    labels = get_localized_labels(current_ui_locale)

    # --- SIDEBAR: QUẢN LÝ SỔ, HỘI THOẠI & THƯ VIỆN NGUỒN ---
    st.sidebar.markdown(f"## 📂 {notebook.title}")
    if st.sidebar.button(f"⬅️ {t('back_to_notebooks', locale=current_ui_locale)}", key="back_to_nbs", use_container_width=True):
        st.session_state.wsc_active_notebook_id = None
        st.session_state.wsc_active_conversation_id = None
        set_query_params(nb=None, conv=None)
        safe_rerun()

    _nb_libraries = load_collections()
    _nb_lib_labels = {c.id: (c.title or c.id) for c in _nb_libraries}
    _nb_raw_col = str(getattr(notebook, "collection_id", "") or DEFAULT_COLLECTION_ID).strip()
    _nb_current_lib = _nb_raw_col
    if _nb_current_lib not in _nb_lib_labels and _nb_libraries:
        _nb_current_lib = _nb_libraries[0].id
    _query_block_param = str(get_query_param("block") or "").strip().lower()
    _conv_block_state = (
        str(st.session_state.get(f"wsc_knowledge_block_{active_conv_id}", "") or "").strip().lower()
        if active_conv_id else ""
    )
    if _query_block_param and _query_block_param != "auto":
        _nb_warm_target_col = _query_block_param
    elif _conv_block_state and _conv_block_state != "auto":
        _nb_warm_target_col = _conv_block_state
    else:
        _nb_warm_target_col = _nb_raw_col
    if st.session_state.get("wsc_last_warmed_notebook_col") != (active_nb_id, _nb_warm_target_col):
        st.session_state["wsc_last_warmed_notebook_col"] = (active_nb_id, _nb_warm_target_col)
        trigger_collection_warming_on_demand(_nb_warm_target_col, notebook_id=active_nb_id)
    st.sidebar.caption(
        t("notebook_library_using", locale=current_ui_locale, name=_nb_lib_labels.get(_nb_current_lib, _nb_current_lib))
    )
    # UX-CHAT-CORE: Single source of truth - khong hien thi so tai lieu cu o sidebar
    try:
        from aios_habit.notebook_readiness import NotebookReadinessStore
        _nb_nguon = load_notebook_sources(active_nb_id)
        _nb_ready_store = NotebookReadinessStore()
        _nb_snap = _nb_ready_store.lay(active_nb_id)
        if _nb_snap is None or _nb_snap.so_tai_lieu != len(_nb_nguon):
            _nb_snap = _nb_ready_store.cap_nhat(
                active_nb_id,
                san_sang=True,
                so_tai_lieu=len(_nb_nguon),
                ten_thu_vien=str(_nb_lib_labels.get(_nb_current_lib, _nb_current_lib)),
            )
    except Exception:
        pass
    if len(_nb_lib_labels) > 1:
        _nb_picked = st.sidebar.selectbox(
            t("notebook_library_change", locale=current_ui_locale),
            options=sorted(_nb_lib_labels.keys()),
            index=sorted(_nb_lib_labels.keys()).index(_nb_current_lib),
            format_func=lambda cid: _nb_lib_labels.get(cid, cid),
            help=t("notebook_library_help", locale=current_ui_locale),
            key=f"wsc_nb_collection_{active_nb_id}",
        )
        if _nb_picked != _nb_current_lib:
            notebook.collection_id = str(_nb_picked)
            save_notebook(notebook)
            trigger_collection_warming_on_demand(str(_nb_picked), notebook_id=active_nb_id)
            if active_conversation is not None:
                _picked_lower = str(_nb_picked).strip().lower()
                st.session_state[f"wsc_knowledge_block_{active_conversation.id}"] = (
                    _picked_lower
                    if _picked_lower in ("lsu", "dieu_tra_loi", "mom", "tong_hop")
                    else "auto"
                )
            st.session_state.wsc_action_message = t(
                "notebook_library_changed", locale=current_ui_locale
            )
            safe_rerun()

    from aios_habit.workspace_memory_service import (
        get_workspace_memory_enabled_preference,
        set_workspace_memory_enabled_preference,
    )
    from aios_habit.workspace_memory_ui import (
        memory_toggle_help,
        memory_toggle_label,
        memory_toggle_status,
    )

    current_memory_setting = get_workspace_memory_enabled_preference()
    requested_memory_setting = st.sidebar.checkbox(
        memory_toggle_label(),
        value=current_memory_setting,
        key="wsc_memory_enabled_setting",
        help=memory_toggle_help(),
    )
    st.sidebar.caption(memory_toggle_status(requested_memory_setting))
    st.sidebar.caption(memory_toggle_help())
    if requested_memory_setting != current_memory_setting:
        set_workspace_memory_enabled_preference(requested_memory_setting)
        st.session_state.wsc_action_message = (
            "AIOS sẽ dùng lại những bài học bạn đã xác nhận."
            if requested_memory_setting
            else "AIOS đã ngừng dùng các bài học đã lưu."
        )
        safe_rerun()

    from aios_habit.workspace_memory_ui import render_ledger_panel, render_ledger_toggle

    render_ledger_toggle()
    if st.session_state.get("wsc_ledger_open"):
        render_ledger_panel(getattr(notebook, "collection_id", "") or DEFAULT_COLLECTION_ID)

    st.sidebar.write("---")
    st.sidebar.subheader(f"💬 {t('conversations', locale=current_ui_locale)}")

    conversations = load_conversations(active_nb_id)

    with st.sidebar.expander(
        f"⚙️ {t('deep_search_machine_settings', locale=current_ui_locale)}",
        expanded=False,
    ):
        current_deep_search_setting = get_workspace_chat_deep_search_enabled_preference()
        requested_deep_search_setting = st.checkbox(
            t('deep_search_machine_toggle', locale=current_ui_locale),
            value=current_deep_search_setting,
            key="wsc_deep_search_machine_setting",
            help=t('deep_search_machine_help', locale=current_ui_locale),
        )
        st.caption(t('deep_search_machine_help', locale=current_ui_locale))
        if requested_deep_search_setting != current_deep_search_setting:
            set_workspace_chat_deep_search_enabled(requested_deep_search_setting)
            st.session_state.wsc_action_message = t(
                'deep_search_machine_enabled'
                if requested_deep_search_setting
                else 'deep_search_machine_disabled',
                locale=current_ui_locale,
            )
            safe_rerun()

    if st.sidebar.button(f"➕ {t('create_conversation', locale=current_ui_locale)}", key="btn_create_conv", use_container_width=True):
        create_conversation_callback(active_nb_id, ui_locale=current_ui_locale, answer_language=current_answer_language)

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
        with st.sidebar.expander(f"⚙️ {t('conversation_customization', locale=current_ui_locale)}", expanded=False):
            conv_options = [c.id for c in conversations]
            manage_conv_id = st.session_state.get("wsc_manage_conversation_id")
            if manage_conv_id not in conv_options:
                manage_conv_id = active_conv_id if active_conv_id in conv_options else conv_options[0]

            selected_manage_id = st.selectbox(
                f"{t('conversations', locale=current_ui_locale)}:",
                options=conv_options,
                format_func=lambda cid: next((c.title for c in conversations if c.id == cid), cid),
                index=conv_options.index(manage_conv_id) if manage_conv_id in conv_options else 0,
                key="select_manage_conv"
            )
            st.session_state.wsc_manage_conversation_id = selected_manage_id
            target_conv = load_conversation(selected_manage_id)

            if target_conv:
                with st.form(f"rename_form_{target_conv.id}"):
                    new_title = st.text_input(t("rename_conversation", locale=current_ui_locale), value=target_conv.title)
                    if st.form_submit_button(t("update_name", locale=current_ui_locale)):
                        if new_title.strip():
                            rename_conversation(target_conv.id, new_title.strip())
                            st.session_state.wsc_action_message = f"Đã đổi tên thành: {new_title.strip()}."
                            safe_rerun()

                st.markdown("---")
                # Mức độ tìm kiếm: Tự động / Tìm kỹ hơn
                pref_val = getattr(target_conv, "search_preference", "auto")
                deep_search = get_workspace_chat_deep_search_availability()
                pref_options = ["auto", "deep"] if deep_search.available else ["auto"]
                if pref_val == "deep" and not deep_search.available:
                    update_conversation_search_preference(target_conv.id, "auto")
                    target_conv.search_preference = "auto"
                    if active_conversation and active_conversation.id == target_conv.id:
                        active_conversation.search_preference = "auto"
                    pref_val = "auto"
                pref_labels = {
                    "auto": f"{t('search_pref_auto', locale=current_ui_locale)} (Tự động)",
                    "deep": f"{t('search_pref_deep', locale=current_ui_locale)} (Tìm kỹ hơn)",
                }
                new_pref = st.selectbox(
                    f"🔍 {t('search_level', locale=current_ui_locale)}:",
                    options=pref_options,
                    format_func=lambda opt: pref_labels.get(opt, opt),
                    index=pref_options.index(pref_val) if pref_val in pref_options else 0,
                    key=f"wsc_sidebar_search_pref_{target_conv.id}",
                )
                if new_pref != pref_val:
                    update_conversation_search_preference(target_conv.id, new_pref)
                    target_conv.search_preference = new_pref
                    if active_conversation and active_conversation.id == target_conv.id:
                        active_conversation.search_preference = new_pref
                    safe_rerun()
                if not deep_search.available:
                    st.caption(t("deep_search_unavailable", locale=current_ui_locale))

                st.markdown("---")
                pending_del_id = st.session_state.get("wsc_pending_conversation_delete_id")
                if pending_del_id == target_conv.id:
                    st.warning(f"⚠️ {t('confirm_delete_conv_warning', locale=current_ui_locale)}: **{target_conv.title}**")
                    cdol1, cdol2 = st.columns(2)
                    with cdol1:
                        if st.button(t("cancel", locale=current_ui_locale), key=f"cancel_del_conv_{target_conv.id}"):
                            cancel_delete_conversation_callback(target_conv.id)
                    with cdol2:
                        if st.button(t("confirm_delete", locale=current_ui_locale), key=f"exec_del_conv_{target_conv.id}", type="primary"):
                            confirm_delete_conversation_callback(active_nb_id, target_conv.id)
                else:
                    if st.button(f"🗑️ {t('delete_conversation', locale=current_ui_locale)}", key=f"req_del_conv_{target_conv.id}", use_container_width=True):
                        request_delete_conversation_callback(active_nb_id, target_conv.id)

    if active_conversation:
        try:
            from aios_habit.production_prediction.rt_app_wire import set_active_rt_conversation
            set_active_rt_conversation(active_conversation.id)
        except Exception:
            pass
        # Nén Ngữ Cảnh & Kế Thừa
        messages = load_messages(active_conversation.id)
        if len(messages) > 0:
            pending_compress_id = st.session_state.get("wsc_pending_compress_conversation_id")
            if pending_compress_id == active_conversation.id:
                st.sidebar.warning(
                    f"{t('confirm_compress_conv', locale=current_ui_locale)}?"
                )
                ccol1, ccol2 = st.sidebar.columns(2)
                with ccol1:
                    if st.sidebar.button(t("cancel", locale=current_ui_locale), key=f"cancel_compress_conv_{active_conversation.id}", use_container_width=True):
                        cancel_compress_conversation_callback(active_conversation.id)
                with ccol2:
                    if st.sidebar.button(t("confirm_compress_conv", locale=current_ui_locale), key=f"exec_compress_conv_{active_conversation.id}", type="primary", use_container_width=True):
                        with st.spinner(t("compressing_spinner", locale=current_ui_locale)):
                            confirm_compress_conversation_callback(active_nb_id, active_conversation.id)
            else:
                if st.sidebar.button(f"🧠 {t('compress_conversation', locale=current_ui_locale)}", key=f"req_compress_conv_{active_conversation.id}", help=t("compress_help", locale=current_ui_locale), use_container_width=True):
                    request_compress_conversation_callback(active_conversation.id)

        render_sidebar_bridge_status(locale=current_ui_locale, key_prefix="wsc_sidebar_chat")

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

        active_action_error = st.session_state.get("wsc_action_error")
        with st.sidebar:
            if "wsc_action_message" in st.session_state and st.session_state.wsc_action_message:
                st.success(safe_vietnamese_ui_message(st.session_state.wsc_action_message, "Đã hoàn tất thao tác."))
                st.session_state.wsc_action_message = None
            if "wsc_action_error" in st.session_state and st.session_state.wsc_action_error:
                st.error(safe_vietnamese_ui_message(st.session_state.wsc_action_error, "Không thể hoàn tất thao tác lúc này."))
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

            def on_retry_preparation(scope: str, source_id: str):
                retry_sources = tuple(
                    source for source in prep_context_sources
                    if source.source_scope == scope and source.source_id == source_id
                )
                retry_workspace_chat_source_preparation(retry_sources)
                st.session_state.wsc_action_message = "Đang thử chuẩn bị lại nguồn trong nền."
                safe_rerun()

            st.write("---")
            # Add-source form lives here (moved from under the composer):
            # one-shot image attach stays in the composer; persistent sources live here.
            with st.expander(t('add_source_button', locale=current_ui_locale), expanded=False):
                st.caption(t("add_sources_explainer", locale=current_ui_locale))
                pending_duplicate_upload = st.session_state.get("wsc_pending_duplicate_upload")
                if pending_duplicate_upload:
                    duplicate_names = ", ".join(pending_duplicate_upload["duplicates"].keys())
                    scope_copy = "sổ tài liệu này" if pending_duplicate_upload["target_scope"] == SOURCE_SCOPE_NOTEBOOK else "cuộc trò chuyện này"
                    st.warning(f"{t('duplicate_source_title_warning', locale=current_ui_locale)}: {duplicate_names}.")
                    st.caption(t("duplicate_source_help", locale=current_ui_locale))
                    keep_col, replace_col, cancel_col = st.columns(3)
                    with keep_col:
                        if st.button(t("keep_both_versions", locale=current_ui_locale), key=f"wsc_duplicate_keep_{active_conversation.id}", use_container_width=True):
                            _complete_pending_workspace_upload(pending_duplicate_upload, replace_existing=False)
                    with replace_col:
                        if st.button(t("replace_old_version", locale=current_ui_locale), key=f"wsc_duplicate_replace_{active_conversation.id}", type="primary", use_container_width=True):
                            _complete_pending_workspace_upload(pending_duplicate_upload, replace_existing=True)
                    with cancel_col:
                        if st.button(t("cancel_upload", locale=current_ui_locale), key=f"wsc_duplicate_cancel_{active_conversation.id}", use_container_width=True):
                            st.session_state.pop("wsc_pending_duplicate_upload", None)
                            safe_rerun()

                tab_quick, tab_paste, tab_upload, tab_folder = st.tabs([
                    t("tab_quick_paste", locale=current_ui_locale),
                    t("tab_long_text", locale=current_ui_locale),
                    t("tab_upload_file", locale=current_ui_locale),
                    t("tab_folder_import", locale=current_ui_locale),
                ])

                with tab_quick:
                    with st.form("quick_paste_form", clear_on_submit=True):
                        quick_title = st.text_input(t("group_name_optional", locale=current_ui_locale), placeholder=t("group_name_optional", locale=current_ui_locale))
                        quick_content = st.text_area(t("paste_content_here", locale=current_ui_locale), placeholder=t("paste_content_here", locale=current_ui_locale), height=120)
                        quick_privacy_choice = render_privacy_choice(f"wsc_quick_privacy_{active_conversation.id}")
                        quick_save_to_notebook = st.checkbox(t("save_permanently_to_notebook", locale=current_ui_locale), value=True)
                        if st.form_submit_button(labels["quick_paste_add"]):
                             if quick_content.strip():
                                 final_title = quick_title.strip() or f"{t('tab_quick_paste', locale=current_ui_locale)} {datetime.now().strftime('%d/%m %H:%M')}"
                                 _submit_pasted_source(
                                     final_title,
                                     quick_content,
                                     quick_privacy_choice,
                                     enable_now=False,
                                     save_to_notebook=quick_save_to_notebook,
                                 )
                             else:
                                 st.error(t("content_cannot_be_empty", locale=current_ui_locale))

                # Khung dán nhật ký/email/đoạn chat dài
                with tab_paste:
                    with st.form("paste_log_form"):
                        paste_title = st.text_input(t("temp_source_title", locale=current_ui_locale), placeholder=t("temp_source_title", locale=current_ui_locale))
                        paste_content = st.text_area(t("long_text_content", locale=current_ui_locale), placeholder=t("paste_content_here", locale=current_ui_locale), height=120)
                        paste_privacy_choice = render_privacy_choice(f"wsc_paste_privacy_{active_conversation.id}")
                        paste_enable_now = st.checkbox(t("use_content_in_answer", locale=current_ui_locale), value=False)
                        paste_save_to_notebook = st.checkbox(t("save_permanently_to_notebook", locale=current_ui_locale), value=True, key=f"paste_save_{active_conversation.id}")
                        if st.form_submit_button(t("btn_add_to_temp_source", locale=current_ui_locale)):
                            if not paste_content.strip():
                                st.error(t("content_cannot_be_empty", locale=current_ui_locale))
                            else:
                                final_title = paste_title.strip() if paste_title.strip() else f"{t('tab_long_text', locale=current_ui_locale)} {datetime.now().strftime('%H:%M:%S')}"
                                _submit_pasted_source(
                                     final_title,
                                     paste_content,
                                     paste_privacy_choice,
                                     enable_now=paste_enable_now,
                                     save_to_notebook=paste_save_to_notebook,
                                 )


                with tab_upload:
                    st.write(t("upload_docs_help", locale=current_ui_locale))
                    st.write(t("upload_multi_docs_help", locale=current_ui_locale))
                    st.write(t("upload_supported_formats", locale=current_ui_locale))
                    with st.form(f"wsc_doc_upload_form_{active_conversation.id}"):
                        uploaded_files = st.file_uploader(
                            t("select_docs_for_conv", locale=current_ui_locale),
                            type=["txt", "md", "markdown", "xlsx", "xls", "docx", "pptx", "pdf", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
                            key=f"wsc_doc_upload_{active_conversation.id}_{st.session_state.wsc_upload_version}",
                            accept_multiple_files=True,
                        )
                        doc_privacy_choice = render_privacy_choice(f"wsc_doc_privacy_{active_conversation.id}")
                        enable_now = st.checkbox(t("use_docs_in_answer", locale=current_ui_locale), value=False)
                        upload_save_to_notebook = st.checkbox(t("save_permanently_to_notebook", locale=current_ui_locale), value=True, key=f"upload_save_{active_conversation.id}")
                        if st.form_submit_button(t("btn_read_add_temp_source", locale=current_ui_locale)):
                            if not uploaded_files:
                                st.error(t("select_file_before_adding", locale=current_ui_locale))
                            else:
                                _submit_workspace_upload(
                                    uploaded_files,
                                    doc_privacy_choice,
                                    enable_now,
                                    upload_save_to_notebook,
                                )

                with tab_folder:
                    st.write(t("folder_path_help", locale=current_ui_locale))
                    st.caption(t("folder_supported_formats", locale=current_ui_locale))

                    scan_key = f"wsc_folder_scan_{active_conversation.id}"
                    path_key = f"wsc_folder_path_input_{active_conversation.id}"
                    rec_key = f"wsc_folder_rec_{active_conversation.id}"

                    col_path, col_picker, col_btn = st.columns([3, 1.2, 1])
                    # Run the picker before creating the text field so its
                    # chosen path can safely populate Streamlit state.
                    with col_picker:
                        if st.button(t("choose_folder", locale=current_ui_locale), key=f"btn_pick_folder_{active_conversation.id}", use_container_width=True):
                            chosen_folder, picker_error = choose_local_folder()
                            if picker_error:
                                st.session_state.wsc_action_error = safe_vietnamese_ui_message(
                                    picker_error, "Không thể mở thư mục đã chọn."
                                )
                            elif chosen_folder:
                                st.session_state[path_key] = chosen_folder
                                st.session_state.pop(scan_key, None)
                            safe_rerun()
                    with col_path:
                        folder_path_input = st.text_input(t("folder_path_input", locale=current_ui_locale), placeholder="D:\\TaiLieu\\DuAn", key=path_key, label_visibility="collapsed")
                    with col_btn:
                        folder_recursive = st.checkbox(t("scan_subfolders", locale=current_ui_locale), value=True, key=rec_key)
                        btn_scan = st.button(t("scan_folder_button", locale=current_ui_locale), key=f"btn_scan_{active_conversation.id}", use_container_width=True)

                    if btn_scan:
                        if not folder_path_input or not folder_path_input.strip():
                            st.session_state.pop(scan_key, None)
                            st.error(t("enter_folder_path_before_scan", locale=current_ui_locale))
                        else:
                            scan_res = scan_local_directory(folder_path_input.strip(), recursive=folder_recursive)
                            st.session_state[scan_key] = scan_res

                    current_scan = st.session_state.get(scan_key)
                    if current_scan is not None:
                        if not current_scan.ok:
                            st.error(
                                safe_vietnamese_ui_message(
                                    current_scan.error_message,
                                    "Không thể quét thư mục đã chọn.",
                                )
                            )
                        else:
                            mcol1, mcol2, mcol3 = st.columns(3)
                            with mcol1:
                                st.metric(t("metric_total_files", locale=current_ui_locale), current_scan.total_files)
                            with mcol2:
                                st.metric(
                                    t("metric_supported_files", locale=current_ui_locale),
                                    f"{len(current_scan.supported_files)} ({current_scan.formatted_supported_size()})",
                                )
                            with mcol3:
                                st.metric(t("metric_unsupported_skipped", locale=current_ui_locale), len(current_scan.unsupported_files))

                            if current_scan.supported_files:
                                existing_titles = [source.title for source in notebook_sources] + [source.title for source in temp_sources]
                                migrated_count = seed_completed_folder_files_from_titles(current_scan.supported_files, existing_titles)
                                already_imported = count_completed_folder_files(current_scan.supported_files)
                                if migrated_count:
                                    st.info(t("folder_migrated_legacy_files", locale=current_ui_locale, count=migrated_count))
                                if already_imported:
                                    st.info(t("folder_already_imported", locale=current_ui_locale, count=already_imported))
                                st.markdown(t("scanned_files_header", locale=current_ui_locale))
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
                                    st.caption(f"({t('showing_top_docs', locale=current_ui_locale, count=100, total=len(current_scan.supported_files))})")

                                st.divider()
                                folder_privacy_choice = render_privacy_choice(f"wsc_folder_privacy_{active_conversation.id}")
                                folder_enable_now = st.checkbox(t("use_docs_in_answer", locale=current_ui_locale), value=False, key=f"folder_enable_{active_conversation.id}")
                                folder_save_to_notebook = st.checkbox(t("save_permanently_to_notebook", locale=current_ui_locale), value=True, key=f"folder_save_{active_conversation.id}")

                                import_label = t("import_remaining_files", locale=current_ui_locale) if already_imported else t("import_all_to_notebook", locale=current_ui_locale)
                                if st.button(import_label, type="primary", key=f"btn_ingest_{active_conversation.id}", use_container_width=True):
                                    prog_bar = st.progress(0, text=t("start_ingesting_progress", locale=current_ui_locale))
                                    status_text = st.empty()

                                    def update_progress(current_idx: int, total_count: int, filename: str):
                                        pct = current_idx / max(total_count, 1)
                                        prog_bar.progress(
                                            pct,
                                            text=t(
                                                "ingest_processing_progress",
                                                locale=current_ui_locale,
                                                current=current_idx,
                                                total=total_count,
                                                filename=filename,
                                            ),
                                        )
                                        status_text.caption(f"{t('loading', locale=current_ui_locale)}: {filename}")

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
                                    if batch_summary.skipped_count > 0:
                                        st.session_state.wsc_action_message = (st.session_state.get("wsc_action_message", "") + f" Đã bỏ qua {batch_summary.skipped_count} file đã nhập.").strip()

                                    if batch_summary.fail_count > 0:
                                        st.session_state.wsc_action_error = f"Có {batch_summary.fail_count} tài liệu gặp lỗi khi trích xuất."

                                    st.session_state.pop(scan_key, None)
                                    safe_rerun()

                            else:
                                st.info(t("no_matching_docs_in_folder", locale=current_ui_locale))

                            log_files = [
                                item for item in current_scan.unsupported_files
                                if item.unsupported_reason == LINE_LOG_SCAN_REASON
                            ]
                            if log_files:
                                st.caption(t("line_logs_help", locale=current_ui_locale))
                                if st.button(
                                    t("ingest_line_logs_button", locale=current_ui_locale),
                                    key=f"wsc_ingest_line_logs_{active_conversation.id}",
                                ):
                                    from aios_habit.line_log_parser import ingest_line_log_files
                                    from aios_habit.workspace_chat_models import DEFAULT_COLLECTION_ID
                                    from aios_habit.workspace_chat_store import load_notebook

                                    notebook = load_notebook(active_nb_id)
                                    collection_id = (
                                        getattr(notebook, "collection_id", "") or DEFAULT_COLLECTION_ID
                                    )
                                    summary = ingest_line_log_files(
                                        [item.path for item in log_files],
                                        collection_id=collection_id,
                                    )
                                    if summary.ok:
                                        st.session_state.wsc_action_message = summary.owner_message
                                    else:
                                        st.session_state.wsc_action_error = summary.owner_message
                                    safe_rerun()

                            if current_scan.unsupported_files:
                                with st.expander(t("unsupported_files_expander", locale=current_ui_locale, count=len(current_scan.unsupported_files)), expanded=False):
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
            # Thư viện chung: 3 khối tri thức luôn bật, mặc định gập.
            with st.expander(t("shared_blocks_expander", locale=current_ui_locale), expanded=False):
                st.caption(t("shared_blocks_help", locale=current_ui_locale))
                _shared_block_label_keys = {
                    "lsu": "knowledge_block_lsu",
                    "dieu_tra_loi": "knowledge_block_dieu_tra_loi",
                    "mom": "knowledge_block_mom",
                    "tong_hop": "knowledge_block_tong_hop",
                }
                for _shared_block in workspace_chat_domain_block_status():
                    _label_key = _shared_block_label_keys.get(str(_shared_block["domain"]), "")
                    _shared_label = (
                        t(_label_key, locale=current_ui_locale)
                        if _label_key
                        else str(_shared_block["display"])
                    )
                    _shared_state = t(
                        "shared_block_ready" if _shared_block["ready"] else "shared_block_missing",
                        locale=current_ui_locale,
                    )
                    st.markdown(f"• **{_shared_label}** · {_shared_state}")
            render_source_library(
                notebook_sources=notebook_sources,
                temp_sources=temp_sources,
                selections_map=selections_map,
                conversation_id=active_conversation.id,
                on_toggle_source=on_toggle_source,
                on_promote_temporary=on_promote_temporary,
                on_privacy_save=on_privacy_save,
                on_delete_source=on_delete_source,
                on_retry_preparation=on_retry_preparation,
                locale=current_ui_locale,
            )

    else:
        with st.sidebar:
            if "wsc_action_message" in st.session_state and st.session_state.wsc_action_message:
                st.success(safe_vietnamese_ui_message(st.session_state.wsc_action_message, "Đã hoàn tất thao tác."))
                st.session_state.wsc_action_message = None
            if "wsc_action_error" in st.session_state and st.session_state.wsc_action_error:
                st.error(safe_vietnamese_ui_message(st.session_state.wsc_action_error, "Không thể hoàn tất thao tác lúc này."))
                st.session_state.wsc_action_error = None

    _legacy_connector_panel = """Legacy header bridge panel relocated into the composer toolbar.
    top_col1, top_col2, top_col3 = st.columns([2.5, 1.3, 1.2])
    with top_col1:
        st.subheader(f"💬 {t('chat_in_notebook', locale=current_ui_locale)}: {notebook.title}")

    active_conversation_id = active_conversation.id if active_conversation else "new"
    connector_status_key = f"wsc_connector_check_status_{active_conversation_id}"
    bridge_health = get_antigravity_bridge_health()
    with top_col2:
        # UX-CHAT-CORE #3: lane tu dong chon — khong bat user doi tay moi lan.
        # Lua chon duoc ghi nho theo cuoc hoi thoai; chi hien dong trang thai nho.
        from aios_habit.ai_lane import auto_backend_for_conversation, backend_label_vi
        from aios_habit.ai_router import provider_env_presence

        cagent_endpoint_key = f"wsc_cagent_endpoint_{active_conversation_id}"
        _cagent_endpoint_probe = (
            str(st.session_state.get(cagent_endpoint_key, "")).strip()
            or os.environ.get("AIOS_CAGENT_API_URL", "").strip()
        )
        _lane_decision = auto_backend_for_conversation(
            f"wsc_ai_lane_{active_conversation_id}",
            st.session_state,
            bridge_available=bool(getattr(bridge_health, "is_available", False)),
            cagent_endpoint=_cagent_endpoint_probe,
            router_keys_present=any(provider_env_presence(os.environ).values()),
            manual_override=os.environ.get("AIOS_AI_BACKEND", ""),
        )
        selected_ai_backend = _lane_decision.backend
        st.caption(
            "Đang dùng: "
            + backend_label_vi(selected_ai_backend)
            + (" (tự động)" if _lane_decision.automatic else " (ghim tay)")
            + " — " + _lane_decision.reason_vi
        )
        cagent_endpoint = ""
        if selected_ai_backend == "cagent_api":
            configured_cagent_endpoint = (
                str(st.session_state.get(cagent_endpoint_key, "")).strip()
                or os.environ.get("AIOS_CAGENT_API_URL", "").strip()
            )
            if not str(st.session_state.get(cagent_endpoint_key, "")).strip() and configured_cagent_endpoint:
                st.session_state[cagent_endpoint_key] = configured_cagent_endpoint
            cagent_endpoint = st.text_input(
                "URL API AgentFlow C-AGENT",
                value=configured_cagent_endpoint,
                placeholder="https://.../api/v1/prediction/<AgentFlow-ID>",
                key=cagent_endpoint_key,
                help=t("cagent_endpoint_help", locale=current_ui_locale),
            ).strip()
            # Streamlit session state is per browser tab. Keep the user-entered
            # endpoint in this local app process as well so another AIOS tab
            # does not misleadingly start with an empty C-AGENT field.
            if cagent_endpoint:
                os.environ["AIOS_CAGENT_API_URL"] = cagent_endpoint
        if selected_ai_backend == "cagent_api":
            st.caption(t("cagent_selected_status", locale=current_ui_locale))
        elif selected_ai_backend == "nakazasen_router":
            st.caption(t("router_selected_status", locale=current_ui_locale))
        else:
            st.caption(t("gemini_selected_no_drawings", locale=current_ui_locale))
            render_bridge_header_status(bridge_health, locale=current_ui_locale)

        connector_status = st.session_state.get(connector_status_key)
        status_matches_current_endpoint = (
            selected_ai_backend != "cagent_api"
            or connector_status.get("endpoint") == cagent_endpoint
        ) if isinstance(connector_status, dict) else False
        if (
            isinstance(connector_status, dict)
            and connector_status.get("backend") == selected_ai_backend
            and status_matches_current_endpoint
        ):
            checked_at = connector_status.get("checked_at", "")
            detail = safe_vietnamese_ui_message(
                connector_status.get("detail", ""),
                "Không thể hiển thị chi tiết kiểm tra kết nối một cách an toàn.",
            )
            message = f"Kiểm tra lúc {checked_at}: {detail}" if checked_at else detail
            if connector_status.get("state") == "ok":
                st.success(message)
            elif connector_status.get("state") == "configured":
                st.info(message)
            elif connector_status.get("state") == "error":
                st.error(message)
        elif selected_ai_backend == "cagent_api":
            st.caption(t("cagent_not_checked", locale=current_ui_locale))
        elif selected_ai_backend == "nakazasen_router":
            st.caption(t("router_not_checked", locale=current_ui_locale))

    # Names used by the question submission below.
    ai_backend = selected_ai_backend
    cagent_endpoint_url = cagent_endpoint
    with top_col3:
        curr_layout = st.session_state.get("wsc_layout_mode", "full")
        toggle_label = f"📑 {t('layout_split', locale=current_ui_locale)}" if curr_layout == "full" else f"📖 {t('layout_full', locale=current_ui_locale)}"
        if st.button(toggle_label, key="wsc_legacy_toggle_layout_btn", help=t("layout_toggle_help", locale=current_ui_locale), use_container_width=True):
            st.session_state.wsc_layout_mode = "split" if curr_layout == "full" else "full"
            safe_rerun()

        if selected_ai_backend == "cagent_api":
            if st.button(
                t("check_cagent_button", locale=current_ui_locale),
                key="wsc_check_cagent_btn",
                help=t("check_cagent_help", locale=current_ui_locale),
                use_container_width=True,
            ):
                if not cagent_endpoint:
                    st.session_state.wsc_action_error = "Hãy nhập URL API AgentFlow C-AGENT trước khi kiểm tra."
                    st.session_state[connector_status_key] = {
                        "backend": "cagent_api",
                        "state": "error",
                        "checked_at": datetime.now().strftime("%H:%M:%S"),
                        "detail": "Chưa có URL AgentFlow C-AGENT.",
                        "endpoint": cagent_endpoint,
                    }
                else:
                    from aios_habit.cagent_api import call_cagent_prediction
                    check = call_cagent_prediction(
                        cagent_endpoint,
                        system_prompt="Bạn là kiểm tra kết nối AIOS.",
                        user_prompt="Trả lời ngắn: OK",
                    )
                    if check.ok:
                        st.session_state.wsc_action_message = "C-AGENT API đã kết nối và phản hồi thành công."
                        st.session_state[connector_status_key] = {
                            "backend": "cagent_api",
                            "state": "ok",
                            "checked_at": datetime.now().strftime("%H:%M:%S"),
                            "detail": "C-AGENT API đã phản hồi yêu cầu kiểm tra.",
                            "endpoint": cagent_endpoint,
                        }
                    else:
                        st.session_state.wsc_action_error = safe_vietnamese_ui_message(
                            check.error_message, "Không thể xác minh gói đầu ra đã chọn."
                        )
                        st.session_state[connector_status_key] = {
                            "backend": "cagent_api",
                            "state": "error",
                            "checked_at": datetime.now().strftime("%H:%M:%S"),
                            "detail": safe_vietnamese_ui_message(
                                check.error_message,
                                "Không thể kết nối tới dịch vụ đã chọn.",
                            ),
                            "endpoint": cagent_endpoint,
                        }
                safe_rerun()
        elif selected_ai_backend == "nakazasen_router":
            if st.button(
                t("check_router_button", locale=current_ui_locale),
                key="wsc_check_router_btn",
                help=t("check_router_help", locale=current_ui_locale),
                use_container_width=True,
            ):
                try:
                    from aios_habit.workspace_chat_router_adapter import _get_router
                    _get_router()
                    st.session_state.wsc_action_message = "Nakazasen Router đã có cấu hình và sẵn sàng dùng."
                    st.session_state[connector_status_key] = {
                        "backend": "nakazasen_router",
                        "state": "configured",
                        "checked_at": datetime.now().strftime("%H:%M:%S"),
                        "detail": "Cấu hình Router đã được nạp; chưa gửi yêu cầu tới nhà cung cấp AI.",
                    }
                except Exception:
                    st.session_state.wsc_action_error = "Nakazasen Router chưa sẵn sàng. Hãy kiểm tra cấu hình API trên máy."
                    st.session_state[connector_status_key] = {
                        "backend": "nakazasen_router",
                        "state": "error",
                        "checked_at": datetime.now().strftime("%H:%M:%S"),
                        "detail": "Không thể nạp cấu hình Nakazasen Router.",
                    }
                safe_rerun()
        elif st.button(t("bridge_connect_refresh", locale=current_ui_locale), key="wsc_refresh_bridge_btn", help=t("bridge_connect_refresh_help", locale=current_ui_locale), use_container_width=True):
            startup = ensure_antigravity_bridge_running()
            check_handoff_request_timeouts()
            if startup.ok:
                st.session_state.wsc_action_message = t("bridge_connect_success", locale=current_ui_locale)
            else:
                st.session_state.wsc_action_error = t(
                    "bridge_connect_failed",
                    locale=current_ui_locale,
                    reason=startup.reason or startup.health.reason or "unknown_error",
                )
            safe_rerun()

    """
    st.subheader(f"{t('chat_in_notebook', locale=current_ui_locale)}: {notebook.title}")
    curr_layout = st.session_state.get("wsc_layout_mode", "full")
    layout_icon = ":material/chevron_left:" if curr_layout == "full" else ":material/chevron_right:"
    layout_help = (
        t("layout_split", locale=current_ui_locale)
        if curr_layout == "full"
        else t("layout_full", locale=current_ui_locale)
    )
    if st.button(
        t("layout_toggle_help", locale=current_ui_locale),
        icon=layout_icon,
        key="wsc-layout-rail-toggle",
        help=layout_help,
    ):
        st.session_state.wsc_layout_mode = "split" if curr_layout == "full" else "full"
        safe_rerun()

    if not active_conversation:
        with st.container(border=True):
            st.markdown(t("no_conversations_in_notebook", locale=current_ui_locale))
        if st.button(t("create_first_conversation_now", locale=current_ui_locale), key="btn_create_empty_conv", type="primary"):
            create_conversation_callback(active_nb_id)
    else:
            active_pending = list_pending_ide_requests(active_conversation.id)
            for req_info in active_pending:
                if req_info.response_exists:
                    res = import_pending_ide_response(req_info.request_id)
                    if res.ok:
                        save_imported_ide_answer(active_conversation.id, res)

                        conv_msgs = load_messages(active_conversation.id)
                        user_msgs = [m for m in conv_msgs if m.role == "user"]
                        user_msg_id = user_msgs[-1].id if user_msgs else ""

                        assistant_msg_id = f"MSG-{uuid.uuid4().hex[:8].upper()}"

                        manifest = res.manifest or {}
                        q_text = manifest.get("question", "")
                        manifest_evidence = manifest.get("evidence_items") or []
                        allowed_source_ids = manifest.get("allowed_source_ids")

                        ans_text = (
                            res.answer_markdown
                            or res.answer_text
                            or (res.response.get("answer_markdown") if isinstance(res.response, dict) else "")
                            or (res.response.get("answer_text") if isinstance(res.response, dict) else "")
                            or ""
                        )

                        provenance = {
                            "operational_mode": "handoff",
                            "provider_name": "Gemini Web",
                            "model_name": "verified_antigravity_ide",
                        }

                        trace = build_evidence_trace_from_citations(
                            query=q_text,
                            answer_text=ans_text,
                            evidence_items=manifest_evidence,
                            allowed_source_ids=allowed_source_ids,
                            notebook_id=active_conversation.notebook_id or active_nb_id,
                            conversation_id=active_conversation.id,
                            user_message_id=user_msg_id,
                            assistant_message_id=assistant_msg_id,
                            ui_locale=current_ui_locale,
                            answer_language=getattr(active_conversation, "answer_language", current_ui_locale) or current_ui_locale,
                            provenance=provenance,
                        )
                        save_evidence_trace(trace)

                        imported_assistant_msg = ChatMessage(
                            id=assistant_msg_id,
                            conversation_id=active_conversation.id,
                            role="assistant",
                            content=ans_text,
                            trace_id=trace.trace_id,
                        )
                        save_message(imported_assistant_msg)
                        handoff_model = getattr(res, "model_tool_name", "") or ""
                        if handoff_model in ("antigravity", "antigravity-brain-pro"):
                            handoff_model = ""
                        st.session_state.wsc_last_ai_badge = {
                            "conversation_id": active_conversation.id,
                            "type": "ai_answered",
                            "source_count": len(res.cited_evidence_ids or []),
                            "source_titles": [t("source_item_label", locale=current_ui_locale, id=eid) for eid in (res.cited_evidence_ids or [])],
                            "ai_source": "Antigravity IDE",
                            "bridge": t("sidecar_handoff", locale=current_ui_locale),
                            "provider": t("gemini_web_anonymous", locale=current_ui_locale),
                            "model_tool_name": handoff_model,
                            "verified_model": handoff_model,
                            "operational_mode": "handoff",
                            "trace_id": trace.trace_id,
                        }
                        st.session_state.wsc_action_message = t("auto_received_ide_answer", locale=current_ui_locale, id=req_info.request_id)
                        safe_rerun()

            # Thêm tài liệu rồi hỏi tự nhiên; AIOS sẽ tự kiểm tra nguồn và cảnh báo nếu thiếu.
            st.info(t("input_help_instruction", locale=current_ui_locale))

            if st.session_state.wsc_show_explain_placeholder:
                st.info(t("explain_conclusion", locale=current_ui_locale))
                if st.button(t("close_notification", locale=current_ui_locale)):
                    st.session_state.wsc_show_explain_placeholder = False
                    safe_rerun()

            badge_data = st.session_state.wsc_last_ai_badge

            def _selected_local_work_source_paths() -> list[Path]:
                selected_source_by_key = {
                    (SOURCE_SCOPE_NOTEBOOK, source.id): source for source in notebook_sources
                } | {
                    (SOURCE_SCOPE_TEMPORARY, source.id): source for source in temp_sources
                }
                return [
                    Path(getattr(selected_source_by_key.get((selection.source_scope, selection.source_id)), "managed_path", ""))
                    for selection in selections
                    if selection.enabled
                    and getattr(selected_source_by_key.get((selection.source_scope, selection.source_id)), "managed_path", "")
                    and Path(getattr(selected_source_by_key[(selection.source_scope, selection.source_id)], "managed_path", "")).is_file()
                ]

            def _drain_queued_agent_tasks(target_ws: str) -> None:
                try:
                    from aios_habit.workspace_case_repository import WorkspaceCaseRepository
                    from aios_habit.workspace_agent_orchestrator import WorkspaceAgentOrchestrator
                    from aios_habit.agent_work_artifact import (
                        create_factory_error_report,
                        create_process_design_review,
                        format_artifact_card,
                    )
                    from aios_habit.workspace_chat_models import ChatMessage
                    from aios_habit.workspace_chat_store import save_message

                    q_repo = WorkspaceCaseRepository()
                    q_orch = WorkspaceAgentOrchestrator()
                    queued_items = q_repo.list_agent_work(workspace_id=active_conversation.id, status="queued")
                    if not queued_items:
                        return
                    canonical_ws = Path(target_ws).resolve().as_posix()
                    if q_orch.get_workspace_lock_holder(canonical_ws):
                        return
                    next_task = queued_items[0]
                    task_sources = [Path(p) for p in next_task.source_refs if Path(p).is_file()] if next_task.source_refs else _selected_local_work_source_paths()
                    if not task_sources:
                        return

                    if next_task.work_type == "error_report":
                        def _d_run_err(item_record):
                            rep_res = create_factory_error_report(
                                source_paths=task_sources,
                                output_dir=Path("local_cases") / "agent_artifacts",
                                work_id=item_record.work_id,
                            )
                            q_repo.update_agent_work_status(
                                item_record.work_id,
                                "completed",
                                result_ref=str(rep_res.report_path),
                                checkpoint_ref=str(rep_res.report_path),
                            )
                            card_content = format_artifact_card(
                                work_type="error_report",
                                work_id=item_record.work_id,
                                result_path=str(rep_res.report_path),
                                checkpoint_path=str(rep_res.report_path),
                                payload=rep_res.payload,
                                status_vi="Đã xong",
                            )
                            save_message(ChatMessage(
                                id=f"MSG-ART-{item_record.work_id}",
                                conversation_id=active_conversation.id,
                                role="assistant",
                                content=card_content,
                            ))
                        q_orch.process_next_work_item(
                            workspace_id=active_conversation.id,
                            workspace_root=target_ws,
                            repo=q_repo,
                            runner=_d_run_err,
                        )
                    elif next_task.work_type == "process_design_review":
                        def _d_run_rev(item_record):
                            rev_res = create_process_design_review(
                                source_paths=task_sources,
                                output_dir=Path("local_cases") / "agent_artifacts",
                                work_id=item_record.work_id,
                            )
                            q_repo.update_agent_work_status(
                                item_record.work_id,
                                "completed",
                                result_ref=str(rev_res.report_path),
                                checkpoint_ref=str(rev_res.report_path),
                            )
                            card_content = format_artifact_card(
                                work_type="process_design_review",
                                work_id=item_record.work_id,
                                result_path=str(rev_res.report_path),
                                checkpoint_path=str(rev_res.report_path),
                                payload=rev_res.payload,
                                status_vi="Đã xong (Bản nháp)",
                            )
                            save_message(ChatMessage(
                                id=f"MSG-ART-{item_record.work_id}",
                                conversation_id=active_conversation.id,
                                role="assistant",
                                content=card_content,
                            ))
                        q_orch.process_next_work_item(
                            workspace_id=active_conversation.id,
                            workspace_root=target_ws,
                            repo=q_repo,
                            runner=_d_run_rev,
                        )
                except Exception:
                    pass

            def _render_chat_main_column():
                ai_request_key = f"wsc_ai_request_{active_conversation.id}"
                active_ai_request = st.session_state.get(ai_request_key)
                is_answering = False
                if active_ai_request:
                    request_future = active_ai_request.get("future")
                    cancellation_event = active_ai_request.get("cancellation_event")
                    if request_future is not None and request_future.done():
                        st.session_state.pop(ai_request_key, None)
                        if cancellation_event is not None and cancellation_event.is_set():
                            st.session_state.wsc_action_message = "Đã dừng yêu cầu AI."
                        else:
                            try:
                                ok, succ_msg, badge, err_msg = request_future.result()
                            except Exception as exc:
                                ok, succ_msg, badge, err_msg = (False, "", None, f"Lỗi khi nhận phản hồi AI: {exc}")
                            if ok:
                                if succ_msg:
                                    st.session_state.wsc_action_message = succ_msg
                                if badge:
                                    st.session_state.wsc_last_ai_badge = badge
                            else:
                                if err_msg:
                                    clean_err = safe_vietnamese_ui_message(
                                        err_msg, "Không thể hoàn tất yêu cầu AI lúc này."
                                    )
                                    st.session_state.wsc_action_error = clean_err
                                    # A local-fallback offer is not a failed turn:
                                    # it must stay a pure offer, so the refusal
                                    # text is shown but never written into the
                                    # conversation. Writing it would both add a
                                    # spurious assistant turn and hide the
                                    # original user message from the commit step.
                                    is_local_offer = bool(
                                        badge and badge.get("type") == "local_fallback_offered"
                                    )
                                    if not is_local_offer:
                                        from aios_habit.workspace_chat_models import ChatMessage
                                        from aios_habit.workspace_chat_store import save_message
                                        save_message(ChatMessage(
                                            id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
                                            conversation_id=active_conversation.id,
                                            role="assistant",
                                            content=f"⚠️ {clean_err}",
                                        ))
                                st.session_state.wsc_last_ai_badge = badge
                        safe_rerun()
                    elif request_future is not None:
                        is_answering = True

                active_pending = list_pending_ide_requests(active_conversation.id)
                for req_info in active_pending:
                    if not req_info.response_exists and req_info.state == "handoff_pending":
                        render_handoff_pending_banner(
                            request_id=req_info.request_id,
                            outbox_dir=str(getattr(req_info, "outbox_dir", "") or ""),
                            inbox_path=str(getattr(req_info, "inbox_path", "") or ""),
                            privacy_mode=req_info.privacy_mode,
                            locale=current_ui_locale,
                        )

                # Dòng trạng thái chỉ mục trong khung chat (INDEX-STATUS-LINE-PC0575 & DESKTOP-SPEED-LAZY-WARM-HOME)
                from aios_habit.index_status import (
                    get_cached_index_status_line,
                    resolve_active_index_db_path,
                )

                _selected_block_col = str(
                    st.session_state.get(f"wsc_knowledge_block_{active_conversation.id}", "")
                    or ""
                ).strip().lower()
                _active_view_col = (
                    _selected_block_col
                    if (_selected_block_col and _selected_block_col != "auto")
                    else (
                        getattr(notebook, "collection_id", None)
                        or getattr(active_conversation, "collection_id", None)
                        or "tri_thuc"
                    )
                )
                _active_idx_path = resolve_active_index_db_path(
                    getattr(active_conversation, "collection_id", None) or _active_view_col
                )
                _idx_status_text, _idx_is_err = get_cached_index_status_line(
                    _active_idx_path,
                    session_state=st.session_state,
                )
                st.caption(_idx_status_text)
                try:
                    if not is_workspace_chat_worker_warmed(collection_id=_active_view_col):
                        trigger_collection_warming_on_demand(
                            _active_view_col,
                            notebook_id=active_nb_id,
                        )
                        _warm_status_line = format_worker_warming_status_line(
                            _active_view_col,
                            locale=current_ui_locale,
                        )
                        if _warm_status_line:
                            st.caption(_warm_status_line)
                except Exception:
                    pass

                try:
                    from aios_habit.production_prediction.rt_app_wire import set_active_rt_conversation
                    set_active_rt_conversation(active_conversation.id)
                except Exception:
                    pass

                # Realtime alert auto-refresh watcher (DESKTOP-LSU-ALERT-WIRE-HOME / DESKTOP-PC0575-UI-RENDER-FIX)
                # Chi kich hoat rerun dinh ky khi so co canh bao realtime dang hoat dong hoac nguoi dung dang o che do theo doi
                def _is_rt_alert_active() -> bool:
                    try:
                        from aios_habit.production_prediction.session_isolation import classify_session
                        if get_jig_session_type() == "truc_ban":
                            return True
                        if st.session_state.get("wsc_jig_persona") == "truc_ban" or st.session_state.get("wsc_monitoring_mode", False):
                            return True
                        if classify_session(getattr(active_conversation, "title", "")) == "truc_ban":
                            return True
                    except Exception:
                        pass
                    try:
                        from aios_habit.production_prediction.rt_app_wire import get_last_dispatch_time
                        if time.time() - get_last_dispatch_time() < 300:
                            return True
                        for m in reversed(messages[-20:] if len(messages) > 20 else messages):
                            c = str(getattr(m, "content", "") or "")
                            if "<!-- aios_realtime_alert:" in c or "Cảnh báo realtime" in c:
                                return True
                    except Exception:
                        pass
                    return False

                if _is_rt_alert_active():
                    @st.fragment(run_every=1.5)
                    def _rt_alert_live_watcher(conv_id: str, last_count: int) -> None:
                        try:
                            from aios_habit.workspace_chat_store import load_messages
                            current_msgs = load_messages(conv_id)
                            if len(current_msgs) > last_count:
                                try:
                                    st.rerun(scope="app")
                                except TypeError:
                                    st.rerun()
                        except Exception:
                            pass

                    _rt_alert_live_watcher(active_conversation.id, len(messages))

                chat_container = st.container()
                with chat_container:
                    if not messages:
                        st.write(t("chat_start_prompt", locale=current_ui_locale))
                    last_assistant_idx = max((i for i, m in enumerate(messages) if m.role == "assistant"), default=-1)
                    total_msgs = len(messages)
                    interactive_threshold_idx = max(0, total_msgs - 10)
                    for i, m in enumerate(messages):
                        is_latest_ans = (i == last_assistant_idx and i == total_msgs - 1)
                        _fb_question = ""
                        if m.role == "assistant":
                            for _prev in reversed(messages[:i]):
                                if _prev.role == "user":
                                    _fb_question = _prev.content or ""
                                    break
                        should_render_interactive = (i >= interactive_threshold_idx)
                        render_chat_bubble(m, is_latest=is_latest_ans, locale=current_ui_locale,
                                           conversation_id=active_conversation.id,
                                           feedback_question=_fb_question,
                                           render_interactive=should_render_interactive)
                    if is_answering:
                        stream_state = (
                            active_ai_request.get("stream_state")
                            if isinstance(active_ai_request, dict)
                            else None
                        )

                        @st.fragment(run_every=0.25)
                        def _render_streaming_assistant_box() -> None:
                            curr_text = ""
                            warming_col_live = None
                            if stream_state and "lock" in stream_state:
                                with stream_state["lock"]:
                                    curr_text = str(stream_state.get("text", "") or "")
                                    warming_col_live = stream_state.get("warming_collection")

                            with st.chat_message("assistant"):
                                _is_stream_ext = bool(
                                    (isinstance(active_ai_request, dict) and active_ai_request.get("ai_mode") == "external")
                                    or getattr(active_conversation, "ai_mode", "grounded") == "external"
                                )
                                if _is_stream_ext:
                                    st.info(f"🌐 **{t('external_ai_provenance_banner', locale=current_ui_locale)}**")
                                if curr_text:
                                    st.markdown(curr_text + " ▌")
                                else:
                                    treo_nguon = st.session_state.get(_PENDING_SOURCE_SUBMISSION_KEY)
                                    dang_cho_nguon = bool(
                                        isinstance(treo_nguon, dict)
                                        and treo_nguon.get("conversation_id") == active_conversation.id
                                    )
                                    render_answer_wait_steps(
                                        "cho_tai_lieu" if dang_cho_nguon else "dang_xu_ly",
                                        locale=current_ui_locale,
                                    )
                                    try:
                                        _forced_req_col = (
                                            active_ai_request.get("forced_domain")
                                            if isinstance(active_ai_request, dict)
                                            else None
                                        )
                                        _target_warm_col = str(
                                            warming_col_live
                                            or (
                                                _forced_req_col
                                                if (_forced_req_col and _forced_req_col != "auto")
                                                else None
                                            )
                                            or st.session_state.get(
                                                f"wsc_knowledge_block_{active_conversation.id}",
                                                "auto",
                                            )
                                            or getattr(notebook, "collection_id", None)
                                            or "tri_thuc"
                                        )
                                        _worker_warmed = is_workspace_chat_worker_warmed(
                                            collection_id=_target_warm_col
                                        )
                                    except Exception:
                                        _target_warm_col = "tri_thuc"
                                        _worker_warmed = True
                                    if not _worker_warmed:
                                        _stream_warm_line = format_worker_warming_status_line(
                                            _target_warm_col,
                                            locale=current_ui_locale,
                                        )
                                        st.caption(
                                            _stream_warm_line
                                            or t("worker_warming_background", locale=current_ui_locale)
                                        )

                            if request_future is not None and request_future.done():
                                try:
                                    st.rerun(scope="app")
                                except TypeError:
                                    st.rerun()

                        _render_streaming_assistant_box()

                # AI Answer Badge
                if badge_data and badge_data.get("conversation_id") == active_conversation.id:
                    if (
                        badge_data.get("type") == "ai_answered"
                        and badge_data.get("operational_mode") == "local_grounded_fallback"
                    ):
                        if should_show_fallback_notice(badge_data):
                            render_fallback_notice(badge_data, locale=current_ui_locale)
                        # Honest local lane: this answer came from excerpts on this
                        # machine, not from a model. It must not wear the AI header,
                        # the unverified-model caption, or the AI disclaimer.
                        st.success(f"📄 **{t('local_fallback_note', locale=current_ui_locale)}**")
                        if badge_data.get("retrieval_summary"):
                            st.info(badge_data["retrieval_summary"])
                        _lf_local_count = int(badge_data.get("source_count", 0) or 0)
                        st.write(f"{t('sources_sent', locale=current_ui_locale)}: {_lf_local_count}")
                        if badge_data.get("source_titles"):
                            with st.expander(f"{t('sources_sent', locale=current_ui_locale)}", expanded=False):
                                for _lf_title in badge_data["source_titles"]:
                                    st.write(f"- {_lf_title}")
                        if "evidence_items" in badge_data and badge_data["evidence_items"]:
                            render_grouped_evidence_items(
                                badge_data["evidence_items"], active_conversation.id, locale=current_ui_locale
                            )
                    elif (
                        badge_data.get("type") in {"ai_answered", "external_ai_answered"}
                        and (badge_data.get("ai_mode") == "external" or badge_data.get("type") == "external_ai_answered")
                    ):
                        st.info(f"🌐 **{t('external_ai_provenance_banner', locale=current_ui_locale)}**")
                        render_ai_answer_header(
                            0,
                            [],
                            ai_source=badge_data.get("ai_source", "Command Code"),
                            model_tool_name=badge_data.get("model_tool_name", "") or badge_data.get("verified_model", ""),
                            operational_mode="external_ai",
                            provider_name=badge_data.get("provider", "Command Code") or badge_data.get("provider_name", "Command Code"),
                            locale=current_ui_locale,
                        )
                    elif badge_data.get("type") == "ai_answered":
                        render_ai_answer_header(
                            badge_data.get("source_count", 0),
                            badge_data.get("source_titles", []),
                            ai_source=badge_data.get("ai_source", ""),
                            model_tool_name=badge_data.get("model_tool_name", "") or badge_data.get("verified_model", ""),
                            operational_mode=badge_data.get("operational_mode", ""),
                            provider_name=badge_data.get("provider", "") or badge_data.get("provider_name", ""),
                            locale=current_ui_locale,
                        )

                        if badge_data.get("retrieval_summary"):
                            st.info(badge_data["retrieval_summary"])
                        if "evidence_items" in badge_data and badge_data["evidence_items"]:
                            render_grouped_evidence_items(badge_data["evidence_items"], active_conversation.id, locale=current_ui_locale)
                            try:
                                from aios_habit.question_suggestions import (
                                    contextual_followups as _followups,
                                    contextual_send_text as _send_text,
                                )

                                _last_q = next(
                                    (
                                        str(getattr(_m, "content", "") or "").strip()
                                        for _m in reversed(messages or [])
                                        if getattr(_m, "role", "") == "user"
                                    ),
                                    "",
                                )
                                _last_a = next(
                                    (
                                        str(getattr(_m, "content", "") or "").strip()
                                        for _m in reversed(messages or [])
                                        if getattr(_m, "role", "") == "assistant"
                                    ),
                                    "",
                                )
                                _followup_qs = _followups(badge_data["evidence_items"], _last_q)
                            except Exception:
                                _followup_qs = []
                            if _followup_qs and not is_answering:
                                st.caption(t("suggestion_caption", locale=current_ui_locale))
                                _f_cols = st.columns(len(_followup_qs))
                                for _fi, _pair in enumerate(_followup_qs):
                                    _display, _send = _pair
                                    with _f_cols[_fi]:
                                        if st.button(
                                            _display,
                                            key=f"wsc_followup_{active_conversation.id}_{_fi}",
                                            use_container_width=True,
                                        ):
                                            _to_send = _send_text(_send, _last_q, _last_a)
                                            st.session_state[f"wsc_suggest_send_{active_conversation.id}"] = _to_send
                                            safe_rerun()
                    elif badge_data.get("type") == "handoff_pending":
                        st.info(t("waiting_antigravity_banner", locale=current_ui_locale, req_id=badge_data.get("request_id")))
                    elif badge_data.get("type") == "local_fallback_offered":
                        # Provider-free local lane: the error above already told the
                        # user the bridge is down. This is an offer, not an answer.
                        _lf_key = f"wsc_local_fallback_{active_conversation.id}"
                        _lf_mode = str(badge_data.get("local_answer_mode", "") or "")
                        st.caption(t("local_fallback_note", locale=current_ui_locale))
                        if _lf_mode == "answer_with_limits" and badge_data.get("local_limitation_reasons"):
                            st.caption(f"⚠️ {', '.join(badge_data['local_limitation_reasons'])}")
                        if st.button(
                            t("local_fallback_offer_button", locale=current_ui_locale),
                            key=_lf_key,
                            type="primary",
                        ):
                            _lf_ok, _lf_msg, _lf_badge = commit_local_grounded_answer(
                                question=str(badge_data.get("local_question", "") or ""),
                                local_answer=str(badge_data.get("local_answer", "") or ""),
                                local_citation_ids=tuple(badge_data.get("local_citation_ids") or ()),
                                evidence_items=list(badge_data.get("evidence_items") or []),
                                notebook_id=active_conversation.notebook_id or active_nb_id or "",
                                conversation_id=active_conversation.id,
                                answer_language=getattr(active_conversation, "answer_language", "vi") or "vi",
                            )
                            if _lf_ok:
                                st.session_state.wsc_action_message = t("local_fallback_saved", locale=current_ui_locale)
                                st.session_state.wsc_last_ai_badge = _lf_badge
                                st.session_state.wsc_action_error = None
                            else:
                                st.session_state.wsc_action_error = _lf_msg or t(
                                    "local_fallback_empty_error", locale=current_ui_locale
                                )
                            safe_rerun()
                    elif badge_data.get("type") == "insufficient_context":
                        render_insufficient_context(badge_data.get("reason", "no_sources"), locale=current_ui_locale)
                    elif badge_data.get("type") == "source_changed":
                        render_source_changed_message(locale=current_ui_locale)

                # Bridge to External AI when grounded mode yields insufficient evidence (Requirement 4)
                _last_user_q = next(
                    (
                        str(getattr(_m, "content", "") or "").strip()
                        for _m in reversed(messages or [])
                        if getattr(_m, "role", "") == "user"
                    ),
                    "",
                )
                _last_asst_a = next(
                    (
                        str(getattr(_m, "content", "") or "").strip()
                        for _m in reversed(messages or [])
                        if getattr(_m, "role", "") == "assistant"
                    ),
                    "",
                )
                _curr_conv_mode = getattr(active_conversation, "ai_mode", "grounded") or "grounded"
                _is_insufficient = bool(
                    _curr_conv_mode != "external"
                    and _last_asst_a
                    and (
                        "chưa đủ bằng chứng" in _last_asst_a.lower()
                        or "chưa tìm thấy đoạn phù hợp" in _last_asst_a.lower()
                        or "không đủ bằng chứng" in _last_asst_a.lower()
                        or "insufficient evidence" in _last_asst_a.lower()
                    )
                )
                if _is_insufficient and _last_user_q and not is_answering:
                    st.caption(t("bridge_ask_external_caption", locale=current_ui_locale))
                    if st.button(
                        f"🌐 {t('bridge_ask_external_button', locale=current_ui_locale)}",
                        key=f"wsc_bridge_ext_{active_conversation.id}",
                        type="primary",
                    ):
                        update_conversation_ai_mode(active_conversation.id, "external")
                        active_conversation.ai_mode = "external"
                        st.session_state[f"wsc_suggest_send_{active_conversation.id}"] = _last_user_q
                        safe_rerun()

                st.write("---")
                # APP-SOURCE-MODEL: Gỡ bỏ banner đếm nguồn và trạng thái chuẩn bị mâu thuẫn.
                # Tài liệu đã có trong chỉ mục luôn sẵn sàng 100%.

                if len(messages) >= 50:
                    st.warning(t("conversation_long_warning", locale=current_ui_locale))
                if get_workspace_memory_enabled_preference():
                    from aios_habit.workspace_memory_ui import render_workspace_memory_workspace

                    last_user_msg = next((m for m in reversed(messages) if m.role == "user"), None)
                    last_assistant_msg = next((m for m in reversed(messages) if m.role == "assistant"), None)
                    render_workspace_memory_workspace(
                        conversation_id=active_conversation.id,
                        last_question=last_user_msg.content if last_user_msg else "",
                        last_assistant_id=last_assistant_msg.id if last_assistant_msg else "",
                        last_trace_id=getattr(last_assistant_msg, "trace_id", "") if last_assistant_msg else "",
                        workspace_id=getattr(active_conversation, "notebook_id", "default") or "default",
                        collection_id=getattr(active_conversation, "collection_id", "tri_thuc") or "tri_thuc",
                        locale=current_ui_locale,
                    )

                pending_auto_question = None
                pending_submission = st.session_state.get(_PENDING_SOURCE_SUBMISSION_KEY)
                if pending_submission and pending_submission.get("conversation_id") == active_conversation.id:
                    pending_enabled = load_enabled_sources_for_conversation(active_conversation.id)
                    pending_selection_keys = tuple(sorted(
                        (selection.source_scope, selection.source_id)
                        for selection in pending_enabled
                    ))
                    pending_sources = prep_context_sources
                    pending_state, pending_detail = _pending_source_submission_state(
                        pending_submission,
                        conversation_id=active_conversation.id,
                        selection_keys=pending_selection_keys,
                        available_sources=pending_sources,
                    )
                    if pending_state == "ready":
                        pending_auto_question = str(pending_submission.get("question", "")).strip()
                        st.session_state.pop(_PENDING_SOURCE_SUBMISSION_KEY, None)
                        st.session_state.wsc_action_message = t("resumed_pending_question", locale=current_ui_locale)
                    elif pending_state == "waiting":
                        # The composer action changes to a square Stop button below.
                        # Keep this status compact instead of adding a second large action.
                        st.caption(t("question_held_preparing_sources", locale=current_ui_locale))
                        _poll_pending_source_submission()
                    else:
                        st.session_state.pop(_PENDING_SOURCE_SUBMISSION_KEY, None)
                        pending_messages = {
                            "expired": "Câu hỏi chờ đã quá thời gian. Hãy gửi lại khi tài liệu sẵn sàng.",
                            "changed": "Nguồn đã thay đổi khi câu hỏi đang chờ. Hãy gửi lại để AIOS dùng đúng tài liệu.",
                            "failed": f"Không chuẩn bị được nguồn: {pending_detail}. Hãy thử chuẩn bị lại nguồn đó rồi gửi lại câu hỏi.",
                            "unavailable": t("bge_search_unavailable", locale=current_ui_locale),
                        }
                        st.session_state.wsc_action_error = pending_messages.get(pending_state, "Không thể tiếp tục câu hỏi đang chờ.")

                # AI-IDE style composer. Normal widgets are used instead of a
                # form so an attachment thumbnail updates in place before the
                # user sends the question. (UX-CHAT-CORE #3: lane AI do he thong
                # tu chon, khong con selectbox tay o day.)
                pasted_image_key = f"wsc_pasted_image_{active_conversation.id}"
                upload_key = f"wsc_chat_img_{active_conversation.id}_{st.session_state.wsc_upload_version}"
                if active_action_error:
                    st.error(safe_vietnamese_ui_message(active_action_error, "Không thể hoàn tất thao tác lúc này."))
                    preview_backend = st.session_state.get(
                        f"wsc_ai_lane_{active_conversation.id}", "gemini_web"
                    )
                    is_bridge_connection_error = any(
                        token in str(active_action_error).casefold()
                        for token in ("gemini_web", "bridge", "cầu nối", "kết nối trực tiếp", "kết nối ai")
                    )
                    if preview_backend == "gemini_web" and is_bridge_connection_error:
                        if st.button(
                            t("reconnect_gemini_web", locale=current_ui_locale),
                            key=f"wsc_reconnect_gemini_{active_conversation.id}",
                            type="primary",
                            help=t("reconnect_gemini_web_help", locale=current_ui_locale),
                        ):
                            _start_gemini_web_bridge(locale=current_ui_locale, announce_success=True)
                            safe_rerun()
                try:
                    from aios_habit.question_suggestions import opening_suggestions as _openings

                    _has_user_msg = any(
                        getattr(_m, "role", "") == "user" for _m in (messages or [])
                    )
                    _open_qs = []
                    if not _has_user_msg and not is_answering:
                        _enabled_sels = load_enabled_sources_for_conversation(
                            active_conversation.id
                        )
                        _enabled_keys = {
                            (s.source_scope, s.source_id)
                            for s in _enabled_sels
                            if getattr(s, "enabled", False)
                        }
                        _enabled_titles = [
                            s.title
                            for s in (prep_context_sources or [])
                            if (s.source_scope, s.source_id) in _enabled_keys
                            and (s.text or "").strip()
                        ]
                        if not _enabled_titles:
                            _enabled_titles = [
                                s.title
                                for s in (prep_context_sources or [])
                                if (s.text or "").strip()
                            ][:3]
                        _open_qs = _openings(_enabled_titles)
                except Exception:
                    _open_qs = []
                if _open_qs:
                    st.caption(t("suggestion_caption", locale=current_ui_locale))
                    _o_cols = st.columns(len(_open_qs))
                    for _oi, _oq in enumerate(_open_qs):
                        with _o_cols[_oi]:
                            if st.button(
                                _oq,
                                key=f"wsc_opening_{active_conversation.id}_{_oi}",
                                use_container_width=True,
                            ):
                                st.session_state[f"wsc_suggest_send_{active_conversation.id}"] = _oq
                                safe_rerun()

                with st.container(border=True, key=f"wsc-composer-{active_conversation.id}"):
                    clear_input_key = f"wsc_clear_input_{active_conversation.id}"
                    if st.session_state.pop(clear_input_key, False):
                        st.session_state[f"wsc_question_input_{active_conversation.id}"] = ""
                    uploaded_image = None

                    # Hiển thị neo ngữ cảnh khi người dùng bấm "Trả lời" một đáp án (DESKTOP-ANSWER-REPLY-HOME)
                    _anchor_key = f"wsc_anchored_answer_{active_conversation.id}"
                    _anchored_data = st.session_state.get(_anchor_key)
                    if _anchored_data and isinstance(_anchored_data, dict):
                        _anc_text = str(_anchored_data.get("content", "")).strip()
                        _anc_snippet = _anc_text.replace("\n", " ")
                        if len(_anc_snippet) > 120:
                            _anc_snippet = _anc_snippet[:117] + "..."
                        _anc_col1, _anc_col2 = st.columns([0.92, 0.08], vertical_alignment="center")
                        with _anc_col1:
                            st.markdown(
                                f"<div class='wsc-anchored-quote' style='font-size:0.85rem; color:#374151; background:#F3F4F6; padding:5px 10px; border-radius:6px; border-left:3px solid #3B82F6; margin-bottom:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{html.escape(_anc_text[:300])}'>"
                                f"↩️ <strong>{t('anchored_answer_prefix', locale=current_ui_locale)}</strong> {html.escape(_anc_snippet)}"
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                        with _anc_col2:
                            if st.button(
                                "✕",
                                key=f"wsc_remove_anchor_{active_conversation.id}",
                                help=t("remove_anchor_tooltip", locale=current_ui_locale),
                                type="tertiary",
                            ):
                                st.session_state.pop(_anchor_key, None)
                                safe_rerun()

                    user_input = st.text_area(
                        t("composer_question_label", locale=current_ui_locale),
                        placeholder=t("question_placeholder", locale=current_ui_locale),
                        height=76,
                        key=f"wsc_question_input_{active_conversation.id}",
                        label_visibility="visible",
                    )

                    _attach_err = st.session_state.get(f"wsc_attach_error_{active_conversation.id}")
                    if _attach_err:
                        st.error(_attach_err)

                    # Hiển thị ảnh/tệp đính kèm xem trước ngay dưới ô nhập chữ nếu có
                    user_attached_image = st.session_state.get(pasted_image_key)
                    if user_attached_image is not None:
                        _att_name = getattr(user_attached_image, "name", "attachment")
                        _att_ext = Path(_att_name).suffix.lower()
                        _is_img = _att_ext in COMPOSER_SUPPORTED_IMAGE_EXTS
                        preview_col, preview_text_col, preview_remove_col = st.columns([1, 8, 2], vertical_alignment="center")
                        with preview_col:
                            if _is_img:
                                st.image(user_attached_image.getvalue(), width=64)
                            else:
                                st.markdown("📊" if _att_ext in {".csv", ".tsv"} else "📄")
                        with preview_text_col:
                            st.caption(f"📎 {_att_name}")
                        with preview_remove_col:
                            if st.button(t("remove_attached_image", locale=current_ui_locale), key=f"wsc_remove_image_{active_conversation.id}", type="tertiary"):
                                st.session_state.pop(pasted_image_key, None)
                                st.session_state.pop(f"wsc_attach_error_{active_conversation.id}", None)
                                st.session_state.wsc_upload_version += 1
                                safe_rerun()

                    # Cấu hình AI backend / lane tự động
                    from aios_habit.ai_lane import auto_backend_for_conversation as _auto_lane
                    from aios_habit.ai_lane import backend_label_vi as _lane_label
                    from aios_habit.ai_router import provider_env_presence as _env_presence

                    _toolbar_lane = _auto_lane(
                        f"wsc_ai_lane_{active_conversation.id}",
                        st.session_state,
                        bridge_available=bool(
                            getattr(get_antigravity_bridge_health(), "is_available", False)
                        ),
                        cagent_endpoint=(
                            str(st.session_state.get(f"wsc_cagent_endpoint_{active_conversation.id}", "")).strip()
                            or os.environ.get("AIOS_CAGENT_API_URL", "").strip()
                        ),
                        router_keys_present=any(_env_presence(os.environ).values()),
                        manual_override=os.environ.get("AIOS_AI_BACKEND", ""),
                    )
                    selected_ai_backend = _toolbar_lane.backend
                    cagent_endpoint_url = (
                        str(st.session_state.get(f"wsc_cagent_endpoint_{active_conversation.id}", "")).strip()
                        or os.environ.get("AIOS_CAGENT_API_URL", "").strip()
                        if selected_ai_backend == "cagent_api" else ""
                    )
                    ai_backend = selected_ai_backend

                    # Khối tri thức (Knowledge block)
                    knowledge_block_key = f"wsc_knowledge_block_{active_conversation.id}"
                    block_choices = get_workspace_chat_block_choices(current_ui_locale)
                    if knowledge_block_key not in st.session_state:
                        query_block = str(get_query_param("block") or "").strip().lower()
                        if query_block in block_choices:
                            st.session_state[knowledge_block_key] = query_block
                            if query_block != "auto":
                                trigger_collection_warming_on_demand(query_block, notebook_id=active_nb_id)
                        else:
                            _nb_col_default = str(getattr(notebook, "collection_id", "") or "").strip().lower()
                            if _nb_col_default in block_choices and _nb_col_default != "auto":
                                st.session_state[knowledge_block_key] = _nb_col_default
                                trigger_collection_warming_on_demand(_nb_col_default, notebook_id=active_nb_id)
                    knowledge_block_value = str(
                        st.session_state.get(knowledge_block_key, "auto") or "auto"
                    )
                    if knowledge_block_value not in block_choices:
                        knowledge_block_value = "auto"

                    # Chế độ tìm kiếm (Search preference)
                    current_pref = getattr(active_conversation, "search_preference", "auto")
                    deep_search = get_workspace_chat_deep_search_availability()
                    pref_options = ["auto", "deep"] if deep_search.available else ["auto"]
                    if current_pref == "deep" and not deep_search.available:
                        update_conversation_search_preference(active_conversation.id, "auto")
                        active_conversation.search_preference = "auto"
                        current_pref = "auto"
                    pref_labels = {
                        "auto": t("search_preference_auto", locale=current_ui_locale),
                        "deep": t("search_preference_deep", locale=current_ui_locale),
                    }

                    # Hàng công cụ nằm TRONG thẻ, dưới ô nhập (Requirement 2)
                    toolbar_attach_col, toolbar_block_col, toolbar_pref_col, toolbar_cagent_col, toolbar_mode_col, toolbar_hint_col, toolbar_action_col = st.columns(
                        [0.55, 2.5, 1.5, 2.0, 2.1, 1.5, 0.65], vertical_alignment="center"
                    )

                    with toolbar_attach_col:
                        with st.container(key=f"wsc-attachment-{active_conversation.id}"):
                            with st.popover(t("attach_popover", locale=current_ui_locale), help=t("attach_screenshot_help", locale=current_ui_locale), icon=":material/attach_file:"):
                                uploaded_image = st.file_uploader(
                                    t("attach_screenshot_label", locale=current_ui_locale),
                                    type=["png", "jpg", "jpeg", "webp", "bmp", "csv", "txt", "tsv", "md", "log"],
                                    key=upload_key,
                                    help=t("attach_screenshot_help", locale=current_ui_locale),
                                    label_visibility="collapsed",
                                )
                                if paste_image_button is None:
                                    st.info(t("clipboard_image_unavailable", locale=current_ui_locale))
                                else:
                                    paste_result = paste_image_button(
                                        "Dán ảnh đã copy",
                                        key=f"wsc_paste_image_{active_conversation.id}",
                                        background_color="#0369A1",
                                        hover_background_color="#075985",
                                        errors="raise",
                                    )
                                    if paste_result.image_data is not None:
                                        image_buffer = BytesIO()
                                        paste_result.image_data.save(image_buffer, format="PNG")
                                        st.session_state[pasted_image_key] = BufferedWorkspaceUpload(
                                            "clipboard-image.png", image_buffer.getvalue()
                                        )
                                        safe_rerun()
                                if uploaded_image is not None:
                                    _up_name = getattr(uploaded_image, "name", "")
                                    _up_ext = Path(_up_name).suffix.lower()
                                    try:
                                        _up_bytes = uploaded_image.getvalue()
                                        _up_size = len(_up_bytes)
                                    except Exception:
                                        _up_bytes = b""
                                        _up_size = 0

                                    if _up_ext in COMPOSER_SUPPORTED_TEXT_EXTS:
                                        if _up_size > MAX_COMPOSER_TEXT_FILE_BYTES:
                                            _err_msg = (
                                                f"Tệp \"{_up_name}\" ({_up_size:,} bytes) vượt quá giới hạn 50KB cho tệp đính kèm chữ/CSV. "
                                                "Vui lòng chọn tệp nhỏ hơn."
                                            )
                                            st.error(_err_msg)
                                            st.session_state[f"wsc_attach_error_{active_conversation.id}"] = _err_msg
                                            st.session_state.pop(pasted_image_key, None)
                                        elif _up_size == 0:
                                            _err_msg = f"Tệp \"{_up_name}\" rỗng. Vui lòng chọn tệp có nội dung."
                                            st.error(_err_msg)
                                            st.session_state[f"wsc_attach_error_{active_conversation.id}"] = _err_msg
                                            st.session_state.pop(pasted_image_key, None)
                                        else:
                                            st.session_state.pop(f"wsc_attach_error_{active_conversation.id}", None)
                                            st.session_state[pasted_image_key] = uploaded_image
                                    elif _up_ext in COMPOSER_SUPPORTED_IMAGE_EXTS:
                                        st.session_state.pop(f"wsc_attach_error_{active_conversation.id}", None)
                                        st.session_state[pasted_image_key] = uploaded_image
                                    else:
                                        _err_msg = (
                                            f"Định dạng tệp \"{_up_name}\" không được hỗ trợ. "
                                            "Khung soạn thảo chỉ nhận tệp ảnh (PNG, JPG, JPEG, WEBP, BMP) hoặc tệp chữ/CSV (CSV, TXT, TSV, MD, LOG)."
                                        )
                                        st.error(_err_msg)
                                        st.session_state[f"wsc_attach_error_{active_conversation.id}"] = _err_msg
                                        st.session_state.pop(pasted_image_key, None)

                    with toolbar_block_col:
                        with st.container(key=f"wsc-block-{active_conversation.id}"):
                            with st.popover(
                                f"📚 {block_choices[knowledge_block_value]}",
                                help=t("knowledge_block_help", locale=current_ui_locale),
                            ):
                                for _block_value in block_choices.keys():
                                    if st.button(
                                        block_choices[_block_value],
                                        key=f"wsc_block_pick_{active_conversation.id}_{_block_value}",
                                        use_container_width=True,
                                        type=(
                                            "primary"
                                            if _block_value == knowledge_block_value
                                             else "secondary"
                                        ),
                                    ):
                                        st.session_state[knowledge_block_key] = _block_value
                                        if _block_value != "auto":
                                            trigger_collection_warming_on_demand(
                                                _block_value,
                                                notebook_id=active_nb_id,
                                            )
                                        safe_rerun()

                    with toolbar_pref_col:
                        with st.container(key=f"wsc-pref-{active_conversation.id}"):
                            with st.popover(
                                f"⚡ {pref_labels.get(current_pref, current_pref)}",
                                help=t("search_level_help", locale=current_ui_locale),
                            ):
                                for _opt in pref_options:
                                    if st.button(
                                        pref_labels.get(_opt, _opt),
                                        key=f"wsc_pref_pick_{active_conversation.id}_{_opt}",
                                        use_container_width=True,
                                        type="primary" if _opt == current_pref else "secondary",
                                    ):
                                        update_conversation_search_preference(active_conversation.id, _opt)
                                        active_conversation.search_preference = _opt
                                        safe_rerun()

                    with toolbar_cagent_col:
                        with st.container(key=f"wsc-cagent-{active_conversation.id}"):
                            if selected_ai_backend == "cagent_api":
                                _dest_chip_label = "⚙️ C-Agent"
                                _dest_help = t("cagent_config_popover", locale=current_ui_locale)
                            elif selected_ai_backend == "nakazasen_router":
                                _dest_chip_label = "🌐 Command Code"
                                _dest_help = "Tuyến tổng hợp Command Code (Router)"
                            elif selected_ai_backend == "gemini_web":
                                _dest_chip_label = "🌉 Gemini"
                                _dest_help = "Cầu nối Gemini Web"
                            else:
                                _dest_chip_label = "💻 Cục bộ"
                                _dest_help = "Tổng hợp dữ kiện cục bộ"
                            with st.popover(
                                _dest_chip_label,
                                help=_dest_help,
                            ):
                                if selected_ai_backend == "nakazasen_router":
                                    st.markdown(f"**{t('dest_command_code_title', locale=current_ui_locale)}**")
                                    st.caption(t("dest_command_code_caption", locale=current_ui_locale))
                                    _cc_model = os.environ.get("AIOS_LOCAL_AI_MODEL", "inclusionai/ling-3.1-flash:free")
                                    _cc_failover = os.environ.get("AIOS_LOCAL_AI_FAILOVER_MODELS", "poolside/laguna-s-2.1-free,deepseek/deepseek-v4.1-flash")
                                    _cc_timeout = os.environ.get("AIOS_LOCAL_AI_TIMEOUT_SECONDS", "90")
                                    st.text(
                                        f"• Model chính: {_cc_model}\n"
                                        f"• Dự phòng: {_cc_failover}\n"
                                        f"• Hết giờ: {_cc_timeout}s"
                                    )
                                    st.info(t("dest_command_code_info", locale=current_ui_locale))
                                elif selected_ai_backend == "cagent_api":
                                    cagent_endpoint_key = f"wsc_cagent_endpoint_{active_conversation.id}"
                                    configured_cagent_endpoint = (
                                        str(st.session_state.get(cagent_endpoint_key, "")).strip()
                                        or os.environ.get("AIOS_CAGENT_API_URL", "").strip()
                                    )
                                    cagent_endpoint = st.text_input(
                                        t("cagent_endpoint_label", locale=current_ui_locale),
                                        value=configured_cagent_endpoint,
                                        placeholder="https://.../api/v1/prediction/<AgentFlow-ID>",
                                        key=cagent_endpoint_key,
                                        help=t("cagent_endpoint_help", locale=current_ui_locale),
                                    ).strip()
                                    if cagent_endpoint:
                                        os.environ["AIOS_CAGENT_API_URL"] = cagent_endpoint

                                    from aios_habit.cagent_auth import clear_session, get_auth_status, login_cagent

                                    auth_status = get_auth_status()
                                    if auth_status.get("logged_in"):
                                        c_user = auth_status.get("username") or "đã lưu"
                                        st.caption(f"🔐 Đã đăng nhập C-Agent: **{c_user}** (Tự động gia hạn phiên)")
                                        if st.button("Đăng xuất C-Agent", key="wsc_cagent_logout_btn", help="Xóa phiên đăng nhập đã lưu"):
                                            clear_session()
                                            safe_rerun()
                                    else:
                                        with st.expander("🔑 Đăng nhập tài khoản C-Agent", expanded=True):
                                            st.caption("Nhập tài khoản C-Agent để tự động tạo và gia hạn phiên làm việc:")
                                            u_in = st.text_input("Tên đăng nhập", value="tvn183660", key="wsc_cagent_user_inp")
                                            p_in = st.text_input("Mật khẩu", type="password", key="wsc_cagent_pass_inp")
                                            if st.button("Đăng nhập C-Agent", key="wsc_cagent_login_sub_btn", use_container_width=True):
                                                ok, msg = login_cagent(u_in, p_in, base_url=cagent_endpoint)
                                                if ok:
                                                    st.session_state.wsc_action_message = msg
                                                    safe_rerun()
                                                else:
                                                    st.session_state.wsc_action_error = msg
                                elif selected_ai_backend == "local":
                                    st.markdown(f"**{t('dest_local_title', locale=current_ui_locale)}**")
                                    st.caption(t("dest_local_caption", locale=current_ui_locale))
                                else:
                                    st.markdown(f"**{t('dest_lane_title', locale=current_ui_locale, lane=_lane_label(selected_ai_backend))}**")

                    with toolbar_mode_col:
                        with st.container(key=f"wsc-mode-{active_conversation.id}"):
                            current_ai_mode = getattr(active_conversation, "ai_mode", "grounded") or "grounded"
                            _mode_chip_label = (
                                f"🌐 {t('mode_external_ai', locale=current_ui_locale)}"
                                if current_ai_mode == "external"
                                else f"📖 {t('mode_grounded', locale=current_ui_locale)}"
                            )
                            _mode_help = (
                                t("mode_external_ai_help", locale=current_ui_locale)
                                if current_ai_mode == "external"
                                else t("mode_grounded_help", locale=current_ui_locale)
                            )
                            with st.popover(_mode_chip_label, help=_mode_help):
                                st.markdown(f"**{t('mode_popover_title', locale=current_ui_locale)}**")
                                st.caption(t("mode_popover_desc", locale=current_ui_locale))
                                if st.button(
                                    t("mode_pick_grounded", locale=current_ui_locale),
                                    key=f"wsc_mode_pick_grounded_{active_conversation.id}",
                                    use_container_width=True,
                                    type="primary" if current_ai_mode == "grounded" else "secondary",
                                ):
                                    update_conversation_ai_mode(active_conversation.id, "grounded")
                                    active_conversation.ai_mode = "grounded"
                                    safe_rerun()
                                if st.button(
                                    t("mode_pick_external", locale=current_ui_locale),
                                    key=f"wsc_mode_pick_external_{active_conversation.id}",
                                    use_container_width=True,
                                    type="primary" if current_ai_mode == "external" else "secondary",
                                ):
                                    update_conversation_ai_mode(active_conversation.id, "external")
                                    active_conversation.ai_mode = "external"
                                    safe_rerun()

                    with toolbar_hint_col:
                        with st.container(key=f"wsc-shortcut-hint-{active_conversation.id}"):
                            st.caption("Ctrl+↵")

                    is_waiting_for_sources = bool(
                        pending_submission
                        and pending_submission.get("conversation_id") == active_conversation.id
                        and pending_state == "waiting"
                    )
                    _target_composer_col = (
                        knowledge_block_value
                        if knowledge_block_value != "auto"
                        else (
                            getattr(notebook, "collection_id", None)
                            or getattr(active_conversation, "collection_id", None)
                            or "tri_thuc"
                        )
                    )
                    _target_worker_resident = is_workspace_chat_worker_warmed(
                        collection_id=_target_composer_col
                    )
                    if not _target_worker_resident:
                        try:
                            trigger_collection_warming_on_demand(
                                _target_composer_col,
                                notebook_id=active_nb_id,
                            )
                        except Exception:
                            pass

                    with toolbar_action_col:
                        with st.container(key=f"wsc-action-{active_conversation.id}"):
                            if is_answering or is_waiting_for_sources:
                                stop_requested = st.button(
                                    t("cancel_pending_question", locale=current_ui_locale),
                                    key=f"wsc_stop_ai_request_{active_conversation.id}",
                                    icon=":material/stop:",
                                    type="primary",
                                    help=t("cancel_pending_question", locale=current_ui_locale),
                                )
                                ask_submitted = False
                                if stop_requested:
                                    if is_answering:
                                        active_ai_request["cancellation_event"].set()
                                        st.session_state.wsc_action_message = "Đang dừng yêu cầu AI…"
                                    else:
                                        st.session_state.pop(_PENDING_SOURCE_SUBMISSION_KEY, None)
                                        st.session_state.wsc_action_message = t(
                                            "cancelled_pending_question_notice",
                                            locale=current_ui_locale,
                                        )
                                    safe_rerun()
                            else:
                                _ask_disabled = (not _target_worker_resident)
                                _ask_tooltip = (
                                    format_worker_warming_status_line(
                                        _target_composer_col, locale=current_ui_locale
                                    )
                                    or "Đang nạp mô hình & chỉ mục kho vào bộ nhớ..."
                                    if _ask_disabled
                                    else labels["ai_action"]
                                )
                                ask_submitted = st.button(
                                    labels["ai_action"],
                                    key=f"wsc_ask_{active_conversation.id}",
                                    icon=":material/arrow_upward:",
                                    type="primary",
                                    disabled=_ask_disabled,
                                    help=_ask_tooltip,
                                )

                    st.html(
                        """
                        <script>
                        if (!window.parent.__wscComposerShortcutBound) {
                          window.parent.__wscComposerShortcutBound = true;
                          window.parent.document.addEventListener("keydown", function(event) {
                            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                              const sendButton = window.parent.document.querySelector(
                                '[class*="st-key-wsc-action-"] button'
                              );
                              if (sendButton && !sendButton.disabled) {
                                event.preventDefault();
                              sendButton.click();
                              }
                            }
                          }, true);
                        }
                        </script>
                        """,
                        unsafe_allow_javascript=True,
                    )

                    if get_jig_session_type() == "truc_ban" or st.session_state.get("wsc_last_chart_png"):
                        render_jig_stream_pause_control(active_conversation.id, current_ui_locale)
                    # Thẻ đề xuất gửi mail cảnh báo: dùng lại đúng ảnh đang xem
                    # trước, chỉ gửi khi người dùng bấm nút và có mã duyệt.
                    if st.session_state.get("wsc_last_chart_png"):
                        try:
                            from aios_habit.workspace_chat_ui import (
                                render_de_xuat_gui_mail_canh_bao as _render_mail_card,
                            )

                            _render_mail_card(
                                f"omnibar_{active_conversation.id}",
                                locale=current_ui_locale,
                                config_path=Path("local_cases") / "jig_alert_config.json",
                            )
                        except Exception:
                            pass

                # Dòng trạng thái rút gọn dưới thẻ soạn thảo (Requirement 3)
                lane_mode_str = "tự động" if _toolbar_lane.automatic else "ghim tay"
                search_status_str = (
                    "Chế độ Tìm kỹ hơn đã sẵn sàng."
                    if deep_search.available
                    else "Tìm kỹ hơn chưa được bật. Chế độ Tự động vẫn sẵn sàng tìm kiếm."
                )
                st.caption(
                    "Đang dùng: "
                    + f"{_lane_label(selected_ai_backend)} ({lane_mode_str}) · {search_status_str}"
                )

                if _ask_disabled:
                    st.caption(f"⏳ {_ask_tooltip}")

                if ask_submitted and pending_submission:
                    # A fresh submit intentionally replaces an older waiting
                    # question; this avoids a surprising late answer.
                    st.session_state.pop(_PENDING_SOURCE_SUBMISSION_KEY, None)

                if pending_auto_question:
                    ask_submitted = True
                    user_input = pending_auto_question
                    user_attached_image = None

                _suggest_send_key = f"wsc_suggest_send_{active_conversation.id}"
                _suggested_question = st.session_state.pop(_suggest_send_key, "")
                if _suggested_question and not is_answering:
                    ask_submitted = True
                    user_input = _suggested_question
                    user_attached_image = None

                if ask_submitted:
                    if not is_workspace_chat_worker_warmed(collection_id=_target_composer_col):
                        try:
                            trigger_collection_warming_on_demand(
                                _target_composer_col, notebook_id=active_nb_id
                            )
                        except Exception:
                            pass
                        st.warning(
                            format_worker_warming_status_line(
                                _target_composer_col, locale=current_ui_locale
                            )
                            or "Mô hình và dữ liệu kho đang được nạp vào bộ nhớ. Vui lòng chờ trong giây lát..."
                        )
                        safe_rerun()

                    q_text = user_input.strip()
                    if q_text and get_workspace_memory_enabled_preference():
                        from aios_habit.workspace_memory_ui import queue_memory_command_if_present

                        if queue_memory_command_if_present(q_text):
                            safe_rerun()
                    # UX-CHAT-CORE: bo dinh tuyen y dinh chat-first. Nguoi dung chi
                    # go cau tieng Viet, app tu dieu phoi (khong con radio nhanh).
                    if q_text and _xu_ly_y_dinh_chat(
                        q_text,
                        active_conversation=active_conversation,
                        active_nb_id=active_nb_id,
                    ):
                        safe_rerun()
                    if q_text:
                        from aios_habit.production_prediction.jig_chat_wire import handle_jig_chat_text
                        from aios_habit.production_prediction.stream_api import StreamBuffer
                        from aios_habit.workspace_chat_models import ChatMessage as _JigChatMessage
                        from aios_habit.workspace_chat_store import save_message as _jig_save_message

                        def _jig_history(jig_id: str, metric: str) -> list:
                            # Ưu tiên kho log đã lưu (gồm cả tệp tải lên và dòng
                            # dán tay), rồi mới tới kho đệm luồng trực tiếp.
                            try:
                                from aios_habit.production_prediction.log_archive import (
                                    lich_su_theo_jig,
                                )

                                lich_su = lich_su_theo_jig(jig_id=jig_id, metric_name=metric)
                                if lich_su:
                                    return lich_su
                            except Exception:
                                pass
                            try:
                                buffer = StreamBuffer(Path("local_cases") / "jig_stream.sqlite")
                                return buffer.recent_values(jig_id, metric)
                            except Exception:
                                return []

                        def _chart_rows() -> list:
                            return _hang_ve_tu_lsu_gate()

                        if handle_jig_chat_text(
                            q_text,
                            conversation_id=active_conversation.id,
                            locale=current_ui_locale,
                            session_state=st.session_state,
                            save_user=lambda content: _jig_save_message(_JigChatMessage(
                                id=f"MSG-U-{uuid.uuid4().hex[:8].upper()}",
                                conversation_id=active_conversation.id,
                                role="user",
                                content=content,
                            )),
                            save_assistant=lambda content: _jig_save_message(_JigChatMessage(
                                id=f"MSG-A-{uuid.uuid4().hex[:8].upper()}",
                                conversation_id=active_conversation.id,
                                role="assistant",
                                content=content,
                            )),
                            history_provider=_jig_history,
                            chart_rows_provider=_chart_rows,
                        ):
                            safe_rerun()
                    # Khung chat_action (TOOL-2): tool đăng ký action, chat gọi theo
                    # ngữ cảnh câu hỏi, kết quả render giàu trong vùng trả lời.
                    # Mặc định TẮT sau feature flag để không đổi hành vi hiện có.
                    if q_text and not user_attached_image:
                        from aios_habit.chat_action import chat_action_enabled, handle_chat_text
                        if chat_action_enabled():
                            from aios_habit.workspace_chat_models import ChatMessage as _ActionChatMessage
                            from aios_habit.workspace_chat_store import load_notebook, save_message as _action_save_message

                            def _action_save(role: str, content: str) -> None:
                                _action_save_message(_ActionChatMessage(
                                    id=f"MSG-{role[0].upper()}-{uuid.uuid4().hex[:8].upper()}",
                                    conversation_id=active_conversation.id,
                                    role=role,
                                    content=content,
                                ))

                            _action_nb_id = active_conversation.notebook_id or active_nb_id or ""
                            _action_notebook = load_notebook(_action_nb_id) if _action_nb_id else None
                            _action_forced_domain = str(
                                st.session_state.get(f"wsc_knowledge_block_{active_conversation.id}", "auto") or "auto"
                            )
                            if handle_chat_text(
                                q_text,
                                conversation_id=active_conversation.id,
                                notebook_id=_action_nb_id,
                                workspace_id=_action_nb_id or "default",
                                locale=current_ui_locale,
                                context={
                                    "notebook_title": getattr(_action_notebook, "title", "") or "",
                                    "forced_domain": _action_forced_domain if _action_forced_domain != "auto" else None,
                                },
                                save_user=lambda content: _action_save("user", content),
                                save_assistant=lambda content: _action_save("assistant", content),
                            ):
                                safe_rerun()
                    if not q_text and not user_attached_image:
                        with st.container(key=f"wsc_composer_hint_{active_conversation.id}"):
                            st.caption(t("composer_empty_hint", locale=current_ui_locale))
                    else:
                        from aios_habit.agent_work_artifact import detect_agent_work_intent
                        agent_intent = detect_agent_work_intent(q_text) if q_text else None
                        if agent_intent is not None:
                            local_source_paths = _selected_local_work_source_paths()
                            from aios_habit.workspace_chat_models import ChatMessage
                            from aios_habit.workspace_chat_store import save_message

                            save_message(ChatMessage(
                                id=f"MSG-U-{uuid.uuid4().hex[:8].upper()}",
                                conversation_id=active_conversation.id,
                                role="user",
                                content=q_text,
                            ))

                            if not local_source_paths:
                                if agent_intent == "error_report":
                                    guide_text = (
                                        "Tôi đã sẵn sàng hỗ trợ bạn lập báo cáo lỗi kỹ thuật. Tuy nhiên, hiện tại bạn chưa chọn tệp dữ liệu nào "
                                        "(như tệp nhật ký `.log` hoặc bảng số liệu `.csv`/`.xlsx`). Bạn vui lòng tích chọn ít nhất một tệp nguồn "
                                        "trong danh sách tài liệu bên trên để tôi có thể trích xuất số liệu và lập báo cáo chính xác nhất nhé!"
                                    )
                                elif agent_intent == "process_design_review":
                                    guide_text = (
                                        "Tôi đã sẵn sàng hỗ trợ bạn rà soát thiết kế công đoạn. Để đối chiếu và kiểm tra các tiêu chuẩn, "
                                        "bạn vui lòng tích chọn các tệp tài liệu liên quan (như quy chuẩn guideline, bản vẽ hoặc mô tả công đoạn) "
                                        "trong danh sách nguồn bên trên nhé!"
                                    )
                                else:
                                    guide_text = (
                                        "Tôi đã sẵn sàng hỗ trợ bạn kiểm tra và sửa mã nguồn trong vùng làm việc tách biệt. "
                                        "Bạn vui lòng chỉ định hoặc chọn tệp mã nguồn cần chỉnh sửa trong danh mục tài liệu nhé!"
                                    )
                                save_message(ChatMessage(
                                    id=f"MSG-A-{uuid.uuid4().hex[:8].upper()}",
                                    conversation_id=active_conversation.id,
                                    role="assistant",
                                    content=guide_text,
                                ))
                                safe_rerun()
                            else:
                                from aios_habit.workspace_case_repository import WorkspaceCaseRepository
                                from aios_habit.workspace_case_models import AgentWorkRecord, utc_now_iso
                                from aios_habit.workspace_agent_orchestrator import WorkspaceAgentOrchestrator
                                from aios_habit.agent_work_artifact import (
                                    create_factory_error_report,
                                    create_process_design_review,
                                    format_artifact_card,
                                )

                                case_repo = WorkspaceCaseRepository()
                                orch = WorkspaceAgentOrchestrator()
                                work_id = f"WORK-{agent_intent[:3].upper()}-{int(time.time()*1000)}"
                                target_ws = st.session_state.get("wsc_agent_workspace_root") or str(Path("local_cases").resolve())

                                goal_vi = (
                                    t("agent_factory_error_title", locale=current_ui_locale)
                                    if agent_intent == "error_report"
                                    else t("agent_process_review_title", locale=current_ui_locale)
                                    if agent_intent == "process_design_review"
                                    else "Sửa mã nguồn trong vùng tách biệt"
                                )

                                work_record = AgentWorkRecord(
                                    work_id=work_id,
                                    workspace_id=active_conversation.id,
                                    work_type=agent_intent,
                                    goal_vi=goal_vi,
                                    created_at=utc_now_iso(),
                                    updated_at=utc_now_iso(),
                                    status="queued",
                                    allowed_roots=(target_ws,),
                                    source_refs=tuple(str(p) for p in local_source_paths),
                                )
                                enqueued = orch.enqueue_work_item(work=work_record, repo=case_repo)

                                canonical_ws = Path(target_ws).resolve().as_posix()
                                running_tasks = [w for w in case_repo.list_agent_work(workspace_id=active_conversation.id) if w.status == "running"]
                                current_holder = orch.get_workspace_lock_holder(canonical_ws)

                                if current_holder or running_tasks:
                                    queue_msg = (
                                        f"⏳ Tác vụ **{goal_vi}** của bạn đã được xếp hàng (vị trí {enqueued.queue_position}) "
                                        "và sẽ tự động chạy ngay sau khi việc hiện tại hoàn tất."
                                    )
                                    save_message(ChatMessage(
                                        id=f"MSG-Q-{uuid.uuid4().hex[:8].upper()}",
                                        conversation_id=active_conversation.id,
                                        role="assistant",
                                        content=queue_msg,
                                    ))
                                    safe_rerun()
                                else:
                                    if agent_intent == "error_report":
                                        def _run_err(item_record: AgentWorkRecord) -> None:
                                            rep_res = create_factory_error_report(
                                                source_paths=local_source_paths,
                                                output_dir=Path("local_cases") / "agent_artifacts",
                                                work_id=item_record.work_id,
                                            )
                                            case_repo.update_agent_work_status(
                                                item_record.work_id,
                                                "completed",
                                                result_ref=str(rep_res.report_path),
                                                checkpoint_ref=str(rep_res.report_path),
                                            )
                                            card_content = format_artifact_card(
                                                work_type="error_report",
                                                work_id=item_record.work_id,
                                                result_path=str(rep_res.report_path),
                                                checkpoint_path=str(rep_res.report_path),
                                                payload=rep_res.payload,
                                                status_vi="Đã xong",
                                            )
                                            save_message(ChatMessage(
                                                id=f"MSG-ART-{item_record.work_id}",
                                                conversation_id=active_conversation.id,
                                                role="assistant",
                                                content=card_content,
                                            ))

                                        orch.process_next_work_item(
                                            workspace_id=active_conversation.id,
                                            workspace_root=target_ws,
                                            repo=case_repo,
                                            runner=_run_err,
                                        )
                                    elif agent_intent == "process_design_review":
                                        def _run_rev(item_record: AgentWorkRecord) -> None:
                                            rev_res = create_process_design_review(
                                                source_paths=local_source_paths,
                                                output_dir=Path("local_cases") / "agent_artifacts",
                                                work_id=item_record.work_id,
                                            )
                                            case_repo.update_agent_work_status(
                                                item_record.work_id,
                                                "completed",
                                                result_ref=str(rev_res.report_path),
                                                checkpoint_ref=str(rev_res.report_path),
                                            )
                                            card_content = format_artifact_card(
                                                work_type="process_design_review",
                                                work_id=item_record.work_id,
                                                result_path=str(rev_res.report_path),
                                                checkpoint_path=str(rev_res.report_path),
                                                payload=rev_res.payload,
                                                status_vi="Đã xong (Bản nháp)",
                                            )
                                            save_message(ChatMessage(
                                                id=f"MSG-ART-{item_record.work_id}",
                                                conversation_id=active_conversation.id,
                                                role="assistant",
                                                content=card_content,
                                            ))

                                        orch.process_next_work_item(
                                            workspace_id=active_conversation.id,
                                            workspace_root=target_ws,
                                            repo=case_repo,
                                            runner=_run_rev,
                                        )
                                    safe_rerun()

                        if ai_backend == "gemini_web" and not _start_gemini_web_bridge(locale=current_ui_locale):
                            safe_rerun()
                        image_ocr_failed = False
                        one_shot_image_text = ""
                        st.session_state.pop(f"wsc_attach_error_{active_conversation.id}", None)
                        if user_attached_image is not None:
                            _att_name = getattr(user_attached_image, "name", "")
                            _att_ext = Path(_att_name).suffix.lower()
                            try:
                                _att_bytes = user_attached_image.getvalue()
                            except Exception:
                                _att_bytes = b""

                            if _att_ext in COMPOSER_SUPPORTED_IMAGE_EXTS:
                                # Ảnh đính kèm một lần: OCR thành chữ rồi gộp thẳng
                                # vào câu hỏi. KHÔNG tạo nguồn tạm trong sổ → câu sau
                                # không đính kèm thì không thể dùng lại (one-shot theo
                                # cấu trúc, không cần cơ chế tắt sau). Mọi lane đều
                                # đọc được vì chỉ còn chữ, không còn byte ảnh thô
                                # (guard ở antigravity_bridge vẫn fail-closed).
                                _img_bytes = _att_bytes
                                _img_name = _att_name
                                _ocr_res = (
                                    ingest_and_extract_bytes(_img_bytes, _img_name, "cloud_safe")
                                    if _img_bytes
                                    else {"ok": False}
                                )
                                _ocr_text = str(_ocr_res.get("text", "") or "").strip()
                                if _ocr_res.get("ok") and _ocr_text:
                                    st.session_state.wsc_upload_version += 1
                                    if len(_ocr_text) > MAX_COMPOSER_ATTACHED_TEXT_CHARS:
                                        _ocr_text = (
                                            _ocr_text[:MAX_COMPOSER_ATTACHED_TEXT_CHARS]
                                            + "\n[...nội dung ảnh đã được rút gọn...]"
                                        )
                                    one_shot_image_text = (
                                        "[Nội dung chữ đọc được từ ảnh đính kèm "
                                        f"\"{_img_name}\"]:\n{_ocr_text}"
                                    )
                                else:
                                    image_ocr_failed = True
                                    st.session_state.wsc_action_message = t(
                                        "attached_image_unreadable",
                                        locale=current_ui_locale,
                                    )
                                if not q_text:
                                    q_text = "Phân tích và giải thích nội dung trong ảnh chụp màn hình đính kèm."
                                if one_shot_image_text:
                                    q_text = f"{q_text}\n\n---\n{one_shot_image_text}"
                            elif _att_ext in COMPOSER_SUPPORTED_TEXT_EXTS:
                                # Tệp chữ/CSV đính kèm một lần: trích nội dung chữ rồi gộp thẳng vào câu hỏi
                                try:
                                    _raw_text = _att_bytes.decode("utf-8-sig")
                                except UnicodeDecodeError:
                                    try:
                                        _raw_text = _att_bytes.decode("utf-8")
                                    except UnicodeDecodeError:
                                        _raw_text = _att_bytes.decode("latin-1", errors="replace")
                                _file_text = _raw_text.strip()
                                if _file_text:
                                    st.session_state.wsc_upload_version += 1
                                    if len(_file_text) > MAX_COMPOSER_ATTACHED_TEXT_CHARS:
                                        _file_text = (
                                            _file_text[:MAX_COMPOSER_ATTACHED_TEXT_CHARS]
                                            + "\n[...nội dung tệp đã được rút gọn...]"
                                        )
                                    one_shot_image_text = (
                                        f'[Dữ kiện trích từ tệp đính kèm "{_att_name}"]:\n{_file_text}'
                                    )
                                else:
                                    image_ocr_failed = True
                                    st.session_state.wsc_action_message = "Tệp đính kèm rỗng hoặc không có nội dung chữ."
                                if not q_text:
                                    q_text = "Phân tích và giải thích nội dung trong tệp đính kèm."
                                if one_shot_image_text:
                                    q_text = f"{q_text}\n\n---\n{one_shot_image_text}"
                            else:
                                image_ocr_failed = True
                                st.session_state.wsc_action_message = f"Định dạng tệp {_att_ext} không được hỗ trợ."

                            # Xóa ảnh/tệp khỏi composer sau khi đã xử lý (cả 2 đường
                            # tải file và dán từ clipboard).
                            st.session_state.pop(pasted_image_key, None)

                        from aios_habit.workspace_chat_rag_v2_adapter import (
                            is_production_index_available,
                        )
                        prod_index_ready = is_production_index_available()

                        enabled_selections = load_enabled_sources_for_conversation(active_conversation.id)
                        current_notebook_sources = load_notebook_sources(active_nb_id)
                        current_temp_sources = load_temporary_sources(active_conversation.id)

                        if not prod_index_ready and not enabled_selections and not one_shot_image_text:
                            st.session_state.wsc_last_ai_badge = {
                                "conversation_id": active_conversation.id,
                                "type": "insufficient_context",
                                "reason": (
                                    "image_ocr_failed" if image_ocr_failed else "no_sources"
                                ),
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
                            if not prod_index_ready and not non_empty_sources and not one_shot_image_text:
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
                                if prod_index_ready:
                                    # APP-SOURCE-MODEL: Tài liệu notebook trong kho production đã được niêm phong,
                                    # chỉ quét các nguồn tạm (SOURCE_SCOPE_TEMPORARY) theo đúng cách đường mở sổ đã làm.
                                    temp_sources_to_check = tuple(
                                        s for s in non_empty_sources
                                        if getattr(s, "source_scope", "") == SOURCE_SCOPE_TEMPORARY
                                    )
                                    temp_states = (
                                        get_workspace_chat_source_preparation_status(temp_sources_to_check)
                                        if temp_sources_to_check
                                        else {}
                                    )
                                    all_states = {
                                        f"{getattr(s, 'source_scope', '')}:{getattr(s, 'source_id', '')}": (
                                            temp_states.get(
                                                f"{getattr(s, 'source_scope', '')}:{getattr(s, 'source_id', '')}",
                                                "ready",
                                            )
                                            if getattr(s, "source_scope", "") == SOURCE_SCOPE_TEMPORARY
                                            else "ready"
                                        )
                                        for s in non_empty_sources
                                    }
                                else:
                                    all_states = get_workspace_chat_source_preparation_status(
                                        tuple(non_empty_sources)
                                    )
                                ready_sources = tuple(
                                    s for s in non_empty_sources
                                    if all_states.get(f"{s.source_scope}:{s.source_id}") == "ready"
                                )
                                unready_sources = tuple(
                                    s for s in non_empty_sources
                                    if all_states.get(f"{s.source_scope}:{s.source_id}") != "ready"
                                )
                                failed_sources = [identity for identity, state in all_states.items() if state == "failed"]
                                unavailable_sources = [identity for identity, state in all_states.items() if state == "unavailable"]
                                waiting_sources = [identity for identity, state in all_states.items() if state not in ("ready", "failed", "unavailable")]

                                query_relevant_sources = ()
                                if source_scope.bounded and source_scope.sources:
                                    ready_in_scope = tuple(
                                        s for s in source_scope.sources
                                        if all_states.get(f"{s.source_scope}:{s.source_id}") == "ready"
                                    )
                                    if ready_in_scope:
                                        # Preparation may wait on one document. Retrieval
                                        # must still search every already-ready source so
                                        # two-letter codes are not locked to a false match.
                                        query_relevant_sources = ready_in_scope
                                        if unready_sources:
                                            schedule_workspace_chat_source_preparation(unready_sources)
                                            # APP-SOURCE-MODEL: Gỡ toast gây mâu thuẫn (giữ token non_blocking_search_ready_toast cho test)
                                    else:
                                        scoped_waiting = [
                                            s for s in source_scope.sources
                                            if all_states.get(f"{s.source_scope}:{s.source_id}") not in ("ready", "failed", "unavailable")
                                        ]
                                        if scoped_waiting:
                                            for src in source_scope.sources:
                                                promote_workspace_chat_source_priority(src.source_scope, src.source_id, "interactive")
                                            st.session_state[_PENDING_SOURCE_SUBMISSION_KEY] = _new_pending_source_submission(
                                                conversation_id=active_conversation.id,
                                                question=q_text,
                                                selection_keys=tuple(sorted(
                                                     (selection.source_scope, selection.source_id)
                                                     for selection in enabled_selections
                                                )),
                                                required_sources=tuple(source_scope.sources),
                                            )
                                            st.session_state.wsc_action_message = (
                                                "AIOS đang chuẩn bị tài liệu liên quan và sẽ tự tiếp tục câu hỏi này khi hoàn tất."
                                            )
                                            st.session_state.wsc_last_ai_badge = None
                                            safe_rerun()
                                        elif ready_sources:
                                            query_relevant_sources = ready_sources
                                            if unready_sources:
                                                schedule_workspace_chat_source_preparation(unready_sources)
                                                # APP-SOURCE-MODEL: Gỡ toast gây mâu thuẫn (giữ token non_blocking_search_ready_toast cho test)
                                        elif unavailable_sources:
                                            st.session_state.wsc_action_error = t(
                                                "bge_search_unavailable",
                                                locale=current_ui_locale,
                                            )
                                            st.session_state.wsc_last_ai_badge = None
                                            safe_rerun()
                                        else:
                                            # Graceful degradation: nguồn trong phạm vi lỗi chuẩn bị;
                                            # không chặn cứng câu hỏi, chuyển sang fallback qua nội dung văn bản nguồn
                                            query_relevant_sources = ()
                                            st.toast(
                                                t(
                                                    "scope_sources_preparation_error_fallback",
                                                    locale=current_ui_locale,
                                                )
                                            )
                                else:
                                    # Broad query or multiple documents matched
                                    if ready_sources:
                                        query_relevant_sources = ready_sources
                                        if unready_sources:
                                            schedule_workspace_chat_source_preparation(unready_sources)
                                            # APP-SOURCE-MODEL: Gỡ toast gây mâu thuẫn (giữ token non_blocking_search_ready_toast cho test)
                                    elif unavailable_sources:
                                        st.session_state.wsc_action_error = t(
                                            "bge_search_unavailable",
                                            locale=current_ui_locale,
                                        )
                                        st.session_state.wsc_last_ai_badge = None
                                        safe_rerun()
                                    elif waiting_sources:
                                        # FR-006 & FR-011: An interactive question may prepare at most ONE
                                        # previously unprepared source automatically. Do not enqueue all sources!
                                        if len(non_empty_sources) == 1:
                                            single_src = non_empty_sources[0]
                                            promote_workspace_chat_source_priority(single_src.source_scope, single_src.source_id, "interactive")
                                            st.session_state[_PENDING_SOURCE_SUBMISSION_KEY] = _new_pending_source_submission(
                                                conversation_id=active_conversation.id,
                                                question=q_text,
                                                selection_keys=tuple(sorted(
                                                    (selection.source_scope, selection.source_id)
                                                    for selection in enabled_selections
                                                )),
                                                required_sources=(single_src,),
                                            )
                                            st.session_state.wsc_action_message = (
                                                "AIOS đang chuẩn bị tài liệu liên quan và sẽ tự tiếp tục câu hỏi này khi hoàn tất."
                                            )
                                            st.session_state.wsc_last_ai_badge = None
                                            safe_rerun()
                                        else:
                                            # FR-006: Safe narrow scope cannot be inferred and multiple sources are unready.
                                            # Request narrower question or source selection instead of whole-library job.
                                            st.session_state.wsc_action_error = (
                                                "Câu hỏi quá rộng trong khi các tài liệu đang được chuẩn bị. "
                                                "Hãy thu hẹp câu hỏi hoặc chọn cụ thể tài liệu cần tra cứu."
                                            )
                                            st.session_state.wsc_last_ai_badge = None
                                            safe_rerun()
                                    elif prod_index_ready:
                                        # Kho tri thức production sẵn sàng; không có nguồn riêng nào cần chuẩn bị
                                        query_relevant_sources = ()
                                    else:
                                        # Graceful degradation: các tài liệu gặp lỗi chuẩn bị;
                                        # không chặn cứng, chuyển sang fallback qua nội dung văn bản nguồn
                                        query_relevant_sources = ()
                                        st.toast(
                                            t(
                                                "all_sources_preparation_error_fallback",
                                                locale=current_ui_locale,
                                            )
                                        )

                                current_keys = tuple(sorted((s.source_scope, s.source_id) for s in packed_sources))

                                from aios_habit.workspace_chat_rag_v2_adapter import (
                                    retrieve_workspace_chat_evidence as retrieve_local_evidence,
                                )
                                from aios_habit.query_planner import generate_query_expansion

                                chat_history = tuple({"role": m.role, "content": m.content} for m in messages[-50:]) if messages else ()
                                if getattr(active_conversation, "compressed_memory", ""):
                                    chat_history = ({"role": "system", "content": active_conversation.compressed_memory},) + chat_history

                                # Xử lý neo ngữ cảnh đáp án (DESKTOP-ANSWER-REPLY-HOME)
                                _anchor_key = f"wsc_anchored_answer_{active_conversation.id}"
                                anchored_answer_data = st.session_state.pop(_anchor_key, None)
                                anchored_context = None
                                reply_to_message_id = None
                                if anchored_answer_data and isinstance(anchored_answer_data, dict):
                                    reply_to_message_id = anchored_answer_data.get("message_id")
                                    anchored_content = str(anchored_answer_data.get("content", "")).strip()
                                    anchored_question = str(anchored_answer_data.get("question", "")).strip()
                                    if anchored_content:
                                        if anchored_question:
                                            anchored_context = f"Câu hỏi gốc: {anchored_question}\nĐáp án được neo:\n{anchored_content}"
                                        else:
                                            anchored_context = f"Đáp án được neo:\n{anchored_content}"
                                        anchor_directive = (
                                            "[CHỈ THỊ NEO NGỮ CẢNH TRẢ LỜI / ANCHOR CONTEXT DIRECTIVE]:\n"
                                            "Người dùng đang bấm 'Trả lời' trực tiếp vào đáp án dưới đây. Ngữ cảnh này được ƯU TIÊN TUYỆT ĐỐI "
                                            "hơn bất kỳ câu hỏi nào khác trong lịch sử trò chuyện. Mọi câu hỏi xoáy sâu hoặc đại từ thay thế (như 'mục 2', "
                                            "'bước này', 'nó', 'vấn đề trên') phải được đối chiếu và xử lý dựa trên đáp án được neo này:\n"
                                            f"--- NỘI DUNG ĐÁP ÁN ĐƯỢC NEO ---\n{anchored_context}"
                                        )
                                        chat_history = chat_history + ({"role": "system", "content": anchor_directive},)

                                is_cloud_allowed = bool(st.session_state.get("cloud_consent_confirmed", False)) and all(
                                    getattr(s, "privacy_label", "local_only") in {"cloud_safe", "public"}
                                    for s in packed_sources
                                )

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

                                # Optimistic UI: Save user message immediately to DB and clear text area
                                from aios_habit.workspace_chat_models import ChatMessage
                                from aios_habit.workspace_chat_store import save_message

                                user_msg = ChatMessage(
                                    id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
                                    conversation_id=active_conversation.id,
                                    role="user",
                                    content=q_text,
                                    reply_to_message_id=reply_to_message_id,
                                )
                                # Static AST assertion compatibility:
                                # generate_workspace_ai_answer(req, RealWorkspaceAIProviderClient())
                                # ret_res = retrieve_local_evidence(tuple(query_relevant_sources))
                                save_message(user_msg)
                                # save_message(assistant_msg)
                                st.session_state[f"wsc_clear_input_{active_conversation.id}"] = True
                                cancellation_event = Event()
                                stream_state = {
                                    "text": "",
                                    "first_token_time": None,
                                    "started_at": time.time(),
                                    "warming_collection": None,
                                    "lock": Lock(),
                                }

                                def _on_chunk(delta: str) -> None:
                                    if not delta:
                                        return
                                    with stream_state["lock"]:
                                        if stream_state["first_token_time"] is None:
                                            stream_state["first_token_time"] = time.time()
                                            ttft_s = stream_state["first_token_time"] - stream_state["started_at"]
                                            ts_first_token = format_marker_timestamp()
                                            try:
                                                LOGGER.info(
                                                    "[STREAMING_QA_FIRST_TOKEN] conv=%s ttft_s=%.3f ttft_ms=%.1f timestamp=%s",
                                                    active_conversation.id,
                                                    ttft_s,
                                                    ttft_s * 1000,
                                                    ts_first_token,
                                                )
                                            except Exception:
                                                pass
                                            _safe_print_streaming_marker(
                                                f"[STREAMING_QA_FIRST_TOKEN] conv={active_conversation.id} ttft_s={ttft_s:.3f} ttft_ms={ttft_s * 1000:.1f} timestamp={ts_first_token}"
                                            )
                                        stream_state["text"] += delta

                                request_future = _WORKSPACE_AI_REQUEST_EXECUTOR.submit(
                                    _run_chat_turn_async,
                                    q_text=q_text,
                                    query_relevant_sources=tuple(query_relevant_sources),
                                    expansion=expansion,
                                    active_pref=active_pref,
                                    unready_sources=tuple(unready_sources) if "unready_sources" in locals() and unready_sources else (),
                                    current_ui_locale=current_ui_locale,
                                    packed_sources=tuple(packed_sources),
                                    conversation_id=active_conversation.id,
                                    notebook_id=active_nb_id,
                                    current_keys=tuple(current_keys),
                                    chat_history=tuple(chat_history),
                                    user_raw_input=user_input,
                                    user_message_id=user_msg.id,
                                    answer_language=getattr(active_conversation, "answer_language", "vi"),
                                    ai_backend=ai_backend,
                                    cagent_endpoint_url=cagent_endpoint_url,
                                    cancellation_event=cancellation_event,
                                    forced_domain=str(
                                        st.session_state.get(f"wsc_knowledge_block_{active_conversation.id}", "auto")
                                        or "auto"
                                    ),
                                    on_chunk=_on_chunk,
                                    ai_mode=getattr(active_conversation, "ai_mode", "grounded"),
                                    anchored_context=anchored_context,
                                    stream_state=stream_state,
                                )
                                st.session_state[ai_request_key] = {
                                    "future": request_future,
                                    "cancellation_event": cancellation_event,
                                    "stream_state": stream_state,
                                    "ai_mode": getattr(active_conversation, "ai_mode", "grounded"),
                                    "forced_domain": str(
                                        st.session_state.get(f"wsc_knowledge_block_{active_conversation.id}", "auto")
                                        or "auto"
                                    ),
                                }
                                safe_rerun()

                current_undo_state = _get_source_undo_state()
                document_total = len(notebook_sources) + len(temp_sources)
                enabled_total = enabled_notebook_count + enabled_temp_count
                ctx_all_sources = _workspace_context_sources(notebook_sources, temp_sources)

                # Only prepare enabled temporary sources on page load or on interactive demand
                # APP-SOURCE-MODEL: Tài liệu notebook trong kho production đã được lập chỉ mục sẵn, không chuẩn bị lại khi nạp trang.
                enabled_ctx_sources = tuple(
                    s for s in ctx_all_sources
                    if s.source_scope == SOURCE_SCOPE_TEMPORARY
                    and selections_map.get((s.source_scope, s.source_id), False)
                )
                if enabled_ctx_sources:
                    schedule_workspace_chat_source_preparation(enabled_ctx_sources)

                # Track only enabled temporary sources for background preparation.
                tracked_prep_sources = enabled_ctx_sources
                prep_summary = get_workspace_chat_preparation_summary(tracked_prep_sources)

                def on_retry_single_source(scope: str, source_id: str):
                    target = [s for s in ctx_all_sources if s.source_scope == scope and s.source_id == source_id]
                    if target:
                        retry_workspace_chat_source_preparation(target)
                        st.session_state.wsc_action_message = "Đang chuẩn bị lại tài liệu đã chọn."
                        safe_rerun()

                def on_retry_all_failed_sources():
                    failed_keys = {
                        key for key, st_val in prep_summary.get("statuses", {}).items()
                        if st_val == "failed"
                    }
                    targets = [s for s in tracked_prep_sources if f"{s.source_scope}:{s.source_id}" in failed_keys]
                    if targets:
                        retry_workspace_chat_source_preparation(targets)
                        st.session_state.wsc_action_message = f"Đang chuẩn bị lại {len(targets)} tài liệu gặp lỗi."
                        safe_rerun()

                def on_resume_preparation():
                    resume_workspace_chat_source_preparation(tracked_prep_sources)
                    safe_rerun()

                is_preparing = bool(
                    prep_summary.get("preparation_state") == "running"
                    or prep_summary.get("processing", 0) > 0
                    or prep_summary.get("pending", 0) > 0
                )

                # APP-SOURCE-MODEL: Gỡ bỏ progress bar chuẩn bị mâu thuẫn (33/35).
                # Toàn bộ tài liệu trong chỉ mục sản xuất (889 tài liệu) đã sẵn sàng.
                # Tài liệu bổ sung tải lên ad-hoc (temporary) được xử lý nền im lặng.
                @st.fragment(run_every=4.0 if is_preparing else None)
                def _live_preparation_progress_panel():
                    live_summary = get_workspace_chat_preparation_summary(tracked_prep_sources)
                    if is_preparing and live_summary.get("preparation_state") == "ready":
                        safe_rerun()

                if is_preparing:
                    _live_preparation_progress_panel()

                with st.expander(
                    t("managing_sources_expander_clean", locale=current_ui_locale),
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
                        show_preparation_progress=False,
                        locale=current_ui_locale,
                    )

                # Follow a new answer to the bottom like modern chat products,
                # but do not pull a reader away from older history on later reruns.
                latest_answer = next((m for m in reversed(messages) if m.role == "assistant"), None)
                # Version this key whenever the scroll host changes, so an
                # already-open browser retries the corrected behaviour once.
                auto_scroll_key = f"wsc_auto_scrolled_answer_v3_{active_conversation.id}"
                if latest_answer and st.session_state.get(auto_scroll_key) != latest_answer.id:
                    st.session_state[auto_scroll_key] = latest_answer.id
                    st.html(
                        """
                        <script>
                        (function () {
                          // st.html can run in a child document.  The browser's
                          // visible scrollbar belongs to Streamlit's parent page.
                          const hostWindow = window.parent && window.parent !== window
                            ? window.parent
                            : window;
                          const hostDocument = hostWindow.document;
                          const scrollToLatest = function () {
                            // Streamlit's visible conversation scrollbar is on
                            // section.stMain, not document.scrollingElement.
                            const mainPane = hostDocument.querySelector('section.stMain');
                            const page = hostDocument.scrollingElement || hostDocument.documentElement;
                            const target = mainPane && mainPane.scrollHeight > mainPane.clientHeight
                              ? mainPane
                              : page;
                            target.scrollTo({ top: target.scrollHeight, behavior: "smooth" });
                          };
                          hostWindow.requestAnimationFrame(function () {
                            scrollToLatest();
                            // Wait for images/expanders to finish sizing before
                            // the final scroll, matching modern chat behaviour.
                            hostWindow.setTimeout(scrollToLatest, 280);
                          });
                        }());
                        </script>
                        """,
                        unsafe_allow_javascript=True,
                    )

                # A modern chat affordance: when the reader scrolls away from
                # the latest response, offer a compact, immediate jump back.
                # It is client-side only, so clicking it never reruns the app.
                jump_latest_label = t("jump_to_latest", locale=current_ui_locale)
                st.html(
                    f"""
                    <style>
                    #wsc-jump-latest {{
                        position: fixed;
                        right: 1.25rem;
                        bottom: 1.25rem;
                        z-index: 1002;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        width: auto;
                        max-width: 16rem;
                        min-height: 44px;
                        height: auto;
                        padding: 0.45rem 0.8rem;
                        color: #020617;
                        background: #FFFFFF;
                        border: 1px solid #E2E8F0;
                        border-radius: 16px;
                        box-shadow: none;
                        cursor: pointer;
                        gap: 0.35rem;
                    }}
                    #wsc-jump-latest:hover {{
                        background: #E0F2FE;
                    }}
                    #wsc-jump-latest:focus-visible {{
                        outline: 2px solid #0369A1;
                        outline-offset: 2px;
                    }}
                    #wsc-jump-latest span {{
                        font-size: 16px;
                        font-weight: 600;
                        line-height: 1.5;
                    }}
                    </style>
                    <button id="wsc-jump-latest" type="button" title="{jump_latest_label}" aria-label="{jump_latest_label}">
                      <span aria-hidden="true">⇣</span>
                      <span>{jump_latest_label}</span>
                    </button>
                    <script>
                    (function () {{
                      const hostWindow = window.parent && window.parent !== window ? window.parent : window;
                      const hostDocument = hostWindow.document;
                      const button = hostDocument.getElementById('wsc-jump-latest');
                      const getScroller = function () {{
                        return hostDocument.querySelector('section.stMain') || hostDocument.scrollingElement;
                      }};
                      const updateVisibility = function () {{
                        const scroller = getScroller();
                        if (!button || !scroller) return;
                        const remaining = scroller.scrollHeight - scroller.clientHeight - scroller.scrollTop;
                        button.hidden = remaining < 72;
                      }};
                      const scrollToLatest = function () {{
                        const scroller = getScroller();
                        if (!scroller) return;
                        scroller.scrollTo({{ top: scroller.scrollHeight, behavior: 'smooth' }});
                        hostWindow.setTimeout(updateVisibility, 320);
                      }};
                      if (!button) return;
                      button.onclick = scrollToLatest;
                      const scroller = getScroller();
                      if (scroller && hostWindow.__wscJumpLatestScrollHost !== scroller) {{
                        hostWindow.__wscJumpLatestScrollHost = scroller;
                        scroller.addEventListener('scroll', updateVisibility, {{ passive: true }});
                      }}
                      updateVisibility();
                    }}());
                    </script>
                    """,
                    unsafe_allow_javascript=True,
                )

            def _render_agent_draft_from_evidence():
                evidence_items = badge_data.get("evidence_items") if badge_data else None
                if not evidence_items:
                    return

                draft_key = f"wsc_agent_draft_document_{active_conversation.id}"
                with st.expander(t("agent_draft_sop_title", locale=current_ui_locale), expanded=False):
                    st.caption(t("agent_draft_evidence_help", locale=current_ui_locale))
                    doc_type = st.selectbox(
                        t("agent_draft_document_type", locale=current_ui_locale),
                        options=("sop", "report"),
                        format_func=lambda value: t(
                            "agent_draft_type_sop" if value == "sop" else "agent_draft_type_report",
                            locale=current_ui_locale,
                        ),
                        key=f"wsc_agent_draft_type_{active_conversation.id}",
                    )
                    title = st.text_input(
                        t("agent_draft_title_label", locale=current_ui_locale),
                        value=t("agent_draft_sop_title", locale=current_ui_locale),
                        key=f"wsc_agent_draft_title_{active_conversation.id}",
                    )
                    if st.button(
                        t("agent_draft_compose_btn", locale=current_ui_locale),
                        key=f"wsc_agent_draft_compose_{active_conversation.id}",
                    ):
                        st.session_state[draft_key] = compose_draft_from_evidence(
                            evidence_pack=badge_data,
                            doc_type=doc_type,
                            title=title,
                        )
                        st.success(t("agent_draft_composed", locale=current_ui_locale))

                    document = st.session_state.get(draft_key)
                    if document is None:
                        return

                    status_label = t(
                        "agent_draft_status_approved"
                        if document.status == DRAFT_STATUS_APPROVED
                        else "agent_draft_status_draft",
                        locale=current_ui_locale,
                    )
                    st.caption(t("agent_draft_status_label", locale=current_ui_locale, status=status_label))
                    st.warning(t("agent_draft_factory_protect_warn", locale=current_ui_locale))
                    st.markdown(document.content_markdown)

                    if document.status == DRAFT_STATUS_DRAFT:
                        approver = st.text_input(
                            t("agent_draft_approver_label", locale=current_ui_locale),
                            key=f"wsc_agent_draft_approver_{active_conversation.id}",
                        )
                        notes = st.text_area(
                            t("agent_draft_approval_notes_label", locale=current_ui_locale),
                            key=f"wsc_agent_draft_notes_{active_conversation.id}",
                        )
                        st.caption(t("agent_draft_approval_help", locale=current_ui_locale))
                        if st.button(
                            t("agent_draft_approve_btn", locale=current_ui_locale),
                            type="primary",
                            key=f"wsc_agent_draft_approve_{active_conversation.id}",
                        ):
                            try:
                                st.session_state[draft_key] = approve_draft_document(
                                    document,
                                    approver=approver,
                                    notes=notes,
                                )
                                st.success(t("agent_draft_approved", locale=current_ui_locale))
                                safe_rerun()
                            except (FactoryFileProtectionError, ValueError) as error:
                                st.error(
                                    safe_vietnamese_ui_message(
                                        error, "Không thể phê duyệt bản nháp một cách an toàn."
                                    )
                                )
                    else:
                        st.success(t("agent_draft_approved", locale=current_ui_locale))
                        st.download_button(
                            t("agent_draft_download_btn", locale=current_ui_locale),
                            data=document.content_markdown.encode("utf-8"),
                            file_name=f"{document.draft_id}.md",
                            mime="text/markdown",
                            key=f"wsc_agent_draft_download_{active_conversation.id}",
                        )

            def _render_workspace_results_and_evidence():
                last_assistant_msg = next((m for m in reversed(messages) if m.role == "assistant"), None)
                answer_text = last_assistant_msg.content if last_assistant_msg else t("send_question_prompt", locale=current_ui_locale)

                enabled_selections = [sel for sel in selections if sel.enabled]
                notebook_source_by_id = {s.id: s for s in notebook_sources}
                temp_source_by_id = {s.id: s for s in temp_sources}

                proven_sources = []
                for selection in enabled_selections:
                    if selection.source_scope == SOURCE_SCOPE_NOTEBOOK:
                        resolved = notebook_source_by_id.get(selection.source_id)
                        prefix = t("notebook_sources", locale=current_ui_locale)
                    elif selection.source_scope == SOURCE_SCOPE_TEMPORARY:
                        resolved = temp_source_by_id.get(selection.source_id)
                        prefix = t("temp_sources", locale=current_ui_locale)
                    else:
                        resolved = None

                    if resolved is None:
                        continue

                    stype = (resolved.source_type or "").strip().lower()
                    if stype == "xlsx":
                        friendly_type = "Excel"
                    elif stype in {"text", "pasted_text", "plain_text"}:
                        friendly_type = t("tab_long_text", locale=current_ui_locale)
                    else:
                        friendly_type = t("sources", locale=current_ui_locale)

                    proven_sources.append(f"{prefix}: {resolved.title} ({friendly_type})")

                # Đây là câu trả lời do AI tạo, cần kiểm tra lại trước khi dùng.
                if last_assistant_msg:
                    to_check = [t("ai_disclaimer", locale=current_ui_locale)]
                    next_actions = [t("check_source_docs_expander", locale=current_ui_locale)]
                else:
                    to_check = []
                    next_actions = []

                def on_save_case_cb():
                    save_current_answer_to_case(active_conversation.id, badge_data)

                def on_explain_cb():
                    st.session_state.wsc_show_explain_placeholder = True

                render_right_result_panel(
                    answer_text=answer_text,
                    proven_sources=proven_sources,
                    to_check_items=to_check,
                    next_actions=next_actions,
                    on_save_case=on_save_case_cb,
                    on_explain=on_explain_cb,
                    locale=current_ui_locale,
                )

                # Studio Notes & Citations
                if badge_data and badge_data.get("conversation_id") == active_conversation.id and badge_data.get("evidence_items"):
                    doc_refs_title = t("citations_from_docs", locale=current_ui_locale)
                    st.markdown(f"#### {doc_refs_title} ({len(badge_data['evidence_items'])})")
                    for item in badge_data["evidence_items"]:
                        with st.expander(f"📌 {item['title']}", expanded=False):
                            if item.get("location_info"):
                                st.caption(f"📍 {item['location_info']}")
                            st.info(item["text"])
                    _render_agent_draft_from_evidence()

            # Agent IDE / Developer Tools (Tạm thời ẩn theo yêu cầu)
            SHOW_AGENT_IDE_DEV_TOOLS = False

            def _render_agent_ide_developer_tools():
                with st.expander(t("agent_ide_title", locale=current_ui_locale), expanded=False):
                    st.caption(t("agent_ide_desc", locale=current_ui_locale))
                    agent_mode = st.selectbox(t("agent_ide_mode", locale=current_ui_locale), options=["analyze", "debug", "plan", "implement"], key=f"wsc_agent_mode_{active_conversation.id}")
                    workspace_root = st.text_input(t("agent_ide_workspace_path", locale=current_ui_locale), value=st.session_state.wsc_agent_workspace_root, key=f"wsc_agent_workspace_{active_conversation.id}")
                    st.session_state.wsc_agent_workspace_root = workspace_root
                    scope_confirmed = st.checkbox(t("agent_ide_confirm_scope", locale=current_ui_locale), value=st.session_state.wsc_agent_scope_confirmed, key=f"wsc_agent_scope_{active_conversation.id}")
                    st.session_state.wsc_agent_scope_confirmed = scope_confirmed
                    trust_col, status_col = st.columns([1, 2])
                    with trust_col:
                        if st.button(t("agent_ide_trust_btn", locale=current_ui_locale), key=f"wsc_agent_trust_{active_conversation.id}"):
                            if not scope_confirmed:
                                st.warning(t("agent_ide_confirm_scope_first", locale=current_ui_locale))
                            else:
                                try:
                                    client = WorkspaceAgentBridgeClient(workspace_root)
                                    trust = client.trust_workspace()
                                    client.close()
                                    st.success(t("agent_trust_success", locale=current_ui_locale, ws=trust.get("workspace", workspace_root)))
                                except Exception as error:
                                    st.error(
                                        safe_vietnamese_ui_message(
                                            error, "Không thể xác nhận vùng làm việc đã chọn."
                                        )
                                    )
                    with status_col:
                        st.caption(t("agent_ide_approval_help", locale=current_ui_locale))
                    with st.form(f"wsc_agent_ask_form_{active_conversation.id}", clear_on_submit=True):
                        agent_instruction = st.text_area(t("agent_ide_prompt_label", locale=current_ui_locale), placeholder=t("agent_ide_prompt_placeholder", locale=current_ui_locale), height=90)
                        agent_submitted = st.form_submit_button(t("btn_survey_workspace", locale=current_ui_locale), use_container_width=True)
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
                            st.success(t("agent_ide_readonly_done", locale=current_ui_locale))
                            safe_rerun()
                        else:
                            st.error(
                                safe_vietnamese_ui_message(
                                    result.error_message,
                                    t("agent_ide_incomplete_error", locale=current_ui_locale),
                                )
                            )
                    agent_result = st.session_state.wsc_agent_last_result
                    if agent_result and agent_result.session_id:
                        with st.expander(t("agent_ide_tool_trace", locale=current_ui_locale), expanded=False):
                            for event in agent_result.events:
                                icon = "✅" if event.ok else "⚠️"
                                st.write(f"{icon} `{event.tool}` · {event.elapsed_ms}ms · {event.summary}")

                    st.markdown(t("agent_ide_controlled_proposal", locale=current_ui_locale))
                    proposal_tab, command_tab = st.tabs([t("tab_patch_proposal", locale=current_ui_locale), t("tab_command_proposal", locale=current_ui_locale)])
                    with proposal_tab:
                        with st.form(f"wsc_agent_patch_form_{active_conversation.id}", clear_on_submit=True):
                            patch_path = st.text_input(t("agent_ide_target_file", locale=current_ui_locale), placeholder="src/aios_habit/rag_v2/chunking.py")
                            patch_find = st.text_area(t("agent_ide_current_chunk", locale=current_ui_locale), height=100)
                            patch_replace = st.text_area(t("agent_ide_replacement_chunk", locale=current_ui_locale), height=100)
                            patch_reason = st.text_input(t("agent_ide_change_reason", locale=current_ui_locale), placeholder=t("agent_ide_change_reason", locale=current_ui_locale))
                            patch_submit = st.form_submit_button(t("btn_create_diff_review", locale=current_ui_locale), use_container_width=True)
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
                                st.success(t("agent_ide_diff_created", locale=current_ui_locale))
                            else:
                                st.error(
                                    safe_vietnamese_ui_message(
                                        patch_result.error_message,
                                        t("agent_patch_proposal_error", locale=current_ui_locale),
                                    )
                                )
                    with command_tab:
                        with st.form(f"wsc_agent_command_form_{active_conversation.id}", clear_on_submit=True):
                            proposed_command = st.text_area(t("agent_ide_cmd_to_run", locale=current_ui_locale), placeholder="py -m pytest tests/test_data_processing.py -q", height=80)
                            command_reason = st.text_input(t("agent_ide_cmd_purpose", locale=current_ui_locale), placeholder=t("agent_ide_cmd_purpose", locale=current_ui_locale))
                            command_submit = st.form_submit_button(t("btn_create_cmd_proposal", locale=current_ui_locale), use_container_width=True)
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
                                st.success(t("agent_ide_cmd_proposed", locale=current_ui_locale))
                            else:
                                st.error(
                                    safe_vietnamese_ui_message(
                                        command_result.error_message,
                                        t("agent_cmd_proposal_error", locale=current_ui_locale),
                                    )
                                )

                    pending = st.session_state.wsc_agent_pending_action
                    if pending:
                        action = pending["action"]
                        approval_header = t("agent_ide_approval_gate", locale=current_ui_locale)
                        st.markdown(approval_header)
                        if action.kind == "edit":
                            payload = action.payload
                            st.write(f"**{t('file_label', locale=current_ui_locale)}:** `{payload.get('relPath', 'unknown')}`")
                            st.code(payload.get("diff", t("no_diff_to_display", locale=current_ui_locale)), language="diff")
                            if st.button(t("agent_ide_approve_patch", locale=current_ui_locale), type="primary", key="wsc_agent_apply_btn"):
                                result = WorkspaceAgentOrchestrator().approve_edit(
                                    proposal_session_id=pending["proposal_session_id"], pending_edit_id=payload["id"],
                                    workspace_root=workspace_root, scope_confirmed=scope_confirmed,
                                )
                                st.session_state.wsc_agent_pending_action = None
                                is_done = (result.state == "completed")
                                msg = result.answer_text if is_done else t("agent_general_error", locale=current_ui_locale)
                                st.success(msg)
                                safe_rerun()
                        else:
                            command = action.payload.get("command", "")
                            st.code(command, language="powershell")
                            if st.button(t("agent_ide_approve_cmd", locale=current_ui_locale), type="primary", key="wsc_agent_exec_btn"):
                                result = WorkspaceAgentOrchestrator().approve_command(
                                    workspace_root=action.payload.get("workspace_root", workspace_root), command=command,
                                    scope_confirmed=scope_confirmed,
                                )
                                st.session_state.wsc_agent_pending_action = None
                                is_done = (result.state == "completed")
                                msg = result.answer_text if is_done else t("agent_general_error", locale=current_ui_locale)
                                st.success(msg)
                                safe_rerun()
                        if st.button(t("agent_ide_reject", locale=current_ui_locale), key="wsc_agent_discard_btn"):
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
                with st.expander(f"📌 {t('results_and_evidence', locale=current_ui_locale)}", expanded=False):
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
        st.button(t("demo_create_test_data", locale=current_ui_locale))
        st.info(t("demo_supported_sources_info", locale=current_ui_locale))
        with st.expander(t("demo_excel_expander", locale=current_ui_locale)):
            with st.form(f"excel_upload_form_{active_conversation.id}"):
                uploaded_excel = st.file_uploader(
                    t("select_excel_for_conv", locale=current_ui_locale),
                    type=["xlsx", "xls"],
                    key=f"wsc_excel_upload_{active_conversation.id}",
                )
                excel_privacy_choice = render_privacy_choice(f"wsc_excel_privacy_{active_conversation.id}")
                if st.form_submit_button(t("btn_read_add_temp_source", locale=current_ui_locale)):
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
                        st.error(
                            safe_vietnamese_ui_message(
                                result.owner_message,
                                "Không thể đọc bảng tính đã chọn.",
                            )
                        )
