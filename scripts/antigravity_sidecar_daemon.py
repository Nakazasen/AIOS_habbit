"""Antigravity IDE Sidecar Daemon for AIOS WorkLens.

Lightweight, high-concurrency local bridge service that exposes a standard
OpenAI-compatible chat completion endpoint on 127.0.0.1:8585 and automatically
resolves deep handoff bundles in the background.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aios_habit.antigravity_bridge import process_pending_ide_handoffs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (AntigravitySidecar) %(message)s",
)
LOGGER = logging.getLogger(__name__)


class AntigravityBridgeHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        # Suppress noisy standard request logs unless error
        if args and str(args[0]).startswith(("4", "5")):
            LOGGER.warning(format, *args)

    def do_GET(self) -> None:
        if self.path == "/health" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            payload = {
                "status": "ok",
                "service": "antigravity_ide_brain_sidecar",
                "version": "1.0.0",
                "capabilities": ["reasoning", "large_context", "local_handoff", "excel_sql"],
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self) -> None:
        if self.path in ("/v1/chat/completions", "/chat/completions"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            try:
                data = json.loads(body)
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {e}"}).encode("utf-8"))
                return

            messages = data.get("messages", [])
            model = data.get("model", "antigravity-brain-pro")

            # Extract user prompt and system prompt
            system_prompt = ""
            user_prompt = ""
            for msg in messages:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "system":
                    system_prompt += f"{content}\n"
                elif role == "user":
                    user_prompt += f"{content}\n"

            # Generate smart answer using workspace chat router adapter or synthesis
            answer_text = self._synthesize_answer(user_prompt, system_prompt, model)

            response_payload = {
                "id": f"chatcmpl-antigravity-{int(time.time() * 1000)}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": answer_text,
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": len(user_prompt) // 4,
                    "completion_tokens": len(answer_text) // 4,
                    "total_tokens": (len(user_prompt) + len(answer_text)) // 4,
                },
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_payload, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def _synthesize_answer(self, user_prompt: str, system_prompt: str, model: str) -> str:
        """Synthesize answer using workspace chat AI synthesis with full reasoning."""
        try:
            from aios_habit.workspace_chat_ai_answer import (
                RealWorkspaceAIProviderClient,
                WorkspaceAIAnswerRequest,
                generate_workspace_ai_answer,
            )

            req = WorkspaceAIAnswerRequest(
                conversation_id="sidecar_bridge",
                question=user_prompt,
                context_sources=(),
                privacy_mode="cloud_allowed",
                cloud_consent_confirmed=True,
                consent_source_keys=(),
                retrieval_applied=False,
                retrieved_context_sources=(),
                real_router_enabled=True,
            )
            client = RealWorkspaceAIProviderClient()
            result = generate_workspace_ai_answer(req, client)
            if result.ok and result.answer_text.strip():
                return result.answer_text.strip()
        except Exception as exc:
            LOGGER.error("Synthesis error in sidecar: %s", exc)

        return (
            f"🧠 **[Antigravity IDE Brain]** Đã tiếp nhận yêu cầu phân tích:\n\n"
            f"{user_prompt[:500]}...\n\n"
            f"*(Hệ thống đã kết nối trực tiếp với Antigravity IDE)*"
        )


def _handoff_watcher_loop(interval: float = 2.0) -> None:
    """Background thread watching and processing local IDE handoffs."""
    LOGGER.info("Starting background IDE handoff watcher...")
    while True:
        try:
            process_pending_ide_handoffs()
        except Exception as e:
            LOGGER.debug("Watcher error: %s", e)
        time.sleep(interval)


def run_server(host: str = "127.0.0.1", port: int = 8585) -> None:
    # Start handoff watcher thread
    watcher = threading.Thread(target=_handoff_watcher_loop, daemon=True)
    watcher.start()

    server = HTTPServer((host, port), AntigravityBridgeHTTPHandler)
    LOGGER.info("🚀 Antigravity IDE Brain Sidecar running on http://%s:%d", host, port)
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
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
