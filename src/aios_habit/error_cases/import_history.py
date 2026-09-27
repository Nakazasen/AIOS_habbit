"""F2: importer for the 29-column "History KDTPS" sheet -> error_cases.

Source: Loi KDTPS.xlsx, sheet "History KDTPS" (header row 4, data from
row 5, 29 columns A-AC). The legacy A-Y mapping does NOT apply here;
see column_map.normalize_history_row and recon 2026-09-27.

Rules:
- Rows missing year (A) or NO. (B) are skipped (counted).
- Rows missing machine type (D) or line (E) are skipped (the history
  dedup key needs them).
- Re-importing an unchanged file (same name + sha256 + sheet) is skipped
  whole ("vat lai file cu thi bo qua"), unless force=True.
- Green-fill detection is kept as a code path (the real file has 0
  green cells); green-skipped columns never overwrite stored values.
- Read-only: the source workbook is never modified.

This module never touches the RAG index.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl

from . import column_map
from . import store

SHEET_NAME = "History KDTPS"
HEADER_ROW_1BASED = 4
N_COLS = 29


def _cell_rgb(cell: Any) -> Optional[Tuple[int, int, int]]:
    """Fill color of a cell as (R, G, B), or None when unfilled."""
    fill = getattr(cell, "fill", None)
    if fill is None or not getattr(fill, "patternType", None):
        return None
    color = getattr(fill, "fgColor", None) or getattr(fill, "start_color", None)
    rgb = getattr(color, "rgb", None)
    if not rgb or rgb == "00000000":
        return None
    hex_rgb = str(rgb)
    if len(hex_rgb) == 8:  # ARGB -> drop alpha
        hex_rgb = hex_rgb[2:]
    if len(hex_rgb) != 6:
        return None
    return (int(hex_rgb[0:2], 16), int(hex_rgb[2:4], 16), int(hex_rgb[4:6], 16))


def green_skip_letters(cells: List[Any]) -> List[str]:
    """Excel column letters whose fill is the legacy 'do not overwrite' green."""
    return [
        column_map.col_letter(i)
        for i, cell in enumerate(cells)
        if column_map.is_green_skip(_cell_rgb(cell))
    ]


def find_existing_batch(
    conn: sqlite3.Connection, source_file: str, file_sha256: str, sheet_name: str
) -> Optional[int]:
    row = conn.execute(
        """SELECT id FROM import_batches
           WHERE source_file = ? AND file_sha256 = ? AND sheet_name = ?""",
        (source_file, file_sha256, sheet_name),
    ).fetchone()
    return int(row["id"]) if row else None


def _is_empty_row(values: List[Any]) -> bool:
    return all(v is None or (isinstance(v, str) and not v.strip()) for v in values)


def _valid_no_dvd(no_dvd: str) -> bool:
    """False when the year (A) or NO. (B) side is missing: '', '/', '/5', '2024/'."""
    return bool(no_dvd) and no_dvd != "/" and not no_dvd.startswith("/") \
        and not no_dvd.endswith("/")


def import_history(
    conn: sqlite3.Connection,
    xlsx_path: str | Path,
    *,
    sheet_name: str = SHEET_NAME,
    force: bool = False,
) -> Dict[str, Any]:
    """Import the History KDTPS sheet. Returns a result dict.

    status is "imported" or "skipped" (unchanged file re-import).
    """
    path = Path(xlsx_path)
    sha = store.sha256_file(path)
    source_file = path.name

    if not force:
        existing = find_existing_batch(conn, source_file, sha, sheet_name)
        if existing is not None:
            return {
                "status": "skipped",
                "batch_id": existing,
                "rows_read": 0,
                "rows_imported": 0,
                "rows_skipped": 0,
            }
        batch_id = store.start_batch(
            conn,
            source_file=source_file,
            file_sha256=sha,
            sheet_name=sheet_name,
            sheet_type=None,  # history sheet has no Máy in/KIT distinction
            header_row=HEADER_ROW_1BASED,
            notes="F2: 29-column History KDTPS format (format=history_29)",
        )
    else:
        # Refresh: re-run into the existing batch so provenance stays one row
        # per (file, sha, sheet); upserts update the cases in place.
        batch_id = find_existing_batch(conn, source_file, sha, sheet_name)
        if batch_id is None:
            batch_id = store.start_batch(
                conn,
                source_file=source_file,
                file_sha256=sha,
                sheet_name=sheet_name,
                sheet_type=None,
                header_row=HEADER_ROW_1BASED,
                notes="F2: 29-column History KDTPS format (format=history_29)",
            )

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet_name]
        rows_read = rows_imported = rows_skipped = 0
        for excel_row, row_cells in enumerate(
            ws.iter_rows(min_row=HEADER_ROW_1BASED + 1, max_col=N_COLS),
            start=HEADER_ROW_1BASED + 1,
        ):
            values = [c.value for c in row_cells]
            if _is_empty_row(values):
                continue
            rows_read += 1
            fields = column_map.normalize_history_row(values)
            no_dvd = (fields.get("no_dvd") or "").strip()
            if not _valid_no_dvd(no_dvd):
                rows_skipped += 1  # missing year (A) or NO. (B)
                continue
            try:
                store.upsert_case(
                    conn,
                    batch_id=batch_id,
                    source_row=excel_row,
                    fields=fields,
                    skip_cells=green_skip_letters(row_cells),
                    format="history_29",
                )
            except ValueError:
                rows_skipped += 1  # missing machine (D) / line (E)
                continue
            rows_imported += 1
    finally:
        wb.close()

    store.finish_batch(
        conn,
        batch_id,
        rows_read=rows_read,
        rows_imported=rows_imported,
        rows_skipped=rows_skipped,
    )
    return {
        "status": "imported",
        "batch_id": batch_id,
        "rows_read": rows_read,
        "rows_imported": rows_imported,
        "rows_skipped": rows_skipped,
    }
