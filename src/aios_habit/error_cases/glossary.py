"""F4: error-code glossary parsers + import.

Four code families, one shared table (see glossary_schema.sql).
All source files are read-only; nothing is written back to them.

Lookup key normalization: NFKC + strip + upper (source files store
C-call digits in full-width, e.g. Ｃ００３０).

B0-DICT adds:
- C_CALL enrichment from ``Iris2020_Cコール自己診断.xlsx`` (2025): per-code
  diagnostic steps (No/step/imagined cause/action, JP+VN in parallel)
  fill the empty ``remedy`` of the C_CALL rows imported by F4; codes the
  02XC table lacks are inserted as new C_CALL rows.
- ``term_aliases``: variant name spellings -> one canonical code, seeded
  from the real parallel JP/VN sources (seed_term_aliases), original names
  kept in error_glossary for traceability.
- C_CALL backfill from the older ``02XC_自己診断表示一覧表.xls`` (2024):
  it carries 10 C codes the newer VN table dropped (C1420, C1760,
  C7631-C7634, C7641-C7644); only codes missing from the table are
  inserted, the VN table stays authoritative (parse_ccall_old /
  import_ccall_old).
- canonical_term() also strips the JAM family prefix: history rows write
  'JAM4709' while the JAM workbook stores bare numbers ('4709').
- suggest_terms() for the B0-FORM input hints; glossary_coverage() for the
  ticket acceptance metric (% of DB codes found in the glossary).
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
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


def parse_ccall_old(path: Path) -> List[Dict[str, Any]]:
    """C_CALL from the older 02XC_自己診断表示一覧表.xls (2024).

    Same workbook family as parse_ccall but an older revision: its
    'サービスコール一覧' sheet uses a wider layout (31 columns) and has
    no VN twin sheet. Columns: 2-3 = code digits (upper 3 + last 1),
    4 = occurrence rank, 11 = name (ja), 12 = detection condition,
    13 = detection content, 14 = check method. Data rows start at row 10.

    The newer VN table (parse_ccall) stays authoritative; this parser only
    exists to recover the 10 codes the newer revision dropped (C1420,
    C1760, C7631-C7634, C7641-C7644) — see import_ccall_old.
    """
    wb = xlrd.open_workbook(str(path))
    sh = wb.sheet_by_name("サービスコール一覧")
    entries: List[Dict[str, Any]] = []
    for r in range(10, sh.nrows):
        hi = norm_code(sh.cell(r, 2).value)
        lo = norm_code(sh.cell(r, 3).value)
        if not re.fullmatch(r"\d{3}", hi) or not re.fullmatch(r"\d", lo):
            continue
        entries.append({
            "code_family": "C_CALL",
            "code": f"C{hi}{lo}",
            "code_sub": "",
            "name_ja": cell_text(sh.cell(r, 11).value),
            "name_vi": "",
            "name_en": "",
            "cause": "\n".join(
                t for t in (cell_text(sh.cell(r, 12).value),
                            cell_text(sh.cell(r, 13).value)) if t
            ),
            "remedy": cell_text(sh.cell(r, 14).value),
            "rank": norm_code(sh.cell(r, 4).value),
            "unit": "",
            "models": "",
        })
    return entries


def import_ccall_old(
    conn: sqlite3.Connection, path: Path, *, force: bool = False
) -> Dict[str, Any]:
    """Backfill C_CALL rows from the older 2024 table (B0-DICT survey fix).

    Only codes MISSING from the glossary are inserted; existing rows
    (from the newer VN table) are never overwritten. Provenance is the
    glossary_imports log (source_file + sha).

    Returns {status, inserted, entries}. Re-import of an unchanged file
    is skipped unless force=True.
    """
    path = Path(path)
    sha = file_sha256(path)
    if not force and conn.execute(
        "SELECT 1 FROM glossary_imports WHERE source_file = ? AND file_sha256 = ?",
        (path.name, sha),
    ).fetchone():
        return {"status": "skipped", "inserted": 0, "entries": 0}

    entries = parse_ccall_old(path)
    inserted = 0
    for e in entries:
        exists = conn.execute(
            """SELECT 1 FROM error_glossary
               WHERE code_family = 'C_CALL' AND code = ? AND code_sub = ''""",
            (e["code"],),
        ).fetchone()
        if exists:
            continue  # newer VN table stays authoritative
        conn.execute(
            """INSERT INTO error_glossary
               (code_family, code, code_sub, name_ja, name_vi, name_en,
                cause, remedy, rank, unit, models, source_file)
               VALUES ('C_CALL', ?, '', ?, NULL, NULL, ?, ?, ?, NULL, NULL, ?)""",
            (e["code"], e["name_ja"] or None, e["cause"] or None,
             e["remedy"] or None, e["rank"] or None, path.name),
        )
        inserted += 1
    conn.execute(
        """INSERT OR IGNORE INTO glossary_imports (source_file, file_sha256, entries)
           VALUES (?, ?, ?)""",
        (path.name, sha, len(entries)),
    )
    seed_term_aliases(conn)
    conn.commit()
    return {"status": "imported", "inserted": inserted, "entries": len(entries)}


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
    seed_term_aliases(conn)
    conn.commit()
    return {"status": "imported", "inserted": inserted, "updated": updated,
            "entries": len(entries)}


def _row_dict(cur: sqlite3.Cursor, row: Any) -> Dict[str, Any]:
    """Row -> dict, whether or not the connection uses sqlite3.Row."""
    if row is None:
        return {}
    if hasattr(row, "keys"):
        return dict(row)
    return {desc[0]: value for desc, value in zip(cur.description, row)}


def lookup(conn: sqlite3.Connection, family: str, code: str,
           code_sub: str = "") -> Optional[Dict[str, Any]]:
    """Exact lookup by (family, normalized code)."""
    cur = conn.execute(
        "SELECT * FROM error_glossary WHERE code_family = ? AND code = ? AND code_sub = ?",
        (family, norm_code(code), code_sub),
    )
    row = cur.fetchone()
    return _row_dict(cur, row) or None


# ---------------------------------------------------------------------------
# B0-DICT: C_CALL enrichment from Iris2020_Cコール自己診断.xlsx (2025)
# ---------------------------------------------------------------------------

# Per-code blocks on the VN/JP sheets of Iris2020_Cコール自己診断.xlsx:
#   'mã số'|'番号' + serial  -> block start
#   'Cxxxx:'|'Cxxxx：' + name -> code row (col A)
#   'No'|'step'|...         -> step header, then step rows (No/step/cause/action)
_DIAG_SERIAL_RE = re.compile(r"^(mã số|番号)$", re.IGNORECASE)
_DIAG_CODE_RE = re.compile(r"^(C\d{4})\s*[:：]\s*(.*)$")
_DIAG_STEP_NO_RE = re.compile(r"^\d+$")


def _diag_cell_text(value: Any) -> str:
    t = unicodedata.normalize("NFKC", "" if value is None else str(value)).strip()
    return t


def _parse_diag_sheet(ws: Any) -> Dict[str, Dict[str, Any]]:
    """Parse one sheet (VN or JP) into {code: {name, steps:[(no, step, cause, action)]}}."""
    blocks: Dict[str, Dict[str, Any]] = {}
    current: Optional[Dict[str, Any]] = None
    in_steps = False
    for row in ws.iter_rows(values_only=True):
        a = _diag_cell_text(row[0] if len(row) > 0 else None)
        if _DIAG_SERIAL_RE.match(a):
            current = None
            in_steps = False
            continue
        m = _DIAG_CODE_RE.match(a)
        if m:
            code = m.group(1).upper()
            current = {"code": code, "name": m.group(2).strip(), "steps": []}
            if code not in blocks:
                blocks[code] = current
            else:
                current = blocks[code]  # same code repeated: merge into first
            in_steps = False
            continue
        if current is None:
            continue
        b = _diag_cell_text(row[1] if len(row) > 1 else None)
        if not in_steps:
            # Step header row: col A = 'No', col B = 'step'.
            if a.lower() == "no" and b.lower() == "step":
                in_steps = True
            continue
        if not _DIAG_STEP_NO_RE.match(a):
            continue
        c = _diag_cell_text(row[2] if len(row) > 2 else None)
        d = _diag_cell_text(row[3] if len(row) > 3 else None)
        current["steps"].append((a, b, c, d))
    return blocks


def _format_diag_remedy(steps_vn: List[tuple], steps_jp: List[tuple]) -> str:
    def fmt(tag: str, steps: List[tuple]) -> List[str]:
        lines = []
        for no, step, cause, action in steps:
            line = f"{tag} {no}. {step}"
            if cause:
                line += f" — NN: {cause}"
            if action:
                line += f" → XL: {action}"
            lines.append(line)
        return lines
    lines = fmt("VI", steps_vn)
    if steps_jp:
        lines.append("---")
        lines.extend(fmt("JP", steps_jp))
    return "\n".join(lines)


def parse_ccall_diag(path: Path) -> List[Dict[str, Any]]:
    """Parse Iris2020_Cコール自己診断.xlsx (sheets VN + JP, read-only).

    Returns one entry per C-call code: {code, name_vi, name_ja, remedy}.
    The remedy is the per-code diagnostic procedure (step / imagined
    cause / action), which the F4 C_CALL import left empty.
    """
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    try:
        vn = _parse_diag_sheet(wb["VN"]) if "VN" in wb.sheetnames else {}
        jp = _parse_diag_sheet(wb["JP"]) if "JP" in wb.sheetnames else {}
    finally:
        wb.close()
    entries: List[Dict[str, Any]] = []
    for code in sorted(set(vn) | set(jp)):
        v, j = vn.get(code, {}), jp.get(code, {})
        entries.append({
            "code_family": "C_CALL",
            "code": code,
            "code_sub": "",
            "name_ja": (j.get("name") or ""),
            "name_vi": (v.get("name") or ""),
            "name_en": "",
            "cause": "",
            "remedy": _format_diag_remedy(v.get("steps", []), j.get("steps", [])),
            "rank": "",
            "unit": "",
            "models": "",
        })
    return entries


def import_ccall_diag(
    conn: sqlite3.Connection, path: Path, *, force: bool = False
) -> Dict[str, Any]:
    """Enrich C_CALL rows with the diag workbook (B0-DICT).

    Existing C_CALL rows keep their F4 values; only empty fields
    (name_vi, name_ja, remedy) are filled from the workbook. Codes the
    02XC table lacks are inserted as new C_CALL rows. Provenance of the
    enrichment is the glossary_imports log (source_file + sha).

    Returns {status, enriched, inserted, entries}. Re-import of an
    unchanged file is skipped unless force=True.
    """
    path = Path(path)
    sha = file_sha256(path)
    if not force and conn.execute(
        "SELECT 1 FROM glossary_imports WHERE source_file = ? AND file_sha256 = ?",
        (path.name, sha),
    ).fetchone():
        return {"status": "skipped", "enriched": 0, "inserted": 0, "entries": 0}

    entries = parse_ccall_diag(path)
    enriched = inserted = 0
    for e in entries:
        cur = conn.execute(
            """SELECT id, name_ja, name_vi, remedy FROM error_glossary
               WHERE code_family = 'C_CALL' AND code = ? AND code_sub = ''""",
            (e["code"],),
        )
        row = _row_dict(cur, cur.fetchone())
        if not row:
            conn.execute(
                """INSERT INTO error_glossary
                   (code_family, code, code_sub, name_ja, name_vi, remedy,
                    source_file)
                   VALUES ('C_CALL', ?, '', ?, ?, ?, ?)""",
                (e["code"], e["name_ja"] or None, e["name_vi"] or None,
                 e["remedy"] or None, path.name),
            )
            inserted += 1
        else:
            fills = {}
            if not (row["name_vi"] or "").strip() and e["name_vi"]:
                fills["name_vi"] = e["name_vi"]
            if not (row["name_ja"] or "").strip() and e["name_ja"]:
                fills["name_ja"] = e["name_ja"]
            if not (row["remedy"] or "").strip() and e["remedy"]:
                fills["remedy"] = e["remedy"]
            if fills:
                conn.execute(
                    "UPDATE error_glossary SET "
                    + ", ".join(f"{k} = ?" for k in fills)
                    + " WHERE id = ?",
                    (*fills.values(), row["id"]),
                )
                enriched += 1
    conn.execute(
        """INSERT OR IGNORE INTO glossary_imports (source_file, file_sha256, entries)
           VALUES (?, ?, ?)""",
        (path.name, sha, len(entries)),
    )
    seed_term_aliases(conn)
    conn.commit()
    return {"status": "imported", "enriched": enriched, "inserted": inserted,
            "entries": len(entries)}


# ---------------------------------------------------------------------------
# B0-DICT: term normalization (aliases -> canonical code)
# ---------------------------------------------------------------------------

def _ensure_alias_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS term_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT NOT NULL,
            code_family TEXT NOT NULL
                CHECK (code_family IN ('C_CALL', 'F_SYSTEM', 'JAM', 'SCT_ADJ')),
            code TEXT NOT NULL,
            lang TEXT NOT NULL DEFAULT '',
            source_file TEXT NOT NULL,
            UNIQUE (alias, code_family, code)
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_alias_alias ON term_aliases (alias)"
    )


def seed_term_aliases(conn: sqlite3.Connection) -> int:
    """Index every glossary name spelling as an alias of its code.

    Only real spellings from the imported sources (no invented terms).
    Idempotent: INSERT OR IGNORE. Returns the number of new aliases.
    """
    _ensure_alias_table(conn)
    added = 0
    for row in conn.execute(
        "SELECT code_family, code, name_ja, name_vi, name_en, source_file"
        " FROM error_glossary"
    ):
        for lang, name in (("ja", row[2]), ("vi", row[3]), ("en", row[4])):
            if not name:
                continue
            alias = norm_code(name)
            if len(alias) < 2 or len(alias) > 120:
                continue
            cur = conn.execute(
                """INSERT OR IGNORE INTO term_aliases
                   (alias, code_family, code, lang, source_file)
                   VALUES (?, ?, ?, ?, ?)""",
                (alias, row[0], row[1], lang, row[5]),
            )
            added += cur.rowcount
    conn.commit()
    return added


_JAM_PREFIX_RE = re.compile(r"^JAM(\d+)$")


def canonical_term(conn: sqlite3.Connection, name: str) -> Optional[Tuple[str, str]]:
    """Resolve a variant name spelling to (code_family, code).

    Falls back to a direct code match, including the JAM family-prefix
    form: history rows write 'JAM4709' while the JAM workbook stores bare
    numbers ('4709'). None = not in the dictionary.
    """
    _ensure_alias_table(conn)
    alias = norm_code(name)
    row = conn.execute(
        "SELECT code_family, code FROM term_aliases WHERE alias = ? LIMIT 1",
        (alias,),
    ).fetchone()
    if row:
        return (row[0], row[1])
    candidates = [alias]
    m = _JAM_PREFIX_RE.match(alias)
    if m:
        candidates.append(m.group(1))  # 'JAM4709' -> bare '4709'
    for family in CODE_FAMILIES:
        for cand in candidates:
            if lookup(conn, family, cand):
                return (family, cand)
    return None


def suggest_terms(
    conn: sqlite3.Connection, prefix: str, *, limit: int = 10
) -> List[Dict[str, Any]]:
    """Name-prefix suggestions for the B0-FORM input hints.

    Returns [{alias, code_family, code, meaning, source_file}] ordered by
    alias. The alias is the spelling as written in the source file.
    """
    _ensure_alias_table(conn)
    like = norm_code(prefix).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = conn.execute(
        """SELECT ta.alias, ta.code_family, ta.code,
                  COALESCE(eg.name_vi, eg.name_ja, eg.name_en, '') AS meaning,
                  eg.source_file
           FROM term_aliases ta
           LEFT JOIN error_glossary eg
             ON eg.code_family = ta.code_family AND eg.code = ta.code
                AND eg.code_sub = ''
           WHERE ta.alias LIKE ? ESCAPE '\\'
           ORDER BY ta.alias LIMIT ?""",
        (like + "%", limit),
    ).fetchall()
    return [
        {"alias": r[0], "code_family": r[1], "code": r[2],
         "meaning": r[3] or "", "source_file": r[4] or ""}
        for r in rows
    ]


# ---------------------------------------------------------------------------
# B0-DICT: acceptance metric — % of DB codes found in the glossary
# ---------------------------------------------------------------------------

_CODE_LIKE_RE = re.compile(r"[0-9]")


def _codes_in_error_cases(conn: sqlite3.Connection) -> List[str]:
    """Distinct normalized code-like values stored in error_cases.

    Collects error_code_c, error_code_h (only values containing a digit —
    plain categories like 'C CALL' are not codes) and error_code_i.
    """
    cols = {row[1] for row in conn.execute("PRAGMA table_info(error_cases)")}
    select_cols = ["error_code_c", "error_code_h"]
    if "error_code_i" in cols:
        select_cols.append("error_code_i")
    codes = set()
    for row in conn.execute(
        f"SELECT {', '.join(select_cols)} FROM error_cases"
    ):
        for value in row:
            if not value:
                continue
            norm = norm_code(value)
            if norm and _CODE_LIKE_RE.search(norm):
                codes.add(norm)
    return sorted(codes)


def glossary_coverage(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Ticket acceptance metric: % of error codes in the DB found in the glossary.

    A code counts as matched when any family has it or an alias resolves
    to it. Returns {total, matched, percent, unmatched} where unmatched
    is a sample (<= 20) for the B0-MEASURE follow-up.
    """
    from . import store  # local import: keep glossary importable standalone

    store.init_db(conn)  # idempotent; ensures error_code_i exists (schema only)
    codes = _codes_in_error_cases(conn)
    unmatched: List[str] = []
    for code in codes:
        hit = canonical_term(conn, code)
        if hit is None:
            unmatched.append(code)
    matched = len(codes) - len(unmatched)
    percent = round(matched / len(codes) * 100, 2) if codes else 0.0
    return {
        "total": len(codes),
        "matched": matched,
        "percent": percent,
        "unmatched": unmatched[:20],
    }
