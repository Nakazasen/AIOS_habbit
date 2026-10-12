"""Script do phan bo thoi gian tung chang cua duong truy hoi tren khoi LSU.

Thuc hien theo Buoc 0 va Buoc 2 cua ve DESKTOP-RAG-NUMPY-COMPLETE-HOME:
- Do tren khoi lsu (chi muc tach khoi hien hanh)
- Bo cau co dinh = 4 cau cua dot quet khoi tri thuc (DESKTOP-KNOWLEDGE-BLOCK-QA-HOME) + 4 cau dau bo 50 cau LSU
- Do 5 chang:
  (a) Nhung cau hoi (embed query)
  (b) Quet dense (dense scan)
  (c) Quet sparse (sparse scan)
  (d) Cham lai / hop nhat / rerank (fuse / rerank)
  (e) Tong truy hoi (total retrieval)
- Chay toi thieu 2 luot moi cau (luot 1 lanh, luot 2 am)
- Xuat ket qua JSON va Markdown
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Ensure UTF-8 output
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from aios_habit.rag_v2.index import SearchOptions, fuse_ranked_channels
from aios_habit.rag_v2.pipeline import RagV2DevPipeline
from aios_habit.rag_v2.query_planning import coerce_query_plan
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceChatRagV2CanaryConfig,
    _pipeline_config,
)

QUESTIONS = [
    {
        "id": "KB-QA-1",
        "group": "Khoi tri thuc (LSU)",
        "question": "Ý nghĩa thông số DMT và PMT trong đo kiểm quang học Iris LSU là gì?",
    },
    {
        "id": "KB-QA-2",
        "group": "Khoi tri thuc (Dieu tra loi)",
        "question": "Mã lỗi C7620 trên dòng máy in Kyocera là lỗi gì, nguyên nhân và đối sách xử lý ra sao?",
    },
    {
        "id": "KB-QA-3",
        "group": "Khoi tri thuc (MOM)",
        "question": "Quy trình xuất kho qua AGV và liên kết với bảng staging oricon trong hệ thống MOM Opcenter như thế nào?",
    },
    {
        "id": "KB-QA-4",
        "group": "Khoi tri thuc (Tu dong/Mo ho)",
        "question": "Làm thế nào để kiểm tra và tối ưu hiệu suất làm việc hàng ngày của thiết bị?",
    },
    {
        "id": "LSU-50-Q0699",
        "group": "50 cau LSU (Q0699)",
        "question": "C7620中Magenta相对Black的副扫描色差达到多少会成为NG？",
    },
    {
        "id": "LSU-50-Q0700",
        "group": "50 cau LSU (Q0700)",
        "question": "C23とC24ではどのような発生Trendでしたか。",
    },
    {
        "id": "LSU-50-Q0703",
        "group": "50 cau LSU (Q0703)",
        "question": "B距離が長くなる想定状態は何ですか。",
    },
    {
        "id": "LSU-50-Q0708",
        "group": "50 cau LSU (Q0708)",
        "question": "光路高さ1.15 mmを超えると必ずCamera読取不能になりますか。",
    },
]


def run_measurement(tag: str = "before") -> dict:
    print(f"=== BAT DAU DO PHAN BO CHANG TRUY HOI (TAG: {tag}) ===")
    cfg = WorkspaceChatRagV2CanaryConfig.from_env()
    pipe_cfg = _pipeline_config(cfg, "bge_m3_hybrid", read_only=True, collection_id="lsu")
    pipeline = RagV2DevPipeline(pipe_cfg)
    options = SearchOptions()

    records = []

    for item in QUESTIONS:
        qid = item["id"]
        q_text = item["question"]
        group = item["group"]
        print(f"\nDang do [{qid}]: {q_text[:50]}...")

        plan = coerce_query_plan(q_text)

        # Luot 1 (Lanh cua cau hoi nay)
        t_start = time.perf_counter()
        _dvec = pipeline.embedding_backend.embed_query(plan.original_query)
        _svec = pipeline.index._sparse_backend.sparse_query(plan.original_query)
        t_emb_1 = (time.perf_counter() - t_start) * 1000.0

        t_start = time.perf_counter()
        dense_res_1 = pipeline.index.dense_candidates(plan, limit=100, options=options)
        t_dense_1 = (time.perf_counter() - t_start) * 1000.0

        t_start = time.perf_counter()
        sparse_res_1 = pipeline.index.sparse_candidates(plan, limit=100, options=options)
        t_sparse_1 = (time.perf_counter() - t_start) * 1000.0

        t_start = time.perf_counter()
        lexical_res_1 = pipeline.index.search_with_summary(plan, limit=100, options=options)
        fused_1 = fuse_ranked_channels(
            plan, lexical_res_1, dense_res_1, limit=10, options=options, sparse_results=sparse_res_1
        )
        t_fuse_1 = (time.perf_counter() - t_start) * 1000.0
        t_total_1 = t_emb_1 + t_dense_1 + t_sparse_1 + t_fuse_1

        # Luot 2 (Am cua cau hoi nay)
        t_start = time.perf_counter()
        _dvec = pipeline.embedding_backend.embed_query(plan.original_query)
        _svec = pipeline.index._sparse_backend.sparse_query(plan.original_query)
        t_emb_2 = (time.perf_counter() - t_start) * 1000.0

        t_start = time.perf_counter()
        dense_res_2 = pipeline.index.dense_candidates(plan, limit=100, options=options)
        t_dense_2 = (time.perf_counter() - t_start) * 1000.0

        t_start = time.perf_counter()
        sparse_res_2 = pipeline.index.sparse_candidates(plan, limit=100, options=options)
        t_sparse_2 = (time.perf_counter() - t_start) * 1000.0

        t_start = time.perf_counter()
        lexical_res_2 = pipeline.index.search_with_summary(plan, limit=100, options=options)
        fused_2 = fuse_ranked_channels(
            plan, lexical_res_2, dense_res_2, limit=10, options=options, sparse_results=sparse_res_2
        )
        t_fuse_2 = (time.perf_counter() - t_start) * 1000.0
        t_total_2 = t_emb_2 + t_dense_2 + t_sparse_2 + t_fuse_2

        top1_id = fused_2.results[0].chunk_id if fused_2.results else ""
        top1_score = fused_2.results[0].score if fused_2.results else 0.0

        rec = {
            "id": qid,
            "group": group,
            "question": q_text,
            "round_1_cold": {
                "nhung_ms": round(t_emb_1, 2),
                "dense_ms": round(t_dense_1, 2),
                "sparse_ms": round(t_sparse_1, 2),
                "fuse_ms": round(t_fuse_1, 2),
                "tong_ms": round(t_total_1, 2),
            },
            "round_2_warm": {
                "nhung_ms": round(t_emb_2, 2),
                "dense_ms": round(t_dense_2, 2),
                "sparse_ms": round(t_sparse_2, 2),
                "fuse_ms": round(t_fuse_2, 2),
                "tong_ms": round(t_total_2, 2),
            },
            "results_count": len(fused_2.results),
            "top1_chunk_id": top1_id,
            "top1_score": round(float(top1_score), 4),
        }
        records.append(rec)
        print(f"  L1 (lanh): nhung={t_emb_1:.1f}ms, dense={t_dense_1:.1f}ms, sparse={t_sparse_1:.1f}ms, fuse={t_fuse_1:.1f}ms -> tong={t_total_1:.1f}ms")
        print(f"  L2 (am):   nhung={t_emb_2:.1f}ms, dense={t_dense_2:.1f}ms, sparse={t_sparse_2:.1f}ms, fuse={t_fuse_2:.1f}ms -> tong={t_total_2:.1f}ms")

    output = {
        "tag": tag,
        "collection": "lsu",
        "index_path": str(pipe_cfg.index_path),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "records": records,
    }
    return output


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "before"
    res = run_measurement(tag)
    out_file = Path(f"docs/phieu-viec/ket-qua/stage-breakdown-{tag}.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"\nDa luu ket qua vao: {out_file}")
