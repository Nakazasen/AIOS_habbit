# -*- coding: utf-8 -*-
"""Citation and Source Viewer for AIOS Workspace Chat.

Implements ticket DESKTOP-HOME-CITATION-SOURCE-VIEWER:
1. Extracts citations from assistant answers:
   - Historical error cases from the 30,075 reconciled DB (e.g. Loi KDTPS.xlsx > History KDTPS > dong 9609).
   - Standard reference documents & glossaries (e.g. 02XC_...-Iris2020 VN.xls).
   - Knowledge repository documents (PDF/XLS/DOC chunks from library.sqlite).
2. Verifies whether each citation exists in the active database or storage.
3. Renders citations as interactive, clickable elements inside the chat bubble.
4. Opens the Source Viewer panel directly under the answer with lazy on-demand loading:
   - For DB cases: displays ALL available fields A-Y that have data, plus source identification.
   - For repository/glossary documents: displays verbatim excerpt, metadata, and open/download action.
   - For missing citations: clearly marks 'khong tim thay nguon goc' in place, preventing fake dead links.
5. Records source verification events to local_cases for continuous improvement metrics.
"""

from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

# Well-known database candidate paths
_DEFAULT_DB_CANDIDATES = (
    Path("C:/tmp/kdtps_standard/error_cases_reconciled.db"),
    Path("C:/tmp/kdtps_standard/error_cases_dict.db"),
    Path("C:/tmp/buoc0-deploy/error_cases_deploy.db"),
    Path.home() / "tmp" / "buoc0-deploy" / "error_cases_deploy.db",
)

# Friendly Vietnamese labels for columns in KDTPS History 29-column format
HISTORY_29_LABELS: Dict[str, str] = {
    "A": "Năm sản xuất",
    "B": "Số vụ điều tra",
    "C": "Ngày sản xuất / phát sinh",
    "D": "Máy / Model",
    "E": "Line sản xuất",
    "F": "Công đoạn sản xuất",
    "G": "Số máy / Serial",
    "H": "Phân loại mã lỗi",
    "I": "Hiện tượng lỗi hiển thị",
    "J": "Số lần phát sinh",
    "L": "Thời điểm phát sinh (tiếng Nhật)",
    "M": "Hiện trạng khi xảy ra (tiếng Việt)",
    "N": "Nội dung điều tra (tiếng Nhật)",
    "O": "Nội dung điều tra (tiếng Việt)",
    "P": "Bộ phận phụ trách",
    "Q": "Trạng thái vụ việc",
    "R": "Tên linh kiện / Board",
    "S": "Mã linh kiện",
    "T": "Lot linh kiện",
    "U": "Nhà cung cấp / Đối tác",
    "V": "Đánh giá an toàn (LKATQT)",
    "W": "Ngày bắt đầu HOLD",
    "X": "Ngày HOLD",
    "Y": "Ngày giải HOLD",
    "Z": "Tính tái hiện / Nhóm vấn đề",
    "AA": "Nguyên nhân gốc",
    "AB": "Đối sách xử lý",
    "AC": "Đường dẫn báo cáo",
}

# Friendly Vietnamese labels for standard 25-column format (A-Y)
LEGACY_25_LABELS: Dict[str, str] = {
    "A": "Số vụ điều tra (No.ĐVD)",
    "B": "Ngày phát sinh",
    "C": "Máy / Model",
    "D": "Line sản xuất",
    "E": "Công đoạn sản xuất",
    "F": "Số máy / Serial",
    "G": "Mã lỗi C (C-Call)",
    "H": "Phân loại lỗi (H-Group)",
    "I": "Hiện tượng lỗi",
    "J": "Tên lỗi",
    "K": "Nội dung sự cố",
    "L": "Tình trạng",
    "M": "Biện pháp tức thì",
    "N": "Nội dung điều tra chi tiết",
    "O": "Bộ phận phụ trách",
    "P": "Đánh giá",
    "Q": "Trạng thái",
    "R": "Linh kiện liên quan",
    "S": "Người phụ trách",
    "T": "Thời gian",
    "U": "Phân loại bổ sung",
    "V": "Trạng thái hoàn thành",
    "W": "Ghi chú bổ sung",
    "X": "Ngày giải quyết",
    "Y": "Cần hỗ trợ từ chuyên gia Nhật",
}

_NA_VALUES = frozenset({"", "-", "—", "ー", "None", "null", "不要", "nan"})


@dataclass
class CitationRef:
    """Represents a citation found inside an answer text."""
    id: str
    ref_type: str  # "db_error_case" | "glossary_document" | "library_document"
    label: str
    source_file: str
    sheet_name: str = ""
    source_row: Optional[int] = None
    case_id: Optional[int] = None
    code: str = ""
    chunk_id: str = ""
    page_or_sheet: str = ""
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CitationRef:
        return cls(
            id=str(data.get("id", "") or ""),
            ref_type=str(data.get("ref_type", "") or ""),
            label=str(data.get("label", "") or ""),
            source_file=str(data.get("source_file", "") or ""),
            sheet_name=str(data.get("sheet_name", "") or ""),
            source_row=int(data["source_row"]) if data.get("source_row") is not None else None,
            case_id=int(data["case_id"]) if data.get("case_id") is not None else None,
            code=str(data.get("code", "") or ""),
            chunk_id=str(data.get("chunk_id", "") or ""),
            page_or_sheet=str(data.get("page_or_sheet", "") or ""),
            raw_text=str(data.get("raw_text", "") or ""),
        )


