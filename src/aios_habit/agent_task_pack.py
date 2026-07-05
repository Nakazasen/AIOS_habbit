"""
Module for Agent Task Pack Export MVP (Gate AI-GW-A17A).
Provides builder, validation, canonical serialization, SHA-256 checksum calculation,
and local export behavior for task packs.
"""

import os
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# --- Exceptions ---

class TaskPackError(Exception):
    """Base exception for all task pack errors."""
    pass

class ValidationError(TaskPackError):
    """Exception raised when task pack validation fails."""
    pass

class ExportError(TaskPackError):
    """Exception raised when exporting a task pack fails."""
    pass

# --- Constraints & Constants ---

TASK_ID_REGEX = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,80}$")

ALLOWED_DESTINATIONS = {"local_owner_only", "external_manual_agent", "owner_managed_chat"}

PRIVACY_ORDER = ["public", "internal", "confidential", "local_only"]

SECRET_PATTERNS = [
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----",
    r"(?i)(api[_-]?key|token|password|secret|credentials)\s*[:=]\s*['\"][^'\"\s]{8,}['\"]",
    r"(sk-[a-zA-Z0-9]{8,})",
    r"(AIza[a-zA-Z0-9_\-]{8,})",
]

RAW_PATTERNS = [
    r"(?i)raw transcript",
    r"(?i)chat transcript",
    r"(?i)conversation transcript",
]

REQUIRED_FIELDS = [
    "schema_version",
    "task_id",
    "task_type",
    "gate",
    "agent_class",
    "objective",
    "repo",
    "scope",
    "privacy",
    "roadmap_reference",
    "pass_fail_rules",
    "rollback",
    "required_report_fields",
    "created_at",
]

REQUIRED_REPO_FIELDS = [
    "logical_repo_id",
    "repo_path_policy",
    "expected_branch",
    "expected_head",
]

REQUIRED_SCOPE_FIELDS = [
    "allowed_files",
    "forbidden_files",
    "allowed_commands",
    "forbidden_commands",
    "required_tests",
]

REQUIRED_PRIVACY_FIELDS = [
    "privacy_class",
    "destination",
    "purpose",
    "consent_ref",
    "source_policy",
]

# --- Validation Helpers ---

def validate_task_id(task_id: str) -> None:
    """
    Validates task_id with regex and ensures no illegal characters are present.
    """
    if not task_id:
        raise ValidationError("Task ID cannot be empty.")
    if len(task_id) < 3 or len(task_id) > 81:
        raise ValidationError("Task ID length must be between 3 and 81 characters.")
    if not TASK_ID_REGEX.match(task_id):
        raise ValidationError("Task ID does not match pattern ^[A-Z0-9][A-Z0-9_-]{2,80}$.")
    if "/" in task_id or "\\" in task_id or ".." in task_id:
        raise ValidationError("Task ID cannot contain slash, backslash, or dot-dot.")
    if re.search(r"[a-zA-Z]:", task_id):
        raise ValidationError("Task ID cannot contain drive letter patterns.")
    if any(ord(c) < 32 or ord(c) == 127 for c in task_id):
        raise ValidationError("Task ID cannot contain control characters.")

def validate_destination(destination: str) -> None:
    """
    Validates destination against allowed values. Reject direct cloud destination.
    """
    if destination not in ALLOWED_DESTINATIONS:
        raise ValidationError(f"Unknown or unsupported destination: '{destination}'.")

def is_absolute_or_system_path(path_str: str) -> bool:
    """
    Checks if path_str is absolute (Unix or Windows), UNC, or user home path.
    """
    if re.match(r"^[a-zA-Z]:", path_str):
        return True
    if path_str.startswith(r"\\") or path_str.startswith("//"):
        return True
    if path_str.startswith("/"):
        return True
    if path_str.startswith("~"):
        return True
    if "Users" in path_str or "home" in path_str:
        return True
    return False

def contains_path_traversal(path_str: str) -> bool:
    """
    Checks if path_str contains path traversal segments like '..'.
    """
    normalized = path_str.replace("\\", "/")
    parts = normalized.split("/")
    return ".." in parts

