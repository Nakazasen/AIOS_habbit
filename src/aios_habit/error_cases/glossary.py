"""F4: error-code glossary parsers + import.

Four code families, one shared table (see glossary_schema.sql).
All source files are read-only; nothing is written back to them.

Lookup key normalization: NFKC + strip + upper (source files store
C-call digits in full-width, e.g. Ｃ００３０).
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

import xlrd

SCHEMA_FILE = Path(__file__).with_name("glossary_schema.sql")

CODE_FAMILIES = ("C_CALL", "F_SYSTEM", "JAM", "SCT_ADJ")


def norm_code(value: Any) -> str:
    return unicodedata.normalize("NFKC", "" if value is None else str(value)).strip().upper()


def cell_text(value: Any) -> str:
    t = unicodedata.normalize("NFKC", "" if value is None else str(value)).strip()
    return "" if t in ("-", "―", "ー") else t


def init_glossary(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
    conn.commit()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Parsers: each returns a list of entry dicts.
# ---------------------------------------------------------------------------

def parse_ccall(path: Path) -> List[Dict[str, Any]]:
    """C_CALL from 02XC_...Iris2020 VN.xls: JP sheet + VN sheet in parallel.

    Data rows: col2 = upper 3 digits, col3 = last digit, col4 = occurrence
    rank, col7 = name, col9 = detection content. Header is rows 8-9.
    """
    wb = xlrd.open_workbook(str(path))
    jp = wb.sheet_by_name("サービスコール一覧")
    vn = wb.sheet_by_name("サービスコール一覧 (2)")
    entries: List[Dict[str, Any]] = []
    for r in range(10, min(jp.nrows, vn.nrows)):
        hi = norm_code(jp.cell(r, 2).value)
        lo = norm_code(jp.cell(r, 3).value)
        if not re.fullmatch(r"\d{3}", hi) or not re.fullmatch(r"\d", lo):
            continue
        entries.append({
            "code_family": "C_CALL",
            "code": f"C{hi}{lo}",
            "code_sub": "",
            "name_ja": cell_text(jp.cell(r, 7).value),
            "name_vi": cell_text(vn.cell(r, 7).value),
            "name_en": "",
            "cause": cell_text(vn.cell(r, 9).value),
            "remedy": "",
            "rank": norm_code(jp.cell(r, 4).value),
            "unit": "",
            "models": "",
        })
    return entries


def parse_uwca(path: Path) -> List[Dict[str, Any]]:
    """F_SYSTEM from UWCA...xls, sheet 'List'.

    Col1 = Code, col2 = 内容(ja), col3 = Contents(en), col4 = Team,
    col5 = procedure (ja), col6 = procedure (en). Header row 0.
    """
    wb = xlrd.open_workbook(str(path))
    sh = wb.sheet_by_name("List")
    entries: List[Dict[str, Any]] = []
    for r in range(1, sh.nrows):
        code = norm_code(sh.cell(r, 1).value)
        if not re.fullmatch(r"F[0-9A-FX]{3,4}", code):
            continue  # sub-header rows like '―'
        entries.append({
            "code_family": "F_SYSTEM",
            "code": code,
            "code_sub": "",
            "name_ja": cell_text(sh.cell(r, 2).value),
            "name_vi": "",
            "name_en": cell_text(sh.cell(r, 3).value),
            "cause": "",
            "remedy": "JA: " + cell_text(sh.cell(r, 5).value)
                      + "\nEN: " + cell_text(sh.cell(r, 6).value),
            "rank": "",
            "unit": cell_text(sh.cell(r, 4).value),  # Team
            "models": "",
        })
    return entries


def parse_sct(path: Path) -> List[Dict[str, Any]]:
    """SCT_ADJ from SCT...xls, Vietnamese sheet.

    Header row 2: ErrNo | ErrDefine | Giải thích | Nguyên nhân |
    Đối sách giải quyết | Ghi chú. ErrNo=03 is duplicated upstream;
    both rows are kept via code_sub = ErrDefine (+#2 on full collision).
    """
    wb = xlrd.open_workbook(str(path))
    sh = wb.sheet_by_name("List code lỗi điều chỉnh tựđộng")
    entries: List[Dict[str, Any]] = []
    seen = set()
    for r in range(3, sh.nrows):
        err_no = norm_code(sh.cell(r, 1).value)
        if not re.fullmatch(r"[0-9A-F]{2}", err_no):
            continue
        err_def = cell_text(sh.cell(r, 2).value)
        sub = err_def
        n = 2
        while ("SCT_ADJ", err_no, sub) in seen:
            sub = f"{err_def}#{n}"
            n += 1
        seen.add(("SCT_ADJ", err_no, sub))
        entries.append({
            "code_family": "SCT_ADJ",
            "code": err_no,
            "code_sub": sub,
            "name_ja": "",
            "name_vi": cell_text(sh.cell(r, 3).value),
            "name_en": "",
            "cause": cell_text(sh.cell(r, 4).value),
            "remedy": cell_text(sh.cell(r, 5).value),
            "rank": "",
            "unit": "",
            "models": "",
        })
    return entries


JAM_SHEETS = (
    "2. ユニット00-09", "3. ユニット10-59", "4. ユニット60-79",
    "5. ユニット90-99", "6. ユニットA0-A9", "7. ユニットB0-B9",
)


def parse_jam(path: Path) -> List[Dict[str, Any]]:
    """JAM from 02XC_...JAM....xls, 6 unit sheets.

    Two layouts exist across sheets; columns are discovered per sheet
    from the header row (row 3) by header text, so both work:
      unit='ユニット', code='JAM番号', name='名称',
      detect='検知状況'|'検知条件', note='備考',
      model cols = non-empty headers right of '備考' ('○'/'〇' = applies).
    Unit cells are merged -> forward-filled. Names are Japanese only;
    name_vi stays NULL until a translation batch fills it.
    """
    wb = xlrd.open_workbook(str(path))
    entries: List[Dict[str, Any]] = []
    for sheet_name in JAM_SHEETS:
        sh = wb.sheet_by_name(sheet_name)
        # Header row varies (row 2 or 3); find it by the JAM番号 marker.
        header_row = next(
            (r for r in range(0, 6)
             if any(cell_text(sh.cell(r, c).value) == "JAM番号"
                    for c in range(sh.ncols))),
            None,
        )
        if header_row is None:
            continue
        header = {cell_text(sh.cell(header_row, c).value): c
                  for c in range(sh.ncols)}
        unit_col = header.get("ユニット")
        code_col = header.get("JAM番号")
        name_col = header.get("名称")          # sheet 5 has no name column
        detect_col = header.get("検知状況", header.get("検知条件"))
        note_col = header.get("備考")
        after = note_col if note_col is not None else code_col
        model_cols = sorted(
            c for c in range(sh.ncols)
            if c > after and cell_text(sh.cell(header_row, c).value)
        )
        model_names = [cell_text(sh.cell(header_row, c).value) for c in model_cols]
        unit = ""
        for r in range(header_row + 1, sh.nrows):
            if unit_col is not None:
                u = cell_text(sh.cell(r, unit_col).value).split("\n")[0]
                if u:
                    unit = u
            code = norm_code(sh.cell(r, code_col).value)
            if not re.fullmatch(r"[0-9A-F]{4}", code):
                continue
            # The code's 1st char is the unit (per sheet 4桁化のルール).
            # Skip rows where they disagree (source copy-paste artifacts,
            # e.g. code 0000 stray at the end of the unit-A0 sheet).
            if unit and code[0] != unit[0].upper():
                continue
            models = ",".join(
                name for name, c in zip(model_names, model_cols)
                if cell_text(sh.cell(r, c).value) in ("○", "〇")
            )
            entries.append({
                "code_family": "JAM",
                "code": code,
                "code_sub": "",
                "name_ja": cell_text(sh.cell(r, name_col).value) if name_col is not None else "",
                "name_vi": "",
                "name_en": "",
                "cause": cell_text(sh.cell(r, detect_col).value) if detect_col is not None else "",
                "remedy": cell_text(sh.cell(r, note_col).value) if note_col is not None else "",
                "rank": "",
                "unit": unit,
                "models": models,
            })
    return entries


PARSERS = {
    "C_CALL": parse_ccall,
    "F_SYSTEM": parse_uwca,
    "SCT_ADJ": parse_sct,
    "JAM": parse_jam,
}


# ---------------------------------------------------------------------------
# Import with file-level skip ("vất lại file cũ thì bỏ qua")
# ---------------------------------------------------------------------------

def import_glossary(
    conn: sqlite3.Connection,
    path: Path,
    family: str,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """Parse one source file and upsert its entries.

    Returns {status, inserted, updated, entries}. If the exact file
    (name + sha256) was imported before and force=False, the whole
    import is skipped: status='skipped', inserted=updated=0.
    """
    if family not in PARSERS:
        raise ValueError(f"unknown family: {family}")
    path = Path(path)
    sha = file_sha256(path)
    if not force and conn.execute(
        "SELECT 1 FROM glossary_imports WHERE source_file = ? AND file_sha256 = ?",
        (path.name, sha),
    ).fetchone():
        return {"status": "skipped", "inserted": 0, "updated": 0, "entries": 0}

    entries = PARSERS[family](path)
    if force:
        # Full refresh for this family (single source file per family).
        conn.execute("DELETE FROM error_glossary WHERE code_family = ?", (family,))
    inserted = updated = 0
    for e in entries:
        exists = conn.execute(
            """SELECT 1 FROM error_glossary
               WHERE code_family = ? AND code = ? AND code_sub = ?""",
            (e["code_family"], e["code"], e["code_sub"]),
        ).fetchone() is not None
        # First occurrence wins: cross-sheet repeats (e.g. JAM appendix
        # rows) are cross-references; the home sheet stays authoritative.
        conn.execute(
            """INSERT INTO error_glossary
               (code_family, code, code_sub, name_ja, name_vi, name_en,
                cause, remedy, rank, unit, models, source_file)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (code_family, code, code_sub) DO NOTHING""",
            (e["code_family"], e["code"], e["code_sub"], e["name_ja"] or None,
             e["name_vi"] or None, e["name_en"] or None, e["cause"] or None,
             e["remedy"] or None, e["rank"] or None, e["unit"] or None,
             e["models"] or None, path.name),
        )
        if exists:
            updated += 1
        else:
            inserted += 1
    conn.execute(
        """INSERT OR IGNORE INTO glossary_imports (source_file, file_sha256, entries)
           VALUES (?, ?, ?)""",
        (path.name, sha, len(entries)),
    )
    conn.commit()
    return {"status": "imported", "inserted": inserted, "updated": updated,
            "entries": len(entries)}


def lookup(conn: sqlite3.Connection, family: str, code: str,
           code_sub: str = "") -> Optional[Dict[str, Any]]:
    """Exact lookup by (family, normalized code)."""
    row = conn.execute(
        "SELECT * FROM error_glossary WHERE code_family = ? AND code = ? AND code_sub = ?",
        (family, norm_code(code), code_sub),
    ).fetchone()
    return dict(row) if row else None
