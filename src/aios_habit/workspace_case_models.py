"""Durable, local-only metadata for a Workspace Chat case."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Final, Optional
from uuid import uuid4


CASE_STATUS_DRAFT: Final[str] = "draft"
CASE_STATUS_TRIAGED: Final[str] = "triaged"
CASE_STATUS_IN_PROGRESS: Final[str] = "in_progress"
CASE_STATUS_WAITING_EVIDENCE: Final[str] = "waiting_evidence"
CASE_STATUS_RESOLVED: Final[str] = "resolved"
CASE_STATUS_CLOSED: Final[str] = "closed"
CASE_TYPE_INVESTIGATION: Final[str] = "investigation"
CASE_PRIORITY_NORMAL: Final[str] = "normal"
CASE_SCOPE_GENERAL: Final[str] = "general"
LOCAL_ADMIN_ACTOR_ID: Final[str] = "local_admin"
CASE_PROVENANCE_UNKNOWN: Final[str] = "unknown"
CASE_PRIVACY_LOCAL_ONLY: Final[str] = "local_only"

EXPERT_REQUEST_STATUS_OPEN: Final[str] = "open"
EXPERT_REQUEST_STATUS_ANSWERED: Final[str] = "answered"
EXPERT_REQUEST_STATUS_CANCELLED: Final[str] = "cancelled"
EXPERT_REQUEST_STATUS_EXPIRED: Final[str] = "expired"

EXPERT_DECISION_CONFIRMED: Final[str] = "confirmed"
EXPERT_DECISION_REJECTED: Final[str] = "rejected"
EXPERT_DECISION_NEEDS_MORE_EVIDENCE: Final[str] = "needs_more_evidence"
EXPERT_DECISION_CONFLICTED: Final[str] = "conflicted"

ALLOWED_EXPERT_DECISIONS: Final[frozenset[str]] = frozenset(
    {
        EXPERT_DECISION_CONFIRMED,
        EXPERT_DECISION_REJECTED,
        EXPERT_DECISION_NEEDS_MORE_EVIDENCE,
        EXPERT_DECISION_CONFLICTED,
    }
)

LESSON_STATUS_CANDIDATE: Final[str] = "candidate"
LESSON_STATUS_APPROVED: Final[str] = "approved"
LESSON_STATUS_REVOKED: Final[str] = "revoked"

ALLOWED_LESSON_STATUSES: Final[frozenset[str]] = frozenset(
    {
        LESSON_STATUS_CANDIDATE,
        LESSON_STATUS_APPROVED,
        LESSON_STATUS_REVOKED,
    }
)

ARTIFACT_STATUS_DRAFT: Final[str] = "draft"
ARTIFACT_STATUS_APPROVED: Final[str] = "approved"
ARTIFACT_STATUS_SUPERSEDED: Final[str] = "superseded"

ALLOWED_ARTIFACT_STATUSES: Final[frozenset[str]] = frozenset(
    {
        ARTIFACT_STATUS_DRAFT,
        ARTIFACT_STATUS_APPROVED,
        ARTIFACT_STATUS_SUPERSEDED,
    }
)

ARTIFACT_TYPE_REPORT: Final[str] = "report"
ARTIFACT_TYPE_SOP: Final[str] = "sop"

ALLOWED_ARTIFACT_TYPES: Final[frozenset[str]] = frozenset(
    {
        ARTIFACT_TYPE_REPORT,
        ARTIFACT_TYPE_SOP,
    }
)


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
    created_by: str = LOCAL_ADMIN_ACTOR_ID
    case_type: str = CASE_TYPE_INVESTIGATION
    priority: str = CASE_PRIORITY_NORMAL
    owner_id: str = LOCAL_ADMIN_ACTOR_ID
    assignee_id: Optional[str] = None
    scope: str = CASE_SCOPE_GENERAL
    version: int = 1
    updated_at: str = field(default_factory=utc_now_iso)
    activity_head_digest: str = ""

    @classmethod
    def new(
        cls,
        *,
        conversation_id: str,
        assistant_message_id: str,
        trace_id: str,
        evidence_digest: str,
        created_by: str = LOCAL_ADMIN_ACTOR_ID,
        scope: str = CASE_SCOPE_GENERAL,
    ) -> "CaseRecord":
        return cls(
            case_id=f"CASE-{uuid4().hex[:12].upper()}",
            conversation_id=conversation_id,
            assistant_message_id=assistant_message_id,
            trace_id=trace_id,
            evidence_digest=evidence_digest,
            title="Hồ sơ vụ việc từ Workspace Chat",
            created_by=created_by,
            owner_id=created_by,
            scope=scope,
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


def case_activity_digest(
    *,
    event_id: str,
    case_id: str,
    event_type: str,
    actor_id: str,
    occurred_at: str,
    payload_digest: str,
    previous_event_digest: str,
) -> str:
    payload = {
        "actor_id": actor_id,
        "case_id": case_id,
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "payload_digest": payload_digest,
        "previous_event_digest": previous_event_digest,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CaseActivity:
    event_id: str
    case_id: str
    event_type: str
    actor_id: str
    occurred_at: str
    payload_digest: str
    previous_event_digest: str
    event_digest: str

    @classmethod
    def new(
        cls,
        *,
        case_id: str,
        event_type: str,
        actor_id: str,
        payload_digest: str,
        previous_event_digest: str = "",
        occurred_at: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> "CaseActivity":
        resolved_event_id = event_id or f"CASE-ACT-{uuid4().hex[:12].upper()}"
        resolved_time = occurred_at or utc_now_iso()
        digest = case_activity_digest(
            event_id=resolved_event_id,
            case_id=case_id,
            event_type=event_type,
            actor_id=actor_id,
            occurred_at=resolved_time,
            payload_digest=payload_digest,
            previous_event_digest=previous_event_digest,
        )
        return cls(
            event_id=resolved_event_id,
            case_id=case_id,
            event_type=event_type,
            actor_id=actor_id,
            occurred_at=resolved_time,
            payload_digest=payload_digest,
            previous_event_digest=previous_event_digest,
            event_digest=digest,
        )


@dataclass(frozen=True)
class CaseChecklistItem:
    item_id: str
    case_id: str
    description: str
    status: str = "open"
    created_by: str = LOCAL_ADMIN_ACTOR_ID
    created_at: str = field(default_factory=utc_now_iso)
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None


@dataclass(frozen=True)
class CaseFilter:
    case_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    owner_id: Optional[str] = None
    assignee_id: Optional[str] = None


@dataclass(frozen=True)
class ExpertRequest:
    request_id: str
    case_id: str
    claim_digest: str
    question_text: str
    required_scope: str
    requested_expert_id: Optional[str] = None
    status: str = EXPERT_REQUEST_STATUS_OPEN
    due_at: Optional[str] = None
    created_by: str = LOCAL_ADMIN_ACTOR_ID
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class ExpertReview:
    review_id: str
    request_id: str
    case_id: str
    claim_digest: str
    evidence_digest: str
    decision: str
    reviewer_id: str
    reviewer_role: str
    scope: str
    rationale: str
    confidence: float = 1.0
    supersedes_review_id: Optional[str] = None
    reviewed_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class CaseLesson:
    lesson_id: str
    case_id: str
    review_id: str
    claim_digest: str
    evidence_digest: str
    title: str
    content: str
    status: str = LESSON_STATUS_CANDIDATE
    version: int = 1
    created_by: str = LOCAL_ADMIN_ACTOR_ID
    created_at: str = field(default_factory=utc_now_iso)
    updated_by: str = LOCAL_ADMIN_ACTOR_ID
    updated_at: str = field(default_factory=utc_now_iso)
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    revoked_by: Optional[str] = None
    revoked_at: Optional[str] = None
    revocation_reason: Optional[str] = None


@dataclass(frozen=True)
class CaseArtifactRecord:
    artifact_id: str
    case_id: str
    artifact_type: str
    title: str
    content_markdown: str
    content_digest: str
    version: int = 1
    status: str = ARTIFACT_STATUS_DRAFT
    created_by: str = LOCAL_ADMIN_ACTOR_ID
    created_at: str = field(default_factory=utc_now_iso)
    updated_by: str = LOCAL_ADMIN_ACTOR_ID
    updated_at: str = field(default_factory=utc_now_iso)
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    approval_notes: Optional[str] = None
    exported_path: Optional[str] = None
    provenance_digest: str = ""


@dataclass(frozen=True)
class CaseDetail:
    case: CaseRecord
    evidence: tuple[CaseEvidenceReference, ...]
    activities: tuple[CaseActivity, ...]
    checklist: tuple[CaseChecklistItem, ...]
    expert_requests: tuple[ExpertRequest, ...] = ()
    expert_reviews: tuple[ExpertReview, ...] = ()
    lessons: tuple[CaseLesson, ...] = ()
    artifacts: tuple[CaseArtifactRecord, ...] = ()


@dataclass(frozen=True)
class TraceResolution:
    status: str
    trace_id: str
    trace: object | None = None
