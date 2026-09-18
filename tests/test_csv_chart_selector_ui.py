"""UI-state tests for chart selection block (015-csv-chart-selector)."""

from __future__ import annotations

import csv
from pathlib import Path

from aios_habit.prediction_shadow_ui import (
    lay_danh_sach_chi_so_ve,
    lay_danh_sach_jig,
    trang_thai_khoi_bieu_do,
)

FIXTURE = Path(__file__).parent / "fixtures" / "lsu_iris" / "chart_selector" / "jig_outcomes.csv"


def _doc_fixture() -> list:
    with open(FIXTURE, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_chua_co_du_lieu_bao_chua_co_va_huong_dan():
    trang_thai = trang_thai_khoi_bieu_do([])
    assert trang_thai["co_du_lieu"] is False
    assert "tải tệp" in trang_thai["thong_bao"]


def test_danh_sach_jig_du_tu_du_lieu():
    assert lay_danh_sach_jig(_doc_fixture()) == ["2ND-1035"]


def test_danh_sach_chi_so_uu_tien_bow_skew():
    chi_so = lay_danh_sach_chi_so_ve(_doc_fixture())
    ten = [c["ma"] for c in chi_so]
    assert "BOW_VALUE" in ten and "SKEW_VALUE" in ten
    assert ten[0] in ("BOW_VALUE", "SKEW_VALUE")
    assert all("ten_viet" in c and c["ten_viet"] for c in chi_so)


def test_du_lieu_hop_le_san_sang_chon():
    trang_thai = trang_thai_khoi_bieu_do(_doc_fixture())
    assert trang_thai["co_du_lieu"] is True
