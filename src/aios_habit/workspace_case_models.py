"""Durable, local-only metadata for a Workspace Chat case."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Final
from uuid import uuid4


CASE_STATUS_DRAFT: Final[str] = "draft"
CASE_PROVENANCE_UNKNOWN: Final[str] = "unknown"
CASE_PRIVACY_LOCAL_ONLY: Final[str] = "local_only"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    conversation_id: str
    assistant_message_id: str
    trace_id: str
    evidence_digest: str
    title: str
    status: str = CASE_STATUS_DRAFT
    created_at: str = field(default_factory=utc_now_iso)
    created_by: str = "Workspace Chat"

    @classmethod
    def new(
        cls,
        *,
        conversation_id: str,
        assistant_message_id: str,
        trace_id: str,
        evidence_digest: str,
    ) -> "CaseRecord":
        return cls(
            case_id=f"CASE-{uuid4().hex[:12].upper()}",
            conversation_id=conversation_id,
            assistant_message_id=assistant_message_id,
            trace_id=trace_id,
            evidence_digest=evidence_digest,
            title="Hồ sơ vụ việc từ Workspace Chat",
        )


@dataclass(frozen=True)
class CaseEvidenceReference:
    reference_id: str
    case_id: str
    trace_id: str
    evidence_node_id: str
    citation_id: str
    source_locator: str
    source_title: str
    reference_digest: str
    provenance_status: str = CASE_PROVENANCE_UNKNOWN
    privacy_label: str = CASE_PRIVACY_LOCAL_ONLY
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class CaseAuditEvent:
    event_id: str
    case_id: str
    event_type: str
    created_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def case_created(cls, case_id: str) -> "CaseAuditEvent":
        return cls(
            event_id=f"CASE-AUDIT-{uuid4().hex[:12].upper()}",
            case_id=case_id,
            event_type="case_created",
        )
