from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from aios_habit.real_doc_inventory import MOM_RUNTIME_DIR, ensure_mom_runtime_dir

BENCHMARK_RECORDS_FILE = MOM_RUNTIME_DIR / "benchmark_records.jsonl"
NOTEBOOK_TITLE = "Production History Registration System and Process Specification Interface"
NOTEBOOK_URL = "https://notebooklm.google.com/notebook/b4a708d1-c613-436d-ac55-2923c1e43b46"


@dataclass
class BenchmarkScores:
    source_traceability: int = 0
    answer_completeness: int = 0
    hallucination_risk: int = 0
    actionability: int = 0
    vietnamese_clarity: int = 0
    evidence_alignment: int = 0


@dataclass
class MomBenchmarkRecord:
    question_id: str
    question: str
    aios_answer_summary: str
    aios_source_refs: list[dict[str, Any]]
    notebooklm_answer_summary: str = ""
    notebooklm_query_status: str = "manual_required"  # success, failed, manual_required
    comparison_scores: dict[str, int] = field(default_factory=dict)
    winner: str = "Inconclusive"  # AIOS, NotebookLM, Tie, Inconclusive
    notes: str = ""
    privacy_level: str = "local_only"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    record_id: str = field(default_factory=lambda: f"MOM-BENCH-{uuid.uuid4().hex[:8].upper()}")


def _clamp_score(value: int) -> int:
    return max(0, min(5, int(value)))


def compare_aios_notebooklm(
    question: str,
    aios_source_refs: list[dict[str, Any]],
    aios_answer_summary: str = "",
    notebooklm_answer_summary: str = "",
    notebooklm_query_status: str = "manual_required",
) -> tuple[dict[str, int], str, str]:
    source_count = len(aios_source_refs)
    has_notebook_answer = bool(notebooklm_answer_summary.strip()) and notebooklm_query_status == "success"

    scores = {
        "source_traceability": _clamp_score(5 if source_count >= 2 else 3 if source_count == 1 else 0),
        "answer_completeness": _clamp_score(3 if aios_answer_summary.strip() else 1 if source_count else 0),
        "hallucination_risk": _clamp_score(5 if source_count and "chưa đủ" in aios_answer_summary.lower() else 4 if source_count else 2),
        "actionability": _clamp_score(4 if "next" in aios_answer_summary.lower() or "kiểm" in aios_answer_summary.lower() else 2 if source_count else 0),
        "vietnamese_clarity": _clamp_score(4 if aios_answer_summary.strip() else 0),
        "evidence_alignment": _clamp_score(5 if source_count else 0),
    }

    if not has_notebook_answer:
        return scores, "Inconclusive", "NotebookLM query chưa thành công; chỉ đánh giá được phía AIOS."

    aios_total = sum(scores.values())
    notebook_bonus = 0
    if any(token in notebooklm_answer_summary.lower() for token in ("nguồn", "source", "trích", "citation")):
        notebook_bonus += 3
    if any(token in notebooklm_answer_summary.lower() for token in ("không đủ", "chưa đủ", "not enough")):
        notebook_bonus += 2
    notebook_total = 15 + notebook_bonus

    if abs(aios_total - notebook_total) <= 2:
        winner = "Tie"
    elif aios_total > notebook_total:
        winner = "AIOS"
    else:
        winner = "NotebookLM"
    return scores, winner, "NotebookLM là comparator, không phải ground truth; ground truth vẫn là MOM source refs."


def build_benchmark_record(
    question_id: str,
    question: str,
    aios_source_refs: list[dict[str, Any]],
    aios_answer_summary: str = "",
    notebooklm_answer_summary: str = "",
    notebooklm_query_status: str = "manual_required",
    notes: str = "",
) -> MomBenchmarkRecord:
    scores, winner, auto_notes = compare_aios_notebooklm(
        question=question,
        aios_source_refs=aios_source_refs,
        aios_answer_summary=aios_answer_summary,
        notebooklm_answer_summary=notebooklm_answer_summary,
        notebooklm_query_status=notebooklm_query_status,
    )
    merged_notes = notes.strip() or auto_notes
    if notes.strip() and auto_notes:
        merged_notes = f"{notes.strip()} | {auto_notes}"
    return MomBenchmarkRecord(
        question_id=question_id,
        question=question,
        aios_answer_summary=aios_answer_summary,
        aios_source_refs=aios_source_refs,
        notebooklm_answer_summary=notebooklm_answer_summary,
        notebooklm_query_status=notebooklm_query_status,
        comparison_scores=scores,
        winner=winner,
        notes=merged_notes,
    )


def save_benchmark_record(record: MomBenchmarkRecord) -> Path:
    ensure_mom_runtime_dir()
    with BENCHMARK_RECORDS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    return BENCHMARK_RECORDS_FILE


def load_benchmark_records(path: str | Path = BENCHMARK_RECORDS_FILE, limit: Optional[int] = None) -> list[MomBenchmarkRecord]:
    p = Path(path)
    if not p.exists():
        return []
    records: list[MomBenchmarkRecord] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(MomBenchmarkRecord(**json.loads(line)))
                except Exception:
                    continue
    records.reverse()
    return records[:limit] if limit else records


