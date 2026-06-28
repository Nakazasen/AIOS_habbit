import json
import subprocess
import sys


def test_owner_workflow_cli_fake_data_is_read_only():
    result = subprocess.run(
        [sys.executable, "-m", "aios_habit.cli", "owner-workflow", "--fake-data"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert payload["mode"] == "fake_data"
    assert payload["read_only"] is True
    assert payload["provider_call"] is False
    assert payload["notebooklm_call"] is False
    assert payload["writes_runtime_outputs"] is False
    assert payload["p1_opened"] is False
    assert payload["runbook"] == "docs/P1_OWNER_ACCEPTANCE_RUNBOOK.md"
    assert any("local_only" in step for step in payload["steps"])
    assert any("insufficient" in step for step in payload["steps"])
    assert any("local answer composer" in step for step in payload["steps"])
    assert any("does not call NotebookLM" in warning for warning in payload["warnings"])


def test_owner_workflow_cli_default_real_data_local_only_mode():
    result = subprocess.run(
        [sys.executable, "-m", "aios_habit.cli", "owner-workflow"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["mode"] == "real_data_local_only"
    assert payload["read_only"] is True
    assert payload["provider_call"] is False
    assert payload["notebooklm_call"] is False
