"""Unit tests for agent_work persistence in WorkspaceCaseRepository."""
from __future__ import annotations

from pathlib import Path
from aios_habit.workspace_case_models import AgentWorkRecord, utc_now_iso
from aios_habit.workspace_case_repository import WorkspaceCaseRepository


def test_agent_work_crud_lifecycle(tmp_path: Path):
    db_path = tmp_path / "cases.sqlite"
    repo = WorkspaceCaseRepository(db_path)
    now = utc_now_iso()

    work1 = AgentWorkRecord(
        work_id="WORK-001",
        workspace_id="WS-ALPHA",
        work_type="code_change",
        goal_vi="Sửa lỗi tính tỷ lệ thu hồi",
        created_at=now,
        updated_at=now,
        allowed_roots=("src/",),
        allowed_commands=("pytest",),
        status="queued",
        queue_position=1,
        idempotency_key="IDEMP-001",
        record_digest="sha256:digest001",
    )

    work2 = AgentWorkRecord(
        work_id="WORK-002",
        workspace_id="WS-ALPHA",
        work_type="error_report",
        goal_vi="Lập báo cáo lỗi nhà máy",
        created_at=now,
        updated_at=now,
        status="queued",
        queue_position=2,
    )

    # 1. Save
    repo.save_agent_work(work1)
    repo.save_agent_work(work2)

    # 2. Get
    retrieved = repo.get_agent_work("WORK-001")
    assert retrieved is not None
    assert retrieved.work_id == "WORK-001"
    assert retrieved.goal_vi == "Sửa lỗi tính tỷ lệ thu hồi"
    assert retrieved.allowed_roots == ("src/",)
    assert retrieved.allowed_commands == ("pytest",)
    assert retrieved.status == "queued"

    # 3. List by workspace and status
    listed = repo.list_agent_work(workspace_id="WS-ALPHA")
    assert len(listed) == 2
    assert [w.work_id for w in listed] == ["WORK-001", "WORK-002"]

    # 4. Update status
    repo.update_agent_work_status(
        "WORK-001",
        "running",
        checkpoint_ref="CKPT-001",
    )
    retrieved_updated = repo.get_agent_work("WORK-001")
    assert retrieved_updated is not None
    assert retrieved_updated.status == "running"
    assert retrieved_updated.checkpoint_ref == "CKPT-001"

    # 5. Filter by status
    running_list = repo.list_agent_work(status="running")
    assert len(running_list) == 1
    assert running_list[0].work_id == "WORK-001"
