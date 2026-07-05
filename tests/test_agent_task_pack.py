import os
import json
import shutil
import pytest
import tempfile
from pathlib import Path
from aios_habit.agent_task_pack import (
    build_agent_task_pack,
    canonicalize_task_pack,
    compute_task_pack_sha256,
    validate_agent_task_pack,
    export_agent_task_pack,
    resolve_privacy_level,
    ValidationError,
    ExportError
)

# Helper function to get a base valid task pack dict
def get_valid_pack():
    return build_agent_task_pack(
        task_id="A17_TASK_EXPORT_001",
        task_type="implementation",
        gate="AI-GW-A17A",
        agent_class="implementation",
        objective="Implement a pure builder for task pack.",
        repo_logical_id="AIOS_habbit_main",
        repo_path_policy="logical_relative",
        expected_branch="main",
        expected_head="f3a9b6c42d2aa40f2cd225f1684d70c06e9dc039",
        allowed_files=["src/aios_habit/agent_task_pack.py"],
        forbidden_files=[".ai/**"],
        allowed_commands=["uv run pytest"],
        forbidden_commands=["git push"],
        required_tests=["tests/test_agent_task_pack.py"],
        privacy_class="internal",
        destination="local_owner_only",
        purpose="Code implementation and test verification",
        consent_ref="consent-123",
        source_policy="redact_raw_contents",
        roadmap_reference={
            "phase": "Phase 4",
            "gate": "AI-GW-A17",
            "lock_status": "P1.0 LOCKED"
        },
        pass_fail_rules=["No forbidden files modified"],
        rollback={
            "allowed": True,
            "strategy": "manual_git_discard_by_owner",
            "description": "manual rollback"
        }
    )

def test_canonical_hash_deterministic():
    pack = get_valid_pack()
    hash1 = compute_task_pack_sha256(pack)
    hash2 = compute_task_pack_sha256(pack)
    assert hash1 == hash2

def test_canonical_json_key_ordering_stable():
    pack1 = {"z": 1, "a": 2, "b": {"y": 3, "x": 4}}
    pack2 = {"a": 2, "z": 1, "b": {"x": 4, "y": 3}}
    c1 = canonicalize_task_pack(pack1)
    c2 = canonicalize_task_pack(pack2)
    assert c1 == c2
    # Ensure no extra whitespace
    assert " " not in c1
    assert "\n" not in c1

def test_hash_excludes_pack_sha256():
    pack = get_valid_pack()
    hash_without = compute_task_pack_sha256(pack)

    # Add pack_sha256 and verify hash doesn't change
    pack_with = pack.copy()
    pack_with["pack_sha256"] = "dummy_hash_value"
    hash_with = compute_task_pack_sha256(pack_with)

    assert hash_without == hash_with

def test_md5_not_used_in_implementation():
    # Read the implementation file and search for MD5 usage
    imp_file = Path(__file__).resolve().parents[1] / "src" / "aios_habit" / "agent_task_pack.py"
    content = imp_file.read_text(encoding="utf-8")
    assert "md5" not in content.lower()
    assert "hashlib.md5" not in content

def test_task_id_validation():
    # Valid cases
    valid_ids = ["A17_TASK_001", "A-B-C", "TASK123", "A" * 80]
    for tid in valid_ids:
        pack = get_valid_pack()
        pack["task_id"] = tid
        # Should not raise ValidationError
        validate_agent_task_pack(pack)

    # Invalid cases
    invalid_ids = [
        "",                 # Empty
        "AB",               # Too short
        "A" * 82,           # Too long
        "task_id",          # Lowercase letters are not allowed in TASK_ID_REGEX
        "TASK/ID",          # Slash
        "TASK\\ID",         # Backslash
        "TASK..ID",         # Dot-dot
        "C:TASK",           # Drive letter
        "TASK\x00ID",       # Control char
        "TASK\nID"          # Control char
    ]
    for tid in invalid_ids:
        pack = get_valid_pack()
        pack["task_id"] = tid
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack)

def test_required_fields_present():
    # Remove required fields one by one
    from aios_habit.agent_task_pack import REQUIRED_FIELDS
    for field in REQUIRED_FIELDS:
        pack = get_valid_pack()
        pack.pop(field)
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack)

def test_strictest_wins_privacy():
    assert resolve_privacy_level(["public", "internal"]) == "internal"
    assert resolve_privacy_level(["public", "confidential", "internal"]) == "confidential"
    assert resolve_privacy_level(["local_only", "confidential"]) == "local_only"
    assert resolve_privacy_level([]) == "local_only"
    assert resolve_privacy_level(["unknown_class"]) == "local_only"

def test_missing_privacy_fields_fails():
    from aios_habit.agent_task_pack import REQUIRED_PRIVACY_FIELDS
    for field in REQUIRED_PRIVACY_FIELDS:
        pack = get_valid_pack()
        pack["privacy"][field] = None
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack)

def test_unknown_destination_fails():
    pack = get_valid_pack()
    pack["privacy"]["destination"] = "cloud" # reject cloud or unknown
    with pytest.raises(ValidationError):
        validate_agent_task_pack(pack)