def notebooklm_manual_required_record(question_id: str, question: str, aios_source_refs: list[dict[str, Any]], aios_answer_summary: str) -> MomBenchmarkRecord:
    return build_benchmark_record(
        question_id=question_id,
        question=question,
        aios_source_refs=aios_source_refs,
        aios_answer_summary=aios_answer_summary,
        notebooklm_query_status="manual_required",
        notes="Streamlit app không gọi trực tiếp NotebookLM MCP; Antigravity agent/browser cần query notebook hiện có.",
    )


def _redact_snippet(text: str, max_len: int = 180) -> str:
    cleaned = " ".join(text.replace("\n", " ").split())
    return cleaned[:max_len].rstrip()


_GENERIC_QUERY_TERMS = {
    "mom", "docs", "doc", "document", "documents", "production", "history", "result",
    "registration", "system", "interface", "process", "overview", "evidence", "source",
    "refs", "safe", "concise", "topic", "unsupported", "not", "in", "input", "output",
    "fields", "field", "interaction", "compare", "specification", "mapping", "flow",
    "confirmation", "approval", "points", "review", "image", "operator",
}

_INTENT_QUERY_TERMS = {
    "input", "output", "fields", "field", "interaction", "compare", "specification",
    "mapping", "flow", "confirmation", "approval", "points", "review", "image", "operator",
}

_UNSUPPORTED_STRICT_TERMS = {
    "blockchain", "crypto", "bitcoin", "payroll", "salary", "invoice", "finance",
    "tax", "crm", "sales", "opportunity", "kubernetes", "deployment", "rollback",
    "machinelearning", "prediction", "model", "accuracy",
}


def _question_specific_terms(question: str) -> set[str]:
    terms = set()
    for token in question.lower().replace("/", " ").replace("_", " ").split():
        clean = "".join(ch for ch in token if ch.isalnum())
        if len(clean) >= 5 and clean not in _GENERIC_QUERY_TERMS:
            terms.add(clean)
    return terms


def generate_mom_grounded_answer(question: str, search_results: list[Any], *, max_sources: int = 5) -> dict[str, Any]:
    """Generate a deterministic local-only answer from MOM search hits.

    The function intentionally avoids cloud/LLM calls. It produces short,
    evidence-grounded sections and source refs suitable for benchmark scoring,
    while detailed confidential text remains in ignored runtime records only.
    """
    specific_terms = _question_specific_terms(question)
    raw_hits = [hit for hit in search_results[:max_sources] if getattr(hit, "score", 0) > 0]
    strict_unsupported = bool(_UNSUPPORTED_STRICT_TERMS.intersection(specific_terms))
    broadened = False
    if strict_unsupported:
        usable = []
    elif specific_terms:
        usable = [
            hit for hit in raw_hits
            if specific_terms.intersection(set(hit.matched_terms))
            or any(term in hit.chunk.relative_path.lower() or term in hit.chunk.preview.lower() for term in specific_terms)
        ]
        if not usable and raw_hits:
            # Safe fallback: broad business-intent terms may still retrieve useful refs,
            # but these refs must never create high confidence.
            usable = raw_hits[: min(max_sources, 3)]
            broadened = True
    else:
        usable = raw_hits
    source_refs: list[dict[str, Any]] = []
    confirmed: list[str] = []
    for index, hit in enumerate(usable, 1):
        chunk = hit.chunk
        source_refs.append({
            "chunk_id": chunk.chunk_id,
            "relative_path": chunk.relative_path,
            "source_file": chunk.source_file,
            "sheet": chunk.sheet,
            "section": chunk.section,
            "score": hit.score,
            "privacy_level": chunk.privacy_level,
            "file_type": chunk.file_type,
            "page": chunk.page,
            "slide": chunk.slide,
            "extractor_name": chunk.extractor_name,
            "extraction_status": chunk.extraction_status,
            "ocr_engine": chunk.ocr_engine,
        })
        label_parts = [chunk.relative_path, chunk.chunk_id]
        if chunk.sheet:
            label_parts.append(f"sheet={chunk.sheet}")
        if chunk.page is not None:
            label_parts.append(f"page={chunk.page}")
        if chunk.slide is not None:
            label_parts.append(f"slide={chunk.slide}")
        confirmed.append(
            f"{index}. Nguồn {' | '.join(str(p) for p in label_parts if p)} khớp các thuật ngữ {', '.join(hit.matched_terms[:5]) or 'liên quan'}; trích yếu: {_redact_snippet(chunk.preview)}"
        )

    files = sorted({ref["relative_path"] for ref in source_refs})
    file_types = sorted({ref["file_type"] for ref in source_refs})
    has_ocr = any(str(ref.get("extraction_status", "")).startswith("ocr") for ref in source_refs)
    source_coverage = {
        "source_count": len(source_refs),
        "files": files,
        "file_types": file_types,
        "has_ocr": has_ocr,
    }

    if not source_refs:
        confidence = "insufficient"
        not_found = "Không đủ bằng chứng trong MOM local index cho câu hỏi này."
        next_checks = [
            "Kiểm tra lại từ khóa tiếng Nhật/Anh/Việt trong tài liệu gốc.",
            "Xác định đúng module/process trước khi kết luận.",
        ]
        confirmed_text = "Không có điểm nào được xác nhận bằng source refs."
    else:
        confidence = "medium" if broadened else "high" if len(source_refs) >= 3 and len(files) >= 2 else "medium" if len(source_refs) >= 2 else "low"
        not_found = "Không kết luận các field/process không xuất hiện trong nguồn trích dẫn; mọi phần ngoài phạm vi nguồn được xem là chưa đủ bằng chứng."
        next_checks = [
            f"Mở lại {files[0]} để kiểm tra ngữ cảnh đầy đủ quanh chunk được trích dẫn.",
            "Đối chiếu thêm sheet/page/slide liên quan nếu cần quyết định nghiệp vụ.",
        ]
        confirmed_text = "\n".join(confirmed)

    confidence_note = "Refs được lọc theo thuật ngữ đặc thù của câu hỏi." if not broadened else "Refs lấy từ fallback broadened nên chỉ dùng mức tin cậy medium/low, không kết luận vượt nguồn."
    answer_text = (
        f"Tóm tắt trả lời / Answer summary:\nAIOS tìm thấy {len(source_refs)} nguồn cục bộ liên quan; mức tin cậy={confidence}. {confidence_note}\n\n"
        f"Điều có bằng chứng / Confirmed by source:\n{confirmed_text}\n\n"
        f"Điểm chưa đủ bằng chứng / Not found / insufficient evidence:\n{not_found}\n\n"
        f"Cần kiểm tra tiếp / Next checks:\n- " + "\n- ".join(next_checks) + "\n\n"
        f"Source coverage:\n{len(source_refs)} nguồn; loại file={', '.join(file_types) if file_types else 'none'}; OCR={'yes' if has_ocr else 'no'}; chỉ cục bộ."
    )
    return {
        "question": question,
        "answer_text": answer_text,
        "confirmed_by_source": confirmed,
        "not_found_or_insufficient_evidence": not_found,
        "next_checks": next_checks,
        "source_refs": source_refs,
        "source_coverage": source_coverage,
        "confidence_level": confidence,
        "confidence_explanation": confidence_note,
        "broadened_fallback": broadened,
        "privacy_level": "local_only",
        "prompt_only": False,
    }


