"""Hợp đồng cấu hình SMTP và thẻ duyệt gửi mail cảnh báo (016 T016-10..T016-13)."""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import pytest

from aios_habit.i18n import TRANSLATIONS
from aios_habit.production_prediction.alert_config_chat import AlertConfig
from aios_habit.production_prediction.alert_mailer import (
    AlertCooldownTracker,
    AlertMailProposal,
    build_alert_email,
    can_send_with_approval,
)
from aios_habit.production_prediction.smtp_config import (
    SmtpConfig,
    co_cau_hinh,
    doc_smtp_config,
    gui_voi_cau_hinh,
    luu_smtp_config,
    thong_bao_loi_gui,
)
from aios_habit.workspace_chat_ui import build_de_xuat_mail_data, khoa_gian_cach

_LOI_THIEU = (
    "Chưa cấu hình máy chủ gửi mail nội bộ. "
    "Vui lòng bổ sung máy chủ, cổng và tài khoản gửi mail trước khi gửi cảnh báo."
)
_MAT_KHAU = "BiMat-916"
_HAM_VE_CAM = ("render_chart_png", "render_chart_svg", "render_spc_png")


class _MayChuSmtpGia:
    ban_ghi: list["_MayChuSmtpGia"] = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.da_dang_nhap = False
        self.tin_da_gui = []
        self.da_tls = False
        _MayChuSmtpGia.ban_ghi.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self, *args, **kwargs):
        self.da_tls = True

    def login(self, user, password):
        self.da_dang_nhap = True

    def send_message(self, msg, *args, **kwargs):
        self.tin_da_gui.append(msg)


def test_doc_smtp_thieu_hoac_hong_tra_mac_dinh(tmp_path):
    thieu = doc_smtp_config(tmp_path / "khong_co.json")
    assert thieu == SmtpConfig()
    assert co_cau_hinh(thieu) is False

    hong = tmp_path / "hong.json"
    hong.write_text("{khong-phai-json", encoding="utf-8")
    assert doc_smtp_config(hong) == SmtpConfig()

    thu_muc = tmp_path / "la_thu_muc"
    thu_muc.mkdir()
    assert doc_smtp_config(thu_muc) == SmtpConfig()
    assert co_cau_hinh(SmtpConfig(host="  ", port=587)) is False
    assert co_cau_hinh(SmtpConfig(host="mail.noi-bo.local", port=0)) is False
    assert co_cau_hinh(SmtpConfig(host="mail.noi-bo.local", port=587)) is True


def test_to_dict_khong_lo_mat_khau_va_vong_luu(tmp_path):
    cfg = SmtpConfig(
        host="máy-chủ.noi-bo.local",
        port=2525,
        ten_dang_nhap="gui-canh-bao",
        mat_khau=_MAT_KHAU,
        dung_tls=False,
        nguoi_gui="Cảnh báo <canhbao@congty.local>",
    )
    cong_khai = cfg.to_dict()
    dumped = json.dumps(cong_khai, ensure_ascii=False)
    assert _MAT_KHAU not in dumped
    assert "mat_khau" not in cong_khai
    assert "password" not in cong_khai
    assert SmtpConfig.from_dict(cong_khai).mat_khau == ""

    duong = tmp_path / "ngoai" / "smtp_config.json"
    luu_smtp_config(cfg, duong)
    raw = duong.read_text(encoding="utf-8")
    assert _MAT_KHAU in raw
    assert "máy-chủ.noi-bo.local" in raw
    tai = doc_smtp_config(duong)
    assert tai.host == cfg.host
    assert tai.port == 2525
    assert tai.ten_dang_nhap == cfg.ten_dang_nhap
    assert tai.mat_khau == _MAT_KHAU
    assert tai.dung_tls is False
    assert tai.nguoi_gui == cfg.nguoi_gui


def test_doc_chap_nhan_khoa_mat_khau_hoac_password(tmp_path):
    theo_password = tmp_path / "password.json"
    theo_password.write_text(
        json.dumps({"host": "mail.noi-bo.local", "port": "25", "password": "tu-password"}),
        encoding="utf-8",
    )
    tai_password = doc_smtp_config(theo_password)
    assert tai_password.mat_khau == "tu-password"
    assert tai_password.port == 25
    assert co_cau_hinh(tai_password) is True

    theo_mat_khau = tmp_path / "mat_khau.json"
    theo_mat_khau.write_text(
        json.dumps({"host": "mail.noi-bo.local", "port": 587, "mat_khau": "tu-mat-khau", "password": "khac"}),
        encoding="utf-8",
    )
    assert doc_smtp_config(theo_mat_khau).mat_khau == "tu-mat-khau"


def test_gui_khi_chua_cau_hinh_thi_dung(monkeypatch):
    da_mo = []

    class _CamMo:
        def __init__(self, *args, **kwargs):
            da_mo.append(args)

    monkeypatch.setattr("aios_habit.production_prediction.alert_mailer.smtplib.SMTP", _CamMo)
    cfg = SmtpConfig(mat_khau=_MAT_KHAU)
    with pytest.raises(ValueError) as exc:
        gui_voi_cau_hinh(MIMEMultipart(), cfg)
    assert str(exc.value) == _LOI_THIEU
    assert _MAT_KHAU not in str(exc.value)
    assert da_mo == []


