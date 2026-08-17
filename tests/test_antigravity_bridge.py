import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import pytest

from aios_habit.antigravity_bridge import (
    AntigravityBridgeResponse,
    call_antigravity_bridge,
    is_antigravity_bridge_available,
    process_pending_ide_handoffs,
)
from aios_habit.ai_provider_bridge import ProviderConfig, answer_with_provider
from aios_habit.brain_gateway import SanitizedRouterPayload, SanitizedSourcePayload
from aios_habit.workspace_chat_router_adapter import generate_answer_via_router_detailed


class MockAntigravityServer(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "provider": "antigravity_ide_brain"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path in ("/v1/chat/completions", "/chat/completions"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            messages = data.get("messages", [])
            user_msg = ""
            for m in messages:
                if m.get("role") == "user":
                    user_msg = m.get("content", "")

            response = {
                "id": "chatcmpl-mock-123",
                "object": "chat.completion",
                "model": "antigravity-brain-pro",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": f"Antigravity Answer for: {user_msg[:40]}",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"total_tokens": 42},
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture
def mock_bridge_server():
    server = HTTPServer(("127.0.0.1", 0), MockAntigravityServer)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    health_url = f"http://127.0.0.1:{port}/health"
    completions_url = f"http://127.0.0.1:{port}/v1/chat/completions"
    yield health_url, completions_url
    server.shutdown()
    server.server_close()


def test_is_antigravity_bridge_available(mock_bridge_server):
    health_url, _ = mock_bridge_server
    assert is_antigravity_bridge_available(health_url=health_url) is True
    assert is_antigravity_bridge_available(health_url="http://127.0.0.1:59999/health", timeout_seconds=0.1) is False


def test_call_antigravity_bridge_success(mock_bridge_server):
    _, completions_url = mock_bridge_server
    res = call_antigravity_bridge(
        question="Giải thích kiến trúc RAG v2",
        system_prompt="Bạn là chuyên gia",
        context_text="Nội dung tài liệu...",
        endpoint_url=completions_url,
    )
    assert res.ok is True
    assert "Antigravity Answer" in res.answer_text
    assert res.tokens_used == 42
    assert res.model == "antigravity-brain-pro"


def test_call_antigravity_bridge_failure():
    res = call_antigravity_bridge(
        question="Test offline",
        endpoint_url="http://127.0.0.1:59999/v1/chat/completions",
        timeout_seconds=0.2,
    )
    assert res.ok is False
    assert res.answer_text == ""
    assert res.error_message != ""


def test_process_pending_ide_handoffs(tmp_path, mock_bridge_server):
    _, completions_url = mock_bridge_server
    handoff_root = tmp_path / "ide_handoff"
    req_id = "REQ_TEST_001"
    outbox_dir = handoff_root / "outbox" / req_id
    outbox_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "request_id": req_id,
        "created_at": "2026-08-15T12:00:00",
        "case_id": "case_1",
        "question": "Kiểm tra lô hàng lỗi",
        "bundle_scope": "active_case_all",
        "allowed_source_ids": ["EVD-1", "EVD-2"],
    }
    (outbox_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (outbox_dir / "prompt_for_antigravity.md").write_text("Prompt for IDE", encoding="utf-8")
    (outbox_dir / "evidence_full.md").write_text("Evidence text", encoding="utf-8")

    processed = process_pending_ide_handoffs(base_dir=handoff_root, endpoint_url=completions_url)
    assert processed == 1

    inbox_resp = handoff_root / "inbox" / req_id / "response.json"
    assert inbox_resp.exists()
    resp_data = json.loads(inbox_resp.read_text(encoding="utf-8"))
    assert resp_data["request_id"] == req_id
    assert "Antigravity Answer" in resp_data["answer_markdown"]
    assert resp_data["confidence"] == "high"


def test_ai_provider_bridge_with_antigravity(mock_bridge_server, monkeypatch):
    health_url, completions_url = mock_bridge_server
    monkeypatch.setattr("aios_habit.antigravity_bridge.DEFAULT_ANTIGRAVITY_HEALTH_URL", health_url)
    monkeypatch.setattr("aios_habit.antigravity_bridge.DEFAULT_ANTIGRAVITY_ENDPOINT", completions_url)

    cfg = ProviderConfig(
        provider_type="antigravity_ide_brain",
        endpoint_url=completions_url,
        model_name="antigravity-brain-pro",
        locality="local",
        enabled=True,
    )
    res = answer_with_provider(
        question="Hỏi qua Antigravity",
        source_context="Context...",
        config=cfg,
        deterministic_answer="Fallback",
        source_privacy="local_only",
    )
    assert res.ok is True
    assert "Antigravity Answer" in res.answer_text
    assert res.provider_name == "antigravity_ide_brain"
