"""Unit tests for index status line (INDEX-STATUS-LINE-PC0575)."""

import hashlib
import json
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


def _resolve_production_db_path() -> Path | None:
    """Return the real production index DB from config, or None if unknown.

    Reads ``runtime.root`` + ``requested_profile`` from
    ``config/workspace_chat_rag_v2.local.json`` and builds
    ``<root>/<profile>/collections/tri_thuc/library.sqlite`` — the file the
    app really queries (INDEX-PROD-HOME). Returns None when the config or
    the file is missing so the caller can skip cleanly.
    """
    config_path = Path("config/workspace_chat_rag_v2.local.json")
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    runtime = raw.get("runtime") or {}
    root_raw = str(runtime.get("root") or "").strip()
    profile = str(raw.get("requested_profile") or "bge_m3_hybrid").strip()
    if not root_raw or not profile:
        return None
    candidate = Path(root_raw) / profile / "collections" / "tri_thuc" / "library.sqlite"
    try:
        if candidate.is_file():
            return candidate
    except OSError:
        return None
    return None


def test_index_status_matches_real_db_if_present() -> None:
    # Hướng (a) của vé INDEX-LOCALCOPY-FIX-HOME: đọc đúng tệp production theo
    # config thay vì bản sao cũ trong local_runs (bản ghim 28/09 chỉ có
    # 133.144 mảnh / 496 tài liệu nên khẳng định số production trên nó gây đỏ
    # oan). Bỏ qua sạch khi tệp production không tồn tại (CI/VM).
    real_db = _resolve_production_db_path()
    if real_db is None or not real_db.is_file():
        pytest.skip("Chỉ mục production thật không có sẵn trên môi trường kiểm thử này.")

    # Đọc trực tiếp từ DB độc lập
    con = sqlite3.connect(f"file:{real_db.resolve().as_posix()}?mode=ro", uri=True)
    try:
        direct_chunks = int(con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
        direct_docs = int(con.execute("SELECT COUNT(DISTINCT document_id) FROM chunks").fetchone()[0])
        direct_fp = compute_logical_fingerprint(con)
    finally:
        con.close()

    info = get_index_status_info(real_db)

    # Relational assertions: displayed numbers match direct DB reads.
    assert info.is_error is False
    assert direct_chunks > 0
    assert direct_docs > 0
    assert info.chunk_count == direct_chunks
    assert info.doc_count == direct_docs
    # Relational fingerprint: both read paths agree, display length holds.
    assert len(direct_fp) == 64
    assert len(info.fingerprint_12) == 12
    assert info.fingerprint_12 == direct_fp[:12]
    assert info.db_name == "library.sqlite"
    assert info.status_line == (
        f"Kho đang dùng: library.sqlite · {format_thousands_vi(direct_docs)} tài liệu "
        f"· {format_thousands_vi(direct_chunks)} mảnh · mã {direct_fp[:12]} · {info.backend}"
    )


def test_persistent_index_status_cache_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra vòng đời Persistent Disk Cache: ghi xuống đĩa và nạp lại khi in-memory cache rỗng."""
    from aios_habit.index_status import _INDEX_STATUS_MEMORY_CACHE, _get_persistent_cache_path

    db_file = tmp_path / "test_persist.sqlite"
    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE chunks (chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, source_fingerprint TEXT, file_type TEXT NOT NULL)")
    con.execute("INSERT INTO chunks VALUES ('c1', 'doc_1', 'fp1', 'txt')")
    con.execute("INSERT INTO chunks VALUES ('c2', 'doc_1', 'fp1', 'txt')")
    con.commit()
    con.close()

    _INDEX_STATUS_MEMORY_CACHE.clear()
    cache_path = _get_persistent_cache_path(db_file)
    if cache_path.exists():
        cache_path.unlink()

    # Lần 1: tính từ SQLite và ghi persistent cache xuống đĩa
    info1 = get_index_status_info(db_file)
    assert info1.is_error is False
    assert info1.doc_count == 1
    assert info1.chunk_count == 2
    assert cache_path.is_file(), "Tệp persistent cache trên đĩa phải được tạo sau lần gọi đầu tiên"

    # Xóa sạch in-memory cache để mô phỏng khởi động lại ứng dụng
    _INDEX_STATUS_MEMORY_CACHE.clear()

    # Chặn sqlite3.connect để chứng minh lần 2 đọc hoàn toàn từ persistent disk cache
    def _fail_connect(*args, **kwargs):
        raise RuntimeError("sqlite3.connect KHÔNG được phép gọi khi persistent cache còn hiệu lực!")
    monkeypatch.setattr(sqlite3, "connect", _fail_connect)

    # Lần 2 (Cold start sau restart): Phải đọc từ persistent cache thành công
    info2 = get_index_status_info(db_file)
    assert info2.is_error is False
    assert info2.doc_count == 1
    assert info2.chunk_count == 2
    assert info2.fingerprint_12 == info1.fingerprint_12
    assert info2.status_line == info1.status_line


def test_persistent_index_status_cache_invalidation_on_change(tmp_path: Path) -> None:
    """Kiểm tra cơ chế vô hiệu hóa cache khi kích thước hoặc mtime của SQLite thay đổi."""
    from aios_habit.index_status import _INDEX_STATUS_MEMORY_CACHE

    db_file = tmp_path / "test_inval.sqlite"
    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE chunks (chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, source_fingerprint TEXT, file_type TEXT NOT NULL)")
    con.execute("INSERT INTO chunks VALUES ('c1', 'doc_1', 'fp1', 'txt')")
    con.commit()
    con.close()

    _INDEX_STATUS_MEMORY_CACHE.clear()
    info1 = get_index_status_info(db_file)
    assert info1.chunk_count == 1

    # Thêm dữ liệu làm thay đổi kích thước và mtime của SQLite
    con = sqlite3.connect(db_file)
    con.execute("INSERT INTO chunks VALUES ('c2', 'doc_2', 'fp2', 'txt')")
    con.commit()
    con.close()

    # Xóa in-memory cache
    _INDEX_STATUS_MEMORY_CACHE.clear()

    # Lần này hệ thống phải phát hiện st_size thay đổi và tính lại, không dùng cache cũ
    info2 = get_index_status_info(db_file)
    assert info2.doc_count == 2
    assert info2.chunk_count == 2
    assert info2.fingerprint_12 != info1.fingerprint_12


def test_persistent_index_status_cache_rollback_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra cờ hoàn lui AIOS_DISABLE_PERSISTENT_INDEX_STATUS_CACHE."""
    from aios_habit.index_status import (
        ENV_DISABLE_PERSISTENT_INDEX_STATUS_CACHE,
        _INDEX_STATUS_MEMORY_CACHE,
        _get_persistent_cache_path,
    )

    monkeypatch.setenv(ENV_DISABLE_PERSISTENT_INDEX_STATUS_CACHE, "1")

    db_file = tmp_path / "test_rollback.sqlite"
    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE chunks (chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, source_fingerprint TEXT, file_type TEXT NOT NULL)")
    con.execute("INSERT INTO chunks VALUES ('c1', 'doc_1', 'fp1', 'txt')")
    con.commit()
    con.close()

    _INDEX_STATUS_MEMORY_CACHE.clear()
    cache_path = _get_persistent_cache_path(db_file)

    info = get_index_status_info(db_file)
    assert info.is_error is False
    assert not cache_path.exists(), "Khi bật cờ tắt persistent cache thì không được tạo tệp cache trên đĩa"


def test_persistent_index_status_cache_corrupted_file_fallback(tmp_path: Path) -> None:
    """Kiểm tra cơ chế chịu lỗi khi tệp cache trên đĩa bị hỏng (corrupted json)."""
    from aios_habit.index_status import _INDEX_STATUS_MEMORY_CACHE, _get_persistent_cache_path

    db_file = tmp_path / "test_corrupt.sqlite"
    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE chunks (chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, source_fingerprint TEXT, file_type TEXT NOT NULL)")
    con.execute("INSERT INTO chunks VALUES ('c1', 'doc_1', 'fp1', 'txt')")
    con.commit()
    con.close()

    cache_path = _get_persistent_cache_path(db_file)
    cache_path.write_text("{ corrupted invalid json ...", encoding="utf-8")

    _INDEX_STATUS_MEMORY_CACHE.clear()

    # Phải fallback an toàn tính từ SQLite mà không gây crash
    info = get_index_status_info(db_file)
    assert info.is_error is False
    assert info.doc_count == 1
    assert info.chunk_count == 1

