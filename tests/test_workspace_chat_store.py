import os
import pytest
from pathlib import Path
import aios_habit.workspace_chat_store as store
from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
    ChatMessage,
    TemporaryConversationSource,
    NotebookSource,
    ConversationSourceSelection
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


def test_delete_notebook_permanently_cascade():
    # 1. Setup target notebook and child data
    nb_id = "target_nb"
    nb = DocumentNotebook(id=nb_id, title="Target Notebook", description="Desc")
    store.save_notebook(nb)

    conv = WorkspaceConversation(id="conv_target", notebook_id=nb_id, title="Target Conversation")
    store.save_conversation(conv)

    msg = ChatMessage(id="msg_target", conversation_id="conv_target", role="user", content="Msg content")
    store.save_message(msg)

    nb_src = NotebookSource(
        id="src_nb_target",
        notebook_id=nb_id,
        title="Source Notebook Title",
        source_type="plain_text",
        privacy_label="machine_only",
        content_preview="Preview",
        content_text="Full text"
    )
    store.save_notebook_source(nb_src)

    temp_src = TemporaryConversationSource(
        id="src_temp_target",
        conversation_id="conv_target",
        source_type="pasted_text",
        title="Temp Title",
        content_preview="Preview",
        content_text="Full text"
    )
    store.save_temporary_source(temp_src)

    sel = ConversationSourceSelection(
        id="sel_target",
        conversation_id="conv_target",
        source_id="src_nb_target",
        source_scope="notebook",
        enabled=True
    )
    store.save_conversation_source_selection(sel)

    # 2. Setup unrelated notebook and child data to verify preservation
    unrelated_id = "unrelated_nb"
    unrelated_nb = DocumentNotebook(id=unrelated_id, title="Unrelated Notebook", description="Desc")
    store.save_notebook(unrelated_nb)

    u_conv = WorkspaceConversation(id="conv_unrelated", notebook_id=unrelated_id, title="Unrelated Conv")
    store.save_conversation(u_conv)

    u_msg = ChatMessage(id="msg_unrelated", conversation_id="conv_unrelated", role="user", content="Unrelated msg")
    store.save_message(u_msg)

    u_nb_src = NotebookSource(
        id="src_nb_unrelated",
        notebook_id=unrelated_id,
        title="Unrelated Source Notebook Title",
        source_type="plain_text",
        privacy_label="local_only",
        content_preview="Preview",
        content_text="Full text"
    )
    store.save_notebook_source(u_nb_src)

    u_temp_src = TemporaryConversationSource(
        id="src_temp_unrelated",
        conversation_id="conv_unrelated",
        source_type="pasted_text",
        title="Unrelated Temp Title",
        content_preview="Preview",
        content_text="Full text"
    )
    store.save_temporary_source(u_temp_src)

    u_sel = ConversationSourceSelection(
        id="sel_unrelated",
        conversation_id="conv_unrelated",
        source_id="src_nb_unrelated",
        source_scope="notebook",
        enabled=False
    )
    store.save_conversation_source_selection(u_sel)

    # Verify pre-condition
    assert store.load_notebook(nb_id) is not None
    assert len(store.load_conversations(nb_id)) == 1
    assert len(store.load_messages("conv_target")) == 1
    assert len(store.load_notebook_sources(nb_id)) == 1
    assert len(store.load_temporary_sources("conv_target")) == 1
    assert len(store.load_conversation_source_selections("conv_target")) == 1

    # 3. Call delete
    res = store.delete_notebook_permanently(nb_id)
    assert res is True

    # 4. Verify cascade deletion
    assert store.load_notebook(nb_id) is None
    assert len(store.load_conversations(nb_id)) == 0
    assert len(store.load_messages("conv_target")) == 0
    assert len(store.load_notebook_sources(nb_id)) == 0
    assert len(store.load_temporary_sources("conv_target")) == 0
    assert len(store.load_conversation_source_selections("conv_target")) == 0

    # 5. Verify preservation of unrelated data
    assert store.load_notebook(unrelated_id) is not None
    assert len(store.load_conversations(unrelated_id)) == 1
    assert len(store.load_messages("conv_unrelated")) == 1
    assert len(store.load_notebook_sources(unrelated_id)) == 1
    assert len(store.load_temporary_sources("conv_unrelated")) == 1

    selections_unrelated = store.load_conversation_source_selections("conv_unrelated")
    assert len(selections_unrelated) == 1
    assert selections_unrelated[0].enabled is False

    # Verify privacy label preserved
    unrelated_sources = store.load_notebook_sources(unrelated_id)
    assert unrelated_sources[0].privacy_label == "local_only"


def test_delete_notebook_permanently_missing():
    # Store contents of all 6 files before call
    files = [
        store.NOTEBOOKS_FILE,
        store.CONVERSATIONS_FILE,
        store.MESSAGES_FILE,
        store.NOTEBOOK_SOURCES_FILE,
        store.TEMPORARY_SOURCES_FILE,
        store.SOURCE_SELECTIONS_FILE
    ]
    contents_before = {}
    for f in files:
        if f.exists():
            contents_before[f] = f.read_bytes()
        else:
            contents_before[f] = None

    res = store.delete_notebook_permanently("non_existent_id")
    assert res is False

    # Ensure not a single byte in any of the files was modified or touched
    for f in files:
        if f.exists():
            assert f.read_bytes() == contents_before[f], f"File {f.name} was touched!"
        else:
            assert contents_before[f] is None
            assert not f.exists()


