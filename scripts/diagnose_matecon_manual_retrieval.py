#!/usr/bin/env python3
"""Read-only evidence check for the Matecon ACR/CTU manual-mode question.

The tool uses an already staged Workspace Chat index.  It never ingests,
rewrites, or activates a deployment.  Its output is intentionally limited to
retrieval metadata and source snippets so an operator can prove whether the
manual chapter was found before asking a cloud answer provider to synthesize.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aios_habit.rag_v2.index import _rerank_hybrid_window, _select_hybrid_results
from aios_habit.rag_v2.pipeline import (
    HybridRankingConfig,
    RagV2DevConfig,
    RagV2DevPipeline,
    SearchOptions,
    SourceSpec,
    _file_fingerprint,
    coerce_query_plan,
)
from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceChatRagV2CanaryConfig,
    close_workspace_chat_rag_v2_runtimes,
    prepare_workspace_chat_sources,
    retrieve_workspace_chat_evidence,
)
from aios_habit.workspace_chat_rag_v2_deployment import (
    EXPECTED_MODEL_CHECKSUM,
    EXPECTED_MODEL_REVISION,
    EXPECTED_RERANKER_CHECKSUM,
    EXPECTED_RERANKER_REVISION,
)

DEFAULT_STAGE_ROOT = PROJECT_ROOT / (
    "local_runs/battle_workspace_stage_cache/"
    "00bb0a09c398d09dfcc9331e2f03bdfbfd130fd1e40e827228eec740d1558074"
)
DEFAULT_SOURCE_ID = "wsc-c38f9bb5c6637fc5ba7c45ec"
DEFAULT_DIAGNOSTIC_RUNTIME = PROJECT_ROOT / "local_runs/matecon_semantic_diagnostic"
DEFAULT_QUESTION = "Chế độ Manual Matecon ACR/CTU hoạt động như thế nào?"


def _result_summary(result) -> dict[str, object]:
    return {
        "reranker_requested": result.reranker_requested,
        "reranker_applied": result.reranker_applied,
        "effective_path": result.effective_path,
        "degraded": result.degraded,
        "degraded_reason": result.degraded_reason,
        "candidate_count": result.search_response.summary.candidate_count,
        "returned_count": result.search_response.summary.returned_count,
        "evidence": [
            {
                "chunk_id": item.chunk_id,
                "score": round(item.score, 6),
                "text": item.text[:500],
            }
            for item in result.search_response.results
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-root", type=Path, default=DEFAULT_STAGE_ROOT)
    parser.add_argument("--source-id", default=DEFAULT_SOURCE_ID)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--with-reranker", action="store_true")
    parser.add_argument(
        "--rerank-limit", type=int, default=10,
        help="Bound the rerank window; 10 is the validated CPU-safe default.",
    )
    parser.add_argument(
        "--debug-reranker",
        action="store_true",
        help="Score the retrieved evidence directly and expose only safe exception metadata.",
    )
    parser.add_argument(
        "--prepare-diagnostic-runtime",
        action="store_true",
        help=(
            "Build and query an isolated, local-only Workspace runtime for this "
            "one manual. This never activates or changes the production manifest."
        ),
    )
    parser.add_argument(
        "--diagnostic-runtime-root",
        type=Path,
        default=DEFAULT_DIAGNOSTIC_RUNTIME,
        help="Dedicated runtime used only with --prepare-diagnostic-runtime.",
    )
    args = parser.parse_args()
    if not 1 <= args.rerank_limit <= 15:
        parser.error("--rerank-limit must be between 1 and 15")

    source = args.stage_root / "materialized_sources" / f"{args.source_id}.txt"
    index = args.stage_root / "bge_m3_hybrid" / "workspace_chat.sqlite"
    if not source.is_file():
        print(json.dumps({"status": "BLOCKED", "reason": "staged_source_or_index_missing"}))
        return 1

    if args.prepare_diagnostic_runtime:
        if args.debug_reranker:
            print(json.dumps({"status": "BLOCKED", "reason": "debug_reranker_not_supported_with_preparation"}))
            return 1
        runtime_root = args.diagnostic_runtime_root.resolve()
        # This uses the exact extracted manual bytes, but never reuses or
        # modifies the app runtime. It is proof of the local retrieval path,
        # not a deployment activation or provider-synthesis operation.
        text = source.read_text(encoding="utf-8")
        workspace_source = WorkspaceAIContextSource(
            source_id="matecon-manual-diagnostic",
            source_scope="local_diagnostic",
            source_type="txt",
            title="Matecon Manual diagnostic source",
            privacy_label="local_only",
            text=text,
            included_chars=len(text),
            truncated=False,
        )
        config = WorkspaceChatRagV2CanaryConfig(
            enabled=True,
            requested_profile="bge_m3_hybrid",
            runtime_root=runtime_root,
            bge_m3_model_path=PROJECT_ROOT / "local_runs/retrieval_models/bge-m3-5617a9f",
            bge_m3_model_revision=EXPECTED_MODEL_REVISION,
            bge_m3_model_checksum=EXPECTED_MODEL_CHECKSUM,
            bge_reranker_model_path=(
                PROJECT_ROOT / "local_runs/retrieval_models/bge-reranker-v2-m3"
                if args.with_reranker else None
            ),
            bge_reranker_model_revision=(
                EXPECTED_RERANKER_REVISION if args.with_reranker else ""
            ),
            bge_reranker_model_checksum=(
                EXPECTED_RERANKER_CHECKSUM if args.with_reranker else ""
            ),
            adaptive_enabled=bool(args.with_reranker),
            retrieval_device="cpu",
            deep_rerank_limit=args.rerank_limit,
        )
        try:
            preparation = prepare_workspace_chat_sources(
                (workspace_source,), config=config, source_timeout_s=300.0,
            )
            result = retrieve_workspace_chat_evidence(
                args.question,
                (workspace_source,),
                config=config,
                search_preference="deep" if args.with_reranker else "auto",
            )
            telemetry = result.get("rag_v2_canary", {})
            output = {
                "status": "OK" if result.get("retrieval_applied") else "BLOCKED",
                "mode": "isolated_local_workspace_diagnostic",
                "production_activation_changed": False,
                "provider_synthesis_used": False,
                "preparation": {
                    "prepared_count": preparation.get("prepared_count", 0),
                    "indexed_chunk_count": preparation.get("report", {}).get("indexed_chunk_count", 0),
                },
                "retrieval_applied": bool(result.get("retrieval_applied")),
                "summary_count": int(result.get("summary_count", 0)),
                "effective_profile": telemetry.get("effective_profile"),
                "reranker_requested": telemetry.get("reranker_requested"),
                "reranker_applied": telemetry.get("reranker_applied"),
                "degraded": telemetry.get("degraded"),
                "degraded_reason": telemetry.get("degraded_reason"),
                "evidence": [
                    {"text": str(item.get("text", ""))[:500]}
                    for item in result.get("evidence_items", [])
                ],
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0 if output["status"] == "OK" else 1
        finally:
            close_workspace_chat_rag_v2_runtimes()

    if not index.is_file():
        print(json.dumps({"status": "BLOCKED", "reason": "staged_source_or_index_missing"}))
        return 1

    config = RagV2DevConfig(
        runtime_root=index.parent,
        index_filename=index.name,
        index_read_only=True,
        ensure_embeddings_on_open=False,
        retrieval_profile="bge_m3_hybrid",
        strict_semantic=True,
        bge_m3_model_path=PROJECT_ROOT / "local_runs/retrieval_models/bge-m3-5617a9f",
        bge_m3_model_revision=EXPECTED_MODEL_REVISION,
        bge_m3_model_checksum=EXPECTED_MODEL_CHECKSUM,
        bge_reranker_model_path=(
            PROJECT_ROOT / "local_runs/retrieval_models/bge-reranker-v2-m3"
            if args.with_reranker else None
        ),
        bge_reranker_model_revision=(EXPECTED_RERANKER_REVISION if args.with_reranker else ""),
        bge_reranker_model_checksum=(EXPECTED_RERANKER_CHECKSUM if args.with_reranker else ""),
        retrieval_device="cpu",
        rerank_limit=args.rerank_limit,
    )
    pipeline = RagV2DevPipeline(config)
    try:
        if args.debug_reranker and not args.with_reranker:
            print(json.dumps({"status": "BLOCKED", "reason": "debug_reranker_requires_with_reranker"}))
            return 1
        if args.debug_reranker:
            backend = pipeline.reranker_backend
            if backend is None:
                print(json.dumps({"status": "BLOCKED", "reason": "reranker_backend_unavailable"}))
                return 1
            plan = coerce_query_plan(args.question)
            options = SearchOptions(
                allowed_privacy_labels=config.allowed_privacy_labels,
                allowed_document_ids=(args.source_id,),
                allowed_source_paths=(str(source),),
                expected_source_fingerprints={args.source_id: _file_fingerprint(source)},
                candidate_limit=config.candidate_limit,
                per_document_limit=config.per_document_limit,
            )
            ranking = HybridRankingConfig(
                rrf_k=config.rrf_k,
                lexical_weight=config.lexical_channel_weight,
                dense_weight=config.dense_channel_weight,
                sparse_weight=config.sparse_channel_weight,
                rerank_limit=config.rerank_limit,
            )
            base = pipeline.index.hybrid_search_with_summary(
                plan,
                limit=config.retrieval_limit,
                options=options,
                dense_limit=config.dense_candidate_limit,
                ranking_config=ranking,
                reranker=None,
            )
            try:
                reranked = _rerank_hybrid_window(
                    plan.original_query, base.results, backend, ranking.rerank_limit
                )
                selected, _rejected = _select_hybrid_results(
                    reranked, plan, limit=config.retrieval_limit,
                    per_document_limit=options.per_document_limit,
                    near_duplicate_threshold=ranking.near_duplicate_threshold,
                )
            except Exception as error:
                print(json.dumps({
                    "status": "FAIL",
                    "reason": "reranker_pipeline_stage_failed",
                    "exception_type": type(error).__name__,
                }))
                return 2
            print(json.dumps({
                "status": "OK",
                "raw_candidate_count": len(base.results),
                "rerank_limit": ranking.rerank_limit,
                "selected_count": len(selected),
            }, ensure_ascii=False, indent=2))
            return 0
        result = pipeline.query(
            args.question,
            (SourceSpec(path=source, document_id=args.source_id, privacy_labels=("cloud_safe",)),),
            rerank_requested=args.with_reranker,
        )
        print(json.dumps({"status": "OK", **_result_summary(result)}, ensure_ascii=False, indent=2))
        return 0
    finally:
        pipeline.close()


if __name__ == "__main__":
    raise SystemExit(main())
