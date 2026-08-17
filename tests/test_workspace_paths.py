from pathlib import Path

from aios_habit.workspace_paths import default_agent_workspace_root


def test_default_agent_workspace_root_is_repository_root(monkeypatch):
    monkeypatch.delenv("AIOS_AGENT_WORKSPACE_ROOT", raising=False)

    assert default_agent_workspace_root() == Path(__file__).resolve().parents[1]


def test_default_agent_workspace_root_honors_explicit_override(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_AGENT_WORKSPACE_ROOT", str(tmp_path))

    assert default_agent_workspace_root() == tmp_path.resolve()
