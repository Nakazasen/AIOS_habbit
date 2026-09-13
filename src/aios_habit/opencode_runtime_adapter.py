"""Thin OpenCode runtime adapter complying with aios_agent_runtime_v1 contract."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from aios_habit.workspace_agent_policy import (
    AgentPolicyError,
    AgentScopeGrant,
    authorize_scope_action,
    canonical_task_root,
    validate_path_in_task_root,
    validate_test_command,
)

SAFE_ENV_KEYS = (
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "TEMP",
    "TMP",
    "PATH",
    "PATHEXT",
    "PYTHONPATH",
)


def safe_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: os.environ[k] for k in SAFE_ENV_KEYS if k in os.environ}
    if extra:
        env.update(extra)
    return env


def utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RuntimeAdapterError(RuntimeError):
    """Safe adapter error presented to AIOS in Vietnamese."""


@dataclass(frozen=True)
class RuntimeRequest:
    work_id: str
    action: str
    payload: dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    session_id: str = ""
    scope_digest: str = ""
    idempotency_key: str = ""
    schema_version: str = "aios_agent_runtime_v1"


@dataclass(frozen=True)
class RuntimeReceipt:
    work_id: str
    session_id: str
    event_id: str
    sequence: int
    event_type: str
    action: str
    status: str
    observed_at: str
    payload_digest: str
    previous_event_digest: str
    payload: dict[str, Any] = field(default_factory=dict)


def compute_digest(data: Any) -> str:
    hasher = hashlib.sha256()
    if isinstance(data, (dict, list)):
        hasher.update(json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    elif isinstance(data, (str, bytes)):
        hasher.update(data if isinstance(data, bytes) else data.encode("utf-8"))
    else:
        hasher.update(str(data).encode("utf-8"))
    return hasher.hexdigest()


class OpenCodeRuntimeAdapter:
    """Thin adapter interfacing AIOS agent execution with the OpenCode runtime or local task root."""

    def __init__(
        self,
        grant: AgentScopeGrant,
        base_url: str | None = None,
        server_process: subprocess.Popen | None = None,
    ) -> None:
        self.grant = grant
        self.task_root = canonical_task_root(grant.task_root)
        self.base_url = base_url.rstrip("/") if base_url else None
        self.server_process = server_process
        self.current_session_id: str = ""
        self._sequence: int = 0
        self._last_event_digest: str = "GENESIS"
        self._receipts_by_key: dict[str, RuntimeReceipt] = {}
        self._receipts_by_id: dict[str, RuntimeReceipt] = {}
        self._events: list[RuntimeReceipt] = []

    def _http_json(
        self,
        endpoint: str,
        method: str = "GET",
        body: dict[str, Any] | None = None,
        timeout: int = 20,
    ) -> tuple[int, Any]:
        if not self.base_url:
            raise RuntimeAdapterError("Máy chủ OpenCode chưa được cấu hình hoặc chưa khởi động.")
        url = f"{self.base_url}{endpoint}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"} if data is not None else {}
        req = urllib.request.Request(url, method=method, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            raw = err.read().decode("utf-8", "replace")
            return err.code, {"error": raw[:500]}
        except Exception as err:
            raise RuntimeAdapterError(f"Lỗi kết nối tới runtime OpenCode: {err}")

    def execute_request(self, request: RuntimeRequest) -> RuntimeReceipt:
        # 1. Scope digest validation
        if request.scope_digest and request.scope_digest != self.grant.scope_digest:
            raise RuntimeAdapterError("Chữ ký phạm vi (scope_digest) không khớp với nhiệm vụ đã cấp quyền.")

        # 2. Idempotency verification
        payload_digest = compute_digest(request.payload)
        if request.idempotency_key:
            existing = self._receipts_by_key.get(request.idempotency_key)
            if existing is not None:
                if existing.payload_digest == payload_digest:
                    return existing
                raise RuntimeAdapterError(
                    f"Khóa xử lý ({request.idempotency_key}) bị trùng lặp với nội dung khác."
                )

        # 3. Policy authorization
        target_path = request.payload.get("path")
        target_command = request.payload.get("command")
        authorize_scope_action(
            self.grant,
            request.action,
            path=target_path,
            command=target_command,
        )

        # 4. Dispatch action
        session_id = request.session_id or self.current_session_id
        action = request.action
        status = "passed"
        result_payload: dict[str, Any] = {}

        try:
            if action == "health":
                result_payload = self._handle_health()
            elif action == "create_session":
                session_id = self._handle_create_session(request.payload.get("title", "AIOS Agent Task"))
                self.current_session_id = session_id
                result_payload = {"session_id": session_id}
            elif action == "get_session":
                result_payload = self._handle_get_session(session_id)
            elif action == "list_events":
                result_payload = {"events": [r.payload for r in self._events]}
            elif action == "read_file":
                content = self._handle_read_file(str(target_path))
                result_payload = {"path": str(target_path), "content": content}
            elif action == "search_files":
                matches = self._handle_search_files(str(request.payload.get("query", "")))
                result_payload = {"query": request.payload.get("query", ""), "matches": matches}
            elif action == "create_file":
                res = self._handle_write_file(str(target_path), str(request.payload.get("content", "")))
                result_payload = res
            elif action == "edit_file":
                res = self._handle_write_file(str(target_path), str(request.payload.get("content", "")))
                result_payload = res
            elif action == "run_test":
                res = self._handle_run_test(
                    target_command,
                    timeout=int(request.payload.get("timeout", 60)),
                )
                result_payload = res
                if not res.get("passed", False):
                    status = "failed"
            elif action == "get_workspace_state":
                result_payload = self._handle_workspace_state()
            elif action == "abort_session":
                result_payload = self._handle_abort_session(session_id)
            else:
                raise RuntimeAdapterError(f"Thao tác runtime không được hỗ trợ: {action}")
        except AgentPolicyError:
            raise
        except Exception as error:
            status = "failed"
            result_payload = {"error": str(error)}

        # 5. Build and record receipt
        self._sequence += 1
        event_id = f"EVT-{self._sequence:06d}"
        observed_at = utc_iso_now()
        event_digest = compute_digest({
            "event_id": event_id,
            "work_id": request.work_id,
            "action": action,
            "status": status,
            "payload_digest": payload_digest,
            "previous": self._last_event_digest,
        })

        receipt = RuntimeReceipt(
            work_id=request.work_id,
            session_id=session_id,
            event_id=event_id,
            sequence=self._sequence,
            event_type=f"runtime.{action}",
            action=action,
            status=status,
            observed_at=observed_at,
            payload_digest=payload_digest,
            previous_event_digest=self._last_event_digest,
            payload=result_payload,
        )

        self._last_event_digest = event_digest
        self._receipts_by_id[event_id] = receipt
        if request.idempotency_key:
            self._receipts_by_key[request.idempotency_key] = receipt
        self._events.append(receipt)
        return receipt

    def _handle_health(self) -> dict[str, Any]:
        if self.base_url:
            code, data = self._http_json("/global/health")
            if code == 200 and isinstance(data, dict):
                return {"status": "ok", "version": data.get("version", ""), "runtime": "opencode"}
        return {"status": "ok", "version": "local_harness", "runtime": "aios_local"}

    def _handle_create_session(self, title: str) -> str:
        if self.base_url:
            code, data = self._http_json("/session", method="POST", body={"title": title})
            if code == 200 and isinstance(data, dict) and data.get("id"):
                return str(data["id"])
        # Fallback local session id
        return f"SESSION-{int(time.time() * 1000)}"

    def _handle_get_session(self, session_id: str) -> dict[str, Any]:
        if self.base_url and session_id:
            code, data = self._http_json(f"/session/{session_id}")
            if code == 200 and isinstance(data, dict):
                return data
        return {"session_id": session_id, "status": "active"}

    def _handle_read_file(self, relative_path: str) -> str:
        resolved = validate_path_in_task_root(relative_path, self.task_root)
        if not resolved.is_file():
            raise RuntimeAdapterError(f"Tệp không tồn tại: {relative_path}")
        return resolved.read_text(encoding="utf-8", errors="replace")

    def _handle_search_files(self, query: str) -> list[str]:
        if self.base_url:
            code, data = self._http_json(f"/find?pattern={urllib.parse.quote(query)}")
            if code == 200 and isinstance(data, list):
                return [str(item) for item in data]

        # Local search within task_root
        matches: list[str] = []
        q_lower = query.lower()
        for root, dirs, files in os.walk(self.task_root):
            # Prune hidden or forbidden dirs
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("local_cases", "local_runs")]
            for filename in files:
                file_path = Path(root) / filename
                rel = file_path.relative_to(self.task_root).as_posix()
                if q_lower in rel.lower():
                    matches.append(rel)
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if q_lower in content.lower():
                        matches.append(rel)
                except Exception:
                    pass
        return sorted(matches)

    def _handle_write_file(self, relative_path: str, content: str) -> dict[str, Any]:
        resolved = validate_path_in_task_root(relative_path, self.task_root)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        hasher = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return {
            "path": resolved.relative_to(self.task_root).as_posix(),
            "bytes_written": len(content.encode("utf-8")),
            "sha256": hasher,
        }

    def _handle_run_test(self, command: str | list[str], timeout: int = 60) -> dict[str, Any]:
        validated_cmd = validate_test_command(command, self.grant.allowed_commands)
        tokens = validated_cmd.split()
        started_time = time.monotonic()
        try:
            completed = subprocess.run(
                tokens,
                cwd=self.task_root,
                env=safe_environment(),
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            elapsed_ms = int((time.monotonic() - started_time) * 1000)
            return {
                "command": validated_cmd,
                "returncode": completed.returncode,
                "passed": completed.returncode == 0,
                "stdout": completed.stdout[-2000:],
                "stderr": completed.stderr[-2000:],
                "duration_ms": elapsed_ms,
            }
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = int((time.monotonic() - started_time) * 1000)
            return {
                "command": validated_cmd,
                "returncode": -1,
                "passed": False,
                "stdout": (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
                "stderr": "Lệnh kiểm thử bị quá thời gian giới hạn (timeout).",
                "duration_ms": elapsed_ms,
            }
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - started_time) * 1000)
            return {
                "command": validated_cmd,
                "returncode": -1,
                "passed": False,
                "stdout": "",
                "stderr": f"Lỗi thực thi lệnh: {exc}",
                "duration_ms": elapsed_ms,
            }

    def _handle_workspace_state(self) -> dict[str, Any]:
        files_manifest: dict[str, str] = {}
        hasher = hashlib.sha256()
        for root, dirs, files in os.walk(self.task_root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("local_cases", "local_runs")]
            for filename in sorted(files):
                f_path = Path(root) / filename
                rel = f_path.relative_to(self.task_root).as_posix()
                try:
                    data = f_path.read_bytes()
                    h = hashlib.sha256(data).hexdigest()
                    files_manifest[rel] = h
                    hasher.update(rel.encode("utf-8"))
                    hasher.update(h.encode("utf-8"))
                except Exception:
                    pass
        return {
            "total_files": len(files_manifest),
            "manifest": files_manifest,
            "workspace_digest": hasher.hexdigest(),
        }

    def _handle_abort_session(self, session_id: str) -> dict[str, Any]:
        if self.base_url and session_id:
            code, _ = self._http_json(f"/session/{session_id}/abort", method="POST")
            return {"aborted": code == 200}
        return {"aborted": True}

    def close(self) -> None:
        if self.server_process is not None:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except Exception:
                try:
                    self.server_process.kill()
                except Exception:
                    pass
            self.server_process = None
