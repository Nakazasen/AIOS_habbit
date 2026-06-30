import pytest
from pathlib import Path
import aios_habit.workspace_chat_store as store
from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
    ChatMessage,
    TemporaryConversationSource
)

@pytest.fixture(autouse=True)
def setup_test_store(tmp_path, monkeypatch):
    test_dir = tmp_path / "workspace_chat"
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(store, "NOTEBOOKS_FILE", test_dir / "notebooks.jsonl")
    monkeypatch.setattr(store, "CONVERSATIONS_FILE", test_dir / "conversations.jsonl")
    monkeypatch.setattr(store, "MESSAGES_FILE", test_dir / "messages.jsonl")
    monkeypatch.setattr(store, "TEMPORARY_SOURCES_FILE", test_dir / "temporary_sources.jsonl")
    store.init_chat_store()

def test_owner_multiple_conversations_in_notebook():
    # 1. Open default notebook MOM / Opcenter
    nb = store.load_notebook("mom_opcenter")
    assert nb is not None
    assert nb.title == "MOM / Opcenter"
    
    # 2. Create multiple conversations in it
    conv1 = WorkspaceConversation(id="conv_a", notebook_id="mom_opcenter", title="Lỗi Manual Supply")
    conv2 = WorkspaceConversation(id="conv_b", notebook_id="mom_opcenter", title="Họp thiết kế")
    store.save_conversation(conv1)
    store.save_conversation(conv2)
    
    # 3. Retrieve all conversations for MOM / Opcenter
    convs = store.load_conversations("mom_opcenter")
    assert len(convs) == 2
    titles = [c.title for c in convs]
    assert "Lỗi Manual Supply" in titles
    assert "Họp thiết kế" in titles

def test_owner_conversation_scoped_temporary_source():
    # 1. Create two conversations
    conv1 = WorkspaceConversation(id="conv_a", notebook_id="mom_opcenter", title="Conv A")
    conv2 = WorkspaceConversation(id="conv_b", notebook_id="mom_opcenter", title="Conv B")
    store.save_conversation(conv1)
    store.save_conversation(conv2)
    
    # 2. Add temporary source to Conv A (e.g. pasted log)
    src_a = TemporaryConversationSource(
        id="src_log_a",
        conversation_id="conv_a",
        source_type="pasted_text",
        title="Opcenter log error",
        content_preview="Log contents..."
    )
    store.save_temporary_source(src_a)
    
    # 3. Retrieve temporary sources for Conv A and Conv B
    sources_a = store.load_temporary_sources("conv_a")
    sources_b = store.load_temporary_sources("conv_b")
    
    # Verify temporary source is in Conv A, not Conv B
    assert len(sources_a) == 1
    assert sources_a[0].title == "Opcenter log error"
    assert sources_a[0].status == "conversation_only"  # equivalent to 'Chưa lưu lâu dài'
    assert len(sources_b) == 0
    
    # 4. Simulate reload (reopening conversation) and verify source is still there
    reloaded_sources_a = store.load_temporary_sources("conv_a")
    assert len(reloaded_sources_a) == 1
    assert reloaded_sources_a[0].title == "Opcenter log error"

def test_owner_open_notebook_state_transition(monkeypatch):
    import streamlit as st
    
    class MockSessionState(dict):
        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError:
                raise AttributeError(name)
        def __setattr__(self, name, value):
            self[name] = value

    session_state = MockSessionState()
    monkeypatch.setattr(st, "session_state", session_state)
    
    # Mock st.rerun
    rerun_called = []
    def mock_rerun():
        rerun_called.append(True)
    monkeypatch.setattr(st, "rerun", mock_rerun)
    
    # Import callback from app
    from aios_habit.workspace_chat_app import open_notebook_callback
    
    # Execute callback
    open_notebook_callback("mom_opcenter")
    
    # Verify state transition
    assert session_state.wsc_active_notebook_id == "mom_opcenter"
    assert session_state.wsc_active_conversation_id is None
    assert session_state.wsc_show_save_placeholder is False
    assert session_state.wsc_show_explain_placeholder is False
    assert len(rerun_called) == 1

