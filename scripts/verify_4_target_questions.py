"""Verification script for all 4 Group (b) target questions + R2 PASS regression cross-check.

Ticket: DESKTOP-RAG-CHUNK-WINDOW-AND-EXCEL-EXPAND-FIX-HOME
Target Questions:
1. Q0685: Bracketの測定値を見るだけで斜め光NG原因を確定できますか。
   Target: OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx
   Expected Facts: '0.002', '0.015'
2. Q0684: NG UNIT与OK UNIT的Bracket测量值大致在哪个范围？
   Target: OKNGUNITのCO・BRACKETの倒れ・傾き確認結果.xlsx
   Expected Facts: '43.956～43.999', '44.030'
3. Q0706: SIM追加後のMagenta光路高さとC7620発生率はどうなりましたか。
   Target: Sirius 2 _ C7620_報告版 4.pptx (Slide 8)
   Expected Facts: '0.7 mm' or '0.7mm', '3/517'
4. TT08: Theo tài liệu Quy tắc chỉ thị số giá (wsc-6f049a1fdfc090dc7d439224.txt) khi lưu kho vào p-Rack tại Tầng 2 nhà C, đối với thùng ORICON có trọng lượng từ 10kg trở lên thì quy định đặt ở tầng mấy?
   Target: wsc-6f049a1fdfc090dc7d439224.txt
   Expected Facts: '10kg', 'tầng 1', 'ORICON'

Regression Cross-Check Questions (from R2 PASS):
- Q0700: C7620エラーの主な発生要因は何ですか。
- Q0703: C7620対策としてSIM追加以外に検討された内容はありますか。
"""
from dataclasses import replace
from pathlib import Path
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aios_habit.workspace_chat_rag_v2_adapter import (
    _pipeline_config,
    WorkspaceChatRagV2CanaryConfig,
)
from aios_habit.rag_v2.pipeline import RagV2DevPipeline
from aios_habit.rag_v2.query_planning import coerce_query_plan
from aios_habit import index_domain


def verify_target_question(
    qid: str,
    query: str,
    pipeline: RagV2DevPipeline,
    specs: list,
    target_doc_keyword: str,
    expected_facts: list[str],
) -> dict:
    print(f"\n{'='*70}", flush=True)
    print(f"VERIFYING [{qid}]: {query}", flush=True)
    print(f"Target document keyword: {target_doc_keyword}", flush=True)
    print(f"Expected facts: {expected_facts}", flush=True)
    print(f"{'='*70}", flush=True)

    t0 = time.perf_counter()
    res = pipeline.query(query, specs)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    pack = res.evidence_pack
    items = pack.items
    print(f"Total evidence pack items: {len(items)} (latency: {latency_ms:.1f}ms)", flush=True)

    matched_facts = {fact: False for fact in expected_facts}
    target_doc_found = False
    evidence_traces = []

    import unicodedata

    for idx, item in enumerate(items, 1):
        doc_name = item.source_name or ""
        doc_path = item.source_path or ""
        text = item.text or ""
        norm_text = unicodedata.normalize("NFKC", text)

        is_target_doc = (target_doc_keyword.lower() in doc_name.lower()) or (target_doc_keyword.lower() in doc_path.lower()) or (target_doc_keyword.lower() in item.document_id.lower())
        if is_target_doc:
            target_doc_found = True

        item_facts = []
        for fact in expected_facts:
            norm_fact = unicodedata.normalize("NFKC", fact)
            fact_variants = [fact, norm_fact]
            if " mm" in norm_fact:
                fact_variants.append(norm_fact.replace(" mm", "mm"))
            elif "mm" in norm_fact:
                fact_variants.append(norm_fact.replace("mm", " mm"))

            if any((fv in text) or (fv in norm_text) for fv in fact_variants):
                matched_facts[fact] = True
                item_facts.append(fact)

        fact_marker = f" [MATCHES: {item_facts}]" if item_facts else ""
        target_marker = " [TARGET DOC]" if is_target_doc else ""
        print(f"  Item #{idx} ({item.citation_id}) doc={doc_name} chunk={item.chunk_id[:16]}{target_marker}{fact_marker}", flush=True)
        print(f"    text snippet: {repr(text[:150])}", flush=True)

        evidence_traces.append({
            "rank": idx,
            "citation": item.citation_id,
            "chunk_id": item.chunk_id,
            "doc_name": doc_name,
            "text": text,
            "matched_facts": item_facts,
        })

    all_facts_passed = all(matched_facts.values())
    print(f"\n--- VERDICT [{qid}] ---", flush=True)
    print(f"Target doc matched in pack: {target_doc_found}", flush=True)
    print(f"Fact matching status: {matched_facts}", flush=True)
    print(f"RESULT: {'PASS' if (target_doc_found and all_facts_passed) else 'FAIL'}", flush=True)

    return {
        "qid": qid,
        "query": query,
        "target_doc_keyword": target_doc_keyword,
        "target_doc_found": target_doc_found,
        "expected_facts": expected_facts,
        "matched_facts": matched_facts,
        "passed": target_doc_found and all_facts_passed,
        "evidence_traces": evidence_traces,
    }


