"""Small client for a published C-AGENT/Flowise prediction endpoint.

The C-AGENT server owns its model credential.  AIOS only sends the approved
chat prompt to the published AgentFlow URL, so no LiteLLM key is stored here.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 60


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
    endpoint_url: str,
    *,
    system_prompt: str,
    user_prompt: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> CAgentResponse:
    """Submit one approved Workspace Chat prompt to a C-AGENT AgentFlow."""
    endpoint = str(endpoint_url or "").strip()
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
    try:
        with urlopen(request, timeout=max(1, int(timeout_seconds))) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as error:
        return CAgentResponse(False, error_message=f"C-AGENT API trả về HTTP {error.code}.")
    except URLError:
        return CAgentResponse(False, error_message="Không kết nối được tới C-AGENT API.")
    except OSError as error:
        return CAgentResponse(False, error_message=f"Lỗi kết nối C-AGENT API: {_safe_error(error)}")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return CAgentResponse(False, error_message="C-AGENT API trả về dữ liệu không hợp lệ.")
    text = _extract_text(payload)
    if not text:
        return CAgentResponse(False, error_message="C-AGENT API không trả về nội dung trả lời.")
    return CAgentResponse(True, text=text)


class CAgentWorkspaceProviderClient:
    """Adapter matching ``WorkspaceAIProviderClient`` without retaining a token."""

    def __init__(self, endpoint_url: str) -> None:
        self.endpoint_url = endpoint_url

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        response = call_cagent_prediction(
            self.endpoint_url,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        if not response.ok:
            raise RuntimeError(response.error_message)
        return response.text
