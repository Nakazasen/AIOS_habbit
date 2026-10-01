"""Tests for the B2 chat actions: danh_gia_goi_y / dong_phieu_loi /
bao_cao_phan_hoi (ticket B2, chat-first UI: no extra toolbars).

DỮ LIỆU MÔ PHỎNG — every fixture below is synthetic (SIMULATED_*),
built only for testing; nothing here is real production data.
"""

from __future__ import annotations

import json
import os

import pytest

from aios_habit import chat_action
from aios_habit import chat_action_phan_hoi as phan_hoi
from aios_habit.chat_action import (
    ChatActionRequest,
    dispatch,
    load_builtin_actions,
    match_action,
    reset_actions,
)
from aios_habit.error_cases import connect, init_db
from aios_habit.error_cases import feedback_loop as fb
from aios_habit.feature_flags import reset_feature_flags


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "phan_hoi_simulated.sqlite"
    conn = connect(str(path))
    init_db(conn)  # B2: now includes the feedback tables
    # A NEW (FORM) case missing phenomenon/process stage at close time.
    conn.execute(
        "INSERT INTO error_cases (no_dvd, sheet_type, raw_json) "
        "VALUES ('FORM-20261001-0001', 'Máy in', '{}')"
    )
    # A legacy 2023 history case.
    conn.execute(
        "INSERT INTO error_cases (no_dvd, sheet_type, raw_json) "
        "VALUES ('2023/461', 'Máy in', ?)",
        (json.dumps({"I": "SIMULATED hiện tượng I"}, ensure_ascii=False),),
    )
    conn.commit()
    conn.close()
    old = os.environ.get("AIOS_ERROR_CASES_DB")
    os.environ["AIOS_ERROR_CASES_DB"] = str(path)
    yield path
    if old is None:
        os.environ.pop("AIOS_ERROR_CASES_DB", None)
    else:
        os.environ["AIOS_ERROR_CASES_DB"] = old


@pytest.fixture(autouse=True)
def _clean_state():
    reset_feature_flags()
    reset_actions()
    yield
    reset_feature_flags()
    reset_actions()


def _request(question, conversation_id="conv-1", context=None):
    ctx = dict(context or {})
    return ChatActionRequest(
        question=question, conversation_id=conversation_id, context=ctx
    )


def _db(db_path):
    conn = connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _log_call(db_path, no_dvd="FORM-20261001-0001", conversation_id="conv-1"):
    conn = _db(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM error_cases WHERE no_dvd = ?", (no_dvd,)
        ).fetchone()
        return fb.log_suggestion_call(
            conn, int(row["id"]),
            suggested_refs=[no_dvd],
            note="tra_cuu_loi_tuong_tu",
            conversation_id=conversation_id,
        )
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Rating
# --------------------------------------------------------------------------


def test_rate_command_is_logged(db_path):
    call_id = _log_call(db_path)
    outcome = dispatch(_request("đánh giá đúng"))
    assert outcome is not None and outcome.action == phan_hoi.RATE_ACTION_NAME
    assert "đúng" in outcome.blocks[0].text
    conn = _db(db_path)
    try:
        ratings = fb.get_ratings(conn, call_id)
        assert len(ratings) == 1
        assert ratings[0]["rating"] == "đúng"
    finally:
        conn.close()


def test_rate_partial_and_wrong_labels(db_path):
    call_id = _log_call(db_path)
    dispatch(_request("đánh giá một phần"))
    conn = _db(db_path)
    try:
        assert fb.get_ratings(conn, call_id)[0]["rating"] == "một phần"
    finally:
        conn.close()
    dispatch(_request("đánh giá sai"))
    conn = _db(db_path)
    try:
        ratings = fb.get_ratings(conn, call_id)
        assert len(ratings) == 2  # re-rate: latest wins downstream
        assert ratings[-1]["rating"] == "sai"
    finally:
        conn.close()


def test_rate_without_any_call_is_friendly(db_path):
    outcome = dispatch(_request("đánh giá đúng", conversation_id="conv-empty"))
    assert outcome is not None
    assert "Chưa có gợi ý nào" in outcome.blocks[0].text


def test_bare_danh_gia_does_not_match(db_path):
    load_builtin_actions()
    assert match_action(_request("đánh giá")) is None


def test_rate_does_not_hijack_answer_quality(db_path):
    load_builtin_actions()
    action = match_action(_request("đánh giá đúng"))
    assert action is not None and action.name == phan_hoi.RATE_ACTION_NAME
    # The longer quality-review command still goes to answer_quality.
    action2 = match_action(_request("đánh giá chất lượng trả lời"))
    assert action2 is not None and action2.name != phan_hoi.RATE_ACTION_NAME


# --------------------------------------------------------------------------
# Close ticket
# --------------------------------------------------------------------------

