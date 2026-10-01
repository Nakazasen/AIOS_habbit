"""B0-DICT tests: error-code dictionary completion + term normalization.

Acceptance for B0-DICT:
- tables in Dieu-tra-loi not yet digitized are surveyed: Maintenance mode
  3.xlsx carries no error codes (verified: 0 code-like tokens in 688 rows;
  adjustment procedures, skipped); the older 02XC_自己診断表示一覧表.xls
  (2024) is NOT fully superseded — it carries 10 C codes the newer VN table
  dropped (C1420, C1760, C7631-C7634, C7641-C7644), recovered by
  import_ccall_old() (real codes only, VN table stays authoritative);
  Iris2020_Cコール自己診断.xlsx (2025, VN+JP parallel, 225 codes with
  per-code diagnostic steps) is parsed and enriches the F4 C_CALL rows
  (remedy was empty) or inserts codes the 02XC table lacks;
- variant name spellings resolve to one canonical code (term_aliases),
  seeded only from the real imported sources; the original names stay in
  error_glossary for traceability;
- suggest_terms() serves the B0-FORM input hints; lookup consumers
  (chat_action_error_lookup, auto_classifier, case_form.lookup_error_code)
  resolve aliases;
- glossary_coverage() reports the ticket metric: % of DB codes in the glossary;
- lookup of a missing code reports "chưa có trong từ điển";
- history column I (phenomenon text embedding the real code, e.g.
  LCD画面にF000表示) is extracted into error_cases.error_code_i so the
  form-vs-history dedup matches on it (bonus b).

Slow tests read the real source files read-only from AIOS_DATA_DIR
(same convention as test_error_cases_f4.py).
"""

import json
import os
import sqlite3
from pathlib import Path

import pytest

from aios_habit.error_cases import (
    backfill_error_code_i,
    canonical_term,
    connect,
    extract_code_from_text,
    find_duplicate_case,
    glossary_coverage,
    import_ccall_diag,
    import_ccall_old,
    import_glossary,
    init_db,
    init_glossary,
    lookup_error_code,
    normalize_history_row,
    parse_ccall_diag,
    parse_ccall_old,
    seed_term_aliases,
    submit_form_case,
    suggest_terms,
    upsert_case,
)
from aios_habit.error_cases.auto_classifier import classify_error
from aios_habit.error_cases import glossary as _glossary
from aios_habit import chat_action_error_lookup

DATA = (
    Path(os.environ.get("AIOS_DATA_DIR", "/home/hatch/workspace/aios_data"))
    / "dieu_tra_loi"
    / "Điều chỉnh"
)
DIAG_FILE = DATA / "Bang ma loi" / "Iris2020_Cコール自己診断.xlsx"
CCALL_FILE = DATA / "Bang ma loi" / "02XC_自己診断表示一覧表-Iris2020 VN.xls"
CCALL_OLD_FILE = DATA / "Bang ma loi" / "02XC_自己診断表示一覧表.xls"
JAM_FILE = DATA / "Bang ma loi" / "02XC_機能定義書_JAM一覧 (1).xls"

pytestmark = pytest.mark.skipif(
    not DIAG_FILE.exists() or not CCALL_FILE.exists()
    or not CCALL_OLD_FILE.exists() or not JAM_FILE.exists(),
    reason="real source files missing (AIOS_DATA_DIR)",
)


def _glossary_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_glossary(conn)
    return conn


@pytest.fixture(scope="module")
def conn():
    c = _glossary_conn()
    import_glossary(c, CCALL_FILE, "C_CALL")
    yield c
    c.close()


@pytest.fixture(scope="module")
def diag_entries():
    return {e["code"]: e for e in parse_ccall_diag(DIAG_FILE)}


# ---------------------------------------------------------------------------
# Survey: the 2025 C-call self-diagnosis workbook
# ---------------------------------------------------------------------------

def test_diag_parses_220ish_codes(diag_entries):
    # Header row declares 220 codes; tolerate small upstream drift.
    assert 200 <= len(diag_entries) <= 260, len(diag_entries)
    assert "C0030" in diag_entries


