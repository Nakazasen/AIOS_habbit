"""Tests for production index domain filtering and auto-preparation suppression (APP-SOURCE-MODEL-PC0575).

Validates:
1. Notebook sources in production index are marked READY instantly without background re-indexing.
2. Temporary sources continue to be enqueued and prepared in the background silently.
3. Domain filtering operates via document_id on unified library.sqlite.
4. Correct counts: LSU (92), Dieu tra loi (681), MOM (44), Total indexed (889).
"""
from pathlib import Path
import pytest

from aios_habit.rag_v2 import (
    RagV2DevConfig,
    RagV2DevPipeline,
    SourceSpec,
)
from aios_habit.index_domain import (
    get_domain_document_ids,
    load_all_index_specs,
    get_specs_for_domain,
    load_domain_document_map,
)
from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_models import (
    SOURCE_SCOPE_NOTEBOOK,
    SOURCE_SCOPE_TEMPORARY,
)
import aios_habit.workspace_chat_rag_v2_adapter as adapter


def test_domain_document_map_counts() -> None:
    doc_map = load_domain_document_map()
    assert len(doc_map) == 889

    lsu_ids = get_domain_document_ids("lsu")
    assert lsu_ids is not None
    assert len(lsu_ids) == 92

    dtl_ids = get_domain_document_ids("dieu_tra_loi")
    assert dtl_ids is not None
    assert len(dtl_ids) == 681

    mom_ids = get_domain_document_ids("mom")
    assert mom_ids is not None
    assert len(mom_ids) == 44

    th_ids = get_domain_document_ids("tong_hop")
    assert th_ids is not None
    assert len(th_ids) == 72

    assert 92 + 681 + 44 + 72 == 889


def test_production_index_specs_retrieval() -> None:
    # TEST-SUITE-HYGIENE-HOME: absolute count 889 belongs to another machine's
    # store. Assert relations over this test's own input instead, keeping the
    # domain-filter meaning (disjoint + auto covers all + sums match).
    prod_db = Path("local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite")
    if not prod_db.is_file():
        pytest.skip("Production database not present on this machine")

    all_specs = load_all_index_specs(prod_db)
    total = len(all_specs)
    assert total > 0, "kho production hien tai rong"

    lsu_specs = get_specs_for_domain("lsu", prod_db)
    dtl_specs = get_specs_for_domain("dieu_tra_loi", prod_db)
    mom_specs = get_specs_for_domain("mom", prod_db)
    auto_specs = get_specs_for_domain("auto", prod_db)

    lsu_ids = {s.document_id for s in lsu_specs}
    dtl_ids = {s.document_id for s in dtl_specs}
    mom_ids = {s.document_id for s in mom_specs}
    auto_ids = {s.document_id for s in auto_specs}
    all_ids = {s.document_id for s in all_specs}

    # auto bao het kho hien tai
    assert auto_ids == all_ids
    assert len(auto_specs) == total
    # cac mien roi nhau (moi tai lieu thuoc dung 1 mien)
    assert not (lsu_ids & dtl_ids)
    assert not (lsu_ids & mom_ids)
    assert not (dtl_ids & mom_ids)
    # cac mien da biet khong vuot tong kho; so con lai la mien tong-hop
    known = lsu_ids | dtl_ids | mom_ids
    assert known <= all_ids
    th_specs = get_specs_for_domain("tong_hop", prod_db)
    th_ids = {s.document_id for s in th_specs}
    assert known | th_ids == all_ids
    assert len(lsu_specs) + len(dtl_specs) + len(mom_specs) + len(th_specs) == total


def test_notebook_source_marked_ready_without_enqueue(tmp_path: Path) -> None:
    canary_dir = tmp_path / "canary_runtime"
    config = adapter.WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        runtime_root=canary_dir,
    )
    db_path = adapter._get_ledger_db_path(config)
    adapter._init_preparation_ledger_db(db_path)
    with adapter._PREPARATION_LOCK:
        adapter._PREPARATION_REGISTRY.clear()

    notebook_source = WorkspaceAIContextSource(
        source_id="nb_src_1",
        source_scope=SOURCE_SCOPE_NOTEBOOK,
        source_type="plain_text",
        title="tai_lieu_notebook.txt",
        privacy_label="local_only",
        text="Nội dung notebook có sẵn trong production index.",
        included_chars=50,
        truncated=False,
    )

    enqueued = adapter.reconcile_and_enqueue_workspace_chat_sources(
        (notebook_source,),
        config=config,
    )
    # Must NOT enqueue for background preparation
    assert enqueued == 0

    # Must be marked READY in the preparation registry
    statuses = adapter.get_workspace_chat_source_preparation_status(
        (notebook_source,),
        config=config,
    )
    assert statuses.get("notebook:nb_src_1") == adapter.PREP_STATE_READY


def test_temporary_source_enqueued_normally(tmp_path: Path, monkeypatch) -> None:
    canary_dir = tmp_path / "canary_runtime"
    config = adapter.WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        runtime_root=canary_dir,
    )
    db_path = adapter._get_ledger_db_path(config)
    adapter._init_preparation_ledger_db(db_path)
    with adapter._PREPARATION_LOCK:
        adapter._PREPARATION_REGISTRY.clear()

    temp_source = WorkspaceAIContextSource(
        source_id="temp_src_1",
        source_scope=SOURCE_SCOPE_TEMPORARY,
        source_type="plain_text",
        title="tai_lieu_moi.txt",
        privacy_label="local_only",
        text="Nội dung người dùng vừa tải lên.",
        included_chars=32,
        truncated=False,
    )

    # Monkeypatch background thread start to avoid spinning up worker
    monkeypatch.setattr(adapter, "start_workspace_chat_background_drain", lambda *a, **kw: None)

    enqueued = adapter.reconcile_and_enqueue_workspace_chat_sources(
        (temp_source,),
        config=config,
    )
    # Temporary source must be enqueued
    assert enqueued == 1

    statuses = adapter.get_workspace_chat_source_preparation_status(
        (temp_source,),
        config=config,
    )
    assert statuses.get("temporary:temp_src_1") == adapter.PREP_STATE_PENDING

