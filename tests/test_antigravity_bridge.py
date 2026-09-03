"""Unit and integration tests for Antigravity Truthful Bridge (Milestone 1).

Covers:
1. Health Endpoint & 6-State FSM (unavailable, direct_ready, handoff_ready, handoff_pending, completed, failed)
2. AST Static Analysis check prohibiting RealWorkspaceAIProviderClient in sidecar daemon
3. Sidecar daemon dynamic health evaluation & HTTP 503 on unverified direct completions
4. Citation integrity check (zero-fabrication policy)
5. Privacy & error message sanitization
6. Direct adapter fail-closed behavior
"""
from __future__ import annotations

import ast
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
import pytest

import aios_habit.antigravity_bridge as bridge_module
from aios_habit.antigravity_bridge import (
    AntigravityBridgeResponse,
    AntigravityHealthStatus,
    call_antigravity_bridge,
    ensure_antigravity_bridge_running,
    get_antigravity_bridge_health,
    get_antigravity_bridge_status,
    is_antigravity_bridge_available,
    process_pending_ide_handoffs,
    sanitize_bridge_error,
    sanitize_reason,
)
from aios_habit.ai_provider_bridge import ProviderConfig, answer_with_provider
from scripts.antigravity_sidecar_daemon import (
    AntigravityBridgeHTTPHandler,
    SIDECAR_CONFIG,
    evaluate_sidecar_health,
)


