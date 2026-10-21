"""Bộ kiểm thử đơn vị toàn diện cho Adapter nạp tri thức bài giảng chuyên gia vào Kho kiến thức tổng hợp (Ticket DESKTOP-KNOWLEDGE-INTAKE-TRITHUC-HOME).

Kiểm chứng toàn diện các tiêu chí:
1. Hồ sơ đích Kho kiến thức tổng hợp (`KHO_TONG_HOP_PROFILE`):
   - Đủ 5 trường bắt buộc (`chu_de`, `noi_dung`, `dieu_kien_ap_dung`, `vi_du`, `nguon`).
   - Đủ các trường phụ (`nguoi_day`, `ngay_day`, `linh_vuc`, `ghi_chu`).
   - Đúng `store_id="kho_tong_hop"` và `ingest_route="DESKTOP-KNOWLEDGE-INTAKE-TRITHUC-HOME"`.
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
   - Triggers SQLite tự động duy trì `chunks_fts` và `source_state`.
   - Chống nạp trùng bằng khóa mục (`document_id`, `chunk_id`, checksum).
7. Kiểm chứng sau nạp (Retrieval Verification):
   - Hỏi lại đúng nội dung bài giảng vừa nạp.
   - Nguồn trích trong câu trả lời PHẢI là chính tài liệu vừa nạp (`Bai_giang_chuyen_gia_*.txt`).
8. Đường lui an toàn (Rollback Mechanism):
   - Gỡ sạch toàn bộ tài liệu đã nạp theo nhãn nguồn `"day-chuyen-gia"`.
   - Trả lại số lượng ban đầu, kiểm tra toàn vẹn CSDL sau khi rollback.
9. Tích hợp tổng hợp bộ máy (Intake Engine Synthesis Integration):
   - Bộ máy thu tri thức tự động tổng hợp đúng khuôn Kho tổng hợp từ các lượt hỏi đáp chế độ DẠY.
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
    KHO_TONG_HOP_PROFILE,
    STORE_ID_DIEU_TRA_LOI,
    STORE_ID_LSU,
    STORE_ID_TONG_HOP,
    format_source_tag,
    format_tonghop_source_tag,
    get_target_profile,
    parse_source_tag,
    reset_target_profiles,
)
from aios_habit.intake_tonghop_ingest_adapter import (
    DEFAULT_MODEL_FINGERPRINT,
    DEFAULT_VERIFICATION_QUESTIONS,
    SOURCE_TAG_EXPERT_TEACHING,
    TongHopTeachingItem,
    backup_tonghop_library,
    check_sqlite_integrity,
    format_tonghop_chunk_text,
    get_default_tonghop_sample_cases,
    ingest_staged_tonghop_items,
    normalize_text_lexical,
    pack_dense_vector,
    rollback_tonghop_teaching_ingest,
    seed_sample_tonghop_teaching_items,
    stage_tonghop_teaching_cases,
    verify_tonghop_teaching_retrieval,
)
from aios_habit.knowledge_intake_engine import (
    MODE_DAY,
    KnowledgeIntakeEngine,
    KnowledgeIntakeSession,
    synthesize_draft_items,
)


def _init_mock_tonghop_library(db_path: Path) -> Path:
    """Khởi tạo một CSDL SQLite giả lập Kho tổng hợp đầy đủ cấu trúc bảng và trigger."""
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
                metadata_json UNINDEXED,
                tokenize='unicode61 remove_diacritics 2'
            );

            -- Triggers đồng bộ FTS
            CREATE TRIGGER IF NOT EXISTS chunks_fts_insert AFTER INSERT ON chunks
            WHEN new.retrievable = 1 BEGIN
                INSERT INTO chunks_fts(chunk_id, normalized_text, source_name, source_path, metadata_json)
                VALUES (new.chunk_id, new.normalized_text, new.source_name, new.source_path, new.metadata_json);
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_fts_delete AFTER DELETE ON chunks BEGIN
                DELETE FROM chunks_fts WHERE chunk_id = old.chunk_id;
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_fts_update AFTER UPDATE ON chunks BEGIN
                DELETE FROM chunks_fts WHERE chunk_id = old.chunk_id;
                INSERT INTO chunks_fts(chunk_id, normalized_text, source_name, source_path, metadata_json)
                SELECT new.chunk_id, new.normalized_text, new.source_name, new.source_path, new.metadata_json
                WHERE new.retrievable = 1;
            END;

            -- Triggers đồng bộ source_state
            CREATE TRIGGER IF NOT EXISTS chunks_source_state_insert AFTER INSERT ON chunks
            WHEN new.retrievable = 1 BEGIN
                INSERT INTO source_state (document_id, source_fingerprint, min_fingerprint, max_fingerprint, chunk_count)
                VALUES (new.document_id, COALESCE(new.source_fingerprint, ''), new.source_fingerprint, new.source_fingerprint, 1)
                ON CONFLICT(document_id) DO UPDATE SET
                    min_fingerprint = MIN(source_state.min_fingerprint, excluded.min_fingerprint),
                    max_fingerprint = MAX(source_state.max_fingerprint, excluded.max_fingerprint),
                    chunk_count = source_state.chunk_count + 1;
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_source_state_delete AFTER DELETE ON chunks
            WHEN old.retrievable = 1 BEGIN
                DELETE FROM source_state WHERE document_id = old.document_id;
                INSERT INTO source_state (document_id, source_fingerprint, min_fingerprint, max_fingerprint, chunk_count)
                SELECT document_id, MIN(source_fingerprint), MIN(source_fingerprint), MAX(source_fingerprint), COUNT(*)
                FROM chunks WHERE document_id = old.document_id AND retrievable = 1 GROUP BY document_id;
            END;

            -- Dữ liệu gốc giả lập ban đầu (1 tài liệu nền sẵn có)
            INSERT INTO chunks (
                chunk_id, document_id, source_path, source_name, file_type,
                text, normalized_text, metadata_json, privacy_labels_json,
                source_fingerprint, checksum, retrievable
            ) VALUES (
                'initial-chunk-01', 'initial-doc-01', 'D:\\Sandbox\\tong_hop\\Tai_lieu_goc.txt',
                'Tai_lieu_goc.txt', 'document', 'Tài liệu hướng dẫn an toàn lao động chung của nhà máy.',
                'tai lieu huong dan an toan lao dong chung cua nha may', '{"domain": "tong_hop", "source_tag": "tai-lieu-goc"}',
                '["local_only"]', 'hash-initial-01', 'hash-initial-01', 1
            );
            """
        )
    finally:
        conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_target_profile_declaration_and_fields():
    """1. Kiểm chứng hồ sơ đích Kho kiến thức tổng hợp khai báo đầy đủ theo yêu cầu vé."""
    reset_target_profiles()
    profile = get_target_profile(STORE_ID_TONG_HOP)

    assert profile is not None
    assert profile.store_id == "kho_tong_hop"
    assert profile.display_name == "Kho kiến thức tổng hợp"
    assert profile.ingest_route == "DESKTOP-KNOWLEDGE-INTAKE-TRITHUC-HOME"
    assert profile.source_prefix == "kho_tong_hop"

    # Kiểm tra 5 trường bắt buộc: chủ đề, nội dung, điều kiện áp dụng, ví dụ, nguồn
    req_fields = profile.required_fields
    assert "chu_de" in req_fields
    assert "noi_dung" in req_fields
    assert "dieu_kien_ap_dung" in req_fields
    assert "vi_du" in req_fields
    assert "nguon" in req_fields
    assert len(req_fields) == 5

    # Kiểm tra các trường phụ
    opt_fields = profile.optional_fields
    assert "nguoi_day" in opt_fields
    assert "ngay_day" in opt_fields
    assert "linh_vuc" in opt_fields
    assert "ghi_chu" in opt_fields

    # Kiểm tra tính hợp lệ bản ghi (validation & completeness)
    valid_record = {
        "chu_de": "Quy trình làm sạch quang học",
        "noi_dung": "Dùng gạc vi sợi tẩm cồn IPA 99.7%",
        "dieu_kien_ap_dung": "Áp dụng trong Cleanroom Class 1000",
        "vi_du": "Kỹ thuật viên lau gương đa giác bị mờ",
        "nguon": "day-chuyen-gia | Nguyễn Ích Khiêm | 2026-10-21",
    }
    ok, missing = profile.validate_record(valid_record)
    assert ok is True
    assert len(missing) == 0
    assert profile.calculate_completeness(valid_record) == 1.0

    # Bản ghi thiếu trường bắt buộc
    incomplete_record = {
        "chu_de": "Quy trình làm sạch quang học",
        "noi_dung": "chưa xác nhận",
        "dieu_kien_ap_dung": "",
        "vi_du": "Ví dụ mẫu",
        "nguon": "day-chuyen-gia",
    }
    ok_inc, missing_inc = profile.validate_record(incomplete_record)
    assert ok_inc is False
    assert len(missing_inc) == 2  # thiếu noi_dung và dieu_kien_ap_dung
    assert profile.calculate_completeness(incomplete_record) == 0.6  # 3/5


