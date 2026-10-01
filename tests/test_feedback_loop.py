"""Step 2 tests: feedback loop (suggestion ratings + gated case closure).

DỮ LIỆU MÔ PHỎNG — every fixture below is synthetic (SIMULATED_*),
randomly generated for testing only; nothing here is real production data.
Nội dung fixture dựa trên từ vựng domain thật (LSU/Iris LSU, JIG BOWSKEW,
phân tích 4M từ file AI_LSU_du_doan_loi.xlsx của công ty) để người trong
ngành đọc thấy đúng chất, nhưng mọi bản ghi đều là bịa cho kiểm thử.
"""

import pytest

from aios_habit.error_cases import connect, init_db
from aios_habit.error_cases.feedback_loop import (
    RATING_CORRECT,
    RATING_PARTIAL,
    RATING_WRONG,
    ClosureBlockedError,
    close_case,
    get_closure,
    init_feedback_loop,
    log_suggestion_call,
    positive_rate_by_quarter,
    rating_coverage,
    record_rating,
)

# --- DỮ LIỆU MÔ PHỎNG: synthetic cases/ratings, labeled SIMULATED_* ---------
SIMULATED_RATINGS_Q1 = [
    # (suggested_at, rating): Q1 2026, mostly positive
    ("2026-01-05 09:00:00", RATING_CORRECT),
    ("2026-02-10 09:00:00", RATING_PARTIAL),
    ("2026-03-15 09:00:00", RATING_WRONG),
    ("2026-03-20 09:00:00", RATING_CORRECT),
]
SIMULATED_RATINGS_Q2 = [
    # Q2 2026: one positive, one wrong
    ("2026-04-02 09:00:00", RATING_WRONG),
    ("2026-05-11 09:00:00", RATING_CORRECT),
]
SIMULATED_UNRATED_CALL_AT = "2026-06-01 09:00:00"  # no rating -> coverage < 100%
# Dựa trên phân tích 4M thật (Máy móc: hiệu suất jig giảm sút) + tên JIG thật.
SIMULATED_CAUSE = ("SIMULATED nguyên nhân thật: hiệu suất JIG BOWSKEW 4 BEAM "
                   "giảm sút, kích thước linh kiện nhựa lot lệch khỏi tiêu chuẩn")
# Dựa trên quy trình LÀM DATA thật (mỗi lot đo 5 unit).
SIMULATED_COUNTERMEASURE = ("SIMULATED đối sách thật: hiệu chỉnh lại JIG "
                            "BOWSKEW 4 BEAM + đo lại kích thước 5 unit/lot")


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "feedback_simulated.sqlite")
    init_db(c)
    init_feedback_loop(c)
    yield c
    c.close()


def _simulated_case(conn, no_dvd):
    cur = conn.execute(
        """INSERT INTO error_cases (no_dvd, sheet_type, raw_json)
           VALUES (?, 'Máy in', '{}')""",
        (no_dvd,),
    )
    conn.commit()
    return int(cur.lastrowid)


def test_rating_is_logged(conn):
    case_id = _simulated_case(conn, "SIMULATED-LSU-001")
    call_id = log_suggestion_call(conn, case_id, suggested_refs=["LSU-100"])
    rid = record_rating(conn, call_id, RATING_CORRECT, rater="SIMULATED-user")
    row = conn.execute(
        "SELECT rating, rater FROM suggestion_ratings WHERE id = ?", (rid,)
    ).fetchone()
    assert row["rating"] == RATING_CORRECT
    assert row["rater"] == "SIMULATED-user"


def test_rating_rejects_unknown_label(conn):
    case_id = _simulated_case(conn, "SIMULATED-LSU-002")
    call_id = log_suggestion_call(conn, case_id)
    with pytest.raises(ValueError):
        record_rating(conn, call_id, "SIMULATED-bogus")


