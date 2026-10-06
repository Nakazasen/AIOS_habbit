from __future__ import annotations

import json
from threading import Event
from urllib.error import HTTPError, URLError

from aios_habit.cagent_api import CAgentWorkspaceProviderClient, call_cagent_prediction


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_cagent_prediction_posts_single_question_and_reads_text(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _Response({"text": "Câu trả lời từ C-AGENT"})

    monkeypatch.setattr("aios_habit.cagent_api.urlopen", fake_urlopen)

    response = call_cagent_prediction(
        "https://cagent.example/api/v1/prediction/flow-id",
        system_prompt="Chỉ dùng nguồn được cung cấp.",
        user_prompt="CÂU HỎI: Xin chào",
    )

    assert response.ok is True
    assert response.text == "Câu trả lời từ C-AGENT"
    assert captured["url"] == "https://cagent.example/api/v1/prediction/flow-id"
    assert "Xin chào" in captured["body"]["question"]


def test_cagent_provider_does_not_accept_or_store_litellm_key(monkeypatch) -> None:
    monkeypatch.setattr(
        "aios_habit.cagent_api.call_cagent_prediction",
        lambda *_args, **_kwargs: type("Response", (), {"ok": True, "text": "OK"})(),
    )
    provider = CAgentWorkspaceProviderClient("https://cagent.example/api/v1/prediction/flow-id")

    assert provider.generate(system_prompt="system", user_prompt="user") == "OK"
    assert not hasattr(provider, "api_key")


def test_cagent_prediction_hides_http_error_detail(monkeypatch) -> None:
    def fake_urlopen(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise HTTPError("https://cagent.example/secret", 401, "Unauthorized", {}, None)

    monkeypatch.setattr("aios_habit.cagent_api.urlopen", fake_urlopen)

    response = call_cagent_prediction(
        "https://cagent.example/api/v1/prediction/flow-id",
        system_prompt="system",
        user_prompt="user",
    )

    assert response.ok is False
    assert response.error_message == "C-AGENT API trả về HTTP 401."


def test_cagent_prediction_retries_once_on_connection_error(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_urlopen(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        if calls["count"] == 1:
            raise URLError("connection refused")
        return _Response({"text": "Trả lời sau khi thử lại"})

    monkeypatch.setattr("aios_habit.cagent_api.urlopen", fake_urlopen)

    response = call_cagent_prediction(
        "https://cagent.example/api/v1/prediction/flow-id",
        system_prompt="system",
        user_prompt="user",
        retry_backoff_seconds=0.0,
    )

    assert response.ok is True
    assert response.text == "Trả lời sau khi thử lại"
    assert calls["count"] == 2


def test_cagent_prediction_reports_connection_loss_after_retry_budget(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_urlopen(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        raise URLError("connection refused")

    monkeypatch.setattr("aios_habit.cagent_api.urlopen", fake_urlopen)

    response = call_cagent_prediction(
        "https://cagent.example/api/v1/prediction/flow-id",
        system_prompt="system",
        user_prompt="user",
        retry_backoff_seconds=0.0,
    )

    assert response.ok is False
    assert calls["count"] == 2
    assert response.error_message == (
        "Không thể kết nối đến máy chủ C-Agent. Vui lòng kiểm tra lại mạng nội bộ công ty."
    )


def test_cagent_prediction_retries_server_errors_then_reports_busy(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_urlopen(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        raise HTTPError("https://cagent.example/x", 503, "Service Unavailable", {}, None)

    monkeypatch.setattr("aios_habit.cagent_api.urlopen", fake_urlopen)

    response = call_cagent_prediction(
        "https://cagent.example/api/v1/prediction/flow-id",
        system_prompt="system",
        user_prompt="user",
        retry_backoff_seconds=0.0,
    )

    assert response.ok is False
    assert calls["count"] == 2
    assert response.error_message == (
        "Dịch vụ C-Agent đang bận hoặc bảo trì tạm thời (HTTP 503). "
        "Vui lòng thử lại sau vài phút."
    )


def test_cagent_prediction_does_not_retry_client_errors(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_urlopen(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        raise HTTPError("https://cagent.example/x", 404, "Not Found", {}, None)

    monkeypatch.setattr("aios_habit.cagent_api.urlopen", fake_urlopen)

    response = call_cagent_prediction(
        "https://cagent.example/api/v1/prediction/flow-id",
        system_prompt="system",
        user_prompt="user",
        retry_backoff_seconds=0.0,
    )

    assert response.ok is False
    assert calls["count"] == 1
    assert response.error_message == "C-AGENT API trả về HTTP 404."


def test_cagent_prediction_timeout_message_is_vietnamese(monkeypatch) -> None:
    def fake_urlopen(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise TimeoutError("timed out")

    monkeypatch.setattr("aios_habit.cagent_api.urlopen", fake_urlopen)

    response = call_cagent_prediction(
        "https://cagent.example/api/v1/prediction/flow-id",
        system_prompt="system",
        user_prompt="user",
        retry_backoff_seconds=0.0,
    )

    assert response.ok is False
    assert response.error_message == (
        "Dịch vụ C-Agent phản hồi quá 60 giây. Vui lòng thử lại với câu hỏi ngắn gọn hơn."
    )


def test_cagent_prediction_invalid_payload_message(monkeypatch) -> None:
    class _InvalidPayloadResponse:
        def __enter__(self) -> "_InvalidPayloadResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"<html>not json</html>"

    monkeypatch.setattr("aios_habit.cagent_api.urlopen", lambda *_a, **_k: _InvalidPayloadResponse())

    response = call_cagent_prediction(
        "https://cagent.example/api/v1/prediction/flow-id",
        system_prompt="system",
        user_prompt="user",
    )

    assert response.ok is False
    assert response.error_message == (
        "Máy chủ C-Agent không trả về nội dung hợp lệ cho câu hỏi này. Vui lòng thử lại."
    )


def test_cagent_prediction_cancelled_before_sending(monkeypatch) -> None:
    cancellation_event = Event()
    cancellation_event.set()

    def fake_urlopen(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("không được gọi endpoint khi đã hủy")

    monkeypatch.setattr("aios_habit.cagent_api.urlopen", fake_urlopen)

    response = call_cagent_prediction(
        "https://cagent.example/api/v1/prediction/flow-id",
        system_prompt="system",
        user_prompt="user",
        cancellation_event=cancellation_event,
    )

    assert response.ok is False
    assert response.error_message == "Đã dừng yêu cầu trả lời từ AI."
