import os
import pytest
from pathlib import Path
import aios_habit.workspace_chat_store as store
from aios_habit.evidence_trace_schema import (
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
)
from aios_habit.local_jsonl import clear_jsonl_cache
from aios_habit.workspace_chat_models import (
    DEFAULT_COLLECTION_ID,
    DocumentNotebook,
    KnowledgeCollection,
    LEGACY_INDEX_FILENAME,
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
    monkeypatch.setattr(store, "COLLECTIONS_FILE", test_dir / "collections.jsonl")
    monkeypatch.setattr(store, "CONVERSATIONS_FILE", test_dir / "conversations.jsonl")
    monkeypatch.setattr(store, "MESSAGES_FILE", test_dir / "messages.jsonl")
    monkeypatch.setattr(store, "TEMPORARY_SOURCES_FILE", test_dir / "temporary_sources.jsonl")
    monkeypatch.setattr(store, "NOTEBOOK_SOURCES_FILE", test_dir / "notebook_sources.jsonl")
    monkeypatch.setattr(store, "SOURCE_SELECTIONS_FILE", test_dir / "conversation_source_selections.jsonl")
    monkeypatch.setattr(store, "TRACES_FILE", test_dir / "traces.jsonl")
    clear_jsonl_cache()
    store.init_chat_store()
    yield
    clear_jsonl_cache()


def test_init_chat_store_defaults():
    nbs = store.load_notebooks()
    assert len(nbs) == 4
    ids = [n.id for n in nbs]
    assert "mom_opcenter" in ids
    assert "interstock_wms" in ids
    assert "email_jp_vn" in ids
    assert "aios_project" in ids

def test_default_collection_uses_dedicated_folder():
    collection = store.ensure_default_collection()
    assert collection.id == DEFAULT_COLLECTION_ID
    assert collection.storage_root == ""
    profile = Path("local_runs/profile")
    root, name = store.collection_runtime_layout(None, profile)
    assert root == profile
    assert name == LEGACY_INDEX_FILENAME
    root, name = store.collection_runtime_layout(DEFAULT_COLLECTION_ID, profile)
    assert root == profile / "collections" / DEFAULT_COLLECTION_ID
    assert name == store.COLLECTION_INDEX_BASENAME


def test_shared_storage_root_puts_index_beside_owner_folder(tmp_path):
    shared = tmp_path / "thu_vien_chung"
    store.ensure_default_collection()
    store.set_collection_storage_root(DEFAULT_COLLECTION_ID, str(shared))
    loaded = store.load_collection(DEFAULT_COLLECTION_ID)
    assert loaded is not None
    assert loaded.storage_root == str(shared)
    root, name = store.collection_runtime_layout(DEFAULT_COLLECTION_ID, Path("unused"))
    assert root == shared / store.COLLECTION_RUNTIME_DIRNAME
    assert name == "library.sqlite"
    assert root.is_dir()


def _write_sqlite(path: Path, values: list[str], *, wal: bool = False) -> None:
    import sqlite3

    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        if wal:
            conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")
        conn.executemany("INSERT INTO t(v) VALUES (?)", [(value,) for value in values])
        conn.commit()
    finally:
        conn.close()


def _sqlite_values(path: Path) -> list[str]:
    import sqlite3

    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute("SELECT v FROM t ORDER BY id").fetchall()
        return [str(row[0]) for row in rows]
    finally:
        conn.close()


def test_relocate_copies_existing_library_and_keeps_old(tmp_path):
    local_root = tmp_path / "local_profile"
    first = tmp_path / "first"
    second = tmp_path / "second"
    store.ensure_default_collection()
    store.set_collection_storage_root(DEFAULT_COLLECTION_ID, str(first))
    source = first / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME
    _write_sqlite(source, ["alpha"])
    store.relocate_collection_storage(
        DEFAULT_COLLECTION_ID,
        str(second),
        local_fallback_root=local_root,
    )
    dest = second / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME
    assert _sqlite_values(dest) == ["alpha"]
    assert _sqlite_values(source) == ["alpha"]
    loaded = store.load_collection(DEFAULT_COLLECTION_ID)
    assert loaded is not None
    assert loaded.storage_root == str(second)
    assert not dest.with_name(dest.name + "-shm").exists()


def test_relocate_keeps_wal_committed_rows(tmp_path):
    import sqlite3

    first = tmp_path / "first"
    second = tmp_path / "second"
    store.ensure_default_collection()
    store.set_collection_storage_root(DEFAULT_COLLECTION_ID, str(first))
    source = first / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME
    source.parent.mkdir(parents=True, exist_ok=True)
    live = sqlite3.connect(str(source))
    try:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        live.execute("INSERT INTO t(v) VALUES ('one')")
        live.commit()
        live.execute("INSERT INTO t(v) VALUES ('wal-only')")
        live.commit()
        store.relocate_collection_storage(
            DEFAULT_COLLECTION_ID,
            str(second),
            local_fallback_root=tmp_path / "local",
        )
    finally:
        live.close()
    dest = second / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME
    assert _sqlite_values(dest) == ["one", "wal-only"]
    assert not dest.with_name(dest.name + "-shm").exists()


def test_relocate_refuses_different_library_at_destination(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    store.ensure_default_collection()
    store.set_collection_storage_root(DEFAULT_COLLECTION_ID, str(first))
    _write_sqlite(first / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME, ["aaa"])
    _write_sqlite(second / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME, ["bbb"])
    try:
        store.relocate_collection_storage(
            DEFAULT_COLLECTION_ID,
            str(second),
            local_fallback_root=tmp_path / "unused",
        )
        raise AssertionError("expected conflict")
    except ValueError as exc:
        assert str(exc) == "storage_root_conflict"
    loaded = store.load_collection(DEFAULT_COLLECTION_ID)
    assert loaded is not None
    assert loaded.storage_root == str(first)
    assert _sqlite_values(second / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME) == ["bbb"]


def test_join_existing_valid_sqlite_without_source_index(tmp_path):
    shared = tmp_path / "shared"
    store.ensure_default_collection()
    dest = shared / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME
    _write_sqlite(dest, ["shared-row"])
    store.relocate_collection_storage(
        DEFAULT_COLLECTION_ID,
        str(shared),
        local_fallback_root=tmp_path / "empty-local",
    )
    loaded = store.load_collection(DEFAULT_COLLECTION_ID)
    assert loaded is not None
    assert loaded.storage_root == str(shared)
    assert _sqlite_values(dest) == ["shared-row"]


def _relocate_pair(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    store.ensure_default_collection()
    store.set_collection_storage_root(DEFAULT_COLLECTION_ID, str(first))
    _write_sqlite(first / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME, ["keep"])
    return first, second


def _assert_pointer_unchanged(first: Path, second: Path) -> None:
    loaded = store.load_collection(DEFAULT_COLLECTION_ID)
    assert loaded is not None
    assert loaded.storage_root == str(first)
    dest = second / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME
    assert not dest.exists()


def test_relocate_io_error_keeps_pointer(tmp_path, monkeypatch):
    first, second = _relocate_pair(tmp_path)

    def _boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(store, "_backup_sqlite", _boom)
    try:
        store.relocate_collection_storage(
            DEFAULT_COLLECTION_ID,
            str(second),
            local_fallback_root=tmp_path / "local",
        )
        raise AssertionError("expected io error")
    except OSError as exc:
        assert "library_io_error" in str(exc)
    _assert_pointer_unchanged(first, second)


def test_relocate_staging_verify_failure_keeps_pointer(tmp_path, monkeypatch):
    first, second = _relocate_pair(tmp_path)
    original = store.sqlite_quick_check

    def _check(path):
        if Path(path).name.startswith(f".{store.COLLECTION_INDEX_BASENAME}.") and Path(path).suffix == ".tmp":
            return False
        return original(path)

    monkeypatch.setattr(store, "sqlite_quick_check", _check)
    try:
        store.relocate_collection_storage(
            DEFAULT_COLLECTION_ID,
            str(second),
            local_fallback_root=tmp_path / "local",
        )
        raise AssertionError("expected invalid library")
    except ValueError as exc:
        assert str(exc) == "library_invalid"
    _assert_pointer_unchanged(first, second)


def test_relocate_replace_failure_keeps_pointer(tmp_path, monkeypatch):
    first, second = _relocate_pair(tmp_path)

    def _boom(_src, _dst):
        raise OSError("replace failed")

    monkeypatch.setattr(store.os, "replace", _boom)
    try:
        store.relocate_collection_storage(
            DEFAULT_COLLECTION_ID,
            str(second),
            local_fallback_root=tmp_path / "local",
        )
        raise AssertionError("expected io error")
    except OSError as exc:
        assert "library_io_error" in str(exc)
    _assert_pointer_unchanged(first, second)


def test_relocate_post_publish_verify_failure_keeps_pointer(tmp_path, monkeypatch):
    first, second = _relocate_pair(tmp_path)
    dest = second / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME
    original = store.sqlite_quick_check

    def _check(path):
        if Path(path) == dest:
            return False
        return original(path)

    monkeypatch.setattr(store, "sqlite_quick_check", _check)
    try:
        store.relocate_collection_storage(
            DEFAULT_COLLECTION_ID,
            str(second),
            local_fallback_root=tmp_path / "local",
        )
        raise AssertionError("expected invalid library")
    except ValueError as exc:
        assert str(exc) == "library_invalid"
    _assert_pointer_unchanged(first, second)


def test_clear_path_moves_to_local_after_backup(tmp_path):
    shared = tmp_path / "shared"
    local_root = tmp_path / "local_profile"
    store.ensure_default_collection()
    store.set_collection_storage_root(DEFAULT_COLLECTION_ID, str(shared))
    _write_sqlite(shared / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME, ["home"])
    store.relocate_collection_storage(
        DEFAULT_COLLECTION_ID,
        "",
        local_fallback_root=local_root,
    )
    loaded = store.load_collection(DEFAULT_COLLECTION_ID)
    assert loaded is not None
    assert loaded.storage_root == ""
    local_db = local_root / "collections" / DEFAULT_COLLECTION_ID / store.COLLECTION_INDEX_BASENAME
    assert _sqlite_values(local_db) == ["home"]


def test_writer_lease_blocks_relocate(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    store.ensure_default_collection()
    store.set_collection_storage_root(DEFAULT_COLLECTION_ID, str(first))
    _write_sqlite(first / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME, ["locked"])
    lease = store.LibraryWriterLease(first / store.COLLECTION_RUNTIME_DIRNAME)
    assert lease.acquire() is True
    try:
        try:
            store.relocate_collection_storage(
                DEFAULT_COLLECTION_ID,
                str(second),
                local_fallback_root=tmp_path / "local",
            )
            raise AssertionError("expected busy")
        except ValueError as exc:
            assert str(exc) == "library_writer_busy"
    finally:
        lease.release()
    loaded = store.load_collection(DEFAULT_COLLECTION_ID)
    assert loaded is not None
    assert loaded.storage_root == str(first)


def test_second_writer_lease_fails_closed(tmp_path):
    runtime = tmp_path / "runtime"
    first = store.LibraryWriterLease(runtime)
    second = store.LibraryWriterLease(runtime)
    assert first.acquire() is True
    try:
        assert second.acquire() is False
    finally:
        first.release()
    assert second.acquire() is True
    second.release()


def test_remote_wal_is_rejected(tmp_path, monkeypatch):
    shared = tmp_path / "share"
    store.ensure_default_collection()
    db = shared / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME
    _write_sqlite(db, ["wal-row"], wal=True)
    monkeypatch.setattr(store, "is_remote_filesystem_path", lambda _path: True)
    try:
        store.relocate_collection_storage(
            DEFAULT_COLLECTION_ID,
            str(shared),
            local_fallback_root=tmp_path / "local",
        )
        raise AssertionError("expected remote wal reject")
    except ValueError as exc:
        assert str(exc) == "shared_library_remote_wal_unsupported"


def test_remote_empty_dest_rejects_local_wal_source(tmp_path, monkeypatch):
    first = tmp_path / "first"
    second = tmp_path / "second"
    store.ensure_default_collection()
    store.set_collection_storage_root(DEFAULT_COLLECTION_ID, str(first))
    source = first / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME
    _write_sqlite(source, ["wal-row"], wal=True)
    dest_prefix = str(second)
    monkeypatch.setattr(
        store,
        "is_remote_filesystem_path",
        lambda path: str(Path(path)).startswith(dest_prefix),
    )
    try:
        store.relocate_collection_storage(
            DEFAULT_COLLECTION_ID,
            str(second),
            local_fallback_root=tmp_path / "local",
        )
        raise AssertionError("expected remote wal reject")
    except ValueError as exc:
        assert str(exc) == "shared_library_remote_wal_unsupported"
    loaded = store.load_collection(DEFAULT_COLLECTION_ID)
    assert loaded is not None
    assert loaded.storage_root == str(first)
    dest = second / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME
    assert not dest.exists()


def test_relocate_does_not_copy_chat_jsonl(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    store.ensure_default_collection()
    store.set_collection_storage_root(DEFAULT_COLLECTION_ID, str(first))
    _write_sqlite(first / store.COLLECTION_RUNTIME_DIRNAME / store.COLLECTION_INDEX_BASENAME, ["keep"])
    (first / "notebooks.jsonl").write_text("{}\n", encoding="utf-8")
    store.relocate_collection_storage(
        DEFAULT_COLLECTION_ID,
        str(second),
        local_fallback_root=tmp_path / "local",
    )
    dest_dir = second / store.COLLECTION_RUNTIME_DIRNAME
    assert list(dest_dir.glob("*.jsonl")) == []
    assert not (second / "notebooks.jsonl").exists()


def test_joined_collection_routes_without_notebook_sources(tmp_path):
    from aios_habit.workspace_chat_rag_v2_adapter import _collection_id_for_sources

    store.ensure_default_collection()
    store.set_collection_storage_root(DEFAULT_COLLECTION_ID, str(tmp_path / "share"))
    assert _collection_id_for_sources([]) == DEFAULT_COLLECTION_ID


def test_lease_released_after_holder_exception(tmp_path):
    runtime = tmp_path / "runtime"
    lease = store.LibraryWriterLease(runtime)
    assert lease.acquire() is True
    try:
        raise RuntimeError("worker failed")
    except RuntimeError:
        lease.release()
    other = store.LibraryWriterLease(runtime)
    assert other.acquire() is True
    other.release()


def test_old_notebook_record_defaults_to_tri_thuc():
    nb = store._deserialize_notebook({"id": "old", "title": "Sổ cũ"})
    assert nb.collection_id == DEFAULT_COLLECTION_ID


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


def test_bulk_source_delete_and_undo_restores_all_selections():
    first = TemporaryConversationSource(id="temp-one", conversation_id="conv-123", source_type="txt", title="Trùng tên", content_preview="one")
    second = TemporaryConversationSource(id="temp-two", conversation_id="conv-123", source_type="txt", title="Khác", content_preview="two")
    other_chat = TemporaryConversationSource(id="temp-other", conversation_id="conv-other", source_type="txt", title="Không bị xóa", content_preview="other")
    store.save_temporary_source(first)
    store.save_temporary_source(second)
    store.save_temporary_source(other_chat)
    store.set_source_enabled("conv-123", "temporary", first.id, True)
    store.set_source_enabled("conv-123", "temporary", second.id, False)

    snapshot = store.delete_sources("temporary", [first.id, second.id])

    assert {source.id for source in store.load_temporary_sources("conv-123")} == set()
    assert {source.id for source in store.load_temporary_sources("conv-other")} == {other_chat.id}
    assert len(snapshot["sources"]) == 2
    assert store.restore_source_snapshot(snapshot) == 2
    restored = {source.id for source in store.load_temporary_sources("conv-123")}
    assert restored == {first.id, second.id}
    restored_selections = {
        selection.source_id: selection.enabled
        for selection in store.load_conversation_source_selections("conv-123")
    }
    assert restored_selections == {first.id: True, second.id: False}


def test_notebook_source_delete_removes_selections_from_every_chat_and_restores_them():
    source = NotebookSource(id="notebook-source", notebook_id="mom_opcenter", source_type="pdf", title="SOP", content_preview="content")
    store.save_notebook_source(source)
    store.set_source_enabled("conv-a", "notebook", source.id, True)
    store.set_source_enabled("conv-b", "notebook", source.id, False)

    snapshot = store.delete_sources("notebook", [source.id])

    assert store.load_notebook_sources("mom_opcenter") == []
    assert all(selection.source_id != source.id for selection in store.load_all_conversation_source_selections())
    assert store.restore_source_snapshot(snapshot) == 1
    restored = {
        selection.conversation_id: selection.enabled
        for selection in store.load_all_conversation_source_selections()
        if selection.source_id == source.id
    }
    assert restored == {"conv-a": True, "conv-b": False}


def test_duplicate_title_lookup_stays_within_its_scope_owner():
    store.save_temporary_source(TemporaryConversationSource(id="temp-a", conversation_id="conv-a", source_type="txt", title="Bao cao.pdf", content_preview=""))
    store.save_temporary_source(TemporaryConversationSource(id="temp-b", conversation_id="conv-b", source_type="txt", title="bao CAO.PDF", content_preview=""))
    store.save_notebook_source(NotebookSource(id="nb-a", notebook_id="nb-a", source_type="pdf", title="Bao cao.pdf", content_preview=""))

    assert store.find_source_ids_by_title("temporary", "conv-a", " bao CAO.pdf ") == ["temp-a"]
    assert store.find_source_ids_by_title("temporary", "conv-b", "Bao cao.pdf") == ["temp-b"]
    assert store.find_source_ids_by_title("notebook", "nb-a", "bao cao.PDF") == ["nb-a"]
    assert store.find_source_ids_by_title("notebook", "nb-missing", "Bao cao.pdf") == []


def test_managed_upload_is_removed_only_when_no_source_still_references_it(tmp_path, monkeypatch):
    import aios_habit.workspace_chat_source_ingest as source_ingest

    managed_root = tmp_path / "managed_workbooks"
    managed_root.mkdir()
    managed_file = managed_root / "shared.xlsx"
    managed_file.write_bytes(b"workbook")
    monkeypatch.setattr(source_ingest, "MANAGED_WORKBOOK_ROOT", managed_root)

    first = TemporaryConversationSource(id="temp-first", conversation_id="conv-123", source_type="xlsx", title="First", content_preview="", managed_path=str(managed_file))
    second = TemporaryConversationSource(id="temp-second", conversation_id="conv-other", source_type="xlsx", title="Second", content_preview="", managed_path=str(managed_file))
    store.save_temporary_source(first)
    store.save_temporary_source(second)

    first_snapshot = store.delete_sources("temporary", [first.id])
    assert store.purge_unreferenced_managed_files(first_snapshot) == 0
    assert managed_file.exists()

    second_snapshot = store.delete_sources("temporary", [second.id])
    assert store.purge_unreferenced_managed_files(second_snapshot) == 1
    assert not managed_file.exists()


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
    # Store contents of all 7 files before call
    files = [
        store.NOTEBOOKS_FILE,
        store.CONVERSATIONS_FILE,
        store.MESSAGES_FILE,
        store.NOTEBOOK_SOURCES_FILE,
        store.TEMPORARY_SOURCES_FILE,
        store.SOURCE_SELECTIONS_FILE,
        store.TRACES_FILE,
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
        store.SOURCE_SELECTIONS_FILE,
        store.TRACES_FILE,
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
        if Path(dst).name == "conversations.jsonl" and str(src).endswith(".tmp"):
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

    # Assert no uniquely named recovery files remain in store directory.
    assert not list(store.LOCAL_CHAT_DIR.glob(".*.tmp"))
    assert not list(store.LOCAL_CHAT_DIR.glob(".*.bak"))


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
        store.SOURCE_SELECTIONS_FILE,
        store.TRACES_FILE,
    ]
    contents_before = {f: f.read_bytes() if f.exists() else None for f in files}

    def fail_batch_write(_targets):
        raise OSError("Simulated write error during temp JSONL writing")

    monkeypatch.setattr(store, "atomic_write_jsonl_batch", fail_batch_write)

    res = store.delete_notebook_permanently(nb_id)
    assert res is False

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
        store.SOURCE_SELECTIONS_FILE,
        store.TRACES_FILE,
    }
    def mock_unlink(self, *args, **kwargs):
        if self in protected_files:
            raise AssertionError(f"Path.unlink called on database file {self.name} during happy path")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    res = store.delete_notebook_permanently(nb_id)
    assert res is True


def test_conversation_search_preference_backward_compatibility():
    # 1. Legacy record without search_preference in JSONL
    legacy_json = '{"id": "legacy_conv", "notebook_id": "mom_opcenter", "title": "Legacy Conv"}\n'
    store.CONVERSATIONS_FILE.write_text(legacy_json, encoding="utf-8")

    loaded = store.load_conversation("legacy_conv")
    assert loaded is not None
    assert loaded.search_preference == "auto"

    # 2. Update to deep and round-trip
    success = store.update_conversation_search_preference("legacy_conv", "deep")
    assert success is True

    reloaded = store.load_conversation("legacy_conv")
    assert reloaded is not None
    assert reloaded.search_preference == "deep"

    # 3. Invalid preference fails safely to auto
    invalid_conv = WorkspaceConversation(
        id="invalid_pref_conv",
        notebook_id="mom_opcenter",
        title="Invalid Pref",
        search_preference="super_ultra_deep",
    )
    assert invalid_conv.search_preference == "auto"
    store.save_conversation(invalid_conv)

    reloaded_invalid = store.load_conversation("invalid_pref_conv")
    assert reloaded_invalid is not None
    assert reloaded_invalid.search_preference == "auto"


def test_resolve_conversation_navigation_recovers_invalid_or_cross_notebook_id():
    first = WorkspaceConversation(id="conv_first", notebook_id="mom_opcenter", title="First")
    second = WorkspaceConversation(id="conv_second", notebook_id="mom_opcenter", title="Second")
    other = WorkspaceConversation(id="conv_other", notebook_id="interstock_wms", title="Other")
    store.save_conversation(first)
    store.save_conversation(second)
    store.save_conversation(other)

    assert store.resolve_conversation_id("mom_opcenter", "conv_second") == "conv_second"
    assert store.resolve_conversation_id("mom_opcenter", "conv_other") == "conv_first"
    assert store.resolve_conversation_id("mom_opcenter", "conv_missing") == "conv_first"
    assert store.resolve_conversation_id("email_jp_vn", "conv_missing") is None


def test_delete_conversation_cascades_only_target_and_keeps_notebook_sources():
    target = WorkspaceConversation(id="conv_target", notebook_id="mom_opcenter", title="Delete me")
    survivor = WorkspaceConversation(id="conv_survivor", notebook_id="mom_opcenter", title="Keep me")
    store.save_conversation(target)
    store.save_conversation(survivor)
    store.save_message(ChatMessage(id="msg_target", conversation_id=target.id, role="user", content="target"))
    store.save_message(ChatMessage(id="msg_survivor", conversation_id=survivor.id, role="user", content="survivor"))
    store.save_temporary_source(TemporaryConversationSource(
        id="temp_target", conversation_id=target.id, source_type="txt", title="Target", content_preview="",
    ))
    store.save_temporary_source(TemporaryConversationSource(
        id="temp_survivor", conversation_id=survivor.id, source_type="txt", title="Survivor", content_preview="",
    ))
    notebook_source = NotebookSource(
        id="nb_source", notebook_id="mom_opcenter", title="Shared", source_type="txt", content_preview="",
    )
    store.save_notebook_source(notebook_source)
    store.set_source_enabled(target.id, "notebook", notebook_source.id, True)
    store.set_source_enabled(survivor.id, "notebook", notebook_source.id, True)

    assert store.delete_conversation(target.id) is True

    assert store.load_conversation(target.id) is None
    assert [message.content for message in store.load_messages(survivor.id)] == ["survivor"]
    assert [source.id for source in store.load_temporary_sources(survivor.id)] == ["temp_survivor"]
    assert store.get_notebook_source(notebook_source.id) is not None
    assert len(store.load_conversation_source_selections(target.id)) == 0
    assert len(store.load_conversation_source_selections(survivor.id)) == 1


def test_rename_conversation_changes_only_named_target_and_refreshes_timestamp():
    target = WorkspaceConversation(id="conv_target", notebook_id="mom_opcenter", title="Same title")
    survivor = WorkspaceConversation(id="conv_survivor", notebook_id="mom_opcenter", title="Same title")
    store.save_conversation(target)
    store.save_conversation(survivor)

    store.rename_conversation(target.id, "Renamed target")

    renamed = store.load_conversation(target.id)
    unchanged = store.load_conversation(survivor.id)
    assert renamed is not None
    assert renamed.title == "Renamed target"
    assert renamed.updated_at >= target.updated_at
    assert unchanged is not None
    assert unchanged.title == "Same title"


def _make_sample_trace(
    trace_id: str,
    conversation_id: str = "conv_unit_1",
    assistant_message_id: str = "ast_unit_1",
    user_message_id: str = "usr_unit_1",
    notebook_id: str = "mom_opcenter",
    query: str = "Định dạng cấu hình hệ thống?",
    answer_text: str = "Hệ thống cấu hình theo tài liệu [1].",
) -> EvidenceTrace:
    nodes = [
        EvidenceNode(
            id=f"{trace_id}_src",
            node_type="source",
            title="Tài liệu cấu hình",
            snippet="Hướng dẫn cài đặt hệ thống.",
            source_id="docs/config.md",
        ),
        EvidenceNode(
            id=f"{trace_id}_cit",
            node_type="citation",
            title="[1]",
            snippet="Trích dẫn [1]",
            source_id=f"{trace_id}_src",
            citation_id="[1]",
        ),
        EvidenceNode(
            id=f"{trace_id}_ans",
            node_type="answer",
            title="Câu trả lời",
            snippet=answer_text,
        ),
    ]
    edges = [
        EvidenceEdge(
            source_id=f"{trace_id}_cit",
            target_id=f"{trace_id}_src",
            relation_type="extracted_from",
        ),
        EvidenceEdge(
            source_id=f"{trace_id}_ans",
            target_id=f"{trace_id}_cit",
            relation_type="cites",
        ),
    ]
    return EvidenceTrace(
        schema_version="rag-trace/v1",
        trace_id=trace_id,
        notebook_id=notebook_id,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        assistant_message_id=assistant_message_id,
        query=query,
        answer_text=answer_text,
        ui_locale="vi",
        answer_language="vi",
        source_language="vi",
        nodes=nodes,
        edges=edges,
        metadata={
            "provenance": {
                "operational_mode": "direct",
                "provider_name": "Gemini Web Stream",
                "model_name": "gemini-2.5-flash",
            },
            "status": "valid",
        },
    )


def test_evidence_trace_save_and_load_by_id():
    trace = _make_sample_trace("trc_unit_001")
    saved = store.save_evidence_trace(trace)
    assert saved.trace_id == "trc_unit_001"

    loaded = store.load_evidence_trace("trc_unit_001")
    assert loaded is not None
    assert loaded.trace_id == "trc_unit_001"
    assert loaded.query == trace.query
    assert loaded.answer_text == trace.answer_text
    assert loaded.assistant_message_id == "ast_unit_1"
    assert len(loaded.nodes) == 3
    assert len(loaded.edges) == 2

    # Non-existent
    assert store.load_evidence_trace("non_existent_trace") is None
    assert store.load_evidence_trace("") is None


def test_evidence_trace_load_conversation_traces():
    t1 = _make_sample_trace("trc_c1_a", conversation_id="conv_alpha", assistant_message_id="ast_a")
    t2 = _make_sample_trace("trc_c1_b", conversation_id="conv_alpha", assistant_message_id="ast_b")
    t3 = _make_sample_trace("trc_c2_a", conversation_id="conv_beta", assistant_message_id="ast_c")

    store.save_evidence_trace(t1)
    store.save_evidence_trace(t2)
    store.save_evidence_trace(t3)

    alpha_traces = store.load_conversation_traces("conv_alpha")
    assert len(alpha_traces) == 2
    assert {t.trace_id for t in alpha_traces} == {"trc_c1_a", "trc_c1_b"}

    beta_traces = store.load_conversation_traces("conv_beta")
    assert len(beta_traces) == 1
    assert beta_traces[0].trace_id == "trc_c2_a"

    assert store.load_conversation_traces("non_existent") == []
    assert store.load_conversation_traces("") == []


def test_evidence_trace_load_message_trace():
    trace = _make_sample_trace(
        "trc_msg_test",
        user_message_id="usr_target_msg",
        assistant_message_id="ast_target_msg",
    )
    store.save_evidence_trace(trace)

    by_ast = store.load_message_trace("ast_target_msg")
    assert by_ast is not None
    assert by_ast.trace_id == "trc_msg_test"

    by_usr = store.load_message_trace("usr_target_msg")
    assert by_usr is not None
    assert by_usr.trace_id == "trc_msg_test"

    assert store.load_message_trace("unknown_msg") is None
    assert store.load_message_trace("") is None


def test_evidence_trace_idempotency_on_duplicate_save():
    t_v1 = _make_sample_trace(
        "trc_idemp_v1",
        assistant_message_id="ast_repeat_1",
        query="Initial question",
        answer_text="Initial answer",
    )
    store.save_evidence_trace(t_v1)

    t_v2 = _make_sample_trace(
        "trc_idemp_v2",
        assistant_message_id="ast_repeat_1",
        query="Refined question",
        answer_text="Refined answer",
    )
    store.save_evidence_trace(t_v2)

    # Verify only 1 line in traces.jsonl
    traces = store.load_all_evidence_traces()
    assert len(traces) == 1
    assert traces[0].trace_id == "trc_idemp_v2"
    assert traces[0].answer_text == "Refined answer"


def test_evidence_trace_restart_and_reload():
    orig_trace = _make_sample_trace(
        "trc_restart_unit",
        conversation_id="conv_restart",
        assistant_message_id="ast_restart",
    )
    store.save_evidence_trace(orig_trace)

    # Simulate restart by clearing cache and creating fresh store wrapper
    clear_jsonl_cache()
    fresh_store = store.WorkspaceChatStore()
    fresh_store.init_store()

    recovered = fresh_store.load_evidence_trace("trc_restart_unit")
    assert recovered is not None
    assert recovered.trace_id == "trc_restart_unit"
    assert recovered.metadata["provenance"]["model_name"] == "gemini-2.5-flash"
    assert len(recovered.nodes) == len(orig_trace.nodes)
    assert len(recovered.edges) == len(orig_trace.edges)


def test_evidence_trace_cascade_delete_conversation():
    conv_del = WorkspaceConversation(id="conv_del", notebook_id="mom_opcenter", title="Delete Me")
    conv_keep = WorkspaceConversation(id="conv_keep", notebook_id="mom_opcenter", title="Keep Me")
    store.save_conversation(conv_del)
    store.save_conversation(conv_keep)

    t_del = _make_sample_trace("trc_to_del", conversation_id="conv_del", assistant_message_id="ast_del")
    t_keep = _make_sample_trace("trc_to_keep", conversation_id="conv_keep", assistant_message_id="ast_keep")
    store.save_evidence_trace(t_del)
    store.save_evidence_trace(t_keep)

    assert store.load_evidence_trace("trc_to_del") is not None
    assert store.load_evidence_trace("trc_to_keep") is not None

    deleted = store.delete_conversation("conv_del")
    assert deleted is True

    assert store.load_evidence_trace("trc_to_del") is None
    assert store.load_conversation_traces("conv_del") == []
    assert store.load_evidence_trace("trc_to_keep") is not None
    assert len(store.load_conversation_traces("conv_keep")) == 1


def test_evidence_trace_cascade_delete_notebook_permanently():
    nb_del = DocumentNotebook(id="nb_purge", title="Purge Notebook")
    nb_keep = DocumentNotebook(id="nb_preserve", title="Preserve Notebook")
    store.save_notebook(nb_del)
    store.save_notebook(nb_keep)

    conv_del = WorkspaceConversation(id="conv_in_purge", notebook_id="nb_purge", title="Purge Conv")
    conv_keep = WorkspaceConversation(id="conv_in_preserve", notebook_id="nb_preserve", title="Preserve Conv")
    store.save_conversation(conv_del)
    store.save_conversation(conv_keep)

    t_del = _make_sample_trace("trc_nb_del", notebook_id="nb_purge", conversation_id="conv_in_purge", assistant_message_id="ast_nb_del")
    t_keep = _make_sample_trace("trc_nb_keep", notebook_id="nb_preserve", conversation_id="conv_in_preserve", assistant_message_id="ast_nb_keep")
    store.save_evidence_trace(t_del)
    store.save_evidence_trace(t_keep)

    assert store.load_evidence_trace("trc_nb_del") is not None
    assert store.load_evidence_trace("trc_nb_keep") is not None

    deleted = store.delete_notebook_permanently("nb_purge")
    assert deleted is True

    assert store.load_evidence_trace("trc_nb_del") is None
    assert store.load_evidence_trace("trc_nb_keep") is not None


def test_workspace_chat_store_class_wrapper_trace_methods():
    ws_store = store.WorkspaceChatStore()
    trace = _make_sample_trace(
        "trc_wrapper_01",
        conversation_id="conv_wrapper",
        assistant_message_id="ast_wrapper",
        user_message_id="usr_wrapper",
    )
    saved = ws_store.save_evidence_trace(trace)
    assert saved.trace_id == "trc_wrapper_01"

    assert ws_store.load_evidence_trace("trc_wrapper_01") is not None
    assert len(ws_store.load_conversation_traces("conv_wrapper")) == 1
    assert ws_store.load_message_trace("ast_wrapper") is not None
    assert ws_store.load_message_trace("usr_wrapper") is not None
    assert len(ws_store.load_all_evidence_traces()) >= 1