def is_forbidden_metadata_path(path_str: str) -> bool:
    """
    Checks if path_str points to forbidden or sensitive paths/files.
    """
    normalized = path_str.replace("\\", "/").lower()
    forbidden_segments = {".ai", "local_cases", "task.md", "walkthrough.md", "implementation_plan.md"}
    parts = normalized.split("/")
    for part in parts:
        if part in forbidden_segments:
            return True
        if part.endswith(".json") and ("secret" in part or "config" in part or "runtime" in part):
            return True
    return False

def check_sensitive_content(text: str) -> None:
    """
    Scans text for secrets, absolute paths, raw transcript markers, and excessive blobs.
    """
    if not text:
        return
    # Check secrets
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, text):
            raise ValidationError("Sensitive data (secret/token/key) detected in text.")
    # Check raw transcripts
    for pattern in RAW_PATTERNS:
        if re.search(pattern, text):
            raise ValidationError("Raw transcript/conversation marker detected in text.")
    # Check absolute paths / system paths in text
    if re.search(r"[a-zA-Z]:\\", text) or re.search(r"[a-zA-Z]:/", text) or re.search(r"\\\\", text):
        raise ValidationError("System path pattern detected in text.")
    # Check home directory pattern
    if "/home/" in text or "/Users/" in text or "\\Users\\" in text or "\\home\\" in text:
        raise ValidationError("Home directory pattern detected in text.")
    # Check local_cases / .ai / runtime paths in text
    for marker in [".ai", "local_cases", "task.md", "walkthrough.md", "implementation_plan.md"]:
        if marker in text:
            raise ValidationError(f"Forbidden workspace reference '{marker}' detected in text.")
    # Large text blobs check
    if len(text) > 1500:
        if "def " in text or "import " in text or "class " in text or "{" in text:
            raise ValidationError("Large text blob resembling code/data payload detected.")

# --- Privacy Resolution ---

def resolve_privacy_level(privacy_levels: List[str]) -> str:
    """
    Resolves the strictest privacy level from a list of levels (strictest-wins).
    """
    if not privacy_levels:
        return "local_only"
        
    strictest_idx = -1
    for lvl in privacy_levels:
        cleaned = lvl.strip().lower()
        if cleaned not in PRIVACY_ORDER:
            cleaned = "local_only"
        idx = PRIVACY_ORDER.index(cleaned)
        if idx > strictest_idx:
            strictest_idx = idx
            
    return PRIVACY_ORDER[strictest_idx]

# --- Core API ---

