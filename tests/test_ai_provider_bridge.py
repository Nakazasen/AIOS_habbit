import json
import socket
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from aios_habit.ai_provider_bridge import (
    ProviderConfig,
    answer_with_provider,
    build_grounded_prompt,
    load_provider_config_from_env_or_session,
    test_provider_connection as check_provider_connection,
)


class _MockOpenAIHandler(BaseHTTPRequestHandler):
    payloads = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        self.__class__.payloads.append(payload)
        body = {
            "choices": [
                {
                    "message": {
                        "content": (
                            "Tóm tắt: câu trả lời từ AI cục bộ.\n"
                            "Nguồn đã dùng: 1. synthetic.txt"
                        )
                    }
                }
            ]
        }
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        return


@pytest.fixture
def mock_openai_server():
    _MockOpenAIHandler.payloads = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MockOpenAIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1/chat/completions"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _config(endpoint="http://127.0.0.1:9999/v1/chat/completions", locality="local"):
    return ProviderConfig(
        provider_type="openai_compatible_local",
        endpoint_url=endpoint,
        model_name="synthetic-local-model",
        locality=locality,
        timeout_seconds=1,
        enabled=True,
    )


def test_missing_provider_uses_deterministic_fallback():
    result = answer_with_provider(
        question="Synthetic question?",
        source_context="Synthetic context",
        config=None,
        deterministic_answer="Deterministic answer",
    )

    assert not result.ok
    assert result.used_fallback
    assert result.answer_text == "Deterministic answer"
    assert result.safety_status == "fallback_missing_config"


def test_local_only_context_is_blocked_for_cloud_locality():
    result = answer_with_provider(
        question="Synthetic question?",
        source_context="PRIVATE_SENTINEL",
        config=_config(locality="cloud"),
        deterministic_answer="Safe fallback",
        source_privacy="local_only",
    )

    assert not result.ok
    assert result.used_fallback
    assert result.answer_text == "Safe fallback"
    assert result.safety_status == "blocked_local_only_cloud"


def test_provider_timeout_uses_fallback(monkeypatch):
    monkeypatch.setattr(
        "aios_habit.ai_provider_bridge._post_chat",
        lambda *args, **kwargs: (_ for _ in ()).throw(socket.timeout()),
    )

    result = answer_with_provider(
        question="Synthetic question?",
        source_context="Synthetic context",
        config=_config(),
        deterministic_answer="Timeout fallback",
    )

    assert not result.ok
    assert result.used_fallback
    assert result.answer_text == "Timeout fallback"
    assert result.safety_status == "fallback_provider_error"


def test_provider_http_error_reports_sanitized_status(monkeypatch):
    monkeypatch.setattr(
        "aios_habit.ai_provider_bridge._post_chat",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            urllib.error.HTTPError("https://example.invalid", 401, "Unauthorized", {}, None)
        ),
    )

    result = answer_with_provider(
        question="Synthetic question?",
        source_context="Synthetic context",
        config=_config(locality="cloud"),
        deterministic_answer="HTTP fallback",
        source_privacy="cloud_allowed",
    )

    assert not result.ok
    assert result.used_fallback
    assert result.answer_text == "HTTP fallback"
    assert result.safety_status == "fallback_provider_error"
    assert "HTTP 401" in result.error_message
    assert "Unauthorized" not in result.error_message


def test_openai_compatible_mock_provider_returns_grounded_answer(mock_openai_server):
    config = _config(mock_openai_server)
    result = answer_with_provider(
        question="Synthetic production question?",
        source_context="Bounded synthetic source context",
        config=config,
        deterministic_answer="Deterministic draft",
        source_refs=[
            {"relative_path": "synthetic.txt", "chunk_id": "SYNTHETIC-1"}
        ],
    )

    assert result.ok
    assert not result.used_fallback
    assert result.model_name == "synthetic-local-model"
    assert "Nguồn đã dùng" in result.answer_text
    assert _MockOpenAIHandler.payloads[-1]["model"] == "synthetic-local-model"
    sent_prompt = _MockOpenAIHandler.payloads[-1]["messages"][-1]["content"]
    assert "Synthetic production question?" in sent_prompt
    assert "synthetic.txt" in sent_prompt


def test_provider_connection_uses_local_mock(mock_openai_server):
    result = check_provider_connection(_config(mock_openai_server))

    assert result.ok
    assert not result.used_fallback
    assert result.safety_status == "local_provider_ok"


def test_grounded_prompt_has_rules_refs_and_bounded_context():
    prompt = build_grounded_prompt(
        question="Câu hỏi synthetic?",
        source_refs=[{"relative_path": "source.txt", "chunk_id": "CHUNK-1"}],
        deterministic_answer="Bản nháp deterministic",
        source_context="X" * 5000,
        max_context_chars=1000,
    )

    assert "Câu hỏi synthetic?" in prompt
    assert "source.txt" in prompt
    assert "CHUNK-1" in prompt
    assert "chưa đủ bằng chứng" in prompt
    assert "Trả lời bằng tiếng Việt" in prompt
    assert "[ĐÃ GIỚI HẠN NGỮ CẢNH CỤC BỘ]" in prompt


def test_session_config_is_transient_and_overrides_environment(monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_AI_ENDPOINT", "http://127.0.0.1:1111/v1/chat/completions")
    monkeypatch.setenv("AIOS_LOCAL_AI_MODEL", "env-model")

    config = load_provider_config_from_env_or_session(
        {
            "local_ai_endpoint": "http://127.0.0.1:2222/v1/chat/completions",
            "local_ai_model": "session-model",
            "local_ai_timeout": 12,
        }
    )

    assert config.endpoint_url.endswith(":2222/v1/chat/completions")
    assert config.model_name == "session-model"
    assert config.timeout_seconds == 12
    assert config.enabled
