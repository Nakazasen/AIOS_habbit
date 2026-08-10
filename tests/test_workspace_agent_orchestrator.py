from dataclasses import dataclass
from aios_habit.workspace_agent_models import WorkspaceAgentRequest
from aios_habit.workspace_agent_orchestrator import WorkspaceAgentOrchestrator


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
