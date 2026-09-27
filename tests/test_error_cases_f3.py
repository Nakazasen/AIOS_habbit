"""F3 tests: field-completeness measurement on synthetic :memory: data.

Acceptance for F3:
- per-field fill rates computed correctly (blank/None count as unfilled)
- fields with no mapping for a row's format (date/cause/fix on legacy
  rows) are n/a, not 0%, and do not trip the F3b gate
- F3b gate: any CORE field < 90% -> needs_f3b with the failing fields;
  exactly 90% passes
- format= and batch_id= filters scope the measurement
- empty DB -> total 0, all rates None, gate not tripped
"""
import sqlite3

import pytest

from aios_habit.error_cases import (
    F3B_THRESHOLD,
    completeness_report,
    connect,
    init_db,
    measure_completeness,
    start_batch,
    upsert_case,
)


@pytest.fixture()
def conn():
    c = connect(":memory:")
    init_db(c)
    yield c
    c.close()


def _batch(conn):
    return start_batch(
        conn, source_file="f.xlsx", file_sha256="abc", sheet_name="S"
    )


def _legacy_fields(i, **over):
    fields = {
        "no_dvd": f"DVD-{i:03d}",
        "sheet_type": "Máy in",
        "department": "ME",
        "machine_type": "Iris",
        "line": "L1",
        "handler": "Nguyen Van A",
        "investigation": "dang dieu tra",
        "raw": {chr(ord("A") + k): f"v{k}" for k in range(25)},
    }
    fields.update(over)
    return fields


def _history_fields(i, **over):
    raw = {chr(ord("A") + k): f"v{k}" for k in range(26)}  # A..Z
    raw.update(
        {
            "A": "2024",
            "B": str(i),
            "C": "2024-01-02",      # date
            "N": "jp investigation",
            "O": "dieu tra VN",     # investigation (VN preferred)
            "AA": "nguyen nhan",    # cause
            "AB": "kaizen",          # fix
            "AC": "http://report",
        }
    )
    fields = {
        "no_dvd": f"2024/{i}",
        "machine_type": "Virgo",
        "line": "C33",
        "department": "ME",
        "handler": "Nguyen Van A",
        "investigation": "dieu tra VN",
        "raw": raw,
    }
    fields.update(over)
    return fields


def _seed_history(conn, batch_id, n, blank=None, start=1):
    """Seed n history rows; blank={field: count} blanks that many rows."""
    blank = blank or {}
    counters = {f: 0 for f in blank}
    for j in range(n):
        i = start + j
        over = {}
        raw_over = {}
        for field, count in blank.items():
            if counters[field] < count:
                counters[field] += 1
                if field == "investigation":
                    over["investigation"] = "   "
                elif field == "cause":
                    raw_over["AA"] = ""
                elif field == "fix":
                    raw_over["AB"] = None
                elif field == "date":
                    raw_over["C"] = ""
                elif field == "handler":
                    over["handler"] = None
        fields = _history_fields(i, **over)
        fields["raw"].update(raw_over)
        upsert_case(
            conn, batch_id=batch_id, source_row=4 + i,
            fields=fields, format="history_29",
        )


def test_all_filled_100_percent_no_f3b(conn):
    b = _batch(conn)
    _seed_history(conn, b, 5)
    r = measure_completeness(conn)
    assert r["total"] == 5
    for field, f in r["fields"].items():
        assert f["rate"] == 100.0, field
        assert f["filled"] == f["applicable"] == 5
    assert r["needs_f3b"] is False
    assert r["f3b_fields"] == []


def test_rates_and_f3b_on_missing_fields(conn):
    b = _batch(conn)
    _seed_history(conn, b, 10, blank={"investigation": 3, "cause": 4})
    r = measure_completeness(conn)
    assert r["total"] == 10
    assert r["fields"]["investigation"]["rate"] == pytest.approx(70.0)
    assert r["fields"]["cause"]["rate"] == pytest.approx(60.0)
    assert r["fields"]["fix"]["rate"] == pytest.approx(100.0)
    assert r["needs_f3b"] is True
    assert set(r["f3b_fields"]) == {"investigation", "cause"}


