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
    # UX-CHAT-CORE: khong con selectbox doi lane tay — lane tu chon va hien
    # "Dang dung: ... (tu dong)". Test khang dinh hanh vi MOI thay vi tim
    # selectbox cu.
    source = _app_source()

    assert "key=backend_key" not in source
    assert '"gemini_web", "cagent_api", "nakazasen_router"' not in source
    assert "auto_backend_for_conversation" in source
    assert '"Đang dùng: "' in source or '"Đang dùng:"' in source
    assert "(tự động)" in source


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
    # ROUND5-UX-COMPOSER: dim meta line under the input (lane status | block
    # switch | search level) and a bottom row that only carries [+] and Hỏi.
    assert "st.columns([4.2, 2.8, 3.2]" in source
    assert "st.columns([2.0, 6.9, 2.1]" in source


def test_composer_toolbar_row_keeps_only_attach_and_send_buttons() -> None:
    """ROUND5-UX-COMPOSER: the lane caption and search dropdown must not sit in
    the same row as the attach/send buttons again (that caused text overlap)."""
    source = _app_source()
    toolbar = source.split(
        "toolbar_attach_col, toolbar_hint_col, toolbar_action_col = st.columns(",
        1,
    )[1]
    toolbar = toolbar.split("st.html(", 1)[0]

    assert 'with st.container(key=f"wsc-attachment-' in toolbar
    assert 'with st.container(key=f"wsc-action-' in toolbar
    assert '"Đang dùng: "' not in toolbar
    assert "st.selectbox" not in toolbar


def test_composer_knowledge_block_switch_defaults_to_auto_with_four_choices() -> None:
    """ROUND5-UX-COMPOSER: one dim line under the input; auto by default; four
    choices; no new toolbar or tab strip."""
    source = _app_source()
    translations = Path("src/aios_habit/i18n.py").read_text(encoding="utf-8")

    assert 'with st.container(key=f"wsc-block-{active_conversation.id}"):' in source
    assert 'st.session_state.get(knowledge_block_key, "auto")' in source
    assert 'for _block_value in ("auto", *_DOMAINS):' in source
    assert 'st.session_state[knowledge_block_key] = _block_value' in source
    assert "forced_domain=str(" in source
    assert "st.tabs" not in source.split('key=f"wsc-block-', 1)[1][:1200]
    for key in (
        "knowledge_block_label",
        "knowledge_block_auto",
        "knowledge_block_lsu",
        "knowledge_block_dieu_tra_loi",
        "knowledge_block_mom",
        "knowledge_block_help",
        "knowledge_block_missing_error",
    ):
        assert f'"{key}"' in translations


def test_sidebar_shared_library_line_is_collapsed_and_lists_three_blocks() -> None:
    """ROUND5-UX-COMPOSER: one collapsed line 'Thư viện chung · 3 khối · luôn bật'."""
    source = _app_source()
    translations = Path("src/aios_habit/i18n.py").read_text(encoding="utf-8")

    assert '"shared_blocks_expander": "Thư viện chung · 3 khối · luôn bật"' in translations
    assert 't("shared_blocks_expander", locale=current_ui_locale), expanded=False' in source
    assert "workspace_chat_domain_block_status()" in source


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
    """FR-027, SC-015: primary navigation is not identified by emoji alone.

    UX-CHAT-CORE: radio "Dieu huong" 3 nhanh da bi bo — sidebar gio huong dan
    nguoi dung go tieng Viet vao o chat. Test khang dinh huong dan MOI co ten
    tieng Viet nhin thay, thay vi tim nhan radio cu.
    """
    source = _app_source()

    assert "st.radio(" not in source
    assert '"chat": "Hỏi tài liệu"' not in source
    assert '"cases": "Hồ sơ và tri thức"' not in source
    assert '"advanced": "Công cụ nâng cao"' not in source
    assert "### 💬 Trợ lý AIOS" in source
    assert "Bạn chỉ cần gõ vào ô chat" in source
    assert "hỏi tài liệu" in source
    assert "cảnh báo ngưỡng" in source
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


def test_one_shot_attach_label_distinguishes_from_persistent_sources() -> None:
    """Attach-in-composer is one-shot; its label must say so and point to the sidebar."""
    source = _app_source()
    translations = Path("src/aios_habit/i18n.py").read_text(encoding="utf-8")

    assert 'with st.popover(t("attach_popover"' in source
    assert '"attach_popover": "🖼️ Ảnh cho câu hỏi này"' in translations
    # Help text states the one-shot lifetime and redirects persistent needs.
    assert "gửi xong là hết" in translations
    assert "Nguồn tham khảo" in translations


def test_confusing_add_sources_expander_removed_from_composer() -> None:
    """The old 'Thêm tài liệu/ảnh để AI tham khảo' expander must not sit under the composer."""
    source = _app_source()

    assert 't("add_sources_expander"' not in source


