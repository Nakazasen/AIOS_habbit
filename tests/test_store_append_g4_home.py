from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import List
import pytest

import aios_habit.workspace_chat_store as store
from aios_habit.local_jsonl import _JSONL_CACHE, atomic_write_jsonl, clear_jsonl_cache, load_jsonl_records
from aios_habit.workspace_chat_models import (
    NotebookSource,
    TemporaryConversationSource,
)


@pytest.fixture(autouse=True)
def setup_isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    test_dir = tmp_path / "workspace_chat_g4"
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(store, "NOTEBOOKS_FILE", test_dir / "notebooks.jsonl")
    monkeypatch.setattr(store, "COLLECTIONS_FILE", test_dir / "collections.jsonl")
    monkeypatch.setattr(store, "CONVERSATIONS_FILE", test_dir / "conversations.jsonl")
    monkeypatch.setattr(store, "MESSAGES_FILE", test_dir / "messages.jsonl")
    monkeypatch.setattr(store, "TEMPORARY_SOURCES_FILE", test_dir / "temporary_sources.jsonl")
    monkeypatch.setattr(store, "NOTEBOOK_SOURCES_FILE", test_dir / "notebook_sources.jsonl")
    monkeypatch.setattr(store, "SOURCE_SELECTIONS_FILE", test_dir / "conversation_source_selections.jsonl")
    monkeypatch.setattr(store, "TRACES_FILE", test_dir / "traces.jsonl")
    monkeypatch.setattr(store, "EXTERNAL_AI_USAGE_FILE", test_dir / "external_ai_usage.jsonl")
    store.clear_store_cache()
    store.init_chat_store()
    return test_dir


def _legacy_save_temporary_source(target_file: Path, src: TemporaryConversationSource) -> None:
    """Reference legacy implementation (read-all + in-place replace + full atomic rewrite)."""
    sources: List[TemporaryConversationSource] = (
        load_jsonl_records(target_file, store._deserialize_temporary_source)
        if target_file.exists()
        else []
    )
    found = False
    for i, item in enumerate(sources):
        if item.id == src.id:
            sources[i] = src
            found = True
            break
    if not found:
        sources.append(src)
    atomic_write_jsonl(target_file, sources)


def _legacy_save_notebook_source(target_file: Path, source: NotebookSource) -> NotebookSource:
    """Reference legacy implementation (read-all + in-place replace + full atomic rewrite)."""
    sources: List[NotebookSource] = (
        load_jsonl_records(target_file, NotebookSource.from_dict)
        if target_file.exists()
        else []
    )
    found = False
    for i, item in enumerate(sources):
        if item.id == source.id:
            sources[i] = source
            found = True
            break
    if not found:
        sources.append(source)
    atomic_write_jsonl(target_file, sources)
    return source


def test_arch12_temporary_source_semantic_equivalence_insert_and_update(tmp_path: Path) -> None:
    """Verify 100% semantic equivalence (content and order) between legacy rewrite and new append-only."""
    legacy_file = tmp_path / "legacy_temporary_sources.jsonl"
    legacy_file.touch()

    operations = [
        TemporaryConversationSource(
            id="tmp-1",
            conversation_id="conv-a",
            source_type="pasted_text",
            title="Temp 1 v1",
            content_preview="p1-v1",
            content_text="full-1-v1",
            privacy_label="local_only",
            status="temporary_only",
            long_term_saved=False,
        ),
        TemporaryConversationSource(
            id="tmp-2",
            conversation_id="conv-a",
            source_type="file",
            title="Temp 2 v1",
            content_preview="p2-v1",
            content_text="full-2-v1",
            privacy_label="machine_only",
            status="temporary_only",
            long_term_saved=False,
        ),
        TemporaryConversationSource(
            id="tmp-3",
            conversation_id="conv-b",
            source_type="xlsx",
            title="Temp 3 v1",
            content_preview="p3-v1",
            content_text="full-3-v1",
            privacy_label="cloud_safe",
            status="temporary_only",
            long_term_saved=False,
        ),
        # Update middle record (tmp-2) -> must stay at index 1
        TemporaryConversationSource(
            id="tmp-2",
            conversation_id="conv-a",
            source_type="file",
            title="Temp 2 v2 (updated privacy)",
            content_preview="p2-v2",
            content_text="full-2-v2",
            privacy_label="cloud_safe",
            status="temporary_only",
            long_term_saved=False,
        ),
        # Append new record (tmp-4) -> index 3
        TemporaryConversationSource(
            id="tmp-4",
            conversation_id="conv-a",
            source_type="pasted_text",
            title="Temp 4 v1",
            content_preview="p4-v1",
            content_text="full-4-v1",
        ),
        # Update first record (tmp-1) -> must stay at index 0
        TemporaryConversationSource(
            id="tmp-1",
            conversation_id="conv-a",
            source_type="pasted_text",
            title="Temp 1 v2 (promoted)",
            content_preview="p1-v2",
            content_text="full-1-v2",
            privacy_label="local_only",
            status="added_to_notebook",
            long_term_saved=True,
        ),
        # Update middle record (tmp-2) a second time -> must still stay at index 1
        TemporaryConversationSource(
            id="tmp-2",
            conversation_id="conv-a",
            source_type="file",
            title="Temp 2 v3 (final)",
            content_preview="p2-v3",
            content_text="full-2-v3",
            privacy_label="local_only",
            status="added_to_notebook",
            long_term_saved=True,
        ),
        # Update last record (tmp-4) -> must stay at index 3
        TemporaryConversationSource(
            id="tmp-4",
            conversation_id="conv-a",
            source_type="pasted_text",
            title="Temp 4 v2",
            content_preview="p4-v2",
            content_text="full-4-v2",
        ),
    ]

    for op in operations:
        _legacy_save_temporary_source(legacy_file, op)
        store.save_temporary_source(op)

    legacy_all = load_jsonl_records(legacy_file, store._deserialize_temporary_source)

    # 1. Warm read from in-memory cache must match legacy 100% in content and order
    warm_all = store.load_all_temporary_sources()
    assert [asdict(item) for item in warm_all] == [asdict(item) for item in legacy_all]
    assert [item.id for item in warm_all] == ["tmp-1", "tmp-2", "tmp-3", "tmp-4"]

    warm_conv_a = store.load_temporary_sources("conv-a")
    legacy_conv_a = [s for s in legacy_all if s.conversation_id == "conv-a"]
    assert [asdict(item) for item in warm_conv_a] == [asdict(item) for item in legacy_conv_a]
    assert [item.id for item in warm_conv_a] == ["tmp-1", "tmp-2", "tmp-4"]

    # 2. Cold read from disk (after clearing cache) must also match legacy 100% in content and order
    store.clear_store_cache()
    cold_all = store.load_all_temporary_sources()
    assert [asdict(item) for item in cold_all] == [asdict(item) for item in legacy_all]
    assert [item.id for item in cold_all] == ["tmp-1", "tmp-2", "tmp-3", "tmp-4"]

    cold_conv_a = store.load_temporary_sources("conv-a")
    assert [asdict(item) for item in cold_conv_a] == [asdict(item) for item in legacy_conv_a]


