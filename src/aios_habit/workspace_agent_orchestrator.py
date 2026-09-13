"""Bounded, observable Workspace Chat Agent IDE orchestration.

All mutable operations follow a three-stage contract: create proposal, review the
exact payload, then explicitly approve or discard. Pending edits live only in the
managed local bridge process; restarting AIOS invalidates them safely.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aios_habit.agent_result_import import (
    WorktreeVerificationResult,
    import_worktree_to_workspace,
    verify_worktree_result,
)
from aios_habit.opencode_runtime_adapter import OpenCodeRuntimeAdapter, RuntimeRequest
from aios_habit.workspace_agent_bridge_client import WorkspaceAgentBridgeClient, WorkspaceAgentBridgeError
from aios_habit.workspace_agent_models import (
    WorkspaceAgentPendingAction, WorkspaceAgentRequest, WorkspaceAgentResult,
    WorkspaceAgentToolEvent, new_action_id, new_session_id,
)
from aios_habit.workspace_agent_policy import (
    MAX_TOOL_STEPS, AgentPolicyError, TASK_TYPE_CODE_CHANGE, authorize_tool,
    canonical_task_root, canonical_workspace_root, create_scope_grant, validate_request,
)


class WorkspaceWriterLock:
    """Guarantees strictly one mutable agent operation writes to a workspace at a time."""
    def __init__(self) -> None:
        self._locks: dict[str, str] = {}  # canonical_workspace_root -> current_work_id
        self._mutex = threading.Lock()

    def acquire(self, workspace_root: str, work_id: str) -> bool:
        root = canonical_workspace_root(workspace_root)
        with self._mutex:
            holder = self._locks.get(root)
            if holder is None or holder == work_id:
                self._locks[root] = work_id
                return True
            return False

    def release(self, workspace_root: str, work_id: str) -> None:
        root = canonical_workspace_root(workspace_root)
        with self._mutex:
            if self._locks.get(root) == work_id:
                del self._locks[root]

    def get_holder(self, workspace_root: str) -> str | None:
        root = canonical_workspace_root(workspace_root)
        with self._mutex:
            return self._locks.get(root)

    @contextmanager
    def hold(self, workspace_root: str, work_id: str):
        if not self.acquire(workspace_root, work_id):
            holder = self.get_holder(workspace_root)
            raise AgentPolicyError(
                f"Workspace đang có một công việc ghi khác đang chạy ({holder}). "
                "Mỗi thư mục làm việc chỉ cho phép một tác vụ ghi tại một thời điểm."
            )
        try:
            yield
        finally:
            self.release(workspace_root, work_id)


@dataclass(frozen=True)
class WorkCheckpoint:
    checkpoint_id: str
    work_id: str
    workspace_root: str
    task_root: str
    kind: str
    created_at: str
    manifest: dict[str, str]
    backup_dir: str
    rollback_status: str = "available"


def create_work_checkpoint(
    *,
    work_id: str,
    workspace_root: str,
    task_root: str | Path,
    kind: str = "snapshot",
) -> WorkCheckpoint:
    root = canonical_task_root(task_root)
    ws_root = canonical_workspace_root(workspace_root)
    manifest: dict[str, str] = {}
    backup_dir = tempfile.mkdtemp(prefix=f"aios_ckpt_{work_id}_")

    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("local_cases", "local_runs", "__pycache__")]
        for file_name in sorted(files):
            file_path = Path(dirpath) / file_name
            rel_posix = file_path.relative_to(root).as_posix()
            try:
                content_bytes = file_path.read_bytes()
                h = hashlib.sha256(content_bytes).hexdigest()
                manifest[rel_posix] = h

                target_backup = Path(backup_dir) / rel_posix
                target_backup.parent.mkdir(parents=True, exist_ok=True)
                target_backup.write_bytes(content_bytes)
            except Exception:
                pass

    checkpoint_id = f"CKPT-{work_id}-{int(time.time() * 1000)}"
    return WorkCheckpoint(
        checkpoint_id=checkpoint_id,
        work_id=work_id,
        workspace_root=ws_root,
        task_root=str(root),
        kind=kind,
        created_at=datetime.now(timezone.utc).isoformat(),
        manifest=manifest,
        backup_dir=backup_dir,
        rollback_status="available",
    )


def rollback_checkpoint(checkpoint: WorkCheckpoint) -> tuple[bool, str]:
    root = Path(checkpoint.task_root)
    backup_dir = Path(checkpoint.backup_dir)
    if not root.exists() or not root.is_dir():
        return False, "Thư mục tác vụ không tồn tại để hoàn tác."

    try:
        # 1. Remove files created after checkpoint
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("local_cases", "local_runs", "__pycache__")]
            for file_name in files:
                f_path = Path(dirpath) / file_name
                rel_posix = f_path.relative_to(root).as_posix()
                if rel_posix not in checkpoint.manifest:
                    try:
                        f_path.unlink()
                    except Exception:
                        pass

        # 2. Restore modified or deleted files from backup
        for rel_posix in checkpoint.manifest:
            backup_file = backup_dir / rel_posix
            target_file = root / rel_posix
            if backup_file.is_file():
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_bytes(backup_file.read_bytes())

        return True, "Đã hoàn tác toàn bộ thay đổi về trạng thái ban đầu an toàn."
    except Exception as error:
        return False, f"Lỗi trong quá trình hoàn tác: {error}"


def cleanup_checkpoint(checkpoint: WorkCheckpoint) -> None:
    backup_dir = Path(checkpoint.backup_dir)
    if backup_dir.exists():
        shutil.rmtree(backup_dir, ignore_errors=True)


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
        self.writer_lock = WorkspaceWriterLock()
        self._checkpoints: dict[str, WorkCheckpoint] = {}

    def acquire_workspace_lock(self, workspace_root: str, work_id: str) -> bool:
        return self.writer_lock.acquire(workspace_root, work_id)

    def release_workspace_lock(self, workspace_root: str, work_id: str) -> None:
        self.writer_lock.release(workspace_root, work_id)

    def create_checkpoint(
        self,
        *,
        work_id: str,
        workspace_root: str,
        task_root: str | Path,
        kind: str = "snapshot",
    ) -> WorkCheckpoint:
        ckpt = create_work_checkpoint(
            work_id=work_id,
            workspace_root=workspace_root,
            task_root=task_root,
            kind=kind,
        )
        self._checkpoints[work_id] = ckpt
        return ckpt

    def rollback(self, work_id_or_checkpoint: str | WorkCheckpoint) -> tuple[bool, str]:
        if isinstance(work_id_or_checkpoint, str):
            ckpt = self._checkpoints.get(work_id_or_checkpoint)
            if ckpt is None:
                return False, "Không tìm thấy checkpoint để hoàn tác cho nhiệm vụ này."
        else:
            ckpt = work_id_or_checkpoint

        return rollback_checkpoint(ckpt)

    def resume_check(self, work_id: str, task_root: str | Path) -> str:
        ckpt = self._checkpoints.get(work_id)
        if ckpt is None:
            return "no_checkpoint"
        root = Path(task_root)
        current_manifest: dict[str, str] = {}
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("local_cases", "local_runs", "__pycache__")]
            for file_name in files:
                f_path = Path(dirpath) / file_name
                rel_posix = f_path.relative_to(root).as_posix()
                try:
                    current_manifest[rel_posix] = hashlib.sha256(f_path.read_bytes()).hexdigest()
                except Exception:
                    pass
        if current_manifest == ckpt.manifest:
            return "clean"
        return "interrupted_unknown"

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

    def run_code_task(
        self,
        *,
        work_id: str,
        workspace_root: str,
        instruction: str,
        test_command: str,
        fix_action: Any | None = None,
        worktree_path: str | Path | None = None,
    ) -> tuple[WorktreeVerificationResult, WorkCheckpoint]:
        canonical_ws = canonical_workspace_root(workspace_root)
        with self.writer_lock.hold(canonical_ws, work_id):
            if worktree_path is not None:
                wt = Path(worktree_path).resolve()
            else:
                wt = Path(tempfile.mkdtemp(prefix=f"aios_worktree_{work_id}_")).resolve()
                for item in os.listdir(canonical_ws):
                    if item.startswith(".") or item in ("local_cases", "local_runs", "__pycache__"):
                        continue
                    src = Path(canonical_ws) / item
                    dst = wt / item
                    if src.is_dir():
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)

            checkpoint = self.create_checkpoint(
                work_id=work_id,
                workspace_root=canonical_ws,
                task_root=wt,
                kind="git_worktree" if (wt / ".git").exists() else "snapshot",
            )

            grant = create_scope_grant(
                work_id=work_id,
                task_root=wt,
                task_type=TASK_TYPE_CODE_CHANGE,
                allowed_commands=(test_command,),
            )
            adapter = OpenCodeRuntimeAdapter(grant=grant)

            # 1. Run test initially to observe baseline
            adapter.execute_request(
                RuntimeRequest(
                    work_id=work_id,
                    action="run_test",
                    payload={"command": test_command},
                )
            )

            # 2. Execute fix
            if callable(fix_action):
                fix_action(adapter)

            # 3. Run test again to observe fix result
            final_receipt = adapter.execute_request(
                RuntimeRequest(
                    work_id=work_id,
                    action="run_test",
                    payload={"command": test_command},
                )
            )

            # 4. Verify results
            verification = verify_worktree_result(
                worktree_path=wt,
                baseline_workspace_path=canonical_ws,
                baseline_manifest=checkpoint.manifest,
                test_receipt=final_receipt.payload,
            )

            return verification, checkpoint

    def import_code_result(
        self,
        *,
        work_id: str,
        workspace_root: str,
        worktree_path: str | Path,
        files_to_import: list[str] | tuple[str, ...] | None = None,
    ) -> tuple[bool, str]:
        canonical_ws = canonical_workspace_root(workspace_root)
        with self.writer_lock.hold(canonical_ws, work_id):
            return import_worktree_to_workspace(
                worktree_path=worktree_path,
                target_workspace_path=canonical_ws,
                files_to_import=files_to_import,
            )

