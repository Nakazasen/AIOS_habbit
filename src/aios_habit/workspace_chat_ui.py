# -*- coding: utf-8 -*-
import streamlit as st
import time
from typing import List, Dict, Any, Callable, Optional, Tuple
from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
    ChatMessage,
    TemporaryConversationSource,
)
from aios_habit.i18n import (
    t,
    normalize_locale,
    get_supported_locales,
    LOCALE_NAMES,
    SUPPORTED_LOCALES,
    DEFAULT_LOCALE,
    TRANSLATIONS,
)
from aios_habit.workspace_chat_store import load_evidence_trace
from aios_habit.evidence_graph_viewer import render_evidence_graph_streamlit
from aios_habit.evidence_trace_schema import EvidenceTrace


def get_vietnamese_labels() -> Dict[str, str]:
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
        "enable_source_for_conv": "Bật nguồn này cho cuộc trò chuyện",
        "disable_source_for_conv": "Tắt nguồn này cho cuộc trò chuyện",
        "source_library_header": "📚 Thư viện nguồn",
        "source_library": "Thư viện nguồn",
        "confirm_delete_source": "Xác nhận xóa nguồn này?",
        "confirm_delete": "Xác nhận xóa",
        "status_enabled": "Đã bật",
        "status_disabled": "Đã tắt",
        "source_options": "Tùy chọn nguồn",
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


def get_localized_labels(locale: str = "vi") -> Dict[str, str]:
    """Return dictionary of localized UI labels for the specified locale using i18n t()."""
    norm_loc = normalize_locale(locale)
    labels = {}
    for key in TRANSLATIONS.get(norm_loc, TRANSLATIONS[DEFAULT_LOCALE]):
        labels[key] = t(key, locale=norm_loc)
    for key, val in get_vietnamese_labels().items():
        if key not in labels:
            labels[key] = val if norm_loc == "vi" else t(key, locale=norm_loc)
    return labels


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
    if owner_choice in (
        PRIVACY_CHOICE_LOCAL_ONLY,
        t("privacy_choice_local_only", "vi"),
        t("privacy_choice_local_only", "ja"),
        t("privacy_choice_local_only", "zh-CN"),
    ):
        return "local_only"
    return "cloud_safe"


def privacy_label_to_owner_choice(privacy_label: str, locale: str = "vi") -> str:
    if privacy_label_is_sendable(privacy_label):
        return t("privacy_choice_sendable", locale=locale)
    return t("privacy_choice_local_only", locale=locale)


def render_privacy_choice(key: str, privacy_label: str = "machine_only", locale: str = "vi") -> str:
    choices = [t("privacy_choice_sendable", locale=locale), t("privacy_choice_local_only", locale=locale)]
    initial_choice = privacy_label_to_owner_choice(privacy_label, locale=locale)
    idx = choices.index(initial_choice) if initial_choice in choices else 0
    return st.radio(
        t("privacy_field_label", locale=locale),
        choices,
        index=idx,
        key=key,
        help=t("privacy_help_copy", locale=locale),
    )


def render_language_selector(
    current_ui_locale: str = "vi",
    current_answer_language: str = "vi",
    on_change: Optional[Callable[[str, str], None]] = None,
    on_ui_locale_change: Optional[Callable[[str], None]] = None,
    on_answer_language_change: Optional[Callable[[str], None]] = None,
    key_prefix: str = "wsc_lang",
    locale: Optional[str] = None,
) -> Tuple[str, str]:
    """Render language selector dropdowns for interface language and AI answer language."""
    eff_locale = normalize_locale(locale or current_ui_locale)
    supported = get_supported_locales()
    loc_codes = [code for code, _ in supported]

    norm_ui = normalize_locale(current_ui_locale)
    if norm_ui not in loc_codes:
        norm_ui = "vi"
    ui_index = loc_codes.index(norm_ui)

    norm_ans = normalize_locale(current_answer_language)
    if norm_ans not in loc_codes:
        norm_ans = "vi"
    ans_index = loc_codes.index(norm_ans)

    ui_label = f"🌐 {t('language_selector', locale=eff_locale)}"
    ans_label = f"🤖 {t('answer_language_selector', locale=eff_locale)}"

    selected_ui = st.selectbox(
        ui_label,
        options=loc_codes,
        index=ui_index,
        format_func=lambda c: f"{LOCALE_NAMES.get(c, c)} ({c})",
        key=f"{key_prefix}_ui_locale",
    )

    selected_ans = st.selectbox(
        ans_label,
        options=loc_codes,
        index=ans_index,
        format_func=lambda c: f"{LOCALE_NAMES.get(c, c)} ({c})",
        key=f"{key_prefix}_answer_language",
    )

    changed = False
    if selected_ui != norm_ui:
        if on_ui_locale_change:
            on_ui_locale_change(selected_ui)
        changed = True

    if selected_ans != norm_ans:
        if on_answer_language_change:
            on_answer_language_change(selected_ans)
        changed = True

    if changed and on_change:
        on_change(selected_ui, selected_ans)

    return selected_ui, selected_ans