def test_source_tag_formatting_and_parsing():
    """2. Kiểm chứng định dạng nhãn nguồn thống nhất cho chế độ dạy."""
    # format_source_tag chế độ dạy với store_id=kho_tong_hop
    tag = format_source_tag(
        mode="day",
        expert_name="Nguyễn Ích Khiêm",
        date_str="2026-10-21",
        store_id=STORE_ID_TONG_HOP,
    )
    assert tag == "day-chuyen-gia | Nguyễn Ích Khiêm | 2026-10-21 | kho_tong_hop"

    # format_tonghop_source_tag chuẩn theo vé: "day-chuyen-gia" + tên người dạy + ngày dạy
    tag_th = format_tonghop_source_tag("Nguyễn Ích Khiêm", "2026-10-21")
    assert tag_th == "day-chuyen-gia | Nguyễn Ích Khiêm | 2026-10-21"

    # parse_source_tag
    parsed = parse_source_tag(tag_th)
    assert parsed["mode"] == "day-chuyen-gia"
    assert parsed["expert_name"] == "Nguyễn Ích Khiêm"
    assert parsed["date"] == "2026-10-21"
    assert parsed["store_id"] == STORE_ID_TONG_HOP


def test_hard_guard_against_production_staging():
    """3. Kiểm chứng cơ chế chặn cứng an toàn từ chối gieo dữ liệu mẫu vào staging thật."""
    # Không truyền staging_store
    with pytest.raises(RuntimeError, match="Chặn cứng an toàn: Không được phép gieo dữ liệu mẫu"):
        stage_tonghop_teaching_cases(staging_store=None)

    # Truyền staging thật
    real_staging = IntakeStagingStore()
    with pytest.raises(RuntimeError, match="Chặn cứng an toàn: Từ chối gieo dữ liệu mẫu vào staging thật"):
        stage_tonghop_teaching_cases(staging_store=real_staging)


