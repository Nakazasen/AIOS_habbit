"""F1 tests: error_cases schema + A-Y mapping + provenance.

Acceptance for F1:
- schema creates both tables with the legacy UNIQUE(no_dvd, sheet_type, department)
- A-Y mapping matches the legacy app (config.py)
- green RGB(146,208,80) cells are detected and never overwrite stored values
- re-importing the same file does not duplicate cases
- every case links to its import batch (file/sha/sheet/row provenance)
"""
import json

import pytest

from aios_habit.error_cases import (
    COLUMN_MAP,
    GREEN_SKIP_RGB,
    SHEET_TYPES,
    batch_stats,
    col_letter,
    connect,
    count_cases,
    finish_batch,
    get_case,
    init_db,
    is_green_skip,
    is_positive_mark,
    normalize_row,
    start_batch,
    upsert_case,
)


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "error_cases.sqlite")
    init_db(c)
    yield c
    c.close()


def make_row(over=None):
    cells = [None] * 25
    base = {
        0: "DVD-001", 2: "Iris2024", 3: "Line1", 6: "C0363", 7: "J123",
        13: "dang dieu tra", 14: "ME", 18: "Nguyen Van A", 21: "o", 24: "",
    }
    base.update(over or {})
    for i, v in base.items():
        cells[i] = v
    return cells


def test_schema_tables_exist(conn):
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"import_batches", "error_cases"} <= tables


def test_column_map_matches_legacy_app():
    # Grounded in /tmp/kdtps-err/src/utils/config.py
    assert COLUMN_MAP[0] == "no_dvd"
    assert COLUMN_MAP[2] == "machine_type"
    assert COLUMN_MAP[3] == "line"
    assert COLUMN_MAP[6] == "error_code_c"
    assert COLUMN_MAP[7] == "error_code_h"
    assert COLUMN_MAP[13] == "investigation"
    assert COLUMN_MAP[14] == "department"
    assert COLUMN_MAP[18] == "handler"
    assert COLUMN_MAP[21] == "is_completed"
    assert COLUMN_MAP[24] == "needs_jp_support"
    assert col_letter(0) == "A" and col_letter(24) == "Y" and col_letter(25) == "Z"


def test_normalize_row_maps_fields():
    f = normalize_row(make_row())
    assert f["no_dvd"] == "DVD-001"
    assert f["machine_type"] == "Iris2024"
    assert f["line"] == "Line1"
    assert f["error_code_c"] == "C0363"
    assert f["investigation"] == "dang dieu tra"
    assert f["handler"] == "Nguyen Van A"
    assert f["is_completed"] == "o"       # marker normalized
    assert f["needs_jp_support"] == ""    # empty stays empty
    assert f["raw"]["A"] == "DVD-001"    # full fidelity kept
    assert len(f["raw"]) == 25


def test_marker_variants():
    assert is_positive_mark("o") and is_positive_mark("O") and is_positive_mark(" o ")
    assert not is_positive_mark("") and not is_positive_mark(None)
    f = normalize_row(make_row({21: "O", 24: "o"}))
    assert f["is_completed"] == "o" and f["needs_jp_support"] == "o"


def test_green_skip_detection():
    assert GREEN_SKIP_RGB == (146, 208, 80)
    assert is_green_skip((146, 208, 80))
    assert not is_green_skip((0, 255, 0))
    assert not is_green_skip(None)


def _batch(conn):
    return start_batch(
        conn, source_file="Loi KDTPS.xlsx", file_sha256="abc123",
        sheet_name="History KDTPS", sheet_type="Máy in", department="ME",
        header_row=4,
    )


def test_upsert_insert_then_update(conn):
    b = _batch(conn)
    fields = normalize_row(make_row())
    fields["sheet_type"] = "Máy in"
    assert upsert_case(conn, batch_id=b, source_row=5, fields=fields) == "inserted"
    assert count_cases(conn) == 1

    fields2 = normalize_row(make_row({13: "da xong", 21: "o"}))
    fields2["sheet_type"] = "Máy in"
    assert upsert_case(conn, batch_id=b, source_row=5, fields=fields2) == "updated"
    assert count_cases(conn) == 1  # no duplicate
    got = get_case(conn, "DVD-001", "Máy in", "ME")
    assert got["investigation"] == "da xong"


def test_reimport_same_file_no_duplicates(conn):
    """Same file imported twice (e.g. unchanged re-run) must not duplicate."""
    rows = [normalize_row(make_row({0: f"DVD-{i:03d}"})) for i in range(1, 6)]
    for run in range(2):
        b = start_batch(
            conn, source_file="Loi KDTPS.xlsx", file_sha256="abc123",
            sheet_name="History KDTPS", sheet_type="KIT",
        )
        for n, f in enumerate(rows):
            f["sheet_type"] = "KIT"
            upsert_case(conn, batch_id=b, source_row=10 + n, fields=dict(f))
        finish_batch(conn, b, rows_read=5, rows_imported=5, rows_skipped=0)
    assert count_cases(conn) == 5


