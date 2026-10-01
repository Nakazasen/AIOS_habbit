"""Tests for the B1-FEAT chat action: tra cứu lỗi tương tự.

The DB fixture is built from the REAL `Loi KDTPS.xlsx` (History KDTPS
sheet) plus the real JAM / SCT_ADJ glossaries, so the "5 real error
codes" acceptance runs against real data, not SIMULATED_* fixtures.
"""

from __future__ import annotations

import os
import time

import pytest

from aios_habit import chat_action
from aios_habit import chat_action_error_lookup as lookup
from aios_habit.chat_action import (
    ChatActionRequest,
    load_builtin_actions,
    match_action,
    registered_actions,
    render_outcome,
    reset_actions,
)
from aios_habit.error_cases import (
    connect,
    count_cases,
    import_glossary,
    import_history,
    init_db,
    init_glossary,
)
from aios_habit.feature_flags import reset_feature_flags

DATA_ROOT = "/home/hatch/workspace/aios_data/dieu_tra_loi/Điều chỉnh"
HISTORY_XLSX = f"{DATA_ROOT}/Lịch sử lỗi/Loi KDTPS.xlsx"

# Five real error codes: four appear verbatim in the history text, C0030 is
# a real C_CALL glossary code (category search path on this VM).
REAL_CODES = ["F000", "C7620", "C3200", "C4701", "C0030"]


@pytest.fixture(scope="module")
def real_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("b1") / "error_cases_real.db"
    conn = connect(str(db_path))
    init_db(conn)
    init_glossary(conn)
    result = import_history(conn, HISTORY_XLSX)
    assert result["status"] == "imported"
    assert result["rows_imported"] > 15000
    base = f"{DATA_ROOT}/Bang ma loi"
    import_glossary(conn, f"{base}/02XC_機能定義書_JAM一覧 (1).xls", "JAM")
    import_glossary(conn, f"{DATA_ROOT}/SCT自動調整エラーコード一覧_140221.xls", "SCT_ADJ")
    conn.close()
    old = os.environ.get("AIOS_ERROR_CASES_DB")
    os.environ["AIOS_ERROR_CASES_DB"] = str(db_path)
    yield db_path
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


def _dispatch(question, context=None):
    load_builtin_actions()
    request = ChatActionRequest(question=question, context=dict(context or {}))
    action = match_action(request)
    assert action is not None and action.name == lookup.ACTION_NAME
    return action.handler(request)


# --------------------------------------------------------------------------
# B1 acceptance: 5 real error codes -> top 3-5 cards, < 1 minute
# --------------------------------------------------------------------------


def test_five_real_codes_return_cards(real_db):
    started = time.time()
    for code in REAL_CODES:
        outcome = _dispatch(code)
        assert outcome is not None, f"no outcome for real code {code}"
        text = render_outcome(outcome)
        cards = [ln for ln in text.splitlines() if ln.startswith("### ")]
        assert 3 <= len(cards) <= 5, f"{code}: expected 3-5 cards, got {len(cards)}"
        for field in ("Hiện tượng:", "Nguyên nhân:", "Đối sách:", "Báo cáo gốc:"):
            assert field in text, f"{code}: missing card field {field}"
        assert "Loi KDTPS.xlsx" in text, f"{code}: report provenance missing"
    elapsed = time.time() - started
    assert elapsed < 60, f"5 real-code lookups took {elapsed:.1f}s (> 60s)"


def test_code_with_hint_words(real_db):
    outcome = _dispatch("tra cứu lỗi C7620 là lỗi gì, cách khắc phục?")
    assert outcome is not None
    text = render_outcome(outcome)
    assert "C7620" in text
    assert text.count("### ") >= 3


def test_symptom_text_without_code(real_db):
    outcome = _dispatch("máy in bị kẹt giấy, màn hình báo Jam9600 thì sửa sao?")
    assert outcome is not None
    text = render_outcome(outcome)
    assert text.count("### ") >= 3


# --------------------------------------------------------------------------
# Matching behaviour
# --------------------------------------------------------------------------


def test_bare_code_matches_without_hint_words():
    load_builtin_actions()
    request = ChatActionRequest(question="C7620")
    action = match_action(request)
    assert action is not None and action.name == lookup.ACTION_NAME


def test_hint_matches():
    load_builtin_actions()
    request = ChatActionRequest(question="tra cứu lịch sử lỗi máy in")
    action = match_action(request)
    assert action is not None and action.name == lookup.ACTION_NAME


def test_unrelated_question_does_not_match():
    load_builtin_actions()
    request = ChatActionRequest(question="hôm nay thời tiết thế nào?")
    assert match_action(request) is None


def test_extract_codes_normalizes():
    assert lookup.extract_codes("lỗi c 7620 và F000") == ["C7620", "F000"]
    assert lookup.extract_codes("không có mã") == []


# --------------------------------------------------------------------------
# Fail-closed: missing / empty DB -> None (normal RAG flow continues)
# --------------------------------------------------------------------------


def test_missing_db_returns_none():
    old = os.environ.pop("AIOS_ERROR_CASES_DB", None)
    try:
        outcome = _dispatch("C7620", context={"error_cases_db": "/khong/co/file.db"})
        assert outcome is None
    finally:
        if old is not None:
            os.environ["AIOS_ERROR_CASES_DB"] = old


