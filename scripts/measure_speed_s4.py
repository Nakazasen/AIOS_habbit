"""Script measuring CJK prefilter speed on the standard 13-query verification set.

Ticket: DESKTOP-QD-S4-REPORT-FIX-HOME
Measures:
- Trigram prefilter time (ms) on index with chunks_fts_trigram table
- LIKE prefilter time (ms) on DB copy with chunks_fts_trigram dropped
Runs multiple warm iterations per query to report stable, truthful measurements.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

os.environ["AIOS_RAGV2_LEXICAL_V2"] = "1"

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR / "src"))

from aios_habit.rag_v2.index import LocalChunkIndex, _CJK_RE
from aios_habit.rag_v2.query_planning import extract_content_terms

# The standard 13-query verification set (same as S1/S3/S3B)
QUERIES = [
    ("Q0662", "Các mục tham khảo số 13–16 có nominal và dung sai thế nào?", "lsu"),
    ("Q0680", "Phương pháp tính độ lệch trái–phải của LENS CO trong file là gì?", "lsu"),
    ("Q0685", "Bracketの測定値を見るだけで斜め光NG原因を確定できますか。", "lsu"),
    ("Q0693", "NanoScan比较后，需要重新Correlation的是哪台Jig？", "lsu"),
    ("Q0703", "B距離が長くなる想定状態は何ですか。", "lsu"),
    ("Q0707", "SIM tape được dán ở đâu, dày bao nhiêu và trình tự thao tác thế nào?", "lsu"),
    ("ALIAS_OKNG_XLSX", "Theo tài liệu OKNGUNITのCO_BRACKETの倒れ_傾き確認結果.xlsx kết quả kiểm tra thế nào?", "lsu"),
    ("ALIAS_OKNG_NOEXT", "Theo tài liệu OKNGUNITのCO_BRACKETの倒れ_傾き確認結果 kết quả kiểm tra thế nào?", "lsu"),
    ("ALIAS_YBEAM_PPTX", "Theo tài liệu Y_BeamH_Camera_140_to_bất_thường.pptx nguyên nhân là gì?", "lsu"),
    ("ALIAS_YBEAM_NOEXT", "Theo tài liệu Y_BeamH_Camera_140_to_bất_thường nguyên nhân là gì?", "lsu"),
    ("ALIAS_TT11", "Trong tài liệu 生産履歴登録システム_変更確認チェックリスト_20260914.xlsx, server mới (máy chủ Linux) có tên máy là gì?", "mom"),
    ("ALIAS_TANABAN", "Theo tài liệu TANABAN_Master.xlsx thông tin là gì?", "mom"),
    ("ALIAS_CTU0330", "Theo tài liệu CTUマップ再検討20260330.xlsx layout thế nào?", "mom"),
]


def measure_cjk_prefilter_speed() -> list[dict]:
    src = r"D:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\mom\library.sqlite"
    if not os.path.exists(src):
        src = r"D:\Sandbox\AIOS_index_split_new\mom\library.sqlite"

    tmp_dir = tempfile.mkdtemp(prefix="rag_speed_s4_")
    results = []

    try:
        # DB with trigram
        db_trigram = str(Path(tmp_dir) / "index_trigram.sqlite")
        shutil.copy2(src, db_trigram)
        idx_init = LocalChunkIndex(db_trigram, ensure_embeddings_on_open=False)
        idx_init.close()

        # DB without trigram (LIKE fallback copy)
        db_like = str(Path(tmp_dir) / "index_like.sqlite")
        shutil.copy2(db_trigram, db_like)
        conn = sqlite3.connect(db_like)
        conn.executescript("""
            DROP TRIGGER IF EXISTS chunks_fts_trigram_insert;
            DROP TRIGGER IF EXISTS chunks_fts_trigram_delete;
            DROP TRIGGER IF EXISTS chunks_fts_trigram_update;
            DROP TABLE IF EXISTS chunks_fts_trigram;
            VACUUM;
        """)
        conn.commit()
        conn.close()

        with LocalChunkIndex(db_trigram, read_only=True) as idx_tri, \
             LocalChunkIndex(db_like, read_only=True) as idx_lk:

            # Eligible IDs
            cur = idx_tri._conn.cursor()
            eligible_ids = [r[0] for r in cur.execute("SELECT chunk_id FROM chunks WHERE retrievable = 1").fetchall()]
            eligible_rows = idx_tri._fetch_chunk_rows(eligible_ids)

            print(f"Index corpus: {len(eligible_ids)} retrievable chunks.", flush=True)
            print("=" * 110, flush=True)
            print(f"{'QID':<18} | {'CJK':<5} | {'LIKE prefilter (Trước)':<24} | {'FTS5 Trigram (Sau)':<20} | {'Speedup':<10} | {'Đánh giá'}")
            print("=" * 110, flush=True)

            NUM_RUNS = 20

            for qid, qtext, domain in QUERIES:
                has_cjk = bool(_CJK_RE.search(qtext))
                terms = extract_content_terms(qtext)

                if not has_cjk:
                    res_item = {
                        "qid": qid,
                        "query": qtext,
                        "has_cjk": False,
                        "like_ms": 0.0,
                        "trigram_ms": 0.0,
                        "speedup": "N/A",
                        "note": "Non-CJK (Bỏ qua tiền lọc)",
                    }
                    results.append(res_item)
                    print(f"{qid:<18} | {'No':<5} | {'N/A (bypassed)':<24} | {'N/A (bypassed)':<20} | {'-':<10} | Non-CJK (Bỏ qua tiền lọc)", flush=True)
                    continue

                # Warmup
                for _ in range(3):
                    idx_tri._cjk_trigram_candidate_ids(terms, eligible_ids)
                    idx_lk._cjk_like_prefilter_ids(eligible_ids, terms)

                # Measure Trigram
                t0 = time.perf_counter()
                for _ in range(NUM_RUNS):
                    t_ids = idx_tri._cjk_trigram_candidate_ids(terms, eligible_ids)
                t_tri = ((time.perf_counter() - t0) / NUM_RUNS) * 1000.0

                # Measure LIKE
                t0 = time.perf_counter()
                for _ in range(NUM_RUNS):
                    l_ids = idx_lk._cjk_like_prefilter_ids(eligible_ids, terms)
                t_like = ((time.perf_counter() - t0) / NUM_RUNS) * 1000.0

                speedup = t_like / t_tri if t_tri > 0 else 1.0

                res_item = {
                    "qid": qid,
                    "query": qtext,
                    "has_cjk": True,
                    "like_ms": round(t_like, 2),
                    "trigram_ms": round(t_tri, 2),
                    "speedup": f"{speedup:.1f}x",
                    "note": f"Nhanh hơn {speedup:.1f} lần",
                }
                results.append(res_item)
                print(f"{qid:<18} | {'Yes':<5} | {t_like:>10.2f} ms{'':<12} | {t_tri:>10.2f} ms{'':<8} | {speedup:>7.1f}x   | Nhanh hơn {speedup:.1f} lần", flush=True)

        print("=" * 110, flush=True)
        cjk_items = [r for r in results if r["has_cjk"]]
        if cjk_items:
            avg_like = sum(r["like_ms"] for r in cjk_items) / len(cjk_items)
            avg_tri = sum(r["trigram_ms"] for r in cjk_items) / len(cjk_items)
            avg_speedup = avg_like / avg_tri if avg_tri > 0 else 1.0
            print(f"{'TRUNG BÌNH CJK':<18} | {len(cjk_items):>3} c | {avg_like:>10.2f} ms{'':<12} | {avg_tri:>10.2f} ms{'':<8} | {avg_speedup:>7.1f}x   | Nhanh hơn trung bình {avg_speedup:.1f} lần", flush=True)
            print("=" * 110, flush=True)

    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    return results


if __name__ == "__main__":
    measure_cjk_prefilter_speed()
