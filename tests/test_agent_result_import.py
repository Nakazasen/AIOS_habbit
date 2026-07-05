import json
import pytest
import tempfile
from pathlib import Path
from aios_habit.agent_result_import import (
    canonicalize_report,
    compute_report_sha256,
    attach_report_sha256,
    get_json_depth,
    is_safe_relative_path,
    load_agent_report,
    validate_agent_report,
    import_agent_report,
    load_agent_report_for_task_pack,
    VERIFIED_PASS,
    FAIL,
    REVIEW_REQUIRED,
    INVALID_REPORT
)

def get_valid_task_pack():
    return {
        "schema_version": "aios_agent_task_pack_v1",
        "task_id": "A17_TASK_EXPORT_001",
        "task_type": "implementation",
        "gate": "AI-GW-A17A",
        "agent_class": "implementation",
        "objective": "Test task objective",
        "repo": {
            "logical_repo_id": "AIOS_habbit_main",
            "repo_path_policy": "logical_relative",
            "expected_branch": "main",
            "expected_head": "f3a9b6c42d2aa40f2cd225f1684d70c06e9dc039"
        },
        "scope": {
            "allowed_files": ["src/aios_habit/agent_task_pack.py"],
            "forbidden_files": [".ai/**", "local_cases/**", "local_runs/**"],
            "allowed_commands": ["uv run pytest"],
            "forbidden_commands": ["git push", "curl", "rm -rf"],
            "required_tests": ["tests/test_agent_task_pack.py"]
        },
        "privacy": {
            "privacy_class": "internal",
            "destination": "local_owner_only",
            "purpose": "Testing",
            "consent_ref": "consent-123",
            "source_policy": "redact_raw_contents"
        },
        "roadmap_reference": {
            "phase": "Phase 4",
            "gate": "AI-GW-A17",
            "lock_status": "P1.0 LOCKED"
        },
        "pass_fail_rules": ["No forbidden files modified"],
        "rollback": {
            "allowed": True,
            "strategy": "manual_git_discard_by_owner",
            "description": "manual rollback"
        },
        "required_report_fields": [],
        "created_at": "2026-07-05T15:21:22Z",
        "pack_sha256": "df39e8cae0996ea3f573e62db7fbb4bf2089e0f6f2eb932394e5a2660583c53d2"
    }

def get_valid_report():
    rep = {
        "schema_version": "aios_agent_report_v1",
        "task_id": "A17_TASK_EXPORT_001",
        "task_pack_sha256": "df39e8cae0996ea3f573e62db7fbb4bf2089e0f6f2eb932394e5a2660583c53d2",
        "agent_class": "implementation",
        "model_tool_name": "Gemini-3.5-Pro-High-via-Antigravity",
        "declared_status": "PASS",
        "baseline": {
            "branch": "main",
            "head": "f3a9b6c42d2aa40f2cd225f1684d70c06e9dc039"
        },
        "final_state": {
            "branch": "main",
            "head": "68b0686b04dd611931cd58a005d9eb7946ddd84a",
            "worktree_clean": True,
            "staged_files": [],
            "untracked_files": [],
            "commit_hash": "68b0686b04dd611931cd58a005d9eb7946ddd84a",
            "push_status": "NOT_PUSHED"
        },
        "declared_files": {
            "changed_files": ["src/aios_habit/agent_task_pack.py"],
            "committed_files": ["src/aios_habit/agent_task_pack.py"],
            "staged_files": [],
            "untracked_files": []
        },
        "declared_commands": [
            {
                "command": "uv run pytest tests/test_agent_task_pack.py -q",
                "exit_code": 0,
                "result": "PASS"
            }
        ],
        "declared_tests": [
            {
                "command": "tests/test_agent_task_pack.py",
                "exit_code": 0,
                "result": "PASS"
            }
        ],
        "risks": ["No immediate security risks identified"],
        "blockers": [],
        "rollback": {
            "performed": False,
            "strategy_details": "N/A"
        },
        "reason_codes": [],
    }
    return attach_report_sha256(rep)

def get_valid_observed_evidence():
    return {
        "command_source": "OWNER_APPROVED_FIXED_CONFIG",
        "command_from_report": False,
        "report_command_ignored": True,
        "worktree_clean": True,
        "staged_files": [],
        "untracked_files": [],
        "changed_files": ["src/aios_habit/agent_task_pack.py"],
        "forbidden_files_touched": [],
        "required_tests_passed": True,
        "verifier_name": "local_verifier",
        "verifier_version": "1.0",
        "observation_time_utc": "2026-07-05T16:00:00Z",
        "owner_triggered": True,
        "owner_triggered_at_utc": "2026-07-05T15:59:00Z",
        "repo_branch": "main",
        "repo_head": "68b0686b04dd611931cd58a005d9eb7946ddd84a"
    }

