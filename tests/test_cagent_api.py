from __future__ import annotations

import json
from urllib.error import HTTPError

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
