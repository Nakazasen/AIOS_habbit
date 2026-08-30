# -*- coding: utf-8 -*-
"""Comprehensive Unit & Integration Test Suite for Workspace Chat UI & i18n Subsystem (Milestone 4).

Validates:
1. Conversation Model & Store Locale Persistence:
   - Default locales (`ui_locale="vi"`, `answer_language="vi"`).
   - Strict locale normalization on model initialization.
   - Backward-compatibility with legacy records missing locale fields.
   - Store updates via `update_conversation_language_settings` (partial & full).
   - Context compression locale inheritance.

2. UI Localized Labels & Key Completeness:
   - `get_localized_labels` across `vi`, `ja`, `zh-CN` with safe fallback to `vi`.
   - Backward-compatible `get_vietnamese_labels()` key coverage parity.
   - Complete coverage of Evidence Graph terminology in all 3 languages.

3. UI Language Selector Component:
   - Dropdown rendering for interface language & AI answer language.
   - Format functions displaying friendly names + language codes.
   - State change callbacks (`on_ui_locale_change`, `on_answer_language_change`, `on_change`).
   - Resilient fallback for invalid initial locale selections.

4. AI Prompt Construction & Language Injection:
   - Explicit language instruction injection for `vi`, `ja`, `zh-CN`.
   - Verbatim evidence preservation (citations `[1]`, `[E1]`, `EVD-001`, filenames, paths, error codes, snippets).
   - Localized prompt section headers (`CÂU HỎI:`, `質問:`, `问题:`, `NGUỒN 1`, `ソース 1`, `来源 1`).
   - Localized chat history role labels (`[Người dùng]`, `[ユーザー]`, `[用户]`, etc.).

5. Outcome Classification with Multilingual Limitation Markers:
   - Vietnamese limitation detection (`chua du thong tin`, `khong du bang chung`, `thieu thong tin`).
   - Japanese limitation detection (`十分な証拠がありません`, `情報が不足`, `証拠不足`).
   - Simplified Chinese limitation detection (`证据不足`, `信息不足`, `根据现有证据`).
   - Multilingual negation handling (e.g. `khong phai la khong du`, `十分な証拠がないわけではない`, `并非证据不足`).
   - Provider failure & insufficient evidence branching.

6. AI Answer Generation & Localized Disclaimers:
   - Localized disclaimer banner appending for `vi`, `ja`, `zh-CN`.
   - Propagation of `answer_language` through `WorkspaceAIAnswerRequest` to prompt composer and provider.

7. UTF-8 & Anti-Mojibake Guarantees:
   - End-to-end multi-byte character persistence in JSONL store for Vietnamese diacritics,
     Japanese Kanji/Kana, and Simplified Chinese Hanzi.
"""
from __future__ import annotations

import ast
import json
import re
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

import aios_habit.workspace_chat_store as chat_store
from aios_habit.i18n import (
    DEFAULT_LOCALE,
    LOCALE_NAMES,
    SUPPORTED_LOCALES,
    TRANSLATIONS,
    get_ai_language_instruction,
    get_supported_locales,
    normalize_locale,
    t,
)
from aios_habit.workspace_chat_ai_answer import (
    MAX_QUESTION_CHARS,
    PRIVACY_MODE_CLOUD_ALLOWED,
    PRIVACY_MODE_LOCAL_PREVIEW_ONLY,
    WorkspaceAIAnswerRequest,
    WorkspaceAIAnswerResult,
    WorkspaceAIContextSource,
    _get_ai_disclaimer,
    build_workspace_ai_prompt,
    classify_workspace_ai_outcome,
    generate_workspace_ai_answer,
)
from aios_habit.workspace_chat_models import (
    ChatMessage,
    ConversationSourceSelection,
    DocumentNotebook,
    NotebookSource,
    TemporaryConversationSource,
    WorkspaceConversation,
)
from aios_habit.workspace_chat_ui import (
    get_localized_labels,
    get_vietnamese_labels,
    render_language_selector,
)


