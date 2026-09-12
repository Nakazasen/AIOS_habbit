#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BQ01-BQ10: BGE-M3 hybrid retrieval + Gemini Web polish (no C-AGENT).

Answers stay in local_runs/. Never writes docs/reports or raw corpus to git.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import aios_habit.workspace_chat_rag_v2_adapter as adapter
from aios_habit.antigravity_bridge import (
    call_antigravity_bridge,
    ensure_antigravity_bridge_running,
)
from aios_habit.brain_gateway import SanitizedRouterPayload, SanitizedSourcePayload
from aios_habit.rag_v2.multilingual_query_expand import expand_question_for_corpus_script
from aios_habit.rag_v2.pipeline import RagV2DevConfig, SourceSpec
from aios_habit.rag_v2.script_family import corpus_needs_cjk_query_expansion
from aios_habit.workspace_chat_router_adapter import generate_answer_via_router_detailed

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
]

SYSTEM_PROMPT = (
    "Bạn là trợ lý tài liệu nhà máy trong Workspace Chat.\n"
    "Chỉ dùng các đoạn bằng chứng được cung cấp. Mỗi khẳng định phải kèm citation [1], [2], ...\n"
    "Không bịa số liệu, tên file, hay bước quy trình không có trong bằng chứng.\n"
    "Nếu thiếu ý, ghi rõ ý nào chưa có bằng chứng.\n"
    "Trả lời tiếng Việt, rõ, theo mục; câu nhiều vế thì trả lời hết từng vế."
)

STAGE_MANIFEST = (
    PROJECT_ROOT
    / "local_runs/battle_workspace_stage_cache"
    / "00bb0a09c398d09dfcc9331e2f03bdfbfd130fd1e40e827228eec740d1558074"
    / "workspace_stage_manifest.json"
)
DEPLOYMENT = PROJECT_ROOT / "config/workspace_chat_rag_v2.local.json"
OUT_DIR = PROJECT_ROOT / "local_runs" / "bq10_polished_expand5"


def _pack_context(items: list[dict], names: dict[str, str]) -> str:
    blocks = []
    for item in items[:12]:
        doc_id = str(item.get("document_id") or "")
        title = names.get(doc_id, doc_id)
        label = item.get("citation_id") or "?"
        text = str(item.get("text") or "")[:1600]
        blocks.append(f"[{label}] {title}\n{text}")
    return "\n\n".join(blocks)


def _polish_gemini(question: str, context: str):
    started = time.time()
    response = call_antigravity_bridge(
        question=question,
        system_prompt=SYSTEM_PROMPT,
        context_text=context,
        privacy_mode="cloud_allowed",
        answer_language="vi",
        timeout_seconds=180,
    )
    return {
        "ok": bool(response.ok and response.answer_text.strip()),
        "answer": response.answer_text.strip(),
        "error": response.error_message,
        "model": response.model,
        "provider": "gemini_web",
        "latency_sec": round((time.time() - started), 2),
    }


