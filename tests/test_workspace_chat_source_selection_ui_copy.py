import pytest
import streamlit as st
from aios_habit.workspace_chat_ui import (
    render_source_status,
    render_source_summary,
    render_notebook_source_list,
    render_temporary_source_list
)
from aios_habit.workspace_chat_models import NotebookSource, TemporaryConversationSource

FORBIDDEN_WORDS = [
    "RAG", "vector", "embedding", "chunk", "retrieval", "citation", "claim",
    "provider router", "Mermaid", "prompt pack", "Nguồn AIOS đã dùng", "Nguồn chứng minh"
]

class MockStreamlit:
    def __init__(self):
        self.calls = []
        
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
        return value

    def button(self, label, key=None, *args, **kwargs):
        self.calls.append(("button", str(label), key, None))
        return False

    def container(self):
        class MockContainer:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        return MockContainer()

@pytest.fixture
def mock_st(monkeypatch):
    mock = MockStreamlit()
    # Monkeypatch streamlit functions
    monkeypatch.setattr(st, "subheader", mock.subheader)
    monkeypatch.setattr(st, "write", mock.write)
    monkeypatch.setattr(st, "markdown", mock.markdown)
    monkeypatch.setattr(st, "info", mock.info)
    monkeypatch.setattr(st, "caption", mock.caption)
    monkeypatch.setattr(st, "checkbox", mock.checkbox)
    monkeypatch.setattr(st, "button", mock.button)
    monkeypatch.setattr(st, "container", mock.container)
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
    render_source_summary(0, 0)
    all_text = " ".join([c[1] for c in mock_st.calls])
    assert "Nguồn đang bật" in all_text
    assert "Chưa có nguồn nào đang bật." in all_text
    assert "Nguồn đang bật là những nguồn bạn đã chọn cho câu hỏi." in all_text
    for word in FORBIDDEN_WORDS:
        assert word.lower() not in all_text.lower()

def test_source_summary_notebook_only(mock_st):
    render_source_summary(3, 0)
    all_text = " ".join([c[1] for c in mock_st.calls])
    assert "Nguồn đang bật" in all_text
    assert "Tổng số nguồn đang bật: 3" in all_text
    assert "Số nguồn trong sổ đang bật: 3" in all_text
    assert "Số nguồn tạm đang bật: 0" in all_text
    assert "Chưa có nguồn nào đang bật." not in all_text
    assert "Nguồn đang bật là những nguồn bạn đã chọn cho câu hỏi." in all_text
    for word in FORBIDDEN_WORDS:
        assert word.lower() not in all_text.lower()

def test_source_summary_temporary_only(mock_st):
    render_source_summary(0, 4)
    all_text = " ".join([c[1] for c in mock_st.calls])
    assert "Nguồn đang bật" in all_text
    assert "Tổng số nguồn đang bật: 4" in all_text
    assert "Số nguồn trong sổ đang bật: 0" in all_text
    assert "Số nguồn tạm đang bật: 4" in all_text
    assert "Chưa có nguồn nào đang bật." not in all_text
    assert "Nguồn đang bật là những nguồn bạn đã chọn cho câu hỏi." in all_text
    for word in FORBIDDEN_WORDS:
        assert word.lower() not in all_text.lower()

def test_source_summary_both(mock_st):
    render_source_summary(2, 5)
    all_text = " ".join([c[1] for c in mock_st.calls])
    assert "Nguồn đang bật" in all_text
    assert "Tổng số nguồn đang bật: 7" in all_text
    assert "Số nguồn trong sổ đang bật: 2" in all_text
    assert "Số nguồn tạm đang bật: 5" in all_text
    assert "Chưa có nguồn nào đang bật." not in all_text
    assert "Nguồn đang bật là những nguồn bạn đã chọn cho câu hỏi." in all_text
    for word in FORBIDDEN_WORDS:
        assert word.lower() not in all_text.lower()

