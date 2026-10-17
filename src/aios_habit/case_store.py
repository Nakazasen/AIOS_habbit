import json
import os
from pathlib import Path
from dataclasses import asdict
from typing import List, Optional, Dict, Any

from .case_models import Case, EvidenceItem


LOCAL_CASES_DIR = Path.cwd() / "local_cases"
CASES_FILE = LOCAL_CASES_DIR / "cases.jsonl"
EVIDENCE_FILE = LOCAL_CASES_DIR / "evidence.jsonl"
ASSETS_DIR = LOCAL_CASES_DIR / "assets"

def init_store():
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    if not CASES_FILE.exists():
        CASES_FILE.touch()
    if not EVIDENCE_FILE.exists():
        EVIDENCE_FILE.touch()

def load_cases() -> List[Case]:
    import inspect
    init_store()
    cases = []
    case_fields = {p.name for p in inspect.signature(Case).parameters.values()}
    with open(CASES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    filtered_data = {k: v for k, v in data.items() if k in case_fields}
                    cases.append(Case(**filtered_data))
                except Exception:
                    pass
    return cases

def load_cases_for_workspace(workspace_id: str) -> List[Case]:
    return [c for c in load_cases() if c.workspace_id == workspace_id]

def load_evidence() -> List[EvidenceItem]:
    import inspect
    init_store()
    items = []
    evidence_fields = {p.name for p in inspect.signature(EvidenceItem).parameters.values()}
    with open(EVIDENCE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    filtered_data = {k: v for k, v in data.items() if k in evidence_fields}
                    items.append(EvidenceItem(**filtered_data))
                except Exception:
                    pass
    return items

def save_case(case: Case):
    init_store()
    cases = load_cases()
    found = False
    for i, c in enumerate(cases):
        if c.case_id == case.case_id:
            cases[i] = case
            found = True
            break
    if not found:
        cases.append(case)

    with open(CASES_FILE, 'w', encoding='utf-8') as f:
        for c in cases:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + '\n')

def save_evidence(evidence: EvidenceItem):
    init_store()
    items = load_evidence()
    found = False
    for i, e in enumerate(items):
        if e.evidence_id == evidence.evidence_id:
            items[i] = evidence
            found = True
            break
    if not found:
        items.append(evidence)

    with open(EVIDENCE_FILE, 'w', encoding='utf-8') as f:
        for e in items:
            f.write(json.dumps(asdict(e), ensure_ascii=False) + '\n')

def get_case_assets_dir(case_id: str) -> Path:
    init_store()
    p = ASSETS_DIR / case_id
    p.mkdir(parents=True, exist_ok=True)
    return p

def create_quick_case_with_evidence(
    title: str,
    situation: str,
    priority: str,
    privacy: str,
    chat_log: str = "",
    notes: str = "",
    excel_csv_file_name: str = "",
    excel_csv_content_bytes: bytes = b"",
    img_file_name: str = "",
    img_content_bytes: bytes = b""
) -> dict:
    import uuid
    from datetime import datetime
    import pandas as pd
    from .case_models import Case, EvidenceItem

    def _ingest_excel(file_path: str, case_id: str, evidence_id: str, original_name: str) -> EvidenceItem:
        try:
            xls = pd.ExcelFile(file_path)
            sheets = xls.sheet_names
            summary = f"Excel Workbook: {original_name}\nSheets: {', '.join(sheets)}\n"
            for sheet in sheets:
                df = pd.read_excel(xls, sheet_name=sheet, nrows=5)
                summary += f"\nSheet '{sheet}' Preview (cols={len(df.columns)}):\n"
                summary += df.to_string(index=False) + "\n"
            return EvidenceItem(evidence_id=evidence_id, case_id=case_id, source_type="excel", source_path=file_path, title=f"Excel Data: {original_name}", structured_summary=summary, extracted_text=summary)
        except Exception as e:
            return EvidenceItem(evidence_id=evidence_id, case_id=case_id, source_type="excel", source_path=file_path, title=f"Excel Data: {original_name}", extracted_text=f"Error reading Excel: {e}", structured_summary="Failed to parse.")

    def _ingest_csv(file_path: str, case_id: str, evidence_id: str, original_name: str) -> EvidenceItem:
        try:
            df = pd.read_csv(file_path, nrows=5)
            summary = f"CSV File: {original_name}\nCols: {len(df.columns)}\nPreview:\n" + df.to_string(index=False)
            return EvidenceItem(evidence_id=evidence_id, case_id=case_id, source_type="csv", source_path=file_path, title=f"CSV Data: {original_name}", structured_summary=summary, extracted_text=summary)
        except Exception as e:
            return EvidenceItem(evidence_id=evidence_id, case_id=case_id, source_type="csv", source_path=file_path, title=f"CSV Data: {original_name}", extracted_text=f"Error reading CSV: {e}", structured_summary="Failed to parse.")

    # 1. Create and save case
    case_id = f"CASE-{str(uuid.uuid4())[:8].upper()}"
    case = Case(
        case_id=case_id,
        title=title.strip(),
        current_situation=situation.strip(),
        priority=priority,
        privacy_level=privacy,
        status="open",
        updated_at=datetime.now().isoformat(),
        source_origin="manual",
        verification_status="draft"
    )
    save_case(case)

    evidences_added = 0

    # 2. Add Chat/Log evidence
    if chat_log.strip():
        ev_id = f"EVD-{str(uuid.uuid4())[:8].upper()}"
        ev = EvidenceItem(
            evidence_id=ev_id,
            case_id=case_id,
            source_type="chat_paste",
            source_path="clipboard",
            title="Đoạn Chat/Log dán nhanh",
            extracted_text=chat_log.strip(),
            privacy_level=privacy,
            source_origin="manual",
            verification_status="draft"
        )
        save_evidence(ev)
        case.timeline_events.append({"date": datetime.now().isoformat(), "event": "Đã thêm nhật ký từ nhập nhanh."})
        evidences_added += 1

    # 3. Add Manual Notes
    if notes.strip():
        ev_id = f"EVD-{str(uuid.uuid4())[:8].upper()}"
        ev = EvidenceItem(
            evidence_id=ev_id,
            case_id=case_id,
            source_type="note",
            source_path="manual",
            title="Ghi chú nhập nhanh",
            extracted_text=notes.strip(),
            privacy_level=privacy,
            source_origin="manual",
            verification_status="draft"
        )
        save_evidence(ev)
        evidences_added += 1

    # 4. Add Excel/CSV
    if excel_csv_file_name and excel_csv_content_bytes:
        ev_id = f"EVD-{str(uuid.uuid4())[:8].upper()}"
        case_assets_dir = get_case_assets_dir(case_id)
        from .source_ingest import safe_asset_filename
        safe_name = safe_asset_filename(excel_csv_file_name)
        target_path = case_assets_dir / safe_name
        target_path.write_bytes(excel_csv_content_bytes)

        path_str = str(target_path)
        if excel_csv_file_name.lower().endswith(".csv"):
            ev = _ingest_csv(path_str, case_id, ev_id, excel_csv_file_name)
        else:
            ev = _ingest_excel(path_str, case_id, ev_id, excel_csv_file_name)
        ev.privacy_level = privacy
        ev.source_origin = "manual"
        ev.verification_status = "draft"
        save_evidence(ev)
        evidences_added += 1

    # 5. Add Image
    if img_file_name and img_content_bytes:
        ev_id = f"EVD-{str(uuid.uuid4())[:8].upper()}"
        case_assets_dir = get_case_assets_dir(case_id)
        from .source_ingest import safe_asset_filename
        safe_name = safe_asset_filename(img_file_name)
        target_path = case_assets_dir / safe_name
        target_path.write_bytes(img_content_bytes)

        path_str = str(target_path)
        ev = EvidenceItem(
            evidence_id=ev_id,
            case_id=case_id,
            source_type="screenshot",
            source_path=path_str,
            title=f"Ảnh chụp: {img_file_name}",
            extracted_text="Hình ảnh tải lên từ nhập nhanh",
            privacy_level=privacy,
            source_origin="manual",
            verification_status="draft"
        )
        save_evidence(ev)
        evidences_added += 1

    if len(case.timeline_events) > 0:
        save_case(case)

    return {
        "case_id": case_id,
        "case": case,
        "evidences_count": evidences_added
    }


class InvestigationClosureBlockedError(ValueError):
    """Raised when closing an investigation case is blocked by the close gate."""

    def __init__(self, message: str, missing_fields: List[str]):
        super().__init__(message)
        self.message = message
        self.missing_fields = missing_fields


_BLANK_PLACEHOLDERS = {
    "",
    "-",
    "--",
    "---",
    "none",
    "null",
    "n/a",
    "na",
    "chua co",
    "chưa có",
    "chua ro",
    "chưa rõ",
    "...",
    "todo",
    "// todo",
    "pass",
}


def is_blank_value(value: Optional[str]) -> bool:
    """Check if value is blank, empty, whitespace, or a placeholder."""
    if value is None:
        return True
    s = str(value).strip().lower()
    return not s or s in _BLANK_PLACEHOLDERS


def close_investigation_case(
    case_id: str,
    actual_cause: str,
    actual_countermeasure: str,
    closed_by: str = "user",
) -> Case:
    """Step 2 Close Gate: Close an investigation case.

    Enforces mandatory actual root cause and actual countermeasure.
    Blocks closing if either field is missing, specifying missing fields.
    When valid, writes results back to local_cases/cases.jsonl without
    touching the knowledge store (library.sqlite / vector store).
    """
    cid = str(case_id or "").strip()
    if not cid:
        raise ValueError("Mã vụ điều tra (case_id) không được để trống.")

    cases = load_cases()
    target_idx = -1
    for i, c in enumerate(cases):
        if c.case_id == cid:
            target_idx = i
            break

    if target_idx < 0:
        raise KeyError(f"Không tìm thấy hồ sơ vụ điều tra '{cid}' trong hệ thống local_cases.")

    case = cases[target_idx]

    # Validate mandatory gate fields
    missing_fields: List[str] = []
    if is_blank_value(actual_cause):
        missing_fields.append("nguyên nhân thật (actual_cause)")
    if is_blank_value(actual_countermeasure):
        missing_fields.append("đối sách thật (actual_countermeasure)")

    if missing_fields:
        missing_str = " và ".join(f"'{f}'" for f in missing_fields)
        msg = (
            f"🚫 **CỔNG CHẶN ĐÓNG VỤ (Bước 2):** Không thể đóng vụ điều tra `{cid}` "
            f"vì chưa nhập {missing_str}. Vui lòng nhập đầy đủ nguyên nhân thật và "
            f"đối sách thật trước khi đóng."
        )
        raise InvestigationClosureBlockedError(msg, missing_fields=missing_fields)

    # Valid: apply closure updates
    from datetime import datetime

    now_iso = datetime.now().isoformat()
    clean_cause = str(actual_cause).strip()
    clean_remedy = str(actual_countermeasure).strip()

    case.status = "resolved"
    case.actual_cause = clean_cause
    case.actual_countermeasure = clean_remedy
    case.outcome = f"Đã giải quyết. Nguyên nhân thật: {clean_cause} | Đối sách thật: {clean_remedy}"
    case.lessons_learned = f"Nguyên nhân cốt lõi: {clean_cause} -> Đối sách phòng ngừa: {clean_remedy}"
    case.closed_at = now_iso
    case.updated_at = now_iso

    case.timeline_events.append({
        "timestamp": now_iso,
        "type": "case_closed",
        "description": f"Đóng vụ điều tra thành công. Nguyên nhân thật: {clean_cause} | Đối sách thật: {clean_remedy}",
        "author": closed_by or "user",
    })

    # Persist case to local_cases/cases.jsonl
    save_case(case)

    # Persist audit record to local_cases/case_closures.jsonl (strictly local_cases)
    closure_audit_file = LOCAL_CASES_DIR / "case_closures.jsonl"
    try:
        audit_record = {
            "case_id": case.case_id,
            "title": case.title,
            "actual_cause": clean_cause,
            "actual_countermeasure": clean_remedy,
            "closed_at": now_iso,
            "closed_by": closed_by or "user",
            "status": case.status,
        }
        with open(closure_audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(audit_record, ensure_ascii=False) + "\n")
    except Exception:
        pass

    return case

