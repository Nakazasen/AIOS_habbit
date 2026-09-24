"""Kiểm thử nhận diện mọi loại log Iris và kho log lưu để phân tích lại (016).

Yêu cầu người dùng: "dù log nào đưa vào cũng vẽ được biểu đồ, có cảnh báo theo
ngưỡng" và "có cơ chế cho từng dòng log vào trong file mà AI phân tích".

Fixture dùng ở đây là dữ liệu tổng hợp ``SYN_``; các bài kiểm tra trên log thật
của nhà máy nằm ngoài repo và chỉ chạy khi có biến môi trường trỏ tới.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import pytest

from aios_habit.production_prediction.iris_log_adapter import (
    chuyen_ban_ghi_iris_sang_snapshot,
    doc_log_iris_tu_dong,
    doc_tep_depth,
    nhan_dien_khoi_log_dan,
    nhan_dien_loai_tep_log,
    parse_khoi_depth_dan,
    thong_diep_khoi_depth,
)
from aios_habit.production_prediction.jig_chat_wire import decide_jig_action
from aios_habit.production_prediction.log_archive import (
    bang_tom_tat_kho_van_ban,
    doc_kho,
    ghi_ban_ghi,
    ghi_dong_log_jig,
    la_lenh_kho_log,
    lich_su_theo_jig,
    tom_tat_kho,
)

GOI = Path("tests/fixtures/lsu_iris/iris_log")
LOG_RONG = GOI / "unit_test" / "2ND-0000-1_2026_07_UnitTest.csv"
TEP_SPEC = GOI / "spec" / "2026_08_Spec.csv"
TEP_DEPTH = GOI / "depth" / "2026_07_Black_depth.csv"


def _khoi_depth_dan() -> str:
    return TEP_DEPTH.read_text(encoding="utf-8-sig")


# --------------------------------------------------------------------------
# Tự nhận diện mọi loại log: "log nào đưa vào cũng phân tích được"
# --------------------------------------------------------------------------


def test_nhan_dien_dung_loai_cho_tung_nhom_tep():
    assert nhan_dien_loai_tep_log(LOG_RONG) == "unit_test"
    assert nhan_dien_loai_tep_log(TEP_DEPTH) == "depth"
    assert nhan_dien_loai_tep_log(TEP_SPEC) == "spec"


def test_doc_tu_dong_doc_duoc_ca_log_rong_lan_log_depth():
    rong = doc_log_iris_tu_dong(LOG_RONG)
    assert rong.loai == "unit_test"
    assert rong.ban_ghi_hop_le()

    sau = doc_log_iris_tu_dong(TEP_DEPTH)
    assert sau.loai == "depth"
    assert sau.ban_ghi_hop_le()


def test_doc_tu_dong_tu_choi_tep_gioi_han_bang_cau_tieng_viet():
    """Tệp Spec/CamPos không phải log đo: phải hướng dẫn đưa vào ô tệp giới hạn."""
    with pytest.raises(ValueError) as loi:
        doc_log_iris_tu_dong(TEP_SPEC)
    thong_diep = str(loi.value)
    assert "tệp giới hạn" in thong_diep
    assert "Tệp giới hạn kèm theo" in thong_diep


def test_doc_tu_dong_tu_choi_tep_la_bang_cau_tieng_viet(tmp_path):
    tep = tmp_path / "la.csv"
    tep.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(ValueError) as loi:
        doc_log_iris_tu_dong(tep)
    assert "Chưa nhận diện được định dạng" in str(loi.value)


def test_doc_tep_depth_khong_co_gia_tri_thi_bao_loi(tmp_path):
    tep = tmp_path / "rong.csv"
    tep.write_text(",,,,Beam:H:LD1\n", encoding="utf-8")
    with pytest.raises(ValueError) as loi:
        doc_tep_depth(tep)
    assert "không có giá trị đo nào" in str(loi.value)


# --------------------------------------------------------------------------
# Nhóm C: tên chỉ số phải giữ trục CamPos
# --------------------------------------------------------------------------


def test_ten_chi_so_depth_giu_ca_vi_tri_dong_lan_vi_tri_truc():
    """Lỗi thật: chỉ giữ vị trí dòng nên 17 cột cùng dòng bị gộp làm một.

    Fixture chỉ có giá trị tại hai vị trí trục (−2 và 0), nên bất biến đúng là:
    mỗi (nhánh chùm tia, dòng, vị trí trục) có giá trị phải thành một chỉ số
    riêng — không được gộp hai vị trí trục thành một tên.
    """
    ket_qua = doc_tep_depth(TEP_DEPTH)
    ten = {b.metric_name for b in ket_qua.ban_ghi_hop_le()}
    # Nhãn nhánh chùm tia phải được giữ, không để rỗng.
    assert all("DEPTH::" not in t for t in ten), "Mất nhãn nhánh chùm tia"
    assert any("BEAM:H:LD1" in t for t in ten)
    assert any("BEAM:V:LD1" in t for t in ten)
    # Vị trí trục phải tách riêng theo từng cột có giá trị.
    assert any(t.endswith(":CAM0") for t in ten)
    assert any(t.endswith(":CAM-2") for t in ten)
    # Mỗi nhánh × dòng × vị trí trục là một chỉ số riêng.
    assert len(ten) == 8, f"Mong 8 chỉ số (2 nhánh × số dòng × 2 trục), nhận {len(ten)}"


def test_nhan_bieu_do_khong_lap_lai_ma_chi_so():
    """Nhãn biểu đồ không được lặp mã chỉ số hai lần (``X (X)``)."""
    from aios_habit.production_prediction.chart_selection import dung_du_lieu_bieu_do

    hang = [
        {"jig_id": "J", "unit_serial": "U", "metric_name": "BOW:BLACK:0",
         "value": 10 + i, "unit": "um", "event_time": f"2026-08-0{i%9+1}"}
        for i in range(3)
    ]
    du_lieu = dung_du_lieu_bieu_do("J", "BOW:BLACK:0", hang)
    assert du_lieu.metric == "BOW:BLACK:0"
    assert "(" not in du_lieu.metric

    # Chỉ số có tên Việt thì vẫn ghép "tên (mã)".
    hang2 = [
        {"jig_id": "J", "unit_serial": "U", "metric_name": "BOW_VALUE",
         "value": 1.0 + i, "unit": "um", "event_time": f"2026-08-0{i%9+1}"}
        for i in range(3)
    ]
    du_lieu2 = dung_du_lieu_bieu_do("J", "BOW_VALUE", hang2)
    assert du_lieu2.metric == "Độ lệch chùm tia (BOW_VALUE)"


def test_khoi_depth_dan_tach_duoc_va_luu_kho(tmp_path):
    kho = tmp_path / "kho"
    ket_qua = parse_khoi_depth_dan(_khoi_depth_dan())
    assert ket_qua.ban_ghi_hop_le()
    assert ket_qua.bo_qua_canh_loi > 0
    # Mọi giá trị lưu được đều không nằm trong vùng canh lỗi.
    assert all(not (999 <= abs(b.value) < 1000 or 9999 <= abs(b.value) < 10000)
               for b in ket_qua.ban_ghi_hop_le())


def test_nhan_dien_khoi_dan_phan_biet_depth_voi_cau_thuong():
    assert nhan_dien_khoi_log_dan(_khoi_depth_dan()) == "depth"
    assert nhan_dien_khoi_log_dan("Hôm nay JIG có gì bất thường?") == "khong_ro"
    assert nhan_dien_khoi_log_dan("") == "khong_ro"


# --------------------------------------------------------------------------
# "Cho từng dòng log vào file mà AI phân tích"
# --------------------------------------------------------------------------


def test_dan_dong_log_iris_thi_duoc_ghi_vao_kho(tmp_path):
    kho = tmp_path / "kho"
    dong_tieu_de = LOG_RONG.read_text(encoding="utf-8-sig").splitlines()
    text = dong_tieu_de[0] + "\n" + dong_tieu_de[1]
    outcome = decide_jig_action(text, kho_log_path=kho)
    assert outcome.handled is True
    cac_dong = doc_kho(kho)
    assert cac_dong, "Dòng log dán vào phải được lưu thành file"
    assert all(d.nguon == "dan_tay" for d in cac_dong)
    assert all(d.value is not None for d in cac_dong)


def test_dan_khoi_depth_thi_duoc_ghi_vao_kho(tmp_path):
    kho = tmp_path / "kho"
    outcome = decide_jig_action(_khoi_depth_dan(), kho_log_path=kho)
    assert outcome.handled is True
    cac_dong = doc_kho(kho)
    assert cac_dong
    assert all(d.value is not None for d in cac_dong)


def test_dan_dong_log_7_cot_cu_cung_duoc_luu(tmp_path):
    kho = tmp_path / "kho"
    outcome = decide_jig_action(
        "2026-09-20T08:00:00,UNIT001,JIG-01,bowskew,0.12,mm,OK", kho_log_path=kho
    )
    assert outcome.handled is True
    cac_dong = doc_kho(kho)
    assert len(cac_dong) == 1
    assert cac_dong[0].unit_serial == "UNIT001"
    assert cac_dong[0].metric_name == "bowskew"


def test_ghi_ban_ghi_bo_qua_ban_ghi_khong_co_gia_tri(tmp_path):
    """Bản ghi canh lỗi (giá trị rỗng) không được ghi vào kho."""
    from aios_habit.production_prediction.iris_log_adapter import BanGhiIris

    kho = tmp_path / "kho"
    cac_ban_ghi = [
        BanGhiIris(unit_serial="U1", ngay="2026.07.01", gio="08:00:00", jig_id="J",
                   metric_name="BOW:BLACK:0", value=12.0, unit="um"),
        BanGhiIris(unit_serial="U1", ngay="2026.07.01", gio="08:00:00", jig_id="J",
                   metric_name="BOW:BLACK:-70", value=None, unit="um",
                   ly_do_bo_qua="canh lỗi 999"),
    ]
    ket_qua = ghi_ban_ghi(cac_ban_ghi, nguon="tep", tep="x.csv", kho=kho)
    assert ket_qua["da_ghi"] == 1
    assert ket_qua["bo_qua_rong"] == 1
    assert ket_qua["bi_cat"] == 0
    assert len(doc_kho(kho)) == 1


def test_ghi_ban_ghi_bao_ro_khi_cham_gioi_han(tmp_path):
    """Lỗi thật: chạm giới hạn thì phải báo, không được cắt dữ liệu âm thầm."""
    from aios_habit.production_prediction.iris_log_adapter import BanGhiIris
    from aios_habit.production_prediction.log_archive import GIOI_HAN_DONG_MOI_LAN

    kho = tmp_path / "kho"
    cac_ban_ghi = [
        BanGhiIris(unit_serial="U1", ngay="2026.07.01", gio="08:00:00", jig_id="J",
                   metric_name=f"M{i}", value=float(i), unit="um")
        for i in range(GIOI_HAN_DONG_MOI_LAN + 5)
    ]
    ket_qua = ghi_ban_ghi(cac_ban_ghi, nguon="tep", tep="big.csv", kho=kho)
    assert ket_qua["da_ghi"] == GIOI_HAN_DONG_MOI_LAN
    assert ket_qua["bi_cat"] == 5, "Phần bị cắt phải được đếm và báo lại"
    assert len(doc_kho(kho)) == GIOI_HAN_DONG_MOI_LAN


def test_kho_log_khong_ghi_duong_dan_tuyet_doi(tmp_path):
    """Kho log không được chứa đường dẫn dữ liệu nhà máy."""
    from aios_habit.production_prediction.iris_log_adapter import doc_tep_log_iris

    kho = tmp_path / "kho"
    p = Path(LOG_RONG).resolve()
    ket_qua = doc_tep_log_iris(p)
    ghi_ban_ghi(ket_qua.ban_ghi_hop_le(), nguon="tep", tep=str(p), kho=kho)
    noi_dung = list(kho.glob("*.jsonl"))[0].read_text(encoding="utf-8")
    assert "Iris LSU" not in noi_dung
    assert str(p.parent) not in noi_dung
    assert p.name in noi_dung  # chỉ giữ tên tệp


def test_kho_log_khong_ghi_duong_dan_o_o_jig(tmp_path):
    """Lỗ thật: ô JIG của dòng dán tay có thể chứa đường dẫn tuyệt đối.

    Người dùng dán dòng log mà ô JIG là đường dẫn thì kho vẫn phải chỉ lưu tên.
    """
    kho = tmp_path / "kho"
    duong_dan = r"D:\Sandbox\Iris LSU\log\secret.csv"
    decide_jig_action(
        f"2026-09-20T08:00:00,UNIT001,{duong_dan},bowskew,0.12,mm,OK",
        kho_log_path=kho,
    )
    noi_dung = list(kho.glob("*.jsonl"))[0].read_text(encoding="utf-8")
    assert "Iris LSU" not in noi_dung
    assert "Sandbox" not in noi_dung
    cac_dong = doc_kho(kho)
    assert len(cac_dong) == 1
    assert cac_dong[0].jig_id == "secret.csv"
    assert cac_dong[0].tep == "secret.csv"

    # Và cả đường ghi bản ghi Iris với jig_id là đường dẫn.
    from aios_habit.production_prediction.iris_log_adapter import BanGhiIris

    kho2 = tmp_path / "kho2"
    ghi_ban_ghi(
        [BanGhiIris(unit_serial="U1", ngay="2026.07.01", gio="08:00:00",
                    jig_id=duong_dan, metric_name="BOW:BLACK:0", value=1.0, unit="um")],
        nguon="tep", tep=duong_dan, kho=kho2,
    )
    noi_dung2 = list(kho2.glob("*.jsonl"))[0].read_text(encoding="utf-8")
    assert "Iris LSU" not in noi_dung2
    assert doc_kho(kho2)[0].jig_id == "secret.csv"


def test_dan_khoi_depth_co_the_ket_luan_theo_nguong(tmp_path):
    """Yêu cầu "log nào cũng có cảnh báo theo ngưỡng": khối depth phải ra thẻ kết luận."""
    kho = tmp_path / "kho"

    # Chưa có ngưỡng: vẫn phải có dòng kết luận, không chỉ tóm tắt số lượng.
    ket_qua = decide_jig_action(_khoi_depth_dan(), kho_log_path=kho)
    assert ket_qua.handled is True
    assert "Kết luận:" in ket_qua.assistant_text

    # Có ngưỡng thật cho **dòng** depth: mọi cột của dòng đó phải theo ngưỡng này.
    from aios_habit.production_prediction.metric_limits import KhoNguong, NguongChiSo

    kho_nguong = KhoNguong()
    kho_nguong.dat(NguongChiSo(
        jig_id="", chi_so="DEPTH:BEAM:H:LD1:IMGHEIGHT:-140",
        gioi_han_duoi=1, gioi_han_tren=2,
    ))
    ket_qua2 = decide_jig_action(
        _khoi_depth_dan(), nguong=kho_nguong, kho_log_path=tmp_path / "kho2"
    )
    assert "Kết luận:" in ket_qua2.assistant_text
    assert "Vi phạm" in ket_qua2.assistant_text
    assert "giới hạn trên" in ket_qua2.assistant_text


def test_kho_log_gom_ca_tep_lan_dan_tay_va_tra_lich_su(tmp_path):
    kho = tmp_path / "kho"
    from aios_habit.production_prediction.iris_log_adapter import doc_tep_log_iris

    ket_qua = doc_tep_log_iris(LOG_RONG)
    ghi_ban_ghi(ket_qua.ban_ghi_hop_le(), nguon="tep", tep="log.csv", kho=kho)
    # Ghi thêm một dòng dán tay cùng (JIG, chỉ số) để kiểm tra lịch sử gộp.
    from aios_habit.production_prediction.jig_log_ingest import parse_jig_log_line

    dong = parse_jig_log_line("2026-09-20T08:00:00,UNIT001,2ND-0000-1_2026_07_UnitTest,BOW:BLACK:0,99.0,um,OK")
    assert dong is not None
    ghi_dong_log_jig([dong], kho=kho)

    tom_tat = tom_tat_kho(kho)
    assert tom_tat["so_dong"] > 0
    lich_su = lich_su_theo_jig(
        kho, jig_id="2ND-0000-1_2026_07_UnitTest", metric_name="BOW:BLACK:0"
    )
    assert 99.0 in lich_su


def test_lenh_kho_log_hien_bang_va_khong_bi_hieu_la_cau_thuong(tmp_path):
    kho = tmp_path / "kho"
    assert la_lenh_kho_log("kho log có gì") is True
    assert la_lenh_kho_log("lịch sử log đã lưu") is True
    assert la_lenh_kho_log("Hôm nay JIG có gì bất thường?") is False

    trong = decide_jig_action("kho log có gì", kho_log_path=kho)
    assert trong.handled is True
    assert "trống" in trong.assistant_text

    dong_tieu_de = LOG_RONG.read_text(encoding="utf-8-sig").splitlines()
    decide_jig_action(dong_tieu_de[0] + "\n" + dong_tieu_de[1], kho_log_path=kho)
    co_du_lieu = decide_jig_action("kho log có gì", kho_log_path=kho)
    assert "Số dòng" in co_du_lieu.assistant_text


def test_kho_log_khong_lam_hong_cau_hoi_thuong(tmp_path):
    for cau in ("Tóm tắt tài liệu này", "Tạo báo cáo lỗi xưởng"):
        assert decide_jig_action(cau, kho_log_path=tmp_path / "kho").handled is False


def test_kho_log_la_jsonl_doc_lai_duoc_va_khong_phai_nhi_phan(tmp_path):
    kho = tmp_path / "kho"
    dong_tieu_de = LOG_RONG.read_text(encoding="utf-8-sig").splitlines()
    decide_jig_action(dong_tieu_de[0] + "\n" + dong_tieu_de[1], kho_log_path=kho)
    cac_tep = list(kho.glob("*.jsonl"))
    assert len(cac_tep) == 1
    dong_dau = cac_tep[0].read_text(encoding="utf-8").splitlines()[0]
    du_lieu = json.loads(dong_dau)
    # Không chứa mật khẩu/đường dẫn tuyệt đối của dữ liệu nhà máy.
    assert "Iris LSU" not in dong_dau
    assert set(du_lieu) >= {"ts", "ghi_luc", "nguon", "unit_serial", "metric_name", "value"}
