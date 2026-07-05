"""
Module for Agent Result Import MVP (Gate AI-GW-A17B).
Provides validator and importer for agent reports under the aios_agent_report_v1 schema.
"""

import json
import hashlib
import fnmatch
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from aios_habit.agent_task_pack import (
    is_absolute_or_system_path,
    contains_path_traversal,
    is_forbidden_metadata_path,
    check_sensitive_content,
    ValidationError,
    TASK_ID_REGEX
)

# --- Verdict Constants ---
VERIFIED_PASS = "VERIFIED_PASS"
FAIL = "FAIL"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
INVALID_REPORT = "INVALID_REPORT"

# --- ImportDecision Dataclass ---
@dataclass(frozen=True)
class ImportDecision:
    verdict: str
    reason_codes: List[str]
    task_id: Optional[str]
    task_pack_sha256: Optional[str]
    report_sha256: Optional[str]
    declared_status: Optional[str]
    safe_summary: str
    evidence_summary: str

# --- Schema Constraints ---
REQUIRED_REPORT_FIELDS = [
    "schema_version",
    "task_id",
    "task_pack_sha256",
    "agent_class",
    "model_tool_name",
    "declared_status",
    "baseline",
    "final_state",
    "declared_files",
    "declared_commands",
    "declared_tests",
    "risks",
    "blockers",
    "rollback",
    "reason_codes",
    "report_sha256",
]

OBSOLETE_REPORT_FIELDS = {
    "status",
    "final_head",
    "files_touched",
    "commands_run",
    "tests_run",
}

# --- Canonicalization & Hash Helpers ---

def canonicalize_report(report_dict: Dict[str, Any]) -> str:
    """
    Serializes a report dictionary to a canonical JSON string.
    Keys are sorted, no extra whitespaces, no NaN/Infinity, UTF-8.
    """
    return json.dumps(
        report_dict,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False
    )

def compute_report_sha256(report_dict: Dict[str, Any]) -> str:
    """
    Computes the SHA-256 integrity hash of the report payload.
    Excludes the 'report_sha256' field itself.
    """
    temp_dict = report_dict.copy()
    temp_dict.pop("report_sha256", None)
    canonical_str = canonicalize_report(temp_dict)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

