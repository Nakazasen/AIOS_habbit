import pytest
from pathlib import Path
import aios_habit.workspace_chat_store as store
from aios_habit.workspace_chat_models import (
    NotebookSource,
    ConversationSourceSelection,
    TemporaryConversationSource,
    SOURCE_SCOPE_NOTEBOOK,
    SOURCE_SCOPE_TEMPORARY
)

@pytest.fixture(autouse=True)
def setup_test_store(tmp_path, monkeypatch):
    test_dir = tmp_path / "workspace_chat"
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(store, "NOTEBOOKS_FILE", test_dir / "notebooks.jsonl")
    monkeypatch.setattr(store, "CONVERSATIONS_FILE", test_dir / "conversations.jsonl")
    monkeypatch.setattr(store, "MESSAGES_FILE", test_dir / "messages.jsonl")
    monkeypatch.setattr(store, "TEMPORARY_SOURCES_FILE", test_dir / "temporary_sources.jsonl")
    monkeypatch.setattr(store, "NOTEBOOK_SOURCES_FILE", test_dir / "notebook_sources.jsonl")
    monkeypatch.setattr(store, "SOURCE_SELECTIONS_FILE", test_dir / "conversation_source_selections.jsonl")
    store.init_chat_store()

def test_notebook_source_crud():
    # Save source
    src = NotebookSource(
        id="src_1",
        notebook_id="mom_opcenter",
        title="Báo cáo vận hành",
        source_type="pasted_text",
        content_preview="Nội dung tóm tắt",
        content_text="Nội dung đầy đủ của báo cáo vận hành Opcenter"
    )
    store.save_notebook_source(src)

    # Get source
    loaded = store.get_notebook_source("src_1")
    assert loaded is not None
    assert loaded.title == "Báo cáo vận hành"

    # List sources
    sources = store.load_notebook_sources("mom_opcenter")
    assert len(sources) == 1
    assert sources[0].id == "src_1"

    # Delete source
    assert store.delete_notebook_source("src_1") is True
    assert store.get_notebook_source("src_1") is None
    assert len(store.load_notebook_sources("mom_opcenter")) == 0

def test_conversation_source_selection():
    # Toggle enabled
    sel = store.set_source_enabled(
        conversation_id="conv_abc",
        source_scope=SOURCE_SCOPE_NOTEBOOK,
        source_id="src_1",
        enabled=True
    )
    assert sel.enabled is True
    assert sel.source_scope == SOURCE_SCOPE_NOTEBOOK

    # Retrieve selections
    selections = store.load_conversation_source_selections("conv_abc")
    assert len(selections) == 1
    assert selections[0].source_id == "src_1"
    assert selections[0].enabled is True

    # Retrieve enabled selections
    enabled = store.load_enabled_sources_for_conversation("conv_abc")
    assert len(enabled) == 1

    # Toggle disabled
    store.set_source_enabled(
        conversation_id="conv_abc",
        source_scope=SOURCE_SCOPE_NOTEBOOK,
        source_id="src_1",
        enabled=False
    )
    selections_disabled = store.load_conversation_source_selections("conv_abc")
    assert selections_disabled[0].enabled is False

    enabled_after = store.load_enabled_sources_for_conversation("conv_abc")
    assert len(enabled_after) == 0

def test_notebook_sources_not_auto_enabled_by_default():
    # Adding a notebook source should not auto-enable it for conversations
    src = NotebookSource(
        id="src_nb",
        notebook_id="mom_opcenter",
        title="Checklist",
        source_type="pasted_text"
    )
    store.save_notebook_source(src)

    # Selections should be empty for a new conversation
    selections = store.load_conversation_source_selections("conv_new")
    assert len(selections) == 0

