"""Tests cho trend_response: phan dang dich chuyen, de xuat dieu tra, luu bai hoc."""

import pytest

from aios_habit.production_prediction.trend_alerts import danh_gia_xu_huong_sma
from aios_habit.production_prediction.trend_response import (
    HINH_DANG_DAO_DONG,
    HINH_DANG_DOT_NGOT,
    HINH_DANG_TROI_DAN,
    de_xuat_dieu_tra,
    lessons_file,
    luu_bai_hoc,
    phan_dang_dich_chuyen,
    xu_ly_xu_huong_xau,
)


@pytest.fixture(autouse=True)
def _isolated_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    yield tmp_path


def test_phan_dang_dot_ngot():
    values = [10.0] * 40 + [15.0] * 8
    trend = danh_gia_xu_huong_sma(values)
    assert trend["canh_bao"] is True
    dang = phan_dang_dich_chuyen(values, trend["diem_bat_thuong"])
    assert dang["hinh_dang"] == HINH_DANG_DOT_NGOT


def test_phan_dang_troi_dan():
    values = [10.0] * 40 + [10.0 + i * 1.5 for i in range(8)]
    trend = danh_gia_xu_huong_sma(values)
    dang = phan_dang_dich_chuyen(values, trend["diem_bat_thuong"])
    assert dang["hinh_dang"] == HINH_DANG_TROI_DAN


def test_phan_dang_dao_dong():
    values = [10.0] * 40 + [25.0, -5.0, 25.0, -5.0, 25.0]
    trend = danh_gia_xu_huong_sma(values)
    dang = phan_dang_dich_chuyen(values, trend["diem_bat_thuong"])
    assert dang["hinh_dang"] == HINH_DANG_DAO_DONG


def test_khong_co_xu_huong_thi_khong_phan_ung():
    trend = danh_gia_xu_huong_sma([10.0] * 60)
    assert xu_ly_xu_huong_xau("J1", "m", [10.0] * 60, trend)["co_xu_huong_xau"] is False


def test_xu_ly_day_du_khi_co_xu_huong():
    values = [10.0] * 40 + [15.0] * 8
    trend = danh_gia_xu_huong_sma(values)
    result = xu_ly_xu_huong_xau("JIG-01", "bowskew", values, trend)
    assert result["co_xu_huong_xau"] is True
    assert "giả thuyết" in result["phan_doan_nguyen_nhan"]["luu_y"].lower() or "Giả thuyết" in result["phan_doan_nguyen_nhan"]["luu_y"]
    assert len(result["de_xuat_dieu_tra"]) >= 3


def test_de_xuat_theo_hinh_dang():
    assert any("mòn" in s for s in de_xuat_dieu_tra(HINH_DANG_TROI_DAN))
    assert any("rơ" in s or "lỏng" in s for s in de_xuat_dieu_tra(HINH_DANG_DAO_DONG))


def test_luu_bai_hoc_vao_local_cases(tmp_path):
    assert luu_bai_hoc("J1", "m", HINH_DANG_DOT_NGOT, "gia thuyet", "ket luan")["ok"] is True
    path = lessons_file()
    assert path.parent == tmp_path
    assert "trend_lessons" in path.name
    assert "gia thuyet" in path.read_text(encoding="utf-8")
