"""B0-FORM: standard Step-0 data-entry form — 12 fields, written straight to the DB.

Replaces per-FY stray Excel files for new reports: the user fills the form
(inside the chat answer area), the data is validated, then one new row is
written to ``error_cases`` — no intermediate file, no stray files created.

The 12 standard fields (per ticket B0-FORM):
    Model / Line / Process stage / Error name / Error code / Phenomenon /
    Investigation / Cause / Countermeasure / Analysis dept /
    Occurred date – closed date / Report link

Column mapping:
    Model -> machine_type | Line -> line | Analysis dept -> department
    Investigation -> investigation | Occurred date -> occurred_at
    Error code -> error_code_c (Cxxx codes) or error_code_h (everything else)
    7 new columns (additive migration, old DBs untouched otherwise):
    Process stage -> process_stage | Error name -> error_name
    Phenomenon -> phenomenon | Cause -> cause | Countermeasure -> countermeasure
    Closed date -> closed_at | Report link -> report_link

Validation rules:
    - 5 required fields: error code, phenomenon, cause, countermeasure,
      process stage — missing blocks the write (never touches the DB).
    - closed date >= occurred date (when both are given) — otherwise blocked.
    - unparseable date -> blocked (fail-closed, avoids storing garbage dates).
    - error code is checked against error_glossary — unknown codes only
      WARN, never block (ticket B0-DICT completes the dictionary later).
    - duplicate (model, line, error code, occurred date) already in the DB ->
      WARN and do NOT insert twice.

Provenance: every manual case belongs to the shared ``FORM-nhap-lieu``
batch (source_file='FORM-nhap-lieu', sheet_name='form'); the ticket number
is auto-generated as ``FORM-YYYYMMDD-NNNN`` into no_dvd (NOT NULL column).
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from . import column_map
from . import glossary as _glossary
from . import auto_classifier as _auto_classifier
from aios_habit.chat_action import normalize_text

# ---------------------------------------------------------------------------
# Định nghĩa 12 trường
# ---------------------------------------------------------------------------

FIELDS: Tuple[Dict[str, Any], ...] = (
    {"key": "model", "label": "Model", "required": False, "column": "machine_type"},
    {"key": "line", "label": "Line", "required": False, "column": "line"},
    {"key": "cong_doan", "label": "Công đoạn", "required": True, "column": "process_stage"},
    {"key": "ten_loi", "label": "Tên lỗi", "required": False, "column": "error_name"},
    {"key": "error_code", "label": "Error code", "required": True, "column": None},
    {"key": "hien_tuong", "label": "Hiện tượng", "required": True, "column": "phenomenon"},
    {"key": "noi_dung_dieu_tra", "label": "Nội dung điều tra", "required": False, "column": "investigation"},
    {"key": "nguyen_nhan", "label": "Nguyên nhân", "required": True, "column": "cause"},
    {"key": "doi_sach", "label": "Đối sách", "required": True, "column": "countermeasure"},
    {"key": "bo_phan_pt", "label": "Bộ phận PT", "required": False, "column": "department"},
    {"key": "ngay_phat_sinh", "label": "Ngày phát sinh", "required": False, "column": "occurred_at"},
    {"key": "ngay_dong", "label": "Ngày đóng", "required": False, "column": "closed_at"},
    {"key": "link_bao_cao", "label": "Link báo cáo", "required": False, "column": "report_link"},
)

#: key -> field spec.
FIELD_BY_KEY: Dict[str, Dict[str, Any]] = {f["key"]: f for f in FIELDS}

#: New columns added by B0-FORM (additive migration for old DBs).
FORM_COLUMNS: Tuple[Tuple[str, str], ...] = (
    ("process_stage", "TEXT"),    # Công đoạn
    ("error_name", "TEXT"),       # Tên lỗi
    ("phenomenon", "TEXT"),       # Hiện tượng
    ("cause", "TEXT"),            # Nguyên nhân
    ("countermeasure", "TEXT"),  # Đối sách
    ("closed_at", "TEXT"),        # Ngày đóng (ISO)
    ("report_link", "TEXT"),      # Link báo cáo
)

#: Shared batch name for every manual form entry.
FORM_BATCH_SOURCE = "FORM-nhap-lieu"
FORM_BATCH_SHA = "FORM"  # sentinel: không có file nguồn
FORM_BATCH_SHEET = "form"

#: The 5 required fields (per ticket).
REQUIRED_KEYS: Tuple[str, ...] = tuple(f["key"] for f in FIELDS if f["required"])

# Label aliases when parsing a form pasted from chat (normalized: no diacritics).
_LABEL_ALIASES: Dict[str, str] = {
    "model": "model",
    "line": "line",
    "cong doan": "cong_doan",
    "cong doan san xuat": "cong_doan",
    "ten loi": "ten_loi",
    "error code": "error_code",
    "ma loi": "error_code",
    "hien tuong": "hien_tuong",
    "hien trang loi": "hien_tuong",
    "noi dung dieu tra": "noi_dung_dieu_tra",
    "tinh trang dieu tra": "noi_dung_dieu_tra",
    "nguyen nhan": "nguyen_nhan",
    "doi sach": "doi_sach",
    "doi sach giai quyet": "doi_sach",
    "bo phan pt": "bo_phan_pt",
    "bo phan phu trach": "bo_phan_pt",
    "ngay phat sinh": "ngay_phat_sinh",
    "ngay san xuat": "ngay_phat_sinh",
    "ngay dong": "ngay_dong",
    "link bao cao": "link_bao_cao",
    "link": "link_bao_cao",
    "bao cao link": "link_bao_cao",
}


def _norm_label(text: str) -> str:
    return normalize_text(text)


def ensure_form_schema(conn: sqlite3.Connection) -> None:
    """Add the form columns when an old DB lacks them (idempotent, ADD COLUMN only)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(error_cases)")}
    for name, ddl in FORM_COLUMNS:
        if name not in cols:
            conn.execute(f"ALTER TABLE error_cases ADD COLUMN {name} {ddl}")
    conn.commit()


