"""Lane C-Agent của Workspace Chat với context staging (vé WIRE-QA-CAGENT).

Kiểm tra phần ghép nối trong `route_workspace_chat_submission`: khi bật feature
flag, câu hỏi được ghép khối tham khảo staging và câu trả lời được gắn nhãn
bản thảo + nguồn cặp Q&A; khi tắt flag thì luồng giữ nguyên như cũ.
"""
from __future__ import annotations

from types import SimpleNamespace

from aios_habit.cagent_api import CAgentResponse
from aios_habit.feature_flags import override_feature_flags

QUESTION = (
    "Trong file cấu hình Matecon điều khiển AGV/ACR trên dây chuyền, hai chế độ "
    "ctrlMode = 0 và ctrlMode = 1 khác nhau như thế nào?"
)


def _run_cagent_route(monkeypatch, question: str = QUESTION):
    import aios_habit.workspace_chat_store as store
    from aios_habit import antigravity_bridge as bridge

    captured: dict[str, object] = {"saved_contents": []}

    def fake_call(endpoint, *, system_prompt, user_prompt, **kwargs):  # type: ignore[no-untyped-def]
        captured["endpoint"] = endpoint
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        captured["call_kwargs"] = kwargs
        return CAgentResponse(True, text="ctrlMode = 0 là tự động; ctrlMode = 1 là thủ công.")

    def fake_save_message(message):  # type: ignore[no-untyped-def]
        captured["saved_contents"].append(message.content)

    monkeypatch.setattr("aios_habit.cagent_api.call_cagent_prediction", fake_call)
    monkeypatch.setattr(store, "save_message", fake_save_message)
    monkeypatch.setattr(store, "load_conversation", lambda conversation_id: None)
    monkeypatch.setattr(store, "load_conversation_source_selections", lambda conversation_id: [])
    monkeypatch.setattr(store, "save_evidence_trace", lambda trace: None)
    monkeypatch.setattr(
        "aios_habit.evidence_trace.build_evidence_trace_from_citations",
        lambda **kwargs: SimpleNamespace(trace_id="trc-wire-test"),
    )
    monkeypatch.setattr(
        bridge, "_get_or_create_user_message", lambda *args, **kwargs: SimpleNamespace(id="MSG-USER")
    )
    monkeypatch.setattr(
        "aios_habit.workspace_memory_service.get_workspace_memory_enabled_preference",
        lambda: False,
    )

    result = bridge.route_workspace_chat_submission(
        question=question,
        evidence_items=[],
        packed_sources=(),
        conversation_id="CONV-WIRE-TEST",
        notebook_id="NB-WIRE-TEST",
        retrieval_applied=False,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(),
        chat_history=(),
        user_raw_input=question,
        backend="cagent_api",
    )
    return result, captured


def test_cagent_lane_injects_staging_reference_and_draft_label(monkeypatch) -> None:
    with override_feature_flags(wire_qa_cagent=True):
        (ok, _message, _badge, error), captured = _run_cagent_route(monkeypatch)

    assert ok is True
    assert error is None
    user_prompt = str(captured["user_prompt"])
    assert "--- DỮ LIỆU THAM KHẢO (BẢN THẢO) ---" in user_prompt
    assert "Câu hỏi gốc:" in user_prompt
    assert "ctrlMode" in user_prompt
    saved = "\n".join(captured["saved_contents"])
    assert saved.startswith("> ⚠️ **Bản thảo — chưa qua chuyên gia duyệt**")
    assert "Cặp Q&A #Q0001" in saved
    # Endpoint giữ nguyên mặc định, không thêm địa chỉ mới; có truyền cancellation.
    assert str(captured["endpoint"]).startswith("https://kdtvn-ai.cmcts.vn/api/v1/prediction/")
    assert "cancellation_event" in captured["call_kwargs"]


def test_cagent_lane_without_staging_context_when_flag_off(monkeypatch) -> None:
    with override_feature_flags(wire_qa_cagent=False):
        (ok, _message, _badge, error), captured = _run_cagent_route(monkeypatch)

    assert ok is True
    assert error is None
    assert "DỮ LIỆU THAM KHẢO (BẢN THẢO)" not in str(captured["user_prompt"])
    saved = "\n".join(captured["saved_contents"])
    assert not saved.startswith("> ⚠️ **Bản thảo")


def test_cagent_lane_without_staging_context_for_unrelated_question(monkeypatch) -> None:
    with override_feature_flags(wire_qa_cagent=True):
        (ok, _message, _badge, error), captured = _run_cagent_route(
            monkeypatch, question="Hôm nay ăn gì ngon nhỉ?"
        )

    assert ok is True
    assert error is None
    assert "DỮ LIỆU THAM KHẢO (BẢN THẢO)" not in str(captured["user_prompt"])
    saved = "\n".join(captured["saved_contents"])
    assert not saved.startswith("> ⚠️ **Bản thảo")
