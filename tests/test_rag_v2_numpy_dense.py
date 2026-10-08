import pytest

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import (
    NUMPY_DENSE_FLAG,
    NUMPY_DENSE_MAX_BYTES_FLAG,
    LocalChunkIndex,
    SearchOptions,
    clear_process_dense_matrix_cache,
    numpy_dense_search_enabled,
)
from aios_habit.rag_v2.query_planning import RetrievalQueryPlan, RetrievalQueryVariant
from aios_habit.rag_v2.semantic import DeterministicEmbeddingBackend


def make_chunk(
    chunk_id: str,
    document_id: str,
    text: str,
    *,
    labels=("allowed",),
    fingerprint="v1",
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        source_path=f"/workspace/{document_id}.txt",
        source_name=f"{document_id}.txt",
        file_type="txt",
        text=text,
        normalized_text=text.casefold(),
        element_ids=(f"element-{chunk_id}",),
        element_types=("text",),
        section_path=("section", chunk_id),
        privacy_labels=labels,
        source_fingerprint=fingerprint,
        checksum=f"checksum-{chunk_id}-{fingerprint}",
    )


def sample_plan() -> RetrievalQueryPlan:
    return RetrievalQueryPlan(
        original_query="semantic target alpha",
        variants=(
            RetrievalQueryVariant(
                text="semantic target alpha",
                origin="original",
                variant_id="query_original",
                facet_id="query",
            ),
            RetrievalQueryVariant(
                text="semantic target beta detail",
                origin="facet",
                variant_id="facet_1",
                facet_id="facet_1",
            ),
            RetrievalQueryVariant(
                text="semantic target gamma",
                origin="expansion",
                variant_id="exp_1",
                facet_id="query",
            ),
        ),
        content_terms=("semantic", "target"),
        expansion_status="expanded",
        intent_category="general",
    )


def sample_chunks() -> list[DocumentChunk]:
    chunks = []
    for index in range(60):
        chunks.append(
            make_chunk(
                f"c{index:03d}",
                f"doc-{index % 7}",
                f"semantic target token{index} shared evidence",
            )
        )
    chunks.append(make_chunk("tie-a", "doc-a", "identical dense text"))
    chunks.append(make_chunk("tie-b", "doc-b", "identical dense text"))
    chunks.append(make_chunk("secret", "doc-secret", "semantic target secret", labels=("secret",)))
    chunks.append(
        make_chunk(
            "stale",
            "doc-stale",
            "semantic target stale",
            fingerprint="old",
        )
    )
    return chunks


def _search(index: LocalChunkIndex):
    options = SearchOptions(
        allowed_privacy_labels=("allowed",),
        expected_source_fingerprints={"doc-stale": "v1"},
        candidate_limit=8,
    )
    return index.dense_candidates(sample_plan(), limit=5, options=options)


def test_numpy_dense_flag_defaults_on_when_numpy_available(monkeypatch):
    pytest.importorskip("numpy")
    monkeypatch.delenv(NUMPY_DENSE_FLAG, raising=False)
    assert numpy_dense_search_enabled() is True


def test_numpy_dense_flag_explicit_off(monkeypatch):
    for val in ("0", "false", "no", "off", "  FALSE  "):
        monkeypatch.setenv(NUMPY_DENSE_FLAG, val)
        assert numpy_dense_search_enabled() is False


def test_numpy_dense_missing_numpy_fallback(monkeypatch, caplog):
    monkeypatch.delenv(NUMPY_DENSE_FLAG, raising=False)
    monkeypatch.setattr("aios_habit.rag_v2.index._is_numpy_available", lambda: False)
    with caplog.at_level("WARNING"):
        assert numpy_dense_search_enabled() is False
    assert "numpy không khả dụng" in caplog.text


