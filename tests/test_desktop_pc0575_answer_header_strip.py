"""Tests for ticket DESKTOP-PC0575-ANSWER-HEADER-STRIP:
Stripping leaked system instruction JSON headers at the beginning of assistant
message content in workspace answer display layer without modifying stored data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

from aios_habit.workspace_chat_models import ChatMessage
from aios_habit.workspace_chat_ui import (
    render_chat_bubble,
    strip_instruction_header,
)


class MockSessionState(dict):
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class MockStreamlit:
    """Mock Streamlit environment capturing rendering calls."""

    def __init__(self) -> None:
        self.calls: List[tuple] = []
        self.session_state = MockSessionState()
        self.widget_states: Dict[str, Any] = {}

    def markdown(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("markdown", str(text)))

    def write(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("write", str(text)))

    def info(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("info", str(text)))

    def caption(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("caption", str(text)))

    def warning(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("warning", str(text)))

    def error(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("error", str(text)))

    def success(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("success", str(text)))

    def html(self, text: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("html", str(text)))

    def feedback(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(("feedback", args, kwargs))
        return None

    def button(self, label: str, key: Optional[str] = None, *args: Any, **kwargs: Any) -> bool:
        self.calls.append(("button", str(label), key))
        return bool(self.widget_states.get(key, False)) if key else False

    def download_button(self, label: str, *args: Any, **kwargs: Any) -> bool:
        self.calls.append(("download_button", str(label)))
        return False

    def columns(self, spec: Any, *args: Any, **kwargs: Any) -> List[Any]:
        class MockColumn:
            def __enter__(self) -> MockColumn:
                return self

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                pass

        count = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        return [MockColumn() for _ in range(count)]

    def chat_message(self, role: str) -> Any:
        class MockChatMessage:
            def __enter__(self) -> MockChatMessage:
                return self

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                pass

        return MockChatMessage()


@pytest.fixture
def mock_st_env():
    env = MockStreamlit()
    with patch("aios_habit.workspace_chat_ui.st", env):
        yield env


# ============================================================================
# 1. UNIT TESTS: POSITIVE CASES (Instruction Header Stripping)
# ============================================================================


def test_strip_instruction_header_real_case_msg_308ce36b() -> None:
    """Verify strip_instruction_header on exact MSG-308CE36B from messages.jsonl."""
    msg_path = Path("local_cases/workspace_chat/messages.jsonl")
    assert msg_path.exists(), "messages.jsonl must exist to verify real case"

    target_content: Optional[str] = None
    with msg_path.open("r", encoding="utf-8") as f:
        for line in f:
            if "MSG-308CE36B" in line:
                data = json.loads(line)
                target_content = data.get("content")
                break

    assert target_content is not None, "MSG-308CE36B must be present in messages.jsonl"
    assert target_content.startswith('{\n  "summary": "Cần thêm thông tin"')

    cleaned = strip_instruction_header(target_content)

    # 1. Header JSON is removed
    assert not cleaned.startswith("{")
    assert '"summary"' not in cleaned[:100]
    assert '"changes"' not in cleaned[:100]
    assert '"tests"' not in cleaned[:100]

    # 2. Main answer body is 100% intact
    expected_start = "Tôi hiểu bạn đang hỏi về mối liên hệ giữa hiện tượng đai đen trong hình ảnh và đường kính BEAM trong hệ thống LSU."
    assert cleaned.startswith(expected_start)
    assert "**Trường hợp hiển thị lý tưởng (chuẩn):**" in cleaned
    assert "Đây là câu trả lời do AI tạo, cần kiểm tra lại trước khi dùng." in cleaned


def test_strip_instruction_header_compact_single_line() -> None:
    raw = '{"summary": "OK", "changes": [], "tests": []}\n\nNội dung câu trả lời.'
    cleaned = strip_instruction_header(raw)
    assert cleaned == "Nội dung câu trả lời."


def test_strip_instruction_header_with_leading_whitespace_and_newlines() -> None:
    raw = '  \n\n  {\n  "summary": "info",\n  "changes": [],\n  "tests": []\n}\n\nPhân tích lỗi LSU.'
    cleaned = strip_instruction_header(raw)
    assert cleaned == "Phân tích lỗi LSU."


def test_strip_instruction_header_subset_keys() -> None:
    raw1 = '{"summary": "abc", "changes": []}\n\nChi tiết.'
    assert strip_instruction_header(raw1) == "Chi tiết."

    raw2 = '{"summary": "abc", "tests": []}\n\nChi tiết.'
    assert strip_instruction_header(raw2) == "Chi tiết."

    raw3 = '{"changes": [], "tests": []}\n\nChi tiết.'
    assert strip_instruction_header(raw3) == "Chi tiết."


def test_strip_instruction_header_only_header_returns_empty() -> None:
    raw = '{"summary": "Chỉ có chỉ dẫn", "changes": [], "tests": []}'
    assert strip_instruction_header(raw) == ""


def test_strip_instruction_header_none_or_empty() -> None:
    assert strip_instruction_header("") == ""
    assert strip_instruction_header(None) == ""


# ============================================================================
# 2. UNIT TESTS: NEGATIVE CASES (Preserve Valid Content)
# ============================================================================


def test_negative_starts_with_plain_curly_brace() -> None:
    raw = "{x, y, z} là tập hợp các điểm trong không gian ba chiều."
    assert strip_instruction_header(raw) == raw


def test_negative_starts_with_math_set() -> None:
    raw = "{1, 2, 3, 4} là tập hợp số tự nhiên."
    assert strip_instruction_header(raw) == raw


def test_negative_starts_with_other_valid_json() -> None:
    raw = '{\n  "host": "localhost",\n  "port": 8080,\n  "debug": true\n}\nĐây là cấu hình mẫu.'
    assert strip_instruction_header(raw) == raw


def test_negative_starts_with_json_having_only_summary() -> None:
    raw = '{\n  "summary": "Báo cáo doanh số tháng 10",\n  "revenue": 5000000\n}'
    assert strip_instruction_header(raw) == raw


def test_negative_json_code_block() -> None:
    raw = '```json\n{\n  "summary": "Cần thêm thông tin",\n  "changes": [],\n  "tests": []\n}\n```\nĐây là code block mẫu.'
    assert strip_instruction_header(raw) == raw


def test_negative_json_in_body_not_start() -> None:
    raw = 'Dưới đây là mẫu chỉ dẫn:\n\n{\n  "summary": "Cần thêm thông tin",\n  "changes": [],\n  "tests": []\n}\n\nVui lòng xem xét.'
    assert strip_instruction_header(raw) == raw


def test_negative_indented_json() -> None:
    raw = '- Ví dụ:\n  {\n    "summary": "test",\n    "changes": [],\n    "tests": []\n  }'
    assert strip_instruction_header(raw) == raw


# ============================================================================
# 3. INTEGRATION TESTS: render_chat_bubble Display Layer
# ============================================================================


def test_render_chat_bubble_strips_header_interactive_mode(mock_st_env: MockStreamlit) -> None:
    raw = '{\n  "summary": "Cần thêm thông tin",\n  "changes": [],\n  "tests": []\n}\n\nĐây là câu trả lời trợ lý đầy đủ.'
    msg = ChatMessage(
        id="msg_test_001",
        conversation_id="conv_test",
        role="assistant",
        content=raw,
        trace_id=None,
    )

    render_chat_bubble(
        msg,
        is_latest=True,
        locale="vi",
        conversation_id="conv_test",
        feedback_question="Câu hỏi?",
        render_interactive=True,
    )

    markdown_calls = [c[1] for c in mock_st_env.calls if c[0] == "markdown"]
    assert len(markdown_calls) >= 1
    rendered_text = markdown_calls[0]

    # JSON header is completely absent
    assert '{"summary"' not in rendered_text
    assert '"changes"' not in rendered_text
    assert '"tests"' not in rendered_text

    # Main content is properly displayed
    assert rendered_text == "Đây là câu trả lời trợ lý đầy đủ."


def test_render_chat_bubble_strips_header_non_interactive_mode(mock_st_env: MockStreamlit) -> None:
    raw = '{\n  "summary": "Cần thêm thông tin",\n  "changes": [],\n  "tests": []\n}\n\nĐây là câu trả lời cũ không có nút.'
    msg = ChatMessage(
        id="msg_test_002",
        conversation_id="conv_test",
        role="assistant",
        content=raw,
        trace_id=None,
    )

    render_chat_bubble(
        msg,
        is_latest=False,
        locale="vi",
        conversation_id="conv_test",
        feedback_question="Câu hỏi cũ?",
        render_interactive=False,
    )

    markdown_calls = [c[1] for c in mock_st_env.calls if c[0] == "markdown"]
    assert len(markdown_calls) == 1
    rendered_text = markdown_calls[0]

    assert '{"summary"' not in rendered_text
    assert rendered_text == "Đây là câu trả lời cũ không có nút."


def test_render_chat_bubble_preserves_valid_curly_brace(mock_st_env: MockStreamlit) -> None:
    raw = "{x, y, z} là hệ trục toạ độ Descarte."
    msg = ChatMessage(
        id="msg_test_003",
        conversation_id="conv_test",
        role="assistant",
        content=raw,
        trace_id=None,
    )

    render_chat_bubble(
        msg,
        is_latest=False,
        locale="vi",
        conversation_id="conv_test",
        render_interactive=False,
    )

    markdown_calls = [c[1] for c in mock_st_env.calls if c[0] == "markdown"]
    assert len(markdown_calls) == 1
    assert markdown_calls[0] == raw
