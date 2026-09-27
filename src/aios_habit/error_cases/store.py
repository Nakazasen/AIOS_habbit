"""F1: SQLite store for error_cases + import_batches (provenance).

One SQLite file per deployment; separate from the RAG index.
Every write path goes through this module so provenance
(batch -> source file/sha/sheet/row) is never lost.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import column_map

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables/indexes idempotently."""
    conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def start_batch(
    conn: sqlite3.Connection,
    *,
    source_file: str,
    file_sha256: str,
    sheet_name: str,
    sheet_type: str,
    department: Optional[str] = None,
    line_filter: Optional[List[str]] = None,
    header_row: Optional[int] = None,
    notes: str = "",
) -> int:
    """Open a new import batch; returns its id (provenance anchor)."""
    if sheet_type not in column_map.SHEET_TYPES:
        raise ValueError(f"sheet_type must be one of {column_map.SHEET_TYPES}")
    cur = conn.execute(
        """INSERT INTO import_batches
           (source_file, file_sha256, sheet_name, sheet_type, department,
            line_filter, header_row, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            source_file,
            file_sha256,
            sheet_name,
            sheet_type,
            department,
            json.dumps(line_filter or [], ensure_ascii=False),
            header_row,
            notes,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_batch(
    conn: sqlite3.Connection,
    batch_id: int,
    *,
    rows_read: int,
    rows_imported: int,
    rows_skipped: int,
) -> None:
    conn.execute(
        """UPDATE import_batches
           SET rows_read = ?, rows_imported = ?, rows_skipped = ?
           WHERE id = ?""",
        (rows_read, rows_imported, rows_skipped, batch_id),
    )
    conn.commit()


def upsert_case(
    conn: sqlite3.Connection,
    *,
    batch_id: int,
    source_row: int,
    fields: Dict[str, Any],
    skip_cells: Optional[List[str]] = None,
) -> str:
    """Insert or update one case. Returns 'inserted' or 'updated'.

    Dedup key (legacy rule): UNIQUE(no_dvd, sheet_type, department).
    Green-skipped columns are recorded but never overwrite stored values:
    on conflict-update, columns listed in skip_cells keep their old value.
    """
    no_dvd = (fields.get("no_dvd") or "").strip()
    if not no_dvd:
        raise ValueError("no_dvd (column A) is required")
    sheet_type = fields.get("sheet_type")
    if sheet_type not in column_map.SHEET_TYPES:
        raise ValueError(f"sheet_type must be one of {column_map.SHEET_TYPES}")

    # Probe before write: timestamp comparison is unreliable within one second.
    existed = get_case(conn, no_dvd, sheet_type, fields.get("department")) is not None

    raw_json = json.dumps(fields.get("raw") or {}, ensure_ascii=False, default=str)
    skip_json = json.dumps(skip_cells or [], ensure_ascii=False)

    params = {
        "batch_id": batch_id,
        "source_row": source_row,
        "no_dvd": no_dvd,
        "sheet_type": sheet_type,
        "department": fields.get("department"),
        "machine_type": fields.get("machine_type"),
        "line": fields.get("line"),
        "error_code_c": fields.get("error_code_c"),
        "error_code_h": fields.get("error_code_h"),
        "investigation": fields.get("investigation"),
        "handler": fields.get("handler"),
        "is_completed": fields.get("is_completed") or "",
        "needs_jp_support": fields.get("needs_jp_support") or "",
        "raw_json": raw_json,
        "skip_cells": skip_json,
    }

    # Skip-listed columns keep their stored value on update (legacy green rule).
    skip_fields = set()
    for letter in skip_cells or []:
        for idx, field in column_map.COLUMN_MAP.items():
            if column_map.col_letter(idx) == letter:
                skip_fields.add(field)

    update_sets = []
    for key in (
        "batch_id", "source_row", "department", "machine_type", "line",
        "error_code_c", "error_code_h", "investigation", "handler",
        "is_completed", "needs_jp_support", "raw_json", "skip_cells",
    ):
        if key in skip_fields:
            update_sets.append(f"{key} = error_cases.{key}")
        else:
            update_sets.append(f"{key} = excluded.{key}")
    update_sets.append("updated_at = datetime('now')")

    cur = conn.execute(
        f"""INSERT INTO error_cases
            (batch_id, source_row, no_dvd, sheet_type, department, machine_type,
             line, error_code_c, error_code_h, investigation, handler,
             is_completed, needs_jp_support, raw_json, skip_cells)
            VALUES (:batch_id, :source_row, :no_dvd, :sheet_type, :department,
                    :machine_type, :line, :error_code_c, :error_code_h,
                    :investigation, :handler, :is_completed, :needs_jp_support,
                    :raw_json, :skip_cells)
            ON CONFLICT (no_dvd, sheet_type, department) DO UPDATE SET
            {", ".join(update_sets)}""",
        params,
    )
    conn.commit()
    return "updated" if existed else "inserted"


def get_case(
    conn: sqlite3.Connection, no_dvd: str, sheet_type: str, department: Optional[str]
) -> Optional[Dict[str, Any]]:
    cur = conn.execute(
        """SELECT * FROM error_cases
           WHERE no_dvd = ? AND sheet_type = ?
             AND (department = ? OR (department IS NULL AND ? IS NULL))""",
        (no_dvd, sheet_type, department, department),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def count_cases(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) AS n FROM error_cases").fetchone()["n"])


def batch_stats(conn: sqlite3.Connection, batch_id: int) -> Dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM import_batches WHERE id = ?", (batch_id,)
    ).fetchone()
    return dict(row) if row else {}
