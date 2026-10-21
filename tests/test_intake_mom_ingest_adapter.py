"""Bộ kiểm thử đơn vị toàn diện cho Adapter nạp tri thức bài giảng chuyên gia vào Kho MOM/Opcenter (Ticket DESKTOP-KNOWLEDGE-INTAKE-MOM-HOME).

Kiểm chứng toàn diện các tiêu chí:
1. Hồ sơ đích Kho MOM/Opcenter (`KHO_MOM_PROFILE`):
   - Đủ 4 trường bắt buộc (`chu_de`, `noi_dung`, `dieu_kien_ap_dung`, `nguon`).
   - Đủ các trường phụ (`nguoi_day`, `ngay_day`, `phan_he`, `man_hinh`, `ghi_chu`).
   - Đúng `store_id="kho_mom"` và `ingest_route="DESKTOP-KNOWLEDGE-INTAKE-MOM-HOME"`.
   - Tính toán đầy đủ độ đủ khuôn (completeness) và xác thực (validation).
2. Nhãn nguồn thống nhất:
   - Gắn nhãn nguồn `"day-chuyen-gia"` + tên người dạy + ngày dạy.
   - Định dạng chuẩn: `day-chuyen-gia | <nguoi_day> | <ngay_day>`.
3. Chặn cứng an toàn (Hard Guard):
   - Cấm gieo dữ liệu mẫu vào staging thật (`knowledge_intake_staging.sqlite`).
   - Chỉ cho phép gieo dữ liệu mẫu vào staging cô lập trong test fixture.
4. Xử lý an toàn khi staging rỗng (0 mục thật):
   - Khi staging thật không có mục nào được duyệt, nạp 0 mục an toàn, delta = 0.
5. Sao lưu DB và kiểm tra toàn vẹn (`PRAGMA integrity_check`):
   - Sao lưu trước khi nạp, kiểm tra toàn vẹn bản sao lưu và CSDL.
6. Chu trình nạp đầy đủ (Full Ingest Lifecycle):
   - Nạp vào bảng `chunks`, `chunk_embeddings`, `chunk_sparse_embeddings`.
   - Triggers SQLite tự động duy trì `chunks_fts`.
   - Chống nạp trùng bằng khóa mục (`document_id`, `chunk_id`, checksum).
   - Bảo toàn 100% dữ liệu sản xuất gốc của Opcenter (`wsc-*.txt`).
7. Kiểm chứng sau nạp & Phân biệt nguồn (Retrieval Verification & Source Distinction):
   - Hỏi lại đúng nội dung bài giảng vừa nạp.
   - Nguồn trích trong câu trả lời PHẢI phân biệt được tài liệu dạy (nhãn nguồn "day-chuyen-gia")
     với dữ liệu sản xuất gốc của Opcenter (`wsc-*.txt`).
8. Đường lui an toàn (Rollback Mechanism):
   - Gỡ sạch toàn bộ tài liệu đã nạp theo nhãn nguồn `"day-chuyen-gia"`.
   - Dữ liệu gốc Opcenter còn nguyên vẹn 100%, kiểm tra toàn vẹn CSDL sau khi rollback.
9. Tích hợp tổng hợp bộ máy (Intake Engine Synthesis Integration):
   - Bộ máy thu tri thức tự động tổng hợp đúng khuôn Kho MOM/Opcenter từ các lượt hỏi đáp chế độ DẠY.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict

import pytest

from aios_habit.chat_action_knowledge_intake import _parse_store_id
from aios_habit.intake_staging import (
    INGEST_CHO_NAP,
    INGEST_DA_NAP,
    STATUS_CHO_DUYET,
    STATUS_DUNG,
    IntakeDraftItemRecord,
    IntakeSessionRecord,
    IntakeStagingStore,
    IntakeTurnRecord,
    get_staging_db_path,
)
from aios_habit.intake_target_profiles import (
    KHO_MOM_PROFILE,
    STORE_ID_DIEU_TRA_LOI,
    STORE_ID_LSU,
    STORE_ID_MOM,
    STORE_ID_TONG_HOP,
    format_mom_source_tag,
    format_source_tag,
    get_target_profile,
    parse_source_tag,
    reset_target_profiles,
)
from aios_habit.intake_mom_ingest_adapter import (
    DEFAULT_MODEL_FINGERPRINT,
    DEFAULT_MOM_VERIFICATION_QUESTIONS,
    SOURCE_TAG_EXPERT_TEACHING,
    MomTeachingItem,
    backup_mom_library,
    check_sqlite_integrity,
    format_mom_chunk_text,
    get_default_mom_sample_cases,
    ingest_staged_mom_items,
    normalize_text_lexical,
    pack_dense_vector,
    rollback_mom_teaching_ingest,
    seed_sample_mom_teaching_items,
    stage_mom_teaching_cases,
    verify_mom_teaching_retrieval,
)
from aios_habit.knowledge_intake_engine import (
    MODE_DAY,
    KnowledgeIntakeEngine,
    KnowledgeIntakeSession,
    synthesize_draft_items,
)


def _init_mock_mom_library(db_path: Path) -> Path:
    """Khởi tạo một CSDL SQLite giả lập Kho MOM/Opcenter đầy đủ cấu trúc bảng và trigger."""
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
                retrievable INTEGER NOT NULL DEFAULT 1 CHECK (retrievable IN (0, 1))
            );
            CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);

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
                content='chunks',
                content_rowid='rowid'
            );

            CREATE TRIGGER IF NOT EXISTS chunks_fts_insert AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, chunk_id, normalized_text, source_name)
                VALUES (new.rowid, new.chunk_id, new.normalized_text, new.source_name);
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_fts_delete AFTER DELETE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, chunk_id, normalized_text, source_name)
                VALUES ('delete', old.rowid, old.chunk_id, old.normalized_text, old.source_name);
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_fts_update AFTER UPDATE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, chunk_id, normalized_text, source_name)
                VALUES ('delete', old.rowid, old.chunk_id, old.normalized_text, old.source_name);
                INSERT INTO chunks_fts(rowid, chunk_id, normalized_text, source_name)
                VALUES (new.rowid, new.chunk_id, new.normalized_text, new.source_name);
            END;
            """
        )

        # Chèn 2 bản ghi dữ liệu sản xuất gốc Opcenter (wsc-*.txt) để kiểm chứng phân biệt nguồn
        raw_doc_id = "wsc-015a1b6d9a94dc147ca10588"
        raw_source_name = f"{raw_doc_id}.txt"
        raw_chunk_id = "9af3924d481e6741232c11641f2e35492b72970d72e294b8037ef036bb08ac09"
        raw_text = "©2025 KYOCERA Document Solutions Inc.1 MES／MOM説明 Dữ liệu sản xuất Opcenter gốc."
        raw_norm = normalize_text_lexical(raw_text)
        raw_meta = json.dumps({"source_name": raw_source_name, "extractor": "TextDocumentConverterAdapter"})

        conn.execute(
            """
            INSERT INTO chunks (
                chunk_id, document_id, source_path, source_name, file_type,
                text, normalized_text, metadata_json, privacy_labels_json,
                source_fingerprint, checksum, retrievable
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
            """,
            (
                raw_chunk_id,
                raw_doc_id,
                f"C:\\AIOS\\materialized\\{raw_source_name}",
                raw_source_name,
                "txt",
                raw_text,
                raw_norm,
                raw_meta,
                '["cloud_safe"]',
                "raw_fp",
                "raw_hash",
            ),
        )
        fake_blob = pack_dense_vector([0.1] * 1024)
        conn.execute(
            """
            INSERT INTO chunk_embeddings (
                chunk_id, model_fingerprint, content_hash, model_id, model_revision,
                runtime, runtime_version, dimension, dtype, normalized, vector_blob, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, '2026-10-17T00:00:00');
            """,
            (raw_chunk_id, DEFAULT_MODEL_FINGERPRINT, "raw_hash", "BAAI/bge-m3", "rev1", "onnx", "1.28.0", 1024, "float32-le", fake_blob),
        )
        conn.execute(
            """
            INSERT INTO chunk_sparse_embeddings (
                chunk_id, model_fingerprint, content_hash, sparse_json, created_at
            ) VALUES (?, ?, ?, ?, '2026-10-17T00:00:00');
            """,
            (raw_chunk_id, DEFAULT_MODEL_FINGERPRINT, "raw_hash", '{"100": 1.0}'),
        )
        conn.commit()
    finally:
        conn.close()

    return db_path


