# -*- coding: utf-8 -*-
"""Unit tests for ticket DESKTOP-HOME-SEND-ACK-UX."""

from pathlib import Path
import pytest

APP_PATH = Path("src/aios_habit/workspace_chat_app.py")


def _app_source() -> str:
    return APP_PATH.read_text(encoding="utf-8")


def test_composer_send_button_registers_on_click_callback() -> None:
    source = _app_source()
    assert "_handle_composer_send_callback" in source
    assert "on_click=_handle_composer_send_callback" in source
    assert "args=(active_conversation.id,)" in source


def test_composer_has_optimistic_message_append() -> None:
    source = _app_source()
    assert "_submitting_ack = st.session_state.get(f\"wsc_submitting_ack_{active_conversation.id}\")" in source
    assert "messages.append(ChatMessage(" in source


def test_streaming_assistant_box_renders_ack_pill() -> None:
    source = _app_source()
    assert "wsc-send-ack-pill" in source
    assert "t('question_received_ack', locale=current_ui_locale)" in source


def test_client_side_shortcut_and_duplicate_suppression_script() -> None:
    source = _app_source()
    assert "__wscComposerShortcutBound" in source
    assert 'data-wsc-sending' in source
    assert 'sendBtn.setAttribute("disabled", "true")' in source
    assert 'event.stopImmediatePropagation()' in source


def test_no_redundant_rerun_on_acknowledged_turn() -> None:
    source = _app_source()
    assert "if not _active_ack:" in source
    assert "safe_rerun()" in source
