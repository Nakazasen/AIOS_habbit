"""F1: A-Y column mapping for KDTPS error case sheets.

Business rules sourced from the legacy kdtps-error-manager
(src/utils/config.py, src/core/excel_handler.py, src/ui/import_dialog.py):

- Column indices are 0-based: A=0, C=2, D=3, G=6, H=7, N=13, O=14,
  S=18, V=21, Y=24.
- Cells filled with light green RGB(146, 208, 80) are never overwritten
  (SKIP_COLOR_RGB in the legacy app).
- sheet_type is one of 'Máy in' / 'KIT'.
- Dedup key: UNIQUE(no_dvd, sheet_type, department).
- Line filter applies on column D.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

# 0-based column index -> semantic field name (legacy config.py)
COLUMN_MAP: Dict[int, str] = {
    0: "no_dvd",           # A: issue number
    2: "machine_type",     # C: machine type
    3: "line",             # D: production line
    6: "error_code_c",     # G: Cxxx error code
    7: "error_code_h",     # H: Jxxx/Fxxx error code
    13: "investigation",   # N: investigation content
    14: "department",      # O: responsible department
    18: "handler",         # S: person in charge
    21: "is_completed",    # V: completed ('o' = done)
    24: "needs_jp_support",  # Y: needs JP support ('o')
}

# Light green fill meaning "do not overwrite" (legacy SKIP_COLOR_RGB)
GREEN_SKIP_RGB: Tuple[int, int, int] = (146, 208, 80)

SHEET_TYPES: Tuple[str, str] = ("Máy in", "KIT")

# Markers meaning "done" / "needs JP support" (case-insensitive, stripped)
POSITIVE_MARKS = {"o", "○", "〇", "x"}


def col_letter(index: int) -> str:
    """0-based column index -> Excel letter (0 -> 'A')."""
    letter = ""
    n = index + 1
    while n:
        n, r = divmod(n - 1, 26)
        letter = chr(ord("A") + r) + letter
    return letter


def is_green_skip(rgb: Tuple[int, int, int] | None) -> bool:
    """True when a cell fill is the legacy 'do not overwrite' green."""
    return rgb is not None and tuple(rgb) == GREEN_SKIP_RGB


def is_positive_mark(value: Any) -> bool:
    """True for completion / JP-support marks ('o', variants)."""
    if value is None:
        return False
    return str(value).strip().lower() in POSITIVE_MARKS


def normalize_row(cells: List[Any]) -> Dict[str, Any]:
    """Map a raw A-Y row (list of cell values) to semantic fields.

    Always returns every mapped field (missing -> None) plus
    ``raw`` (all 25 values as a letter-keyed dict) for fidelity.
    """
    out: Dict[str, Any] = {field: None for field in COLUMN_MAP.values()}
    raw: Dict[str, Any] = {}
    for i in range(25):
        letter = col_letter(i)
        value = cells[i] if i < len(cells) else None
        raw[letter] = value
        field = COLUMN_MAP.get(i)
        if field is not None:
            out[field] = value
    # Normalize the two marker columns to '' / 'o'
    out["is_completed"] = "o" if is_positive_mark(out["is_completed"]) else ""
    out["needs_jp_support"] = "o" if is_positive_mark(out["needs_jp_support"]) else ""
    out["raw"] = raw
    return out


# ---------------------------------------------------------------------------
# Second format profile: 29-column history sheet ("History KDTPS" in
# Loi KDTPS.xlsx). Recon 2026-09-27: the legacy A-Y mapping does NOT apply
# here — column semantics differ (S = part code not handler, V = LKATQT
# not completed, Y = unhold date not JP support, true line is E not D).
# ---------------------------------------------------------------------------

# 0-based column index -> semantic field for the 29-column history format
HISTORY_29_MAP: Dict[int, str] = {
    3: "machine_type",    # D: machine type
    4: "line",            # E: production line (the true line column)
    7: "error_code_h",    # H: error category as listed (ERROR / JAM / ...)
    15: "department",     # P: responsible department
}

# Columns with no semantic slot in error_cases; kept in raw_json only.
# G serial, J occurrences, X/Y HOLD dates, Z reproducibility, AA cause,
# AB kaizen, AC report link.
#
# B0-DICT: column I (\"不具合現象 / Hiện trạng lỗi\", the phenomenon text)
# usually embeds the REAL error code, e.g. LCD画面にF000表示, while column H
# only carries the group ('F CALL'). The first code-shaped token of I is
# extracted into error_cases.error_code_i at import time
# (see extract_code_from_text) so the form-vs-history dedup can match on it.

#: Real occurrence date for the 29-column history sheet. Recon 2026-10-01
#: (ticket `date-map`): C "生産日 / Ngày tháng sản xuất" is a real date in
#: 100% of the 15.737 data rows (datetime 00:00), year always matching
#: column A. X ("HOLD日 / Ngày Hold") and Y ("HOLD解除日 / Ngày giải Hold")
#: are hold dates, not occurrence dates, and 97.9% / 98.5% of them are the
#: empty placeholder "ー" in the source -- they stay in raw_json only.
HISTORY_29_DATE_INDEX: int = 2  # column C

#: Source placeholder values meaning "no date given".
DATE_NA_MARKS: Tuple[str, ...] = ("ー", "－", "—", "–", "-", "--", "/", "//")

# B0-DICT: code shapes as they appear embedded in the phenomenon text
# (history_29 column I). Order matters: JAMxxxx before the bare hex-4
# family so 'JAM4012' is not truncated; (?!\d) avoids matching a prefix
# of a longer digit run.
_RE_REAL_CODE = re.compile(r"(JAM\d{4}|C\d{4}|F[0-9A-F]{3,4})(?!\d)")

# Real F-family codes without any digit (wildcard templates from the
# UWCA workbook). Anything else F+hex-letters-only is an English word
# ('FEED', 'FACE', 'FADE'), not a code.
_F_NO_DIGIT_TEMPLATES = frozenset({"FCAX", "FCFX", "FDEX", "FEEX"})


def extract_code_from_text(value: Any) -> Optional[str]:
    """Extract the real error code embedded in free text (e.g. column I).

    Returns the first code-shaped token (JAM4012, C4701, F000), NFKC/upper
    normalized, or None when the text carries no code. Never guesses: only
    exact shape matches count. F-family candidates with no digit at all
    (e.g. the English word 'FEED') are skipped unless they are one of the
    real no-digit templates from the UWCA workbook.
    """
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", str(value)).upper()
    for m in _RE_REAL_CODE.finditer(text):
        tok = m.group(1)
        if tok.startswith("F") and not any(ch.isdigit() for ch in tok):
            if tok not in _F_NO_DIGIT_TEMPLATES:
                continue  # English word, not an error code
        return tok
    return None


def parse_date_cell(value: Any) -> Optional[str]:
    """Parse a source date cell into an ISO 'YYYY-MM-DD' string, or None.

    Accepts the types/formats that occur in the workbook: datetime/date
    objects (openpyxl) and written text (ISO, YYYY/M/D, YYYY.M.D,
    YYYY年M月D日, with an optional trailing 日). Placeholders ('ー', ...)
    and unparseable text return None -- never guesses a date.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text or text in DATE_NA_MARKS:
        return None
    text = text.rstrip("日")
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        pass
    for fmt in ("%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def history_no_dvd(year: Any, no: Any) -> str:
    """Dedup-visible case id for history rows: 'year/NO' (A + B)."""
    y = "" if year is None else str(year).strip()
    n = "" if no is None else str(no).strip()
    return f"{y}/{n}"


def normalize_history_row(cells: List[Any]) -> Dict[str, Any]:
    """Map a raw 29-column history row to semantic fields.

    Investigation prefers the Vietnamese column O, falling back to
    Japanese column N. ``no_dvd`` is derived as 'year/NO' from A+B.
    ``occurred_at`` is the ISO occurrence date parsed from column C
    (None when the source cell is empty/unparseable).
    """
    out: Dict[str, Any] = {
        "no_dvd": None, "machine_type": None, "line": None,
        "error_code_c": None, "error_code_h": None, "error_code_i": None,
        "investigation": None,
        "department": None, "handler": None,
        "is_completed": "", "needs_jp_support": "",
        "occurred_at": None,
    }
    raw: Dict[str, Any] = {}
    for i in range(29):
        letter = col_letter(i)
        value = cells[i] if i < len(cells) else None
        raw[letter] = value
        field = HISTORY_29_MAP.get(i)
        if field is not None:
            out[field] = value
    out["no_dvd"] = history_no_dvd(raw.get("A"), raw.get("B"))
    out["occurred_at"] = parse_date_cell(raw.get("C"))
    # B0-DICT: real code embedded in the phenomenon text (column I).
    out["error_code_i"] = extract_code_from_text(raw.get("I"))
    vn = raw.get("O")
    jp = raw.get("N")
    out["investigation"] = vn if vn not in (None, "") else jp
    out["raw"] = raw
    return out