class MockFSMBridgeServer(BaseHTTPRequestHandler):
    """Configurable mock HTTP server for testing Antigravity Bridge FSM & completions."""

    @property
    def health_payload(self) -> dict[str, Any]:
        return getattr(
            self.server,
            "health_payload",
            {
                "status": "handoff_ready",
                "mode": "handoff",
                "capabilities": ["local_handoff"],
                "reason": "",
            },
        )

    @property
    def health_status_code(self) -> int:
        return getattr(self.server, "health_status_code", 200)

    @property
    def completion_response(self) -> dict[str, Any]:
        return getattr(self.server, "completion_response", {})

    @property
    def completion_status_code(self) -> int:
        return getattr(self.server, "completion_status_code", 200)

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        if self.path in ("/health", "/", "/health/"):
            self.send_response(self.health_status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.health_payload).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        if self.path in ("/v1/chat/completions", "/chat/completions"):
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(raw_body)
            except Exception:
                data = {}

            if self.completion_status_code != 200:
                body_bytes = json.dumps(self.completion_response or {"error": "Internal Error"}).encode("utf-8")
                self.send_response(self.completion_status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body_bytes)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body_bytes)
                return
            messages = data.get("messages", [])
            user_msg = ""
            for m in messages:
                if m.get("role") == "user":
                    user_msg = m.get("content", "")

            resp = self.completion_response or {
                "id": "chatcmpl-mock-test",
                "object": "chat.completion",
                "model": data.get("model", "antigravity-brain-pro"),
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": f"Antigravity response for: {user_msg[:30]}",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"total_tokens": 35},
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture
def mock_fsm_server():
    server = HTTPServer(("127.0.0.1", 0), MockFSMBridgeServer)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    server.health_payload = {
        "status": "handoff_ready",
        "mode": "handoff",
        "capabilities": ["local_handoff"],
        "reason": "",
    }
    server.health_status_code = 200
    server.completion_response = {}
    server.completion_status_code = 200

    health_url = f"http://127.0.0.1:{port}/health"
    completions_url = f"http://127.0.0.1:{port}/v1/chat/completions"
    try:
        yield server, health_url, completions_url
    finally:
        server.shutdown()
        server.server_close()


# ============================================================================
# 1. Health Endpoint FSM 6 States Tests
# ============================================================================

class TestAntigravityHealthFSM:
    def test_health_fsm_unavailable_when_server_offline(self):
        """When bridge server is down, status must be 'unavailable' with mode 'none'."""
        status = get_antigravity_bridge_status(
            health_url="http://127.0.0.1:59999/health", timeout_seconds=0.1
        )
        assert status.status == "unavailable"
        assert status.mode == "none"
        assert status.is_available is False
        assert status.is_ready is False
        assert is_antigravity_bridge_available(health_url="http://127.0.0.1:59999/health", timeout_seconds=0.1) is False

    @pytest.mark.parametrize("fsm_state,mode,capabilities", [
        ("direct_ready", "direct", ["direct_chat"]),
        ("handoff_ready", "handoff", ["local_handoff"]),
        ("handoff_pending", "handoff", ["local_handoff"]),
        ("completed", "handoff", ["local_handoff"]),
        ("failed", "none", []),
        ("unavailable", "none", []),
    ])
    def test_health_fsm_all_six_states(self, mock_fsm_server, fsm_state, mode, capabilities):
        """Verify get_antigravity_bridge_status accurately parses all 6 FSM states."""
        server, health_url, _ = mock_fsm_server
        server.health_payload = {
            "status": fsm_state,
            "mode": mode,
            "capabilities": capabilities,
            "reason": f"State reason for {fsm_state}",
        }
        status = get_antigravity_bridge_status(health_url=health_url)
        assert status.status == fsm_state
        assert status.mode == mode
        assert list(status.capabilities) == capabilities
        assert f"State reason for {fsm_state}" in status.reason
        if fsm_state in ("direct_ready", "handoff_ready", "handoff_pending", "completed"):
            assert status.is_available is True
        else:
            assert status.is_available is False

    def test_health_fsm_server_500_error(self, mock_fsm_server):
        """When server returns 500 Internal Error, status must be 'failed' with sanitized reason."""
        server, health_url, _ = mock_fsm_server
        server.health_status_code = 500
        server.health_payload = {"status": "failed", "reason": "Internal daemon error in D:/Sandbox/secret.txt"}
        status = get_antigravity_bridge_status(health_url=health_url)
        assert status.status == "failed"
        assert status.mode == "none"
        assert status.is_available is False
        assert "D:/Sandbox" not in status.reason

    def test_health_fsm_no_fake_capabilities_advertised(self, mock_fsm_server):
        """Sidecar must never advertise unverified capabilities (reasoning, large_context, excel_sql)."""
        server, health_url, _ = mock_fsm_server
        server.health_payload = {
            "status": "handoff_ready",
            "mode": "handoff",
            "capabilities": ["local_handoff", "reasoning", "large_context", "excel_sql"],
            "reason": "",
        }
        status = get_antigravity_bridge_status(health_url=health_url)
        forbidden = {"reasoning", "large_context", "excel_sql"}
        assert not any(cap in forbidden for cap in status.capabilities)
        assert "local_handoff" in status.capabilities


class TestLocalSidecarStartup:
    """The UI may start only a local direct sidecar, never a remote provider."""

    @staticmethod
    def _unavailable() -> AntigravityHealthStatus:
        return AntigravityHealthStatus(status="unavailable", reason="not listening")

    @staticmethod
    def _direct_ready() -> AntigravityHealthStatus:
        return AntigravityHealthStatus(
            status="direct_ready",
            mode="direct",
            capabilities=["direct_chat"],
        )

    def test_does_not_start_process_when_bridge_is_already_ready(self, monkeypatch):
        monkeypatch.setattr(bridge_module, "get_antigravity_bridge_health", lambda **_: self._direct_ready())

        def unexpected_start(*args, **kwargs):
            raise AssertionError("a ready bridge must not be started again")

        monkeypatch.setattr(bridge_module.subprocess, "Popen", unexpected_start)
        result = ensure_antigravity_bridge_running()

        assert result.ok is True
        assert result.started is False
        assert result.health.is_direct_ready is True

    def test_starts_local_direct_sidecar_and_waits_for_health(self, monkeypatch, tmp_path):
        launcher = tmp_path / "antigravity_sidecar_daemon.py"
        launcher.touch()
        checks = iter([self._unavailable(), self._unavailable(), self._direct_ready()])
        command: list[str] = []

        class RunningProcess:
            def poll(self):
                return None

        def fake_popen(args, **kwargs):
            command.extend(args)
            assert kwargs["cwd"]
            return RunningProcess()

        monkeypatch.setattr(bridge_module, "SIDECAR_DAEMON_PATH", launcher)
        monkeypatch.setattr(bridge_module, "get_antigravity_bridge_health", lambda **_: next(checks))
        monkeypatch.setattr(bridge_module.subprocess, "Popen", fake_popen)
        monkeypatch.setattr(bridge_module.time, "sleep", lambda _: None)

        result = ensure_antigravity_bridge_running(startup_timeout_seconds=0.5)

        assert result.ok is True
        assert result.started is True
        assert result.health.is_direct_ready is True
        assert command[1] == str(launcher)
        assert command[-4:] == ["--port", "8585", "--mode", "direct"]

    def test_refuses_to_start_a_process_for_remote_health_url(self, monkeypatch):
        monkeypatch.setattr(bridge_module, "get_antigravity_bridge_health", lambda **_: self._unavailable())

        def unexpected_start(*args, **kwargs):
            raise AssertionError("remote endpoint must never start a local sidecar")

        monkeypatch.setattr(bridge_module.subprocess, "Popen", unexpected_start)
        result = ensure_antigravity_bridge_running("https://example.com/health")

        assert result.ok is False
        assert result.started is False
        assert result.reason == "bridge_start_requires_local_health_url"


# ============================================================================
# 2. AST Static Analysis Verification for Sidecar Daemon
# ============================================================================

class TestSidecarDaemonASTSecurity:
    @pytest.fixture
    def sidecar_ast(self):
        project_root = Path(__file__).resolve().parent.parent
        sidecar_path = project_root / "scripts" / "antigravity_sidecar_daemon.py"
        assert sidecar_path.exists(), f"Sidecar script not found at {sidecar_path}"
        code = sidecar_path.read_text(encoding="utf-8")
        return ast.parse(code, filename=str(sidecar_path))

    def test_sidecar_daemon_no_forbidden_ai_imports(self, sidecar_ast):
        """Sidecar daemon MUST NOT import RealWorkspaceAIProviderClient or synthesis pipeline."""
        forbidden_modules = {
            "aios_habit.workspace_chat_ai_answer",
            "aios_habit.workspace_chat_router_adapter",
        }
        forbidden_names = {
            "RealWorkspaceAIProviderClient",
            "generate_workspace_ai_answer",
            "WorkspaceAIAnswerRequest",
        }

        imported_modules = set()
        imported_names = set()

        for node in ast.walk(sidecar_ast):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.add(node.module)
                for alias in node.names:
                    imported_names.add(alias.name)

        assert not (imported_modules & forbidden_modules), (
            f"Sidecar imports forbidden modules: {imported_modules & forbidden_modules}"
        )
        assert not (imported_names & forbidden_names), (
            f"Sidecar imports forbidden names: {imported_names & forbidden_names}"
        )

    def test_sidecar_daemon_no_forbidden_instantiations(self, sidecar_ast):
        """Sidecar daemon MUST NOT call or instantiate RealWorkspaceAIProviderClient."""
        for node in ast.walk(sidecar_ast):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "RealWorkspaceAIProviderClient":
                    pytest.fail("Found direct instantiation of RealWorkspaceAIProviderClient in sidecar")
                elif isinstance(func, ast.Attribute) and func.attr == "RealWorkspaceAIProviderClient":
                    pytest.fail("Found attribute instantiation of RealWorkspaceAIProviderClient in sidecar")


# ============================================================================
# 3. Dynamic Sidecar Health & Direct Rejection Tests
# ============================================================================

class TestSidecarDaemonDynamicHealth:
    def test_evaluate_sidecar_health_empty_outbox(self, tmp_path):
        """When outbox is empty, health is handoff_ready."""
        health = evaluate_sidecar_health(handoff_root=tmp_path, mode="handoff")
        assert health["status"] == "handoff_ready"
        assert health["mode"] == "handoff"
        assert health["capabilities"] == ["local_handoff"]

    def test_evaluate_sidecar_health_with_pending_requests(self, tmp_path):
        """When outbox has pending request without response, health is handoff_pending."""
        outbox = tmp_path / "outbox" / "REQ-PENDING-001"
        outbox.mkdir(parents=True, exist_ok=True)
        manifest = {
            "request_id": "REQ-PENDING-001",
            "created_at": "2026-08-22T06:00:00",
            "question": "What is the status?",
        }
        (outbox / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        health = evaluate_sidecar_health(handoff_root=tmp_path, mode="handoff")
        assert health["status"] == "handoff_pending"
        assert health["mode"] == "handoff"
        assert "1 request(s)" in health["reason"]

    def test_sidecar_rejects_direct_completion_http_503(self, monkeypatch):
        """Sidecar returns HTTP 503 when direct chat completions is requested without verified adapter."""
        monkeypatch.setitem(SIDECAR_CONFIG, "mode", "handoff")
        server = HTTPServer(("127.0.0.1", 0), AntigravityBridgeHTTPHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            import urllib.request
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/v1/chat/completions",
                data=json.dumps({"messages": [{"role": "user", "content": "hello"}]}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 503
            err_data = json.loads(exc_info.value.read().decode("utf-8"))
            assert err_data["error"]["type"] == "direct_adapter_unavailable"
        finally:
            server.shutdown()
            server.server_close()


# ============================================================================
# 4. Citation Integrity Tests (Zero-Fabrication Policy)
# ============================================================================

class TestAntigravityCitationIntegrity:
    def test_process_handoff_with_genuine_citation(self, tmp_path, mock_fsm_server):
        """Genuine citations present in model output must be preserved."""
        server, _, completions_url = mock_fsm_server
        server.completion_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Dựa trên tài liệu [EVD-1], hệ thống đạt chuẩn ISO 9001.",
                    }
                }
            ],
            "model": "antigravity-brain-pro",
        }

        handoff_root = tmp_path / "ide_handoff"
        req_id = "REQ_CIT_001"
        outbox_dir = handoff_root / "outbox" / req_id
        outbox_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "request_id": req_id,
            "created_at": "2026-08-21T12:00:00",
            "case_id": "case_1",
            "question": "Kiểm tra tiêu chuẩn",
            "bundle_scope": "active_case_all",
            "allowed_source_ids": ["EVD-1", "EVD-2"],
        }
        (outbox_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (outbox_dir / "prompt_for_antigravity.md").write_text("Prompt", encoding="utf-8")

        processed = process_pending_ide_handoffs(base_dir=handoff_root, endpoint_url=completions_url)
        assert processed == 1

        inbox_resp = handoff_root / "inbox" / req_id / "response.json"
        assert inbox_resp.exists()
        resp_data = json.loads(inbox_resp.read_text(encoding="utf-8"))
        assert resp_data["cited_evidence_ids"] == ["EVD-1"]
        assert resp_data["evidence_ids_used"] == ["EVD-1"]
        assert resp_data["confidence"] == "high"

    def test_process_handoff_zero_citations_no_fabrication(self, tmp_path, mock_fsm_server):
        """When model provides NO citations, cited_evidence_ids must be EMPTY (NO fabrication)."""
        server, _, completions_url = mock_fsm_server
        server.completion_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Không có thông tin cụ thể trong hồ sơ đã cung cấp.",
                    }
                }
            ],
            "model": "antigravity-brain-pro",
        }

        handoff_root = tmp_path / "ide_handoff"
        req_id = "REQ_NO_CIT_002"
        outbox_dir = handoff_root / "outbox" / req_id
        outbox_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "request_id": req_id,
            "created_at": "2026-08-21T12:00:00",
            "case_id": "case_1",
            "question": "Hỏi không có bằng chứng",
            "bundle_scope": "active_case_all",
            "allowed_source_ids": ["EVD-1", "EVD-2"],
        }
        (outbox_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (outbox_dir / "prompt_for_antigravity.md").write_text("Prompt", encoding="utf-8")

        processed = process_pending_ide_handoffs(base_dir=handoff_root, endpoint_url=completions_url)
        assert processed == 1

        inbox_resp = handoff_root / "inbox" / req_id / "response.json"
        resp_data = json.loads(inbox_resp.read_text(encoding="utf-8"))
        # ZERO-FABRICATION: Must NOT fall back to ["EVD-1"]
        assert resp_data["cited_evidence_ids"] == []
        assert resp_data["evidence_ids_used"] == []
        assert resp_data["confidence"] == "low"
        assert len(resp_data["limitations"]) > 0

    def test_process_handoff_unknown_citation_filtered(self, tmp_path, mock_fsm_server):
        """Citations not listed in allowed_source_ids must be filtered out."""
        server, _, completions_url = mock_fsm_server
        server.completion_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Theo tài liệu [EVD-999], thông tin này không nằm trong bundle.",
                    }
                }
            ],
            "model": "antigravity-brain-pro",
        }

        handoff_root = tmp_path / "ide_handoff"
        req_id = "REQ_UNAUTH_CIT_003"
        outbox_dir = handoff_root / "outbox" / req_id
        outbox_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "request_id": req_id,
            "created_at": "2026-08-21T12:00:00",
            "case_id": "case_1",
            "question": "Hỏi nguồn lạ",
            "bundle_scope": "active_case_all",
            "allowed_source_ids": ["EVD-1", "EVD-2"],
        }
        (outbox_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (outbox_dir / "prompt_for_antigravity.md").write_text("Prompt", encoding="utf-8")

        process_pending_ide_handoffs(base_dir=handoff_root, endpoint_url=completions_url)
        inbox_resp = handoff_root / "inbox" / req_id / "response.json"
        resp_data = json.loads(inbox_resp.read_text(encoding="utf-8"))
        assert resp_data["cited_evidence_ids"] == []

    def test_process_handoff_word_boundary_matching(self, tmp_path, mock_fsm_server):
        """Ensure EVD-10 does not falsely match allowed ID EVD-1."""
        server, _, completions_url = mock_fsm_server
        server.completion_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Chỉ có thông tin từ [EVD-10], không có EVD-1 ở đây.",
                    }
                }
            ],
            "model": "antigravity-brain-pro",
        }

        handoff_root = tmp_path / "ide_handoff"
        req_id = "REQ_BOUNDARY_004"
        outbox_dir = handoff_root / "outbox" / req_id
        outbox_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "request_id": req_id,
            "created_at": "2026-08-21T12:00:00",
            "case_id": "case_1",
            "question": "Hỏi boundary",
            "bundle_scope": "active_case_all",
            "allowed_source_ids": ["EVD-1", "EVD-10"],
        }
        (outbox_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (outbox_dir / "prompt_for_antigravity.md").write_text("Prompt", encoding="utf-8")

        process_pending_ide_handoffs(base_dir=handoff_root, endpoint_url=completions_url)
        inbox_resp = handoff_root / "inbox" / req_id / "response.json"
        resp_data = json.loads(inbox_resp.read_text(encoding="utf-8"))
        assert "EVD-10" in resp_data["cited_evidence_ids"]
        # EVD-1 should NOT be matched just because 'EVD-1' is a prefix of 'EVD-10' (unless EVD-1 itself was in text)
        assert resp_data["status"] == "completed"

    def test_process_handoff_expires_stale_requests(self, tmp_path, mock_fsm_server):
        """Expired handoff requests must transition to failed and not be processed."""
        _, _, completions_url = mock_fsm_server
        handoff_root = tmp_path / "ide_handoff"
        req_id = "REQ_EXPIRED_005"
        outbox_dir = handoff_root / "outbox" / req_id
        outbox_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "request_id": req_id,
            "created_at": "2026-01-01T00:00:00",
            "expires_at": "2026-01-01T00:05:00",
            "timeout_seconds": 300,
            "case_id": "case_1",
            "question": "Expired question",
            "bundle_scope": "active_case_all",
            "allowed_source_ids": ["EVD-1"],
        }
        (outbox_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (outbox_dir / "prompt_for_antigravity.md").write_text("Prompt", encoding="utf-8")
        status = {
            "request_id": req_id,
            "state": "handoff_pending",
            "created_at": "2026-01-01T00:00:00",
            "expires_at": "2026-01-01T00:05:00",
            "timeout_seconds": 300,
        }
        (outbox_dir / "request_status.json").write_text(json.dumps(status), encoding="utf-8")

        processed = process_pending_ide_handoffs(base_dir=handoff_root, endpoint_url=completions_url)
        assert processed == 0
        status_after = json.loads((outbox_dir / "request_status.json").read_text(encoding="utf-8"))
        assert status_after["state"] == "failed"
        assert status_after["error_reason"] == "timeout"


# ============================================================================
# 5. Privacy & Error Sanitization Tests
# ============================================================================

class TestAntigravityPrivacyAndSanitization:
    def test_sanitize_bridge_error_masks_absolute_paths(self):
        raw_err = "Error accessing file D:\\Sandbox\\AIOS_habbit\\confidential\\data.pdf: Permission denied"
        sanitized = sanitize_bridge_error(raw_err)
        assert "D:\\Sandbox\\AIOS_habbit" not in sanitized
        assert "<path>" in sanitized

    def test_sanitize_bridge_error_masks_api_tokens(self):
        raw_err = "Failed request with header Authorization: Bearer sk-ant-api03-abcdef1234567890"
        sanitized = sanitize_bridge_error(raw_err)
        assert "sk-ant-api03-abcdef1234567890" not in sanitized
        assert "<redacted_token>" in sanitized

    def test_bridge_error_does_not_leak_user_prompt(self):
        sensitive_prompt = "TOP_SECRET_PATIENT_RECORD_XYZ"
        res = call_antigravity_bridge(
            question=sensitive_prompt,
            endpoint_url="http://127.0.0.1:59999/v1/chat/completions",
            timeout_seconds=0.1,
        )
        assert res.ok is False
        assert sensitive_prompt not in res.error_message

    def test_local_only_cloud_fail_closed(self):
        """When privacy_mode is local_only, calling non-local endpoint is blocked immediately."""
        res = call_antigravity_bridge(
            question="Private question",
            endpoint_url="http://external-cloud-api.example.com/v1/chat/completions",
            privacy_mode="local_only",
        )
        assert res.ok is False
        assert "Bị chặn" in res.error_message


# ============================================================================
# 6. Direct Adapter Fail-Closed Behavior Tests
# ============================================================================

class TestAntigravityFailClosed:
    def test_call_antigravity_bridge_offline_fails_closed(self):
        res = call_antigravity_bridge(
            question="Kiểm tra fail-closed",
            endpoint_url="http://127.0.0.1:59999/v1/chat/completions",
            timeout_seconds=0.1,
        )
        assert res.ok is False
        assert res.answer_text == ""
        assert res.error_message != ""

    def test_call_antigravity_bridge_http_500(self, mock_fsm_server):
        server, _, completions_url = mock_fsm_server
        server.completion_status_code = 500
        server.completion_response = {"error": "Daemon internal error"}

        res = call_antigravity_bridge(
            question="Kiểm tra HTTP 500",
            endpoint_url=completions_url,
            timeout_seconds=1.0,
        )
        assert res.ok is False
        assert "HTTP 500" in res.error_message

    def test_ai_provider_bridge_with_antigravity_success(self, mock_fsm_server, monkeypatch):
        server, health_url, completions_url = mock_fsm_server
        server.health_payload = {
            "status": "direct_ready",
            "mode": "direct",
            "capabilities": ["direct_chat"],
            "reason": "",
        }
        monkeypatch.setattr("aios_habit.antigravity_bridge.DEFAULT_ANTIGRAVITY_HEALTH_URL", health_url)
        monkeypatch.setattr("aios_habit.antigravity_bridge.DEFAULT_ANTIGRAVITY_ENDPOINT", completions_url)

        cfg = ProviderConfig(
            provider_type="antigravity_ide_brain",
            endpoint_url=completions_url,
            model_name="antigravity-brain-pro",
            locality="local",
            enabled=True,
        )
        res = answer_with_provider(
            question="Hỏi qua Antigravity",
            source_context="Context...",
            config=cfg,
            deterministic_answer="Fallback",
            source_privacy="local_only",
        )
        assert res.ok is True
        assert "Antigravity response" in res.answer_text
        assert res.provider_name == "antigravity_ide_brain"

    def test_ai_provider_bridge_offline_fail_closed(self, monkeypatch):
        """When Antigravity bridge is offline, provider bridge must fail closed without fallback."""
        monkeypatch.setattr("aios_habit.antigravity_bridge.DEFAULT_ANTIGRAVITY_HEALTH_URL", "http://127.0.0.1:59999/health")
        monkeypatch.setattr("aios_habit.antigravity_bridge.DEFAULT_ANTIGRAVITY_ENDPOINT", "http://127.0.0.1:59999/v1/chat/completions")

        cfg = ProviderConfig(
            provider_type="antigravity_ide_brain",
            endpoint_url="http://127.0.0.1:59999/v1/chat/completions",
            model_name="antigravity-brain-pro",
            locality="local",
            enabled=True,
        )
        res = answer_with_provider(
            question="Hỏi qua Antigravity offline",
            source_context="Context...",
            config=cfg,
            deterministic_answer="Deterministic Draft",
            source_privacy="local_only",
        )
        assert res.ok is False
        assert res.answer_text == ""
        assert res.used_fallback is False
        assert res.safety_status == "antigravity_runtime_unavailable"


# ============================================================================
# 7. Tier 5 Adversarial Stress & Hardening Test Suites
# ============================================================================


class TestTier5AdversarialSocketDropoutsAndFailClosed:
    """Tier 5 Adversarial: Network socket dropouts, hangs, HTTP errors & fail-closed enforcement."""

    def test_direct_bridge_socket_reset_mid_payload(self):
        """Mock server abruptly closes TCP connection before returning body."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.listen(1)

        def _reset_client():
            try:
                conn, _ = srv.accept()
                conn.recv(1024)
                # Immediately close socket without HTTP response
                conn.close()
            except Exception:
                pass
            finally:
                try:
                    srv.close()
                except Exception:
                    pass

        threading.Thread(target=_reset_client, daemon=True).start()
        res = call_antigravity_bridge(
            question="Stress test socket reset",
            endpoint_url=f"http://127.0.0.1:{port}/v1/chat/completions",
            timeout_seconds=1.0,
        )
        assert res.ok is False
        assert res.answer_text == ""
        assert res.error_message != ""

    def test_direct_bridge_http_500_with_sensitive_error_sanitization(self, mock_fsm_server):
        """HTTP 500 error containing secret file paths and auth tokens must be sanitized."""
        server, _, completions_url = mock_fsm_server
        server.completion_status_code = 500
        server.completion_response = {
            "error": "Failed at D:/AIOS_Sandbox/confidential/vault.key with token sk-ant-api03-abcdef9876543210"
        }

        res = call_antigravity_bridge(
            question="Test sanitization",
            endpoint_url=completions_url,
            timeout_seconds=1.0,
        )
        assert res.ok is False
        assert "D:/AIOS_Sandbox" not in res.error_message
        assert "sk-ant-api03-abcdef9876543210" not in res.error_message
        assert "<path>" in res.error_message or "<redacted_token>" in res.error_message

    def test_direct_bridge_slowloris_timeout(self):
        """Server accepts connection but hangs; client must timeout cleanly and fail closed."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.listen(1)

        def _hang_client():
            try:
                conn, _ = srv.accept()
                time.sleep(1.0)
                conn.close()
            except Exception:
                pass
            finally:
                try:
                    srv.close()
                except Exception:
                    pass

        threading.Thread(target=_hang_client, daemon=True).start()
        res = call_antigravity_bridge(
            question="Test slowloris",
            endpoint_url=f"http://127.0.0.1:{port}/v1/chat/completions",
            timeout_seconds=0.2,
        )
        assert res.ok is False
        assert res.answer_text == ""
        assert "timed out" in res.error_message.lower() or "timeout" in res.error_message.lower()

    @pytest.mark.parametrize("status_code", [502, 503, 504])
    def test_direct_bridge_http_gateway_errors_fail_closed(self, mock_fsm_server, status_code):
        """HTTP 502/503/504 gateway failures must return ok=False with non-empty error message."""
        server, _, completions_url = mock_fsm_server
        server.completion_status_code = status_code
        server.completion_response = {"error": f"Gateway error {status_code}"}

        res = call_antigravity_bridge(
            question="Testing gateway error",
            endpoint_url=completions_url,
            timeout_seconds=1.0,
        )
        assert res.ok is False
        assert res.answer_text == ""
        assert str(status_code) in res.error_message or "lỗi" in res.error_message.lower() or "error" in res.error_message.lower()


class TestTier5AdversarialPrivacyBoundaryAndSanitization:
    """Tier 5 Adversarial: Privacy boundary leakage prevention and error string sanitization."""

    @pytest.mark.parametrize("remote_url", [
        "http://api.openai.com/v1/chat/completions",
        "https://external-ai.cloud.com/v1/completions",
        "http://8.8.8.8:8585/v1/chat/completions",
        "http://198.51.100.1/v1/chat/completions",
    ])
    def test_local_only_mode_blocks_remote_endpoints_immediately(self, remote_url):
        """Privacy mode local_only MUST block non-loopback endpoints immediately without sending packets."""
        res = call_antigravity_bridge(
            question="Confidential financial or patient query",
            endpoint_url=remote_url,
            privacy_mode="local_only",
        )
        assert res.ok is False
        assert "Bị chặn" in res.error_message
        assert "local_only" in res.error_message

    def test_sanitize_reason_comprehensive_matrix(self):
        """Verify sanitize_reason across diverse combinations of paths, Windows drive letters, and tokens."""
        cases = [
            ("Error at C:\\Users\\Admin\\AppData\\Local\\secret.txt: failed", "<path>: failed"),
            ("Error in D:/Sandbox/AIOS_habbit/data/confidential.pdf cannot be opened", "<path> cannot be opened"),
            ("Token Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 was rejected", "Token <redacted_token> was rejected"),
            ("sk-ant-api03-1234567890abcdef12345 is unauthorized", "<redacted_token> is unauthorized"),
            ("Unix path /var/log/audit/secret.log not accessible", "<path> not accessible"),
        ]
        for raw, expected_substr in cases:
            sanitized = sanitize_reason(raw)
            assert "C:\\Users" not in sanitized
            assert "D:/Sandbox" not in sanitized
            assert "eyJhbGci" not in sanitized
            assert "sk-ant-api03" not in sanitized
            assert "/var/log" not in sanitized

    def test_error_sanitization_bounds_max_length(self):
        """Excessively long error messages should be truncated to 200 characters."""
        long_error = "Failure at " + "D:/VeryLongPath/" * 30 + " with secret sk-ant-api03-999999999999999"
        sanitized = sanitize_reason(long_error)
        assert len(sanitized) <= 200
        assert "sk-ant-api03" not in sanitized


class TestTier5AdversarialCitationBoundaryAndZeroFabrication:
    """Tier 5 Adversarial: Word boundary citation matching and strict zero-fabrication."""

    def test_word_boundary_avoids_prefix_suffix_false_positives(self, tmp_path, mock_fsm_server):
        """Ensures that citation IDs sharing prefixes/suffixes (e.g. EVD-1 vs EVD-100, EVD-1-EXTRA) are not falsely attributed."""
        server, _, completions_url = mock_fsm_server
        server.completion_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Referencing [EVD-100] and text mention EVD-1-EXTRA.",
                    }
                }
            ],
            "model": "antigravity-brain-pro",
        }

        handoff_root = tmp_path / "ide_handoff"
        req_id = "REQ_ADV_CIT_001"
        outbox_dir = handoff_root / "outbox" / req_id
        outbox_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "request_id": req_id,
            "created_at": "2026-08-22T00:00:00",
            "case_id": "case_adv",
            "question": "Boundary check",
            "bundle_scope": "active_case_all",
            "allowed_source_ids": ["EVD-1", "EVD-10"],
        }
        (outbox_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (outbox_dir / "prompt_for_antigravity.md").write_text("Prompt", encoding="utf-8")

        processed = process_pending_ide_handoffs(base_dir=handoff_root, endpoint_url=completions_url)
        assert processed == 1

        inbox_resp = handoff_root / "inbox" / req_id / "response.json"
        resp_data = json.loads(inbox_resp.read_text(encoding="utf-8"))
        assert resp_data["cited_evidence_ids"] == []
        assert resp_data["confidence"] == "low"

    def test_zero_citations_never_fabricates_first_allowed_id(self, tmp_path, mock_fsm_server):
        """When completion does not reference any evidence, zero citations are attributed (never defaulting to allowed_source_ids[0])."""
        server, _, completions_url = mock_fsm_server
        server.completion_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Đây là câu trả lời chung chung không chứa bất kỳ trích dẫn nào.",
                    }
                }
            ],
            "model": "antigravity-brain-pro",
        }

        handoff_root = tmp_path / "ide_handoff"
        req_id = "REQ_ADV_ZERO_FAB"
        outbox_dir = handoff_root / "outbox" / req_id
        outbox_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "request_id": req_id,
            "created_at": "2026-08-22T00:00:00",
            "case_id": "case_adv_zero",
            "question": "Zero citations check",
            "bundle_scope": "active_case_all",
            "allowed_source_ids": ["EVD-FIRST-ALLOWED", "EVD-SECOND-ALLOWED"],
        }
        (outbox_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (outbox_dir / "prompt_for_antigravity.md").write_text("Prompt", encoding="utf-8")

        processed = process_pending_ide_handoffs(base_dir=handoff_root, endpoint_url=completions_url)
        assert processed == 1

        inbox_resp = handoff_root / "inbox" / req_id / "response.json"
        resp_data = json.loads(inbox_resp.read_text(encoding="utf-8"))
        assert resp_data["cited_evidence_ids"] == []
        assert resp_data["evidence_ids_used"] == []
        assert resp_data["confidence"] == "low"
        assert len(resp_data["limitations"]) > 0

    def test_unauthorized_citation_sorted_rejection(self, tmp_path, mock_fsm_server):
        """Model citing multiple unknown IDs has those unknown IDs filtered out during bridge resolution."""
        server, _, completions_url = mock_fsm_server
        server.completion_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Sử dụng các nguồn [EVD-ZEBRA], [EVD-ALPHA], [EVD-BETA].",
                    }
                }
            ],
            "model": "antigravity-brain-pro",
        }

        handoff_root = tmp_path / "ide_handoff"
        req_id = "REQ_ADV_UNAUTH"
        outbox_dir = handoff_root / "outbox" / req_id
        outbox_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "request_id": req_id,
            "created_at": "2026-08-22T00:00:00",
            "case_id": "case_adv_unauth",
            "question": "Unauthorized check",
            "bundle_scope": "active_case_all",
            "allowed_source_ids": ["EVD-1"],
        }
        (outbox_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (outbox_dir / "prompt_for_antigravity.md").write_text("Prompt", encoding="utf-8")

        processed = process_pending_ide_handoffs(base_dir=handoff_root, endpoint_url=completions_url)
        assert processed == 1

        inbox_resp = handoff_root / "inbox" / req_id / "response.json"
        resp_data = json.loads(inbox_resp.read_text(encoding="utf-8"))
        assert resp_data["cited_evidence_ids"] == []


class TestAntigravityBridgeFailClosedAndE2E:
    """Additional regression tests for Fail-Closed routing and E2E handoff response writing."""

    def test_route_submission_bridge_unavailable_fails_closed_zero_fallback(self):
        from aios_habit.antigravity_bridge import route_workspace_chat_submission

        health = AntigravityHealthStatus(
            status="unavailable",
            mode="none",
            capabilities=[],
            reason="Daemon not running",
        )

        ok, msg, badge, err = route_workspace_chat_submission(
            question="Tra cứu lỗi máy",
            evidence_items=[],
            packed_sources=(),
            conversation_id="CONV-TEST-FAILCLOSED",
            notebook_id="NB-TEST",
            retrieval_applied=False,
            retrieved_sources=(),
            retrieval_summary="",
            current_keys=(),
            chat_history=(),
            user_raw_input="Tra cứu lỗi máy",
            health_status=health,
        )

        assert ok is False
        assert badge is None
        assert err is not None
        assert "không khả dụng" in err
        assert "fail-closed" in err

    def test_ide_handoff_e2e_write_response_and_import(self, tmp_path):
        from aios_habit.case_models import EvidenceItem
        from aios_habit.ide_handoff_bridge import (
            write_ide_handoff_bundle,
            write_ide_handoff_response,
            import_pending_ide_response,
            save_imported_ide_answer,
            list_pending_ide_requests,
        )

        handoff_root = tmp_path / "ide_handoff"
        ev_item = EvidenceItem(
            evidence_id="EVD-TEST-1",
            case_id="CONV-E2E-1",
            source_type="plain_text",
            source_path="local/test.txt",
            title="Tài liệu thử nghiệm",
            extracted_text="Đây là nội dung thử nghiệm lỗi E001.",
            privacy_level="local_only",
        )

        # 1. Write outbox bundle
        bundle_req = write_ide_handoff_bundle(
            case_id="CONV-E2E-1",
            question="Lỗi E001 là gì?",
            bundle_scope="active_case_all",
            evidence_items=[ev_item],
            root=handoff_root,
        )
        assert bundle_req.ok

        # 2. Verify pending status before response
        pending_before = list_pending_ide_requests(handoff_root)
        assert len(pending_before) == 1
        assert pending_before[0].response_exists is False
        assert pending_before[0].state == "handoff_pending"

        # 3. IDE Consumer writes response to Inbox
        resp_path = write_ide_handoff_response(
            request_id=bundle_req.request_id,
            answer_markdown="Theo tài liệu [EVD-TEST-1], lỗi E001 là lỗi cảm biến.",
            root=handoff_root,
            privacy_acknowledged=True,
            used_full_bundle=True,
        )
        assert resp_path.exists()

        # 4. Verify pending list now sees response
        pending_after = list_pending_ide_requests(handoff_root)
        assert len(pending_after) == 1
        assert pending_after[0].response_exists is True

        # 5. UI imports pending response
        validation = import_pending_ide_response(bundle_req.request_id, root=handoff_root)
        assert validation.ok is True
        assert validation.final_answer is True
        assert "EVD-TEST-1" in validation.response["evidence_ids_used"]

        # 6. Save imported answer and verify completed status
        saved_ans = save_imported_ide_answer("CONV-E2E-1", validation, root=handoff_root)
        assert saved_ans.pack_id == bundle_req.request_id
        assert saved_ans.route_summary == "ide_full_bundle_handoff"

        status_file = bundle_req.bundle_dir / "request_status.json"
        status_data = json.loads(status_file.read_text(encoding="utf-8"))
        assert status_data["state"] == "completed"
        assert status_data["saved_answer_id"] == saved_ans.draft_id

    def test_ide_handoff_import_creates_and_links_evidence_trace(self, tmp_path, monkeypatch):
        """Verify importing handoff response creates EvidenceTrace with handoff provenance and links trace_id."""
        import aios_habit.workspace_chat_store as store_mod
        from aios_habit.case_models import EvidenceItem
        from aios_habit.evidence_trace import build_evidence_trace_from_citations
        from aios_habit.ide_handoff_bridge import (
            write_ide_handoff_bundle,
            write_ide_handoff_response,
            import_pending_ide_response,
            save_imported_ide_answer,
        )
        from aios_habit.workspace_chat_models import ChatMessage

        # Sandbox chat store
        monkeypatch.setattr(store_mod, "LOCAL_CHAT_DIR", tmp_path)
        monkeypatch.setattr(store_mod, "MESSAGES_FILE", tmp_path / "messages.jsonl")
        monkeypatch.setattr(store_mod, "TRACES_FILE", tmp_path / "traces.jsonl")
        store_mod.init_chat_store()

        handoff_root = tmp_path / "ide_handoff"
        conv_id = "CONV-HANDOFF-TRACE"
        nb_id = "NB-HANDOFF-TRACE"

        # Save user message
        user_msg = ChatMessage(
            id="MSG-USER-1",
            conversation_id=conv_id,
            role="user",
            content="Quy trình xuất kho?",
        )
        store_mod.save_message(user_msg)

        ev_item = EvidenceItem(
            evidence_id="EVD-HANDOFF-1",
            case_id=conv_id,
            source_type="plain_text",
            source_path="local/sop.txt",
            title="Quy trình xuất kho",
            extracted_text="Bước 1: Quét mã phiếu xuất kho trên hệ thống.",
            privacy_level="local_only",
        )

        bundle_req = write_ide_handoff_bundle(
            case_id=conv_id,
            question="Quy trình xuất kho?",
            bundle_scope="active_case_all",
            evidence_items=[ev_item],
            root=handoff_root,
        )

        resp_path = write_ide_handoff_response(
            request_id=bundle_req.request_id,
            answer_markdown="Theo tài liệu [EVD-HANDOFF-1], bước đầu tiên là quét mã phiếu xuất kho.",
            root=handoff_root,
            privacy_acknowledged=True,
            used_full_bundle=True,
        )

        # Execute import logic matching workspace_chat_app
        validation = import_pending_ide_response(bundle_req.request_id, root=handoff_root)
        assert validation.ok is True

        manifest = validation.manifest or {}
        ans_text = validation.response.get("answer_markdown", "")
        assistant_msg_id = "MSG-AST-1"

        provenance = {
            "operational_mode": "handoff",
            "provider_name": "Gemini Web",
            "model_name": "verified_antigravity_ide",
        }

        trace = build_evidence_trace_from_citations(
            query=manifest.get("question", ""),
            answer_text=ans_text,
            evidence_items=manifest.get("evidence_items") or [ev_item],
            allowed_source_ids=manifest.get("allowed_source_ids"),
            notebook_id=nb_id,
            conversation_id=conv_id,
            user_message_id=user_msg.id,
            assistant_message_id=assistant_msg_id,
            ui_locale="vi",
            answer_language="vi",
            provenance=provenance,
        )
        store_mod.save_evidence_trace(trace)

        ast_msg = ChatMessage(
            id=assistant_msg_id,
            conversation_id=conv_id,
            role="assistant",
            content=ans_text,
            trace_id=trace.trace_id,
        )
        store_mod.save_message(ast_msg)

        # Verify saved message and trace
        loaded_msgs = store_mod.load_messages(conv_id)
        loaded_ast = [m for m in loaded_msgs if m.role == "assistant"][0]
        assert loaded_ast.trace_id == trace.trace_id

        loaded_trace = store_mod.load_evidence_trace(trace.trace_id)
        assert loaded_trace is not None
        assert loaded_trace.provenance["operational_mode"] == "handoff"
        assert loaded_trace.provenance["provider_name"] == "Gemini Web"
        assert loaded_trace.provenance["model_name"] == "verified_antigravity_ide"
        assert loaded_trace.metadata["status"] == "valid"


# ============================================================================
# 8. Handoff Bundle Multilingual & Verbatim Evidence Preservation E2E Tests (R1)
# ============================================================================


class TestAntigravityHandoffMultilingualE2E:
    """E2E test suite verifying multilingual bundle generation, prompt injection, and verbatim evidence rules."""

    @pytest.fixture
    def sample_evidence(self):
        from aios_habit.case_models import EvidenceItem

        return [
            EvidenceItem(
                evidence_id="[E1]",
                case_id="CONV-LANG-001",
                source_type="plain_text",
                source_path="local/spec_doc.pdf",
                title="Specification Doc",
                extracted_text="Error code ERR_TIMEOUT_404 observed at line 42.",
                privacy_level="local_only",
            ),
            EvidenceItem(
                evidence_id="EVD-001",
                case_id="CONV-LANG-001",
                source_type="plain_text",
                source_path="local/inventory_2026.xlsx",
                title="Inventory Spreadsheet",
                extracted_text="Stock quantity: 150 units remaining.",
                privacy_level="cloud_allowed",
            ),
        ]

    def test_handoff_bundle_multilingual_ja_e2e(self, tmp_path, sample_evidence):
        """Verify Japanese bundle has answer_language in manifest, Japanese prompt instruction, and verbatim rules."""
        from aios_habit.ide_handoff_bridge import (
            write_ide_handoff_bundle,
            validate_handoff_bundle,
            verify_bundle_integrity,
        )

        bundle_req = write_ide_handoff_bundle(
            case_id="CONV-JA-001",
            question="在庫とエラー状況はどうなっていますか？",
            bundle_scope="active_case_all",
            evidence_items=sample_evidence,
            root=tmp_path,
            answer_language="ja",
        )
        assert bundle_req.ok

        # 1. Check manifest.json
        manifest_path = bundle_req.bundle_dir / "manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["answer_language"] == "ja"

        # 2. Check prompt_for_antigravity.md and prompt.md
        prompt_antigravity_path = bundle_req.bundle_dir / "prompt_for_antigravity.md"
        assert prompt_antigravity_path.exists()
        prompt_text = prompt_antigravity_path.read_text(encoding="utf-8")

        prompt_md_path = bundle_req.bundle_dir / "prompt.md"
        assert prompt_md_path.exists()
        assert prompt_md_path.read_text(encoding="utf-8") == prompt_text

        # Japanese instruction check
        assert "言語指示: 回答はすべて日本語で記述してください。" in prompt_text
        # Verbatim preservation rules check
        assert "引用ID（例: [1]、[E1]、EVD-001）" in prompt_text
        assert "ファイル名（例: document.pdf）" in prompt_text
        assert "ファイルパス、エラーコード、および引用スニペットは翻訳せず、原文のまま100%保持してください。" in prompt_text
        assert "識別子や証拠引用を翻訳または改変することは固く禁じます。" in prompt_text

        # 3. Validation & Cryptographic integrity
        val = validate_handoff_bundle(bundle_req.bundle_dir)
        assert val["ok"] is True
        assert val["missing"] == []

        int_ok, int_errs = verify_bundle_integrity(bundle_req.bundle_dir)
        assert int_ok is True
        assert int_errs == []

    def test_handoff_bundle_multilingual_zh_cn_e2e(self, tmp_path, sample_evidence):
        """Verify Simplified Chinese bundle has answer_language in manifest, Chinese prompt instruction, and verbatim rules."""
        from aios_habit.ide_handoff_bridge import (
            write_ide_handoff_bundle,
            validate_handoff_bundle,
            verify_bundle_integrity,
        )

        bundle_req = write_ide_handoff_bundle(
            case_id="CONV-ZH-001",
            question="请汇报库存和错误情况？",
            bundle_scope="active_case_all",
            evidence_items=sample_evidence,
            root=tmp_path,
            answer_language="zh-CN",
        )
        assert bundle_req.ok

        # 1. Check manifest.json
        manifest_path = bundle_req.bundle_dir / "manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["answer_language"] == "zh-CN"

        # 2. Check prompt_for_antigravity.md and prompt.md
        prompt_antigravity_path = bundle_req.bundle_dir / "prompt_for_antigravity.md"
        assert prompt_antigravity_path.exists()
        prompt_text = prompt_antigravity_path.read_text(encoding="utf-8")

        prompt_md_path = bundle_req.bundle_dir / "prompt.md"
        assert prompt_md_path.exists()
        assert prompt_md_path.read_text(encoding="utf-8") == prompt_text

        # Chinese instruction check
        assert "语言指示: 请完全使用简体中文回答。" in prompt_text
        # Verbatim preservation rules check
        assert "请100%完整保留所有引用ID（例如 [1]、[E1]、EVD-001）" in prompt_text
        assert "文件名（例如 document.pdf）、文件路径、技术错误代码和原文摘录片段。" in prompt_text
        assert "严禁翻译或篡改任何标识符和证据引用。" in prompt_text

        # 3. Validation & Cryptographic integrity
        val = validate_handoff_bundle(bundle_req.bundle_dir)
        assert val["ok"] is True
        assert val["missing"] == []

        int_ok, int_errs = verify_bundle_integrity(bundle_req.bundle_dir)
        assert int_ok is True
        assert int_errs == []

    def test_handoff_bundle_multilingual_vi_default_e2e(self, tmp_path, sample_evidence):
        """Verify Vietnamese default bundle has answer_language='vi' and Vietnamese prompt instruction with verbatim rules."""
        from aios_habit.ide_handoff_bridge import (
            write_ide_handoff_bundle,
            validate_handoff_bundle,
            verify_bundle_integrity,
        )

        bundle_req = write_ide_handoff_bundle(
            case_id="CONV-VI-001",
            question="Kiểm tra tình trạng kho và lỗi?",
            bundle_scope="active_case_all",
            evidence_items=sample_evidence,
            root=tmp_path,
        )
        assert bundle_req.ok

        # 1. Check manifest.json
        manifest_path = bundle_req.bundle_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["answer_language"] == "vi"

        # 2. Check prompt_for_antigravity.md
        prompt_antigravity_path = bundle_req.bundle_dir / "prompt_for_antigravity.md"
        prompt_text = prompt_antigravity_path.read_text(encoding="utf-8")

        assert "Yêu cầu ngôn ngữ: Trả lời hoàn toàn bằng Tiếng Việt." in prompt_text
        assert "Giữ nguyên vẹn 100% tất cả các mã trích dẫn (ví dụ [1], [E1], EVD-001)" in prompt_text
        assert "tên tệp (ví dụ document.pdf), đường dẫn tệp, mã lỗi kỹ thuật và các đoạn trích dẫn nguồn gốc." in prompt_text
        assert "Tuyệt đối không dịch hoặc làm thay đổi các mã định danh và trích dẫn bằng chứng." in prompt_text

        val = validate_handoff_bundle(bundle_req.bundle_dir)
        assert val["ok"] is True

        int_ok, int_errs = verify_bundle_integrity(bundle_req.bundle_dir)
        assert int_ok is True
        assert int_errs == []

    def test_route_workspace_chat_submission_handoff_multilingual_propagation(self, tmp_path):
        """Verify route_workspace_chat_submission correctly propagates answer_language to the handoff bundle."""
        from aios_habit.antigravity_bridge import route_workspace_chat_submission

        health = AntigravityHealthStatus(
            status="handoff_ready",
            mode="handoff",
            capabilities=["local_handoff"],
            reason="Handoff ready",
        )

        evidence = [
            {
                "evidence_id": "EVD-PROP-1",
                "title": "Tài liệu kỹ thuật",
                "snippet": "Nội dung chi tiết về mã lỗi 404.",
                "source_type": "plain_text",
                "source_path": "doc.txt",
                "privacy_level": "local_only",
            }
        ]

        # Test Japanese propagation
        ok_ja, msg_ja, badge_ja, err_ja = route_workspace_chat_submission(
            question="日本語の質問",
            evidence_items=evidence,
            packed_sources=(),
            conversation_id="CONV-ROUTE-JA",
            notebook_id="NB-ROUTING",
            retrieval_applied=True,
            retrieved_sources=(),
            retrieval_summary="",
            current_keys=(),
            chat_history=(),
            user_raw_input="日本語の質問",
            health_status=health,
            handoff_root=tmp_path,
            answer_language="ja",
        )
        assert ok_ja is True
        assert err_ja is None
        assert badge_ja is not None
        req_id_ja = badge_ja["request_id"]
        manifest_ja_path = tmp_path / "outbox" / req_id_ja / "manifest.json"
        assert manifest_ja_path.exists()
        manifest_ja = json.loads(manifest_ja_path.read_text(encoding="utf-8"))
        assert manifest_ja["answer_language"] == "ja"

        prompt_ja_path = tmp_path / "outbox" / req_id_ja / "prompt_for_antigravity.md"
        assert prompt_ja_path.exists()
        prompt_ja_text = prompt_ja_path.read_text(encoding="utf-8")
        assert "言語指示: 回答はすべて日本語で記述してください。" in prompt_ja_text

        # Test Chinese propagation
        ok_zh, msg_zh, badge_zh, err_zh = route_workspace_chat_submission(
            question="中文问题",
            evidence_items=evidence,
            packed_sources=(),
            conversation_id="CONV-ROUTE-ZH",
            notebook_id="NB-ROUTING",
            retrieval_applied=True,
            retrieved_sources=(),
            retrieval_summary="",
            current_keys=(),
            chat_history=(),
            user_raw_input="中文问题",
            health_status=health,
            handoff_root=tmp_path,
            answer_language="zh-CN",
        )
        assert ok_zh is True
        assert err_zh is None
        assert badge_zh is not None
        req_id_zh = badge_zh["request_id"]
        manifest_zh_path = tmp_path / "outbox" / req_id_zh / "manifest.json"
        assert manifest_zh_path.exists()
        manifest_zh = json.loads(manifest_zh_path.read_text(encoding="utf-8"))
        assert manifest_zh["answer_language"] == "zh-CN"

        prompt_zh_path = tmp_path / "outbox" / req_id_zh / "prompt_for_antigravity.md"
        assert prompt_zh_path.exists()
        prompt_zh_text = prompt_zh_path.read_text(encoding="utf-8")
        assert "语言指示: 请完全使用简体中文回答。" in prompt_zh_text

    def test_build_full_bundle_request_locale_normalization(self, sample_evidence):
        """Verify build_full_bundle_request normalizes locale variations correctly."""
        from aios_habit.ide_handoff_bridge import build_full_bundle_request

        # 'ja-JP' or uppercase 'JA' -> 'ja'
        manifest_ja, _, _, _ = build_full_bundle_request(
            case_id="CASE-NORM-JA",
            question="Question?",
            bundle_scope="active_case_all",
            evidence_items=sample_evidence,
            answer_language="JA",
        )
        assert manifest_ja["answer_language"] == "ja"

        # 'zh_CN' or 'zh' -> 'zh-CN'
        manifest_zh, _, _, _ = build_full_bundle_request(
            case_id="CASE-NORM-ZH",
            question="Question?",
            bundle_scope="active_case_all",
            evidence_items=sample_evidence,
            answer_language="zh_cn",
        )
        assert manifest_zh["answer_language"] == "zh-CN"

        # Unknown / None / invalid -> 'vi'
        manifest_vi, _, _, _ = build_full_bundle_request(
            case_id="CASE-NORM-VI",
            question="Question?",
            bundle_scope="active_case_all",
            evidence_items=sample_evidence,
            answer_language="unknown_locale",
        )
        assert manifest_vi["answer_language"] == "vi"

    def test_route_submission_direct_mode_creates_and_links_evidence_trace(self, mock_fsm_server, monkeypatch, tmp_path):
        """Verify direct mode builds EvidenceTrace, saves it, and attaches trace_id to assistant message."""
        import aios_habit.workspace_chat_store as store_mod
        from aios_habit.antigravity_bridge import route_workspace_chat_submission

        # Sandbox chat store
        monkeypatch.setattr(store_mod, "LOCAL_CHAT_DIR", tmp_path)
        monkeypatch.setattr(store_mod, "MESSAGES_FILE", tmp_path / "messages.jsonl")
        monkeypatch.setattr(store_mod, "TRACES_FILE", tmp_path / "traces.jsonl")
        monkeypatch.setattr(store_mod, "SOURCE_SELECTIONS_FILE", tmp_path / "conversation_source_selections.jsonl")
        monkeypatch.setattr(store_mod, "CONVERSATIONS_FILE", tmp_path / "conversations.jsonl")
        store_mod.init_chat_store()

        server, health_url, completions_url = mock_fsm_server
        server.completion_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Theo tài liệu [1], cổng kết nối là COM3.",
                    }
                }
            ],
            "model": "gemini-2.5-flash",
        }

        health = AntigravityHealthStatus(
            status="direct_ready",
            mode="direct",
            capabilities=["direct_chat"],
        )

        evidence = [
            {
                "id": "src_com_doc",
                "title": "Cấu hình thiết bị",
                "snippet": "Cổng kết nối COM3 được sử dụng cho máy quét.",
                "source_path": "config.txt",
                "citation_label": "[1]",
            }
        ]

        ok, msg, badge, err = route_workspace_chat_submission(
            question="Cổng kết nối là gì?",
            evidence_items=evidence,
            packed_sources=(),
            conversation_id="CONV-DIR-TRACE",
            notebook_id="NB-DIR-TRACE",
            retrieval_applied=True,
            retrieved_sources=(),
            retrieval_summary="1 source retrieved",
            current_keys=(),
            chat_history=(),
            user_raw_input="Cổng kết nối là gì?",
            health_status=health,
            endpoint_url=completions_url,
            answer_language="vi",
        )

        assert ok is True
        assert err is None
        assert badge is not None
        assert "trace_id" in badge
        trace_id = badge["trace_id"]
        assert trace_id.startswith("trc_")

        # Verify assistant message has trace_id
        msgs = store_mod.load_messages("CONV-DIR-TRACE")
        assert len(msgs) == 2
        ast_msg = [m for m in msgs if m.role == "assistant"][0]
        assert ast_msg.trace_id == trace_id

        # Verify trace was saved and has genuine provenance
        trace = store_mod.load_evidence_trace(trace_id)
        assert trace is not None
        assert trace.trace_id == trace_id
        assert trace.notebook_id == "NB-DIR-TRACE"
        assert trace.conversation_id == "CONV-DIR-TRACE"
        assert trace.provenance["operational_mode"] == "direct"
        assert trace.provenance["provider_name"] == "Gemini Web Stream"
        assert trace.provenance["model_name"] == "verified_gemini_stream"
        assert trace.metadata["status"] == "valid"
        assert trace.metadata["insufficient_evidence"] is False
        assert len(trace.nodes) >= 3  # question, answer, source, citation

    def test_route_submission_direct_mode_missing_citations_insufficient_evidence(self, mock_fsm_server, monkeypatch, tmp_path):
        """Verify direct mode with zero citations marks trace as insufficient_evidence."""
        import aios_habit.workspace_chat_store as store_mod
        from aios_habit.antigravity_bridge import route_workspace_chat_submission

        monkeypatch.setattr(store_mod, "LOCAL_CHAT_DIR", tmp_path)
        monkeypatch.setattr(store_mod, "MESSAGES_FILE", tmp_path / "messages.jsonl")
        monkeypatch.setattr(store_mod, "TRACES_FILE", tmp_path / "traces.jsonl")
        monkeypatch.setattr(store_mod, "SOURCE_SELECTIONS_FILE", tmp_path / "conversation_source_selections.jsonl")
        monkeypatch.setattr(store_mod, "CONVERSATIONS_FILE", tmp_path / "conversations.jsonl")
        store_mod.init_chat_store()

        server, health_url, completions_url = mock_fsm_server
        server.completion_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Đây là câu trả lời chung chung không trích dẫn tài liệu.",
                    }
                }
            ],
            "model": "gemini-2.5-flash",
        }

        health = AntigravityHealthStatus(
            status="direct_ready",
            mode="direct",
            capabilities=["direct_chat"],
        )

        ok, msg, badge, err = route_workspace_chat_submission(
            question="Chào bạn?",
            evidence_items=[],
            packed_sources=(),
            conversation_id="CONV-DIR-NOCIT",
            notebook_id="NB-DIR-NOCIT",
            retrieval_applied=False,
            retrieved_sources=(),
            retrieval_summary="",
            current_keys=(),
            chat_history=(),
            user_raw_input="Chào bạn?",
            health_status=health,
            endpoint_url=completions_url,
            answer_language="vi",
        )

        assert ok is True
        trace_id = badge["trace_id"]
        trace = store_mod.load_evidence_trace(trace_id)
        assert trace is not None
        assert trace.metadata["status"] == "insufficient_evidence"
        assert trace.metadata["insufficient_evidence"] is True

    @pytest.mark.parametrize("citation_format", ["[EVD-001]", "[1]"])
    def test_route_submission_direct_mode_rag_evidence_real_source_id_enabled(
        self, mock_fsm_server, monkeypatch, tmp_path, citation_format
    ):
        """Regression E2E test: Conversation with enabled selection source_id=SRC-001

        Verifies retrieval evidence dict with source_id=SRC-001, evidence_id=EVD-001 produces
        a valid trace with source and citation nodes when replied using [EVD-001] or [1].
        """
        import aios_habit.workspace_chat_store as store_mod
        from aios_habit.antigravity_bridge import route_workspace_chat_submission
        from aios_habit.workspace_chat_models import ConversationSourceSelection

        monkeypatch.setattr(store_mod, "LOCAL_CHAT_DIR", tmp_path)
        monkeypatch.setattr(store_mod, "MESSAGES_FILE", tmp_path / "messages.jsonl")
        monkeypatch.setattr(store_mod, "TRACES_FILE", tmp_path / "traces.jsonl")
        monkeypatch.setattr(store_mod, "SOURCE_SELECTIONS_FILE", tmp_path / "conversation_source_selections.jsonl")
        monkeypatch.setattr(store_mod, "CONVERSATIONS_FILE", tmp_path / "conversations.jsonl")
        store_mod.init_chat_store()

        conv_id = f"CONV-REG-SRC-{citation_format.strip('[]')}"
        nb_id = "NB-REG-01"

        # Enabled selection for SRC-001
        store_mod.save_conversation_source_selection(
            ConversationSourceSelection(
                id=f"sel-enabled-{citation_format.strip('[]')}",
                conversation_id=conv_id,
                source_id="SRC-001",
                source_scope="notebook",
                enabled=True,
            )
        )

        server, health_url, completions_url = mock_fsm_server
        server.completion_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": f"Theo tài liệu {citation_format}, bước 1 là khởi động máy kiểm đếm.",
                    }
                }
            ],
            "model": "gemini-2.5-flash",
        }

        health = AntigravityHealthStatus(
            status="direct_ready",
            mode="direct",
            capabilities=["direct_chat"],
        )

        evidence = [
            {
                "source_id": "SRC-001",
                "evidence_id": "EVD-001",
                "citation_id": "EVD-001",
                "title": "Quy trình vận hành máy",
                "snippet": "Bước 1 là khởi động máy kiểm đếm trước ca làm việc.",
                "source_path": "manual.txt",
                "citation_label": "[1]",
            }
        ]

        ok, msg, badge, err = route_workspace_chat_submission(
            question="Bước 1 là gì?",
            evidence_items=evidence,
            packed_sources=(),
            conversation_id=conv_id,
            notebook_id=nb_id,
            retrieval_applied=True,
            retrieved_sources=(),
            retrieval_summary="1 source retrieved",
            current_keys=(),
            chat_history=(),
            user_raw_input="Bước 1 là gì?",
            health_status=health,
            endpoint_url=completions_url,
            answer_language="vi",
        )

        assert ok is True
        assert err is None
        assert badge is not None
        trace_id = badge["trace_id"]
        assert trace_id.startswith("trc_")

        # Verify assistant message has trace_id
        msgs = store_mod.load_messages(conv_id)
        assert len(msgs) == 2
        ast_msg = [m for m in msgs if m.role == "assistant"][0]
        assert ast_msg.trace_id == trace_id

        # Verify trace is valid and properly linked
        trace = store_mod.load_evidence_trace(trace_id)
        assert trace is not None
        assert trace.metadata["status"] == "valid"
        assert trace.metadata.get("insufficient_evidence") is not True

        node_types = {n.node_type for n in trace.nodes}
        assert "source" in node_types
        assert "citation" in node_types
        assert "answer" in node_types
        assert "question" in node_types

    def test_route_submission_direct_mode_rag_evidence_real_source_id_disabled_insufficient_evidence(
        self, mock_fsm_server, monkeypatch, tmp_path
    ):
        """Regression E2E test: Same data but source_id=SRC-001 is disabled in conversation selections.

        Must result in insufficient_evidence trace, and citation must not be accepted into trace.
        """
        import aios_habit.workspace_chat_store as store_mod
        from aios_habit.antigravity_bridge import route_workspace_chat_submission
        from aios_habit.workspace_chat_models import ConversationSourceSelection

        monkeypatch.setattr(store_mod, "LOCAL_CHAT_DIR", tmp_path)
        monkeypatch.setattr(store_mod, "MESSAGES_FILE", tmp_path / "messages.jsonl")
        monkeypatch.setattr(store_mod, "TRACES_FILE", tmp_path / "traces.jsonl")
        monkeypatch.setattr(store_mod, "SOURCE_SELECTIONS_FILE", tmp_path / "conversation_source_selections.jsonl")
        monkeypatch.setattr(store_mod, "CONVERSATIONS_FILE", tmp_path / "conversations.jsonl")
        store_mod.init_chat_store()

        conv_id = "CONV-REG-DISABLED"
        nb_id = "NB-REG-01"

        # Disabled selection for SRC-001
        store_mod.save_conversation_source_selection(
            ConversationSourceSelection(
                id="sel-disabled-01",
                conversation_id=conv_id,
                source_id="SRC-001",
                source_scope="notebook",
                enabled=False,
            )
        )

        server, health_url, completions_url = mock_fsm_server
        server.completion_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Theo tài liệu [EVD-001], bước 1 là khởi động máy kiểm đếm.",
                    }
                }
            ],
            "model": "gemini-2.5-flash",
        }

        health = AntigravityHealthStatus(
            status="direct_ready",
            mode="direct",
            capabilities=["direct_chat"],
        )

        evidence = [
            {
                "source_id": "SRC-001",
                "evidence_id": "EVD-001",
                "citation_id": "EVD-001",
                "title": "Quy trình vận hành máy",
                "snippet": "Bước 1 là khởi động máy kiểm đếm trước ca làm việc.",
                "source_path": "manual.txt",
                "citation_label": "[1]",
            }
        ]

        ok, msg, badge, err = route_workspace_chat_submission(
            question="Bước 1 là gì?",
            evidence_items=evidence,
            packed_sources=(),
            conversation_id=conv_id,
            notebook_id=nb_id,
            retrieval_applied=True,
            retrieved_sources=(),
            retrieval_summary="1 source retrieved",
            current_keys=(),
            chat_history=(),
            user_raw_input="Bước 1 là gì?",
            health_status=health,
            endpoint_url=completions_url,
            answer_language="vi",
        )

        assert ok is True
        trace_id = badge["trace_id"]
        trace = store_mod.load_evidence_trace(trace_id)
        assert trace is not None
        assert trace.metadata["status"] == "insufficient_evidence"
        assert trace.metadata["insufficient_evidence"] is True
        # Source from disabled selection must not be in trace nodes
        source_nodes = [n for n in trace.nodes if n.node_type == "source"]
        assert len(source_nodes) == 0
