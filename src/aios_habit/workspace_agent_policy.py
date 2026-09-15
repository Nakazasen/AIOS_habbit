"""Fail-closed permission policy for Workspace Chat Agent IDE actions."""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

READ_TOOLS = frozenset({
    'index_status', 'index_build', 'index_refresh', 'index_search', 'project_indexer',
    'semantic_index', 'list_dir', 'read_file', 'read_file_paged', 'search_files',
    'git_context', 'git_status', 'git_diff', 'git_file_diff', 'git_log',
    'pending_edits', 'command_job_status',
})
APPROVAL_TOOLS = frozenset({
    'write_file', 'apply_patch', 'apply_pending_edit', 'discard_pending_edit',
    'execute_command', 'start_command_job', 'cancel_command_job',
})
DISALLOWED_TOOLS = frozenset({
    'delete_file', 'move_file', 'git_stage', 'git_unstage', 'git_discard',
    'git_commit', 'git_push', 'provider_mutate', 'extension_install',
})
MAX_TOOL_STEPS = 8
MAX_INSTRUCTION_CHARS = 8_000
MAX_COMMAND_CHARS = 1_000

# MVP Task Types
TASK_TYPE_ERROR_REPORT = "error_report"
TASK_TYPE_PROCESS_DESIGN_REVIEW = "process_design_review"
TASK_TYPE_CODE_CHANGE = "code_change"
VALID_TASK_TYPES = frozenset({
    TASK_TYPE_ERROR_REPORT,
    TASK_TYPE_PROCESS_DESIGN_REVIEW,
    TASK_TYPE_CODE_CHANGE,
})

# Actions for Agent Runtime Protocol
RUNTIME_READ_ACTIONS = frozenset({
    "health",
    "get_session",
    "list_events",
    "read_file",
    "search_files",
    "get_workspace_state",
})
RUNTIME_WRITE_ACTIONS = frozenset({
    "create_file",
    "edit_file",
})
RUNTIME_COMMAND_ACTIONS = frozenset({
    "run_test",
})
RUNTIME_SESSION_ACTIONS = frozenset({
    "create_session",
    "resume_session",
    "abort_session",
    "undo",
})
RUNTIME_DENIED_ACTIONS = frozenset({
    "git_commit",
    "git_push",
    "git_merge",
    "git_deploy",
    "delete_file",
    "move_file",
    "system_admin",
    "env_file",
    "path_traversal",
    "symlink_escape",
})

# Secret tokens and forbidden file patterns
FORBIDDEN_FILE_PATTERNS = (
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r"^id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$", re.IGNORECASE),
    re.compile(r"^.*(\.pem|\.key|\.p12|\.pfx|\.kdbx)$", re.IGNORECASE),
    re.compile(r"^.*(credential|secret|token|password).*$", re.IGNORECASE),
)
FORBIDDEN_DIR_NAMES = frozenset({
    ".git",
    "local_cases",
    "local_runs",
    ".ssh",
    ".aws",
    ".azure",
})

# Shell metacharacters forbidden in test commands to prevent injection
SHELL_METACHAR_PATTERN = re.compile(r"[;&|<>`$]")

# Safe test command allowlist prefixes
DEFAULT_ALLOWED_TEST_PREFIXES = (
    "pytest",
    "python -m pytest",
    "python -m unittest",
    "python test_",
    "python -m tests",
    "uv run pytest",
    "uv run --no-sync pytest",
    "uv run --no-sync --group dev pytest",
    "uv run python -m unittest",
    "uv run python -m pytest",
    "uv run python test_",
)


class AgentPolicyError(ValueError):
    """Raised when a workspace agent request violates an explicit safety rule."""


@dataclass(frozen=True)
class PolicyDecision:
    tool: str
    category: str
    requires_approval: bool


@dataclass(frozen=True)
class AgentScopeGrant:
    work_id: str
    task_root: str
    task_type: str
    allowed_actions: frozenset[str]
    denied_actions: frozenset[str]
    allowed_commands: tuple[str, ...]
    privacy_route: str = "local_only"
    policy_version: str = "aios_agent_runtime_v1"
    scope_digest: str = ""


def canonical_workspace_root(workspace_root: str) -> str:
    candidate = Path(workspace_root).expanduser().resolve()
    if not candidate.is_dir():
        raise AgentPolicyError('Workspace đã chọn không tồn tại hoặc không phải thư mục.')
    return str(candidate)


def canonical_task_root(task_root: str | Path) -> Path:
    candidate = Path(task_root).expanduser().resolve()
    if not candidate.exists():
        raise AgentPolicyError(f'Thư mục tác vụ không tồn tại: {candidate.name}')
    if not candidate.is_dir():
        raise AgentPolicyError('Thư mục tác vụ không phải là một thư mục hợp lệ.')
    return candidate