# ===========================================================================
# 1. Kiểm thử Hồ sơ đích Kho MOM/Opcenter
# ===========================================================================


def test_mom_target_profile_registration():
    """Kiểm tra hồ sơ đích Kho MOM/Opcenter được khai báo chuẩn và tự động đăng ký."""
    reset_target_profiles()
    profile = get_target_profile(STORE_ID_MOM)
    assert profile is not None
    assert profile.store_id == "kho_mom"
    assert profile.display_name == "Kho MOM/Opcenter"
    assert profile.ingest_route == "DESKTOP-KNOWLEDGE-INTAKE-MOM-HOME"
    assert profile.source_prefix == "kho_mom"

    # 4 trường bắt buộc theo vé
    reqs = profile.required_fields
    assert len(reqs) == 4
    assert set(reqs) == {"chu_de", "noi_dung", "dieu_kien_ap_dung", "nguon"}

    # Các trường phụ
    opts = profile.optional_fields
    assert "nguoi_day" in opts
    assert "ngay_day" in opts
    assert "phan_he" in opts
    assert "man_hinh" in opts
    assert "ghi_chu" in opts

    # Kiểm tra tính completeness
    valid_record = {
        "chu_de": "Hướng dẫn đọc màn hình WIP Tracking",
        "noi_dung": "Chi tiết các bước thao tác trên Opcenter",
        "dieu_kien_ap_dung": "Áp dụng tại trạm WIP Tracking",
        "nguon": "day-chuyen-gia | Nguyễn Văn Chuyên | 2026-10-21",
    }
    ok, missing = profile.validate_record(valid_record)
    assert ok is True
    assert len(missing) == 0
    assert profile.calculate_completeness(valid_record) == 1.0

    # Thiếu trường
    invalid_record = {"chu_de": "Test"}
    ok_inv, missing_inv = profile.validate_record(invalid_record)
    assert ok_inv is False
    assert len(missing_inv) == 3