@dataclass
class SourceRecordField:
    """Single key-value field of a source record."""
    column_letter: str
    label_vi: str
    value: str
    is_highlight: bool = False


@dataclass
class SourceViewerPayload:
    """Detailed source data loaded lazily on demand when user clicks a citation."""
    found: bool
    citation_ref: CitationRef
    title: str
    identifier: str
    source_type: str
    fields: List[SourceRecordField] = field(default_factory=list)
    excerpt_text: str = ""
    file_path: Optional[str] = None
    can_open_file: bool = False
    raw_json: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


# ---------------------------------------------------------------------------
# Database & File Path Resolvers
# ---------------------------------------------------------------------------

def _get_error_cases_db_path() -> Optional[Path]:
    """Locate the reconciled 30,075 error_cases SQLite database."""
    env = os.environ.get("AIOS_ERROR_CASES_DB")
    if env:
        p = Path(env)
        if p.is_file():
            return p
    for cand in _DEFAULT_DB_CANDIDATES:
        if cand.is_file():
            return cand
    return None


def _open_sqlite_ro(path: Path | str) -> sqlite3.Connection:
    """Safely open SQLite database in read-only mode."""
    p_str = str(Path(path).resolve()).replace("\\", "/")
    uri = f"file:{p_str}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def _get_active_library_db_path(collection_id: str = "tri_thuc") -> Optional[Path]:
    """Find active library.sqlite for a collection."""
    try:
        from aios_habit.index_status import resolve_active_index_db_path
        p = resolve_active_index_db_path(collection_id)
        if p and p.is_file():
            return p
    except Exception:
        pass
    cand = Path(f"C:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/{collection_id}/library.sqlite")
    if cand.is_file():
        return cand
    cand2 = Path("data/library.sqlite")
    if cand2.is_file():
        return cand2
    return None


def _find_file_on_machine(filename: str) -> Optional[Path]:
    """Search for a source file on local machine if it exists."""
    if not filename:
        return None
    p = Path(filename)
    if p.is_file():
        return p

    search_roots = [
        Path(r"D:\Sandbox\AIOS_habbit\local_cases\managed_workbooks"),
        Path(r"D:\Sandbox\AIOS_habbit\local_cases\library_backups"),
        Path(r"D:\Sandbox\AIOS_habbit\local_cases"),
        Path(r"C:\tmp\kdtps_standard"),
        Path(r"C:\tmp"),
    ]
    for root in search_roots:
        if root.is_dir():
            target = root / filename
            if target.is_file():
                return target
            target_sub = root / p.name
            if target_sub.is_file():
                return target_sub
    return None


# ---------------------------------------------------------------------------
# Citation Extraction from Markdown Text
# ---------------------------------------------------------------------------

