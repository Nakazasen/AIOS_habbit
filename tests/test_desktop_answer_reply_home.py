"""Unit tests for DESKTOP-ANSWER-REPLY-HOME: per-answer reply with anchored context.

Covers:
1. ChatMessage model and serialization round-trip with reply_to_message_id.
2. i18n translation keys parity across vi, ja, zh-CN.
3. build_workspace_ai_prompt with anchored_context injection.
4. WorkspaceAIAnswerRequest dataclass fields.
5. render_answer_feedback_row "Trả lời" action interaction.
6. workspace_chat_router_adapter prompt construction with anchored_context.
"""

from unittest.mock import MagicMock, patch
import pytest

from aios_habit.workspace_chat_models import ChatMessage
from aios_habit.workspace_chat_store import _deserialize_message
from aios_habit.i18n import t, TRANSLATIONS
from aios_habit.workspace_chat_ai_answer import (
    WorkspaceAIAnswerRequest,
    WorkspaceAIContextSource,
    build_workspace_ai_prompt,
)
from aios_habit.workspace_chat_ui import render_answer_feedback_row
from aios_habit.workspace_chat_router_adapter import (
    _build_router_prompts,
    SanitizedRouterPayload,
)


class TestChatMessageReplyToModel:
    def test_chat_message_reply_to_message_id_defaults_to_none(self):
        msg = ChatMessage(id="MSG-1", conversation_id="conv-1", role="user", content="Hello")
        assert msg.reply_to_message_id is None

    def test_chat_message_with_reply_to_message_id(self):
        msg = ChatMessage(
            id="MSG-2",
            conversation_id="conv-1",
            role="user",
            content="Mục 2 xử lý thế nào?",
            reply_to_message_id="MSG-ANSWER-1",
        )
        assert msg.reply_to_message_id == "MSG-ANSWER-1"

    def test_serialization_and_deserialization_roundtrip(self):
        msg = ChatMessage(
            id="MSG-3",
            conversation_id="conv-1",
            role="user",
            content="Chi tiết mục này?",
            reply_to_message_id="MSG-PARENT-99",
        )
        record = msg.to_dict()
        assert record["reply_to_message_id"] == "MSG-PARENT-99"

        deserialized = _deserialize_message(record)
        assert deserialized.id == msg.id
        assert deserialized.reply_to_message_id == "MSG-PARENT-99"
        assert deserialized.content == msg.content

    def test_deserialization_backward_compatibility_when_field_missing(self):
        old_record = {
            "id": "MSG-OLD",
            "conversation_id": "conv-1",
            "role": "assistant",
            "content": "Old answer",
            "created_at": "2026-10-10T00:00:00Z",
            "model_version": "v1",
        }
        msg = _deserialize_message(old_record)
        assert msg.reply_to_message_id is None


class TestAnswerReplyI18nKeys:
    REQUIRED_KEYS = [
        "answer_reply_action",
        "answer_reply_help",
        "anchored_answer_prefix",
        "remove_anchor_button",
        "remove_anchor_tooltip",
    ]

    @pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
    def test_required_reply_keys_exist_and_non_empty(self, locale):
        for key in self.REQUIRED_KEYS:
            val = t(key, locale=locale)
            assert val is not None and len(val.strip()) > 0, f"Key '{key}' is missing or empty for locale '{locale}'"


class TestAnchoredPromptBuilding:
    def test_build_workspace_ai_prompt_injects_anchored_context(self):
        src = WorkspaceAIContextSource(
            source_id="s1",
            source_scope="temporary",
            source_type="file",
            title="Doc 1",
            privacy_label="local_only",
            text="1. Khởi động\n2. Đo áp suất\n3. Đóng nắp",
            included_chars=100,
        )
        sys_p, user_p = build_workspace_ai_prompt(
            question="Mục số 2 xử lý như thế nào?",
            context_sources=(src,),
            anchored_context="1. Khởi động\n2. Đo áp suất\n3. Đóng nắp",
        )
        assert "--- ĐÁP ÁN ĐƯỢC NEO NGỮ CẢNH (ƯU TIÊN HÀNG ĐẦU) ---" in user_p
        assert "Đo áp suất" in user_p
        assert "ƯU TIÊN HÀNG ĐẦU" in user_p

    def test_build_workspace_ai_prompt_without_anchored_context(self):
        src = WorkspaceAIContextSource(
            source_id="s1",
            source_scope="temporary",
            source_type="file",
            title="Doc 1",
            privacy_label="local_only",
            text="Khởi động máy",
            included_chars=50,
        )
        sys_p, user_p = build_workspace_ai_prompt(
            question="Khởi động máy thế nào?",
            context_sources=(src,),
            anchored_context=None,
        )
        assert "--- ĐÁP ÁN ĐƯỢC NEO NGỮ CẢNH" not in user_p


class TestRouterAdapterAnchoredPrompts:
    def test_router_prompts_include_anchored_context(self):
        payload = SanitizedRouterPayload(
            sanitized_question="Mục này xử lý ra sao?",
            sanitized_sources=(),
            metadata={
                "ai_mode": "external",
                "anchored_context": "Đáp án trước nói về giải pháp cân bằng tải.",
            },
        )
        system_p, user_p = _build_router_prompts(payload)
        assert "--- ĐÁP ÁN ĐƯỢC NEO NGỮ CẢNH (ƯU TIÊN HÀNG ĐẦU) ---" in user_p
        assert "giải pháp cân bằng tải" in user_p


class TestRenderAnswerFeedbackRowReplyAction:
    def test_reply_button_sets_session_state(self):
        mock_st = MagicMock()
        mock_st.session_state = {}
        mock_st.rerun = MagicMock()

        def fake_button(label, key=None, **kwargs):
            if "wsc_reply_btn_" in str(key):
                return True
            return False

        mock_st.button = fake_button
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col1.button = fake_button
        mock_col2.button = MagicMock(return_value=False)
        mock_st.columns.return_value = [mock_col1, mock_col2]

        with patch("aios_habit.workspace_chat_ui.st", mock_st):
            render_answer_feedback_row(
                message_id="MSG-ANS-123",
                conversation_id="CONV-TEST",
                question="Quy trình bảo dưỡng gồm những gì?",
                answer="1. Kiểm tra dầu 2. Thay lọc gió 3. Siết ốc",
                locale="vi",
            )
            assert mock_st.rerun.called
            anchor_val = mock_st.session_state.get("wsc_anchored_answer_CONV-TEST")
            assert anchor_val is not None
            assert anchor_val["message_id"] == "MSG-ANS-123"
            assert anchor_val["question"] == "Quy trình bảo dưỡng gồm những gì?"
            assert "Kiểm tra dầu" in anchor_val["content"]
