"""Client for the local, stdio-only NVIDIA Workspace Agent bridge."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import threading
import time
import uuid
from typing import Any


class WorkspaceAgentBridgeError(RuntimeError):
    pass


class WorkspaceAgentBridgeClient:
    def __init__(self, workspace_root: str, *, bridge_path: str | None = None, node_command: str | None = None, timeout_seconds: float = 30.0):
        self.workspace_root = str(Path(workspace_root).resolve())
        self.bridge_path = bridge_path or os.environ.get('AIOS_NVIDIA_AGENT_BRIDGE_PATH', r'D:\Sandbox\Nvidia\tools\workspace-agent-bridge.mjs')
        self.node_command = node_command or os.environ.get('AIOS_NODE_COMMAND', 'node')
        self.timeout_seconds = timeout_seconds
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def _start(self) -> None:
        if self._process and self._process.poll() is None:
            return
        bridge = Path(self.bridge_path)
        if not bridge.is_file():
            raise WorkspaceAgentBridgeError('Local NVIDIA Agent bridge chưa sẵn sàng.')
        env = {**os.environ, 'AIOS_AGENT_WORKSPACE': self.workspace_root}
        try:
            self._process = subprocess.Popen(
                [self.node_command, str(bridge)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, encoding='utf-8', errors='replace',
                cwd=str(bridge.parent.parent), env=env, bufsize=1,
            )
        except OSError as error:
            raise WorkspaceAgentBridgeError('Không thể khởi động local NVIDIA Agent bridge.') from error

    def request(self, action: str, *, tool: str = '', args: dict[str, Any] | None = None, approved: bool = False) -> dict[str, Any]:
        payload = {'id': uuid.uuid4().hex, 'action': action, 'tool': tool, 'args': args or {}, 'approved': approved}
        with self._lock:
            self._start()
            assert self._process and self._process.stdin and self._process.stdout
            try:
                self._process.stdin.write(json.dumps(payload, ensure_ascii=False) + '\n')
                self._process.stdin.flush()
            except OSError as error:
                raise WorkspaceAgentBridgeError('Kết nối local Agent bridge đã bị ngắt.') from error
            deadline = time.monotonic() + self.timeout_seconds
            while time.monotonic() < deadline:
                line = self._process.stdout.readline()
                if not line:
                    break
                response = json.loads(line)
                if response.get('id') == payload['id']:
                    if not response.get('ok'):
                        raise WorkspaceAgentBridgeError(str(response.get('error') or 'Agent bridge từ chối yêu cầu.'))
                    return response.get('result') or {}
        raise WorkspaceAgentBridgeError('Local Agent bridge không phản hồi đúng hạn.')

    def status(self) -> dict[str, Any]:
        return self.request('status')

    def trust_workspace(self) -> dict[str, Any]:
        return self.request('trust_workspace', approved=True)

    def call_tool(self, tool: str, args: dict[str, Any] | None = None, *, approved: bool = False) -> dict[str, Any]:
        return self.request('tool', tool=tool, args=args, approved=approved)

    def close(self) -> None:
        with self._lock:
            if self._process and self._process.poll() is None:
                self._process.terminate()
            self._process = None