def test_close_blocked_without_actual_cause(conn):
    case_id = _simulated_case(conn, "SIMULATED-LSU-003")
    with pytest.raises(ClosureBlockedError):
        close_case(conn, case_id, actual_cause="   ",
                   actual_countermeasure=SIMULATED_COUNTERMEASURE)
    assert get_closure(conn, case_id) is None


def test_close_blocked_without_actual_countermeasure(conn):
    case_id = _simulated_case(conn, "SIMULATED-LSU-004")
    with pytest.raises(ClosureBlockedError):
        close_case(conn, case_id, actual_cause=SIMULATED_CAUSE,
                   actual_countermeasure="")
    assert get_closure(conn, case_id) is None


def test_close_writes_back_actuals_to_knowledge_store(conn):
    case_id = _simulated_case(conn, "SIMULATED-LSU-005")
    cid = close_case(conn, case_id, actual_cause=SIMULATED_CAUSE,
                     actual_countermeasure=SIMULATED_COUNTERMEASURE,
                     closed_by="SIMULATED-tech")
    closure = get_closure(conn, case_id)
    assert closure is not None and int(closure["id"]) == cid
    assert closure["actual_cause"] == SIMULATED_CAUSE
    assert closure["actual_countermeasure"] == SIMULATED_COUNTERMEASURE
    # written back into error_cases.investigation + marked completed
    case = conn.execute(
        "SELECT investigation, is_completed FROM error_cases WHERE id = ?",
        (case_id,),
    ).fetchone()
    assert SIMULATED_CAUSE in case["investigation"]
    assert SIMULATED_COUNTERMEASURE in case["investigation"]
    assert case["is_completed"] == "o"


def test_rating_coverage_metric(conn):
    # 7 calls, 6 rated -> coverage 6/7
    total = 0
    for ts, rating in SIMULATED_RATINGS_Q1 + SIMULATED_RATINGS_Q2:
        cid = _simulated_case(conn, f"SIMULATED-LSU-C{total}")
        call_id = log_suggestion_call(conn, cid, suggested_at=ts)
        record_rating(conn, call_id, rating, rated_at=ts)
        total += 1
    cid = _simulated_case(conn, "SIMULATED-LSU-UNRATED")
    log_suggestion_call(conn, cid, suggested_at=SIMULATED_UNRATED_CALL_AT)
    total += 1
    cov = rating_coverage(conn)
    assert cov["calls"] == total == 7
    assert cov["rated"] == 6
    assert cov["coverage"] == pytest.approx(6 / 7)


def test_positive_rate_by_quarter(conn):
    for i, (ts, rating) in enumerate(SIMULATED_RATINGS_Q1 + SIMULATED_RATINGS_Q2):
        cid = _simulated_case(conn, f"SIMULATED-LSU-Q{i}")
        call_id = log_suggestion_call(conn, cid, suggested_at=ts)
        record_rating(conn, call_id, rating, rated_at=ts)
    by_q = positive_rate_by_quarter(conn)
    # Q1: 3 positive of 4 ; Q2: 1 positive of 2
    assert by_q["2026-Q1"]["rated"] == 4
    assert by_q["2026-Q1"]["positive"] == 3
    assert by_q["2026-Q1"]["rate"] == pytest.approx(0.75)
    assert by_q["2026-Q2"]["rated"] == 2
    assert by_q["2026-Q2"]["positive"] == 1
    assert by_q["2026-Q2"]["rate"] == pytest.approx(0.5)


# --------------------------------------------------------------------------
# B2 (2026-10-01): hard close rules QD-BK82-1, conversation-scoped ratings,
# hientuong_missing flag (QD-BK82-2)
# --------------------------------------------------------------------------

import json as _json

from aios_habit.error_cases.feedback_loop import (
    flag_hientuong_missing,
    get_ratings,
    latest_suggestion_call,
    latest_unrated_suggestion_call,
    phenomenon_state,
)


def _form_case(conn, no_dvd="FORM-20261001-0001"):
    """A NEW case as created by the B0-FORM entry form (no_dvd FORM-*)."""
    cur = conn.execute(
        """INSERT INTO error_cases (no_dvd, sheet_type, raw_json)
           VALUES (?, 'Máy in', '{}')""",
        (no_dvd,),
    )
    conn.commit()
    return int(cur.lastrowid)