def test_mom_source_tag_formatting():
    """Kiểm tra định dạng và phân rã nhãn nguồn cho Kho MOM/Opcenter."""
    tag = format_mom_source_tag(expert_name="Nguyễn Văn Chuyên", date_str="2026-10-21")
    assert tag == "day-chuyen-gia | Nguyễn Văn Chuyên | 2026-10-21"

    parsed = parse_source_tag("day-chuyen-gia | Nguyễn Văn Chuyên | 2026-10-21 | kho_mom")
    assert parsed["mode"] == "day-chuyen-gia"
    assert parsed["expert_name"] == "Nguyễn Văn Chuyên"
    assert parsed["date"] == "2026-10-21"
    assert parsed["store_id"] == "kho_mom"


def test_mom_parse_store_id():
    """Kiểm tra nhận diện kho MOM từ câu lệnh chat."""
    assert _parse_store_id("thu tri thuc kho mom") == STORE_ID_MOM
    assert _parse_store_id("day kien thuc opcenter") == STORE_ID_MOM
    assert _parse_store_id("kho tong hop") == STORE_ID_TONG_HOP
    assert _parse_store_id("kho lsu") == STORE_ID_LSU


# ===========================================================================
# 2. Kiểm thử Chặn Cứng An Toàn (Hard Guard)
# ===========================================================================


def test_hard_guard_blocks_real_staging():
    """Cơ chế chặn cứng an toàn phải ném ngoại lệ nếu cố tình gieo dữ liệu mẫu vào Staging thật."""
    real_staging_path = get_staging_db_path()
    real_store = IntakeStagingStore(real_staging_path)

    with pytest.raises(RuntimeError) as exc_info:
        seed_sample_mom_teaching_items(staging_store=real_store)
    assert "Chặn cứng an toàn" in str(exc_info.value)

    with pytest.raises(RuntimeError) as exc_info2:
        seed_sample_mom_teaching_items(staging_store=None)
    assert "Chặn cứng an toàn" in str(exc_info2.value)


# ===========================================================================
# 3. Kiểm thử Xử Lý Khi Staging Rỗng (0 Mục Thật)
# ===========================================================================


def test_ingest_empty_staging_safe(tmp_path: Path):
    """Khi staging không có mục nào chờ nạp, adapter phải nạp 0 mục an toàn, delta = 0."""
    mock_db = _init_mock_mom_library(tmp_path / "mom_library.sqlite")
    empty_staging = IntakeStagingStore(tmp_path / "empty_staging.sqlite")

    result = ingest_staged_mom_items(
        staging_store=empty_staging,
        library_path=mock_db,
        skip_backup=True,
    )

    assert result["ok"] is True
    assert result["ingested_count"] == 0
    assert result["delta_chunks"] == 0
    assert result["delta_retrievable_chunks"] == 0
    assert result["delta_docs"] == 0
    assert result["delta_embeddings"] == 0
    assert result["delta_sparse"] == 0
    assert result["integrity_status"] == "ok"
    assert "0 mục thật" in result["note"]


# ===========================================================================
# 4. Kiểm thử Sao Lưu CSDL & Toàn Vẹn (Backup & Integrity)
# ===========================================================================


