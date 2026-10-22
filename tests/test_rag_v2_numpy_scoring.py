import math
import os
import sqlite3
from pathlib import Path
import pytest

from aios_habit.rag_v2.semantic import (
    NUMPY_SCORING_FLAG,
    SemanticBackendError,
    _cosine_similarity_numpy,
    _cosine_similarity_python,
    _sparse_dot_similarity_numpy,
    _sparse_dot_similarity_python,
    batch_cosine_similarity,
    batch_sparse_dot_similarity,
    cosine_similarity,
    normalize_sparse_vector,
    normalize_vector,
    numpy_scoring_enabled,
    sparse_dot_similarity,
)


def test_numpy_scoring_flag_defaults_on_when_numpy_available(monkeypatch):
    pytest.importorskip("numpy")
    monkeypatch.delenv(NUMPY_SCORING_FLAG, raising=False)
    assert numpy_scoring_enabled() is True


def test_numpy_scoring_flag_explicit_off(monkeypatch):
    for val in ("0", "false", "no", "off", "  FALSE  ", "Off"):
        monkeypatch.setenv(NUMPY_SCORING_FLAG, val)
        assert numpy_scoring_enabled() is False


def test_numpy_scoring_missing_numpy_fallback(monkeypatch):
    monkeypatch.delenv(NUMPY_SCORING_FLAG, raising=False)
    monkeypatch.setattr("aios_habit.rag_v2.semantic._is_numpy_available", lambda: False)
    assert numpy_scoring_enabled() is False


def test_cosine_similarity_dimension_mismatch():
    with pytest.raises(SemanticBackendError, match="cosine vectors must have equal positive dimensions"):
        cosine_similarity((1.0, 2.0), (1.0,))

    with pytest.raises(SemanticBackendError, match="cosine vectors must have equal positive dimensions"):
        cosine_similarity((), ())


def test_cosine_similarity_synthetic_equivalence(monkeypatch):
    pytest.importorskip("numpy")
    import random

    random.seed(42)

    # Test trên các chiều vector khác nhau: 16, 128, 1024
    for dim in (16, 128, 1024):
        query = normalize_vector(tuple(random.uniform(-1.0, 1.0) for _ in range(dim)))
        candidates = [
            normalize_vector(tuple(random.uniform(-1.0, 1.0) for _ in range(dim)))
            for _ in range(50)
        ]

        # Python pure path
        monkeypatch.setenv(NUMPY_SCORING_FLAG, "0")
        assert numpy_scoring_enabled() is False
        py_scores = [cosine_similarity(query, cand) for cand in candidates]

        # Numpy path
        monkeypatch.delenv(NUMPY_SCORING_FLAG, raising=False)
        assert numpy_scoring_enabled() is True
        np_scores = [cosine_similarity(query, cand) for cand in candidates]

        # Sai lệch số học tuyệt đối phải nằm trong ngưỡng float32 tiền lệ (<= 1e-6)
        max_diff = max(abs(p - n) for p, n in zip(py_scores, np_scores))
        assert max_diff <= 1e-6, f"Max diff {max_diff} exceeded 1e-6 threshold for dim {dim}"

        # Thứ hạng top-k giữa hai đường phải giống hệt nhau
        py_ranked = sorted(range(len(py_scores)), key=lambda i: -py_scores[i])
        np_ranked = sorted(range(len(np_scores)), key=lambda i: -np_scores[i])
        assert py_ranked[:10] == np_ranked[:10], f"Top-10 ranking mismatch for dim {dim}"


def test_sparse_dot_similarity_synthetic_equivalence(monkeypatch):
    pytest.importorskip("numpy")
    import random

    random.seed(42)

    # Tập từ vựng tổng hợp
    vocab = [f"token_{i}" for i in range(200)]

    query_sparse = {
        token: round(random.uniform(0.1, 5.0), 3)
        for token in random.sample(vocab, 25)
    }

    candidates_sparse = []
    for _ in range(60):
        cand = {
            token: round(random.uniform(0.1, 5.0), 3)
            for token in random.sample(vocab, random.randint(10, 40))
        }
        candidates_sparse.append(cand)

    # Python pure path
    monkeypatch.setenv(NUMPY_SCORING_FLAG, "0")
    assert numpy_scoring_enabled() is False
    py_scores = [sparse_dot_similarity(query_sparse, cand) for cand in candidates_sparse]

    # Numpy path
    monkeypatch.delenv(NUMPY_SCORING_FLAG, raising=False)
    assert numpy_scoring_enabled() is True
    np_scores = [sparse_dot_similarity(query_sparse, cand) for cand in candidates_sparse]

    # Điểm từng mảnh khớp trong dung sai float32
    max_diff = max(abs(p - n) for p, n in zip(py_scores, np_scores))
    assert max_diff <= 1e-4, f"Max diff {max_diff} exceeded threshold"

    # Thứ hạng top-k giống hệt
    py_ranked = sorted(range(len(py_scores)), key=lambda i: (-py_scores[i], i))
    np_ranked = sorted(range(len(np_scores)), key=lambda i: (-np_scores[i], i))
    assert py_ranked[:10] == np_ranked[:10], "Top-10 ranking mismatch for sparse dot"


