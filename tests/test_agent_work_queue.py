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
    allowed_roots: tuple[str, ...] = (),
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
        allowed_roots=allowed_roots,
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

    # 3. Cancel running work with allowed_roots and workspace_root=None also releases lock
    task3 = _make_work("WORK-CANCEL-3", ws_id, "code_change", "Chạy với allowed_roots", allowed_roots=(ws_root,))
    orchestrator.enqueue_work_item(work=task3, repo=temp_repo)
    assert orchestrator.acquire_workspace_lock(ws_root, "WORK-CANCEL-3") is True
    temp_repo.update_agent_work_status("WORK-CANCEL-3", "running")

    cancelled_running3 = orchestrator.cancel_work_item(
        work_id="WORK-CANCEL-3", repo=temp_repo, workspace_root=None
    )
    assert cancelled_running3 is True
    assert temp_repo.get_agent_work("WORK-CANCEL-3").status == "cancelled"
    # Verify lock was released via allowed_roots fallback
    assert orchestrator.acquire_workspace_lock(ws_root, "WORK-NEXT-2") is True
    orchestrator.release_workspace_lock(ws_root, "WORK-NEXT-2")

    # 4. Cannot cancel completed work
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


def test_process_next_work_item_lock_contention(temp_repo, temp_workspace):
    """Verify that lock contention safely returns None and keeps the task in queued state."""
    orchestrator = WorkspaceAgentOrchestrator()
    ws_id = "ws-lock-contention"
    ws_root = str(temp_workspace)

    task = _make_work("WORK-CONTEND-1", ws_id, "error_report", "Báo cáo lỗi chờ khóa")
    orchestrator.enqueue_work_item(work=task, repo=temp_repo)

    # External lock is held
    assert orchestrator.acquire_workspace_lock(ws_root, "EXTERNAL-HOLDER") is True

    # Processing next item must fail closed and return None without altering status
    result = orchestrator.process_next_work_item(
        workspace_id=ws_id,
        workspace_root=ws_root,
        repo=temp_repo,
        runner=lambda item: None,
    )
    assert result is None
    item = temp_repo.get_agent_work("WORK-CONTEND-1")
    assert item is not None
    assert item.status == "queued"

    # Release external lock and retry processing
    orchestrator.release_workspace_lock(ws_root, "EXTERNAL-HOLDER")
    executed = []
    result2 = orchestrator.process_next_work_item(
        workspace_id=ws_id,
        workspace_root=ws_root,
        repo=temp_repo,
        runner=lambda item: executed.append(item.work_id),
    )
    assert result2 is not None
    assert result2.status == "completed"
    assert executed == ["WORK-CONTEND-1"]


def test_workspace_chat_app_wires_enqueue_and_process_work_item():
    """Verify workspace_chat_app user tasks enqueue before execution and run via process_next_work_item in Conversational Omnibar."""
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")

    # Static block is eliminated
    assert "_render_local_work_tools" not in app_source

    # Omnibar wires enqueue, process, and drain via orchestrator
    assert "orch.enqueue_work_item(" in app_source
    assert "orch.process_next_work_item(" in app_source
    assert "_drain_queued_agent_tasks(" in app_source

    # Inline artifact card in chat UI wires rollback
    assert "q_orch.rollback(" in ui_source or "orch.rollback(" in ui_source


def test_factory_error_and_process_review_queue_execution_and_rollback(temp_repo, temp_workspace, tmp_path):
    """Verify that factory error and process review work items execute cleanly in queue, preserve metadata, and roll back."""
    from aios_habit.agent_work_artifact import create_factory_error_report, create_process_design_review

    orchestrator = WorkspaceAgentOrchestrator()
    ws_id = "ws-real-queue-run"
    ws_root = str(temp_workspace)
    fixture_error = Path("tests/fixtures/agent_harness/factory_error/nhat_ky_lo_A17.log").resolve()
    fixture_csv = Path("tests/fixtures/agent_harness/factory_error/so_lieu_lo_A17.csv").resolve()
    fixture_guideline = Path("tests/fixtures/agent_harness/process_design/guideline_han_v2.md").resolve()
    out_dir = tmp_path / "artifacts"

    # 1. Enqueue and process factory error report
    err_work_id = "WORK-QUEUE-ERR-01"
    err_task = _make_work(
        err_work_id,
        ws_id,
        "error_report",
        "Báo cáo lỗi qua hàng đợi",
        allowed_roots=(ws_root,),
    )
    orchestrator.enqueue_work_item(work=err_task, repo=temp_repo)

    def _run_err(item_record):
        rep_res = create_factory_error_report(
            source_paths=[fixture_error, fixture_csv],
            output_dir=out_dir,
            work_id=item_record.work_id,
        )
        temp_repo.update_agent_work_status(
            item_record.work_id,
            "completed",
            result_ref=str(rep_res.report_path),
            checkpoint_ref=str(rep_res.report_path),
        )

    processed_err = orchestrator.process_next_work_item(
        workspace_id=ws_id,
        workspace_root=ws_root,
        repo=temp_repo,
        runner=_run_err,
    )
    assert processed_err is not None
    assert processed_err.status == "completed"
    assert Path(processed_err.result_ref).is_file()
    assert processed_err.allowed_roots == (ws_root,)

    # Rollback factory error report
    ok_err, msg_err = orchestrator.rollback(processed_err.checkpoint_ref)
    assert ok_err is True
    assert not Path(processed_err.result_ref).exists()
    temp_repo.update_agent_work_status(processed_err.work_id, "rolled_back")
    assert temp_repo.get_agent_work(processed_err.work_id).status == "rolled_back"

    # 2. Enqueue and process process design review
    rev_work_id = "WORK-QUEUE-REV-01"
    rev_task = _make_work(
        rev_work_id,
        ws_id,
        "process_design_review",
        "Rà soát công đoạn qua hàng đợi",
        allowed_roots=(ws_root,),
    )
    orchestrator.enqueue_work_item(work=rev_task, repo=temp_repo)

    def _run_rev(item_record):
        rev_res = create_process_design_review(
            source_paths=[fixture_guideline],
            output_dir=out_dir,
            work_id=item_record.work_id,
        )
        temp_repo.update_agent_work_status(
            item_record.work_id,
            "completed",
            result_ref=str(rev_res.report_path),
            checkpoint_ref=str(rev_res.report_path),
        )

    processed_rev = orchestrator.process_next_work_item(
        workspace_id=ws_id,
        workspace_root=ws_root,
        repo=temp_repo,
        runner=_run_rev,
    )
    assert processed_rev is not None
    assert processed_rev.status == "completed"
    assert Path(processed_rev.result_ref).is_file()

    # Rollback process review
    ok_rev, msg_rev = orchestrator.rollback(processed_rev.checkpoint_ref)
    assert ok_rev is True
    assert not Path(processed_rev.result_ref).exists()


