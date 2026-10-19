"""Bộ kiểm thử đơn vị cho Adapter nạp tri thức phỏng vấn chuyên gia vào Kho LSU (Ticket DESKTOP-LSU-EXPERT-INTERVIEW-INGEST-HOME).

Kiểm chứng toàn diện:
1. Trích xuất đúng 33 dòng từ review pack markdown:
   - 18 dòng thiếu mã: ma_loi == "chưa có/chưa rõ", cho_bo_sung == "cho bo sung", is_5_fields_complete == False.
   - 15 dòng có mã đầy đủ: giữ nguyên mã lỗi gốc.
2. Lưu vào staging:
   - session_id, store_id="kho_lsu", ingest_status="cho_nap", review_status="dung".
   - Bộ lọc filter_cho_bo_sung_staged_items trả về chính xác 18 dòng.
3. Sao lưu trực tuyến library.sqlite và kiểm tra tính toàn vẹn (integrity_check).
4. Định dạng chunk và nhãn nguồn: "phong-van-chuyen-gia", tên người phỏng vấn, ngày phỏng vấn.
5. Nạp vào Kho LSU và cơ chế chống nạp trùng (idempotent upsert).
6. Cơ chế rollback / gỡ bỏ sạch toàn bộ dữ liệu mang nhãn nguồn.
7. Kiểm chứng truy hồi và ghi nhận feedback Bước 2.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict

import pytest

from aios_habit.answer_feedback import feedback_file
from aios_habit.intake_lsu_ingest_adapter import (
    CHO_BO_SUNG_FLAG,
    DEFAULT_REVIEW_PACK_PATH,
    EXPERT_NAME_DEFAULT,
    INTERVIEW_DATE_DEFAULT,
    MISSING_CODE_VALUE,
    SOURCE_TAG_EXPERT_INTERVIEW,
    STT_CHO_BO_SUNG,
    STT_CO_MA_DAY_DU,
    backup_lsu_library,
    check_sqlite_integrity,
    filter_cho_bo_sung_staged_items,
    format_interview_chunk_text,
    ingest_staged_lsu_items,
    parse_lsu_review_pack,
    rollback_lsu_interview_ingest,
    stage_lsu_review_pack,
    verify_lsu_interview_retrieval,
)
from aios_habit.intake_staging import (
    INGEST_CHO_NAP,
    STATUS_DUNG,
    IntakeStagingStore,
)


def _init_mock_lsu_library(db_path: Path) -> Path:
    """Khởi tạo một DB SQLite giả lập Kho LSU đầy đủ cấu trúc bảng và trigger."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS chunks (
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
                retrievable INTEGER NOT NULL DEFAULT 1 CHECK (retrievable IN (0, 1)),
                domain TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
            CREATE TABLE IF NOT EXISTS source_state (
                document_id TEXT PRIMARY KEY,
                source_fingerprint TEXT NOT NULL DEFAULT '',
                min_fingerprint TEXT,
                max_fingerprint TEXT,
                chunk_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS chunk_embeddings (
                chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
                model_fingerprint TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                model_id TEXT NOT NULL,
                model_revision TEXT NOT NULL,
                runtime TEXT NOT NULL,
                runtime_version TEXT NOT NULL,
                dimension INTEGER NOT NULL CHECK (dimension > 0),
                dtype TEXT NOT NULL CHECK (dtype = 'float32-le'),
                normalized INTEGER NOT NULL CHECK (normalized IN (0, 1)),
                vector_blob BLOB NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (chunk_id, model_fingerprint)
            );
            CREATE TABLE IF NOT EXISTS chunk_sparse_embeddings (
                chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
                model_fingerprint TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                sparse_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (chunk_id, model_fingerprint)
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                normalized_text,
                source_name,
                source_path,
                metadata_json,
                tokenize='unicode61'
            );
            CREATE TRIGGER IF NOT EXISTS chunks_fts_insert AFTER INSERT ON chunks
            WHEN new.retrievable = 1 BEGIN
                INSERT INTO chunks_fts(chunk_id, normalized_text, source_name, source_path, metadata_json)
                VALUES (new.chunk_id, new.normalized_text, new.source_name, new.source_path, new.metadata_json);
            END;
            CREATE TRIGGER IF NOT EXISTS chunks_fts_delete AFTER DELETE ON chunks BEGIN
                DELETE FROM chunks_fts WHERE chunk_id = old.chunk_id;
            END;
            CREATE TRIGGER IF NOT EXISTS chunks_embeddings_content_update
            AFTER UPDATE OF text, normalized_text, checksum ON chunks
            BEGIN
                DELETE FROM chunk_embeddings WHERE chunk_id = old.chunk_id;
                DELETE FROM chunk_sparse_embeddings WHERE chunk_id = old.chunk_id;
            END;
            """
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def test_parse_lsu_review_pack():
    """Kiểm tra bóc tách 33 dòng từ review pack theo đúng quy chuẩn điều phối."""
    if not DEFAULT_REVIEW_PACK_PATH.is_file():
        pytest.skip("Tệp review pack không tồn tại tại đường dẫn mặc định.")

    rows = parse_lsu_review_pack(DEFAULT_REVIEW_PACK_PATH)
    assert len(rows) == 33

    cho_bo_sung_rows = [r for r in rows if r.cho_bo_sung == CHO_BO_SUNG_FLAG]
    complete_rows = [r for r in rows if r.cho_bo_sung == ""]

    assert len(cho_bo_sung_rows) == 18
    assert len(complete_rows) == 15

    # Kiểm tra đúng từng số thứ tự gốc của 18 dòng thiếu mã
    stt_cho_bo_sung_actual = tuple(r.stt for r in cho_bo_sung_rows)
    assert stt_cho_bo_sung_actual == STT_CHO_BO_SUNG

    # Kiểm tra đúng từng số thứ tự gốc của 15 dòng có đủ mã
    stt_co_ma_actual = tuple(r.stt for r in complete_rows)
    assert stt_co_ma_actual == STT_CO_MA_DAY_DU

    # Kiểm tra giá trị ma_loi của 18 dòng
    for r in cho_bo_sung_rows:
        assert r.ma_loi == MISSING_CODE_VALUE
        assert r.cho_bo_sung == "cho bo sung"
        assert r.is_5_fields_complete is False

    # Kiểm tra dòng STT 5 (Sirius 2 C7620)
    row_5 = next(r for r in rows if r.stt == 5)
    assert row_5.ma_loi == "C7620"
    assert row_5.cho_bo_sung == ""
    assert row_5.is_5_fields_complete is True
    assert "SIM tape" in row_5.doi_sach


def test_staging_lsu_review_pack(tmp_path: Path):
    """Kiểm tra đưa 33 dòng vào staging store và bộ lọc truy vấn cờ 'cho bo sung'."""
    staging_db = tmp_path / "staging_test.sqlite"
    store = IntakeStagingStore(staging_db)

    staged_items = stage_lsu_review_pack(staging_store=store)
    assert len(staged_items) == 33

    # Kiểm tra phiên
    session = store.get_session("session-lsu-expert-interview-20261018")
    assert session is not None
    assert session.store_id == "kho_lsu"
    assert session.mode == "phong_van"
    assert session.status == "approved"

    # Kiểm tra trạng thái nạp và duyệt
    for item in staged_items:
        assert item.store_id == "kho_lsu"
        assert item.review_status == STATUS_DUNG
        assert item.ingest_status == INGEST_CHO_NAP
        assert SOURCE_TAG_EXPERT_INTERVIEW in item.source_tag or "phong-van" in item.source_tag

    # Kiểm tra bộ lọc 18 dòng cho bổ sung
    cho_bo_sung_items = filter_cho_bo_sung_staged_items(store)
    assert len(cho_bo_sung_items) == 18
    for it in cho_bo_sung_items:
        assert it.fields.get("cho_bo_sung") == CHO_BO_SUNG_FLAG
        assert it.fields.get("ma_loi") == MISSING_CODE_VALUE
        assert it.fields.get("is_5_fields_complete") == "false"


def test_backup_lsu_library(tmp_path: Path):
    """Kiểm tra sao lưu library.sqlite và xác thực tính toàn vẹn."""
    mock_db = _init_mock_lsu_library(tmp_path / "library.sqlite")
    backup_file = tmp_path / "backup" / "library.sqlite.bak"

    res = backup_lsu_library(library_path=mock_db, backup_dest=backup_file)
    assert res["ok"] is True
    assert res["integrity_status"] == "ok"
    assert Path(res["backup_path"]).is_file()
    assert res["sha256"] != ""

    # Kiểm tra integrity độc lập
    ok, msg = check_sqlite_integrity(backup_file)
    assert ok is True
    assert msg == "ok"


def test_format_interview_chunk_text():
    """Kiểm tra văn bản chunk định dạng đầy đủ thông tin trường."""
    if not DEFAULT_REVIEW_PACK_PATH.is_file():
        pytest.skip("Review pack không khả dụng.")

    rows = parse_lsu_review_pack(DEFAULT_REVIEW_PACK_PATH)
    r1 = rows[0]  # STT 1 (cho bo sung)
    text1 = format_interview_chunk_text(r1)
    assert EXPERT_NAME_DEFAULT == "Nguyễn Ích Khiêm"
    assert "[Nguồn tri thức]: Phỏng vấn chuyên gia LSU" in text1
    assert "[Chuyên gia]: %s" % EXPERT_NAME_DEFAULT in text1
    assert "[Chuyên gia]: Nguyễn Ích Khiêm" in text1
    assert "Nguyễn Trọng Khiêm" not in text1
    assert "[STT gốc]: 1" in text1
    assert "[Mã lỗi]: %s" % MISSING_CODE_VALUE in text1
    assert "[Cờ trạng thái]: %s" % CHO_BO_SUNG_FLAG in text1
    assert "[Hiện tượng]:" in text1

    r5 = rows[4]  # STT 5 (C7620)
    text5 = format_interview_chunk_text(r5)
    assert "[Mã lỗi]: C7620" in text5
    assert "[Cờ trạng thái]" not in text5
    assert "SIM tape" in text5


def test_ingest_staged_lsu_items_and_anti_duplication(tmp_path: Path, monkeypatch):
    """Kiểm tra nạp 33 dòng vào Kho LSU và tính bất biến chống nạp trùng."""
    staging_db = tmp_path / "staging.sqlite"
    mock_db = _init_mock_lsu_library(tmp_path / "library.sqlite")
    backup_dest = tmp_path / "library.sqlite.bak-test"
    store = IntakeStagingStore(staging_db)

    # 1. Nạp lần đầu
    stage_lsu_review_pack(staging_store=store)
    report1 = ingest_staged_lsu_items(
        staging_store=store,
        library_path=mock_db,
        skip_backup=False,
    )

    assert report1["ok"] is True
    assert report1["ingested_count"] == 33
    assert report1["after_chunks"] == 33
    assert report1["interview_chunks_in_db"] == 33
    assert report1["interview_dense_vectors_in_db"] == 33
    assert report1["interview_sparse_vectors_in_db"] == 33
    assert report1["integrity_status"] == "ok"

    # 2. Nạp lần hai (chống nạp trùng / idempotent test)
    report2 = ingest_staged_lsu_items(
        staging_store=store,
        library_path=mock_db,
        skip_backup=True,
    )

    assert report2["ok"] is True
    assert report2["ingested_count"] == 33
    # Số lượng chunks trong DB vẫn giữ nguyên 33, không bị nhân đôi
    assert report2["after_chunks"] == 33
    assert report2["interview_chunks_in_db"] == 33

    # Kiểm tra FTS5 cũng có đúng 33 bản ghi
    conn = sqlite3.connect(str(mock_db))
    try:
        fts_count = int(conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0])
        assert fts_count == 33
    finally:
        conn.close()


def test_rollback_lsu_interview_ingest(tmp_path: Path):
    """Kiểm tra cơ chế rollback sạch sẽ toàn bộ các mục mang nhãn nguồn."""
    staging_db = tmp_path / "staging.sqlite"
    mock_db = _init_mock_lsu_library(tmp_path / "library.sqlite")
    store = IntakeStagingStore(staging_db)

    # Nạp 33 dòng
    stage_lsu_review_pack(staging_store=store)
    ingest_staged_lsu_items(staging_store=store, library_path=mock_db, skip_backup=True)

    # Thực hiện rollback
    rollback_res = rollback_lsu_interview_ingest(library_path=mock_db)
    assert rollback_res["ok"] is True
    assert rollback_res["removed_chunks_count"] == 33
    assert rollback_res["integrity_status"] == "ok"

    # Kiểm tra các bảng đã sạch 100%
    conn = sqlite3.connect(str(mock_db))
    try:
        chunk_c = int(conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
        dense_c = int(conn.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0])
        sparse_c = int(conn.execute("SELECT COUNT(*) FROM chunk_sparse_embeddings").fetchone()[0])
        fts_c = int(conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0])
        assert chunk_c == 0
        assert dense_c == 0
        assert sparse_c == 0
        assert fts_c == 0
    finally:
        conn.close()


def test_verify_lsu_interview_retrieval(tmp_path: Path, monkeypatch):
    """Kiểm tra quy trình kiểm chứng truy hồi và ghi nhận feedback Bước 2."""
    staging_db = tmp_path / "staging.sqlite"
    mock_db = _init_mock_lsu_library(tmp_path / "library.sqlite")
    store = IntakeStagingStore(staging_db)

    # Chuyển hướng file feedback vào thư mục tạm
    fb_path = tmp_path / "answer_feedback.jsonl"
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))

    # Nạp dữ liệu vào mock DB
    stage_lsu_review_pack(staging_store=store)
    ingest_staged_lsu_items(staging_store=store, library_path=mock_db, skip_backup=True)

    # Chạy kiểm chứng truy hồi
    eval_res = verify_lsu_interview_retrieval(
        library_path=mock_db,
        record_to_feedback_loop=True,
    )

    assert eval_res["ok"] is True
    assert eval_res["total_questions"] == 5
    assert eval_res["hits"] >= 4
    assert eval_res["hit_rate"] >= 0.8

    # Kiểm tra feedback đã được ghi vào file JSONL
    assert fb_path.is_file()
    lines = [json.loads(line) for line in fb_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 5
    for record in lines:
        assert record["topic"] == "phong-van-chuyen-gia"
        assert record["lane"] == "kho_lsu"
        assert record["rating"] in ("huu_ich", "chua_huu_ich")
