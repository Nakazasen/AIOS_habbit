import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(r"D:\Sandbox\AIOS_habbit")
sys.path.insert(0, str(REPO_ROOT / "src"))

from aios_habit.workspace_chat_rag_v2_adapter import (
    _pipeline_config,
    WorkspaceChatRagV2CanaryConfig,
)
from aios_habit.rag_v2.pipeline import (
    RagV2DevPipeline,
    _balance_lsu_machine_series,
)
from aios_habit.rag_v2.query_planning import coerce_query_plan
from aios_habit.rag_v2.evidence import build_evidence_pack, EvidencePackConfig
from aios_habit import index_domain

cfg = WorkspaceChatRagV2CanaryConfig.from_env()

print("=" * 80)
print("VERIFICATION OF THE THREE CASES (DESKTOP-SERIAL-DISAMBIGUATION-EXACT-ROUTING-FIX-HOME)")
print("=" * 80)

# CASE 1: DTL19
print("\n--- CASE 1: DTL19 ---")
q_dtl19 = (
    "Trong báo cáo điều tra lỗi Không lên nguồn.xlsx trên máy Iris2024 "
    "(số hiệu 05-0469, Serial J3C0053Y4242), cụm nguồn UNIT LOW VOLTAGE "
    "bị lỗi có mã linh kiện và nhà cung cấp là gì?"
)
matched_dtl19, missing_dtl19 = index_domain.match_named_documents(q_dtl19)
print(f"Matched documents count: {len(matched_dtl19)}, missing: {missing_dtl19}")
for i, m in enumerate(matched_dtl19, 1):
    fn = getattr(m.path, "name", str(m))
    doc_id = getattr(m, "document_id", "")
    print(f"  Rank #{i}: {fn} (id={doc_id})")

dtl19_rank1_ok = False
if matched_dtl19:
    top_name = getattr(matched_dtl19[0].path, "name", str(matched_dtl19[0]))
    if "05-0469" in top_name and "Không lên nguồn.xlsx" in top_name:
        dtl19_rank1_ok = True
print(f"-> DTL19 PASS (Rank 1 matches KTD-2025-05-0469): {dtl19_rank1_ok}")

# CASE 2: Q0704
print("\n--- CASE 2: Q0704 ---")
q_0704 = (
    "Trong file Sirius 2 _ C7620_報告版 4.pptx, vào đợt bảo dưỡng khuôn ngày 14/2 "
    "thì màu nào (Magenta hay Black hay Cyan hay Yellow) có sự thay đổi kích thước Housing lớn nhất?"
)
pipe_cfg_lsu = _pipeline_config(cfg, "bge_m3_hybrid", read_only=True, collection_id="lsu")
pipeline_lsu = RagV2DevPipeline(pipe_cfg_lsu)

plan_0704 = coerce_query_plan(q_0704)
resp_0704 = pipeline_lsu.index.hybrid_search_with_summary(plan_0704, limit=30)
resp_bal_0704 = _balance_lsu_machine_series(plan_0704, resp_0704, is_lsu=True)

ev_cfg = EvidencePackConfig(
    max_items=5,
    per_document_limit=2,
    min_semantic_support_score=0.0,
    min_top_score=0.0,
    min_final_evidence_term_coverage=0.0,
    min_term_coverage=0.0,
)
pack_0704 = build_evidence_pack(plan_0704, resp_bal_0704, config=ev_cfg)

target_0704 = "Sirius 2 _ C7620_報告版 4.pptx"
q0704_ev_ranks = []
for i, item in enumerate(pack_0704.items, 1):
    is_t = target_0704.lower() in (item.source_name or "").lower()
    tag = "[TARGET]" if is_t else "        "
    print(f"  Item #{i}: {tag} {item.source_name} | {item.chunk_id[:16]}")
    if is_t:
        q0704_ev_ranks.append(i)

q0704_top3_ok = any(r <= 3 for r in q0704_ev_ranks)
print(f"-> Q0704 PASS (Target doc in Evidence Top 3): {q0704_top3_ok} (ranks: {q0704_ev_ranks})")

# CASE 3: Q1827
print("\n--- CASE 3: Q1827 ---")
q_1827 = "Các cột `-8` đến `-3` và `+2` đến `+8` ghi `--`; phải xử lý thế nào?"
targets_1827 = [
    "2026_08_magenta_profile.csv",
    "2026_08_error_bowoveradjust.csv",
    "sirius 2 _ c7620_報告版 4.pptx",
]

plan_1827 = coerce_query_plan(q_1827)
print(f"Q1827 plan variants: {len(plan_1827.variants)}")
for v in plan_1827.variants:
    print(f"  Variant: origin={v.origin}, facet={v.facet_id}, text={repr(v.text)}")
print(f"Q1827 content terms: {plan_1827.content_terms}")

resp_1827 = pipeline_lsu.index.hybrid_search_with_summary(plan_1827, limit=30)
resp_bal_1827 = _balance_lsu_machine_series(plan_1827, resp_1827, is_lsu=True)
pack_1827 = build_evidence_pack(plan_1827, resp_bal_1827, config=ev_cfg)

q1827_ev_ranks = []
for i, item in enumerate(pack_1827.items, 1):
    is_t = any(td in (item.source_name or "").lower() for td in targets_1827)
    tag = "[TARGET]" if is_t else "        "
    print(f"  Item #{i}: {tag} {item.source_name} | {item.chunk_id[:16]}")
    if is_t:
        q1827_ev_ranks.append(i)

q1827_top3_ok = any(r <= 3 for r in q1827_ev_ranks)
print(f"-> Q1827 PASS (Target doc in Evidence Top 3): {q1827_top3_ok} (ranks: {q1827_ev_ranks})")

print("\n" + "=" * 80)
print(f"FINAL QUALITY GATES:")
print(f"  DTL19 Rank 1 Match: {'PASS' if dtl19_rank1_ok else 'FAIL'}")
print(f"  Q0704 Top 3 Evidence: {'PASS' if q0704_top3_ok else 'FAIL'}")
print(f"  Q1827 Top 3 Evidence: {'PASS' if q1827_top3_ok else 'FAIL'}")
print("=" * 80)
