"""Tests for the chat-first intent router: every sentence gets an intent."""

from aios_habit.chat_intent_router import (
    CANH_BAO_NGUONG,
    CONG_CU_NANG_CAO,
    HOI_DAP_CHUNG,
    HOI_TAI_LIEU,
    HO_SO_DIEU_TRA,
    MO_SO,
    TAO_SO,
    classify_intent,
    extract_slots,
    route,
)
from aios_habit import chat_intent_router as router


def test_canh_bao_nguong_intents():
    assert classify_intent("cảnh báo khi nhiệt độ vượt 80") == CANH_BAO_NGUONG
    assert classify_intent("CẢNH BÁO KHI áp suất dưới 5") == CANH_BAO_NGUONG
    assert classify_intent("đặt ngưỡng độ rung 10") == CANH_BAO_NGUONG
    assert classify_intent("liệt kê cảnh báo") == CANH_BAO_NGUONG
    assert classify_intent("xóa cảnh báo CB-ABC123") == CANH_BAO_NGUONG


def test_tao_so_va_mo_so():
    assert classify_intent("tạo sổ Lỗi JIG") == TAO_SO
    assert classify_intent("mở sổ Lỗi JIG") == MO_SO
    # "mở hồ sơ" must not be mistaken for "mở sổ"
    assert classify_intent("mở hồ sơ điều tra") == HO_SO_DIEU_TRA


def test_view_intents():
    assert classify_intent("mở công cụ nâng cao") == CONG_CU_NANG_CAO
    assert classify_intent("mở lsu") == CONG_CU_NANG_CAO
    assert classify_intent("dạy AIOS điều tôi biết") == HO_SO_DIEU_TRA


def test_lenh_mo_view_dai_khong_cuop():
    # Long message (pasted log data) must reach the analysis pipeline,
    # not open a view.
    dai = "mở lsu giúp tôi phân tích đoạn log này:\n" + "dòng log jig số liệu, " * 30
    assert classify_intent(dai) == HOI_TAI_LIEU
    dai2 = "điều tra lỗi giúp tôi với dữ liệu sau:\n" + "chi tiết lỗi FXXX, " * 30
    assert classify_intent(dai2) == HOI_TAI_LIEU


def test_small_talk_va_fallback():
    assert classify_intent("xin chào") == HOI_DAP_CHUNG
    assert classify_intent("") == HOI_DAP_CHUNG
    # ordinary questions fall back to document Q&A
    assert classify_intent("lỗi FXXX là gì?") == HOI_TAI_LIEU
    assert classify_intent("nguyên nhân kẹt phôi trên line 3") == HOI_TAI_LIEU


def test_extract_ten_so():
    intent, slots = route("tạo sổ Lỗi JIG tháng 10")
    assert intent == TAO_SO
    assert slots["ten_so"] == "Lỗi JIG tháng 10"
    intent, slots = route("mở sổ bảo trì")
    assert intent == MO_SO
    assert slots["ten_so"] == "bảo trì"


def test_diacritics_insensitive():
    assert classify_intent("canh bao khi nhiet do vuot 80") == CANH_BAO_NGUONG
    assert classify_intent("tao so moi") == TAO_SO


def test_classify_all_intents_mot_cau_nhieu_y():
    from aios_habit.chat_intent_router import DU_LIEU_DAN, classify_all_intents

    csv_block = "nhiet_do,ap_suat\n70,5\n72,5\n74,6\n"
    cau = csv_block + "vẽ biểu đồ và cảnh báo khi nhiệt độ vượt 80"
    intents = classify_all_intents(cau)
    ten_y = [y for y, _ in intents]
    assert DU_LIEU_DAN in ten_y
    assert CANH_BAO_NGUONG in ten_y
    # single-intent entry point keeps old behaviour: first match wins
    assert classify_intent("cảnh báo khi nhiệt độ vượt 80") == CANH_BAO_NGUONG


def test_classify_all_intents_khong_khoi_du_lieu():
    from aios_habit.chat_intent_router import classify_all_intents

    intents = classify_all_intents("cảnh báo khi nhiệt độ vượt 80")
    assert [(y, s) for y, s in intents] == [(CANH_BAO_NGUONG, {})]


def test_classify_all_intents_chi_co_du_lieu_dan():
    from aios_habit.chat_intent_router import DU_LIEU_DAN, classify_all_intents

    csv_block = "thoi_gian,nhiet_do\n10:00,70\n10:01,72\n"
    intents = classify_all_intents("phân tích giúp tôi:\n" + csv_block)
    assert intents[0][0] == DU_LIEU_DAN


def test_classify_all_intents_rong():
    from aios_habit.chat_intent_router import classify_all_intents

    assert classify_all_intents("")[0][0] == HOI_DAP_CHUNG
    assert classify_all_intents("lỗi FXXX là gì?")[0][0] == HOI_TAI_LIEU


def test_ve_bieu_do_intent_don():
    from aios_habit.chat_intent_router import VE_BIEU_DO, classify_intent

    assert classify_intent("vẽ biểu đồ bowskew JIG-01") == VE_BIEU_DO
    assert classify_intent("VẼ BIỂU ĐỒ độ rung") == VE_BIEU_DO


def test_ve_bieu_do_gop_voi_canh_bao_nguong():
    # UX-E2E-APP muc (a): cau gop phai ra DU ca 2 y dinh, phan chart
    # khong duoc bi bo khi cau con chua y dinh khac.
    from aios_habit.chat_intent_router import (
        VE_BIEU_DO,
        classify_all_intents,
    )

    intents = classify_all_intents("vẽ biểu đồ bowskew JIG-01 và đặt ngưỡng trên 12")
    ten_y = [y for y, _ in intents]
    assert CANH_BAO_NGUONG in ten_y
    assert VE_BIEU_DO in ten_y


