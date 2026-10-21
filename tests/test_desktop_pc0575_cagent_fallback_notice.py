"""Tests for ticket DESKTOP-PC0575-CAGENT-FALLBACK-NOTICE-FIX:
Clear fallback notice displayed on turns where the actual route fell back
away from the user's chosen/pinned backend due to timeout/error (especially
falling back to local document synthesis).

Verifies:
1. should_show_fallback_notice returns True for fallback from C-Agent/pinned backend to local.
2. Negative tests:
   - Pinned backend succeeds -> False (no warning).
   - User explicitly selected local backend -> False (no warning).
   - Normal automatic routing without fallback -> False (no warning).
   - Empty or None badge -> False.
   - Fallback to another remote AI model -> False.
3. format_fallback_notice produces exact Vietnamese text calling out "C-Agent" accurately.
4. render_fallback_notice renders st.warning appropriately.
5. render_chat_bubble displays warning when fallback badge is provided.
6. End-to-end simulation with bridge.route_workspace_chat_submission.
7. Preserves existing answer labels (local_fallback_note) without modification.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List, Optional
import pytest

from aios_habit.workspace_chat_models import ChatMessage
from aios_habit.workspace_chat_ui import (
    format_fallback_notice,
    render_chat_bubble,
    render_fallback_notice,
    should_show_fallback_notice,
)


class MockSessionState(dict):
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class MockStreamlit:
    """Mock Streamlit environment capturing rendering calls."""

    def __init__(self) -> None:
        self.calls: List[tuple] = []
        self.session_state = MockSessionState()
        self.widget_states: Dict[str, Any] = {}

    def markdown(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("markdown", str(text)))

    def write(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("write", str(text)))

    def info(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("info", str(text)))

    def caption(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("caption", str(text)))

    def warning(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("warning", str(text)))

    def error(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("error", str(text)))

    def success(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("success", str(text)))

    def chat_message(self, role: str) -> "MockChatMessageContext":
        return MockChatMessageContext(self, role)

    def container(self) -> "MockStreamlit":
        return self


class MockChatMessageContext:
    def __init__(self, mock_st: MockStreamlit, role: str) -> None:
        self.mock_st = mock_st
        self.role = role

    def __enter__(self) -> "MockChatMessageContext":
        self.mock_st.calls.append(("chat_message_start", self.role))
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.mock_st.calls.append(("chat_message_end", self.role))


@pytest.fixture
def mock_st_env(monkeypatch: pytest.MonkeyPatch) -> MockStreamlit:
    mock = MockStreamlit()
    monkeypatch.setattr("streamlit.markdown", mock.markdown)
    monkeypatch.setattr("streamlit.write", mock.write)
    monkeypatch.setattr("streamlit.info", mock.info)
    monkeypatch.setattr("streamlit.caption", mock.caption)
    monkeypatch.setattr("streamlit.warning", mock.warning)
    monkeypatch.setattr("streamlit.error", mock.error)
    monkeypatch.setattr("streamlit.success", mock.success)
    monkeypatch.setattr("streamlit.chat_message", mock.chat_message)
    monkeypatch.setattr("streamlit.session_state", mock.session_state)
    return mock


# ==============================================================================
# 1. UNIT TESTS: Condition to show/hide fallback notice
# ==============================================================================

def test_should_show_fallback_notice_cagent_fallback():
    """True when C-Agent was initial_backend, fallback occurred, and answer is local synthesis."""
    badge = {
        "fallback_used": True,
        "initial_backend": "cagent_api",
        "operational_mode": "local_grounded_fallback",
        "provider": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
        "bridge": "Trích xuất cục bộ",
    }
    assert should_show_fallback_notice(badge) is True


def test_should_show_fallback_notice_gemini_fallback():
    """True when Gemini Web was initial_backend and fell back to local."""
    badge = {
        "fallback_used": True,
        "initial_backend": "gemini_web",
        "operational_mode": "local_grounded_fallback",
        "provider": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
    }
    assert should_show_fallback_notice(badge) is True


def test_should_show_fallback_notice_router_fallback():
    """True when Nakazasen Router was initial_backend and fell back to local."""
    badge = {
        "fallback_used": True,
        "initial_backend": "nakazasen_router",
        "operational_mode": "local_grounded_fallback",
        "provider": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
    }
    assert should_show_fallback_notice(badge) is True


def test_should_not_show_when_pinned_cagent_succeeds():
    """Negative test: When pinned C-Agent succeeds, no warning must be shown."""
    badge = {
        "fallback_used": False,
        "initial_backend": None,
        "operational_mode": "grounded",
        "provider": "cagent_api",
        "verified_model": "flowise_cagent",
    }
    assert should_show_fallback_notice(badge) is False


def test_should_not_show_when_user_explicitly_chose_local_lane():
    """Negative test: When user intentionally selects local lane, no warning must be shown."""
    # Direct local execution without initial_backend
    badge_direct_local = {
        "fallback_used": True,
        "initial_backend": None,
        "operational_mode": "local_grounded_fallback",
        "provider": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
    }
    assert should_show_fallback_notice(badge_direct_local) is False

    # Explicit initial_backend = "local"
    badge_explicit_local = {
        "fallback_used": True,
        "initial_backend": "local",
        "operational_mode": "local_grounded_fallback",
        "provider": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
    }
    assert should_show_fallback_notice(badge_explicit_local) is False


def test_should_not_show_when_fallback_target_is_remote_ai():
    """Negative test: If fallback stayed on an AI model (e.g. C-Agent -> Nakazasen Router), no local warning."""
    badge_router_target = {
        "fallback_used": True,
        "initial_backend": "cagent_api",
        "operational_mode": "external_ai",
        "provider": "Command Code Pool",
    }
    assert should_show_fallback_notice(badge_router_target) is False


def test_should_not_show_when_badge_empty_or_none():
    """Negative test: None or empty data returns False."""
    assert should_show_fallback_notice(None) is False
    assert should_show_fallback_notice({}) is False
    assert should_show_fallback_notice("not-a-dict") is False


# ==============================================================================
# 2. UNIT TESTS: Format text and proper naming of C-Agent
# ==============================================================================

def test_format_fallback_notice_cagent_vietnamese():
    """Warning text in Vietnamese properly naming 'C-Agent'."""
    badge = {
        "fallback_used": True,
        "initial_backend": "cagent_api",
        "operational_mode": "local_grounded_fallback",
        "provider": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
    }
    notice = format_fallback_notice(badge, locale="vi")
    assert notice == "Dịch vụ C-Agent không phản hồi trong thời gian chờ, đáp án hiện tại là bản tổng hợp cục bộ từ tài liệu."
    assert "C-Agent" in notice
    assert "không phản hồi trong thời gian chờ" in notice
    assert "tổng hợp cục bộ từ tài liệu" in notice


def test_format_fallback_notice_gemini_vietnamese():
    """Warning text in Vietnamese properly naming 'Gemini qua cầu nối'."""
    badge = {
        "fallback_used": True,
        "initial_backend": "gemini_web",
        "operational_mode": "local_grounded_fallback",
        "provider": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
    }
    notice = format_fallback_notice(badge, locale="vi")
    assert notice == "Dịch vụ Gemini qua cầu nối không phản hồi trong thời gian chờ, đáp án hiện tại là bản tổng hợp cục bộ từ tài liệu."


def test_format_fallback_notice_returns_empty_when_not_applicable():
    """Returns empty string when notice should not be shown."""
    badge_ok = {
        "fallback_used": False,
        "operational_mode": "grounded",
    }
    assert format_fallback_notice(badge_ok, locale="vi") == ""


# ==============================================================================
# 3. UNIT TESTS: UI rendering with Streamlit Mock
# ==============================================================================

def test_render_fallback_notice_displays_warning(mock_st_env: MockStreamlit):
    """render_fallback_notice calls st.warning with the expected text."""
    badge = {
        "fallback_used": True,
        "initial_backend": "cagent_api",
        "operational_mode": "local_grounded_fallback",
        "provider": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
    }
    render_fallback_notice(badge, locale="vi")

    warning_calls = [c for c in mock_st_env.calls if c[0] == "warning"]
    assert len(warning_calls) == 1
    assert "Dịch vụ C-Agent không phản hồi trong thời gian chờ, đáp án hiện tại là bản tổng hợp cục bộ từ tài liệu." in warning_calls[0][1]


def test_render_fallback_notice_suppressed_for_negative_cases(mock_st_env: MockStreamlit):
    """Negative test: render_fallback_notice suppresses warning when not applicable."""
    badge_local = {
        "fallback_used": True,
        "initial_backend": "local",
        "operational_mode": "local_grounded_fallback",
    }
    render_fallback_notice(badge_local, locale="vi")
    warning_calls = [c for c in mock_st_env.calls if c[0] == "warning"]
    assert len(warning_calls) == 0


def test_render_chat_bubble_with_fallback_badge(mock_st_env: MockStreamlit):
    """render_chat_bubble renders warning when fallback badge is attached."""
    msg = ChatMessage(
        id="MSG-TEST-1",
        conversation_id="CONV-1",
        role="assistant",
        content="Nội dung trích xuất cục bộ từ tài liệu.",
    )
    fallback_badge = {
        "fallback_used": True,
        "initial_backend": "cagent_api",
        "operational_mode": "local_grounded_fallback",
        "provider": "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình",
    }
    render_chat_bubble(msg, is_latest=True, locale="vi", badge_data=fallback_badge)

    warning_calls = [c for c in mock_st_env.calls if c[0] == "warning"]
    assert len(warning_calls) == 1
    assert "Dịch vụ C-Agent không phản hồi trong thời gian chờ" in warning_calls[0][1]


def test_render_chat_bubble_without_fallback_badge(mock_st_env: MockStreamlit):
    """Negative test: render_chat_bubble does not render warning when no fallback badge."""
    msg = ChatMessage(
        id="MSG-TEST-2",
        conversation_id="CONV-1",
        role="assistant",
        content="Nội dung trả lời thông thường.",
    )
    ok_badge = {
        "fallback_used": False,
        "initial_backend": None,
        "operational_mode": "grounded",
    }
    render_chat_bubble(msg, is_latest=True, locale="vi", badge_data=ok_badge)

    warning_calls = [c for c in mock_st_env.calls if c[0] == "warning"]
    assert len(warning_calls) == 0


# ==============================================================================
# 4. INTEGRATION SIMULATION: Real routing failover trace reproduction
# ==============================================================================

def test_integration_routing_simulation_cagent_timeout_triggers_notice(monkeypatch: pytest.MonkeyPatch):
    """Simulates the 17:53 incident: C-Agent times out, falls back to local, and UI badge triggers warning."""
    import aios_habit.workspace_chat_store as store
    import aios_habit.antigravity_bridge as bridge
    from aios_habit.cagent_api import CAgentResponse

    saved_messages = []
    saved_traces = []

    monkeypatch.setattr(store, "save_message", lambda msg: saved_messages.append(msg))
    monkeypatch.setattr(store, "save_evidence_trace", lambda trc: saved_traces.append(trc))
    monkeypatch.setattr(store, "load_messages", lambda conv_id: list(saved_messages))
    monkeypatch.setattr(store, "load_conversation", lambda conv_id: None)
    monkeypatch.setattr(store, "load_conversation_source_selections", lambda conv_id: [])
    monkeypatch.setattr(
        "aios_habit.evidence_trace.build_evidence_trace_from_citations",
        lambda **kwargs: SimpleNamespace(trace_id="trc_test_pc0575", metadata={"status": "valid"}),
    )
    monkeypatch.setattr(
        bridge,
        "_get_or_create_user_message",
        lambda *args, **kwargs: SimpleNamespace(id="MSG-USER-PC0575"),
    )
    monkeypatch.setattr(
        "aios_habit.workspace_memory_service.get_workspace_memory_enabled_preference",
        lambda: False,
    )

    # Simulate C-Agent timeout (as happened at 17:53)
    def fake_cagent_timeout(*args, **kwargs):
        return CAgentResponse(False, error_message="Dịch vụ C-Agent phản hồi quá 60 giây. Vui lòng thử lại với câu hỏi ngắn gọn hơn.")

    monkeypatch.setattr("aios_habit.cagent_api.call_cagent_prediction", fake_cagent_timeout)

    # Execute route submission with pinned backend="cagent_api"
    ok, succ_msg, badge, err = bridge.route_workspace_chat_submission(
        question="LSU là gì và gồm những bộ phận quang học chính nào?",
        evidence_items=[{"evidence_id": "EV-LSU-1", "title": "Tài liệu LSU", "text": "LSU là Laser Scanner Unit"}],
        packed_sources=(),
        conversation_id="CONV-9C730D76",
        notebook_id="NB-E35A7BEE",
        retrieval_applied=True,
        retrieved_sources=(),
        retrieval_summary="Đang tra cứu khối LSU.",
        current_keys=(),
        chat_history=(),
        user_raw_input="LSU là gì và gồm những bộ phận quang học chính nào?",
        backend="cagent_api",
        cagent_endpoint_url="https://kdtvn-ai.cmcts.vn/api/v1/prediction/fake",
    )

    assert ok is True
    assert badge is not None

    # Verify provenance data returned by route_workspace_chat_submission
    assert badge.get("fallback_used") is True
    assert badge.get("initial_backend") == "cagent_api"
    assert badge.get("operational_mode") == "local_grounded_fallback"
    assert badge.get("provider") == "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình"

    # Verify display layer condition
    assert should_show_fallback_notice(badge) is True

    # Verify exact warning notice string
    notice = format_fallback_notice(badge, locale="vi")
    assert notice == "Dịch vụ C-Agent không phản hồi trong thời gian chờ, đáp án hiện tại là bản tổng hợp cục bộ từ tài liệu."

    # Verify existing answer label is preserved intact (unmodified)
    from aios_habit.i18n import t
    assert t("local_fallback_note", locale="vi") == "Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình"


def test_cagent_external_mode_routes_to_cagent_with_zero_internal_sources(tmp_path, monkeypatch):
    """When backend='cagent_api' and ai_mode='external', C-Agent handles external QA with 0 internal sources."""
    import aios_habit.workspace_chat_store as store_mod
    import aios_habit.antigravity_bridge as bridge
    from aios_habit import cagent_api
    from aios_habit.cagent_api import CAgentResponse
    from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource

    monkeypatch.setattr(store_mod, "LOCAL_CHAT_DIR", tmp_path)
    monkeypatch.setattr(store_mod, "MESSAGES_FILE", tmp_path / "messages.jsonl")
    monkeypatch.setattr(store_mod, "TRACES_FILE", tmp_path / "traces.jsonl")
    monkeypatch.setattr(store_mod, "CONVERSATIONS_FILE", tmp_path / "conversations.jsonl")
    monkeypatch.setattr(store_mod, "SOURCE_SELECTIONS_FILE", tmp_path / "selections.jsonl")
    monkeypatch.setattr(store_mod, "EXTERNAL_AI_USAGE_FILE", tmp_path / "ext_usage.jsonl")
    store_mod.init_chat_store()

    captured = {}

    def _mock_cagent(endpoint_url="", *, system_prompt="", user_prompt="", **kwargs):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        return CAgentResponse(ok=True, text="Cảm biến quang học chuyển đổi ánh sáng thành tín hiệu điện.")

    monkeypatch.setattr(cagent_api, "call_cagent_prediction", _mock_cagent)

    secret_source = WorkspaceAIContextSource(
        source_id="SRC-SECRET-1",
        source_scope="notebook",
        source_type="text",
        title="Bí mật nội bộ công ty",
        privacy_label="cloud_allowed",
        text="MẬT_KHẨU_NỘI_BỘ_TUYỆT_MẬT_9999",
        included_chars=30,
        truncated=False,
    )

    ok, succ_msg, badge, err = bridge.route_workspace_chat_submission(
        question="Cảm biến quang học là gì?",
        evidence_items=[{"evidence_id": "EV-1", "title": "Bí mật nội bộ công ty", "text": "MẬT_KHẨU_NỘI_BỘ_TUYỆT_MẬT_9999"}],
        packed_sources=(secret_source,),
        conversation_id="CONV-EXT-CAGENT-01",
        notebook_id="NB-8354F455",
        retrieval_applied=False,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(),
        chat_history=(),
        user_raw_input="Cảm biến quang học là gì?",
        backend="cagent_api",
        cagent_endpoint_url="https://kdtvn-ai.cmcts.vn/api/v1/prediction/fake",
        ai_mode="external",
    )

    assert ok is True
    assert err is None
    assert badge is not None
    assert badge["provider"] == "C-AGENT API"
    assert badge["operational_mode"] == "external_ai"
    assert badge["ai_mode"] == "external"
    assert badge["source_count"] == 0
    assert badge["source_titles"] == []
    assert badge["evidence_items"] == []
    assert badge.get("fallback_used") is not True
    assert "MẬT_KHẨU_NỘI_BỘ_TUYỆT_MẬT_9999" not in captured["user_prompt"]
    assert "Bí mật nội bộ công ty" not in captured["user_prompt"]