# 1. Canonical report hash is deterministic
def test_canonical_hash_deterministic():
    r1 = get_valid_report()
    r2 = get_valid_report()
    assert compute_report_sha256(r1) == compute_report_sha256(r2)

# 2. report_sha256 excludes itself from hash
def test_hash_excludes_report_sha256():
    r1 = get_valid_report()
    h1 = compute_report_sha256(r1)

    r2 = r1.copy()
    r2["report_sha256"] = "different_hash"
    h2 = compute_report_sha256(r2)
    assert h1 == h2

# 3. Invalid report_sha256 => INVALID_REPORT
def test_invalid_report_sha256():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    rep["report_sha256"] = "a" * 64
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == INVALID_REPORT
    assert "INVALID_REPORT_HASH" in decision.reason_codes

# 4. Unsupported schema_version => INVALID_REPORT + SCHEMA_VERSION_UNSUPPORTED
def test_unsupported_schema_version():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    rep["schema_version"] = "unsupported_v2"
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == INVALID_REPORT
    assert "SCHEMA_VERSION_UNSUPPORTED" in decision.reason_codes

# 5. Missing required top-level fields => INVALID_REPORT
def test_missing_top_level_field():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    rep.pop("declared_status")
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == INVALID_REPORT
    assert "MISSING_REQUIRED_FIELD" in decision.reason_codes

# 6. Missing required nested fields => INVALID_REPORT
def test_missing_nested_fields():
    tp = get_valid_task_pack()

    # Missing baseline.branch
    rep1 = get_valid_report()
    rep1["baseline"].pop("branch")
    rep1 = attach_report_sha256(rep1)
    assert validate_agent_report(rep1, tp).verdict == INVALID_REPORT

    # Missing final_state.worktree_clean
    rep2 = get_valid_report()
    rep2["final_state"].pop("worktree_clean")
    rep2 = attach_report_sha256(rep2)
    assert validate_agent_report(rep2, tp).verdict == INVALID_REPORT

# 7. Obsolete fields status/final_head/files_touched/commands_run/tests_run rejected
def test_obsolete_fields_rejected():
    tp = get_valid_task_pack()
    obsolete = ["status", "final_head", "files_touched", "commands_run", "tests_run"]
    for field in obsolete:
        rep = get_valid_report()
        rep[field] = "dummy"
        rep = attach_report_sha256(rep)
        decision = validate_agent_report(rep, tp)
        assert decision.verdict == INVALID_REPORT
        assert "OBSOLETE_FIELD_PRESENT" in decision.reason_codes

# 8. Invalid task_id patterns rejected
def test_invalid_task_id_patterns():
    tp = get_valid_task_pack()
    bad_ids = ["", "A", "a" * 82, "task/id", "task\\id", "task..id", "C:task", "TASK\nID"]
    for bid in bad_ids:
        rep = get_valid_report()
        rep["task_id"] = bid
        rep = attach_report_sha256(rep)
        decision = validate_agent_report(rep, tp)
        assert decision.verdict == INVALID_REPORT
        assert "INVALID_TASK_ID" in decision.reason_codes

# 9. Task_id mismatch vs task pack rejected
def test_task_id_mismatch():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    rep["task_id"] = "A17_TASK_EXPORT_999"
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == INVALID_REPORT
    assert "TASK_ID_MISMATCH" in decision.reason_codes or "WRONG_TASK_PACK" in decision.reason_codes

# 10. Task_pack_sha256 mismatch rejected
def test_task_pack_sha256_mismatch():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    rep["task_pack_sha256"] = "a" * 64
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == INVALID_REPORT
    assert "PACK_HASH_MISMATCH" in decision.reason_codes or "WRONG_TASK_PACK" in decision.reason_codes

# 11. Baseline branch/head mismatch returns REVIEW_REQUIRED with BASELINE_MISMATCH
def test_baseline_mismatch():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    rep["baseline"]["branch"] = "develop"
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == REVIEW_REQUIRED
    assert "BASELINE_MISMATCH" in decision.reason_codes

