import pytest
import streamlit as st
from aios_habit.workspace_chat_ui import (
    render_source_status,
    render_source_library
)
from aios_habit.workspace_chat_models import NotebookSource, TemporaryConversationSource

FORBIDDEN_WORDS = [
    "RAG", "vector", "embedding", "chunk", "retrieval", "citation", "claim",
    "provider router", "Mermaid", "prompt pack", "Nguồn AIOS đã dùng", "Nguồn chứng minh"
]

class MockSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)
    def __setattr__(self, name, value):
        self[name] = value

class MockStreamlit:
    def __init__(self):
        self.calls = []
        self.widget_states = {}
        self.session_state = MockSessionState()

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
        return [MockColumn() for _ in range(spec)]

    def warning(self, text, *args, **kwargs):
        self.calls.append(("warning", str(text), None, None))

@pytest.fixture
def mock_st(monkeypatch):
    mock = MockStreamlit()
    monkeypatch.setattr(st, "subheader", mock.subheader)
    monkeypatch.setattr(st, "write", mock.write)
    monkeypatch.setattr(st, "markdown", mock.markdown)
    monkeypatch.setattr(st, "info", mock.info)
    monkeypatch.setattr(st, "caption", mock.caption)
    monkeypatch.setattr(st, "checkbox", mock.checkbox)
    monkeypatch.setattr(st, "button", mock.button)
    monkeypatch.setattr(st, "container", mock.container)
    monkeypatch.setattr(st, "expander", mock.expander)
    monkeypatch.setattr(st, "text_input", mock.text_input)
    monkeypatch.setattr(st, "columns", mock.columns)
    monkeypatch.setattr(st, "warning", mock.warning)
    monkeypatch.setattr(st, "session_state", mock.session_state)
    return mock

def test_render_source_status():
    assert render_source_status("ready") == "Sẵn sàng"
    assert render_source_status("preview_only") == "Chỉ xem trước"
    assert render_source_status("failed") == "Lỗi"
    # Scopes/technical names should return empty string
    assert render_source_status("notebook") == ""
    assert render_source_status("temporary") == ""
    assert render_source_status("conversation_only") == ""
    assert render_source_status("added_to_notebook") == ""
    assert render_source_status("SRC-12345") == ""

def test_source_summary_0_sources(mock_st):
    render_source_library(
        notebook_sources=[],
        temp_sources=[],
        selections_map={},
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_bulk_toggle=lambda *a: None,
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None])
    assert "Đang bật 0 nguồn cho câu hỏi" in all_text
    assert "Không có nguồn phù hợp với bộ lọc hiện tại." in all_text
    for word in FORBIDDEN_WORDS:
        assert word.lower() not in all_text.lower()

def test_source_summary_notebook_only(mock_st):
    notebook_sources = [
        NotebookSource(id="src_1", notebook_id="nb_1", title="Title 1", source_type="txt", content_preview=""),
        NotebookSource(id="src_2", notebook_id="nb_1", title="Title 2", source_type="txt", content_preview="")
    ]
    selections_map = {("notebook", "src_1"): True, ("notebook", "src_2"): True}
    render_source_library(
        notebook_sources=notebook_sources,
        temp_sources=[],
        selections_map=selections_map,
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_bulk_toggle=lambda *a: None,
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None])
    assert "Đang bật 2 nguồn cho câu hỏi" in all_text
    assert "Title 1" in all_text
    assert "Title 2" in all_text
    for word in FORBIDDEN_WORDS:
        assert word.lower() not in all_text.lower()

def test_source_summary_temporary_only(mock_st):
    temp_sources = [
        TemporaryConversationSource(id="temp_1", conversation_id="conv_1", title="Temp Title 1", source_type="txt", content_preview=""),
        TemporaryConversationSource(id="temp_2", conversation_id="conv_1", title="Temp Title 2", source_type="txt", content_preview="")
    ]
    selections_map = {("temporary", "temp_1"): True, ("temporary", "temp_2"): False}
    render_source_library(
        notebook_sources=[],
        temp_sources=temp_sources,
        selections_map=selections_map,
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_bulk_toggle=lambda *a: None,
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None])
    assert "Đang bật 1 nguồn cho câu hỏi" in all_text
    assert "Temp Title 1" in all_text
    assert "Temp Title 2" in all_text
    for word in FORBIDDEN_WORDS:
        assert word.lower() not in all_text.lower()

