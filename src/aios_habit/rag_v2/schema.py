"""
Generic element schema for RAG v2.
This module defines the basic document element, element types, and table structures.
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Optional, Dict, List, Tuple
from enum import Enum
import hashlib
import datetime

class ExtractionStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"

class ElementType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    IMAGE = "image"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class TableCell:
    row_index: int
    column_index: int
    text: str
    is_header: bool = False
    row_span: int = 1
    col_span: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TableCell":
        return cls(**data)

@dataclass
class TableData:
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    cells: List[TableCell] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headers": self.headers,
            "rows": self.rows,
            "cells": [c.to_dict() for c in self.cells]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TableData":
        headers = data.get("headers", [])
        rows = data.get("rows", [])
        cells_data = data.get("cells", [])
        cells = [TableCell.from_dict(c) for c in cells_data]
        return cls(headers=headers, rows=rows, cells=cells)

@dataclass
class DocumentElement:
    element_id: str
    document_id: str
    source_path: str
    source_name: str
    file_type: str
    extractor: str
    extraction_status: ExtractionStatus
    element_type: ElementType

    # Optional metadata / warnings
    extraction_warning: Optional[str] = None

    # Coordinates / Hierarchy
    page: Optional[int] = None
    slide: Optional[int] = None
    sheet: Optional[str] = None
    row_range: Optional[Tuple[int, int]] = None
    column_range: Optional[Tuple[int, int]] = None
    cell_range: Optional[str] = None
    bbox: Optional[Tuple[float, float, float, float]] = None

    # Content
    text: Optional[str] = None
    normalized_text: Optional[str] = None
    table: Optional[TableData] = None

    # NLP hints
    language_hint: Optional[str] = None
    confidence: Optional[float] = None

    # Security/Traceability
    privacy_labels: Tuple[str, ...] = field(default_factory=tuple)
    checksum: Optional[str] = None
    source_fingerprint: Optional[str] = None

    # Graph / Hierarchy
    parent_element_id: Optional[str] = None
    section_path: Tuple[str, ...] = field(default_factory=tuple)

    # Timestamps
    created_at: Optional[str] = None
    indexed_at: Optional[str] = None

    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._compute_checksum()
        if not self.created_at:
            self.created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _compute_checksum(self) -> str:
        # Checksum based on source info and content
        m = hashlib.sha256()
        m.update(self.source_path.encode('utf-8'))
        if self.text:
            m.update(self.text.encode('utf-8'))
        if self.table:
            # Basic table hashing
            for row in self.table.rows:
                m.update(str(row).encode('utf-8'))
        if self.page is not None:
            m.update(str(self.page).encode('utf-8'))
        return m.hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["extraction_status"] = self.extraction_status.value
        d["element_type"] = self.element_type.value
        if self.table:
            d["table"] = self.table.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentElement":
        data_copy = data.copy()

        # Enums
        if "extraction_status" in data_copy:
            data_copy["extraction_status"] = ExtractionStatus(data_copy["extraction_status"])
        else:
            data_copy["extraction_status"] = ExtractionStatus.SUCCESS

        if "element_type" in data_copy:
            data_copy["element_type"] = ElementType(data_copy["element_type"])
        else:
            data_copy["element_type"] = ElementType.UNKNOWN

        # Objects
        if data_copy.get("table"):
            data_copy["table"] = TableData.from_dict(data_copy["table"])

        # Tuples
        if "privacy_labels" in data_copy:
            data_copy["privacy_labels"] = tuple(data_copy["privacy_labels"])
        if "section_path" in data_copy:
            data_copy["section_path"] = tuple(data_copy["section_path"])
        if "row_range" in data_copy and data_copy["row_range"] is not None:
            data_copy["row_range"] = tuple(data_copy["row_range"])
        if "column_range" in data_copy and data_copy["column_range"] is not None:
            data_copy["column_range"] = tuple(data_copy["column_range"])
        if "bbox" in data_copy and data_copy["bbox"] is not None:
            data_copy["bbox"] = tuple(data_copy["bbox"])

        return cls(**data_copy)