def test_add_source_form_lives_in_sidebar_next_to_source_list() -> None:
    """Persistent-source adding + toggling live in the sidebar (NotebookLM pattern)."""
    source = _app_source()
    translations = Path("src/aios_habit/i18n.py").read_text(encoding="utf-8")

    assert "\"add_source_button\": \"＋ Thêm nguồn\"" in translations
    assert 't(\'add_source_button\'' in source
    # Full source list with per-source toggles is rendered (was summary-only before).
    assert "render_source_library(" in source
    assert "render_source_library_summary(" not in source
    # Sidebar panel wires the real management callbacks.
    assert "on_promote_temporary=on_promote_temporary" in source
    assert "on_delete_source=on_delete_source" in source
    assert "on_retry_preparation=on_retry_preparation" in source


def test_source_library_renamed_to_nguon_tham_khao() -> None:
    translations = Path("src/aios_habit/i18n.py").read_text(encoding="utf-8")

    assert '"source_library": "Nguồn tham khảo"' in translations


def test_attached_image_is_ocr_first_never_hard_blocked_before_ingest() -> None:
    """Regression (UX-ATTACH-SOURCES cho-muse 04/10): an attached image must be
    OCR'd into a text source first; the ask flow must not hard-block merely
    because an image is attached on an image-blocking lane."""
    source = _app_source()

    # The premature gate is gone: no "attached image + blocking backend => error".
    assert "if user_attached_image is not None and connector_blocks_image_files" not in source
    # The image still flows through ingest (OCR) in the ask path — now directly,
    # without creating a persistent temporary source.
    assert "ingest_and_extract_bytes(_img_bytes, _img_name" in source
    # Fail-closed guard for REAL image payloads stays downstream (bridge level).
    assert "image_files_blocked_message" in Path(
        "src/aios_habit/antigravity_bridge.py"
    ).read_text(encoding="utf-8")


def test_one_shot_image_is_inline_ocr_text_never_a_persistent_source() -> None:
    """Regression (UX-ATTACH-SOURCES vòng 3, 04/10): the attached image is OCR'd
    and inlined into the question text. No temporary source is created in the
    store, so a later question cannot reuse it — one-shot by construction,
    immune to session-state timing."""
    source = _app_source()

    # Direct OCR without store side effects (no process_workspace_upload_batch
    # for the one-shot composer image, no wsc_one_shot_source_ids bookkeeping).
    assert "ingest_and_extract_bytes(_img_bytes, _img_name" in source
    assert "wsc_one_shot_source_ids" not in source
    # The OCR text is merged into the question for this turn only.
    assert "one_shot_image_text" in source
    assert "Nội dung chữ đọc được từ ảnh đính kèm" in source
    # Pasted (clipboard) image is cleared from the composer after ingest too.
    assert "st.session_state.pop(pasted_image_key, None)" in source


def test_image_only_question_passes_the_no_sources_gate() -> None:
    """A question carrying only an attached image must not die at the
    'insufficient_context' gates — the image text IS the context."""
    source = _app_source()

    assert "if not enabled_selections and not one_shot_image_text:" in source
    assert "if not non_empty_sources and not one_shot_image_text:" in source


def test_add_source_expander_label_has_single_plus() -> None:
    """Regression (UX-ATTACH-SOURCES cho-muse 04/10): the sidebar expander must
    not render '＋ ＋ Thêm nguồn' (plus baked into i18n AND prepended in code)."""
    source = _app_source()

    assert "f\"＋ {t('add_source_button'" not in source


def test_attached_image_unreadable_message_exists_in_all_locales() -> None:
    """Gentle notice (not a hard error) when OCR cannot read the attached image."""
    translations = Path("src/aios_habit/i18n.py").read_text(encoding="utf-8")

    assert '"attached_image_unreadable"' in translations
    assert "Chưa đọc được nội dung ảnh" in translations
    assert "画像の内容を読み取れませんでした" in translations  # ja
    assert "无法读取图片内容" in translations  # zh


def test_image_ocr_failure_reports_actionable_reason_not_generic_no_sources() -> None:
    """Regression (UX-ATTACH-SOURCES re-verify 04/10): when OCR fails and no
    other source is enabled, the badge reason must be 'image_ocr_failed' with
    an actionable message — not the generic 'no_sources' dead end."""
    source = _app_source()

    assert '"reason": (\n                                    "image_ocr_failed" if image_ocr_failed else "no_sources"\n                                )' in source or '"image_ocr_failed" if image_ocr_failed else "no_sources"' in source
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    assert 'if reason == "image_ocr_failed":' in ui_source
    translations = Path("src/aios_habit/i18n.py").read_text(encoding="utf-8")
    assert '"image_ocr_failed_detail"' in translations
    assert "Tesseract" in translations