def test_source_summary_both(mock_st):
    notebook_sources = [NotebookSource(id="src_1", notebook_id="nb_1", title="Title 1", source_type="txt", content_preview="")]
    temp_sources = [TemporaryConversationSource(id="temp_1", conversation_id="conv_1", title="Temp Title 1", source_type="txt", content_preview="")]
    selections_map = {("notebook", "src_1"): True, ("temporary", "temp_1"): True}
    render_source_library(
        notebook_sources=notebook_sources,
        temp_sources=temp_sources,
        selections_map=selections_map,
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_bulk_toggle=lambda *a: None,
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None])
    assert "Đang bật 2 nguồn cho câu hỏi" in all_text
    assert "Title 1" in all_text
    assert "Temp Title 1" in all_text

def test_render_notebook_source_list_empty(mock_st):
    render_source_library(
        notebook_sources=[],
        temp_sources=[],
        selections_map={},
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_bulk_toggle=lambda *a: None,
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None])
    assert "📚 Thư viện nguồn" in all_text
    assert "Không có nguồn phù hợp với bộ lọc hiện tại." in all_text

def test_render_notebook_source_list_with_items(mock_st):
    notebook_sources = [
        NotebookSource(id="src_1", notebook_id="nb_1", title="Opcenter Checklist", source_type="txt", content_preview="Some opcenter checks")
    ]
    selections_map = {("notebook", "src_1"): True}
    render_source_library(
        notebook_sources=notebook_sources,
        temp_sources=[],
        selections_map=selections_map,
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_bulk_toggle=lambda *a: None,
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None])
    assert "Opcenter Checklist" in all_text
    assert "Some opcenter checks" in all_text
    assert "Trong sổ" in all_text
    assert "Đang bật" in all_text

    checkbox_calls = [c for c in mock_st.calls if c[0] == "checkbox"]
    assert checkbox_calls[0][1] == "Chỉ hiển thị nguồn đang bật"
    assert checkbox_calls[1][1] == "Bật nguồn này cho cuộc trò chuyện"
    assert checkbox_calls[1][3] == "wsc_toggle_notebook_conv_1_src_1"

def test_render_temporary_source_list_empty(mock_st):
    render_source_library(
        notebook_sources=[],
        temp_sources=[],
        selections_map={},
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_bulk_toggle=lambda *a: None,
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None])
    assert "Không có nguồn phù hợp với bộ lọc hiện tại." in all_text

def test_render_temporary_source_list_with_items(mock_st):
    temp_sources = [
        TemporaryConversationSource(id="temp_1", conversation_id="conv_1", title="Temp Title 1", source_type="txt", content_preview="Temp Preview 1", status="conversation_only", long_term_saved=False)
    ]
    selections_map = {("temporary", "temp_1"): False}
    render_source_library(
        notebook_sources=[],
        temp_sources=temp_sources,
        selections_map=selections_map,
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_bulk_toggle=lambda *a: None,
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None])
    assert "Temp Title 1" in all_text
    assert "Temp Preview 1" in all_text
    assert "Tạm trong cuộc trò chuyện" in all_text
    assert "Đang tắt" in all_text

    button_calls = [c for c in mock_st.calls if c[0] == "button"]
    button_labels = [c[1] for c in button_calls]
    assert "Thêm vào sổ tài liệu" in button_labels

def test_no_forbidden_words_in_generated_copy(mock_st):
    notebook_sources = [NotebookSource(id="src_1", notebook_id="nb_1", title="Title 1", source_type="txt", content_preview="")]
    temp_sources = [TemporaryConversationSource(id="temp_1", conversation_id="conv_1", title="Temp Title 1", source_type="txt", content_preview="")]
    selections_map = {("notebook", "src_1"): True, ("temporary", "temp_1"): True}
    render_source_library(
        notebook_sources=notebook_sources,
        temp_sources=temp_sources,
        selections_map=selections_map,
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_bulk_toggle=lambda *a: None,
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None]).lower()
    for word in FORBIDDEN_WORDS:
        assert word.lower() not in all_text, f"Forbidden word '{word}' found in owner-facing output copy"
