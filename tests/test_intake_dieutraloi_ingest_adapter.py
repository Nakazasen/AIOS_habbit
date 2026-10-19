"""Bộ kiểm thử đơn vị toàn diện cho Adapter nạp tri thức phỏng vấn chuyên gia vào Kho điều tra lỗi (Ticket DESKTOP-KNOWLEDGE-INTAKE-DIEUTRALOI-HOME).

Kiểm chứng toàn diện các tiêu chí:
1. Hồ sơ đích Kho điều tra lỗi (`KHO_DIEU_TRA_LOI_PROFILE`):
   - Đủ 5 trường bắt buộc (`ma_loi`, `hien_tuong`, `nguyen_nhan`, `doi_sach`, `cong_doan`).
   - Đủ 4 trường phụ (`model`, `line`, `bo_phan_phu_trach`, `ngay`).
   - Đúng `store_id="kho_dieu_tra_loi"` và `ingest_route="DESKTOP-KNOWLEDGE-INTAKE-DIEUTRALOI-HOME"`.
2. Đưa ca phỏng vấn chuyên gia vào Staging store (`stage_dieutraloi_interview_cases`):
   - Đúng `store_id="kho_dieu_tra_loi"`, `ingest_status="cho_nap"`, `review_status="dung"`.
3. Sao lưu trực tuyến CSDL ca lỗi và kiểm tra tính toàn vẹn (`PRAGMA integrity_check`).
4. Nạp vào bảng `error_cases` và cô lập tuyệt đối theo kho đích:
   - CHỈ nạp các mục `cho_nap` thuộc `kho_dieu_tra_loi`.
   - Tuyệt đối không nạp mục của `kho_lsu` hoặc mục `khong_nap` / `loai`.
   - Gán nhãn nguồn `"phong-van-chuyen-gia"` + tên chuyên gia + ngày phỏng vấn.
5. Chống nạp trùng bằng khóa mục (idempotent dedup):
   - Chạy nạp lần 2 hoặc stage lại cùng mục không tạo thêm bản ghi trùng.
6. Kiểm chứng sau nạp bằng chức năng tra cứu ca tương tự Bước 1 (`search_similar`):
   - Tất cả 5 câu hỏi kiểm chứng đều trả về đúng ca phỏng vấn chuyên gia trong kết quả.
7. Đường lui an toàn (`rollback_dieutraloi_interview_ingest`):
   - Xóa sạch toàn bộ mục mang nhãn nguồn `"phong-van-chuyen-gia"`, giữ nguyên 100% các ca báo cáo gốc.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict

import pytest

from aios_habit.chat_action_knowledge_intake import _parse_store_id
from aios_habit.intake_dieutraloi_ingest_adapter import (
    BATCH_SOURCE_EXPERT_INTERVIEW,
    INGEST_ROUTE_DIEU_TRA_LOI,
    SOURCE_TAG_EXPERT_INTERVIEW,
    DieuTraLoiInterviewCase,
    backup_error_cases_db,
    check_sqlite_integrity,
    get_default_dieutraloi_interview_cases,
    ingest_staged_dieutraloi_items,
    rollback_dieutraloi_interview_ingest,
    seed_sample_dieutraloi_interview_items,
    split_error_code,
    stage_dieutraloi_interview_cases,
    verify_dieutraloi_interview_retrieval,
)
from aios_habit.intake_staging import (
    INGEST_CHO_NAP,
    INGEST_KHONG_NAP,
    STATUS_DUNG,
    STATUS_LOAI,
    IntakeDraftItemRecord,
    IntakeSessionRecord,
    IntakeStagingStore,
)
from aios_habit.intake_target_profiles import (
    KHO_DIEU_TRA_LOI_PROFILE,
    STORE_ID_DIEU_TRA_LOI,
    STORE_ID_LSU,
    get_target_profile,
    reset_target_profiles,
)


def _init_mock_error_cases_db(db_path: Path) -> Path:
    """Khởi tạo một CSDL SQLite giả lập bảng error_cases và import_batches với 2 ca báo cáo gốc."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS import_batches (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file   TEXT NOT NULL,
                file_sha256   TEXT NOT NULL,
                sheet_name    TEXT NOT NULL,
                sheet_type    TEXT,
                department    TEXT,
                line_filter   TEXT,
                header_row    INTEGER,
                imported_at   TEXT NOT NULL DEFAULT (datetime('now')),
                rows_read     INTEGER NOT NULL DEFAULT 0,
                rows_imported INTEGER NOT NULL DEFAULT 0,
                rows_skipped  INTEGER NOT NULL DEFAULT 0,
                notes         TEXT
            );

            CREATE TABLE IF NOT EXISTS error_cases (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id         INTEGER REFERENCES import_batches (id),
                source_row       INTEGER,
                no_dvd           TEXT NOT NULL,
                sheet_type       TEXT,
                department       TEXT,
                machine_type     TEXT,
                line             TEXT,
                error_code_c     TEXT,
                error_code_h     TEXT,
                investigation    TEXT,
                handler          TEXT,
                is_completed     TEXT NOT NULL DEFAULT '',
                needs_jp_support TEXT NOT NULL DEFAULT '',
                raw_json         TEXT NOT NULL,
                skip_cells       TEXT NOT NULL DEFAULT '[]',
                created_at       TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
                occurred_at      TEXT,
                error_code_i     TEXT,
                process_stage    TEXT,
                error_name       TEXT,
                phenomenon       TEXT,
                cause            TEXT,
                countermeasure   TEXT,
                closed_at        TEXT,
                report_link      TEXT,
                error_code_i_src  TEXT,
                error_code_i_note TEXT,
                hientuong_missing TEXT
            );
            """
        )
        # Chèn 1 batch gốc và 2 ca báo cáo gốc
        cur = conn.execute(
            """
            INSERT INTO import_batches (source_file, file_sha256, sheet_name, rows_read, rows_imported)
            VALUES ('Loi KDTPS.xlsx', 'sha256-orig', 'History KDTPS', 2, 2);
            """
        )
        b_id = int(cur.lastrowid)
        conn.execute(
            """
            INSERT INTO error_cases (
                batch_id, source_row, no_dvd, department, machine_type, line,
                error_code_c, error_code_h, error_code_i, phenomenon, cause,
                countermeasure, raw_json
            ) VALUES (?, 10, 'DVD-ORIG-001', 'PE', 'Iris', 'Line 1',
                      'C0030', NULL, 'C0030', 'Kẹt mô tơ chính', 'Bánh răng mòn',
                      'Thay bánh răng', '{"I": "Kẹt mô tơ chính", "AA": "Bánh răng mòn", "AB": "Thay bánh răng"}');
            """,
            (b_id,),
        )
        conn.execute(
            """
            INSERT INTO error_cases (
                batch_id, source_row, no_dvd, department, machine_type, line,
                error_code_c, error_code_h, error_code_i, phenomenon, cause,
                countermeasure, raw_json
            ) VALUES (?, 11, 'DVD-ORIG-002', 'QA', 'Sirius', 'Line 2',
                      'C7610', NULL, 'C7610', 'Đứt cầu chì nhiệt', 'Quá dòng',
                      'Thay cầu chì', '{"I": "Đứt cầu chì nhiệt", "AA": "Quá dòng", "AB": "Thay cầu chì"}');
            """,
            (b_id,),
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def test_kho_dieu_tra_loi_profile_conforms_to_spec():
    """Hồ sơ đích Kho điều tra lỗi phải có đủ 5 trường bắt buộc và 4 trường phụ theo đúng yêu cầu vé."""
    reset_target_profiles()
    profile = get_target_profile(STORE_ID_DIEU_TRA_LOI)
    assert profile is not None
    assert profile.store_id == "kho_dieu_tra_loi"
    assert profile.display_name == "Kho điều tra lỗi"
    assert profile.ingest_route == INGEST_ROUTE_DIEU_TRA_LOI
    assert profile.source_prefix == "kho_dieu_tra_loi"

    assert profile.required_fields == (
        "ma_loi",
        "hien_tuong",
        "nguyen_nhan",
        "doi_sach",
        "cong_doan",
    )
    assert profile.optional_fields == (
        "model",
        "line",
        "bo_phan_phu_trach",
        "ngay",
    )

    # Kiểm tra nhận diện kho đích trong chat action
    assert _parse_store_id("mo phien thu tri thuc kho dieu tra loi") == STORE_ID_DIEU_TRA_LOI


def test_default_interview_cases_completeness():
    """Tập 5 ca phỏng vấn chuyên gia mặc định phải đầy đủ 5 trường bắt buộc và 4 trường phụ."""
    cases = get_default_dieutraloi_interview_cases()
    assert len(cases) == 5
    profile = KHO_DIEU_TRA_LOI_PROFILE

    for c in cases:
        assert c.is_5_fields_complete is True
        record = {
            "ma_loi": c.ma_loi,
            "hien_tuong": c.hien_tuong,
            "nguyen_nhan": c.nguyen_nhan,
            "doi_sach": c.doi_sach,
            "cong_doan": c.cong_doan,
            "model": c.model,
            "line": c.line,
            "bo_phan_phu_trach": c.bo_phan_phu_trach,
            "ngay": c.ngay,
        }
        ok, missing = profile.validate_record(record)
        assert ok is True, f"Ca {c.item_id} thiếu trường: {missing}"
        assert profile.calculate_completeness(record) == 1.0


def test_split_error_code():
    """Kiểm tra phân tách mã lỗi Cxxx và Fxxx/Jxxx."""
    assert split_error_code("C2340") == ("C2340", None)
    assert split_error_code("c7620") == ("C7620", None)
    assert split_error_code("F000") == (None, "F000")
    assert split_error_code("J0411") == (None, "J0411")


def test_backup_and_integrity_check(tmp_path: Path):
    """Kiểm tra sao lưu CSDL ca lỗi và xác thực PRAGMA integrity_check."""
    db_file = _init_mock_error_cases_db(tmp_path / "error_cases_test.db")
    ok, msg = check_sqlite_integrity(db_file)
    assert ok is True
    assert msg == "ok"

    b_path, b_sha, b_size = backup_error_cases_db(
        db_path=db_file,
        backup_dir=tmp_path / "backups",
        backup_tag="unit-test",
    )
    assert b_path.is_file()
    assert len(b_sha) == 64
    assert b_size > 0
    ok_b, _ = check_sqlite_integrity(b_path)
    assert ok_b is True


def test_stage_and_ingest_strict_store_isolation(tmp_path: Path):
    """Chỉ nạp các mục CHO_NAP thuộc kho_dieu_tra_loi, tuyệt đối không nạp kho khác hoặc mục bị loại."""
    db_file = _init_mock_error_cases_db(tmp_path / "error_cases_test.db")
    staging = IntakeStagingStore(db_path=tmp_path / "staging.sqlite")

    # 1. Stage 5 ca của Kho điều tra lỗi (CHO_NAP)
    staged_dtl = stage_dieutraloi_interview_cases(staging_store=staging)
    assert len(staged_dtl) == 5

    # 2. Thêm 1 mục CHO_NAP của Kho LSU để kiểm chứng không nạp nhầm
    staging.save_session(
        IntakeSessionRecord(
            session_id="sess-lsu-other",
            store_id=STORE_ID_LSU,
            mode="phong_van",
            expert_name="Kỹ sư LSU",
            topic="Lỗi LSU",
            status="completed",
        )
    )
    staging.save_draft_item(
        IntakeDraftItemRecord(
            draft_id="draft-lsu-999",
            session_id="sess-lsu-other",
            store_id=STORE_ID_LSU,
            mode="phong_van",
            expert_name="Kỹ sư LSU",
            topic="Lỗi LSU",
            source_tag="phong-van | Kỹ sư LSU | 2026-10-18 | kho_lsu",
            fields={"ma_loi": "C9999", "hien_tuong": "LSU test", "nguyen_nhan": "X", "doi_sach": "Y", "cong_doan": "Z"},
            review_status=STATUS_DUNG,
            ingest_status=INGEST_CHO_NAP,
        )
    )

    # 3. Thêm 1 mục bị LOẠI (khong_nap) của Kho điều tra lỗi
    staging.save_draft_item(
        IntakeDraftItemRecord(
            draft_id="draft-dtl-rejected",
            session_id=staged_dtl[0].session_id,
            store_id=STORE_ID_DIEU_TRA_LOI,
            mode="phong_van",
            expert_name="Kỹ sư B",
            topic="Mục bị loại",
            source_tag="phong-van | Kỹ sư B | 2026-10-18 | kho_dieu_tra_loi",
            fields={"ma_loi": "C8888", "hien_tuong": "Bị loại", "nguyen_nhan": "X", "doi_sach": "Y", "cong_doan": "Z"},
            review_status=STATUS_LOAI,
            ingest_status=INGEST_KHONG_NAP,
        )
    )

    # 4. Thực hiện nạp
    res = ingest_staged_dieutraloi_items(
        db_path=db_file,
        staging_store=staging,
        backup=True,
    )
    assert res["status"] == "success"
    assert res["count_before"] == 2
    assert res["ingested_count"] == 5
    assert res["skipped_count"] == 0
    assert res["count_after"] == 7
    assert res["delta"] == 5
    assert res["integrity_ok"] is True

    # Kiểm tra tuyệt đối không có C9999 (Kho LSU) hay C8888 (mục bị loại) trong error_cases
    conn = sqlite3.connect(str(db_file))
    try:
        codes = [r[0] for r in conn.execute("SELECT error_code_i FROM error_cases;").fetchall()]
        assert "C9999" not in codes
        assert "C8888" not in codes
        assert "C2340" in codes
        assert "C7620" in codes
        assert "C4001" in codes
        assert "F000" in codes
        assert "J0411" in codes
    finally:
        conn.close()


def test_idempotent_dedup_on_repeated_ingest(tmp_path: Path):
    """Chống nạp trùng: chạy lại lần 2 hoặc stage lại cùng dữ liệu không được nạp đúp."""
    db_file = _init_mock_error_cases_db(tmp_path / "error_cases_test.db")
    staging = IntakeStagingStore(db_path=tmp_path / "staging.sqlite")

    stage_dieutraloi_interview_cases(staging_store=staging)
    res1 = ingest_staged_dieutraloi_items(db_path=db_file, staging_store=staging, backup=False)
    assert res1["ingested_count"] == 5
    assert res1["count_after"] == 7

    # Stage lại các mục về trạng thái CHO_NAP và chạy nạp lần 2
    stage_dieutraloi_interview_cases(staging_store=staging)
    res2 = ingest_staged_dieutraloi_items(db_path=db_file, staging_store=staging, backup=False)
    assert res2["ingested_count"] == 0
    assert res2["skipped_count"] == 5
    assert res2["count_before"] == 7
    assert res2["count_after"] == 7


def test_step1_retrieval_verification_and_rollback(tmp_path: Path):
    """Kiểm chứng tra cứu Bước 1 trả về đúng các ca phỏng vấn và rollback xóa sạch sẽ."""
    db_file = _init_mock_error_cases_db(tmp_path / "error_cases_test.db")
    staging = IntakeStagingStore(db_path=tmp_path / "staging.sqlite")

    stage_dieutraloi_interview_cases(staging_store=staging)
    ingest_staged_dieutraloi_items(db_path=db_file, staging_store=staging, backup=False)

    # 1. Kiểm chứng tra cứu Bước 1
    verify_res = verify_dieutraloi_interview_retrieval(db_path=db_file)
    assert verify_res["total_questions"] == 5
    assert verify_res["hits"] == 5
    assert verify_res["hit_rate_percent"] == 100.0

    for r in verify_res["results"]:
        assert r["is_hit"] is True
        matched = r["matched_case"]
        assert matched is not None
        assert SOURCE_TAG_EXPERT_INTERVIEW in matched["bao_cao_goc"]
        assert matched["no_dvd"].startswith("PV-DTL-")

    # 2. Kiểm chứng Rollback (đường lui an toàn)
    rb_res = rollback_dieutraloi_interview_ingest(db_path=db_file)
    assert rb_res["status"] == "rolled_back"
    assert rb_res["deleted_cases"] == 5
    assert rb_res["count_before"] == 7
    assert rb_res["count_after"] == 2
    assert rb_res["integrity_ok"] is True

    # Đảm bảo 2 ca báo cáo gốc vẫn còn nguyên vẹn
    conn = sqlite3.connect(str(db_file))
    try:
        orig_rows = conn.execute("SELECT no_dvd FROM error_cases ORDER BY id;").fetchall()
        assert [r[0] for r in orig_rows] == ["DVD-ORIG-001", "DVD-ORIG-002"]
    finally:
        conn.close()


def test_sample_seeding_hard_guard_against_production_staging(tmp_path: Path):
    """Cơ chế chặn cứng: Từ chối chạy dữ liệu mẫu khi staging đích là staging thật hoặc None."""
    # 1. Gọi không truyền staging_store -> phải từ chối chạy
    with pytest.raises(RuntimeError, match="Chặn cứng an toàn"):
        stage_dieutraloi_interview_cases()

    with pytest.raises(RuntimeError, match="Chặn cứng an toàn"):
        seed_sample_dieutraloi_interview_items()

    # 2. Gọi với default staging store (staging thật) -> phải từ chối chạy
    real_store = IntakeStagingStore()
    with pytest.raises(RuntimeError, match="Chặn cứng an toàn"):
        stage_dieutraloi_interview_cases(staging_store=real_store)

    with pytest.raises(RuntimeError, match="Chặn cứng an toàn"):
        seed_sample_dieutraloi_interview_items(staging_store=real_store)

    # 3. Chỉ cho phép chạy trên staging_store kiểm thử (tmp_path)
    isolated_staging = IntakeStagingStore(db_path=tmp_path / "fixture_staging.sqlite")
    staged = stage_dieutraloi_interview_cases(staging_store=isolated_staging)
    assert len(staged) == 5

    staged_alias = seed_sample_dieutraloi_interview_items(staging_store=isolated_staging)
    assert len(staged_alias) == 5


def test_ingest_empty_staging_store(tmp_path: Path):
    """Khi staging không có mục CHO_NAP nào của Kho điều tra lỗi, adapter nạp an toàn 0 ca."""
    db_file = _init_mock_error_cases_db(tmp_path / "empty_test.db")
    empty_staging = IntakeStagingStore(db_path=tmp_path / "empty_staging.sqlite")

    res = ingest_staged_dieutraloi_items(db_path=db_file, staging_store=empty_staging, backup=False)
    assert res["status"] == "success"
    assert res["total_ready_items"] == 0
    assert res["ingested_count"] == 0
    assert res["skipped_count"] == 0
    assert res["delta"] == 0
    assert res["count_before"] == 2
    assert res["count_after"] == 2
    assert res["integrity_ok"] is True

