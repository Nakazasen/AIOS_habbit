# -*- coding: utf-8 -*-
"""Automated test suite for ticket DESKTOP-HOME-FUZZY-MEMORY-SEARCH-VERIFY-FIX.

Covers:
1. Ground Truth verification for all scenarios:
   - Scenario 1 (Accented & Unaccented): Virgo x [2023-08-01, 2023-10-31] x lệch lề tờ postcard -> exactly 11 cases.
   - Scenario 2 (Single Month): 6th Next x tháng 1 năm 2023 x màn hình trắng -> exactly 1 case (ID 38, Phiếu 2023/38).
   - Scenario 3 (Quarter): Virgo x quý 4 năm 2023 x lệch lề tờ postcard -> exactly 12 cases.
   - Scenario 4 (0-case combo with near-matches): Iris x [2023-08-01, 2023-10-31] x lệch lề postcard -> 0 cases,
     near matches on Virgo proposed with '[Gần đúng - Dòng máy khác: Virgo]', logged with is_zero_result=True.
2. Domain Scope Isolation (Requirements 2.7 & 2.8) across 4 notebooks:
   - Sổ Điều tra lỗi (NB-LAZY-DTL): matches() is True; returns cases for JAM4212; returns 11 cases for Scenario 1.
   - Sổ MOM (mom_opcenter): matches() is False; does NOT return 63 cases or KDTPS cases;
     honest response explains MOM (44 docs) lacks technical data and suggests switching to Sổ Điều tra lỗi.
   - Sổ LSU (NB-LAZY-LSU): matches() is False; error lookup does not fire.
   - Sổ Tổng hợp (NB-C26E1C84): matches() is False; error lookup does not fire.
3. Non-regression of FILTER ticket:
   - Iris: 6,961 cases
   - Serial WD72Z12772: 1 case
   - C7620 nam 2025: 60 cases
   - Virgo: 3,182 cases
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from aios_habit import chat_action as ca
from aios_habit.chat_action_error_lookup import (
    ACTION_NAME,
    extract_codes,
    extract_date_entities,
    extract_filter_entities,
    extract_machine_entities,
    extract_phenomenon_concepts,
    log_filter_event,
    search_similar,
    _is_dieu_tra_loi_scope,
    _open_ro,
)
from aios_habit.workspace_chat_app import _run_chat_turn_async
from aios_habit.workspace_chat_store import load_messages

DB_PATH = Path(r"C:\tmp\kdtps_standard\error_cases_reconciled.db")


@pytest.fixture(autouse=True)
def _reset_actions():
    ca.reset_actions()
    ca.load_builtin_actions()
    yield
    ca.reset_actions()


# -----------------------------------------------------------------------------
# 1. SCENARIO 1: User Scenario (Accented & Unaccented)
# -----------------------------------------------------------------------------

@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_scenario_1_user_query_accented():
    """Scenario 1 (accented): 'tìm các ca máy Virgo từ tháng 8 đến tháng 10 năm 2023 bị lệch lề tờ postcard'."""
    q = "tìm các ca máy Virgo từ tháng 8 đến tháng 10 năm 2023 bị lệch lề tờ postcard"
    conn = _open_ro(DB_PATH)
    try:
        # Entity extraction check
        ents = extract_filter_entities(conn, q)
        assert ents["machine"] is not None and ents["machine"]["name"] == "Virgo"
        assert ents["date_range"] is not None
        assert ents["date_range"]["params"] == ["2023-08-01", "2023-10-31"]
        concept_ids = [c["id"] for c in ents.get("phenomenon_concepts", [])]
        assert "POSTCARD" in concept_ids
        assert "SKEW_MARGIN" in concept_ids

        # Search matching
        cases, codes, total = search_similar(conn, q, filter_entities=ents)
        assert total == 11, f"Expected exactly 11 cases for Scenario 1 Ground Truth, got {total}"
        assert len(cases) == 5  # Top 5 cards rendered

        expected_ids = {2057, 2253, 2278, 2336, 2418, 2438, 2496, 2521, 2618, 2654, 2692}
        all_11_ids = {c["id"] for c in cases}
        assert all_11_ids.issubset(expected_ids)
        for c in cases:
            assert "virgo" in c["machine_type"].lower()
            assert "2023-08-01" <= c["occurred_at"] <= "2023-10-31"

        # End-to-end chat action dispatch
        req = ca.ChatActionRequest(question=q, notebook_id="NB-LAZY-DTL", context={"forced_domain": "dieu_tra_loi"})
        outcome = ca.dispatch_multi(req)
        assert outcome is not None
        rendered = ca.render_outcome(outcome)
        assert "Virgo" in rendered
        assert "11" in rendered
        assert "2023-08-01" in rendered or "2023" in rendered
    finally:
        conn.close()


@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_scenario_1_user_query_unaccented():
    """Scenario 1 (unaccented): 'tim cac ca may Virgo tu thang 8 den thang 10 nam 2023 lech le to postcard'."""
    q = "tim cac ca may Virgo tu thang 8 den thang 10 nam 2023 lech le to postcard"
    conn = _open_ro(DB_PATH)
    try:
        ents = extract_filter_entities(conn, q)
        assert ents["machine"] is not None and ents["machine"]["name"] == "Virgo"
        assert ents["date_range"] is not None
        assert ents["date_range"]["params"] == ["2023-08-01", "2023-10-31"]
        concept_ids = [c["id"] for c in ents.get("phenomenon_concepts", [])]
        assert "POSTCARD" in concept_ids
        assert "SKEW_MARGIN" in concept_ids

        cases, codes, total = search_similar(conn, q, filter_entities=ents)
        assert total == 11, f"Expected exactly 11 cases for unaccented query, got {total}"
        for c in cases:
            assert "virgo" in c["machine_type"].lower()
            assert "2023-08-01" <= c["occurred_at"] <= "2023-10-31"

        req = ca.ChatActionRequest(question=q, notebook_id="NB-LAZY-DTL", context={"forced_domain": "dieu_tra_loi"})
        outcome = ca.dispatch_multi(req)
        assert outcome is not None
        rendered = ca.render_outcome(outcome)
        assert "11" in rendered
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# 2. SCENARIO 2: Single Month (6th Next, Jan 2023, White Screen)
# -----------------------------------------------------------------------------

@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_scenario_2_single_month_white_screen():
    """Scenario 2: 'cac ca may 6th Next thang 1 nam 2023 bi man hinh trang'."""
    q = "cac ca may 6th Next thang 1 nam 2023 bi man hinh trang"
    conn = _open_ro(DB_PATH)
    try:
        ents = extract_filter_entities(conn, q)
        assert ents["machine"] is not None and ents["machine"]["name"] == "6thNext"
        assert ents["date_range"] is not None
        assert ents["date_range"]["params"] == ["2023-01%"]
        concept_ids = [c["id"] for c in ents.get("phenomenon_concepts", [])]
        assert "WHITE_SCREEN" in concept_ids

        cases, codes, total = search_similar(conn, q, filter_entities=ents)
        assert total == 1, f"Expected exactly 1 case for Scenario 2, got {total}"
        assert len(cases) == 1
        assert cases[0]["id"] == 38
        assert cases[0]["no_dvd"] == "2023/38"
        assert cases[0]["occurred_at"] == "2023-01-10"
        assert "6th" in cases[0]["machine_type"].lower()

        req = ca.ChatActionRequest(question=q, notebook_id="NB-LAZY-DTL", context={"forced_domain": "dieu_tra_loi"})
        outcome = ca.dispatch_multi(req)
        assert outcome is not None
        rendered = ca.render_outcome(outcome)
        assert "2023/38" in rendered
        assert "6th Next" in rendered
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# 3. SCENARIO 3: Quarter (Virgo, Q4 2023, Postcard Skew)
# -----------------------------------------------------------------------------

@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_scenario_3_quarter_q4_2023():
    """Scenario 3: 'cac ca may Virgo quy 4 nam 2023 lech le to postcard'."""
    q = "cac ca may Virgo quy 4 nam 2023 lech le to postcard"
    conn = _open_ro(DB_PATH)
    try:
        ents = extract_filter_entities(conn, q)
        assert ents["machine"] is not None and ents["machine"]["name"] == "Virgo"
        assert ents["date_range"] is not None
        assert ents["date_range"]["params"] == ["2023-10-01", "2023-12-31"]
        concept_ids = [c["id"] for c in ents.get("phenomenon_concepts", [])]
        assert "POSTCARD" in concept_ids

        cases, codes, total = search_similar(conn, q, filter_entities=ents)
        assert total == 12, f"Expected exactly 12 cases for Scenario 3 Ground Truth, got {total}"
        for c in cases:
            assert "virgo" in c["machine_type"].lower()
            assert "2023-10-01" <= c["occurred_at"] <= "2023-12-31"

        req = ca.ChatActionRequest(question=q, notebook_id="NB-LAZY-DTL", context={"forced_domain": "dieu_tra_loi"})
        outcome = ca.dispatch_multi(req)
        assert outcome is not None
        rendered = ca.render_outcome(outcome)
        assert "12" in rendered
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# 4. SCENARIO 4: 0-Case Combo with Near-Matches Honesty
# -----------------------------------------------------------------------------

@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_scenario_4_zero_cases_with_near_matches(tmp_path: Path):
    """Scenario 4: Iris has 0 cases of postcard skew in Aug-Oct 2023; proposes Virgo near matches."""
    q = "may Iris tu thang 8 den thang 10 nam 2023 bi lech le to postcard"
    conn = _open_ro(DB_PATH)
    try:
        ents = extract_filter_entities(conn, q)
        cases, codes, total = search_similar(conn, q, filter_entities=ents)
        assert total == 0, f"Expected 0 cases for Iris in this timeframe, got {total}"
        assert len(cases) > 0, "Expected near-match cases to be proposed"
        for c in cases:
            assert c.get("is_near_match") is True or bool(c.get("near_match_label"))
            assert "Virgo" in str(c.get("near_match_label") or "") or "Khác" in str(c.get("near_match_label") or "")

        # Rendered output honesty
        req = ca.ChatActionRequest(question=q, notebook_id="NB-LAZY-DTL", context={"forced_domain": "dieu_tra_loi"})
        outcome = ca.dispatch_multi(req)
        assert outcome is not None
        rendered = ca.render_outcome(outcome)
        assert "0 ca" in rendered
        assert "Gần đúng" in rendered

        # Event logging check
        log_filter_event(
            question=q,
            entities={"machine": "Iris", "serial": None, "date_range": "2023-08-01 .. 2023-10-31", "codes": []},
            matched_count=0,
            top_cases=cases,
            conversation_id="CONV-SCENARIO-4",
            base_dir=tmp_path,
        )
        log_file = tmp_path / "machine_serial_date_filter_events.jsonl"
        assert log_file.is_file()
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        ev = json.loads(lines[0])
        assert ev["matched_count"] == 0
        assert ev.get("is_zero_result") is True
        assert len(ev.get("near_match_dvds", [])) > 0
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# 5. DOMAIN SCOPE ISOLATION (Requirements 2.7 & 2.8) across 4 Notebooks
# -----------------------------------------------------------------------------

def test_domain_scope_isolation_check():
    """Verify Requirements 2.7 & 2.8: Error case lookup strictly locked to Sổ Điều tra lỗi."""
    # 1. Check helper function
    req_dtl = ca.ChatActionRequest(question="JAM4212", notebook_id="NB-LAZY-DTL")
    req_dtl2 = ca.ChatActionRequest(question="JAM4212", notebook_id="dieu_tra_loi")
    req_mom = ca.ChatActionRequest(question="JAM4212", notebook_id="mom_opcenter")
    req_lsu = ca.ChatActionRequest(question="JAM4212", notebook_id="NB-LAZY-LSU")
    req_tonghop = ca.ChatActionRequest(question="JAM4212", notebook_id="NB-C26E1C84")

    assert _is_dieu_tra_loi_scope(req_dtl) is True
    assert _is_dieu_tra_loi_scope(req_dtl2) is True
    assert _is_dieu_tra_loi_scope(req_mom) is False
    assert _is_dieu_tra_loi_scope(req_lsu) is False
    assert _is_dieu_tra_loi_scope(req_tonghop) is False

    # 2. Sổ Điều tra lỗi (NB-LAZY-DTL): matches() is True
    assert ca.dispatch_multi(req_dtl) is not None

    # 3. Sổ MOM (mom_opcenter): matches() is False (does NOT trigger error lookup action)
    assert ca.dispatch_multi(req_mom) is None

    # 4. Sổ LSU (NB-LAZY-LSU): matches() is False
    assert ca.dispatch_multi(req_lsu) is None

    # 5. Sổ Tổng hợp (NB-C26E1C84): matches() is False
    assert ca.dispatch_multi(req_tonghop) is None


def test_mom_opcenter_honest_answer_when_error_code_queried():
    """Verify Req 2.8: In Sổ MOM, querying JAM4212 produces honest answer stating MOM lacks data and suggests Sổ DTL."""
    conv_id = "test_conv_mom_scope_verify"
    ok, ans, badge, err = _run_chat_turn_async(
        q_text="JAM4212",
        notebook_id="mom_opcenter",
        ai_mode="grounded",
        conversation_id=conv_id,
    )
    assert ok is True
    msgs = load_messages(conv_id)
    assert len(msgs) >= 2
    last_content = msgs[-1].content

    # Strict isolation assertions
    assert "30.075" in last_content
    assert "Sổ Điều tra lỗi" in last_content or "NB-LAZY-DTL" in last_content
    assert "chưa có dữ liệu kỹ thuật về mã lỗi" in last_content or "không có dữ liệu" in last_content
    # MUST NOT leak 63 cases
    assert "63 ca" not in last_content
    assert "- **Máy:**" not in last_content


@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_dieu_tra_loi_retains_cases_for_jam4212():
    """Verify Req 2.8 control check: In Sổ Điều tra lỗi, JAM4212 retains error lookup behavior."""
    conn = _open_ro(DB_PATH)
    try:
        cases, codes, total = search_similar(conn, "JAM4212")
        assert "JAM4212" in codes
        assert total in (63, 30075) or total > 0
        assert len(cases) > 0

        req = ca.ChatActionRequest(question="JAM4212", notebook_id="NB-LAZY-DTL", context={"forced_domain": "dieu_tra_loi"})
        outcome = ca.dispatch_multi(req)
        assert outcome is not None
        rendered = ca.render_outcome(outcome)
        assert "30.075" in rendered or "63" in rendered
        assert "JAM4212" in rendered
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# 6. NON-REGRESSION OF PREVIOUS FILTER TICKET GATES
# -----------------------------------------------------------------------------

@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_filter_non_regression_gates():
    """Verify non-regression of all previously accepted filter gates."""
    conn = _open_ro(DB_PATH)
    try:
        # Iris 6,961 cases
        _, _, total_iris = search_similar(conn, "cac ca cua may Iris")
        assert total_iris == 6961

        # Serial WD72Z12772 = 1 case
        cases_serial, _, total_serial = search_similar(conn, "serial WD72Z12772")
        assert total_serial == 1
        assert cases_serial[0]["no_dvd"] == "2023/1"

        # C7620 nam 2025 = 60 cases
        _, _, total_c7620_2025 = search_similar(conn, "C7620 nam 2025")
        assert total_c7620_2025 == 60

        # Virgo = 3,182 cases
        _, _, total_virgo = search_similar(conn, "cac ca cua may Virgo")
        assert total_virgo == 3182
    finally:
        conn.close()
