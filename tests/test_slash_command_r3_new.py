# -*- coding: utf-8 -*-
"""Unit tests for newly wired slash commands /phongvan, /thongke, /trangthai (DESKTOP-HOME-SLASH-CATALOG-R3)."""

from __future__ import annotations

import pytest

from aios_habit.chat_action import ChatActionRequest
from aios_habit.chat_action_expert_interview import handle_interview
from aios_habit.chat_action_health import handle_health_status
from aios_habit.chat_action_statistics import handle_stats_command
from aios_habit.chat_intent_router import (
    PHONG_VAN_CHUYEN_GIA,
    THONG_KE_HE_THONG,
    TRANG_THAI_HE_THONG,
    classify_intent,
)
from aios_habit.slash_command_catalog import get_command_catalog


def test_r3_commands_in_catalog() -> None:
    cat = {item["command"]: item for item in get_command_catalog()}
    for cmd in ("/phongvan", "/thongke", "/trangthai"):
        assert cmd in cat, f"Lệnh {cmd} phải có mặt trong catalog!"
        entry = cat[cmd]
        assert entry.get("description"), f"Thiếu description cho {cmd}"
        assert entry.get("description_ja"), f"Thiếu description_ja cho {cmd}"
        assert entry.get("description_zh"), f"Thiếu description_zh cho {cmd}"
        assert entry.get("category"), f"Thiếu category cho {cmd}"
        assert len(entry.get("aliases", [])) >= 2, f"Phải có ít nhất 2 aliases cho {cmd}"


def test_r3_router_classification() -> None:
    # 1. /phongvan
    assert classify_intent("/phongvan") == PHONG_VAN_CHUYEN_GIA
    assert classify_intent("/phong-van") == PHONG_VAN_CHUYEN_GIA
    assert classify_intent("/インタビュー") == PHONG_VAN_CHUYEN_GIA
    assert classify_intent("/专家访谈") == PHONG_VAN_CHUYEN_GIA
    assert classify_intent("bắt đầu phỏng vấn chuyên gia") == PHONG_VAN_CHUYEN_GIA
    assert classify_intent("chạy phỏng vấn chuyên gia") == PHONG_VAN_CHUYEN_GIA

    # 2. /thongke
    assert classify_intent("/thongke") == THONG_KE_HE_THONG
    assert classify_intent("/thong-ke") == THONG_KE_HE_THONG
    assert classify_intent("/統計") == THONG_KE_HE_THONG
    assert classify_intent("/统计") == THONG_KE_HE_THONG
    assert classify_intent("thống kê vận hành") == THONG_KE_HE_THONG
    assert classify_intent("báo cáo thống kê") == THONG_KE_HE_THONG

    # 3. /trangthai
    assert classify_intent("/trangthai") == TRANG_THAI_HE_THONG
    assert classify_intent("/trang-thai") == TRANG_THAI_HE_THONG
    assert classify_intent("/ステータス") == TRANG_THAI_HE_THONG
    assert classify_intent("/状态") == TRANG_THAI_HE_THONG
    assert classify_intent("kiểm tra trạng thái hệ thống") == TRANG_THAI_HE_THONG
    assert classify_intent("sức khỏe dịch vụ") == TRANG_THAI_HE_THONG


def test_r3_handlers_execution() -> None:
    req = ChatActionRequest(
        question="/thongke",
        locale="vi",
        conversation_id="TEST-CONV-R3",
        notebook_id="default",
        workspace_id="default",
    )

    # 1. Thống kê
    out_stats = handle_stats_command(req)
    assert out_stats is not None
    assert len(out_stats.blocks) >= 2
    assert "thống kê" in out_stats.title.lower()

    # 2. Sức khỏe
    out_health = handle_health_status(req)
    assert out_health is not None
    assert len(out_health.blocks) >= 2
    assert "sức khỏe" in out_health.title.lower() or "trạng thái" in out_health.title.lower()

    # 3. Phỏng vấn chuyên gia
    out_interview = handle_interview(req)
    assert out_interview is not None
    assert "phỏng vấn" in out_interview.title.lower()
