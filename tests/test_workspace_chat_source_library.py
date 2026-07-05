import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from pathlib import Path
import streamlit as st

from aios_habit.workspace_chat_models import (
    TemporaryConversationSource,
    NotebookSource,
    ConversationSourceSelection,
    DocumentNotebook,
    WorkspaceConversation,
    ChatMessage,
    SOURCE_SCOPE_TEMPORARY,
    SOURCE_SCOPE_NOTEBOOK
)
import aios_habit.workspace_chat_store as store
from aios_habit.workspace_chat_ui import render_source_library

@pytest.fixture
def temp_workspace(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        monkeypatch.setattr(store, "LOCAL_CHAT_DIR", tdp)
        monkeypatch.setattr(store, "TEMPORARY_SOURCES_FILE", tdp / "temporary_sources.jsonl")
        monkeypatch.setattr(store, "NOTEBOOK_SOURCES_FILE", tdp / "notebook_sources.jsonl")
        monkeypatch.setattr(store, "SOURCE_SELECTIONS_FILE", tdp / "conversation_source_selections.jsonl")
        monkeypatch.setattr(store, "NOTEBOOKS_FILE", tdp / "notebooks.jsonl")
        monkeypatch.setattr(store, "CONVERSATIONS_FILE", tdp / "conversations.jsonl")
        monkeypatch.setattr(store, "MESSAGES_FILE", tdp / "messages.jsonl")
        store.init_chat_store()
        yield tdp

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
        self.calls.append(("subheader", str(text)))

    def write(self, text, *args, **kwargs):
        self.calls.append(("write", str(text)))

    def markdown(self, text, *args, **kwargs):
        self.calls.append(("markdown", str(text)))

    def info(self, text, *args, **kwargs):
        self.calls.append(("info", str(text)))

    def caption(self, text, *args, **kwargs):
        self.calls.append(("caption", str(text)))

    def checkbox(self, label, value=False, key=None, on_change=None, *args, **kwargs):
        self.calls.append(("checkbox", str(label), value, key, on_change))
        if key in self.widget_states:
            return self.widget_states[key]
        return value

    def expander(self, label, expanded=False, *args, **kwargs):
        self.calls.append(("expander", str(label), expanded))
        class MockExpander:
            def __enter__(self): return self
            def __exit__(self, exc_type, exc_val, exc_tb): pass
        return MockExpander()

    def button(self, label, key=None, *args, **kwargs):
        self.calls.append(("button", str(label), key))
        if key in self.widget_states:
            return self.widget_states[key]
        return False

    def text_input(self, label, value="", placeholder=None, key=None, *args, **kwargs):
        self.calls.append(("text_input", str(label), value, placeholder, key))
        if key in self.widget_states:
            return self.widget_states[key]
        return value

    def columns(self, spec):
        class MockColumn:
            def __enter__(self): return self
            def __exit__(self, exc_type, exc_val, exc_tb): pass
        return [MockColumn() for _ in range(spec)]

    def warning(self, text, *args, **kwargs):
        self.calls.append(("warning", str(text)))

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
    monkeypatch.setattr(st, "container", lambda *a, **k: MagicMock())
    monkeypatch.setattr(st, "expander", mock.expander)
    monkeypatch.setattr(st, "text_input", mock.text_input)
    monkeypatch.setattr(st, "columns", mock.columns)
    monkeypatch.setattr(st, "warning", mock.warning)
    monkeypatch.setattr(st, "session_state", mock.session_state)
    return mock

def test_delete_temporary_source(temp_workspace):
    ts1 = TemporaryConversationSource(id="TS1", conversation_id="C1", source_type="txt", title="1", content_preview="")
    ts2 = TemporaryConversationSource(id="TS2", conversation_id="C1", source_type="txt", title="2", content_preview="")
    store.save_temporary_source(ts1)
    store.save_temporary_source(ts2)
    store.set_source_enabled("C1", SOURCE_SCOPE_TEMPORARY, "TS1", True)
    store.set_source_enabled("C1", SOURCE_SCOPE_TEMPORARY, "TS2", True)
    
    assert store.delete_temporary_source("TS1") is True
    sources = store.load_all_temporary_sources()
    assert len(sources) == 1
    assert sources[0].id == "TS2"
    selections = store.load_all_conversation_source_selections()
    assert len(selections) == 1
    assert selections[0].source_id == "TS2"

def test_delete_notebook_source(temp_workspace):
    ns1 = NotebookSource(id="NS1", notebook_id="NB1", source_type="txt", title="1", content_preview="")
    ns2 = NotebookSource(id="NS2", notebook_id="NB1", source_type="txt", title="2", content_preview="")
    store.save_notebook_source(ns1)
    store.save_notebook_source(ns2)
    store.set_source_enabled("C1", SOURCE_SCOPE_NOTEBOOK, "NS1", True)
    store.set_source_enabled("C1", SOURCE_SCOPE_NOTEBOOK, "NS2", True)
    
    assert store.delete_notebook_source("NS1") is True
    sources = store.load_all_notebook_sources()
    assert len(sources) == 1
    assert sources[0].id == "NS2"
    selections = store.load_all_conversation_source_selections()
    assert len(selections) == 1
    assert selections[0].source_id == "NS2"

def test_delete_temporary_source_preserves_parent_data(temp_workspace):
    nb = DocumentNotebook(id="NB1", title="Notebook 1")
    conv = WorkspaceConversation(id="C1", notebook_id="NB1", title="Conv 1")
    msg = ChatMessage(id="M1", conversation_id="C1", role="user", content="hello", created_at="2026-07-04T00:00:00")
    store.save_notebook(nb)
    store.save_conversation(conv)
    store.save_message(msg)

    ts1 = TemporaryConversationSource(id="TS1", conversation_id="C1", source_type="txt", title="1", content_preview="")
    ts2 = TemporaryConversationSource(id="TS2", conversation_id="C1", source_type="txt", title="2", content_preview="")
    store.save_temporary_source(ts1)
    store.save_temporary_source(ts2)

    assert store.delete_temporary_source("TS1") is True
    
    assert len(store.load_notebooks()) > 0
    assert len(store.load_all_conversations()) == 1
    assert len(store.load_messages("C1")) == 1
    assert len(store.load_all_temporary_sources()) == 1
    assert store.load_all_temporary_sources()[0].id == "TS2"

def test_delete_notebook_source_preserves_parent_data(temp_workspace):
    nb = DocumentNotebook(id="NB1", title="Notebook 1")
    conv = WorkspaceConversation(id="C1", notebook_id="NB1", title="Conv 1")
    msg = ChatMessage(id="M1", conversation_id="C1", role="user", content="hello", created_at="2026-07-04T00:00:00")
    store.save_notebook(nb)
    store.save_conversation(conv)
    store.save_message(msg)

    ns1 = NotebookSource(id="NS1", notebook_id="NB1", source_type="txt", title="1", content_preview="")
    ns2 = NotebookSource(id="NS2", notebook_id="NB1", source_type="txt", title="2", content_preview="")
    store.save_notebook_source(ns1)
    store.save_notebook_source(ns2)

    assert store.delete_notebook_source("NS1") is True

    assert len(store.load_notebooks()) > 0
    assert len(store.load_all_conversations()) == 1
    assert len(store.load_messages("C1")) == 1
    assert len(store.load_all_notebook_sources()) == 1
    assert store.load_all_notebook_sources()[0].id == "NS2"

def test_delete_non_existent_source(temp_workspace):
    assert store.delete_temporary_source("NON_EXIST") is False
    assert store.delete_notebook_source("NON_EXIST") is False

def test_search_title_case_insensitive(mock_st):
    notebook_sources = [
        NotebookSource(id="src_1", notebook_id="nb_1", title="Opcenter SOP", source_type="txt", content_preview=""),
        NotebookSource(id="src_2", notebook_id="nb_1", title="WMS Guidelines", source_type="txt", content_preview="")
    ]
    mock_st.widget_states["wsc_search_conv_1"] = "opcenter"

    render_source_library(
        notebook_sources=notebook_sources,
        temp_sources=[],
        selections_map={},
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_bulk_toggle=lambda *a: None,
        on_delete_source=lambda *a: None,
    )
    all_text = " ".join([c[1] for c in mock_st.calls])
    assert "Opcenter SOP" in all_text
    assert "WMS Guidelines" not in all_text

def test_enabled_only_filter(mock_st):
    notebook_sources = [
        NotebookSource(id="src_1", notebook_id="nb_1", title="SOP 1", source_type="txt", content_preview=""),
        NotebookSource(id="src_2", notebook_id="nb_1", title="SOP 2", source_type="txt", content_preview="")
    ]
    selections_map = {("notebook", "src_1"): True, ("notebook", "src_2"): False}
    mock_st.widget_states["wsc_filter_enabled_conv_1"] = True

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
    all_text = " ".join([c[1] for c in mock_st.calls])
    assert "SOP 1" in all_text
    assert "SOP 2" not in all_text

def test_filtered_bulk_enable(mock_st):
    notebook_sources = [
        NotebookSource(id="src_1", notebook_id="nb_1", title="SOP 1", source_type="txt", content_preview=""),
        NotebookSource(id="src_2", notebook_id="nb_1", title="SOP 2", source_type="txt", content_preview="")
    ]
    mock_st.widget_states["wsc_search_conv_1"] = "SOP 1"
    mock_st.widget_states["wsc_bulk_enable_conv_1"] = True

    bulk_toggled = []
    def on_bulk_toggle(sources, enabled):
        bulk_toggled.append((sources, enabled))

    render_source_library(
        notebook_sources=notebook_sources,
        temp_sources=[],
        selections_map={},
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_bulk_toggle=on_bulk_toggle,
        on_delete_source=lambda *a: None,
    )
    assert len(bulk_toggled) == 1
    assert bulk_toggled[0][0] == [("notebook", "src_1")]
    assert bulk_toggled[0][1] is True

def test_filtered_bulk_disable(mock_st):
    notebook_sources = [
        NotebookSource(id="src_1", notebook_id="nb_1", title="SOP 1", source_type="txt", content_preview=""),
        NotebookSource(id="src_2", notebook_id="nb_1", title="SOP 2", source_type="txt", content_preview="")
    ]
    mock_st.widget_states["wsc_search_conv_1"] = "SOP 2"
    mock_st.widget_states["wsc_bulk_disable_conv_1"] = True

    bulk_toggled = []
    def on_bulk_toggle(sources, enabled):
        bulk_toggled.append((sources, enabled))

    render_source_library(
        notebook_sources=notebook_sources,
        temp_sources=[],
        selections_map={},
        conversation_id="conv_1",
        on_toggle_source=lambda *a: None,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_bulk_toggle=on_bulk_toggle,
        on_delete_source=lambda *a: None,
    )
    assert len(bulk_toggled) == 1
    assert bulk_toggled[0][0] == [("notebook", "src_2")]
    assert bulk_toggled[0][1] is False

def test_individual_toggle_callback(mock_st):
    notebook_sources = [
        NotebookSource(id="src_1", notebook_id="nb_1", title="SOP 1", source_type="txt", content_preview="")
    ]
    toggled = []
    def on_toggle_source(scope, source_id, enabled):
        toggled.append((scope, source_id, enabled))

    mock_st.widget_states["wsc_toggle_notebook_conv_1_src_1"] = True
    
    render_source_library(
        notebook_sources=notebook_sources,
        temp_sources=[],
        selections_map={},
        conversation_id="conv_1",
        on_toggle_source=on_toggle_source,
        on_promote_temporary=lambda *a: None,
        on_privacy_save=lambda *a: None,
        on_bulk_toggle=lambda *a: None,
        on_delete_source=lambda *a: None,
    )
    
    checkbox_calls = [c for c in mock_st.calls if c[0] == "checkbox" and c[3] == "wsc_toggle_notebook_conv_1_src_1"]
    assert len(checkbox_calls) == 1
    on_change_cb = checkbox_calls[0][4]
    
    mock_st.session_state["wsc_toggle_notebook_conv_1_src_1"] = True
    on_change_cb()
    
    assert len(toggled) == 1
    assert toggled[0] == ("notebook", "src_1", True)
