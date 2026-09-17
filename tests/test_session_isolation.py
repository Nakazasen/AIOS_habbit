"""Contract tests for Zero-UI session isolation (US12 T065)."""

from __future__ import annotations

from aios_habit.production_prediction.session_isolation import (
    SessionPersona,
    classify_session,
    filter_alert_for_session,
    parse_persona_command,
    should_deliver_machine_alert,
)


def test_phien_ca_nhan_mac_dinh_yen_tinh():
    assert classify_session("Trao đổi văn phòng") == "ca_nhan"
    assert should_deliver_machine_alert("ca_nhan") is False


def test_phien_truc_ban_duoc_nhan_canh_bao():
    assert classify_session("Trực ban công đoạn LSU") == "truc_ban"
    assert should_deliver_machine_alert("truc_ban") is True


def test_bat_tat_che_do_bang_mot_cau_chat():
    current = SessionPersona(ten_phien="Chung")
    updated, reply = parse_persona_command("bật trực ban", current)
    assert updated.che_do == "truc_ban"
    assert "trực ban" in reply
    updated2, reply2 = parse_persona_command("chế độ cá nhân", updated)
    assert updated2.che_do == "ca_nhan"
    assert "yên tĩnh" in reply2


def test_loc_canh_bao_khong_chen_vao_phien_ca_nhan():
    alert = {"tieu_de": "Cảnh báo JIG", "noi_dung": "Trôi dốc"}
    assert filter_alert_for_session(alert, "ca_nhan") is None
    assert filter_alert_for_session(alert, "truc_ban") == alert
