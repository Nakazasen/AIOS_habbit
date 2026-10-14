"""Authentication and session lifecycle manager for C-Agent (Flowise / Agent Studio).

Provides seamless single-login and automatic background token refresh.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)

DEFAULT_CAGENT_BASE_URL = "https://kdtvn-ai.cmcts.vn"
SESSION_DIR = Path.home() / ".aios"
SESSION_FILE = SESSION_DIR / "cagent_session.json"
MARGIN_SECONDS_BEFORE_REFRESH = 180.0  # Refresh 3 minutes before expiration


@dataclass(frozen=True)
class CAgentAuthTokens:
    access_token: str
    refresh_token: str
    username: str = ""
    expires_at: float = 0.0


def _extract_base_url(endpoint_or_base: str = "") -> str:
    url = str(endpoint_or_base or os.environ.get("AIOS_CAGENT_API_URL", "") or DEFAULT_CAGENT_BASE_URL).strip()
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return DEFAULT_CAGENT_BASE_URL


def decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode JWT payload without verifying signature (used to inspect exp & username)."""
    parts = str(token or "").split(".")
    if len(parts) < 2:
        return {}
    payload_b64 = parts[1]
    # Add base64 padding if missing
    padding = len(payload_b64) % 4
    if padding:
        payload_b64 += "=" * (4 - padding)
    try:
        decoded_bytes = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
        data = json.loads(decoded_bytes.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        LOGGER.debug("Failed to decode JWT payload: %s", exc)
        return {}


def load_session() -> CAgentAuthTokens | None:
    """Load persisted C-Agent auth session from user profile."""
    if not SESSION_FILE.is_file():
        return None
    try:
        content = SESSION_FILE.read_text(encoding="utf-8")
        data = json.loads(content)
        access_token = str(data.get("access_token", "")).strip()
        refresh_token = str(data.get("refresh_token", "")).strip()
        username = str(data.get("username", "")).strip()
        expires_at = float(data.get("expires_at", 0.0))
        if not access_token:
            return None
        return CAgentAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            username=username,
            expires_at=expires_at,
        )
    except Exception as exc:
        LOGGER.warning("Could not read C-Agent session file: %s", exc)
        return None


def save_session(tokens: CAgentAuthTokens) -> None:
    """Persist C-Agent session to disk."""
    try:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        data = asdict(tokens)
        SESSION_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        LOGGER.warning("Failed to save C-Agent session: %s", exc)


def clear_session() -> None:
    """Remove persisted C-Agent session file."""
    try:
        if SESSION_FILE.is_file():
            SESSION_FILE.unlink(missing_ok=True)
    except Exception as exc:
        LOGGER.warning("Failed to clear C-Agent session: %s", exc)


