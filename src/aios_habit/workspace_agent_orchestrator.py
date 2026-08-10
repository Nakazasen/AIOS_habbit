"""Bounded, observable Workspace Chat Agent IDE orchestration.

All mutable operations follow a three-stage contract: create proposal, review the
exact payload, then explicitly approve or discard. Pending edits live only in the
managed local bridge process; restarting AIOS invalidates them safely.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

from aios_habit.workspace_agent_bridge_client import WorkspaceAgentBridgeClient, WorkspaceAgentBridgeError
from aios_habit.workspace_agent_models import (
    WorkspaceAgentPendingAction, WorkspaceAgentRequest, WorkspaceAgentResult,
    WorkspaceAgentToolEvent, new_action_id, new_session_id,
)
from aios_habit.workspace_agent_policy import (
    MAX_TOOL_STEPS, AgentPolicyError, authorize_tool, validate_request,
)


def _summary(value: Any, limit: int = 420) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value
    text = text.replace('\n', ' ')
    return text[:limit] + ('…' if len(text) > limit else '')


def _event(tool: str, started: float, result: Any, *, ok: bool = True, category: str = 'read') -> WorkspaceAgentToolEvent:
    return WorkspaceAgentToolEvent(
        event_id=f'TOOL-{int(started * 1000)}', tool=tool, category=category, ok=ok,
        elapsed_ms=int((time.monotonic() - started) * 1000), summary=_summary(result),
    )


def _extract_query(instruction: str) -> str:
    return ' '.join(instruction.split())[:300]


class _PendingBridgeSessions:
    """Own bridge processes while a user reviews proposals in the local AIOS server."""
    def __init__(self) -> None:
        self._clients: dict[str, WorkspaceAgentBridgeClient] = {}
        self._lock = threading.Lock()

    def remember(self, session_id: str, client: WorkspaceAgentBridgeClient) -> None:
        with self._lock:
            prior = self._clients.pop(session_id, None)
            if prior is not None:
                prior.close()
            self._clients[session_id] = client

    def take(self, session_id: str) -> WorkspaceAgentBridgeClient | None:
        with self._lock:
            return self._clients.pop(session_id, None)

    def discard(self, session_id: str) -> None:
        client = self.take(session_id)
        if client is not None:
            client.close()


_PENDING_BRIDGE_SESSIONS = _PendingBridgeSessions()


class WorkspaceAgentOrchestrator:
    def __init__(self, bridge_client_factory=WorkspaceAgentBridgeClient):
        self._bridge_client_factory = bridge_client_factory

    def run(self, request: WorkspaceAgentRequest) -> WorkspaceAgentResult:
        session_id = new_session_id()
        try:
            workspace_root = validate_request(
                workspace_root=request.workspace_root, instruction=request.instruction,
                scope_confirmed=request.workspace_scope_confirmed,
            )
        except ValueError as error:
            return WorkspaceAgentResult(session_id=session_id, state='failed', answer_text='', error_message=str(error))

        client = self._bridge_client_factory(workspace_root)
        events: list[WorkspaceAgentToolEvent] = []
        evidence: dict[str, Any] = {}
        try:
            started = time.monotonic(); status = client.status(); events.append(_event('status', started, status))
            if not status.get('trusted'):
                return WorkspaceAgentResult(
                    session_id=session_id, state='failed', answer_text='', events=tuple(events),
                    error_message='Workspace chưa được tin cậy. Hãy xác nhận tin cậy rõ ràng trong Workspace Chat trước khi dùng Agent IDE.',
                )
            query = _extract_query(request.instruction)
            plan = [('project_indexer', {'query': query, 'maxFiles': 30, 'includeContent': False}), ('search_files', {'query': query, 'limit': 20}), ('git_status', {})]
            if request.mode in {'debug', 'implement'}:
                plan.append(('git_context', {'includeDiff': True, 'includeLog': False}))
            for tool, args in plan[:MAX_TOOL_STEPS]:
                started = time.monotonic()
                try:
                    data = client.call_tool(tool, args)
                    events.append(_event(tool, started, data))
                    evidence[tool] = data
                except WorkspaceAgentBridgeError as error:
                    events.append(_event(tool, started, str(error), ok=False))
            return WorkspaceAgentResult(session_id=session_id, state='completed', answer_text=self._build_answer(request, evidence), events=tuple(events))
        except WorkspaceAgentBridgeError as error:
            return WorkspaceAgentResult(session_id=session_id, state='failed', answer_text='', events=tuple(events), error_message=f'Local Agent bridge: {error}')
        finally:
            client.close()

    def propose_patch(self, *, workspace_root: str, file_path: str, find: str, replace: str, reason: str, scope_confirmed: bool) -> WorkspaceAgentResult:
        session_id = new_session_id()
        client: WorkspaceAgentBridgeClient | None = None
        try:
            root = validate_request(workspace_root=workspace_root, instruction=reason or 'Đề xuất chỉnh sửa', scope_confirmed=scope_confirmed)
            authorize_tool('apply_patch', {'filePath': file_path}, approved=True)
            client = self._bridge_client_factory(root)
            if not client.status().get('trusted'):
                raise AgentPolicyError('Workspace chưa được tin cậy. Không thể tạo proposal chỉnh sửa.')
            started = time.monotonic()
            proposal = client.call_tool('apply_patch', {'filePath': file_path, 'find': find, 'replace': replace, 'reason': reason}, approved=True)
            pending = proposal.get('pendingEdit') or {}
            if not pending.get('id') or not pending.get('diff'):
                raise WorkspaceAgentBridgeError('Agent bridge không trả về diff hợp lệ để review.')
            _PENDING_BRIDGE_SESSIONS.remember(session_id, client)
            client = None
            return WorkspaceAgentResult(
                session_id=session_id, state='awaiting_edit_approval', answer_text='Đã tạo diff để bạn xem xét. Chưa có tệp nào bị sửa.',
                events=(_event('apply_patch', started, proposal, category='proposal'),),
                pending_action=WorkspaceAgentPendingAction(new_action_id(), 'edit', reason or f'Đề xuất chỉnh sửa {file_path}', pending),
            )
        except (ValueError, WorkspaceAgentBridgeError) as error:
            return WorkspaceAgentResult(session_id=session_id, state='failed', answer_text='', error_message=str(error))
        finally:
            if client is not None:
                client.close()

    def approve_edit(self, *, proposal_session_id: str, pending_edit_id: str, workspace_root: str, scope_confirmed: bool, hunk_ids: list[str] | None = None) -> WorkspaceAgentResult:
        session_id = new_session_id()
        try:
            validate_request(workspace_root=workspace_root, instruction='Áp dụng proposal chỉnh sửa', scope_confirmed=scope_confirmed)
            authorize_tool('apply_pending_edit', {'id': pending_edit_id}, approved=True)
            client = _PENDING_BRIDGE_SESSIONS.take(proposal_session_id)
            if client is None:
                raise AgentPolicyError('Proposal đã hết hạn hoặc AIOS đã khởi động lại. Hãy tạo lại diff trước khi áp dụng.')
            started = time.monotonic()
            try:
                applied = client.call_tool('apply_pending_edit', {'id': pending_edit_id, 'hunkIds': hunk_ids}, approved=True)
            finally:
                client.close()
            return WorkspaceAgentResult(
                session_id=session_id, state='completed', answer_text='Đã áp dụng đúng proposal bạn đã phê duyệt.',
                events=(_event('apply_pending_edit', started, applied, category='approval'),),
            )
        except (ValueError, WorkspaceAgentBridgeError) as error:
            return WorkspaceAgentResult(session_id=session_id, state='failed', answer_text='', error_message=str(error))

    def discard_edit(self, *, proposal_session_id: str, pending_edit_id: str) -> WorkspaceAgentResult:
        session_id = new_session_id()
        client = _PENDING_BRIDGE_SESSIONS.take(proposal_session_id)
        if client is None:
            return WorkspaceAgentResult(session_id=session_id, state='cancelled', answer_text='Proposal đã không còn hoạt động hoặc đã được hủy.', error_message='')
        try:
            started = time.monotonic()
            discarded = client.call_tool('discard_pending_edit', {'id': pending_edit_id}, approved=True)
            return WorkspaceAgentResult(session_id=session_id, state='cancelled', answer_text='Đã hủy proposal. Không có tệp nào bị sửa.', events=(_event('discard_pending_edit', started, discarded, category='approval'),))
        except WorkspaceAgentBridgeError as error:
            return WorkspaceAgentResult(session_id=session_id, state='failed', answer_text='', error_message=str(error))
        finally:
            client.close()

    def propose_command(self, *, workspace_root: str, command: str, reason: str, scope_confirmed: bool) -> WorkspaceAgentResult:
        session_id = new_session_id()
        try:
            root = validate_request(workspace_root=workspace_root, instruction=reason or 'Đề xuất chạy lệnh', scope_confirmed=scope_confirmed)
            authorize_tool('execute_command', {'command': command}, approved=True)
            client = self._bridge_client_factory(root)
            try:
                if not client.status().get('trusted'):
                    raise AgentPolicyError('Workspace chưa được tin cậy. Không thể tạo proposal chạy lệnh.')
            finally:
                client.close()
            return WorkspaceAgentResult(
                session_id=session_id, state='awaiting_command_approval', answer_text='Lệnh đang chờ bạn xem xét và phê duyệt. Chưa có lệnh nào được chạy.',
                pending_action=WorkspaceAgentPendingAction(new_action_id(), 'command', reason or 'Đề xuất chạy lệnh', {'workspace_root': root, 'command': command}),
            )
        except (ValueError, WorkspaceAgentBridgeError) as error:
            return WorkspaceAgentResult(session_id=session_id, state='failed', answer_text='', error_message=str(error))

    def approve_command(self, *, workspace_root: str, command: str, scope_confirmed: bool) -> WorkspaceAgentResult:
        session_id = new_session_id()
        client: WorkspaceAgentBridgeClient | None = None
        try:
            root = validate_request(workspace_root=workspace_root, instruction='Chạy lệnh đã phê duyệt', scope_confirmed=scope_confirmed)
            authorize_tool('execute_command', {'command': command}, approved=True)
            client = self._bridge_client_factory(root)
            started = time.monotonic()
            execution = client.call_tool('execute_command', {'command': command}, approved=True)
            text = 'Lệnh đã chạy thành công.' if execution.get('ok') else 'Lệnh đã chạy nhưng trả về lỗi; xem stdout/stderr trong dấu vết.'
            return WorkspaceAgentResult(session_id=session_id, state='completed', answer_text=text, events=(_event('execute_command', started, execution, category='approval'),))
        except (ValueError, WorkspaceAgentBridgeError) as error:
            return WorkspaceAgentResult(session_id=session_id, state='failed', answer_text='', error_message=str(error))
        finally:
            if client is not None:
                client.close()

    def _build_answer(self, request: WorkspaceAgentRequest, evidence: dict[str, Any]) -> str:
        indexed = evidence.get('project_indexer', {})
        matches = evidence.get('search_files', {})
        git = evidence.get('git_status', {})
        files = indexed.get('relevantFiles', []) if isinstance(indexed, dict) else []
        match_count = len(matches.get('matches', [])) if isinstance(matches, dict) else 0
        lines = [f'**Agent IDE ({request.mode})** đã khảo sát workspace cục bộ trong phạm vi đã xác nhận.', f'- Tìm thấy **{len(files)}** tệp liên quan theo truy vấn.', f'- Tìm thấy **{match_count}** kết quả tìm kiếm nội dung.']
        if isinstance(git, dict) and git.get('isRepo'):
            lines.append(f"- Git branch: `{git.get('branch', 'unknown')}`; thay đổi: {git.get('totalChanges', 0)}; untracked: {git.get('totalUntracked', 0)}.")
        if files:
            lines.append('- Tệp nên đọc tiếp: ' + ', '.join(f'`{item.get("relPath")}`' for item in files[:8]) + '.')
        lines.append('\nMọi diff/lệnh đều cần review và phê duyệt riêng; Agent không tự áp dụng thay đổi.')
        return '\n'.join(lines)
