import json
import os
from pathlib import Path
from dataclasses import asdict
from typing import List

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
    init_store()
    cases = []
    with open(CASES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    cases.append(Case(**data))
                except Exception:
                    pass
    return cases

def load_evidence() -> List[EvidenceItem]:
    init_store()
    items = []
    with open(EVIDENCE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    items.append(EvidenceItem(**data))
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
    from .case_models import Case, EvidenceItem
    from .case_ingest import ingest_csv, ingest_excel
    
    # 1. Create and save case
    case_id = f"CASE-{str(uuid.uuid4())[:8].upper()}"
    case = Case(
        case_id=case_id,
        title=title.strip(),
        current_situation=situation.strip(),
        priority=priority,
        privacy_level=privacy,
        status="open",
        updated_at=datetime.now().isoformat()
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
            privacy_level=privacy
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
            privacy_level=privacy
        )
        save_evidence(ev)
        evidences_added += 1
        
    # 4. Add Excel/CSV
    if excel_csv_file_name and excel_csv_content_bytes:
        ev_id = f"EVD-{str(uuid.uuid4())[:8].upper()}"
        case_assets_dir = get_case_assets_dir(case_id)
        from .case_ingest import safe_asset_filename
        safe_name = safe_asset_filename(excel_csv_file_name)
        target_path = case_assets_dir / safe_name
        target_path.write_bytes(excel_csv_content_bytes)
        
        path_str = str(target_path)
        if excel_csv_file_name.lower().endswith(".csv"):
            ev = ingest_csv(path_str, case_id, ev_id, excel_csv_file_name)
        else:
            ev = ingest_excel(path_str, case_id, ev_id, excel_csv_file_name)
        ev.privacy_level = privacy
        save_evidence(ev)
        evidences_added += 1
        
    # 5. Add Image
    if img_file_name and img_content_bytes:
        ev_id = f"EVD-{str(uuid.uuid4())[:8].upper()}"
        case_assets_dir = get_case_assets_dir(case_id)
        from .case_ingest import safe_asset_filename
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
            privacy_level=privacy
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