def test_cancel_work_item_releases_both_explicit_and_allowed_roots(temp_repo, tmp_path):
    """Verify that cancelling releases locks on both explicit workspace_root and all allowed_roots."""
    orchestrator = WorkspaceAgentOrchestrator()
    ws_id = "ws-dual-root"
    root_a = str((tmp_path / "root_a").resolve())
    root_b = str((tmp_path / "root_b").resolve())
    Path(root_a).mkdir()
    Path(root_b).mkdir()

    work_id = "WORK-DUAL-CANCEL"
    task = _make_work(work_id, ws_id, "code_change", "Tác vụ đa thư mục", allowed_roots=(root_a,))
    orchestrator.enqueue_work_item(work=task, repo=temp_repo)

    # Lock both roots
    assert orchestrator.acquire_workspace_lock(root_a, work_id) is True
    assert orchestrator.acquire_workspace_lock(root_b, work_id) is True

    # Cancel passing root_b as workspace_root: both root_b and root_a (from allowed_roots) must be released
    cancelled = orchestrator.cancel_work_item(work_id=work_id, repo=temp_repo, workspace_root=root_b)
    assert cancelled is True

    # Both roots must now be free
    assert orchestrator.acquire_workspace_lock(root_a, "NEXT-HOLDER") is True
    orchestrator.release_workspace_lock(root_a, "NEXT-HOLDER")
    assert orchestrator.acquire_workspace_lock(root_b, "NEXT-HOLDER") is True
    orchestrator.release_workspace_lock(root_b, "NEXT-HOLDER")


def test_rollback_idempotent_on_unlinked_artifact_file(tmp_path):
    """Verify that rollback on an artifact path that was already unlinked succeeds idempotently."""
    orchestrator = WorkspaceAgentOrchestrator()
    artifact_dir = tmp_path / "agent_artifacts"
    artifact_dir.mkdir(parents=True)
    report_file = artifact_dir / "bao_cao_loi_WORK-TEST-IDEMP.md"
    report_file.write_text("# Test content", encoding="utf-8")

    # First rollback deletes file
    ok1, msg1 = orchestrator.rollback(str(report_file))
    assert ok1 is True
    assert not report_file.exists()

    # Second rollback on already deleted file succeeds idempotently
    ok2, msg2 = orchestrator.rollback(str(report_file))
    assert ok2 is True
    assert "trước đó" in msg2


def test_process_next_work_item_preserves_custom_status_set_by_runner(temp_repo, temp_workspace):
    """Verify process_next_work_item does not overwrite status if runner set a non-running status."""
    orchestrator = WorkspaceAgentOrchestrator()
    ws_id = "ws-custom-status"
    ws_root = str(temp_workspace)

    work_id = "WORK-CUSTOM-STATUS"
    task = _make_work(work_id, ws_id, "error_report", "Báo cáo lỗi tự đổi trạng thái")
    orchestrator.enqueue_work_item(work=task, repo=temp_repo)

    def custom_runner(item: AgentWorkRecord):
        # Runner explicitly sets status with metadata
        temp_repo.update_agent_work_status(
            item.work_id,
            "completed",
            result_ref="ref/custom/path.md",
            checkpoint_ref="ref/custom/path.md",
        )

    processed = orchestrator.process_next_work_item(
        workspace_id=ws_id,
        workspace_root=ws_root,
        repo=temp_repo,
        runner=custom_runner,
    )
    assert processed is not None
    assert processed.status == "completed"
    assert processed.result_ref == "ref/custom/path.md"
    assert processed.checkpoint_ref == "ref/custom/path.md"
