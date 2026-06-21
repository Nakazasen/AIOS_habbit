import uuid
from datetime import datetime
from aios_habit.case_models import Case, EvidenceItem
from aios_habit.case_store import save_case, save_evidence

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
