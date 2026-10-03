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
