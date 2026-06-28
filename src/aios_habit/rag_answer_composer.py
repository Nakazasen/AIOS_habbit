from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from aios_habit.rag_evidence import RAGEvidencePack


@dataclass
class LocalAnswerDraft:
    draft_id: str
    pack_id: str
    query: str
    answer_text: str
    citation_ids: List[str]
    evidence_ids: List[str]
    privacy_mode: str
    allowed_external: bool
    insufficient_evidence: bool
    confidence_label: str
    warnings: List[str] = field(default_factory=list)
    composer_name: str = "deterministic_local_template_v1"
    provider_call: bool = False
    notebooklm_call: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, str] = field(default_factory=dict)


def stable_answer_draft_id(pack: RAGEvidencePack) -> str:
    citation_payload = "|".join(item.citation_id + item.evidence_id for item in pack.items)
    raw = f"{pack.pack_id}:{pack.query}:{pack.privacy_mode}:{pack.insufficient_evidence}:{citation_payload}"
    return "ANS-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()


def compose_local_answer(pack: RAGEvidencePack, max_items: int = 5) -> LocalAnswerDraft:
    """Compose a deterministic local draft from evidence only.

    This is not an LLM and does not infer beyond snippets. It exists to give the
    owner a local, cited draft when provider/NotebookLM use is not allowed or not
    needed.
    """
    warnings: List[str] = []
    if pack.insufficient_evidence:
        warnings.append("Insufficient evidence: do not treat this as a complete answer.")
        warnings.extend(pack.missing_evidence_warnings)
    if pack.privacy_mode == "local_only":
        warnings.append("Privacy: local_only evidence must not be exported externally.")
    elif not pack.allowed_external:
        warnings.append("Privacy: external export is not allowed by the current pack configuration.")

    citation_ids = [item.citation_id for item in pack.items[:max_items]]
    evidence_ids = [item.evidence_id for item in pack.items[:max_items]]

    lines = [
        f"Local draft for: {pack.query}",
        f"Confidence: {pack.confidence_label}",
    ]
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in warnings)

    if not pack.items:
        lines.append("No cited evidence was available, so no factual answer is drafted.")
    else:
        lines.append("Evidence-grounded points:")
        for item in pack.items[:max_items]:
            snippet = " ".join(item.snippet.split())
            lines.append(f"- {item.citation_id} {snippet}")
        lines.append("Use only the cited points above; verify before taking action.")

    return LocalAnswerDraft(
        draft_id=stable_answer_draft_id(pack),
        pack_id=pack.pack_id,
        query=pack.query,
        answer_text="\n".join(lines),
        citation_ids=citation_ids,
        evidence_ids=evidence_ids,
        privacy_mode=pack.privacy_mode,
        allowed_external=pack.allowed_external,
        insufficient_evidence=pack.insufficient_evidence,
        confidence_label=pack.confidence_label,
        warnings=warnings,
    )


def local_answer_draft_to_dict(draft: LocalAnswerDraft) -> Dict[str, Any]:
    return asdict(draft)
