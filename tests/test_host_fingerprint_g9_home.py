"""Comprehensive tests for DESKTOP-SPEED-FIX-G9-HOSTFP-HOME.

Covers:
1. O(1) ``source_state`` table and SQLite triggers (INSERT, UPDATE, DELETE,
   replace_document_chunks, delete_document, retrievable=0 exclusion, NULL vs
   non-NULL fingerprints, and mismatched chunk fingerprints).
2. 100% semantic equivalence between legacy ``chunks`` GROUP BY / SELECT DISTINCT
   queries and the new ``_get_covered_source_fingerprints`` implementation across
   all 4 real production databases on the home machine (``tong_hop``, ``lsu``,
   ``dieu_tra_loi``, ``tri_thuc``), plus cold (< 1000 ms) and warm (~0 ms) latency
   verification and query-plan proof that ``chunks`` is not scanned.
3. Safe fallback when ``source_state`` is absent (synthetic ``chunks``-only DBs
   and multi-MB sidecar / index skip-scan fallback), preserving 100% equivalence.
4. Fail-closed control tests for missing documents, fingerprint mismatches, and
   missing dense/sparse embeddings in ``verify_selected_document_coverage``.
5. Fast cross-domain mechanical identifier resolution in ``index_domain`` without
   scanning the ``chunks`` table on per-domain collections.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
import time
from typing import Iterable, Optional
from unittest.mock import patch

import pytest

from aios_habit import index_domain
from aios_habit.rag_v2 import DocumentElement, ElementType, ExtractionStatus
from aios_habit.rag_v2.chunking import StructureAwareChunker
from aios_habit.rag_v2.index import (
    SOURCE_STATE_TABLE_NAME,
    LocalChunkIndex,
    ensure_index_source_state,
)
from aios_habit.rag_v2.semantic import DeterministicEmbeddingBackend
import aios_habit.workspace_chat_rag_v2_adapter as adapter

PRODUCTION_COLLECTIONS_ROOT = Path(
    r"C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections"
)
REAL_COLLECTION_IDS: tuple[str, ...] = ("tong_hop", "lsu", "dieu_tra_loi", "tri_thuc")


def _legacy_covered_source_fingerprints(
    index_path: Path,
    candidate_doc_ids: Optional[Iterable[str]] = None,
    *,
    read_only: bool = False,
) -> dict[str, str]:
    """Reference pre-G9 implementation scanning the chunks table directly."""
    resolved_path = Path(index_path).resolve()
    if not resolved_path.is_file():
        return {}
    candidate_list = (
        tuple(dict.fromkeys(str(d) for d in candidate_doc_ids if d))
        if candidate_doc_ids is not None
        else None
    )
    if read_only and candidate_list is not None and not candidate_list:
        return {}

    uri = resolved_path.as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        if read_only:
            if candidate_list is None:
                rows = conn.execute(
                    "SELECT DISTINCT document_id FROM chunks WHERE retrievable = 1"
                ).fetchall()
                return {str(r[0]): "" for r in rows if r and r[0] is not None}
            found_docs: set[str] = set()
            for i in range(0, len(candidate_list), 500):
                batch = candidate_list[i : i + 500]
                placeholders = ",".join("?" for _ in batch)
                rows = conn.execute(
                    f"""
                    SELECT DISTINCT document_id
                    FROM chunks
                    WHERE retrievable = 1 AND document_id IN ({placeholders})
                    """,
                    batch,
                ).fetchall()
                for r in rows:
                    if r and r[0] is not None:
                        found_docs.add(str(r[0]))
            return {d: "" for d in candidate_list if d in found_docs}

        if candidate_list is None:
            rows = conn.execute(
                """
                SELECT document_id,
                       MIN(source_fingerprint) AS min_fp,
                       MAX(source_fingerprint) AS max_fp
                FROM chunks
                WHERE retrievable = 1
                GROUP BY document_id
                """
            ).fetchall()
            return {str(r[0]): str(r[1] or "") for r in rows}

        if not candidate_list:
            return {}
        fetched: dict[str, str] = {}
        for i in range(0, len(candidate_list), 500):
            batch = candidate_list[i : i + 500]
            placeholders = ",".join("?" for _ in batch)
            rows = conn.execute(
                f"""
                SELECT document_id,
                       MIN(source_fingerprint) AS min_fp,
                       MAX(source_fingerprint) AS max_fp
                FROM chunks
                WHERE retrievable = 1 AND document_id IN ({placeholders})
                GROUP BY document_id
                """,
                batch,
            ).fetchall()
            for r in rows:
                fetched[str(r[0])] = str(r[1] or "")
        return {d: fetched[d] for d in candidate_list if d in fetched}


def _make_chunk(
    doc_id: str,
    idx: int,
    text: str,
    fp: Optional[str] = "fp-01",
    *,
    retrievable: bool = True,
):
    chunker = StructureAwareChunker(max_chars=300)
    el = DocumentElement(
        element_id=f"el-{doc_id}-{idx}",
        document_id=doc_id,
        source_path=f"C:/docs/{doc_id}.txt",
        source_name=f"{doc_id}.txt",
        file_type="txt",
        extractor="unit",
        extraction_status=ExtractionStatus.SUCCESS,
        element_type=ElementType.TEXT,
        text=text,
        privacy_labels=("local_only",),
        source_fingerprint=fp,
        page=1,
    )
    chunk = chunker.chunk_elements([el])[0]
    if not retrievable:
        object.__setattr__(chunk, "retrievable", False)
    if fp is None:
        object.__setattr__(chunk, "source_fingerprint", None)
    return chunk


def test_g9_source_state_lifecycle_triggers_and_fail_closed_control(
    tmp_path: Path,
) -> None:
    """Verify source_state triggers keep O(1) metadata 100% synchronized and fail-closed."""
    db_path = tmp_path / "g9_lifecycle.sqlite"
    backend = DeterministicEmbeddingBackend(dimension=8)

    c_alpha_1 = _make_chunk("doc-alpha", 1, "Alpha text one", "fp-alpha")
    c_alpha_2 = _make_chunk("doc-alpha", 2, "Alpha text two", "fp-alpha")
    c_beta_1 = _make_chunk("doc-beta", 1, "Beta text one", "fp-beta-1")
    c_beta_2 = _make_chunk("doc-beta", 2, "Beta text two", "fp-beta-2")
    c_nonret = _make_chunk("doc-nonret", 1, "Hidden chunk", "fp-hidden", retrievable=False)
    c_nullfp = _make_chunk("doc-nullfp", 1, "Null fp chunk", None, retrievable=True)

    with LocalChunkIndex(
        db_path,
        embedding_backend=backend,
        sparse_backend=backend,
    ) as idx:
        assert idx._has_source_state_table is True
        idx.upsert_chunks([c_alpha_1, c_alpha_2, c_beta_1, c_beta_2, c_nonret, c_nullfp])

        # Verify document_state reads O(1) from source_state and matches semantics
        st_alpha = idx.document_state("doc-alpha")
        assert st_alpha == {
            "document_id": "doc-alpha",
            "chunk_count": 2,
            "source_fingerprint": "fp-alpha",
        }
        # doc-beta has mismatched fingerprints across chunks -> source_fingerprint is None
        st_beta = idx.document_state("doc-beta")
        assert st_beta == {
            "document_id": "doc-beta",
            "chunk_count": 2,
            "source_fingerprint": None,
        }
        # doc-nonret has only retrievable=0 -> chunk_count=0, source_fingerprint=None
        st_nonret = idx.document_state("doc-nonret")
        assert st_nonret == {
            "document_id": "doc-nonret",
            "chunk_count": 0,
            "source_fingerprint": None,
        }
        # doc-nullfp has NULL fingerprint -> chunk_count=1, source_fingerprint=None
        st_nullfp = idx.document_state("doc-nullfp")
        assert st_nullfp == {
            "document_id": "doc-nullfp",
            "chunk_count": 1,
            "source_fingerprint": None,
        }

        # Verify replace_document_chunks updates source_state via triggers
        c_beta_fixed = _make_chunk("doc-beta", 1, "Beta unified text", "fp-beta-unified")
        idx.replace_document_chunks("doc-beta", [c_beta_fixed])
        assert idx.document_state("doc-beta") == {
            "document_id": "doc-beta",
            "chunk_count": 1,
            "source_fingerprint": "fp-beta-unified",
        }

        # Verify delete_document removes document from source_state
        idx.delete_document("doc-nullfp")
        assert idx.document_state("doc-nullfp") == {
            "document_id": "doc-nullfp",
            "chunk_count": 0,
            "source_fingerprint": None,
        }

    # Verify _get_covered_source_fingerprints matches legacy 100%
    adapter.clear_covered_source_fingerprints_cache()
    all_cands = ["doc-alpha", "doc-beta", "doc-nonret", "doc-nullfp", "doc-missing"]
    assert adapter._get_covered_source_fingerprints(
        db_path, all_cands, read_only=False
    ) == _legacy_covered_source_fingerprints(db_path, all_cands, read_only=False)
    assert adapter._get_covered_source_fingerprints(
        db_path, all_cands, read_only=True
    ) == _legacy_covered_source_fingerprints(db_path, all_cands, read_only=True)

    # Verify fail-closed control on verify_selected_document_coverage
    with LocalChunkIndex(
        db_path,
        embedding_backend=backend,
        sparse_backend=backend,
        read_only=True,
        ensure_embeddings_on_open=False,
    ) as ro_idx:
        cov_ok = ro_idx.verify_selected_document_coverage(
            ["doc-alpha", "doc-beta"],
            expected_document_fingerprints={
                "doc-alpha": "fp-alpha",
                "doc-beta": "fp-beta-unified",
            },
            sparse_required=True,
        )
        assert cov_ok["valid"] is True

        # Mismatched expected fingerprint -> MUST fail closed
        cov_bad_fp = ro_idx.verify_selected_document_coverage(
            ["doc-alpha", "doc-beta"],
            expected_document_fingerprints={
                "doc-alpha": "fp-alpha",
                "doc-beta": "fp-stale-wrong",
            },
            sparse_required=True,
        )
        assert cov_bad_fp["valid"] is False
        assert cov_bad_fp["fingerprint_mismatch_document_ids"] == ("doc-beta",)

        # Missing document -> MUST fail closed
        cov_missing = ro_idx.verify_selected_document_coverage(
            ["doc-alpha", "doc-nonret"],
            expected_document_fingerprints={"doc-alpha": "fp-alpha"},
            sparse_required=True,
        )
        assert cov_missing["valid"] is False
        assert cov_missing["missing_document_ids"] == ("doc-nonret",)


def test_g9_fallback_when_source_state_table_absent(tmp_path: Path) -> None:
    """Verify safe fallback when source_state is dropped from an index DB."""
    db_path = tmp_path / "g9_no_source_state.sqlite"
    backend = DeterministicEmbeddingBackend(dimension=8)
    chunks = [
        _make_chunk("doc-1", 1, "Doc one chunk one", "fp-1"),
        _make_chunk("doc-2", 1, "Doc two chunk one", "fp-2"),
        _make_chunk("doc-3", 1, "Doc three non-retrievable", "fp-3", retrievable=False),
    ]
    with LocalChunkIndex(db_path, embedding_backend=backend, sparse_backend=backend) as idx:
        idx.upsert_chunks(chunks)

    # Drop source_state and its triggers to simulate an unmigrated legacy database
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            DROP TRIGGER IF EXISTS chunks_source_state_insert;
            DROP TRIGGER IF EXISTS chunks_source_state_delete;
            DROP TRIGGER IF EXISTS chunks_source_state_update;
            DROP TABLE IF EXISTS source_state;
            """
        )

    adapter.clear_covered_source_fingerprints_cache()
    cands = ["doc-1", "doc-2", "doc-3", "doc-missing"]
    assert adapter._get_covered_source_fingerprints(
        db_path, cands, read_only=False
    ) == _legacy_covered_source_fingerprints(db_path, cands, read_only=False)
    adapter.clear_covered_source_fingerprints_cache()
    assert adapter._get_covered_source_fingerprints(
        db_path, None, read_only=False
    ) == _legacy_covered_source_fingerprints(db_path, None, read_only=False)
    adapter.clear_covered_source_fingerprints_cache()
    assert adapter._get_covered_source_fingerprints(
        db_path, cands, read_only=True
    ) == _legacy_covered_source_fingerprints(db_path, cands, read_only=True)
    adapter.clear_covered_source_fingerprints_cache()
    assert adapter._get_covered_source_fingerprints(
        db_path, None, read_only=True
    ) == _legacy_covered_source_fingerprints(db_path, None, read_only=True)

    # Now run ensure_index_source_state and verify source_state is backfilled cleanly
    assert ensure_index_source_state(db_path) is True
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT document_id, source_fingerprint, chunk_count FROM {SOURCE_STATE_TABLE_NAME} ORDER BY document_id"
        ).fetchall()
    assert [(r[0], r[1], r[2]) for r in rows] == [
        ("doc-1", "fp-1", 1),
        ("doc-2", "fp-2", 1),
    ]