def test_external_destination_path_restrictions():
    # If destination is external_manual_agent or owner_managed_chat, reject absolute paths, etc.
    destinations = ["external_manual_agent", "owner_managed_chat"]
    for dest in destinations:
        # Windows drive path
        pack = get_valid_pack()
        pack["privacy"]["destination"] = dest
        pack["scope"]["allowed_files"] = ["D:\\Sandbox\\file.txt"]
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack)

        # Unix absolute path
        pack = get_valid_pack()
        pack["privacy"]["destination"] = dest
        pack["scope"]["allowed_files"] = ["/var/log/file.txt"]
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack)

        # UNC path
        pack = get_valid_pack()
        pack["privacy"]["destination"] = dest
        pack["scope"]["allowed_files"] = ["\\\\server\\share\\file.txt"]
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack)

        # Home path (indicator)
        pack = get_valid_pack()
        pack["privacy"]["destination"] = dest
        pack["scope"]["allowed_files"] = ["~/file.txt"]
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack)

        # Home/username indicator
        pack = get_valid_pack()
        pack["privacy"]["destination"] = dest
        pack["scope"]["allowed_files"] = ["C:\\Users\\Admin\\file.txt"]
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack)

        # Traversal path
        pack = get_valid_pack()
        pack["privacy"]["destination"] = dest
        pack["scope"]["allowed_files"] = ["src/../tests/file.txt"]
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack)

        # Forbidden metadata/sensitive path
        pack = get_valid_pack()
        pack["privacy"]["destination"] = dest
        pack["scope"]["allowed_files"] = ["local_cases/case_001.json"]
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack)

def test_local_owner_only_path_behavior():
    # local_owner_only destination allows absolute local paths if policy permits
    pack = get_valid_pack()
    pack["privacy"]["destination"] = "local_owner_only"
    pack["repo"]["repo_path_policy"] = "local_owner_private"
    pack["scope"]["allowed_files"] = ["D:\\Sandbox\\file.txt"]
    # Should validate successfully
    validate_agent_task_pack(pack)

def test_confidential_local_only_raw_content_rejected():
    # If privacy class is confidential or local_only, reject raw content (secret/path/raw-marker) in objective
    sensitive_privacy_classes = ["confidential", "local_only"]
    for p_class in sensitive_privacy_classes:
        pack = get_valid_pack()
        pack["privacy"]["privacy_class"] = p_class

        # Test secret leak
        pack["objective"] = "My secret api key is sk-1234567890abcdef."
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack)

        # Test Windows path leak
        pack = get_valid_pack()
        pack["privacy"]["privacy_class"] = p_class
        pack["objective"] = "Look into D:\\Secrets\\code.py"
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack)

        # Test raw marker leak
        pack = get_valid_pack()
        pack["privacy"]["privacy_class"] = p_class
        pack["objective"] = "Review the raw transcript of discussion."
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack)

def test_utf8_parseable_no_bom():
    pack = get_valid_pack()
    with tempfile.TemporaryDirectory() as tmp_dir:
        exported_path, sha = export_agent_task_pack(pack, export_root=tmp_dir)
        content_bytes = Path(exported_path).read_bytes()
        assert not content_bytes.startswith(b"\xef\xbb\xbf")

        # Verify JSON parseable
        parsed = json.loads(content_bytes.decode("utf-8"))
        assert parsed["task_id"] == pack["task_id"]

def test_atomic_export_writes_under_outbox():
    pack = get_valid_pack()
    with tempfile.TemporaryDirectory() as tmp_dir:
        exported_path, sha = export_agent_task_pack(pack, export_root=tmp_dir)
        expected_path = Path(tmp_dir) / pack["task_id"] / f"{sha}.json"
        assert Path(exported_path).resolve() == expected_path.resolve()
        assert expected_path.exists()

def test_no_overwrite_by_default():
    pack = get_valid_pack()
    with tempfile.TemporaryDirectory() as tmp_dir:
        export_agent_task_pack(pack, export_root=tmp_dir)

        # Second export of same pack without overwrite must fail
        with pytest.raises(ExportError):
            export_agent_task_pack(pack, export_root=tmp_dir, overwrite=False)

def test_path_containment_enforced():
    pack = get_valid_pack()
    with tempfile.TemporaryDirectory() as tmp_dir:
        exported_path, sha = export_agent_task_pack(pack, export_root=tmp_dir)
        assert Path(exported_path).resolve().relative_to(Path(tmp_dir).resolve())

def test_exported_json_contains_matching_pack_sha256():
    pack = get_valid_pack()
    with tempfile.TemporaryDirectory() as tmp_dir:
        exported_path, sha = export_agent_task_pack(pack, export_root=tmp_dir)
        data = json.loads(Path(exported_path).read_text(encoding="utf-8"))
        assert data["pack_sha256"] == sha

def test_no_obsolete_report_fields():
    pack = get_valid_pack()
    obsolete_fields = ["status", "final_head", "files_touched", "commands_run", "tests_run"]
    for field in obsolete_fields:
        pack_bad = pack.copy()
        pack_bad["required_report_fields"] = [field]
        with pytest.raises(ValidationError):
            validate_agent_task_pack(pack_bad)

def test_forbidden_imports_and_usage():
    imp_file = Path(__file__).resolve().parents[1] / "src" / "aios_habit" / "agent_task_pack.py"
    content = imp_file.read_text(encoding="utf-8")

    forbidden = [
        "subprocess",
        "requests",
        "urllib",
        "socket",
        "httpx",
        "llm_client",
        "ai_provider_bridge",
        "ai_router",
        "notebook_qa",
        "ide_handoff_bridge"
    ]

    for term in forbidden:
        assert f"import {term}" not in content
        assert f"from {term}" not in content
        assert f"import aios_habit.{term}" not in content