def attach_report_sha256(report_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attaches the computed report_sha256 to a copy of the report dictionary.
    """
    copy_dict = report_dict.copy()
    copy_dict["report_sha256"] = compute_report_sha256(copy_dict)
    return copy_dict

# --- JSON Depth Checker ---

def get_json_depth(val: Any) -> int:
    """
    Recursively computes the depth of a nested JSON object/list.
    """
    if isinstance(val, dict):
        if not val:
            return 1
        return 1 + max(get_json_depth(v) for v in val.values())
    elif isinstance(val, list):
        if not val:
            return 1
        return 1 + max(get_json_depth(v) for v in val)
    else:
        return 1

# --- Safe Path Checker ---

def is_safe_relative_path(path_str: str) -> bool:
    """
    Checks if path_str is a safe relative path, free of traversal or system roots.
    """
    if not isinstance(path_str, str):
        return False
    if any(ord(c) < 32 for c in path_str):
        return False
    if is_absolute_or_system_path(path_str):
        return False
    if contains_path_traversal(path_str):
        return False
    if is_forbidden_metadata_path(path_str):
        return False
    # Avoid local_runs, local_cases, .ai references explicitly
    normalized = path_str.replace("\\", "/").lower()
    parts = normalized.split("/")
    for part in parts:
        if part in {".ai", "local_cases", "local_runs", "task.md", "walkthrough.md", "implementation_plan.md"}:
            return False
    return True

# --- Sensitive Content Wrapper ---

def scan_text_safe(text: str) -> Optional[str]:
    """
    Runs sensitive content scanning on text.
    Returns a reason code if violation is found, otherwise None.
    """
    if not text or not isinstance(text, str):
        return None
    try:
        check_sensitive_content(text)
    except ValidationError:
        return "SECRET_PATTERN_DETECTED"
    return None

# --- Main Importer API ---

def load_agent_report(path: Path) -> Dict[str, Any]:
    """
    Loads agent report from a path with strict file-level security constraints:
    - Max size 1 MiB.
    - Strict UTF-8 without BOM.
    - Max JSON depth 20.
    """
    resolved_path = Path(path).resolve()
    if not resolved_path.is_file():
        raise FileNotFoundError(f"Report file not found: {path}")

    # Check file size
    size = resolved_path.stat().st_size
    if size > 1048576: # 1 MiB
        raise ValueError("REPORT_TOO_LARGE")

    raw_bytes = resolved_path.read_bytes()

    # Reject UTF-8 BOM
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF8_BOM_REJECTED")

    try:
        content_str = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise ValueError("MALFORMED_JSON")

    try:
        report_data = json.loads(content_str)
    except json.JSONDecodeError:
        raise ValueError("MALFORMED_JSON")

    if not isinstance(report_data, dict):
        raise ValueError("INVALID_FIELD_TYPE")

    # Depth check
    if get_json_depth(report_data) > 20:
        raise ValueError("REPORT_TOO_DEEP")

    return report_data

def validate_agent_report(
    report: Dict[str, Any],
    task_pack: Dict[str, Any],
    observed_evidence: Optional[Dict[str, Any]] = None
) -> ImportDecision:
    """
    Validates report against schema and matching task pack.
    Returns ImportDecision object.
    """
    if not isinstance(report, dict):
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=["INVALID_FIELD_TYPE"],
            task_id=None,
            task_pack_sha256=None,
            report_sha256=None,
            declared_status=None,
            safe_summary="Báo cáo không phải là một đối tượng JSON.",
            evidence_summary="Dữ liệu báo cáo đầu vào không hợp lệ (không phải dict)."
        )

    reason_codes = []

    # 1. Schema check
    schema_version = report.get("schema_version")
    if schema_version != "aios_agent_report_v1":
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=["SCHEMA_VERSION_UNSUPPORTED"],
            task_id=report.get("task_id") if isinstance(report.get("task_id"), str) else None,
            task_pack_sha256=report.get("task_pack_sha256") if isinstance(report.get("task_pack_sha256"), str) else None,
            report_sha256=None,
            declared_status=report.get("declared_status") if isinstance(report.get("declared_status"), str) else None,
            safe_summary="Không hỗ trợ schema version.",
            evidence_summary="Lược đồ không hợp lệ."
        )

    # 2. Required fields check
    for field in REQUIRED_REPORT_FIELDS:
        if field not in report:
            reason_codes.append("MISSING_REQUIRED_FIELD")

    # 3. Obsolete fields check
    for field in OBSOLETE_REPORT_FIELDS:
        if field in report:
            reason_codes.append("OBSOLETE_FIELD_PRESENT")

    if reason_codes:
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=list(set(reason_codes)),
            task_id=report.get("task_id") if isinstance(report.get("task_id"), str) else None,
            task_pack_sha256=report.get("task_pack_sha256") if isinstance(report.get("task_pack_sha256"), str) else None,
            report_sha256=None,
            declared_status=report.get("declared_status") if isinstance(report.get("declared_status"), str) else None,
            safe_summary="Thiếu trường bắt buộc hoặc chứa trường lỗi thời.",
            evidence_summary="Thiếu trường bắt buộc hoặc chứa trường lỗi thời trong lược đồ."
        )

    # 4. Field types check
    type_checks = {
        "task_id": str,
        "task_pack_sha256": str,
        "agent_class": str,
        "model_tool_name": str,
        "declared_status": str,
        "baseline": dict,
        "final_state": dict,
        "declared_files": dict,
        "declared_commands": list,
        "declared_tests": list,
        "risks": list,
        "blockers": list,
        "rollback": dict,
        "reason_codes": list,
        "report_sha256": str,
    }
    for field, expected_type in type_checks.items():
        if not isinstance(report[field], expected_type):
            reason_codes.append("INVALID_FIELD_TYPE")

    if reason_codes:
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=list(set(reason_codes)),
            task_id=None,
            task_pack_sha256=None,
            report_sha256=None,
            declared_status=None,
            safe_summary="Kiểu dữ liệu trường không hợp lệ.",
            evidence_summary="Lỗi kiểm tra kiểu dữ liệu trường."
        )

    task_id = report["task_id"]
    task_pack_sha256 = report["task_pack_sha256"]
    declared_status = report["declared_status"]
    report_sha256 = report["report_sha256"]

    # 5. Task ID Regex Check
    # Match ^[A-Z0-9][A-Z0-9_-]{2,80}$ and verify no traversal/drive letters
    if not TASK_ID_REGEX.match(task_id) or len(task_id) < 3 or len(task_id) > 81 or "/" in task_id or "\\" in task_id or ".." in task_id or ":" in task_id:
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=["INVALID_TASK_ID"],
            task_id=None,
            task_pack_sha256=task_pack_sha256,
            report_sha256=report_sha256,
            declared_status=declared_status,
            safe_summary="Task ID định dạng không an toàn.",
            evidence_summary="Task ID vi phạm các quy tắc đặt tên an toàn."
        )

    # 6. Report Hash Check
    computed_hash = compute_report_sha256(report)
    if report_sha256 != computed_hash:
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=["INVALID_REPORT_HASH"],
            task_id=task_id,
            task_pack_sha256=task_pack_sha256,
            report_sha256=report_sha256,
            declared_status=declared_status,
            safe_summary="Hash báo cáo không hợp lệ.",
            evidence_summary="Sai biệt report_sha256 thực tế so với khai báo."
        )

    # 7. Task Pack Matching Checks
    pack_sha = task_pack.get("pack_sha256")
    pack_task_id = task_pack.get("task_id")
    pack_agent_class = task_pack.get("agent_class")

    if task_id != pack_task_id:
        reason_codes.append("TASK_ID_MISMATCH")
        reason_codes.append("WRONG_TASK_PACK")
    if task_pack_sha256 != pack_sha:
        reason_codes.append("PACK_HASH_MISMATCH")
        reason_codes.append("WRONG_TASK_PACK")
    if pack_agent_class and report["agent_class"] != pack_agent_class:
        reason_codes.append("WRONG_TASK_PACK")

    if "WRONG_TASK_PACK" in reason_codes or "TASK_ID_MISMATCH" in reason_codes or "PACK_HASH_MISMATCH" in reason_codes:
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=list(set(reason_codes)),
            task_id=task_id,
            task_pack_sha256=task_pack_sha256,
            report_sha256=report_sha256,
            declared_status=declared_status,
            safe_summary="Báo cáo không khớp với Task Pack hiện tại.",
            evidence_summary="Sai biệt task_id hoặc task_pack_sha256 hoặc agent_class."
        )

    # 8. Baseline Branch/HEAD Match check
    expected_branch = task_pack.get("repo", {}).get("expected_branch")
    expected_head = task_pack.get("repo", {}).get("expected_head")

    report_baseline = report["baseline"]
    rep_branch = report_baseline.get("branch")
    rep_head = report_baseline.get("head")

    if not isinstance(rep_branch, str) or not isinstance(rep_head, str):
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=["MISSING_REQUIRED_FIELD"],
            task_id=task_id,
            task_pack_sha256=task_pack_sha256,
            report_sha256=report_sha256,
            declared_status=declared_status,
            safe_summary="Baseline thiếu trường branch hoặc head.",
            evidence_summary="Trường baseline không đầy đủ cấu trúc."
        )

    if rep_branch != expected_branch or rep_head != expected_head:
        return ImportDecision(
            verdict=REVIEW_REQUIRED,
            reason_codes=["BASELINE_MISMATCH"],
            task_id=task_id,
            task_pack_sha256=task_pack_sha256,
            report_sha256=report_sha256,
            declared_status=declared_status,
            safe_summary="Baseline lệch so với Task Pack.",
            evidence_summary="Baseline branch hoặc head lệch so với yêu cầu trong Task Pack."
        )

    # 9. Verify final_state and declared_files nested structure
    final_state = report["final_state"]
    declared_files = report["declared_files"]

    fs_branch = final_state.get("branch")
    fs_head = final_state.get("head")
    fs_clean = final_state.get("worktree_clean")
    fs_staged = final_state.get("staged_files") if "staged_files" in final_state else final_state.get("staged")
    fs_untracked = final_state.get("untracked_files") if "untracked_files" in final_state else final_state.get("untracked")

    if (not isinstance(fs_branch, str) or not isinstance(fs_head, str) or
        not isinstance(fs_clean, bool) or not isinstance(fs_staged, list) or not isinstance(fs_untracked, list)):
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=["MISSING_REQUIRED_FIELD"],
            task_id=task_id,
            task_pack_sha256=task_pack_sha256,
            report_sha256=report_sha256,
            declared_status=declared_status,
            safe_summary="final_state cấu trúc thiếu trường.",
            evidence_summary="Cấu trúc trường final_state không hợp lệ."
        )

    df_changed = declared_files.get("changed_files") if "changed_files" in declared_files else declared_files.get("changed")
    df_committed = declared_files.get("committed_files") if "committed_files" in declared_files else declared_files.get("committed")
    df_staged = declared_files.get("staged_files") if "staged_files" in declared_files else declared_files.get("staged")
    df_untracked = declared_files.get("untracked_files") if "untracked_files" in declared_files else declared_files.get("untracked")

    if (not isinstance(df_changed, list) or not isinstance(df_committed, list) or
        not isinstance(df_staged, list) or not isinstance(df_untracked, list)):
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=["MISSING_REQUIRED_FIELD"],
            task_id=task_id,
            task_pack_sha256=task_pack_sha256,
            report_sha256=report_sha256,
            declared_status=declared_status,
            safe_summary="declared_files cấu trúc thiếu trường.",
            evidence_summary="Cấu trúc trường declared_files không hợp lệ."
        )

    # 10. Path safety checks (relative paths, no traversal, etc.)
    all_declared_paths = []
    all_declared_paths.extend(fs_staged)
    all_declared_paths.extend(fs_untracked)
    all_declared_paths.extend(df_changed)
    all_declared_paths.extend(df_committed)
    all_declared_paths.extend(df_staged)
    all_declared_paths.extend(df_untracked)

    for p in all_declared_paths:
        if not is_safe_relative_path(p):
            return ImportDecision(
                verdict=INVALID_REPORT,
                reason_codes=["UNSAFE_PATH"],
                task_id=task_id,
                task_pack_sha256=task_pack_sha256,
                report_sha256=report_sha256,
                declared_status=declared_status,
                safe_summary="Phát hiện đường dẫn không an toàn.",
                evidence_summary="Khai báo chứa đường dẫn không hợp lệ hoặc vi phạm quy tắc an toàn."
            )

    # 11. Sensitive data check in unsafe text fields
    # Fields to scan: model_tool_name, risks, blockers, reason_codes
    text_fields_to_scan = [report["model_tool_name"]]
    for r in report["risks"]:
        if isinstance(r, str):
            text_fields_to_scan.append(r)
    for b in report["blockers"]:
        if isinstance(b, str):
            text_fields_to_scan.append(b)
    for rc in report["reason_codes"]:
        if isinstance(rc, str):
            text_fields_to_scan.append(rc)

    for txt in text_fields_to_scan:
        err_code = scan_text_safe(txt)
        if err_code:
            return ImportDecision(
                verdict=INVALID_REPORT,
                reason_codes=[err_code],
                task_id=task_id,
                task_pack_sha256=task_pack_sha256,
                report_sha256=report_sha256,
                declared_status=declared_status,
                safe_summary="Phát hiện dữ liệu nhạy cảm hoặc rò rỉ thông tin.",
                evidence_summary="Scan phát hiện API key, absolute path hoặc thông tin bảo mật trong chuỗi."
            )

    # 12. Check allowed scope files
    allowed_files_list = task_pack.get("scope", {}).get("allowed_files", [])
    forbidden_files_patterns = task_pack.get("scope", {}).get("forbidden_files", [])

    # Compile forbidden files patterns
    # We check if any changed/committed file touches a forbidden pattern or is outside allowed scope
    touched_files = set(df_changed + df_committed)

    # Allow lists check
    for f in touched_files:
        # Check allowed list
        if f not in allowed_files_list:
            return ImportDecision(
                verdict=FAIL,
                reason_codes=["FORBIDDEN_FILE_TOUCHED"],
                task_id=task_id,
                task_pack_sha256=task_pack_sha256,
                report_sha256=report_sha256,
                declared_status=declared_status,
                safe_summary="Sửa đổi tệp ngoài danh sách cho phép.",
                evidence_summary="Phát hiện sửa đổi tệp không thuộc danh sách cho phép trong Task Pack."
            )
        # Check forbidden list (glob matching)
        for pattern in forbidden_files_patterns:
            if fnmatch.fnmatch(f, pattern):
                return ImportDecision(
                    verdict=FAIL,
                    reason_codes=["FORBIDDEN_FILE_TOUCHED"],
                    task_id=task_id,
                    task_pack_sha256=task_pack_sha256,
                    report_sha256=report_sha256,
                    declared_status=declared_status,
                    safe_summary="Sửa đổi tệp nằm trong danh sách cấm.",
                    evidence_summary="Phát hiện sửa đổi tệp thuộc danh sách cấm của Task Pack."
                )

    # 13. Command execution check: reject forbidden commands in declared commands
    # e.g., git push, curl, rm -rf
    forbidden_commands = task_pack.get("scope", {}).get("forbidden_commands", [])
    for cmd_obj in report["declared_commands"]:
        if not isinstance(cmd_obj, dict) or "command" not in cmd_obj:
            return ImportDecision(
                verdict=INVALID_REPORT,
                reason_codes=["MISSING_REQUIRED_FIELD"],
                task_id=task_id,
                task_pack_sha256=task_pack_sha256,
                report_sha256=report_sha256,
                declared_status=declared_status,
                safe_summary="Trường declared_commands không đúng cấu trúc.",
                evidence_summary="Lệnh tự khai thiếu thuộc tính command."
            )
        cmd_str = cmd_obj["command"]
        if not isinstance(cmd_str, str):
            return ImportDecision(
                verdict=INVALID_REPORT,
                reason_codes=["INVALID_FIELD_TYPE"],
                task_id=task_id,
                task_pack_sha256=task_pack_sha256,
                report_sha256=report_sha256,
                declared_status=declared_status,
                safe_summary="Lệnh tự khai có kiểu không phải chuỗi.",
                evidence_summary="Lệnh tự khai có kiểu không phải string."
            )
        for f_cmd in forbidden_commands:
            if f_cmd in cmd_str:
                return ImportDecision(
                    verdict=FAIL,
                    reason_codes=["COMMAND_EXECUTION_FORBIDDEN"],
                    task_id=task_id,
                    task_pack_sha256=task_pack_sha256,
                    report_sha256=report_sha256,
                    declared_status=declared_status,
                    safe_summary="Lệnh tự khai chứa nội dung cấm thực thi.",
                    evidence_summary="Phát hiện lệnh tự khai chứa từ khóa hoặc lệnh cấm thực thi."
                )

    # 14. Required tests check
    required_tests = task_pack.get("scope", {}).get("required_tests", [])
    declared_test_names = []
    declared_test_results = {}
    declared_test_exit_codes = {}

    for t_obj in report["declared_tests"]:
        if not isinstance(t_obj, dict):
            return ImportDecision(
                verdict=INVALID_REPORT,
                reason_codes=["INVALID_FIELD_TYPE"],
                task_id=task_id,
                task_pack_sha256=task_pack_sha256,
                report_sha256=report_sha256,
                declared_status=declared_status,
                safe_summary="Test tự khai không đúng cấu trúc dict.",
                evidence_summary="Phần tử declared_tests không phải dict."
            )
        t_name = t_obj.get("command") or t_obj.get("name")
        if not isinstance(t_name, str):
            return ImportDecision(
                verdict=INVALID_REPORT,
                reason_codes=["MISSING_REQUIRED_FIELD"],
                task_id=task_id,
                task_pack_sha256=task_pack_sha256,
                report_sha256=report_sha256,
                declared_status=declared_status,
                safe_summary="Test tự khai thiếu tên hoặc lệnh.",
                evidence_summary="Test tự khai thiếu trường định danh (command hoặc name)."
            )
        declared_test_names.append(t_name)

        # Capture result & exit code
        t_res = t_obj.get("result") or t_obj.get("outcome")
        t_code = t_obj.get("exit_code")

        declared_test_results[t_name] = t_res
        declared_test_exit_codes[t_name] = t_code

    for req_t in required_tests:
        # Check if matched by exact or substring
        matched = False
        for dt_name in declared_test_names:
            if req_t == dt_name or req_t in dt_name:
                matched = True
                # Validate exit code if result is PASS
                t_res = declared_test_results[dt_name]
                t_code = declared_test_exit_codes[dt_name]
                if isinstance(t_res, str) and t_res.upper() == "PASS":
                    if t_code is None:
                        reason_codes.append("TEST_EXIT_CODE_MISSING")
                    elif isinstance(t_code, int) and t_code != 0:
                        reason_codes.append("TEST_EXIT_CODE_MISSING") # or another suitable code
                break
        if not matched:
            reason_codes.append("MISSING_REQUIRED_TEST")

    if "MISSING_REQUIRED_TEST" in reason_codes:
        return ImportDecision(
            verdict=REVIEW_REQUIRED,
            reason_codes=list(set(reason_codes)),
            task_id=task_id,
            task_pack_sha256=task_pack_sha256,
            report_sha256=report_sha256,
            declared_status=declared_status,
            safe_summary="Thiếu kết quả kiểm thử bắt buộc.",
            evidence_summary="Thiếu kết quả của một hoặc nhiều kiểm thử bắt buộc theo yêu cầu."
        )

    # 15. Check dirty state for pass-like reports
    if declared_status == "PASS":
        # Staged or untracked file presence
        has_staged = len(fs_staged) > 0 or len(df_staged) > 0
        has_untracked = len(fs_untracked) > 0 or len(df_untracked) > 0

        if has_staged:
            reason_codes.append("STAGED_FILES_PRESENT")
        if has_untracked:
            reason_codes.append("UNTRACKED_FILES_PRESENT")
        if not fs_clean:
            reason_codes.append("RUNTIME_DIRTY")

    # 16. Handing observed evidence verification
    if declared_status == "PASS":
        if not observed_evidence:
            reason_codes.append("DECLARED_PASS_WITHOUT_OBSERVED_EVIDENCE")
            reason_codes.append("OBSERVED_EVIDENCE_REQUIRED")
            return ImportDecision(
                verdict=REVIEW_REQUIRED,
                reason_codes=list(set(reason_codes)),
                task_id=task_id,
                task_pack_sha256=task_pack_sha256,
                report_sha256=report_sha256,
                declared_status=declared_status,
                safe_summary="Cần chủ sở hữu kiểm chứng thực tế.",
                evidence_summary="Báo cáo khai PASS nhưng thiếu observed evidence từ owner verifier độc lập."
            )
        else:
            # Validate observed evidence structure & safety rules
            oe_src = observed_evidence.get("command_source")
            oe_from_rep = observed_evidence.get("command_from_report")
            oe_ignored = observed_evidence.get("report_command_ignored")
            oe_clean = observed_evidence.get("worktree_clean")
            oe_staged = observed_evidence.get("staged_files")
            oe_untracked = observed_evidence.get("untracked_files")
            oe_changed = observed_evidence.get("changed_files", [])
            oe_forbidden_touched = observed_evidence.get("forbidden_files_touched", [])
            oe_tests_passed = observed_evidence.get("required_tests_passed")

            oe_valid = (
                oe_src == "OWNER_APPROVED_FIXED_CONFIG" and
                oe_from_rep is False and
                oe_ignored is True and
                oe_clean is True and
                isinstance(oe_staged, list) and len(oe_staged) == 0 and
                isinstance(oe_untracked, list) and len(oe_untracked) == 0 and
                isinstance(oe_changed, list) and
                isinstance(oe_forbidden_touched, list) and len(oe_forbidden_touched) == 0 and
                oe_tests_passed is True
            )

            # Check that all changed files are in allowed list
            if oe_valid and isinstance(oe_changed, list):
                for f in oe_changed:
                    if f not in allowed_files_list:
                        oe_valid = False
                        reason_codes.append("FORBIDDEN_FILE_TOUCHED")
                        break

            if oe_valid:
                # If there are any pending soft reason codes like test exit code missing or staged files in report, we still return REVIEW_REQUIRED
                clean_reason_codes = [rc for rc in reason_codes if rc not in {"DECLARED_PASS_WITHOUT_OBSERVED_EVIDENCE", "OBSERVED_EVIDENCE_REQUIRED"}]
                if clean_reason_codes:
                    return ImportDecision(
                        verdict=REVIEW_REQUIRED,
                        reason_codes=list(set(clean_reason_codes)),
                        task_id=task_id,
                        task_pack_sha256=task_pack_sha256,
                        report_sha256=report_sha256,
                        declared_status=declared_status,
                        safe_summary="Báo cáo khớp bằng chứng nhưng có cảnh báo.",
                        evidence_summary="Observed evidence hợp lệ nhưng report chứa cảnh báo bổ sung."
                    )
                else:
                    return ImportDecision(
                        verdict=VERIFIED_PASS,
                        reason_codes=["OK"],
                        task_id=task_id,
                        task_pack_sha256=task_pack_sha256,
                        report_sha256=report_sha256,
                        declared_status=declared_status,
                        safe_summary="Xác nhận kiểm thử thành công (VERIFIED_PASS).",
                        evidence_summary="Khớp nối 100% giữa tự khai báo và kết quả quan sát cục bộ độc lập."
                    )
            else:
                reason_codes.append("OBSERVED_EVIDENCE_REQUIRED")
                return ImportDecision(
                    verdict=REVIEW_REQUIRED,
                    reason_codes=list(set(reason_codes)),
                    task_id=task_id,
                    task_pack_sha256=task_pack_sha256,
                    report_sha256=report_sha256,
                    declared_status=declared_status,
                    safe_summary="Bằng chứng quan sát không hợp lệ hoặc thiếu chứng thực.",
                    evidence_summary="Observed evidence không vượt qua các chốt chặn an toàn hoặc không khớp final state sạch."
                )

    # 17. Handing declared FAIL or REVIEW_REQUIRED status
    if declared_status == "FAIL":
        return ImportDecision(
            verdict=FAIL,
            reason_codes=["OK"] if not reason_codes else list(set(reason_codes)),
            task_id=task_id,
            task_pack_sha256=task_pack_sha256,
            report_sha256=report_sha256,
            declared_status=declared_status,
            safe_summary="Báo cáo ghi nhận lỗi của Agent (FAIL).",
            evidence_summary="Báo cáo được nhập thành công với trạng thái lỗi tự khai."
        )

    # Fallback to REVIEW_REQUIRED
    return ImportDecision(
        verdict=REVIEW_REQUIRED,
        reason_codes=["OK"] if not reason_codes else list(set(reason_codes)),
        task_id=task_id,
        task_pack_sha256=task_pack_sha256,
        report_sha256=report_sha256,
        declared_status=declared_status,
        safe_summary="Báo cáo cần phê duyệt thủ công.",
        evidence_summary=f"Trạng thái tự khai: {declared_status}. Lý do: {reason_codes}"
    )

def import_agent_report(
    report: Dict[str, Any],
    task_pack: Dict[str, Any],
    observed_evidence: Optional[Dict[str, Any]] = None
) -> ImportDecision:
    """
    Main entry point to import a report dictionary.
    Runs schema and security validations.
    """
    return validate_agent_report(report, task_pack, observed_evidence)

def load_agent_report_for_task_pack(
    report_path: Path,
    task_pack_path: Path,
    observed_evidence: Optional[Dict[str, Any]] = None
) -> ImportDecision:
    """
    Loads task pack and report from files, parses, and returns ImportDecision.
    Handles malformed, too large, deep nesting, or BOM errors gracefully by returning INVALID_REPORT.
    """
    try:
        report_data = load_agent_report(report_path)
    except ValueError as e:
        err_msg = str(e)
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=[err_msg],
            task_id=None,
            task_pack_sha256=None,
            report_sha256=None,
            declared_status=None,
            safe_summary="Lỗi tải file báo cáo.",
            evidence_summary="Không thể đọc hoặc phân tích cú pháp file JSON report."
        )
    except FileNotFoundError:
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=["FILE_NOT_FOUND"],
            task_id=None,
            task_pack_sha256=None,
            report_sha256=None,
            declared_status=None,
            safe_summary="Không tìm thấy file báo cáo.",
            evidence_summary="File report không tồn tại trên đường dẫn chỉ định."
        )

    if not Path(task_pack_path).is_file():
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=["FILE_NOT_FOUND"],
            task_id=None,
            task_pack_sha256=None,
            report_sha256=None,
            declared_status=None,
            safe_summary="Không tìm thấy file Task Pack.",
            evidence_summary="File Task Pack không tồn tại trên đường dẫn chỉ định."
        )

    try:
        # Load task pack simply as json
        task_pack_bytes = Path(task_pack_path).read_bytes()
        if task_pack_bytes.startswith(b"\xef\xbb\xbf"):
            task_pack_bytes = task_pack_bytes[3:]
        task_pack = json.loads(task_pack_bytes.decode("utf-8"))
    except Exception as e:
        return ImportDecision(
            verdict=INVALID_REPORT,
            reason_codes=["MALFORMED_JSON"],
            task_id=None,
            task_pack_sha256=None,
            report_sha256=None,
            declared_status=None,
            safe_summary="Lỗi tải file Task Pack.",
            evidence_summary="Không thể đọc hoặc phân tích cú pháp file Task Pack."
        )

    return validate_agent_report(report_data, task_pack, observed_evidence)
