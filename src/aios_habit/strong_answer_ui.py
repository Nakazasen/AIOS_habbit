from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable

from aios_habit.ai_provider_bridge import build_grounded_prompt
from aios_habit.case_models import EvidenceItem
from aios_habit.case_store import save_evidence
from aios_habit.rag_answer_composer import PastedStrongModelAnswer, compose_local_answer, strong_answer_to_dict
from aios_habit.rag_evidence import RAGEvidencePack, build_evidence_pack
from aios_habit.rag_ingest import RAGChunk
from aios_habit.rag_search import create_rag_search_schema, index_rag_chunks, search_rag_chunks
from aios_habit.query_intent import extract_query_intent


@dataclass
class StrongAnswerUIPreparation:
    question: str
    detected_intent: str
    evidence_pack: RAGEvidencePack
    local_draft: Any
    top_evidence_files: list[str]
    metadata_only_warning: str
    evidence_quality: str
    final_answer: bool = False


@dataclass
class StrongPromptExport:
    prompt_text: str
    blocked_direct_provider_call: bool
    privacy_warning: str
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    route_summary: str = "manual_evidence_pack_only"


def _evidence_to_chunks(evidence_items: Iterable[EvidenceItem]) -> list[RAGChunk]:
    chunks: list[RAGChunk] = []
    for index, evidence in enumerate(evidence_items):
        text = (evidence.extracted_text or evidence.structured_summary or "").strip()
        if not text:
            text = f"Metadata-only source record: {evidence.title}. Content was not extracted."
        chunks.append(
            RAGChunk(
                chunk_id=f"{evidence.evidence_id}-C0000",
                document_id=evidence.evidence_id,
                element_ids=[evidence.evidence_id],
                text=text,
                source_title=evidence.title,
                source_path=evidence.source_path,
                relative_path=evidence.title,
                citation_label=evidence.title,
                file_type=evidence.source_type,
                element_types=[evidence.source_type],
                page_numbers=[],
                sheet_names=[],
                slide_numbers=[],
                section_labels=[],
                row_ranges=[],
                cell_ranges=[],
                privacy_mode=evidence.privacy_level,
                chunk_index=index,
            )
        )
    return chunks


def prepare_local_evidence_answer(question: str, evidence_items: Iterable[EvidenceItem], limit: int = 8) -> StrongAnswerUIPreparation:
    if not question.strip():
        raise ValueError("question is required")
    chunks = _evidence_to_chunks(evidence_items)
    conn = sqlite3.connect(":memory:")
    create_rag_search_schema(conn)
    index_rag_chunks(conn, chunks)
    results = search_rag_chunks(conn, question, limit=limit)
    pack = build_evidence_pack(question, results)
    local_draft = compose_local_answer(pack)
    intent = extract_query_intent(question)
    warning = ""
    if pack.metadata_only_evidence_count > 0:
        warning = "Có bằng chứng chỉ là metadata; không coi là nội dung đủ để trả lời cuối."
    return StrongAnswerUIPreparation(
        question=question,
        detected_intent=intent.intent_name if intent else "none",
        evidence_pack=pack,
        local_draft=local_draft,
        top_evidence_files=[item.source_title for item in pack.items[:5]],
        metadata_only_warning=warning,
        evidence_quality=pack.evidence_quality,
        final_answer=False,
    )


def build_strong_answer_prompt_for_ui(question: str, evidence_pack: RAGEvidencePack, local_draft_text: str) -> StrongPromptExport:
    valid_items = [item for item in evidence_pack.items if item.metadata.get("_is_metadata_only") != "True"]
    refs = [{"chunk_id": item.chunk_id, "relative_path": item.relative_path} for item in valid_items[:5]]
    context = "\n\n".join(f"{item.citation_id} {item.text}" for item in valid_items[:5])
    focus_note = ""
    for item in valid_items:
        if item.metadata.get("_focus_note"):
            focus_note = item.metadata["_focus_note"]
            break
    prompt = build_grounded_prompt(
        question=question,
        source_refs=refs,
        deterministic_answer=local_draft_text,
        source_context=context,
        focus_note=focus_note,
    )
    blocked = evidence_pack.privacy_mode == "local_only" or not evidence_pack.allowed_external
    warning = ""
    if blocked:
        warning = "Tự động gọi cloud bị chặn vì dữ liệu local_only. Bạn chỉ nên dùng prompt này nếu đã được phép."
    return StrongPromptExport(
        prompt_text=prompt,
        blocked_direct_provider_call=blocked,
        privacy_warning=warning,
        evidence_refs=refs,
    )


def save_pasted_strong_answer(
    case_id: str,
    question: str,
    answer_text: str,
    model_tool_name: str,
    evidence_pack: RAGEvidencePack,
    route_summary: str = "manual_evidence_pack_only",
) -> PastedStrongModelAnswer:
    if not answer_text.strip():
        raise ValueError("answer_text is required")
    if not model_tool_name.strip():
        raise ValueError("model_tool_name is required")
    valid_items = [item for item in evidence_pack.items if item.metadata.get("_is_metadata_only") != "True"]
    citation_ids = [item.citation_id for item in valid_items[:5]]
    evidence_ids = [item.evidence_id for item in valid_items[:5]]
    final_answer = bool(valid_items and answer_text.strip())
    pasted = PastedStrongModelAnswer(
        draft_id=f"PASTE-{uuid.uuid4().hex[:12].upper()}",
        pack_id=evidence_pack.pack_id,
        query=question,
        answer_text=answer_text.strip(),
        citation_ids=citation_ids,
        evidence_ids=evidence_ids,
        privacy_mode=evidence_pack.privacy_mode,
        allowed_external=evidence_pack.allowed_external,
        insufficient_evidence=evidence_pack.insufficient_evidence,
        confidence_label=evidence_pack.confidence_label,
        warnings=list(evidence_pack.missing_evidence_warnings),
        final_answer=final_answer,
        model_tool_name=model_tool_name.strip(),
        route_summary=route_summary,
        metadata={"evidence_refs": ",".join(evidence_ids), "created_at": datetime.now().isoformat()},
    )
    save_evidence(
        EvidenceItem(
            evidence_id=pasted.draft_id,
            case_id=case_id,
            source_type="pasted_strong_model_answer",
            source_path="manual_paste_back",
            title=f"Câu trả lời AI mạnh - {model_tool_name.strip()}",
            extracted_text=answer_text.strip(),
            structured_summary=str(strong_answer_to_dict(pasted)),
            confidence=pasted.confidence_label,
            privacy_level=evidence_pack.privacy_mode,
            review_status="reviewed" if final_answer else "draft",
            source_origin="manual",
            verification_status="reviewed" if final_answer else "draft",
        )
    )
    return pasted
