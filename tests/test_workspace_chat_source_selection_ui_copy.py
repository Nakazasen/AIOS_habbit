# -*- coding: utf-8 -*-
"""UI Copy and Layout Smoke Tests for AIOS Workspace Chat.

Verifies that source library renderers, readiness badges, evidence grouping,
and truthful provenance headers correctly localize user-facing text across
vi, ja, and zh-CN without leaking forbidden technical jargon into owner views.
"""
import ast
from pathlib import Path

import pytest
import streamlit as st
from aios_habit.workspace_chat_ui import (
    render_source_status,
    render_source_library,
    render_source_library_summary,
    render_preparation_progress_bar,
    render_document_manager,
    render_ai_answer_header,
    render_grouped_evidence_items,
    format_preparation_summary_text,
)
from aios_habit.workspace_chat_models import NotebookSource, TemporaryConversationSource
from aios_habit.i18n import t

FORBIDDEN_WORDS = [
    "RAG", "vector", "embedding", "chunk", "retrieval", "citation", "claim",
    "provider router", "Mermaid", "prompt pack", "Nguồn AIOS đã dùng", "Nguồn chứng minh",
    "Giao AI xử lý", "Nhập kết quả AI", "task pack", "report import", "hash", "gate",
    "commit", "branch", "push", "A17", "Các bước thử nghiệm", "Pilot",
    "Hỏi AI với nguồn đang bật", "Kiểm tra nguồn trước"
]


class MockSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


class WidgetStatesDict(dict):
    def __init__(self, session_state):
        super().__init__()
        self.session_state = session_state

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.session_state[key] = value


class MockStreamlit:
    def __init__(self):
        self.calls = []
        self.session_state = MockSessionState()
        self.widget_states = WidgetStatesDict(self.session_state)

    def subheader(self, text, *args, **kwargs):
        self.calls.append(("subheader", str(text), None, None))

    def write(self, text, *args, **kwargs):
        self.calls.append(("write", str(text), None, None))

    def markdown(self, text, *args, **kwargs):
        self.calls.append(("markdown", str(text), None, None))

    def info(self, text, *args, **kwargs):
        self.calls.append(("info", str(text), None, None))

    def caption(self, text, *args, **kwargs):
        self.calls.append(("caption", str(text), None, None))

    def checkbox(self, label, value=False, key=None, on_change=None, *args, **kwargs):
        self.calls.append(("checkbox", str(label), value, key, on_change))
        if key in self.widget_states:
            return self.widget_states[key]
        return value

    def expander(self, label, expanded=False, *args, **kwargs):
        self.calls.append(("expander", str(label), expanded, None))
        class MockExpander:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        return MockExpander()

    def button(self, label, key=None, *args, **kwargs):
        self.calls.append(("button", str(label), key, None))
        if key in self.widget_states:
            return self.widget_states[key]
        return False

    def container(self):
        class MockContainer:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        return MockContainer()

    def text_input(self, label, value="", placeholder=None, key=None, *args, **kwargs):
        self.calls.append(("text_input", str(label), value, placeholder))
        if key in self.widget_states:
            return self.widget_states[key]
        return value

    def columns(self, spec):
        class MockColumn:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        count = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        return [MockColumn() for _ in range(count)]

    def warning(self, text, *args, **kwargs):
        self.calls.append(("warning", str(text), None, None))

    def success(self, text, *args, **kwargs):
        self.calls.append(("success", str(text), None, None))

    def progress(self, value, text=None, *args, **kwargs):
        self.calls.append(("progress", int(value), str(text or ""), None))

    def text_area(self, label, value="", *args, **kwargs):
        self.calls.append(("text_area", str(label), value, None))