def test_gui_voi_cau_hinh_uy_quyen_smtp_khong_dang_nhap_khi_trong(monkeypatch):
    _MayChuSmtpGia.ban_ghi.clear()
    monkeypatch.setattr("aios_habit.production_prediction.alert_mailer.smtplib.SMTP", _MayChuSmtpGia)
    proposal = AlertMailProposal(
        tieu_de="Cảnh báo xu hướng JIG JIG-09",
        tom_tat="JIG JIG-09 — chỉ số BOWSKEW vừa kích hoạt kết luận Nguy cơ.",
        nguoi_nhan=["to.truong@congty.local", "qc@congty.local"],
        ma_duyet="DUYET-TEST01",
    )
    msg = build_alert_email(proposal, anh_png_bytes=b"\x89PNG\r\n\x1a\nanh-gia")
    cfg = SmtpConfig(host="smtp.noi-bo.local", port=2525, ten_dang_nhap="", mat_khau=_MAT_KHAU, dung_tls=True)
    ket_qua = gui_voi_cau_hinh(msg, cfg)
    assert ket_qua["trang_thai"] == "Đã gửi"
    assert len(_MayChuSmtpGia.ban_ghi) == 1
    server = _MayChuSmtpGia.ban_ghi[0]
    assert server.host == "smtp.noi-bo.local"
    assert server.port == 2525
    assert server.da_dang_nhap is False
    assert len(server.tin_da_gui) == 1
    raw = server.tin_da_gui[0].as_string()
    assert "to.truong@congty.local" in raw
    assert "qc@congty.local" in raw
    assert "Content-ID: <bieudoxu_huong>" in raw
    assert _MAT_KHAU not in raw


def test_thong_bao_loi_gui_khong_lo_loi_tho():
    cau = thong_bao_loi_gui(RuntimeError("boom"))
    assert "boom" not in cau
    assert "Hãy kiểm tra mạng nội bộ" in cau
    assert "thử gửi lại" in cau
    lo_mk = thong_bao_loi_gui(RuntimeError(f"password={_MAT_KHAU} boom"))
    assert "boom" not in lo_mk
    assert _MAT_KHAU not in lo_mk


def test_can_send_with_approval_van_chan():
    proposal = AlertMailProposal(
        tieu_de="Cảnh báo",
        tom_tat="Tóm tắt đủ để gửi.",
        nguoi_nhan=["a@congty.local"],
        ma_duyet="DUYET-ABC",
    )
    assert can_send_with_approval(proposal, False) is False
    assert can_send_with_approval(replace(proposal, ma_duyet=""), True) is False


def test_gian_cach_chan_gui_lien_tiep_roi_mo_lai():
    tracker = AlertCooldownTracker(cooldown_seconds=60)
    assert tracker.duoc_phep_gui("J1|BOWSKEW", now_ts=1000.0) is True
    tracker.danh_dau_da_gui("J1|BOWSKEW", now_ts=1000.0)
    assert tracker.duoc_phep_gui("J1|BOWSKEW", now_ts=1000.0) is False
    assert tracker.duoc_phep_gui("J1|BOWSKEW", now_ts=1060.0) is True
    assert khoa_gian_cach({"ma_jig": "J1", "ten_chi_so": "BOWSKEW"}) == "J1|BOWSKEW"


def test_the_de_xuat_neu_jig_chi_so_va_co_anh():
    config = AlertConfig(nguoi_nhan=["to.truong@congty.local"], gian_cach_phut=15)
    meta = {"ma_jig": "JIG-09", "ten_chi_so": "BOWSKEW", "ket_luan": "Nguy cơ"}
    trong = build_de_xuat_mail_data(config, meta, anh_xem_truoc=b"")
    assert trong["co_anh"] is False
    assert "JIG-09" in trong["tom_tat"]
    assert "BOWSKEW" in trong["tom_tat"]
    assert "Nguy cơ" in trong["tom_tat"]
    assert "JIG-09" in trong["tieu_de"]
    co_anh = build_de_xuat_mail_data(config, meta, anh_xem_truoc=b"\x89PNG")
    assert co_anh["co_anh"] is True
    assert co_anh["loai_the"] == "de_xuat_email"
    assert co_anh["nguoi_nhan"] == ["to.truong@congty.local"]
    assert co_anh["ten_anh"] == "bieu_do_xu_huong.png"
    assert co_anh["ma_duyet"].startswith("DUYET-")
    assert len(co_anh["ma_duyet"]) == 14


def test_chuoi_mail_co_o_ca_ba_ngon_ngu():
    khoa = (
        "mail_alert_send",
        "mail_alert_cancel",
        "mail_alert_code",
        "mail_alert_hint",
        "mail_alert_no_image",
        "mail_alert_preview_caption",
        "mail_alert_no_recipients",
        "mail_alert_sent",
        "mail_alert_cancelled",
        "mail_alert_need_approval",
        "mail_alert_cooldown",
    )
    for locale in ("vi", "ja", "zh-CN"):
        for key in khoa:
            assert TRANSLATIONS[locale][key].strip()
    assert TRANSLATIONS["vi"]["mail_alert_send"] == "Gửi cảnh báo"
    assert TRANSLATIONS["vi"]["mail_alert_cancel"] == "Hủy đề xuất"


def test_xem_truoc_dung_lai_anh_khong_ve_lai():
    source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    ham = next(
        nut
        for nut in ast.parse(source).body
        if isinstance(nut, ast.FunctionDef) and nut.name == "render_de_xuat_gui_mail_canh_bao"
    )
    doan = ast.get_source_segment(source, ham) or ""
    assert "wsc_last_chart_png" in doan
    assert "st.image" in doan
    assert "can_send_with_approval" in doan
    assert "gui_voi_cau_hinh" in doan
    assert "thong_bao_loi_gui" in doan
    assert "AlertCooldownTracker" in doan
    assert "gian_cach_phut * 60" in doan
    assert "khoa_gian_cach" in doan
    for ten in _HAM_VE_CAM:
        assert ten not in doan
    for nut in ast.walk(ham):
        if not isinstance(nut, ast.Call):
            continue
        func = nut.func
        ten = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
        assert ten not in _HAM_VE_CAM
