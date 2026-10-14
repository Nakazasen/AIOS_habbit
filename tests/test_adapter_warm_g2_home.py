"""Comprehensive tests for DESKTOP-SPEED-FIX-G2-ADAPTER-WARM-HOME.

Covers:
- ARCH-04: Removal of global _LAST_WARMUP_PIPE_CONFIG; deterministic resolution of
  pipe_config from explicit pipe_config or collection_id across all status, progress,
  and warm-up entrypoints.
- ARCH-07: Per-collection and dedicated user-target warm executors with explicit worker
  bounds so user target collection warming is never blocked by a sequential background
  warm task on another collection; preserves priority yield.
- ARCH-11: SQL IN (...) batch pushdown in _get_covered_source_fingerprints(read_only=True)
  when candidate_doc_ids is provided, with 100% semantic equivalence to legacy full
  SELECT DISTINCT scan.
- ARCH-16: _DOMAIN_SPECS_QUERY_CACHE and _prewarm_domain_specs_async keyed by
  index_domain.extract_exact_mechanical_identifiers(question) instead of raw str(question),
  preserving 100% identical SourceSpec outputs for both normal and mechanical-ID questions.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
import threading
import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from aios_habit import index_domain
import aios_habit.workspace_chat_rag_v2_adapter as adapter


def _make_canary_config(tmp_path: Path) -> adapter.WorkspaceChatRagV2CanaryConfig:
    model_dir = tmp_path / "pinned-bge-m3"
    model_dir.mkdir(parents=True, exist_ok=True)
    return adapter.WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        requested_profile="bge_m3_hybrid",
        runtime_root=tmp_path / "rag_runtime",
        bge_m3_model_path=model_dir,
        bge_m3_model_revision="rev-g2-test",
        bge_m3_model_checksum="sha256:" + "b" * 64,
        fail_closed_on_error=True,
    )


# ---------------------------------------------------------------------------
# ARCH-04 Tests
# ---------------------------------------------------------------------------


def test_arch04_last_warmup_pipe_config_global_removed() -> None:
    """_LAST_WARMUP_PIPE_CONFIG global must not exist on workspace_chat_rag_v2_adapter."""
    assert not hasattr(adapter, "_LAST_WARMUP_PIPE_CONFIG")


def test_arch04_no_cross_collection_pipe_config_leakage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Warming collection 'lsu' must not leak its pipe_config to subsequent calls without pipe_config."""
    config = _make_canary_config(tmp_path)
    monkeypatch.setattr(
        "aios_habit.workspace_chat_store.load_collection",
        lambda col_id: SimpleNamespace(id=col_id, storage_root=""),
    )

    lsu_pipe_cfg = adapter._pipeline_config(
        config, config.requested_profile, read_only=True, collection_id="lsu"
    )
    tri_thuc_pipe_cfg = adapter._warmup_pipeline_config(config)
    assert lsu_pipe_cfg.runtime_root != tri_thuc_pipe_cfg.runtime_root

    init_seen: list[Any] = []
    ready_seen: list[Any] = []
    readiness_seen: list[Any] = []

    monkeypatch.setattr(
        adapter,
        "initialize_workspace_chat_rag_v2_worker",
        lambda cfg, *, timeout_s=None, pipe_config=None, collection_id=None: (
            init_seen.append((pipe_config, collection_id)) or {"status": "ok"}
        ),
    )
    monkeypatch.setattr(adapter._SUBPROCESS_CLIENT, "_persistent_applies", lambda cfg: True)
    monkeypatch.setattr(
        adapter._SUBPROCESS_CLIENT,
        "is_ready",
        lambda cfg: ready_seen.append(cfg) or (cfg.runtime_root == lsu_pipe_cfg.runtime_root),
    )
    monkeypatch.setattr(
        adapter._SUBPROCESS_CLIENT,
        "readiness",
        lambda cfg: readiness_seen.append(cfg)
        or {
            "alive": cfg.runtime_root == lsu_pipe_cfg.runtime_root,
            "ready": cfg.runtime_root == lsu_pipe_cfg.runtime_root,
            "pid": 1234 if cfg.runtime_root == lsu_pipe_cfg.runtime_root else None,
            "reason": "",
        },
    )

    # 1. Warm 'lsu' explicitly
    ok = adapter.ensure_workspace_chat_worker_warming(
        config=config,
        blocking=True,
        pipe_config=lsu_pipe_cfg,
    )
    assert ok is True

    # 2. Calling is_workspace_chat_worker_warmed without pipe_config must check tri_thuc (False), NOT lsu (True)
    ready_seen.clear()
    assert adapter.is_workspace_chat_worker_warmed(config=config) is False
    assert len(ready_seen) == 1
    assert ready_seen[0].runtime_root == tri_thuc_pipe_cfg.runtime_root

    # 3. Calling with explicit collection_id="lsu" checks lsu (True)
    ready_seen.clear()
    assert adapter.is_workspace_chat_worker_warmed(config=config, collection_id="lsu") is True
    assert len(ready_seen) == 1
    assert ready_seen[0].runtime_root == lsu_pipe_cfg.runtime_root

    # 4. Calling get_workspace_chat_worker_progress without pipe_config checks tri_thuc, NOT lsu
    readiness_seen.clear()
    prog_default = adapter.get_workspace_chat_worker_progress(config=config)
    assert prog_default["ready"] is False
    assert len(readiness_seen) == 1
    assert readiness_seen[0].runtime_root == tri_thuc_pipe_cfg.runtime_root

    # 5. Calling get_workspace_chat_worker_progress with collection_id="lsu" checks lsu
    readiness_seen.clear()
    prog_lsu = adapter.get_workspace_chat_worker_progress(config=config, collection_id="lsu")
    assert prog_lsu["ready"] is True
    assert prog_lsu["pid"] == 1234
    assert len(readiness_seen) == 1
    assert readiness_seen[0].runtime_root == lsu_pipe_cfg.runtime_root

    # 6. Calling ensure_workspace_chat_worker_warming with collection_id="dieu_tra_loi" resolves dieu_tra_loi
    init_seen.clear()
    monkeypatch.setattr(adapter._SUBPROCESS_CLIENT, "is_ready", lambda cfg: False)
    assert (
        adapter.ensure_workspace_chat_worker_warming(
            config=config,
            blocking=True,
            collection_id="dieu_tra_loi",
        )
        is True
    )
    assert len(init_seen) == 1
    resolved_cfg, _ = init_seen[0]
    assert resolved_cfg is not None
    assert resolved_cfg.runtime_root.name == "dieu_tra_loi"
    assert adapter._collection_id_from_pipe_config(resolved_cfg) == "dieu_tra_loi"


