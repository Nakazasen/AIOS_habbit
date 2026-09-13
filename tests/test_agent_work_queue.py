"""Tests for US4: Agent work queue, workspace writer lock, cancellation, and restart recovery."""
import tempfile
from pathlib import Path
import pytest

from aios_habit.workspace_agent_orchestrator import WorkspaceAgentOrchestrator
from aios_habit.workspace_case_models import AgentWorkRecord, utc_now_iso
from aios_habit.workspace_case_repository import WorkspaceCaseRepository


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "workspace_cases.sqlite"
        repo = WorkspaceCaseRepository(database_path=db_path)
        repo.initialize()
        yield repo


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir).resolve()


def _make_work(
    work_id: str,
    workspace_id: str,
    work_type: str,
    goal_vi: str,
    status: str = "queued",
) -> AgentWorkRecord:
    now = utc_now_iso()
    return AgentWorkRecord(
        work_id=work_id,
        workspace_id=workspace_id,
        work_type=work_type,
        goal_vi=goal_vi,
        created_at=now,
        updated_at=now,
        status=status,
    )


def test_queue_preserves_fifo_order_across_three_work_types(temp_repo):
    orchestrator = WorkspaceAgentOrchestrator()
    ws_id = "ws-queue-test"

    # Enqueue three tasks belonging to three distinct types
    task1 = _make_work("WORK-1", ws_id, "error_report", "Báo cáo lỗi xưởng dây chuyền SMT")
    task2 = _make_work("WORK-2", ws_id, "process_design_review", "Rà soát thiết kế công đoạn ép nhựa")
    task3 = _make_work("WORK-3", ws_id, "code_change", "Sửa lỗi tính tỷ lệ thu hồi Yield Rate")

    e1 = orchestrator.enqueue_work_item(work=task1, repo=temp_repo)
    e2 = orchestrator.enqueue_work_item(work=task2, repo=temp_repo)
    e3 = orchestrator.enqueue_work_item(work=task3, repo=temp_repo)

    assert e1.queue_position == 1
    assert e2.queue_position == 2
    assert e3.queue_position == 3

    queued = temp_repo.list_agent_work(workspace_id=ws_id, status="queued")
    assert len(queued) == 3
    assert [w.work_id for w in queued] == ["WORK-1", "WORK-2", "WORK-3"]
    assert [w.work_type for w in queued] == ["error_report", "process_design_review", "code_change"]


def test_single_writer_lock_prevents_concurrent_writes_same_workspace(temp_workspace):
    orchestrator = WorkspaceAgentOrchestrator()
    ws_root = str(temp_workspace)

    # Work 1 acquires lock
    assert orchestrator.acquire_workspace_lock(ws_root, "WORK-1") is True

    # Work 2 on same workspace is blocked
    assert orchestrator.acquire_workspace_lock(ws_root, "WORK-2") is False

    # Same work_id can re-acquire (idempotent for owner)
    assert orchestrator.acquire_workspace_lock(ws_root, "WORK-1") is True

    # Release Work 1 lock
    orchestrator.release_workspace_lock(ws_root, "WORK-1")

    # Now Work 2 can acquire lock
    assert orchestrator.acquire_workspace_lock(ws_root, "WORK-2") is True
    orchestrator.release_workspace_lock(ws_root, "WORK-2")


def test_concurrent_writes_allowed_across_different_workspaces():
    orchestrator = WorkspaceAgentOrchestrator()
    with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
        ws_root_a = str(Path(tmp_a).resolve())
        ws_root_b = str(Path(tmp_b).resolve())

        # Tasks on different workspaces can hold locks simultaneously
        assert orchestrator.acquire_workspace_lock(ws_root_a, "WORK-A") is True
        assert orchestrator.acquire_workspace_lock(ws_root_b, "WORK-B") is True

        orchestrator.release_workspace_lock(ws_root_a, "WORK-A")
        orchestrator.release_workspace_lock(ws_root_b, "WORK-B")