def test_render_notebook_source_list_empty(mock_st):
    render_notebook_source_list([], {}, lambda *a: None, "conv_1")
    all_text = " ".join([c[1] for c in mock_st.calls])
    assert "Nguồn trong sổ" in all_text
    assert "Chưa có nguồn trong sổ." in all_text
    assert "Nguồn trong sổ được giữ lại để dùng trong nhiều cuộc trò chuyện." in all_text

def test_render_notebook_source_list_with_items(mock_st):
    srcs = [
        NotebookSource(id="src_1", notebook_id="nb_1", title="Title 1", source_type="pasted_text", content_preview="Preview 1"),
        NotebookSource(id="src_2", notebook_id="nb_1", title="Title 2", source_type="pasted_text", content_preview="Preview 2", extraction_status="failed")
    ]
    selections = {"src_1": True, "src_2": False}
    
    render_notebook_source_list(srcs, selections, lambda *a: None, "conv_1")
    all_text = " ".join([c[1] for c in mock_st.calls])
    assert "Title 1" in all_text
    assert "Preview: Preview 1" in all_text
    assert "Trạng thái: Sẵn sàng" in all_text
    assert "Title 2" in all_text
    assert "Trạng thái: Lỗi" in all_text
    
    checkbox_keys = [c[3] for c in mock_st.calls if c[0] == "checkbox"]
    assert "wsc_source_notebook_conv_1_src_1" in checkbox_keys
    assert "wsc_source_notebook_conv_1_src_2" in checkbox_keys

def test_render_temporary_source_list_empty(mock_st):
    render_temporary_source_list([], {}, lambda *a: None, lambda *a: None, "conv_1")
    all_text = " ".join([c[1] for c in mock_st.calls])
    assert "Nguồn tạm trong cuộc trò chuyện" in all_text
    assert "Chưa có nguồn tạm trong cuộc trò chuyện này." in all_text
    assert "Nguồn tạm chỉ thuộc cuộc trò chuyện hiện tại." in all_text

def test_render_temporary_source_list_with_items(mock_st):
    srcs = [
        TemporaryConversationSource(id="temp_1", conversation_id="conv_1", title="Temp Title 1", source_type="pasted_text", content_preview="Temp Preview 1", status="conversation_only", long_term_saved=False),
        TemporaryConversationSource(id="temp_2", conversation_id="conv_1", title="Temp Title 2", source_type="pasted_text", content_preview="Temp Preview 2", status="added_to_notebook", long_term_saved=True)
    ]
    selections = {"temp_1": True, "temp_2": False}
    
    render_temporary_source_list(srcs, selections, lambda *a: None, lambda *a: None, "conv_1")
    all_text = " ".join([c[1] for c in mock_st.calls])
    assert "Temp Title 1" in all_text
    assert "Temp Preview 1" in all_text
    
    checkbox_keys = [c[3] for c in mock_st.calls if c[0] == "checkbox"]
    assert "wsc_source_temporary_conv_1_temp_1" in checkbox_keys
    
    button_keys = [c[2] for c in mock_st.calls if c[0] == "button"]
    assert "wsc_promote_temporary_conv_1_temp_1" in button_keys
    assert "Đã thêm vào sổ tài liệu" in all_text
    assert "wsc_promote_temporary_conv_1_temp_2" not in button_keys

def test_no_forbidden_words_in_generated_copy(mock_st):
    render_source_summary(1, 1)
    render_notebook_source_list([NotebookSource(id="src_1", notebook_id="nb_1", title="Title 1", source_type="pasted_text")], {"src_1": True}, lambda *a: None, "conv_1")
    render_temporary_source_list([TemporaryConversationSource(id="temp_1", conversation_id="conv_1", title="Temp Title 1", source_type="pasted_text", content_preview="Temp Preview 1")], {"temp_1": True}, lambda *a: None, lambda *a: None, "conv_1")
    
    all_text = " ".join([c[1] for c in mock_st.calls]).lower()
    for word in FORBIDDEN_WORDS:
        assert word.lower() not in all_text, f"Forbidden word '{word}' found in owner-facing output copy"