# 12. Changed file outside allowed_files returns FAIL with FORBIDDEN_FILE_TOUCHED
def test_changed_file_outside_scope():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    rep["declared_files"]["changed_files"] = ["src/aios_habit/unauthorized.py"]
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == FAIL
    assert "FORBIDDEN_FILE_TOUCHED" in decision.reason_codes

# 13. Forbidden paths (.ai/local_cases/local_runs/traversal/absolute/drive/UNC) rejected
def test_unsafe_paths_rejected():
    tp = get_valid_task_pack()
    unsafe_paths = [
        "../traversal.py",
        "C:\\absolute\\path.py",
        "\\\\UNC\\share\\file.py",
        "local_cases/case_001.json",
        ".ai/config.json",
        "local_runs/outbox/task.json"
    ]
    for up in unsafe_paths:
        rep = get_valid_report()
        rep["declared_files"]["changed_files"] = [up]
        rep = attach_report_sha256(rep)
        decision = validate_agent_report(rep, tp)
        assert decision.verdict == INVALID_REPORT
        assert "UNSAFE_PATH" in decision.reason_codes

# 14. Staged/untracked non-empty with declared PASS returns REVIEW_REQUIRED
def test_dirty_worktree_staged_untracked():
    tp = get_valid_task_pack()

    # staged files present
    rep1 = get_valid_report()
    rep1["declared_files"]["staged_files"] = ["src/aios_habit/agent_task_pack.py"]
    rep1 = attach_report_sha256(rep1)
    decision1 = validate_agent_report(rep1, tp)
    assert decision1.verdict == REVIEW_REQUIRED
    assert "STAGED_FILES_PRESENT" in decision1.reason_codes

    # untracked files present
    rep2 = get_valid_report()
    rep2["declared_files"]["untracked_files"] = ["src/aios_habit/scratch.py"]
    rep2 = attach_report_sha256(rep2)
    decision2 = validate_agent_report(rep2, tp)
    assert decision2.verdict == REVIEW_REQUIRED
    assert "UNTRACKED_FILES_PRESENT" in decision2.reason_codes

# 15. Required test missing returns REVIEW_REQUIRED
def test_missing_required_test():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    rep["declared_tests"] = [] # empty, missing the required test
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == REVIEW_REQUIRED
    assert "MISSING_REQUIRED_TEST" in decision.reason_codes

# 16. Declared test PASS missing exit_code returns REVIEW_REQUIRED with TEST_EXIT_CODE_MISSING
def test_test_pass_missing_exit_code():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    rep["declared_tests"] = [
        {
            "command": "tests/test_agent_task_pack.py",
            "result": "PASS"
            # exit_code missing
        }
    ]
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == REVIEW_REQUIRED
    assert "TEST_EXIT_CODE_MISSING" in decision.reason_codes

# 17. Declared PASS without observed evidence returns REVIEW_REQUIRED and not VERIFIED_PASS
def test_declared_pass_without_observed_evidence():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    decision = validate_agent_report(rep, tp, observed_evidence=None)
    assert decision.verdict == REVIEW_REQUIRED
    assert "DECLARED_PASS_WITHOUT_OBSERVED_EVIDENCE" in decision.reason_codes

# 18. Valid FAIL report remains FAIL
def test_valid_fail_report():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    rep["declared_status"] = "FAIL"
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == FAIL

# 19. Valid REVIEW_REQUIRED report remains REVIEW_REQUIRED
def test_valid_review_required_report():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    rep["declared_status"] = "REVIEW_REQUIRED"
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == REVIEW_REQUIRED

# 20. Malformed JSON file returns INVALID_REPORT
def test_load_malformed_json():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"{invalid_json}")
        f_path = Path(f.name)
    try:
        tp_file = Path("tp.json") # dummy
        decision = load_agent_report_for_task_pack(f_path, tp_file)
        assert decision.verdict == INVALID_REPORT
        assert "MALFORMED_JSON" in decision.reason_codes
    finally:
        f_path.unlink()

# 21. Oversized report returns INVALID_REPORT + REPORT_TOO_LARGE
def test_oversized_report():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"{" + b'"a": "b",' * 120000 + b'"c": "d"}') # > 1.1 MiB
        f_path = Path(f.name)
    try:
        decision = load_agent_report_for_task_pack(f_path, Path("dummy.json"))
        assert decision.verdict == INVALID_REPORT
        assert "REPORT_TOO_LARGE" in decision.reason_codes
    finally:
        f_path.unlink()