def extract_citations_from_text(content: str) -> List[CitationRef]:
    """Parse all verifiable citations from an assistant response text.

    Finds:
    1. Historical error cases:
       - Matches `- **Báo cáo gốc:** `file › sheet › dòng N``
       - Or `- **Báo cáo gốc:** `file > sheet > dòng N``
    2. Reference documents / Glossaries:
       - Matches `- **Tài liệu tham chiếu:** filename.xls`
       - Or `- **Tài liệu nguồn:** filename.xls`
    3. Document citations:
       - Matches `[E1] [Primary] filename: ...`
       - Matches table rows `| [E1] | Primary | filename | ...`
    """
    if not content or not isinstance(content, str):
        return []

    citations: List[CitationRef] = []
    seen_ids: set[str] = set()

    # 1. Error code in header/section 1
    code_match = re.search(r"\*\*(?:Mã lỗi|Ma loi):\*\*\s*`?([A-Z0-9_\-]+)`?", content, re.IGNORECASE)
    primary_code = code_match.group(1).strip() if code_match else ""

    # 2. Reference document in Section 1
    ref_doc_pattern = re.compile(
        r"-\s*\*\*(?:Tài liệu tham chiếu|Tai lieu tham chieu|Tài liệu nguồn|Tai lieu nguon):\*\*\s*`?([^\n\r`]+)`?",
        re.IGNORECASE,
    )
    for m in ref_doc_pattern.finditer(content):
        doc_name = m.group(1).strip()
        if doc_name and doc_name not in seen_ids and doc_name not in ("—", "-", "ー"):
            cite_id = f"doc_{hashlib.md5(doc_name.encode('utf-8')).hexdigest()[:8]}"
            seen_ids.add(doc_name)
            citations.append(
                CitationRef(
                    id=cite_id,
                    ref_type="glossary_document",
                    label=doc_name,
                    source_file=doc_name,
                    code=primary_code,
                    raw_text=m.group(0),
                )
            )

    # 3. Individual historical cases in Section 4
    # Pattern: `- **Báo cáo gốc:** `Loi KDTPS.xlsx › History KDTPS › dòng 9609``
    # or with `>` instead of `›`
    case_pattern = re.compile(
        r"-\s*\*\*(?:Báo cáo gốc|Bao cao goc):\*\*\s*`?([^`\n\r]+)`?",
        re.IGNORECASE,
    )
    for m in case_pattern.finditer(content):
        raw_val = m.group(1).strip()
        if not raw_val or raw_val in ("—", "-", "ー"):
            continue

        parts = [p.strip() for p in re.split(r"[›>]", raw_val)]
        source_file = parts[0] if len(parts) >= 1 else raw_val
        sheet_name = parts[1] if len(parts) >= 2 else ""
        row_str = parts[2] if len(parts) >= 3 else ""

        row_num: Optional[int] = None
        m_row = re.search(r"(?:dòng|dong)\s*(\d+)", raw_val, re.IGNORECASE)
        if m_row:
            try:
                row_num = int(m_row.group(1))
            except ValueError:
                row_num = None

        cite_id = f"case_row_{row_num}" if row_num is not None else f"case_{hashlib.md5(raw_val.encode('utf-8')).hexdigest()[:8]}"
        if cite_id not in seen_ids:
            seen_ids.add(cite_id)
            citations.append(
                CitationRef(
                    id=cite_id,
                    ref_type="db_error_case",
                    label=raw_val,
                    source_file=source_file,
                    sheet_name=sheet_name,
                    source_row=row_num,
                    code=primary_code,
                    raw_text=m.group(0),
                )
            )

    # 4. RAG / Evidence citations [E1] ...
    rag_line_pattern = re.compile(
        r"-\s*\[E(\d+)\]\s*\[(.*?)\]\s*([^:\n\r]+):\s*([^\n\r]+)",
        re.IGNORECASE,
    )
    for m in rag_line_pattern.finditer(content):
        e_idx = m.group(1)
        role = m.group(2).strip()
        src_title = m.group(3).strip()
        snippet = m.group(4).strip()
        cite_id = f"rag_e{e_idx}"
        if cite_id not in seen_ids:
            seen_ids.add(cite_id)
            citations.append(
                CitationRef(
                    id=cite_id,
                    ref_type="library_document",
                    label=f"[E{e_idx}] {src_title}",
                    source_file=src_title,
                    raw_text=m.group(0),
                )
            )

    # 5. RAG source table rows: `| [E1] | Primary | filename | type | location | ... |`
    rag_table_pattern = re.compile(
        r"\|\s*\[E(\d+)\]\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|",
        re.IGNORECASE,
    )
    for m in rag_table_pattern.finditer(content):
        e_idx = m.group(1)
        role = m.group(2).strip()
        src_title = m.group(3).strip()
        loc = m.group(5).strip()
        cite_id = f"rag_e{e_idx}"
        if cite_id not in seen_ids:
            seen_ids.add(cite_id)
            citations.append(
                CitationRef(
                    id=cite_id,
                    ref_type="library_document",
                    label=f"[E{e_idx}] {src_title} ({loc})" if loc and loc != "n/a" else f"[E{e_idx}] {src_title}",
                    source_file=src_title,
                    page_or_sheet=loc if loc != "n/a" else "",
                    raw_text=m.group(0),
                )
            )

    return citations


# ---------------------------------------------------------------------------
# Citation Existence Check (Fast < 5ms)
# ---------------------------------------------------------------------------

def check_citation_exists(ref: CitationRef, notebook_id: str = "") -> bool:
    """Quickly verify whether a citation has a valid corresponding record.

    Returns False if the record cannot be found in the local databases.
    This guarantees requirement 2.3: no fake dead links.
    """
    if ref.ref_type == "db_error_case":
        db_path = _get_error_cases_db_path()
        if not db_path:
            return False
        try:
            conn = _open_sqlite_ro(db_path)
            try:
                if ref.case_id is not None:
                    row = conn.execute("SELECT 1 FROM error_cases WHERE id = ? LIMIT 1", (ref.case_id,)).fetchone()
                    return bool(row)
                if ref.source_row is not None:
                    row = conn.execute("SELECT 1 FROM error_cases WHERE source_row = ? LIMIT 1", (ref.source_row,)).fetchone()
                    return bool(row)
                row = conn.execute("SELECT 1 FROM error_cases WHERE raw_json LIKE ? LIMIT 1", (f"%{ref.label}%",)).fetchone()
                return bool(row)
            finally:
                conn.close()
        except Exception:
            return False

    elif ref.ref_type == "glossary_document":
        db_path = _get_error_cases_db_path()
        if not db_path:
            return False
        try:
            conn = _open_sqlite_ro(db_path)
            try:
                # Check error_glossary or glossary_imports
                if ref.source_file:
                    row = conn.execute(
                        "SELECT 1 FROM error_glossary WHERE source_file LIKE ? LIMIT 1",
                        (f"%{ref.source_file}%",),
                    ).fetchone()
                    if row:
                        return True
                    row_imp = conn.execute(
                        "SELECT 1 FROM glossary_imports WHERE source_file LIKE ? LIMIT 1",
                        (f"%{ref.source_file}%",),
                    ).fetchone()
                    if row_imp:
                        return True
                if ref.code:
                    row_code = conn.execute(
                        "SELECT 1 FROM error_glossary WHERE code = ? LIMIT 1",
                        (ref.code,),
                    ).fetchone()
                    if row_code:
                        return True
                return False
            finally:
                conn.close()
        except Exception:
            return False

    elif ref.ref_type == "library_document":
        col_id = "tri_thuc" if not notebook_id or notebook_id in ("NB-LAZY-DTL", "dieu_tra_loi") else notebook_id
        lib_path = _get_active_library_db_path(col_id)
        if not lib_path:
            return False
        try:
            conn = _open_sqlite_ro(lib_path)
            try:
                if ref.chunk_id:
                    row = conn.execute("SELECT 1 FROM chunks WHERE chunk_id = ? LIMIT 1", (ref.chunk_id,)).fetchone()
                    return bool(row)
                if ref.source_file:
                    row = conn.execute(
                        "SELECT 1 FROM chunks WHERE source_name LIKE ? OR relative_path LIKE ? LIMIT 1",
                        (f"%{ref.source_file}%", f"%{ref.source_file}%"),
                    ).fetchone()
                    return bool(row)
                return False
            finally:
                conn.close()
        except Exception:
            return False

    return False