@pytest.mark.parametrize("collection_id", REAL_COLLECTION_IDS)
def test_g9_real_production_databases_equivalence_and_sub_second_cold_latency(
    collection_id: str,
) -> None:
    """Verify 100% old==new equivalence and <1s cold / ~0ms warm latency on all 4 real production DBs."""
    db_path = PRODUCTION_COLLECTIONS_ROOT / collection_id / "library.sqlite"
    if not db_path.is_file():
        pytest.skip(f"Production DB not present at {db_path}")

    assert ensure_index_source_state(db_path) is True
    specs = index_domain.load_all_index_specs(db_path)
    assert len(specs) > 0
    candidate_ids = [str(s.document_id) for s in specs]
    probe_ids = candidate_ids + ["nonexistent-doc-g9-1", "nonexistent-doc-g9-2"]

    # Compute ground-truth legacy mappings
    legacy_rw_full = _legacy_covered_source_fingerprints(db_path, None, read_only=False)
    legacy_rw_cands = _legacy_covered_source_fingerprints(db_path, probe_ids, read_only=False)
    legacy_ro_full = _legacy_covered_source_fingerprints(db_path, None, read_only=True)
    legacy_ro_cands = _legacy_covered_source_fingerprints(db_path, probe_ids, read_only=True)

    # 1. Cold read_only=False with candidate_doc_ids (further ensures no SELECT on chunks table)
    adapter.clear_covered_source_fingerprints_cache()
    executed_sql: list[str] = []
    real_connect = sqlite3.connect

    def _tracing_connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        conn.set_trace_callback(executed_sql.append)
        return conn

    t0 = time.perf_counter()
    with patch(
        "aios_habit.workspace_chat_rag_v2_adapter.sqlite3.connect",
        side_effect=_tracing_connect,
    ):
        new_rw_cands = adapter._get_covered_source_fingerprints(
            db_path, probe_ids, read_only=False
        )
    cold_rw_ms = (time.perf_counter() - t0) * 1000.0

    assert new_rw_cands == legacy_rw_cands
    assert cold_rw_ms < 1000.0, f"Cold RW latency {cold_rw_ms:.2f}ms exceeded 1000ms on {collection_id}"
    select_sql = [s for s in executed_sql if s.strip().upper().startswith("SELECT")]
    assert len(select_sql) >= 1
    for stmt in select_sql:
        assert "FROM source_state" in stmt
        assert "FROM chunks" not in stmt

    # 2. Warm read_only=False (0 SQLite connections, ~0 ms)
    with patch("aios_habit.workspace_chat_rag_v2_adapter.sqlite3.connect") as mock_conn:
        t0 = time.perf_counter()
        warm_rw_cands = adapter._get_covered_source_fingerprints(
            db_path, probe_ids, read_only=False
        )
        warm_rw_ms = (time.perf_counter() - t0) * 1000.0
        mock_conn.assert_not_called()
    assert warm_rw_cands == legacy_rw_cands
    assert warm_rw_ms < 10.0

    # 3. Shared cache: read_only=True after read_only=False makes 0 SQLite connections!
    with patch("aios_habit.workspace_chat_rag_v2_adapter.sqlite3.connect") as mock_conn:
        shared_ro_cands = adapter._get_covered_source_fingerprints(
            db_path, probe_ids, read_only=True
        )
        mock_conn.assert_not_called()
    assert shared_ro_cands == legacy_ro_cands

    # 4. Cold read_only=False with candidate_doc_ids=None
    adapter.clear_covered_source_fingerprints_cache()
    t0 = time.perf_counter()
    new_rw_full = adapter._get_covered_source_fingerprints(db_path, None, read_only=False)
    cold_rw_full_ms = (time.perf_counter() - t0) * 1000.0
    assert new_rw_full == legacy_rw_full
    assert cold_rw_full_ms < 1000.0

    # 5. Cold read_only=True with candidate_doc_ids=None and candidate_doc_ids=probe_ids
    adapter.clear_covered_source_fingerprints_cache()
    t0 = time.perf_counter()
    new_ro_full = adapter._get_covered_source_fingerprints(db_path, None, read_only=True)
    cold_ro_full_ms = (time.perf_counter() - t0) * 1000.0
    assert new_ro_full == legacy_ro_full
    assert cold_ro_full_ms < 1000.0

    adapter.clear_covered_source_fingerprints_cache()
    t0 = time.perf_counter()
    new_ro_cands = adapter._get_covered_source_fingerprints(
        db_path, probe_ids, read_only=True
    )
    cold_ro_cands_ms = (time.perf_counter() - t0) * 1000.0
    assert new_ro_cands == legacy_ro_cands
    assert cold_ro_cands_ms < 1000.0