def test_arch12_notebook_source_semantic_equivalence_insert_and_update(tmp_path: Path) -> None:
    """Verify 100% semantic equivalence (content and order) for save_notebook_source."""
    legacy_file = tmp_path / "legacy_notebook_sources.jsonl"
    legacy_file.touch()

    operations = [
        NotebookSource(
            id="nb-src-1",
            notebook_id="nb-alpha",
            title="Doc 1 v1",
            source_type="pdf",
            privacy_label="machine_only",
            content_preview="nb1-v1",
            content_text="nb1-text-v1",
        ),
        NotebookSource(
            id="nb-src-2",
            notebook_id="nb-alpha",
            title="Doc 2 v1",
            source_type="docx",
            privacy_label="local_only",
            content_preview="nb2-v1",
            content_text="nb2-text-v1",
        ),
        NotebookSource(
            id="nb-src-3",
            notebook_id="nb-beta",
            title="Doc 3 v1",
            source_type="xlsx",
            privacy_label="cloud_safe",
            content_preview="nb3-v1",
            content_text="nb3-text-v1",
        ),
        # Update nb-src-1 in place (index 0)
        NotebookSource(
            id="nb-src-1",
            notebook_id="nb-alpha",
            title="Doc 1 v2",
            source_type="pdf",
            privacy_label="cloud_safe",
            content_preview="nb1-v2",
            content_text="nb1-text-v2",
        ),
        # Append nb-src-4 (index 3)
        NotebookSource(
            id="nb-src-4",
            notebook_id="nb-alpha",
            title="Doc 4 v1",
            source_type="txt",
            privacy_label="local_only",
            content_preview="nb4-v1",
            content_text="nb4-text-v1",
        ),
        # Update nb-src-2 in place (index 1)
        NotebookSource(
            id="nb-src-2",
            notebook_id="nb-alpha",
            title="Doc 2 v2",
            source_type="docx",
            privacy_label="cloud_safe",
            content_preview="nb2-v2",
            content_text="nb2-text-v2",
        ),
    ]

    for op in operations:
        expected_ret = _legacy_save_notebook_source(legacy_file, op)
        actual_ret = store.save_notebook_source(op)
        assert asdict(actual_ret) == asdict(expected_ret)

    legacy_all = load_jsonl_records(legacy_file, NotebookSource.from_dict)

    # 1. Warm read from in-memory cache
    warm_all = store.load_all_notebook_sources()
    assert [asdict(item) for item in warm_all] == [asdict(item) for item in legacy_all]
    assert [item.id for item in warm_all] == ["nb-src-1", "nb-src-2", "nb-src-3", "nb-src-4"]

    warm_alpha = store.load_notebook_sources("nb-alpha")
    legacy_alpha = [s for s in legacy_all if s.notebook_id == "nb-alpha"]
    assert [asdict(item) for item in warm_alpha] == [asdict(item) for item in legacy_alpha]
    assert [item.id for item in warm_alpha] == ["nb-src-1", "nb-src-2", "nb-src-4"]

    for src_id in ("nb-src-1", "nb-src-2", "nb-src-3", "nb-src-4"):
        got = store.get_notebook_source(src_id)
        exp = next(s for s in legacy_all if s.id == src_id)
        assert got is not None
        assert asdict(got) == asdict(exp)

    # 2. Cold read from disk after clearing cache
    store.clear_store_cache()
    cold_all = store.load_all_notebook_sources()
    assert [asdict(item) for item in cold_all] == [asdict(item) for item in legacy_all]
    assert [item.id for item in cold_all] == ["nb-src-1", "nb-src-2", "nb-src-3", "nb-src-4"]


