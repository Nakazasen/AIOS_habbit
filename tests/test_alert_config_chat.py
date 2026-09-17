"""Contract tests for Omnibar alert config text dashboard (US12 T062)."""

from __future__ import annotations

from aios_habit.production_prediction.alert_config_chat import (
    AlertConfig,
    parse_config_command,
    render_text_dashboard,
)


def test_bang_cau_hinh_hien_trong_tin_nhan_chat():
    config = AlertConfig(nguoi_nhan=["to.truong@congty.local"], nguong_phan_tram=80, gian_cach_phut=30)
    text = render_text_dashboard(config)
    assert "Bảng cấu hình cảnh báo" in text
    assert "to.truong@congty.local" in text
    assert "80% dung sai" in text
    assert "30 phút" in text


def test_them_email_bang_cau_chat_tu_nhien():
    config = AlertConfig()
    updated, reply = parse_config_command("thêm email to.truong@congty.local", config)
    assert "to.truong@congty.local" in updated.nguoi_nhan
    assert "Đã thêm" in reply


def test_doi_nguong_va_gian_cach():
    config = AlertConfig()
    updated, _ = parse_config_command("đổi ngưỡng 90%", config)
    assert updated.nguong_phan_tram == 90
    updated2, _ = parse_config_command("đổi giãn cách 60 phút", updated)
    assert updated2.gian_cach_phut == 60


def test_tu_choi_nguong_ngoai_khoang():
    config = AlertConfig()
    updated, reply = parse_config_command("đổi ngưỡng 150%", config)
    assert updated.nguong_phan_tram == config.nguong_phan_tram
    assert "1% đến 100%" in reply


def test_khong_sinh_trang_cai_dat_rieng():
    import inspect

    import aios_habit.production_prediction.alert_config_chat as module

    source = inspect.getsource(module)
    assert "st.form" not in source
    assert "st.modal" not in source
