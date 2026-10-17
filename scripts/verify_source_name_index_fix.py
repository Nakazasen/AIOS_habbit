import time
import sqlite3
from pathlib import Path
from aios_habit.rag_v2.index import LocalChunkIndex, ensure_index_source_name_index
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceChatRagV2CanaryConfig,
    _pipeline_config,
    _COVERAGE_CACHE,
    _COVERAGE_CACHE_LOCK,
    get_workspace_chat_source_preparation_status,
    is_production_index_available,
)
from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_models import SOURCE_SCOPE_NOTEBOOK, SOURCE_SCOPE_TEMPORARY

def main():
    db_path = Path(r"C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\lsu\library.sqlite")
    print(f"Target DB: {db_path} (exists: {db_path.is_file()}, size: {db_path.stat().st_size / (1024*1024):.2f} MB)")

    # 1. Check index existence before
    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as ro:
        indexes = [r[1] for r in ro.execute("PRAGMA index_list(chunks)").fetchall()]
        print("Indexes before opening through app:", indexes)
        has_before = "idx_chunks_retrievable_source_name" in indexes
        print("Has idx_chunks_retrievable_source_name before:", has_before)

    # 2. Open via application mechanism: LocalChunkIndex
    print("\n--- OPENING VIA APPLICATION MECHANISM (LocalChunkIndex) ---")
    t0 = time.perf_counter()
    index_instance = LocalChunkIndex(db_path, read_only=True)
    t1 = time.perf_counter()
    initial_create_ms = (t1 - t0) * 1000.0
    print(f"Time to open and auto-create index on {db_path.name}: {initial_create_ms:.2f} ms ({initial_create_ms/1000.0:.4f} s)")
    print(f"index_instance._has_retrievable_source_name_index: {index_instance._has_retrievable_source_name_index}")

    # 3. Check index existence after
    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as ro:
        indexes_after = [r[1] for r in ro.execute("PRAGMA index_list(chunks)").fetchall()]
        print("Indexes after opening through app:", indexes_after)
        has_after = "idx_chunks_retrievable_source_name" in indexes_after
        print("Has idx_chunks_retrievable_source_name after:", has_after)

        # 4. EXPLAIN QUERY PLAN
        plan = ro.execute(
            "EXPLAIN QUERY PLAN SELECT document_id FROM chunks WHERE source_name=? AND retrievable=1 LIMIT 1",
            ("test_candidate_title",)
        ).fetchall()
        print("\nEXPLAIN QUERY PLAN for exact candidate title lookup:")
        for row in plan:
            print(f"  {row}")

        plan_like = ro.execute(
            "EXPLAIN QUERY PLAN SELECT document_id FROM chunks WHERE source_name LIKE '%C7620%' AND retrievable=1 LIMIT 1"
        ).fetchall()
        print("\nEXPLAIN QUERY PLAN for C7620 fallback lookup:")
        for row in plan_like:
            print(f"  {row}")

    # 5. Measure scanning 494 sources under cold cache
    print("\n--- MEASURING 494 SOURCES STATUS SCAN (COLD CACHE) ---")
    cfg = WorkspaceChatRagV2CanaryConfig.from_env()

    # Create 494 sources: 35 existing LSU document titles, 459 nonexistent / outside sources
    # Read actual document_id / source_name from library.sqlite
    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as ro:
        existing_rows = ro.execute(
            "SELECT DISTINCT document_id, source_name FROM chunks WHERE retrievable=1 LIMIT 35"
        ).fetchall()

    test_sources = []
    # Add the 35 existing sources
    for doc_id, src_name in existing_rows:
        test_sources.append(
            WorkspaceAIContextSource(
                source_id=doc_id,
                source_scope=SOURCE_SCOPE_NOTEBOOK,
                source_type="file",
                title=src_name or "Doc Title",
                privacy_label="local_only",
                text="sample document text content",
                included_chars=28,
            )
        )
    # Add 459 nonexistent sources to reach 494 sources total
    for i in range(len(test_sources), 494):
        test_sources.append(
            WorkspaceAIContextSource(
                source_id=f"src_dummy_{i:04d}",
                source_scope=SOURCE_SCOPE_NOTEBOOK,
                source_type="file",
                title=f"Nonexistent Dummy Source Document #{i:04d}",
                privacy_label="local_only",
                text="sample document text content",
                included_chars=28,
            )
        )

    print(f"Total test sources created: {len(test_sources)} (35 matching + {len(test_sources)-35} misses)")

    # Test A: Direct scan with cold _COVERAGE_CACHE (testing the index speedup)
    with _COVERAGE_CACHE_LOCK:
        _COVERAGE_CACHE.clear()

    t_scan_start = time.perf_counter()
    statuses = get_workspace_chat_source_preparation_status(test_sources, config=cfg)
    t_scan_end = time.perf_counter()
    scan_duration_s = t_scan_end - t_scan_start

    ready_cnt = sum(1 for v in statuses.values() if v == "ready")
    unready_cnt = len(statuses) - ready_cnt
    print(f"Cold scan 494 sources duration: {scan_duration_s:.4f} s ({scan_duration_s * 1000:.2f} ms)")
    print(f"Statuses count: {len(statuses)}, ready: {ready_cnt}, other: {unready_cnt}")

    # Test B: Warm cache repeat scan
    t_warm_start = time.perf_counter()
    statuses_warm = get_workspace_chat_source_preparation_status(test_sources, config=cfg)
    t_warm_end = time.perf_counter()
    warm_duration_s = t_warm_end - t_warm_start
    print(f"Warm scan 494 sources duration: {warm_duration_s:.4f} s ({warm_duration_s * 1000:.2f} ms)")

    # Test C: Also ensure the other collections (mom, dieu_tra_loi, tong_hop, tri_thuc) have the index
    print("\n--- ENSURING OTHER PRODUCTION COLLECTIONS ---")
    for coll in ["mom", "dieu_tra_loi", "tong_hop", "tri_thuc"]:
        p = Path(f"C:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/{coll}/library.sqlite")
        if p.is_file():
            t_c0 = time.perf_counter()
            ok = ensure_index_source_name_index(p)
            t_c1 = time.perf_counter()
            print(f"Collection {coll}: auto-created/verified = {ok} in {(t_c1 - t_c0)*1000:.2f} ms")

    # Test D: UI prompt submission path under prod_index_ready = True
    print("\n--- TEST D: UI PROMPT SUBMISSION PATH (prod_index_ready = True) ---")
    ui_sources = list(test_sources)
    ui_sources[-2] = WorkspaceAIContextSource(
        source_id="temp_01",
        source_scope=SOURCE_SCOPE_TEMPORARY,
        source_type="file",
        title="Temporary Attached Doc 1",
        privacy_label="local_only",
        text="temporary doc text",
        included_chars=18,
    )
    ui_sources[-1] = WorkspaceAIContextSource(
        source_id="temp_02",
        source_scope=SOURCE_SCOPE_TEMPORARY,
        source_type="file",
        title="Temporary Attached Doc 2",
        privacy_label="local_only",
        text="temporary doc text 2",
        included_chars=20,
    )
    prod_ready = is_production_index_available(cfg)
    t_ui_start = time.perf_counter()
    if prod_ready:
        temp_to_check = tuple(s for s in ui_sources if getattr(s, "source_scope", "") == SOURCE_SCOPE_TEMPORARY)
        temp_states = get_workspace_chat_source_preparation_status(temp_to_check, config=cfg) if temp_to_check else {}
        all_states = {
            f"{getattr(s, 'source_scope', '')}:{getattr(s, 'source_id', '')}": (
                temp_states.get(f"{getattr(s, 'source_scope', '')}:{getattr(s, 'source_id', '')}", "ready")
                if getattr(s, "source_scope", "") == SOURCE_SCOPE_TEMPORARY
                else "ready"
            )
            for s in ui_sources
        }
    else:
        all_states = get_workspace_chat_source_preparation_status(ui_sources, config=cfg)
    t_ui_end = time.perf_counter()
    ui_duration_ms = (t_ui_end - t_ui_start) * 1000.0
    print(f"UI Path (prod_index_ready={prod_ready}) 494 sources scan: {ui_duration_ms:.2f} ms ({ui_duration_ms/1000.0:.6f} s)")


if __name__ == "__main__":
    main()