# 22. UTF-8 BOM file returns INVALID_REPORT + UTF8_BOM_REJECTED
def test_utf8_bom_rejected():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"\xef\xbb\xbf{}")
        f_path = Path(f.name)
    try:
        decision = load_agent_report_for_task_pack(f_path, Path("dummy.json"))
        assert decision.verdict == INVALID_REPORT
        assert "UTF8_BOM_REJECTED" in decision.reason_codes
    finally:
        f_path.unlink()

# 23. Too-deep JSON returns INVALID_REPORT + REPORT_TOO_DEEP
def test_too_deep_json():
    # Construct a nested json structure of depth 25
    val = {}
    for _ in range(25):
        val = {"child": val}
    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as f:
        json.dump(val, f)
        f_path = Path(f.name)
    try:
        decision = load_agent_report_for_task_pack(f_path, Path("dummy.json"))
        assert decision.verdict == INVALID_REPORT
        assert "REPORT_TOO_DEEP" in decision.reason_codes
    finally:
        f_path.unlink()

# 24. Secret/token/private-key pattern in unsafe field is rejected
def test_secret_pattern_detected():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    rep["risks"] = ["Look at my sk-1234567890abcdef api key."]
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == INVALID_REPORT
    assert "SECRET_PATTERN_DETECTED" in decision.reason_codes

# 25. Markdown/prose cannot produce VERIFIED_PASS
def test_markdown_cannot_produce_pass():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    # Even if we put Markdown or PASS descriptions, verdict remains REVIEW_REQUIRED unless observed evidence is present
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == REVIEW_REQUIRED

# 26. observed_evidence can produce VERIFIED_PASS
def test_observed_evidence_verified_pass():
    tp = get_valid_task_pack()
    rep = get_valid_report()
    oe = get_valid_observed_evidence()
    decision = validate_agent_report(rep, tp, observed_evidence=oe)
    assert decision.verdict == VERIFIED_PASS

# 27. observed_evidence missing any required property downgrades to REVIEW_REQUIRED
def test_observed_evidence_downgrades():
    tp = get_valid_task_pack()
    rep = get_valid_report()

    # Mismatch command source
    oe = get_valid_observed_evidence()
    oe["command_source"] = "REPORT_COMMAND"
    decision = validate_agent_report(rep, tp, observed_evidence=oe)
    assert decision.verdict == REVIEW_REQUIRED

    # Untracked files present in local verification environment
    oe2 = get_valid_observed_evidence()
    oe2["untracked_files"] = ["unauthorized.py"]
    decision2 = validate_agent_report(rep, tp, observed_evidence=oe2)
    assert decision2.verdict == REVIEW_REQUIRED

# 28. Source scan confirms no forbidden imports or dangerous calls
def test_forbidden_imports():
    import_file = Path(__file__).resolve().parents[1] / "src" / "aios_habit" / "agent_result_import.py"
    content = import_file.read_text(encoding="utf-8")

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

# 29. Control characters in paths rejected
def test_paths_with_control_characters():
    tp = get_valid_task_pack()

    # Path with newline
    rep = get_valid_report()
    rep["declared_files"]["changed_files"] = ["src/aios_habit/agent_task_pack\n.py"]
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == INVALID_REPORT
    assert "UNSAFE_PATH" in decision.reason_codes

    # Path with tab
    rep = get_valid_report()
    rep["declared_files"]["changed_files"] = ["src/aios_habit/agent_task_pack\t.py"]
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == INVALID_REPORT
    assert "UNSAFE_PATH" in decision.reason_codes

    # Path with NUL character
    rep = get_valid_report()
    rep["declared_files"]["changed_files"] = ["src/aios_habit/agent_task_pack\x00.py"]
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == INVALID_REPORT
    assert "UNSAFE_PATH" in decision.reason_codes

