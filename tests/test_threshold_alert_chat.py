"""Tests for chat-driven threshold alerts: parse, persist, SMA(20) trend gate."""

from aios_habit.threshold_alert_chat import (
    KhoQuyTacCanhBao,
    kiem_tra_quy_tac,
    la_lenh_liet_ke,
    parse_lenh_canh_bao,
    parse_lenh_xoa,
    xu_ly_cau_lenh,
)


def test_parse_canh_bao_khi_vuot():
    p = parse_lenh_canh_bao("cảnh báo khi nhiệt độ vượt 80")
    assert p == {"thong_so": "nhiệt độ", "phep_so_sanh": ">", "nguong": 80.0}


def test_parse_canh_bao_khi_duoi_va_dau():
    p = parse_lenh_canh_bao("cảnh báo khi áp suất < 5")
    assert p["phep_so_sanh"] == "<"
    assert p["nguong"] == 5.0
    p = parse_lenh_canh_bao("Cảnh báo khi độ rung lớn hơn 12,5")
    assert p["phep_so_sanh"] == ">"
    assert p["nguong"] == 12.5


def test_parse_dat_nguong():
    p = parse_lenh_canh_bao("đặt ngưỡng nhiệt độ 80")
    assert p is not None
    assert p["thong_so"] == "nhiệt độ"
    assert p["phep_so_sanh"] == ">"
    p = parse_lenh_canh_bao("thiết lập ngưỡng áp suất dưới 5")
    assert p["phep_so_sanh"] == "<"


def test_parse_khong_phai_lenh():
    assert parse_lenh_canh_bao("lỗi FXXX là gì?") is None
    assert parse_lenh_canh_bao("phân tích log jig") is None


def test_lenh_liet_ke_va_xoa():
    assert la_lenh_liet_ke("liệt kê cảnh báo") is True
    assert la_lenh_liet_ke("xin chào") is False
    assert parse_lenh_xoa("xóa cảnh báo CB-ABC123") == "CB-ABC123"
    assert parse_lenh_xoa("cảnh báo khi nhiệt độ vượt 80") is None


def test_kho_them_liet_ke_xoa(tmp_path):
    kho = KhoQuyTacCanhBao(tmp_path)
    rule = kho.them("nhiệt độ", ">", 80.0)
    assert rule.id.startswith("CB-")
    rules = kho.liet_ke()
    assert len(rules) == 1
    assert rules[0].mo_ta() == "cảnh báo khi nhiệt độ vượt 80"
    # persists across instances
    kho2 = KhoQuyTacCanhBao(tmp_path)
    assert len(kho2.liet_ke()) == 1
    assert kho2.xoa(rule.id) is True
    assert kho2.liet_ke() == []
    assert kho2.xoa("CB-KHONGCO") is False


def test_kiem_tra_kich_hoat_theo_xu_huong(tmp_path):
    kho = KhoQuyTacCanhBao(tmp_path)
    rule = kho.them("nhiệt độ", ">", 80.0)
    # stable then a sustained upward trend crossing the threshold
    chuoi = [70.0] * 25 + [82.0, 84.0, 86.0, 88.0, 90.0]
    ket_qua = kiem_tra_quy_tac(rule, chuoi)
    assert ket_qua["kich_hoat"] is True
    assert "SMA(20)" in ket_qua["ly_do"]


def test_kiem_tra_mot_diem_xau_khong_canh_bao(tmp_path):
    kho = KhoQuyTacCanhBao(tmp_path)
    rule = kho.them("nhiệt độ", ">", 80.0)
    # single spike above threshold as the LATEST point, otherwise stable
    # -> no alert (trend gate: one bad point is not a trend)
    chuoi = [70.0] * 29 + [95.0]
    ket_qua = kiem_tra_quy_tac(rule, chuoi)
    assert ket_qua["kich_hoat"] is False
    assert "chưa thành xu hướng" in ket_qua["ly_do"]


def test_kiem_tra_trong_nguong(tmp_path):
    kho = KhoQuyTacCanhBao(tmp_path)
    rule = kho.them("nhiệt độ", ">", 80.0)
    ket_qua = kiem_tra_quy_tac(rule, [70.0] * 30)
    assert ket_qua["kich_hoat"] is False
    assert "trong ngưỡng" in ket_qua["ly_do"]


def test_xu_ly_cau_lenh_tron_vong(tmp_path):
    tra_loi = xu_ly_cau_lenh(
        "cảnh báo khi nhiệt độ vượt 80",
        history_provider=lambda thong_so: [70.0] * 30,
        base_dir=tmp_path,
    )
    assert tra_loi is not None
    assert "Đã lưu quy tắc" in tra_loi
    assert "trong ngưỡng" in tra_loi

    tra_loi2 = xu_ly_cau_lenh("liệt kê cảnh báo", base_dir=tmp_path)
    assert "nhiệt độ" in tra_loi2

    tra_loi3 = xu_ly_cau_lenh("xin chào bạn", base_dir=tmp_path)
    assert tra_loi3 is None
