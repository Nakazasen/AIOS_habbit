"""Static UI contracts for the compact Workspace Chat composer."""
from pathlib import Path


APP_PATH = Path("src/aios_habit/workspace_chat_app.py")


def _app_source() -> str:
    return APP_PATH.read_text(encoding="utf-8")


def test_composer_default_state_uses_compact_primary_controls() -> None:
    source = _app_source()

    assert 'key=f"wsc-composer-{active_conversation.id}"' in source
    assert "height=76" in source
    assert 'label_visibility="collapsed"' in source
    assert "__wscComposerShortcutBound" in source
    assert 'event.key === "Enter"' in source


def test_composer_attachment_is_progressively_disclosed_with_existing_constraints() -> None:
    source = _app_source()

    assert 'with st.popover("Đính kèm"' in source
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


def test_evidence_graph_toggle_caches_trace_and_hides_the_canvas_before_rerun() -> None:
    source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")

    assert "wsc_evidence_trace_" in source
    assert "wscInstantGraphClose" in source
    assert "button.addEventListener('pointerdown'" in source
    assert "slot.style.display = 'none'" in source
