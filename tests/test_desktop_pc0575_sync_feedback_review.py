"""Unit and parity tests for DESKTOP-PC0575-SYNC-FEEDBACK-REVIEW on PC0575.

Verifies:
1. Manual count from PC0575 local_cases/answer_feedback.jsonl exactly matches summary.
2. Empty feedback store responds honestly without throwing errors.
3. Chat command classification correctly captures feedback commands and preserves ordinary RAG questions.
4. Summary response contains no retrieved document citations or leakage.
5. Chat app intent router end-to-end handling saves user and assistant messages properly.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import aios_habit.workspace_chat_app as app
import aios_habit.workspace_chat_store as store
from aios_habit import answer_feedback
from aios_habit.chat_intent_router import (
    HOI_TAI_LIEU,
    XEM_PHAN_HOI,
    classify_all_intents,
    classify_intent,
)
from aios_habit.feedback_review_home import format_feedback_review_summary


def test_pc0575_answer_feedback_manual_count_match():
    """Live local_cases/answer_feedback.jsonl on PC0575 matches summary output."""
    fb_file = answer_feedback.feedback_file()
    assert fb_file.exists(), f"File {fb_file} không tồn tại trên PC0575!"

    raw_records = []
    with fb_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                raw_records.append(json.loads(line))

    summary = format_feedback_review_summary()
    total = len(raw_records)
    good = sum(1 for r in raw_records if r.get("rating") == "huu_ich")
    bad = sum(1 for r in raw_records if r.get("rating") == "chua_huu_ich")

    if total == 0:
        assert "Chưa có phản hồi nào trong kho lưu cục bộ." in summary
    else:
        assert f"Tổng số phản hồi:** {total} lượt ({good} đạt / {bad} chê)" in summary
        rate_good = round(good / total * 100, 1)
        rate_bad = round(bad / total * 100, 1)
        assert f"{rate_good}% đạt · {rate_bad}% chê" in summary


def test_pc0575_empty_store_honest_response():
    """When feedback store is empty, format_feedback_review_summary answers honestly."""
    res = format_feedback_review_summary(records=[])
    assert "📊 Tóm tắt phản hồi đáp án" in res
    assert "Chưa có phản hồi nào trong kho lưu cục bộ." in res


def test_pc0575_chat_command_classification_and_rag_preservation():
    """Feedback commands route to XEM_PHAN_HOI while ordinary domain questions route to HOI_TAI_LIEU."""
    feedback_cmds = [
        "xem phản hồi",
        "xem lại phản hồi",
        "thống kê phản hồi",
        "/feedback",
        "/xemphanhoi",
    ]
    for cmd in feedback_cmds:
        assert classify_intent(cmd) == XEM_PHAN_HOI

    rag_queries = [
        "C23 và C24 có quy trình phản hồi thế nào?",
        "Lỗi phản hồi tín hiệu cảm biến C7620",
        "Quy trình xử lý phản hồi lỗi từ khách hàng",
    ]
    for q in rag_queries:
        assert classify_intent(q) == HOI_TAI_LIEU
        all_intents = [it for it, _ in classify_all_intents(q)]
        assert XEM_PHAN_HOI not in all_intents


def test_pc0575_no_retrieval_content_leakage():
    """Summary response does not contain retrieved document snippets or references."""
    summary = format_feedback_review_summary()
    assert "02XC_" not in summary
    assert "History KDTPS" not in summary
    assert "Nguồn: DB ca lỗi" not in summary


class MockSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


def test_pc0575_e2e_intent_handling(monkeypatch):
    """End-to-end chat intent handling executes and records messages."""
    import streamlit as st

    session_state = MockSessionState()
    monkeypatch.setattr(st, "session_state", session_state)
    saved = []
    monkeypatch.setattr(store, "save_message", lambda msg: saved.append(msg))
    conv = SimpleNamespace(id="CONV-PC0575-FB-TEST")

    handled = app._xu_ly_y_dinh_chat(
        "xem phản hồi",
        active_conversation=conv,
        active_nb_id="NB-DEFAULT",
    )
    assert handled is True
    assert len(saved) == 2
    assert saved[0].role == "user"
    assert saved[0].content == "xem phản hồi"
    assert saved[1].role == "assistant"
    assert "📊 Tóm tắt phản hồi đáp án" in saved[1].content
