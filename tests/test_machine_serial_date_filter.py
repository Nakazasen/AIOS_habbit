# -*- coding: utf-8 -*-
"""Automated test suite for ticket DESKTOP-HOME-MACHINE-SERIAL-DATE-FILTER.

Verifies:
1. Entity recognition covering all distinct machine_types in DB (Iris, 6thNext/6th Next,
   Virgo, Libra2/Libra 2, Sirius2/Sirius 2, Polaris Next, Mebius, Brazil, Kairos, etc.).
2. Serial pattern recognition (WD72Z12772, 3V2XM1930) matching raw_json['G'].
3. Date & date range recognition (year, month/year, from-to range, exact date).
4. Structured SQL filtering (AND combinations with error codes/keywords, or standalone
   filter returning exact matched count).
5. Card summary line: "- **Máy:** <machine_type> | **Serial:** <serial> | **Ngày phát sinh:** <occurred_at>"
   matching the original record in citation_source_viewer.
6. Regression: normal queries without filter (C6770, C7620, JAM4212) remain unchanged.
7. Continuous improvement event logging to local_cases/machine_serial_date_filter_events.jsonl.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import pytest

from aios_habit import chat_action as ca
from aios_habit.chat_action_error_lookup import (
    ACTION_NAME,
    extract_codes,
    extract_date_entities,
    extract_filter_entities,
    extract_machine_entities,
    extract_serial_entities,
    get_machine_registry,
    log_filter_event,
    resolve_db_path,
    search_similar,
    _open_ro,
)
from aios_habit.citation_source_viewer import (
    CitationRef,
    resolve_citation_source,
)
from aios_habit.final_answer_composer import deliver_5tier_ladder_answer

DB_PATH = Path(r"C:\tmp\kdtps_standard\error_cases_reconciled.db")


@pytest.fixture(autouse=True)
def _reset_actions():
    ca.reset_actions()
    ca.load_builtin_actions()
    yield
    ca.reset_actions()


@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_machine_registry_covers_all_db_machine_types():
    """Verify 2.1(a): machine registry is built from distinct DB machine_types, not a hardcoded short list."""
    conn = _open_ro(DB_PATH)
    try:
        reg = get_machine_registry(conn)
        assert len(reg) > 100, f"Expected broad registry from distinct DB values, got {len(reg)}"
        for expected in (
            "iris", "iris2020", "iris2024", "6thnext", "polarisnext",
            "virgo", "libra", "libra2", "sirius", "sirius2", "mebius", "brazil", "kairos"
        ):
            assert expected in reg, f"Missing {expected} in machine registry"
    finally:
        conn.close()


@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_entity_recognition_machines_serials_dates():
    """Verify entity extraction for machines, serials, and date ranges."""
    conn = _open_ro(DB_PATH)
    try:
        # Machines (Iris, 6thNext, Virgo, Libra2, Sirius2, Polaris Next)
        assert extract_machine_entities(conn, "cac ca cua may Iris")["name"] == "Iris"
        assert extract_machine_entities(conn, "máy 6thNext")["name"] == "6thNext"
        assert extract_machine_entities(conn, "máy 6th Next")["name"] == "6thNext"
        assert extract_machine_entities(conn, "cac ca may Virgo")["name"] == "Virgo"
        assert extract_machine_entities(conn, "may Libra2")["name"] == "Libra 2"
        assert extract_machine_entities(conn, "máy Libra 2")["name"] == "Libra 2"
        assert extract_machine_entities(conn, "may Sirius2")["name"] == "Sirius 2"
        assert extract_machine_entities(conn, "máy Sirius 2")["name"] == "Sirius 2"
        assert extract_machine_entities(conn, "dòng máy Polaris Next")["name"] == "Polaris Next"

        # Serials
        assert extract_serial_entities("serial WD72Z12772") == "WD72Z12772"
        assert extract_serial_entities("tra cứu WD72Z12772") == "WD72Z12772"
        assert extract_serial_entities("số máy 3V2XM1930") == "3V2XM1930"
        assert extract_serial_entities("C7620") is None

        # Dates
        d_yr = extract_date_entities("C7620 năm 2025")
        assert d_yr is not None and d_yr["type"] == "year" and d_yr["params"] == ["2025%"]

        d_my = extract_date_entities("các ca tháng 1/2023")
        assert d_my is not None and d_my["type"] == "month" and d_my["params"] == ["2023-01%"]

        d_rng = extract_date_entities("từ 2023-01-01 đến 2023-01-31")
        assert d_rng is not None and d_rng["type"] == "range" and d_rng["params"] == ["2023-01-01", "2023-01-31"]
    finally:
        conn.close()


@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_filter_iris_matches_baseline_6961():
    """Verify Gate 1: Querying Iris returns all Iris family cases and declares 6,961 matched cases."""
    q = "cac ca cua may Iris"
    req = ca.ChatActionRequest(question=q, notebook_id="NB-LAZY-DTL", context={"forced_domain": "dieu_tra_loi"})
    outcome = ca.dispatch_multi(req)
    assert outcome is not None
    rendered = ca.render_outcome(outcome)
    assert "Iris" in rendered
    assert "6.961" in rendered

    conn = _open_ro(DB_PATH)
    try:
        cases, _, total = search_similar(conn, q)
        assert total == 6961
        assert len(cases) == 5
        for c in cases:
            assert "iris" in c["machine_type"].lower()
    finally:
        conn.close()


@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_filter_other_machines_virgo_libra2_sirius2():
    """Verify Supplementary Gate (04:02): At least 2 other machines besides Iris/6thNext match independent SQL counts."""
    conn = _open_ro(DB_PATH)
    try:
        # 1. Virgo -> 3,182 cases
        sql_virgo = conn.execute("SELECT COUNT(*) FROM error_cases WHERE REPLACE(machine_type, ' ', '') LIKE '%Virgo%'").fetchone()[0]
        cases_v, _, total_v = search_similar(conn, "cac ca cua may Virgo")
        assert total_v == sql_virgo == 3182
        for c in cases_v:
            assert "virgo" in c["machine_type"].lower()

        # 2. Libra2 -> 483 cases
        sql_libra2 = conn.execute("SELECT COUNT(*) FROM error_cases WHERE REPLACE(machine_type, ' ', '') LIKE '%Libra2%'").fetchone()[0]
        cases_l, _, total_l = search_similar(conn, "cac ca cua may Libra2")
        assert total_l == sql_libra2 == 483
        for c in cases_l:
            assert "libra" in c["machine_type"].lower().replace(" ", "")

        # 3. Sirius2 -> 1,231 cases
        sql_sirius2 = conn.execute("SELECT COUNT(*) FROM error_cases WHERE REPLACE(machine_type, ' ', '') LIKE '%Sirius2%'").fetchone()[0]
        cases_s, _, total_s = search_similar(conn, "cac ca cua may Sirius2")
        assert total_s == sql_sirius2 == 1231
        for c in cases_s:
            assert "sirius" in c["machine_type"].lower().replace(" ", "")

        # 4. 6thNext -> 1,068 cases
        cases_6, _, total_6 = search_similar(conn, "cac ca cua may 6thNext")
        assert total_6 == 1068
    finally:
        conn.close()


@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_filter_serial_wd72z12772_exact_match():
    """Verify Gate 2: Querying serial WD72Z12772 returns exact case (phieu 2023/1, 6th Next, 2023-01-05)."""
    q = "serial WD72Z12772"
    req = ca.ChatActionRequest(question=q, notebook_id="NB-LAZY-DTL", context={"forced_domain": "dieu_tra_loi"})
    outcome = ca.dispatch_multi(req)
    assert outcome is not None
    rendered = ca.render_outcome(outcome)

    assert "WD72Z12772" in rendered
    assert "2023/1" in rendered
    assert "6th Next" in rendered
    assert "2023-01-05" in rendered
    assert "- **Máy:** 6th Next | **Serial:** 110C0Y3NL0 WD72Z12772 | **Ngày phát sinh:** 2023-01-05" in rendered

    conn = _open_ro(DB_PATH)
    try:
        cases, _, total = search_similar(conn, q)
        assert total == 1
        assert len(cases) == 1
        assert cases[0]["id"] == 1
        assert cases[0]["no_dvd"] == "2023/1"
        assert cases[0]["occurred_at"] == "2023-01-05"
    finally:
        conn.close()


@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_filter_code_plus_year_c7620_2025():
    """Verify Gate 3: Querying C7620 nam 2025 returns only cases with occurred_at in 2025."""
    q = "C7620 nam 2025"
    conn = _open_ro(DB_PATH)
    try:
        cases, codes, total = search_similar(conn, q)
        assert "C7620" in codes
        assert total == 60
        assert len(cases) > 0
        for c in cases:
            assert c["occurred_at"].startswith("2025"), f"Case {c['no_dvd']} has date {c['occurred_at']} not in 2025"
    finally:
        conn.close()


@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_summary_line_matches_citation_source_viewer():
    """Verify Gate 5: Summary line on card matches verbatim record in citation_source_viewer."""
    conn = _open_ro(DB_PATH)
    try:
        cases, _, _ = search_similar(conn, "serial WD72Z12772")
        c = cases[0]
        ref = CitationRef(
            id="cite_test_1",
            ref_type="db_error_case",
            raw_text=c["bao_cao_goc"],
            label=c["bao_cao_goc"],
            source_file="Loi KDTPS.xlsx",
            sheet_name="History KDTPS",
            source_row=5,
            case_id=c["id"],
        )
        payload = resolve_citation_source(ref)
        assert payload.found
        field_map = {f.column_letter: f.value for f in payload.fields}
        assert field_map["C"] == c["occurred_at"] == "2023-01-05"
        assert field_map["D"].strip() == c["machine_type"] == "6th Next"
        assert field_map["G"] == c["serial"] == "110C0Y3NL0 WD72Z12772"
    finally:
        conn.close()


@pytest.mark.skipif(not DB_PATH.is_file(), reason="Missing reconciled DB")
def test_regression_unfiltered_queries_unchanged():
    """Verify Gate 4: Normal queries without filter (C6770, C7620, JAM4212) retain 30,075 total and behavior."""
    for code_q in ("C6770", "C7620", "JAM4212"):
        req = ca.ChatActionRequest(question=code_q, notebook_id="NB-LAZY-DTL", context={"forced_domain": "dieu_tra_loi"})
        outcome = ca.dispatch_multi(req)
        assert outcome is not None
        rendered = ca.render_outcome(outcome)
        assert "30.075" in rendered
        assert "- **Máy:**" in rendered
        assert "| **Serial:**" in rendered
        assert "| **Ngày phát sinh:**" in rendered


def test_continuous_improvement_event_logging(tmp_path: Path):
    """Verify Requirement 2.5: Every filter invocation logs an event to machine_serial_date_filter_events.jsonl."""
    log_filter_event(
        question="cac ca cua may Iris",
        entities={"machine": "Iris", "serial": None, "date_range": None, "codes": []},
        matched_count=6961,
        top_cases=[{"id": 8286, "no_dvd": "2025/5348"}],
        conversation_id="CONV-TEST-001",
        base_dir=tmp_path,
    )
    log_file = tmp_path / "machine_serial_date_filter_events.jsonl"
    assert log_file.is_file()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["question"] == "cac ca cua may Iris"
    assert data["entities"]["machine"] == "Iris"
    assert data["matched_count"] == 6961
    assert data["top_dvds"] == ["2025/5348"]
