import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

@dataclass
class RAGDocumentElement:
    element_id: str
    document_id: str
    source_title: str
    source_path: str
    relative_path: str
    file_type: str
    element_type: str
    text: str
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    slide_number: Optional[int] = None
    section_label: Optional[str] = None
    row_start: Optional[int] = None
    row_end: Optional[int] = None
    cell_range: Optional[str] = None
    privacy_mode: str = "local_only"
    extractor_name: str = "unknown"
    extraction_status: str = "unknown"
    warnings: List[str] = field(default_factory=list)
    source_hash: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RAGChunk:
    chunk_id: str
    document_id: str
    element_ids: List[str]
    text: str
    source_title: str
    source_path: str
    relative_path: str
    citation_label: str
    file_type: str
    element_types: List[str]
    page_numbers: List[int]
    sheet_names: List[str]
    slide_numbers: List[int]
    section_labels: List[str]
    row_ranges: List[str]
    cell_ranges: List[str]
    privacy_mode: str = "local_only"
    source_hash: str = ""
    chunk_index: int = 0
    parent_chunk_id: Optional[str] = None
    previous_chunk_id: Optional[str] = None
    next_chunk_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

def compute_source_hash(data: Union[str, bytes, Path]) -> str:
    if isinstance(data, Path):
        if not data.exists():
            return ""
        data = data.read_bytes()
    elif isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()

def stable_document_id(source_path: str, source_hash: str) -> str:
    # Deterministic ID for a document based on its path and content hash
    raw = f"{source_path}:{source_hash}".encode("utf-8")
    return f"DOC-{hashlib.md5(raw).hexdigest()[:12].upper()}"

def stable_element_id(document_id: str, element_index: int, element_type: str) -> str:
    return f"{document_id}-E{element_index:04d}-{element_type[:4].upper()}"

def stable_chunk_id(document_id: str, chunk_index: int, source_hash: str) -> str:
    raw = f"{document_id}:{chunk_index}:{source_hash}".encode("utf-8")
    return f"{document_id}-C{chunk_index:04d}-{hashlib.md5(raw).hexdigest()[:4].upper()}"

def normalize_privacy_mode(value: Optional[str]) -> str:
    if not value:
        return "local_only"
    v = value.strip().lower()
    if v in {"local_only", "company", "mật", "private"}:
        return "local_only"
    if v in {"cloud_safe", "public", "normal"}:
        return "cloud_safe"
    return "local_only"

