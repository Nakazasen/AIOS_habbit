"""Fail-closed permission policy for Workspace Chat Agent IDE actions."""
from __future__ import annotations

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


class AgentPolicyError(ValueError):
    """Raised when a workspace agent request violates an explicit safety rule."""


@dataclass(frozen=True)
class PolicyDecision:
    tool: str
    category: str
    requires_approval: bool


def canonical_workspace_root(workspace_root: str) -> str:
    candidate = Path(workspace_root).expanduser().resolve()
    if not candidate.is_dir():
        raise AgentPolicyError('Workspace đã chọn không tồn tại hoặc không phải thư mục.')
    return str(candidate)


def validate_request(*, workspace_root: str, instruction: str, scope_confirmed: bool) -> str:
    if not scope_confirmed:
        raise AgentPolicyError('Bạn cần xác nhận phạm vi Workspace Agent IDE trước khi tiếp tục.')
    if not isinstance(instruction, str) or not instruction.strip():
        raise AgentPolicyError('Yêu cầu Agent IDE không được để trống.')
    if len(instruction) > MAX_INSTRUCTION_CHARS:
        raise AgentPolicyError('Yêu cầu Agent IDE vượt quá giới hạn an toàn.')
    return canonical_workspace_root(workspace_root)


def authorize_tool(tool: str, args: dict[str, Any], *, approved: bool) -> PolicyDecision:
    if tool in DISALLOWED_TOOLS or tool not in READ_TOOLS | APPROVAL_TOOLS:
        raise AgentPolicyError('Thao tác này chưa được Workspace Chat Agent IDE hỗ trợ.')
    if tool in APPROVAL_TOOLS and not approved:
        raise AgentPolicyError('Thao tác này cần phê duyệt rõ ràng trước khi thực hiện.')
    if tool in {'execute_command', 'start_command_job'}:
        command = args.get('command')
        if not isinstance(command, str) or not command.strip() or len(command) > MAX_COMMAND_CHARS:
            raise AgentPolicyError('Lệnh được đề xuất không hợp lệ hoặc vượt quá giới hạn an toàn.')
    return PolicyDecision(tool=tool, category='read' if tool in READ_TOOLS else 'approval', requires_approval=tool in APPROVAL_TOOLS)
