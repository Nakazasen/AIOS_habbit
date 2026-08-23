"""Tests for Workspace Chat Context Compression via Antigravity Direct."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
import streamlit as st
import aios_habit.workspace_chat_store as store

from aios_habit.antigravity_bridge import (
    AntigravityHealthStatus,
    AntigravityBridgeResponse,
    FSM_DIRECT_READY,
    FSM_HANDOFF_READY,
    compress_conversation_context_direct,
    call_antigravity_bridge,
    route_workspace_chat_submission,
)
from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
    ChatMessage,
    NotebookSource,
    TemporaryConversationSource,
    SOURCE_SCOPE_NOTEBOOK,
    SOURCE_SCOPE_TEMPORARY,
)
from aios_habit.workspace_chat_store import (
    save_notebook,
    save_conversation,
    load_conversation,
    save_message,
    load_messages,
    save_notebook_source,
    load_notebook_sources,
    save_temporary_source,
    load_temporary_sources,
    set_source_enabled,
    load_conversation_source_selections,
)
from aios_habit.workspace_chat_app import (
    request_compress_conversation_callback,
    cancel_compress_conversation_callback,
    confirm_compress_conversation_callback,
)


@pytest.fixture(autouse=True)
def setup_test_store(tmp_path, monkeypatch):
    """Set up clean isolated storage and Streamlit session state for testing."""
    test_dir = tmp_path / "workspace_chat"
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(store, "NOTEBOOKS_FILE", test_dir / "notebooks.jsonl")
    monkeypatch.setattr(store, "CONVERSATIONS_FILE", test_dir / "conversations.jsonl")
    monkeypatch.setattr(store, "MESSAGES_FILE", test_dir / "messages.jsonl")
    monkeypatch.setattr(store, "TEMPORARY_SOURCES_FILE", test_dir / "temporary_sources.jsonl")
    monkeypatch.setattr(store, "NOTEBOOK_SOURCES_FILE", test_dir / "notebook_sources.jsonl")
    monkeypatch.setattr(store, "SOURCE_SELECTIONS_FILE", test_dir / "conversation_source_selections.jsonl")
    store.init_chat_store()
    st.session_state.clear()
    yield test_dir
    st.session_state.clear()


def test_compression_request_and_cancel_callbacks():
    """Clicking compress sets pending state; cancel clears it without any changes."""
    conv_id = "CONV-TEST-REQ"
    request_compress_conversation_callback(conv_id)
    assert st.session_state.get("wsc_pending_compress_conversation_id") == conv_id

    cancel_compress_conversation_callback(conv_id)
    assert st.session_state.get("wsc_pending_compress_conversation_id") is None


def test_confirm_compression_locked_fails_if_not_pending():
    """Calling confirm without user request state is strictly blocked at logic level."""
    nb = DocumentNotebook(id="NB-1", title="Sổ A")
    save_notebook(nb)
    conv = WorkspaceConversation(id="CONV-1", notebook_id="NB-1", title="Chat 1")
    save_conversation(conv)
    save_message(ChatMessage(id="M1", conversation_id="CONV-1", role="user", content="Câu hỏi"))

    health = AntigravityHealthStatus(status=FSM_DIRECT_READY, mode="direct", capabilities=["direct_chat"])

    # 1. No pending state set
    st.session_state.wsc_pending_compress_conversation_id = None
    success = confirm_compress_conversation_callback("NB-1", "CONV-1", health_status=health)
    assert success is False
    assert "chưa được xác nhận" in st.session_state.get("wsc_action_error", "")

    # 2. Pending state set for a different conversation
    st.session_state.wsc_pending_compress_conversation_id = "CONV-OTHER"
    success2 = confirm_compress_conversation_callback("NB-1", "CONV-1", health_status=health)
    assert success2 is False
    assert "chưa được xác nhận" in st.session_state.get("wsc_action_error", "")


def test_compress_context_direct_helper_success(monkeypatch):
    """compress_conversation_context_direct calls call_antigravity_bridge with prompt and history."""
    captured_calls = []

    def fake_bridge(question, system_prompt="", context_text="", **kwargs):
        captured_calls.append({
            "question": question,
            "system_prompt": system_prompt,
            "kwargs": kwargs,
        })
        return AntigravityBridgeResponse(
            ok=True,
            answer_text="Tóm tắt: Hệ thống đã kiểm thử BGE-M3 thành công.",
            model="antigravity-brain-pro",
        )

    monkeypatch.setattr("aios_habit.antigravity_bridge.call_antigravity_bridge", fake_bridge)

    health = AntigravityHealthStatus(
        status=FSM_DIRECT_READY,
        mode="direct",
        capabilities=["direct_chat"],
    )

    history = (
        {"role": "user", "content": "Kiểm tra BGE-M3 trên CPU"},
        {"role": "assistant", "content": "BGE-M3 hoạt động ổn định trên CPU với RRF."},
    )

    ok, summary, err = compress_conversation_context_direct(
        history,
        health_status=health,
    )

    assert ok is True
    assert summary == "Tóm tắt: Hệ thống đã kiểm thử BGE-M3 thành công."
    assert err is None
    assert len(captured_calls) == 1
    assert "Kiểm tra BGE-M3 trên CPU" in captured_calls[0]["question"]


def test_compress_context_direct_helper_fails_closed_when_not_direct_ready(monkeypatch):
    """If bridge is not direct_ready, compression immediately fails closed with zero bridge calls."""
    captured_calls = []
    monkeypatch.setattr("aios_habit.antigravity_bridge.call_antigravity_bridge", lambda *a, **kw: captured_calls.append(1))

    health = AntigravityHealthStatus(
        status=FSM_HANDOFF_READY,
        mode="handoff",
        capabilities=["handoff_bundle"],
    )

    ok, summary, err = compress_conversation_context_direct(
        ({"role": "user", "content": "Tin nhắn test"},),
        health_status=health,
    )

    assert ok is False
    assert summary == ""
    assert err is not None
    assert "chưa sẵn sàng" in err
    assert len(captured_calls) == 0


def test_confirm_compression_success_inherits_notebook_sources_and_ignores_temp_sources(monkeypatch):
    """On success: creates new conversation with summary, inherits notebook selections, ignores temp sources."""
    nb = DocumentNotebook(id="NB-1", title="Sổ dự án A")
    save_notebook(nb)

    conv = WorkspaceConversation(
        id="CONV-ORIG",
        notebook_id="NB-1",
        title="Cuộc trò chuyện ban đầu",
        search_preference="deep",
    )
    save_conversation(conv)

    msg1 = ChatMessage(id="MSG-1", conversation_id="CONV-ORIG", role="user", content="Cấu hình BGE-M3 thế nào?")
    msg2 = ChatMessage(id="MSG-2", conversation_id="CONV-ORIG", role="assistant", content="Dùng revision 5617a9f.")
    save_message(msg1)
    save_message(msg2)

    # Notebook sources (1 enabled, 1 disabled)
    ns1 = NotebookSource(id="NBS-1", notebook_id="NB-1", title="Tài liệu kiến trúc", source_type="plain_text", content_preview="...", content_text="...")
    ns2 = NotebookSource(id="NBS-2", notebook_id="NB-1", title="Ghi chú nháp", source_type="plain_text", content_preview="...", content_text="...")
    save_notebook_source(ns1)
    save_notebook_source(ns2)
    set_source_enabled("CONV-ORIG", SOURCE_SCOPE_NOTEBOOK, "NBS-1", True)
    set_source_enabled("CONV-ORIG", SOURCE_SCOPE_NOTEBOOK, "NBS-2", False)

    # Temporary source in old conversation
    ts1 = TemporaryConversationSource(id="TMS-1", conversation_id="CONV-ORIG", source_type="plain_text", title="Nguồn tạm cũ", content_preview="...", content_text="...")
    save_temporary_source(ts1)
    set_source_enabled("CONV-ORIG", SOURCE_SCOPE_TEMPORARY, "TMS-1", True)

    health = AntigravityHealthStatus(status=FSM_DIRECT_READY, mode="direct", capabilities=["direct_chat"])

    def fake_compress(history, health_status=None, **kwargs):
        return (True, "Tóm tắt: Đã thống nhất cấu hình BGE-M3 revision 5617a9f.", None)

    monkeypatch.setattr("aios_habit.antigravity_bridge.compress_conversation_context_direct", fake_compress)

    # User requests compression first
    request_compress_conversation_callback("CONV-ORIG")
    assert st.session_state.get("wsc_pending_compress_conversation_id") == "CONV-ORIG"

    # Confirm compression
    success = confirm_compress_conversation_callback("NB-1", "CONV-ORIG", health_status=health)
    assert success is True

    new_conv_id = st.session_state.get("wsc_active_conversation_id")
    assert new_conv_id is not None
    assert new_conv_id != "CONV-ORIG"

    new_conv = load_conversation(new_conv_id)
    assert new_conv is not None
    assert new_conv.title == "Tiếp tục: Cuộc trò chuyện ban đầu"
    assert new_conv.compressed_memory == "Tóm tắt: Đã thống nhất cấu hình BGE-M3 revision 5617a9f."
    assert new_conv.search_preference == "deep"

    # Old conversation and messages remain intact
    old_conv = load_conversation("CONV-ORIG")
    assert old_conv is not None
    assert len(load_messages("CONV-ORIG")) == 2

    # Inherited notebook source selections in new conv
    new_selections = load_conversation_source_selections(new_conv_id)
    sel_map = {(s.source_scope, s.source_id): s.enabled for s in new_selections}
    assert sel_map.get((SOURCE_SCOPE_NOTEBOOK, "NBS-1")) is True
    assert sel_map.get((SOURCE_SCOPE_NOTEBOOK, "NBS-2")) is False

    # Temporary sources are NOT copied to new conv
    new_temp_sources = load_temporary_sources(new_conv_id)
    assert len(new_temp_sources) == 0
    assert (SOURCE_SCOPE_TEMPORARY, "TMS-1") not in sel_map


def test_confirm_compression_bridge_error_keeps_old_chat_active_and_sets_error(monkeypatch):
    """When bridge returns error or empty summary: old chat remains active, error is displayed."""
    nb = DocumentNotebook(id="NB-1", title="Sổ A")
    save_notebook(nb)
    conv = WorkspaceConversation(id="CONV-1", notebook_id="NB-1", title="Chat 1")
    save_conversation(conv)
    save_message(ChatMessage(id="M1", conversation_id="CONV-1", role="user", content="Câu hỏi"))

    st.session_state.wsc_active_conversation_id = "CONV-1"

    health = AntigravityHealthStatus(status=FSM_DIRECT_READY, mode="direct", capabilities=["direct_chat"])

    # 1. Bridge returns error
    monkeypatch.setattr(
        "aios_habit.antigravity_bridge.compress_conversation_context_direct",
        lambda history, health_status=None, **kw: (False, "", "Lỗi kết nối Antigravity Direct (Timeout)"),
    )

    request_compress_conversation_callback("CONV-1")
    success = confirm_compress_conversation_callback("NB-1", "CONV-1", health_status=health)
    assert success is False
    assert st.session_state.get("wsc_action_error") == "Lỗi kết nối Antigravity Direct (Timeout)"
    # Old chat remains the active conversation
    assert st.session_state.get("wsc_active_conversation_id") == "CONV-1"
    assert st.session_state.get("wsc_pending_compress_conversation_id") is None

    # 2. Bridge returns empty summary
    monkeypatch.setattr(
        "aios_habit.antigravity_bridge.compress_conversation_context_direct",
        lambda history, health_status=None, **kw: (True, "   ", None),
    )

    request_compress_conversation_callback("CONV-1")
    success2 = confirm_compress_conversation_callback("NB-1", "CONV-1", health_status=health)
    assert success2 is False
    assert "rỗng" in st.session_state.get("wsc_action_error", "")
    assert st.session_state.get("wsc_active_conversation_id") == "CONV-1"


def test_direct_submission_payload_contains_compressed_memory_and_rag_evidence(monkeypatch):
    """When querying in a new chat with compressed_memory, the Direct payload includes system memory + RAG."""
    sent_payloads = []

    def mock_urlopen(req, timeout=None):
        req_data = json.loads(req.data.decode("utf-8"))
        sent_payloads.append(req_data)

        class MockResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                return json.dumps({
                    "choices": [{"message": {"content": "Câu trả lời kết hợp tóm tắt và tài liệu mới."}}],
                    "model": "antigravity-brain-pro",
                    "usage": {"total_tokens": 50},
                }).encode("utf-8")

        return MockResponse()

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    health = AntigravityHealthStatus(status=FSM_DIRECT_READY, mode="direct", capabilities=["direct_chat"])

    chat_history = (
        {"role": "system", "content": "Tóm tắt: Phiên trước đã thảo luận về BGE-M3."},
    )

    evidence_items = [
        {"title": "Doc_1.txt", "text": "Nội dung Doc 1 về tham số batch_size=1."},
    ]

    ok, msg, badge, err = route_workspace_chat_submission(
        question="Tham số tối ưu là gì?",
        evidence_items=evidence_items,
        packed_sources=(),
        conversation_id="CONV-NEW",
        notebook_id="NB-1",
        retrieval_applied=True,
        retrieved_sources=(),
        retrieval_summary="Đã dùng 1 đoạn liên quan",
        current_keys=(),
        chat_history=chat_history,
        user_raw_input="Tham số tối ưu là gì?",
        health_status=health,
    )

    assert ok is True
    assert err is None
    assert len(sent_payloads) == 1

    payload = sent_payloads[0]
    messages = payload["messages"]
    assert len(messages) >= 2

    # System message from compressed_memory and/or language instruction
    assert any(m["role"] == "system" and "Tóm tắt: Phiên trước đã thảo luận về BGE-M3." in m["content"] for m in messages)

    # User question containing RAG evidence
    user_msg = next((m for m in messages if m["role"] == "user"), None)
    assert user_msg is not None
    assert "Tham số tối ưu là gì?" in user_msg["content"]
    assert "Doc_1.txt" in user_msg["content"]
    assert "batch_size=1" in user_msg["content"]


def test_zero_router_calls_during_compression(monkeypatch):
    """Ensure Smart Router / generate_answer_via_router is never invoked during compression."""
    router_called = []

    def mock_router(*args, **kwargs):
        router_called.append(1)
        raise RuntimeError("Router should not be called!")

    monkeypatch.setattr("aios_habit.workspace_chat_router_adapter.generate_answer_via_router", mock_router, raising=False)
    monkeypatch.setattr("aios_habit.query_planner.generate_memory_compression", mock_router, raising=False)

    nb = DocumentNotebook(id="NB-1", title="Sổ A")
    save_notebook(nb)
    conv = WorkspaceConversation(id="CONV-1", notebook_id="NB-1", title="Chat 1")
    save_conversation(conv)
    save_message(ChatMessage(id="M1", conversation_id="CONV-1", role="user", content="Nội dung test"))

    health = AntigravityHealthStatus(status=FSM_DIRECT_READY, mode="direct", capabilities=["direct_chat"])

    monkeypatch.setattr(
        "aios_habit.antigravity_bridge.call_antigravity_bridge",
        lambda *a, **kw: AntigravityBridgeResponse(ok=True, answer_text="Tóm tắt hoàn hảo.", model="direct-model"),
    )

    request_compress_conversation_callback("CONV-1")
    success = confirm_compress_conversation_callback("NB-1", "CONV-1", health_status=health)
    assert success is True
    assert len(router_called) == 0


def test_e2e_full_chain_with_real_http_server(monkeypatch):
    """End-to-End test with real HTTP server:

    request -> confirm -> compress via HTTP -> new chat created -> ask question -> Direct receives memory + RAG.
    """
    received_requests = []

    class MockDirectSidecarHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            if self.path == "/health":
                resp = {
                    "status": "direct_ready",
                    "mode": "direct",
                    "capabilities": ["direct_chat", "gemini_web_direct"],
                    "reason": "",
                }
                body = json.dumps(resp).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            if self.path == "/v1/chat/completions":
                length = int(self.headers.get("Content-Length", 0))
                body_bytes = self.rfile.read(length)
                payload = json.loads(body_bytes.decode("utf-8"))
                received_requests.append(payload)

                messages = payload.get("messages", [])
                # If compression prompt (contains the full history divider):
                if any("TOÀN BỘ LỊCH SỬ HỘI THOẠI" in str(m.get("content", "")) for m in messages):
                    reply_content = "Tóm tắt: Kiến trúc RAG v2 với BGE-M3 hoạt động ổn định."
                else:
                    # Regular QA turn with inherited memory + question + RAG:
                    reply_content = "AI Direct: Tham số tối ưu cho BGE-M3 là batch_size=1 trên CPU."

                resp = {
                    "id": "chatcmpl-e2e-test",
                    "object": "chat.completion",
                    "created": 1234567890,
                    "model": "antigravity-brain-pro",
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": reply_content},
                        "finish_reason": "stop",
                    }],
                    "usage": {"total_tokens": 42},
                }
                data = json.dumps(resp).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), MockDirectSidecarHandler)
    server_port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    completions_url = f"http://127.0.0.1:{server_port}/v1/chat/completions"
    health_url = f"http://127.0.0.1:{server_port}/health"

    # Set default bridge endpoints to test server
    monkeypatch.setattr("aios_habit.antigravity_bridge.DEFAULT_ANTIGRAVITY_ENDPOINT", completions_url)
    monkeypatch.setattr("aios_habit.antigravity_bridge.DEFAULT_ANTIGRAVITY_HEALTH_URL", health_url)

    try:
        # Step 1: Create initial conversation with messages & sources
        nb = DocumentNotebook(id="NB-E2E", title="Sổ E2E")
        save_notebook(nb)
        conv = WorkspaceConversation(id="CONV-E2E-1", notebook_id="NB-E2E", title="Thảo luận BGE-M3", search_preference="auto")
        save_conversation(conv)
        save_message(ChatMessage(id="M1", conversation_id="CONV-E2E-1", role="user", content="Làm sao để chạy BGE-M3?"))
        save_message(ChatMessage(id="M2", conversation_id="CONV-E2E-1", role="assistant", content="Dùng model revision 5617a9f."))

        ns1 = NotebookSource(id="NBS-1", notebook_id="NB-E2E", title="Tài liệu BGE-M3", source_type="plain_text", content_preview="...", content_text="...")
        save_notebook_source(ns1)
        set_source_enabled("CONV-E2E-1", SOURCE_SCOPE_NOTEBOOK, "NBS-1", True)

        ts1 = TemporaryConversationSource(id="TMS-1", conversation_id="CONV-E2E-1", source_type="plain_text", title="File tạm", content_preview="...", content_text="...")
        save_temporary_source(ts1)
        set_source_enabled("CONV-E2E-1", SOURCE_SCOPE_TEMPORARY, "TMS-1", True)

        st.session_state.wsc_active_conversation_id = "CONV-E2E-1"

        # Step 2: Request compression
        request_compress_conversation_callback("CONV-E2E-1")
        assert st.session_state.wsc_pending_compress_conversation_id == "CONV-E2E-1"

        # Step 3: Confirm compression (talking to real HTTP server)
        health = AntigravityHealthStatus(status=FSM_DIRECT_READY, mode="direct", capabilities=["direct_chat"])
        success = confirm_compress_conversation_callback(
            "NB-E2E",
            "CONV-E2E-1",
            health_status=health,
            endpoint_url=completions_url,
        )
        assert success is True

        new_conv_id = st.session_state.wsc_active_conversation_id
        assert new_conv_id is not None
        assert new_conv_id != "CONV-E2E-1"

        new_conv = load_conversation(new_conv_id)
        assert new_conv is not None
        assert new_conv.compressed_memory == "Tóm tắt: Kiến trúc RAG v2 với BGE-M3 hoạt động ổn định."

        # Verify first HTTP request (compression request) received by server
        assert len(received_requests) == 1
        comp_req = received_requests[0]
        assert any("Làm sao để chạy BGE-M3?" in m.get("content", "") for m in comp_req["messages"])

        # Step 4: Ask next question in the new conversation
        evidence_items = [{"title": "Tài liệu BGE-M3", "text": "Khuyến nghị CPU: batch_size=1"}]
        chat_history = (
            {"role": "system", "content": new_conv.compressed_memory},
        )

        ok, msg, badge, err = route_workspace_chat_submission(
            question="Cấu hình tối ưu là gì?",
            evidence_items=evidence_items,
            packed_sources=(),
            conversation_id=new_conv.id,
            notebook_id="NB-E2E",
            retrieval_applied=True,
            retrieved_sources=(),
            retrieval_summary="Đã dùng 1 nguồn",
            current_keys=(),
            chat_history=chat_history,
            user_raw_input="Cấu hình tối ưu là gì?",
            health_status=health,
            endpoint_url=completions_url,
        )

        assert ok is True
        assert err is None
        assert badge is not None
        assert badge["operational_mode"] == "direct"
        assert badge["ai_source"] == "Antigravity IDE"

        # Verify second HTTP request received by server
        assert len(received_requests) == 2
        qa_req = received_requests[1]
        qa_messages = qa_req["messages"]
        assert len(qa_messages) >= 2
        assert any(m["role"] == "system" and "Tóm tắt: Kiến trúc RAG v2 với BGE-M3 hoạt động ổn định." in m["content"] for m in qa_messages)
        user_qa_msg = next((m for m in qa_messages if m["role"] == "user"), None)
        assert user_qa_msg is not None
        assert "Cấu hình tối ưu là gì?" in user_qa_msg["content"]
        assert "Tài liệu BGE-M3" in user_qa_msg["content"]

        # Verify messages saved to new conversation
        saved_new_msgs = load_messages(new_conv.id)
        assert len(saved_new_msgs) == 2
        assert saved_new_msgs[0].role == "user"
        assert saved_new_msgs[0].content == "Cấu hình tối ưu là gì?"
        assert saved_new_msgs[1].role == "assistant"
        assert "batch_size=1" in saved_new_msgs[1].content

    finally:
        server.shutdown()
        server.server_close()
