# -*- coding: utf-8 -*-
import time
from pathlib import Path
from threading import Lock
import pytest

from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_app import _run_chat_turn_async
from aios_habit.workspace_chat_store import load_messages


def test_named_doc_not_found_emits_all_markers_and_saves_message(monkeypatch, tmp_path):
    """Verify that when a question asks for a non-existent document:
    1. STREAMING_QA_START, STREAMING_QA_FIRST_TOKEN, STREAMING_QA_COMPLETE are all emitted.
    2. The refusal answer is saved as a ChatMessage in messages.jsonl.
    3. The return tuple matches the expected contract (ok=True, refusal answer, truthful refusal badge).
    """
    printed_markers: list[str] = []

    def mock_safe_print(msg: str) -> None:
        printed_markers.append(msg)

    monkeypatch.setattr("aios_habit.workspace_chat_app._safe_print_streaming_marker", mock_safe_print)

    # Use a isolated messages.jsonl file
    test_messages_file = tmp_path / "messages.jsonl"
    monkeypatch.setattr("aios_habit.workspace_chat_store.MESSAGES_FILE", test_messages_file)

    conv_id = f"CONV-TEST-NOT-FOUND-{int(time.time() * 1000)}"
    user_msg_id = "MSG-USER-TEST-001"

    source = WorkspaceAIContextSource(
        source_id="S-1",
        source_scope="notebook",
        source_type="plain_text",
        title="tai_lieu_mau.txt",
        privacy_label="local_only",
        text="Noi dung tai lieu mau.",
        included_chars=22,
        truncated=False,
    )

    chunks_received: list[str] = []

    def on_chunk(delta: str) -> None:
        chunks_received.append(delta)

    stream_state = {
        "text": "",
        "first_token_time": None,
        "started_at": time.time(),
        "warming_collection": None,
        "lock": Lock(),
    }

    t0 = time.time()
    res = _run_chat_turn_async(
        q_text="Hay tra cuu file abcxyz_not_found.msg xem co loi gi khong?",
        query_relevant_sources=(source,),
        conversation_id=conv_id,
        user_message_id=user_msg_id,
        on_chunk=on_chunk,
        stream_state=stream_state,
    )
    elapsed = time.time() - t0

    # 1. Quality requirement: response under 5 seconds
    assert elapsed < 5.0, f"Turn took too long: {elapsed:.2f}s"

    # 2. Return contract
    ok, answer, badge, err = res
    assert ok is True
    assert "abcxyz_not_found.msg" in answer
    assert "Không tìm thấy tài liệu" in answer
    assert isinstance(badge, dict)
    assert badge.get("provider") == "local_truthful_refusal"
    assert badge.get("document_missing") is True
    assert err is None

    # 3. on_chunk received the refusal answer
    assert len(chunks_received) > 0
    assert answer in "".join(chunks_received)

    # 4. All 3 markers are present in printed_markers
    marker_str = "\n".join(printed_markers)
    assert "[STREAMING_QA_START]" in marker_str
    assert f"conv={conv_id}" in marker_str
    assert "[STREAMING_QA_FIRST_TOKEN]" in marker_str
    assert "[STREAMING_QA_COMPLETE]" in marker_str
    assert "ok=True" in marker_str

    # 5. messages.jsonl has the refusal answer saved
    saved_msgs = load_messages(conv_id)
    assert len(saved_msgs) >= 1
    asst_msg = next((m for m in saved_msgs if m.role == "assistant"), None)
    assert asst_msg is not None
    assert asst_msg.content == answer
    assert asst_msg.conversation_id == conv_id
    assert asst_msg.reply_to_message_id == user_msg_id


def test_named_doc_not_found_without_on_chunk_emits_markers(monkeypatch, tmp_path):
    """Verify that when on_chunk is None, STREAMING_QA_FIRST_TOKEN is still emitted directly."""
    printed_markers: list[str] = []

    def mock_safe_print(msg: str) -> None:
        printed_markers.append(msg)

    monkeypatch.setattr("aios_habit.workspace_chat_app._safe_print_streaming_marker", mock_safe_print)

    test_messages_file = tmp_path / "messages.jsonl"
    monkeypatch.setattr("aios_habit.workspace_chat_store.MESSAGES_FILE", test_messages_file)

    conv_id = f"CONV-TEST-NO-CHUNK-{int(time.time() * 1000)}"

    source = WorkspaceAIContextSource(
        source_id="S-1",
        source_scope="notebook",
        source_type="plain_text",
        title="tai_lieu_mau.txt",
        privacy_label="local_only",
        text="Noi dung tai lieu mau.",
        included_chars=22,
        truncated=False,
    )

    res = _run_chat_turn_async(
        q_text="Hay tra cuu file xyz_missing_doc.xlsx ve thong so",
        query_relevant_sources=(source,),
        conversation_id=conv_id,
        on_chunk=None,
        stream_state=None,
    )

    ok, answer, badge, err = res
    assert ok is True
    assert "xyz_missing_doc.xlsx" in answer

    marker_str = "\n".join(printed_markers)
    assert "[STREAMING_QA_START]" in marker_str
    assert "[STREAMING_QA_FIRST_TOKEN]" in marker_str
    assert "[STREAMING_QA_COMPLETE]" in marker_str

    saved_msgs = load_messages(conv_id)
    assert len(saved_msgs) == 1
    assert saved_msgs[0].content == answer
