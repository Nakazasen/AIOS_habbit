"""Static UI contracts for the compact Workspace Chat composer."""
from pathlib import Path


APP_PATH = Path("src/aios_habit/workspace_chat_app.py")


def _app_source() -> str:
    return APP_PATH.read_text(encoding="utf-8")


def test_gemini_reconnect_button_is_in_the_live_composer_not_legacy_header() -> None:
    source = _app_source()
    legacy_marker = "_legacy_connector_panel"
    live = source.split(legacy_marker, 1)[-1]
    live = live.split('"""', 2)[-1]
    assert 't("reconnect_gemini_web"' in live
    assert 'key=f"wsc_reconnect_gemini_{active_conversation.id}"' in live
    assert "_start_gemini_web_bridge" in live
    assert 'ai_backend == "gemini_web" and not _start_gemini_web_bridge' in live
    assert 'announce_success=True' in live


def test_composer_default_state_uses_compact_primary_controls() -> None:
    source = _app_source()

    assert 'key=f"wsc-composer-{active_conversation.id}"' in source
    assert "height=76" in source
    assert 'label_visibility="collapsed"' in source
    assert "__wscComposerShortcutBound" in source
    assert 'event.key === "Enter"' in source


def test_composer_attachment_is_progressively_disclosed_with_existing_constraints() -> None:
    source = _app_source()

    assert 'with st.popover(t("attach_popover"' in source
    assert 'key=f"wsc-attachment-{active_conversation.id}"' in source
    assert "justify-content: center !important" in source
    assert "button > svg:last-child" in source
    assert 'type=["png", "jpg", "jpeg", "webp", "bmp"]' in source
    assert "wsc_chat_img_{active_conversation.id}_{st.session_state.wsc_upload_version}" in source
    assert "attach_screenshot_help" in source
    assert "paste_image_button" in source
    assert "clipboard-image.png" in source
    assert "wsc_remove_image_" in source


def test_screenshot_source_tab_is_merged_into_the_general_document_upload_flow() -> None:
    source = _app_source()

    assert "tab_image" not in source
    assert '"tab_upload_file": "Thêm tài liệu / ảnh"' in Path("src/aios_habit/i18n.py").read_text(encoding="utf-8")


def test_add_sources_explains_what_is_added_and_its_scope() -> None:
    source = _app_source()
    translations = Path("src/aios_habit/i18n.py").read_text(encoding="utf-8")

    assert 't("add_sources_explainer", locale=current_ui_locale)' in source
    assert '"add_sources_expander": "Thêm tài liệu/ảnh để AI tham khảo"' in translations
    assert '"add_sources_explainer"' in translations


def test_composer_keeps_explicit_submit_and_keyboard_hint() -> None:
    source = _app_source()

    assert "ask_submitted = st.button" in source
    assert "Ctrl+↵" in source
    assert "st.chat_input" not in source


def test_composer_uses_an_icon_action_and_a_real_stop_for_pending_work() -> None:
    source = _app_source()

    assert 'key=f"wsc-action-{active_conversation.id}"' in source
    assert 'key=f"wsc-shortcut-hint-{active_conversation.id}"' in source
    assert 'icon=":material/arrow_upward:"' in source
    assert 'icon=":material/stop:"' in source
    assert "wsc_stop_ai_request_" in source
    assert "question_held_preparing_sources" in source
    assert "toolbar_hint_col, toolbar_action_col" in source
    assert "with toolbar_action_col:" in source
    assert "_WORKSPACE_AI_REQUEST_EXECUTOR.submit" in source
    assert "cancellation_event=cancellation_event" in source


def test_composer_model_picker_maps_to_existing_ai_backends() -> None:
    source = _app_source()

    assert '"gemini_web", "cagent_api", "nakazasen_router"' in source
    assert "ai_connector_gemini" in source
    assert "ai_connector_cagent" in source
    assert "ai_connector_router" in source
    assert "cagent_endpoint_url" in source
    assert 'key=backend_key' in source
    assert 'with st.popover(f"◉' not in source


