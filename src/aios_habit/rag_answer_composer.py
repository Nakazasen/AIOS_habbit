from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from aios_habit.rag_evidence import RAGEvidencePack
from aios_habit.citation_answer import build_citation_index, compose_citation_first_answer
from aios_habit.final_answer_composer import FinalOwnerAnswer, compose_final_owner_answer, final_owner_answer_to_dict


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
    answer_kind: str = "local_evidence_draft"
    final_answer: bool = False
    requires_strong_model_or_human_review: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass
class StrongModelAnswer:
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
    composer_name: str = "strong_model_bridge"
    provider_call: bool = True
    notebooklm_call: bool = False
    answer_kind: str = "strong_model_answer"
    final_answer: bool = True
    requires_strong_model_or_human_review: bool = False
    model_tool_name: str = ""
    provider_name: str = ""
    model_name: str = ""
    route_summary: str = ""
    prompt_pack_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass
class PastedStrongModelAnswer:
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
    composer_name: str = "pasted_strong_model"
    provider_call: bool = False
    notebooklm_call: bool = False
    answer_kind: str = "pasted_strong_model_answer"
    final_answer: bool = True
    requires_strong_model_or_human_review: bool = False
    model_tool_name: str = ""
    route_summary: str = "Manual paste-back by user"
    prompt_pack_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    pasted_back_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, str] = field(default_factory=dict)


def stable_answer_draft_id(pack: RAGEvidencePack) -> str:
    citation_payload = "|".join(item.citation_id + item.evidence_id for item in pack.items)
    raw = f"{pack.pack_id}:{pack.query}:{pack.privacy_mode}:{pack.insufficient_evidence}:{citation_payload}"
    return "ANS-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()


def compose_local_answer(pack: RAGEvidencePack, max_items: int = 5, mode: str = "local_evidence_draft") -> LocalAnswerDraft | FinalOwnerAnswer:
    if mode == "final_owner_answer":
        return compose_final_owner_answer(pack, max_items=max_items)
    if mode != "local_evidence_draft":
        raise ValueError(f"Unsupported answer composition mode: {mode}")

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
        
    warnings.append("This is a local evidence draft, not a final model answer.")
    if getattr(pack, "metadata_only_evidence_count", 0) > 0 and getattr(pack, "content_evidence_count", 0) == 0:
        warnings.append("Only metadata was found; document content was not extracted.")

    # Filter items to only include real content evidence
    valid_items = []
    excluded_metadata_items = []
    for item in pack.items:
        if item.metadata.get("_is_metadata_only") == "True":
            excluded_metadata_items.append(item)
        else:
            valid_items.append(item)

    citation_ids = [item.citation_id for item in valid_items[:max_items]]
    evidence_ids = [item.evidence_id for item in valid_items[:max_items]]

    lines = [
        f"Local draft for: {pack.query}",
        f"Confidence: {pack.confidence_label}",
    ]
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in warnings)

    if not valid_items:
        lines.append("No extracted content evidence was available, so no factual answer is drafted.")
        if excluded_metadata_items:
            lines.append("Note: Only file metadata was retrieved. Document content extraction may be unsupported.")
        final_answer_text = "\n".join(lines)
    else:
        # Use citation_answer module for structured composition
        refs = build_citation_index(valid_items[:max_items])
        
        # Build initial draft answer combining warnings
        draft_lines = [
            f"Local draft for: {pack.query}",
            f"Confidence: {pack.confidence_label}",
        ]
        if warnings:
            draft_lines.append("Warnings:")
            draft_lines.extend(f"- {warning}" for warning in warnings)
        
        draft_lines.append("Evidence-grounded points:")
        for ref in refs:
            draft_lines.append(f"- {ref.ref_id} {ref.snippet}")
            
        if excluded_metadata_items:
            draft_lines.append(f"\n(Excluded {len(excluded_metadata_items)} metadata-only results from draft.)")
        draft_lines.append("Use only the cited points above; verify before taking action.")
        
        # Infer answer type based on evidence content roughly
        answer_type = "general"
        if any(f in ref.file_type.lower() for ref in refs for f in ["html", "png", "jpg"]):
            answer_type = "screenshot"
        elif any(f in ref.file_type.lower() for ref in refs for f in ["pdf", "pptx"]):
            answer_type = "pdf"
            
        final_answer_text = compose_citation_first_answer(
            question=pack.query,
            refs=refs,
            draft_answer="\n".join(draft_lines),
            answer_type=answer_type
        )
        citation_ids = [ref.ref_id for ref in refs]

    return LocalAnswerDraft(
        draft_id=stable_answer_draft_id(pack),
        pack_id=pack.pack_id,
        query=pack.query,
        answer_text=final_answer_text,
        citation_ids=citation_ids,
        evidence_ids=evidence_ids,
        privacy_mode=pack.privacy_mode,
        allowed_external=pack.allowed_external,
        insufficient_evidence=pack.insufficient_evidence,
        confidence_label=pack.confidence_label,
        warnings=warnings,
        answer_kind="local_evidence_draft",
        final_answer=False,
        requires_strong_model_or_human_review=True,
    )


def local_answer_draft_to_dict(draft: LocalAnswerDraft) -> Dict[str, Any]:
    return asdict(draft)

def compose_answer(pack: RAGEvidencePack, mode: str = "final_owner_answer", max_items: int = 5) -> LocalAnswerDraft | FinalOwnerAnswer:
    if mode == "final_owner_answer":
        return compose_final_owner_answer(pack, max_items=max_items)
    return compose_local_answer(pack, max_items=max_items, mode="local_evidence_draft")


def strong_answer_to_dict(draft: StrongModelAnswer | PastedStrongModelAnswer) -> Dict[str, Any]:
    return asdict(draft)


def answer_to_dict(answer: LocalAnswerDraft | FinalOwnerAnswer | StrongModelAnswer | PastedStrongModelAnswer) -> Dict[str, Any]:
    if isinstance(answer, FinalOwnerAnswer):
        return final_owner_answer_to_dict(answer)
    return asdict(answer)