# ---------------------------------------------------------------------------
# Error code: tách cột + đối chiếu từ điển
# ---------------------------------------------------------------------------

_RE_C_CODE = re.compile(r"C\d{3,4}")
_RE_F_CODE = re.compile(r"F[0-9A-FX]{3,4}")
_RE_HEX4 = re.compile(r"[0-9A-F]{4}")
_RE_HEX2 = re.compile(r"[0-9A-F]{2}")


def split_error_code(code: str) -> Tuple[Optional[str], Optional[str]]:
    """Split a normalized error code into (error_code_c, error_code_h).

    Legacy schema convention: column G = Cxxx codes, column H = everything
    else (Fxxx/Jxxx/hex). No guessing: a code matching no pattern is kept
    verbatim in column H so it stays searchable/dedupable.
    """
    norm = _glossary.norm_code(code)
    if _RE_C_CODE.fullmatch(norm):
        return norm, None
    return None, norm


def _glossary_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='error_glossary'"
    ).fetchone()
    return row is not None


def lookup_error_code(conn: sqlite3.Connection, code: str) -> Optional[Dict[str, Any]]:
    """Look up an error code in the glossary (all families). None = unknown / no glossary.

    Exact match first; B0-DICT: falls back to the term-alias index
    (variant name spellings -> canonical code, JAM family-prefix form
    like 'JAM4709'); F_SYSTEM additionally supports the X wildcard stored
    in the dictionary (e.g. 'F10X' matches 'F100').
    """
    if not _glossary_table_exists(conn):
        return None
    norm = _glossary.norm_code(code)
    for family in _glossary.CODE_FAMILIES:
        hit = _glossary.lookup(conn, family, norm)
        if hit:
            return hit
    resolved = _glossary.canonical_term(conn, norm)
    if resolved:
        hit = _glossary.lookup(conn, resolved[0], resolved[1])
        if hit:
            return hit
    # F_SYSTEM wildcard: 'F10X' ~ 'F100'.
    for row in conn.execute(
        "SELECT * FROM error_glossary WHERE code_family='F_SYSTEM' AND code LIKE '%X%'"
    ):
        pattern = "^" + re.escape(row["code"]).replace("X", "[0-9A-F]") + "$"
        if re.fullmatch(pattern, norm):
            return dict(row)
    return None


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


