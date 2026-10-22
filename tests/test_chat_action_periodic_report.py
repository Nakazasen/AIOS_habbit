# -*- coding: utf-8 -*-
"""Tests cho điểm vào Báo cáo xu hướng định kỳ trên chat_action & chat_intent_router (DESKTOP-HOME-STEP4-PERIODIC-REPORT-ACCEPTANCE)."""

from __future__ import annotations

import pytest

from aios_habit.chat_action import (
    ChatActionRequest,
    dispatch_multi,
    load_builtin_actions,
    match_action,
    reset_actions,
)
from aios_habit.chat_intent_router import (
    BAO_CAO_XU_HUONG,
    classify_all_intents,
    nhan_y_dinh,
)


def test_chat_intent_router_classifies_periodic_report():
    """Kiểm tra router nhận diện chính xác ý định sinh báo cáo xu hướng định kỳ."""
    queries = [
        "báo cáo xu hướng định kỳ",
        "sinh báo cáo xu hướng định kỳ",
        "báo cáo xu hướng tuần",
        "báo cáo định kỳ tuần 2026-W34",
        "xuất báo cáo xu hướng định kỳ",
        "/baocaoxuhuong",
    ]
    for q in queries:
        intents = classify_all_intents(q)
        assert len(intents) >= 1
        assert intents[0][0] == BAO_CAO_XU_HUONG, f"Failed for query: {q}"


def test_chat_action_periodic_report_registered_and_dispatches():
    """Kiểm tra ChatAction 'bao_cao_xu_huong_dinh_ky' được nạp tự động và xử lý câu lệnh."""
    reset_actions()
    load_builtin_actions()

    # 1. Tuần mặc định (mới nhất)
    req = ChatActionRequest(question="sinh báo cáo xu hướng định kỳ")
    matched = match_action(req)
    assert matched is not None
    assert matched.name == "bao_cao_xu_huong_dinh_ky"

    outcome = dispatch_multi(req)
    assert outcome is not None
    assert outcome.action == "bao_cao_xu_huong_dinh_ky"
    assert "Báo cáo xu hướng định kỳ" in outcome.title
    assert len(outcome.blocks) >= 1
    assert "BÁO CÁO XU HƯỚNG LỖI ĐỊNH KỲ" in outcome.blocks[0].text
    assert "BẢNG TỈ LỆ PHÁT SINH THEO 5 CHIỀU" in outcome.blocks[0].text


def test_chat_action_periodic_report_with_target_week():
    """Kiểm tra ChatAction với tuần chỉ định cụ thể (2026-W34)."""
    reset_actions()
    load_builtin_actions()

    req = ChatActionRequest(question="báo cáo định kỳ tuần 2026-W34")
    outcome = dispatch_multi(req)
    assert outcome is not None
    assert "2026-W34" in outcome.blocks[0].text
    assert "35,139" in outcome.blocks[0].text  # 35,139 bản ghi tuần 2026-W34
