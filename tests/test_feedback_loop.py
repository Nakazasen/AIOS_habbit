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
