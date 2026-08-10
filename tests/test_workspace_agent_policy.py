import pytest
from aios_habit.workspace_agent_policy import AgentPolicyError, authorize_tool, validate_request


def test_policy_blocks_destructive_or_unapproved_operations(tmp_path):
    with pytest.raises(AgentPolicyError): authorize_tool('git_discard', {}, approved=True)
    with pytest.raises(AgentPolicyError): authorize_tool('execute_command', {'command': 'pytest'}, approved=False)
    assert authorize_tool('search_files', {'query': 'x'}, approved=False).category == 'read'


def test_policy_requires_explicit_scope_and_real_workspace(tmp_path):
    with pytest.raises(AgentPolicyError): validate_request(workspace_root=str(tmp_path), instruction='x', scope_confirmed=False)
    assert validate_request(workspace_root=str(tmp_path), instruction='x', scope_confirmed=True) == str(tmp_path.resolve())
