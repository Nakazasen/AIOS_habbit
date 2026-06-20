import json
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd
from .case_ingest import safe_asset_filename

LOCAL_CASES_DIR = Path.cwd() / "local_cases"
SOURCES_FILE = LOCAL_CASES_DIR / "sources.jsonl"
NOTEBOOK_ASSETS_DIR = LOCAL_CASES_DIR / "notebook_assets"
NOTEBOOK_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
MAX_PREVIEW_CHARS = 1000

@dataclass
class SourceDocument:
    source_id: str
    notebook_id: str
    filename: str
    original_filename: str
    source_type: str  # pdf, excel, csv, markdown, docx, txt, image, etc.
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    privacy_level: str = "local_only"
    asset_path: str = ""
    preview_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

def init_source_store():
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    NOTEBOOK_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    if not SOURCES_FILE.exists():
        SOURCES_FILE.touch()

def load_sources() -> List[SourceDocument]:
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    if not SOURCES_FILE.exists():
        return []
    sources = []
    with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    sources.append(SourceDocument(**data))
                except Exception:
                    pass
    return sources

def save_source(src: SourceDocument):
    LOCAL_CASES_DIR.mkdir(parents=True, exist_ok=True)
    sources = load_sources()
    found = False
    for i, s in enumerate(sources):
        if s.source_id == src.source_id:
            sources[i] = src
            found = True
            break
    if not found:
        sources.append(src)
    
    with open(SOURCES_FILE, 'w', encoding='utf-8') as f:
        for s in sources:
            f.write(json.dumps(asdict(s), ensure_ascii=False) + '\n')

def get_notebook_assets_dir(notebook_id: str) -> Path:
    if not notebook_id or not NOTEBOOK_ID_PATTERN.fullmatch(notebook_id):
        raise ValueError("Invalid notebook_id: only letters, numbers, underscores, and hyphens are allowed.")

    root = NOTEBOOK_ASSETS_DIR.resolve()
    candidate = (root / notebook_id).resolve()

    if not candidate.is_relative_to(root):
        raise ValueError("Invalid notebook asset path: directory traversal attempt detected.")

    candidate.mkdir(parents=True, exist_ok=True)
    return candidate

def ingest_source_document(
    notebook_id: str,
    original_filename: str,
    file_bytes: bytes,
    title: str,
    description: str = "",
    privacy_level: str = "local_only",
    tags: List[str] = None
) -> SourceDocument:
    import uuid
    init_source_store()
    
    source_id = f"SRC-{str(uuid.uuid4())[:8].upper()}"
    sanitized_name = safe_asset_filename(original_filename)
    
    notebook_assets_dir = get_notebook_assets_dir(notebook_id).resolve()
    dest_path = (notebook_assets_dir / sanitized_name).resolve()
    
    # Strict Path Containment Check
    if not dest_path.is_relative_to(notebook_assets_dir):
        raise ValueError("Invalid target path: directory traversal attempt detected.")
        
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
        
    # Extract metadata and preview text
    ext = Path(original_filename).suffix.lower().replace(".", "")
    if not ext:
        ext = "txt"
        
    preview_text = ""
    metadata = {
        "file_size_bytes": len(file_bytes),
        "extension": ext
    }
    
    # Parse based on type
    if ext in ("txt", "md", "markdown"):
        try:
            preview_text = file_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            preview_text = f"Error reading text: {e}"
    elif ext == "csv":
        try:
            csv_str = file_bytes.decode("utf-8", errors="replace")
            lines = [line for line in csv_str.splitlines() if line.strip()]
            preview_text = "\n".join(lines[:10])
            metadata["row_count_preview"] = len(lines)
            
            if lines:
                cols = lines[0].split(",")
                metadata["columns"] = [c.strip() for c in cols]
        except Exception as e:
            preview_text = f"Error reading CSV preview: {e}"
    elif ext in ("xlsx", "xls"):
        try:
            df = pd.read_excel(dest_path, nrows=5)
            preview_text = f"Excel Preview (sheets/columns):\nColumns: {', '.join(df.columns)}\n"
            preview_text += df.to_string(index=False)
            metadata["columns"] = list(df.columns)
        except Exception as e:
            preview_text = f"Error reading Excel preview: {e}"
    else:
        preview_text = "Chưa có xem trước nội dung cho định dạng này ở M1.7."

    preview_text = preview_text[:MAX_PREVIEW_CHARS]
        
    src_doc = SourceDocument(
        source_id=source_id,
        notebook_id=notebook_id,
        filename=sanitized_name,
        original_filename=original_filename,
        source_type=ext,
        title=title.strip() if title.strip() else original_filename,
        description=description,
        tags=tags or [],
        privacy_level=privacy_level,
        asset_path=str(dest_path),
        preview_text=preview_text,
        metadata=metadata
    )
    save_source(src_doc)
    return src_doc