def test_cancel_work_item(temp_repo, temp_workspace):
    orchestrator = WorkspaceAgentOrchestrator()
    ws_id = "ws-cancel-test"
    ws_root = str(temp_workspace)

    # 1. Cancel queued work
    task = _make_work("WORK-CANCEL-1", ws_id, "error_report", "Báo cáo lỗi cần hủy")
    orchestrator.enqueue_work_item(work=task, repo=temp_repo)
    cancelled = orchestrator.cancel_work_item(work_id="WORK-CANCEL-1", repo=temp_repo)
    assert cancelled is True
    updated = temp_repo.get_agent_work("WORK-CANCEL-1")
    assert updated is not None
    assert updated.status == "cancelled"

    # 2. Cancel running work releases lock
    task2 = _make_work("WORK-CANCEL-2", ws_id, "code_change", "Nhiệm vụ đang chạy")
    orchestrator.enqueue_work_item(work=task2, repo=temp_repo)
    assert orchestrator.acquire_workspace_lock(ws_root, "WORK-CANCEL-2") is True
    temp_repo.update_agent_work_status("WORK-CANCEL-2", "running")

    cancelled_running = orchestrator.cancel_work_item(
        work_id="WORK-CANCEL-2", repo=temp_repo, workspace_root=ws_root
    )
    assert cancelled_running is True
    assert temp_repo.get_agent_work("WORK-CANCEL-2").status == "cancelled"
    # Verify lock was released
    assert orchestrator.acquire_workspace_lock(ws_root, "WORK-NEXT") is True
    orchestrator.release_workspace_lock(ws_root, "WORK-NEXT")

    # 3. Cannot cancel completed work
    temp_repo.update_agent_work_status("WORK-CANCEL-1", "completed")
    assert orchestrator.cancel_work_item(work_id="WORK-CANCEL-1", repo=temp_repo) is False


def test_resume_and_restart_recovery(temp_repo):
    orchestrator = WorkspaceAgentOrchestrator()
    ws_id = "ws-restart-test"

    # Setup 3 tasks before simulated crash: 1 completed, 1 stranded in running, 1 queued
    t_completed = _make_work("WORK-DONE", ws_id, "error_report", "Đã xong", status="completed")
    t_running = _make_work("WORK-RUNNING", ws_id, "code_change", "Bị sập khi đang chạy", status="running")
    t_queued = _make_work("WORK-WAITING", ws_id, "process_design_review", "Đang chờ lượt", status="queued")

    temp_repo.save_agent_work(t_completed)
    temp_repo.save_agent_work(t_running)
    temp_repo.save_agent_work(t_queued)

    # Simulate restart by creating a new orchestrator instance
    new_orchestrator = WorkspaceAgentOrchestrator()
    interrupted = new_orchestrator.resume_interrupted_tasks(repo=temp_repo, workspace_id=ws_id)

    assert len(interrupted) == 1
    assert interrupted[0].work_id == "WORK-RUNNING"
    assert interrupted[0].status == "interrupted_unknown"

    # Completed task was untouched
    assert temp_repo.get_agent_work("WORK-DONE").status == "completed"

    # Queued task remains queued ready to run
    assert temp_repo.get_agent_work("WORK-WAITING").status == "queued"


def test_process_next_work_item_execution_and_failure(temp_repo, temp_workspace):
    orchestrator = WorkspaceAgentOrchestrator()
    ws_id = "ws-process-test"
    ws_root = str(temp_workspace)

    task1 = _make_work("WORK-EXEC-1", ws_id, "error_report", "Tác vụ thành công")
    task2 = _make_work("WORK-EXEC-2", ws_id, "code_change", "Tác vụ ném ngoại lệ")
    orchestrator.enqueue_work_item(work=task1, repo=temp_repo)
    orchestrator.enqueue_work_item(work=task2, repo=temp_repo)

    executed_ids = []

    def successful_runner(item: AgentWorkRecord):
        executed_ids.append(item.work_id)

    # Process first item
    res1 = orchestrator.process_next_work_item(
        workspace_id=ws_id,
        workspace_root=ws_root,
        repo=temp_repo,
        runner=successful_runner,
    )
    assert res1 is not None
    assert res1.work_id == "WORK-EXEC-1"
    assert res1.status == "completed"
    assert executed_ids == ["WORK-EXEC-1"]

    # Process second item which raises error
    def failing_runner(item: AgentWorkRecord):
        raise ValueError("Lỗi mô phỏng trong lúc xử lý")

    with pytest.raises(ValueError, match="Lỗi mô phỏng trong lúc xử lý"):
        orchestrator.process_next_work_item(
            workspace_id=ws_id,
            workspace_root=ws_root,
            repo=temp_repo,
            runner=failing_runner,
        )

    res2 = temp_repo.get_agent_work("WORK-EXEC-2")
    assert res2 is not None
    assert res2.status == "failed"

    # Lock must be released even after failure
    assert orchestrator.acquire_workspace_lock(ws_root, "WORK-ANOTHER") is True
    orchestrator.release_workspace_lock(ws_root, "WORK-ANOTHER")
