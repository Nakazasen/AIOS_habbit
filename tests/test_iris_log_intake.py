"""Kiểm thử bộ chuyển đổi log Iris, ngưỡng thật và lệnh ngưỡng qua chat (016).

Toàn bộ dữ liệu dùng ở đây là fixture tổng hợp ``SYN_`` trong
``tests/fixtures/lsu_iris/iris_log/``; không có dữ liệu thật của nhà máy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aios_habit.production_prediction.iris_log_adapter import (
    chuyen_ban_ghi_iris_sang_snapshot,
    la_canh_loi,
    doc_tep_log_iris,
    la_dong_log_iris,
    la_dong_tieu_de_iris,
    la_tep_log_iris,
    parse_dong_log_iris,
    tach_cot_do,
    thong_diep_thieu_cot,
)
from aios_habit.production_prediction.jig_log_ingest import (
    evaluate_single_log_ewma,
    is_jig_log_line,
    parse_jig_log_line,
)
from aios_habit.production_prediction.metric_limits import (
    CHO_XAC_NHAN,
    HIEU_LUC,
    KhoNguong,
    NguongChiSo,
    bang_nguong_van_ban,
    doc_nguong,
    la_lenh_nguong,
    luu_nguong,
    ngung_do_tu_tep_gioi_han,
    phan_loai_theo_nguong,
    xu_ly_lenh_nguong,
)

GOI = Path("tests/fixtures/lsu_iris/iris_log")
LOG_THAT = GOI / "unit_test" / "SYN_UnitTest_572cot.csv"
LOG_TIEU_DE = GOI / "unit_test" / "header_va_mot_dong.csv"
LOG_THIEU = GOI / "unit_test" / "thieu_serial.csv"
TEP_SPEC = GOI / "spec" / "SYN_Spec_gioi_han.csv"
TEP_DEPTH = GOI / "depth" / "SYN_Black_depth.csv"


def _dong_tieu_de(duong_dan: Path) -> str:
    return duong_dan.read_text(encoding="utf-8-sig").splitlines()[0]


def _dong_du_lieu(duong_dan: Path) -> str:
    return duong_dan.read_text(encoding="utf-8-sig").splitlines()[1]


# --------------------------------------------------------------------------
# T016-01 — bộ chuyển đổi tách ma trận rộng
# --------------------------------------------------------------------------


def test_tach_cot_do_doc_dung_ho_mau_vi_tri_don_vi():
    cot = tach_cot_do("BEAM_DIAMETER:H:BLACK:-140:0:LD1:[um]")
    assert cot is not None
    assert cot.ho == "BEAM_DIAMETER"
    assert cot.mau == "BLACK"
    assert cot.don_vi == "um"
    # Tên chỉ số giữ đúng thứ tự thành phần như trong tệp gốc (đã bỏ đơn vị),
    # vì tên này phải tra khớp được với tệp giới hạn của JIG.
    assert cot.ten_chuan() == "BEAM_DIAMETER:H:BLACK:-140:0:LD1"

    don = tach_cot_do("SKEW:CYAN[um]")
    assert don is not None and don.mau == "CYAN" and don.ten_chuan() == "SKEW:CYAN"

    # Cột hai thành phần (không có màu) không được sinh dấu hai chấm rỗng.
    apc = tach_cot_do("APC:CURRENT[mA]")
    assert apc is not None and apc.ten_chuan() == "APC:CURRENT"
    assert "::" not in apc.ten_chuan()

    # Cột không phải chỉ số đo phải trả None, không được đoán bừa.
    assert tach_cot_do("DATE") is None
    assert tach_cot_do("SERIAL NUMBER") is None
    assert tach_cot_do("") is None


def test_doc_log_iris_tach_moi_o_thanh_mot_gia_tri_do():
    ket_qua = doc_tep_log_iris(LOG_THAT)
    assert ket_qua.loai == "unit_test"
    assert ket_qua.so_dong == 3
    assert ket_qua.so_cot == 572
    assert not ket_qua.thieu_cot
    hop_le = ket_qua.ban_ghi_hop_le()
    assert hop_le
    # Một dòng 572 cột phải nở thành rất nhiều giá trị đo, không phải 7 cột.
    assert len(hop_le) > 100
    # Mọi bản ghi hợp lệ đều phải quy về đúng một Unit trong tệp.
    assert {b.unit_serial for b in hop_le} == {"SYN_UNIT_001", "SYN_UNIT_002", "SYN_UNIT_003"}


def test_canh_loi_999_bi_bo_va_ghi_ly_do():
    ket_qua = doc_tep_log_iris(LOG_THAT)
    assert ket_qua.bo_qua_canh_loi > 0
    assert all(not la_canh_loi(b.value) for b in ket_qua.ban_ghi)
    co_ly_do = [b for b in ket_qua.ban_ghi if b.ly_do_bo_qua and b.value is None]
    assert co_ly_do
    assert "999" in co_ly_do[0].ly_do_bo_qua
    assert co_ly_do[0].metric_name


def test_nhan_theo_mau_giu_dung_mau_cua_RESULT():
    ket_qua = doc_tep_log_iris(LOG_THAT)
    # Bộ nhãn cấp tệp lấy từ dòng đầu (SYN_UNIT_001 chấm OK mọi màu).
    assert ket_qua.nhan_theo_mau["BLACK"] == "OK"
    # Mỗi bản ghi phải mang nhãn của đúng dòng và đúng màu của nó:
    # SYN_UNIT_002 có RESULT:BLACK = NG và RESULT:CYAN = OK.
    den = [
        b for b in ket_qua.ban_ghi_hop_le()
        if b.unit_serial == "SYN_UNIT_002" and b.mau == "BLACK"
    ]
    xanh = [
        b for b in ket_qua.ban_ghi_hop_le()
        if b.unit_serial == "SYN_UNIT_002" and b.mau == "CYAN"
    ]
    assert den and xanh
    assert {b.target_label for b in den} == {"NG"}
    assert {b.target_label for b in xanh} == {"OK"}
    # Và bản ghi của Unit được chấm OK thì phải mang nhãn OK.
    ok_den = [
        b for b in ket_qua.ban_ghi_hop_le()
        if b.unit_serial == "SYN_UNIT_001" and b.mau == "BLACK"
    ]
    assert ok_den and {b.target_label for b in ok_den} == {"OK"}


def test_thoi_gian_iris_duoc_ghep_dung():
    ket_qua = doc_tep_log_iris(LOG_THAT)
    dem = ket_qua.ban_ghi_hop_le()[0].event_time
    assert dem is not None
    assert (dem.year, dem.month, dem.day, dem.hour, dem.minute) == (2026, 7, 1, 16, 33)


def test_tep_thieu_cot_bat_buoc_bao_dung_ten_cot():
    ket_qua = doc_tep_log_iris(LOG_THIEU)
    assert ket_qua.thieu_cot
    assert any("SERIAL NUMBER" in cot for cot in ket_qua.thieu_cot)
    thong_diep = thong_diep_thieu_cot(ket_qua, "thieu_serial.csv")
    assert "SERIAL NUMBER" in thong_diep
    assert "thieu_serial.csv" in thong_diep


def test_tep_khong_phai_log_iris_bao_loi_tieng_viet(tmp_path):
    tep = tmp_path / "khong_phai_log.csv"
    tep.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(ValueError) as loi:
        doc_tep_log_iris(tep)
    assert "ma trận rộng" in str(loi.value)
    assert la_tep_log_iris(tep) is False


def test_snapshot_chuan_dung_lai_duoc_duong_cong_du_lieu():
    from aios_habit.production_prediction.lsu_iris import (
        evaluate_data_gate_rubric,
        join_lsu_trace,
        normalize_records,
    )

    ket_qua = doc_tep_log_iris(LOG_THAT)
    snapshot = chuyen_ban_ghi_iris_sang_snapshot([ket_qua], nguon_tep=["2ND-0000-1_2026_07_UnitTest.csv"])
    assert snapshot.jig_outcomes
    assert all(j.metric_name and j.unit_serial for j in snapshot.jig_outcomes)
    normalized = normalize_records(snapshot)
    traces = join_lsu_trace(normalized)
    assert set(traces) == {"SYN_UNIT_001", "SYN_UNIT_002", "SYN_UNIT_003"}
    bao_cao = evaluate_data_gate_rubric(snapshot, normalized, traces)
    assert bao_cao.total_rows == len(snapshot.jig_outcomes)


def test_nhom_depth_doc_duoc_chuoi_do():
    from aios_habit.production_prediction.iris_log_adapter import doc_nhom_c_depth

    import csv as _csv

    with TEP_DEPTH.open(encoding="utf-8-sig", newline="") as f:
        cac_dong = [r for r in _csv.reader(f)]
    ket_qua = doc_nhom_c_depth(cac_dong, TEP_DEPTH.name)
    assert ket_qua.loai == "depth"
    hop_le = ket_qua.ban_ghi_hop_le()
    assert hop_le
    assert {b.unit_serial for b in hop_le} == {"SYN_UNIT_001", "SYN_UNIT_002"}
    assert all(not la_canh_loi(b.value) for b in hop_le)


def test_nhom_spec_doc_duoc_gioi_han():
    import csv as _csv

    from aios_habit.production_prediction.iris_log_adapter import doc_nhom_b_gioi_han

    with TEP_SPEC.open(encoding="utf-8-sig", newline="") as f:
        cac_dong = [r for r in _csv.reader(f)]
    tieu_de = [c.strip() for c in cac_dong[0]]
    ngung = doc_nhom_b_gioi_han(tieu_de, cac_dong[1:])
    assert "Spec:Current:Lower[mA]" in ngung
    assert "Spec:Current:Upper[mA]" in ngung
    assert "Spec:Bow[um]" in ngung
    assert ngung["Spec:Current:Lower[mA]"]["gia_tri_moi_nhat"] == 370
    assert ngung["Spec:Current:Upper[mA]"]["gia_tri_moi_nhat"] == 520


# --------------------------------------------------------------------------
# T016-03 — ô nhập chat hiểu dòng Iris thật, kể cả khi dán kèm tiêu đề
# --------------------------------------------------------------------------


def test_nhan_dien_dong_iris_that_va_dong_tieu_de():
    assert la_dong_tieu_de_iris(_dong_tieu_de(LOG_THAT)) is True
    assert la_dong_log_iris(_dong_du_lieu(LOG_THAT)) is True
    # Dòng tiêu đề phải được nhận là tiêu đề, không phải dòng dữ liệu.
    assert la_dong_log_iris(_dong_tieu_de(LOG_THAT)) is False
    # Dòng 7 cột cũ vẫn phải được nhận diện như trước (không hồi quy).
    assert is_jig_log_line("2026-09-20T08:00:00,UNIT001,JIG-01,bowskew,0.12,mm,OK") is True


def test_dong_iris_that_khong_bi_bam_nat_boi_bo_phan_tich_7_cot():
    """Lỗi cũ: dòng 572 cột bị hiểu thành timestamp/serial/metric sai hết."""
    du_lieu = _dong_du_lieu(LOG_THAT)
    assert parse_jig_log_line(du_lieu) is None
    ket_qua = parse_dong_log_iris(du_lieu)
    assert ket_qua.thieu_cot == ["dòng tiêu đề của tệp log"]
    assert ket_qua.so_cot == 572


def test_dan_kem_tieu_de_va_dong_du_lieu_thi_tach_duoc_ban_ghi():
    ket_qua = parse_dong_log_iris(_dong_tieu_de(LOG_THAT) + "\n" + _dong_du_lieu(LOG_THAT))
    assert not ket_qua.thieu_cot
    hop_le = ket_qua.ban_ghi_hop_le()
    assert hop_le
    assert {b.unit_serial for b in hop_le} == {"SYN_UNIT_001"}
    assert all(b.jig_id == "IrisLSU (log dán)" for b in hop_le)


def test_dong_7_cot_cu_van_hoat_dong_nhu_truoc():
    parsed = parse_jig_log_line("2026-09-20T08:00:00,UNIT001,JIG-01,bowskew,0.12,mm,OK")
    assert parsed is not None
    assert parsed.unit_serial == "UNIT001"
    assert parsed.metric == "bowskew"
    assert parsed.value == 0.12


# --------------------------------------------------------------------------
# T016-05 / T016-06 — kho ngưỡng và đọc ngưỡng từ tệp giới hạn
# --------------------------------------------------------------------------


def test_gioi_han_tuong_minh_tu_tep_spec_co_hieu_luc_ngay():
    import csv as _csv

    from aios_habit.production_prediction.iris_log_adapter import doc_nhom_b_gioi_han

    with TEP_SPEC.open(encoding="utf-8-sig", newline="") as f:
        cac_dong = [r for r in _csv.reader(f)]
    tieu_de = [c.strip() for c in cac_dong[0]]
    ngung = doc_nhom_b_gioi_han(tieu_de, cac_dong[1:])
    danh_sach = ngung_do_tu_tep_gioi_han("2ND-1004", ngung, nguon="2026_08_Spec.csv")
    hieu_luc = [n for n in danh_sach if n.trang_thai == HIEU_LUC]
    assert hieu_luc
    dong = [n for n in hieu_luc if n.chi_so == "APC:CURRENT"]
    assert dong
    assert dong[0].gioi_han_duoi == 370
    assert dong[0].gioi_han_tren == 520
    vi_tri = [n for n in hieu_luc if n.chi_so == "BEAM_POS:X"]
    assert vi_tri and vi_tri[0].gioi_han_duoi == 2890 and vi_tri[0].gioi_han_tren == 3190


def test_dung_sai_mot_con_so_khong_tu_dong_co_hieu_luc():
    """An toàn: Spec:Bow[um] = 25 không phải giới hạn trên/dưới.

    Đo thật trên 2ND-1004 cho thấy Bow:Black:0 nằm trong khoảng −225…+22 nhưng
    máy vẫn chấm OK, nên áp thẳng ±25 sẽ báo động giả hàng loạt.
    """
    import csv as _csv

    from aios_habit.production_prediction.iris_log_adapter import doc_nhom_b_gioi_han

    with TEP_SPEC.open(encoding="utf-8-sig", newline="") as f:
        cac_dong = [r for r in _csv.reader(f)]
    tieu_de = [c.strip() for c in cac_dong[0]]
    ngung = doc_nhom_b_gioi_han(tieu_de, cac_dong[1:])
    danh_sach = ngung_do_tu_tep_gioi_han("2ND-1004", ngung, nguon="2026_08_Spec.csv")
    bow = [n for n in danh_sach if n.chi_so == "BOW"]
    assert bow
    assert bow[0].trang_thai == CHO_XAC_NHAN
    assert bow[0].hieu_luc() is False
    assert bow[0].gioi_han_tren is None and bow[0].gioi_han_duoi is None
    assert "dung sai một con số" in bow[0].ghi_chu
    # Và vì chưa hiệu lực nên không được dùng để phân loại.
    assert phan_loai_theo_nguong(999.0, bow[0]) is None


def test_phan_loai_theo_nguong_that():
    nguong = NguongChiSo(
        jig_id="2ND-1004", chi_so="APC:CURRENT",
        gioi_han_duoi=370, gioi_han_tren=520, nguon="2026_08_Spec.csv",
        nguong_phan_tram=80.0,
    )
    vuot = phan_loai_theo_nguong(600.0, nguong)
    assert vuot is not None and vuot["trang_thai"] == "Vi phạm" and vuot["canh_bao"] is True
    duoi = phan_loai_theo_nguong(300.0, nguong)
    assert duoi is not None and duoi["trang_thai"] == "Vi phạm"
    giua = phan_loai_theo_nguong(445.0, nguong)
    assert giua is not None and giua["trang_thai"] == "Đạt"
    # 80% của nửa dải 75 → 60; 505 lệch 60 → chạm mức theo dõi.
    can_bien = phan_loai_theo_nguong(505.0, nguong)
    assert can_bien is not None and can_bien["trang_thai"] == "Cận biên"


def test_kho_nguong_luu_va_doc_lai(tmp_path):
    tep = tmp_path / "metric_limits.json"
    kho = KhoNguong()
    kho.dat(NguongChiSo(jig_id="2ND-1004", chi_so="BOW", gioi_han_tren=25, nguon="nguoi_dung"))
    luu_nguong(kho, tep)
    lai = doc_nguong(tep)
    lay = lai.lay("2ND-1004", "BOW")
    assert lay is not None and lay.gioi_han_tren == 25
    assert lay.hieu_luc() is True


def test_doc_nguong_thieu_tep_tra_kho_rong(tmp_path):
    assert doc_nguong(tmp_path / "khong_ton_tai.json").danh_sach() == []


# --------------------------------------------------------------------------
# T016-07 — ngưỡng thật quyết định kết luận thay cho trung bình ± 3σ
# --------------------------------------------------------------------------


def test_evaluate_ewma_dung_nguong_that_khi_co():
    nguong = NguongChiSo(
        jig_id="JIG-01", chi_so="bowskew",
        gioi_han_duoi=0.0, gioi_han_tren=0.2, nguon="tep_spec",
    )
    # Nền phẳng: nếu không có ngưỡng thật thì EWMA kết luận "Vi phạm" vì lệch nền.
    ket_qua = evaluate_single_log_ewma(0.5, [0.01] * 30, nguong=nguong)
    assert ket_qua["trang_thai"] == "Vi phạm"
    assert ket_qua["nguon_nguong"] == "tep_spec"
    assert "giới hạn trên" in ket_qua["chi_tiet"]

    # Và khi nằm trong ngưỡng thật thì phải là Đạt, dù nền rất khác.
    trong = evaluate_single_log_ewma(0.1, [0.01] * 30, nguong=nguong)
    assert trong["trang_thai"] == "Đạt"


def test_evaluate_ewma_khong_co_nguong_giu_hanh_vi_cu():
    ket_qua = evaluate_single_log_ewma(0.50, [0.10] * 30)
    assert ket_qua["trang_thai"] == "Vi phạm"
    assert "nguon_nguong" not in ket_qua


# --------------------------------------------------------------------------
# T016-09 — nhập / xem / xóa ngưỡng qua chat
# --------------------------------------------------------------------------


def test_lenh_nguong_khong_gianh_lenh_cau_hinh_canh_bao():
    assert la_lenh_nguong("đặt ngưỡng trên 25 cho Bow") is True
    assert la_lenh_nguong("xem ngưỡng") is True
    # Các câu này thuộc cấu hình cảnh báo chung, không phải ngưỡng chỉ số.
    assert la_lenh_nguong("đổi ngưỡng 90%") is False
    assert la_lenh_nguong("thêm email to.truong@congty.local") is False
    assert la_lenh_nguong("đổi giãn cách 60 phút") is False


def test_dat_nguong_qua_chat_roi_xem_lai_va_xoa():
    kho = KhoNguong()
    kho, loi_nhan = xu_ly_lenh_nguong("đặt ngưỡng trên 25 cho Bow", kho, jig_id="2ND-1004")
    assert "25" in loi_nhan
    assert kho.lay("2ND-1004", "BOW") is not None

    kho, xem = xu_ly_lenh_nguong("xem ngưỡng", kho, jig_id="2ND-1004")
    assert "BOW" in xem

    kho, xoa = xu_ly_lenh_nguong("xóa ngưỡng Bow", kho, jig_id="2ND-1004")
    assert "Đã xóa" in xoa
    assert kho.lay("2ND-1004", "BOW") is None


def test_dat_nguong_thieu_phia_thi_hoi_lai_khong_doan():
    kho = KhoNguong()
    kho_moi, loi_nhan = xu_ly_lenh_nguong("đặt ngưỡng 25 cho Bow", kho)
    assert "trên hay ngưỡng dưới" in loi_nhan
    assert kho_moi.danh_sach() == []


def test_dat_nguong_thieu_chi_so_thi_hoi_lai():
    kho = KhoNguong()
    _, loi_nhan = xu_ly_lenh_nguong("đặt ngưỡng trên 25", kho)
    assert "chỉ số" in loi_nhan


def test_dat_nguong_qua_chat_duoc_luu_va_dung_lai_duoc(tmp_path):
    """Lỗi thật: nếu không phát hiện thay đổi thì ngưỡng không được lưu."""
    from aios_habit.production_prediction.jig_chat_wire import handle_jig_chat_text

    duong_dan = tmp_path / "metric_limits.json"
    saved: list = []
    handled = handle_jig_chat_text(
        "đặt ngưỡng trên 25 cho Bow",
        conversation_id="CONV-01",
        locale="vi",
        session_state={},
        save_user=lambda c: saved.append(("user", c)),
        save_assistant=lambda c: saved.append(("assistant", c)),
        config_path=tmp_path / "jig_alert_config.json",
        limits_path=duong_dan,
    )
    assert handled is True
    assert duong_dan.exists(), "Ngưỡng phải được lưu sau khi người dùng đặt"
    kho = doc_nguong(duong_dan)
    assert kho.lay("", "BOW") is not None
    assert kho.lay("", "BOW").gioi_han_tren == 25
    assert kho.lay("", "BOW").nguon == "nguoi_dung"


def test_lenh_xem_nguong_khong_ghi_tep(tmp_path):
    """Chỉ xem thì không được tạo tệp ngưỡng."""
    from aios_habit.production_prediction.jig_chat_wire import handle_jig_chat_text

    duong_dan = tmp_path / "metric_limits.json"
    handle_jig_chat_text(
        "xem ngưỡng",
        conversation_id="CONV-01",
        locale="vi",
        session_state={},
        save_user=lambda c: None,
        save_assistant=lambda c: None,
        config_path=tmp_path / "jig_alert_config.json",
        limits_path=duong_dan,
    )
    assert not duong_dan.exists()


def test_bang_nguong_van_ban_nêu_nguồn_va_muc_theo_doi():
    kho = KhoNguong()
    kho.dat(NguongChiSo(
        jig_id="2ND-1004", chi_so="APC:CURRENT",
        gioi_han_duoi=370, gioi_han_tren=520, nguon="2026_08_Spec.csv", nguong_phan_tram=80,
    ))
    bang = bang_nguong_van_ban(kho, "2ND-1004")
    assert "APC:CURRENT" in bang
    assert "370" in bang and "520" in bang
    assert "80%" in bang


# --------------------------------------------------------------------------
# Ngưỡng tệp giới hạn là chuỗi theo S/N: tra đúng S/N và đúng thời điểm
# --------------------------------------------------------------------------


def test_nguong_tra_dung_so_seri_chu_khong_lay_dong_moi_nhat_cua_ca_tep():
    """An toàn: mỗi S/N có ngưỡng riêng; tra sai S/N sẽ báo động giả."""
    from datetime import datetime

    from aios_habit.production_prediction.metric_limits import doc_nguong_tu_tep_gioi_han

    tep = GOI / "spec" / "SYN_2026_08_Spec.csv"
    # Kèm thời điểm đo nằm trước lần cập nhật ngày 03/08 của SYN_UNIT_A01.
    truoc_cap_nhat = datetime(2026, 8, 2, 9, 0, 0)
    a1 = doc_nguong_tu_tep_gioi_han(tep, "SYN_UNIT_A01", luc_do=truoc_cap_nhat, jig_id="2ND-1004")
    a2 = doc_nguong_tu_tep_gioi_han(tep, "SYN_UNIT_A02", luc_do=truoc_cap_nhat, jig_id="2ND-1004")
    dong_a1 = [n for n in a1 if n.chi_so == "APC:CURRENT" and n.hieu_luc()][0]
    dong_a2 = [n for n in a2 if n.chi_so == "APC:CURRENT" and n.hieu_luc()][0]
    assert (dong_a1.gioi_han_duoi, dong_a1.gioi_han_tren) == (370, 520)
    assert (dong_a2.gioi_han_duoi, dong_a2.gioi_han_tren) == (50, 200)
    # S/N lạ thì không được đoán bừa.
    assert doc_nguong_tu_tep_gioi_han(tep, "KHONG_CO_SERI", jig_id="x") == []


def test_nguong_khong_lay_dong_tuong_lai():
    """Chống rò rỉ tương lai: chỉ dùng dòng có thời điểm ≤ lúc đo."""
    from datetime import datetime

    from aios_habit.production_prediction.metric_limits import doc_nguong_tu_tep_gioi_han

    tep = GOI / "spec" / "SYN_2026_08_Spec.csv"
    truoc = doc_nguong_tu_tep_gioi_han(
        tep, "SYN_UNIT_A01", luc_do=datetime(2026, 8, 1, 14, 0, 0), jig_id="2ND-1004"
    )
    sau = doc_nguong_tu_tep_gioi_han(
        tep, "SYN_UNIT_A01", luc_do=datetime(2026, 8, 4, 14, 0, 0), jig_id="2ND-1004"
    )
    truoc_cur = [n for n in truoc if n.chi_so == "APC:CURRENT" and n.hieu_luc()][0]
    sau_cur = [n for n in sau if n.chi_so == "APC:CURRENT" and n.hieu_luc()][0]
    assert (truoc_cur.gioi_han_duoi, truoc_cur.gioi_han_tren) == (370, 520)
    # Sau khi tệp cập nhật ngày 03/08 thì dùng cặp mới.
    assert (sau_cur.gioi_han_duoi, sau_cur.gioi_han_tren) == (100, 300)


def test_nguong_khong_ro_ri_tuong_lai_khi_do_truoc_moi_dong_spec():
    """Lỗi thật đã sửa: đo trước mọi dòng Spec của S/N thì phải KHÔNG có ngưỡng.

    Trước khi sửa, hàm rơi về dòng muộn nhất của S/N (một dòng ở tương lai), tức
    là dùng thông tin tương lai để quyết định cảnh báo.
    """
    from datetime import datetime

    from aios_habit.production_prediction.metric_limits import doc_nguong_tu_tep_gioi_han

    tep = GOI / "spec" / "SYN_2026_08_Spec.csv"
    # Mọi dòng Spec của fixture đều ở 01/08 và 03/08/2026.
    truoc_moi_dong = doc_nguong_tu_tep_gioi_han(
        tep, "SYN_UNIT_A01", luc_do=datetime(2020, 1, 1), jig_id="2ND-1004"
    )
    assert truoc_moi_dong == []



def test_nguong_tu_tep_gioi_han_khop_voi_ket_luan_cua_may():
    """Bất biến an toàn: ngưỡng hiệu lực không được mâu thuẫn với nhãn OK/NG.

    Fixture ``SYN_limits_consistency.csv`` có 3 Unit với Current 427,62 / 180,0 /
    700,0 và nhãn OK / OK / NG, còn ngưỡng tra theo S/N là 370–520 và 50–200.
    Vì mỗi Unit được tra đúng ngưỡng của nó nên không Unit OK nào bị gắn cờ oan.
    """
    from aios_habit.production_prediction.metric_limits import (
        doc_nguong_tu_tep_gioi_han,
        phan_loai_theo_nguong,
    )

    tep_gioi_han = GOI / "spec" / "SYN_2026_08_Spec.csv"
    ket_qua = doc_tep_log_iris(GOI / "unit_test" / "SYN_limits_consistency.csv")
    assert not ket_qua.thieu_cot
    do_dac = {
        b.unit_serial: b
        for b in ket_qua.ban_ghi_hop_le()
        if b.metric_name == "APC:CURRENT" and b.value is not None
    }
    assert set(do_dac) == {"SYN_UNIT_A01", "SYN_UNIT_A02", "SYN_UNIT_A03"}
    assert do_dac["SYN_UNIT_A01"].target_label == "OK"
    assert do_dac["SYN_UNIT_A02"].target_label == "OK"
    assert do_dac["SYN_UNIT_A03"].target_label == "NG"

    ket_luan = {}
    for unit_serial, ban_ghi in do_dac.items():
        danh_sach = doc_nguong_tu_tep_gioi_han(
            tep_gioi_han, unit_serial, luc_do=ban_ghi.event_time, jig_id="2ND-1004"
        )
        nguong = [n for n in danh_sach if n.chi_so == "APC:CURRENT" and n.hieu_luc()]
        assert nguong, f"Thiếu ngưỡng hiệu lực cho {unit_serial}"
        phan_loai = phan_loai_theo_nguong(ban_ghi.value, nguong[0])
        assert phan_loai is not None
        ket_luan[unit_serial] = phan_loai["trang_thai"]

    assert ket_luan["SYN_UNIT_A01"] == "Đạt"
    # SYN_UNIT_A02 chỉ nằm trong ngưỡng của chính nó (50–200), không phải 370–520.
    assert ket_luan["SYN_UNIT_A02"] == "Đạt"
    assert ket_luan["SYN_UNIT_A03"] == "Vi phạm"


# --------------------------------------------------------------------------
# Chống tái phát cho các lỗi kiểm toán độc lập tìm ra (T016-17)
# --------------------------------------------------------------------------


def test_gan_canh_loi_chi_an_dung_vung_999_khong_an_gia_tri_that():
    """Lỗi thật: dùng ngưỡng ``>= 999`` sẽ nuốt giá trị đo hợp lệ > 1000.

    Đo thật cho thấy máy chỉ ghi ``999`` và ``999.9``, còn vị trí chùm tia
    ``BeamPosX`` ≈ 2890–3190 µm là giá trị thật.
    """
    from aios_habit.production_prediction.iris_log_adapter import la_canh_loi

    assert la_canh_loi(999.0) is True
    assert la_canh_loi(999.9) is True
    assert la_canh_loi(9999.9) is True
    assert la_canh_loi(9999.0) is True
    assert la_canh_loi(-999.0) is True
    # Giá trị thật phải được giữ.
    assert la_canh_loi(2890.0) is False
    assert la_canh_loi(3190.0) is False
    assert la_canh_loi(1000.0) is False
    assert la_canh_loi(60.0) is False
    assert la_canh_loi(None) is False


def test_canh_loi_999_9_bi_bo_khoi_ban_ghi_hop_le():
    """Lỗi thật: chỉ so bằng đúng ``999.0`` nên ``999.9`` lọt vào dữ liệu dùng được."""
    ket_qua = doc_tep_log_iris(LOG_THAT)
    assert all(not (999 <= abs(b.value) < 1000) for b in ket_qua.ban_ghi_hop_le())


def test_cho_xac_nhan_khong_che_nguong_dung_chung_da_hieu_luc():
    """Lỗi thật: bản ghi ``cho_xac_nhan`` của Unit này che mất ngưỡng dùng chung.

    Trước khi sửa, ``lay()`` trả bản chờ xác nhận, lớp gọi tưởng không có ngưỡng
    nên rơi về EWMA và đổi kết luận từ Đạt sang Vi phạm.
    """
    from aios_habit.production_prediction.metric_limits import phan_loai_theo_nguong

    kho = KhoNguong()
    kho.dat(NguongChiSo(jig_id="J", chi_so="BOW", gioi_han_duoi=0, gioi_han_tren=200))
    kho.dat(NguongChiSo(jig_id="J", chi_so="BOW", unit_serial="SN1", trang_thai=CHO_XAC_NHAN))
    lay = kho.lay("J", "BOW", "SN1")
    assert lay is not None
    assert lay.hieu_luc() is True, "Phải trả ngưỡng dùng chung đã hiệu lực"
    phan_loai = phan_loai_theo_nguong(100.0, lay)
    assert phan_loai is not None and phan_loai["trang_thai"] == "Đạt"


def test_nguong_theo_moc_hieu_luc_khong_ap_nguoc_cho_lan_do_cu():
    """Lỗi thật: khoá chỉ theo S/N nên dải mới bị áp cho lần đo cũ."""
    from datetime import datetime

    kho = KhoNguong()
    kho.dat(NguongChiSo(
        jig_id="J", chi_so="APC:CURRENT", unit_serial="SN1",
        gioi_han_duoi=50, gioi_han_tren=200, hieu_luc_tu="2026-08-01T00:00:00",
    ))
    kho.dat(NguongChiSo(
        jig_id="J", chi_so="APC:CURRENT", unit_serial="SN1",
        gioi_han_duoi=370, gioi_han_tren=520, hieu_luc_tu="2026-08-10T00:00:00",
    ))
    cu = kho.lay("J", "APC:CURRENT", "SN1", datetime(2026, 8, 2, 9, 0, 0))
    moi = kho.lay("J", "APC:CURRENT", "SN1", datetime(2026, 8, 11, 9, 0, 0))
    assert (cu.gioi_han_duoi, cu.gioi_han_tren) == (50, 200)
    assert (moi.gioi_han_duoi, moi.gioi_han_tren) == (370, 520)
    # Trước cả hai mốc thì không có ngưỡng nào hiệu lực.
    assert kho.lay("J", "APC:CURRENT", "SN1", datetime(2026, 7, 1, 9, 0, 0)) is None


def test_nap_nguong_giu_nhieu_dai_theo_thoi_gian():
    """Lỗi thật: nạp ngưỡng chỉ giữ dải của lần đo đầu tiên."""
    from datetime import datetime

    from aios_habit.production_prediction.metric_limits import nap_nguong_tu_tep_gioi_han

    class DoDac:
        def __init__(self, sn, moc):
            self.unit_serial = sn
            self.event_time = moc

    tep = GOI / "spec" / "SYN_2026_08_Spec.csv"
    kho = KhoNguong()
    # Đo trước mốc cập nhật 03/08 rồi sau đó.
    nap_nguong_tu_tep_gioi_han(
        kho, tep, [DoDac("SYN_UNIT_A01", datetime(2026, 8, 2, 9, 0, 0))], jig_id="2ND-1004"
    )
    nap_nguong_tu_tep_gioi_han(
        kho, tep, [DoDac("SYN_UNIT_A01", datetime(2026, 8, 11, 9, 0, 0))], jig_id="2ND-1004"
    )
    cu = kho.lay("2ND-1004", "APC:CURRENT", "SYN_UNIT_A01", datetime(2026, 8, 2, 9, 0, 0))
    moi = kho.lay("2ND-1004", "APC:CURRENT", "SYN_UNIT_A01", datetime(2026, 8, 11, 9, 0, 0))
    assert (cu.gioi_han_duoi, cu.gioi_han_tren) == (370, 520)
    assert (moi.gioi_han_duoi, moi.gioi_han_tren) == (100, 300)


def test_bieu_do_lay_dung_dai_cua_so_seri_dang_ve():
    """Lỗi thật: biểu đồ vẽ dải của S/N đầu danh sách chưa lọc."""
    from aios_habit.production_prediction.chart_selection import dung_du_lieu_bieu_do

    kho = KhoNguong()
    kho.dat(NguongChiSo(
        jig_id="J", chi_so="BOW", unit_serial="SN_A", gioi_han_duoi=50, gioi_han_tren=200,
    ))
    kho.dat(NguongChiSo(
        jig_id="J", chi_so="BOW", unit_serial="SN_B", gioi_han_duoi=370, gioi_han_tren=520,
    ))
    hang = [
        # Dòng đầu là S/N khác, chỉ số khác → không được quyết định dải của biểu đồ.
        {"jig_id": "J", "unit_serial": "SN_A", "metric_name": "SKEW", "value": 10, "event_time": "t1"},
        {"jig_id": "J", "unit_serial": "SN_B", "metric_name": "BOW", "value": 400, "event_time": "t2"},
    ]
    du_lieu = dung_du_lieu_bieu_do("J", "BOW", hang, kho_nguong=kho)
    assert du_lieu.usl == 520 and du_lieu.lsl == 370
    assert du_lieu.values == [400]


def test_lenh_doi_nguong_khong_dau_phan_tram_khong_bi_gianh():
    """Lỗi thật: ``đổi ngưỡng 90`` (không %) bị hiểu thành lệnh ngưỡng chỉ số."""
    from aios_habit.production_prediction.jig_chat_wire import decide_jig_action

    assert la_lenh_nguong("đổi ngưỡng 90") is False
    assert la_lenh_nguong("thay ngưỡng 90") is False
    assert la_lenh_nguong("đặt ngưỡng trên 25 cho Bow") is True
    kho = KhoNguong()
    outcome = decide_jig_action("đổi ngưỡng 90", nguong=kho)
    assert outcome.handled is True
    # Không được tạo ngưỡng chỉ số nào từ câu này.
    assert outcome.nguong_changed is False
    assert kho.danh_sach() == []
    # Và phải hướng dẫn người dùng ghi đúng dạng phần trăm.
    assert "%" in outcome.assistant_text
    # Đổi ngưỡng phần trăm hợp lệ vẫn đi đúng đường cấu hình cảnh báo.
    from aios_habit.production_prediction.alert_config_chat import AlertConfig

    config = AlertConfig()
    hop_le = decide_jig_action("đổi ngưỡng 90%", alert_config=config)
    assert hop_le.config_changed is True
    assert config.nguong_phan_tram == 90


def test_chi_so_current_va_voltage_quy_ve_cung_khoa_voi_spec():
    """Lỗi thật: ``Current[mA]`` không quy về ``APC:CURRENT`` nên không gặp ngưỡng."""
    from aios_habit.production_prediction.chart_selection import ma_chi_so_chuan

    assert ma_chi_so_chuan("Current") == "APC:CURRENT"
    assert ma_chi_so_chuan("CURRENT") == "APC:CURRENT"
    assert ma_chi_so_chuan("Voltage") == "APC:VOLTAGE"
    assert ma_chi_so_chuan("APC:CURRENT") == "APC:CURRENT"
    assert ma_chi_so_chuan("Spec:Current:Lower[mA]") == "APC:CURRENT"
    assert ma_chi_so_chuan("BeamPosX:Black:-140:LD1[um]") == "BEAM_POS:X"


# --------------------------------------------------------------------------
# Chống tái phát cho lượt kiểm toán thứ hai (các lỗi còn sót)
# --------------------------------------------------------------------------


def test_cot_beampos_co_don_vi_giua_ten_van_tach_duoc():
    """Lỗi thật: ``BeamPosX:Black:-140:LD1_1[um]:6face`` bị bỏ vì đơn vị ở giữa."""
    from aios_habit.production_prediction.chart_selection import ma_chi_so_chuan

    cot = tach_cot_do("BeamPosX:Black:-140:LD1_1[um]:6face")
    assert cot is not None
    assert cot.ho == "BEAM_POS:X"
    assert cot.mau == "BLACK"
    assert cot.don_vi == "um"
    # Đơn vị không được còn nằm trong tên chỉ số.
    assert "[" not in cot.ten_chuan() and "]" not in cot.ten_chuan()
    assert ma_chi_so_chuan(cot.ten_chuan()) == "BEAM_POS:X"
    # Và đơn vị ở cuối vẫn hoạt động như trước.
    assert tach_cot_do("SKEW:BLACK[um]").ten_chuan() == "SKEW:BLACK"


def test_canh_loi_bao_gom_ca_bien_the_9999():
    """Lỗi thật: chỉ chặn vùng 999 nên ``9999.9`` lọt vào dữ liệu dùng được."""
    from aios_habit.production_prediction.iris_log_adapter import la_canh_loi

    assert la_canh_loi(9999.9) is True
    assert la_canh_loi(9999.0) is True
    # Vị trí chùm tia thật nằm giữa hai vùng canh lỗi và phải được giữ.
    assert la_canh_loi(3554.2) is False
    assert la_canh_loi(2890.0) is False


def test_nguong_rieng_cua_unit_thang_nguong_dung_chung_moi_hon():
    """Lỗi thật: sắp theo mốc thời gian trước nên dải dùng chung mới hơn đè dải riêng."""
    from datetime import datetime

    kho = KhoNguong()
    kho.dat(NguongChiSo(
        jig_id="J", chi_so="BOW", unit_serial="SNX",
        gioi_han_duoi=50, gioi_han_tren=200, hieu_luc_tu="2026-08-01T00:00:00",
    ))
    kho.dat(NguongChiSo(
        jig_id="J", chi_so="BOW",
        gioi_han_duoi=370, gioi_han_tren=520, hieu_luc_tu="2026-08-10T00:00:00",
    ))
    lay = kho.lay("J", "BOW", "SNX", datetime(2026, 8, 11))
    assert (lay.gioi_han_duoi, lay.gioi_han_tren) == (50, 200)


def test_nguong_nguoi_dung_khong_hieu_luc_tu_thang_nguong_spec():
    """Lỗi thật: ngưỡng nhập tay không có mốc nên bị ngưỡng spec có mốc đè."""
    from datetime import datetime

    kho = KhoNguong()
    kho.dat(NguongChiSo(
        jig_id="J", chi_so="BOW", unit_serial="SNX",
        gioi_han_duoi=1, gioi_han_tren=2, nguon="nguoi_dung",
    ))
    kho.dat(NguongChiSo(
        jig_id="J", chi_so="BOW", unit_serial="SNX",
        gioi_han_duoi=370, gioi_han_tren=520, hieu_luc_tu="2026-08-10T00:00:00",
    ))
    lay = kho.lay("J", "BOW", "SNX", datetime(2026, 8, 11))
    assert (lay.gioi_han_duoi, lay.gioi_han_tren) == (1, 2)


def test_bieu_do_dung_moc_cua_diem_dang_ve():
    """Lỗi thật: lấy mốc của dòng đầu cùng S/N nhưng khác chỉ số."""
    from aios_habit.production_prediction.chart_selection import dung_du_lieu_bieu_do

    kho = KhoNguong()
    kho.dat(NguongChiSo(
        jig_id="J", chi_so="BOW", unit_serial="SNX",
        gioi_han_duoi=50, gioi_han_tren=200, hieu_luc_tu="2026-08-01T00:00:00",
    ))
    kho.dat(NguongChiSo(
        jig_id="J", chi_so="BOW", unit_serial="SNX",
        gioi_han_duoi=370, gioi_han_tren=520, hieu_luc_tu="2026-08-10T00:00:00",
    ))
    rows = [
        {"jig_id": "J", "unit_serial": "SNX", "metric_name": "SKEW", "value": 5, "event_time": "2026-08-02"},
        {"jig_id": "J", "unit_serial": "SNX", "metric_name": "BOW", "value": 400, "event_time": "2026-08-11"},
    ]
    du_lieu = dung_du_lieu_bieu_do("J", "BOW", rows, kho_nguong=kho)
    assert (du_lieu.usl, du_lieu.lsl) == (520, 370)


def test_bieu_do_nhieu_so_seri_thi_khong_ve_duong_gioi_han():
    """Lỗi thật: nhiều S/N trên cùng biểu đồ vẫn vẽ một dải của S/N đầu."""
    from aios_habit.production_prediction.chart_selection import dung_du_lieu_bieu_do

    kho = KhoNguong()
    kho.dat(NguongChiSo(jig_id="J", chi_so="BOW", unit_serial="SN_A", gioi_han_duoi=50, gioi_han_tren=200))
    kho.dat(NguongChiSo(jig_id="J", chi_so="BOW", unit_serial="SN_B", gioi_han_duoi=370, gioi_han_tren=520))
    rows = [
        {"jig_id": "J", "unit_serial": "SN_A", "metric_name": "BOW", "value": 80, "event_time": "t1"},
        {"jig_id": "J", "unit_serial": "SN_B", "metric_name": "BOW", "value": 400, "event_time": "t2"},
    ]
    du_lieu = dung_du_lieu_bieu_do("J", "BOW", rows, kho_nguong=kho)
    assert du_lieu.usl is None and du_lieu.lsl is None
    assert du_lieu.values == [80, 400]


def test_nguong_bo_qua_dong_spec_thieu_thoi_diem_khi_do_som_hon():
    """Lỗi thật: dòng Spec thiếu thời điểm được coi là luôn hợp lệ."""
    import csv as _csv
    import tempfile
    from datetime import datetime
    from pathlib import Path as _Path

    from aios_habit.production_prediction.metric_limits import doc_nguong_tu_tep_gioi_han

    with tempfile.TemporaryDirectory() as tmp:
        tep = _Path(tmp) / "spec.csv"
        with tep.open("w", encoding="utf-8-sig", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["DATE", " TIME", "S/N", "Spec:Current:Lower[mA]", "Spec:Current:Upper[mA]"])
            w.writerow(["", "", "SNX", "111", "222"])
            w.writerow(["2026/08/01", "13:00:00", "SNX", "50", "200"])
        # Đo trước mọi dòng có thời điểm → không được lấy dòng thiếu thời điểm.
        ket_qua = doc_nguong_tu_tep_gioi_han(tep, "SNX", luc_do=datetime(2026, 7, 1), jig_id="J")
        assert ket_qua == []
        # Đo sau dòng có thời điểm → dùng dòng đó.
        sau = doc_nguong_tu_tep_gioi_han(tep, "SNX", luc_do=datetime(2026, 8, 2), jig_id="J")
        dong = [n for n in sau if n.chi_so == "APC:CURRENT" and n.hieu_luc()][0]
        assert (dong.gioi_han_duoi, dong.gioi_han_tren) == (50, 200)


def test_lenh_doi_nguong_co_phia_van_dat_duoc_nguong_chi_so():
    """Lỗi thật: mọi câu bắt đầu bằng ``đổi`` đều bị đẩy sang đường phần trăm."""
    from aios_habit.production_prediction.jig_chat_wire import decide_jig_action

    assert la_lenh_nguong("đổi ngưỡng trên 25 cho Bow") is True
    kho = KhoNguong()
    outcome = decide_jig_action("đổi ngưỡng trên 25 cho Bow", nguong=kho)
    assert outcome.nguong_changed is True
    assert kho.lay("", "BOW").gioi_han_tren == 25
    # Còn ``đổi ngưỡng 90`` (không phía, không %) vẫn về đường phần trăm.
    assert la_lenh_nguong("đổi ngưỡng 90") is False


# --------------------------------------------------------------------------
# Chống tái phát cho lượt kiểm toán thứ ba
# --------------------------------------------------------------------------


def test_tach_cot_do_khong_loi_khi_tieu_de_thieu_don_vi():
    """Lỗi thật: tiêu đề không có ``[đơn vị]`` làm hàm ném UnboundLocalError.

    Người dùng dán tiêu đề không đơn vị (``SKEW:BLACK``) sẽ làm hỏng cả lượt đọc
    thay vì trả về thông báo thiếu cột bằng tiếng Việt.
    """
    cot = tach_cot_do("SKEW:BLACK")
    assert cot is not None
    assert cot.ho == "SKEW" and cot.mau == "BLACK"
    assert cot.don_vi == ""
    assert tach_cot_do("BOW:BLACK:0") is not None
    assert tach_cot_do("APC:CURRENT") is not None


def test_nguong_nguoi_dung_nhap_qua_chat_thang_nguong_doc_tu_tep_jig():
    """Lỗi thật: ngưỡng chat lưu với ``jig_id=''`` nên bị ngưỡng Spec của JIG đè."""
    import csv as _csv
    import tempfile
    from datetime import datetime
    from pathlib import Path as _Path

    from aios_habit.production_prediction.metric_limits import nap_nguong_tu_tep_gioi_han

    kho = KhoNguong()
    kho, _ = xu_ly_lenh_nguong("đặt ngưỡng trên 2 cho Current", kho, jig_id="")

    with tempfile.TemporaryDirectory() as tmp:
        tep = _Path(tmp) / "spec.csv"
        with tep.open("w", encoding="utf-8-sig", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["DATE", " TIME", "S/N", "Spec:Current:Lower[mA]", "Spec:Current:Upper[mA]"])
            w.writerow(["2026/08/01", "13:00:00", "SNX", "370", "520"])

        class DoDac:
            unit_serial = "SNX"
            event_time = datetime(2026, 8, 11)

        nap_nguong_tu_tep_gioi_han(kho, tep, [DoDac()], jig_id="J")

    lay = kho.lay("J", "APC:CURRENT", "SNX", datetime(2026, 8, 11))
    assert lay is not None
    assert lay.nguon == "nguoi_dung"
    assert lay.gioi_han_tren == 2


def test_bieu_do_nhieu_so_seri_khong_ve_ca_duong_gioi_han_dung_chung():
    """Lỗi thật: nhiều S/N vẫn vẽ dải dùng chung nếu kho có dải đó."""
    from aios_habit.production_prediction.chart_selection import dung_du_lieu_bieu_do

    kho = KhoNguong()
    kho.dat(NguongChiSo(jig_id="J", chi_so="BOW", unit_serial="SN_A", gioi_han_duoi=50, gioi_han_tren=200))
    kho.dat(NguongChiSo(jig_id="J", chi_so="BOW", unit_serial="SN_B", gioi_han_duoi=370, gioi_han_tren=520))
    kho.dat(NguongChiSo(jig_id="J", chi_so="BOW", gioi_han_duoi=1, gioi_han_tren=9))
    rows = [
        {"jig_id": "J", "unit_serial": "SN_A", "metric_name": "BOW", "value": 80, "event_time": "t1"},
        {"jig_id": "J", "unit_serial": "SN_B", "metric_name": "BOW", "value": 400, "event_time": "t2"},
    ]
    du_lieu = dung_du_lieu_bieu_do("J", "BOW", rows, kho_nguong=kho)
    assert du_lieu.usl is None and du_lieu.lsl is None


# --------------------------------------------------------------------------
# Thiếu ngưỡng: nói rõ thiếu gì, nhập gì, và ghi rõ biểu đồ là MÔ PHỎNG
# --------------------------------------------------------------------------


def _hang_depth(so_diem: int = 6):
    return [
        {"jig_id": "J", "unit_serial": "U", "metric_name": "DEPTH:BEAM:H:LD1:IMGHEIGHT:0:CAM0",
         "value": 60 + i, "unit": "", "event_time": f"2026-08-0{i % 9 + 1}"}
        for i in range(so_diem)
    ]


def test_thieu_nguong_thi_bieu_do_duoc_danh_dau_mo_phong():
    """Yêu cầu: thiếu ngưỡng thì vẫn vẽ được nhưng phải nói rõ là mô phỏng."""
    from aios_habit.production_prediction.chart_selection import dung_du_lieu_bieu_do
    from aios_habit.production_prediction.spc_chart import render_chart_png, render_chart_svg

    du_lieu = dung_du_lieu_bieu_do("J", "DEPTH:BEAM:H:LD1:IMGHEIGHT:0:CAM0", _hang_depth())
    assert du_lieu.mo_phong is True
    assert du_lieu.ghi_chu_mo_phong() and "MÔ PHỎNG" in du_lieu.ghi_chu_mo_phong()
    # Ảnh PNG vẫn vẽ được (không chặn người dùng) và SVG mang dòng MÔ PHỎNG.
    import tempfile
    from pathlib import Path as _Path

    with tempfile.TemporaryDirectory() as tmp:
        out = _Path(tmp) / "a.png"
        render_chart_png(du_lieu, "xu_huong", out)
        assert out.stat().st_size > 0
    assert "MÔ PHỎNG" in render_chart_svg(du_lieu, "xu_huong")


def test_co_nguong_that_thi_khong_con_la_mo_phong():
    from aios_habit.production_prediction.chart_selection import dung_du_lieu_bieu_do

    kho = KhoNguong()
    kho.dat(NguongChiSo(
        jig_id="J", chi_so="DEPTH:BEAM:H:LD1:IMGHEIGHT:0", gioi_han_duoi=50, gioi_han_tren=70,
    ))
    du_lieu = dung_du_lieu_bieu_do(
        "J", "DEPTH:BEAM:H:LD1:IMGHEIGHT:0:CAM0", _hang_depth(), kho_nguong=kho
    )
    assert du_lieu.mo_phong is False
    assert (du_lieu.usl, du_lieu.lsl) == (70, 50)
    assert du_lieu.ghi_chu_mo_phong() == ""


def test_huong_dan_thieu_nguong_neu_dung_viec_can_lam():
    """Câu hướng dẫn phải nói thiếu gì, gợi ý lệnh chat, và cả đường bổ sung tệp."""
    from aios_habit.production_prediction.chart_selection import huong_dan_thieu_nguong

    huong_dan = huong_dan_thieu_nguong("DEPTH:BEAM:H:LD1:IMGHEIGHT:0:CAM0")
    assert "thiếu ngưỡng trên/dưới" in huong_dan
    assert "MÔ PHỎNG" in huong_dan
    assert "đặt ngưỡng trên 100 cho DEPTH:BEAM:H:LD1:IMGHEIGHT:0" in huong_dan
    assert "đặt ngưỡng dưới 10 cho DEPTH:BEAM:H:LD1:IMGHEIGHT:0" in huong_dan
    assert "Tệp giới hạn kèm theo" in huong_dan
    # Không được gợi ý khoá quá tổng quát (sẽ áp cho mọi dòng đo sâu).
    assert "cho DEPTH\n" not in huong_dan
    assert "cho DEPTH:" in huong_dan


def test_huong_dan_thieu_nguong_khong_goi_y_khoa_qua_rong():
    from aios_habit.production_prediction.chart_selection import huong_dan_thieu_nguong

    assert "cho APC:CURRENT" in huong_dan_thieu_nguong("APC:CURRENT")
    assert "cho BOW:BLACK:0" in huong_dan_thieu_nguong("BOW:BLACK:0")
    assert "cho BOW_VALUE" in huong_dan_thieu_nguong("BOW_VALUE")


def test_chat_ve_bieu_do_thieu_nguong_thi_noi_ro_va_ghi_mo_phong():
    """Trả lời chat phải nêu thiếu gì, nhập gì, và đánh dấu ảnh là mô phỏng."""
    from aios_habit.production_prediction.jig_chat_wire import decide_jig_action

    hang = _hang_depth()
    ket_qua = decide_jig_action(
        "vẽ biểu đồ xu hướng cho DEPTH:BEAM:H:LD1:IMGHEIGHT:0:CAM0 trên J",
        chart_rows_provider=lambda: hang,
    )
    assert ket_qua.handled is True
    assert ket_qua.chart_png is not None
    assert ket_qua.chart_meta.get("mo_phong") is True
    assert "MÔ PHỎNG" in ket_qua.assistant_text
    assert "đặt ngưỡng trên" in ket_qua.assistant_text
    assert "Tệp giới hạn kèm theo" in ket_qua.assistant_text


def test_kho_log_khong_ghi_duong_dan_o_bat_ky_cot_nao(tmp_path):
    """Lỗ hổng thật: đường dẫn ở cột Unit/metric/status vẫn lọt vào kho.

    Chỉ làm sạch cột JIG là chưa đủ — người dùng có thể dán đường dẫn vào bất kỳ
    ô nào của dòng log.
    """
    from aios_habit.production_prediction.iris_log_adapter import BanGhiIris
    from aios_habit.production_prediction.jig_chat_wire import decide_jig_action
    from aios_habit.production_prediction.log_archive import ghi_ban_ghi

    duong_dan = r"D:\Sandbox\Iris LSU\log\secret.csv"
    for vi_tri, dong in (
        ("unit", f"2026-09-20T08:00:00,{duong_dan},JIG-01,bowskew,0.12,mm,OK"),
        ("metric", f"2026-09-20T08:00:00,U1,JIG-01,{duong_dan},0.12,mm,OK"),
        ("status", f"2026-09-20T08:00:00,U1,JIG-01,bowskew,0.12,mm,{duong_dan}"),
    ):
        kho = tmp_path / f"kho_{vi_tri}"
        decide_jig_action(dong, kho_log_path=kho)
        raw = list(kho.glob("*.jsonl"))[0].read_text(encoding="utf-8")
        assert "Iris LSU" not in raw, f"Rò rỉ đường dẫn ở cột {vi_tri}"
        assert "Sandbox" not in raw

    # Và cả đường ghi trực tiếp với unit_serial là đường dẫn.
    kho2 = tmp_path / "kho_truc_tiep"
    ghi_ban_ghi(
        [BanGhiIris(unit_serial=duong_dan, ngay="2026.07.01", gio="08:00:00",
                    jig_id="J", metric_name="BOW", value=1.0, unit="um")],
        nguon="tep", tep="x.csv", kho=kho2,
    )
    raw2 = list(kho2.glob("*.jsonl"))[0].read_text(encoding="utf-8")
    assert "Iris LSU" not in raw2 and "Sandbox" not in raw2


def test_ten_chi_so_that_co_hai_cham_va_gach_cheo_khong_bi_nham_la_duong_dan(tmp_path):
    """Không được nhận nhầm tên chỉ số thật thành đường dẫn."""
    from aios_habit.production_prediction.jig_log_ingest import parse_jig_log_line
    from aios_habit.production_prediction.log_archive import (
        doc_kho,
        ghi_dong_log_jig,
    )

    kho = tmp_path / "kho"
    dong = parse_jig_log_line("2026-09-20T08:00:00,U1,JIG-01,takt:UnitSet/Cable,4.7,sec,OK")
    assert dong is not None
    ghi_dong_log_jig([dong], kho=kho)
    luu = doc_kho(kho)
    assert luu[0].metric_name == "takt:UnitSet/Cable"


def test_bieu_do_so_sanh_mau_thieu_nguong_van_duoc_danh_dau_mo_phong():
    """Lỗ hổng thật: biểu đồ dạng danh sách bị ép mo_phong=False nên email mất nhãn."""
    from aios_habit.production_prediction.jig_chat_wire import decide_jig_action

    ten_chi_so = "DEPTH:BEAM:H:LD1:IMGHEIGHT:0"
    rows = [
        {"jig_id": "J", "unit_serial": "U", "metric_name": f"{ten_chi_so}:CAM+{k}",
         "value": 60 + i, "unit": "", "event_time": f"2026-08-0{i % 9 + 1}"}
        for k in range(4)
        for i in range(3)
    ]
    ket_qua = decide_jig_action(
        f"vẽ biểu đồ so sánh theo màu cho {ten_chi_so}:CAM+0 trên J",
        chart_rows_provider=lambda: rows,
    )
    assert ket_qua.chart_meta.get("loai_bieu_do") == "so_sanh_mau"
    assert ket_qua.chart_meta.get("mo_phong") is True
    assert "MÔ PHỎNG" in ket_qua.assistant_text

    # Và email phải mang tiền tố mô phỏng theo đúng cờ đó.
    from aios_habit.workspace_chat_ui import build_de_xuat_mail_data

    mail = build_de_xuat_mail_data({"nguoi_nhan": ["a@b.local"]}, ket_qua.chart_meta)
    assert mail["tieu_de"].startswith("[MÔ PHỎNG]")


def test_bieu_do_so_sanh_mau_danh_dau_mo_phong_khong_le_thu_tu_chuoi():
    """Lỗ hổng thật: băng MÔ PHỎNG chỉ xét chuỗi đầu, nên đổi thứ tự là mất dấu.

    Ảnh, câu trả lời chat và tiền tố email phải cùng một kết luận: biểu đồ so
    sánh là mô phỏng nếu **còn** chuỗi thiếu giới hạn, bất kể thứ tự chuỗi.
    """
    from aios_habit.production_prediction.chart_selection import dung_du_lieu_bieu_do
    from aios_habit.production_prediction.metric_limits import KhoNguong, NguongChiSo
    from aios_habit.production_prediction.spc_chart import render_chart_svg

    def hang(chi_so: str):
        return [
            {"jig_id": "J", "unit_serial": "U", "metric_name": chi_so,
             "value": 10 + i, "unit": "", "event_time": f"2026-08-0{i % 9 + 1}"}
            for i in range(3)
        ]

    kho = KhoNguong()
    kho.dat(NguongChiSo(jig_id="J", chi_so="BOW", gioi_han_duoi=0, gioi_han_tren=25))
    co_nguong = dung_du_lieu_bieu_do("J", "BOW", hang("BOW"), kho_nguong=kho)
    khong_nguong = dung_du_lieu_bieu_do("J", "SKEW:BLACK", hang("SKEW:BLACK"))
    assert co_nguong.mo_phong is False and khong_nguong.mo_phong is True

    # Đổi thứ tự chuỗi không được đổi kết luận.
    assert "MÔ PHỎNG" in render_chart_svg([co_nguong, khong_nguong], "so_sanh_mau")
    assert "MÔ PHỎNG" in render_chart_svg([khong_nguong, co_nguong], "so_sanh_mau")
    # Cả hai chuỗi đều có giới hạn thì không đánh dấu.
    kho.dat(NguongChiSo(jig_id="J", chi_so="SKEW", gioi_han_duoi=0, gioi_han_tren=99))
    day_du = [
        dung_du_lieu_bieu_do("J", "BOW", hang("BOW"), kho_nguong=kho),
        dung_du_lieu_bieu_do("J", "SKEW:BLACK", hang("SKEW:BLACK"), kho_nguong=kho),
    ]
    assert all(c.mo_phong is False for c in day_du)
    assert "MÔ PHỎNG" not in render_chart_svg(day_du, "so_sanh_mau")


def test_email_mo_phong_duoc_ghi_ro_trong_chu():
    """Người nhận email đọc phần chữ phải biết ảnh là mô phỏng, không chỉ dựa vào ảnh."""
    from aios_habit.production_prediction.metric_limits import KhoNguong
    from aios_habit.workspace_chat_ui import build_de_xuat_mail_data

    mo_phong = build_de_xuat_mail_data(
        {"nguoi_nhan": ["a@b.local"]},
        {"ma_jig": "J", "ten_chi_so": "DEPTH:X:Y", "mo_phong": True},
    )
    assert mo_phong["tieu_de"].startswith("[MÔ PHỎNG]")
    assert "MÔ PHỎNG" in mo_phong["tom_tat"]
    assert "chưa có giới hạn trên/dưới thật" in mo_phong["tom_tat"]

    that = build_de_xuat_mail_data(
        {"nguoi_nhan": ["a@b.local"]},
        {"ma_jig": "J", "ten_chi_so": "BOW", "mo_phong": False},
    )
    assert "MÔ PHỎNG" not in that["tieu_de"]
    assert "MÔ PHỎNG" not in that["tom_tat"]


def test_lam_theo_huong_dan_thi_het_mo_phong():
    """Vòng lặp phải khép kín: gõ đúng câu hệ thống gợi ý thì phải ra biểu đồ thật.

    Lỗi thật: bộ phân tích lệnh chat không nhận ra mã chỉ số dài của log đo sâu,
    nên chính câu hướng dẫn hệ thống in ra lại **không dùng được**.
    """
    from aios_habit.production_prediction.jig_chat_wire import decide_jig_action

    chi_so = "DEPTH:BEAM:H:LD1:IMGHEIGHT:+140"
    hang = [
        {"jig_id": "J", "unit_serial": "U", "metric_name": f"{chi_so}:CAM+1",
         "value": 60 + i, "unit": "", "event_time": f"2026-08-0{i % 9 + 1}"}
        for i in range(6)
    ]
    kho = KhoNguong()

    # Đúng câu mà huong_dan_thieu_nguong() in ra.
    dat = decide_jig_action(f"đặt ngưỡng trên 65 cho {chi_so}", nguong=kho)
    assert dat.nguong_changed is True, "Câu hướng dẫn phải đặt được ngưỡng"
    assert dat.nguong_changed and dat.assistant_text.startswith("Đã đặt ngưỡng trên 65")
    assert kho.lay("", chi_so).gioi_han_tren == 65

    duoi = decide_jig_action(f"đặt ngưỡng dưới 10 cho {chi_so}", nguong=kho)
    assert kho.lay("", chi_so).gioi_han_duoi == 10

    ve = decide_jig_action(
        f"vẽ biểu đồ xu hướng cho {chi_so}:CAM+1 trên J",
        nguong=kho,
        chart_rows_provider=lambda: hang,
    )
    assert ve.chart_png is not None
    assert ve.chart_meta.get("mo_phong") is False, "Đã có ngưỡng thì không còn mô phỏng"
    assert "thiếu ngưỡng" not in ve.assistant_text

    # Và các lệnh cũ vẫn hoạt động.
    assert decide_jig_action("đặt ngưỡng trên 25 cho Bow", nguong=kho).nguong_changed is True
    assert kho.lay("", "BOW").gioi_han_tren == 25