def test_composer_toolbar_labels_stay_on_one_line() -> None:
    """The attach and send labels must not break into one character per line."""
    source = _app_source()
    attach = source.split(
        '[class*="st-key-wsc-attachment-"] [data-testid="stPopover"] button p',
        1,
    )[1][:240]
    ask = source.split(
        '[class*="st-key-wsc-action-"] [data-testid="stButton"] button p',
        1,
    )[1][:240]

    assert "nowrap" in attach
    assert "anywhere" not in attach
    assert "nowrap" in ask
    assert "st.columns([2.2, 3.4, 2.2, 2.0, 1.2, 1.6]" in source


def test_composer_has_narrow_viewport_guard() -> None:
    source = _app_source()

    assert "@media (max-width: 360px)" in source
    assert "st-key-wsc-composer-" in source
    assert "padding: 0.7rem 0.85rem" in source
    assert "gap: 4px !important" in source
    assert "height: 72px !important" in source
    assert "height: 62px !important" in source


def test_new_assistant_answer_auto_scrolls_without_a_manual_jump_button() -> None:
    source = _app_source()

    assert "latest-ai-anchor" not in source
    assert "wsc_auto_scrolled_answer_v3_" in source
    assert "window.parent && window.parent !== window" in source
    assert "section.stMain" in source
    assert "target.scrollTo({ top: target.scrollHeight, behavior: \"smooth\" })" in source


def test_reader_can_jump_to_the_latest_answer_from_a_fixed_bottom_control() -> None:
    source = _app_source()

    assert 'id="wsc-jump-latest"' in source
    assert "jump_latest_label = t(\"jump_to_latest\"" in source
    assert "bottom: 1.25rem" in source
    assert "button.onclick = scrollToLatest" in source
    assert "scroller.scrollTo({{ top: scroller.scrollHeight, behavior: 'smooth' }})" in source
    assert '<span aria-hidden="true">⇣</span>' in source


def test_layout_switch_is_a_persistent_right_rail_control() -> None:
    source = _app_source()

    assert 'key="wsc-layout-rail-toggle"' in source
    assert 'layout_icon = ":material/chevron_left:"' in source
    assert '"st-key-wsc-layout-rail-toggle"' in source
    assert "position: fixed !important" in source
    assert "right: 0 !important" in source
    assert 'key="wsc_toggle_layout_btn"' not in source


def test_global_theme_css_is_injected_with_st_html() -> None:
    """Streamlit 1.60 shows markdown <style> as body text; style-only st.html does not."""
    source = _app_source()
    marker = ".stDeployButton {display:none;}"
    deploy = source.find(marker)
    assert deploy != -1
    prefix = source[:deploy]
    assert prefix.rfind("st.html(") > prefix.rfind("st.markdown(")
    closing = source.find("</style>", deploy)
    assert closing != -1
    assert "unsafe_allow_html" not in source[prefix.rfind("st.html(") : closing]


def test_evidence_graph_toggle_caches_trace_and_hides_the_canvas_before_rerun() -> None:
    source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")

    assert "wsc_evidence_trace_" in source
    assert "wscInstantGraphClose" in source
    assert "button.addEventListener('pointerdown'" in source
    assert "slot.style.display = 'none'" in source


def test_composer_text_input_clearing_uses_deferred_reset() -> None:
    source = _app_source()

    # Deferred clear flag check must precede text_area instantiation
    assert 'clear_input_key = f"wsc_clear_input_{active_conversation.id}"' in source
    assert 'st.session_state.pop(clear_input_key, False)' in source
    assert 'st.session_state[f"wsc_clear_input_{active_conversation.id}"] = True' in source

    # Check that after save_message(user_msg), we use the clear flag, not direct widget mutation
    post_save = source.split("save_message(user_msg)", 1)[1]
    pre_executor = post_save.split("_WORKSPACE_AI_REQUEST_EXECUTOR.submit", 1)[0]
    assert 'st.session_state[f"wsc_clear_input_{active_conversation.id}"] = True' in pre_executor
    assert 'st.session_state[f"wsc_question_input_{active_conversation.id}"]' not in pre_executor