def test_batch_cosine_and_sparse_similarity():
    pytest.importorskip("numpy")
    v1 = (1.0, 0.0, 0.0)
    cands = [
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.7071, 0.7071, 0.0),
    ]
    batch_scores = batch_cosine_similarity(v1, cands)
    assert len(batch_scores) == 3
    assert abs(batch_scores[0] - 1.0) < 1e-5
    assert abs(batch_scores[1] - 0.0) < 1e-5
    assert abs(batch_scores[2] - 0.7071) < 1e-4

    s1 = {"a": 1.0, "b": 2.0}
    scands = [
        {"a": 1.0, "c": 3.0},
        {"b": 2.0},
        {"d": 5.0},
    ]
    batch_sparse = batch_sparse_dot_similarity(s1, scands)
    assert len(batch_sparse) == 3
    assert abs(batch_sparse[0] - 1.0) < 1e-5
    assert abs(batch_sparse[1] - 4.0) < 1e-5
    assert abs(batch_sparse[2] - 0.0) < 1e-5


def test_real_index_sample_equivalence(monkeypatch):
    """Trích mẫu chỉ mục thật (chỉ đọc) để kiểm tra tương đương giữa đường Python và Numpy."""
    pytest.importorskip("numpy")
    import json
    import struct

    db_path = Path(r"D:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\lsu\library.sqlite")
    if not db_path.is_file():
        pytest.skip("Chỉ mục LSU production không khả dụng trên máy này")

    uri = f"file:///{db_path.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.execute("PRAGMA query_only=ON")
        dense_rows = conn.execute(
            "SELECT chunk_id, vector_blob, dimension FROM chunk_embeddings LIMIT 20"
        ).fetchall()
        sparse_rows = conn.execute(
            "SELECT chunk_id, sparse_json FROM chunk_sparse_embeddings LIMIT 20"
        ).fetchall()

    assert len(dense_rows) >= 10
    assert len(sparse_rows) >= 10

    # Unpack dense vectors
    dense_vectors = []
    for row in dense_rows:
        dim = int(row[2])
        blob = bytes(row[1])
        vec = struct.unpack(f"{dim}f", blob)
        dense_vectors.append(vec)

    query_dense = dense_vectors[0]
    cand_dense = dense_vectors[1:]

    # So sánh Python vs Numpy trên dense thật
    monkeypatch.setenv(NUMPY_SCORING_FLAG, "0")
    py_dense_scores = [cosine_similarity(query_dense, c) for c in cand_dense]

    monkeypatch.delenv(NUMPY_SCORING_FLAG, raising=False)
    np_dense_scores = [cosine_similarity(query_dense, c) for c in cand_dense]

    max_diff_dense = max(abs(p - n) for p, n in zip(py_dense_scores, np_dense_scores))
    assert max_diff_dense <= 1e-6, f"Real dense max diff {max_diff_dense} exceeded 1e-6"

    # Top-k dense thật
    py_top = sorted(range(len(py_dense_scores)), key=lambda i: -py_dense_scores[i])
    np_top = sorted(range(len(np_dense_scores)), key=lambda i: -np_dense_scores[i])
    assert py_top[:5] == np_top[:5], "Real dense top-5 ranking mismatch"

    # Sparse thật
    sparse_vectors = [json.loads(row[1]) for row in sparse_rows]
    query_sparse = sparse_vectors[0]
    cand_sparse = sparse_vectors[1:]

    monkeypatch.setenv(NUMPY_SCORING_FLAG, "0")
    py_sparse_scores = [sparse_dot_similarity(query_sparse, c) for c in cand_sparse]

    monkeypatch.delenv(NUMPY_SCORING_FLAG, raising=False)
    np_sparse_scores = [sparse_dot_similarity(query_sparse, c) for c in cand_sparse]

    max_diff_sparse = max(abs(p - n) for p, n in zip(py_sparse_scores, np_sparse_scores))
    assert max_diff_sparse <= 1e-4, f"Real sparse max diff {max_diff_sparse} exceeded threshold"

    py_top_sparse = sorted(range(len(py_sparse_scores)), key=lambda i: (-py_sparse_scores[i], i))
    np_top_sparse = sorted(range(len(np_sparse_scores)), key=lambda i: (-np_sparse_scores[i], i))
    assert py_top_sparse[:5] == np_top_sparse[:5], "Real sparse top-5 ranking mismatch"
