"""Unit tests for Gemini Web proxy engine."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from aios_habit.gemini_web_engine import (
    clean_gemini_text,
    extract_response_text,
    generate_gemini_web_reply,
    MODELS_MAP,
)


def test_clean_gemini_text_removes_code_artifacts():
    dirty = "Đây là kết quả: ```python?code_reference&code_event_index=0\nx=1\n```\nChuẩn xác 100%."
    cleaned = clean_gemini_text(dirty)
    assert "code_reference" not in cleaned
    assert "Đây là kết quả:" in cleaned
    assert "Chuẩn xác 100%." in cleaned


def test_extract_response_text_success():
    inner_payload = [
        None,
        None,
        None,
        None,
        [
            [None, ["Câu trả lời hoàn chỉnh từ Gemini Web!"]],
        ],
    ]
    outer_chunk = json.dumps([None, None, json.dumps(inner_payload)])
    raw_stream = f'123\n)]\'\n[["wrb.fr",null,{json.dumps(json.dumps(inner_payload))}]]\n'

    text = extract_response_text(raw_stream)
    assert text == "Câu trả lời hoàn chỉnh từ Gemini Web!"


def test_extract_response_text_with_bard_error():
    raw_err = ")]}'\n[[\"wrb.fr\",null,null,null,null,null,null,null,null,null,\"BardErrorInfo [102]\"]]"
    with pytest.raises(RuntimeError) as exc:
        extract_response_text(raw_err)
    assert "BardErrorInfo [102]" in str(exc.value)


@patch("aios_habit.gemini_web_engine.gemini_stream_generate")
def test_generate_gemini_web_reply_success(mock_stream):
    inner_payload = [
        None,
        None,
        None,
        None,
        [
            [None, ["Cấu hình Baudrate RS232: 9600 8-N-1."]],
        ],
    ]
    mock_stream.return_value = f'[["wrb.fr",null,{json.dumps(json.dumps(inner_payload))}]]\n'

    res = generate_gemini_web_reply("Kiểm tra Baudrate", model_name="gemini-3.6-flash")
    assert res["ok"] is True
    assert "9600 8-N-1" in res["answer_text"]
    assert res["model"] == ""
    assert res["error"] == ""


@patch("aios_habit.gemini_web_engine.gemini_stream_generate")
def test_generate_gemini_web_reply_failure(mock_stream):
    mock_stream.side_effect = RuntimeError("Connection timeout to Gemini")

    res = generate_gemini_web_reply("Kiểm tra lỗi", model_name="gemini-3.6-flash")
    assert res["ok"] is False
    assert res["answer_text"] == ""
    assert "Connection timeout" in res["error"]