def render_notebook_header(locale: str = "vi"):
    st.title(f"📚 {t('notebooks_title', locale=locale)}")
    st.write(t("notebook_header_desc", locale=locale))


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
    locale: str = "vi",
):
    with st.container():
        st.markdown(f"### 📂 {nb.title}")
        st.write(nb.description or t("no_notebook_description", locale=locale))
        st.write(t("conv_count_label", locale=locale, count=conv_count))
        collection_title = ""
        try:
            from aios_habit.workspace_chat_store import load_collection
            collection = load_collection(getattr(nb, "collection_id", "") or "")
            if collection is not None:
                collection_title = collection.title
        except Exception:
            collection_title = ""
        if collection_title:
            st.caption(t("collection_card_label", locale=locale, name=collection_title))
        if st.button(f"{t('open_notebook', locale=locale)} {nb.title}", key=f"open_nb_{nb.id}"):
            on_open(nb.id)
        if on_archive_request is not None:
            if archive_pending:
                st.warning(t("archive_confirm_prompt", locale=locale))
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button(t("archive_notebook", locale=locale), key=f"confirm_archive_nb_{nb.id}"):
                        on_archive_confirm(nb.id)
                with cancel_col:
                    if st.button(t("cancel", locale=locale), key=f"cancel_archive_nb_{nb.id}"):
                        on_archive_cancel(nb.id)
            elif st.button(t("archive_notebook", locale=locale), key=f"archive_nb_{nb.id}"):
                on_archive_request(nb.id)

        # Danger zone
        st.write("---")
        st.markdown(f"**{t('danger_zone', locale=locale)}**")
        if on_delete_request is not None:
            if delete_pending:
                st.error(t("delete_notebook_warning", locale=locale))
                confirm_title = st.text_input(
                    t("delete_notebook_prompt", locale=locale),
                    placeholder=nb.title,
                    key=f"delete_confirm_title_active_{nb.id}"
                )
                ack = st.checkbox(
                    t("delete_notebook_ack", locale=locale),
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
                        t("delete_notebook_confirm", locale=locale),
                        key=f"confirm_delete_nb_{nb.id}",
                        disabled=btn_disabled
                    ):
                        effective_title = confirm_title.strip() if confirm_title.strip() else nb.title
                        on_delete_confirm(nb.id, effective_title, ack)
                with cancel_col:
                    if st.button(
                        t("cancel", locale=locale),
                        key=f"cancel_delete_nb_{nb.id}"
                    ):
                        on_delete_cancel(nb.id)
            else:
                if st.button(t("delete_notebook", locale=locale), key=f"delete_nb_active_{nb.id}"):
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
    locale: str = "vi",
):
    with st.container():
        st.markdown(f"### 📦 {nb.title}")
        st.write(nb.description or t("no_notebook_description", locale=locale))
        st.write(t("conv_count_label", locale=locale, count=conv_count))
        if st.button(t("restore_notebook", locale=locale), key=f"restore_nb_{nb.id}"):
            on_restore(nb.id)

        # Danger zone
        st.write("---")
        st.markdown(f"**{t('danger_zone', locale=locale)}**")
        if on_delete_request is not None:
            if delete_pending:
                st.error(t("delete_notebook_warning", locale=locale))
                confirm_title = st.text_input(
                    t("delete_notebook_prompt", locale=locale),
                    placeholder=nb.title,
                    key=f"delete_confirm_title_archive_{nb.id}"
                )
                ack = st.checkbox(
                    t("delete_notebook_ack", locale=locale),
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
                        t("delete_notebook_confirm", locale=locale),
                        key=f"confirm_delete_nb_archive_{nb.id}",
                        disabled=btn_disabled
                    ):
                        effective_title = confirm_title.strip() if confirm_title.strip() else nb.title
                        on_delete_confirm(nb.id, effective_title, ack)
                with cancel_col:
                    if st.button(
                        t("cancel", locale=locale),
                        key=f"cancel_delete_nb_archive_{nb.id}"
                    ):
                        on_delete_cancel(nb.id)
            else:
                if st.button(t("delete_notebook", locale=locale), key=f"delete_nb_archive_{nb.id}"):
                    on_delete_request(nb.id)
        st.write("---")


