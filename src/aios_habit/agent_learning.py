"""Local-only, evidence-governed observations for retrieval improvement.

Candidates contain stable hashes and bounded operational metadata only. They do
not contain user prompts, source contents, source paths, provider output, or
credentials. Promotion is explicit and requires existing AIOS evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable

from .core import append_jsonl, read_jsonl, sha_text

CANDIDATE_STATUSES = {"candidate", "reviewed", "promoted", "rejected"}
ACTIONABLE_KINDS = {"semantic_failure", "lexical_insufficiency"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_reason(reason: str) -> str:
    compact = "".join(char if char.isalnum() else "_" for char in str(reason).casefold())
    return compact.strip("_")[:96] or "unknown"


@dataclass
class LearningCandidate:
    candidate_id: str
    kind: str
    context_hash: str
    reason_code: str
    profile: str
    status: str = "candidate"
    count: int = 1
    first_seen_at: str = field(default_factory=_now)
    last_seen_at: str = field(default_factory=_now)
    evidence_ids: list[str] = field(default_factory=list)
    review_note: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.kind not in ACTIONABLE_KINDS:
            errors.append("invalid kind")
        if self.status not in CANDIDATE_STATUSES:
            errors.append("invalid status")
        if len(self.context_hash) != 64 or any(char not in "0123456789abcdef" for char in self.context_hash):
            errors.append("invalid context_hash")
        if not self.reason_code or len(self.reason_code) > 96 or not self.reason_code.replace("_", "").isalnum():
            errors.append("invalid reason_code")
        if not self.profile or len(self.profile) > 64:
            errors.append("invalid profile")
        if self.count < 1:
            errors.append("invalid count")
        if self.status == "promoted" and not self.evidence_ids:
            errors.append("promoted candidate requires evidence")
        return errors


def candidate_path(repo: Path) -> Path:
    return repo / "04_extraction_workspace" / "learning_candidates.jsonl"


def _candidate_key(kind: str, context_hash: str, reason_code: str, profile: str) -> str:
    return sha_text("|".join((kind, context_hash, reason_code, profile)))[:20]


def _load(path: Path) -> list[LearningCandidate]:
    return [LearningCandidate(**record) for record in read_jsonl(path)]


def _write(path: Path, candidates: Iterable[LearningCandidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(asdict(candidate), sort_keys=True) + "\n" for candidate in candidates),
        encoding="utf-8",
    )


def list_candidates(repo: Path) -> list[LearningCandidate]:
    return _load(candidate_path(repo))


def observe(
    repo: Path,
    *,
    kind: str,
    context_fingerprint: str,
    reason_code: str,
    profile: str,
) -> LearningCandidate | None:
    """Append or deduplicate a sanitized, local-only improvement candidate."""
    if kind not in ACTIONABLE_KINDS or not context_fingerprint:
        return None
    safe_reason = _safe_reason(reason_code)
    context_hash = sha_text(context_fingerprint)
    path = candidate_path(repo)
    records = _load(path)
    key = _candidate_key(kind, context_hash, safe_reason, profile)
    for index, record in enumerate(records):
        existing_key = _candidate_key(record.kind, record.context_hash, record.reason_code, record.profile)
        if existing_key == key and record.status == "candidate":
            updated = LearningCandidate(
                **{**asdict(record), "count": record.count + 1, "last_seen_at": _now()}
            )
            records[index] = updated
            _write(path, records)
            return updated
    candidate = LearningCandidate(
        candidate_id=f"LRN-{key.upper()}",
        kind=kind,
        context_hash=context_hash,
        reason_code=safe_reason,
        profile=profile[:64],
    )
    if candidate.validate():
        return None
    append_jsonl(path, asdict(candidate))
    return candidate


def review(
    repo: Path,
    candidate_id: str,
    status: str,
    *,
    evidence_ids: Iterable[str] = (),
    note: str = "",
) -> LearningCandidate:
    """Transition a candidate only after validating explicit evidence on promotion."""
    if status not in CANDIDATE_STATUSES - {"candidate"}:
        raise ValueError("invalid_review_status")
    path = candidate_path(repo)
    records = _load(path)
    evidence = sorted({value.strip() for value in evidence_ids if value.strip()})
    known_evidence = {
        item.get("evidence_id")
        for item in read_jsonl(repo / "03_evidence_registry" / "records" / "evidence.jsonl")
    }
    for index, record in enumerate(records):
        if record.candidate_id != candidate_id:
            continue
        if record.status != "candidate":
            raise ValueError("candidate_not_reviewable")
        if status == "promoted" and (not evidence or any(value not in known_evidence for value in evidence)):
            raise ValueError("promotion_requires_existing_evidence")
        updated = LearningCandidate(
            **{
                **asdict(record),
                "status": status,
                "evidence_ids": evidence if status == "promoted" else record.evidence_ids,
                "review_note": _safe_reason(note)[:96],
                "last_seen_at": _now(),
            }
        )
        if updated.validate():
            raise ValueError("invalid_candidate_transition")
        records[index] = updated
        _write(path, records)
        return updated
    raise ValueError("candidate_not_found")
