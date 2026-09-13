from dataclasses import dataclass
from pathlib import Path
import pytest
from aios_habit.workspace_agent_models import WorkspaceAgentRequest
from aios_habit.workspace_agent_orchestrator import (
    WorkspaceAgentOrchestrator,
    WorkspaceWriterLock,
    create_work_checkpoint,
    rollback_checkpoint,
)
from aios_habit.workspace_agent_policy import AgentPolicyError


@dataclass
class FakeClient:
    trusted: bool = True
    def __init__(self, root): self.root = root; self.calls = []
    def status(self): return {'trusted': self.trusted, 'workspace': self.root}
    def call_tool(self, tool, args=None, approved=False):
        self.calls.append((tool, args, approved))
        if tool == 'project_indexer': return {'relevantFiles': [{'relPath': 'src/main.py'}]}
        if tool == 'search_files': return {'matches': []}
        if tool == 'git_status': return {'isRepo': True, 'branch': 'main', 'totalChanges': 0, 'totalUntracked': 0}
        return {}
    def close(self): pass


def test_agent_requires_explicit_workspace_scope(tmp_path):
    result = WorkspaceAgentOrchestrator(FakeClient).run(WorkspaceAgentRequest('c', str(tmp_path), 'phân tích', workspace_scope_confirmed=False))
    assert result.state == 'failed'
    assert 'xác nhận' in result.error_message


def test_agent_runs_only_read_tools_in_bounded_inspection(tmp_path):
    result = WorkspaceAgentOrchestrator(FakeClient).run(WorkspaceAgentRequest('c', str(tmp_path), 'phân tích kiến trúc', workspace_scope_confirmed=True))
    assert result.state == 'completed'
    assert all(event.category == 'read' for event in result.events)
    assert 'chưa khảo sát' not in result.answer_text


def test_workspace_writer_lock(tmp_path: Path):
    lock = WorkspaceWriterLock()
    ws = str(tmp_path)

    # 1. Acquire lock by WORK-1
    assert lock.acquire(ws, "WORK-1") is True
    assert lock.get_holder(ws) == "WORK-1"

    # Re-entrant by same work_id
    assert lock.acquire(ws, "WORK-1") is True

    # 2. Block WORK-2 on same workspace
    assert lock.acquire(ws, "WORK-2") is False

    # 3. Context manager raises on collision
    with pytest.raises(AgentPolicyError, match="đang có một công việc ghi khác"):
        with lock.hold(ws, "WORK-2"):
            pass

    # 4. Release allows WORK-2
    lock.release(ws, "WORK-1")
    assert lock.acquire(ws, "WORK-2") is True
    lock.release(ws, "WORK-2")


def test_orchestrator_checkpoint_and_rollback(tmp_path: Path):
    orchestrator = WorkspaceAgentOrchestrator(FakeClient)
    ws = str(tmp_path)
    task_root = tmp_path / "task"
    task_root.mkdir()

    # Create initial files
    file_a = task_root / "module_a.py"
    file_a.write_text("initial_a", encoding="utf-8")
    file_b = task_root / "module_b.py"
    file_b.write_text("initial_b", encoding="utf-8")

    # Checkpoint
    ckpt = orchestrator.create_checkpoint(
        work_id="WORK-CKPT-01",
        workspace_root=ws,
        task_root=task_root,
    )
    assert "module_a.py" in ckpt.manifest
    assert "module_b.py" in ckpt.manifest

    # Check clean resume
    assert orchestrator.resume_check("WORK-CKPT-01", task_root) == "clean"

    # Make modifications: modify a, delete b, create c
    file_a.write_text("modified_a", encoding="utf-8")
    file_b.unlink()
    file_c = task_root / "module_c.py"
    file_c.write_text("created_c", encoding="utf-8")

    # Now resume_check detects interruption
    assert orchestrator.resume_check("WORK-CKPT-01", task_root) == "interrupted_unknown"

    # Rollback!
    ok, msg = orchestrator.rollback("WORK-CKPT-01")
    assert ok is True
    assert "hoàn tác" in msg

    # Verify state after rollback
    assert file_a.read_text(encoding="utf-8") == "initial_a"
    assert file_b.exists() and file_b.read_text(encoding="utf-8") == "initial_b"
    assert not file_c.exists()
    assert orchestrator.resume_check("WORK-CKPT-01", task_root) == "clean"

