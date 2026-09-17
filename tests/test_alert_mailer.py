"""Contract tests for alert mailer with Monozukuri chart (US12 T061)."""

from __future__ import annotations

import pytest

from aios_habit.production_prediction.alert_mailer import (
    AlertCooldownTracker,
    AlertMailProposal,
    build_alert_email,
    build_proposal_card,
    should_send,
)


def test_tao_email_html_tieng_viet_kem_anh_inline(tmp_path):
    from PIL import Image

    png_path = tmp_path / "mini.png"
    Image.new("RGB", (8, 8), "white").save(png_path, format="PNG")
    png_bytes = png_path.read_bytes()
    proposal = AlertMailProposal(
        tieu_de="Cảnh báo xu hướng JIG BOWSKEW",
        tom_tat="Giá trị bowskew đang trôi gần ngưỡng trên.",
        nguoi_nhan=["to.truong@congty.local"],
        ma_duyet="DUYET-001",
    )
    msg = build_alert_email(proposal, anh_png_bytes=png_bytes, bao_cao_markdown="# Báo cáo")
    raw = msg.as_string()
    assert "to.truong@congty.local" in raw
    assert "Cảnh báo" in proposal.tieu_de
    assert "bieudoxu_huong" in raw


def test_tu_choi_nguoi_nhan_khong_hop_le():
    proposal = AlertMailProposal(tieu_de="Cảnh báo", tom_tat="Tóm tắt", nguoi_nhan=["khong-phai-email"])
    with pytest.raises(ValueError, match="người nhận"):
        build_alert_email(proposal)


def test_the_duyet_truoc_khi_gui():
    card = build_proposal_card("Cảnh báo", "Tóm tắt", ["a@congty.local"], "DUYET-002")
    assert card["loai_the"] == "de_xuat_email"
    assert "Gửi" in str(card["huong_dan"])


def test_chong_spam_bang_cooldown():
    assert should_send(1000.0, None, 1800) is True
    assert should_send(1000.0, 900.0, 1800) is False
    assert should_send(3000.0, 900.0, 1800) is True


def test_bo_theo_doi_cooldown_theo_khoa():
    tracker = AlertCooldownTracker(cooldown_seconds=600)
    assert tracker.duoc_phep_gui("JIG-01", now_ts=1000.0) is True
    tracker.danh_dau_da_gui("JIG-01", now_ts=1000.0)
    assert tracker.duoc_phep_gui("JIG-01", now_ts=1200.0) is False
    assert tracker.duoc_phep_gui("JIG-01", now_ts=2000.0) is True
