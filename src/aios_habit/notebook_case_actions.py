import uuid
from datetime import datetime
from pathlib import Path
from aios_habit.case_models import Case, EvidenceItem
from aios_habit.case_store import save_case, save_evidence


def _short_text(value: str, limit: int) -> str:
    cleaned = " ".join(str(value or "").split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "…"


def _safe_answer_summary(answer_text: str) -> str:
    """Keep the answer summary but exclude the source-excerpt section."""
    text = str(answer_text or "")
    for marker in ("Điều có bằng chứng / Confirmed by source:", "Nguồn đã dùng"):
        if marker in text:
            text = text.split(marker, 1)[0]
    return _short_text(text, 500) or "AIOS đã tạo câu trả lời cục bộ từ Sổ tri thức."


def create_case_draft_from_qa_answer(
    question: str,
    answer: dict,
    notebook_name: str,
    notebook_id: str,
    workspace_id: str,
) -> dict:
    """Persist a local-only draft Case and EvidenceItems from one Q&A result."""
    question_clean = _short_text(question, 500)
    if not question_clean:
        raise ValueError("Câu hỏi không được để trống.")

    answer = answer or {}
    source_refs = list(answer.get("source_refs") or [])
    next_checks = [
        _short_text(item, 300)
        for item in answer.get("next_checks") or []
        if str(item or "").strip()
    ]
    insufficient = _short_text(
        answer.get("not_found_or_insufficient_evidence")
        or "Chưa xác định được phần thiếu bằng chứng; cần kiểm tra lại nguồn trước khi kết luận.",
        600,
    )
    confidence = _short_text(answer.get("confidence_level") or "unknown", 30)
    source_origin = "mom_official_local" if notebook_id == "mom" else "knowledge_notebook"

    case_id = f"CASE-{str(uuid.uuid4())[:8].upper()}"
    title = f"Điều tra từ Sổ tri thức: {_short_text(question_clean, 90)}"
    current_situation = "\n\n".join([
        f"**Nguồn khởi tạo:** Hỏi đáp trong Sổ tri thức “{_short_text(notebook_name, 120)}”",
        f"**Câu hỏi:** {question_clean}",
        f"**Tóm tắt câu trả lời cục bộ:** {_safe_answer_summary(answer.get('answer_text', ''))}",
        f"**Điểm chưa đủ bằng chứng:** {insufficient}",
        f"**Mức tin cậy:** {confidence}. Cần người dùng kiểm tra trước khi xác nhận.",
    ])

    evidence_ids = []
    case_sources = []
    for index, ref in enumerate(source_refs, 1):
        relative_path = _short_text(ref.get("relative_path") or ref.get("source_file") or "Nguồn chưa đặt tên", 500)
        source_id = _short_text(ref.get("chunk_id") or ref.get("source_id") or "", 120)
        source_path = relative_path + (f"#{source_id}" if source_id else "")
        filename = Path(relative_path).name or relative_path
        evidence_id = f"EVID-{str(uuid.uuid4())[:8].upper()}"
        evidence = EvidenceItem(
            evidence_id=evidence_id,
            case_id=case_id,
            source_type=_short_text(ref.get("file_type") or "document", 40),
            source_path=source_path,
            title=f"Nguồn {index}: {_short_text(filename, 120)}",
            extracted_text=f"Nguồn tham chiếu từ câu trả lời trong Sổ tri thức “{_short_text(notebook_name, 120)}”.",
            structured_summary=f"Mức tin cậy câu trả lời: {confidence}; cần kiểm tra nguồn gốc trước khi xác nhận.",
            confidence=confidence,
            privacy_level="local_only",
            review_status="raw",
            source_origin=source_origin,
            verification_status="draft",
        )
        save_evidence(evidence)
        evidence_ids.append(evidence_id)
        case_sources.append(source_path)

    new_case = Case(
        case_id=case_id,
        title=title,
        status="open",
        priority="normal",
        current_situation=current_situation,
        sources=case_sources,
        evidence_items=evidence_ids,
        next_actions=next_checks,
        privacy_level="local_only",
        workspace_id=workspace_id,
        linked_notebook_ids=[notebook_id] if notebook_id else [],
        source_origin=source_origin,
        verification_status="draft",
        updated_at=datetime.now().isoformat(),
    )
    save_case(new_case)
    return {
        "case_id": case_id,
        "title": title,
        "evidence_count": len(evidence_ids),
        "case": new_case,
    }

def create_case_from_investigation_import(import_record, workspace_id: str) -> dict:
    # Handle both object and dict
    if hasattr(import_record, "title"):
        title = import_record.title
        parsed_json = import_record.parsed_json or {}
        notebook_id = import_record.notebook_id
    else:
        title = import_record.get("title", "NotebookLM Import")
        parsed_json = import_record.get("parsed_json", {}) or {}
        notebook_id = import_record.get("notebook_id", "")

    symptoms = parsed_json.get("symptoms", [])
    hypotheses = parsed_json.get("hypotheses", [])
    evidence_to_check = parsed_json.get("evidence_to_check", [])

    situation_lines = []
    if symptoms:
        situation_lines.append("**Triệu chứng:**\n" + "\n".join(f"- {s}" for s in symptoms))
    if hypotheses:
        situation_lines.append("**Giả thuyết:**\n" + "\n".join(f"- {h}" for h in hypotheses))
    if evidence_to_check:
        situation_lines.append("**Bằng chứng cần kiểm tra:**\n" + "\n".join(f"- {e}" for e in evidence_to_check))
    current_situation = "\n\n".join(situation_lines)

    case_id = f"CASE-{str(uuid.uuid4())[:8].upper()}"
    
    # Create Case
    new_case = Case(
        case_id=case_id,
        title=title,
        status="open",
        priority="normal",
        current_situation=current_situation,
        privacy_level="local_only",
        workspace_id=workspace_id,
        linked_notebook_ids=[notebook_id] if notebook_id else [],
        source_origin="notebooklm_import",
        verification_status="draft"
    )
    
    evidence_ids = []
    # Create evidence items
    for item in evidence_to_check:
        if not item or not str(item).strip():
            continue
        ev_id = f"EVID-{str(uuid.uuid4())[:8].upper()}"
        evidence = EvidenceItem(
            evidence_id=ev_id,
            case_id=case_id,
            source_type="note",
            source_path="",
            title=str(item)[:60] + "..." if len(str(item)) > 60 else str(item),
            extracted_text=str(item),
            privacy_level="local_only",
            review_status="raw",
            source_origin="notebooklm_import",
            verification_status="draft"
        )
        save_evidence(evidence)
        evidence_ids.append(ev_id)
        
    new_case.evidence_items = evidence_ids
    save_case(new_case)
    
    return {
        "case_id": case_id,
        "evidence_count": len(evidence_ids)
    }