def is_forbidden_name(name: str) -> bool:
    for pattern in FORBIDDEN_FILE_PATTERNS:
        if pattern.match(name):
            return True
    return False


def validate_path_in_task_root(target_path: str | Path, task_root: str | Path) -> Path:
    root = canonical_task_root(task_root)
    raw = str(target_path).strip()
    if not raw:
        raise AgentPolicyError('Đường dẫn tệp không được để trống.')

    parts = Path(raw).parts
    if any(p == ".." for p in parts):
        raise AgentPolicyError('Thao tác bị từ chối: phát hiện đường dẫn thoát ra ngoài thư mục làm việc (path traversal).')

    candidate_path = Path(raw)
    resolved = (root / candidate_path).resolve() if not candidate_path.is_absolute() else candidate_path.resolve()

    try:
        rel = resolved.relative_to(root)
    except ValueError:
        raise AgentPolicyError('Thao tác bị từ chối: đường dẫn nằm ngoài phạm vi thư mục tác vụ được cấp phép.')

    for part in rel.parts:
        if part in FORBIDDEN_DIR_NAMES:
            raise AgentPolicyError(f'Thao tác bị từ chối: truy cập vào vùng cấm ({part}) không được phép.')
        if is_forbidden_name(part):
            raise AgentPolicyError(f'Thao tác bị từ chối: truy cập tệp chứa bí mật hoặc cấu hình nhạy cảm ({part}).')

    return resolved


def validate_test_command(command: str | list[str], allowed_commands: tuple[str, ...] | None = None) -> str:
    if isinstance(command, (list, tuple)):
        cmd_str = " ".join(str(c).strip() for c in command)
    elif isinstance(command, str):
        cmd_str = command.strip()
    else:
        raise AgentPolicyError('Lệnh kiểm thử không hợp lệ.')

    if not cmd_str:
        raise AgentPolicyError('Lệnh kiểm thử không được để trống.')
    if len(cmd_str) > MAX_COMMAND_CHARS:
        raise AgentPolicyError('Lệnh kiểm thử vượt quá giới hạn an toàn.')

    if SHELL_METACHAR_PATTERN.search(cmd_str):
        raise AgentPolicyError('Thao tác bị từ chối: lệnh chứa ký tự đặc biệt nguy hiểm hoặc chuỗi lệnh vỏ (shell injection).')

    prefixes = allowed_commands if allowed_commands is not None else DEFAULT_ALLOWED_TEST_PREFIXES
    normalized_cmd = " ".join(cmd_str.split())
    matched = False
    for prefix in prefixes:
        prefix_norm = " ".join(prefix.split())
        if prefix_norm.endswith("_"):
            if normalized_cmd.startswith(prefix_norm):
                matched = True
                break
        else:
            if normalized_cmd == prefix_norm or normalized_cmd.startswith(prefix_norm + " "):
                matched = True
                break

    if not matched:
        raise AgentPolicyError('Thao tác bị từ chối: lệnh không nằm trong danh sách lệnh kiểm thử được phép.')

    return normalized_cmd


def is_safe_artifact_path(
    target_path: str | Path,
    allowed_roots: tuple[str | Path, ...] | None = None,
) -> bool:
    """Validate that target_path resolves strictly within one of the allowed roots."""
    try:
        raw = str(target_path).strip()
        if not raw:
            return False
        parts = Path(raw).parts
        if any(p == ".." for p in parts):
            return False
        resolved = Path(raw).resolve()

        # Explicitly authorized caller roots
        if allowed_roots:
            for root in allowed_roots:
                try:
                    if resolved.is_relative_to(Path(root).resolve()):
                        return True
                except (ValueError, AttributeError):
                    continue

        # Repository-contained safe roots
        base_roots = [
            Path("artifacts").resolve(),
            Path("local_cases").resolve(),
            Path("tests").resolve(),
        ]
        for root in base_roots:
            try:
                if resolved.is_relative_to(root):
                    return True
            except (ValueError, AttributeError):
                continue

        # Controlled temporary subdirectories only (never the entire system tempdir)
        sys_temp = Path(tempfile.gettempdir()).resolve()
        try:
            if resolved.is_relative_to(sys_temp):
                rel_parts = resolved.relative_to(sys_temp).parts
                if rel_parts and (rel_parts[0].startswith("aios_") or rel_parts[0].startswith("pytest-")):
                    return True
        except (ValueError, AttributeError):
            pass

        return False
    except Exception:
        return False


