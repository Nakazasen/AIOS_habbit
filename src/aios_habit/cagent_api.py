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
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_CAGENT_API_URL = "https://kdtvn-ai.cmcts.vn/api/v1/prediction/1881aa32-c996-4e6f-9257-78246177ba9f"

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


def _safe_error(value: object) -> str:
    """Return a concise error without reflecting endpoint details or secrets."""
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    return text[:180]


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

    question = f"{system_prompt}\n\n{user_prompt}".strip()
    body = json.dumps({"question": question}, ensure_ascii=False).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    effective_timeout = max(1, int(timeout_seconds))

    def cancelled() -> bool:
        checker = getattr(cancellation_event, "is_set", None)
        return bool(callable(checker) and checker())

    def timeout_response() -> CAgentResponse:
        return CAgentResponse(
            False,
            error_message=_TIMEOUT_MESSAGE_TEMPLATE.format(timeout=effective_timeout),
        )

    total_attempts = MAX_RETRIES + 1
    raw = ""
    for attempt in range(1, total_attempts + 1):
        if cancelled():
            return CAgentResponse(False, error_message=_CANCELLED_MESSAGE)
        try:
            with urlopen(request, timeout=effective_timeout) as response:
                raw = response.read().decode("utf-8")
            break
        except HTTPError as error:
            try:
                err_body = error.read().decode("utf-8", errors="replace")
                logging.getLogger(__name__).warning("C-AGENT API HTTP %s: %s", error.code, err_body[:500])
            except Exception:
                pass
            if 500 <= error.code < 600:
                if attempt < total_attempts:
                    _sleep_before_retry(retry_backoff_seconds)
                    continue
                return CAgentResponse(
                    False,
                    error_message=_SERVER_BUSY_MESSAGE_TEMPLATE.format(code=error.code),
                )
            return CAgentResponse(False, error_message=f"C-AGENT API trả về HTTP {error.code}.")
        except URLError as error:
            if isinstance(getattr(error, "reason", None), TimeoutError):
                return timeout_response()
            if attempt < total_attempts:
                _sleep_before_retry(retry_backoff_seconds)
                continue
            return CAgentResponse(False, error_message=_NETWORK_ERROR_MESSAGE)
        except TimeoutError:
            return timeout_response()
        except OSError as error:
            return CAgentResponse(False, error_message=f"Lỗi kết nối C-AGENT API: {_safe_error(error)}")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return CAgentResponse(False, error_message=_INVALID_PAYLOAD_MESSAGE)
    text = _extract_text(payload)
    if not text:
        return CAgentResponse(False, error_message=_INVALID_PAYLOAD_MESSAGE)
    return CAgentResponse(True, text=text)


def _sleep_before_retry(seconds: float) -> None:
    """Backoff cố định 2–3 s trước lần thử lại (tắt được khi test với ``0``)."""
    if seconds > 0:
        time.sleep(seconds)


class CAgentWorkspaceProviderClient:
    """Adapter matching ``WorkspaceAIProviderClient`` without retaining a token."""

    def __init__(self, endpoint_url: str = "") -> None:
        self.endpoint_url = str(endpoint_url or os.environ.get("AIOS_CAGENT_API_URL", "") or DEFAULT_CAGENT_API_URL).strip()

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        response = call_cagent_prediction(
            self.endpoint_url,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        if not response.ok:
            raise RuntimeError(response.error_message)
        return response.text