def test_safe_ingest_on_empty_staging(tmp_path: Path):
    """4. Kiểm chứng xử lý an toàn khi staging rỗng (0 mục thật): không nạp, không sửa DB, delta = 0."""
    db_file = _init_mock_tonghop_library(tmp_path / "empty_test.sqlite")
    empty_staging = IntakeStagingStore(db_path=tmp_path / "empty_staging.sqlite")

    res = ingest_staged_tonghop_items(
        staging_store=empty_staging,
        library_path=db_file,
        skip_backup=True,
    )

    assert res["ok"] is True
    assert res["ingested_count"] == 0
    assert res["skipped_count"] == 0
    assert res["delta_chunks"] == 0
    assert res["delta_docs"] == 0
    assert res["delta_embeddings"] == 0
    assert res["before_chunks"] == 1
    assert res["after_chunks"] == 1
    assert "0 mục thật trong staging" in res["note"]


def test_backup_and_integrity_check(tmp_path: Path):
    """5. Kiểm chứng sao lưu trực tuyến và kiểm tra tính toàn vẹn CSDL."""
    db_file = _init_mock_tonghop_library(tmp_path / "backup_test.sqlite")
    bk_dest = tmp_path / "backup_test.sqlite.bak"

    bk_info = backup_tonghop_library(library_path=db_file, backup_dest=bk_dest)
    assert bk_info["ok"] is True
    assert bk_info["integrity_status"] == "ok"
    assert Path(bk_info["backup_path"]).is_file()
    assert len(bk_info["sha256"]) == 64

    # Kiểm tra tính toàn vẹn bản sao lưu
    ok, msg = check_sqlite_integrity(bk_dest)
    assert ok is True
    assert msg == "ok"


def test_chunk_formatting_structure():
    """6. Kiểm chứng định dạng văn bản chunk có cấu trúc rõ ràng."""
    cases = get_default_tonghop_sample_cases()
    c1 = cases[0]

    chunk_text = format_tonghop_chunk_text(c1)
    assert "[Nguồn tri thức]: Bài giảng chuyên gia (Dạy tri thức nền)" in chunk_text
    assert "[Người dạy]: Nguyễn Ích Khiêm" in chunk_text
    assert "[Ngày dạy]: 2026-10-21" in chunk_text
    assert "[Nhãn nguồn]: day-chuyen-gia | Nguyễn Ích Khiêm | 2026-10-21" in chunk_text
    assert "[Kho đích]: Kho kiến thức tổng hợp" in chunk_text
    assert "[Chủ đề]: Quy trình cân chỉnh và tiêu chuẩn sạch quang học" in chunk_text
    assert "[Điều kiện áp dụng]: Áp dụng tại phòng sạch Cleanroom Class 1000" in chunk_text
    assert "[Ví dụ minh họa]: Tại xưởng LSU, kỹ thuật viên lau gương đa giác" in chunk_text
    assert "[Nội dung bài giảng]: Nguyên lý làm sạch gương quang học" in chunk_text
    assert "[Ghi chú]: Cần kiểm tra định kỳ hạt bụi phòng sạch" in chunk_text