def test_bieu_do_gui_mail_khong_phai_ve_bieu_do():
    # "bieu do gui mail" thuoc lenh cau hinh canh bao, khong phai ve bieu do.
    from aios_habit.chat_intent_router import VE_BIEU_DO, classify_all_intents

    ten_y = [y for y, _ in classify_all_intents("vẽ biểu đồ gửi mail tuần")]
    assert VE_BIEU_DO not in ten_y


def test_nhan_va_giai_thich_ve_bieu_do():
    from aios_habit.chat_intent_router import (
        TAT_CA_Y_DINH,
        VE_BIEU_DO,
        giai_thich_y_dinh,
        nhan_y_dinh,
    )

    assert nhan_y_dinh(VE_BIEU_DO) == "Vẽ biểu đồ"
    assert giai_thich_y_dinh(VE_BIEU_DO) != ""
    assert VE_BIEU_DO in TAT_CA_Y_DINH


def test_tao_vu_dieu_tra_intents():
    from aios_habit.chat_intent_router import TAO_VU_DIEU_TRA, classify_intent

    assert classify_intent("Tạo vụ điều tra lỗi mới: máy in báo lỗi kẹt giấy ở line 3") == TAO_VU_DIEU_TRA
    assert classify_intent("tạo vụ điều tra kẹt giấy") == TAO_VU_DIEU_TRA
    assert classify_intent("lập vụ điều tra sự cố") == TAO_VU_DIEU_TRA
    assert classify_intent("tao ca loi C7620") == TAO_VU_DIEU_TRA
    assert classify_intent("ghi nhận lỗi JAM4709") == TAO_VU_DIEU_TRA
    assert classify_intent("báo lỗi mới tại line 3") == TAO_VU_DIEU_TRA


def test_extract_case_entities_full():
    from aios_habit.chat_intent_router import extract_case_entities

    ent1 = extract_case_entities("Tạo vụ điều tra lỗi mới: máy in báo lỗi kẹt giấy ở line 3")
    assert ent1["phenomenon"] == "máy in báo lỗi kẹt giấy"
    assert ent1["line"] == "Line 3"
    assert ent1["machine_type"] == "máy in"
    assert ent1["error_code"] == ""

    ent2 = extract_case_entities("Tạo ca lỗi C7620 máy Polaris ở line C33")
    assert ent2["error_code"] == "C7620"
    assert ent2["line"] == "Line C33"
    assert ent2["machine_type"] == "Polaris"

    ent3 = extract_case_entities("ghi nhận lỗi JAM4709 kẹt giấy")
    assert ent3["error_code"] == "JAM4709"
    assert "kẹt giấy" in ent3["phenomenon"]


def test_khong_pha_hanh_vi_cu():
    from aios_habit.chat_intent_router import (
        HOI_TAI_LIEU,
        TAO_SO,
        classify_intent,
    )

    # Tra cuu loi khong bi cuop boi TAO_VU_DIEU_TRA
    assert classify_intent("tra cứu lỗi kẹt giấy") == HOI_TAI_LIEU
    assert classify_intent("tra cuu loi C7620") == HOI_TAI_LIEU
    # Tao so khong bi cuop
    assert classify_intent("tạo sổ Sổ nghiệm thu") == TAO_SO


def test_xem_tien_do_vu_intents():
    from aios_habit.chat_intent_router import XEM_TIEN_DO_VU, classify_intent, route

    assert classify_intent("Xem tiến độ vụ này") == XEM_TIEN_DO_VU
    assert classify_intent("xem tien do vu nay") == XEM_TIEN_DO_VU
    assert classify_intent("tiến độ vụ này") == XEM_TIEN_DO_VU
    assert classify_intent("tiến độ ca này thế nào") == XEM_TIEN_DO_VU
    assert classify_intent("Xem tiến độ vụ CASE-1234ABCD") == XEM_TIEN_DO_VU

    intent, slots = route("Xem tiến độ vụ CASE-1234ABCD")
    assert intent == XEM_TIEN_DO_VU
    assert slots.get("case_id") == "CASE-1234ABCD"


def test_lap_cay_4m_intents():
    from aios_habit.chat_intent_router import LAP_CAY_4M_VU, classify_intent, route

    assert classify_intent("Lập cây 4M cho vụ này") == LAP_CAY_4M_VU
    assert classify_intent("lap cay 4m cho vu nay") == LAP_CAY_4M_VU
    assert classify_intent("cây 4m cho vụ này") == LAP_CAY_4M_VU
    assert classify_intent("lập cây 4m vụ CASE-ABCD") == LAP_CAY_4M_VU
    assert classify_intent("phân tích 4m cho vụ này") == LAP_CAY_4M_VU

    intent, slots = route("Lập cây 4M cho vụ CASE-9999")
    assert intent == LAP_CAY_4M_VU
    assert slots.get("case_id") == "CASE-9999"


def test_extract_case_id_from_text():
    from aios_habit.chat_intent_router import extract_case_id_from_text

    assert extract_case_id_from_text("Xem tiến độ vụ CASE-A1B2C3D4") == "CASE-A1B2C3D4"
    assert extract_case_id_from_text("CASE-12345678 là gì?") == "CASE-12345678"
    assert extract_case_id_from_text("Không có mã vụ nào ở đây") == ""

