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

from typing import Any, Dict, List, Tuple

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
# G serial, I defect description, J occurrences, X/Y hold dates,
# Z reproducibility, AA cause, AB kaizen, AC report link.


def history_no_dvd(year: Any, no: Any) -> str:
    """Dedup-visible case id for history rows: 'year/NO' (A + B)."""
    y = "" if year is None else str(year).strip()
    n = "" if no is None else str(no).strip()
    return f"{y}/{n}"


def normalize_history_row(cells: List[Any]) -> Dict[str, Any]:
    """Map a raw 29-column history row to semantic fields.

    Investigation prefers the Vietnamese column O, falling back to
    Japanese column N. ``no_dvd`` is derived as 'year/NO' from A+B.
    """
    out: Dict[str, Any] = {
        "no_dvd": None, "machine_type": None, "line": None,
        "error_code_c": None, "error_code_h": None, "investigation": None,
        "department": None, "handler": None,
        "is_completed": "", "needs_jp_support": "",
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
    vn = raw.get("O")
    jp = raw.get("N")
    out["investigation"] = vn if vn not in (None, "") else jp
    out["raw"] = raw
    return out
