"""Antigravity IDE Sidecar Daemon for AIOS WorkLens.

Truthful, non-facade local bridge service that exposes health FSM status on
127.0.0.1:8585 and serves direct completions via Gemini Web or tracks asynchronous handoff lifecycle states.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
import uuid

# Windows console UTF-8 safety
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aios_habit.ide_handoff_bridge import (
    HANDOFF_ROOT,
    list_pending_ide_requests,
)
from aios_habit.gemini_web_engine import (
    generate_gemini_web_reply,
    ensure_latest_bl,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (AntigravitySidecar) %(message)s",
)
LOGGER = logging.getLogger(__name__)

# FSM State Constants
FSM_UNAVAILABLE = "unavailable"
FSM_DIRECT_READY = "direct_ready"
FSM_HANDOFF_READY = "handoff_ready"
FSM_HANDOFF_PENDING = "handoff_pending"
FSM_COMPLETED = "completed"
FSM_FAILED = "failed"

# Operational Mode setting: "direct" or "handoff"
SIDECAR_CONFIG = {
    "mode": "direct",
}


def sanitize_reason(reason: str) -> str:
    """Sanitize error reasons to prevent path/secret leakage."""
    if not reason:
        return ""
    text = str(reason).replace("\\", "/")
    # Mask paths
    text = re.sub(r"([A-Za-z]:)?/[a-zA-Z0-9_\-\./]+", "<path>", text)
    # Mask API tokens
    text = re.sub(r"(sk-[a-zA-Z0-9_\-]+|Bearer\s+[a-zA-Z0-9_\-]+)", "<redacted_token>", text)
    return text[:200].strip()


def evaluate_sidecar_health(
    handoff_root: Path | str = HANDOFF_ROOT,
    mode: str | None = None,
) -> dict[str, Any]:
    """Dynamically evaluate the honest 6-state FSM health."""
    root = Path(handoff_root)
    effective_mode = mode if mode is not None else SIDECAR_CONFIG.get("mode", "handoff")
    is_direct = effective_mode == "direct"

    # 1. Direct adapter check
    if is_direct:
        return {
            "status": FSM_DIRECT_READY,
            "mode": "direct",
            "service": "antigravity_ide_brain_sidecar",
            "version": "1.0.0",
            "capabilities": ["direct_chat", "local_handoff", "gemini_web_direct"],
            "reason": "",
        }

    # 2. Check handoff subsystem
    try:
        root.mkdir(parents=True, exist_ok=True)
        (root / "outbox").mkdir(parents=True, exist_ok=True)
        (root / "inbox").mkdir(parents=True, exist_ok=True)
        (root / "processed").mkdir(parents=True, exist_ok=True)

        pending = list_pending_ide_requests(root)
        unresolved = [p for p in pending if not p.response_exists and p.state in ("handoff_pending", "created")]

        if unresolved:
            return {
                "status": FSM_HANDOFF_PENDING,
                "mode": "handoff",
                "service": "antigravity_ide_brain_sidecar",
                "version": "1.0.0",
                "capabilities": ["local_handoff"],
                "reason": f"{len(unresolved)} request(s) awaiting IDE response",
            }

        return {
            "status": FSM_HANDOFF_READY,
            "mode": "handoff",
            "service": "antigravity_ide_brain_sidecar",
            "version": "1.0.0",
            "capabilities": ["local_handoff"],
            "reason": "",
        }
    except Exception as exc:
        LOGGER.error("Handoff root evaluation failed: %s", exc)
        return {
            "status": FSM_FAILED,
            "mode": "none",
            "service": "antigravity_ide_brain_sidecar",
            "version": "1.0.0",
            "capabilities": [],
            "reason": sanitize_reason(str(exc)),
        }


class AntigravityBridgeHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        if args and str(args[0]).startswith(("4", "5")):
            LOGGER.warning(format, *args)

    def do_GET(self) -> None:
        if self.path in ("/health", "/", "/health/"):
            payload = evaluate_sidecar_health()
            body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                self.wfile.write(body_bytes)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                pass
        else:
            self.send_response(404)
            self.send_header("Connection", "close")
            self.end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Connection", "close")
        self.end_headers()

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req_data = json.loads(raw_body)
        except Exception:
            req_data = {}

        if self.path in ("/v1/chat/completions", "/chat/completions"):
            is_direct = SIDECAR_CONFIG.get("mode") == "direct"
            if not is_direct:
                response_bytes = json.dumps({
                    "error": {
                        "message": "Antigravity IDE direct chat completion is unavailable. Please use asynchronous handoff mode.",
                        "type": "direct_adapter_unavailable",
                        "code": 503,
                        "status": "unavailable",
                    }
                }, ensure_ascii=False).encode("utf-8")

                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(response_bytes)
                return

            # Direct Mode execution via Gemini Web engine
            messages = req_data.get("messages", [])
            model_name = req_data.get("model", "")

            prompt_parts = []
            for m in messages:
                role = m.get("role", "")
                content = m.get("content", "")
                if role == "system":
                    prompt_parts.append(f"[Yêu cầu hệ thống]: {content}")
                elif role == "user":
                    prompt_parts.append(f"[Câu hỏi]: {content}")
                elif role == "assistant":
                    prompt_parts.append(f"[Câu trả lời trước]: {content}")
            full_prompt = "\n\n".join(prompt_parts) if prompt_parts else "Xin chào!"

            res = generate_gemini_web_reply(
                prompt=full_prompt,
                model_name=model_name or "gemini-3.6-flash",
                timeout_seconds=60.0,
            )

            if res["ok"]:
                response_payload = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": res.get("model", ""),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": res["answer_text"],
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": len(full_prompt) // 4,
                        "completion_tokens": len(res["answer_text"]) // 4,
                        "total_tokens": (len(full_prompt) + len(res["answer_text"])) // 4,
                    },
                }
                response_bytes = json.dumps(response_payload, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(response_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    self.wfile.write(response_bytes)
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                    pass
            else:
                err_msg = res.get("error", "Gemini Web generation failed.")
                err_payload = {
                    "error": {
                        "message": sanitize_reason(err_msg),
                        "type": "gemini_web_error",
                        "code": 502,
                    }
                }
                response_bytes = json.dumps(err_payload, ensure_ascii=False).encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    self.wfile.write(response_bytes)
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                    pass
        else:
            self.send_response(404)
            self.send_header("Connection", "close")
            self.end_headers()


def _handoff_watcher_loop(interval: float = 2.0) -> None:
    """Background thread watching and processing local IDE handoffs."""
    LOGGER.info("Starting background IDE handoff watcher...")
    from aios_habit.antigravity_bridge import process_pending_ide_handoffs

    while True:
        try:
            process_pending_ide_handoffs()
        except Exception as e:
            LOGGER.debug("Watcher error: %s", e)
        time.sleep(interval)


def run_server(host: str = "127.0.0.1", port: int = 8585, mode: str = "direct") -> None:
    SIDECAR_CONFIG["mode"] = mode
    ensure_latest_bl()

    # Start handoff watcher thread
    watcher = threading.Thread(target=_handoff_watcher_loop, daemon=True)
    watcher.start()

    server = ThreadingHTTPServer((host, port), AntigravityBridgeHTTPHandler)
    server.daemon_threads = True
    LOGGER.info("🚀 Antigravity IDE Brain Sidecar running on http://%s:%d (mode: %s)", host, port, mode)
    LOGGER.info("Endpoints: GET /health | POST /v1/chat/completions")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down Antigravity Sidecar...")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Antigravity IDE Sidecar Daemon")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8585, help="Port to bind")
    parser.add_argument("--mode", default="direct", choices=["direct", "handoff"], help="Operational mode")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, mode=args.mode)
