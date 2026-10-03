import tempfile
from pathlib import Path

import pytest
from aios_habit.workspace_agent_policy import (
    AgentPolicyError,
    AgentScopeGrant,
    TASK_TYPE_CODE_CHANGE,
    TASK_TYPE_ERROR_REPORT,
    TASK_TYPE_PROCESS_DESIGN_REVIEW,
    authorize_scope_action,
    authorize_tool,
    create_scope_grant,
    validate_path_in_task_root,
    validate_request,
    validate_test_command,
)


def test_policy_blocks_destructive_or_unapproved_operations(tmp_path):
    with pytest.raises(AgentPolicyError): authorize_tool('git_discard', {}, approved=True)
    with pytest.raises(AgentPolicyError): authorize_tool('delete_file', {}, approved=True)
    with pytest.raises(AgentPolicyError): authorize_tool('move_file', {}, approved=True)
    with pytest.raises(AgentPolicyError): authorize_tool('execute_command', {'command': 'pytest'}, approved=False)
    assert authorize_tool('search_files', {'query': 'x'}, approved=False).category == 'read'


def test_policy_requires_explicit_scope_and_real_workspace(tmp_path):
    with pytest.raises(AgentPolicyError): validate_request(workspace_root=str(tmp_path), instruction='x', scope_confirmed=False)
    assert validate_request(workspace_root=str(tmp_path), instruction='x', scope_confirmed=True) == str(tmp_path.resolve())