def test_delete_notebook_permanently_archived():
    nb_id = "archived_nb"
    nb = DocumentNotebook(id=nb_id, title="Archived Notebook", description="Desc", archived_at="2026-07-04T12:00:00")
    store.save_notebook(nb)

    conv = WorkspaceConversation(id="conv_archived", notebook_id=nb_id, title="Archived Conversation")
    store.save_conversation(conv)

    res = store.delete_notebook_permanently(nb_id)
    assert res is True

    assert store.load_notebook(nb_id) is None
    assert len(store.load_conversations(nb_id)) == 0


def test_delete_notebook_permanently_failure_rollback(monkeypatch):
    # Setup initial notebook and data
    nb_id = "rollback_nb"
    nb = DocumentNotebook(id=nb_id, title="Rollback Notebook", description="Desc")
    store.save_notebook(nb)

    conv = WorkspaceConversation(id="conv_rollback", notebook_id=nb_id, title="Rollback Conversation")
    store.save_conversation(conv)

    # Capture state before call
    files = [
        store.NOTEBOOKS_FILE,
        store.CONVERSATIONS_FILE,
        store.MESSAGES_FILE,
        store.NOTEBOOK_SOURCES_FILE,
        store.TEMPORARY_SOURCES_FILE,
        store.SOURCE_SELECTIONS_FILE
    ]
    contents_before = {}
    for f in files:
        if f.exists():
            contents_before[f] = f.read_bytes()
        else:
            contents_before[f] = None

    original_replace = os.replace

    def mock_replace(src, dst):
        # Fail when trying to overwrite conversations.jsonl with its .tmp file
        if "conversations.jsonl" in str(dst) and "conversations.tmp" in str(src):
            raise OSError("Simulated atomic replacement error")
        return original_replace(src, dst)

    monkeypatch.setattr(os, "replace", mock_replace)

    res = store.delete_notebook_permanently(nb_id)
    assert res is False

    # Ensure rollback restored every single file back to its exact original state
    for f in files:
        if f.exists():
            assert f.read_bytes() == contents_before[f], f"File {f.name} was not rolled back correctly!"
        else:
            assert not f.exists()

    # Assert no .tmp or .bak files remain in store directory
    for f in files:
        assert not f.with_suffix(".tmp").exists()
        assert not f.with_suffix(".bak").exists()


def test_delete_notebook_permanently_temp_write_failure(monkeypatch):
    nb_id = "temp_fail_nb"
    nb = DocumentNotebook(id=nb_id, title="Temp Fail Notebook", description="Desc")
    store.save_notebook(nb)

    files = [
        store.NOTEBOOKS_FILE,
        store.CONVERSATIONS_FILE,
        store.MESSAGES_FILE,
        store.NOTEBOOK_SOURCES_FILE,
        store.TEMPORARY_SOURCES_FILE,
        store.SOURCE_SELECTIONS_FILE
    ]
    contents_before = {f: f.read_bytes() if f.exists() else None for f in files}

    # Wrapper to simulate failure in write() after open() has succeeded
    original_open = open

    class FaultyFileWrapper:
        def __init__(self, real_file, is_target_temp):
            self.real_file = real_file
            self.is_target_temp = is_target_temp

        def write(self, data):
            if self.is_target_temp:
                raise OSError("Simulated write error during temp JSONL writing")
            return self.real_file.write(data)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.real_file.close()

        def close(self):
            self.real_file.close()

    def mock_open(file, mode='r', *args, **kwargs):
        real_file = original_open(file, mode, *args, **kwargs)
        if "notebooks.tmp" in str(file) and 'w' in mode:
            return FaultyFileWrapper(real_file, True)
        return real_file

    monkeypatch.setattr("builtins.open", mock_open)

    res = store.delete_notebook_permanently(nb_id)
    assert res is False

    # Assert all temp files (including the partially written messages.tmp) are cleaned up
    for f in files:
        assert not f.with_suffix(".tmp").exists(), f"Temp file {f.name}.tmp was not cleaned up!"
        assert not f.with_suffix(".bak").exists(), f"Backup file {f.name}.bak was created unexpectedly!"

    # Ensure original files are completely untouched
    for f in files:
        if f.exists():
            assert f.read_bytes() == contents_before[f]
        else:
            assert contents_before[f] is None


def test_delete_notebook_permanently_no_target_gap(monkeypatch):
    nb_id = "gap_nb"
    nb = DocumentNotebook(id=nb_id, title="Gap Notebook", description="Desc")
    store.save_notebook(nb)

    # Assure rename is never called (prevent gap)
    def mock_rename(src, dst):
        raise AssertionError("rename must not be called during delete happy path to prevent gap")
    monkeypatch.setattr(os, "rename", mock_rename)

    # Assure unlink is never called on actual database files during happy path
    original_unlink = Path.unlink
    protected_files = {
        store.NOTEBOOKS_FILE,
        store.CONVERSATIONS_FILE,
        store.MESSAGES_FILE,
        store.NOTEBOOK_SOURCES_FILE,
        store.TEMPORARY_SOURCES_FILE,
        store.SOURCE_SELECTIONS_FILE
    }
    def mock_unlink(self, *args, **kwargs):
        if self in protected_files:
            raise AssertionError(f"Path.unlink called on database file {self.name} during happy path")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    res = store.delete_notebook_permanently(nb_id)
    assert res is True
