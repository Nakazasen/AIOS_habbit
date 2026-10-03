"""Test cau tra loi gop da y dinh (UX-CHAT-CORE-FIX1 F1).

_xu_ly_y_dinh_chat phai chay HET y dinh trong mot cau chat va gop thanh
MOT cau tra loi duy nhat trong vung tra loi; y dinh khong xu ly duoc phai
duoc ghi ro trong cau tra loi gop, khong im lang bo qua.
"""

from types import SimpleNamespace

import pytest
import streamlit as st

import aios_habit.workspace_chat_app as app
import aios_habit.workspace_chat_store as store
from aios_habit.feature_flags import override_feature_flags


class MockSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


CSV_SAMPLE = """thoi_gian,nhiet_do,ap_suat
10:00,36.5,101.2
10:05,37.1,100.8
10:10,38.0,100.1
"""


@pytest.fixture
def mock_app(monkeypatch):
    session_state = MockSessionState()
    monkeypatch.setattr(st, "session_state", session_state)
    da_luu = []
    monkeypatch.setattr(store, "save_message", lambda msg: da_luu.append(msg))
    conv = SimpleNamespace(id="CONV-TEST")
    return session_state, da_luu, conv


def test_cau_gop_chay_het_hai_y_dinh_trong_mot_cau_tra_loi(monkeypatch, mock_app):
    """2-3 y/cau: dan CSV + canh bao nguong -> 1 cau tra loi co du 2 phan."""
    _session_state, da_luu, conv = mock_app
    monkeypatch.setattr(
        "aios_habit.threshold_alert_chat.xu_ly_cau_lenh",
        lambda cau, history_provider=None: "CẢNH BÁO: nhiệt độ vượt ngưỡng 80.",
    )
    cau = CSV_SAMPLE + "vẽ biểu đồ và cảnh báo khi nhiệt độ vượt 80"
    with override_feature_flags(chat_action=True):
        ket_qua = app._xu_ly_y_dinh_chat(
            cau, active_conversation=conv, active_nb_id="NB-1"
        )
    assert ket_qua is True
    # Chi MOT cap tin nhan duoc luu: 1 user + 1 assistant (cau tra loi gop).
    assert len(da_luu) == 2
    assert da_luu[0].role == "user"
    assert da_luu[1].role == "assistant"
    tra_loi = da_luu[1].content
    assert "Phân tích dữ liệu vừa dán" in tra_loi
    assert "Cảnh báo ngưỡng" in tra_loi
    assert "CẢNH BÁO: nhiệt độ vượt ngưỡng 80." in tra_loi
    assert "dữ liệu bạn vừa dán" in tra_loi  # caption bieu do trung thuc


def test_y_dinh_khong_xu_ly_duoc_duoc_ghi_ro_khong_bo_qua_im_lang(
    monkeypatch, mock_app
):
    """Y dinh hong phai co ghi chu ro rang trong cau tra loi gop."""
    _session_state, da_luu, conv = mock_app
    monkeypatch.setattr(
        "aios_habit.threshold_alert_chat.xu_ly_cau_lenh",
        lambda cau, history_provider=None: None,  # khong trich duoc thong so
    )
    cau = CSV_SAMPLE + "cảnh báo khi nhiệt độ vượt 80"
    with override_feature_flags(chat_action=True):
        ket_qua = app._xu_ly_y_dinh_chat(
            cau, active_conversation=conv, active_nb_id="NB-1"
        )
    assert ket_qua is True
    tra_loi = da_luu[1].content
    assert "Phân tích dữ liệu vừa dán" in tra_loi  # phan lam duoc van co
    assert "chưa xử lý được phần này" in tra_loi  # phan hong duoc ghi ro


def test_chi_chuyen_view_khong_luu_tin_nhan_rong(monkeypatch, mock_app):
    """Y dinh chi mo view (khong co doan van ban) thi khong luu bong bong rong."""
    session_state, da_luu, conv = mock_app
    with override_feature_flags(chat_action=True):
        ket_qua = app._xu_ly_y_dinh_chat(
            "mở công cụ nâng cao", active_conversation=conv, active_nb_id="NB-1"
        )
    assert ket_qua is True
    assert session_state.wsc_show_lsu_data_gate is True
    assert da_luu == []