def main():
    print("==================================================================", flush=True)
    print("  DESKTOP-RAG-CHUNK-WINDOW-AND-EXCEL-EXPAND-FIX-HOME VERIFICATION  ", flush=True)
    print("==================================================================", flush=True)

    cfg = WorkspaceChatRagV2CanaryConfig.from_env()

    # Pipeline 1: LSU
    print("\n[1/2] Initializing LSU Pipeline...", flush=True)
    pipe_cfg_lsu = _pipeline_config(cfg, "bge_m3_hybrid", read_only=True, collection_id="lsu")
    pipeline_lsu = RagV2DevPipeline(pipe_cfg_lsu)
    specs_lsu = index_domain.get_specs_for_domain("lsu")
    print(f"LSU Pipeline ready with {len(specs_lsu)} specs.", flush=True)

    # Pipeline 2: Tri Thuc
    print("\n[2/2] Initializing Tri Thuc Pipeline...", flush=True)
    pipe_cfg_tt = _pipeline_config(cfg, "bge_m3_hybrid", read_only=True, collection_id="tri_thuc")
    pipeline_tt = RagV2DevPipeline(pipe_cfg_tt)
    specs_tt = index_domain.get_specs_for_domain("tri_thuc")
    print(f"Tri Thuc Pipeline ready with {len(specs_tt)} specs.", flush=True)

    results = []

    # Target 1: Q0685
    r_q0685 = verify_target_question(
        qid="Q0685",
        query="Bracketの測定値を見るだけで斜め光NG原因を確定できますか。",
        pipeline=pipeline_lsu,
        specs=specs_lsu,
        target_doc_keyword="OKNGUNIT",
        expected_facts=["0.002", "0.015"],
    )
    results.append(r_q0685)

    # Target 2: Q0684
    r_q0684 = verify_target_question(
        qid="Q0684",
        query="NG UNIT与OK UNIT的Bracket测量值大致在哪个范围？",
        pipeline=pipeline_lsu,
        specs=specs_lsu,
        target_doc_keyword="OKNGUNIT",
        expected_facts=["43.956", "44.03"],
    )
    results.append(r_q0684)

    # Target 3: Q0706
    r_q0706 = verify_target_question(
        qid="Q0706",
        query="SIM追加後のMagenta光路高さとC7620発生率はどうなりましたか。",
        pipeline=pipeline_lsu,
        specs=specs_lsu,
        target_doc_keyword="Sirius 2 _ C7620_報告版 4.pptx",
        expected_facts=["0.7 mm", "3/517"],
    )
    results.append(r_q0706)

    # Target 4: TT08
    r_tt08 = verify_target_question(
        qid="TT08",
        query="Theo tài liệu Quy tắc chỉ thị số giá (wsc-6f049a1fdfc090dc7d439224.txt) khi lưu kho vào p-Rack tại Tầng 2 nhà C, đối với thùng ORICON có trọng lượng từ 10kg trở lên thì quy định đặt ở tầng mấy?",
        pipeline=pipeline_tt,
        specs=specs_tt,
        target_doc_keyword="wsc-6f049a1fdfc090dc7d439224",
        expected_facts=["10kg", "tầng 1", "ORICON"],
    )
    results.append(r_tt08)

    # Regression Cross-Check on sample of PASS questions from R2
    print("\n" + "="*70, flush=True)
    print("RUNNING REGRESSION CROSS-CHECK ON SAMPLE PASS QUESTIONS FROM R2", flush=True)
    print("="*70, flush=True)

    r_q0700 = verify_target_question(
        qid="Q0700",
        query="C7620エラーの主な発生要因は何ですか。",
        pipeline=pipeline_lsu,
        specs=specs_lsu,
        target_doc_keyword="Sirius 2 _ C7620_報告版 4.pptx",
        expected_facts=["C7620"],
    )
    results.append(r_q0700)

    r_q0703 = verify_target_question(
        qid="Q0703",
        query="C7620対策としてSIM追加以外に検討された内容はありますか。",
        pipeline=pipeline_lsu,
        specs=specs_lsu,
        target_doc_keyword="Sirius 2 _ C7620_報告版 4.pptx",
        expected_facts=["SIM"],
    )
    results.append(r_q0703)

    print("\n" + "="*70, flush=True)
    print("SUMMARY OF ALL VERIFICATION TESTS", flush=True)
    print("="*70, flush=True)
    all_target_passed = True
    for r in results:
        status_str = "PASS" if r["passed"] else "FAIL"
        print(f"[{status_str}] {r['qid']}: {r['query'][:50]}... | Target Doc: {r['target_doc_found']} | Facts: {r['matched_facts']}")
        if not r["passed"]:
            all_target_passed = False

    print(f"\nOVERALL RESULT: {'ALL TESTS PASSED 100%' if all_target_passed else 'SOME TESTS FAILED'}", flush=True)


if __name__ == "__main__":
    main()