def test_full_ingest_lifecycle_in_isolated_db(tmp_path: Path):
    """7. Kiểm chứng toàn bộ chu trình nạp tri thức vào CSDL giả lập trong tmp_path."""
    db_file = _init_mock_tonghop_library(tmp_path / "lifecycle_test.sqlite")
    test_staging = IntakeStagingStore(db_path=tmp_path / "test_staging.sqlite")

    # 1. Gieo dữ liệu mẫu vào staging cô lập
    staged_items = stage_tonghop_teaching_cases(staging_store=test_staging)
    assert len(staged_items) == 5

    # 2. Thực hiện nạp
    ingest_res = ingest_staged_tonghop_items(
        staging_store=test_staging,
        library_path=db_file,
        skip_backup=False,
    )

    assert ingest_res["ok"] is True
    assert ingest_res["ingested_count"] == 5
    assert ingest_res["skipped_count"] == 0
    assert ingest_res["before_chunks"] == 1
    assert ingest_res["after_chunks"] == 6
    assert ingest_res["delta_chunks"] == 5
    assert ingest_res["delta_docs"] == 5
    assert ingest_res["delta_embeddings"] == 5
    assert ingest_res["delta_sparse"] == 5
    assert ingest_res["teaching_chunks_in_db"] == 5
    assert ingest_res["integrity_status"] == "ok"
    assert ingest_res["backup"] is not None

    # Kiểm tra trạng thái trong staging đã chuyển sang DA_NAP
    for it in staged_items:
        stored = test_staging.get_draft_item(it.draft_id)
        assert stored is not None
        assert stored.ingest_status == INGEST_DA_NAP

    # 3. Chống nạp trùng: nạp lại lần nữa với cùng các mục
    # Tái stage các mục ở trạng thái CHO_NAP
    for it in staged_items:
        test_staging.update_draft_item_status(it.draft_id, ingest_status=INGEST_CHO_NAP)

    ingest_res2 = ingest_staged_tonghop_items(
        staging_store=test_staging,
        library_path=db_file,
        skip_backup=True,
    )
    assert ingest_res2["ok"] is True
    assert ingest_res2["ingested_count"] == 0
    assert ingest_res2["skipped_count"] == 5
    assert ingest_res2["delta_chunks"] == 0
    assert ingest_res2["after_chunks"] == 6


def test_retrieval_verification(tmp_path: Path):
    """8. Kiểm chứng sau nạp: hỏi lại đúng nội dung và kiểm tra nguồn trích dẫn là chính tài liệu vừa nạp."""
    db_file = _init_mock_tonghop_library(tmp_path / "retrieval_test.sqlite")
    test_staging = IntakeStagingStore(db_path=tmp_path / "test_staging.sqlite")

    stage_tonghop_teaching_cases(staging_store=test_staging)
    ingest_staged_tonghop_items(
        staging_store=test_staging,
        library_path=db_file,
        skip_backup=True,
    )

    # Chạy kiểm chứng truy hồi 5 câu hỏi mặc định
    v_res = verify_tonghop_teaching_retrieval(library_path=db_file)
    assert v_res["ok"] is True
    assert v_res["total_questions"] == 5
    assert v_res["hits"] == 5
    assert v_res["hit_rate"] == 1.0
    assert v_res["hit_rate_percent"] == 100.0

    for item in v_res["results"]:
        assert item["is_hit"] is True
        assert item["has_exact_ingested_citation"] is True
        assert "Bai_giang_chuyen_gia_" in item["citation_source"]
        assert len(item["answer_excerpt"]) > 0