@pytest.fixture
def mock_st(monkeypatch):
    st_mock = MockStreamlit()
    monkeypatch.setattr(st, "subheader", st_mock.subheader)
    monkeypatch.setattr(st, "write", st_mock.write)
    monkeypatch.setattr(st, "markdown", st_mock.markdown)
    monkeypatch.setattr(st, "info", st_mock.info)
    monkeypatch.setattr(st, "caption", st_mock.caption)
    monkeypatch.setattr(st, "checkbox", st_mock.checkbox)
    monkeypatch.setattr(st, "expander", st_mock.expander)
    monkeypatch.setattr(st, "button", st_mock.button)
    monkeypatch.setattr(st, "container", st_mock.container)
    monkeypatch.setattr(st, "text_input", st_mock.text_input)
    monkeypatch.setattr(st, "columns", st_mock.columns)
    monkeypatch.setattr(st, "warning", st_mock.warning)
    monkeypatch.setattr(st, "success", st_mock.success)
    monkeypatch.setattr(st, "progress", st_mock.progress)
    monkeypatch.setattr(st, "text_area", st_mock.text_area)
    monkeypatch.setattr(st, "session_state", st_mock.session_state)
    return st_mock


@pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
def test_render_source_status_multilingual(locale: str):
    res_ready = render_source_status("ready", locale=locale)
    assert res_ready == t("status_ready", locale=locale)

    res_unavail = render_source_status("unavailable", locale=locale)
    assert res_unavail == t("status_bge_unavailable", locale=locale)

    res_failed = render_source_status("failed", locale=locale)
    assert res_failed == t("status_failed", locale=locale)


@pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
def test_render_source_library_summary_multilingual(mock_st, locale: str):
    render_source_library_summary(notebook_count=2, temporary_count=1, enabled_count=3, locale=locale)
    info_calls = [c[1] for c in mock_st.calls if c[0] == "info"]
    assert len(info_calls) == 1
    assert t("sources_in_use", locale=locale) in info_calls[0]
    assert t("sources_in_use_desc", locale=locale) in info_calls[0]


@pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
def test_render_source_library_source_row_coverage(mock_st, locale: str):
    """Verifies complete source row coverage: enabled/disabled, notebook/temporary, checkbox, promote, and delete buttons."""
    nb_src = [NotebookSource(id="src_1", notebook_id="nb_1", title="Quy trình chuẩn.pdf", source_type="pdf", content_preview="Preview SOP")]
    tmp_src = [TemporaryConversationSource(id="tmp_1", conversation_id="conv_1", title="Ghi chú tạm.txt", source_type="txt", content_preview="Preview Temp")]
    render_source_library(
        notebook_sources=nb_src,
        temp_sources=tmp_src,
        selections_map={("notebook", "src_1"): True, ("temporary", "tmp_1"): False},
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        locale=locale,
    )
    subheader_calls = [c[1] for c in mock_st.calls if c[0] == "subheader"]
    assert any(t("source_library", locale=locale) in s for s in subheader_calls)

    caption_calls = [c[1] for c in mock_st.calls if c[0] == "caption"]
    # Check scope indications
    assert any(t("in_notebook", locale=locale) in c for c in caption_calls)
    assert any(t("temp_in_conversation", locale=locale) in c for c in caption_calls)
    # Check enabled/disabled state captions
    assert any(t("status_enabled", locale=locale) in c for c in caption_calls)
    assert any(t("status_disabled", locale=locale) in c for c in caption_calls)

    # Check checkbox labels
    checkbox_calls = [c[1] for c in mock_st.calls if c[0] == "checkbox"]
    assert all(t("enable_this_source", locale=locale) in cb for cb in checkbox_calls)

    # Check buttons: promote button for temp source, delete buttons
    button_calls = [c[1] for c in mock_st.calls if c[0] == "button"]
    assert any(t("add_to_notebook", locale=locale) in b for b in button_calls)
    assert any(t("delete_source", locale=locale) in b for b in button_calls)


@pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
def test_document_preparation_summary_text_matrix(locale: str):
    """Test user-safe document preparation copy across every supported locale."""
    # 1. Library unavailable
    unavail_summary = {"total": 3, "bge_available": False}
    unavail_text = format_preparation_summary_text(unavail_summary, locale=locale)
    assert unavail_text == t("bge_unavailable", locale=locale)

    # 2. Pending
    pending_summary = {
        "total": 3,
        "ready": 1,
        "processing": 0,
        "pending": 2,
        "failed": 0,
        "bge_available": True,
    }
    pending_text = format_preparation_summary_text(pending_summary, locale=locale)
    assert t("bge_ready_ratio", locale=locale, ready=1, total=3) in pending_text
    assert t("bge_pending_count", locale=locale, count=2) in pending_text

    # 3. Processing never exposes the current document title in the shared banner.
    doc_title = "quy_trinh_2026_special_v1.pdf"
    proc_summary = {
        "total": 4,
        "ready": 2,
        "processing": 1,
        "pending": 1,
        "failed": 0,
        "current_source_title": doc_title,
        "bge_available": True,
    }
    proc_text = format_preparation_summary_text(proc_summary, locale=locale)
    assert t("bge_ready_ratio", locale=locale, ready=2, total=4) in proc_text
    assert doc_title not in proc_text
    assert "BGE-M3" not in proc_text

    # 4. Failed
    fail_summary = {
        "total": 5,
        "ready": 3,
        "processing": 0,
        "pending": 0,
        "failed": 2,
        "bge_available": True,
    }
    fail_text = format_preparation_summary_text(fail_summary, locale=locale)
    assert t("bge_ready_ratio", locale=locale, ready=3, total=5) in fail_text
    assert t("bge_failed_count", locale=locale, count=2) in fail_text

    # 5. All ready
    ready_summary = {
        "total": 5,
        "ready": 5,
        "processing": 0,
        "pending": 0,
        "failed": 0,
        "bge_available": True,
    }
    ready_text = format_preparation_summary_text(ready_summary, locale=locale)
    assert t("bge_ready_ratio", locale=locale, ready=5, total=5) in ready_text


@pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
def test_render_preparation_progress_bar_all_ready_multilingual(mock_st, locale: str):
    summary = {
        "total": 5,
        "ready": 5,
        "processing": 0,
        "pending": 0,
        "failed": 0,
        "bge_available": True,
    }
    render_preparation_progress_bar(summary, locale=locale)
    progress_calls = [c for c in mock_st.calls if c[0] == "progress"]
    assert progress_calls == [("progress", 100, t("document_preparation_progress", locale=locale, completed=5, total=5, percent=100), None)]
    success_calls = [c[1] for c in mock_st.calls if c[0] == "success"]
    assert len(success_calls) == 1
    assert t("bge_ready_ratio", locale=locale, ready=5, total=5) in success_calls[0]


@pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
def test_render_preparation_progress_bar_with_failures_multilingual(mock_st, locale: str):
    summary = {
        "total": 5,
        "ready": 3,
        "processing": 0,
        "pending": 0,
        "failed": 2,
        "bge_available": True,
    }
    retried = []
    render_preparation_progress_bar(summary, on_retry_all_failed=lambda: retried.append(True), locale=locale)
    warning_calls = [c[1] for c in mock_st.calls if c[0] == "warning"]
    assert len(warning_calls) == 1
    assert t("bge_ready_ratio", locale=locale, ready=3, total=5) in warning_calls[0]
    assert t("bge_failed_count", locale=locale, count=2) in warning_calls[0]
    button_calls = [c[1] for c in mock_st.calls if c[0] == "button"]
    assert any(t("retry_preparation", locale=locale) in b for b in button_calls)


def test_render_preparation_progress_shows_percent_and_paused_action(mock_st):
    summary = {
        "total": 78,
        "ready": 20,
        "processing": 0,
        "pending": 58,
        "failed": 0,
        "completed": 20,
        "progress_percent": 26,
        "preparation_state": "paused",
        "bge_available": True,
    }
    resumed = []

    render_preparation_progress_bar(summary, on_resume=lambda: resumed.append(True))

    progress_calls = [c for c in mock_st.calls if c[0] == "progress"]
    assert progress_calls == [("progress", 26, "Đã chuẩn bị xong 20/78 tài liệu (26%)", None)]
    warning_calls = [c[1] for c in mock_st.calls if c[0] == "warning"]
    assert any("tạm dừng" in call for call in warning_calls)
    assert any(call[0] == "button" and call[1] == t("resume_pending_preparation") for call in mock_st.calls)