# ---------------------------------------------------------------------------
# Test Fixtures & Setup
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_isolated_chat_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate chat store storage in a temporary directory for each test."""
    test_dir = tmp_path / "workspace_chat_test"
    monkeypatch.setattr(chat_store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(chat_store, "NOTEBOOKS_FILE", test_dir / "notebooks.jsonl")
    monkeypatch.setattr(chat_store, "COLLECTIONS_FILE", test_dir / "collections.jsonl")
    monkeypatch.setattr(chat_store, "CONVERSATIONS_FILE", test_dir / "conversations.jsonl")
    monkeypatch.setattr(chat_store, "MESSAGES_FILE", test_dir / "messages.jsonl")
    monkeypatch.setattr(chat_store, "TEMPORARY_SOURCES_FILE", test_dir / "temporary_sources.jsonl")
    monkeypatch.setattr(chat_store, "NOTEBOOK_SOURCES_FILE", test_dir / "notebook_sources.jsonl")
    monkeypatch.setattr(chat_store, "SOURCE_SELECTIONS_FILE", test_dir / "conversation_source_selections.jsonl")
    chat_store.init_chat_store()


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard against unintended network calls during test execution."""
    def fail_socket(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Forbidden network socket call during unit test execution")
    monkeypatch.setattr(socket, "socket", fail_socket)


class MockAIProvider:
    """Mock AI provider capturing system & user prompts and returning configurable responses."""

    def __init__(self, response_text: str = "Câu trả lời mẫu từ AI.", raise_error: bool = False) -> None:
        self.response_text = response_text
        self.raise_error = raise_error
        self.call_count = 0
        self.last_system_prompt: Optional[str] = None
        self.last_user_prompt: Optional[str] = None

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        if self.raise_error:
            raise RuntimeError("Simulated AI Provider connection error")
        return self.response_text


# ===========================================================================
# 1. Conversation Model & Store Locale Persistence
# ===========================================================================

class TestConversationModelAndStoreLocale:
    """Tests for WorkspaceConversation locale fields, serialization, and store persistence."""

    def test_conversation_model_locale_defaults(self) -> None:
        """Verify default ui_locale and answer_language are 'vi'."""
        conv = WorkspaceConversation(
            id="conv_def_01",
            notebook_id="mom_opcenter",
            title="Cuộc trò chuyện mặc định",
        )
        assert conv.ui_locale == "vi"
        assert conv.answer_language == "vi"

    def test_conversation_model_locale_normalization(self) -> None:
        """Verify locale variations normalize properly on conversation construction."""
        # Japanese variations
        conv_ja = WorkspaceConversation(
            id="conv_ja",
            notebook_id="mom_opcenter",
            title="Japanese Conv",
            ui_locale="ja-JP",
            answer_language="JAPANESE",
        )
        assert conv_ja.ui_locale == "ja"
        assert conv_ja.answer_language == "ja"

        # Simplified Chinese variations
        conv_zh = WorkspaceConversation(
            id="conv_zh",
            notebook_id="mom_opcenter",
            title="Chinese Conv",
            ui_locale="zh_CN",
            answer_language="zh-Hans",
        )
        assert conv_zh.ui_locale == "zh-CN"
        assert conv_zh.answer_language == "zh-CN"

        # Vietnamese variations
        conv_vi = WorkspaceConversation(
            id="conv_vi",
            notebook_id="mom_opcenter",
            title="Vietnamese Conv",
            ui_locale="vi_VN",
            answer_language="VIETNAMESE",
        )
        assert conv_vi.ui_locale == "vi"
        assert conv_vi.answer_language == "vi"

        # Invalid / unknown string falls back safely to 'vi'
        conv_fallback = WorkspaceConversation(
            id="conv_fb",
            notebook_id="mom_opcenter",
            title="Fallback Conv",
            ui_locale="fr-FR",
            answer_language="es",
        )
        assert conv_fallback.ui_locale == "vi"
        assert conv_fallback.answer_language == "vi"

    def test_conversation_dict_serialization_and_deserialization(self) -> None:
        """Verify to_dict and from_dict roundtrip preserving locale fields."""
        original = WorkspaceConversation(
            id="conv_roundtrip",
            notebook_id="mom_opcenter",
            title="Multilingual Session",
            ui_locale="ja",
            answer_language="zh-CN",
            search_preference="deep",
        )
        data = original.to_dict()
        assert data["ui_locale"] == "ja"
        assert data["answer_language"] == "zh-CN"
        assert data["search_preference"] == "deep"

        reconstructed = WorkspaceConversation.from_dict(data)
        assert reconstructed.id == original.id
        assert reconstructed.ui_locale == "ja"
        assert reconstructed.answer_language == "zh-CN"
        assert reconstructed.search_preference == "deep"

    def test_conversation_backward_compatibility_legacy_records(self) -> None:
        """Verify legacy dictionary without ui_locale or answer_language safely initializes defaults."""
        legacy_data = {
            "id": "legacy_conv_99",
            "notebook_id": "mom_opcenter",
            "title": "Legacy Record Prior to Commit A",
            "selected_source_ids": ["src_1"],
            "temporary_source_ids": [],
            "saved_case_id": None,
            "compressed_memory": "",
            "search_preference": "auto",
        }
        # Neither ui_locale nor answer_language in dict
        conv = WorkspaceConversation.from_dict(legacy_data)
        assert conv.id == "legacy_conv_99"
        assert conv.ui_locale == "vi"
        assert conv.answer_language == "vi"

    def test_store_conversation_locale_persistence(self) -> None:
        """Verify saving and reloading conversation from JSONL store preserves locale settings."""
        conv = WorkspaceConversation(
            id="conv_store_01",
            notebook_id="mom_opcenter",
            title="Kiểm tra lưu trữ locale",
            ui_locale="ja",
            answer_language="zh-CN",
        )
        chat_store.save_conversation(conv)

        loaded = chat_store.load_conversation("conv_store_01")
        assert loaded is not None
        assert loaded.ui_locale == "ja"
        assert loaded.answer_language == "zh-CN"

    def test_store_update_conversation_language_settings_partial_and_full(self) -> None:
        """Verify update_conversation_language_settings handles partial and full updates."""
        conv = WorkspaceConversation(
            id="conv_update_lang",
            notebook_id="mom_opcenter",
            title="Đổi ngôn ngữ hội thoại",
            ui_locale="vi",
            answer_language="vi",
        )
        chat_store.save_conversation(conv)
        original_updated_at = conv.updated_at

        # 1. Update UI locale only
        res1 = chat_store.update_conversation_language_settings("conv_update_lang", ui_locale="ja")
        assert res1 is not None
        assert res1.ui_locale == "ja"
        assert res1.answer_language == "vi"

        loaded1 = chat_store.load_conversation("conv_update_lang")
        assert loaded1 is not None
        assert loaded1.ui_locale == "ja"
        assert loaded1.answer_language == "vi"

        # 2. Update AI answer language only
        res2 = chat_store.update_conversation_language_settings("conv_update_lang", answer_language="zh-CN")
        assert res2 is not None
        assert res2.ui_locale == "ja"
        assert res2.answer_language == "zh-CN"

        loaded2 = chat_store.load_conversation("conv_update_lang")
        assert loaded2 is not None
        assert loaded2.ui_locale == "ja"
        assert loaded2.answer_language == "zh-CN"

        # 3. Update non-existent conversation returns None
        res_none = chat_store.update_conversation_language_settings("non_existent_conv_id", ui_locale="ja")
        assert res_none is None

    def test_workspace_chat_store_class_wrapper_language_methods(self) -> None:
        """Verify WorkspaceChatStore OOP wrapper delegates update_conversation_language_settings correctly."""
        store_wrapper = chat_store.WorkspaceChatStore()
        conv = WorkspaceConversation(
            id="conv_oop_01",
            notebook_id="mom_opcenter",
            title="OOP Wrapper Test",
            ui_locale="vi",
            answer_language="vi",
        )
        store_wrapper.save_conversation(conv)

        updated = store_wrapper.update_conversation_language_settings(
            "conv_oop_01",
            ui_locale="ja",
            answer_language="ja",
        )
        assert updated is not None
        assert updated.ui_locale == "ja"
        assert updated.answer_language == "ja"

    def test_conversation_locale_persistence_through_context_compression(self) -> None:
        """Verify new compressed conversation properly inherits ui_locale and answer_language."""
        parent_conv = WorkspaceConversation(
            id="conv_parent_01",
            notebook_id="mom_opcenter",
            title="Japanese Consultation",
            ui_locale="ja",
            answer_language="zh-CN",
            search_preference="deep",
        )
        chat_store.save_conversation(parent_conv)

        # Simulate context compression creation logic
        compressed_summary = "要約：前回の議論ではサーバー設定について合意しました。"
        new_conv = WorkspaceConversation(
            id="conv_child_compressed",
            notebook_id=parent_conv.notebook_id,
            title=f"Tiếp tục: {parent_conv.title}",
            compressed_memory=compressed_summary,
            search_preference=getattr(parent_conv, "search_preference", "auto"),
            ui_locale=getattr(parent_conv, "ui_locale", "vi"),
            answer_language=getattr(parent_conv, "answer_language", "vi"),
        )
        chat_store.save_conversation(new_conv)

        reloaded = chat_store.load_conversation("conv_child_compressed")
        assert reloaded is not None
        assert reloaded.ui_locale == "ja"
        assert reloaded.answer_language == "zh-CN"
        assert reloaded.search_preference == "deep"
        assert reloaded.compressed_memory == compressed_summary



# ===========================================================================
# 2. UI Localized Labels & Key Completeness
# ===========================================================================

class TestUILocalizedLabels:
    """Tests for UI label dictionaries and completeness."""

    def test_get_localized_labels_returns_full_dictionary_for_all_locales(self) -> None:
        """Verify get_localized_labels returns populated dictionaries for vi, ja, and zh-CN."""
        for loc in ("vi", "ja", "zh-CN"):
            labels = get_localized_labels(loc)
            assert isinstance(labels, dict)
            assert len(labels) >= 100, f"Locale '{loc}' label dictionary is too small ({len(labels)} keys)"

            # Check core app navigation keys
            assert "app_title" in labels
            assert "open_notebook" in labels
            assert "create_conversation" in labels
            assert "language_selector" in labels
            assert "answer_language_selector" in labels

            # Check specific language translations
            if loc == "vi":
                assert labels["open_notebook"] == "Mở sổ"
                assert labels["language_selector"] == "Ngôn ngữ giao diện"
                assert labels["ai_action"] == "Hỏi"
            elif loc == "ja":
                assert labels["open_notebook"] == "ノートを開く"
                assert labels["language_selector"] == "表示言語"
                assert labels["ai_action"] == "質問する"
            elif loc == "zh-CN":
                assert labels["open_notebook"] == "打开笔记本"
                assert labels["language_selector"] == "界面语言"
                assert labels["ai_action"] == "提问"

    def test_get_localized_labels_fallback_for_unknown_locale(self) -> None:
        """Verify unknown or None locale gracefully falls back to Vietnamese labels."""
        labels_unknown = get_localized_labels("unknown_locale_xyz")
        labels_vi = get_localized_labels("vi")
        assert labels_unknown == labels_vi

    def test_get_vietnamese_labels_backward_compatibility(self) -> None:
        """Verify legacy get_vietnamese_labels() returns expected keys and values."""
        vn_labels = get_vietnamese_labels()
        assert isinstance(vn_labels, dict)
        assert vn_labels["notebooks_title"] == "Sổ tài liệu của tôi"
        assert vn_labels["open_notebook"] == "Mở sổ"
        assert vn_labels["conversations"] == "Cuộc trò chuyện"
        assert vn_labels["ai_action"] == "Hỏi"
        assert vn_labels["source_check"] == "Kiểm tra"

        # Parity: every key in get_vietnamese_labels must exist in get_localized_labels("vi")
        loc_vi = get_localized_labels("vi")
        for k, v in vn_labels.items():
            assert k in loc_vi, f"Legacy key '{k}' missing from get_localized_labels('vi')"
            assert loc_vi[k] == v, f"Mismatch for key '{k}': '{loc_vi[k]}' vs '{v}'"

    def test_evidence_graph_terminology_in_localized_labels(self) -> None:
        """Verify all critical Evidence Graph labels exist in all 3 languages."""
        eg_keys = [
            "evidence_graph",
            "nodes",
            "edges",
            "claims",
            "citations",
            "verifications",
            "node_type_claim",
            "node_type_evidence",
            "edge_supports",
            "edge_refutes",
            "edge_cites",
            "verification_status_verified",
            "confidence_high",
        ]
        for loc in ("vi", "ja", "zh-CN"):
            labels = get_localized_labels(loc)
            for k in eg_keys:
                assert k in labels, f"Evidence graph key '{k}' missing in locale '{loc}'"
                assert len(labels[k].strip()) > 0, f"Evidence graph key '{k}' is empty in locale '{loc}'"


# ===========================================================================
# 3. UI Dropdown Language Selector Component
# ===========================================================================

class TestUILanguageSelector:
    """Tests for render_language_selector component logic and event callbacks."""

    def test_render_language_selector_renders_options(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify selectboxes are invoked with supported locale codes and format functions."""
        calls: List[Dict[str, Any]] = []

        def mock_selectbox(label: str, options: List[str], index: int, format_func: Any, key: str) -> str:
            calls.append({
                "label": label,
                "options": options,
                "index": index,
                "key": key,
                "formatted": [format_func(opt) for opt in options],
            })
            return options[index]

        monkeypatch.setattr("streamlit.selectbox", mock_selectbox)

        ui_loc, ans_lang = render_language_selector(
            current_ui_locale="vi",
            current_answer_language="ja",
            key_prefix="test_lang",
        )

        assert ui_loc == "vi"
        assert ans_lang == "ja"
        assert len(calls) == 2

        # Check UI selectbox call
        ui_call = calls[0]
        assert "Ngôn ngữ giao diện" in ui_call["label"]
        assert ui_call["options"] == ["vi", "ja", "zh-CN"]
        assert ui_call["index"] == 0  # 'vi' is index 0
        assert ui_call["formatted"] == ["Tiếng Việt (vi)", "日本語 (ja)", "简体中文 (zh-CN)"]

        # Check AI Answer selectbox call
        ans_call = calls[1]
        assert "Ngôn ngữ trả lời AI" in ans_call["label"]
        assert ans_call["options"] == ["vi", "ja", "zh-CN"]
        assert ans_call["index"] == 1  # 'ja' is index 1

    def test_render_language_selector_callbacks_on_change(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify callbacks fire when user changes UI locale or answer language."""
        # Simulate user selecting 'zh-CN' for UI and 'ja' for AI answer
        def mock_selectbox(label: str, options: List[str], index: int, format_func: Any, key: str) -> str:
            if "ui_locale" in key:
                return "zh-CN"
            if "answer_language" in key:
                return "ja"
            return options[index]

        monkeypatch.setattr("streamlit.selectbox", mock_selectbox)

        changed_ui_records: List[str] = []
        changed_ans_records: List[str] = []
        combined_records: List[Tuple[str, str]] = []

        render_language_selector(
            current_ui_locale="vi",
            current_answer_language="vi",
            on_ui_locale_change=lambda u: changed_ui_records.append(u),
            on_answer_language_change=lambda a: changed_ans_records.append(a),
            on_change=lambda u, a: combined_records.append((u, a)),
            key_prefix="test_cb",
        )

        assert changed_ui_records == ["zh-CN"]
        assert changed_ans_records == ["ja"]
        assert combined_records == [("zh-CN", "ja")]

    def test_render_language_selector_invalid_input_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify invalid current locales are safely mapped to 'vi' index 0."""
        calls: List[Dict[str, Any]] = []

        def mock_selectbox(label: str, options: List[str], index: int, format_func: Any, key: str) -> str:
            calls.append({"index": index, "options": options})
            return options[index]

        monkeypatch.setattr("streamlit.selectbox", mock_selectbox)

        ui_loc, ans_lang = render_language_selector(
            current_ui_locale="non_existent_lang",
            current_answer_language="xyz",
            key_prefix="test_invalid",
        )

        assert ui_loc == "vi"
        assert ans_lang == "vi"
        assert calls[0]["index"] == 0
        assert calls[1]["index"] == 0


# ===========================================================================
# 4. AI Prompt Construction & Language Injection
# ===========================================================================

class TestAIPromptLanguageInjectionAndPreservation:
    """Tests for build_workspace_ai_prompt with explicit language instruction and citation preservation."""

    def test_prompt_system_instruction_vietnamese(self) -> None:
        """Verify system prompt contains Vietnamese requirement and strict evidence preservation."""
        src = WorkspaceAIContextSource(
            source_id="src_1",
            source_scope="notebook",
            source_type="xlsx",
            title="Báo cáo tài chính.xlsx",
            privacy_label="cloud_allowed",
            text="Doanh thu Q3: 150 tỷ. [E1] ERR_OK",
            included_chars=32,
            truncated=False,
        )
        sys_prompt, user_prompt = build_workspace_ai_prompt(
            question="Doanh thu Q3 là bao nhiêu?",
            context_sources=(src,),
            answer_language="vi",
        )

        # System prompt assertions
        assert "Yêu cầu ngôn ngữ: Trả lời hoàn toàn bằng Tiếng Việt." in sys_prompt
        assert "Giữ nguyên vẹn 100% tất cả các mã trích dẫn" in sys_prompt
        assert "[1]" in sys_prompt
        assert "document.pdf" in sys_prompt

        # User prompt structure
        assert "CÂU HỎI:" in user_prompt
        assert "NGUỒN 1" in user_prompt
        assert "Tiêu đề: Báo cáo tài chính.xlsx" in user_prompt
        assert "Doanh thu Q3: 150 tỷ. [E1] ERR_OK" in user_prompt

    def test_prompt_system_instruction_japanese(self) -> None:
        """Verify system prompt contains Japanese requirement and Japanese section headers."""
        src = WorkspaceAIContextSource(
            source_id="src_jp",
            source_scope="notebook",
            source_type="xlsx",
            title="operation_manual_2026.pdf",
            privacy_label="cloud_allowed",
            text="サーバー起動コマンド: systemctl start app [E1]",
            included_chars=40,
            truncated=False,
        )
        sys_prompt, user_prompt = build_workspace_ai_prompt(
            question="サーバーの起動方法は？",
            context_sources=(src,),
            answer_language="ja",
        )

        # System prompt assertions
        assert "言語指示: 回答はすべて日本語で記述してください。" in sys_prompt
        assert "引用ID（例: [1]、[E1]、EVD-001）" in sys_prompt
        assert "翻訳せず、原文のまま100%保持してください。" in sys_prompt

        # User prompt structure in Japanese
        assert "質問:" in user_prompt
        assert "サーバーの起動方法は？" in user_prompt
        assert "ソース 1" in user_prompt
        assert "タイトル: operation_manual_2026.pdf" in user_prompt
        assert "種別: Excel" in user_prompt or "種別: ソース" in user_prompt
        assert "内容:" in user_prompt
        assert "サーバー起動コマンド: systemctl start app [E1]" in user_prompt

    def test_prompt_system_instruction_simplified_chinese(self) -> None:
        """Verify system prompt contains Simplified Chinese requirement and Chinese section headers."""
        src = WorkspaceAIContextSource(
            source_id="src_zh",
            source_scope="notebook",
            source_type="plain_text",
            title="audit_specs.txt",
            privacy_label="cloud_allowed",
            text="错误代码: ERR_500_TIMEOUT. 来源引用: [EVD-88]",
            included_chars=45,
            truncated=False,
        )
        sys_prompt, user_prompt = build_workspace_ai_prompt(
            question="系统报告了什么错误？",
            context_sources=(src,),
            answer_language="zh-CN",
        )

        # System prompt assertions
        assert "语言指示: 请完全使用简体中文回答。" in sys_prompt
        assert "请100%完整保留所有引用ID（例如 [1]、[E1]、EVD-001）" in sys_prompt
        assert "严禁翻译或篡改任何标识符和证据引用。" in sys_prompt

        # User prompt structure in Chinese
        assert "问题:" in user_prompt
        assert "系统报告了什么错误？" in user_prompt
        assert "来源 1" in user_prompt
        assert "标题: audit_specs.txt" in user_prompt
        assert "类型: 文本" in user_prompt or "类型: 来源" in user_prompt
        assert "内容:" in user_prompt
        assert "错误代码: ERR_500_TIMEOUT. 来源引用: [EVD-88]" in user_prompt

    def test_prompt_localized_chat_history_roles(self) -> None:
        """Verify chat history role headers are localized correctly in user prompt."""
        history = (
            {"role": "user", "content": "Câu hỏi trước đó"},
            {"role": "assistant", "content": "Câu trả lời trước đó"},
            {"role": "system", "content": "Ngữ cảnh tóm tắt"},
        )
        src = WorkspaceAIContextSource(
            source_id="src_1",
            source_scope="temporary",
            source_type="txt",
            title="Notes.txt",
            privacy_label="cloud_allowed",
            text="Sample snippet.",
            included_chars=14,
            truncated=False,
        )

        # Vietnamese history
        _, user_vn = build_workspace_ai_prompt("Hỏi tiếp", (src,), history, answer_language="vi")
        assert "--- LỊCH SỬ HỘI THOẠI GẦN ĐÂY ---" in user_vn
        assert "[Người dùng]: Câu hỏi trước đó" in user_vn
        assert "[Ngữ cảnh kế thừa]: Ngữ cảnh tóm tắt" in user_vn
        assert "--- CÂU HỎI MỚI NHẤT ---" in user_vn

        # Japanese history
        _, user_ja = build_workspace_ai_prompt("次の質問", (src,), history, answer_language="ja")
        assert "--- 最近の会話履歴 ---" in user_ja
        assert "[ユーザー]: Câu hỏi trước đó" in user_ja
        assert "[継承コンテキスト]: Ngữ cảnh tóm tắt" in user_ja
        assert "--- 最新の質問 ---" in user_ja

        # Simplified Chinese history
        _, user_zh = build_workspace_ai_prompt("下一个问题", (src,), history, answer_language="zh-CN")
        assert "--- 最近对话历史 ---" in user_zh
        assert "[用户]: Câu hỏi trước đó" in user_zh
        assert "[继承上下文]: Ngữ cảnh tóm tắt" in user_zh
        assert "--- 最新问题 ---" in user_zh

    def test_prompt_strict_verbatim_evidence_preservation(self) -> None:
        """Verify that citation identifiers, file paths, and raw text are untouched in prompt blocks."""
        raw_content = (
            "[E1] /var/log/audit/syslog_2026-08-23.log -> ERR_CORRUPT_SEGMENT\n"
            "Citation ID: EVD-9923 | Source: opcenter_mom_final.pdf"
        )
        src = WorkspaceAIContextSource(
            source_id="src_verbatim",
            source_scope="notebook",
            source_type="plain_text",
            title="syslog_2026-08-23.log",
            privacy_label="cloud_allowed",
            text=raw_content,
            included_chars=len(raw_content),
            truncated=False,
        )
        _, user_prompt = build_workspace_ai_prompt(
            question="Kiểm tra mã lỗi trong log",
            context_sources=(src,),
            answer_language="ja",
        )

        assert "<<<SOURCE_CONTENT" in user_prompt
        assert raw_content in user_prompt
        assert "SOURCE_CONTENT" in user_prompt


# ===========================================================================
# 5. Outcome Classification with Multilingual Limitation Markers
# ===========================================================================

class TestOutcomeClassificationMultilingual:
    """Tests for classify_workspace_ai_outcome across vi, ja, zh-CN, and en limitation markers."""

    def test_classify_vietnamese_limitations(self) -> None:
        """Verify Vietnamese limitation phrases trigger 'answer_with_limits'."""
        vn_cases = [
            "Dựa trên các tài liệu hiện có, hiện chưa đủ thông tin để kết luận quy trình.",
            "Tài liệu không đề cập đến nguyên nhân sự cố trong phiên họp.",
            "Không tìm thấy đủ thông tin về ngân sách dự án.",
            "Theo nguồn cung cấp, hiện thiếu bằng chứng xác thực.",
        ]
        for text in vn_cases:
            outcome, grounding = classify_workspace_ai_outcome(text, provider_success=True, evidence_supplied=True)
            assert outcome == "answer_with_limits", f"Failed on Vietnamese limitation: '{text}'"
            assert grounding == "explicit_answer_limitation"

    def test_classify_japanese_limitations(self) -> None:
        """Verify Japanese limitation phrases trigger 'answer_with_limits'."""
        ja_cases = [
            "提供された資料には十分な証拠がありません。",
            "サーバーの仕様に関して情報が不足しています。",
            "該当するエラーコードは文書内に記載されていません。",
            "提供された証拠に基づく限り、確認できません。",
            "証拠不十分のため、追加確認が必要です。",
        ]
        for text in ja_cases:
            outcome, grounding = classify_workspace_ai_outcome(text, provider_success=True, evidence_supplied=True)
            assert outcome == "answer_with_limits", f"Failed on Japanese limitation: '{text}'"
            assert grounding == "explicit_answer_limitation"

    def test_classify_simplified_chinese_limitations(self) -> None:
        """Verify Simplified Chinese limitation phrases trigger 'answer_with_limits'."""
        zh_cases = [
            "根据现有证据，目前证据不足以确认具体原因。",
            "在所提供的参考文档中，没有足够的信息来回答此问题。",
            "相关配置文件中未找到相关信息。",
            "来源未提及该模块的具体部署参数。",
        ]
        for text in zh_cases:
            outcome, grounding = classify_workspace_ai_outcome(text, provider_success=True, evidence_supplied=True)
            assert outcome == "answer_with_limits", f"Failed on Chinese limitation: '{text}'"
            assert grounding == "explicit_answer_limitation"

    def test_classify_negated_limitations_pass_cleanly(self) -> None:
        """Verify negated limitations are correctly recognized as confident 'success' answers."""
        negated_cases = [
            ("vi", "Dữ liệu đã đầy đủ, không phải là không đủ thông tin để phân tích."),
            ("ja", "必要なデータは揃っており、十分な証拠がないわけではない。"),
            ("zh", "分析表明并非证据不足，所有核心指标均已核实。"),
            ("en", "The documentation is comprehensive and not lacking evidence."),
        ]
        for lang, text in negated_cases:
            outcome, grounding = classify_workspace_ai_outcome(text, provider_success=True, evidence_supplied=True)
            assert outcome == "success", f"Negation failed for [{lang}]: '{text}' (got {outcome})"
            assert grounding == "evidence_supplied_unverified"

    def test_classify_provider_failure_and_insufficient_evidence(self) -> None:
        """Verify fail-closed status when provider fails or evidence was not supplied."""
        # Provider failure
        outcome1, grounding1 = classify_workspace_ai_outcome("Any text", provider_success=False, evidence_supplied=True)
        assert outcome1 == "provider_error"
        assert grounding1 == "not_assessed_provider_failure"

        # No evidence supplied
        outcome2, grounding2 = classify_workspace_ai_outcome("Any text", provider_success=True, evidence_supplied=False)
        assert outcome2 == "insufficient_evidence"
        assert grounding2 == "insufficient_evidence"


# ===========================================================================
# 6. AI Answer Generation & Localized Disclaimers
# ===========================================================================

class TestAIAnswerGenerationAndDisclaimers:
    """Tests for generate_workspace_ai_answer disclaimer localization and provider propagation."""

    def test_localized_disclaimer_strings(self) -> None:
        """Verify _get_ai_disclaimer returns exact localized strings."""
        assert _get_ai_disclaimer("vi") == "\n\nĐây là câu trả lời do AI tạo, cần kiểm tra lại trước khi dùng."
        assert _get_ai_disclaimer("ja") == "\n\nこれはAIによって生成された回答です。使用前に確認してください。"
        assert _get_ai_disclaimer("zh-CN") == "\n\n这是由AI生成的回答，使用前请核对。"
        # Fallback
        assert _get_ai_disclaimer("invalid_locale") == "\n\nĐây là câu trả lời do AI tạo, cần kiểm tra lại trước khi dùng."

    def test_generate_ai_answer_appends_target_language_disclaimer(self) -> None:
        """Verify generate_workspace_ai_answer appends disclaimer in requested answer_language."""
        src = WorkspaceAIContextSource(
            source_id="src_disc",
            source_scope="notebook",
            source_type="plain_text",
            title="Guide.pdf",
            privacy_label="cloud_allowed",
            text="Bước 1: Khởi động hệ thống.",
            included_chars=26,
            truncated=False,
        )
        provider = MockAIProvider(response_text="手順に従って実行してください。")

        # Request Japanese answer
        req_ja = WorkspaceAIAnswerRequest(
            conversation_id="conv_disc_ja",
            question="手順は何ですか？",
            context_sources=(src,),
            privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
            cloud_consent_confirmed=True,
            consent_source_keys=(("notebook", "src_disc"),),
            answer_language="ja",
            ui_locale="ja",
        )
        result_ja = generate_workspace_ai_answer(req_ja, provider)
        assert result_ja.ok is True
        assert "手順に従って実行してください。" in result_ja.answer_text
        assert "これはAIによって生成された回答です。使用前に確認してください。" in result_ja.answer_text

        # Request Chinese answer
        provider_zh = MockAIProvider(response_text="请按照步骤执行。")
        req_zh = WorkspaceAIAnswerRequest(
            conversation_id="conv_disc_zh",
            question="步骤是什么？",
            context_sources=(src,),
            privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
            cloud_consent_confirmed=True,
            consent_source_keys=(("notebook", "src_disc"),),
            answer_language="zh-CN",
            ui_locale="zh-CN",
        )
        result_zh = generate_workspace_ai_answer(req_zh, provider_zh)
        assert result_zh.ok is True
        assert "请按照步骤执行。" in result_zh.answer_text
        assert "这是由AI生成的回答，使用前请核对。" in result_zh.answer_text

    def test_generate_ai_answer_propagates_language_to_prompt(self) -> None:
        """Verify generate_workspace_ai_answer passes answer_language into prompt generator."""
        src = WorkspaceAIContextSource(
            source_id="src_prop",
            source_scope="notebook",
            source_type="plain_text",
            title="Doc.txt",
            privacy_label="cloud_allowed",
            text="Sample content",
            included_chars=14,
            truncated=False,
        )
        provider = MockAIProvider(response_text="Sample AI answer")
        req = WorkspaceAIAnswerRequest(
            conversation_id="conv_prop",
            question="Test question",
            context_sources=(src,),
            privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
            cloud_consent_confirmed=True,
            consent_source_keys=(("notebook", "src_prop"),),
            answer_language="zh-CN",
        )
        generate_workspace_ai_answer(req, provider)

        assert provider.last_system_prompt is not None
        assert "语言指示: 请完全使用简体中文回答。" in provider.last_system_prompt


# ===========================================================================
# 7. UTF-8 & Anti-Mojibake Guarantees
# ===========================================================================

class TestUTF8AntiMojibakePersistence:
    """Tests guaranteeing zero character corruption for Vietnamese diacritics, Kanji/Kana, and Hanzi."""

    def test_utf8_multilingual_chat_message_persistence(self) -> None:
        """Verify chat messages with diacritics and East Asian characters store and reload cleanly."""
        multilingual_content = (
            "Tiếng Việt: Thử nghiệm đối soát bằng chứng với đầy đủ dấu: ắ, ằ, ẳ, ẵ, ặ, ế, ề, ể, ễ, ệ, ố, ồ, ổ, ỗ, ộ.\n"
            "日本語：多言語ワークスペースチャット、証拠グラフ、および引用追跡機能の完全性検証。\n"
            "简体中文：证据追踪数据契约、多语言提示词注入与严格的去乱码保证。\n"
            "Special: [E1] /path/to/ファイル_2026.xlsx -> ERR_001: 完了 (thành công)"
        )
        msg = ChatMessage(
            id="msg_utf8_01",
            conversation_id="conv_utf8",
            role="assistant",
            content=multilingual_content,
        )
        chat_store.save_message(msg)

        loaded_msgs = chat_store.load_messages("conv_utf8")
        assert len(loaded_msgs) == 1
        assert loaded_msgs[0].content == multilingual_content
        # Direct raw byte inspection in file to confirm pure UTF-8 without unicode escapes (\uXXXX)
        raw_text = chat_store.MESSAGES_FILE.read_text(encoding="utf-8")
        assert "Thử nghiệm đối soát bằng chứng" in raw_text
        assert "多言語ワークスペースチャット" in raw_text
        assert "证据追踪数据契约" in raw_text
        assert "\\u" not in raw_text

    def test_utf8_multilingual_temporary_source_persistence(self) -> None:
        """Verify temporary conversation sources preserve mixed-language content and previews."""
        title = "Tài liệu kỹ thuật Nhật - Việt (日越技術文書 / 中日越技术规范)"
        content = (
            "1. Yêu cầu hệ thống: BGE-M3 embedding model và Evidence Graph trace.\n"
            "2. 日本語要件：すべての引用識別子とエラーコードは原文のまま保持すること。\n"
            "3. 规范说明：严禁篡改原文中的任何引用锚点与技术代码。"
        )
        ts = TemporaryConversationSource(
            id="src_utf8_temp",
            conversation_id="conv_utf8_src",
            source_type="pasted_text",
            title=title,
            content_preview=content[:80],
            content_text=content,
            privacy_label="cloud_allowed",
        )
        chat_store.save_temporary_source(ts)

        loaded = chat_store.load_temporary_sources("conv_utf8_src")
        assert len(loaded) == 1
        assert loaded[0].title == title
        assert loaded[0].content_text == content
        assert loaded[0].content_preview == content[:80]


VIETNAMESE_DIACRITICS_REGEX = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
    r"ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]"
)

STREAMLIT_UI_FUNCTIONS = {
    "write", "markdown", "caption", "button", "info", "warning", "error",
    "success", "title", "header", "subheader", "text_input", "text_area",
    "selectbox", "radio", "checkbox", "expander", "progress", "toast",
    "file_uploader", "metric", "spinner", "dataframe",
}


class AntiHardcodeUIVisitor(ast.NodeVisitor):
    """AST Visitor that inspects UI renderer functions for raw hardcoded Vietnamese string literals."""

    def __init__(self, allowed_functions: Optional[set[str]] = None):
        self.allowed_functions = allowed_functions or {"get_vietnamese_labels"}
        self.violations: list[dict[str, Any]] = []
        self.current_function: Optional[str] = "module_root"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Whitelist functions explicitly designated for backward-compatibility dictionary returns
        if node.name in self.allowed_functions:
            return
        prev_fn = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_fn

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if node.name in self.allowed_functions:
            return
        prev_fn = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_fn

    def visit_Call(self, node: ast.Call) -> None:
        is_st_call = False
        func_name = ""
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and node.func.value.id == "st") or \
               (isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "sidebar"):
                func_name = node.func.attr
                if func_name in STREAMLIT_UI_FUNCTIONS:
                    is_st_call = True

        if is_st_call:
            # Check positional arguments
            for arg in node.args:
                self._check_node_for_vi_hardcode(arg, node.lineno, func_name)
            # Check keyword arguments (e.g. placeholder=..., help=...)
            for kw in node.keywords:
                self._check_node_for_vi_hardcode(kw.value, node.lineno, f"{func_name}({kw.arg}=)")

        self.generic_visit(node)

    def _check_node_for_vi_hardcode(self, node: ast.AST, lineno: int, context: str) -> None:
        # Check direct string constants
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if VIETNAMESE_DIACRITICS_REGEX.search(node.value):
                self.violations.append({
                    "function": self.current_function,
                    "line": lineno,
                    "context": context,
                    "string": node.value,
                })
        # Check formatted f-strings (ast.JoinedStr)
        elif isinstance(node, ast.JoinedStr):
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    if VIETNAMESE_DIACRITICS_REGEX.search(part.value):
                        self.violations.append({
                            "function": self.current_function,
                            "line": lineno,
                            "context": f"{context} [f-string]",
                            "string": part.value,
                        })


class TestWorkspaceChatUIAntiHardcode:
    """AST guard verifying zero raw hardcoded Vietnamese string literals in UI renderers and app entry point."""

    def test_ast_workspace_chat_ui_zero_hardcoded_vietnamese(self) -> None:
        """Verify all declared UI renderer functions in workspace_chat_ui.py use t(...) or get_localized_labels()."""
        ui_path = Path("src/aios_habit/workspace_chat_ui.py")
        assert ui_path.exists(), f"Target file does not exist: {ui_path}"
        tree = ast.parse(ui_path.read_text(encoding="utf-8"), filename=str(ui_path))

        visitor = AntiHardcodeUIVisitor(allowed_functions={"get_vietnamese_labels"})
        visitor.visit(tree)

        if visitor.violations:
            msg = "\n".join(
                f"  - Line {v['line']} in `{v['function']}()` ({v['context']}): \"{v['string']}\""
                for v in visitor.violations
            )
            pytest.fail(f"Found {len(visitor.violations)} hardcoded Vietnamese strings in UI renderers:\n{msg}")

    def test_ast_workspace_chat_app_zero_hardcoded_vietnamese(self) -> None:
        """Verify all Streamlit UI calls in workspace_chat_app.py use centralized t(...) i18n lookups."""
        app_path = Path("src/aios_habit/workspace_chat_app.py")
        assert app_path.exists(), f"Target file does not exist: {app_path}"
        tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))

        visitor = AntiHardcodeUIVisitor(allowed_functions={"create_safe_test_data"})
        visitor.visit(tree)

        if visitor.violations:
            msg = "\n".join(
                f"  - Line {v['line']} in `{v['function']}()` ({v['context']}): \"{v['string']}\""
                for v in visitor.violations
            )
            pytest.fail(f"Found {len(visitor.violations)} hardcoded Vietnamese strings in workspace_chat_app.py:\n{msg}")

    def test_new_translation_keys_parity_and_non_empty(self) -> None:
        """Verify all new Commit A translation keys exist and are non-empty in vi, ja, zh-CN."""
        new_keys = [
            "notebook_header_desc",
            "create_notebook",
            "notebook_title_label",
            "notebook_desc_label",
            "btn_create_notebook",
            "no_notebook_description",
            "conv_count_label",
            "chat_start_prompt",
            "jump_to_latest",
            "refresh",
            "layout_split",
            "layout_full",
            "add_sources_expander",
            "results_and_evidence",
            "search_level_help",
            "status_bge_unavailable",
            "status_preview_only",
            "status_prep_error",
            "no_conversations_in_notebook",
            "create_first_conversation_now",
            "close_save_notification",
            "close_notification",
            "managing_sources_expander",
            "citations_from_docs",
            "conversation_long_warning",
            "cancel_pending_question",
            "question_held_preparing_sources",
            "waiting_antigravity_banner",
            "ai_analysis_spinner",
            "step1_checking_sources_toast",
            "step3_composing_answer_toast",
            "no_evidence_found_error",
            "no_matched_segments_error",
            "duplicate_source_title_warning",
            "duplicate_source_help",
            "keep_both_versions",
            "replace_old_version",
            "cancel_upload",
            "group_name_optional",
            "paste_content_here",
            "save_permanently_to_notebook",
            "temp_source_title",
            "long_text_content",
            "use_content_in_answer",
            "attach_screenshot_help",
            "enable_images_for_question",
            "upload_docs_help",
            "upload_multi_docs_help",
            "upload_supported_formats",
            "use_docs_in_answer",
            "folder_path_input",
            "folder_path_help",
            "folder_supported_formats",
            "scan_subfolders",
            "scan_folder_button",
            "scanned_files_header",
            "import_all_to_notebook",
            "import_remaining_files",
            "folder_migrated_legacy_files",
            "folder_already_imported",
            "resume_pending_preparation",
            "ingest_processing_progress",
            "attach_popover",
            "cagent_config_popover",
            "cagent_endpoint_label",
            "shared_library_expander",
            "shared_library_help",
            "shared_library_path_label",
            "shared_library_choose",
            "shared_library_save",
            "shared_library_cleared",
            "shared_library_moved",
            "shared_library_joined",
            "shared_library_busy",
            "shared_library_io_error",
            "shared_library_invalid",
            "shared_library_remote_wal_unsupported",
            "shared_library_conflict",
            "no_matching_docs_in_folder",
            "content_cannot_be_empty",
            "select_at_least_one_image",
            "select_file_before_adding",
            "enter_folder_path_before_scan",
            "agent_ide_title",
            "agent_ide_desc",
            "agent_ide_mode",
            "agent_ide_workspace_path",
            "agent_ide_confirm_scope",
            "agent_ide_trust_btn",
            "agent_ide_prompt_label",
            "agent_ide_approval_help",
            "agent_ide_readonly_done",
            "agent_ide_tool_trace",
            "agent_ide_controlled_proposal",
            "agent_ide_target_file",
            "agent_ide_current_chunk",
            "agent_ide_replacement_chunk",
            "agent_ide_change_reason",
            "agent_ide_cmd_to_run",
            "agent_ide_cmd_purpose",
            "agent_ide_diff_created",
            "agent_ide_cmd_proposed",
            "agent_ide_approval_gate",
            "agent_ide_approve_patch",
            "agent_ide_approve_cmd",
            "agent_ide_reject",
            "agent_ide_confirm_scope_first",
            "demo_create_test_data",
            "demo_supported_sources_info",
            "demo_excel_expander",
        ]
        for locale in ("vi", "ja", "zh-CN"):
            loc_dict = TRANSLATIONS.get(locale, {})
            for key in new_keys:
                assert key in loc_dict, f"Missing key '{key}' in locale '{locale}'"
                val = loc_dict[key]
                assert isinstance(val, str) and len(val.strip()) > 0, f"Empty value for key '{key}' in locale '{locale}'"