def test_numpy_dense_topk_matches_python_path(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    clear_process_dense_matrix_cache()
    backend = DeterministicEmbeddingBackend(dimension=32)
    with LocalChunkIndex(tmp_path / "dense.sqlite", embedding_backend=backend) as index:
        index.upsert_chunks(sample_chunks())

        # Đường Python cũ khi tắt cờ
        monkeypatch.setenv(NUMPY_DENSE_FLAG, "0")
        python_results = _search(index)

        # Đường Numpy mặc định khi bật cờ
        monkeypatch.delenv(NUMPY_DENSE_FLAG, raising=False)
        numpy_results = _search(index)
        assert index._dense_matrix_cache is not None

    assert python_results
    assert [item.chunk_id for item in numpy_results] == [item.chunk_id for item in python_results]
    assert numpy_results == python_results
    assert "secret" not in {item.chunk_id for item in numpy_results}
    assert "stale" not in {item.chunk_id for item in numpy_results}


def test_numpy_dense_over_budget_keeps_python_results(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    clear_process_dense_matrix_cache()
    monkeypatch.delenv(NUMPY_DENSE_FLAG, raising=False)
    monkeypatch.setenv(NUMPY_DENSE_MAX_BYTES_FLAG, "0")
    backend = DeterministicEmbeddingBackend(dimension=16)
    with LocalChunkIndex(tmp_path / "budget.sqlite", embedding_backend=backend) as index:
        index.upsert_chunks(sample_chunks()[:12])
        numpy_attempt = _search(index)
        assert index._dense_matrix_cache is None
        monkeypatch.setenv(NUMPY_DENSE_FLAG, "0")
        python_results = _search(index)
    assert numpy_attempt == python_results


def test_numpy_dense_cache_sees_new_chunks(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    clear_process_dense_matrix_cache()
    monkeypatch.delenv(NUMPY_DENSE_FLAG, raising=False)
    backend = DeterministicEmbeddingBackend(dimension=16)
    with LocalChunkIndex(tmp_path / "refresh.sqlite", embedding_backend=backend) as index:
        index.upsert_chunks([make_chunk("old", "doc-old", "semantic target old")])
        first = index.dense_candidates("semantic target", limit=5)
        index.upsert_chunks([make_chunk("new", "doc-new", "semantic target new unique")])
        second = index.dense_candidates("semantic target", limit=5)
        assert index._dense_matrix_cache is not None
        assert set(index._dense_matrix_cache.chunk_ids) == {"old", "new"}
    assert {item.chunk_id for item in first} == {"old"}
    assert {item.chunk_id for item in second} == {"old", "new"}


def test_numpy_dense_process_level_cache(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    clear_process_dense_matrix_cache()
    monkeypatch.delenv(NUMPY_DENSE_FLAG, raising=False)
    backend = DeterministicEmbeddingBackend(dimension=16)
    db_path = tmp_path / "shared_proc.sqlite"

    with LocalChunkIndex(db_path, embedding_backend=backend) as index1:
        index1.upsert_chunks(sample_chunks()[:10])
        res1 = index1.dense_candidates("semantic target", limit=5)
        assert index1._dense_matrix_cache is not None

    # Instance thứ hai mở cùng DB: lấy từ cache cấp tiến trình
    with LocalChunkIndex(db_path, embedding_backend=backend, read_only=True) as index2:
        assert index2._dense_matrix_cache is None
        res2 = index2.dense_candidates("semantic target", limit=5)
        # _dense_matrix_cache được gán từ process cache
        assert index2._dense_matrix_cache is not None
        assert [x.chunk_id for x in res2] == [x.chunk_id for x in res1]

    clear_process_dense_matrix_cache()


def test_numpy_dense_exception_fallback_to_python(tmp_path, monkeypatch, caplog):
    pytest.importorskip("numpy")
    clear_process_dense_matrix_cache()
    monkeypatch.delenv(NUMPY_DENSE_FLAG, raising=False)
    backend = DeterministicEmbeddingBackend(dimension=16)
    with LocalChunkIndex(tmp_path / "fallback.sqlite", embedding_backend=backend) as index:
        index.upsert_chunks(sample_chunks()[:10])

        def _raise_error(*args, **kwargs):
            raise RuntimeError("mô phỏng lỗi tính toán numpy")

        monkeypatch.setattr(index, "_dense_candidates_numpy", _raise_error)
        with caplog.at_level("WARNING"):
            results = index.dense_candidates("semantic target", limit=5)
        assert results  # vẫn trả về kết quả nhờ fallback về Python
        assert "Đường quét dense numpy gặp lỗi" in caplog.text