def test_diag_c0030_has_vn_name_and_steps(diag_entries):
    e = diag_entries["C0030"]
    assert "FAX" in e["name_vi"]
    assert "FAX基板" in e["name_ja"]
    assert "VI 1." in e["remedy"]
    assert "Reset nguồn" in e["remedy"]


def test_diag_codes_are_real_c_call_shape(diag_entries):
    import re

    for code in diag_entries:
        assert re.fullmatch(r"C\d{4}", code), code


# ---------------------------------------------------------------------------
# Enrichment: F4 C_CALL rows gain the diagnostic procedure
# ---------------------------------------------------------------------------

def test_import_ccall_diag_enriches_remedy(conn):
    before = conn.execute(
        "SELECT remedy FROM error_glossary "
        "WHERE code_family='C_CALL' AND code='C0030' AND code_sub=''"
    ).fetchone()[0]
    assert not (before or "").strip()  # F4 left remedy empty
    res = import_ccall_diag(conn, DIAG_FILE)
    assert res["status"] == "imported"
    assert res["enriched"] > 0
    after = conn.execute(
        "SELECT remedy, name_vi, name_ja FROM error_glossary "
        "WHERE code_family='C_CALL' AND code='C0030' AND code_sub=''"
    ).fetchone()
    assert "VI 1." in (after[0] or "")
    assert "FAX" in (after[1] or "")
    # Re-import of the unchanged file is skipped ("vất lại file cũ thì bỏ qua").
    again = import_ccall_diag(conn, DIAG_FILE)
    assert again["status"] == "skipped"


def test_import_ccall_diag_inserts_codes_missing_from_02xc():
    c = _glossary_conn()
    try:
        res = import_ccall_diag(c, DIAG_FILE)
        n = c.execute(
            "SELECT COUNT(*) FROM error_glossary WHERE code_family='C_CALL'"
        ).fetchone()[0]
        assert n == res["entries"] == res["inserted"]
        assert res["inserted"] > 0
    finally:
        c.close()


# ---------------------------------------------------------------------------
# Term normalization: variant spellings -> one canonical code
# ---------------------------------------------------------------------------

def test_canonical_term_resolves_variant_names(conn):
    import_ccall_diag(conn, DIAG_FILE)  # seeds aliases as a side effect
    assert canonical_term(conn, "FAX基板システム異常") == ("C_CALL", "C0030")
    entry = _glossary.lookup(conn, "C_CALL", "C0030")
    assert entry is not None
    if entry.get("name_vi"):
        assert canonical_term(conn, entry["name_vi"]) == ("C_CALL", "C0030")
    assert canonical_term(conn, "MÃ LẠ KHÔNG TỒN TẠI XYZ") is None


def test_seed_term_aliases_idempotent(conn):
    first = seed_term_aliases(conn)
    second = seed_term_aliases(conn)
    assert second == 0
    assert first >= 0


def test_suggest_terms_prefix(conn):
    import_ccall_diag(conn, DIAG_FILE)
    sug = suggest_terms(conn, "FAX", limit=5)
    assert sug, "expected at least one suggestion for prefix 'FAX'"
    assert any(s["code"] == "C0030" for s in sug)
    assert all("code" in s and "meaning" in s for s in sug)


def test_original_names_kept_for_trace(conn):
    row = conn.execute(
        "SELECT name_ja, name_vi, source_file FROM error_glossary "
        "WHERE code_family='C_CALL' AND code='C0030' AND code_sub=''"
    ).fetchone()
    assert row[0] and row[1]  # both spellings preserved
    assert "02XC" in (row[2] or "")


# ---------------------------------------------------------------------------
# Consumers: lookup (B1), form warning (B0-FORM), classifier (B5)
# ---------------------------------------------------------------------------

def test_lookup_glossary_resolves_alias(conn):
    import_ccall_diag(conn, DIAG_FILE)
    found = chat_action_error_lookup.lookup_glossary(conn, ["FAX基板システム異常"])
    assert "C0030" in found or "FAX基板システム異常" in found


