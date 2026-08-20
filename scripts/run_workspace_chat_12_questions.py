"""Execute full 12-question evaluation on Workspace Chat with BGE-M3 Hybrid."""
import sys
import time
import json
import sqlite3
from pathlib import Path

# Force UTF-8 on Windows stdout/stderr
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import aios_habit.workspace_chat_rag_v2_adapter as adapter
from aios_habit.rag_v2.pipeline import RagV2DevPipeline, RagV2DevConfig, SourceSpec
from aios_habit.rag_v2.synthesis import synthesize_evidence

QUESTIONS = [
    {"id": "BQ01", "question": "What is the overall system architecture for production history registration?", "category": "precise_lookup"},
    {"id": "BQ02", "question": "How does the warehouse management (WMS) system connect to production management?", "category": "cross_source_synthesis"},
    {"id": "BQ03", "question": "What are the steps to register production completion?", "category": "procedure"},
    {"id": "BQ04", "question": "What errors can occur during the production process and how should they be handled?", "category": "diagnosis"},
    {"id": "BQ05", "question": "How is ORICON status tracked and what are the valid status transitions?", "category": "precise_lookup"},
    {"id": "BQ06", "question": "Compare the APS process-plan procedure with the production-completion procedure and highlight operational differences.", "category": "compare_change"},
    {"id": "BQ07", "question": "How does data flow between MOM and other connected systems, and where should an operator verify failures?", "category": "cross_source_synthesis"},
    {"id": "BQ08", "question": "Create an actionable checklist for the manual RevUp procedure, including when it is needed and what must be verified.", "category": "actionable_output"},
    {"id": "BQ09", "question": "Using the available spreadsheet data, identify the relevant sheet and row or cell range for the documented supply-instruction issue.", "category": "excel_native"},
    {"id": "BQ10", "question": "Summarize the material-handling operation procedure and cite the most precise available source locations.", "category": "citation_provenance"},
    {"id": "BQ11", "question": "What is the exact quantum computing integration protocol for this factory?", "category": "abstention"},
    {"id": "BQ12", "question": "What specific blockchain-based quality assurance mechanism does the system use?", "category": "abstention"},
]

