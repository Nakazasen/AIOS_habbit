"""Tests for OPT-RAGV2-PYLOOPS.

Covers the three Python-loop optimizations in ``aios_habit.rag_v2.index``:

- V2-A: ``LocalChunkIndex.preload_dense_matrix_cache()`` warms the dense
  matrix cache at worker init instead of the first cold query.
- V1-A2: ``_cjk_like_prefilter_rows()`` narrows deterministic-scan candidate
  rows with SQL LIKE predicates; it must never change the ranked results.
- V3-A: the sparse inverted-index cache must return exactly the same ranked
  results as the legacy per-query Python scan.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import (
    NUMPY_DENSE_FLAG,
    LocalChunkIndex,
    SearchOptions,
)
from aios_habit.rag_v2.semantic import DeterministicEmbeddingBackend

pytestmark = pytest.mark.slow


def make_chunk(
    chunk_id: str,
    text: str,
    *,
    source_name: str = "source.txt",
    source_path: str = "source.txt",
    metadata: dict | None = None,
    labels: tuple[str, ...] = ("allowed",),
    fingerprint: str = "v1",
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        source_path=source_path,
        source_name=source_name,
        file_type="txt",
        text=text,
        normalized_text=text.casefold(),
        element_ids=(f"element-{chunk_id}",),
        element_types=("text",),
        section_path=("section", chunk_id),
        privacy_labels=labels,
        source_fingerprint=fingerprint,
        metadata=metadata or {},
    )


def index_with_chunks(tmp_path: Path, chunks: list[DocumentChunk], **kwargs) -> LocalChunkIndex:
    index = LocalChunkIndex(tmp_path / "index.sqlite", **kwargs)
    index.upsert_chunks(chunks)
    return index


# ---------------------------------------------------------------------------
# V2-A: dense preload
# ---------------------------------------------------------------------------


def _deterministic_index(tmp_path: Path, count: int = 8) -> LocalChunkIndex:
    chunks = [
        make_chunk(f"chunk-{i:03d}", f"sample document text number {i} beam diameter")
        for i in range(count)
    ]
    backend = DeterministicEmbeddingBackend(dimension=16)
    return index_with_chunks(tmp_path, chunks, embedding_backend=backend)


def test_dense_preload_warms_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    np = pytest.importorskip("numpy")
    assert np is not None
    monkeypatch.setenv(NUMPY_DENSE_FLAG, "1")
    with _deterministic_index(tmp_path) as index:
        assert index._dense_matrix_cache is None
        chunk_count, elapsed_ms = index.preload_dense_matrix_cache()
        assert chunk_count == 8
        assert elapsed_ms >= 0.0
        assert index._dense_matrix_cache is not None
        # A second preload must reuse the cached matrix instead of reloading.
        before = index._dense_matrix_cache
        index.preload_dense_matrix_cache()
        assert index._dense_matrix_cache is before


def test_dense_preload_disabled_without_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # TEST-STALE-GUARDS-HOME: RETRIEVAL-DENSE-NUMPY-PC0575 (commit 1b33f88, verdict
    # DAT 11:55 08/10) da doi numpy-dense thanh MAC DINH BAT khi co numpy — xoa bien
    # moi truong khong con tat duoc. Tat dung phai dat co = "0" (duong rollback 1 dong).
    # Test khang dinh HANH VI hien tai: co=0 -> khong nap; mac dinh (co numpy) -> co nap.
    monkeypatch.setenv(NUMPY_DENSE_FLAG, "0")
    with _deterministic_index(tmp_path) as index:
        assert index.preload_dense_matrix_cache() == (0, 0.0)
        assert index._dense_matrix_cache is None


def test_dense_results_identical_with_and_without_preload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("numpy")
    monkeypatch.setenv(NUMPY_DENSE_FLAG, "1")
    with _deterministic_index(tmp_path) as index:
        index.preload_dense_matrix_cache()
        warm = index.dense_candidates("beam diameter", limit=5)
    with _deterministic_index(tmp_path / "cold") as index:
        cold = index.dense_candidates("beam diameter", limit=5)
    assert [(r.chunk_id, r.score) for r in warm] == [(r.chunk_id, r.score) for r in cold]


def test_dense_preload_skips_when_backend_missing(tmp_path: Path) -> None:
    chunks = [make_chunk("chunk-001", "plain text without any embedding backend")]
    with index_with_chunks(tmp_path, chunks) as index:
        assert index.preload_dense_matrix_cache() == (0, 0.0)


# ---------------------------------------------------------------------------
# V1-A2: CJK LIKE prefilter must not change results
# ---------------------------------------------------------------------------


def _cjk_chunks() -> list[DocumentChunk]:
    return [
        # Matches the longest CJK term.
        make_chunk(
            "beam-ng",
            "Beam径がNGの場合はIrisを清掃してから再測定してください",
            source_name="LSU manual.txt",
        ),
        # Matches the second-longest term (Vietnamese).
        make_chunk(
            "nguyen-nhan",
            "Nguyên nhân gây ra lỗi beam là do thấu kính bị bẩn",
            source_name="notes.txt",
        ),
        # Matches both longest terms.
        make_chunk(
            "both",
            "Beam径の異常の nguyên nhân は光軸のずれです",
            source_name="LSU manual.txt",
        ),
        # Matches only via metadata (source_name) on the longest term --
        # the 4-column LIKE keeps it, unlike a normalized_text-only filter.
        make_chunk(
            "metadata-only",
            "このチャンクは本文に一致する語を含みません",
            source_name="Beam径 troubleshooting guide.txt",
        ),
        # Matches nothing; both paths must drop it.
        make_chunk(
            "unrelated",
            "今日は良い天気です",
            source_name="weather.txt",
        ),
    ]


def _search_signature(index: LocalChunkIndex, query: str):
    response = index.search_with_summary(query, limit=10)
    return (
        [(r.chunk_id, r.score) for r in response.results],
        response.summary.candidate_backend,
        response.summary.query,
    )


def test_cjk_prefilter_matches_full_scan_on_long_term_queries(tmp_path: Path) -> None:
    # Ticket acceptance bar: identical ranking when every genuine match
    # contains a longest term.
    query = "Lỗi Beam径 NG trên Iris LSU là gì, nguyên nhân và hướng xử lý?"
    with index_with_chunks(tmp_path / "prefilter", _cjk_chunks()) as index:
        prefiltered = _search_signature(index, query)
    with index_with_chunks(tmp_path / "fullscan", _cjk_chunks()) as index:
        index._cjk_like_prefilter_rows = lambda rows, terms: None  # type: ignore[method-assign]
        full_scan = _search_signature(index, query)
    assert prefiltered == full_scan
    chunk_ids = [chunk_id for chunk_id, _ in prefiltered[0]]
    assert "beam-ng" in chunk_ids
    assert "nguyen-nhan" in chunk_ids
    assert "both" in chunk_ids
    assert "metadata-only" in chunk_ids
    assert "unrelated" not in chunk_ids


def test_cjk_prefilter_drops_short_term_only_matches(tmp_path: Path) -> None:
    # TEST-STALE-GUARDS-HOME: CJK-PREFILTER-FIX-HOME (commit 195b970) da gop thuc the
    # voi thuat ngu roi lay 2 cum dai nhat — voi cau hoi cua ve, 2 cum la `nguyen` va
    # `beam径`: prefilter giu dung 4 manh that, loai `short-only` (chi co Iris LSU).
    # Tang diem sau do cung loai `short-only` (chi khop `loi`/`iris`/`lsu`, khong vuot
    # nguong xep hang duong that) — bao cao CJK-PREFILTER-FIX-HOME muc 4 xac nhan ket
    # qua cuoi: beam-ng, both, nguyen-nhan, metadata-only. Test khang dinh HANH VI
    # hien tai o ca 2 tang: prefilter loai + full-scan cung loai.
    chunks = _cjk_chunks() + [
        make_chunk(
            "short-only",
            "Iris LSU の lỗi について説明します",
            source_name="short.txt",
        ),
    ]
    query = "Lỗi Beam径 NG trên Iris LSU là gì, nguyên nhân và hướng xử lý?"
    with index_with_chunks(tmp_path / "prefilter", chunks) as index:
        prefiltered_ids = [chunk_id for chunk_id, _ in _search_signature(index, query)[0]]
    with index_with_chunks(tmp_path / "fullscan", chunks) as index:
        index._cjk_like_prefilter_rows = lambda rows, terms: None  # type: ignore[method-assign]
        full_scan_ids = [chunk_id for chunk_id, _ in _search_signature(index, query)[0]]
    # Ca 2 tang deu loai short-only: prefilter (khong chua cum dai) + tang diem.
    assert "short-only" not in prefiltered_ids
    assert "short-only" not in full_scan_ids
    # Prefilter van la tap con cua full-scan (khong giu thua manh nao).
    assert set(prefiltered_ids) <= set(full_scan_ids)
    assert set(prefiltered_ids) == {"beam-ng", "both", "nguyen-nhan", "metadata-only"}


def test_cjk_prefilter_uses_two_longest_terms_deterministically(tmp_path: Path) -> None:
    chunks = [
        make_chunk("t1", "a bb ccc dddd", source_name="s.txt"),
        make_chunk("t2", "a bb", source_name="s.txt"),
    ]
    with index_with_chunks(tmp_path, chunks) as index:
        rows = list(
            index._conn.execute(
                "SELECT chunk_id, normalized_text, source_name, source_path, metadata_json"
                " FROM chunks"
            ).fetchall()
        )
        first = index._cjk_like_prefilter_rows(rows, ("dddd", "ccc", "bb", "a"))
        second = index._cjk_like_prefilter_rows(rows, ("a", "bb", "ccc", "dddd"))
        assert first is not None and second is not None
        assert [r["chunk_id"] for r in first] == [r["chunk_id"] for r in second]
        # The two longest terms are "dddd" and "ccc": only t1 contains "dddd".
        assert [r["chunk_id"] for r in first] == ["t1"]


def test_cjk_prefilter_escapes_like_wildcards(tmp_path: Path) -> None:
    chunks = [
        make_chunk("literal", "a_b を含むチャンク 径", source_name="s.txt"),
        make_chunk("wildcard", "axb を含むチャンク 径", source_name="s.txt"),
    ]
    with index_with_chunks(tmp_path, chunks) as index:
        rows = list(
            index._conn.execute(
                "SELECT chunk_id, normalized_text, source_name, source_path, metadata_json"
                " FROM chunks"
            ).fetchall()
        )
        kept = index._cjk_like_prefilter_rows(rows, ("a_b",))
        assert kept is not None
        kept_ids = {row["chunk_id"] for row in kept}
        # Without escaping, "%a_b%" would also match "axb".
        assert kept_ids == {"literal"}


def test_cjk_prefilter_falls_back_on_sql_error(tmp_path: Path) -> None:
    with index_with_chunks(tmp_path, _cjk_chunks()) as index:
        broken = index._conn
        broken.close()  # any SQL use now fails
        assert index._cjk_like_prefilter_rows([], ("径",)) is None


def test_cjk_prefilter_flag_off_falls_back_to_full_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AIOS_RAG_V2_CJK_PREFILTER", "0")
    with index_with_chunks(tmp_path, _cjk_chunks()) as index:
        rows = list(
            index._conn.execute(
                "SELECT chunk_id, normalized_text, source_name, source_path, metadata_json"
                " FROM chunks"
            ).fetchall()
        )
        assert index._cjk_like_prefilter_rows(rows, ("beam径", "nguyên")) is None
        response = index.search_with_summary(
            "Lỗi Beam径 NG trên Iris LSU là gì, nguyên nhân và hướng xử lý?",
            limit=10,
        )
        assert response.summary.candidate_backend == "deterministic_scan"
        assert [r.chunk_id for r in response.results]


def test_non_cjk_query_still_uses_fts_path(tmp_path: Path) -> None:
    with index_with_chunks(tmp_path, _cjk_chunks()) as index:
        response = index.search_with_summary("beam diameter error", limit=10)
        assert response.summary.candidate_backend == "fts5_bm25"


# ---------------------------------------------------------------------------
# V3-A: sparse inverted-index cache equivalence
# ---------------------------------------------------------------------------


def _sparse_index(tmp_path: Path, chunks: list[DocumentChunk]) -> LocalChunkIndex:
    backend = DeterministicEmbeddingBackend(dimension=16)
    return index_with_chunks(tmp_path, chunks, embedding_backend=backend)


def _sparse_chunks() -> list[DocumentChunk]:
    base = [
        ("beam-ng", "Beam径 NG エラー Iris LSU 対処方法 清掃"),
        ("beam-diameter", "beam diameter measurement procedure laser scanning unit"),
        ("sim-block", "SIM を LD BLOCK ASSY に貼り付ける手順 beam エラー"),
        ("tie-a", "beam diameter ng error troubleshooting"),
        ("tie-b", "beam diameter ng error troubleshooting"),  # exact tie with tie-a
        ("unrelated", "今日は良い天気です 散歩 日記"),
    ]
    return [make_chunk(chunk_id, text) for chunk_id, text in base]


def _sparse_signature(index: LocalChunkIndex, query: str):
    results = index.sparse_candidates(query, limit=10)
    return [
        (
            r.chunk_id,
            r.score,
            r.ranking_signals["sparse_dot"],
            r.ranking_signals["sparse_multi_variant_rrf"],
            r.matched_query_variants,
        )
        for r in results
    ]


def test_sparse_cache_matches_legacy_scan(tmp_path: Path) -> None:
    chunks = _sparse_chunks()
    with _sparse_index(tmp_path / "cached", chunks) as index:
        cache = index._sparse_vector_cache_for(
            index._embedding_backend.descriptor.fingerprint
        )
        assert cache is not None
        assert len(cache.chunk_ids) == len(chunks)
        cached_results = _sparse_signature(index, "Beam径 NG エラー")
    with _sparse_index(tmp_path / "legacy", chunks) as index:
        index._sparse_vector_cache_for = lambda fingerprint: None  # type: ignore[method-assign]
        legacy_results = _sparse_signature(index, "Beam径 NG エラー")
    assert cached_results == legacy_results
    # The exact-tie pair must keep a deterministic, identical order.
    tied = [chunk_id for chunk_id, *_ in cached_results if chunk_id in ("tie-a", "tie-b")]
    assert tied == [chunk_id for chunk_id, *_ in legacy_results if chunk_id in ("tie-a", "tie-b")]


def test_sparse_cache_respects_privacy_and_staleness(tmp_path: Path) -> None:
    secret = make_chunk("secret", "beam diameter ng error", labels=("secret",))
    stale = make_chunk("stale", "beam diameter ng error", fingerprint="old")
    chunks = _sparse_chunks() + [secret, stale]
    with _sparse_index(tmp_path, chunks) as index:
        options = SearchOptions(
            allowed_privacy_labels=("allowed",),
            expected_source_fingerprints={"doc-stale": "v1"},
        )
        results = index.sparse_candidates(
            "beam diameter ng error", limit=20, options=options
        )
        chunk_ids = [r.chunk_id for r in results]
        assert "secret" not in chunk_ids
        assert "stale" not in chunk_ids
        # Both filters apply identically on the legacy path.
        index._sparse_vector_cache_for = lambda fingerprint: None  # type: ignore[method-assign]
        legacy_ids = [
            r.chunk_id
            for r in index.sparse_candidates(
                "beam diameter ng error", limit=20, options=options
            )
        ]
        assert chunk_ids == legacy_ids


def test_sparse_cache_budget_falls_back_to_legacy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    chunks = _sparse_chunks()
    monkeypatch.setenv("AIOS_RAG_V2_SPARSE_MAX_BYTES", "1")
    with _sparse_index(tmp_path, chunks) as index:
        chunk_count, _elapsed_ms = index.preload_sparse_vector_cache()
        assert chunk_count == 0
        assert index._sparse_vector_cache is None
        results = index.sparse_candidates("beam diameter", limit=5)
        assert [r.chunk_id for r in results]


def test_sparse_preload_warms_cache(tmp_path: Path) -> None:
    with _sparse_index(tmp_path, _sparse_chunks()) as index:
        assert index._sparse_vector_cache is None
        chunk_count, elapsed_ms = index.preload_sparse_vector_cache()
        assert chunk_count == len(_sparse_chunks())
        assert elapsed_ms >= 0.0
        assert index._sparse_vector_cache is not None
        before = index._sparse_vector_cache
        index.preload_sparse_vector_cache()
        assert index._sparse_vector_cache is before


def test_sparse_preload_skips_when_backend_missing(tmp_path: Path) -> None:
    chunks = [make_chunk("chunk-001", "plain text without any embedding backend")]
    with index_with_chunks(tmp_path, chunks) as index:
        assert index.preload_sparse_vector_cache() == (0, 0.0)


def test_sparse_cache_invalidated_by_write(tmp_path: Path) -> None:
    chunks = _sparse_chunks()
    with _sparse_index(tmp_path, chunks) as index:
        index.preload_sparse_vector_cache()
        first = index._sparse_vector_cache
        assert first is not None
        index.upsert_chunks([make_chunk("extra", "brand new chunk about beam")])
        index.ensure_embeddings()
        second = index._sparse_vector_cache_for(
            index._embedding_backend.descriptor.fingerprint
        )
        assert second is not None
        assert second is not first
        assert len(second.chunk_ids) == len(chunks) + 1


def test_sparse_serialized_vectors_survive_json_roundtrip(tmp_path: Path) -> None:
    # Guards the array("I")/array("d") postings against JSON-unfriendly types.
    with _sparse_index(tmp_path, _sparse_chunks()) as index:
        cache = index._sparse_vector_cache_for(
            index._embedding_backend.descriptor.fingerprint
        )
        assert cache is not None
        for term, (positions, weights) in cache.postings.items():
            assert isinstance(term, str)
            assert all(isinstance(p, int) for p in positions)
            assert all(isinstance(w, float) for w in weights)
        json.dumps({term: [list(p), list(w)] for term, (p, w) in cache.postings.items()})
