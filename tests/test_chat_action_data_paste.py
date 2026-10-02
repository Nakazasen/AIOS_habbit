"""Tests cho chat_action_data_paste (UX-CHAT-CORE): dan log/CSV -> phan tich + ve."""

import pytest

from aios_habit import chat_action
from aios_habit.chat_action import BLOCK_CHART, BLOCK_TABLE, ChatActionRequest
from aios_habit.chat_action_data_paste import (
    _describe_numeric,
    _draw_line_chart,
    _looks_like_csv,
    _looks_like_log,
    _numeric_columns,
    _parse_csv_block,
    extract_pasted_block,
)


@pytest.fixture(autouse=True)
def _clean_state():
    chat_action.reset_actions()
    yield
    chat_action.reset_actions()


CSV_SAMPLE = """thoi_gian,nhiet_do,ap_suat
10:00,36.5,101.2
10:05,37.1,100.8
10:10,38.0,100.1
"""

LOG_SAMPLE = """2026-10-01 10:00:01 INFO he thong khoi dong
2026-10-01 10:00:02 ERROR cam bien nhiet do mat ket noi
2026-10-01 10:00:03 WARNING nhiet do vuot nguong
2026-10-01 10:00:04 INFO thu ket noi lai
"""


def test_looks_like_csv_detects_consistent_delimiters():
    assert _looks_like_csv(CSV_SAMPLE.splitlines()) is True
    assert _looks_like_csv(["chi mot dong, khong du"]) is False
    assert _looks_like_csv(["cau hoi binh thuong khong co bang"]) is False


def test_looks_like_log_detects_timestamps():
    assert _looks_like_log(LOG_SAMPLE.splitlines()) is True
    assert _looks_like_log(["dong mot", "dong hai"]) is False


def test_extract_pasted_block_returns_none_for_plain_question():
    assert extract_pasted_block("hom nay troi dep qua") is None


def test_parse_csv_block_headers_and_rows():
    headers, data = _parse_csv_block(CSV_SAMPLE)
    assert headers == ["thoi_gian", "nhiet_do", "ap_suat"]
    assert len(data) == 3


def test_numeric_columns_detection():
    headers, data = _parse_csv_block(CSV_SAMPLE)
    numeric = _numeric_columns(headers, data)
    assert 1 in numeric and 2 in numeric
    assert 0 not in numeric


def test_describe_numeric_stats():
    text = _describe_numeric([1.0, 2.0, 3.0])
    assert "min: 1" in text and "max: 3" in text and "trung bình: 2" in text


def test_draw_line_chart_returns_png_bytes():
    headers, data = _parse_csv_block(CSV_SAMPLE)
    png = _draw_line_chart(headers, data, [1, 2])
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(png) > 1000


def test_action_matches_pasted_csv_without_command():
    chat_action.load_builtin_actions()
    request = ChatActionRequest(question="giup toi voi\n" + CSV_SAMPLE)
    hits = chat_action.match_all_actions(request)
    assert any(h.name == "phan_tich_du_lieu_dan" for h in hits)


def test_action_matches_log_paste():
    chat_action.load_builtin_actions()
    request = ChatActionRequest(question=LOG_SAMPLE)
    hits = chat_action.match_all_actions(request)
    assert any(h.name == "phan_tich_du_lieu_dan" for h in hits)


def test_csv_handler_returns_summary_table_and_chart():
    chat_action.load_builtin_actions()
    outcome = chat_action.dispatch_multi(ChatActionRequest(question=CSV_SAMPLE))
    assert outcome is not None
    kinds = [block.kind for block in outcome.blocks]
    assert BLOCK_TABLE in kinds
    assert BLOCK_CHART in kinds
    assert outcome.action == "phan_tich_du_lieu_dan"


def test_chart_caption_is_honest_not_simulated():
    chat_action.load_builtin_actions()
    outcome = chat_action.dispatch_multi(ChatActionRequest(question=CSV_SAMPLE))
    text = chat_action.render_outcome(outcome)
    assert "MÔ PHỎNG" not in text
    assert "dữ liệu bạn vừa dán" in text


def test_log_handler_counts_and_lists_suspicious_lines():
    chat_action.load_builtin_actions()
    outcome = chat_action.dispatch_multi(ChatActionRequest(question=LOG_SAMPLE))
    assert outcome is not None
    text = chat_action.render_outcome(outcome)
    assert "Dòng nghi có lỗi/cảnh báo: 2" in text


def test_multi_intent_paste_plus_another_action():
    chat_action.load_builtin_actions()
    question = "vẽ biểu đồ giúp tôi\n" + CSV_SAMPLE
    outcome = chat_action.dispatch_multi(ChatActionRequest(question=question))
    assert outcome is not None
    # Ca dan du lieu phai co mat trong cau tra loi gop.
    assert "phan_tich_du_lieu_dan" in outcome.action
