"""Integration checks for the pinned OpenCode runtime on harmless fixtures."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "agent_harness"
PROBE_SCRIPT = REPOSITORY_ROOT / "scripts" / "probe_opencode_runtime.py"
PROBE_MODEL_ENV = "AIOS_OPENCODE_PROBE_MODEL"


def _run_probe(tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    model = os.environ.get(PROBE_MODEL_ENV, "").strip()
    if not model:
        pytest.skip(
            "G1 chỉ gọi Agent khi chủ sở hữu đặt AIOS_OPENCODE_PROBE_MODEL rõ ràng; "
            "không tự dùng credential cloud có sẵn."
        )

    workspace = tmp_path / "harness-fixture"
    shutil.copytree(FIXTURE_ROOT, workspace)

    unicode_spec = json.loads(
        (workspace / "factory_error" / "duong_dan_unicode.json").read_text(encoding="utf-8")
    )
    unicode_target = workspace / unicode_spec["relative_path"]
    unicode_target.parent.mkdir(parents=True)
    unicode_target.write_text(unicode_spec["content_vi"], encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(PROBE_SCRIPT),
            "--fixture",
            str(workspace),
            "--bind",
            "127.0.0.1",
            "--model",
            model,
            "--json",
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=180,
    )
    assert completed.stdout, completed.stderr
    return completed, json.loads(completed.stdout)


def test_probe_proves_required_runtime_capabilities(tmp_path: Path) -> None:
    completed, payload = _run_probe(tmp_path)

    assert completed.returncode == 0, payload
    assert payload["status"] == "passed"
    assert payload["runtime"]["version"] == "1.14.33"
    assert payload["runtime"]["binary_sha256"] == (
        "C37DD78F32F9636D4D79D0B23FF43E37FCFB5A418602074587B7CB280F8774E4"
    )

    capabilities = payload["capabilities"]
    for name in (
        "health",
        "create_session",
        "get_session",
        "list_events",
        "read_file",
        "search_files",
        "create_file",
        "edit_file",
        "run_test_failure",
        "run_test_success",
        "resume_session",
        "undo",
        "abort_session",
    ):
        assert capabilities[name]["status"] == "passed", (name, capabilities[name])

    workspace = payload["workspace"]
    assert workspace["baseline_digest"] == workspace["after_undo_digest"]
    assert workspace["created_file_removed"] is True
    assert workspace["unicode_round_trip"] is True


def test_probe_denies_actions_outside_the_task_root(tmp_path: Path) -> None:
    completed, payload = _run_probe(tmp_path)

    assert completed.returncode == 0, payload
    denials = payload["denials"]
    for action in (
        "path_traversal",
        "symlink_escape",
        "env_file",
        "command_not_allowed",
        "git_commit",
        "git_push",
    ):
        assert denials[action]["status"] == "denied", (action, denials[action])
        assert denials[action]["before_digest"] == denials[action]["after_digest"]


def test_probe_without_live_model_does_not_fake_pass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Reflect accurate OpenCode runtime status: with no live model connected, runtime remains blocked/unproved without faking PASS."""
    monkeypatch.delenv(PROBE_MODEL_ENV, raising=False)
    with pytest.raises(pytest.skip.Exception):
        _run_probe(tmp_path)
