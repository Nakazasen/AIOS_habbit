"""Structure-aware chunk creation for generic RAG v2 elements."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .schema import DocumentElement, ElementType, ExtractionStatus


def _clean_text(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    document_id: str
    source_path: str
    source_name: str
    file_type: str
    text: str
    normalized_text: str
    element_ids: Tuple[str, ...]
    element_types: Tuple[str, ...]
    page_range: Optional[Tuple[int, int]] = None
    slide_range: Optional[Tuple[int, int]] = None
    sheet_names: Tuple[str, ...] = field(default_factory=tuple)
    row_range: Optional[Tuple[int, int]] = None
    column_range: Optional[Tuple[int, int]] = None
    cell_range: Optional[str] = None
    parent_element_ids: Tuple[str, ...] = field(default_factory=tuple)
    section_path: Tuple[str, ...] = field(default_factory=tuple)
    privacy_labels: Tuple[str, ...] = field(default_factory=tuple)
    source_fingerprint: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentChunk":
        copy = dict(data)
        for key in (
            "element_ids", "element_types", "sheet_names", "parent_element_ids",
            "section_path", "privacy_labels",
        ):
            if key in copy and copy[key] is not None:
                copy[key] = tuple(copy[key])
        for key in ("page_range", "slide_range", "row_range", "column_range"):
            if key in copy and copy[key] is not None:
                copy[key] = tuple(copy[key])
        return cls(**copy)


class StructureAwareChunker:
    def __init__(self, max_chars: int = 1200) -> None:
        if max_chars < 80:
            raise ValueError("max_chars must be at least 80")
        self.max_chars = max_chars

    def chunk_elements(self, elements: Iterable[DocumentElement]) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        for element in elements:
            if element.extraction_status in {ExtractionStatus.FAILED, ExtractionStatus.UNSUPPORTED}:
                continue
            text = self._element_text(element)
            if not text:
                continue
            for index, part in enumerate(self._split_text(text)):
                chunks.append(self._build_chunk(element, part, index))
        return chunks

    def _element_text(self, element: DocumentElement) -> str:
        if element.element_type == ElementType.TABLE and element.table is not None:
            lines: List[str] = []
            if element.table.headers:
                lines.append(" | ".join(_clean_text(cell) for cell in element.table.headers))
            for row in element.table.rows:
                lines.append(" | ".join(_clean_text(cell) for cell in row))
            if not lines and element.table.cells:
                for cell in element.table.cells:
                    label = f"r{cell.row_index}c{cell.column_index}"
                    lines.append(f"{label}: {_clean_text(cell.text)}")
            return "\n".join(line for line in lines if line.strip())
        return _clean_text(element.normalized_text or element.text)

    def _split_text(self, text: str) -> List[str]:
        text = text.strip()
        if len(text) <= self.max_chars:
            return [text]
        parts: List[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.max_chars, len(text))
            if end < len(text):
                boundary = max(text.rfind(". ", start, end), text.rfind("\n", start, end), text.rfind(" ", start, end))
                if boundary > start + max(40, self.max_chars // 3):
                    end = boundary + 1
            part = text[start:end].strip()
            if part:
                parts.append(part)
            start = end
        return parts

    def _build_chunk(self, element: DocumentElement, text: str, part_index: int) -> DocumentChunk:
        normalized = _clean_text(text).lower()
        checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
        metadata = {
            "element_id": element.element_id,
            "extractor": element.extractor,
            "part_index": part_index,
            "page": element.page,
            "slide": element.slide,
            "sheet": element.sheet,
            "bbox": element.bbox,
        }
        return DocumentChunk(
            chunk_id=self._chunk_id(element, part_index, checksum),
            document_id=element.document_id,
            source_path=element.source_path,
            source_name=element.source_name,
            file_type=element.file_type,
            text=text,
            normalized_text=normalized,
            element_ids=(element.element_id,),
            element_types=(element.element_type.value,),
            page_range=(element.page, element.page) if element.page is not None else None,
            slide_range=(element.slide, element.slide) if element.slide is not None else None,
            sheet_names=(element.sheet,) if element.sheet else tuple(),
            row_range=tuple(element.row_range) if element.row_range is not None else None,
            column_range=tuple(element.column_range) if element.column_range is not None else None,
            cell_range=element.cell_range,
            parent_element_ids=(element.parent_element_id,) if element.parent_element_id else tuple(),
            section_path=tuple(element.section_path),
            privacy_labels=tuple(element.privacy_labels),
            source_fingerprint=element.source_fingerprint,
            checksum=checksum,
            metadata=metadata,
        )

    def _chunk_id(self, element: DocumentElement, part_index: int, checksum: str) -> str:
        raw = "|".join([element.document_id, element.source_path, element.element_id, str(part_index), checksum])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