def test_empty_db_returns_none(tmp_path):
    db_path = tmp_path / "empty.db"
    conn = connect(str(db_path))
    init_db(conn)
    conn.close()
    outcome = _dispatch("C7620", context={"error_cases_db": str(db_path)})
    assert outcome is None


# --------------------------------------------------------------------------
# Rendering: glossary meaning header + card shape
# --------------------------------------------------------------------------


def test_render_cards_with_glossary_meaning():
    cases = [
        {
            "no_dvd": "2023/5",
            "where": "6th Next / A15",
            "category": "C CALL",
            "hien_tuong": "LCD hiện C0030",
            "nguyen_nhan": "Hỏng board FAX",
            "doi_sach": "Thay board",
            "bao_cao_goc": "Loi KDTPS.xlsx › History KDTPS › dòng 9",
        }
    ]
    glossary = {
        "C0030": {
            "name_vi": "Bất thường hệ thống bản mạch FAX",
            "cause": "Board FAX lỗi",
            "remedy": "Thay board",
        }
    }
    text = lookup._render_cards(cases, ["C0030"], glossary, 15707)
    assert "Bất thường hệ thống bản mạch FAX" in text
    assert "### 1. Phiếu 2023/5" in text
    assert "Báo cáo gốc:" in text


def test_registered_as_builtin_last():
    load_builtin_actions()
    names = [a.name for a in registered_actions()]
    assert lookup.ACTION_NAME in names
    # Lowest match priority: appended after the TOOL-1..5 actions.
    assert names[-1] == lookup.ACTION_NAME


def test_db_is_real_not_simulated(real_db):
    conn = connect(str(real_db))
    try:
        assert count_cases(conn) > 15000
    finally:
        conn.close()


# --------------------------------------------------------------------------
# QD1 (2026-10-01): on a code lookup, cases carrying a real code rank first
# --------------------------------------------------------------------------


def _real_conn(real_db):
    return connect(str(real_db))


def test_code_lookup_prefers_real_code_cases(real_db):
    conn = _real_conn(real_db)
    try:
        cases, codes, _total = lookup.search_similar(conn, "F000")
        assert codes == ["F000"]
        assert 3 <= len(cases) <= 5
        flags = [c["co_ma_that"] for c in cases]
        assert any(flags), "expected real-code cases in top results"
        # All real-code cases come before any code-missing case.
        seen_missing = False
        for flag in flags:
            if not flag:
                seen_missing = True
            elif seen_missing:
                pytest.fail("a real-code case ranked below a code-missing case")
    finally:
        conn.close()


def test_symptom_search_keeps_score_order(real_db):
    conn = _real_conn(real_db)
    try:
        cases, codes, _total = lookup.search_similar(conn, "kẹt giấy")
        assert codes == []
        assert len(cases) >= 3
    finally:
        conn.close()


def test_code_missing_column_respected(real_db, tmp_path):
    import shutil
    import sqlite3

    flagged = tmp_path / "flagged.db"
    shutil.copy(str(real_db), flagged)
    conn = sqlite3.connect(str(flagged))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("ALTER TABLE error_cases ADD COLUMN code_missing INTEGER DEFAULT 0")
        target = conn.execute(
            "SELECT id FROM error_cases "
            "WHERE error_code_i IS NOT NULL AND error_code_i <> '' LIMIT 1"
        ).fetchone()
        assert target is not None
        conn.execute("UPDATE error_cases SET code_missing = 1 WHERE id = ?", (target["id"],))
        conn.commit()
        row = conn.execute("SELECT * FROM error_cases WHERE id = ?", (target["id"],)).fetchone()
        assert lookup._has_code_missing_col(conn)
        assert not lookup._has_real_code(row, True)
        # Same row counts as a real code once the flag column is ignored.
        assert lookup._has_real_code(row, False)
    finally:
        conn.close()


# --------------------------------------------------------------------------
# QD2 (2026-10-01): empty countermeasure + recorded immediate action (M/O)
# means "no formal countermeasure needed"
# --------------------------------------------------------------------------


_QD2_SELECT = (
    "SELECT ec.*, b.source_file, b.sheet_name FROM error_cases ec "
    "LEFT JOIN import_batches b ON b.id = ec.batch_id"
)


def test_qd2_empty_countermeasure_with_immediate_action(real_db):
    import json

    conn = _real_conn(real_db)
    try:
        found = None
        for r in conn.execute(_QD2_SELECT):
            d = json.loads(r["raw_json"] or "{}")
            ab = str(d.get("AB") or "").strip()
            mo = str(d.get("M") or "").strip() or str(d.get("O") or "").strip()
            if ab in ("", "-", "—", "ー") and mo:
                found = r
                break
        assert found is not None, "no QD2-style row in real data"
        card = lookup._case_dict(found)
        assert card["doi_sach"] == "Không cần đối sách chính thức"
    finally:
        conn.close()


def test_qd2_empty_countermeasure_without_immediate_action(real_db):
    import json

    conn = _real_conn(real_db)
    try:
        found = None
        for r in conn.execute(_QD2_SELECT):
            d = json.loads(r["raw_json"] or "{}")
            ab = str(d.get("AB") or "").strip()
            mo = str(d.get("M") or "").strip() or str(d.get("O") or "").strip()
            if ab in ("", "-", "—", "ー") and not mo:
                found = r
                break
        if found is None:
            pytest.skip("real data has no fully-empty countermeasure row")
        card = lookup._case_dict(found)
        assert card["doi_sach"] == ""
    finally:
        conn.close()