# ---------------------------------------------------------------------------
# ARCH-07 Tests
# ---------------------------------------------------------------------------


def test_arch07_executor_separation_and_worker_bounds() -> None:
    """Verify per-collection executors and user-target warm executor have explicit bounds."""
    assert adapter._MAX_WARM_COLLECTION_EXECUTORS == 4
    assert adapter._MAX_USER_TARGET_WARM_WORKERS == 2

    ex_lsu = adapter._get_background_warm_executor("lsu")
    ex_th = adapter._get_background_warm_executor("tong_hop")
    ex_dtl = adapter._get_background_warm_executor("dieu_tra_loi")
    ex_tt = adapter._get_background_warm_executor("tri_thuc")
    ex_def = adapter._get_background_warm_executor("default")
    ex_target = adapter._get_user_target_warm_executor()

    assert ex_lsu is not ex_th
    assert ex_lsu is not ex_dtl
    assert ex_lsu is not ex_tt
    assert ex_tt is ex_def  # default and tri_thuc normalize to same collection
    assert ex_target is not ex_lsu
    assert ex_target is not ex_th

    assert ex_lsu._max_workers == 1
    assert ex_th._max_workers == 1
    assert ex_dtl._max_workers == 1
    assert ex_tt._max_workers == 1
    assert ex_target._max_workers == 2