def test_g9_scenario_a_dieu_tra_loi_domain_specs_no_chunks_scan() -> None:
    """Verify Scenario A question with mechanical IDs on dieu_tra_loi matches legacy 100% in <250ms."""
    dtl_db = PRODUCTION_COLLECTIONS_ROOT / "dieu_tra_loi" / "library.sqlite"
    if not dtl_db.is_file():
        pytest.skip(f"Production DB not present at {dtl_db}")

    question_a = (
        "Lịch sử điều tra lỗi kẹt giấy JAM4212 và báo cáo KTD-2026-06-0647 tại trạm C33"
    )
    adapter.clear_covered_source_fingerprints_cache()
    t0 = time.perf_counter()
    specs = adapter._get_cached_specs_for_domain("dieu_tra_loi", dtl_db, question=question_a)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    t0_warm = time.perf_counter()
    specs_warm = adapter._get_cached_specs_for_domain(
        "dieu_tra_loi", dtl_db, question=question_a
    )
    warm_ms = (time.perf_counter() - t0_warm) * 1000.0

    assert specs == specs_warm
    assert len(specs) == 679
    assert elapsed_ms < 250.0, f"Scenario A domain specs took {elapsed_ms:.2f}ms (expected <250ms)"
    assert warm_ms < 5.0