def test_validate_path_in_task_root(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    valid_file = sub / "report.md"
    valid_file.write_text("ok", encoding="utf-8")

    # Valid relative and absolute paths within root
    assert validate_path_in_task_root("sub/report.md", tmp_path) == valid_file.resolve()
    assert validate_path_in_task_root(str(valid_file), tmp_path) == valid_file.resolve()

    # Path traversal attempts
    with pytest.raises(AgentPolicyError, match="path traversal"):
        validate_path_in_task_root("../outside.txt", tmp_path)
    with pytest.raises(AgentPolicyError, match="path traversal"):
        validate_path_in_task_root("sub/../../outside.txt", tmp_path)

    # Path outside task root
    outside = tmp_path.parent / "escape.txt"
    with pytest.raises(AgentPolicyError, match="ngoài phạm vi"):
        validate_path_in_task_root(str(outside), tmp_path)

    # Forbidden files & secrets
    with pytest.raises(AgentPolicyError, match="chứa bí mật"):
        validate_path_in_task_root(".env", tmp_path)
    with pytest.raises(AgentPolicyError, match="chứa bí mật"):
        validate_path_in_task_root(".env.production", tmp_path)
    with pytest.raises(AgentPolicyError, match="chứa bí mật"):
        validate_path_in_task_root("keys/id_rsa", tmp_path)
    with pytest.raises(AgentPolicyError, match="chứa bí mật"):
        validate_path_in_task_root("cert.pem", tmp_path)
    with pytest.raises(AgentPolicyError, match="chứa bí mật"):
        validate_path_in_task_root("user_credentials.json", tmp_path)

    # Forbidden directories
    with pytest.raises(AgentPolicyError, match="vùng cấm"):
        validate_path_in_task_root(".git/config", tmp_path)
    with pytest.raises(AgentPolicyError, match="vùng cấm"):
        validate_path_in_task_root("local_cases/cases.db", tmp_path)


def test_validate_test_command():
    # Valid allowlisted commands
    assert validate_test_command("pytest") == "pytest"
    assert validate_test_command("python -m unittest discover") == "python -m unittest discover"
    assert validate_test_command(["python", "test_yield_rate.py"]) == "python test_yield_rate.py"
    assert validate_test_command("uv run --no-sync pytest tests/") == "uv run --no-sync pytest tests/"

    # Shell injection attempts
    with pytest.raises(AgentPolicyError, match="ký tự đặc biệt"):
        validate_test_command("pytest; rm -rf /")
    with pytest.raises(AgentPolicyError, match="ký tự đặc biệt"):
        validate_test_command("pytest && whoami")
    with pytest.raises(AgentPolicyError, match="ký tự đặc biệt"):
        validate_test_command("pytest | grep pass")
    with pytest.raises(AgentPolicyError, match="ký tự đặc biệt"):
        validate_test_command("pytest > output.txt")
    with pytest.raises(AgentPolicyError, match="ký tự đặc biệt"):
        validate_test_command("pytest $(calc)")

    # Non-allowlisted commands
    with pytest.raises(AgentPolicyError, match="không nằm trong danh sách"):
        validate_test_command("git commit -m evil")
    with pytest.raises(AgentPolicyError, match="không nằm trong danh sách"):
        validate_test_command("curl http://example.com")
    # Substring bypass attempts: containing allowlisted token later in string must fail
    with pytest.raises(AgentPolicyError, match="không nằm trong danh sách"):
        validate_test_command("curl evil.com pytest")
    with pytest.raises(AgentPolicyError, match="không nằm trong danh sách"):
        validate_test_command("bash -c pytest")
    with pytest.raises(AgentPolicyError, match="không nằm trong danh sách"):
        validate_test_command("echo hello uv run pytest")


def test_is_safe_artifact_path(tmp_path):
    from aios_habit.workspace_agent_policy import is_safe_artifact_path

    # Traversal and invalid paths
    assert is_safe_artifact_path("") is False
    assert is_safe_artifact_path("   ") is False
    assert is_safe_artifact_path("../outside.md") is False
    assert is_safe_artifact_path("sub/../../outside.md") is False
    assert is_safe_artifact_path("C:\\Windows\\System32\\cmd.exe") is False

    # Default safe roots: pytest tmp_path is allowed (starts with pytest-)
    temp_file = tmp_path / "report.md"
    temp_file.write_text("ok", encoding="utf-8")
    assert is_safe_artifact_path(temp_file) is True

    # Entire OS tempdir must NOT be allowed by default (Finding 4)
    arbitrary_temp_file = Path(tempfile.gettempdir()) / "secret_os_temp_file.csv"
    assert is_safe_artifact_path(arbitrary_temp_file) is False

    # AIOS-created temp subdirectories are allowed
    aios_temp_file = Path(tempfile.gettempdir()) / "aios_ckpt_test" / "report.md"
    assert is_safe_artifact_path(aios_temp_file) is True

    # Custom allowed roots
    custom_root = tmp_path / "custom_work"
    custom_root.mkdir()
    custom_file = custom_root / "output.json"
    assert is_safe_artifact_path(custom_file, allowed_roots=(custom_root,)) is True


def test_is_safe_artifact_path_allows_agent_doc_root(tmp_path, monkeypatch):
    """Hoi quy 2026-10-03 (verify lan 2 cho-muse): cong an toan cua the dinh
    kem trong chat phai tin goc mac dinh cua bao cao agent
    (default_doc_root(): ~/AIOS_bao_cao khi khong dat AIOS_DOC_ROOT), neu
    khong nut Tai ve bi mo, nut Xem toan van bao sai. Traversal van bi chan."""
    from aios_habit.agent_doc_edit import default_doc_root
    from aios_habit.workspace_agent_policy import is_safe_artifact_path

    monkeypatch.setenv("AIOS_DOC_ROOT", str(tmp_path / "AIOS_bao_cao"))
    root = default_doc_root()
    report = root / "tuan.docx"
    report.write_bytes(b"PK fake docx")
    md_file = root / "tuan-verify.md"
    md_file.write_text("ok", encoding="utf-8")

    # File duoi goc bao cao: the dinh kem tin (duoc phep)
    assert is_safe_artifact_path(report, allowed_roots=(root,)) is True
    assert is_safe_artifact_path(md_file, allowed_roots=(root,)) is True
    # (Khong assert False khi thieu allowed_roots o day vi tmp_path cua
    # pytest von la thu muc tam duoc kiem soat, tu nhien duoc phep.)

    # Traversal ".." ra khoi goc: chan
    assert is_safe_artifact_path(str(root / ".." / "secret.md"), allowed_roots=(root,)) is False

    # File ngoai goc: chan (dung file ngay duoi thu muc tam he thong,
    # khong thuoc bat ky goc mac dinh nao)
    outside = Path(tempfile.gettempdir()) / "secret_outside_doc_root.md"
    assert is_safe_artifact_path(outside, allowed_roots=(root,)) is False


def test_scope_grant_and_action_authorization(tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    # Code change grant
    code_grant = create_scope_grant(
        work_id="WORK-001",
        task_root=worktree,
        task_type=TASK_TYPE_CODE_CHANGE,
    )
    assert code_grant.scope_digest
    assert "run_test" in code_grant.allowed_actions
    assert "edit_file" in code_grant.allowed_actions

    # Action authorization for code change
    dec = authorize_scope_action(code_grant, "read_file", path="main.py")
    assert dec.category == "read"

    dec_test = authorize_scope_action(code_grant, "run_test", command="pytest -q")
    assert dec_test.category == "command"

    # Always denied actions
    with pytest.raises(AgentPolicyError, match="bị cấm tuyệt đối"):
        authorize_scope_action(code_grant, "git_commit")
    with pytest.raises(AgentPolicyError, match="bị cấm tuyệt đối"):
        authorize_scope_action(code_grant, "git_push")

    # Error report grant: run_test is NOT allowed
    report_grant = create_scope_grant(
        work_id="WORK-002",
        task_root=worktree,
        task_type=TASK_TYPE_ERROR_REPORT,
    )
    assert "run_test" not in report_grant.allowed_actions
    with pytest.raises(AgentPolicyError, match="không được cấp phép"):
        authorize_scope_action(report_grant, "run_test", command="pytest")