def test_arch12_append_only_no_full_rewrite_and_in_memory_cache_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify save_temporary_source and save_notebook_source use _append_jsonl_record, never atomic_write_jsonl, and keep _JSONL_CACHE warm."""
    def forbid_atomic_write(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("atomic_write_jsonl must NOT be called during save_temporary_source or save_notebook_source")

    monkeypatch.setattr(store, "atomic_write_jsonl", forbid_atomic_write)

    append_calls: list[tuple[Path, str]] = []
    orig_append = store._append_jsonl_record

    def spy_append(path: Path, record: object) -> None:
        append_calls.append((path, getattr(record, "id", "")))
        orig_append(path, record)

    monkeypatch.setattr(store, "_append_jsonl_record", spy_append)

    t1 = TemporaryConversationSource(id="t1", conversation_id="c1", source_type="txt", title="T1", content_preview="v1")
    t2 = TemporaryConversationSource(id="t2", conversation_id="c1", source_type="txt", title="T2", content_preview="v1")
    t1_upd = TemporaryConversationSource(id="t1", conversation_id="c1", source_type="txt", title="T1-upd", content_preview="v2")

    store.save_temporary_source(t1)
    store.save_temporary_source(t2)
    store.save_temporary_source(t1_upd)

    nb1 = NotebookSource(id="n1", notebook_id="nb1", title="N1", source_type="pdf", content_preview="v1")
    nb2 = NotebookSource(id="n2", notebook_id="nb1", title="N2", source_type="pdf", content_preview="v1")
    nb1_upd = NotebookSource(id="n1", notebook_id="nb1", title="N1-upd", source_type="pdf", content_preview="v2")

    store.save_notebook_source(nb1)
    store.save_notebook_source(nb2)
    store.save_notebook_source(nb1_upd)

    assert len(append_calls) == 6

    # Physical JSONL files have 3 raw lines each (2 inserts + 1 update append)
    temp_raw_lines = [l for l in store.TEMPORARY_SOURCES_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    nb_raw_lines = [l for l in store.NOTEBOOK_SOURCES_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(temp_raw_lines) == 3
    assert len(nb_raw_lines) == 3

    # Reading right after save hits warm _JSONL_CACHE without calling load_jsonl_records
    def forbid_disk_load(*_args: object, **_kwargs: object) -> list[object]:
        raise AssertionError("load_jsonl_records should not be called when _JSONL_CACHE is already updated in-place")

    monkeypatch.setattr(store, "load_jsonl_records", forbid_disk_load)

    loaded_temp = store.load_all_temporary_sources()
    assert [(s.id, s.title) for s in loaded_temp] == [("t1", "T1-upd"), ("t2", "T2")]

    loaded_nb = store.load_all_notebook_sources()
    assert [(s.id, s.title) for s in loaded_nb] == [("n1", "N1-upd"), ("n2", "N2")]


def test_arch12_cold_cache_append_reconciles_on_next_load() -> None:
    """Verify appending when cache is cold does not lose prior records and reconciles on next load."""
    s1 = TemporaryConversationSource(id="s1", conversation_id="c1", source_type="txt", title="S1-v1", content_preview="")
    s2 = TemporaryConversationSource(id="s2", conversation_id="c1", source_type="txt", title="S2-v1", content_preview="")
    store.save_temporary_source(s1)
    store.save_temporary_source(s2)

    # Evict cache to simulate a cold process that saves before reading
    clear_jsonl_cache()
    assert len(_JSONL_CACHE) == 0

    s1_v2 = TemporaryConversationSource(id="s1", conversation_id="c1", source_type="txt", title="S1-v2", content_preview="")
    s3 = TemporaryConversationSource(id="s3", conversation_id="c1", source_type="txt", title="S3-v1", content_preview="")
    store.save_temporary_source(s1_v2)
    store.save_temporary_source(s3)

    # Now load_all_temporary_sources must read all 4 raw lines from disk and reconcile to 3 records in order
    loaded = store.load_all_temporary_sources()
    assert [(s.id, s.title) for s in loaded] == [
        ("s1", "S1-v2"),
        ("s2", "S2-v1"),
        ("s3", "S3-v1"),
    ]