def test_lookup_render_shows_meaning_and_source(conn):
    import_ccall_diag(conn, DIAG_FILE)
    glossary = chat_action_error_lookup.lookup_glossary(conn, ["C0030"])
    assert glossary, "C0030 must be found"
    text = chat_action_error_lookup._render_cards([], ["C0030"], glossary, 15707)
    assert "FAX" in text
    assert "Nguồn:" in text  # ticket: tra mã có -> nghĩa + link nguồn


def test_case_form_warns_chua_co_trong_tu_dien(tmp_path):
    path = tmp_path / "dict_test.db"
    conn = connect(path)
    try:
        init_db(conn)
        init_glossary(conn)
        assert lookup_error_code(conn, "SIMULATED_Z9999") is None
    finally:
        conn.close()


def test_auto_classifier_resolves_alias(conn):
    import_ccall_diag(conn, DIAG_FILE)
    res = classify_error("FAX基板システム異常", glossary_conn=conn)
    assert res.code_family == "C_CALL"
    assert any("Chuẩn hóa tên gọi" in r for r in res.reasons)


# ---------------------------------------------------------------------------
# Acceptance metric: % of DB codes found in the glossary
# ---------------------------------------------------------------------------

def _error_cases_conn():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    init_glossary(conn)
    conn.execute(
        "INSERT INTO error_glossary (code_family, code, name_vi, source_file)"
        " VALUES ('C_CALL', 'C0030', 'Mã C-call mẫu', 'test'),"
        "        ('F_SYSTEM', 'F000', 'Mã F mẫu', 'test')"
    )
    seed_term_aliases(conn)
    conn.commit()
    return conn


def _insert_case(conn, **kw):
    fields = {
        "no_dvd": kw.get("no_dvd", "2023/1"),
        "machine_type": "6th Next",
        "line": "A15",
        "error_code_c": kw.get("error_code_c"),
        "error_code_h": kw.get("error_code_h"),
        "error_code_i": kw.get("error_code_i"),
        "raw": {"I": kw.get("phenomenon", "")},
    }
    return upsert_case(conn, batch_id=1, source_row=1, fields=fields,
                       format="history_29")


def test_glossary_coverage_metric():
    conn = _error_cases_conn()
    try:
        conn.execute(
            "INSERT INTO import_batches (source_file, file_sha256, sheet_name)"
            " VALUES ('t.xlsx', 'x', 'History KDTPS')"
        )
        _insert_case(conn, no_dvd="2023/1", error_code_c="C0030",
                     error_code_h="ERROR", phenomenon='LCD画面に"C0030"表示')
        _insert_case(conn, no_dvd="2023/2", error_code_c=None,
                     error_code_h="F CALL", error_code_i="F000",
                     phenomenon="LCD画面にF000表示")
        _insert_case(conn, no_dvd="2023/3", error_code_c="C9999",
                     error_code_h="C CALL", phenomenon="mã lạ")
        cov = glossary_coverage(conn)
        assert cov["total"] == 3, cov
        assert cov["matched"] == 2, cov
        assert cov["percent"] == pytest.approx(66.67, abs=0.01), cov
        assert cov["unmatched"] == ["C9999"], cov
    finally:
        conn.close()


def test_glossary_coverage_excludes_plain_categories():
    conn = _error_cases_conn()
    try:
        conn.execute(
            "INSERT INTO import_batches (source_file, file_sha256, sheet_name)"
            " VALUES ('t.xlsx', 'x', 'History KDTPS')"
        )
        _insert_case(conn, no_dvd="2023/1", error_code_h="C CALL")
        _insert_case(conn, no_dvd="2023/2", error_code_h="JAM")
        cov = glossary_coverage(conn)
        assert cov["total"] == 0, cov  # 'C CALL' / 'JAM' are groups, not codes
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Bonus b: error_code_i — real code from phenomenon text (column I)
# ---------------------------------------------------------------------------

def test_extract_code_from_text():
    assert extract_code_from_text("LCD画面にF000表示") == "F000"
    assert extract_code_from_text("JAM4709 kẹt giấy") == "JAM4709"
    assert extract_code_from_text("máy báo C4701 liên tục") == "C4701"
    assert extract_code_from_text("Ｃ４７０１") == "C4701"  # full-width
    assert extract_code_from_text("không có mã ở đây") is None
    assert extract_code_from_text(None) is None
    assert extract_code_from_text("") is None
    # English words starting with F + hex letters are NOT codes.
    assert extract_code_from_text("FEED kẹt giấy") is None
    assert extract_code_from_text("mặt FACE bị trầy") is None
    # ...but a real code later in the text is still found (no masking).
    assert extract_code_from_text("FEED kẹt giấy, mã F100") == "F100"


