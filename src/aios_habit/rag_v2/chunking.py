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
    retrievable: bool = True
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
    """Create retrieval children plus local-only parent context views."""

    def __init__(
        self,
        max_chars: int = 900,
        *,
        parent_max_chars: int = 6000,
        table_rows_per_chunk: int = 4,
    ) -> None:
        if max_chars < 80:
            raise ValueError("max_chars must be at least 80")
        if parent_max_chars < max_chars:
            raise ValueError("parent_max_chars must be at least max_chars")
        if table_rows_per_chunk < 1:
            raise ValueError("table_rows_per_chunk must be positive")
        # Child representations intentionally stay inside the 600-1,000 character
        # retrieval target even when an older caller still passes the former 1,200 default.
        self.max_chars = min(max_chars, 1000)
        self.parent_max_chars = min(max(parent_max_chars, 3000), 8000)
        self.table_rows_per_chunk = table_rows_per_chunk

    def chunk_elements(self, elements: Iterable[DocumentElement]) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        for element in elements:
            if element.extraction_status in {ExtractionStatus.FAILED, ExtractionStatus.UNSUPPORTED}:
                continue
            text = self._element_text(element)
            if not text:
                continue
            if element.element_type == ElementType.TABLE and element.table is not None:
                chunks.extend(self._chunk_table(element, text))
            else:
                chunks.extend(self._chunk_text_element(element, text))
        return chunks

    def _element_text(self, element: DocumentElement) -> str:
        if element.element_type == ElementType.TABLE and element.table is not None:
            lines: List[str] = []
            if element.table.headers:
                lines.append(" | ".join(_clean_text(cell) for cell in element.table.headers))
            rows = list(element.table.rows)
            if element.table.headers and rows and self._same_row(rows[0], element.table.headers):
                rows = rows[1:]
            for row in rows:
                lines.append(" | ".join(_clean_text(cell) for cell in row))
            if not lines and element.table.cells:
                for cell in element.table.cells:
                    label = f"r{cell.row_index}c{cell.column_index}"
                    lines.append(f"{label}: {_clean_text(cell.text)}")
            return "\n".join(line for line in lines if line.strip())
        return _clean_text(element.normalized_text or element.text)

    @staticmethod
    def _same_row(left: Iterable[str], right: Iterable[str]) -> bool:
        return tuple(_clean_text(value).casefold() for value in left) == tuple(
            _clean_text(value).casefold() for value in right
        )

    def _chunk_text_element(self, element: DocumentElement, text: str) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        child_index = 0
        for parent_index, parent_text in enumerate(self._split_text(text, self.parent_max_chars)):
            child_parts = self._split_text(parent_text, self.max_chars)
            parent_id = f"{element.element_id}::parent::{parent_index:04d}"
            has_parent_view = len(child_parts) > 1
            for child_text in child_parts:
                parent_ids = tuple(
                    value
                    for value in (
                        parent_id if has_parent_view else None,
                        element.parent_element_id,
                    )
                    if value
                )
                chunks.append(self._build_chunk(
                    element,
                    child_text,
                    child_index,
                    parent_element_ids=parent_ids,
                    representation_role="child",
                ))
                child_index += 1
            if has_parent_view:
                chunks.append(self._build_chunk(
                    element,
                    parent_text,
                    parent_index,
                    element_ids=(parent_id,),
                    parent_element_ids=(element.parent_element_id,) if element.parent_element_id else (),
                    representation_role="parent",
                    retrievable=False,
                ))
        return chunks

    def _chunk_table(self, element: DocumentElement, raw_text: str) -> List[DocumentChunk]:
        table = element.table
        if table is None:
            return []
        parent_id = f"{element.element_id}::table-parent"
        chunks: List[DocumentChunk] = []
        child_index = 0
        headers = [_clean_text(value) for value in table.headers]
        rows = [list(row) for row in table.rows]
        header_rows = [list(row) for row in table.header_rows]
        header_count = len(header_rows)
        if header_count and rows[:header_count] == header_rows:
            rows = rows[header_count:]
        elif headers and rows and self._same_row(rows[0], headers):
            header_rows = [rows[0]]
            header_count = 1
            rows = rows[1:]
        elif headers:
            # Headers exist but aren't duplicated in rows (old-style TableData).
            # They still occupy source row(s), so offset data_start accordingly.
            header_count = header_count or 1

        source_start = element.row_range[0] if element.row_range else 1
        data_start = source_start + header_count
        column_range = element.column_range or (
            (1, len(headers or (rows[0] if rows else [])))
            if headers or rows
            else None
        )

        def append_retrievable_parts(
            text: str,
            *,
            row_range: Optional[Tuple[int, int]],
            cell_range: Optional[str],
            representation_role: str,
        ) -> None:
            nonlocal child_index
            for part in self._split_text(text, self.max_chars):
                chunks.append(self._build_chunk(
                    element,
                    part,
                    child_index,
                    row_range=row_range,
                    column_range=column_range,
                    cell_range=cell_range,
                    parent_element_ids=(parent_id,),
                    representation_role=representation_role,
                ))
                child_index += 1

        sheet_prefix = f"Sheet: {element.sheet}\n" if element.sheet else ""
        if headers:
            schema_lines = [f"Columns: {' | '.join(headers)}"]
            schema_lines.extend(
                f"Header row {source_start + offset}: {' | '.join(_clean_text(value) for value in row)}"
                for offset, row in enumerate(header_rows)
            )
            schema_text = sheet_prefix + "\n".join(schema_lines)
            header_end = source_start + max(0, header_count - 1)
            schema_range = (source_start, header_end)
            append_retrievable_parts(
                schema_text,
                row_range=schema_range,
                cell_range=self._cell_range(column_range, schema_range),
                representation_role="table_schema",
            )

        group: List[tuple[int, List[str]]] = []
        for offset, row in enumerate(rows):
            source_row = data_start + offset
            candidate = [*group, (source_row, row)]
            candidate_text = self._table_group_text(element, headers, candidate)
            if group and (
                len(group) >= self.table_rows_per_chunk
                or len(candidate_text) > self.max_chars
            ):
                row_range = (group[0][0], group[-1][0])
                append_retrievable_parts(
                    self._table_group_text(element, headers, group),
                    row_range=row_range,
                    cell_range=self._cell_range(column_range, row_range),
                    representation_role="table_rows",
                )
                group = [(source_row, row)]
            else:
                group = candidate
        if group:
            row_range = (group[0][0], group[-1][0])
            append_retrievable_parts(
                self._table_group_text(element, headers, group),
                row_range=row_range,
                cell_range=self._cell_range(column_range, row_range),
                representation_role="table_rows",
            )

        parent_text = raw_text
        if sheet_prefix and not parent_text.startswith(sheet_prefix):
            parent_text = f"{sheet_prefix}{parent_text}"
        chunks.append(self._build_chunk(
            element,
            parent_text,
            0,
            element_ids=(parent_id,),
            parent_element_ids=(element.parent_element_id,) if element.parent_element_id else (),
            representation_role="table_parent",
            retrievable=False,
        ))
        return chunks

    @staticmethod
    def _table_group_text(
        element: DocumentElement,
        headers: List[str],
        group: List[tuple[int, List[str]]],
    ) -> str:
        lines = []
        if element.sheet:
            lines.append(f"Sheet: {element.sheet}")
        if headers:
            lines.append(f"Columns: {' | '.join(headers)}")
        lines.extend(
            f"Row {row_number}: {' | '.join(_clean_text(value) for value in row)}"
            for row_number, row in group
        )
        return "\n".join(lines)

    @staticmethod
    def _column_name(number: int) -> str:
        value = ""
        while number > 0:
            number, remainder = divmod(number - 1, 26)
            value = chr(65 + remainder) + value
        return value

    def _cell_range(
        self,
        column_range: Optional[Tuple[int, int]],
        row_range: Optional[Tuple[int, int]],
    ) -> Optional[str]:
        if column_range is None or row_range is None:
            return None
        return (
            f"{self._column_name(column_range[0])}{row_range[0]}:"
            f"{self._column_name(column_range[1])}{row_range[1]}"
        )

    def _split_text(self, text: str, limit: Optional[int] = None) -> List[str]:
        text = text.strip()
        max_chars = limit or self.max_chars
        if len(text) <= max_chars:
            return [text]
        parts: List[str] = []
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            if end < len(text):
                boundary = max(
                    text.rfind(". ", start, end),
                    text.rfind("\n", start, end),
                    text.rfind(" ", start, end),
                )
                if boundary > start + max(40, max_chars // 3):
                    end = boundary + 1
            part = text[start:end].strip()
            if part:
                parts.append(part)
            start = end
        return parts

    def _build_chunk(
        self,
        element: DocumentElement,
        text: str,
        part_index: int,
        *,
        element_ids: Optional[Tuple[str, ...]] = None,
        parent_element_ids: Optional[Tuple[str, ...]] = None,
        row_range: Optional[Tuple[int, int]] = None,
        column_range: Optional[Tuple[int, int]] = None,
        cell_range: Optional[str] = None,
        representation_role: str = "child",
        retrievable: bool = True,
    ) -> DocumentChunk:
        normalized = _clean_text(text).lower()
        checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
        resolved_element_ids = element_ids or (element.element_id,)
        metadata = {
            "element_id": resolved_element_ids[0],
            "extractor": element.extractor,
            "part_index": part_index,
            "page": element.page,
            "slide": element.slide,
            "sheet": element.sheet,
            "bbox": element.bbox,
            "representation_role": representation_role,
            "retrievable": retrievable,
        }
        return DocumentChunk(
            chunk_id=self._chunk_id(element, part_index, checksum, representation_role),
            document_id=element.document_id,
            source_path=element.source_path,
            source_name=element.source_name,
            file_type=element.file_type,
            text=text,
            normalized_text=normalized,
            element_ids=resolved_element_ids,
            element_types=(element.element_type.value,),
            page_range=(element.page, element.page) if element.page is not None else None,
            slide_range=(element.slide, element.slide) if element.slide is not None else None,
            sheet_names=(element.sheet,) if element.sheet else tuple(),
            row_range=row_range if row_range is not None else (
                tuple(element.row_range) if element.row_range is not None else None
            ),
            column_range=column_range if column_range is not None else (
                tuple(element.column_range) if element.column_range is not None else None
            ),
            cell_range=cell_range if cell_range is not None else element.cell_range,
            parent_element_ids=parent_element_ids if parent_element_ids is not None else (
                (element.parent_element_id,) if element.parent_element_id else tuple()
            ),
            section_path=tuple(element.section_path),
            privacy_labels=tuple(element.privacy_labels),
            source_fingerprint=element.source_fingerprint,
            checksum=checksum,
            retrievable=retrievable,
            metadata=metadata,
        )

    def _chunk_id(
        self,
        element: DocumentElement,
        part_index: int,
        checksum: str,
        representation_role: str,
    ) -> str:
        raw = "|".join([
            element.document_id,
            element.source_path,
            element.element_id,
            representation_role,
            str(part_index),
            checksum,
        ])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