def render_chat_bubble(
    msg: ChatMessage,
    is_latest: bool = False,
    locale: str = "vi",
    trace_loader: Optional[Callable[[str], Optional[EvidenceTrace]]] = None,
):
    if msg.role == "user":
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif msg.role == "assistant":
        with st.chat_message("assistant"):
            if is_latest:
                latest_badge_text = t("latest_answer_badge", locale=locale)
                st.markdown(
                    f'<div style="display:inline-flex; align-items:center; gap:6px; background:rgba(14,165,233,0.15); border:1px solid rgba(14,165,233,0.4); color:#38bdf8; font-size:12px; font-weight:600; padding:2px 10px; border-radius:9999px; margin-bottom:10px;">✨ {latest_badge_text}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown(msg.content)

            # On-demand Evidence Graph Action (Commit C)
            if msg.trace_id and str(msg.trace_id).strip():
                trace_id_str = str(msg.trace_id).strip()
                msg_key_id = msg.id or trace_id_str
                state_key = f"wsc_show_graph_{msg_key_id}"

                # Keep this expensive canvas out of the page-wide rerun path.
                # A fragment reruns only the graph controls, so closing does
                # not rebuild the whole conversation and source library.
                trace_cache_key = f"wsc_evidence_trace_{trace_id_str}"

                def _load_trace_once() -> Optional[EvidenceTrace]:
                    session_state = getattr(st, "session_state", {})
                    cached_trace = session_state.get(trace_cache_key)
                    if cached_trace is not None:
                        return cached_trace
                    loader = trace_loader or load_evidence_trace
                    try:
                        trace = loader(trace_id_str)
                    except Exception:
                        trace = None
                    if trace is not None and hasattr(st, "session_state"):
                        st.session_state[trace_cache_key] = trace
                    return trace

                def _install_instant_graph_close_hook() -> None:
                    """Remove the rendered iframe at pointer-down, before Streamlit updates."""
                    if not hasattr(st, "html"):
                        return
                    st.html(
                        f"""
                        <script>
                        (function () {{
                          const hostWindow = window.parent && window.parent !== window ? window.parent : window;
                          const hostDocument = hostWindow.document;
                          const button = hostDocument.querySelector(
                            '[class*="st-key-btn_hide_graph_{msg_key_id}"] button'
                          );
                          if (!button || button.dataset.wscInstantGraphClose === 'true') return;
                          button.dataset.wscInstantGraphClose = 'true';
                          button.addEventListener('pointerdown', function () {{
                            const bubble = button.closest('[data-testid="stChatMessage"]');
                            if (!bubble) return;
                            bubble.querySelectorAll('iframe').forEach(function (frame) {{
                              const slot = frame.closest('[data-testid="stElementContainer"]') || frame.parentElement;
                              // React owns this element. Hide it instantly;
                              // Streamlit will remove it safely on rerun.
                              if (slot) slot.style.display = 'none';
                            }});
                          }}, {{ passive: true }});
                        }}());
                        </script>
                        """,
                        unsafe_allow_javascript=True,
                    )

                def _render_graph_control() -> None:
                    session_state = getattr(st, "session_state", {})
                    is_open = bool(session_state.get(state_key, False))
                    if not is_open:
                        if st.button(
                            t("btn_view_evidence_graph", locale=locale),
                            key=f"btn_view_graph_{msg_key_id}",
                        ):
                            if hasattr(st, "session_state"):
                                st.session_state[state_key] = True
                            # Keep the established bare-mode contract for
                            # unit tests; a real Streamlit session reruns to
                            # replace the opener with the close control.
                            if isinstance(getattr(st, "session_state", None), dict):
                                trace = _load_trace_once()
                                if trace is not None:
                                    render_evidence_graph_streamlit(trace, locale=locale)
                                else:
                                    st.warning(t("evidence_trace_not_found", locale=locale))
                            else:
                                st.rerun()
                        return

                    if st.button(
                        t("btn_hide_evidence_graph", locale=locale),
                        key=f"btn_hide_graph_{msg_key_id}",
                    ):
                        if hasattr(st, "session_state"):
                            st.session_state[state_key] = False
                        st.rerun()
                        return

                    trace = _load_trace_once()
                    if trace is not None:
                        render_evidence_graph_streamlit(trace, locale=locale)
                        _install_instant_graph_close_hook()
                    else:
                        st.warning(t("evidence_trace_not_found", locale=locale))

                _render_graph_control()
    else:
        st.info(msg.content)


def render_right_result_panel(
    answer_text: str,
    proven_sources: List[str],
    to_check_items: List[str],
    next_actions: List[str],
    on_save_case: Callable[[], None],
    on_explain: Callable[[], None],
    locale: str = "vi",
):
    st.subheader(f"💡 {t('main_answer', locale=locale)}")
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
        st.write(t("no_sources", locale=locale))

    with st.expander(f"⚙️ {t('source_options', locale=locale)}", expanded=False):
        st.subheader(f"⚠️ {t('to_check', locale=locale)}")
        if to_check_items:
            for item in to_check_items:
                st.warning(item)
        else:
            st.write(t("no_content", locale=locale))

        st.subheader(f"🚀 {t('next_actions', locale=locale)}")
        if next_actions:
            for act in next_actions:
                st.write(f"- {act}")
        else:
            st.write(t("no_content", locale=locale))

        st.write("---")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(t("save_to_case", locale=locale), use_container_width=True):
                on_save_case()
        with col2:
            if st.button(t("explain_conclusion", locale=locale), use_container_width=True):
                on_explain()


def render_source_status(status: str, locale: str = "vi") -> str:
    norm_loc = normalize_locale(locale)
    if status == "ready":
        return t("status_ready", locale=norm_loc)
    if status == "unavailable":
        return t("status_bge_unavailable", locale=norm_loc)
    if status == "preview_only":
        return t("status_preview_only", locale=norm_loc)
    if status == "failed":
        return t("status_failed", locale=norm_loc)
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


def _format_prep_status(prep_status: str, extraction_status: str = "", locale: str = "vi") -> str:
    norm_loc = normalize_locale(locale)
    if extraction_status in ("failed", "unsupported_no_local_ocr", "dependency_missing"):
        return t("status_prep_error", locale=norm_loc)
    if prep_status in ("processing", "pending", "not_prepared"):
        return t("status_processing", locale=norm_loc)
    if prep_status == "ready":
        return t("status_ready", locale=norm_loc)
    if prep_status == "unavailable":
        return t("status_bge_unavailable", locale=norm_loc)
    if prep_status == "failed":
        return t("status_failed", locale=norm_loc)
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
    locale: str = "vi",
):
    st.subheader(f"📚 {t('source_library', locale=locale)}")

    nb_count = len(notebook_sources)
    tmp_count = len(temp_sources)
    total_sources = nb_count + tmp_count
    enabled_count = sum(1 for val in selections_map.values() if val)

    st.caption(f"📁 **{t('in_notebook', locale=locale)}:** {nb_count} · ⏱️ **{t('temp_in_conversation', locale=locale)}:** {tmp_count}")
    st.write(t("enabled_sources_count", locale=locale, count=enabled_count))

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
        st.write(t("no_sources", locale=locale))
        return

    col_all, col_none = st.columns(2)
    with col_all:
        if st.button(f"🔘 {t('enable_all', locale=locale)}", key=f"wsc_select_all_{conversation_id}", use_container_width=True):
            for item in all_items:
                on_toggle_source(item["scope"], item["source"].id, True)
    with col_none:
        if st.button(f"⚪ {t('disable_all', locale=locale)}", key=f"wsc_deselect_all_{conversation_id}", use_container_width=True):
            for item in all_items:
                on_toggle_source(item["scope"], item["source"].id, False)

    prep_map = preparation_status_map or {}

    for item in all_items:
        s = item["source"]
        scope = item["scope"]
        is_enabled = item["enabled"]

        icon = get_source_icon(getattr(s, "title", ""), getattr(s, "source_type", ""))
        st.markdown(f"{icon} **{s.title}**")

        scope_str = t("in_notebook", locale=locale) if scope == "notebook" else t("temp_in_conversation", locale=locale)
        status_str = t("status_enabled", locale=locale) if is_enabled else t("status_disabled", locale=locale)

        prep_st = prep_map.get(f"{scope}:{s.id}", "ready")
        ext_st = getattr(s, "extraction_status", "") or getattr(s, "status", "")
        prep_label = _format_prep_status(prep_st, ext_st, locale=locale)

        status_line = f"{scope_str} | {status_str}"
        if prep_label:
            status_line += f" | {prep_label}"
        st.caption(status_line)

        if prep_st == "failed" and on_retry_preparation is not None:
            if st.button(t("retry_preparation", locale=locale), key=f"wsc_retry_prepare_{scope}_{conversation_id}_{s.id}"):
                on_retry_preparation(scope, s.id)

        widget_key = f"wsc_toggle_{scope}_{conversation_id}_{s.id}"
        st.checkbox(
            t("enable_this_source", locale=locale),
            value=is_enabled,
            key=widget_key,
            on_change=lambda sc=scope, sid=s.id, k=widget_key, default_val=is_enabled: on_toggle_source(sc, sid, st.session_state.get(k, default_val))
        )

        with st.expander(f"⚙️ {t('source_options', locale=locale)}", expanded=False):
            privacy_label = getattr(s, "privacy_label", "")
            if not privacy_label_is_sendable(privacy_label):
                st.warning(t("privacy_blocked_status", locale=locale))

            st.markdown(f"**{t('readable_content', locale=locale)}:**")
            if getattr(s, "content_preview", None):
                st.write(s.content_preview)
            else:
                st.write(t("no_content", locale=locale))

            st.markdown("---")
            privacy_key = f"wsc_privacy_{scope}_{conversation_id}_{s.id}"
            owner_choice = render_privacy_choice(privacy_key, privacy_label, locale=locale)
            if st.button(t("privacy_save_button", locale=locale), key=f"wsc_save_privacy_{scope}_{conversation_id}_{s.id}"):
                on_privacy_save(scope, s.id, owner_choice)

            if scope == "temporary":
                is_promoted = getattr(s, "long_term_saved", False) or getattr(s, "status", "") == "added_to_notebook"
                if is_promoted:
                    st.caption(t("add_to_notebook", locale=locale))
                else:
                    if st.button(t("add_to_notebook", locale=locale), key=f"wsc_promote_{conversation_id}_{s.id}"):
                        on_promote_temporary(s.id)

            st.markdown("---")
            confirm_key = f"wsc_delete_confirm_{scope}_{s.id}"
            if st.session_state.get(confirm_key, False):
                st.warning(t("confirm_delete_source", locale=locale))
                dcol1, dcol2 = st.columns(2)
                with dcol1:
                    if st.button(t("cancel", locale=locale), key=f"wsc_del_cancel_{scope}_{s.id}"):
                        st.session_state[confirm_key] = False
                        __safe_rerun()
                with dcol2:
                    if st.button(t("confirm_delete", locale=locale), key=f"wsc_del_exec_{scope}_{s.id}"):
                        st.session_state[confirm_key] = False
                        on_delete_source(scope, s.id)
            else:
                if st.button(t("delete_source", locale=locale), key=f"wsc_del_req_{scope}_{s.id}"):
                    st.session_state[confirm_key] = True
                    __safe_rerun()

        st.markdown("<hr style='margin: 4px 0; border: 0.5px solid rgba(255,255,255,0.08);'/>", unsafe_allow_html=True)


