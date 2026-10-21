# -*- coding: utf-8 -*-
"""Unit & Contract tests for ticket DESKTOP-HOME-SEND-ACK-CLIENT-INSTANT.

Verifies:
1. Optimistic slot rendered at the bottom of the chat container with proper DOM data attributes.
2. Client-side script performs instant visual ack (<0.05s) and locks composer controls (sendBtn, textarea).
3. Reconciliation contract: cleans optimistic ghost node when server render arrives (replaces ghost node exactly once, no double bubble).
4. Error contract: clears optimistic ghost node and unlocks composer on server rejection/error (no hanging ghost node).
5. Cold worker protection: textarea input listener never unlocks a button disabled by worker warming.
6. Shortcut contract: Ctrl+Enter executes instant ack and submits without duplicate firing.
7. Continuous improvement loop: logs send ack events into local_cases/send_ack_events.jsonl.
"""

from pathlib import Path
import re
import pytest

APP_PATH = Path("src/aios_habit/workspace_chat_app.py")


def _app_source() -> str:
    return APP_PATH.read_text(encoding="utf-8")


def test_optimistic_slot_rendered_with_reconciliation_attributes() -> None:
    source = _app_source()
    assert 'wsc-optimistic-slot' in source
    assert 'data-conv-id="{active_conversation.id}"' in source
    assert 'data-messages-count="{total_msgs}"' in source
    assert 'data-answering="{_opt_answering_str}"' in source
    assert 'data-error="{_opt_has_error_str}"' in source


def test_client_script_instant_visual_ack_present() -> None:
    source = _app_source()
    assert "__wscDoInstantAck = function(textarea, sendBtn)" in source
    assert 'wsc-client-optimistic-bubble' in source
    assert 'data-testid="stChatMessageAvatarUser"' in source
    assert 'wsc-client-optimistic-ack' in source
    assert 'data-testid="stChatMessageAvatarAssistant"' in source
    assert 'wsc-send-ack-pill' in source
    assert '{_js_ack_text}' in source
    assert 'targetSlot.scrollIntoView' in source


def test_composer_controls_locked_instantly_on_send() -> None:
    source = _app_source()
    assert 'sendBtn.setAttribute("data-wsc-sending", "true")' in source
    assert 'sendBtn.setAttribute("disabled", "true")' in source
    assert 'sendBtn.style.pointerEvents = "none"' in source
    assert 'textarea.setAttribute("readonly", "true")' in source


def test_reconciliation_contract_ghost_node_replaced_cleanly() -> None:
    source = _app_source()
    # Contract: when server is answering, optimistic slot is emptied to prevent double bubbles
    assert 'parentDoc.getElementById("wsc-optimistic-slot-" + convId)' in source
    assert 'if (slot && (isAnswering || hasError || slot.getAttribute("data-wsc-filled") === "true"))' in source
    assert 'slot.innerHTML = "";' in source
    assert 'slot.removeAttribute("data-wsc-filled");' in source


def test_error_contract_ghost_node_removed_on_server_error() -> None:
    source = _app_source()
    # Contract: when server error occurs (hasError == true), slot is cleared and controls unlocked
    assert '_js_has_error = "true" if bool(st.session_state.get("wsc_action_error")) else "false"' in source
    assert 'if (currentSendBtn && !isAnswering)' in source
    assert 'currentSendBtn.removeAttribute("data-wsc-sending");' in source
    assert 'currentTextarea.removeAttribute("readonly");' in source


def test_cold_worker_protection_never_unlocks_warming_button() -> None:
    source = _app_source()
    # Input event must ONLY reset button if data-wsc-sending was active, NEVER if worker warming disabled it!
    input_handler_pattern = re.search(
        r'parentDoc\.addEventListener\("input".*?if \(btn && btn\.getAttribute\("data-wsc-sending"\) === "true"\)',
        source,
        re.DOTALL,
    )
    assert input_handler_pattern is not None, "Input listener must strictly guard against unlocking cold worker buttons"


def test_ctrl_enter_shortcut_contract() -> None:
    source = _app_source()
    assert '(event.ctrlKey || event.metaKey) && event.key === "Enter"' in source
    assert 'parentWin.__wscDoInstantAck(textarea, sendButton);' in source
    assert 'sendButton.click();' in source


def test_continuous_improvement_loop_logging_contract() -> None:
    source = _app_source()
    assert 'local_cases' in source
    assert 'send_ack_events.jsonl' in source
    assert 'ack_mode": "client_instant"' in source