def login_cagent(
    username: str,
    password: str,
    base_url: str = "",
    timeout_seconds: int = 15,
) -> tuple[bool, str]:
    """Authenticate with C-Agent server and persist the returned session."""
    user = str(username or "").strip()
    pwd = str(password or "").strip()
    if not user or not pwd:
        return False, "Vui lòng nhập tên đăng nhập và mật khẩu."

    root_url = _extract_base_url(base_url)
    login_endpoint = f"{root_url}/api/v1/user/login"
    payload = json.dumps({"username": user, "password": pwd}, ensure_ascii=False).encode("utf-8")

    req = Request(
        login_endpoint,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
            res_data = json.loads(raw)
    except HTTPError as err:
        try:
            err_raw = err.read().decode("utf-8", errors="replace")
            err_json = json.loads(err_raw)
            msg = err_json.get("message") or err_json.get("error") or f"Lỗi HTTP {err.code}"
            attempts = err_json.get("remainingAttempts")
            if attempts is not None:
                msg = f"{msg} (Còn {attempts} lần thử)"
            return False, str(msg)
        except Exception:
            return False, f"Đăng nhập thất bại (HTTP {err.code})."
    except URLError as err:
        return False, f"Không thể kết nối đến máy chủ C-Agent: {err.reason}"
    except Exception as err:
        return False, f"Lỗi đăng nhập C-Agent: {err}"

    if not isinstance(res_data, dict):
        return False, "Phản hồi từ máy chủ không hợp lệ."

    # Look for accessToken and refreshToken
    access_token = str(res_data.get("accessToken", "") or res_data.get("access_token", "")).strip()
    refresh_token = str(res_data.get("refreshToken", "") or res_data.get("refresh_token", "")).strip()

    # Sometimes nested in "data" object
    if not access_token and isinstance(res_data.get("data"), dict):
        inner = res_data["data"]
        access_token = str(inner.get("accessToken", "") or inner.get("access_token", "")).strip()
        refresh_token = str(inner.get("refreshToken", "") or inner.get("refresh_token", "")).strip()

    if not access_token:
        msg = res_data.get("message") or "Không nhận được token xác thực từ máy chủ."
        return False, str(msg)

    # Determine expiration time from JWT
    claims = decode_jwt_payload(access_token)
    exp = float(claims.get("exp", 0.0))
    if not exp:
        exp = time.time() + 3600.0  # Default 1 hour if exp not in claims

    extracted_user = str(claims.get("username", "") or user)

    tokens = CAgentAuthTokens(
        access_token=access_token,
        refresh_token=refresh_token,
        username=extracted_user,
        expires_at=exp,
    )
    save_session(tokens)
    return True, f"Đăng nhập thành công tài khoản {extracted_user}."


def refresh_cagent_token(
    base_url: str = "",
    timeout_seconds: int = 15,
) -> tuple[bool, str]:
    """Use the stored refresh token to obtain a new access token."""
    session = load_session()
    if not session or not session.refresh_token:
        return False, "Chưa có phiên hoặc Refresh Token hợp lệ."

    root_url = _extract_base_url(base_url)
    refresh_endpoint = f"{root_url}/api/v1/user/refresh-token"
    payload = json.dumps({"refreshToken": session.refresh_token}, ensure_ascii=False).encode("utf-8")

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if session.access_token:
        headers["Authorization"] = f"Bearer {session.access_token}"

    req = Request(refresh_endpoint, data=payload, method="POST", headers=headers)

    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
            res_data = json.loads(raw)
    except HTTPError as err:
        LOGGER.warning("C-Agent token refresh HTTP %s", err.code)
        return False, f"Không thể làm mới phiên (HTTP {err.code}). Vui lòng đăng nhập lại."
    except Exception as exc:
        LOGGER.warning("C-Agent token refresh error: %s", exc)
        return False, f"Lỗi làm mới phiên C-Agent: {exc}"

    if not isinstance(res_data, dict):
        return False, "Phản hồi làm mới token không hợp lệ."

    access_token = str(res_data.get("accessToken", "") or res_data.get("access_token", "")).strip()
    new_refresh = str(res_data.get("refreshToken", "") or res_data.get("refresh_token", "")).strip()

    if not access_token and isinstance(res_data.get("data"), dict):
        inner = res_data["data"]
        access_token = str(inner.get("accessToken", "") or inner.get("access_token", "")).strip()
        new_refresh = str(inner.get("refreshToken", "") or inner.get("refresh_token", "")).strip()

    if not access_token:
        return False, "Máy chủ không trả về access token mới."

    claims = decode_jwt_payload(access_token)
    exp = float(claims.get("exp", 0.0)) or (time.time() + 3600.0)

    updated_tokens = CAgentAuthTokens(
        access_token=access_token,
        refresh_token=new_refresh or session.refresh_token,
        username=session.username,
        expires_at=exp,
    )
    save_session(updated_tokens)
    return True, "Làm mới phiên đăng nhập thành công."


def get_valid_access_token(base_url: str = "") -> str:
    """Return an active, valid Bearer access token, refreshing automatically if needed."""
    # 1. Check explicit override in environment
    env_token = os.environ.get("AIOS_CAGENT_ACCESS_TOKEN", "").strip() or os.environ.get("AIOS_CAGENT_TOKEN", "").strip()
    if env_token:
        return env_token

    # 2. Load stored session
    session = load_session()
    if not session or not session.access_token:
        return ""

    now = time.time()
    # 3. If token is still comfortably valid (> margin), use it
    if session.expires_at > (now + MARGIN_SECONDS_BEFORE_REFRESH):
        return session.access_token

    # 4. If expiring soon or expired, attempt background refresh
    if session.refresh_token:
        LOGGER.info("C-Agent access token expiring soon, refreshing in background...")
        ok, _ = refresh_cagent_token(base_url)
        if ok:
            renewed = load_session()
            if renewed and renewed.access_token:
                return renewed.access_token

    # 5. Fallback: if token hasn't strictly expired yet, return it anyway
    if session.expires_at > now:
        return session.access_token

    return ""


def get_auth_status() -> dict[str, Any]:
    """Return summary of current authentication status for UI rendering."""
    env_token = os.environ.get("AIOS_CAGENT_ACCESS_TOKEN", "").strip() or os.environ.get("AIOS_CAGENT_TOKEN", "").strip()
    if env_token:
        return {
            "logged_in": True,
            "username": "env_override",
            "source": "environment",
            "expires_in_seconds": None,
            "message": "Đang dùng token từ biến môi trường.",
        }

    session = load_session()
    if not session or not session.access_token:
        return {
            "logged_in": False,
            "username": "",
            "source": "none",
            "expires_in_seconds": 0,
            "message": "Chưa đăng nhập tài khoản C-Agent.",
        }

    now = time.time()
    remaining = max(0.0, session.expires_at - now) if session.expires_at else None
    is_valid = session.expires_at == 0.0 or session.expires_at > now

    return {
        "logged_in": is_valid,
        "username": session.username,
        "source": "session_file",
        "expires_in_seconds": remaining,
        "has_refresh_token": bool(session.refresh_token),
        "message": f"Đã đăng nhập ({session.username})" if is_valid else "Phiên đã hết hạn.",
    }


if __name__ == "__main__":
    import getpass
    import sys

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    if cmd == "login":
        u = input("Tên đăng nhập: ").strip() if len(args) < 2 else args[1]
        p = getpass.getpass("Mật khẩu: ") if len(args) < 3 else args[2]
        ok, msg = login_cagent(u, p)
        print(msg)
        sys.exit(0 if ok else 1)
    elif cmd == "logout":
        clear_session()
        print("Đã đăng xuất C-Agent.")
    elif cmd == "refresh":
        ok, msg = refresh_cagent_token()
        print(msg)
        sys.exit(0 if ok else 1)
    elif cmd == "status":
        info = get_auth_status()
        print(json.dumps(info, ensure_ascii=False, indent=2))
    elif cmd == "token":
        tok = get_valid_access_token()
        print(tok if tok else "(Không có token hợp lệ)")
    else:
        print("Cách dùng: python -m aios_habit.cagent_auth [status|login|logout|refresh|token]")
