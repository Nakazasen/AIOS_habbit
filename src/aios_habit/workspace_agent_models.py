"""Typed, redacted state for Workspace Chat Agent IDE sessions."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
import uuid

AgentState = Literal['ready', 'running', 'awaiting_edit_approval', 'awaiting_command_approval', 'completed', 'failed', 'cancelled']


def _now() -> str:
    return datetime.now().isoformat()


@dataclass(frozen=True)
class WorkspaceAgentRequest:
    conversation_id: str
    workspace_root: str
    instruction: str
    mode: Literal['analyze', 'debug', 'plan', 'implement'] = 'analyze'
    workspace_scope_confirmed: bool = False
    document_context_allowed: bool = False


@dataclass(frozen=True)
class WorkspaceAgentToolEvent:
    event_id: str
    tool: str
    category: Literal['read', 'proposal', 'approval']
    ok: bool
    elapsed_ms: int
    summary: str


@dataclass(frozen=True)
class WorkspaceAgentPendingAction:
    action_id: str
    kind: Literal['edit', 'command']
    summary: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class WorkspaceAgentResult:
    session_id: str
    state: AgentState
    answer_text: str
    events: tuple[WorkspaceAgentToolEvent, ...] = ()
    pending_action: WorkspaceAgentPendingAction | None = None
    error_message: str = ''
    created_at: str = field(default_factory=_now)


def new_session_id() -> str:
    return f'AGENT-{uuid.uuid4().hex[:12].upper()}'


def new_action_id() -> str:
    return f'ACT-{uuid.uuid4().hex[:12].upper()}'