def test_backup_mom_library(tmp_path: Path):
    """Kiểm tra sao lưu an toàn CSDL Kho MOM/Opcenter và kiểm tra toàn vẹn."""
    mock_db = _init_mock_mom_library(tmp_path / "mom_library.sqlite")
    backup_dest = tmp_path / "backups" / "mom_backup.sqlite"

    backup_info = backup_mom_library(library_path=mock_db, backup_dest=backup_dest)

    assert backup_info["ok"] is True
    assert Path(backup_info["backup_path"]).is_file()
    assert backup_info["integrity_status"] == "ok"
    assert len(backup_info["sha256"]) == 64
    assert backup_info["size_bytes"] > 0

    ok_check, msg_check = check_sqlite_integrity(backup_dest)
    assert ok_check is True
    assert msg_check == "ok"


# ===========================================================================
# 5. Kiểm thử Chu Trình Nạp Đầy Đủ & Chống Nạp Trùng
# ===========================================================================


def test_ingest_mom_teaching_items_lifecycle(tmp_path: Path):
    """Kiểm tra chu trình nạp 5 bài giảng mẫu vào CSDL giả lập và chống nạp trùng."""
    mock_db = _init_mock_mom_library(tmp_path / "mom_library.sqlite")
    test_staging = IntakeStagingStore(tmp_path / "test_staging.sqlite")

    # 1. Gieo dữ liệu mẫu vào test staging
    staged = seed_sample_mom_teaching_items(staging_store=test_staging)
    assert len(staged) == 5

    # 2. Thực hiện nạp
    ingest_res = ingest_staged_mom_items(
        staging_store=test_staging,
        library_path=mock_db,
        skip_backup=False,
    )

    assert ingest_res["ok"] is True
    assert ingest_res["ingested_count"] == 5
    assert ingest_res["delta_chunks"] == 5
    assert ingest_res["delta_retrievable_chunks"] == 5
    assert ingest_res["delta_embeddings"] == 5
    assert ingest_res["delta_sparse"] == 5
    assert ingest_res["integrity_status"] == "ok"
    assert ingest_res["backup"] is not None

    # Kiểm tra trạng thái trong staging đã chuyển sang da_nap
    for item in staged:
        refetched = test_staging.get_draft_item(item.draft_id)
        assert refetched is not None
        assert refetched.ingest_status == INGEST_DA_NAP

    # 3. Chống nạp trùng (Idempotence)
    # Đưa lại trạng thái cho_nap trên cùng nội dung và chạy nạp lại
    for item in staged:
        test_staging.update_draft_item_status(item.draft_id, ingest_status=INGEST_CHO_NAP)

    re_ingest_res = ingest_staged_mom_items(
        staging_store=test_staging,
        library_path=mock_db,
        skip_backup=True,
    )
    assert re_ingest_res["ok"] is True
    assert re_ingest_res["ingested_count"] == 0
    assert re_ingest_res["skipped_count"] == 5
    assert re_ingest_res["delta_chunks"] == 0


# ===========================================================================
# 6. Kiểm thử Truy Hồi Sau Nạp & Phân Biệt Dữ Liệu Gốc
# ===========================================================================


def test_verify_mom_teaching_retrieval_distinction(tmp_path: Path):
    """Kiểm tra truy hồi 5/5 câu hỏi và xác minh nguồn trích phân biệt được với dữ liệu gốc."""
    mock_db = _init_mock_mom_library(tmp_path / "mom_library.sqlite")
    test_staging = IntakeStagingStore(tmp_path / "test_staging.sqlite")

    seed_sample_mom_teaching_items(staging_store=test_staging)
    ingest_staged_mom_items(
        staging_store=test_staging,
        library_path=mock_db,
        skip_backup=True,
    )

    # Chạy kiểm chứng
    verify_res = verify_mom_teaching_retrieval(library_path=mock_db)

    assert verify_res["ok"] is True
    assert verify_res["total_questions"] == 5
    assert verify_res["hits"] == 5
    assert verify_res["hit_rate"] == 1.0

    for r in verify_res["results"]:
        assert r["is_hit"] is True
        assert r["has_exact_ingested_citation"] is True
        # Yêu cầu cốt lõi của vé: phân biệt được tài liệu dạy với dữ liệu sản xuất gốc Opcenter
        assert r["is_teaching_source"] is True
        assert r["is_raw_opcenter"] is False
        assert r["differentiates_source"] is True
        assert "Bai_giang_chuyen_gia_mom_" in r["citation_source"]
        assert "wsc-" not in r["citation_source"]


