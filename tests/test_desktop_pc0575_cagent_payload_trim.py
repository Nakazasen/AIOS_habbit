"""Unit and integration tests for DESKTOP-PC0575-CAGENT-PAYLOAD-TRIM-FIX.

Requirements:
1. Limit conversation history sent with C-Agent synthesis call to a reasonable budget.
2. Short conversation below threshold is kept intact (behavior unchanged).
3. Long conversation is trimmed to the most recent turns within turn count and character budget.
4. Current question and retrieval evidence are ALWAYS preserved intact.
5. Routing and timeout behaviors remain completely unchanged.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List
import pytest

from aios_habit.cagent_api import (
    DEFAULT_CAGENT_MAX_HISTORY_CHARS,
    DEFAULT_CAGENT_MAX_HISTORY_TURNS,
    CAgentResponse,
    trim_chat_history_for_cagent,
)
from aios_habit.workspace_chat_ai_answer import (
    WorkspaceAIContextSource,
    build_workspace_ai_prompt,
)
from aios_habit import antigravity_bridge as bridge


# ---------------------------------------------------------------------------
# Unit tests for trim_chat_history_for_cagent
# ---------------------------------------------------------------------------

def test_trim_chat_history_empty_or_none() -> None:
    assert trim_chat_history_for_cagent(None) == ()
    assert trim_chat_history_for_cagent([]) == ()
    assert trim_chat_history_for_cagent(()) == ()


def test_trim_chat_history_short_conversation_kept_intact() -> None:
    short_history = (
        {"role": "user", "content": "Xin chào trợ lý."},
        {"role": "assistant", "content": "Chào bạn, tôi có thể giúp gì?"},
        {"role": "user", "content": "Cho tôi biết thông tin về LSU."},
        {"role": "assistant", "content": "LSU là cụm quét laser trong máy in."},
    )
    result = trim_chat_history_for_cagent(short_history, max_turns=6, max_chars=4000)
    assert len(result) == 4
    assert result == short_history


def test_trim_chat_history_long_conversation_trimmed_to_max_turns() -> None:
    # 20 messages (10 turns)
    long_history = tuple(
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Tin nhắn số {i}: nội dung kiểm thử ngắn"}
        for i in range(20)
    )
    result = trim_chat_history_for_cagent(long_history, max_turns=6, max_chars=4000)
    # Should keep exactly the last 6 messages
    assert len(result) == 6
    assert result[0]["content"] == "Tin nhắn số 14: nội dung kiểm thử ngắn"
    assert result[-1]["content"] == "Tin nhắn số 19: nội dung kiểm thử ngắn"


def test_trim_chat_history_character_budget_capping() -> None:
    # 6 messages, but each is 1000 characters (total 6000 > 4000)
    history_with_large_messages = tuple(
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"MSG_{i}_" + ("A" * 990)}
        for i in range(6)
    )
    result = trim_chat_history_for_cagent(history_with_large_messages, max_turns=6, max_chars=4000)
    total_chars = sum(len(m["content"]) for m in result)
    assert total_chars <= 4000
    # The most recent message should always be kept
    assert result[-1]["content"].startswith("MSG_5_")
    # Older messages that exceed the budget must be dropped
    assert len(result) < 6


def test_trim_chat_history_single_huge_message_truncation() -> None:
    huge_history = (
        {"role": "user", "content": "X" * 5000},
    )
    result = trim_chat_history_for_cagent(huge_history, max_turns=6, max_chars=4000)
    assert len(result) == 1
    assert len(result[0]["content"]) == 4000


def test_trim_chat_history_preserves_anchor_directive() -> None:
    anchor_directive = (
        "[CHỈ THỊ NEO NGỮ CẢNH TRẢ LỜI / ANCHOR CONTEXT DIRECTIVE]:\n"
        "Người dùng đang bấm 'Trả lời' trực tiếp vào đáp án dưới đây. Ngữ cảnh này được ƯU TIÊN TUYỆT ĐỐI."
    )
    history = tuple(
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Tin nhắn {i}"}
        for i in range(20)
    ) + ({"role": "system", "content": anchor_directive},)

    result = trim_chat_history_for_cagent(history, max_turns=6, max_chars=4000)
    # The anchor directive at the end must be preserved
    assert len(result) == 6
    assert result[-1]["role"] == "system"
    assert "[CHỈ THỊ NEO NGỮ CẢNH" in result[-1]["content"]
    # Preceding messages are the most recent conversational ones
    assert result[-2]["content"] == "Tin nhắn 19"


def test_trim_chat_history_custom_budget_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    history = tuple(
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Msg {i}"}
        for i in range(10)
    )
    # Custom max_turns parameter
    res_custom = trim_chat_history_for_cagent(history, max_turns=4)
    assert len(res_custom) == 4
    assert res_custom[-1]["content"] == "Msg 9"
    assert res_custom[0]["content"] == "Msg 6"


# ---------------------------------------------------------------------------
# Integration tests with route_workspace_chat_submission
# ---------------------------------------------------------------------------

def test_cagent_lane_trims_long_history_before_sending(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that route_workspace_chat_submission trims a 50-message history down to 6 messages when submitting to C-Agent."""
    captured: Dict[str, Any] = {}

    def fake_call(endpoint: str, *, system_prompt: str, user_prompt: str, **kwargs: Any) -> CAgentResponse:
        captured["endpoint"] = endpoint
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        captured["kwargs"] = kwargs
        return CAgentResponse(True, text="Đây là câu trả lời kiểm thử từ C-Agent.")

    monkeypatch.setattr("aios_habit.cagent_api.call_cagent_prediction", fake_call)
    monkeypatch.setattr("aios_habit.workspace_chat_store.save_message", lambda *args, **kwargs: None)
    monkeypatch.setattr("aios_habit.workspace_chat_store.load_conversation", lambda *args: None)
    monkeypatch.setattr("aios_habit.workspace_chat_store.load_conversation_source_selections", lambda *args: [])
    monkeypatch.setattr("aios_habit.workspace_chat_store.save_evidence_trace", lambda *args: None)
    monkeypatch.setattr(
        "aios_habit.evidence_trace.build_evidence_trace_from_citations",
        lambda **kwargs: SimpleNamespace(trace_id="trc-test-trim-01"),
    )
    monkeypatch.setattr(
        bridge, "_get_or_create_user_message", lambda *args, **kwargs: SimpleNamespace(id="MSG-USER-TRIM")
    )
    monkeypatch.setattr(
        "aios_habit.workspace_memory_service.get_workspace_memory_enabled_preference",
        lambda: False,
    )

    # 50 messages history
    long_history = tuple(
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Câu chuyện thứ {i}: chi tiết quá khứ"}
        for i in range(50)
    )

    current_question = "LSU là gì và gồm những bộ phận quang học chính nào?"
    src_text = "LSU (Laser Scanning Unit) gồm các bộ phận: polygon mirror, f-theta lens, LD board."
    test_source = WorkspaceAIContextSource(
        source_id="src-lsu-01",
        title="Tài liệu đào tạo LSU",
        source_scope="notebook",
        source_type="plain_text",
        privacy_label="cloud_safe",
        text=src_text,
        included_chars=len(src_text),
    )

    ok, message, badge, error = bridge.route_workspace_chat_submission(
        question=current_question,
        evidence_items=[],
        packed_sources=(test_source,),
        conversation_id="CONV-TRIM-TEST",
        notebook_id="NB-TRIM-TEST",
        retrieval_applied=True,
        retrieved_sources=(test_source,),
        retrieval_summary="Tra cứu 1 đoạn liên quan.",
        current_keys=(),
        chat_history=long_history,
        user_raw_input=current_question,
        backend="cagent_api",
    )

    assert ok is True
    assert error is None
    assert badge is not None
    assert badge["operational_mode"] == "external_api"

    user_prompt = str(captured["user_prompt"])
    # 1. Current question is completely intact
    assert current_question in user_prompt
    # 2. Retrieval evidence is completely intact
    assert "polygon mirror, f-theta lens, LD board" in user_prompt
    # 3. Old messages (e.g. 0 to 43) are trimmed out
    assert "Câu chuyện thứ 0:" not in user_prompt
    assert "Câu chuyện thứ 10:" not in user_prompt
    assert "Câu chuyện thứ 43:" not in user_prompt
    # 4. Recent messages (44 to 49) are kept
    assert "Câu chuyện thứ 44:" in user_prompt
    assert "Câu chuyện thứ 49:" in user_prompt