def compute_scope_digest(work_id: str, task_root: str, task_type: str, allowed_actions: frozenset[str]) -> str:
    hasher = hashlib.sha256()
    hasher.update(work_id.encode("utf-8"))
    hasher.update(task_root.encode("utf-8"))
    hasher.update(task_type.encode("utf-8"))
    for action in sorted(allowed_actions):
        hasher.update(action.encode("utf-8"))
    return hasher.hexdigest()


def create_scope_grant(
    *,
    work_id: str,
    task_root: str | Path,
    task_type: str,
    allowed_commands: tuple[str, ...] | None = None,
    privacy_route: str = "local_only",
) -> AgentScopeGrant:
    if task_type not in VALID_TASK_TYPES:
        raise AgentPolicyError(f'Loại nhiệm vụ không hợp lệ: {task_type}.')

    root = canonical_task_root(task_root)
    actions = set(RUNTIME_READ_ACTIONS) | set(RUNTIME_SESSION_ACTIONS)

    if task_type == TASK_TYPE_CODE_CHANGE:
        actions.update(RUNTIME_WRITE_ACTIONS)
        actions.update(RUNTIME_COMMAND_ACTIONS)
        cmds = allowed_commands if allowed_commands is not None else DEFAULT_ALLOWED_TEST_PREFIXES
    elif task_type in {TASK_TYPE_ERROR_REPORT, TASK_TYPE_PROCESS_DESIGN_REVIEW}:
        actions.update(RUNTIME_WRITE_ACTIONS)
        cmds = ()
    else:
        cmds = ()

    allowed_frozen = frozenset(actions)
    digest = compute_scope_digest(work_id, str(root), task_type, allowed_frozen)

    return AgentScopeGrant(
        work_id=work_id,
        task_root=str(root),
        task_type=task_type,
        allowed_actions=allowed_frozen,
        denied_actions=RUNTIME_DENIED_ACTIONS,
        allowed_commands=cmds,
        privacy_route=privacy_route,
        scope_digest=digest,
    )


def authorize_scope_action(
    grant: AgentScopeGrant,
    action: str,
    *,
    path: str | Path | None = None,
    command: str | list[str] | None = None,
) -> PolicyDecision:
    if action in grant.denied_actions or action in RUNTIME_DENIED_ACTIONS:
        raise AgentPolicyError(f'Thao tác {action} bị cấm tuyệt đối theo chính sách an toàn.')

    if action not in grant.allowed_actions:
        raise AgentPolicyError(f'Thao tác {action} không được cấp phép cho loại nhiệm vụ {grant.task_type}.')

    if path is not None and action in (RUNTIME_READ_ACTIONS | RUNTIME_WRITE_ACTIONS):
        validate_path_in_task_root(path, grant.task_root)

    if action == "run_test":
        if command is None:
            raise AgentPolicyError('Lệnh kiểm thử không được để trống khi chạy run_test.')
        validate_test_command(command, grant.allowed_commands)

    category = 'read' if action in RUNTIME_READ_ACTIONS else ('command' if action in RUNTIME_COMMAND_ACTIONS else 'write')
    return PolicyDecision(tool=action, category=category, requires_approval=False)


def validate_request(*, workspace_root: str, instruction: str, scope_confirmed: bool) -> str:
    if not scope_confirmed:
        raise AgentPolicyError('Bạn cần xác nhận phạm vi Workspace Agent IDE trước khi tiếp tục.')
    if not isinstance(instruction, str) or not instruction.strip():
        raise AgentPolicyError('Yêu cầu Agent IDE không được để trống.')
    if len(instruction) > MAX_INSTRUCTION_CHARS:
        raise AgentPolicyError('Yêu cầu Agent IDE vượt quá giới hạn an toàn.')
    return canonical_workspace_root(workspace_root)


def authorize_tool(tool: str, args: dict[str, Any], *, approved: bool) -> PolicyDecision:
    if tool in {'delete_file', 'move_file'} or tool in DISALLOWED_TOOLS:
        raise AgentPolicyError('Thao tác xóa hoặc di chuyển file nhà máy bị cấm tuyệt đối.')
    if tool not in READ_TOOLS | APPROVAL_TOOLS:
        raise AgentPolicyError('Thao tác này chưa được Workspace Chat Agent IDE hỗ trợ.')
    if tool in APPROVAL_TOOLS and not approved:
        raise AgentPolicyError('Thao tác này cần phê duyệt rõ ràng trước khi thực hiện.')
    if tool in {'execute_command', 'start_command_job'}:
        command = args.get('command')
        if not isinstance(command, str) or not command.strip() or len(command) > MAX_COMMAND_CHARS:
            raise AgentPolicyError('Lệnh được đề xuất không hợp lệ hoặc vượt quá giới hạn an toàn.')
    return PolicyDecision(tool=tool, category='read' if tool in READ_TOOLS else 'approval', requires_approval=tool in APPROVAL_TOOLS)
