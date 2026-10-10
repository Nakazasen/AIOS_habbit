"""Unit tests for synthesis lane failover and transition chain (DESKTOP-SYNTH-LANE-FIX-HOME).

Verifies:
1. Timeout / error on C-Agent -> automatic fallback to Nakazasen Router.
2. Error / system prompt leak on Router -> automatic fallback to local extractive synthesis.
3. Direct 'local' backend execution returns grounded answer and badge.
4. Preserves OCR text and evidence items in local fallback answer.
5. All transition paths guarantee completion without hanging.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
import pytest

from aios_habit.cagent_api import CAgentResponse
from aios_habit.workspace_chat_ai_answer import WorkspaceAIAnswerResult
from aios_habit import antigravity_bridge as bridge


@pytest.fixture
def mock_store_and_trace(monkeypatch):
    import aios_habit.workspace_chat_store as store

    saved_messages = []
    saved_traces = []

    monkeypatch.setattr(store, "save_message", lambda msg: saved_messages.append(msg))
    monkeypatch.setattr(store, "save_evidence_trace", lambda trc: saved_traces.append(trc))
    monkeypatch.setattr(store, "load_messages", lambda conv_id: list(saved_messages))
    monkeypatch.setattr(store, "load_conversation", lambda conv_id: None)
    monkeypatch.setattr(store, "load_conversation_source_selections", lambda conv_id: [])
    monkeypatch.setattr(
        "aios_habit.evidence_trace.build_evidence_trace_from_citations",
        lambda **kwargs: SimpleNamespace(trace_id="trc-failover-test", metadata={"status": "valid"}),
    )
    monkeypatch.setattr(
        bridge,
        "_get_or_create_user_message",
        lambda *args, **kwargs: SimpleNamespace(id="MSG-USER-TEST"),
    )
    monkeypatch.setattr(
        "aios_habit.workspace_memory_service.get_workspace_memory_enabled_preference",
        lambda: False,
    )
    return {"messages": saved_messages, "traces": saved_traces}


def test_cagent_timeout_falls_back_to_router(monkeypatch, mock_store_and_trace):
    """When C-Agent times out, route automatically transitions to nakazasen_router."""
    def fake_cagent(*args, **kwargs):
        return CAgentResponse(False, error_message="Dịch vụ C-Agent phản hồi quá thời gian chờ (timeout)")

    def fake_router_answer(request, context):
        return WorkspaceAIAnswerResult(
            ok=True,
            answer_text="Câu trả lời thành công từ Nakazasen Router.",
            included_source_titles=("Tài liệu LSU",),
            warnings=(),
            effective_provider="Command Code Pool",
            effective_model="inclusionai/ling-3.1-flash:free",
        )

    monkeypatch.setattr("aios_habit.cagent_api.call_cagent_prediction", fake_cagent)
    monkeypatch.setattr("aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer", fake_router_answer)

    ok, msg, badge, err = bridge.route_workspace_chat_submission(
        question="Ý nghĩa thông số DMT và PMT là gì?",
        evidence_items=[{"evidence_id": "EV1", "title": "Tài liệu LSU", "text": "DMT và PMT đo quang học"}],
        packed_sources=(),
        conversation_id="CONV-FAILOVER-1",
        notebook_id="NB-1",
        retrieval_applied=True,
        retrieved_sources=(),
        retrieval_summary="Đang tra cứu khối LSU.",
        current_keys=(),
        chat_history=(),
        user_raw_input="Ý nghĩa thông số DMT và PMT là gì?",
        backend="cagent_api",
        cagent_endpoint_url="https://fake-cagent.local/api",
    )

    assert ok is True
    assert "chuyển tuyến dự phòng từ C-Agent" in msg
    assert badge is not None
    assert badge.get("fallback_used") is True
    assert badge.get("initial_backend") == "cagent_api"
    assert badge.get("retrieval_summary") == "Đang tra cứu khối LSU."
    assert "Command Code Pool" in badge.get("provider", "")


def test_router_error_falls_back_to_local_extractive(monkeypatch, mock_store_and_trace):
    """When router fails or leaks, route automatically transitions to local extractive synthesis."""
    def fake_router_answer(request, context):
        return WorkspaceAIAnswerResult(
            ok=False,
            answer_text="",
            included_source_titles=(),
            warnings=(),
            error_message="Router quota exceeded or connection reset",
        )

    monkeypatch.setattr("aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer", fake_router_answer)

    ev_items = [
        {"evidence_id": "EV-C7620", "title": "Sổ tay mã lỗi Kyocera", "text": "Mã lỗi C7620: Lỗi giao tiếp bo mạch chính và bo scan."}
    ]

    ok, msg, badge, err = bridge.route_workspace_chat_submission(
        question="Mã lỗi C7620 trên dòng máy in Kyocera là gì?",
        evidence_items=ev_items,
        packed_sources=(),
        conversation_id="CONV-FAILOVER-2",
        notebook_id="NB-1",
        retrieval_applied=True,
        retrieved_sources=(),
        retrieval_summary="Đang tra cứu khối Điều tra lỗi.",
        current_keys=(),
        chat_history=(),
        user_raw_input="Mã lỗi C7620 trên dòng máy in Kyocera là gì?",
        backend="nakazasen_router",
    )

    assert ok is True
    assert "chuyển tuyến dự phòng từ Nakazasen Router" in msg
    assert badge is not None
    assert badge.get("fallback_used") is True
    assert badge.get("initial_backend") == "nakazasen_router"
    assert badge.get("operational_mode") == "local_grounded_fallback"
    assert badge.get("retrieval_summary") == "Đang tra cứu khối Điều tra lỗi."
    # Verify assistant message was saved to store
    assert len(mock_store_and_trace["messages"]) >= 1
    assistant_msg = mock_store_and_trace["messages"][-1]
    assert "Sổ tay mã lỗi Kyocera" in assistant_msg.content
    assert "C7620" in assistant_msg.content


def test_direct_local_backend_execution(monkeypatch, mock_store_and_trace):
    """When backend is set to 'local', runs directly without calling external APIs."""
    ev_items = [
        {"evidence_id": "EV-AGV", "title": "Tài liệu MOM Opcenter", "text": "Xuất kho AGV qua staging oricon."}
    ]

    ok, msg, badge, err = bridge.route_workspace_chat_submission(
        question="Quy trình xuất kho qua AGV như thế nào?",
        evidence_items=ev_items,
        packed_sources=(),
        conversation_id="CONV-LOCAL-1",
        notebook_id="NB-1",
        retrieval_applied=True,
        retrieved_sources=(),
        retrieval_summary="Đang tra cứu khối MOM.",
        current_keys=(),
        chat_history=(),
        user_raw_input="Quy trình xuất kho qua AGV như thế nào?",
        backend="local",
    )

    assert ok is True
    assert badge is not None
    assert badge.get("operational_mode") == "local_grounded_fallback"
    assert badge.get("retrieval_summary") == "Đang tra cứu khối MOM."
    assert len(mock_store_and_trace["messages"]) >= 1
    assert "MOM Opcenter" in mock_store_and_trace["messages"][-1].content


def test_local_fallback_preserves_ocr_extracted_text(monkeypatch, mock_store_and_trace):
    """Local fallback answer includes OCR extracted text block if present in the prompt."""
    def fake_router_answer(request, context):
        return WorkspaceAIAnswerResult(
            ok=False,
            answer_text="",
            included_source_titles=(),
            warnings=(),
            error_message="Provider offline",
        )

    monkeypatch.setattr("aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer", fake_router_answer)

    q_with_ocr = (
        "Dựa vào ảnh đính kèm cho biết thông số đo kiểm.\n\n"
        "[Nội dung chữ đọc được từ ảnh đính kèm (ảnh_1.png)]:\n"
        "Mã thiết bị: OPTO-BENCH-77A\n"
        "Điện áp: 24.50 V\n"
        "Dòng đỉnh: 3.82 A\n"
        "Độ lệch tâm: 0.038 mm\n"
        "Tần số: 1250 Hz\n"
        "Thời gian: 14.2 ms\n"
        "Kết luận: DAT_CHUAN_PASS"
    )

    ok, msg, badge, err = bridge.route_workspace_chat_submission(
        question=q_with_ocr,
        evidence_items=[],
        packed_sources=(),
        conversation_id="CONV-OCR-FALLBACK",
        notebook_id="NB-1",
        retrieval_applied=False,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(),
        chat_history=(),
        user_raw_input=q_with_ocr,
        backend="nakazasen_router",
    )

    assert ok is True
    assert badge is not None
    assistant_content = mock_store_and_trace["messages"][-1].content
    assert "OPTO-BENCH-77A" in assistant_content
    assert "24.50 V" in assistant_content
    assert "3.82 A" in assistant_content
    assert "0.038 mm" in assistant_content
    assert "1250 Hz" in assistant_content
    assert "14.2 ms" in assistant_content
    assert "DAT_CHUAN_PASS" in assistant_content


def test_router_timeout_falls_back_to_local_extractive(monkeypatch, mock_store_and_trace):
    """When router hangs longer than AIOS_ROUTER_TIMEOUT_SECONDS, timeout triggers local fallback."""
    import time
    def hanging_router_answer(request, context):
        time.sleep(2.0)
        return WorkspaceAIAnswerResult(ok=True, answer_text="Late answer")

    monkeypatch.setenv("AIOS_ROUTER_TIMEOUT_SECONDS", "1")
    monkeypatch.setattr("aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer", hanging_router_answer)

    ev_items = [
        {"evidence_id": "EV-TO", "title": "Tài liệu kiểm định", "text": "Độ chính xác đạt 99.9%."}
    ]

    ok, msg, badge, err = bridge.route_workspace_chat_submission(
        question="Tài liệu kiểm định nói gì?",
        evidence_items=ev_items,
        packed_sources=(),
        conversation_id="CONV-ROUTER-TIMEOUT",
        notebook_id="NB-1",
        retrieval_applied=True,
        retrieved_sources=(),
        retrieval_summary="Đang tra cứu tài liệu.",
        current_keys=(),
        chat_history=(),
        user_raw_input="Tài liệu kiểm định nói gì?",
        backend="nakazasen_router",
    )

    assert ok is True
    assert badge is not None
    assert badge.get("fallback_used") is True
    assert badge.get("operational_mode") == "local_grounded_fallback"
    assert "Độ chính xác đạt 99.9%" in mock_store_and_trace["messages"][-1].content