def test_f3b_boundary_exactly_90_passes(conn):
    b = _batch(conn)
    _seed_history(conn, b, 10, blank={"fix": 1})  # 90.0% exactly
    r = measure_completeness(conn)
    assert r["fields"]["fix"]["rate"] == pytest.approx(90.0)
    assert r["needs_f3b"] is False


def test_f3b_boundary_below_90_fails(conn):
    b = _batch(conn)
    _seed_history(conn, b, 10, blank={"fix": 2})  # 80.0%
    r = measure_completeness(conn)
    assert r["needs_f3b"] is True
    assert r["f3b_fields"] == ["fix"]


def test_legacy_rows_cause_fix_date_are_na(conn):
    b = _batch(conn)
    for i in range(1, 6):
        upsert_case(
            conn, batch_id=b, source_row=i,
            fields=_legacy_fields(i), format="legacy",
        )
    r = measure_completeness(conn, format="legacy")
    assert r["total"] == 5
    for field in ("date", "cause", "fix"):
        assert r["fields"][field]["rate"] is None, field
        assert r["fields"][field]["applicable"] == 0
    assert r["fields"]["no_dvd"]["rate"] == 100.0
    # n/a core fields must not trip the gate
    assert r["needs_f3b"] is False


def test_format_filter_mixed_db(conn):
    b = _batch(conn)
    for i in range(1, 4):
        upsert_case(
            conn, batch_id=b, source_row=i,
            fields=_legacy_fields(i), format="legacy",
        )
    _seed_history(conn, b, 4, blank={"cause": 4})  # 0% cause on history rows
    r_all = measure_completeness(conn)
    assert r_all["total"] == 7
    # cause applies to history rows only
    assert r_all["fields"]["cause"]["applicable"] == 4
    assert r_all["fields"]["cause"]["rate"] == pytest.approx(0.0)
    assert r_all["needs_f3b"] is True
    r_hist = measure_completeness(conn, format="history_29")
    assert r_hist["total"] == 4
    r_leg = measure_completeness(conn, format="legacy")
    assert r_leg["total"] == 3
    assert r_leg["fields"]["cause"]["rate"] is None


def test_batch_id_filter(conn):
    b1 = start_batch(
        conn, source_file="a.xlsx", file_sha256="a", sheet_name="S")
    b2 = start_batch(
        conn, source_file="b.xlsx", file_sha256="b", sheet_name="S")
    _seed_history(conn, b1, 3)
    _seed_history(conn, b2, 7, blank={"fix": 7}, start=100)
    r = measure_completeness(conn, batch_id=b2)
    assert r["total"] == 7
    assert r["fields"]["fix"]["rate"] == pytest.approx(0.0)
    assert r["needs_f3b"] is True
    r1 = measure_completeness(conn, batch_id=b1)
    assert r1["total"] == 3
    assert r1["needs_f3b"] is False


def test_empty_db(conn):
    r = measure_completeness(conn)
    assert r["total"] == 0
    for f in r["fields"].values():
        assert f["rate"] is None
        assert f["filled"] == f["applicable"] == 0
    assert r["needs_f3b"] is False
    assert r["f3b_fields"] == []


def test_invalid_format_rejected(conn):
    with pytest.raises(ValueError):
        measure_completeness(conn, format="nope")


def test_report_marks_and_gate_line(conn):
    b = _batch(conn)
    for i in range(1, 4):
        upsert_case(
            conn, batch_id=b, source_row=i,
            fields=_legacy_fields(i), format="legacy",
        )
    _seed_history(conn, b, 2, blank={"fix": 2})  # 0% fix
    text = completeness_report(measure_completeness(conn))
    assert "| fix | 0 | 2 | 0.0% | BELOW 90% |" in text
    assert "F3b gate: FAIL" in text
    assert "fix" in text.split("F3b gate: FAIL")[1]

    ok_text = completeness_report(
        measure_completeness(conn, format="legacy"))
    assert "F3b gate: PASS" in ok_text
    assert "n/a" in ok_text


def test_threshold_constant():
    assert F3B_THRESHOLD == 90.0


def test_source_row_counts_as_filled(conn):
    b = _batch(conn)
    _seed_history(conn, b, 3)
    r = measure_completeness(conn)
    assert r["fields"]["source_row"]["rate"] == 100.0
