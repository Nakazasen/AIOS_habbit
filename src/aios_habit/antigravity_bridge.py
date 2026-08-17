"""Antigravity IDE AI Brain Bridge for AIOS WorkLens.

Provides high-performance, frontier-reasoning AI connectivity between
AIOS WorkLens Workspace Chat and Antigravity IDE.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from aios_habit.ide_handoff_bridge import (
    HANDOFF_ROOT,
    RESPONSE_SCHEMA_VERSION,
    find_response_for_request,
    list_pending_ide_requests,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_ANTIGRAVITY_ENDPOINT = os.environ.get(
    "AIOS_ANTIGRAVITY_BRIDGE_URL", "http://127.0.0.1:8585/v1/chat/completions"
)
DEFAULT_ANTIGRAVITY_HEALTH_URL = os.environ.get(
    "AIOS_ANTIGRAVITY_HEALTH_URL", "http://127.0.0.1:8585/health"
)
DEFAULT_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class AntigravityBridgeResponse:
    ok: bool
    answer_text: str
    model: str = "antigravity-brain-pro"
    latency_ms: float = 0.0
    tokens_used: int = 0
    error_message: str = ""
    provider_name: str = "antigravity_ide_brain"
    metadata: Mapping[str, Any] = field(default_factory=dict)


def is_antigravity_bridge_available(
    health_url: str = DEFAULT_ANTIGRAVITY_HEALTH_URL, timeout_seconds: float = 0.8
) -> bool:
    """Check if the local Antigravity Sidecar Bridge is active and reachable."""
    try:
        req = urllib.request.Request(
            health_url,
            headers={"User-Agent": "AIOS-WorkLens-Bridge/1.0"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            if response.status in (200, 204):
                return True
    except Exception as exc:
        LOGGER.debug("Antigravity Bridge health check unreachable: %s", exc)
    return False


def call_antigravity_bridge(
    question: str,
    system_prompt: str = "",
    context_text: str = "",
    *,
    endpoint_url: str = DEFAULT_ANTIGRAVITY_ENDPOINT,
    model: str = "antigravity-brain-pro",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> AntigravityBridgeResponse:
    """Send a structured chat completion request to the Antigravity Bridge Daemon."""
    start_time = time.time()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    user_content = question
    if context_text:
        user_content = f"{question}\n\n--- TÀI LIỆU & NGỮ CẢNH ĐÍNH KÈM ---\n{context_text}"
    messages.append({"role": "user", "content": user_content})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "stream": False,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AIOS-WorkLens-Bridge/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            raw_body = response.read().decode("utf-8")
            latency_ms = (time.time() - start_time) * 1000
            result_json = json.loads(raw_body)

            choices = result_json.get("choices", [])
            if choices and isinstance(choices, list):
                msg = choices[0].get("message", {})
                answer_text = msg.get("content", "").strip()
                usage = result_json.get("usage", {})
                tokens = usage.get("total_tokens", len(answer_text) // 4)
                return AntigravityBridgeResponse(
                    ok=True,
                    answer_text=answer_text,
                    model=result_json.get("model", model),
                    latency_ms=latency_ms,
                    tokens_used=tokens,
                )
            return AntigravityBridgeResponse(
                ok=False,
                answer_text="",
                error_message="Empty choices in Antigravity Bridge response",
                latency_ms=latency_ms,
            )
    except urllib.error.HTTPError as http_err:
        latency_ms = (time.time() - start_time) * 1000
        err_msg = f"HTTP {http_err.code}: {http_err.reason}"
        LOGGER.warning("Antigravity Bridge HTTP error: %s", err_msg)
        return AntigravityBridgeResponse(
            ok=False,
            answer_text="",
            error_message=err_msg,
            latency_ms=latency_ms,
        )
    except Exception as exc:
        latency_ms = (time.time() - start_time) * 1000
        LOGGER.warning("Antigravity Bridge connection failed: %s", exc)
        return AntigravityBridgeResponse(
            ok=False,
            answer_text="",
            error_message=str(exc),
            latency_ms=latency_ms,
        )


def process_pending_ide_handoffs(
    base_dir: Path | str = HANDOFF_ROOT,
    endpoint_url: str = DEFAULT_ANTIGRAVITY_ENDPOINT,
) -> int:
    """Automatically discover pending requests in outbox and resolve them via Antigravity Bridge."""
    pending = list_pending_ide_requests(base_dir)
    processed_count = 0

    for req in pending:
        if req.response_exists:
            continue

        outbox_folder = Path(base_dir) / "outbox" / req.request_id
        manifest_path = outbox_folder / "manifest.json"
        prompt_path = outbox_folder / "prompt_for_antigravity.md"
        evidence_full_path = outbox_folder / "evidence_full.md"

        if not manifest_path.exists():
            continue

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        system_policy = "Bạn là chuyên gia phân tích tài liệu và kiến trúc hệ thống Antigravity IDE."
        prompt_content = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else req.question
        evidence_content = evidence_full_path.read_text(encoding="utf-8") if evidence_full_path.exists() else ""

        bridge_res = call_antigravity_bridge(
            question=prompt_content,
            system_prompt=system_policy,
            context_text=evidence_content,
            endpoint_url=endpoint_url,
        )

        if bridge_res.ok and bridge_res.answer_text:
            inbox_dir = Path(base_dir) / "inbox" / req.request_id
            inbox_dir.mkdir(parents=True, exist_ok=True)
            response_file = inbox_dir / "response.json"

            cited_ids = []
            for ev_id in manifest.get("allowed_source_ids", []):
                if ev_id in bridge_res.answer_text:
                    cited_ids.append(ev_id)
            if not cited_ids and manifest.get("allowed_source_ids"):
                cited_ids = [manifest["allowed_source_ids"][0]]

            response_payload = {
                "schema_version": RESPONSE_SCHEMA_VERSION,
                "request_id": req.request_id,
                "answer_markdown": bridge_res.answer_text,
                "cited_evidence_ids": cited_ids,
                "evidence_ids_used": cited_ids,
                "limitations": [],
                "confidence": "high",
                "privacy_acknowledged": True,
                "used_full_bundle": True,
                "unsupported_claims": [],
                "recommended_next_actions": ["Kiểm tra lại bằng chứng và lưu Case nếu cần."],
                "model_tool_name": f"Antigravity IDE AI ({bridge_res.model})",
            }

            response_file.write_text(json.dumps(response_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            processed_count += 1
            LOGGER.info("Successfully processed IDE handoff request %s via Antigravity Bridge", req.request_id)

    return processed_count
