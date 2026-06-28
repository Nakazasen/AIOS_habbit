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


def _safe_citation_label(source_title: str, relative_path: str, source_path: str) -> str:
    label = source_title.strip() if source_title else ""
    if not label:
        label = Path(relative_path or source_path).name
    return label or "unknown-source"


def build_elements_from_extracted_payload(
    *,
    source_path: str,
    text: str,
    source_title: str = "",
    relative_path: str = "",
    file_type: str = "",
    source_hash: str = "",
    privacy_mode: Optional[str] = None,
    extractor_name: str = "unknown",
    extraction_status: str = "ok",
    element_type: str = "text",
    metadata: Optional[Dict[str, Any]] = None,
) -> List[RAGDocumentElement]:
    """Build a minimal normalized element list from an extracted text payload.

    This is intentionally small and local-only: it does not parse, OCR, index,
    call providers, or replace the existing extractor stack.
    """
    resolved_hash = source_hash or compute_source_hash(text or "")
    doc_id = stable_document_id(source_path, resolved_hash)
    clean_text = (text or "").strip()
    warnings: List[str] = []
    if not clean_text:
        warnings.append("empty_text")
    return [
        RAGDocumentElement(
            element_id=stable_element_id(doc_id, 0, element_type or "unknown"),
            document_id=doc_id,
            source_title=source_title or Path(source_path).name,
            source_path=source_path,
            relative_path=relative_path or Path(source_path).name,
            file_type=file_type or Path(source_path).suffix.lower() or ".txt",
            element_type=element_type or "unknown",
            text=clean_text,
            privacy_mode=normalize_privacy_mode(privacy_mode),
            extractor_name=extractor_name,
            extraction_status=extraction_status,
            warnings=warnings,
            source_hash=resolved_hash,
            metadata=metadata or {},
        )
    ]


def build_chunks_from_elements(
    elements: List[RAGDocumentElement],
    *,
    max_chars: int = 1200,
) -> List[RAGChunk]:
    """Build deterministic metadata-rich chunks from normalized elements."""
    chunks: List[RAGChunk] = []
    for index, element in enumerate([e for e in elements if e.text.strip()]):
        row_ranges = []
        if element.row_start is not None or element.row_end is not None:
            row_ranges.append(f"{element.row_start or ''}:{element.row_end or ''}")
        chunk_text = element.text[:max_chars]
        chunk = RAGChunk(
            chunk_id=stable_chunk_id(element.document_id, index, compute_source_hash(chunk_text)),
            document_id=element.document_id,
            element_ids=[element.element_id],
            text=chunk_text,
            source_title=element.source_title,
            source_path=element.source_path,
            relative_path=element.relative_path,
            citation_label=_safe_citation_label(element.source_title, element.relative_path, element.source_path),
            file_type=element.file_type,
            element_types=[element.element_type],
            page_numbers=[element.page_number] if element.page_number is not None else [],
            sheet_names=[element.sheet_name] if element.sheet_name else [],
            slide_numbers=[element.slide_number] if element.slide_number is not None else [],
            section_labels=[element.section_label] if element.section_label else [],
            row_ranges=row_ranges,
            cell_ranges=[element.cell_range] if element.cell_range else [],
            privacy_mode=normalize_privacy_mode(element.privacy_mode),
            source_hash=element.source_hash,
            chunk_index=index,
            metadata=dict(element.metadata),
        )
        chunks.append(chunk)
    for index, chunk in enumerate(chunks):
        if index > 0 and chunks[index - 1].document_id == chunk.document_id:
            chunk.previous_chunk_id = chunks[index - 1].chunk_id
            chunks[index - 1].next_chunk_id = chunk.chunk_id
    return chunks
