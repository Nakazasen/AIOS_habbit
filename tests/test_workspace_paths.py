from pathlib import Path

from aios_habit.workspace_paths import default_agent_workspace_root


def test_default_agent_workspace_root_is_repository_root(monkeypatch):
    monkeypatch.delenv("AIOS_AGENT_WORKSPACE_ROOT", raising=False)

    assert default_agent_workspace_root() == Path(__file__).resolve().parents[1]


def test_default_agent_workspace_root_honors_explicit_override(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_AGENT_WORKSPACE_ROOT", str(tmp_path))

    assert default_agent_workspace_root() == tmp_path.resolve()
 
 
def test_load_env_file_parses_values_and_preserves_existing(tmp_path, monkeypatch):
    import os
    from aios_habit.workspace_paths import load_env_file

    env_path = tmp_path / ".env"
    env_path.write_text(
        "# Synthetic comment\n"
        "TEST_KEY_UNQUOTED=hello_world\n"
        'TEST_KEY_DOUBLE_QUOTES="double quoted value"\n'
        "TEST_KEY_SINGLE_QUOTES='single quoted value'\n"
        "TEST_KEY_EXISTING=new_value\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("TEST_KEY_EXISTING", "original_value")
    monkeypatch.delenv("TEST_KEY_UNQUOTED", raising=False)
    monkeypatch.delenv("TEST_KEY_DOUBLE_QUOTES", raising=False)
    monkeypatch.delenv("TEST_KEY_SINGLE_QUOTES", raising=False)

    load_env_file(env_path)

    assert os.environ.get("TEST_KEY_UNQUOTED") == "hello_world"
    assert os.environ.get("TEST_KEY_DOUBLE_QUOTES") == "double quoted value"
    assert os.environ.get("TEST_KEY_SINGLE_QUOTES") == "single quoted value"
    assert os.environ.get("TEST_KEY_EXISTING") == "original_value"


def test_load_env_file_handles_missing_file(tmp_path):
    from aios_habit.workspace_paths import load_env_file

    missing = tmp_path / "non_existent.env"
    load_env_file(missing)  # Should not raise exception
