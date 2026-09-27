"""F3: field-completeness measurement for error_cases (Step 0 data quality).

Read-only: measures, per field, the share of rows where the field is
filled (non-null and non-blank). Fields with no mapping for a row's
format (e.g. cause/fix/date in legacy A-Y rows) are reported as n/a and
excluded from the F3b gate.

Row format is detected per row from raw_json keys: history rows carry
letters Z..AC (29 columns), legacy rows only A..Y (25 columns).

F3b gate: when any CORE field is filled in less than F3B_THRESHOLD (90%)
of its applicable rows, needs_f3b=True — open ticket F3b (backfill
campaign) instead of silently shipping thin data.

This module never touches the RAG index.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

#: Completeness below this rate (percent) opens the F3b backfill ticket.
F3B_THRESHOLD: float = 90.0

#: Fields that must be >= F3B_THRESHOLD filled, or F3b opens.
CORE_FIELDS: Tuple[str, ...] = (
    "no_dvd",
    "machine_type",
    "line",
    "investigation",
    "cause",
    "fix",
)

#: Fields measured, in report order.
MEASURED_FIELDS: Tuple[str, ...] = (
    "no_dvd",
    "machine_type",
    "line",
    "department",
    "handler",
    "date",
    "investigation",
    "cause",
    "fix",
    "source_row",
)

# Field -> spec. "column" reads the error_cases table directly;
# "raw" reads a letter from raw_json per row format (None = not mapped,
# the field is n/a for that format).
_FIELD_SPECS: Dict[str, Dict[str, Any]] = {
    "no_dvd": {"column": "no_dvd"},
    "machine_type": {"column": "machine_type"},
    "line": {"column": "line"},
    "department": {"column": "department"},
    "handler": {"column": "handler"},
    "investigation": {"column": "investigation"},
    "source_row": {"column": "source_row"},
    # History sheet: C = production date, AA = cause, AB = kaizen/fix.
    # (recon 2026-09-27; AB filled only ~56.8% in the real file.)
    "date": {"raw": {"legacy": None, "history_29": "C"}},
    "cause": {"raw": {"legacy": None, "history_29": "AA"}},
    "fix": {"raw": {"legacy": None, "history_29": "AB"}},
}

# Raw letters that only exist in the 29-column history format.
_HISTORY_LETTERS = frozenset({"Z", "AA", "AB", "AC"})

FORMATS = ("legacy", "history_29")


def _filled(value: Any) -> bool:
    """A field counts as filled when non-null and non-blank."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _detect_format(raw: Dict[str, Any]) -> str:
    """history_29 when raw_json carries letters Z..AC, else legacy."""
    if not isinstance(raw, dict):
        return "legacy"
    return "history_29" if (set(raw) & _HISTORY_LETTERS) else "legacy"


def _field_value(
    row: sqlite3.Row, raw: Dict[str, Any], row_format: str, field: str
) -> Tuple[bool, Any]:
    """(applicable, value) for one field on one row.

    applicable=False when the field has no mapping for the row's format
    (reported as n/a, excluded from the F3b gate).
    """
    spec = _FIELD_SPECS[field]
    if "column" in spec:
        return True, row[spec["column"]]
    letter = spec["raw"].get(row_format)
    if letter is None:
        return False, None
    return True, raw.get(letter)


def measure(
    conn: sqlite3.Connection,
    *,
    format: Optional[str] = None,
    batch_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Measure field completeness over error_cases (read-only).

    Returns a dict with total rows in scope, per-field
    {filled, applicable, rate} (rate None when the field is n/a for the
    whole scope), the F3b gate flag and the failing core fields.
    """
    if format is not None and format not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS} or None")

    sql = (
        "SELECT no_dvd, machine_type, line, department, handler, "
        "investigation, source_row, raw_json FROM error_cases"
    )
    params: List[Any] = []
    if batch_id is not None:
        sql += " WHERE batch_id = ?"
        params.append(batch_id)

    filled = {f: 0 for f in MEASURED_FIELDS}
    applicable = {f: 0 for f in MEASURED_FIELDS}
    total = 0
    for row in conn.execute(sql, params):
        try:
            raw = json.loads(row["raw_json"] or "{}")
        except (ValueError, TypeError):
            raw = {}
        row_format = _detect_format(raw)
        if format is not None and row_format != format:
            continue
        total += 1
        for field in MEASURED_FIELDS:
            ok, value = _field_value(row, raw, row_format, field)
            if not ok:
                continue
            applicable[field] += 1
            if _filled(value):
                filled[field] += 1

    fields: Dict[str, Dict[str, Any]] = {}
    for field in MEASURED_FIELDS:
        n_app = applicable[field]
        rate = (filled[field] / n_app * 100.0) if n_app else None
        fields[field] = {"filled": filled[field], "applicable": n_app, "rate": rate}

    f3b_fields = [
        f
        for f in CORE_FIELDS
        if fields[f]["rate"] is not None and fields[f]["rate"] < F3B_THRESHOLD
    ]
    return {
        "total": total,
        "format": format,
        "batch_id": batch_id,
        "threshold": F3B_THRESHOLD,
        "fields": fields,
        "needs_f3b": bool(f3b_fields),
        "f3b_fields": f3b_fields,
    }


def _status(rate: Optional[float]) -> str:
    if rate is None:
        return "n/a"
    return "OK" if rate >= F3B_THRESHOLD else "BELOW 90%"


def report(result: Dict[str, Any]) -> str:
    """Render a measure() result as a short markdown report."""
    scope = []
    scope.append(f"format={result['format'] or 'all'}")
    if result["batch_id"] is not None:
        scope.append(f"batch_id={result['batch_id']}")
    lines = [
        "# F3 field-completeness report",
        "",
        f"Scope: {', '.join(scope)} — total cases: {result['total']}",
        "",
        "| field | filled | applicable | rate | status |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for field in MEASURED_FIELDS:
        f = result["fields"][field]
        rate = "n/a" if f["rate"] is None else f"{f['rate']:.1f}%"
        lines.append(
            f"| {field} | {f['filled']} | {f['applicable']} | {rate} | {_status(f['rate'])} |"
        )
    lines.append("")
    if result["needs_f3b"]:
        lines.append(
            f"F3b gate: FAIL — below {result['threshold']:.0f}%: "
            + ", ".join(result["f3b_fields"])
            + " → open ticket F3b (backfill)."
        )
    else:
        lines.append(
            f"F3b gate: PASS — all core fields >= {result['threshold']:.0f}%."
        )
    return "\n".join(lines) + "\n"