# 30. Unsafe values/secrets/absolute paths are not echoed in summaries
def test_summaries_privacy():
    tp = get_valid_task_pack()

    # 30a. Unsafe path should not be echoed
    rep = get_valid_report()
    unsafe_path = "C:\\Users\\Admin\\secret.txt"
    rep["declared_files"]["changed_files"] = [unsafe_path]
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    assert decision.verdict == INVALID_REPORT
    assert "UNSAFE_PATH" in decision.reason_codes
    assert "C:\\Users" not in decision.safe_summary
    assert "C:\\Users" not in decision.evidence_summary
    assert "secret.txt" not in decision.safe_summary
    assert "secret.txt" not in decision.evidence_summary

    # 30b. Secret pattern should not be echoed
    rep2 = get_valid_report()
    secret_str = "sk-1234567890abcdef"
    rep2["risks"] = [f"Look at my {secret_str} api key."]
    rep2 = attach_report_sha256(rep2)
    decision2 = validate_agent_report(rep2, tp)
    assert decision2.verdict == INVALID_REPORT
    assert "SECRET_PATTERN_DETECTED" in decision2.reason_codes
    assert secret_str not in decision2.safe_summary
    assert secret_str not in decision2.evidence_summary

    # 30c. Private key pattern should not be echoed
    rep3 = get_valid_report()
    pkey_str = "-----BEGIN PRIVATE KEY-----"
    rep3["risks"] = [f"Private info: {pkey_str}"]
    rep3 = attach_report_sha256(rep3)
    decision3 = validate_agent_report(rep3, tp)
    assert decision3.verdict == INVALID_REPORT
    assert "SECRET_PATTERN_DETECTED" in decision3.reason_codes
    assert "-----BEGIN" not in decision3.safe_summary
    assert "-----BEGIN" not in decision3.evidence_summary

# 31. Non-object JSON roots structurally rejected without crash
def test_non_object_json_roots():
    tp = get_valid_task_pack()

    # Direct list validate
    decision = validate_agent_report([], tp)
    assert decision.verdict == INVALID_REPORT
    assert "INVALID_FIELD_TYPE" in decision.reason_codes

    # Direct string validate
    decision = validate_agent_report("string_report", tp)
    assert decision.verdict == INVALID_REPORT
    assert "INVALID_FIELD_TYPE" in decision.reason_codes

    # Direct None/null validate
    decision = validate_agent_report(None, tp)
    assert decision.verdict == INVALID_REPORT
    assert "INVALID_FIELD_TYPE" in decision.reason_codes

    # File loading JSON root list
    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as f:
        json.dump([1, 2, 3], f)
        f_path = Path(f.name)
    try:
        decision = load_agent_report_for_task_pack(f_path, Path("dummy.json"))
        assert decision.verdict == INVALID_REPORT
        assert "INVALID_FIELD_TYPE" in decision.reason_codes
    finally:
        f_path.unlink()

    # File loading JSON root string
    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as f:
        json.dump("just a string", f)
        f_path = Path(f.name)
    try:
        decision = load_agent_report_for_task_pack(f_path, Path("dummy.json"))
        assert decision.verdict == INVALID_REPORT
        assert "INVALID_FIELD_TYPE" in decision.reason_codes
    finally:
        f_path.unlink()

# 32. agent_class match only if available
def test_agent_class_match_only_if_available():
    tp = get_valid_task_pack()
    tp.pop("agent_class", None) # agent_class not available in task pack
    rep = get_valid_report()
    rep["agent_class"] = "implementation" # report agent class can be anything
    rep = attach_report_sha256(rep)
    decision = validate_agent_report(rep, tp)
    # Baseline matched, no WRONG_TASK_PACK since agent_class is not in task_pack
    assert "WRONG_TASK_PACK" not in decision.reason_codes

    # But if agent_class is in task pack and mismatches
    tp["agent_class"] = "testing"
    decision = validate_agent_report(rep, tp)
    assert "WRONG_TASK_PACK" in decision.reason_codes

# 33. Comprehensive observed evidence downgrade parameterized test
@pytest.mark.parametrize(
    "prop_name, wrong_value",
    [
        ("command_source", "REPORT_COMMAND"),
        ("command_source", None),
        ("command_from_report", True),
        ("report_command_ignored", False),
        ("worktree_clean", False),
        ("staged_files", ["unauthorized.py"]),
        ("untracked_files", ["unauthorized.py"]),
        ("forbidden_files_touched", ["src/aios_habit/agent_task_pack.py"]),
        ("required_tests_passed", False),
        ("changed_files", ["src/aios_habit/unauthorized.py"]),
    ]
)
def test_observed_evidence_downgrades_exhaustive(prop_name, wrong_value):
    tp = get_valid_task_pack()
    rep = get_valid_report()
    oe = get_valid_observed_evidence()

    # Apply wrong value
    oe[prop_name] = wrong_value

    decision = validate_agent_report(rep, tp, observed_evidence=oe)
    assert decision.verdict == REVIEW_REQUIRED