def test_arch07_user_target_warming_not_blocked_by_slow_background_warming(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """While background warming on 'lsu' is mid-initialization, user target 'tong_hop' warms immediately."""
    config = _make_canary_config(tmp_path)
    monkeypatch.setattr(
        "aios_habit.workspace_chat_store.load_collection",
        lambda col_id: SimpleNamespace(id=col_id, storage_root=""),
    )

    lsu_cfg = adapter._pipeline_config(
        config, config.requested_profile, read_only=True, collection_id="lsu"
    )
    tong_hop_cfg = adapter._pipeline_config(
        config, config.requested_profile, read_only=True, collection_id="tong_hop"
    )

    lsu_entered = threading.Event()
    release_lsu = threading.Event()
    tong_hop_done = threading.Event()
    completion_order: list[str] = []

    def _mock_init_worker(cfg, *, timeout_s=None, pipe_config=None, collection_id=None):
        col = adapter._collection_id_from_pipe_config(pipe_config) or collection_id
        if col == "lsu":
            lsu_entered.set()
            release_lsu.wait(timeout=5.0)
            completion_order.append("lsu")
        elif col == "tong_hop":
            completion_order.append("tong_hop")
            tong_hop_done.set()
        return {"status": "ok"}

    monkeypatch.setattr(adapter, "initialize_workspace_chat_rag_v2_worker", _mock_init_worker)
    monkeypatch.setattr(adapter._SUBPROCESS_CLIENT, "_persistent_applies", lambda cfg: False)

    with adapter._WARMUP_LOCK:
        adapter._WARMUP_ATTEMPTS.clear()
        adapter._WARMUP_IN_QUEUE.clear()
        adapter._WARMUP_RUNNING_KEYS.clear()

    try:
        # 1. Start slow background warm on 'lsu'
        assert (
            adapter.ensure_workspace_chat_worker_warming(
                config=config,
                blocking=False,
                pipe_config=lsu_cfg,
                collection_id="lsu",
            )
            is True
        )
        assert lsu_entered.wait(timeout=2.0), "lsu background warm did not start"

        # 2. User turn activates retrieval for 'tong_hop' and triggers non-blocking warm
        t0 = time.perf_counter()
        with adapter.user_retrieval_priority_scope("tong_hop"):
            assert (
                adapter.ensure_workspace_chat_worker_warming(
                    config=config,
                    blocking=False,
                    pipe_config=tong_hop_cfg,
                    collection_id="tong_hop",
                )
                is True
            )
            finished_fast = tong_hop_done.wait(timeout=1.0)
            elapsed_tong_hop_ms = (time.perf_counter() - t0) * 1000.0

        assert finished_fast is True, "tong_hop was blocked by lsu background warm!"
        assert elapsed_tong_hop_ms < 250.0
        # lsu is still blocked because release_lsu has not been set yet
        assert completion_order == ["tong_hop"]
    finally:
        release_lsu.set()


# ---------------------------------------------------------------------------
# ARCH-11 Tests
# ---------------------------------------------------------------------------


def _create_large_chunks_db(db_path: Path, total_docs: int = 640) -> None:
    """Create a multi-hundred-document SQLite index to test batching and SQL pushdown."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                source_path TEXT NOT NULL,
                source_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                text TEXT NOT NULL,
                normalized_text TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                privacy_labels_json TEXT NOT NULL,
                source_fingerprint TEXT,
                checksum TEXT,
                retrievable INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute("CREATE INDEX idx_chunks_retrievable ON chunks(retrievable, document_id)")
        rows = []
        for i in range(total_docs):
            doc_id = f"doc_{i:04d}"
            # Every 7th document has retrievable=0 only
            retrievable = 0 if (i % 7 == 0) else 1
            rows.append(
                (
                    f"chk_{i:04d}_a",
                    doc_id,
                    f"/docs/{doc_id}.pdf",
                    f"{doc_id}.pdf",
                    "pdf",
                    f"content {i}",
                    f"content {i}",
                    "{}",
                    "[]",
                    f"fp_{i:04d}",
                    f"sum_{i:04d}",
                    retrievable,
                )
            )
            if i % 3 == 0:
                rows.append(
                    (
                        f"chk_{i:04d}_b",
                        doc_id,
                        f"/docs/{doc_id}.pdf",
                        f"{doc_id}.pdf",
                        "pdf",
                        f"content {i} part 2",
                        f"content {i} part 2",
                        "{}",
                        "[]",
                        f"fp_{i:04d}",
                        f"sum_{i:04d}_b",
                        retrievable,
                    )
                )
        conn.executemany(
            """
            INSERT INTO chunks (
                chunk_id, document_id, source_path, source_name, file_type,
                text, normalized_text, metadata_json, privacy_labels_json,
                source_fingerprint, checksum, retrievable
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _legacy_readonly_covered_fingerprints(
    db_path: Path,
    candidate_doc_ids: list[str] | None,
) -> dict[str, str]:
    """Reference implementation of the old read_only full SELECT DISTINCT scan."""
    uri = db_path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        rows = conn.execute(
            "SELECT DISTINCT document_id FROM chunks WHERE retrievable = 1"
        ).fetchall()
    covered_set = {str(r[0]) for r in rows if r and r[0] is not None}
    if candidate_doc_ids is None:
        return {d: "" for d in covered_set}
    candidate_list = tuple(dict.fromkeys(str(d) for d in candidate_doc_ids if d))
    return {d: "" for d in candidate_list if d in covered_set}


def test_arch11_readonly_sql_in_batch_pushdown_and_semantic_equivalence(
    tmp_path: Path,
) -> None:
    """Verify read_only=True with candidate_doc_ids uses batched IN (...) SQL and matches legacy 100%."""
    adapter.clear_covered_source_fingerprints_cache()
    db_path = tmp_path / "arch11_library.sqlite"
    _create_large_chunks_db(db_path, total_docs=640)

    # 560 candidates (>500 so it splits into 2 batches: 500 + 60), including missing and retrievable=0 docs
    candidates = [f"doc_{i:04d}" for i in range(540)] + [f"missing_{j:03d}" for j in range(20)]

    expected = _legacy_readonly_covered_fingerprints(db_path, candidates)

    executed_sql: list[str] = []
    real_connect = sqlite3.connect

    def _tracing_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        conn = real_connect(*args, **kwargs)
        conn.set_trace_callback(executed_sql.append)
        return conn

    with patch("aios_habit.workspace_chat_rag_v2_adapter.sqlite3.connect", side_effect=_tracing_connect):
        actual = adapter._get_covered_source_fingerprints(
            db_path,
            candidate_doc_ids=candidates,
            read_only=True,
        )

    assert actual == expected
    assert list(actual.keys()) == list(expected.keys())

    select_stmts = [s.strip() for s in executed_sql if s.strip().upper().startswith("SELECT")]
    # Must have executed exactly 2 batched SELECT statements (500 + 60) with IN (...)
    assert len(select_stmts) == 2
    for stmt in select_stmts:
        assert "document_id IN (" in stmt
        assert "WHERE retrievable = 1 AND document_id IN" in stmt

    # Second call with subset + already checked missing docs must make ZERO SQLite connections
    with patch("aios_habit.workspace_chat_rag_v2_adapter.sqlite3.connect") as mock_conn:
        subset = candidates[:50] + ["missing_005"]
        actual_cached = adapter._get_covered_source_fingerprints(
            db_path,
            candidate_doc_ids=subset,
            read_only=True,
        )
        mock_conn.assert_not_called()
    assert actual_cached == _legacy_readonly_covered_fingerprints(db_path, subset)

    # Empty candidate list returns {} immediately with 0 SQLite connections
    with patch("aios_habit.workspace_chat_rag_v2_adapter.sqlite3.connect") as mock_conn:
        assert adapter._get_covered_source_fingerprints(db_path, candidate_doc_ids=[], read_only=True) == {}
        mock_conn.assert_not_called()

    # Full scan (candidate_doc_ids=None) still works and matches legacy 100%
    full_actual = adapter._get_covered_source_fingerprints(
        db_path,
        candidate_doc_ids=None,
        read_only=True,
    )
    full_expected = _legacy_readonly_covered_fingerprints(db_path, None)
    assert full_actual == full_expected


# ---------------------------------------------------------------------------
# ARCH-16 Tests
# ---------------------------------------------------------------------------


def test_arch16_domain_specs_cache_key_uses_exact_mechanical_identifiers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify _DOMAIN_SPECS_QUERY_CACHE and _prewarm_domain_specs_async use extract_exact_mechanical_identifiers."""
    adapter.clear_covered_source_fingerprints_cache()
    db_path = tmp_path / "arch16_library.sqlite"
    _create_large_chunks_db(db_path, total_docs=20)

    calls: list[tuple[str | None, str | None]] = []

    def _fake_get_specs_for_domain(
        domain: str | None,
        path: Path | str | None = None,
        question: str | None = None,
    ) -> tuple[Any, ...]:
        calls.append((domain, question))
        exact_ids = index_domain.extract_exact_mechanical_identifiers(str(question or ""))
        base = [
            SimpleNamespace(source_id="s1", document_id="doc_0001", path=str(db_path)),
            SimpleNamespace(source_id="s2", document_id="doc_0002", path=str(db_path)),
        ]
        if exact_ids:
            for idx, tok in enumerate(exact_ids, start=10):
                base.append(
                    SimpleNamespace(
                        source_id=f"s_{tok}",
                        document_id=f"doc_00{idx}",
                        path=str(db_path),
                    )
                )
        return tuple(base)

    monkeypatch.setattr(index_domain, "get_specs_for_domain", _fake_get_specs_for_domain)

    # 1. Two distinct normal questions (no mechanical IDs) must hit the exact same cache key
    q1 = "Quy trình kiểm tra ngoại quan cụm LSU tại dây chuyền lắp ráp là gì?"
    q2 = "Hướng dẫn xử lý khi bề mặt thấu kính bị bụi bẩn trong phòng sạch?"
    assert index_domain.extract_exact_mechanical_identifiers(q1) == ()
    assert index_domain.extract_exact_mechanical_identifiers(q2) == ()

    specs1 = adapter._get_cached_specs_for_domain("lsu", db_path, question=q1)
    specs2 = adapter._get_cached_specs_for_domain("lsu", db_path, question=q2)

    assert specs1 == specs2
    assert len(calls) == 1  # Second normal question was a 100% cache HIT!

    # Check the actual key structure in _DOMAIN_SPECS_QUERY_CACHE
    cache_keys = list(adapter._DOMAIN_SPECS_QUERY_CACHE.keys())
    assert len(cache_keys) == 1
    assert cache_keys[0][0] == "lsu"
    assert cache_keys[0][4] == ()

    # 2. Question with mechanical identifiers ('g1', 'g2', 'C7620') gets its own exact_ids key
    q_mech_1 = "Cho biết dung sai vị trí g1 và g2 của lỗi C7620?"
    expected_ids = index_domain.extract_exact_mechanical_identifiers(q_mech_1)
    assert expected_ids == ("g1", "g2", "C7620")

    specs_mech_1 = adapter._get_cached_specs_for_domain("lsu", db_path, question=q_mech_1)
    assert len(calls) == 2
    assert [s.document_id for s in specs_mech_1] == [
        "doc_0001",
        "doc_0002",
        "doc_0010",
        "doc_0011",
        "doc_0012",
    ]

    # Another question with the same mechanical IDs hits cache
    q_mech_2 = "Kiểm tra điểm g1, g2 khi báo mã C7620 như thế nào?"
    assert index_domain.extract_exact_mechanical_identifiers(q_mech_2) == expected_ids
    specs_mech_2 = adapter._get_cached_specs_for_domain("lsu", db_path, question=q_mech_2)
    assert specs_mech_2 == specs_mech_1
    assert len(calls) == 2

    # 3. _prewarm_domain_specs_async uses exact_ids in dedup_key and populates cache for subsequent questions
    adapter.clear_covered_source_fingerprints_cache()
    calls.clear()

    adapter._prewarm_domain_specs_async(
        "dieu_tra_loi",
        db_path,
        question="Câu hỏi làm ấm đầu tiên không có mã cơ khí",
    )
    deadline = time.time() + 2.0
    while not adapter._DOMAIN_SPECS_QUERY_CACHE and time.time() < deadline:
        time.sleep(0.02)

    assert len(calls) == 1
    # Subsequent turn with a completely different normal question hits the prewarmed cache!
    specs_after_prewarm = adapter._get_cached_specs_for_domain(
        "dieu_tra_loi",
        db_path,
        question="Câu hỏi thứ hai hoàn toàn khác câu làm ấm",
    )
    assert len(calls) == 1
    assert len(specs_after_prewarm) == 2
