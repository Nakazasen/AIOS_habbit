"""Unit tests for index status line (INDEX-STATUS-LINE-PC0575)."""

import hashlib
from pathlib import Path
import sqlite3
import pytest

from aios_habit.index_status import (
    WARNING_INDEX_UNAVAILABLE,
    compute_logical_fingerprint,
    format_thousands_vi,
    get_cached_index_status_line,
    get_index_status_info,
    resolve_display_backend_name,
)


def test_index_status_missing_file(tmp_path: Path) -> None:
    non_existent = tmp_path / "does_not_exist.sqlite"
    info = get_index_status_info(non_existent)
    assert info.is_error is True
    assert info.status_line == WARNING_INDEX_UNAVAILABLE
    assert info.doc_count == 0
    assert info.chunk_count == 0
    assert info.fingerprint_12 == ""


def test_index_status_none_path() -> None:
    info = get_index_status_info(None)
    assert info.is_error is True
    assert info.status_line == WARNING_INDEX_UNAVAILABLE


def test_index_status_empty_db(tmp_path: Path) -> None:
    empty_db = tmp_path / "empty.sqlite"
    con = sqlite3.connect(empty_db)
    con.close()

    info = get_index_status_info(empty_db)
    assert info.is_error is True
    assert info.status_line == WARNING_INDEX_UNAVAILABLE


def test_index_status_no_chunks(tmp_path: Path) -> None:
    db_file = tmp_path / "no_chunks.sqlite"
    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE chunks (chunk_id TEXT PRIMARY KEY, document_id TEXT)")
    con.commit()
    con.close()

    info = get_index_status_info(db_file)
    assert info.is_error is True
    assert info.status_line == WARNING_INDEX_UNAVAILABLE


def test_index_status_mock_db_counts_and_fingerprint(tmp_path: Path) -> None:
    db_file = tmp_path / "test_library.sqlite"
    con = sqlite3.connect(db_file)
    con.execute(
        """
        CREATE TABLE chunks (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            source_fingerprint TEXT,
            file_type TEXT NOT NULL
        )
        """
    )
    # Doc A: 2 content chunks
    con.execute("INSERT INTO chunks VALUES ('c1', 'doc_A', 'fp_alpha', 'txt')")
    con.execute("INSERT INTO chunks VALUES ('c2', 'doc_A', 'fp_alpha', 'txt')")
    # Doc B: 1 content chunk + 1 summary chunk
    con.execute("INSERT INTO chunks VALUES ('c3', 'doc_B', 'fp_beta', 'xlsx')")
    con.execute("INSERT INTO chunks VALUES ('c4', 'doc_B', NULL, 'document_summary')")
    # Doc C: 1 summary chunk only
    con.execute("INSERT INTO chunks VALUES ('c5', 'doc_C', NULL, 'document_summary')")
    con.commit()
    con.close()

    # Manual expected fingerprint calculation:
    # doc_A: fp='fp_alpha', n_content=2
    # doc_B: fp='fp_beta', n_content=1
    # doc_C: fp='', n_content=0
    expected_lines = [
        "doc_A|fp_alpha|2",
        "doc_B|fp_beta|1",
        "doc_C||0",
    ]
    expected_fp = hashlib.sha256("\n".join(expected_lines).encode("utf-8")).hexdigest()
    expected_12 = expected_fp[:12]

    info = get_index_status_info(db_file, backend_name="onnx")
    assert info.is_error is False
    assert info.doc_count == 3
    assert info.chunk_count == 5
    assert info.fingerprint_12 == expected_12
    assert info.backend == "ONNX fp32"
    assert info.db_name == "test_library.sqlite"
    assert info.status_line == (
        f"Kho đang dùng: test_library.sqlite · 3 tài liệu · 5 mảnh · mã {expected_12} · ONNX fp32"
    )


def test_index_status_thousand_formatting() -> None:
    assert format_thousands_vi(0) == "0"
    assert format_thousands_vi(889) == "889"
    assert format_thousands_vi(1000) == "1.000"
    assert format_thousands_vi(149800) == "149.800"
    assert format_thousands_vi(1234567) == "1.234.567"


def test_index_status_caching(tmp_path: Path) -> None:
    db_file = tmp_path / "cache_test.sqlite"
    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE chunks (chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, source_fingerprint TEXT, file_type TEXT NOT NULL)")
    con.execute("INSERT INTO chunks VALUES ('c1', 'd1', 'fp1', 'txt')")
    con.commit()
    con.close()

    session_state: dict = {}
    line1, err1 = get_cached_index_status_line(db_file, session_state=session_state)
    assert err1 is False
    assert "Kho đang dùng: cache_test.sqlite" in line1

    # Tamper with session state cache to verify it returns from cache
    session_state["wsc_index_status_cache"]["status_line"] = "Kho đang dùng: cached_version"
    line2, err2 = get_cached_index_status_line(db_file, session_state=session_state)
    assert line2 == "Kho đang dùng: cached_version"
    assert err2 is False


def test_resolve_display_backend_name() -> None:
    assert resolve_display_backend_name("onnx") == "ONNX fp32"
    assert resolve_display_backend_name("onnxruntime") == "ONNX fp32"
    assert resolve_display_backend_name("onnx_int8") == "ONNX int8"
    assert resolve_display_backend_name("pytorch") == "PyTorch"
    assert resolve_display_backend_name("flagembedding") == "PyTorch"
    assert resolve_display_backend_name(None) == "ONNX fp32"
    assert resolve_display_backend_name("ONNX fp32") == "ONNX fp32"


def test_index_status_matches_real_db_if_present() -> None:
    real_db = Path("local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite")
    if not real_db.is_file():
        pytest.skip("Chỉ mục thật không có sẵn trên môi trường kiểm thử này.")

    # Đọc trực tiếp từ DB độc lập
    con = sqlite3.connect(f"file:{real_db.resolve().as_posix()}?mode=ro", uri=True)
    try:
        direct_chunks = int(con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
        direct_docs = int(con.execute("SELECT COUNT(DISTINCT document_id) FROM chunks").fetchone()[0])
        direct_fp = compute_logical_fingerprint(con)
    finally:
        con.close()

    info = get_index_status_info(real_db)

    # Khẳng định số hiển thị khớp số đọc trực tiếp từ DB
    assert info.is_error is False
    assert info.chunk_count == direct_chunks == 149800
    assert info.doc_count == direct_docs == 889
    assert info.fingerprint_12 == direct_fp[:12] == "87a3626a85bc"
    assert info.db_name == "library.sqlite"
    assert info.status_line == (
        "Kho đang dùng: library.sqlite · 889 tài liệu · 149.800 mảnh · mã 87a3626a85bc · ONNX fp32"
    )
