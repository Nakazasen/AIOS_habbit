"""Knowledge claim extraction, provenance verification, and conflict detection for expert knowledge acquisition.

Implements T048, T049, T050, T051 of Goal 010-expert-knowledge-acquisition.
Fail-closed invariants:
1. Every claim MUST have verified source provenance (turn ID, segment ID, document chunk ID).
2. Claims lacking verified support are strictly rejected (zero unsupported claims).
3. Transcripts containing unconfirmed critical tokens (numbers, units, model codes) cannot produce claims.
4. Conflicting claims across experts remain strictly 'conflicted' (no automatic winner picking, mandatory escalation).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from aios_habit.expert_interview_models import InterviewSession, InterviewTurn
from aios_habit.local_transcription import TranscriptionReceipt, TranscriptionSegment, extract_critical_tokens

# Claim Status Constants
CLAIM_STATUS_CANDIDATE = "candidate"
CLAIM_STATUS_CONFIRMED = "confirmed"
CLAIM_STATUS_CONFLICTED = "conflicted"
CLAIM_STATUS_REJECTED = "rejected"
CLAIM_STATUS_SUPERSEDED = "superseded"

VALID_CLAIM_STATUSES = {
    CLAIM_STATUS_CANDIDATE,
    CLAIM_STATUS_CONFIRMED,
    CLAIM_STATUS_CONFLICTED,
    CLAIM_STATUS_REJECTED,
    CLAIM_STATUS_SUPERSEDED,
}


class KnowledgeClaimError(Exception):
    """Base exception for knowledge claim processing."""
    pass


class UnsupportedClaimError(KnowledgeClaimError):
    """Raised when a claim has no verifiable source references."""
    pass


class UnconfirmedCriticalTokenError(KnowledgeClaimError):
    """Raised when claim extraction is attempted on a transcript with unconfirmed numbers, units, or codes."""
    pass


class StaleSourceProvenanceError(KnowledgeClaimError):
    """Raised when source reference digest is stale or mismatched."""
    pass


@dataclass(frozen=True)
class KnowledgeClaim:
    """Atomic, verifiable technical claim extracted from expert interview and provenance sources."""

    claim_id: str
    statement: str
    scope: str
    source_refs: Tuple[str, ...]
    version: str = "1.0"
    validity_conditions: Tuple[str, ...] = ()
    confidence: float = 1.0
    uncertainty_note: str = ""
    status: str = CLAIM_STATUS_CANDIDATE
    conflict_claim_ids: Tuple[str, ...] = ()
    escalation_id: Optional[str] = None
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ValueError("Nội dung phát biểu tri thức (statement) không được để trống.")
        if not self.scope.strip():
            raise ValueError("Phạm vi công đoạn (scope) không được để trống.")
        if not self.source_refs:
            raise UnsupportedClaimError("Mỗi phát biểu tri thức bắt buộc phải có ít nhất một nguồn chứng minh (source_refs).")
        if self.status not in VALID_CLAIM_STATUSES:
            raise ValueError(f"Trạng thái '{self.status}' không hợp lệ. Phải thuộc {VALID_CLAIM_STATUSES}.")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Độ tin cậy confidence ({self.confidence}) phải nằm trong khoảng [0.0, 1.0].")

    @property
    def digest(self) -> str:
        """Compute deterministic payload digest representing claim semantic content."""
        payload = f"{self.claim_id}:{self.version}:{self.statement}:{self.scope}:{','.join(sorted(self.source_refs))}:{','.join(sorted(self.validity_conditions))}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ConflictDetectionResult:
    """Result of evaluating potential contradictions between claims in the same scope."""

    has_conflict: bool
    conflicting_claim_ids: Tuple[str, ...] = ()
    reason: str = ""
    escalation_required: bool = False


def extract_claim_from_turn(
    turn: InterviewTurn,
    session: InterviewSession,
    scope: str,
    transcript_receipt: Optional[TranscriptionReceipt] = None,
    require_confirmed_tokens: bool = True,
) -> KnowledgeClaim:
    """Extract atomic knowledge claim from an interview turn with strict provenance verification.

    Implements T049 and T050.
    """
    answer_text = turn.answer_text.strip()
    if not answer_text or turn.answer_state in ("skipped", "unknown"):
        raise KnowledgeClaimError("Không thể trích xuất phát biểu tri thức từ câu trả lời bị bỏ qua hoặc chưa rõ.")

    # T050: Enforce confirmation of critical tokens if derived from audio transcript
    if transcript_receipt is not None and require_confirmed_tokens:
        for seg in transcript_receipt.segments:
            if seg.critical_tokens and not seg.is_confirmed:
                raise UnconfirmedCriticalTokenError(
                    f"Đoạn chép lời '{seg.segment_id}' chứa thông số kỹ thuật {seg.critical_tokens} chưa được chuyên gia xác nhận."
                )

    # Build exact source references
    source_refs_list = [f"turn:{turn.turn_id}"]
    if transcript_receipt:
        source_refs_list.append(f"transcript:{transcript_receipt.receipt_id}")
        for s in transcript_receipt.segments:
            source_refs_list.append(f"segment:{s.segment_id}")

    # Extract conditions and thresholds
    critical_tokens = extract_critical_tokens(answer_text)
    validity_conds = tuple(f"Thông số yêu cầu: {t}" for t in critical_tokens)

    uncertainty = "Chuyên gia tự đánh giá chưa hoàn toàn chắc chắn." if turn.answer_state == "uncertain" else ""
    confidence = turn.answer_confidence if turn.answer_state != "uncertain" else min(turn.answer_confidence, 0.6)

    claim_id = f"CLM-{session.session_id}-{turn.sequence}"

    return KnowledgeClaim(
        claim_id=claim_id,
        statement=answer_text,
        scope=scope,
        source_refs=tuple(source_refs_list),
        version="1.0",
        validity_conditions=validity_conds,
        confidence=confidence,
        uncertainty_note=uncertainty,
        status=CLAIM_STATUS_CANDIDATE,
    )


def detect_claim_conflicts(
    new_claim: KnowledgeClaim,
    existing_claims: Sequence[KnowledgeClaim],
) -> ConflictDetectionResult:
    """Analyze claims in the same scope to identify conflicting numerical thresholds or contradictory conditions.

    Implements T051.
    Invariants:
    - Never auto-resolve contradictions.
    - Contradicting claims must be linked and escalated.
    """
    conflicts: List[str] = []
    conflict_reasons: List[str] = []

    # Extract numbers and tokens from new claim
    new_tokens = set(extract_critical_tokens(new_claim.statement))

    for ex in existing_claims:
        # Only compare active claims in the exact same scope
        if ex.claim_id == new_claim.claim_id:
            continue
        if ex.scope != new_claim.scope:
            continue
        if ex.status in (CLAIM_STATUS_REJECTED, CLAIM_STATUS_SUPERSEDED):
            continue

        ex_tokens = set(extract_critical_tokens(ex.statement))

        # Check for diverging thresholds on similar metric terms (e.g. temperature, pressure)
        # Numerical divergence check:
        # If both mention different numbers with same unit (e.g., 55 độ C vs 70 độ C)
        diff_tokens = new_tokens.symmetric_difference(ex_tokens)
        has_number_conflict = False
        for tok in diff_tokens:
            if any(char.isdigit() for char in tok):
                has_number_conflict = True
                break

        if has_number_conflict and len(new_tokens) > 0 and len(ex_tokens) > 0:
            conflicts.append(ex.claim_id)
            conflict_reasons.append(
                f"Xung đột thông số kỹ thuật giữa '{new_claim.claim_id}' ({list(new_tokens)}) và '{ex.claim_id}' ({list(ex_tokens)}) trong công đoạn '{new_claim.scope}'."
            )

    if conflicts:
        return ConflictDetectionResult(
            has_conflict=True,
            conflicting_claim_ids=tuple(conflicts),
            reason="; ".join(conflict_reasons),
            escalation_required=True,
        )

    return ConflictDetectionResult(has_conflict=False)


def mark_conflicting_claims(
    claim_a: KnowledgeClaim,
    conflicting_ids: Tuple[str, ...],
    reason: str,
) -> KnowledgeClaim:
    """Mark claim as conflicted with explicit conflict links, without choosing a winner."""
    return KnowledgeClaim(
        claim_id=claim_a.claim_id,
        statement=claim_a.statement,
        scope=claim_a.scope,
        source_refs=claim_a.source_refs,
        version=claim_a.version,
        validity_conditions=claim_a.validity_conditions,
        confidence=claim_a.confidence,
        uncertainty_note=f"{claim_a.uncertainty_note} [XUNG ĐỘT: {reason}]".strip(),
        status=CLAIM_STATUS_CONFLICTED,
        conflict_claim_ids=conflicting_ids,
        escalation_id=f"ESC-CONF-{int(datetime.now(timezone.utc).timestamp())}",
        confirmed_by=claim_a.confirmed_by,
        confirmed_at=claim_a.confirmed_at,
        created_at=claim_a.created_at,
    )