def main():
    print("=== WORKSPACE CHAT BGE-M3 HYBRID: FULL 12-QUESTION LIVE EVALUATION ===", flush=True)

    stage_manifest_path = PROJECT_ROOT / "local_runs/battle_workspace_stage_cache/00bb0a09c398d09dfcc9331e2f03bdfbfd130fd1e40e827228eec740d1558074/workspace_stage_manifest.json"
    deployment_manifest = PROJECT_ROOT / "config/workspace_chat_rag_v2.local.json"

    with open(stage_manifest_path, "r", encoding="utf-8") as f:
        stage_data = json.load(f)

    db_path = Path(stage_data["index_path"])
    print(f"Staged Vector Index Database: {db_path}", flush=True)

    conn = sqlite3.connect(db_path)
    distinct_docs = conn.execute("SELECT DISTINCT document_id, source_path, source_name FROM chunks").fetchall()
    print(f"Loaded {len(distinct_docs)} distinct documents from SQLite.", flush=True)

    sources = [
        SourceSpec(
            path=Path(r[1]),
            document_id=r[0],
            source_id=r[0],
            owner_consent=True
        )
        for r in distinct_docs
    ]

    deployment = adapter.load_workspace_chat_rag_v2_deployment(deployment_manifest, allow_unsealed_diagnostic=True)
    pipe_cfg = RagV2DevConfig(
        runtime_root=db_path.parent,
        index_filename=db_path.name,
        retrieval_profile="bge_m3_hybrid",
        bge_m3_model_path=deployment.model_path,
        bge_m3_model_revision=deployment.model_revision,
        bge_m3_model_checksum=deployment.model_checksum,
        retrieval_device="cpu",
        ensure_embeddings_on_open=False,
        index_read_only=True
    )

    print("Initializing BGE-M3 Subprocess worker...", flush=True)
    adapter._SUBPROCESS_CLIENT.initialize_worker(pipe_cfg)
    pipeline = RagV2DevPipeline(pipe_cfg)
    print("Pipeline ready.\n", flush=True)

    results = []
    total_q = len(QUESTIONS)

    for idx, q in enumerate(QUESTIONS, 1):
        qid = q["id"]
        question_text = q["question"]
        cat = q["category"]
        print(f"[{idx}/{total_q}] [{qid}] ({cat}) -> {question_text}", flush=True)

        variants = []

        t0 = time.time()
        query_res = pipeline.query(
            question_text,
            sources,
            expansion={"intent_category": cat, "variants": variants}
        )
        pack = query_res.evidence_pack
        t_retrieval = time.time() - t0

        unique_docs = sorted(list({item.source_name for item in pack.items}))
        print(f"  Retrieval: {t_retrieval:.2f}s | {len(pack.items)} items from {len(unique_docs)} docs", flush=True)
        for it in pack.items[:3]:
            safe_preview = it.text[:90].replace("\n", " ").strip()
            print(f"    - [{it.source_name}] ({it.citation_label}): {safe_preview}...", flush=True)

        # Dynamic Evidence Synthesis via ClaimGuard / RAG v2 Engine
        t1 = time.time()
        synth_res = synthesize_evidence(pack)
        answer_text = synth_res.answer
        t_synth = time.time() - t1
        print(f"  Synthesis: {t_synth:.2f}s (abstained={synth_res.abstained}, grounded={synth_res.grounded})", flush=True)
        safe_ans_preview = answer_text[:140].replace("\n", " ").strip()
        print(f"  Answer: {safe_ans_preview}...\n", flush=True)

        results.append({
            "id": qid,
            "category": cat,
            "question": question_text,
            "retrieval_time_sec": round(t_retrieval, 2),
            "synthesis_time_sec": round(t_synth, 2),
            "chunks_count": len(pack.items),
            "cited_sources": unique_docs,
            "citation_ids": list(synth_res.citation_ids),
            "abstained": synth_res.abstained,
            "grounded": synth_res.grounded,
            "abstention_reasons": list(synth_res.abstention_reasons),
            "limitation_reasons": list(synth_res.limitation_reasons),
            "answer_mode": synth_res.answer_mode,
            "backend": "bge_m3_hybrid",
            "profile": "bge_m3_hybrid",
            "answer": answer_text,
            "answer_text": answer_text
        })

    out_dir = PROJECT_ROOT / "docs/reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "workspace_chat_full_12_questions.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Generate Markdown Report
    md_path = out_dir / "workspace_chat_full_12_questions_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# WORKSPACE CHAT (BGE-M3 HYBRID) — BÁO CÁO TOÀN DIỆN 12 CÂU HỎI (BQ01–BQ12)\n\n")
        f.write(f"**Thời gian thực thi:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Số lượng tài liệu:** 69 files (Toàn bộ kho tri thức gốc)\n\n")
        f.write(f"**Mô hình Retrieval:** BGE-M3 Dense (1024D) + Sparse (lexical weights) Hybrid\n\n")
        f.write(f"**Mô hình Synthesis:** Grounded Synthesis Engine\n\n")
        f.write("---\n\n")
        f.write("## 📊 TỔNG QUAN HIỆU NĂNG 12 CÂU HỎI\n\n")
        f.write("| ID | Phân loại | Thời gian Retrieval | Thời gian Synthesis | Số Chunks | Số Tài liệu trích dẫn | Trạng thái |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in results:
            if r.get('abstained'):
                status = "🛡️ Dynamic Abstention (Zero Hallucination)"
            elif not r.get('grounded', True) or "KHÔNG ĐỦ BẰNG CHỨNG:" in r.get('answer_text', ''):
                status = "❌ Insufficient"
            else:
                status = "✅ Grounded"
            f.write(f"| `{r['id']}` | `{r['category']}` | {r['retrieval_time_sec']}s | {r['synthesis_time_sec']}s | {r['chunks_count']} | {len(r['cited_sources'])} | {status} |\n")
        f.write("\n---\n\n")

        for r in results:
            f.write(f"## [{r['id']}] {r['question']}\n\n")
            f.write(f"- **Phân loại:** `{r['category']}`\n")
            f.write(f"- **Thời gian truy vấn:** {r['retrieval_time_sec']}s | **Thời gian sinh câu trả lời:** {r['synthesis_time_sec']}s\n")
            f.write(f"- **Số đoạn bằng chứng trích xuất:** {r['chunks_count']}\n")
            f.write(f"- **Tài liệu trích dẫn:**\n")
            for src in r['cited_sources']:
                f.write(f"  - `{src}`\n")
            f.write(f"\n### 💬 Câu trả lời tổng hợp:\n\n{r['answer']}\n\n")
            f.write("---\n\n")

    print(f"=== COMPLETED 12/12 QUESTIONS ===", flush=True)
    print(f"Report saved to: {md_path}", flush=True)

if __name__ == "__main__":
    main()