def _polish_nakazasen(question: str, items: list[dict], names: dict[str, str]):
    started = time.time()
    sources = tuple(
        SanitizedSourcePayload(
            source_id=str(item.get("document_id") or index),
            source_scope="notebook",
            source_type="txt",
            title=f"[{item.get('citation_id')}] {names.get(str(item.get('document_id') or ''), item.get('document_id'))}",
            text=str(item.get("text") or "")[:1600],
            privacy_label="cloud_safe",
        )
        for index, item in enumerate(items[:12], start=1)
    )
    payload = SanitizedRouterPayload(
        sanitized_question=question,
        sanitized_sources=sources,
        metadata={"task_type": "workspace_chat", "polished_bq10": True},
    )
    detailed = generate_answer_via_router_detailed(payload)
    return {
        "ok": bool(detailed.ok and detailed.text.strip()),
        "answer": detailed.text.strip(),
        "error": "" if detailed.ok else detailed.text,
        "model": detailed.route.effective_model,
        "provider": detailed.route.effective_provider or "nakazasen_router",
        "latency_sec": round((time.time() - started), 2),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=== BQ01-BQ10 polished (BGE-M3 hybrid + Gemini Web, Nakazasen fallback) ===", flush=True)

    sidecar = ensure_antigravity_bridge_running()
    gemini_ready = bool(sidecar.ok and sidecar.health.is_direct_ready)
    print(f"Gemini Web sidecar: ready={gemini_ready} status={sidecar.health.status}", flush=True)

    with STAGE_MANIFEST.open(encoding="utf-8") as handle:
        stage_data = json.load(handle)
    db_path = Path(stage_data["index_path"])
    conn = sqlite3.connect(db_path)
    distinct_docs = conn.execute(
        "SELECT DISTINCT document_id, source_path, source_name FROM chunks"
    ).fetchall()
    sample_heads = conn.execute(
        "SELECT source_name, substr(text, 1, 160) FROM chunks WHERE retrievable = 1 LIMIT 80"
    ).fetchall()
    conn.close()
    sources = [
        SourceSpec(path=Path(row[1]), document_id=row[0], source_id=row[0], owner_consent=True)
        for row in distinct_docs
    ]
    print(f"Index documents: {len(sources)}", flush=True)

    deployment = adapter.load_workspace_chat_rag_v2_deployment(
        DEPLOYMENT, allow_unsealed_diagnostic=True
    )
    pipe_cfg = RagV2DevConfig(
        runtime_root=db_path.parent,
        index_filename=db_path.name,
        retrieval_profile="bge_m3_hybrid",
        bge_m3_model_path=deployment.model_path,
        bge_m3_model_revision=deployment.model_revision,
        bge_m3_model_checksum=deployment.model_checksum,
        retrieval_device="cpu",
        ensure_embeddings_on_open=False,
        index_read_only=True,
    )
    print("init BGE worker (read-only; FTS all chunks + dense on existing vectors)", flush=True)
    adapter._SUBPROCESS_CLIENT.initialize_worker(pipe_cfg, timeout_s=300.0)
    names = {str(row[0]): str(row[2] or row[0]) for row in distinct_docs}
    sample_texts = [f"{row[0] or ''}\n{row[1] or ''}" for row in sample_heads]
    corpus_script = (
        "cjk"
        if corpus_needs_cjk_query_expansion(
            "What is the overall system architecture?",
            sample_texts,
        )
        else "latin"
    )
    print(f"corpus_script={corpus_script}", flush=True)

    results = []
    for index, item in enumerate(QUESTIONS, start=1):
        qid = item["id"]
        question = item["question"]
        print(f"\n[{index}/10] {qid} {question}", flush=True)
        expansion = expand_question_for_corpus_script(
            question,
            corpus_script=corpus_script,
            gemini_ready=gemini_ready,
        )
        variant_preview = []
        if expansion:
            variant_preview = [row.get("text") for row in expansion.get("variants") or []]
        print(f"  expand {variant_preview}", flush=True)
        t0 = time.time()
        query_res = adapter._SUBPROCESS_CLIENT.query_ready(
            question,
            sources,
            pipe_cfg,
            expansion=expansion,
            timeout_s=90.0,
        )
        pack_items = list(query_res.get("items") or [])
        retrieval_s = round(time.time() - t0, 2)
        cited = sorted(
            {
                names.get(str(entry.get("document_id") or ""), str(entry.get("document_id") or ""))
                for entry in pack_items
            }
        )
        print(f"  retrieval {retrieval_s}s | {len(pack_items)} chunks / {len(cited)} docs", flush=True)

        context = _pack_context(pack_items, names)
        polish = {"ok": False, "answer": "", "error": "no_provider", "provider": "", "model": "", "latency_sec": 0}
        if gemini_ready:
            polish = _polish_gemini(question, context)
            if not polish["ok"]:
                print(f"  Gemini fail: {polish['error'][:180]}", flush=True)
                polish = _polish_nakazasen(question, pack_items, names)
        else:
            polish = _polish_nakazasen(question, pack_items, names)

        print(
            f"  polish {polish['provider']} {polish['latency_sec']}s ok={polish['ok']}",
            flush=True,
        )
        preview = (polish["answer"] or polish["error"] or "")[:160].replace("\n", " ")
        print(f"  preview: {preview}", flush=True)

        results.append(
            {
                "id": qid,
                "category": item["category"],
                "question": question,
                "retrieval_time_sec": retrieval_s,
                "chunks_count": len(pack_items),
                "expansion_variants": variant_preview,
                "cited_sources": cited,
                "polish_ok": polish["ok"],
                "polish_provider": polish["provider"],
                "polish_model": polish["model"],
                "polish_latency_sec": polish["latency_sec"],
                "error": polish["error"],
                "answer": polish["answer"],
            }
        )
        (OUT_DIR / f"{qid}.json").write_text(
            json.dumps(results[-1], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    (OUT_DIR / "bq10_polished.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# BQ01–BQ10 — BGE-M3 Hybrid + Gemini/Nakazasen (bản chau chuốt)",
        "",
        f"Thời gian: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "C-AGENT không dùng. Artifact local_runs/bq10_polished/ — không commit.",
        "",
    ]
    for row in results:
        lines.append(f"## {row['id']} — {row['question']}")
        lines.append("")
        lines.append(
            f"- Tìm: {row['retrieval_time_sec']}s, {row['chunks_count']} đoạn / {len(row['cited_sources'])} tài liệu"
        )
        lines.append(
            f"- Viết: {row['polish_provider']} `{row['polish_model']}` {row['polish_latency_sec']}s ok={row['polish_ok']}"
        )
        lines.append("")
        lines.append(row["answer"] or f"(lỗi) {row['error']}")
        lines.append("")
    (OUT_DIR / "bq10_polished.md").write_text("\n".join(lines), encoding="utf-8")
    ok_count = sum(1 for row in results if row["polish_ok"])
    print(f"\nDONE {ok_count}/10 polished. {OUT_DIR / 'bq10_polished.md'}", flush=True)
    return 0 if ok_count == 10 else 2


if __name__ == "__main__":
    raise SystemExit(main())
