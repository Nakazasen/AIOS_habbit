"""Tests cho trend_alerts: SMA(20), diem bat thuong, chi canh bao theo xu huong."""

import pytest

from aios_habit.production_prediction.trend_alerts import (
    danh_gia_xu_huong_sma,
    detect_abnormal_sma,
    should_alert_series,
    sma,
)


def test_sma_values_and_leading_nones():
    result = sma([1.0, 2.0, 3.0, 4.0], window=3)
    assert result[0] is None and result[1] is None
    assert result[2] == pytest.approx(2.0)
    assert result[3] == pytest.approx(3.0)


def test_sma_window_must_be_positive():
    with pytest.raises(ValueError):
        sma([1.0], window=0)


def test_stable_series_has_no_abnormal_points():
    values = [10.0 + (i % 3) * 0.1 for i in range(60)]
    points = detect_abnormal_sma(values)
    assert not any(p["abnormal"] for p in points)
    assert danh_gia_xu_huong_sma(values)["canh_bao"] is False
    assert danh_gia_xu_huong_sma(values)["trang_thai"] == "Đạt"


def test_single_spike_does_not_alert():
    values = [10.0] * 40 + [50.0] + [10.0] * 5
    result = danh_gia_xu_huong_sma(values)
    assert result["canh_bao"] is False
    assert result["trang_thai"] == "Cận biên"
    assert "đơn lẻ" in result["chi_tiet"]


def test_consecutive_abnormal_points_alert():
    values = [10.0] * 40 + [50.0] * 5
    result = danh_gia_xu_huong_sma(values)
    assert result["canh_bao"] is True
    assert result["trang_thai"] == "Vi phạm"
    assert "liên tiếp" in result["chi_tiet"]


def test_several_abnormal_in_lookback_alerts():
    values = [10.0] * 40 + [50.0, 10.0, 50.0, 10.0, 50.0]
    result = danh_gia_xu_huong_sma(values, diem_lien_tiep=99)
    assert result["canh_bao"] is True


def test_sustained_shift_alerts():
    values = [10.0] * 40 + [15.0] * 10
    assert should_alert_series(values) is True


def test_not_enough_points_is_can_bien():
    result = danh_gia_xu_huong_sma([1.0, 2.0, 3.0])
    assert result["canh_bao"] is False
    assert result["trang_thai"] == "Cận biên"


def test_real_threshold_breach_counts_as_abnormal():
    class Nguong:
        gioi_han_tren = 12.0
        gioi_han_duoi = 8.0

    values = [10.0] * 40 + [13.0, 13.5, 14.0]
    result = danh_gia_xu_huong_sma(values, nguong=Nguong())
    assert result["canh_bao"] is True
    assert any(
        p["ly_do"] == "vuot_nguong_that"
        for p in detect_abnormal_sma(values, nguong=Nguong())
        if p["abnormal"]
    )


def test_single_threshold_breach_does_not_alert_alone():
    class Nguong:
        gioi_han_tren = 12.0
        gioi_han_duoi = 8.0

    values = [10.0] * 40 + [13.0] + [10.0] * 4
    result = danh_gia_xu_huong_sma(values, nguong=Nguong())
    assert result["canh_bao"] is False


def test_abnormal_point_marks_sma_and_residual():
    values = [10.0] * 40 + [50.0]
    points = detect_abnormal_sma(values)
    last = points[-1]
    assert last["abnormal"] is True
    assert last["sma"] is not None
    assert last["residual"] == pytest.approx(50.0 - last["sma"])


def test_gate_chi_tat_canh_bao_khi_khong_co_xu_huong():
    # 1 diem xau don le: giu nguyen phan loai diem (trung thuc), chi tat canh bao.
    from aios_habit.production_prediction.trend_alerts import (
        gate_canh_bao_theo_xu_huong,
    )

    ket_luan = {"trang_thai": "Vi phạm", "chi_tiet": "Diem lech.", "canh_bao": True}
    xu_huong = danh_gia_xu_huong_sma([10.0] * 40 + [50.0] + [10.0] * 5)
    gate_canh_bao_theo_xu_huong(ket_luan, xu_huong)
    assert ket_luan["canh_bao"] is False
    assert ket_luan["trang_thai"] == "Vi phạm"
    assert "SMA" in ket_luan["xu_huong_sma"]


def test_gate_nang_khi_xu_huong_bat_duoc_dich_chuyen():
    from aios_habit.production_prediction.trend_alerts import (
        gate_canh_bao_theo_xu_huong,
    )

    ket_luan = {"trang_thai": "Đạt", "chi_tiet": "Trong dai.", "canh_bao": False}
    xu_huong = danh_gia_xu_huong_sma([10.0] * 40 + [15.0] * 10)
    gate_canh_bao_theo_xu_huong(ket_luan, xu_huong)
    assert ket_luan["canh_bao"] is True
    assert ket_luan["trang_thai"] == "Vi phạm"


def test_gate_giu_nguyen_khi_dong_thuan():
    from aios_habit.production_prediction.trend_alerts import (
        gate_canh_bao_theo_xu_huong,
    )

    ket_luan = {"trang_thai": "Đạt", "chi_tiet": "On.", "canh_bao": False}
    xu_huong = danh_gia_xu_huong_sma([10.0] * 60)
    gate_canh_bao_theo_xu_huong(ket_luan, xu_huong)
    assert ket_luan["canh_bao"] is False
    assert ket_luan["trang_thai"] == "Đạt"