def test_composer_nontech_has_visible_vietnamese_label() -> None:
    """FR-014: question input must carry a visible Vietnamese label, not a collapsed one."""
    source = _app_source()
    translations = Path("src/aios_habit/i18n.py").read_text(encoding="utf-8")

    assert 't("composer_question_label"' in source
    assert '"composer_question_label"' in translations
    text_area_at = source.find("user_input = st.text_area(")
    assert text_area_at != -1
    text_area_call = source[text_area_at : text_area_at + 600]
    assert 't("composer_question_label"' in text_area_call
    assert 'label_visibility="visible"' in text_area_call


def test_composer_action_targets_meet_44px_touch_rule() -> None:
    """FR-015: send/stop buttons must meet the 44px minimum with 8px spacing."""
    source = _app_source()

    assert "min-height: 44px !important" in source
    assert "min-width: 44px !important" in source
    assert "gap: 8px !important" in source


def test_composer_empty_guidance_is_shown_next_to_send_action() -> None:
    """FR-015: empty-submit guidance must render adjacent to the send action."""
    source = _app_source()

    assert "wsc_composer_hint_" in source
    assert 't("composer_empty_hint"' in source


def test_qa_bubbles_distinguish_question_and_answer() -> None:
    """FR-021: question and answer bubbles must differ visually."""
    source = _app_source()

    assert "Bong bóng hỏi đáp" in source
    assert '[data-testid="stChatMessageAvatarUser"]' in source
    assert '[data-testid="stChatMessageAvatarAssistant"]' in source


def test_answer_text_has_readable_measure_without_truncation() -> None:
    """FR-022: answer text measure is capped for readability, never cut."""
    source = _app_source()

    assert "max-width: 75ch" in source


def test_cho_hien_ba_buoc_theo_trang_thai_that() -> None:
    """FR-023: waiting steps must follow the real pipeline state."""
    from aios_habit.workspace_chat_ui import build_answer_wait_steps

    cho_nguon = build_answer_wait_steps("cho_tai_lieu")
    assert [s["dang_chay"] for s in cho_nguon] == [True, False, False]
    dang_xu_ly = build_answer_wait_steps("dang_xu_ly")
    assert [s["dang_chay"] for s in dang_xu_ly] == [False, False, True]


def test_khoi_cho_dung_trang_thai_that_trong_app() -> None:
    """FR-023: app must render wait steps from the real waiting state."""
    source = _app_source()

    assert "render_answer_wait_steps" in source
    assert '"cho_tai_lieu"' in source
    assert '"dang_xu_ly"' in source


def test_khung_sang_khong_tai_font_mang() -> None:
    """FR-025, FR-028, SC-019: one light surface, offline font, no remote font URL."""
    source = _app_source()
    theme = Path(".streamlit/config.toml").read_text(encoding="utf-8")

    assert 'page_title="Hỏi tài liệu"' in source
    assert "fonts.googleapis.com" not in theme
    assert "fonts.googleapis.com" not in source
    assert 'primaryColor = "#0369A1"' in theme
    assert 'backgroundColor = "#F8FAFC"' in theme
    assert 'textColor = "#020617"' in theme
    assert 'redColor = "#DC2626"' in theme
    assert 'greenColor = "#1A7F37"' in theme
    assert "[theme.dark]" not in theme
    assert "font-size: 16px" in source
    assert "prefers-reduced-motion: reduce" in source
    assert "button:focus-visible" in source
    assert "#DC2626" in source
    assert "background: rgba(15, 23, 42" not in source


