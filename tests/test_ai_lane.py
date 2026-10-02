"""Tests cho ai_lane (UX-CHAT-CORE #3): tu dong chon lane, ghi nho, khong nhay."""

from aios_habit.ai_lane import (
    BACKEND_CAGENT,
    BACKEND_GEMINI_WEB,
    BACKEND_LOCAL,
    BACKEND_ROUTER,
    auto_backend_for_conversation,
    backend_label_vi,
    describe_decision_for_answer,
    select_ai_backend,
)


def test_priority_bridge_first():
    decision = select_ai_backend(
        bridge_available=True, cagent_endpoint="http://x", router_keys_present=True
    )
    assert decision.backend == BACKEND_GEMINI_WEB
    assert decision.automatic is True


def test_falls_back_to_cagent_then_router_then_local():
    assert (
        select_ai_backend(bridge_available=False, cagent_endpoint="http://x").backend
        == BACKEND_CAGENT
    )
    assert (
        select_ai_backend(bridge_available=False, router_keys_present=True).backend
        == BACKEND_ROUTER
    )
    assert (
        select_ai_backend(bridge_available=False).backend == BACKEND_LOCAL
    )


def test_router_skipped_while_cooling_down():
    decision = select_ai_backend(
        bridge_available=False, router_keys_present=True, router_cooling_down=True
    )
    assert decision.backend == BACKEND_LOCAL


def test_manual_override_pins_backend():
    decision = select_ai_backend(
        bridge_available=True, manual_override="cagent_api"
    )
    assert decision.backend == BACKEND_CAGENT
    assert decision.automatic is False


def test_invalid_override_is_ignored():
    decision = select_ai_backend(bridge_available=True, manual_override="khong_co")
    assert decision.backend == BACKEND_GEMINI_WEB


def test_remembers_choice_per_conversation_key():
    session = {}
    first = auto_backend_for_conversation(
        "lane_conv1", session, bridge_available=False, cagent_endpoint="http://x"
    )
    assert first.backend == BACKEND_CAGENT
    assert session["lane_conv1"] == BACKEND_CAGENT
    # Bridge phuc hoi (uu tien cao hon) nhung cagent van kha dung -> giu cagent, khong nhay.
    second = auto_backend_for_conversation(
        "lane_conv1",
        session,
        bridge_available=True,
        cagent_endpoint="http://x",
    )
    assert second.backend == BACKEND_CAGENT
    assert "Giữ lane" in second.reason_vi


def test_remembered_lane_dropped_when_unavailable():
    session = {"lane_conv1": BACKEND_GEMINI_WEB}
    decision = auto_backend_for_conversation(
        "lane_conv1",
        session,
        bridge_available=False,
        cagent_endpoint="http://x",
    )
    assert decision.backend == BACKEND_CAGENT
    assert session["lane_conv1"] == BACKEND_CAGENT


def test_different_conversations_have_independent_memory():
    session = {}
    auto_backend_for_conversation("lane_a", session, bridge_available=True)
    auto_backend_for_conversation(
        "lane_b", session, bridge_available=False, cagent_endpoint="http://x"
    )
    assert session["lane_a"] == BACKEND_GEMINI_WEB
    assert session["lane_b"] == BACKEND_CAGENT


def test_local_fallback_reason_tells_user_what_to_check():
    decision = select_ai_backend(bridge_available=False)
    assert "cầu nối" in decision.reason_vi


def test_describe_decision_for_answer_is_vietnamese():
    decision = select_ai_backend(bridge_available=True)
    text = describe_decision_for_answer(decision)
    assert "Đang dùng:" in text
    assert backend_label_vi(BACKEND_GEMINI_WEB) in text