def build_agent_task_pack(
    task_id: str,
    task_type: str,
    gate: str,
    agent_class: str,
    objective: str,
    repo_logical_id: str,
    repo_path_policy: str,
    expected_branch: str,
    expected_head: str,
    allowed_files: List[str],
    forbidden_files: List[str],
    allowed_commands: List[str],
    forbidden_commands: List[str],
    required_tests: List[str],
    privacy_class: str,
    destination: str,
    purpose: str,
    consent_ref: str,
    source_policy: str,
    roadmap_reference: Dict[str, Any],
    pass_fail_rules: List[str],
    rollback: Dict[str, Any],
    required_report_fields: Optional[List[str]] = None,
    created_at: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs the task pack dictionary with v1 schema structure.
    Does not compute the hash or export the pack.
    """
    if required_report_fields is None:
        required_report_fields = [
            "schema_version",
            "task_id",
            "task_pack_sha256",
            "agent_class",
            "model_tool_name",
            "declared_status",
            "baseline.branch",
            "baseline.head",
            "final_state.branch",
            "final_state.head",
            "final_state.commit_hash",
            "final_state.push_status",
            "declared_files.changed",
            "declared_files.staged",
            "declared_files.untracked",
            "declared_files.committed",
            "declared_commands",
            "declared_tests",
            "risks",
            "blockers",
            "rollback",
            "reason_codes",
            "report_sha256"
        ]
        
    if created_at is None:
        from datetime import datetime, timezone
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        
    return {
        "schema_version": "aios_agent_task_pack_v1",
        "task_id": task_id,
        "task_type": task_type,
        "gate": gate,
        "agent_class": agent_class,
        "objective": objective,
        "repo": {
            "logical_repo_id": repo_logical_id,
            "repo_path_policy": repo_path_policy,
            "expected_branch": expected_branch,
            "expected_head": expected_head,
        },
        "scope": {
            "allowed_files": allowed_files,
            "forbidden_files": forbidden_files,
            "allowed_commands": allowed_commands,
            "forbidden_commands": forbidden_commands,
            "required_tests": required_tests,
        },
        "privacy": {
            "privacy_class": privacy_class,
            "destination": destination,
            "purpose": purpose,
            "consent_ref": consent_ref,
            "source_policy": source_policy,
        },
        "roadmap_reference": roadmap_reference,
        "pass_fail_rules": pass_fail_rules,
        "rollback": rollback,
        "required_report_fields": required_report_fields,
        "created_at": created_at,
    }

def canonicalize_task_pack(pack_dict: Dict[str, Any]) -> str:
    """
    Serializes a task pack dictionary to a canonical JSON string.
    Keys are sorted, no extra whitespaces, no NaN/Infinity, UTF-8.
    """
    return json.dumps(
        pack_dict,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False
    )

def compute_task_pack_sha256(pack_dict: Dict[str, Any]) -> str:
    """
    Computes the SHA-256 integrity hash/checksum of the task pack.
    Note: Excludes 'pack_sha256' from the calculation payload.
    """
    temp_dict = pack_dict.copy()
    temp_dict.pop("pack_sha256", None)
    
    canonical_str = canonicalize_task_pack(temp_dict)
    utf8_bytes = canonical_str.encode("utf-8")
    
    # Check that there is no BOM signature
    if utf8_bytes.startswith(b"\xef\xbb\xbf"):
        raise ValidationError("BOM signature is not allowed in UTF-8 encoding.")
        
    return hashlib.sha256(utf8_bytes).hexdigest()

def validate_agent_task_pack(pack: Dict[str, Any]) -> None:
    """
    Validates a completed task pack dictionary against schema and security policies.
    """
    # 1. Check schema_version
    schema_version = pack.get("schema_version")
    if schema_version != "aios_agent_task_pack_v1":
        raise ValidationError(f"Unsupported or missing schema version: {schema_version}")
        
    # 2. Check required fields
    for field in REQUIRED_FIELDS:
        if field not in pack:
            raise ValidationError(f"Missing required field: '{field}'")
            
    # 3. Validate task_id
    validate_task_id(pack["task_id"])
    
    # 4. Validate privacy
    privacy = pack["privacy"]
    if not isinstance(privacy, dict):
        raise ValidationError("Field 'privacy' must be a dictionary.")
    for f in REQUIRED_PRIVACY_FIELDS:
        if f not in privacy or privacy[f] is None:
            raise ValidationError(f"Missing or null required privacy field: 'privacy.{f}'")
            
    validate_destination(privacy["destination"])
    
    # 5. Validate repo
    repo = pack["repo"]
    if not isinstance(repo, dict):
        raise ValidationError("Field 'repo' must be a dictionary.")
    for f in REQUIRED_REPO_FIELDS:
        if f not in repo:
            raise ValidationError(f"Missing required repo field: 'repo.{f}'")
            
    # 6. Validate scope
    scope = pack["scope"]
    if not isinstance(scope, dict):
        raise ValidationError("Field 'scope' must be a dictionary.")
    for f in REQUIRED_SCOPE_FIELDS:
        if f not in scope:
            raise ValidationError(f"Missing required scope field: 'scope.{f}'")
            
    destination = privacy["destination"]
    
    # Relative path list check
    for path_list_name in ["allowed_files", "forbidden_files", "required_tests"]:
        paths = scope.get(path_list_name, [])
        if not isinstance(paths, list):
            raise ValidationError(f"Scope field '{path_list_name}' must be a list.")
        for p in paths:
            if not isinstance(p, str):
                raise ValidationError(f"Path in '{path_list_name}' must be a string.")
            if contains_path_traversal(p):
                raise ValidationError(f"Path traversal detected in '{path_list_name}': '{p}'")
            
            # Apply forbidden metadata path restriction ONLY to allowed_files and required_tests
            if path_list_name in {"allowed_files", "required_tests"}:
                if is_forbidden_metadata_path(p):
                    raise ValidationError(f"Forbidden path reference detected in '{path_list_name}': '{p}'")
                
            # If destination is external/chat, reject absolute local paths, UNC, etc.
            if destination in {"external_manual_agent", "owner_managed_chat"}:
                if is_absolute_or_system_path(p):
                    raise ValidationError(
                        f"Absolute or system path not allowed in '{path_list_name}' "
                        f"for external destination '{destination}': '{p}'"
                    )

    # 7. Check confidential/local_only raw content restrictions
    privacy_class = privacy["privacy_class"]
    if privacy_class not in {"local_only", "confidential", "internal", "public", "machine_only", "cloud_safe"}:
        raise ValidationError(f"Unknown privacy class: '{privacy_class}'")
        
    if privacy_class in {"local_only", "confidential"}:
        check_sensitive_content(pack["objective"])
        for field_name in ["objective", "created_at"]:
            if field_name in pack:
                check_sensitive_content(pack[field_name])
    else:
        check_sensitive_content(pack["objective"])

    # 8. Required report fields validation
    req_report_fields = pack.get("required_report_fields", [])
    if not isinstance(req_report_fields, list):
        raise ValidationError("Field 'required_report_fields' must be a list.")
        
    obsolete_report_fields = {"status", "final_head", "files_touched", "commands_run", "tests_run"}
    for f in req_report_fields:
        if f in obsolete_report_fields:
            raise ValidationError(f"Obsolete report field '{f}' requested in 'required_report_fields'")
            
    expected_report_fields = {
        "schema_version", "task_id", "task_pack_sha256", "agent_class", "model_tool_name",
        "declared_status", "baseline.branch", "baseline.head", "final_state.branch",
        "final_state.head", "final_state.commit_hash", "final_state.push_status",
        "declared_files.changed", "declared_files.staged", "declared_files.untracked",
        "declared_files.committed", "declared_commands", "declared_tests", "risks",
        "blockers", "rollback", "reason_codes", "report_sha256"
    }
    for expected_f in expected_report_fields:
        if expected_f not in req_report_fields:
            raise ValidationError(f"Missing required report field '{expected_f}' in 'required_report_fields'")

def export_agent_task_pack(
    pack_dict: Dict[str, Any],
    export_root: str = "local_runs/agent_bridge/outbox",
    overwrite: bool = False
) -> Tuple[str, str]:
    """
    Validates, computes the integrity hash/checksum, and atomically writes the task pack
    JSON to the local directory: <export_root>/<task_id>/<pack_sha256>.json.
    Ensures path containment and no silent overwrite by default.
    Returns: Tuple[str, str] representing the (exported_file_path, pack_sha256).
    """
    pack_copy = pack_dict.copy()
    
    # Calculate integrity hash and attach it
    pack_sha256 = compute_task_pack_sha256(pack_copy)
    pack_copy["pack_sha256"] = pack_sha256
    
    # Run full schema and security validation
    validate_agent_task_pack(pack_copy)
    
    task_id = pack_copy["task_id"]
    
    root_path = Path(export_root).resolve()
    target_dir = root_path / task_id
    target_file = target_dir / f"{pack_sha256}.json"
    
    # Enforce path containment
    resolved_target = target_file.resolve()
    try:
        resolved_target.relative_to(root_path)
    except ValueError:
        raise ExportError("Path containment violation: target path is outside export root.")
        
    # Create parent directories
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Check overwrite
    if target_file.exists() and not overwrite:
        raise ExportError(f"Target file already exists and overwrite is disabled: {target_file}")
        
    # Atomic write behavior
    temp_file = target_dir / f"{pack_sha256}.tmp"
    try:
        content = canonicalize_task_pack(pack_copy)
        temp_file.write_text(content, encoding="utf-8")
        os.replace(str(temp_file), str(target_file))
    except Exception as e:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass
        raise ExportError(f"Failed to write task pack atomically: {e}")
        
    return str(target_file), pack_sha256
