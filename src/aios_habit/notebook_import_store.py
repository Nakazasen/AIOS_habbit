import json
import inspect
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any

LOCAL_CASES_DIR = Path.cwd() / "local_cases"
IMPORTS_FILE = LOCAL_CASES_DIR / "notebook_bridge_imports.jsonl"

@dataclass
class NotebookBridgeImport:
    import_id: str
    notebook_id: str
    workspace_id: str
    import_type: str  # knowledge_graph_json, study_pack_json, case_investigation_json, mermaid_graph
    title: str
    raw_text: str
    parsed_json: Dict[str, Any]
    mermaid_text: str
    source: str = "notebooklm_bridge"
    privacy_level: str = "local_only"
    status: str = "draft"  # draft, reviewed, confirmed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

def load_bridge_imports(notebook_id: Optional[str] = None) -> List[NotebookBridgeImport]:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    if not IMPORTS_FILE.exists():
        return []
    import_fields = {p.name for p in inspect.signature(NotebookBridgeImport).parameters.values()}
    records = []
    with open(IMPORTS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    filtered_data = {k: v for k, v in data.items() if k in import_fields}
                    if "privacy_level" not in filtered_data:
                        filtered_data["privacy_level"] = "local_only"
                    if "status" not in filtered_data:
                        filtered_data["status"] = "draft"
                    record = NotebookBridgeImport(**filtered_data)
                    if notebook_id is None or record.notebook_id == notebook_id:
                        records.append(record)
                except Exception:
                    pass
    return records

def save_bridge_import(import_record: NotebookBridgeImport) -> NotebookBridgeImport:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    records = load_bridge_imports()
    found = False
    for i, r in enumerate(records):
        if r.import_id == import_record.import_id:
            import_record.updated_at = datetime.now().isoformat()
            records[i] = import_record
            found = True
            break
    if not found:
        records.append(import_record)
        
    with open(IMPORTS_FILE, 'w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + '\n')
    return import_record

def get_bridge_import(import_id: str) -> Optional[NotebookBridgeImport]:
    records = load_bridge_imports()
    for r in records:
        if r.import_id == import_id:
            return r
    return None

def delete_bridge_import(import_id: str) -> bool:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    records = load_bridge_imports()
    orig_len = len(records)
    records = [r for r in records if r.import_id != import_id]
    if len(records) == orig_len:
        return False
    with open(IMPORTS_FILE, 'w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + '\n')
    return True
