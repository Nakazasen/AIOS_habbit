import json
import subprocess
import sys
from types import SimpleNamespace

import aios_habit.ai_router as router_module
import aios_habit.cli as cli_module
from aios_habit.ai_router import RouterProviderConfig


def test_owner_workflow_cli_fake_data_is_read_only():
    result = subprocess.run(
        [sys.executable, "-m", "aios_habit.cli", "owner-workflow", "--fake-data"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30.0,
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
        timeout=30.0,
    )
    payload = json.loads(result.stdout)
    assert payload["mode"] == "real_data_local_only"
    assert payload["read_only"] is True
    assert payload["provider_call"] is False
    assert payload["notebooklm_call"] is False


def test_provider_check_is_read_only_when_no_provider_is_configured(capsys, monkeypatch):
    monkeypatch.setattr(router_module, "provider_configs_from_env", lambda: [])

    result = cli_module.cmd_provider_check(SimpleNamespace(timeout=1))
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["status"] == "PASS"
    assert payload["read_only"] is True
    assert payload["configured_provider_count"] == 0
    assert payload["checks"] == []


def test_provider_check_reports_model_state_without_exposing_secret(capsys, monkeypatch):
    secret = "".join(("fake", "-secret-value"))
    config = RouterProviderConfig(
        "deepseek",
        "DeepSeek",
        "https://api.deepseek.com/chat/completions",
        "retired-model",
        secret,
        True,
        allow_model_auto_substitution=False,
    )
    monkeypatch.setattr(router_module, "provider_configs_from_env", lambda: [config])
    monkeypatch.setattr(
        cli_module,
        "check_provider_models",
        lambda **_kwargs: {
            "status": "stale_models",
            "error": "",
            "latency_ms": 12.5,
            "valid": [],
            "stale": ["retired-model"],
            "suggestion": "deepseek-v4-flash",
            "available": ["deepseek-v4-flash"],
        },
    )

    result = cli_module.cmd_provider_check(SimpleNamespace(timeout=1))
    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    check = payload["checks"][0]

    assert result == 0
    assert payload["status"] == "WARN"
    assert check["provider_id"] == "deepseek"
    assert check["model_from"] == "environment_override"
    assert check["suggested_model"] == "deepseek-v4-flash"
    assert check["available_model_count"] == 1
    assert secret not in stdout