# ===========================================================================
# 7. Kiểm thử Đường Lui An Toàn (Rollback)
# ===========================================================================


def test_rollback_mom_teaching_ingest(tmp_path: Path):
    """Kiểm tra gỡ sạch toàn bộ tài liệu đã nạp theo nhãn nguồn day-chuyen-gia."""
    mock_db = _init_mock_mom_library(tmp_path / "mom_library.sqlite")
    test_staging = IntakeStagingStore(tmp_path / "test_staging.sqlite")

    # Lấy số lượng chunks gốc (dữ liệu sản xuất ban đầu: 1 chunk wsc-*.txt)
    conn_init = sqlite3.connect(str(mock_db))
    initial_chunks = conn_init.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    conn_init.close()

    # Nạp 5 bài giảng
    seed_sample_mom_teaching_items(staging_store=test_staging)
    ingest_staged_mom_items(
        staging_store=test_staging,
        library_path=mock_db,
        skip_backup=True,
    )

    # Thực hiện Rollback
    rollback_res = rollback_mom_teaching_ingest(library_path=mock_db)

    assert rollback_res["ok"] is True
    assert rollback_res["removed_chunks_count"] == 5
    assert rollback_res["integrity_status"] == "ok"

    # Kiểm tra số lượng chunks quay về ban đầu
    conn_post = sqlite3.connect(str(mock_db))
    current_chunks = conn_post.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    remaining_raw = conn_post.execute("SELECT source_name FROM chunks").fetchall()
    conn_post.close()

    assert current_chunks == initial_chunks
    assert len(remaining_raw) == 1
    assert remaining_raw[0][0].startswith("wsc-")


# ===========================================================================
# 8. Kiểm thử Tích Hợp Tổng Hợp Bộ Máy (Engine Synthesis)
# ===========================================================================


def test_knowledge_intake_engine_synthesis_mom():
    """Kiểm tra bộ máy KnowledgeIntakeEngine tự động tổng hợp đúng khuôn Kho MOM/Opcenter."""
    reset_target_profiles()
    profile = get_target_profile(STORE_ID_MOM)
    assert profile is not None

    session = KnowledgeIntakeSession(
        session_id="session-test-mom-synth",
        store_id=STORE_ID_MOM,
        mode=MODE_DAY,
        expert_name="Nguyễn Văn Chuyên",
        topic="Hướng dẫn đọc màn hình WIP Tracking trên Opcenter",
        profile=profile,
        created_at="2026-10-21T09:00:00",
    )

    from aios_habit.knowledge_intake_engine import ActiveTurn

    session.turns = [
        ActiveTurn(
            turn_id="turn-mom-0",
            turn_index=0,
            speaker="expert",
            question_text="Giải thích ý nghĩa trạng thái lệnh sản xuất?",
            answer_text="Trạng thái gồm QUEUED, IN_PROGRESS, HOLD và CLOSED. Cần đối chiếu Good Qty trước khi Move Next.",
            probe_type="mo_dau_bai_giang",
        ),
        ActiveTurn(
            turn_id="turn-mom-1",
            turn_index=1,
            speaker="expert",
            question_text="Phân hệ và điều kiện áp dụng?",
            answer_text="Áp dụng tại phân hệ WIP Tracking trên giao diện Opcenter Execution cho line hoàn thiện.",
            probe_type="phan_he_man_hinh",
        ),
        ActiveTurn(
            turn_id="turn-mom-2",
            turn_index=2,
            speaker="expert",
            question_text="Lưu ý vận hành?",
            answer_text="Tuyệt đối không chuyển trạng thái Closed thủ công khi chưa có QA ký.",
            probe_type="ghi_chu",
        ),
    ]

    drafts = synthesize_draft_items(session)
    assert len(drafts) == 1
    draft = drafts[0]

    assert draft.store_id == STORE_ID_MOM
    assert draft.mode == "day"
    assert draft.fields["chu_de"] == "Hướng dẫn đọc màn hình WIP Tracking trên Opcenter"
    assert "QUEUED" in draft.fields["noi_dung"]
    assert "WIP Tracking" in draft.fields["dieu_kien_ap_dung"]
    assert "day-chuyen-gia" in draft.fields["nguon"]
    assert "Nguyễn Văn Chuyên" in draft.fields["nguon"]
    assert draft.fields["nguoi_day"] == "Nguyễn Văn Chuyên"
    assert "QA ký" in draft.fields["ghi_chu"]

    # Xác thực độ đủ khuôn
    ok, missing = profile.validate_record(draft.fields)
    assert ok is True
    assert len(missing) == 0