def score_mom_real_answer(answer: dict[str, Any], *, valid_source_refs: bool = True) -> dict[str, int]:
    refs = answer.get("source_refs") or []
    text = str(answer.get("answer_text") or "")
    confidence = str(answer.get("confidence_level") or "")
    insufficient = confidence == "insufficient" or not refs
    has_sections = all(token in text.lower() for token in ("confirmed by source", "not found", "next checks", "source coverage"))
    confirmed = answer.get("confirmed_by_source") or []
    next_checks = answer.get("next_checks") or []
    files = {ref.get("relative_path") for ref in refs}

    if not text.strip():
        return {"source_traceability": 0, "evidence_alignment": 0, "completeness": 0, "unknown_handling": 0, "actionability": 0, "clarity": 0, "hallucination_control": 0}

    has_confirmed = bool(confirmed)
    source_traceability = 5 if refs and valid_source_refs else 0
    evidence_alignment = 5 if refs and valid_source_refs and has_confirmed and not (confidence == "high" and len(refs) < 2) else 2 if refs and valid_source_refs else 0
    completeness = 5 if has_sections and len(refs) >= 3 and len(files) >= 2 and has_confirmed else 3 if has_sections and refs and has_confirmed else 1 if has_sections else 0
    unknown_handling = 5 if "chưa đủ bằng chứng" in text.lower() or "không đủ bằng chứng" in text.lower() or "insufficient evidence" in text.lower() else 3 if refs else 5
    actionability = 5 if has_confirmed and len(next_checks) >= 2 and "kiểm" in text.lower() else 2 if next_checks else 0
    clarity = 5 if has_sections and len(text) > 120 else 3 if text.strip() else 0
    hallucination_control = 5 if not (confidence == "high" and insufficient) and valid_source_refs and (has_confirmed or insufficient) else 1
    if confidence == "high" and insufficient:
        hallucination_control = 0
        evidence_alignment = min(evidence_alignment, 1)
    return {
        "source_traceability": source_traceability,
        "evidence_alignment": evidence_alignment,
        "completeness": completeness,
        "unknown_handling": unknown_handling,
        "actionability": actionability,
        "clarity": clarity,
        "hallucination_control": hallucination_control,
    }


def weighted_real_answer_score(scores: dict[str, int]) -> float:
    weights = {
        "source_traceability": 20,
        "evidence_alignment": 25,
        "completeness": 20,
        "unknown_handling": 10,
        "actionability": 10,
        "clarity": 5,
        "hallucination_control": 10,
    }
    return round(sum((scores.get(key, 0) / 5) * weight for key, weight in weights.items()), 2)
