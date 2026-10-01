"""Contract tests cho ve J1-CSV: nhap ca tep CSV, chon bieu do, cau hinh mail.

Du lieu mo phong deu trich tu log JIG that
(``IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv`` — 2ND-1035), gan mac SIMULATED_*,
khong bia. Test tu bo qua neu may khong co du lieu that.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aios_habit.production_prediction.alert_config_chat import (
    AlertConfig,
    parse_config_command,
    render_text_dashboard,
)
from aios_habit.production_prediction.chart_selection import (
    LOAI_BIEU_DO,
    chon_va_ve_bieu_do,
    goi_y_loai_bieu_do,
)
from aios_habit.production_prediction.jig_chat_wire import (
    bieu_do_tu_dong_cho_canh_bao,
    decide_jig_action,
    load_alert_config,
    save_alert_config,
)
from aios_habit.production_prediction.jig_csv_import import (
    nhap_tep_csv_log,
    thong_diep_nhap_tep,
)
from aios_habit.production_prediction.log_archive import doc_kho

DU_LIEU_THAT = Path(
    "/home/hatch/workspace/aios_data/lsu/Iris LSU/thu nghiem 6pcs do thong so va log"
    "/2ND-1035/IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv"
)
co_du_lieu_that = pytest.mark.skipif(
    not DU_LIEU_THAT.is_file(), reason="Thieu du lieu log JIG that tren may nay"
)


def _tep_simulated_iris(tmp_path: Path, so_dong: int = 3) -> Path:
    """Cat lat tep that thanh tep SIMULATED_* (tieu de + N dong)."""
    dong = DU_LIEU_THAT.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    tep = tmp_path / "SIMULATED_iris_2nd1035.csv"
    tep.write_text("\n".join(dong[: 1 + so_dong]) + "\n", encoding="utf-8")
    return tep


def _hang_ve() -> list:
    return [
        {
            "jig_id": "2ND-1035",
            "metric_name": "BOW_VALUE",
            "value": 10.0 + (i % 5) * 0.01,
            "unit": "um",
            "unit_serial": "U1",
            "event_time": "2026-08-%02d" % (i % 28 + 1),
        }
        for i in range(30)
    ]


@co_du_lieu_that
def test_nhap_tep_iris_rong_tu_du_lieu_that(tmp_path):
    tep = _tep_simulated_iris(tmp_path)
    kho = tmp_path / "kho"
    bang = tmp_path / "bang.json"
    ket_qua = nhap_tep_csv_log(tep, kho=kho, bang_nhap_tep=bang)
    assert not ket_qua.bo_qua_vi_trung
    assert ket_qua.dinh_dang == "iris_rong"
    assert ket_qua.da_ghi > 0
    cac_dong = doc_kho(kho)
    assert len(cac_dong) == ket_qua.da_ghi
    assert {d.nguon for d in cac_dong} == {"tep"}
    assert bang.is_file()


@co_du_lieu_that
def test_nhap_lai_tep_cu_thi_bo_qua(tmp_path):
    """Bat buoc moi ve code: vat lai tep cu thi bo qua tu cua."""
    tep = _tep_simulated_iris(tmp_path)
    kho = tmp_path / "kho"
    bang = tmp_path / "bang.json"
    lan1 = nhap_tep_csv_log(tep, kho=kho, bang_nhap_tep=bang)
    truoc = len(doc_kho(kho))
    lan2 = nhap_tep_csv_log(tep, kho=kho, bang_nhap_tep=bang)
    assert lan1.da_ghi > 0
    assert lan2.bo_qua_vi_trung
    assert lan2.da_ghi == 0
    assert len(doc_kho(kho)) == truoc
    assert "bỏ qua" in thong_diep_nhap_tep(lan2)


@co_du_lieu_that
def test_tep_thay_doi_thi_nhap_lai(tmp_path):
    tep = _tep_simulated_iris(tmp_path, so_dong=3)
    kho = tmp_path / "kho"
    bang = tmp_path / "bang.json"
    lan1 = nhap_tep_csv_log(tep, kho=kho, bang_nhap_tep=bang)
    dong_that = DU_LIEU_THAT.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    with open(tep, "a", encoding="utf-8") as f:
        f.write(dong_that[4] + "\n")
    lan2 = nhap_tep_csv_log(tep, kho=kho, bang_nhap_tep=bang)
    assert not lan2.bo_qua_vi_trung
    assert lan2.da_ghi > lan1.da_ghi


def test_nhap_tep_loi_tieng_viet(tmp_path):
    kho = tmp_path / "kho"
    bang = tmp_path / "bang.json"
    with pytest.raises(ValueError, match="Không tìm thấy tệp"):
        nhap_tep_csv_log(tmp_path / "khong_co.csv", kho=kho, bang_nhap_tep=bang)
    tep_txt = tmp_path / "ghi_chu.txt"
    tep_txt.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match="không phải CSV"):
        nhap_tep_csv_log(tep_txt, kho=kho, bang_nhap_tep=bang)
    tep_la = tmp_path / "la.csv"
    tep_la.write_text("xin chào\nkhông phải log\n", encoding="utf-8")
    with pytest.raises(ValueError, match="không chứa dòng log JIG"):
        nhap_tep_csv_log(tep_la, kho=kho, bang_nhap_tep=bang)


@co_du_lieu_that
def test_nhap_dong_le_tu_ban_ghi_that(tmp_path):
    """Dong le 7 cot duoc dung tu ban ghi that (khong bia du lieu)."""
    from aios_habit.production_prediction.iris_log_adapter import parse_dong_log_iris

    dong = DU_LIEU_THAT.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    ket_qua = parse_dong_log_iris("\n".join(dong[:3]))
    ban_ghi = ket_qua.ban_ghi_hop_le()[:5]
    assert ban_ghi
    tep = tmp_path / "SIMULATED_dong_le.csv"
    tep.write_text(
        "\n".join(
            ",".join(
                [
                    b.event_time.isoformat() if b.event_time else "",
                    b.unit_serial,
                    b.jig_id or "2ND-1035",
                    b.metric_name,
                    str(b.value),
                    b.unit or "",
                    b.target_label or "OK",
                ]
            )
            for b in ban_ghi
        )
        + "\n",
        encoding="utf-8",
    )
    kho = tmp_path / "kho"
    ket_qua_nhap = nhap_tep_csv_log(tep, kho=kho, bang_nhap_tep=tmp_path / "bang.json")
    assert ket_qua_nhap.dinh_dang == "dong_le"
    assert ket_qua_nhap.da_ghi == len(ban_ghi)
    assert {d.nguon for d in doc_kho(kho)} == {"tep"}


def test_chon_bieu_do_ve_ngay_ca_ba_loai():
    from PIL import Image
    import io as _io

    for ma_loai in LOAI_BIEU_DO:
        anh, meta = chon_va_ve_bieu_do(ma_loai, "2ND-1035", "BOW_VALUE", _hang_ve())
        assert len(anh) > 1000
        hinh = Image.open(_io.BytesIO(anh))
        hinh.verify()
        assert meta["loai_bieu_do"] == ma_loai
        assert meta["ma_jig"] == "2ND-1035"
        assert meta["ten_anh"] == "bieu_do_" + ma_loai + ".png"


def test_chon_bieu_do_sai_thi_bao_loai_hop_le():
    with pytest.raises(ValueError, match="Xu hướng theo thời gian"):
        chon_va_ve_bieu_do("sai", "2ND-1035", "BOW_VALUE", _hang_ve())


def test_goi_y_loai_bieu_do_tu_cau_tieng_viet():
    assert goi_y_loai_bieu_do("chọn biểu đồ phân bố") == "phan_bo"
    assert goi_y_loai_bieu_do("vẽ biểu đồ so sánh theo màu") == "so_sanh_mau"
    assert goi_y_loai_bieu_do("chọn biểu đồ xu hướng") == "xu_huong"
    assert goi_y_loai_bieu_do("xin chào") is None


def test_cau_hinh_bieu_do_gui_mail():
    cau_hinh = AlertConfig()
    assert cau_hinh.bieu_do_dinh_kem == ["xu_huong"]
    cap_nhat, loi_nhan = parse_config_command("chọn biểu đồ gửi mail phân bố", cau_hinh)
    assert cap_nhat.bieu_do_dinh_kem == ["xu_huong", "phan_bo"]
    assert "Phân bố" in loi_nhan
    # Cau hinh khac (them email) khong duoc reset bieu do da chon.
    cap_nhat2, _ = parse_config_command("thêm email a@b.com", cap_nhat)
    assert cap_nhat2.bieu_do_dinh_kem == ["xu_huong", "phan_bo"]
    bo, loi_bo = parse_config_command("bỏ biểu đồ gửi mail xu hướng", cap_nhat2)
    assert bo.bieu_do_dinh_kem == ["phan_bo"]
    assert "Đã bỏ" in loi_bo
    khong_ro, loi_khong_ro = parse_config_command("chọn biểu đồ gửi mail", cau_hinh)
    assert khong_ro.bieu_do_dinh_kem == ["xu_huong"]
    assert "Xu hướng theo thời gian" in loi_khong_ro
    bang = render_text_dashboard(cap_nhat2)
    assert "Biểu đồ đính kèm mail" in bang
    assert "Phân bố giá trị" in bang


def test_luu_doc_cau_hinh_giu_bieu_do_dinh_kem(tmp_path):
    duong = tmp_path / "cau_hinh.json"
    cau_hinh = AlertConfig(bieu_do_dinh_kem=["phan_bo", "so_sanh_mau"])
    save_alert_config(cau_hinh, duong)
    doc_lai = load_alert_config(duong)
    assert doc_lai.bieu_do_dinh_kem == ["phan_bo", "so_sanh_mau"]
    # Ma loai la trong tep cu bi loc bo, thieu khoa thi ve mac dinh.
    duong.write_text('{"bieu_do_dinh_kem": ["phan_bo", "sai"]}', encoding="utf-8")
    assert load_alert_config(duong).bieu_do_dinh_kem == ["phan_bo"]
    assert load_alert_config(tmp_path / "khong_co.json").bieu_do_dinh_kem == ["xu_huong"]


def test_bieu_do_tu_dong_theo_cau_hinh():
    cau_hinh = AlertConfig(bieu_do_dinh_kem=["phan_bo"])
    ket_qua = bieu_do_tu_dong_cho_canh_bao(cau_hinh, "2ND-1035", "BOW_VALUE", _hang_ve())
    assert len(ket_qua) == 1
    ma_loai, anh, meta = ket_qua[0]
    assert ma_loai == "phan_bo"
    assert len(anh) > 1000
    assert meta["ten_anh"] == "bieu_do_phan_bo.png"


def test_canh_bao_tu_dong_ve_bieu_do_da_cau_hinh():
    """Canh bao kich hoat -> tu dong ve dung bieu do user da setup."""
    cau_hinh = AlertConfig(bieu_do_dinh_kem=["phan_bo"])
    dong_log = "2026-10-01T10:00:00,U001,JIG-A,BOW_VALUE,99.9,um,OK"
    ket_qua = decide_jig_action(
        dong_log,
        alert_config=cau_hinh,
        history_provider=lambda jig, chi_so: [10.0] * 20,
        chart_rows_provider=lambda: [
            dict(h, jig_id="JIG-A") for h in _hang_ve()
        ],
    )
    assert ket_qua.handled
    assert "Vi phạm" in ket_qua.assistant_text
    assert ket_qua.chart_png is not None and len(ket_qua.chart_png) > 1000
    assert ket_qua.chart_meta["loai_bieu_do"] == "phan_bo"
    assert "tự động vẽ" in ket_qua.assistant_text


def test_lenh_chat_nhap_tep_csv(tmp_path):
    kho = tmp_path / "kho"
    tep = tmp_path / "SIMULATED_chat.csv"
    tep.write_text(
        "2026-10-01T10:00:00,U001,JIG-A,BOW_VALUE,10.5,um,OK\n",
        encoding="utf-8",
    )
    ket_qua = decide_jig_action(
        'nhập tệp log "%s"' % tep, kho_log_path=kho
    )
    assert ket_qua.handled
    assert "Đã nhập 1 giá trị đo" in ket_qua.assistant_text
    assert len(doc_kho(kho)) == 1
    # Nhap lai tep cu -> bo qua.
    ket_qua2 = decide_jig_action('nhập tệp log "%s"' % tep, kho_log_path=kho)
    assert "bỏ qua" in ket_qua2.assistant_text
    assert len(doc_kho(kho)) == 1


def test_lenh_chat_chon_bieu_do_ve_ngay():
    ket_qua = decide_jig_action(
        "chọn biểu đồ phân bố",
        alert_config=AlertConfig(),
        chart_rows_provider=lambda: _hang_ve(),
    )
    assert ket_qua.handled
    assert "áp dụng ngay" in ket_qua.assistant_text
    assert ket_qua.chart_png is not None and len(ket_qua.chart_png) > 1000
    assert ket_qua.chart_meta["loai_bieu_do"] == "phan_bo"


def test_lenh_cau_hinh_bieu_do_gui_mail_khong_bi_ve_nham():
    """Lenh cau hinh mail khong duoc roi vao nhanh ve bieu do."""
    ket_qua = decide_jig_action(
        "chọn biểu đồ gửi mail phân bố",
        alert_config=AlertConfig(),
        chart_rows_provider=lambda: _hang_ve(),
    )
    assert ket_qua.handled
    assert ket_qua.chart_png is None
    assert "đính kèm vào mail" in ket_qua.assistant_text