def _history_case(conn, no_dvd, raw):
    """A history-imported case with a raw_json letter map (I/M/O/F/AA/AB)."""
    cur = conn.execute(
        """INSERT INTO error_cases (no_dvd, sheet_type, raw_json)
           VALUES (?, 'Máy in', ?)""",
        (no_dvd, _json.dumps(raw, ensure_ascii=False)),
    )
    conn.commit()
    return int(cur.lastrowid)


def test_close_new_case_blocked_without_phenomenon_and_process_stage(conn):
    # QD-BK82-1: a NEW case cannot be closed on actuals alone.
    case_id = _form_case(conn)
    with pytest.raises(ClosureBlockedError) as exc:
        close_case(conn, case_id, actual_cause=SIMULATED_CAUSE,
                   actual_countermeasure=SIMULATED_COUNTERMEASURE)
    assert "Hiện tượng" in str(exc.value)
    assert "Công đoạn" in str(exc.value)
    assert get_closure(conn, case_id) is None


def test_close_new_case_accepts_supplied_fields_and_writes_back(conn):
    case_id = _form_case(conn)
    cid = close_case(
        conn, case_id,
        actual_cause=SIMULATED_CAUSE,
        actual_countermeasure=SIMULATED_COUNTERMEASURE,
        phenomenon="SIMULATED hiện tượng: kẹt giấy ở cụm sấy",
        process_stage="SIMULATED công đoạn: sấy",
        closed_by="SIMULATED-tech",
    )
    assert get_closure(conn, case_id)["id"] == cid
    row = conn.execute(
        "SELECT phenomenon, process_stage, cause, countermeasure, "
        "closed_at, is_completed FROM error_cases WHERE id = ?",
        (case_id,),
    ).fetchone()
    assert row["phenomenon"] == "SIMULATED hiện tượng: kẹt giấy ở cụm sấy"
    assert row["process_stage"] == "SIMULATED công đoạn: sấy"
    assert row["cause"] == SIMULATED_CAUSE
    assert row["countermeasure"] == SIMULATED_COUNTERMEASURE
    assert row["closed_at"]  # ISO date stamped at close
    assert row["is_completed"] == "o"


def test_close_new_case_reads_stored_phenomenon_without_resupply(conn):
    # Phenomenon/process stage already on the row: no need to re-supply.
    case_id = _form_case(conn)
    conn.execute(
        "UPDATE error_cases SET phenomenon = ?, process_stage = ? WHERE id = ?",
        ("SIMULATED hiện tượng có sẵn", "SIMULATED công đoạn có sẵn", case_id),
    )
    conn.commit()
    cid = close_case(conn, case_id, actual_cause=SIMULATED_CAUSE,
                     actual_countermeasure=SIMULATED_COUNTERMEASURE)
    assert get_closure(conn, case_id)["id"] == cid


def test_close_legacy_case_needs_only_actuals(conn):
    # 2023 history row: legacy rule — actuals suffice, no auto-fill.
    case_id = _history_case(conn, "2023/461", {"AA": "", "I": "SIMULATED I"})
    cid = close_case(conn, case_id, actual_cause=SIMULATED_CAUSE,
                     actual_countermeasure=SIMULATED_COUNTERMEASURE)
    assert get_closure(conn, case_id)["id"] == cid
    row = conn.execute(
        "SELECT phenomenon FROM error_cases WHERE id = ?", (case_id,)
    ).fetchone()
    assert not row["phenomenon"]  # not backfilled automatically


