import json
import os
import subprocess
import sys
from pathlib import Path

from aios_habit.audit import audit_repo
from aios_habit.discovery import discover_projects
from aios_habit.memory import validate_memory
from aios_habit.models import EvidenceRecord, MemoryUnit, RAW_PATTERNS, scan_text_for_patterns
from aios_habit.phase_gate import phase_validate
from aios_habit.storage import append_jsonl


def run_cli(*args):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path("src").resolve())
    return subprocess.run(
        [sys.executable, "-m", "aios_habit.cli", *args],
        capture_output=True,
        text=True,
        env=env,
    )


def test_schema_parsing():
    for path in Path("10_schemas").glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))


def test_path_handling():
    assert Path("src") / "aios_habit"


def test_discovery_dry_run():
    cards = discover_projects(Path("."), 1)
    assert cards


def test_discovery_respects_ignore_denylist(tmp_path):
    visible = tmp_path / "visible"
    visible.mkdir()
    (visible / "README.md").write_text("x", encoding="utf-8")

    ignored = tmp_path / "__pycache__"
    ignored.mkdir()
    (ignored / "README.md").write_text("x", encoding="utf-8")

    cards = discover_projects(tmp_path, 2)
    assert any(card.name == "visible" for card in cards)
    assert not any(card.name == "__pycache__" for card in cards)


def test_evidence_validation():
    assert EvidenceRecord("", "", "", "").validate()
    assert not EvidenceRecord("EVD-1", "t", "markdown", "README.md").validate()


def test_memory_validation():
    memory = MemoryUnit("M", "identity", "t", "s", [], status="draft")
    assert not memory.validate()


def test_verified_memory_requires_existing_evidence(tmp_path):
    memory_path = tmp_path / "mem.jsonl"
    evidence_path = tmp_path / "evid.jsonl"
    memory = MemoryUnit("M", "identity", "t", "s", ["EVD-MISSING"], status="verified")
    append_jsonl(memory_path, memory.__dict__)
    assert validate_memory(memory_path, evidence_path)


def test_export_excludes_raw_transcript_markers():
    assert scan_text_for_patterns("raw transcript content", RAW_PATTERNS)


def test_export_excludes_local_only_evidence():
    record = EvidenceRecord("EVD-1", "t", "markdown", "p", allowed_for_export=False)
    assert record.allowed_for_export is False


def test_audit_fails_on_secret_pattern(tmp_path):
    (tmp_path / "README.md").write_text("api_key` = abcdefghijk", encoding="utf-8")
    errors, _warnings = audit_repo(tmp_path)
    assert errors


def test_audit_fails_on_missing_evidence(tmp_path):
    for filename in [
        "CONSTITUTION.md",
        "ROADMAP.md",
        "ARCHITECTURE.md",
        "PROJECT_HANDOVER.md",
        "CHANGELOG.md",
        "README.md",
        "pyproject.toml",
    ]:
        (tmp_path / filename).write_text("x", encoding="utf-8")
    memory = MemoryUnit("M", "identity", "t", "s", ["EVD-X"], status="verified")
    append_jsonl(tmp_path / "05_memory_vault/memory_units.jsonl", memory.__dict__)
    errors, _warnings = audit_repo(tmp_path)
    assert any("evidence missing" in error for error in errors)


def test_phase_gate_fails_when_deliverable_missing(tmp_path):
    errors = phase_validate(tmp_path, "0")
    assert errors


def test_phase_gate_passes_when_fixture_complete():
    assert not phase_validate(Path("."), "0")


def test_cli_smoke_tests():
    assert run_cli("--help").returncode == 0
    assert run_cli("status").returncode == 0


def test_handover_generation():
    assert run_cli("handover", "build", "--dry-run").returncode == 0


def test_git_public_safety_ignore_rules():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    required_patterns = [
        "03_evidence_registry/records/*.jsonl",
        "05_memory_vault/*.jsonl",
        "07_ai_export_packs/*/*_export_pack.md",
        ".env",
        "__pycache__/",
    ]
    for pattern in required_patterns:
        assert pattern in gitignore


def test_supported_workspace_chat_launchers_exist():
    assert Path("scripts/run_workspace_chat.ps1").exists()
    assert Path("RUN_AIOS_WORKSPACE_CHAT.bat").exists()



def test_secret_pattern_ignores_api_key_variable_plumbing_but_catches_literals():
    from aios_habit.core import SECRET_PATTERNS, scan_text_for_patterns

    assert not scan_text_for_patterns('api_key=api_key,\nif config.api_key:\n', SECRET_PATTERNS)
    runtime_secret_literal = 'api_key=' + chr(34) + 'real-looking-token' + chr(34)
    assert scan_text_for_patterns(runtime_secret_literal, SECRET_PATTERNS)
