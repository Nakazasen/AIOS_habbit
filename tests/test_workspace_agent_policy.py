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