def test_green_cells_never_overwrite(conn):
    b = _batch(conn)
    f1 = normalize_row(make_row())
    f1["sheet_type"] = "Máy in"
    upsert_case(conn, batch_id=b, source_row=5, fields=f1)

    # Re-import where column N is green-skipped: investigation must survive.
    f2 = normalize_row(make_row({13: "gia tri moi bi chan"}))
    f2["sheet_type"] = "Máy in"
    upsert_case(conn, batch_id=b, source_row=5, fields=f2, skip_cells=["N"])
    got = get_case(conn, "DVD-001", "Máy in", "ME")
    assert got["investigation"] == "dang dieu tra"
    assert json.loads(got["skip_cells"]) == ["N"]


def test_provenance_batch_link(conn):
    b = _batch(conn)
    f = normalize_row(make_row())
    f["sheet_type"] = "Máy in"
    upsert_case(conn, batch_id=b, source_row=42, fields=f)
    finish_batch(conn, b, rows_read=10, rows_imported=9, rows_skipped=1)

    got = get_case(conn, "DVD-001", "Máy in", "ME")
    assert got["batch_id"] == b
    assert got["source_row"] == 42
    st = batch_stats(conn, b)
    assert st["source_file"] == "Loi KDTPS.xlsx"
    assert st["file_sha256"] == "abc123"
    assert st["rows_imported"] == 9 and st["rows_skipped"] == 1


def test_validation_errors(conn):
    b = _batch(conn)
    f = normalize_row(make_row())
    f["sheet_type"] = "Máy in"
    f["no_dvd"] = "  "
    with pytest.raises(ValueError):
        upsert_case(conn, batch_id=b, source_row=5, fields=f)
    f["no_dvd"] = "DVD-002"
    f["sheet_type"] = "Sai"
    with pytest.raises(ValueError):
        upsert_case(conn, batch_id=b, source_row=5, fields=f)
    with pytest.raises(ValueError):
        start_batch(conn, source_file="x.xlsx", file_sha256="s",
                    sheet_name="s", sheet_type="Sai")


def test_sheet_types():
    assert set(SHEET_TYPES) == {"Máy in", "KIT"}


# ---------------------------------------------------------------------------
# history_29 format profile (recon 2026-09-27 on Loi KDTPS.xlsx)
# ---------------------------------------------------------------------------
from aios_habit.error_cases import (  # noqa: E402
    HISTORY_29_MAP,
    history_no_dvd,
    normalize_history_row,
)


def make_history_row(over=None):
    cells = [None] * 29
    base = {
        0: 2024, 1: 3422, 3: "Sirius 2", 4: "C23", 6: "SER123",
        7: "ERROR", 13: "JP text", 14: "VN text", 15: "ME",
        21: "×", 24: "2024-01-01",
    }
    base.update(over or {})
    for i, v in base.items():
        cells[i] = v
    return cells


def test_history_29_map_columns():
    assert HISTORY_29_MAP[3] == "machine_type"   # D, not C
    assert HISTORY_29_MAP[4] == "line"           # E is the true line
    assert HISTORY_29_MAP[7] == "error_code_h"   # H category
    assert HISTORY_29_MAP[15] == "department"    # P
    assert history_no_dvd(2024, 3422) == "2024/3422"


def test_normalize_history_row():
    f = normalize_history_row(make_history_row())
    assert f["no_dvd"] == "2024/3422"
    assert f["machine_type"] == "Sirius 2"
    assert f["line"] == "C23"
    assert f["error_code_h"] == "ERROR"
    assert f["investigation"] == "VN text"   # VN preferred
    assert f["department"] == "ME"
    assert f["handler"] is None              # no person column in this format
    assert f["is_completed"] == ""           # V is LKATQT, not completion
    assert f["needs_jp_support"] == ""       # Y is unhold date, not JP support
    assert len(f["raw"]) == 29
    # VN empty -> fallback to JP
    f2 = normalize_history_row(make_history_row({14: ""}))
    assert f2["investigation"] == "JP text"


def test_history_29_dedup_wider_key(conn):
    """Same (year, NO) with different machine/line are distinct cases."""
    b = start_batch(
        conn, source_file="Loi KDTPS.xlsx", file_sha256="h29",
        sheet_name="History KDTPS", sheet_type="Máy in",
    )
    r1 = normalize_history_row(make_history_row())
    r2 = normalize_history_row(make_history_row({3: "6th A4", 4: "C25"}))
    assert upsert_case(conn, batch_id=b, source_row=5, fields=r1,
                       format="history_29") == "inserted"
    assert upsert_case(conn, batch_id=b, source_row=6, fields=r2,
                       format="history_29") == "inserted"
    assert count_cases(conn) == 2
    # Same triple -> update, not a third row
    r3 = normalize_history_row(make_history_row({14: "VN moi"}))
    assert upsert_case(conn, batch_id=b, source_row=5, fields=r3,
                       format="history_29") == "updated"
    assert count_cases(conn) == 2


def test_history_29_requires_machine_and_line(conn):
    b = start_batch(conn, source_file="x.xlsx", file_sha256="s",
                    sheet_name="s", sheet_type="KIT")
    bad = normalize_history_row(make_history_row({4: None}))
    with pytest.raises(ValueError):
        upsert_case(conn, batch_id=b, source_row=5, fields=bad,
                    format="history_29")