def render_source_library_summary(notebook_count: int, temporary_count: int, enabled_count: int, locale: str = "vi") -> None:
    """Keep the sidebar informative without hiding source-management actions in it."""
    st.subheader(f"📚 {t('source_library', locale=locale)}")
    st.caption(f"{t('in_notebook', locale=locale)}: {notebook_count} · {t('temp_in_conversation', locale=locale)}: {temporary_count}")
    st.caption(t("enabled_sources_count", locale=locale, count=enabled_count))
    st.info(f"{t('sources_in_use', locale=locale)}: {t('sources_in_use_desc', locale=locale)}")


def format_preparation_summary_text(summary: Optional[Dict[str, Any]], locale: str = "vi") -> str:
    """Format document preparation progress without exposing internal engines."""
    if not summary or summary.get("total", 0) <= 0:
        return ""
    if not summary.get("bge_available", True):
        return t("bge_unavailable", locale=locale)

    total = summary.get("total", 0)
    ready = summary.get("ready", 0)
    pending = summary.get("pending", 0)
    failed = summary.get("failed", 0)
    completed = summary.get("completed", ready)
    progress_percent = summary.get(
        "progress_percent",
        int(round((completed * 100) / total)) if total else 0,
    )
    preparation_state = summary.get("preparation_state", "")

    parts = [
        t(
            "document_preparation_progress",
            locale=locale,
            completed=completed,
            total=total,
            percent=progress_percent,
        ),
        t("bge_ready_ratio", locale=locale, ready=ready, total=total),
    ]
    if failed > 0:
        parts.append(t("document_preparation_needs_attention", locale=locale, count=failed))
    elif preparation_state == "running":
        parts.append(t("document_preparation_running", locale=locale))
    elif preparation_state == "paused":
        parts.append(t("document_preparation_paused", locale=locale))
    elif preparation_state == "ready":
        parts.append(t("document_preparation_complete", locale=locale))
    elif pending > 0:
        parts.append(t("bge_pending_count", locale=locale, count=pending))

    return " · ".join(parts)


