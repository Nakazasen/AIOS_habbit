"""Verification script for QD-S4 Rollback procedure on real DB copy.

Ticket: DESKTOP-QD-S4-REPORT-FIX-HOME
Proves that dropping the 3 real triggers (chunks_fts_trigram_insert,
chunks_fts_trigram_delete, chunks_fts_trigram_update) before dropping
chunks_fts_trigram table leaves NO dangling triggers on chunks mutations.
Executed on a temporary copy of a real production index database.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

os.environ["AIOS_RAGV2_LEXICAL_V2"] = "1"

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR / "src"))

from aios_habit.rag_v2.index import LocalChunkIndex


def run_rollback_verification() -> None:
    src = r"D:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\mom\library.sqlite"
    if not os.path.exists(src):
        src = r"D:\Sandbox\AIOS_index_split_new\mom\library.sqlite"

    print("==================================================================", flush=True)
    print("QD-S4 ROLLBACK VERIFICATION ON REAL INDEX DATABASE COPY", flush=True)
    print("==================================================================", flush=True)
    print(f"Source Production DB: {src}", flush=True)

    tmp_dir = tempfile.mkdtemp(prefix="rag_rollback_")
    try:
        copy_db = str(Path(tmp_dir) / "mom_rollback_test.sqlite")
        shutil.copy2(src, copy_db)
        db_size_mb = os.path.getsize(copy_db) / (1024 * 1024)
        print(f"Temporary DB Copy: {copy_db} ({db_size_mb:.2f} MB)", flush=True)

        print("\n--- BƯỚC 1: Khởi tạo chunks_fts_trigram & triggers qua LocalChunkIndex ---", flush=True)
        # Initialize schema via LocalChunkIndex
        init_index = LocalChunkIndex(copy_db, ensure_embeddings_on_open=False)
        init_index.close()

        conn = sqlite3.connect(copy_db)
        cur = conn.cursor()

        # Check virtual table schema
        table_rows = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chunks_fts_trigram'"
        ).fetchall()
        print(f"Bảng chunks_fts_trigram: {table_rows}", flush=True)
        assert len(table_rows) == 1, "Bảng chunks_fts_trigram phải tồn tại!"

        columns = [r[1] for r in cur.execute("PRAGMA table_info(chunks_fts_trigram)").fetchall()]
        print(f"Schema cột thực tế ({len(columns)} cột): {columns}", flush=True)
        assert len(columns) == 5, f"Bảng trigram phải có 5 cột, tìm thấy: {columns}"
        assert columns == ["chunk_id", "normalized_text", "source_name", "source_path", "metadata_json"]

        # Check triggers
        trigger_rows = [
            r[0]
            for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'chunks_fts_trigram%'"
            ).fetchall()
        ]
        print(f"3 triggers thực tế: {sorted(trigger_rows)}", flush=True)
        assert "chunks_fts_trigram_insert" in trigger_rows, "Thiếu trigger chunks_fts_trigram_insert!"
        assert "chunks_fts_trigram_delete" in trigger_rows, "Thiếu trigger chunks_fts_trigram_delete!"
        assert "chunks_fts_trigram_update" in trigger_rows, "Thiếu trigger chunks_fts_trigram_update!"

        initial_chunks = cur.execute("SELECT count(*) FROM chunks").fetchone()[0]
        initial_trigrams = cur.execute("SELECT count(*) FROM chunks_fts_trigram").fetchone()[0]
        print(f"Số lượng bản ghi: chunks={initial_chunks}, chunks_fts_trigram={initial_trigrams}", flush=True)
        conn.close()

        print("\n--- BƯỚC 2: Chạy trình tự Rollback đã đính chính ---", flush=True)
        rollback_sql = """
        DROP TRIGGER IF EXISTS chunks_fts_trigram_insert;
        DROP TRIGGER IF EXISTS chunks_fts_trigram_delete;
        DROP TRIGGER IF EXISTS chunks_fts_trigram_update;
        DROP TABLE IF EXISTS chunks_fts_trigram;
        VACUUM;
        """
        print("Thực thi SQL Rollback:", flush=True)
        print(rollback_sql, flush=True)
        conn = sqlite3.connect(copy_db)
        conn.executescript(rollback_sql)
        conn.commit()

        print("\n--- BƯỚC 3: Xác nhận bảng và 3 triggers đã bị xóa hoàn toàn ---", flush=True)
        cur = conn.cursor()
        rem_tables = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chunks_fts_trigram'"
        ).fetchall()
        rem_triggers = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE '%trigram%'"
        ).fetchall()
        print(f"Bảng chunks_fts_trigram còn lại: {rem_tables}", flush=True)
        print(f"Triggers trigram còn lại: {rem_triggers}", flush=True)
        assert len(rem_tables) == 0, "Bảng chunks_fts_trigram phải bị xóa hoàn toàn!"
        assert len(rem_triggers) == 0, "Toàn bộ triggers trigram phải bị xóa hoàn toàn!"

        print("\n--- BƯỚC 4: Kiểm tra đột biến dữ liệu (INSERT / UPDATE / DELETE) trên chunks ---", flush=True)
        test_chunk_id = f"test-rollback-{uuid.uuid4().hex[:8]}"

        # 1. INSERT
        print(f"1. Thao tác INSERT chunk mới (chunk_id={test_chunk_id})...", flush=True)
        conn.execute(
            """
            INSERT INTO chunks (
                chunk_id, document_id, source_path, source_name, file_type,
                text, normalized_text, metadata_json, privacy_labels_json, retrievable
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_chunk_id,
                "test-doc-id",
                "test_path.xlsx",
                "test_path.xlsx",
                "xlsx",
                "生産履歴登録システムの更新テストデータです。",
                "生産履歴登録システムの更新テストデータです。",
                "{}",
                "[\"allowed\"]",
                1,
            ),
        )
        conn.commit()
        print("   -> INSERT THÀNH CÔNG! Không gặp lỗi trigger treo.", flush=True)

        # 2. UPDATE
        print(f"2. Thao tác UPDATE chunk vừa tạo (chunk_id={test_chunk_id})...", flush=True)
        conn.execute(
            "UPDATE chunks SET text = ?, normalized_text = ? WHERE chunk_id = ?",
            ("生産履歴登録システム_変更確認", "生産履歴登録システム_変更確認", test_chunk_id),
        )
        conn.commit()
        print("   -> UPDATE THÀNH CÔNG! Không gặp lỗi trigger treo.", flush=True)

        # 3. DELETE
        print(f"3. Thao tác DELETE chunk vừa tạo (chunk_id={test_chunk_id})...", flush=True)
        conn.execute("DELETE FROM chunks WHERE chunk_id = ?", (test_chunk_id,))
        conn.commit()
        print("   -> DELETE THÀNH CÔNG! Không gặp lỗi trigger treo.", flush=True)
        conn.close()

        print("\n--- BƯỚC 5: Kiểm tra cơ chế Fallback trong suốt khi mở chỉ mục Read-Only ---", flush=True)
        with LocalChunkIndex(copy_db, read_only=True) as index:
            print("Mở LocalChunkIndex thành công ở chế độ read_only=True.", flush=True)
            res = index.search_with_summary("生産履歴登録システム", limit=5)
            print(f"Kết quả truy vấn: tìm thấy {len(res.results)} chunks.", flush=True)
            assert len(res.results) > 0, "Truy vấn phải trả về kết quả qua đường LIKE fallback!"
            breakdown = dict(res.summary.lexical_breakdown_ms)
            print(f"Phân rã thời gian Lexical: {breakdown}", flush=True)
            assert breakdown.get("like_prefilter_ms", 0.0) > 0.0, "Phải kích hoạt like_prefilter_ms!"
            assert "trigram_match_ms" not in breakdown, "Không được có trigram_match_ms khi thiếu bảng!"
            print(f"Top-1 hit: doc_id={res.results[0].document_id}, chunk_id={res.results[0].chunk_id}", flush=True)
            print("   -> Cơ chế Fallback LIKE trong suốt hoạt động 100% hoàn hảo không lỗi!", flush=True)

        print("\n==================================================================", flush=True)
        print("KẾT LUẬN: Rollback ĐẠT CHUẨN 100% - KHÔNG CÒN TRIGGER TREO", flush=True)
        print("==================================================================", flush=True)
    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    run_rollback_verification()