def test_close_new_2026_history_ticket_requires_fields(conn):
    # The BK-82 "42 rows": 2026/NNNN history tickets are NEW cases.
    case_id = _history_case(conn, "2026/2422", {"I": "", "F": "-"})
    with pytest.raises(ClosureBlockedError):
        close_case(conn, case_id, actual_cause=SIMULATED_CAUSE,
                   actual_countermeasure=SIMULATED_COUNTERMEASURE)
    # ... and close fine once the closer supplies them.
    close_case(conn, case_id, actual_cause=SIMULATED_CAUSE,
               actual_countermeasure=SIMULATED_COUNTERMEASURE,
               phenomenon="SIMULATED bổ sung hiện tượng",
               process_stage="SIMULATED bổ sung công đoạn")
    assert get_closure(conn, case_id) is not None


def test_close_never_overwrites_stored_values(conn):
    case_id = _form_case(conn)
    conn.execute(
        "UPDATE error_cases SET cause = ?, phenomenon = ?, process_stage = ? "
        "WHERE id = ?",
        ("nguyên nhân đã chốt", "hiện tượng đã chốt", "công đoạn đã chốt",
         case_id),
    )
    conn.commit()
    close_case(conn, case_id, actual_cause=SIMULATED_CAUSE,
               actual_countermeasure=SIMULATED_COUNTERMEASURE,
               phenomenon="SIMULATED ghi đè?", process_stage="SIMULATED ghi đè?")
    row = conn.execute(
        "SELECT cause, phenomenon, process_stage FROM error_cases WHERE id = ?",
        (case_id,),
    ).fetchone()
    assert row["cause"] == "nguyên nhân đã chốt"
    assert row["phenomenon"] == "hiện tượng đã chốt"
    assert row["process_stage"] == "công đoạn đã chốt"


def test_latest_unrated_call_is_conversation_scoped(conn):
    c1 = _simulated_case(conn, "SIMULATED-LSU-R1")
    c2 = _simulated_case(conn, "SIMULATED-LSU-R2")
    call_a = log_suggestion_call(conn, c1, conversation_id="conv-A")
    call_b = log_suggestion_call(conn, c2, conversation_id="conv-B")
    assert int(latest_unrated_suggestion_call(conn, "conv-A")["id"]) == call_a
    assert int(latest_unrated_suggestion_call(conn, "conv-B")["id"]) == call_b
    record_rating(conn, call_a, RATING_CORRECT)
    assert latest_unrated_suggestion_call(conn, "conv-A") is None
    # ... but the rated call is still findable as "latest".
    assert int(latest_suggestion_call(conn, "conv-A")["id"]) == call_a
    assert len(get_ratings(conn, call_a)) == 1


def test_phenomenon_state_and_flag(conn):
    blank_id = _history_case(conn, "2026/2423",
                             {"I": "", "M": "SIMULATED thao tác M", "O": ""})
    full_id = _history_case(conn, "2026/2424", {"I": "SIMULATED hiện tượng I"})
    st = phenomenon_state(conn, blank_id)
    assert st["missing"] is True
    assert st["source"] is None
    assert st["suggested_text"] == "SIMULATED thao tác M"
    assert st["suggested_source"] == "M"
    st2 = phenomenon_state(conn, full_id)
    assert st2["missing"] is False
    assert st2["source"] == "raw_I"
    flagged = flag_hientuong_missing(conn)
    assert flagged == 1
    row = conn.execute(
        "SELECT hientuong_missing FROM error_cases WHERE id = ?", (blank_id,)
    ).fetchone()
    assert row["hientuong_missing"] == "1"
    row2 = conn.execute(
        "SELECT hientuong_missing FROM error_cases WHERE id = ?", (full_id,)
    ).fetchone()
    assert not row2["hientuong_missing"]


def test_init_db_creates_feedback_tables(conn):
    # store.init_db now wires the feedback schema in (B2).
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {"suggestion_calls", "suggestion_ratings", "case_closures"} <= tables
    cols = {r[1] for r in conn.execute("PRAGMA table_info(error_cases)")}
    assert "hientuong_missing" in cols


