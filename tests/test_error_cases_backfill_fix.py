"""F3b tests: `fix` backfill from recorded handling text + gate integration.

Acceptance for the f3b-backfill ticket:
- extraction is verbatim: the value is the raw tail of the source cell
  from the last marker line; no marker -> no value
- plan/dry-run counts ab_filled / blank / extractable / unextractable
  and never writes; apply writes raw_json["_backfill"]["fix"] provenance
  (value/source/marker/rule/line/chars/at) and is idempotent
- apply skips rows whose AB was meanwhile filled
- completeness.measure counts a recorded backfill as a filled `fix`
  (and reports it under `backfilled`), so the F3b gate sees the raise;
  blank/None backfill values do not count
"""
import json

import pytest

from aios_habit.error_cases import (
    FIX_BACKFILL_RULE,
    FIX_MARKERS_JP,
    FIX_MARKERS_VN,
    apply_fix_backfill,
    connect,
    extract_fix_segment,
    init_db,
    measure_completeness,
    plan_fix_backfill,
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
        conn, source_file="f.xlsx", file_sha256="abc", sheet_name="History KDTPS"
    )


def _history_fields(i, *, ab="kaizen", o="dieu tra VN", n="jp investigation", **over):
    raw = {
        "A": "2025",
        "B": str(i),
        "C": "2025-01-02",
        "N": n,
        "O": o,
        "AA": "nguyen nhan",
        "AB": ab,
        "AC": "",
    }
    fields = {
        "no_dvd": f"2025/{i}",
        "machine_type": "Virgo",
        "line": "C33",
        "department": "ME",
        "handler": "Nguyen Van A",
        "investigation": o,
        "raw": raw,
    }
    fields.update(over)
    return fields


def _seed(conn, batch_id, i, **over):
    upsert_case(
        conn,
        batch_id=batch_id,
        source_row=4 + i,
        fields=_history_fields(i, **over),
        format="history_29",
    )


def _raw(conn, no_dvd):
    row = conn.execute(
        "SELECT raw_json FROM error_cases WHERE no_dvd = ?", (no_dvd,)
    ).fetchone()
    return json.loads(row["raw_json"])


