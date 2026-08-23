import pytest
import streamlit as st
from aios_habit.workspace_chat_ui import (
    render_source_status,
    render_source_library
)
from aios_habit.workspace_chat_models import NotebookSource, TemporaryConversationSource

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

    def error(self, text, *args, **kwargs):
        self.calls.append(("error", str(text), None, None))

    def text_area(self, label, value="", *args, **kwargs):
        self.calls.append(("text_area", str(label), value, None))
        return value

    def divider(self):
        self.calls.append(("divider", None, None, None))

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
    monkeypatch.setattr(st, "success", mock.success)
    monkeypatch.setattr(st, "error", mock.error)
    monkeypatch.setattr(st, "text_area", mock.text_area)
    monkeypatch.setattr(st, "divider", mock.divider)
    monkeypatch.setattr(st, "session_state", mock.session_state)
    return mock

def test_render_source_status():
    assert render_source_status("ready") == "Sẵn sàng"
    assert render_source_status("unavailable") == "BGE-M3 chưa sẵn sàng"
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
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None])
    assert "Đang bật 0 nguồn cho câu hỏi" in all_text
    assert "Chưa có nguồn tài liệu." in all_text
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
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None])
    assert "📚 Thư viện nguồn" in all_text
    assert "Chưa có nguồn tài liệu." in all_text

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
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None])
    assert "Opcenter Checklist" in all_text
    assert "Trong sổ" in all_text
    assert "Đang bật" in all_text

    checkbox_calls = [c for c in mock_st.calls if c[0] == "checkbox"]
    assert checkbox_calls[0][1] == "Bật nguồn này cho cuộc trò chuyện"
    assert checkbox_calls[0][3] == "wsc_toggle_notebook_conv_1_src_1"

def test_render_temporary_source_list_empty(mock_st):
    render_source_library(
        notebook_sources=[],
        temp_sources=[],
        selections_map={},
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None])
    assert "Chưa có nguồn tài liệu." in all_text

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
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None])
    assert "Temp Title 1" in all_text
    assert "Temp Preview 1" in all_text
    assert "Tạm trong cuộc trò chuyện" in all_text
    assert "Đã tắt" in all_text

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
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls if c[1] is not None]).lower()
    for word in FORBIDDEN_WORDS:
        assert word.lower() not in all_text, f"Forbidden word '{word}' found in owner-facing output copy"


def test_render_preparation_progress_bar_all_ready(mock_st):
    from aios_habit.workspace_chat_ui import render_preparation_progress_bar
    summary = {
        "total": 5,
        "ready": 5,
        "processing": 0,
        "pending": 0,
        "failed": 0,
        "summary_text": "BGE-M3: 5/5 tài liệu đã sẵn sàng",
    }
    render_preparation_progress_bar(summary)
    success_calls = [c[1] for c in mock_st.calls if c[0] == "success"]
    assert len(success_calls) == 1
    assert "BGE-M3: 5/5 tài liệu đã sẵn sàng" in success_calls[0]


def test_render_preparation_progress_bar_with_failures(mock_st):
    from aios_habit.workspace_chat_ui import render_preparation_progress_bar
    summary = {
        "total": 5,
        "ready": 3,
        "processing": 0,
        "pending": 0,
        "failed": 2,
        "summary_text": "BGE-M3: 3/5 sẵn sàng · 2 lỗi",
    }
    retried = []
    render_preparation_progress_bar(summary, on_retry_all_failed=lambda: retried.append(True))
    warning_calls = [c[1] for c in mock_st.calls if c[0] == "warning"]
    assert len(warning_calls) == 1
    assert "BGE-M3: 3/5 sẵn sàng · 2 lỗi" in warning_calls[0]
    button_calls = [c[1] for c in mock_st.calls if c[0] == "button"]
    assert any("Thử lại các lỗi" in b for b in button_calls)


def test_render_document_manager_readiness_badges(mock_st):
    from aios_habit.workspace_chat_ui import render_document_manager
    nb_src = [NotebookSource(id="src_1", notebook_id="nb_1", title="Doc 1", source_type="pdf", content_preview="Preview 1")]
    tmp_src = [TemporaryConversationSource(id="tmp_1", conversation_id="conv_1", title="Doc 2", source_type="txt", content_preview="Preview 2")]
    prep_summary = {
        "total": 2,
        "ready": 1,
        "processing": 0,
        "pending": 0,
        "failed": 1,
        "summary_text": "BGE-M3: 1/2 sẵn sàng · 1 lỗi",
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
    )
    all_captions = [c[1] for c in mock_st.calls if c[0] == "caption"]
    assert any("BGE-M3:** Sẵn sàng" in c for c in all_captions)
    assert any("BGE-M3:** Lỗi đọc tài liệu (File corrupted)" in c for c in all_captions)


def test_render_ai_answer_header_truthful_provenance(mock_st):
    from aios_habit.workspace_chat_ui import render_ai_answer_header
    render_ai_answer_header(
        source_count=2,
        source_titles=["Doc A", "Doc B"],
        ai_source="Antigravity IDE",
        model_tool_name="antigravity-brain-pro",  # fake model name should be suppressed
        operational_mode="direct",
        provider_name="Gemini Web (Nặc danh)",
    )
    all_success = [c[1] for c in mock_st.calls if c[0] == "success"]
    all_captions = [c[1] for c in mock_st.calls if c[0] == "caption"]

    assert any("Cầu nối:** `Sidecar (Trực tiếp)`" in s for s in all_success)
    assert any("Nhà cung cấp:** `Gemini Web (Nặc danh)`" in s for s in all_success)
    assert not any("antigravity-brain-pro" in c for c in all_captions)
    assert any("Gemini Web Stream (Chưa xác minh định danh)" in c for c in all_captions)


def test_render_grouped_evidence_items(mock_st):
    from aios_habit.workspace_chat_ui import render_grouped_evidence_items
    evidence_items = [
        {"title": "Hướng dẫn sử dụng", "location_info": "Trang 1", "text": "Đoạn 1 nội dung"},
        {"title": "Hướng dẫn sử dụng", "location_info": "Trang 3", "text": "Đoạn 2 nội dung"},
        {"title": "Báo cáo tài chính", "location_info": "Mục 2", "text": "Đoạn 3 tài chính"},
    ]
    render_grouped_evidence_items(evidence_items, conversation_id="conv_1")
    markdown_calls = [c[1] for c in mock_st.calls if c[0] == "markdown"]
    assert any("Hướng dẫn sử dụng** · *2 đoạn trích*" in m for m in markdown_calls)
    assert any("Báo cáo tài chính** · *1 đoạn trích*" in m for m in markdown_calls)


def test_render_ai_answer_header_grouped_duplicate_titles(mock_st):
    from aios_habit.workspace_chat_ui import render_ai_answer_header
    render_ai_answer_header(
        source_count=3,
        source_titles=["Hướng dẫn sử dụng.pdf", "Hướng dẫn sử dụng.pdf", "Báo cáo tài chính.xlsx"],
        ai_source="Antigravity IDE",
        operational_mode="direct",
    )
    write_calls = [c[1] for c in mock_st.calls if c[0] == "write"]
    assert any("2 tài liệu (3 đoạn trích)" in w for w in write_calls)
    assert any("Hướng dẫn sử dụng.pdf · *(2 đoạn trích)*" in w for w in write_calls)
    assert any("- Báo cáo tài chính.xlsx" in w for w in write_calls)
