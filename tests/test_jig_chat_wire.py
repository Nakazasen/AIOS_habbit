"""Contract tests for US12 chat wiring (Omnibar JIG/config/persona routing)."""

from __future__ import annotations

from aios_habit.production_prediction.alert_config_chat import AlertConfig
from aios_habit.production_prediction.jig_chat_wire import (
    decide_jig_action,
    handle_jig_chat_text,
    is_config_intent,
    is_persona_intent,
    load_alert_config,
)


def test_dong_log_jig_duoc_xu_ly_khong_qua_rag():
    outcome = decide_jig_action("2026-09-20T08:00:00,UNIT001,JIG-01,bowskew,0.12,mm,OK")
    assert outcome.handled is True
    assert "UNIT001" in outcome.assistant_text
    assert "bowskew" in outcome.assistant_text


def test_cau_hoi_thuong_khong_bi_chan():
    assert decide_jig_action("Hôm nay JIG có gì bất thường?").handled is False
    assert decide_jig_action("Tạo báo cáo lỗi xưởng tuần này").handled is False


def test_lenh_xem_cai_dat_hien_bang():
    assert is_config_intent("xem cấu hình cảnh báo") is True
    assert is_config_intent("cài đặt cảnh báo LSU") is True
    outcome = decide_jig_action("xem cấu hình cảnh báo")
    assert outcome.handled is True
    assert "Bảng cấu hình cảnh báo" in outcome.assistant_text


def test_lenh_them_email_va_doi_nguong():
    config = AlertConfig()
    outcome = decide_jig_action("thêm email to.truong@congty.local", alert_config=config)
    assert outcome.handled is True
    assert "to.truong@congty.local" in config.nguoi_nhan
    assert outcome.config_changed is True
    outcome2 = decide_jig_action("đổi ngưỡng 90%", alert_config=config)
    assert outcome2.handled is True
    assert config.nguong_phan_tram == 90


def test_lenh_truc_ban_doi_persona():
    outcome = decide_jig_action("bật trực ban", persona_che_do="ca_nhan")
    assert outcome.handled is True
    assert outcome.new_persona == "truc_ban"
    assert is_persona_intent("chế độ cá nhân") is True


def test_di_lich_su_ewma_cho_danh_gia_xu_huong():
    outcome = decide_jig_action(
        "2026-09-20T08:00:00,UNIT001,JIG-01,bowskew,0.50,mm,OK",
        history_provider=lambda jig, metric: [0.10] * 30,
    )
    assert outcome.handled is True
    assert "Vi phạm" in outcome.assistant_text


def test_dau_noi_app_luu_tin_nhan_va_cau_hinh(tmp_path):
    saved = []
    state = {"wsc_jig_persona": "ca_nhan"}
    config_path = tmp_path / "jig_alert_config.json"
    handled = handle_jig_chat_text(
        "thêm email to.truong@congty.local",
        conversation_id="CONV-01",
        locale="vi",
        session_state=state,
        save_user=lambda content: saved.append(("user", content)),
        save_assistant=lambda content: saved.append(("assistant", content)),
        config_path=config_path,
    )
    assert handled is True
    assert [role for role, _ in saved] == ["user", "assistant"]
    assert "Bảng cấu hình cảnh báo" in saved[1][1]
    assert config_path.exists()
    assert "to.truong@congty.local" in load_alert_config(config_path).nguoi_nhan


def test_dau_noi_app_bo_qua_cau_thuong(tmp_path):
    saved = []
    handled = handle_jig_chat_text(
        "Tóm tắt tài liệu này giúp tôi",
        conversation_id="CONV-01",
        locale="vi",
        session_state={},
        save_user=lambda content: saved.append(content),
        save_assistant=lambda content: saved.append(content),
        config_path=tmp_path / "khong_dung.json",
    )
    assert handled is False
    assert saved == []