def test_init_feedback_loop_on_legacy_db_without_conversation_id(tmp_path):
    # Hồi quy: DB cũ (Bước 2) có bảng suggestion_calls nhưng thiếu cột
    # conversation_id. init phải thêm cột TRƯỚC khi tạo index, không được
    # nổ OperationalError "no such column: conversation_id".
    import sqlite3

    db = tmp_path / "legacy_schema_simulated.sqlite"
    raw = sqlite3.connect(db)
    raw.execute(
        "CREATE TABLE error_cases ("
        " id INTEGER PRIMARY KEY, no_dvd TEXT, sheet_type TEXT, raw_json TEXT)"
    )
    raw.execute(
        """CREATE TABLE suggestion_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            suggested_at TEXT NOT NULL DEFAULT (datetime('now')),
            suggested_refs TEXT NOT NULL DEFAULT '[]',
            note TEXT NOT NULL DEFAULT '')"""
    )
    raw.execute(
        "INSERT INTO suggestion_calls (case_id, suggested_refs)"
        " VALUES (1, '[\"SIMULATED-legacy-001\"]')"
    )
    raw.commit()
    raw.close()

    legacy = connect(db)
    init_feedback_loop(legacy)  # must not raise

    cols = {r[1] for r in legacy.execute("PRAGMA table_info(suggestion_calls)")}
    assert "conversation_id" in cols
    # Dòng cũ giữ nguyên + cột mới điền giá trị rỗng.
    old_rows = legacy.execute(
        "SELECT suggested_refs, conversation_id FROM suggestion_calls"
    ).fetchall()
    assert old_rows[0]["suggested_refs"] == '["SIMULATED-legacy-001"]'
    assert old_rows[0]["conversation_id"] == ""
    # Vòng B2 chạy được trên DB đã migrate: log + đánh giá + truy vấn.
    call_id = log_suggestion_call(
        legacy, 1, suggested_refs=["SIMULATED-legacy-001"], conversation_id="SIMULATED-conv"
    )
    record_rating(legacy, call_id, RATING_CORRECT, rater="SIMULATED-reviewer")
    latest = latest_suggestion_call(legacy, conversation_id="SIMULATED-conv")
    assert latest is not None and latest["id"] == call_id
    assert latest["conversation_id"] == "SIMULATED-conv"
    legacy.close()


def test_init_feedback_loop_on_db_without_feedback_tables(tmp_path):
    # DB trắng chưa có bảng suggestion_calls: migration phải bỏ qua êm,
    # schema script tạo bảng đã có cột conversation_id ngay từ đầu.
    import sqlite3

    db = tmp_path / "no_feedback_tables_simulated.sqlite"
    raw = sqlite3.connect(db)
    raw.execute(
        "CREATE TABLE error_cases ("
        " id INTEGER PRIMARY KEY, no_dvd TEXT, sheet_type TEXT, raw_json TEXT)"
    )
    raw.commit()
    raw.close()

    fresh = connect(db)
    init_feedback_loop(fresh)  # guard: không ALTER bảng chưa tồn tại
    init_feedback_loop(fresh)  # idempotent
    cols = {r[1] for r in fresh.execute("PRAGMA table_info(suggestion_calls)")}
    assert "conversation_id" in cols
    fresh.close()


def test_rating_coverage_counts_rerated_call_once(conn):
    # Hồi quy: đánh giá lại một lượt gợi ý là hành vi có thiết kế; mẫu số
    # `calls` phải đếm mỗi lượt 1 lần (COUNT(DISTINCT c.id)), không phồng
    # theo số dòng rating sau LEFT JOIN.
    case_id = _simulated_case(conn, "SIMULATED-rerate-001")
    call_id = log_suggestion_call(conn, case_id, suggested_refs=["SIMULATED-001"])
    record_rating(conn, call_id, RATING_CORRECT, rater="SIMULATED-a")
    record_rating(conn, call_id, RATING_PARTIAL, rater="SIMULATED-b")  # đánh giá lại
    cov = rating_coverage(conn)
    assert cov["calls"] == 1
    assert cov["rated"] == 1
    assert cov["coverage"] == pytest.approx(1.0)