# ---------------------------------------------------------------------------
# Lazy Detailed Source Resolver (Loaded on-demand only when user clicks)
# ---------------------------------------------------------------------------

def resolve_citation_source(ref: CitationRef, notebook_id: str = "") -> SourceViewerPayload:
    """Fetch the complete verbatim source record on-demand when user clicks.

    Meets requirement 2.2:
    - For DB 30,075 cases: full record with all A-Y fields having data + source provenance.
    - For repository/glossary docs: verbatim relevant excerpt + file path + download/open option.
    - For missing records: returns payload with found=False and friendly Vietnamese explanation.
    """
    if ref.ref_type == "db_error_case":
        db_path = _get_error_cases_db_path()
        if not db_path:
            return SourceViewerPayload(
                found=False,
                citation_ref=ref,
                title="Bản ghi ca lỗi lịch sử",
                identifier=ref.label,
                source_type="db_error_case",
                error_message="Không tìm thấy cơ sở dữ liệu ca lỗi 30.075 ca trên máy.",
            )

        try:
            conn = _open_sqlite_ro(db_path)
            try:
                row = None
                if ref.case_id is not None:
                    sql = (
                        "SELECT ec.*, b.source_file AS batch_source_file, b.sheet_name AS batch_sheet_name "
                        "FROM error_cases ec "
                        "LEFT JOIN import_batches b ON b.id = ec.batch_id "
                        "WHERE ec.id = ? LIMIT 1"
                    )
                    row = conn.execute(sql, (ref.case_id,)).fetchone()
                elif ref.source_row is not None:
                    sql = (
                        "SELECT ec.*, b.source_file AS batch_source_file, b.sheet_name AS batch_sheet_name "
                        "FROM error_cases ec "
                        "LEFT JOIN import_batches b ON b.id = ec.batch_id "
                        "WHERE ec.source_row = ? LIMIT 1"
                    )
                    row = conn.execute(sql, (ref.source_row,)).fetchone()

                if not row:
                    return SourceViewerPayload(
                        found=False,
                        citation_ref=ref,
                        title="Bản ghi ca lỗi lịch sử",
                        identifier=ref.label,
                        source_type="db_error_case",
                        error_message=f"Không tìm thấy nguồn gốc của ca này trong cơ sở dữ liệu (dòng {ref.source_row or '—'}).",
                    )

                raw = json.loads(row["raw_json"] or "{}")
                src_file = row["batch_source_file"] or ref.source_file or "Loi KDTPS.xlsx"
                sheet = row["batch_sheet_name"] or ref.sheet_name or "History KDTPS"
                row_num = row["source_row"] or ref.source_row or "—"
                provenance = f"{src_file} › {sheet} › dòng {row_num}"

                # Detect format: history_29 vs legacy_25
                is_history_29 = bool("AA" in raw or "AB" in raw or "AC" in raw or raw.get("Z"))
                labels_map = HISTORY_29_LABELS if is_history_29 else LEGACY_25_LABELS

                fields_list: List[SourceRecordField] = []

                # Core primary highlights
                no_dvd_val = str(row["no_dvd"] or raw.get("B") or "").strip()
                if no_dvd_val:
                    fields_list.append(SourceRecordField("A-B", "Số vụ điều tra", no_dvd_val, is_highlight=True))

                occurred_val = str(row["occurred_at"] or raw.get("C") or "").strip()
                if occurred_val and occurred_val not in _NA_VALUES:
                    fields_list.append(SourceRecordField("C", "Ngày sản xuất / phát sinh", occurred_val, is_highlight=True))

                machine_val = str(row["machine_type"] or raw.get("D") or "").replace("\n", " ").strip()
                if machine_val and machine_val not in _NA_VALUES:
                    fields_list.append(SourceRecordField("D", "Máy / Model", machine_val, is_highlight=True))

                line_val = str(row["line"] or raw.get("E") or "").strip()
                if line_val and line_val not in _NA_VALUES:
                    fields_list.append(SourceRecordField("E", "Line sản xuất", line_val, is_highlight=True))

                stage_val = str(row["process_stage"] or raw.get("F") or "").strip()
                if stage_val and stage_val not in _NA_VALUES:
                    fields_list.append(SourceRecordField("F", "Công đoạn", stage_val, is_highlight=True))

                serial_val = str(raw.get("G") or "").replace("\n", " ").strip()
                if serial_val and serial_val not in _NA_VALUES:
                    fields_list.append(SourceRecordField("G", "Số máy / Serial", serial_val))

                code_val = str(row["error_code_i"] or row["error_code_c"] or row["error_code_h"] or "").strip()
                if code_val and code_val not in _NA_VALUES:
                    fields_list.append(SourceRecordField("H-I", "Mã lỗi liên quan", code_val, is_highlight=True))

                phenomenon_val = str(row["phenomenon"] or raw.get("I") or "").strip()
                if phenomenon_val and phenomenon_val not in _NA_VALUES:
                    fields_list.append(SourceRecordField("I", "Hiện tượng lỗi", phenomenon_val, is_highlight=True))

                # Iterate through all letter columns A to Y (and beyond Z, AA, AB, AC)
                all_col_letters = [
                    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N",
                    "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "AA", "AB", "AC"
                ]
                covered_letters = {"A-B", "C", "D", "E", "F", "G", "H-I", "I"}

                for col_let in all_col_letters:
                    if col_let in ("A", "B", "C", "D", "E", "F", "G", "I"):
                        continue
                    val = str(raw.get(col_let) or "").strip()
                    if val and val not in _NA_VALUES:
                        lbl = labels_map.get(col_let, f"Cột {col_let}")
                        is_hl = col_let in ("N", "O", "AA", "AB", "R", "S", "P")
                        fields_list.append(SourceRecordField(col_let, lbl, val, is_highlight=is_hl))

                # Add semantic columns if not covered by raw
                if row["cause"] and not any(f.column_letter == "AA" for f in fields_list):
                    fields_list.append(SourceRecordField("AA", "Nguyên nhân", str(row["cause"]), is_highlight=True))
                if row["countermeasure"] and not any(f.column_letter == "AB" for f in fields_list):
                    fields_list.append(SourceRecordField("AB", "Đối sách", str(row["countermeasure"]), is_highlight=True))

                title = f"Hồ sơ ca điều tra lịch sử: Vụ {no_dvd_val or '—'} (Dòng {row_num})"
                return SourceViewerPayload(
                    found=True,
                    citation_ref=ref,
                    title=title,
                    identifier=provenance,
                    source_type="db_error_case",
                    fields=fields_list,
                    raw_json=raw,
                    can_open_file=False,
                )
            finally:
                conn.close()
        except Exception as err:
            return SourceViewerPayload(
                found=False,
                citation_ref=ref,
                title="Bản ghi ca lỗi lịch sử",
                identifier=ref.label,
                source_type="db_error_case",
                error_message=f"Lỗi khi đọc bản ghi từ cơ sở dữ liệu: {err}",
            )

    elif ref.ref_type == "glossary_document":
        db_path = _get_error_cases_db_path()
        if not db_path:
            return SourceViewerPayload(
                found=False,
                citation_ref=ref,
                title="Tài liệu tham chiếu chuẩn",
                identifier=ref.label,
                source_type="glossary_document",
                error_message="Không tìm thấy cơ sở dữ liệu từ điển mã lỗi trên máy.",
            )

        try:
            conn = _open_sqlite_ro(db_path)
            try:
                row = None
                if ref.code:
                    row = conn.execute(
                        "SELECT * FROM error_glossary WHERE code = ? LIMIT 1",
                        (ref.code,),
                    ).fetchone()
                if not row and ref.source_file:
                    row = conn.execute(
                        "SELECT * FROM error_glossary WHERE source_file LIKE ? LIMIT 1",
                        (f"%{ref.source_file}%",),
                    ).fetchone()

                if not row:
                    return SourceViewerPayload(
                        found=False,
                        citation_ref=ref,
                        title="Tài liệu tham chiếu chuẩn",
                        identifier=ref.label,
                        source_type="glossary_document",
                        error_message=f"Không tìm thấy nội dung tham chiếu trong danh mục tài liệu chuẩn ({ref.source_file}).",
                    )

                code_val = row["code"] or ref.code or ""
                fam_val = row["code_family"] or ""
                name_vi = row["name_vi"] or ""
                name_ja = row["name_ja"] or ""
                cause_val = row["cause"] or ""
                remedy_val = row["remedy"] or ""
                src_file = row["source_file"] or ref.source_file

                excerpt_lines = [
                    f"**Mã định danh:** `{code_val}` ({fam_val})",
                    f"**Tên mã lỗi:** {name_vi}" + (f" / {name_ja}" if name_ja else ""),
                ]
                if cause_val:
                    excerpt_lines.append(f"\n**Cơ chế phát sinh (Nguyên văn từ tài liệu gốc):**\n> {cause_val}")
                if remedy_val:
                    excerpt_lines.append(f"\n**Quy trình đối sách & xử lý chuẩn (Nguyên văn từ tài liệu gốc):**\n{remedy_val}")

                # Check if original file is located on machine
                local_file = _find_file_on_machine(src_file)

                return SourceViewerPayload(
                    found=True,
                    citation_ref=ref,
                    title=f"Tài liệu tham chiếu chuẩn: {src_file}",
                    identifier=f"{src_file} (Mã {code_val})",
                    source_type="glossary_document",
                    excerpt_text="\n".join(excerpt_lines),
                    file_path=str(local_file) if local_file else None,
                    can_open_file=bool(local_file and local_file.is_file()),
                )
            finally:
                conn.close()
        except Exception as err:
            return SourceViewerPayload(
                found=False,
                citation_ref=ref,
                title="Tài liệu tham chiếu chuẩn",
                identifier=ref.label,
                source_type="glossary_document",
                error_message=f"Lỗi khi đọc tài liệu tham chiếu: {err}",
            )

    elif ref.ref_type == "library_document":
        col_id = "tri_thuc" if not notebook_id or notebook_id in ("NB-LAZY-DTL", "dieu_tra_loi") else notebook_id
        lib_path = _get_active_library_db_path(col_id)
        if not lib_path:
            return SourceViewerPayload(
                found=False,
                citation_ref=ref,
                title="Tài liệu trong kho",
                identifier=ref.label,
                source_type="library_document",
                error_message="Không tìm thấy cơ sở dữ liệu kho tài liệu trên máy.",
            )

        try:
            conn = _open_sqlite_ro(lib_path)
            try:
                row = None
                if ref.chunk_id:
                    row = conn.execute("SELECT * FROM chunks WHERE chunk_id = ? LIMIT 1", (ref.chunk_id,)).fetchone()
                if not row and ref.source_file:
                    row = conn.execute(
                        "SELECT * FROM chunks WHERE source_name LIKE ? OR relative_path LIKE ? LIMIT 1",
                        (f"%{ref.source_file}%", f"%{ref.source_file}%"),
                    ).fetchone()

                if not row:
                    return SourceViewerPayload(
                        found=False,
                        citation_ref=ref,
                        title="Tài liệu trong kho",
                        identifier=ref.label,
                        source_type="library_document",
                        error_message=f"Không tìm thấy đoạn trích của tài liệu '{ref.source_file}' trong kho tài liệu.",
                    )

                src_name = row["source_name"] or ref.source_file
                src_path = row["source_path"] or ""
                text_content = row["text"] or ""
                meta = json.loads(row["metadata_json"] or "{}")
                sheet = meta.get("sheet") or (meta.get("sheet_names", [""])[0] if meta.get("sheet_names") else "")
                page = meta.get("page") or (meta.get("page_numbers", [""])[0] if meta.get("page_numbers") else "")

                loc_str = ""
                if sheet:
                    loc_str = f"Sheet: {sheet}"
                elif page:
                    loc_str = f"Trang: {page}"

                identifier_str = f"{src_name}" + (f" ({loc_str})" if loc_str else "")

                local_file = Path(src_path) if src_path and Path(src_path).is_file() else _find_file_on_machine(src_name)

                return SourceViewerPayload(
                    found=True,
                    citation_ref=ref,
                    title=f"Đoạn trích tài liệu: {src_name}",
                    identifier=identifier_str,
                    source_type="library_document",
                    excerpt_text=text_content,
                    file_path=str(local_file) if local_file else None,
                    can_open_file=bool(local_file and local_file.is_file()),
                )
            finally:
                conn.close()
        except Exception as err:
            return SourceViewerPayload(
                found=False,
                citation_ref=ref,
                title="Tài liệu trong kho",
                identifier=ref.label,
                source_type="library_document",
                error_message=f"Lỗi khi đọc đoạn trích tài liệu: {err}",
            )

    return SourceViewerPayload(
        found=False,
        citation_ref=ref,
        title="Nguồn tham khảo",
        identifier=ref.label,
        source_type=ref.ref_type,
        error_message="Loại nguồn trích dẫn không được hỗ trợ hoặc không tìm thấy.",
    )