def render_preparation_progress_bar(
    summary: Optional[Dict[str, Any]],
    on_retry_all_failed: Optional[Callable[[], None]] = None,
    on_resume: Optional[Callable[[], None]] = None,
    locale: str = "vi",
) -> None:
    """Render a truthful, actionable document-preparation progress panel."""
    if not summary or summary.get("total", 0) <= 0:
        return
    text = format_preparation_summary_text(summary, locale=locale)
    if not text:
        return
    failed = summary.get("failed", 0)
    ready = int(summary.get("ready", 0))
    failed = int(summary.get("failed", 0))
    completed = int(summary.get("completed", ready))
    total = int(summary.get("total", 0))
    default_percent = int(round((completed * 100) / total)) if total else 0
    progress_percent = max(0, min(100, int(summary.get("progress_percent", default_percent))))
    preparation_state = summary.get("preparation_state", "")
    if not preparation_state:
        if ready == total:
            preparation_state = "ready"
        elif failed > 0:
            preparation_state = "needs_attention"
        elif summary.get("processing", 0) or summary.get("pending", 0):
            preparation_state = "running"
        else:
            preparation_state = "paused"

    if summary.get("bge_available", True):
        st.progress(progress_percent, text=t("document_preparation_progress", locale=locale,
                                             completed=completed,
                                             total=total,
                                             percent=progress_percent))

    if preparation_state == "ready":
        st.success(f"📚 {text}")
    elif preparation_state in {"paused", "needs_attention"} or failed > 0:
        st.warning(f"📚 {text}")
    else:
        st.info(f"📚 {text}")

    if preparation_state == "paused" and on_resume is not None:
        if st.button(t("resume_pending_preparation", locale=locale), key="wsc_resume_pending_preparation", use_container_width=True):
            on_resume()
    if failed > 0 and preparation_state != "running" and on_retry_all_failed is not None:
        if st.button(f"🔄 {t('retry_preparation', locale=locale)}", key="wsc_retry_all_failed_sources", use_container_width=True):
            on_retry_all_failed()


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
    show_preparation_progress: bool = True,
    locale: str = "vi",
) -> None:
    """Render the owner-facing document manager in the chat column."""
    st.subheader(f"📚 {t('sources_in_use', locale=locale)}")
    st.caption(t("sources_in_use_desc", locale=locale))
    st.info(t("input_help_instruction", locale=locale))

    if preparation_summary and show_preparation_progress:
        render_preparation_progress_bar(preparation_summary, on_retry_all_failed=on_retry_all_failed, locale=locale)

    def render_undo_control() -> None:
        seconds_remaining = max(0, int(undo_expires_at - time.time()))
        if seconds_remaining <= 0 or on_undo_delete is None:
            return
        undo_col, _ = st.columns(2)
        with undo_col:
            st.warning(f"{t('undo_delete', locale=locale)}: {seconds_remaining}s")
            if st.button(f"↩️ {t('undo_delete', locale=locale)}", key=f"wsc_source_undo_{conversation_id}", use_container_width=True):
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
            st.info(t("no_sources", locale=locale))
            return

        enable_col, disable_col = st.columns(2)
        with enable_col:
            if st.button(
                f"🔘 {t('enable_all', locale=locale)} ({len(sources)})",
                key=f"wsc_document_enable_all_{scope}_{conversation_id}",
                use_container_width=True,
            ):
                for source in sources:
                    on_toggle_source(scope, source.id, True)
                    st.session_state[f"wsc_document_toggle_{scope}_{conversation_id}_{source.id}"] = True
                st.session_state.wsc_action_message = f"{t('enable_all', locale=locale)} ({len(sources)})."
                __safe_rerun()
        with disable_col:
            if st.button(
                f"⚪ {t('disable_all', locale=locale)} ({len(sources)})",
                key=f"wsc_document_disable_all_{scope}_{conversation_id}",
                use_container_width=True,
            ):
                for source in sources:
                    on_toggle_source(scope, source.id, False)
                    st.session_state[f"wsc_document_toggle_{scope}_{conversation_id}_{source.id}"] = False
                st.session_state.wsc_action_message = f"{t('disable_all', locale=locale)} ({len(sources)})."
                __safe_rerun()

        confirm_key = f"wsc_bulk_delete_confirm_{scope}_{conversation_id}"
        if st.session_state.get(confirm_key, False):
            st.warning(
                f"{t('confirm_delete_source', locale=locale)} ({len(sources)})"
            )
            cancel_col, execute_col = st.columns(2)
            with cancel_col:
                if st.button(t("cancel", locale=locale), key=f"wsc_bulk_delete_cancel_{scope}_{conversation_id}"):
                    st.session_state[confirm_key] = False
                    __safe_rerun()
            with execute_col:
                if st.button(t("confirm_delete", locale=locale), key=f"wsc_bulk_delete_execute_{scope}_{conversation_id}", type="primary"):
                    st.session_state[confirm_key] = False
                    on_delete_sources(scope, [source.id for source in sources])
        else:
            label = f"🗑️ {t('delete_source', locale=locale)} ({len(sources)})"
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
                state = t("status_enabled", locale=locale) if enabled else t("status_disabled", locale=locale)
                location = t("in_notebook", locale=locale) if scope == "notebook" else t("temp_in_conversation", locale=locale)
                st.caption(f"{location} · {state}")

                # Never expose the internal retrieval engine in owner-facing UI.
                if item_status == "ready":
                    st.caption(f"🟢 **{t('document_preparation_status_label', locale=locale)}:** {t('status_ready', locale=locale)}")
                elif item_status == "processing":
                    st.caption(f"⏳ **{t('document_preparation_status_label', locale=locale)}:** {t('status_processing', locale=locale)}")
                elif item_status == "pending":
                    st.caption(f"⏱️ **{t('document_preparation_status_label', locale=locale)}:** {t('status_pending', locale=locale)}")
                elif item_status == "failed":
                    st.caption(f"🔴 **{t('document_preparation_status_label', locale=locale)}:** {t('status_failed', locale=locale)}")
                elif item_status == "unavailable":
                    st.caption(f"⚪ **{t('document_preparation_status_label', locale=locale)}:** {t('status_bge_unavailable', locale=locale)}")

            with action_col:
                if item_status == "failed" and on_retry_source is not None:
                    if st.button(f"🔄 {t('retry_preparation', locale=locale)}", key=f"wsc_retry_src_{scope}_{conversation_id}_{source.id}", use_container_width=True):
                        on_retry_source(scope, source.id)

                individual_confirm_key = f"wsc_document_delete_confirm_{scope}_{source.id}"
                if st.session_state.get(individual_confirm_key, False):
                    if st.button(t("confirm_delete", locale=locale), key=f"wsc_document_delete_execute_{scope}_{source.id}", type="primary", use_container_width=True):
                        st.session_state[individual_confirm_key] = False
                        on_delete_source(scope, source.id)
                    if st.button(t("cancel", locale=locale), key=f"wsc_document_delete_cancel_{scope}_{source.id}", use_container_width=True):
                        st.session_state[individual_confirm_key] = False
                        __safe_rerun()
                elif st.button(f"🗑️ {t('delete_source', locale=locale)}", key=f"wsc_document_delete_request_{scope}_{source.id}", use_container_width=True):
                    st.session_state[individual_confirm_key] = True
                    __safe_rerun()

            toggle_key = f"wsc_document_toggle_{scope}_{conversation_id}_{source.id}"
            st.checkbox(
                t("use_doc_for_answer", locale=locale),
                value=enabled,
                key=toggle_key,
                on_change=lambda sc=scope, sid=source.id, key=toggle_key, default=enabled: on_toggle_source(sc, sid, st.session_state.get(key, default)),
            )
            with st.expander(t("options_expander", locale=locale), expanded=False):
                st.write(getattr(source, "content_preview", "") or t("no_content", locale=locale))
                choice = render_privacy_choice(f"wsc_document_privacy_{scope}_{conversation_id}_{source.id}", getattr(source, "privacy_label", ""), locale=locale)
                if st.button(t("privacy_save_button", locale=locale), key=f"wsc_document_privacy_save_{scope}_{conversation_id}_{source.id}"):
                    on_privacy_save(scope, source.id, choice)
                if scope == "temporary" and not getattr(source, "long_term_saved", False):
                    if st.button(t("add_to_notebook", locale=locale), key=f"wsc_document_promote_{conversation_id}_{source.id}"):
                        on_promote_temporary(source.id)
            st.divider()

    render_group(
        "temporary",
        t("temp_sources", locale=locale),
        t("only_this_conversation", locale=locale),
        temporary_sources,
    )
    render_group(
        "notebook",
        t("notebook_sources", locale=locale),
        t("in_notebook", locale=locale),
        notebook_sources,
    )