def _set_raw(conn, no_dvd, raw):
    conn.execute(
        "UPDATE error_cases SET raw_json = ? WHERE no_dvd = ?",
        (json.dumps(raw, ensure_ascii=False), no_dvd),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# extract_fix_segment
# ---------------------------------------------------------------------------


def test_extract_returns_none_without_marker():
    assert extract_fix_segment("lay log\nOFF/ON 15 lan OK", FIX_MARKERS_VN) is None
    assert extract_fix_segment(None, FIX_MARKERS_VN) is None
    assert extract_fix_segment("   \n ", FIX_MARKERS_VN) is None


def test_extract_takes_last_marker_line_to_end_verbatim():
    text = "Lay log\nĐối sách: giữ nguyên\nĐối sách: đổi mới\nClose"
    seg = extract_fix_segment(text, FIX_MARKERS_VN)
    assert seg["value"] == "Đối sách: đổi mới\nClose"
    assert seg["marker"] == "đối sách"
    assert seg["line"] == 3
    assert seg["chars"] == len("Đối sách: đổi mới\nClose")


def test_extract_vietnamese_matching_is_case_insensitive():
    seg = extract_fix_segment("ĐỐI ỨNG thay thế linh kiện", FIX_MARKERS_VN)
    assert seg["value"] == "ĐỐI ỨNG thay thế linh kiện"
    assert seg["marker"] == "đối ứng"


def test_extract_japanese_matching_is_case_sensitive():
    seg = extract_fix_segment("＋LOG取得済み\n対策：交換する", FIX_MARKERS_JP, case_sensitive=True)
    assert seg["value"] == "対策：交換する"
    assert seg["marker"] == "対策"
    assert seg["line"] == 2


def test_extract_value_is_exact_tail_of_source():
    text = "Buoc 1\nBuoc 2\nXử lý lỗi đơn phát.\n"
    seg = extract_fix_segment(text, FIX_MARKERS_VN)
    assert text.rstrip().endswith(seg["value"])
    assert seg["value"] == "Xử lý lỗi đơn phát."


# ---------------------------------------------------------------------------
# plan_backfill (dry-run)
# ---------------------------------------------------------------------------


def test_plan_counts_sources_and_never_writes(conn):
    b = _batch(conn)
    _seed(conn, b, 1, ab="dummy")  # AB filled -> skipped
    _seed(conn, b, 2, ab=None, o="Lay log\nXử lý lỗi đơn phát")  # O marker
    _seed(conn, b, 3, ab=None, o="Chi do nhiet do\nKhong ket luan")  # no marker
    _seed(conn, b, 4, ab="", o="x", n="＋処置：Eraser基板交換")  # N-only marker
    plan = plan_fix_backfill(conn)
    assert plan["format"] == "history_29"
    assert plan["scanned"] == 4
    assert plan["ab_filled"] == 1
    assert plan["blank"] == 3
    assert plan["already_backfilled"] == 0
    assert plan["extractable"] == 2
    assert plan["unextractable"] == 1
    assert plan["sources"] == {"O": 1, "N": 1}
    assert {c["no_dvd"] for c in plan["candidates"]} == {"2025/2", "2025/4"}
    # dry-run: nothing written
    for no_dvd in ("2025/2", "2025/4"):
        assert "_backfill" not in _raw(conn, no_dvd)


def test_plan_prefers_vietnamese_column_over_japanese(conn):
    b = _batch(conn)
    _seed(conn, b, 5, ab=None, o="Lay log\nThay thế bản mạch APC", n="対策：基板交換")
    plan = plan_fix_backfill(conn)
    candidate = plan["candidates"][0]
    assert candidate["source"] == "O"
    assert candidate["value"] == "Thay thế bản mạch APC"


def test_plan_excludes_legacy_rows_and_other_formats(conn):
    b = _batch(conn)
    upsert_case(
        conn,
        batch_id=b,
        source_row=99,
        fields={
            "no_dvd": "DVD-1",
            "sheet_type": "Máy in",
            "department": "ME",
            "machine_type": "Iris",
            "line": "L1",
            "raw": {"A": "x", "N": "Xử lý lỗi"},
        },
        format="legacy",
    )
    plan = plan_fix_backfill(conn)
    assert plan["scanned"] == 0
    assert plan["candidates"] == []


def test_plan_batch_filter(conn):
    b1 = _batch(conn)
    b2 = start_batch(conn, source_file="g.xlsx", file_sha256="d", sheet_name="S")
    _seed(conn, b1, 1, ab=None, o="Xử lý lỗi đơn phát")
    _seed(conn, b2, 2, ab=None, o="Xử lý lỗi đơn phát")
    plan = plan_fix_backfill(conn, batch_id=b2)
    assert plan["scanned"] == 1
    assert [c["no_dvd"] for c in plan["candidates"]] == ["2025/2"]


# ---------------------------------------------------------------------------
# apply_backfill
# ---------------------------------------------------------------------------


def test_apply_writes_provenance_and_leaves_other_rows_alone(conn):
    b = _batch(conn)
    _seed(conn, b, 1, ab=None, o="Lay log\nĐối ứng thay thế linh kiện U1")
    _seed(conn, b, 2, ab=None, o="Chi do nhiet do")
    plan = plan_fix_backfill(conn)
    result = apply_fix_backfill(conn, plan, at="2026-10-01T05:00:00+07:00")
    assert result["applied"] == 1
    assert result["skipped_ab_filled"] == 0
    assert result["skipped_existing"] == 0

    raw = _raw(conn, "2025/1")
    entry = raw["_backfill"]["fix"]
    assert entry["value"] == "Đối ứng thay thế linh kiện U1"
    assert entry["source"] == "O"
    assert entry["marker"] == "đối ứng"
    assert entry["rule"] == FIX_BACKFILL_RULE
    assert entry["line"] == 2
    assert entry["chars"] == len("Đối ứng thay thế linh kiện U1")
    assert entry["at"] == "2026-10-01T05:00:00+07:00"
    # AB itself stays blank (raw fidelity preserved)
    assert not raw.get("AB")
    # untouched row keeps no backfill
    assert "_backfill" not in _raw(conn, "2025/2")


def test_apply_is_idempotent_and_refresh_overwrites(conn):
    b = _batch(conn)
    _seed(conn, b, 1, ab=None, o="Lay log\nXử lý lỗi đơn phát")
    plan = plan_fix_backfill(conn)
    assert apply_fix_backfill(conn, plan, at="2026-10-01T05:00:00+07:00")["applied"] == 1

    plan2 = plan_fix_backfill(conn)
    assert plan2["already_backfilled"] == 1
    assert plan2["extractable"] == 0
    result2 = apply_fix_backfill(conn, plan2)
    assert result2["applied"] == 0
    assert _raw(conn, "2025/1")["_backfill"]["fix"]["at"] == "2026-10-01T05:00:00+07:00"

    plan3 = plan_fix_backfill(conn, refresh=True)
    assert plan3["extractable"] == 1
    result3 = apply_fix_backfill(conn, plan3, refresh=True, at="2026-10-01T06:00:00+07:00")
    assert result3["applied"] == 1
    assert _raw(conn, "2025/1")["_backfill"]["fix"]["at"] == "2026-10-01T06:00:00+07:00"


def test_apply_skips_row_whose_ab_got_filled_meanwhile(conn):
    b = _batch(conn)
    _seed(conn, b, 1, ab=None, o="Lay log\nXử lý lỗi đơn phát")
    plan = plan_fix_backfill(conn)
    raw = _raw(conn, "2025/1")
    raw["AB"] = "要"  # e.g. a refresh import filled AB between plan and apply
    _set_raw(conn, "2025/1", raw)
    result = apply_fix_backfill(conn, plan)
    assert result["applied"] == 0
    assert result["skipped_ab_filled"] == 1
    assert "_backfill" not in _raw(conn, "2025/1")


# ---------------------------------------------------------------------------
# completeness gate integration
# ---------------------------------------------------------------------------


def test_gate_counts_recorded_backfill_as_filled_fix(conn):
    b = _batch(conn)
    for i in range(1, 6):  # 5 rows with AB filled
        _seed(conn, b, i, ab="dummy")
    for i in range(6, 10):  # 4 rows rescued by the backfill
        _seed(conn, b, i, ab=None, o="Lay log\nXử lý lỗi đơn phát")
    _seed(conn, b, 10, ab=None, o="Chi do nhiet do, chua ket luan")  # still blank
    plan = plan_fix_backfill(conn)
    assert plan["extractable"] == 4
    apply_fix_backfill(conn, plan, at="2026-10-01T05:00:00+07:00")

    result = measure_completeness(conn)
    fix = result["fields"]["fix"]
    assert fix["applicable"] == 10
    assert fix["filled"] == 9
    assert fix["backfilled"] == 4
    assert fix["rate"] == pytest.approx(90.0)
    assert result["needs_f3b"] is False


def test_gate_ignores_blank_backfill_value(conn):
    b = _batch(conn)
    _seed(conn, b, 1, ab=None, o="Chi do nhiet do")
    raw = _raw(conn, "2025/1")
    raw["_backfill"] = {"fix": {"value": "   "}}
    _set_raw(conn, "2025/1", raw)
    result = measure_completeness(conn)
    fix = result["fields"]["fix"]
    assert fix["filled"] == 0
    assert fix["backfilled"] == 0
    assert result["needs_f3b"] is True


def test_gate_legacy_fix_stays_not_applicable(conn):
    b = _batch(conn)
    upsert_case(
        conn,
        batch_id=b,
        source_row=1,
        fields={
            "no_dvd": "DVD-1",
            "sheet_type": "Máy in",
            "department": "ME",
            "machine_type": "Iris",
            "line": "L1",
            "raw": {"A": "x", "_backfill": {"fix": {"value": "khong co cot AB"}}},
        },
        format="legacy",
    )
    result = measure_completeness(conn)
    fix = result["fields"]["fix"]
    assert fix["applicable"] == 0
    assert fix["rate"] is None