# ---------------------------------------------------------------------------
# Metric Event Logger (Continuous Improvement Loop - Requirement 2.4)
# ---------------------------------------------------------------------------

def record_source_verification_event(
    conversation_id: str,
    message_id: str,
    citation_ref: CitationRef,
    found: bool,
    base_cases_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Log user source verification event to local_cases (requirement 2.4).

    Does NOT write to the knowledge repository or disturb live indices.
    """
    cases_dir = Path(base_cases_dir) if base_cases_dir else Path(r"D:\Sandbox\AIOS_habbit\local_cases")
    if not cases_dir.is_dir():
        cases_dir = Path("local_cases")
    cases_dir.mkdir(parents=True, exist_ok=True)

    log_file = cases_dir / "source_verification_events.jsonl"
    event_id = f"SRC-VIEW-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{os.urandom(3).hex().upper()}"
    event_record = {
        "event_id": event_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "conversation_id": conversation_id,
        "message_id": message_id,
        "citation_id": citation_ref.id,
        "citation_type": citation_ref.ref_type,
        "citation_label": citation_ref.label,
        "source_file": citation_ref.source_file,
        "sheet_name": citation_ref.sheet_name,
        "source_row": citation_ref.source_row,
        "case_id": citation_ref.case_id,
        "found": found,
    }

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_record, ensure_ascii=False) + "\n")
    except Exception:
        pass

    return event_record


def get_source_verification_metrics(base_cases_dir: Optional[Path | str] = None) -> Dict[str, Any]:
    """Read aggregated source verification metrics from local_cases."""
    cases_dir = Path(base_cases_dir) if base_cases_dir else Path(r"D:\Sandbox\AIOS_habbit\local_cases")
    if not cases_dir.is_dir():
        cases_dir = Path("local_cases")
    log_file = cases_dir / "source_verification_events.jsonl"

    if not log_file.is_file():
        return {
            "total_views": 0,
            "views_by_type": {},
            "successful_resolutions": 0,
            "missing_resolutions": 0,
            "recent_events": [],
        }

    total = 0
    by_type: Dict[str, int] = {}
    success = 0
    missing = 0
    events: List[Dict[str, Any]] = []

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    total += 1
                    t = ev.get("citation_type", "unknown")
                    by_type[t] = by_type.get(t, 0) + 1
                    if ev.get("found"):
                        success += 1
                    else:
                        missing += 1
                    events.append(ev)
                except Exception:
                    pass
    except Exception:
        pass

    return {
        "total_views": total,
        "views_by_type": by_type,
        "successful_resolutions": success,
        "missing_resolutions": missing,
        "recent_events": events[-10:],
    }


# ---------------------------------------------------------------------------
# Streamlit UI Rendering Functions
# ---------------------------------------------------------------------------

def render_source_viewer_panel(
    st_module: Any,
    payload: SourceViewerPayload,
    on_close: Optional[Callable[[], None]] = None,
    key_prefix: str = "",
) -> None:
    """Render the Source Viewer panel inside the chat bubble under the answer.

    Adheres to:
    - Minimalist chat-first style (fits inside answer without full-screen modal).
    - Clear distinction between DB historical cases and reference documents.
    - Zero forbidden jargon in user-facing Vietnamese strings.
    """
    st = st_module
    with st.container(border=True):
        # Header bar
        header_cols = st.columns([0.85, 0.15])
        with header_cols[0]:
            icon = "🏛️" if payload.source_type == "db_error_case" else "📖"
            st.markdown(f"### {icon} {payload.title}")
            st.caption(f"📍 **Nguồn gốc:** `{payload.identifier}`")

        with header_cols[1]:
            if st.button("✖ Đóng", key=f"{key_prefix}_btn_close", use_container_width=True):
                if on_close:
                    on_close()

        st.divider()

        # If source record is not found in database / storage
        if not payload.found:
            st.warning(f"⚠️ {payload.error_message}")
            return

        # Case 1: DB Historical Error Case (30,075 cases)
        if payload.source_type == "db_error_case":
            st.info("📊 **Toàn bộ bản ghi chi tiết các trường A–Y từ cơ sở dữ liệu lịch sử:**")

            # High-priority highlight fields
            hl_fields = [f for f in payload.fields if f.is_highlight]
            other_fields = [f for f in payload.fields if not f.is_highlight]

            if hl_fields:
                cols_hl = st.columns(2)
                for i, field_item in enumerate(hl_fields):
                    target_col = cols_hl[i % 2]
                    with target_col:
                        with st.container(border=True):
                            st.markdown(f"**{field_item.label_vi}** `[Cột {field_item.column_letter}]`")
                            st.markdown(field_item.value)

            # Full list of all fields
            if other_fields:
                with st.expander("📋 Xem thêm các trường dữ liệu bổ sung trong bản ghi", expanded=False):
                    for field_item in other_fields:
                        st.markdown(f"- **{field_item.label_vi}** `[Cột {field_item.column_letter}]`: {field_item.value}")

            # Raw fidelity view
            if payload.raw_json:
                with st.expander("🔍 Xem dữ liệu thô nguyên vẹn (JSON A–Y)", expanded=False):
                    st.json(payload.raw_json)

        # Case 2 & 3: Reference Document or Library Document
        elif payload.source_type in ("glossary_document", "library_document"):
            st.markdown("📑 **Nội dung trích đoạn nguyên văn đối chiếu từ tài liệu gốc:**")
            with st.container(border=True):
                st.markdown(payload.excerpt_text)

            # File Actions (Download & Open on machine)
            action_cols = st.columns(2)
            with action_cols[0]:
                st.download_button(
                    label="📥 Tải đoạn trích đối chiếu (.txt)",
                    data=payload.excerpt_text.encode("utf-8"),
                    file_name=f"trich_dan_{payload.citation_ref.id}.txt",
                    mime="text/plain; charset=utf-8",
                    key=f"{key_prefix}_btn_dl_excerpt",
                    use_container_width=True,
                )

            with action_cols[1]:
                if payload.can_open_file and payload.file_path:
                    if st.button("📂 Mở tệp gốc trên máy", key=f"{key_prefix}_btn_open_file", use_container_width=True):
                        try:
                            os.startfile(payload.file_path)
                            st.success(f"Đã mở tệp: {Path(payload.file_path).name}")
                        except Exception as e:
                            st.error(f"Không thể mở tệp trực tiếp: {e}")
                else:
                    st.caption("ℹ️ Tệp gốc được lưu trữ trong cơ sở dữ liệu nội bộ trên máy.")

        st.caption("🔒 Dữ liệu được trích xuất trực tiếp từ kho lưu trữ cục bộ để phục vụ tự kiểm chứng.")


def render_assistant_answer_with_citations(
    st_module: Any,
    content: str,
    conversation_id: str = "",
    message_id: str = "",
    notebook_id: str = "",
    locale: str = "vi",
) -> None:
    """Render an assistant message with interactive, clickable citations and on-demand source viewer.

    1. Parses all citations in the message text.
    2. Renders the answer text with clickable source buttons directly at each citation.
    3. If any citation is not found, clearly marks it in-place as '(không tìm thấy nguồn gốc)'.
    4. When user clicks any citation, opens the Source Viewer panel directly under the answer.
    5. Records the source verification event in local_cases for metrics.
    """
    st = st_module
    citations = extract_citations_from_text(content)
    if not citations:
        st.markdown(content)
        return

    # Map citation by label or source_row or raw text
    cite_by_text: Dict[str, CitationRef] = {}
    for c in citations:
        if c.raw_text:
            cite_by_text[c.raw_text.strip()] = c

    # Split content into lines to render clickable buttons at the exact citation lines
    lines = content.split("\n")
    current_chunk: List[str] = []

    active_state_key = f"wsc_active_citation_{message_id}"
    active_cite_data = getattr(st, "session_state", {}).get(active_state_key) if hasattr(st, "session_state") else None

    for line_idx, line in enumerate(lines):
        line_stripped = line.strip()

        # Check if line contains a known citation
        matched_cite: Optional[CitationRef] = None
        for raw_k, c in cite_by_text.items():
            if raw_k in line_stripped or (c.source_row and f"dòng {c.source_row}" in line_stripped):
                matched_cite = c
                break

        if matched_cite is not None:
            # Flush preceding text
            if current_chunk:
                st.markdown("\n".join(current_chunk))
                current_chunk = []

            exists = check_citation_exists(matched_cite, notebook_id=notebook_id)
            if exists:
                # Render label
                if matched_cite.ref_type == "db_error_case":
                    st.markdown(f"- **Báo cáo gốc:** `{matched_cite.label}`")
                    btn_label = f"🔍 Xem hồ sơ gốc ({matched_cite.label})"
                elif matched_cite.ref_type == "glossary_document":
                    st.markdown(f"- **Tài liệu tham chiếu:** `{matched_cite.source_file}`")
                    btn_label = f"📖 Mở nguồn tài liệu: {matched_cite.source_file}"
                else:
                    st.markdown(f"- **Nguồn tài liệu:** `{matched_cite.label}`")
                    btn_label = f"📑 Mở đoạn trích nguồn: {matched_cite.source_file}"

                btn_key = f"btn_cite_{message_id}_{matched_cite.id}_{line_idx}"
                if st.button(btn_label, key=btn_key):
                    if hasattr(st, "session_state"):
                        st.session_state[active_state_key] = matched_cite.to_dict()
                    active_cite_data = matched_cite.to_dict()
                    record_source_verification_event(
                        conversation_id=conversation_id,
                        message_id=message_id,
                        citation_ref=matched_cite,
                        found=True,
                    )
            else:
                # Requirement 2.3: mark clearly as not found in place
                if matched_cite.ref_type == "db_error_case":
                    st.markdown(f"- **Báo cáo gốc:** `{matched_cite.label}` — *(⚠️ không tìm thấy nguồn gốc)*")
                elif matched_cite.ref_type == "glossary_document":
                    st.markdown(f"- **Tài liệu tham chiếu:** `{matched_cite.source_file}` — *(⚠️ không tìm thấy nguồn gốc)*")
                else:
                    st.markdown(f"- **Nguồn tài liệu:** `{matched_cite.label}` — *(⚠️ không tìm thấy nguồn gốc)*")
        else:
            current_chunk.append(line)

    if current_chunk:
        st.markdown("\n".join(current_chunk))

    # Render on-demand source viewer panel if user clicked any citation
    if active_cite_data and isinstance(active_cite_data, dict):
        try:
            active_ref = CitationRef.from_dict(active_cite_data)
            payload = resolve_citation_source(active_ref, notebook_id=notebook_id)

            def _close_panel():
                if hasattr(st, "session_state"):
                    st.session_state[active_state_key] = None
                if hasattr(st, "rerun"):
                    st.rerun()

            render_source_viewer_panel(
                st_module=st,
                payload=payload,
                on_close=_close_panel,
                key_prefix=f"panel_{message_id}_{active_ref.id}",
            )
        except Exception as err:
            st.error(f"Lỗi khi hiển thị trình xem nguồn: {err}")

