"""Immutable recall, decision, and correction models for Goal 011."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

PROVIDER_MODE_LOCAL = "local"
PROVIDER_MODE_CLOUD = "cloud"
PROVIDER_MODES = frozenset({PROVIDER_MODE_LOCAL, PROVIDER_MODE_CLOUD})

SOURCE_KIND_MEMORY_UNIT = "memory_unit"
SOURCE_KIND_SENIOR_LEARNING_CARD = "senior_learning_card"
SOURCE_KIND_CASE_LESSON = "case_lesson"
SOURCE_KIND_PUBLISHED_ARTIFACT = "published_artifact"
SOURCE_KIND_USER_MEMORY = "user_memory"
US1_SOURCE_KINDS = frozenset(
    {
        SOURCE_KIND_MEMORY_UNIT,
        SOURCE_KIND_SENIOR_LEARNING_CARD,
        SOURCE_KIND_CASE_LESSON,
        SOURCE_KIND_PUBLISHED_ARTIFACT,
    }
)
SOURCE_KINDS = US1_SOURCE_KINDS | {SOURCE_KIND_USER_MEMORY}

PRIVACY_LOCAL_ONLY = "local_only"
PRIVACY_CLOUD_ALLOWED = "cloud_allowed"
PRIVACY_CLASSES = frozenset({PRIVACY_LOCAL_ONLY, PRIVACY_CLOUD_ALLOWED})

ELIGIBLE_STATUSES = frozenset({"verified", "confirmed"})
INELIGIBLE_STATUSES = frozenset(
    {"draft", "candidate", "rejected", "deprecated", "revoked", "needs_evidence"}
)

PROMPT_DELIMITER_OPEN = "<<<MEMORY_CONTENT"
PROMPT_DELIMITER_CLOSE = "MEMORY_CONTENT"

DEFAULT_RECALL_LIMIT = 5
DEFAULT_CHAR_BUDGET = 4000
MAX_RECALL_LIMIT = 5
MAX_CHAR_BUDGET = 4000


def _require_nonempty(value: str, field_name: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty")
    return text


@dataclass(frozen=True)
class WorkspaceMemoryRecallRequest:
    question: str
    workspace_id: str
    collection_id: str
    provider_mode: str
    include_local_only: bool = False
    limit: int = DEFAULT_RECALL_LIMIT
    char_budget: int = DEFAULT_CHAR_BUDGET

    def __post_init__(self) -> None:
        object.__setattr__(self, "question", _require_nonempty(self.question, "question"))
        object.__setattr__(self, "workspace_id", _require_nonempty(self.workspace_id, "workspace_id"))
        object.__setattr__(
            self, "collection_id", _require_nonempty(self.collection_id, "collection_id")
        )
        mode = (self.provider_mode or "").strip().lower()
        if mode not in PROVIDER_MODES:
            raise ValueError("provider_mode must be local or cloud")
        object.__setattr__(self, "provider_mode", mode)
        if not isinstance(self.include_local_only, bool):
            raise ValueError("include_local_only must be bool")
        if not isinstance(self.limit, int) or not (1 <= self.limit <= MAX_RECALL_LIMIT):
            raise ValueError("limit must be an integer from 1 to 5")
        if not isinstance(self.char_budget, int) or not (1 <= self.char_budget <= MAX_CHAR_BUDGET):
            raise ValueError("char_budget must be an integer from 1 to 4000")


@dataclass(frozen=True)
class WorkspaceMemoryRecallItem:
    memory_key: str
    source_kind: str
    source_id: str
    title: str
    statement: str
    applies_when: str
    does_not_apply_when: str
    scope: str
    status: str
    evidence_refs: tuple[str, ...]
    privacy_classification: str
    export_allowed: bool
    updated_at: str
    score: float = 0.0
    match_reasons: tuple[str, ...] = ()
    conflict_group: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "memory_key", _require_nonempty(self.memory_key, "memory_key"))
        kind = (self.source_kind or "").strip()
        if kind not in SOURCE_KINDS:
            raise ValueError("source_kind is not supported")
        object.__setattr__(self, "source_kind", kind)
        object.__setattr__(self, "source_id", _require_nonempty(self.source_id, "source_id"))
        object.__setattr__(self, "title", _require_nonempty(self.title, "title"))
        statement = _require_nonempty(self.statement, "statement")
        if PROMPT_DELIMITER_OPEN in statement or PROMPT_DELIMITER_CLOSE in statement:
            raise ValueError("statement must not contain prompt delimiters")
        object.__setattr__(self, "statement", statement)
        object.__setattr__(self, "scope", _require_nonempty(self.scope, "scope"))
        status = (self.status or "").strip().lower()
        if status not in ELIGIBLE_STATUSES:
            raise ValueError("status must be verified or confirmed for recall items")
        object.__setattr__(self, "status", status)
        refs = tuple(ref.strip() for ref in self.evidence_refs if (ref or "").strip())
        if not refs:
            raise ValueError("evidence_refs must contain at least one valid ref")
        object.__setattr__(self, "evidence_refs", refs)
        privacy = (self.privacy_classification or "").strip()
        if privacy not in PRIVACY_CLASSES:
            raise ValueError("privacy_classification must be local_only or cloud_allowed")
        object.__setattr__(self, "privacy_classification", privacy)
        if not isinstance(self.export_allowed, bool):
            raise ValueError("export_allowed must be bool")
        object.__setattr__(self, "updated_at", _require_nonempty(self.updated_at, "updated_at"))
        if kind == SOURCE_KIND_USER_MEMORY and status not in ELIGIBLE_STATUSES:
            raise ValueError("user_memory recall items must be confirmed")


@dataclass(frozen=True)
class MemoryRecallTrace:
    trace_id: str
    created_at: str
    question_hash: str
    provider_mode: str
    selected_source_ids: tuple[str, ...]
    excluded_reason_codes: tuple[str, ...]
    rounded_scores: tuple[float, ...]
    total_chars: int
    consent_fingerprint: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "trace_id", _require_nonempty(self.trace_id, "trace_id"))
        object.__setattr__(self, "created_at", _require_nonempty(self.created_at, "created_at"))
        object.__setattr__(self, "question_hash", _require_nonempty(self.question_hash, "question_hash"))
        mode = (self.provider_mode or "").strip().lower()
        if mode not in PROVIDER_MODES:
            raise ValueError("provider_mode must be local or cloud")
        object.__setattr__(self, "provider_mode", mode)
        object.__setattr__(
            self,
            "consent_fingerprint",
            _require_nonempty(self.consent_fingerprint, "consent_fingerprint"),
        )
        if self.total_chars < 0:
            raise ValueError("total_chars must be >= 0")


@dataclass(frozen=True)
class WorkspaceMemoryRecallResult:
    items: tuple[WorkspaceMemoryRecallItem, ...] = ()
    excluded_counts: Mapping[str, int] = field(default_factory=dict)
    has_conflict: bool = False
    consent_fingerprint: str = "empty"
    trace: MemoryRecallTrace | None = None
    fallback_reason: str | None = None

    def __post_init__(self) -> None:
        if len(self.items) > MAX_RECALL_LIMIT:
            raise ValueError("items must not exceed 5")
        total_chars = sum(len(item.statement) + len(item.title) for item in self.items)
        if total_chars > MAX_CHAR_BUDGET:
            raise ValueError("items exceed char_budget")
        counts = {str(key): int(value) for key, value in dict(self.excluded_counts).items()}
        object.__setattr__(self, "excluded_counts", counts)
        object.__setattr__(
            self,
            "consent_fingerprint",
            _require_nonempty(self.consent_fingerprint, "consent_fingerprint"),
        )
        if self.has_conflict and not any(item.conflict_group for item in self.items):
            raise ValueError("has_conflict requires a conflict_group on at least one item")


DECISION_ACTIONS = frozenset({"confirm", "forget", "revoke", "supersede", "merge"})
CORRECTION_STATUSES = frozenset({"candidate", "confirmed", "cancelled"})


@dataclass(frozen=True)
class MemoryDecision:
    decision_id: str
    memory_id: str
    action: str
    statement: str
    scope: str
    evidence_refs: tuple[str, ...]
    content_digest: str
    actor_label: str
    created_at: str
    supersedes_decision_id: str | None = None
    privacy_classification: str = PRIVACY_LOCAL_ONLY
    export_allowed: bool = False
    title: str = ""
    applies_when: str = ""
    does_not_apply_when: str = ""
    conflict_group: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_id", _require_nonempty(self.decision_id, "decision_id"))
        object.__setattr__(self, "memory_id", _require_nonempty(self.memory_id, "memory_id"))
        action = (self.action or "").strip()
        if action not in DECISION_ACTIONS:
            raise ValueError("action is not supported")
        object.__setattr__(self, "action", action)
        if action in {"confirm", "supersede", "merge"}:
            object.__setattr__(self, "statement", _require_nonempty(self.statement, "statement"))
        object.__setattr__(self, "scope", _require_nonempty(self.scope, "scope"))
        object.__setattr__(self, "content_digest", _require_nonempty(self.content_digest, "content_digest"))
        object.__setattr__(self, "actor_label", _require_nonempty(self.actor_label, "actor_label"))
        object.__setattr__(self, "created_at", _require_nonempty(self.created_at, "created_at"))
        privacy = (self.privacy_classification or "").strip()
        if privacy not in PRIVACY_CLASSES:
            raise ValueError("privacy_classification must be local_only or cloud_allowed")
        object.__setattr__(self, "privacy_classification", privacy)
        if action in {"supersede", "merge"} and not (self.supersedes_decision_id or "").strip():
            raise ValueError("supersede/merge requires supersedes_decision_id")

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "memory_id": self.memory_id,
            "action": self.action,
            "statement": self.statement,
            "scope": self.scope,
            "evidence_refs": list(self.evidence_refs),
            "content_digest": self.content_digest,
            "actor_label": self.actor_label,
            "created_at": self.created_at,
            "supersedes_decision_id": self.supersedes_decision_id,
            "privacy_classification": self.privacy_classification,
            "export_allowed": self.export_allowed,
            "title": self.title,
            "applies_when": self.applies_when,
            "does_not_apply_when": self.does_not_apply_when,
            "conflict_group": self.conflict_group,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "MemoryDecision":
        refs = data.get("evidence_refs") or ()
        return cls(
            decision_id=str(data["decision_id"]),
            memory_id=str(data["memory_id"]),
            action=str(data["action"]),
            statement=str(data.get("statement") or ""),
            scope=str(data["scope"]),
            evidence_refs=tuple(str(ref) for ref in refs),
            content_digest=str(data["content_digest"]),
            actor_label=str(data["actor_label"]),
            created_at=str(data["created_at"]),
            supersedes_decision_id=(str(data["supersedes_decision_id"]) if data.get("supersedes_decision_id") else None),
            privacy_classification=str(data.get("privacy_classification") or PRIVACY_LOCAL_ONLY),
            export_allowed=bool(data.get("export_allowed", False)),
            title=str(data.get("title") or ""),
            applies_when=str(data.get("applies_when") or ""),
            does_not_apply_when=str(data.get("does_not_apply_when") or ""),
            conflict_group=(str(data["conflict_group"]) if data.get("conflict_group") else None),
        )


@dataclass(frozen=True)
class CorrectionLessonCandidate:
    candidate_id: str
    statement: str
    applies_when: str
    does_not_apply_when: str
    message_ref: str
    trace_ref: str | None = None
    similar_memory_ids: tuple[str, ...] = ()
    status: str = "candidate"

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _require_nonempty(self.candidate_id, "candidate_id"))
        object.__setattr__(self, "statement", _require_nonempty(self.statement, "statement"))
        object.__setattr__(self, "applies_when", _require_nonempty(self.applies_when, "applies_when"))
        object.__setattr__(self, "message_ref", _require_nonempty(self.message_ref, "message_ref"))
        status = (self.status or "").strip()
        if status not in CORRECTION_STATUSES:
            raise ValueError("status must be candidate, confirmed, or cancelled")
        object.__setattr__(self, "status", status)
        if "assistant_answer" in self.message_ref.lower() and len(self.statement) > 4000:
            raise ValueError("candidate must not persist a raw assistant answer")

    def to_decision(self, *, actor_label: str, scope: str, evidence_refs: tuple[str, ...]) -> MemoryDecision:
        import hashlib
        from datetime import datetime, timezone

        digest = hashlib.sha256(f"{self.statement.strip().casefold()}|{scope.strip().casefold()}".encode("utf-8")).hexdigest()
        return MemoryDecision(
            decision_id=f"dec_{self.candidate_id}",
            memory_id=f"corr_{self.candidate_id}",
            action="confirm",
            statement=self.statement,
            scope=scope,
            evidence_refs=evidence_refs,
            content_digest=digest,
            actor_label=actor_label,
            created_at=datetime.now(timezone.utc).isoformat(),
            applies_when=self.applies_when,
            does_not_apply_when=self.does_not_apply_when,
        )
