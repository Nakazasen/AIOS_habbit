"""Contract tests for shared chart-selection builder (015-csv-chart-selector)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aios_habit.production_prediction.chart_selection import (
    LOAI_BIEU_DO,
    dung_du_lieu_bieu_do,
    hieu_lenh_ve_bieu_do,
    la_chi_so_do_duoc,
    la_tep_depth_khong_tieu_de,
    doc_depth_khong_tieu_de,
    sap_xep_chi_so_uu_tien,
    ten_tieng_viet,
)
from aios_habit.production_prediction.spc_chart import (
    render_chart_png,
    render_chart_svg,
)

FIXTURE = Path(__file__).parent / "fixtures" / "lsu_iris" / "chart_selector" / "jig_outcomes.csv"


def _doc_fixture() -> list:
    import csv

    with open(FIXTURE, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_ba_loai_bieu_do_duoc_ho_tro():
    assert set(LOAI_BIEU_DO) == {"xu_huong", "phan_bo", "so_sanh_mau"}


def test_uu_tien_nhom_do_lech_do_nghieng():
    sap_xep = sap_xep_chi_so_uu_tien(["BEAMDIAMETER", "SKEW_VALUE", "TAKT_TIME", "BOW_VALUE"])
    assert sap_xep[0] in ("BOW_VALUE", "SKEW_VALUE")
    assert sap_xep[1] in ("BOW_VALUE", "SKEW_VALUE")


def test_cot_ky_thuat_khong_hien_lam_chi_so():
    assert not la_chi_so_do_duoc("DATE")
    assert not la_chi_so_do_duoc("TotalJudge")
    assert not la_chi_so_do_duoc("takt:BowSkewMeasureBlack[sec]")
    assert la_chi_so_do_duoc("BOW_VALUE")


def test_ten_tieng_viet_kem_ma_goc():
    assert "lệch" in ten_tieng_viet("BOW_VALUE")
    assert "nghiêng" in ten_tieng_viet("SKEW_VALUE")


def test_dung_du_lieu_dung_jig_dung_chi_so():
    du_lieu = dung_du_lieu_bieu_do("2ND-1035", "BOW_VALUE", _doc_fixture())
    assert du_lieu.jig_id == "2ND-1035"
    assert len(du_lieu.values) == 6
    assert du_lieu.cl is not None


def test_thieu_jig_bao_loi_tieng_viet():
    with pytest.raises(ValueError, match="mã JIG"):
        dung_du_lieu_bieu_do("", "BOW_VALUE", _doc_fixture())


def test_khong_tim_thay_du_lieu_bao_loi_tieng_viet():
    with pytest.raises(ValueError, match="Không tìm thấy"):
        dung_du_lieu_bieu_do("2ND-9999", "BOW_VALUE", _doc_fixture())


def test_ve_ca_ba_loai_png_300dpi(tmp_path: Path):
    from PIL import Image

    du_lieu = dung_du_lieu_bieu_do("2ND-1035", "BOW_VALUE", _doc_fixture())
    for loai in ("xu_huong", "phan_bo"):
        out = render_chart_png(du_lieu, loai, tmp_path / f"{loai}.png")
        with Image.open(out) as anh:
            dpi = anh.info.get("dpi", (0, 0))
            assert abs(dpi[0] - 300) < 0.01
    out_ss = render_chart_png([du_lieu, du_lieu], "so_sanh_mau", tmp_path / "so_sanh.png")
    assert out_ss.exists()


def test_ve_ca_ba_loai_svg_co_tem():
    du_lieu = dung_du_lieu_bieu_do("2ND-1035", "BOW_VALUE", _doc_fixture())
    for loai in ("xu_huong", "phan_bo"):
        svg = render_chart_svg(du_lieu, loai)
        assert "<svg" in svg and "2ND-1035" in svg
    svg_ss = render_chart_svg([du_lieu, du_lieu], "so_sanh_mau")
    assert "So sánh" in svg_ss


def test_tep_depth_khong_tieu_de_tu_nhan_dien():
    tep = Path(__file__).parent / "fixtures" / "lsu_iris" / "chart_selector" / "depth_no_header.csv"
    assert la_tep_depth_khong_tieu_de(tep)
    du_lieu = doc_depth_khong_tieu_de(tep)
    assert len(du_lieu) == 3
    assert du_lieu[0]["gia_tri"]


def test_tep_trong_bao_loi_tieng_viet():
    tep = Path(__file__).parent / "fixtures" / "lsu_iris" / "chart_selector" / "empty.csv"
    with pytest.raises(ValueError, match="trống"):
        doc_depth_khong_tieu_de(tep)


def test_hieu_lenh_chat_du_thong_tin():
    ket_qua = hieu_lenh_ve_bieu_do(
        "vẽ biểu đồ độ lệch cho 2ND-1035", danh_sach_jig=["2ND-1035"], danh_sach_chi_so=["BOW_VALUE"]
    )
    assert ket_qua.ma_jig == "2ND-1035"
    assert ket_qua.ten_chi_so == "BOW_VALUE"
    assert not ket_qua.con_thieu


def test_hieu_lenh_chat_thieu_thi_hoi_lai():
    ket_qua = hieu_lenh_ve_bieu_do("vẽ biểu đồ giúp tôi")
    assert "mã JIG" in ket_qua.con_thieu
    assert "tên chỉ số" in ket_qua.con_thieu


def test_hieu_lenh_chat_phan_biet_loai():
    ket_qua = hieu_lenh_ve_bieu_do("xem phân bố độ nghiêng 2ND-1035")
    assert ket_qua.loai_bieu_do == "phan_bo"
    ket_qua2 = hieu_lenh_ve_bieu_do("so sánh 4 màu độ lệch 2ND-1035")
    assert ket_qua2.loai_bieu_do == "so_sanh_mau"


def test_anh_xem_truoc_dung_chung_cho_email(tmp_path: Path):
    from aios_habit.production_prediction.alert_mailer import (
        AlertMailProposal,
        build_alert_email,
    )

    du_lieu = dung_du_lieu_bieu_do("2ND-1035", "BOW_VALUE", _doc_fixture())
    duong_anh = tmp_path / "xem_truoc.png"
    render_chart_png(du_lieu, "xu_huong", duong_anh)
    anh_bytes = duong_anh.read_bytes()
    assert len(anh_bytes) > 1000
    thu = build_alert_email(
        AlertMailProposal(
            tieu_de="Cảnh báo xu hướng JIG 2ND-1035",
            tom_tat="Độ lệch chùm tia vượt ngưỡng cần kiểm tra.",
            nguoi_nhan=["to.truong@example.com"],
        ),
        anh_png_bytes=anh_bytes,
    )
    raw = thu.as_string()
    assert "bieudoxu_huong" in raw


def test_lenh_chat_ve_bieu_do_tra_anh_va_luu_phien():
    from aios_habit.production_prediction.jig_chat_wire import decide_jig_action

    cac_hang = [
        {"jig_id": "2ND-1035", "metric_name": "BOW_VALUE", "value": 0.10 + i * 0.01,
         "unit": "um", "event_time": f"2026-08-01T13:{i:02d}:00+07:00"}
        for i in range(6)
    ]
    ket_qua = decide_jig_action(
        "vẽ biểu đồ độ lệch cho 2ND-1035", chart_rows_provider=lambda: cac_hang
    )
    assert ket_qua.handled is True
    assert ket_qua.chart_png and len(ket_qua.chart_png) > 1000
    assert ket_qua.chart_meta and ket_qua.chart_meta["ma_jig"] == "2ND-1035"


def test_lenh_chat_ve_bieu_do_thieu_du_lieu_hoi_lai():
    from aios_habit.production_prediction.jig_chat_wire import decide_jig_action

    ket_qua = decide_jig_action("vẽ biểu đồ giúp tôi", chart_rows_provider=lambda: [])
    assert ket_qua.handled is True
    assert "tải tệp" in ket_qua.assistant_text
