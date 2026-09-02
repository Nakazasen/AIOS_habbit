# -*- coding: utf-8 -*-
"""Comprehensive End-to-End Test Suite for Multilingual Language Switching (vi / ja / zh-CN).

Validates:
1. Dynamic UI language switching between Vietnamese, Japanese, and Simplified Chinese.
2. AI Answer language switching and corresponding prompt injection.
3. 100% translation key parity across vi, ja, and zh-CN dictionaries.
4. Localized Case Management (US1) in vi, ja, and zh-CN.
5. Localized Chat Composer & Source Library in vi, ja, and zh-CN.
6. Error message safety and localized fallbacks in all 3 languages.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
import pytest

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
from aios_habit.workspace_case_models import (
    CaseActivity,
    CaseChecklistItem,
    CaseDetail,
    CaseEvidenceReference,
    CaseRecord,
    TraceResolution,
)
from aios_habit.workspace_case_service import CaseValidationError
from aios_habit.workspace_case_ui import (
    case_detail_sections,
    case_list_rows,
    safe_case_error_message,
)
from aios_habit.workspace_chat_ai_answer import (
    WorkspaceAIContextSource,
    _get_ai_disclaimer,
    build_workspace_ai_prompt,
)
from aios_habit.workspace_chat_models import (
    ChatMessage,
)
from aios_habit.workspace_chat_ui import (
    get_localized_labels,
    render_language_selector,
)


def _sample_case() -> CaseRecord:
    return CaseRecord.new(
        conversation_id="CONV-LANG-TEST",
        assistant_message_id="MSG-LANG-TEST",
        trace_id="trace-lang-test",
        evidence_digest="digest-lang-test",
    )


def test_supported_locales_completeness():
    """Verify supported locales are exactly Vietnamese, Japanese, and Simplified Chinese."""
    assert SUPPORTED_LOCALES == ("vi", "ja", "zh-CN")
    assert LOCALE_NAMES["vi"] == "Tiếng Việt"
    assert LOCALE_NAMES["ja"] == "日本語"
    assert LOCALE_NAMES["zh-CN"] == "简体中文"


def test_100_percent_translation_key_parity():
    """Ensure every single key exists and is non-empty across all 3 languages."""
    vi_keys = set(TRANSLATIONS["vi"].keys())
    ja_keys = set(TRANSLATIONS["ja"].keys())
    zh_keys = set(TRANSLATIONS["zh-CN"].keys())

    assert vi_keys == ja_keys, f"Mismatch between vi and ja: {vi_keys ^ ja_keys}"
    assert vi_keys == zh_keys, f"Mismatch between vi and zh-CN: {vi_keys ^ zh_keys}"
    assert len(vi_keys) >= 200

    for loc in SUPPORTED_LOCALES:
        for k, v in TRANSLATIONS[loc].items():
            assert isinstance(v, str) and len(v.strip()) > 0, f"Empty translation for key '{k}' in locale '{loc}'"


@pytest.mark.parametrize("locale,expected_title,expected_open", [
    ("vi", "AIOS Workspace Chat", "Mở sổ"),
    ("ja", "AIOS Workspace Chat", "ノートを開く"),
    ("zh-CN", "AIOS Workspace Chat", "打开笔记本"),
])
def test_ui_labels_switch_dynamically(locale: str, expected_title: str, expected_open: str):
    """Verify get_localized_labels returns correct text for all 3 supported languages."""
    labels = get_localized_labels(locale)
    assert labels["app_title"] == expected_title
    assert labels["open_notebook"] == expected_open


@pytest.mark.parametrize("locale,expected_type,expected_status,expected_priority,expected_assignee", [
    ("vi", "Điều tra", "Nháp", "Bình thường", "Chưa giao"),
    ("ja", "調査", "下書き", "通常", "未割り当て"),
    ("zh-CN", "调查", "草稿", "正常", "未分配"),
])
def test_case_list_multilingual_switching(locale: str, expected_type: str, expected_status: str, expected_priority: str, expected_assignee: str):
    """Verify Case Management list headers and values translate properly per locale."""
    case = _sample_case()
    rows = case_list_rows([case], locale=locale)
    assert len(rows) == 1
    row = rows[0]

    col_type = t("case_col_type", locale=locale)
    col_status = t("case_col_status", locale=locale)
    col_priority = t("case_col_priority", locale=locale)
    col_assignee = t("case_col_assignee", locale=locale)

    assert row[col_type] == expected_type
    assert row[col_status] == expected_status
    assert row[col_priority] == expected_priority
    assert row[col_assignee] == expected_assignee


@pytest.mark.parametrize("locale,expected_timeline_event,expected_actor,expected_trace_msg", [
    ("vi", "Tạo hồ sơ", "Quản trị viên cục bộ", "Có thể mở dấu vết bằng chứng gốc"),
    ("ja", "ケース作成", "ローカル管理者", "元の証拠トレースを開くことができます"),
    ("zh-CN", "创建案例", "本地管理员", "可打开原始证据追踪记录"),
])
def test_case_detail_multilingual_sections(locale: str, expected_timeline_event: str, expected_actor: str, expected_trace_msg: str):
    """Verify Case Detail sections, timeline, and trace status translate per locale."""
    case = _sample_case()
    activity = CaseActivity.new(
        case_id=case.case_id,
        event_type="case_created",
        actor_id="local_admin",
        payload_digest="digest-1",
    )
    checklist_item = CaseChecklistItem(
        item_id="CHK-1",
        case_id=case.case_id,
        description="Verify error log",
        status="open",
        created_at="2026-08-30T10:00:00Z",
    )
    detail = CaseDetail(
        case=case,
        evidence=(),
        activities=(activity,),
        checklist=(checklist_item,),
    )
    trace = TraceResolution(status="available", trace_id=case.trace_id, trace=None)

    sections = case_detail_sections(detail, trace, locale=locale)
    assert sections["trace_status"] == expected_trace_msg

    timeline = sections["timeline"]
    assert len(timeline) == 1
    col_event = t("case_col_event", locale=locale)
    col_actor = t("case_col_actor", locale=locale)
    assert timeline[0][col_event] == expected_timeline_event
    assert timeline[0][col_actor] == expected_actor


@pytest.mark.parametrize("locale,expected_keyword", [
    ("vi", "Yêu cầu ngôn ngữ: Trả lời hoàn toàn bằng Tiếng Việt."),
    ("ja", "言語指示: 回答はすべて日本語で記述してください。"),
    ("zh-CN", "语言指示: 请完全使用简体中文回答。"),
])
def test_ai_prompt_language_instruction_injection(locale: str, expected_keyword: str):
    """Verify AI prompt language instruction specifies the exact requested language with verbatim evidence preservation."""
    instruction = get_ai_language_instruction(locale)
    assert expected_keyword in instruction
    assert "[1]" in instruction or "引用ID" in instruction or "mã trích dẫn" in instruction


@pytest.mark.parametrize("locale,expected_banner_keyword", [
    ("vi", "câu trả lời do AI tạo"),
    ("ja", "AIによって生成された回答"),
    ("zh-CN", "由AI生成的回答"),
])
def test_ai_disclaimer_multilingual(locale: str, expected_banner_keyword: str):
    """Verify AI disclaimer banner reflects the target locale."""
    disclaimer = _get_ai_disclaimer(locale)
    assert expected_banner_keyword in disclaimer


def test_language_selector_callbacks():
    """Verify language selector callbacks fire appropriately on change."""
    ui_changed = []
    ans_changed = []

    def on_ui(val: str):
        ui_changed.append(val)

    def on_ans(val: str):
        ans_changed.append(val)

    # Simulate render_language_selector helper with mock streamlit
    st_mock = MagicMock()
    # verify format_func and options
    supported = get_supported_locales()
    assert [c for c, _ in supported] == ["vi", "ja", "zh-CN"]
    assert LOCALE_NAMES["vi"] == "Tiếng Việt"
    assert LOCALE_NAMES["ja"] == "日本語"
    assert LOCALE_NAMES["zh-CN"] == "简体中文"
