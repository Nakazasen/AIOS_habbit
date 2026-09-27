"""F4 tests: error-code glossary (Bang ma loi / UWCA / SCT).

Runs against the real source files (read-only) in the local data dir.
Covers >= 5 sample codes from recon 2026-09-27 plus the standing rule
"vất lại file cũ thì bỏ qua" (re-import of an unchanged file is skipped).
"""
import os
import sqlite3
from pathlib import Path

import pytest

from aios_habit.error_cases.glossary import (
    import_glossary,
    init_glossary,
    lookup,
    norm_code,
)

DATA = (
    Path(os.environ.get("AIOS_DATA_DIR", "/home/hatch/workspace/aios_data"))
    / "dieu_tra_loi"
    / "Điều chỉnh"
)
CCALL_FILE = DATA / "Bang ma loi" / "02XC_自己診断表示一覧表-Iris2020 VN.xls"
UWCA_FILE = DATA / "UWCAシステムエラー(FXXX)概要.xls"
SCT_FILE = DATA / "SCT自動調整エラーコード一覧_140221.xls"
JAM_FILE = DATA / "Bang ma loi" / "02XC_機能定義書_JAM一覧 (1).xls"

ALL_SOURCES = [
    (CCALL_FILE, "C_CALL"),
    (UWCA_FILE, "F_SYSTEM"),
    (SCT_FILE, "SCT_ADJ"),
    (JAM_FILE, "JAM"),
]


@pytest.fixture(scope="module")
def conn():
    for path, _ in ALL_SOURCES:
        assert path.exists(), f"source file missing: {path}"
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_glossary(c)
    results = {}
    for path, family in ALL_SOURCES:
        results[family] = import_glossary(c, path, family)
    yield c, results
    c.close()


def test_all_families_imported(conn):
    c, results = conn
    for family, r in results.items():
        assert r["status"] == "imported", family
        assert r["inserted"] > 0, family
    counts = {
        row["code_family"]: row["n"]
        for row in c.execute(
            "SELECT code_family, COUNT(*) n FROM error_glossary GROUP BY 1"
        )
    }
    assert counts["C_CALL"] >= 200
    assert counts["F_SYSTEM"] >= 100
    assert counts["JAM"] >= 3000
    assert counts["SCT_ADJ"] >= 35


def test_ccall_c0030(conn):
    c, _ = conn
    e = lookup(c, "C_CALL", "C0030")
    assert e is not None
    assert "FAX" in e["name_vi"]
    assert "FAX基板" in e["name_ja"]
    assert e["rank"] == "A"


def test_ccall_c0120(conn):
    c, _ = conn
    e = lookup(c, "C_CALL", "C0120")
    assert e is not None and e["name_vi"]


def test_fsystem_f000(conn):
    c, _ = conn
    e = lookup(c, "F_SYSTEM", "F000")
    assert e is not None
    assert "Panel" in (e["name_en"] or "")


def test_fsystem_wildcard_f10x(conn):
    c, _ = conn
    e = lookup(c, "F_SYSTEM", "F10X")
    assert e is not None
    assert "OS" in (e["name_ja"] or "")


def test_jam_6000(conn):
    c, _ = conn
    e = lookup(c, "JAM", "6000")
    assert e is not None and e["name_ja"]


def test_jam_0000(conn):
    c, _ = conn
    e = lookup(c, "JAM", "0000")
    assert e is not None
    assert "初期JAM" in (e["name_ja"] or "")


def test_sct_01(conn):
    c, _ = conn
    e = lookup(c, "SCT_ADJ", "01", "ADJ_ERR_SRCH_ORGERR1")
    assert e is not None
    assert e["name_vi"]


def test_sct_duplicate_03_kept(conn):
    c, _ = conn
    rows = c.execute(
        "SELECT code_sub FROM error_glossary "
        "WHERE code_family='SCT_ADJ' AND code='03'"
    ).fetchall()
    assert len(rows) == 2  # upstream duplicate, both kept


def test_fullwidth_normalization():
    assert norm_code("Ｃ００３０") == "C0030"
    assert norm_code("f10x") == "F10X"


def test_reimport_same_file_skipped(conn):
    """'Vất lại file cũ thì bỏ qua': unchanged file -> skipped, 0 writes."""
    c, _ = conn
    before = c.execute("SELECT COUNT(*) n FROM error_glossary").fetchone()["n"]
    for path, family in ALL_SOURCES:
        r = import_glossary(c, path, family)
        assert r["status"] == "skipped", family
        assert r["inserted"] == 0 and r["updated"] == 0
    after = c.execute("SELECT COUNT(*) n FROM error_glossary").fetchone()["n"]
    assert before == after
