"""
Module for Isolated Coding Assistant (US6 / FR-010).
Integrates Task Pack scoping, immutable coding proposal generation,
diff validation, and observed execution result verification.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from aios_habit.agent_result_import import (
    FAIL,
    INVALID_REPORT,
    REVIEW_REQUIRED,
    VERIFIED_PASS,
    ImportDecision,
    validate_agent_report,
)
from aios_habit.agent_task_pack import (
    ValidationError,
    build_agent_task_pack,
    compute_task_pack_sha256,
    export_agent_task_pack,
    is_forbidden_metadata_path,
    validate_agent_task_pack,
)


class CodingAssistantError(Exception):
    """Base exception for coding assistant operations."""


class ScopeViolationError(CodingAssistantError):
    """Raised when a proposal touches forbidden files or runs forbidden commands."""


class ProposalStateError(CodingAssistantError):
    """Raised when proposal action is invalid for current status or digest."""


@dataclass(frozen=True)
class CodingProposal:
    proposal_id: str
    task_id: str
    case_id: str
    version: int
    diff_content: str
    commands_to_run: tuple[str, ...]
    risk_assessment: str
    status: str  # "pending", "approved", "rejected", "applied"
    proposal_digest: str
    created_at: str
    created_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    approval_notes: str = ""
    rejection_reason: str = ""


def parse_diff_touched_files(diff_text: str) -> list[str]:
    """Extract touched relative file paths from a unified diff."""
    files = set()
    for line in diff_text.splitlines():
        if line.startswith("--- ") or line.startswith("+++ "):
            path_part = line[4:].strip()
            if path_part.startswith("a/") or path_part.startswith("b/"):
                path_part = path_part[2:]
            if path_part and path_part != "/dev/null":
                clean = path_part.replace("\\", "/").strip()
                files.add(clean)
    return sorted(files)


def compute_proposal_digest(payload: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 digest of proposal immutable fields."""
    temp = {
        "task_id": payload.get("task_id", ""),
        "case_id": payload.get("case_id", ""),
        "version": payload.get("version", 1),
        "diff_content": payload.get("diff_content", ""),
        "commands_to_run": sorted(payload.get("commands_to_run", ())),
        "risk_assessment": payload.get("risk_assessment", ""),
    }
    encoded = json.dumps(temp, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def create_coding_task_pack(
    *,
    task_id: str,
    case_id: str,
    objective: str,
    allowed_files: list[str],
    allowed_commands: list[str],
    required_tests: list[str],
    expected_branch: str = "main",
    expected_head: str = "0" * 40,
    export_root: str = "local_runs/agent_bridge/outbox",
) -> tuple[dict[str, Any], str, str]:
    """
    Build, validate and export a coding task pack under strict scope limits.
    Forbids local_cases, local_runs, .env, destructive and line control commands.
    """
    clean_obj = objective.strip()
    if not clean_obj:
        raise ValidationError("Mục tiêu task lập trình không được để trống.")

    forbidden_files = [
        ".ai/**",
        "local_cases/**",
        "local_runs/**",
        ".env*",
        "specs/**/owner-decisions*.yaml",
    ]
    forbidden_commands = [
        "git push",
        "rm -rf",
        "rmdir",
        "del",
        "shutdown",
        "reboot",
        "format",
        "curl",
        "wget",
        "nc",
    ]

    pack = build_agent_task_pack(
        task_id=task_id,
        task_type="implementation",
        gate="US6-CODING",
        agent_class="implementation",
        objective=clean_obj,
        repo_logical_id="AIOS_habbit_main",
        repo_path_policy="logical_relative",
        expected_branch=expected_branch,
        expected_head=expected_head,
        allowed_files=allowed_files,
        forbidden_files=forbidden_files,
        allowed_commands=allowed_commands,
        forbidden_commands=forbidden_commands,
        required_tests=required_tests,
        privacy_class="internal",
        destination="local_owner_only",
        purpose=f"Coding assistance for case {case_id}",
        consent_ref=f"case-consent-{case_id}",
        source_policy="redact_raw_contents",
        roadmap_reference={
            "phase": "Phase 008",
            "gate": "US6",
            "lock_status": "P1.0 LOCKED",
        },
        pass_fail_rules=[
            "Chỉ sửa các tệp trong danh sách allowed_files",
            "Không sửa tệp thuộc danh sách cấm",
            "Mọi kiểm thử bắt buộc phải đạt exit code 0",
        ],
        rollback={
            "allowed": True,
            "strategy": "manual_git_discard_by_owner",
            "description": "Chủ sở hữu hủy bỏ thay đổi qua git restore.",
        },
    )

    validate_agent_task_pack(pack)
    exported_path, pack_sha256 = export_agent_task_pack(pack, export_root=export_root, overwrite=True)
    return pack, pack_sha256, exported_path


def create_coding_proposal(
    *,
    task_pack: dict[str, Any],
    case_id: str,
    diff_content: str,
    commands_to_run: list[str],
    risk_assessment: str,
    author: str = "local_admin",
) -> CodingProposal:
    """Create an immutable code modification proposal subject to user approval."""
    clean_diff = diff_content.strip()
    if not clean_diff:
        raise ScopeViolationError("Nội dung diff của đề xuất không được để trống.")

    touched_files = parse_diff_touched_files(clean_diff)
    if not touched_files:
        raise ScopeViolationError("Không tìm thấy tệp tin nào được sửa đổi trong diff.")

    scope = task_pack.get("scope", {})
    allowed_files = scope.get("allowed_files", [])
    forbidden_files = scope.get("forbidden_files", [])
    allowed_commands = scope.get("allowed_commands", [])
    forbidden_commands = scope.get("forbidden_commands", [])

    for f in touched_files:
        if is_forbidden_metadata_path(f):
            raise ScopeViolationError(f"Tệp '{f}' thuộc đường dẫn cấm tuyệt đối (local_cases, local_runs, .env).")

        is_allowed = any(fnmatch.fnmatch(f, pat) for pat in allowed_files)
        if not is_allowed:
            raise ScopeViolationError(f"Tệp '{f}' nằm ngoài phạm vi cho phép (allowed_files).")

        is_forbidden = any(fnmatch.fnmatch(f, pat) for pat in forbidden_files)
        if is_forbidden:
            raise ScopeViolationError(f"Tệp '{f}' nằm trong danh sách tệp cấm sửa (forbidden_files).")

    for cmd in commands_to_run:
        clean_cmd = cmd.strip()
        if not clean_cmd:
            continue
        is_cmd_allowed = any(clean_cmd == ac or clean_cmd.startswith(ac) for ac in allowed_commands)
        if not is_cmd_allowed:
            raise ScopeViolationError(f"Lệnh '{clean_cmd}' không nằm trong danh sách lệnh được phép (allowed_commands).")
        for fc in forbidden_commands:
            if fc in clean_cmd:
                raise ScopeViolationError(f"Lệnh '{clean_cmd}' chứa từ khóa hoặc lệnh cấm: '{fc}'.")

    now_iso = datetime.now(timezone.utc).isoformat()
    proposal_id = f"PROP-{uuid4().hex[:10].upper()}"
    digest = compute_proposal_digest({
        "task_id": task_pack["task_id"],
        "case_id": case_id,
        "version": 1,
        "diff_content": clean_diff,
        "commands_to_run": commands_to_run,
        "risk_assessment": risk_assessment.strip(),
    })

    return CodingProposal(
        proposal_id=proposal_id,
        task_id=task_pack["task_id"],
        case_id=case_id,
        version=1,
        diff_content=clean_diff,
        commands_to_run=tuple(commands_to_run),
        risk_assessment=risk_assessment.strip(),
        status="pending",
        proposal_digest=digest,
        created_at=now_iso,
        created_by=author,
    )


def approve_coding_proposal(
    proposal: CodingProposal,
    *,
    expected_digest: str,
    approver: str,
    notes: str = "",
) -> CodingProposal:
    """Approve a coding proposal with explicit digest matching."""
    if proposal.status != "pending":
        raise ProposalStateError("Chỉ có thể phê duyệt đề xuất đang ở trạng thái chờ duyệt (pending).")
    if expected_digest != proposal.proposal_digest:
        raise ProposalStateError("Mã digest của đề xuất không khớp với phiên bản dự kiến.")

    now_iso = datetime.now(timezone.utc).isoformat()
    return CodingProposal(
        proposal_id=proposal.proposal_id,
        task_id=proposal.task_id,
        case_id=proposal.case_id,
        version=proposal.version + 1,
        diff_content=proposal.diff_content,
        commands_to_run=proposal.commands_to_run,
        risk_assessment=proposal.risk_assessment,
        status="approved",
        proposal_digest=proposal.proposal_digest,
        created_at=proposal.created_at,
        created_by=proposal.created_by,
        approved_by=approver,
        approved_at=now_iso,
        approval_notes=notes.strip(),
        rejection_reason="",
    )


def reject_coding_proposal(
    proposal: CodingProposal,
    *,
    reviewer: str,
    reason: str,
) -> CodingProposal:
    """Reject a coding proposal with a clear reason."""
    if proposal.status != "pending":
        raise ProposalStateError("Chỉ có thể từ chối đề xuất đang ở trạng thái chờ duyệt (pending).")
    clean_reason = reason.strip()
    if not clean_reason:
        raise ProposalStateError("Vui lòng nhập lý do từ chối đề xuất.")

    return CodingProposal(
        proposal_id=proposal.proposal_id,
        task_id=proposal.task_id,
        case_id=proposal.case_id,
        version=proposal.version + 1,
        diff_content=proposal.diff_content,
        commands_to_run=proposal.commands_to_run,
        risk_assessment=proposal.risk_assessment,
        status="rejected",
        proposal_digest=proposal.proposal_digest,
        created_at=proposal.created_at,
        created_by=proposal.created_by,
        approved_by=reviewer,
        approved_at=datetime.now(timezone.utc).isoformat(),
        approval_notes="",
        rejection_reason=clean_reason,
    )


def build_observed_evidence(
    *,
    tests_passed: bool,
    changed_files: list[str],
    worktree_clean: bool = True,
    staged_files: Optional[list[str]] = None,
    untracked_files: Optional[list[str]] = None,
    forbidden_files_touched: Optional[list[str]] = None,
    repo_branch: str = "main",
    repo_head: str = "68b0686b04dd611931cd58a005d9eb7946ddd84a",
) -> dict[str, Any]:
    """Build observed execution evidence conforming to agent_result_import rules."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "command_source": "OWNER_APPROVED_FIXED_CONFIG",
        "command_from_report": False,
        "report_command_ignored": True,
        "worktree_clean": worktree_clean,
        "staged_files": staged_files if staged_files is not None else [],
        "untracked_files": untracked_files if untracked_files is not None else [],
        "changed_files": list(changed_files),
        "forbidden_files_touched": forbidden_files_touched if forbidden_files_touched is not None else [],
        "required_tests_passed": tests_passed,
        "verifier_name": "local_verifier",
        "verifier_version": "1.0",
        "observation_time_utc": now_iso,
        "owner_triggered": True,
        "owner_triggered_at_utc": now_iso,
        "repo_branch": repo_branch,
        "repo_head": repo_head,
    }


def verify_coding_execution(
    *,
    task_pack: dict[str, Any],
    proposal: CodingProposal,
    report_dict: dict[str, Any],
    observed_evidence: Optional[dict[str, Any]] = None,
) -> ImportDecision:
    """
    Validates execution results against task pack and proposal.
    Rejects self-reported PASS if observed evidence is missing or invalid.
    """
    if proposal.status != "approved":
        return ImportDecision(
            verdict=FAIL,
            reason_codes=["PROPOSAL_NOT_APPROVED"],
            task_id=task_pack.get("task_id"),
            task_pack_sha256=task_pack.get("pack_sha256"),
            report_sha256=None,
            declared_status=report_dict.get("declared_status"),
            safe_summary="Đề xuất lập trình chưa được phê duyệt.",
            evidence_summary="Không thể nhập kết quả chạy cho một proposal chưa được người dùng phê duyệt.",
        )

    return validate_agent_report(report_dict, task_pack, observed_evidence=observed_evidence)
