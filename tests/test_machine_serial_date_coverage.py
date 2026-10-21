# -*- coding: utf-8 -*-
"""Unit tests for machine serial and date coverage audit.

Ticket: DESKTOP-HOME-MACHINE-SERIAL-DATE-COVERAGE
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import pytest

DB_PATH = Path(r"C:\tmp\kdtps_standard\error_cases_reconciled.db")


@pytest.mark.skipif(not DB_PATH.is_file(), reason="Production DB not available at C:\\tmp")
def test_error_cases_schema_columns():
    con = sqlite3.connect(f"file:{DB_PATH.resolve().as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cols = [r["name"] for r in con.execute("PRAGMA table_info(error_cases)").fetchall()]
    con.close()

    # machine_type, no_dvd, occurred_at exist in schema
    assert "machine_type" in cols
    assert "no_dvd" in cols
    assert "occurred_at" in cols

    # serial is NOT a column in schema
    assert "serial" not in cols
    assert "serial_no" not in cols


@pytest.mark.skipif(not DB_PATH.is_file(), reason="Production DB not available at C:\\tmp")
def test_error_cases_total_and_coverage():
    con = sqlite3.connect(f"file:{DB_PATH.resolve().as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    total = con.execute("SELECT COUNT(*) FROM error_cases").fetchone()[0]
    assert total == 30075

    # Coverage checks
    has_dvd = con.execute("SELECT COUNT(*) FROM error_cases WHERE no_dvd IS NOT NULL AND TRIM(no_dvd) != ''").fetchone()[0]
    assert has_dvd == 30075

    has_date = con.execute("SELECT COUNT(*) FROM error_cases WHERE occurred_at IS NOT NULL AND TRIM(occurred_at) != ''").fetchone()[0]
    assert has_date == 28976

    has_machine = con.execute("SELECT COUNT(*) FROM error_cases WHERE machine_type IS NOT NULL AND TRIM(machine_type) != ''").fetchone()[0]
    assert has_machine == 27829
    con.close()


@pytest.mark.skipif(not DB_PATH.is_file(), reason="Production DB not available at C:\\tmp")
def test_iris_and_6thnext_serial_coverage():
    con = sqlite3.connect(f"file:{DB_PATH.resolve().as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    # Iris exact
    iris_rows = con.execute("SELECT raw_json FROM error_cases WHERE TRIM(machine_type) = 'Iris'").fetchall()
    assert len(iris_rows) == 28
    for r in iris_rows:
        rj = json.loads(r["raw_json"] or "{}")
        assert "G" in rj and rj["G"]

    # 6thNext exact
    next_rows = con.execute("SELECT raw_json FROM error_cases WHERE TRIM(machine_type) = '6thNext'").fetchall()
    assert len(next_rows) == 193
    for r in next_rows:
        rj = json.loads(r["raw_json"] or "{}")
        assert "G" in rj and rj["G"]

    con.close()