class ValidationResult:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> Dict[str, List[str]]:
        return {"errors": list(self.errors), "warnings": list(self.warnings)}


def validate_form(data: Dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> ValidationResult:
    """Validate form data. errors block the write; warnings do not."""
    res = ValidationResult()
    get = lambda k: data.get(k)

    for key in REQUIRED_KEYS:
        if _blank(get(key)):
            label = FIELD_BY_KEY[key]["label"]
            res.errors.append(f"Thiếu trường bắt buộc: {label}.")

    occurred_raw, closed_raw = get("ngay_phat_sinh"), get("ngay_dong")
    occurred = closed = None
    if not _blank(occurred_raw):
        occurred = column_map.parse_date_cell(occurred_raw)
        if occurred is None:
            res.errors.append(
                "Không hiểu 'Ngày phát sinh' — dùng định dạng YYYY-MM-DD "
                "(vd. 2026-10-01)."
            )
    if not _blank(closed_raw):
        closed = column_map.parse_date_cell(closed_raw)
        if closed is None:
            res.errors.append(
                "Không hiểu 'Ngày đóng' — dùng định dạng YYYY-MM-DD (vd. 2026-10-01)."
            )
    if occurred and closed and closed < occurred:
        res.errors.append(
            f"'Ngày đóng' ({closed}) phải >= 'Ngày phát sinh' ({occurred})."
        )

    if not _blank(get("error_code")) and conn is not None:
        if lookup_error_code(conn, str(get("error_code"))) is None:
            res.warnings.append(
                f"Mã lỗi '{str(get('error_code')).strip()}' lạ — chưa có trong "
                "từ điển. Vẫn ghi nhận, nên bổ sung từ điển sau (vé B0-DICT)."
            )

    return res


# ---------------------------------------------------------------------------
# Chống trùng
# ---------------------------------------------------------------------------

def _has_error_code_i(conn: sqlite3.Connection) -> bool:
    """True when the DB was built/migrated with the B0-DICT error_code_i column."""
    return any(
        row[1] == "error_code_i"
        for row in conn.execute("PRAGMA table_info(error_cases)")
    )


def find_duplicate(
    conn: sqlite3.Connection,
    *,
    model: Any,
    line: Any,
    error_code: str,
    ngay_phat_sinh: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Find an existing case with the same (model, line, error code, occurred date).

    The error code matches against error_code_c, error_code_h AND
    error_code_i (B0-DICT): history rows store the group in column H
    ('C CALL') while the real code (e.g. C4701) was embedded in the
    phenomenon text (column I) — extracted into error_code_i at import.
    """
    norm = _glossary.norm_code(error_code)
    occurred = (
        column_map.parse_date_cell(ngay_phat_sinh)
        if not _blank(ngay_phat_sinh)
        else None
    )
    code_clauses = ["error_code_c = ?", "error_code_h = ?"]
    params: List[Any] = [
        None if _blank(model) else str(model).strip(),
        None if _blank(line) else str(line).strip(),
        norm,
        norm,
    ]
    if _has_error_code_i(conn):
        code_clauses.append("error_code_i = ?")
        params.append(norm)
    params.extend([occurred, occurred])
    row = conn.execute(
        f"""SELECT id, no_dvd, machine_type, line, error_code_c, error_code_h,
                   occurred_at
           FROM error_cases
           WHERE COALESCE(machine_type, '') = COALESCE(?, '')
             AND COALESCE(line, '') = COALESCE(?, '')
             AND ({' OR '.join(code_clauses)})
             AND ((occurred_at = ?) OR (occurred_at IS NULL AND ? IS NULL))
           LIMIT 1""",
        params,
    ).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Ghi DB
# ---------------------------------------------------------------------------

def ensure_form_batch(conn: sqlite3.Connection) -> int:
    """Shared batch for manual entries (created once, then reused)."""
    from . import store

    batch_id = store.start_batch(
        conn,
        source_file=FORM_BATCH_SOURCE,
        file_sha256=FORM_BATCH_SHA,
        sheet_name=FORM_BATCH_SHEET,
        notes="Ca nhập tay qua form chuẩn B0-FORM (không qua file Excel).",
    )
    return batch_id


def _next_no_dvd(conn: sqlite3.Connection) -> str:
    prefix = f"FORM-{date.today():%Y%m%d}-"
    seq = 1
    while True:
        candidate = f"{prefix}{seq:04d}"
        exists = conn.execute(
            "SELECT 1 FROM error_cases WHERE no_dvd = ?", (candidate,)
        ).fetchone()
        if not exists:
            return candidate
        seq += 1


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


# ---------------------------------------------------------------------------
# B5: phan loai tu dong + canh bao tai phat
# ---------------------------------------------------------------------------

#: Recurrence window for the entry form: 7 days — a recurrence across
#: shifts/days is what the reporter needs ("loi nay da phat sinh N lan").
_FORM_RECURRENCE_WINDOW_HOURS = 168.0


def _auto_classify_new_case(
    conn: sqlite3.Connection, data: Dict[str, Any], error_code: str
) -> Optional[Dict[str, Any]]:
    """B5: classify + compare against history + detect recurrence.

    Best-effort: never raises, never blocks the insert. Returns None when
    the lookup cannot run. Runs BEFORE the INSERT so detect_recurrence's
    "+1 = the new case" counting stays correct.
    """
    try:
        out = _auto_classifier.classify_new_error(
            conn,
            error_code,
            phenomenon=str(data.get("hien_tuong") or ""),
            investigation=str(data.get("noi_dung_dieu_tra") or ""),
            machine_type=_clean(data.get("model")),
            line=_clean(data.get("line")),
            window_hours=_FORM_RECURRENCE_WINDOW_HOURS,
        )
    except Exception:
        return None
    cls = out["classification"]
    rec = out["recurrence_alert"]
    return {
        "nhom_nguyen_nhan": cls.nhom_nguyen_nhan,
        "nhom_nguyen_nhan_vi": _auto_classifier.CAUSE_LABEL_VI.get(
            cls.nhom_nguyen_nhan, cls.nhom_nguyen_nhan
        ),
        "cong_doan": cls.cong_doan,
        "bo_phan": cls.bo_phan,
        "confidence": cls.confidence,
        "reasons": list(cls.reasons),
        "history_checked": bool(out.get("history_checked")),
        "history_match_count": len(out.get("history_matches") or []),
        "recurrence": (
            {
                "count": rec.count,
                "window_hours": rec.window_hours,
                "message_vi": rec.message_vi,
                "suggested_remedy": rec.suggested_remedy,
                "suggested_from": rec.suggested_from,
            }
            if rec is not None
            else None
        ),
    }


def submit_case(
    conn: sqlite3.Connection, data: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate + dedup + insert one new case. Never inserts twice.

    Returns a dict: status in {'inserted', 'duplicate', 'blocked'},
    case_id / no_dvd (when inserted), errors, warnings.
    """
    ensure_form_schema(conn)
    validation = validate_form(data, conn)
    if not validation.ok:
        return {
            "status": "blocked",
            "case_id": None,
            "no_dvd": None,
            "errors": validation.errors,
            "warnings": validation.warnings,
        }

    error_code = str(data.get("error_code")).strip()
    dup = find_duplicate(
        conn,
        model=_clean(data.get("model")),
        line=_clean(data.get("line")),
        error_code=error_code,
        ngay_phat_sinh=_clean(data.get("ngay_phat_sinh")),
    )
    if dup is not None:
        return {
            "status": "duplicate",
            "case_id": int(dup["id"]),
            "no_dvd": dup["no_dvd"],
            "errors": [],
            "warnings": [
                "Trùng ca đã có (cùng Model, Line, Error code, Ngày phát sinh) "
                f"— mã phiếu {dup['no_dvd']}. Không nhập đúp."
            ],
        }

    code_c, code_h = split_error_code(error_code)
    occurred = column_map.parse_date_cell(data.get("ngay_phat_sinh"))
    closed = column_map.parse_date_cell(data.get("ngay_dong"))
    batch_id = ensure_form_batch(conn)
    no_dvd = _next_no_dvd(conn)

    # B5: run BEFORE the INSERT — detect_recurrence counts the new case
    # itself as +1, so the row must not be in the DB yet.
    auto = _auto_classify_new_case(conn, data, error_code)

    form_snapshot = {
        f["key"]: _clean(data.get(f["key"])) for f in FIELDS
    }
    raw = {
        "format": "form",
        "source": "manual-form",
        "form": form_snapshot,
    }

    cur = conn.execute(
        """INSERT INTO error_cases
           (batch_id, source_row, no_dvd, sheet_type, department, machine_type,
            line, error_code_c, error_code_h, investigation, handler,
            is_completed, needs_jp_support, occurred_at, process_stage,
            error_name, phenomenon, cause, countermeasure, closed_at,
            report_link, raw_json, skip_cells)
           VALUES (?, NULL, ?, NULL, ?, ?, ?, ?, ?, ?, NULL, '', '', ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]')""",
        (
            batch_id,
            no_dvd,
            _clean(data.get("bo_phan_pt")),
            _clean(data.get("model")),
            _clean(data.get("line")),
            code_c,
            code_h,
            _clean(data.get("noi_dung_dieu_tra")),
            occurred,
            _clean(data.get("cong_doan")),
            _clean(data.get("ten_loi")),
            _clean(data.get("hien_tuong")),
            _clean(data.get("nguyen_nhan")),
            _clean(data.get("doi_sach")),
            closed,
            _clean(data.get("link_bao_cao")),
            json.dumps(raw, ensure_ascii=False),
        ),
    )
    conn.execute(
        "UPDATE import_batches SET rows_imported = rows_imported + 1, "
        "rows_read = rows_read + 1 WHERE id = ?",
        (batch_id,),
    )
    conn.commit()
    return {
        "status": "inserted",
        "case_id": int(cur.lastrowid),
        "no_dvd": no_dvd,
        "errors": [],
        "warnings": validation.warnings,
        # B5: phan loai tu dong + doi chieu lich su + canh bao tai phat
        # (None when the best-effort lookup could not run).
        "auto": auto,
    }


# ---------------------------------------------------------------------------
# Render / parse form cho chat
# ---------------------------------------------------------------------------

def render_blank_form() -> str:
    """Blank form template (markdown) rendered inside the chat answer area."""
    lines = [
        "### Form nhập báo cáo lỗi mới (Bước 0)",
        "",
        "Điền các dòng dưới đây rồi gửi lại, **bắt đầu bằng: `nộp báo cáo`**.",
        "Trường có * là bắt buộc. Ngày viết dạng YYYY-MM-DD.",
        "",
    ]
    for f in FIELDS:
        mark = " *" if f["required"] else ""
        lines.append(f"- **{f['label']}**{mark}:")
    lines += [
        "",
        "_Mã lỗi lạ (không có trong từ điển) vẫn ghi nhận được, chỉ cảnh báo._",
    ]
    return "\n".join(lines)


def parse_form_text(text: str) -> Dict[str, str]:
    """Parse a filled form (lines of 'Label: value') into a keyed dict."""
    out: Dict[str, str] = {}
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip().lstrip("-•*").strip()
        if ":" not in line:
            continue
        label_part, _, value = line.partition(":")
        key = _LABEL_ALIASES.get(_norm_label(label_part))
        if key is None or key in out:
            continue
        value = value.strip()
        if value:
            out[key] = value
    return out


def looks_like_filled_form(text: str) -> bool:
    """Guess whether the text is a filled form (>= 3 valued fields)."""
    return len(parse_form_text(text)) >= 3


def read_case(conn: sqlite3.Connection, case_id: int) -> Optional[Dict[str, Any]]:
    """Re-read a just-written case (all 12 fields) for verification."""
    row = conn.execute(
        "SELECT * FROM error_cases WHERE id = ?", (case_id,)
    ).fetchone()
    return dict(row) if row else None
