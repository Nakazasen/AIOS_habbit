# -*- coding: utf-8 -*-
"""Test PC0575-specific display name for external AI mode according to user decision 12/10/2026.

Ticket context: DESKTOP-PC0575-SYNC-R3-GROUPB-CHECK
"""
from __future__ import annotations

import os
import pytest
from aios_habit.i18n import t, is_pc0575_environment


def test_pc0575_external_ai_mode_labels(monkeypatch):
    """Verify PC0575 profile returns user agreed naming from 12/10/2026."""
    monkeypatch.setenv("AIOS_EXTERNAL_AI_LABEL_PROFILE", "pc0575")
    assert is_pc0575_environment() is True

    assert t("mode_external_ai") == "Hỏi AI ngoài phạm vi kho kiến thức"
    assert t("mode_pick_external") == "🌐 Hỏi AI ngoài phạm vi kho kiến thức"
    assert t("external_ai_provenance_banner") == "Câu trả lời ngoài phạm vi kho kiến thức — không dựa trên dữ kiện trong kho. Kiểm chứng trước khi dùng."
    assert t("bridge_ask_external_button") == "Hỏi AI ngoài phạm vi kho kiến thức câu này"


def test_home_external_ai_mode_labels(monkeypatch):
    """Verify home profile keeps original concise naming."""
    monkeypatch.setenv("AIOS_EXTERNAL_AI_LABEL_PROFILE", "home")
    assert is_pc0575_environment() is False

    assert t("mode_external_ai") == "Hỏi AI ngoài"
    assert t("mode_pick_external") == "🌐 Hỏi AI ngoài"
    assert t("external_ai_provenance_banner") == "Trả lời bởi AI bên ngoài — không dựa trên dữ kiện trong kho. Kiểm chứng trước khi dùng."
    assert t("bridge_ask_external_button") == "Hỏi AI ngoài câu này"