def test_notebook_short_circuits_while_temporary_enqueues_together(tmp_path: Path, monkeypatch) -> None:
    """BGE-ERROR-CODE-HOME: one reconcile call — notebook ready instantly, temporary enqueued."""
    canary_dir = tmp_path / "canary_runtime"
    config = adapter.WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        runtime_root=canary_dir,
    )
    db_path = adapter._get_ledger_db_path(config)
    adapter._init_preparation_ledger_db(db_path)
    with adapter._PREPARATION_LOCK:
        adapter._PREPARATION_REGISTRY.clear()

    notebook_source = WorkspaceAIContextSource(
        source_id="nb_src_joint",
        source_scope=SOURCE_SCOPE_NOTEBOOK,
        source_type="plain_text",
        title="tai_lieu_notebook_chung.txt",
        privacy_label="local_only",
        text="Nội dung notebook có sẵn trong production index.",
        included_chars=50,
        truncated=False,
    )
    temp_source = WorkspaceAIContextSource(
        source_id="temp_src_joint",
        source_scope=SOURCE_SCOPE_TEMPORARY,
        source_type="plain_text",
        title="tai_lieu_moi_chung.txt",
        privacy_label="local_only",
        text="Nội dung người dùng vừa tải lên.",
        included_chars=32,
        truncated=False,
    )

    # Monkeypatch background thread start to avoid spinning up worker
    monkeypatch.setattr(adapter, "start_workspace_chat_background_drain", lambda *a, **kw: None)

    enqueued = adapter.reconcile_and_enqueue_workspace_chat_sources(
        (notebook_source, temp_source),
        config=config,
    )
    # Only the temporary source enters the preparation queue
    assert enqueued == 1

    statuses = adapter.get_workspace_chat_source_preparation_status(
        (notebook_source, temp_source),
        config=config,
    )
    assert statuses.get("notebook:nb_src_joint") == adapter.PREP_STATE_READY
    assert statuses.get("temporary:temp_src_joint") == adapter.PREP_STATE_PENDING


def test_pipeline_read_only_vs_mutable_missing_source_file_behavior(tmp_path: Path) -> None:
    """Verifies pipeline behavior for indexed sources whose original file is missing from disk:
    1. In mutable mode (index_read_only=False): prepare() reports status='missing',
       and query() sets expected fingerprint to '__source_unavailable__'.
    2. In read-only mode (index_read_only=True): prepare() recognizes the document from index
       (status='unchanged'), and query() retrieves successfully without requiring raw file on disk.
    """
    runtime = tmp_path / "runtime"
    source_file = tmp_path / "manual.txt"
    source_file.write_text("Hướng dẫn bảo trì động cơ bước và laser scanner unit.", encoding="utf-8")
    source = SourceSpec(source_file, document_id="doc_manual_001")

    # Step 1: Ingest into index in mutable mode
    cfg_mutable = RagV2DevConfig(runtime_root=runtime, index_read_only=False, max_chunk_chars=120)
    with RagV2DevPipeline(cfg_mutable) as p_mut:
        ingest_rep = p_mut.ingest([source])
        assert ingest_rep.indexed_chunk_count > 0

    # Step 2: Delete original file from disk (simulating deployment without raw sources)
    source_file.unlink()
    assert not source_file.is_file()

    # Step 3: Test mutable mode (index_read_only=False) -> MUST retain legacy missing behavior
    with RagV2DevPipeline(cfg_mutable) as p_mut:
        ingest_rep_mut = p_mut.ingest([source])
        assert len(ingest_rep_mut.items) == 1
        assert ingest_rep_mut.items[0].status == "failed"
        assert "source_unavailable" in ingest_rep_mut.items[0].warning_codes

        # Query in mutable mode with missing file abstains due to __source_unavailable__
        query_res = p_mut.query("động cơ bước", [source])
        assert query_res.evidence_pack.item_count == 0
        assert "stale_fingerprint_excluded_all_chunks" in query_res.evidence_pack.insufficiency_reasons

    # Step 4: Test read-only mode (index_read_only=True) -> retrieves from index, treated as unchanged
    cfg_readonly = RagV2DevConfig(
        runtime_root=runtime,
        index_read_only=True,
        ensure_embeddings_on_open=False,
        max_chunk_chars=120,
    )
    with RagV2DevPipeline(cfg_readonly) as p_ro:
        ingest_rep_ro = p_ro.ingest([source])
        assert len(ingest_rep_ro.items) == 1
        assert ingest_rep_ro.items[0].status == "unchanged"
        assert ingest_rep_ro.items[0].chunk_count > 0

        # Query in read-only mode successfully finds evidence from library.sqlite
        query_res_ro = p_ro.query("động cơ bước", [source])
        assert query_res_ro.evidence_pack.item_count > 0
        assert query_res_ro.evidence_pack.items[0].document_id == "doc_manual_001"