def test_promote_temporary_source():
    # Save a temporary source
    temp_src = TemporaryConversationSource(
        id="temp_src_99",
        conversation_id="conv_abc",
        source_type="pasted_text",
        title="Lỗi vận hành manual",
        content_preview="ERROR: DB fail",
        content_text="Full trace stack of DB failure..."
    )
    store.save_temporary_source(temp_src)

    # Promote it
    nb_src = store.promote_temporary_source_to_notebook(
        conversation_id="conv_abc",
        temporary_source_id="temp_src_99",
        notebook_id="mom_opcenter"
    )

    assert nb_src is not None
    assert nb_src.notebook_id == "mom_opcenter"
    assert nb_src.title == "Lỗi vận hành manual"
    assert nb_src.origin_temporary_source_id == "temp_src_99"
    assert nb_src.content_preview == "ERROR: DB fail"
    assert nb_src.content_text == "Full trace stack of DB failure..."

    # Check that original temporary source status was updated
    temp_sources = store.load_temporary_sources("conv_abc")
    assert len(temp_sources) == 1
    assert temp_sources[0].id == "temp_src_99"
    assert temp_sources[0].long_term_saved is True
    assert temp_sources[0].status == "added_to_notebook"

    # Verify no auto-enable for the new notebook source in selections
    selections = store.load_conversation_source_selections("conv_abc")
    assert len(selections) == 0

def test_isolated_store_directories():
    # Check that paths point to our test directory, not real local_cases
    assert store.LOCAL_CHAT_DIR.name == "workspace_chat"
    assert store.NOTEBOOK_SOURCES_FILE.parent == store.LOCAL_CHAT_DIR
    assert store.SOURCE_SELECTIONS_FILE.parent == store.LOCAL_CHAT_DIR

def test_set_source_enabled_no_duplicates():
    # Call enable multiple times on same scope/id
    sel1 = store.set_source_enabled("conv_test", SOURCE_SCOPE_NOTEBOOK, "src_dup", True)
    sel2 = store.set_source_enabled("conv_test", SOURCE_SCOPE_NOTEBOOK, "src_dup", True)
    assert sel1.id == sel2.id
    
    # Disable and enable again
    sel3 = store.set_source_enabled("conv_test", SOURCE_SCOPE_NOTEBOOK, "src_dup", False)
    sel4 = store.set_source_enabled("conv_test", SOURCE_SCOPE_NOTEBOOK, "src_dup", True)
    assert sel3.id == sel4.id
    assert sel4.enabled is True
    
    selections = store.load_conversation_source_selections("conv_test")
    assert len(selections) == 1
    assert selections[0].id == sel1.id

def test_timestamp_toggle_behavior():
    sel_en = store.set_source_enabled("conv_time", SOURCE_SCOPE_NOTEBOOK, "src_time", True)
    assert sel_en.enabled_at is not None
    assert sel_en.disabled_at is None
    
    sel_dis = store.set_source_enabled("conv_time", SOURCE_SCOPE_NOTEBOOK, "src_time", False)
    assert sel_dis.disabled_at is not None

def test_promote_missing_temporary_source_raises_error():
    with pytest.raises(ValueError, match="Temporary source not found"):
        store.promote_temporary_source_to_notebook("conv_nonexistent", "temp_nonexistent", "mom_opcenter")

def test_delete_notebook_source_dangling_selection():
    # Create source
    src = NotebookSource(
        id="src_to_delete",
        notebook_id="mom_opcenter",
        title="To Delete",
        source_type="pasted_text"
    )
    store.save_notebook_source(src)
    
    # Enable it for conversation
    store.set_source_enabled("conv_del", SOURCE_SCOPE_NOTEBOOK, "src_to_delete", True)
    
    # Delete source
    store.delete_notebook_source("src_to_delete")
    
    # Verify current selection remains as current Phase 2A non-goal (no auto-cascade delete)
    selections = store.load_conversation_source_selections("conv_del")
    assert len(selections) == 1
    assert selections[0].source_id == "src_to_delete"

def test_malformed_jsonl_tolerance():
    # Write a malformed JSONL line into notebook sources file
    with open(store.NOTEBOOK_SOURCES_FILE, "w", encoding="utf-8") as f:
        f.write("{invalid json}\n")
        f.write('{"id": "valid_src", "notebook_id": "mom_opcenter", "title": "Valid Source", "source_type": "pasted_text"}\n')
        
    # Read should succeed and skip the malformed line
    sources = store.load_notebook_sources("mom_opcenter")
    assert len(sources) == 1
    assert sources[0].id == "valid_src"