def render_ai_source_context_summary(enabled_count: int, locale: str = "vi"):
    """Compact AI source context summary shown near the question area."""
    if enabled_count > 0:
        st.info(t("enabled_sources_count", locale=locale, count=enabled_count))
    else:
        st.warning(t("no_sources", locale=locale))


def render_bridge_header_status(health: Any, locale: str = "vi"):
    """Renders truthful bridge status badge in the app header."""
    status = getattr(health, "status", "unavailable") if health else "unavailable"
    reason = getattr(health, "reason", "") if health else ""

    if status == "direct_ready":
        st.info(t("bridge_direct_ready_badge", locale=locale))
    elif status in ("handoff_ready", "completed"):
        st.info(t("bridge_handoff_ready_badge", locale=locale))
    elif status == "handoff_pending":
        st.warning(t("bridge_handoff_pending_badge", locale=locale))
    elif status == "failed":
        sanitized = reason or t("bridge_failed", locale=locale)
        badge_title = t("bridge_failed_badge", locale=locale)
        st.error(f"{badge_title}: {sanitized}")
    else:
        st.info(t("bridge_unconnected_badge", locale=locale))


def render_ai_answer_header(
    source_count: int,
    source_titles: List[str],
    ai_source: str = "",
    model_tool_name: str = "",
    operational_mode: str = "",
    provider_name: str = "",
    locale: str = "vi",
):
    """Renders truthful provenance badges separating Bridge, Provider, and Model."""
    ai_answered_text = t("ai_answered", locale=locale)
    sources_sent_text = t("sources_sent", locale=locale)
    disclaimer_text = t("ai_disclaimer", locale=locale)

    mode_label = t("sidecar_handoff", locale=locale) if operational_mode == "handoff" else t("sidecar_direct", locale=locale) if operational_mode == "direct" else operational_mode

    if ai_source and ("antigravity" in str(ai_source).lower() or str(ai_source) == "Antigravity IDE"):
        bridge_label = mode_label
        if provider_name in ("Gemini Web (Nặc danh)", "Gemini Web (Ẩn danh)", "Gemini Web (匿名)", "Gemini Web（匿名）"):
            provider_label = t("gemini_web_anonymous", locale=locale)
        elif provider_name in ("Gemini Web Stream (Nặc danh)", "Gemini Web Stream (Ẩn danh)", "Gemini Web Stream (匿名)", "Gemini Web Stream（匿名）"):
            provider_label = t("gemini_web_stream", locale=locale)
        else:
            provider_label = provider_name or t("gemini_web_stream", locale=locale)
        st.success(f"✅ **{ai_answered_text}** · 🌉 `{bridge_label}` · 🌐 `{provider_label}`")
    elif ai_source and ("smart_router" in str(ai_source).lower() or str(ai_source) == "Smart Router"):
        st.info(f"✅ **{ai_answered_text}** · 🌐 `{t('smart_router_auto', locale=locale)}`")
    else:
        st.success(f"✅ **{ai_answered_text}**")

    # Group source titles to avoid repetitive headers
    title_counts: dict[str, int] = {}
    if source_titles:
        for t_title in source_titles:
            clean_t = str(t_title).strip()
            if clean_t:
                title_counts[clean_t] = title_counts.get(clean_t, 0) + 1

    distinct_doc_count = len(title_counts) if title_counts else source_count
    if title_counts and source_count > distinct_doc_count:
        st.write(f"{sources_sent_text}: {distinct_doc_count} ({source_count})")
    else:
        st.write(f"{sources_sent_text}: {source_count}")

    # Truthful Model Identity
    clean_model = model_tool_name.strip() if model_tool_name else ""
    if clean_model and clean_model not in ("antigravity-brain-pro", "gemini-pro", "antigravity", "auto", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-flash-lite"):
        st.caption(f"`{clean_model}`")
    else:
        st.caption(f"`{t('model_unverified', locale=locale)}`")

    if title_counts:
        with st.expander(f"{sources_sent_text}", expanded=False):
            for title, count in title_counts.items():
                if count > 1:
                    st.write(f"- {title} ({count})")
                else:
                    st.write(f"- {title}")
    st.caption(disclaimer_text)


def render_grouped_evidence_items(evidence_items: List[Dict[str, Any]], conversation_id: str, locale: str = "vi") -> None:
    """Group multiple retrieved excerpts by source title/id to avoid redundant headers."""
    if not evidence_items:
        return
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in evidence_items:
        title = item.get("title", t("no_content", locale=locale))
        grouped.setdefault(title, []).append(item)

    with st.expander(f"🔍 {t('evidence_snippets_detail', locale=locale)} ({len(evidence_items)})"):
        for title, items in grouped.items():
            count_label = f"{len(items)}"
            st.markdown(f"📄 **{title}** · *{count_label}*")
            for idx, item in enumerate(items, 1):
                loc = item.get("location_info", "")
                loc_str = f" ({loc})" if loc else ""
                snippet_text = item.get("text", item.get("snippet", ""))
                st.caption(f"#{idx}{loc_str}:")
                st.text_area(
                    f"{idx}_{title}",
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
    locale: str = "vi",
):
    """Renders active pending banner when waiting for Antigravity IDE outbox/inbox processing."""
    with st.container():
        st.warning(f"⏳ **{t('bridge_handoff_pending', locale=locale)}** (`{request_id}`)")
        guidance_text = f"**{t('bridge_handoff_pending', locale=locale)}**\n\n"
        if outbox_dir:
            guidance_text += f"- **Outbox**: `{outbox_dir}`\n"
        if inbox_path:
            guidance_text += f"- **Inbox**: `{inbox_path}`\n"
        st.markdown(guidance_text)

        if privacy_mode == "local_only":
            local_privacy_text = t("privacy_choice_local_only", locale=locale)
            st.caption(f"🔒 {local_privacy_text}")

        if on_check_inbox is not None:
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"🔄 {t('source_check', locale=locale)}", key=f"wsc_check_inbox_{request_id}", use_container_width=True):
                    on_check_inbox(request_id)
            with col2:
                if on_cancel_request is not None and st.button(f"❌ {t('cancel', locale=locale)}", key=f"wsc_cancel_handoff_{request_id}", use_container_width=True):
                    on_cancel_request(request_id)


def render_insufficient_context(reason: str = "no_sources", locale: str = "vi"):
    """Renders 'Thiếu ngữ cảnh' badge with appropriate message."""
    st.error(f"⚠️ **{t('insufficient_context', locale=locale)}**")
    st.write(t("no_sources", locale=locale))


def render_privacy_block_message(locale: str = "vi"):
    """Renders friendly privacy block message."""
    st.error(t("privacy_ai_hard_block_copy", locale=locale))


def render_source_changed_message(locale: str = "vi"):
    """Renders source-set-changed warning."""
    st.warning(t("source_changed_warning", locale=locale))
