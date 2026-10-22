"""Small client for a published C-AGENT/Flowise prediction endpoint.

The C-AGENT server owns its model credential.  AIOS only sends the approved
chat prompt to the published AgentFlow URL, so no LiteLLM key is stored here.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen



DEFAULT_TIMEOUT_SECONDS = int(os.environ.get("AIOS_CAGENT_TIMEOUT_SECONDS", "60"))
DEFAULT_CAGENT_API_URL = "https://kdtvn-ai.cmcts.vn/api/v1/prediction/1881aa32-c996-4e6f-9257-78246177ba9f"

# Ngân sách cắt tỉa lịch sử hội thoại cho C-Agent (DESKTOP-PC0575-CAGENT-PAYLOAD-TRIM-FIX)
# Mặc định tối đa 6 tin nhắn gần nhất (3 lượt hỏi-đáp) và không quá 4.000 ký tự.
DEFAULT_CAGENT_MAX_HISTORY_TURNS = int(
    os.environ.get(
        "AIOS_CAGENT_MAX_HISTORY_TURNS",
        os.environ.get("AIOS_CAGENT_MAX_HISTORY_MESSAGES", "6"),
    )
)
DEFAULT_CAGENT_MAX_HISTORY_CHARS = int(
    os.environ.get("AIOS_CAGENT_MAX_HISTORY_CHARS", "4000")
)


def trim_chat_history_for_cagent(
    chat_history: Sequence[Mapping[str, Any]] | None,
    *,
    max_turns: int | None = None,
    max_chars: int | None = None,
) -> tuple[dict[str, Any], ...]:
    """Giới hạn lịch sử hội thoại gửi kèm cuộc gọi tổng hợp C-Agent (DESKTOP-PC0575-CAGENT-PAYLOAD-TRIM-FIX).

    Quy tắc nghiệp vụ:
    1. Giữ nguyên vẹn 100% nếu hội thoại ngắn (<= max_turns và <= max_chars).
    2. Cắt tỉa hội thoại dài, chỉ giữ các lượt gần nhất trong ngân sách số lượt và tổng ký tự.
    3. Bảo toàn chỉ thị neo ngữ cảnh (anchor directive) nếu có ở cuối lịch sử.
    4. Không bao giờ can thiệp vào câu hỏi hiện tại hay bằng chứng truy hồi (được lắp ráp riêng).
    """
    if not chat_history:
        return ()

    eff_max_turns = max_turns if max_turns is not None else DEFAULT_CAGENT_MAX_HISTORY_TURNS
    eff_max_chars = max_chars if max_chars is not None else DEFAULT_CAGENT_MAX_HISTORY_CHARS

    items = [dict(m) for m in chat_history]
    if not items:
        return ()

    total_chars = sum(len(str(m.get("content", ""))) for m in items)
    if len(items) <= eff_max_turns and total_chars <= eff_max_chars:
        return tuple(items)

    # Tách directive neo ngữ cảnh ở cuối (nếu có) để luôn ưu tiên giữ
    anchor_item: dict[str, Any] | None = None
    if items and items[-1].get("role") == "system" and "[CHỈ THỊ NEO NGỮ CẢNH" in str(items[-1].get("content", "")):
        anchor_item = items[-1]
        items = items[:-1]

    # Giới hạn số lượt/tin nhắn gần nhất
    allowed_turns = eff_max_turns if anchor_item is None else max(1, eff_max_turns - 1)
    if len(items) > allowed_turns:
        items = items[-allowed_turns:]

    # Giới hạn tổng ký tự (ưu tiên giữ tin nhắn mới nhất, loại bỏ dần tin cũ hơn)
    anchor_chars = len(str(anchor_item.get("content", ""))) if anchor_item else 0
    available_chars = max(0, eff_max_chars - anchor_chars)

    accumulated: list[dict[str, Any]] = []
    current_char_count = 0
    for m in reversed(items):
        m_len = len(str(m.get("content", "")))
        if current_char_count + m_len <= available_chars:
            accumulated.append(m)
            current_char_count += m_len
        elif not accumulated and available_chars > 0:
            trimmed_msg = dict(m)
            content_str = str(m.get("content", ""))
            trimmed_msg["content"] = content_str[:available_chars]
            accumulated.append(trimmed_msg)
            current_char_count += available_chars
            break
        else:
            break

    accumulated.reverse()
    if anchor_item is not None:
        accumulated.append(anchor_item)

    return tuple(accumulated)

# WIRE-QA-CAGENT spec §2: tối đa 1 lần thử lại, backoff cố định 2–3 giây,
# chỉ cho lỗi mạng tức thời (URLError không phải timeout) và HTTP 5xx.
MAX_RETRIES = 1
DEFAULT_RETRY_BACKOFF_SECONDS = 2.5

# Thông báo tiếng Việt theo bảng spec §3.2 — không lộ traceback/đường dẫn/endpoint.
_TIMEOUT_MESSAGE_TEMPLATE = (
    "Dịch vụ C-Agent phản hồi quá {timeout} giây. "
    "Vui lòng thử lại với câu hỏi ngắn gọn hơn."
)
_NETWORK_ERROR_MESSAGE = (
    "Không thể kết nối đến máy chủ C-Agent. Vui lòng kiểm tra lại mạng nội bộ công ty."
)
_SERVER_BUSY_MESSAGE_TEMPLATE = (
    "Dịch vụ C-Agent đang bận hoặc bảo trì tạm thời (HTTP {code}). "
    "Vui lòng thử lại sau vài phút."
)
_INVALID_PAYLOAD_MESSAGE = (
    "Máy chủ C-Agent không trả về nội dung hợp lệ cho câu hỏi này. Vui lòng thử lại."
)
_CANCELLED_MESSAGE = "Đã dừng yêu cầu trả lời từ AI."


@dataclass(frozen=True)
class CAgentResponse:
    ok: bool
    text: str = ""
    error_message: str = ""


def _mask_secret(text: str, secret: str) -> str:
    """Mask occurrences of secret token from text/logs/error messages."""
    if not text or not secret:
        return text
    return text.replace(secret, "[REDACTED]")


def _safe_error(value: object, key: str = "") -> str:
    """Return a concise error without reflecting endpoint details or secrets."""
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    if key:
        text = _mask_secret(text, key)
    return text[:180]


def _resolve_api_key(api_key: str | None = None, endpoint_url: str = "") -> str:
    """Resolve C-Agent API key from argument, environment, .env file, or user session."""
    if api_key is not None:
        return str(api_key).strip()
    try:
        from aios_habit.workspace_paths import load_env_file

        load_env_file()
    except Exception:
        pass
    env_key = str(os.environ.get("AIOS_CAGENT_API_KEY", "") or "").strip()
    if env_key:
        return env_key
    try:
        from aios_habit.cagent_auth import get_valid_access_token

        return get_valid_access_token(endpoint_url)
    except Exception:
        return ""


def _extract_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in ("text", "answer", "response"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def call_cagent_prediction(
    endpoint_url: str = "",
    *,
    system_prompt: str,
    user_prompt: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    cancellation_event: Any | None = None,
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    api_key: str | None = None,
) -> CAgentResponse:
    """Submit one approved Workspace Chat prompt to a C-AGENT AgentFlow.

    Thử lại tối đa ``MAX_RETRIES`` lần (backoff 2–3 s) CHỈ khi mất kết nối mạng
    tức thời (``URLError`` không phải timeout) hoặc HTTP 5xx. Không thử lại với
    HTTP 4xx, timeout, dữ liệu sai, hoặc khi người dùng đã hủy.
    """
    endpoint = str(endpoint_url or os.environ.get("AIOS_CAGENT_API_URL", "") or DEFAULT_CAGENT_API_URL).strip()
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        return CAgentResponse(False, error_message="C-AGENT API chưa có URL AgentFlow hợp lệ.")

    resolved_api_key = _resolve_api_key(api_key, endpoint)

    def _make_error(msg: str) -> CAgentResponse:
        return CAgentResponse(False, error_message=_mask_secret(msg, resolved_api_key))

    question = f"{system_prompt}\n\n{user_prompt}".strip()
    body = json.dumps({"question": question}, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if resolved_api_key:
        headers["Authorization"] = f"Bearer {resolved_api_key}"
    request = Request(
        endpoint,
        data=body,
        method="POST",
        headers=headers,
    )

    effective_timeout = max(1, int(timeout_seconds))

    # Simulation hook for timeout testing (Gate 3)
    mock_timeout_file = Path.home() / ".aios" / "mock_timeout.txt"
    if mock_timeout_file.is_file() or os.environ.get("AIOS_CAGENT_MOCK_TIMEOUT"):
        time.sleep(1.0)
        return _make_error(_TIMEOUT_MESSAGE_TEMPLATE.format(timeout=effective_timeout))

    def cancelled() -> bool:
        checker = getattr(cancellation_event, "is_set", None)
        return bool(callable(checker) and checker())

    def timeout_response() -> CAgentResponse:
        return _make_error(_TIMEOUT_MESSAGE_TEMPLATE.format(timeout=effective_timeout))

    total_attempts = MAX_RETRIES + 1
    raw = ""
    for attempt in range(1, total_attempts + 1):
        if cancelled():
            return _make_error(_CANCELLED_MESSAGE)
        try:
            with urlopen(request, timeout=effective_timeout) as response:
                raw = response.read().decode("utf-8")
            break
        except HTTPError as error:
            try:
                err_body = error.read().decode("utf-8", errors="replace")
                if resolved_api_key:
                    err_body = _mask_secret(err_body, resolved_api_key)
                logging.getLogger(__name__).warning("C-AGENT API HTTP %s: %s", error.code, err_body[:500])
            except Exception:
                pass
            if error.code == 401 and attempt < total_attempts:
                try:
                    from aios_habit.cagent_auth import get_valid_access_token, refresh_cagent_token

                    ok, _ = refresh_cagent_token(endpoint)
                    if ok:
                        renewed = get_valid_access_token(endpoint)
                        if renewed and renewed != resolved_api_key:
                            resolved_api_key = renewed
                            headers["Authorization"] = f"Bearer {resolved_api_key}"
                            request = Request(endpoint, data=body, method="POST", headers=headers)
                            continue
                except Exception:
                    pass
            if 500 <= error.code < 600:
                if attempt < total_attempts:
                    _sleep_before_retry(retry_backoff_seconds)
                    continue
                return _make_error(_SERVER_BUSY_MESSAGE_TEMPLATE.format(code=error.code))
            return _make_error(f"C-AGENT API trả về HTTP {error.code}.")
        except URLError as error:
            if isinstance(getattr(error, "reason", None), TimeoutError):
                return timeout_response()
            if attempt < total_attempts:
                _sleep_before_retry(retry_backoff_seconds)
                continue
            return _make_error(_NETWORK_ERROR_MESSAGE)
        except TimeoutError:
            return timeout_response()
        except OSError as error:
            return _make_error(f"Lỗi kết nối C-AGENT API: {_safe_error(error, resolved_api_key)}")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _make_error(_INVALID_PAYLOAD_MESSAGE)
    text = _extract_text(payload)
    if not text:
        return _make_error(_INVALID_PAYLOAD_MESSAGE)
    return CAgentResponse(True, text=text)


def _sleep_before_retry(seconds: float) -> None:
    """Backoff cố định 2–3 s trước lần thử lại (tắt được khi test với ``0``)."""
    if seconds > 0:
        time.sleep(seconds)


class CAgentWorkspaceProviderClient:
    """Adapter matching ``WorkspaceAIProviderClient`` without retaining a token."""

    def __init__(self, endpoint_url: str = "", *, api_key: str | None = None) -> None:
        self.endpoint_url = str(endpoint_url or os.environ.get("AIOS_CAGENT_API_URL", "") or DEFAULT_CAGENT_API_URL).strip()
        self._api_key = api_key

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        response = call_cagent_prediction(
            self.endpoint_url,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            api_key=self._api_key,
        )
        if not response.ok:
            raise RuntimeError(response.error_message)
        return response.text