def test_dieu_huong_chinh_co_ten_tieng_viet_nhin_thay() -> None:
    """FR-027, SC-015: primary navigation is not identified by emoji alone."""
    source = _app_source()
    translations = Path("src/aios_habit/i18n.py").read_text(encoding="utf-8")

    assert '"chat": "Hỏi tài liệu"' in source
    assert '"cases": "Hồ sơ và tri thức"' in source
    assert '"advanced": "Công cụ nâng cao"' in source
    assert "📖 Hỏi tài liệu" not in source.split("_legacy_connector_panel", 1)[-1]
    assert '"sidebar_navigation_heading": "### Điều hướng"' in translations
    assert 't("no_conversations_in_notebook"' in source
    assert 't("workspace_select_prompt"' in source
    assert "with st.container(border=True):" in source


def test_cum_trich_dan_thu_gon_mac_dinh_dong() -> None:
    """FR-024: evidence detail frames must default to collapsed."""
    source = _app_source()

    assert 'with st.expander(f"📌 {item[\'title\']}", expanded=False)' in source



def test_local_fallback_label_is_honest_and_vietnamese() -> None:
    """FR-030 / SC-013: the local answer lane never claims a model produced it."""
    import sys

    sys.path.insert(0, "src")
    from aios_habit.antigravity_bridge import LOCAL_GROUNDED_FALLBACK_PROVIDER
    from aios_habit.i18n import TRANSLATIONS, SUPPORTED_LOCALES

    source = _app_source()
    keys = (
        "local_fallback_offer_button",
        "local_fallback_note",
        "local_fallback_empty_error",
        "local_fallback_saved",
    )

    # Every visible string exists in every shipped locale.
    for locale in SUPPORTED_LOCALES:
        table = TRANSLATIONS.get(locale, {})
        for key in keys:
            assert key in table, f"{key} missing for {locale}"
            assert str(table[key]).strip(), f"{key} empty for {locale}"

    # The app wires the offer branch and the commit helper.
    assert 'badge_data.get("type") == "local_fallback_offered"' in source
    assert "commit_local_grounded_answer(" in source
    assert 't("local_fallback_offer_button"' in source
    assert 't("local_fallback_note"' in source

    # Being local, it must say so plainly and never borrow a model name.
    assert "chưa qua mô hình" in LOCAL_GROUNDED_FALLBACK_PROVIDER
    folded = LOCAL_GROUNDED_FALLBACK_PROVIDER.casefold()
    for forbidden in ("antigravity", "gemini", "gpt", "claude", "sonnet", "api"):
        assert forbidden not in folded, forbidden


def test_local_fallback_answer_never_wears_the_ai_header() -> None:
    """Audit #2 / FR-030: a committed local answer must not read as an AI answer."""
    source = _app_source()

    # The app must branch on the honest operational mode before the AI header.
    local_branch = 'badge_data.get("operational_mode") == "local_grounded_fallback"'
    assert local_branch in source
    local_at = source.index(local_branch)
    ai_header_at = source.index("render_ai_answer_header(", local_at)
    assert local_at < ai_header_at, "the local branch must precede the AI header"
    between = source[local_at:ai_header_at]
    assert "t('local_fallback_note'" in between
    assert 'render_grouped_evidence_items(' in between
    # No model attribution or AI disclaimer may appear in the local branch.
    assert "model_tool_name" not in between
    assert "ai_disclaimer" not in between


def test_local_fallback_offer_is_not_written_as_a_chat_message() -> None:
    """Audit #1 / FR-026: the offer stays an offer, never an assistant turn."""
    source = _app_source()

    marker = 'is_local_offer = bool('
    assert marker in source
    guard_at = source.index(marker)
    save_at = source.index("save_message(ChatMessage(", guard_at)
    assert guard_at < save_at, "the offer guard must precede the error save"
    guard_block = source[guard_at:save_at]
    assert 'badge.get("type") == "local_fallback_offered"' in guard_block
    assert "if not is_local_offer:" in guard_block