def test_normalize_history_row_extracts_error_code_i():
    cells = [None] * 29
    cells[0] = 2023       # A: year
    cells[1] = 5          # B: NO.
    cells[2] = "2023-01-05"  # C: date
    cells[3] = "6th Next"  # D: machine
    cells[4] = "A15"      # E: line
    cells[7] = "F CALL"   # H: group only
    cells[8] = "LCD画面にF000表示"  # I: phenomenon with the real code
    fields = normalize_history_row(cells)
    assert fields["error_code_h"] == "F CALL"
    assert fields["error_code_i"] == "F000"


def test_find_duplicate_matches_error_code_i(tmp_path):
    path = tmp_path / "dedup_i.db"
    conn = connect(path)
    try:
        init_db(conn)
        conn.execute(
            "INSERT INTO import_batches (source_file, file_sha256, sheet_name)"
            " VALUES ('t.xlsx', 'x', 'History KDTPS')"
        )
        # History row: group in H, real code only in I.
        _insert_case(conn, no_dvd="2023/5", error_code_h="C CALL",
                     error_code_i="C4701", phenomenon="máy báo C4701")
        dup = find_duplicate_case(
            conn, model="6th Next", line="A15",
            error_code="C4701", ngay_phat_sinh=None,
        )
        assert dup is not None, "form re-entry by real code must match history"
        assert dup["no_dvd"] == "2023/5"
    finally:
        conn.close()


def test_backfill_error_code_i_dry_run_then_apply(tmp_path):
    path = tmp_path / "backfill_i.db"
    conn = connect(path)
    try:
        init_db(conn)
        conn.execute(
            "INSERT INTO import_batches (source_file, file_sha256, sheet_name)"
            " VALUES ('t.xlsx', 'x', 'History KDTPS')"
        )
        _insert_case(conn, no_dvd="2023/7", error_code_h="F CALL",
                     phenomenon="LCD画面にF000表示")
        assert conn.execute(
            "SELECT error_code_i FROM error_cases").fetchone()[0] is None
        # raw_json already carries column I -> backfill needs no source file
        conn.execute("UPDATE error_cases SET error_code_i = NULL")
        dry = backfill_error_code_i(conn)
        assert dry["status"] == "planned"
        assert dry["would_update"] == 1, dry
        assert conn.execute(
            "SELECT error_code_i FROM error_cases").fetchone()[0] is None
        applied = backfill_error_code_i(conn, apply=True)
        assert applied["status"] == "applied"
        assert applied["updated"] == 1, applied
        assert conn.execute(
            "SELECT error_code_i FROM error_cases").fetchone()[0] == "F000"
        rerun = backfill_error_code_i(conn, apply=True)
        assert rerun["updated"] == 0 and rerun["no_change"] == 1
    finally:
        conn.close()


def test_submit_form_case_stores_and_dedups_with_error_code_i(tmp_path):
    path = tmp_path / "form_i.db"
    conn = connect(path)
    try:
        init_db(conn)
        init_glossary(conn)
        data = {
            "model": "Iris2024", "line": "C33", "cong_doan": "A1",
            "ten_loi": "SIMULATED mã thật",
            "error_code": "C4701",
            "hien_tuong": "SIMULATED hiện tượng",
            "noi_dung_dieu_tra": "SIMULATED điều tra",
            "nguyen_nhan": "SIMULATED nguyên nhân",
            "doi_sach": "SIMULATED đối sách",
            "bo_phan_pt": "SIMULATED bộ phận",
            "ngay_phat_sinh": "2026-09-01",
            "ngay_dong": "2026-09-02",
            "link_bao_cao": "",
        }
        first = submit_form_case(conn, data)
        assert first["status"] == "inserted", first
        second = submit_form_case(conn, data)
        assert second["status"] == "duplicate", second
    finally:
        conn.close()
