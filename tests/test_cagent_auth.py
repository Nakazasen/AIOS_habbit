from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from aios_habit.cagent_api import call_cagent_prediction
from aios_habit.cagent_auth import (
    CAgentAuthTokens,
    clear_session,
    decode_jwt_payload,
    get_auth_status,
    get_valid_access_token,
    load_session,
    login_cagent,
    refresh_cagent_token,
    save_session,
)


def _make_dummy_jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.signature"


class _MockResponse:
    def __init__(self, data: dict, status: int = 200) -> None:
        self._data = data
        self.status = status

    def __enter__(self) -> _MockResponse:
        return self

    def __exit__(self, *args) -> None:
        pass

    def read(self) -> bytes:
        return json.dumps(self._data).encode("utf-8")


@pytest.fixture(autouse=True)
def isolated_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session_file = tmp_path / "cagent_session.json"
    session_dir = tmp_path
    monkeypatch.setattr("aios_habit.cagent_auth.SESSION_FILE", session_file)
    monkeypatch.setattr("aios_habit.cagent_auth.SESSION_DIR", session_dir)
    monkeypatch.delenv("AIOS_CAGENT_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("AIOS_CAGENT_TOKEN", raising=False)
    monkeypatch.delenv("AIOS_CAGENT_API_KEY", raising=False)


def test_decode_jwt_payload() -> None:
    jwt = _make_dummy_jwt({"username": "test_user", "exp": 1800000000})
    payload = decode_jwt_payload(jwt)
    assert payload.get("username") == "test_user"
    assert payload.get("exp") == 1800000000

    assert decode_jwt_payload("invalid") == {}
    assert decode_jwt_payload("") == {}


def test_session_save_load_clear() -> None:
    tokens = CAgentAuthTokens(
        access_token="acc123",
        refresh_token="ref456",
        username="user1",
        expires_at=time.time() + 3600,
    )
    save_session(tokens)

    loaded = load_session()
    assert loaded is not None
    assert loaded.access_token == "acc123"
    assert loaded.refresh_token == "ref456"
    assert loaded.username == "user1"

    clear_session()
    assert load_session() is None


def test_login_cagent_success(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _make_dummy_jwt({"username": "tvn183660", "exp": time.time() + 3600})

    def fake_urlopen(request, timeout):
        assert "/api/v1/user/login" in request.full_url
        data = json.loads(request.data.decode())
        assert data["username"] == "tvn183660"
        assert data["password"] == "secret"
        return _MockResponse({"accessToken": token, "refreshToken": "ref_abc"})

    monkeypatch.setattr("aios_habit.cagent_auth.urlopen", fake_urlopen)

    ok, msg = login_cagent("tvn183660", "secret")
    assert ok is True
    assert "tvn183660" in msg

    session = load_session()
    assert session is not None
    assert session.access_token == token
    assert session.refresh_token == "ref_abc"
    assert session.username == "tvn183660"


def test_login_cagent_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout):
        raise HTTPError(
            request.full_url,
            401,
            "Unauthorized",
            {},
            _MockResponse({"message": "Sai mật khẩu", "remainingAttempts": 3}),  # type: ignore
        )

    monkeypatch.setattr("aios_habit.cagent_auth.urlopen", fake_urlopen)

    ok, msg = login_cagent("tvn183660", "wrong_pass")
    assert ok is False
    assert "Sai mật khẩu" in msg
    assert "Còn 3 lần thử" in msg


def test_refresh_cagent_token_success(monkeypatch: pytest.MonkeyPatch) -> None:
    old_acc = _make_dummy_jwt({"username": "tvn", "exp": time.time() - 100})
    save_session(CAgentAuthTokens(old_acc, "ref_123", "tvn", time.time() - 100))

    new_acc = _make_dummy_jwt({"username": "tvn", "exp": time.time() + 3600})

    def fake_urlopen(request, timeout):
        assert "/api/v1/user/refresh-token" in request.full_url
        data = json.loads(request.data.decode())
        assert data["refreshToken"] == "ref_123"
        return _MockResponse({"data": {"accessToken": new_acc, "refreshToken": "ref_456"}})

    monkeypatch.setattr("aios_habit.cagent_auth.urlopen", fake_urlopen)

    ok, msg = refresh_cagent_token()
    assert ok is True

    session = load_session()
    assert session is not None
    assert session.access_token == new_acc
    assert session.refresh_token == "ref_456"


def test_get_valid_access_token_auto_refreshes(monkeypatch: pytest.MonkeyPatch) -> None:
    # Expired token in session
    old_acc = _make_dummy_jwt({"username": "tvn", "exp": time.time() - 10})
    save_session(CAgentAuthTokens(old_acc, "ref_old", "tvn", time.time() - 10))

    new_acc = _make_dummy_jwt({"username": "tvn", "exp": time.time() + 3600})

    refreshed = False

    def fake_urlopen(request, timeout):
        nonlocal refreshed
        refreshed = True
        return _MockResponse({"accessToken": new_acc, "refreshToken": "ref_new"})

    monkeypatch.setattr("aios_habit.cagent_auth.urlopen", fake_urlopen)

    token = get_valid_access_token()
    assert refreshed is True
    assert token == new_acc


def test_get_auth_status() -> None:
    assert get_auth_status()["logged_in"] is False

    valid_token = _make_dummy_jwt({"username": "tvn", "exp": time.time() + 3600})
    save_session(CAgentAuthTokens(valid_token, "ref", "tvn", time.time() + 3600))

    status = get_auth_status()
    assert status["logged_in"] is True
    assert status["username"] == "tvn"


def test_call_cagent_prediction_uses_auth_session(monkeypatch: pytest.MonkeyPatch) -> None:
    valid_token = _make_dummy_jwt({"username": "tvn", "exp": time.time() + 3600})
    save_session(CAgentAuthTokens(valid_token, "ref", "tvn", time.time() + 3600))

    auth_header_sent = ""

    def fake_urlopen(request, timeout):
        nonlocal auth_header_sent
        auth_header_sent = request.headers.get("Authorization", "")
        return _MockResponse({"text": "Tra loi tu C-Agent"})

    monkeypatch.setattr("aios_habit.cagent_api.urlopen", fake_urlopen)

    res = call_cagent_prediction(
        "https://cagent.example/api/v1/prediction/flow",
        system_prompt="sys",
        user_prompt="usr",
    )
    assert res.ok is True
    assert auth_header_sent == f"Bearer {valid_token}"