_CLOSE_FORM = """đóng phiếu
mã phiếu: FORM-20261001-0001
nguyên nhân thật: SIMULATED nguyên nhân thật
đối sách thật: SIMULATED đối sách thật
"""

_CLOSE_FORM_FULL = _CLOSE_FORM + """hiện tượng: SIMULATED hiện tượng
công đoạn: SIMULATED công đoạn
"""


def test_close_template_without_fields(db_path):
    outcome = dispatch(_request("đóng phiếu"))
    assert outcome is not None and outcome.action == phan_hoi.CLOSE_ACTION_NAME
    assert "mã phiếu" in outcome.blocks[0].text


def test_close_new_case_blocked_without_phenomenon(db_path):
    outcome = dispatch(_request(_CLOSE_FORM))
    assert outcome is not None
    text = outcome.blocks[0].text
    assert "Chưa đóng được phiếu" in text
    assert "Hiện tượng" in text and "Công đoạn" in text
    conn = _db(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM error_cases WHERE no_dvd = 'FORM-20261001-0001'"
        ).fetchone()
        assert fb.get_closure(conn, int(row["id"])) is None
    finally:
        conn.close()


def test_close_new_case_succeeds_with_all_fields(db_path):
    outcome = dispatch(_request(_CLOSE_FORM_FULL))
    assert outcome is not None
    assert "Đã đóng phiếu" in outcome.blocks[0].text
    conn = _db(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM error_cases WHERE no_dvd = 'FORM-20261001-0001'"
        ).fetchone()
        closure = fb.get_closure(conn, int(row["id"]))
        assert closure is not None
        assert closure["actual_cause"] == "SIMULATED nguyên nhân thật"
    finally:
        conn.close()


def test_close_unknown_ticket(db_path):
    outcome = dispatch(
        _request(
            "đóng phiếu\nmã phiếu: 2099/9999\n"
            "nguyên nhân thật: x\nđối sách thật: y"
        )
    )
    assert outcome is not None
    assert "Không tìm thấy phiếu" in outcome.blocks[0].text


def test_close_legacy_case_needs_only_actuals(db_path):
    outcome = dispatch(
        _request(
            "đóng phiếu\nmã phiếu: 2023/461\n"
            "nguyên nhân thật: SIMULATED nguyên nhân\nđối sách thật: SIMULATED đối sách"
        )
    )
    assert outcome is not None
    assert "Đã đóng phiếu" in outcome.blocks[0].text


def test_close_wins_over_lookup_on_code_in_text(db_path):
    # "đóng phiếu F000 ..." must reach the close action, not the lookup.
    load_builtin_actions()
    action = match_action(_request("đóng phiếu F000"))
    assert action is not None and action.name == phan_hoi.CLOSE_ACTION_NAME


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def test_report_renders_numbers(db_path):
    c1 = _log_call(db_path, conversation_id="conv-r")
    c2 = _log_call(db_path, conversation_id="conv-r")
    _log_call(db_path, conversation_id="conv-r")  # unrated
    conn = _db(db_path)
    try:
        fb.record_rating(conn, c1, "đúng", rated_at="2026-01-05 09:00:00")
        fb.record_rating(conn, c2, "sai", rated_at="2026-04-02 09:00:00")
        # Backdate the calls into their quarters for the quarterly table.
        conn.execute(
            "UPDATE suggestion_calls SET suggested_at = '2026-01-05 09:00:00' "
            "WHERE id = ?", (c1,))
        conn.execute(
            "UPDATE suggestion_calls SET suggested_at = '2026-04-02 09:00:00' "
            "WHERE id = ?", (c2,))
        conn.commit()
    finally:
        conn.close()
    outcome = dispatch(_request("báo cáo phản hồi", conversation_id="conv-r"))
    assert outcome is not None and outcome.action == phan_hoi.REPORT_ACTION_NAME
    assert outcome.blocks[0].kind == "markdown"
    head = outcome.blocks[0].text
    assert "67%" in head  # 2 of 3 calls rated
    assert "Chưa đạt" in head  # below the 80% target
    table = outcome.blocks[1]
    assert table.kind == "table"
    quarters = [row[0] for row in table.rows]
    assert "2026-Q1" in quarters and "2026-Q2" in quarters


def test_report_without_data(db_path):
    outcome = dispatch(_request("báo cáo phản hồi", conversation_id="conv-x"))
    assert outcome is not None
    # Fresh DB has feedback tables but no calls yet.
    assert "67%" not in outcome.blocks[0].text


def test_lookup_stays_last_builtin():
    load_builtin_actions()
    assert "aios_habit.chat_action_phan_hoi" in chat_action.BUILTIN_ACTION_MODULES
    names = [a.name for a in chat_action.registered_actions()]
    assert phan_hoi.RATE_ACTION_NAME in names
    assert phan_hoi.CLOSE_ACTION_NAME in names
    assert phan_hoi.REPORT_ACTION_NAME in names
    assert names[-1] == "tra_cuu_loi_tuong_tu"