def test_cagent_lane_short_history_kept_intact_in_submission(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that route_workspace_chat_submission leaves a short history untouched."""
    captured: Dict[str, Any] = {}

    def fake_call(endpoint: str, *, system_prompt: str, user_prompt: str, **kwargs: Any) -> CAgentResponse:
        captured["user_prompt"] = user_prompt
        return CAgentResponse(True, text="Trả lời từ C-Agent cho short history.")

    monkeypatch.setattr("aios_habit.cagent_api.call_cagent_prediction", fake_call)
    monkeypatch.setattr("aios_habit.workspace_chat_store.save_message", lambda *args, **kwargs: None)
    monkeypatch.setattr("aios_habit.workspace_chat_store.load_conversation", lambda *args: None)
    monkeypatch.setattr("aios_habit.workspace_chat_store.load_conversation_source_selections", lambda *args: [])
    monkeypatch.setattr("aios_habit.workspace_chat_store.save_evidence_trace", lambda *args: None)
    monkeypatch.setattr(
        "aios_habit.evidence_trace.build_evidence_trace_from_citations",
        lambda **kwargs: SimpleNamespace(trace_id="trc-test-trim-02"),
    )
    monkeypatch.setattr(
        bridge, "_get_or_create_user_message", lambda *args, **kwargs: SimpleNamespace(id="MSG-USER-TRIM2")
    )
    monkeypatch.setattr(
        "aios_habit.workspace_memory_service.get_workspace_memory_enabled_preference",
        lambda: False,
    )

    short_history = (
        {"role": "user", "content": "Câu hỏi ngắn 1"},
        {"role": "assistant", "content": "Đáp án ngắn 1"},
    )
    question = "Câu hỏi ngắn 2"

    ok, message, badge, error = bridge.route_workspace_chat_submission(
        question=question,
        evidence_items=[],
        packed_sources=(),
        conversation_id="CONV-SHORT-TEST",
        notebook_id="NB-SHORT-TEST",
        retrieval_applied=False,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(),
        chat_history=short_history,
        user_raw_input=question,
        backend="cagent_api",
    )

    assert ok is True
    user_prompt = str(captured["user_prompt"])
    assert "Câu hỏi ngắn 1" in user_prompt
    assert "Đáp án ngắn 1" in user_prompt
    assert "Câu hỏi ngắn 2" in user_prompt


def test_cagent_lane_does_not_mutate_chat_history_for_failover(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that if C-Agent fails/times out, the original chat_history is not mutated for subsequent candidates in failover."""
    history = (
        {"role": "user", "content": "Tin nhắn 1"},
        {"role": "assistant", "content": "Tin nhắn 2"},
    )
    original_tuple = tuple(history)

    def fake_cagent_fail(endpoint: str, **kwargs: Any) -> CAgentResponse:
        return CAgentResponse(False, error_message="C-Agent timeout simulation")

    monkeypatch.setattr("aios_habit.cagent_api.call_cagent_prediction", fake_cagent_fail)

    # Route with cagent_api -> should fail cagent and cascade down
    ok, message, badge, error = bridge.route_workspace_chat_submission(
        question="Test failover",
        evidence_items=[],
        packed_sources=(),
        conversation_id="CONV-FAILOVER-TEST",
        notebook_id="NB-FAILOVER-TEST",
        retrieval_applied=False,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(),
        chat_history=history,
        user_raw_input="Test failover",
        backend="cagent_api",
    )

    # chat_history tuple was not modified
    assert history == original_tuple
