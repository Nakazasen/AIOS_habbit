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

def test_init_chat_store_defaults():
    nbs = store.load_notebooks()
    assert len(nbs) == 4
    ids = [n.id for n in nbs]
    assert "mom_opcenter" in ids
    assert "interstock_wms" in ids
    assert "email_jp_vn" in ids
    assert "aios_project" in ids

def test_notebook_persistence():
    nb = DocumentNotebook(id="custom_nb", title="My Custom Notebook", description="Custom desc")
    store.save_notebook(nb)
    
    loaded = store.load_notebook("custom_nb")
    assert loaded is not None
    assert loaded.title == "My Custom Notebook"
    assert loaded.description == "Custom desc"

def test_conversation_persistence():
    conv = WorkspaceConversation(id="conv_123", notebook_id="mom_opcenter", title="First Conversation")
    store.save_conversation(conv)
    
    loaded = store.load_conversation("conv_123")
    assert loaded is not None
    assert loaded.title == "First Conversation"
    assert loaded.notebook_id == "mom_opcenter"
    
    # Test rename
    store.rename_conversation("conv_123", "Renamed Conversation")
    loaded2 = store.load_conversation("conv_123")
    assert loaded2.title == "Renamed Conversation"

def test_messages_persistence():
    msg = ChatMessage(id="msg_1", conversation_id="conv_123", role="user", content="Hello store")
    store.save_message(msg)
    
    msgs = store.load_messages("conv_123")
    assert len(msgs) == 1
    assert msgs[0].content == "Hello store"

def test_temporary_sources_persistence():
    long_log = "Error in line 1: DB connection failed.\n" * 10
    ts = TemporaryConversationSource(
        id="src_99",
        conversation_id="conv_123",
        source_type="pasted_text",
        title="My Temp Log",
        content_preview=long_log[:150],
        content_text=long_log
    )
    store.save_temporary_source(ts)
    
    sources = store.load_temporary_sources("conv_123")
    assert len(sources) == 1
    assert sources[0].title == "My Temp Log"
    assert sources[0].content_text == long_log
    assert len(sources[0].content_preview) == 150
    assert len(sources[0].content_preview) < len(sources[0].content_text)

