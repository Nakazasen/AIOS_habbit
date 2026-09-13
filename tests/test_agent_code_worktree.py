"""E2E tests for US3: Agent code edit, test, re-test, import result, and rollback."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from aios_habit.opencode_runtime_adapter import OpenCodeRuntimeAdapter, RuntimeRequest
from aios_habit.workspace_agent_orchestrator import WorkspaceAgentOrchestrator
from aios_habit.workspace_agent_policy import AgentPolicyError

FIXTURE_CODE_DIR = Path(__file__).resolve().parent / "fixtures" / "agent_harness" / "code_workspace"


def test_e2e_code_fix_cycle(tmp_path: Path):
    workspace = tmp_path / "workspace"
    shutil.copytree(FIXTURE_CODE_DIR, workspace)

    orchestrator = WorkspaceAgentOrchestrator()
    work_id = "WORK-CODE-001"
    test_command = "pytest yield_rate_check.py"

    def fix_action(adapter: OpenCodeRuntimeAdapter) -> None:
        read_res = adapter.execute_request(
            RuntimeRequest(
                work_id=work_id,
                action="read_file",
                payload={"path": "yield_rate.py"},
            )
        )
        content = read_res.payload["content"]
        assert "passed // inspected" in content

        # Fix integer division bug
        fixed_content = content.replace("passed // inspected * 100", "(passed / inspected) * 100")

        adapter.execute_request(
            RuntimeRequest(
                work_id=work_id,
                action="edit_file",
                payload={"path": "yield_rate.py", "content": fixed_content},
            )
        )

    # 1. Run code task in isolated worktree
    verification, checkpoint = orchestrator.run_code_task(
        work_id=work_id,
        workspace_root=str(workspace),
        instruction="Sửa lỗi chia số nguyên khi tính tỷ lệ thu hồi",
        test_command=test_command,
        fix_action=fix_action,
    )

    # Verification checks
    assert verification.test_passed is True
    assert verification.exit_code == 0
    assert verification.has_conflict is False
    assert verification.can_import is True
    assert "yield_rate.py" in verification.files_changed
    assert "passed // inspected" in verification.diff_summary
    assert "(passed / inspected)" in verification.diff_summary
    assert "sẵn sàng" in verification.explanation_vi.lower()

    # Main workspace remains untouched before import
    original_in_workspace = (workspace / "yield_rate.py").read_text(encoding="utf-8")
    assert "passed // inspected" in original_in_workspace

    # 2. Import verified changes to workspace
    imported, msg = orchestrator.import_code_result(
        work_id=work_id,
        workspace_root=str(workspace),
        worktree_path=checkpoint.task_root,
        files_to_import=verification.files_changed,
    )
    assert imported is True
    assert "Đã đưa thành công" in msg

    # Main workspace now has the fix
    updated_in_workspace = (workspace / "yield_rate.py").read_text(encoding="utf-8")
    assert "(passed / inspected) * 100" in updated_in_workspace

    # 3. Test rollback
    ok, rollback_msg = orchestrator.rollback(checkpoint)
    assert ok is True
    # Worktree is rolled back to original baseline
    reverted_worktree = (Path(checkpoint.task_root) / "yield_rate.py").read_text(encoding="utf-8")
    assert "passed // inspected" in reverted_worktree


def test_e2e_code_fix_detects_conflict(tmp_path: Path):
    workspace = tmp_path / "workspace"
    shutil.copytree(FIXTURE_CODE_DIR, workspace)

    orchestrator = WorkspaceAgentOrchestrator()
    work_id = "WORK-CODE-CONFLICT"
    test_command = "pytest yield_rate_check.py"

    def fix_with_concurrent_conflict(adapter: OpenCodeRuntimeAdapter) -> None:
        # Edit in worktree
        adapter.execute_request(
            RuntimeRequest(
                work_id=work_id,
                action="edit_file",
                payload={"path": "yield_rate.py", "content": "def calculate_yield(passed, inspected):\n    return (passed / inspected) * 100\n"},
            )
        )
        # Simultaneously edit same file in main workspace!
        (workspace / "yield_rate.py").write_text("# Concurrent edit in main workspace\n", encoding="utf-8")

    verification, checkpoint = orchestrator.run_code_task(
        work_id=work_id,
        workspace_root=str(workspace),
        instruction="Sửa lỗi và kiểm tra xung đột",
        test_command=test_command,
        fix_action=fix_with_concurrent_conflict,
    )

    assert verification.has_conflict is True
    assert verification.can_import is False
    assert "yield_rate.py" in verification.conflict_files
    assert "xung đột" in verification.explanation_vi


def test_e2e_code_fix_fails_gracefully(tmp_path: Path):
    workspace = tmp_path / "workspace"
    shutil.copytree(FIXTURE_CODE_DIR, workspace)

    orchestrator = WorkspaceAgentOrchestrator()
    work_id = "WORK-CODE-FAIL"
    test_command = "pytest yield_rate_check.py"

    def broken_fix_action(adapter: OpenCodeRuntimeAdapter) -> None:
        # Write broken code that still fails the test
        adapter.execute_request(
            RuntimeRequest(
                work_id=work_id,
                action="edit_file",
                payload={"path": "yield_rate.py", "content": "def calculate_yield(passed, inspected):\n    return -1.0\n"},
            )
        )

    verification, checkpoint = orchestrator.run_code_task(
        work_id=work_id,
        workspace_root=str(workspace),
        instruction="Sửa lỗi nhưng test không đạt",
        test_command=test_command,
        fix_action=broken_fix_action,
    )

    assert verification.test_passed is False
    assert verification.can_import is False
    assert "chưa đạt" in verification.explanation_vi