def test_rollback_mechanism(tmp_path: Path):
    """9. Kiểm chứng cơ chế đường lui an toàn: gỡ toàn bộ tài liệu đã nạp theo nhãn nguồn 'day-chuyen-gia'."""
    db_file = _init_mock_tonghop_library(tmp_path / "rollback_test.sqlite")
    test_staging = IntakeStagingStore(db_path=tmp_path / "test_staging.sqlite")

    stage_tonghop_teaching_cases(staging_store=test_staging)
    ingest_staged_tonghop_items(
        staging_store=test_staging,
        library_path=db_file,
        skip_backup=True,
    )

    # Trước khi rollback: 6 chunks (1 gốc + 5 bài giảng)
    conn = sqlite3.connect(str(db_file))
    assert conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 6
    assert conn.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0] == 5
    conn.close()

    # Thực hiện rollback
    rb_res = rollback_tonghop_teaching_ingest(library_path=db_file)
    assert rb_res["ok"] is True
    assert rb_res["removed_chunks_count"] == 5
    assert rb_res["integrity_status"] == "ok"

    # Sau khi rollback: còn đúng 1 chunk gốc ban đầu, 0 chunk embeddings
    conn_after = sqlite3.connect(str(db_file))
    assert conn_after.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 1
    assert conn_after.execute("SELECT COUNT(*) FROM chunk_embeddings").fetchone()[0] == 0
    assert conn_after.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0] == 1
    assert conn_after.execute("SELECT COUNT(*) FROM source_state").fetchone()[0] == 1
    conn_after.close()

    # Kiểm tra toàn vẹn CSDL sau rollback
    ok, msg = check_sqlite_integrity(db_file)
    assert ok is True
    assert msg == "ok"


def test_engine_synthesis_integration(tmp_path: Path):
    """10. Kiểm chứng tích hợp bộ máy thu tri thức tự động tổng hợp đúng khuôn Kho tổng hợp từ lượt hỏi đáp."""
    reset_target_profiles()
    profile = get_target_profile(STORE_ID_TONG_HOP)
    assert profile is not None

    session = KnowledgeIntakeSession(
        session_id="session-test-th-01",
        store_id=STORE_ID_TONG_HOP,
        mode=MODE_DAY,
        expert_name="Kỹ sư Nguyễn Văn An",
        topic="Nguyên lý cảm ứng từ IH",
        profile=profile,
        created_at="2026-10-21T09:00:00",
    )

    # Giả lập các lượt trả lời của chuyên gia
    turn_0 = IntakeTurnRecord(
        turn_id="turn-th-0",
        session_id=session.session_id,
        store_id=STORE_ID_TONG_HOP,
        turn_index=0,
        speaker="ai",
        question_text="Tổng quan về nguyên lý hoạt động?",
        answer_text="Hệ thống gia nhiệt IH sử dụng cuộn coil biến thiên sinh dòng điện xoáy Eddy.",
        probe_type="mo_dau_bai_giang",
        timestamp="2026-10-21T09:01:00",
    )
    turn_1 = IntakeTurnRecord(
        turn_id="turn-th-1",
        session_id=session.session_id,
        store_id=STORE_ID_TONG_HOP,
        turn_index=1,
        speaker="ai",
        question_text="Phạm vi và điều kiện áp dụng?",
        answer_text="Áp dụng cho dòng máy in công nghiệp tốc độ cao từ 65 trang/phút trở lên.",
        probe_type="pham_vi_ap_dung",
        timestamp="2026-10-21T09:02:00",
    )
    turn_2 = IntakeTurnRecord(
        turn_id="turn-th-2",
        session_id=session.session_id,
        store_id=STORE_ID_TONG_HOP,
        turn_index=2,
        speaker="ai",
        question_text="Ví dụ thực tế đã từng xảy ra?",
        answer_text="Ví dụ máy Sirius bị không chín mực mép do cuộn coil bị lệch khe hở 0.8mm.",
        probe_type="vi_du_that_nha_may",
        timestamp="2026-10-21T09:03:00",
    )

    from aios_habit.knowledge_intake_engine import ActiveTurn

    session.turns = [
        ActiveTurn(turn_id=t.turn_id, turn_index=t.turn_index, speaker="expert", question_text=t.question_text, answer_text=t.answer_text, probe_type=t.probe_type)
        for t in (turn_0, turn_1, turn_2)
    ]

    draft_items = synthesize_draft_items(session)
    assert len(draft_items) == 1
    d = draft_items[0]

    assert d.store_id == STORE_ID_TONG_HOP
    assert d.fields["chu_de"] == "Nguyên lý cảm ứng từ IH"
    assert "cuộn coil" in d.fields["noi_dung"]
    assert "Áp dụng cho dòng máy in" in d.fields["dieu_kien_ap_dung"]
    assert "Ví dụ máy Sirius" in d.fields["vi_du"]
    assert "day-chuyen-gia | Kỹ sư Nguyễn Văn An" in d.fields["nguon"]

    # Xác thực độ đủ khuôn
    ok, missing = profile.validate_record(d.fields)
    assert ok is True
    assert len(missing) == 0