def test_document_manager_can_hide_duplicate_preparation_progress(mock_st):
    summary = {
        "total": 2,
        "ready": 1,
        "processing": 0,
        "pending": 0,
        "failed": 1,
        "bge_available": True,
    }

    render_preparation_progress_bar(summary, on_retry_all_failed=lambda: None)
    render_document_manager(
        notebook_sources=[],
        temporary_sources=[],
        selections_map={},
        conversation_id="conv-no-duplicate-progress",
        on_toggle_source=lambda *args: None,
        on_delete_source=lambda *args: None,
        on_delete_sources=lambda *args: None,
        on_promote_temporary=lambda *args: None,
        on_privacy_save=lambda *args: None,
        preparation_summary=summary,
        on_retry_all_failed=lambda: None,
        show_preparation_progress=False,
    )

    retry_calls = [call for call in mock_st.calls if call[0] == "button" and call[2] == "wsc_retry_all_failed_sources"]
    assert len(retry_calls) == 1


def test_workspace_chat_renders_the_shared_preparation_banner_only_once():
    app_tree = ast.parse(Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8"))
    document_manager_calls = [
        node
        for node in ast.walk(app_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "render_document_manager"
        and any(keyword.arg == "preparation_summary" for keyword in node.keywords)
    ]

    assert len(document_manager_calls) == 1
    progress_flag = next(
        keyword.value
        for keyword in document_manager_calls[0].keywords
        if keyword.arg == "show_preparation_progress"
    )
    assert isinstance(progress_flag, ast.Constant) and progress_flag.value is False


@pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
def test_render_document_manager_readiness_badges(mock_st, locale: str):
    nb_src = [NotebookSource(id="src_1", notebook_id="nb_1", title="Doc 1", source_type="pdf", content_preview="Preview 1")]
    tmp_src = [TemporaryConversationSource(id="tmp_1", conversation_id="conv_1", title="Doc 2", source_type="txt", content_preview="Preview 2")]
    prep_summary = {
        "total": 2,
        "ready": 1,
        "processing": 0,
        "pending": 0,
        "failed": 1,
        "bge_available": True,
        "statuses": {"notebook:src_1": "ready", "temporary:tmp_1": "failed"},
        "errors": {"temporary:tmp_1": "File corrupted"},
    }
    retried_sources = []
    render_document_manager(
        notebook_sources=nb_src,
        temporary_sources=tmp_src,
        selections_map={("notebook", "src_1"): True, ("temporary", "tmp_1"): True},
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_delete_source=lambda *a: None,
        on_delete_sources=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        preparation_summary=prep_summary,
        on_retry_source=lambda sc, sid: retried_sources.append((sc, sid)),
        locale=locale,
    )
    all_captions = [c[1] for c in mock_st.calls if c[0] == "caption"]
    assert any(t("status_ready", locale=locale) in c for c in all_captions)
    assert not any("File corrupted" in c for c in all_captions)
    assert any(t("document_preparation_status_label", locale=locale) in c for c in all_captions)


@pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
def test_render_ai_answer_header_truthful_provenance_and_model_separation(mock_st, locale: str):
    """Verifies truthful provenance header separating Bridge, Provider, and Model status."""
    # 1. Test unverified/suppressed model alias (e.g. antigravity-brain-pro)
    render_ai_answer_header(
        source_count=2,
        source_titles=["Doc A", "Doc B"],
        ai_source="Antigravity IDE",
        model_tool_name="antigravity-brain-pro",  # fake model name should be suppressed
        operational_mode="direct",
        provider_name="Gemini Web (Ẩn danh)",
        locale=locale,
    )
    all_success = [c[1] for c in mock_st.calls if c[0] == "success"]
    all_captions = [c[1] for c in mock_st.calls if c[0] == "caption"]

    # Bridge & Provider separation
    assert any(t("sidecar_direct", locale=locale) in s for s in all_success)
    assert any(t("gemini_web_anonymous", locale=locale) in s for s in all_success)

    # Model status: must be localized 'model_unverified', NOT internal alias
    assert any(t("model_unverified", locale=locale) in c for c in all_captions)
    assert not any("antigravity-brain-pro" in c for c in all_captions)
    assert any(t("ai_disclaimer", locale=locale) in c for c in all_captions)


@pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
def test_render_ai_answer_header_verified_model_display(mock_st, locale: str):
    """Verifies that an authentic verified model name is displayed cleanly."""
    render_ai_answer_header(
        source_count=1,
        source_titles=["Doc A"],
        ai_source="Antigravity IDE",
        model_tool_name="claude-3-5-sonnet",
        operational_mode="handoff",
        provider_name="Gemini Web (Ẩn danh)",
        locale=locale,
    )
    all_success = [c[1] for c in mock_st.calls if c[0] == "success"]
    all_captions = [c[1] for c in mock_st.calls if c[0] == "caption"]

    assert any(t("sidecar_handoff", locale=locale) in s for s in all_success)
    assert any("claude-3-5-sonnet" in c for c in all_captions)
    assert not any(t("model_unverified", locale=locale) in c for c in all_captions)


@pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
def test_render_ai_answer_header_grouped_duplicate_titles(mock_st, locale: str):
    render_ai_answer_header(
        source_count=3,
        source_titles=["Hướng dẫn sử dụng.pdf", "Hướng dẫn sử dụng.pdf", "Báo cáo tài chính.xlsx"],
        ai_source="Antigravity IDE",
        operational_mode="direct",
        locale=locale,
    )
    write_calls = [c[1] for c in mock_st.calls if c[0] == "write"]
    expected_count_header = f"{t('sources_sent', locale=locale)}: 2 (3)"
    assert any(expected_count_header in w for w in write_calls)
    assert any("Hướng dẫn sử dụng.pdf" in w for w in write_calls)
    assert any("Báo cáo tài chính.xlsx" in w for w in write_calls)


@pytest.mark.parametrize("locale", ["vi", "ja", "zh-CN"])
def test_render_grouped_evidence_items_multilingual(mock_st, locale: str):
    """Verifies evidence grouping: 'Hướng dẫn sử dụng' has exactly 2 excerpts, 'Báo cáo tài chính' has 1."""
    evidence_items = [
        {"title": "Hướng dẫn sử dụng", "location_info": "Trang 1", "text": "Đoạn 1 nội dung quy trình"},
        {"title": "Hướng dẫn sử dụng", "location_info": "Trang 3", "text": "Đoạn 2 nội dung vận hành"},
        {"title": "Báo cáo tài chính", "location_info": "Mục 2", "text": "Đoạn 3 số liệu tài chính"},
    ]
    render_grouped_evidence_items(evidence_items, conversation_id="conv_1", locale=locale)

    expander_calls = [c[1] for c in mock_st.calls if c[0] == "expander"]
    expected_expander_label = f"🔍 {t('evidence_snippets_detail', locale=locale)} (3)"
    assert any(expected_expander_label in exp for exp in expander_calls)

    markdown_calls = [c[1] for c in mock_st.calls if c[0] == "markdown"]
    assert any("📄 **Hướng dẫn sử dụng** · *2*" in m for m in markdown_calls)
    assert any("📄 **Báo cáo tài chính** · *1*" in m for m in markdown_calls)

    text_area_values = [c[2] for c in mock_st.calls if c[0] == "text_area"]
    assert "Đoạn 1 nội dung quy trình" in text_area_values
    assert "Đoạn 2 nội dung vận hành" in text_area_values
    assert "Đoạn 3 số liệu tài chính" in text_area_values


def test_forbidden_words_not_in_owner_facing_ui(mock_st):
    nb_src = [NotebookSource(id="src_1", notebook_id="nb_1", title="Doc 1", source_type="pdf", content_preview="Preview 1")]
    tmp_src = [TemporaryConversationSource(id="tmp_1", conversation_id="conv_1", title="Doc 2", source_type="txt", content_preview="Preview 2")]
    render_source_library(
        notebook_sources=nb_src,
        temp_sources=tmp_src,
        selections_map={("notebook", "src_1"): True, ("temporary", "tmp_1"): False},
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        locale="vi",
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None]).lower()
    for word in FORBIDDEN_WORDS:
        assert word.lower() not in all_text, f"Forbidden word '{word}' found in owner-facing output copy"
