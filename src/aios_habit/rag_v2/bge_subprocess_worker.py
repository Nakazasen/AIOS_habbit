"""Isolated Subprocess Worker for BGE-M3 RAG v2 Pipeline.

Runs in its own dedicated Python process, accepting JSON-RPC commands over stdin
and returning JSON responses over stdout. Isolates C-extension native memory and PyTorch
state from the main Streamlit process.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Mapping, Sequence

from aios_habit.rag_v2.pipeline import (
    RagV2DevConfig,
    RagV2DevPipeline,
    RagV2QueryResult,
    SourceSpec,
)
from aios_habit.rag_v2.adapters import ConversionContext
from aios_habit.rag_v2.schema import ExtractionStatus
from aios_habit.rag_v2_synthesis_provider import create_synthesis_provider


def _config_from_dict(payload: Mapping[str, Any]) -> RagV2DevConfig:
    kwargs = dict(payload)
    if "runtime_root" in kwargs and kwargs["runtime_root"] is not None:
        kwargs["runtime_root"] = Path(kwargs["runtime_root"])
    if "embedding_cache_dir" in kwargs and kwargs["embedding_cache_dir"] is not None:
        kwargs["embedding_cache_dir"] = Path(kwargs["embedding_cache_dir"])
    if "bge_m3_model_path" in kwargs and kwargs["bge_m3_model_path"] is not None:
        kwargs["bge_m3_model_path"] = Path(kwargs["bge_m3_model_path"])
    if "bge_reranker_model_path" in kwargs and kwargs["bge_reranker_model_path"] is not None:
        kwargs["bge_reranker_model_path"] = Path(kwargs["bge_reranker_model_path"])
    if "allowed_privacy_labels" in kwargs and isinstance(kwargs["allowed_privacy_labels"], list):
        kwargs["allowed_privacy_labels"] = tuple(kwargs["allowed_privacy_labels"])
    return RagV2DevConfig(**kwargs)


def _source_spec_from_dict(payload: Mapping[str, Any]) -> SourceSpec:
    return SourceSpec(
        path=Path(payload["path"]),
        source_id=payload.get("source_id", ""),
        document_id=payload.get("document_id", ""),
        privacy_labels=tuple(payload.get("privacy_labels", ("local_only",))),
        enabled=bool(payload.get("enabled", True)),
        owner_consent=bool(payload.get("owner_consent", False)),
        language_hints=tuple(payload.get("language_hints", ())),
    )


def _serialize_query_result(result: RagV2QueryResult) -> dict[str, Any]:
    summary = result.search_response.summary
    items = []
    for item in result.evidence_pack.items:
        items.append({
            "document_id": item.document_id,
            "text": item.text or item.snippet or "",
            "score": float(item.score),
            "citation_id": item.citation_id,
            "evidence_id": item.evidence_id,
            "element_types": tuple(getattr(item, "element_types", ())),
            "page": getattr(item, "page", None),
            "sheet": getattr(item, "sheet", None),
            "slide": getattr(item, "slide", None),
            "row_range": getattr(item, "row_range", None),
            "column_range": getattr(item, "column_range", None),
            "cell_range": getattr(item, "cell_range", None),
            "section_path": tuple(getattr(item, "section_path", ())),
            "matched_query_facets": tuple(getattr(item, "matched_query_facets", ())),
            "matched_obligations": tuple(getattr(item, "matched_obligations", ())),
        })
    synthesis = result.synthesis_result
    return {
        "summary": {
            "filtered_as_stale_count": summary.filtered_as_stale_count,
            "candidate_count": summary.candidate_count,
            "returned_count": summary.returned_count,
            "indexed_chunk_count": summary.indexed_chunk_count,
            "candidate_backend": summary.candidate_backend,
            "evidence_set_term_coverage": summary.evidence_set_term_coverage,
            "planned_facet_ids": list(summary.planned_facet_ids),
            "covered_facet_ids": list(summary.covered_facet_ids),
            "missing_facet_ids": list(summary.missing_facet_ids),
            "planned_obligation_ids": list(summary.planned_obligation_ids),
            "covered_obligation_ids": list(summary.covered_obligation_ids),
            "missing_obligation_ids": list(summary.missing_obligation_ids),
            # These fields were added to the worker protocol before the
            # corresponding SearchSummary counters existed in the deterministic
            # index implementation.  Serialize them defensively so an older
            # (but otherwise valid) SearchSummary cannot crash the worker after
            # doing all the expensive embedding work.
            "multivector_candidate_count": int(
                getattr(summary, "multivector_candidate_count", 0)
            ),
            "multivector_coverage_count": int(
                getattr(summary, "multivector_coverage_count", 0)
            ),
            "multivector_load_latency_ms": float(
                getattr(summary, "multivector_load_latency_ms", 0.0)
            ),
            "multivector_maxsim_latency_ms": float(
                getattr(summary, "multivector_maxsim_latency_ms", 0.0)
            ),
            "rerank_latency_ms": summary.rerank_latency_ms,
        },
        "insufficiency_reasons": list(result.evidence_pack.insufficiency_reasons),
        "items": items,
        "routing": {
            "reranker_requested": getattr(result, "reranker_requested", False),
            "reranker_applied": getattr(result, "reranker_applied", False),
            "effective_path": getattr(result, "effective_path", "hybrid"),
            "degraded": getattr(result, "degraded", False),
            "degraded_reason": getattr(result, "degraded_reason", ""),
            "rerank_latency_ms": float(getattr(summary, "rerank_latency_ms", 0.0) or 0.0),
            "policy_version": getattr(result, "policy_version", "adaptive-reranking-v1"),
        },
        "synthesis": {
            "answer": synthesis.answer,
            "citation_ids": list(synthesis.citation_ids),
            "claims": [asdict(claim) for claim in synthesis.claims],
            "grounded": synthesis.grounded,
            "abstained": synthesis.abstained,
            "abstention_reasons": list(synthesis.abstention_reasons),
            "answer_mode": synthesis.answer_mode,
            "limitation_reasons": list(synthesis.limitation_reasons),
            "provider_used": synthesis.provider_used,
            "mode": synthesis.mode,
        },
    }



def _safe_readiness(pipeline: RagV2DevPipeline) -> dict[str, Any]:
    """Expose only protocol and model identity, never source or filesystem state."""
    capability = pipeline.index.semantic_capability
    descriptor = capability.model.to_safe_dict() if capability and capability.model else None
    return {
        "pid": os.getpid(),
        "protocol_version": "1",
        "retrieval_profile": pipeline.config.retrieval_profile,
        "model": descriptor,
    }


def _stage_source(pipeline: RagV2DevPipeline, source: SourceSpec) -> dict[str, Any]:
    """Extract and chunk one source without making it query-visible."""
    if not source.enabled:
        raise RuntimeError("staged_source_disabled")
    if not source.path.is_file():
        raise RuntimeError("staged_source_unavailable")
    fingerprint = pipeline.index.document_state(source.document_id).get("source_fingerprint")
    from aios_habit.rag_v2.pipeline import _file_fingerprint
    source_fingerprint = _file_fingerprint(source.path)
    if fingerprint and fingerprint == source_fingerprint:
        coverage = pipeline.index.verify_selected_document_coverage(
            (source.document_id,),
            expected_document_fingerprints={source.document_id: source_fingerprint},
            sparse_required=pipeline.config.retrieval_profile in {
                "bge_m3_hybrid", "bge_m3_multivector",
            },
            multivector_required=(
                pipeline.config.retrieval_profile == "bge_m3_multivector"
            ),
        )
        if coverage["valid"]:
            return {"status": "unchanged", "chunk_count": 0}
        # Matching source bytes alone are not enough.  A prior lexical or
        # interrupted preparation may have published chunks without BGE-M3
        # vectors; rebuild this one document atomically below.
    context = ConversionContext(
        source_id=source.source_id,
        document_id=source.document_id,
        privacy_labels=source.privacy_labels,
        owner_consent=source.owner_consent,
        cloud_allowed=source.owner_consent and all(
            label in {"cloud_safe", "public"} for label in source.privacy_labels
        ),
        source_fingerprint=source_fingerprint,
        language_hints=list(source.language_hints),
        fail_soft=True,
    )
    elements = pipeline.registry.convert_document(str(source.path), context)
    failed = [item for item in elements if item.extraction_status in {
        ExtractionStatus.FAILED, ExtractionStatus.UNSUPPORTED,
    }]
    usable = [item for item in elements if item.extraction_status not in {
        ExtractionStatus.FAILED, ExtractionStatus.UNSUPPORTED,
    }]
    if not usable:
        raise RuntimeError("staged_conversion_incomplete")
    chunks = tuple(pipeline.chunker.chunk_elements(usable))
    if not chunks:
        raise RuntimeError("staged_empty_extracted_content")
    return {
        "status": "partial" if failed else "converted",
        "chunks": chunks,
        "source_fingerprint": source_fingerprint,
        "element_count": len(elements),
        "retrievable_count": sum(chunk.retrievable for chunk in chunks),
    }


def main() -> None:
    pipeline: RagV2DevPipeline | None = None
    staged: dict[str, dict[str, Any]] = {}

    # Line-buffered stdin/stdout reading loop
    for line in sys.stdin:
        line_str = line.strip()
        if not line_str:
            continue

        try:
            request = json.loads(line_str)
        except json.JSONDecodeError as err:
            response = {"status": "error", "error": f"json_decode_error: {err}"}
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            continue

        command = request.get("command", "")

        try:
            if command == "init":
                config_dict = request.get("config", {})
                init_phase = "init"
                try:
                    config = _config_from_dict(config_dict)
                    if pipeline is not None:
                        pipeline.close()
                    started = time.perf_counter()
                    init_phase = "model_verify"
                    model_path = config.bge_m3_model_path
                    if config.retrieval_profile.startswith("bge_m3_") and (
                        model_path is None or not Path(model_path).is_dir()
                    ):
                        raise RuntimeError("pinned_model_unavailable")
                    init_phase = "model_load"
                    synthesis_provider = create_synthesis_provider()
                    pipeline = RagV2DevPipeline(
                        config,
                        synthesis_provider=synthesis_provider,
                    )
                    init_phase = "index_open"
                    # Force a harmless schema read now so index failures are
                    # attributed during readiness rather than the first query.
                    pipeline.index.embedding_status()
                except Exception:
                    traceback.print_exc(file=sys.stderr)
                    sys.stderr.flush()
                    response = {
                        "status": "error",
                        "error": "worker_initialization_failed",
                        "error_phase": init_phase,
                    }
                else:
                    response = {
                        "status": "ok",
                        "readiness": {
                            **_safe_readiness(pipeline),
                            "init_latency_ms": round(
                                (time.perf_counter() - started) * 1000.0, 3
                            ),
                        },
                    }

            elif command == "health":
                if pipeline is None:
                    raise RuntimeError("worker_not_initialized")
                response = {"status": "ok", "readiness": _safe_readiness(pipeline)}

            elif command == "stage_source":
                if pipeline is None:
                    raise RuntimeError("worker_not_initialized")
                source = _source_spec_from_dict(request.get("spec", {}))
                staged_result = _stage_source(pipeline, source)
                if staged_result["status"] == "unchanged":
                    response = {"status": "ok", "staged": staged_result}
                else:
                    staged[source.document_id] = {
                        **staged_result,
                        "chunks": staged_result["chunks"],
                        "dense_vectors": {},
                        "sparse_vectors": {},
                        "multivector_vectors": {},
                    }
                    response = {"status": "ok", "staged": {
                        "status": staged_result["status"],
                        "document_id": source.document_id,
                        "chunk_count": len(staged_result["chunks"]),
                        "retrievable_count": staged_result["retrievable_count"],
                    }}

            elif command == "embed_staged_chunk_group":
                if pipeline is None:
                    raise RuntimeError("worker_not_initialized")
                document_id = str(request.get("document_id", ""))
                group_size = int(request.get("group_size", 0))
                if group_size < 1:
                    raise RuntimeError("invalid_staged_group_size")
                stage = staged.get(document_id)
                if stage is None:
                    raise RuntimeError("staged_source_not_found")
                pending = [
                    chunk for chunk in stage["chunks"]
                    if chunk.retrievable and chunk.chunk_id not in stage["dense_vectors"]
                ][:group_size]
                backend = pipeline.embedding_backend
                if pending and backend is not None:
                    texts = tuple(chunk.text for chunk in pending)
                    vectors = backend.embed_documents(texts)
                    sparse = backend.sparse_documents(texts)
                    multivectors = (
                        backend.multivector_documents(texts)
                        if backend.multivector_capability.available
                        else ()
                    )
                    if len(vectors) != len(pending) or len(sparse) != len(pending):
                        raise RuntimeError("staged_embedding_count_mismatch")
                    if multivectors and len(multivectors) != len(pending):
                        raise RuntimeError("staged_multivector_count_mismatch")
                    stage["dense_vectors"].update(
                        (chunk.chunk_id, vector) for chunk, vector in zip(pending, vectors)
                    )
                    stage["sparse_vectors"].update(
                        (chunk.chunk_id, vector) for chunk, vector in zip(pending, sparse)
                    )
                    stage["multivector_vectors"].update(
                        (chunk.chunk_id, vector)
                        for chunk, vector in zip(pending, multivectors)
                    )
                if backend is None:
                    pending = []
                    remaining = 0
                else:
                    remaining = sum(
                        chunk.retrievable and chunk.chunk_id not in stage["dense_vectors"]
                        for chunk in stage["chunks"]
                    )
                response = {"status": "ok", "progress": {
                    "document_id": document_id,
                    "embedded_count": len(pending),
                    "remaining_count": remaining,
                }}

            elif command == "commit_staged_source":
                if pipeline is None:
                    raise RuntimeError("worker_not_initialized")
                document_id = str(request.get("document_id", ""))
                stage = staged.pop(document_id, None)
                if stage is None:
                    raise RuntimeError("staged_source_not_found")
                indexed = pipeline.index.replace_document_chunks_with_embeddings(
                    document_id,
                    stage["chunks"],
                    stage["dense_vectors"],
                    stage["sparse_vectors"],
                    stage["multivector_vectors"],
                )
                response = {"status": "ok", "ingest_report": {
                    "converted_count": 1,
                    "skipped_count": 0,
                    "failed_count": 0,
                    "indexed_chunk_count": indexed,
                }}

            elif command == "abort_staged_source":
                document_id = str(request.get("document_id", ""))
                staged.pop(document_id, None)
                response = {"status": "ok"}

            elif command == "delete_documents":
                if pipeline is None:
                    raise RuntimeError("worker_not_initialized")
                document_ids = [
                    str(document_id).strip()
                    for document_id in request.get("document_ids", [])
                    if str(document_id).strip()
                ]
                removed_chunk_count = sum(
                    pipeline.index.delete_document(document_id)
                    for document_id in document_ids
                )
                for document_id in document_ids:
                    staged.pop(document_id, None)
                response = {"status": "ok", "removed_chunk_count": removed_chunk_count}

            elif command == "prepare_sources":
                if pipeline is None:
                    raise RuntimeError("worker_not_initialized")
                specs_dict = request.get("specs", [])
                specs = [_source_spec_from_dict(s) for s in specs_dict]

                report = pipeline.ingest(specs)
                if report.failed_count or report.unsupported_count or report.empty_count:
                    raise RuntimeError("rag_v2_ingestion_incomplete")

                response = {
                    "status": "ok",
                    "ingest_report": {
                        "converted_count": report.converted_count,
                        "skipped_count": report.skipped_count,
                        "failed_count": report.failed_count,
                        "indexed_chunk_count": report.indexed_chunk_count,
                    },
                }

            elif command == "query":
                if pipeline is None:
                    raise RuntimeError("worker_not_initialized")
                question = str(request.get("question", ""))
                specs_dict = request.get("specs", [])
                specs = [_source_spec_from_dict(s) for s in specs_dict]
                expansion = request.get("expansion")
                routing = request.get("routing")
                rerank_requested = False
                routing_reason_codes = ()
                policy_version = "adaptive-reranking-v1"
                if isinstance(routing, dict):
                    if routing.get("schema_version") != 1:
                        raise RuntimeError("unsupported_routing_schema_version")
                    rerank_requested = bool(routing.get("rerank_requested", False))
                    routing_reason_codes = tuple(str(c) for c in routing.get("reason_codes", ()))
                    policy_version = str(routing.get("policy_version", "adaptive-reranking-v1"))

                query_res = pipeline.query(
                    question,
                    specs,
                    expansion=expansion,
                    rerank_requested=rerank_requested,
                    routing_reason_codes=routing_reason_codes,
                    policy_version=policy_version,
                )
                if query_res.search_response.summary.filtered_as_stale_count:
                    raise RuntimeError("rag_v2_stale_index")

                serialized = _serialize_query_result(query_res)
                if isinstance(routing, dict):
                    serialized["routing"]["policy_version"] = policy_version
                response = {
                    "status": "ok",
                    "query_result": serialized,
                }

            elif command == "ingest_and_query":
                if pipeline is None:
                    raise RuntimeError("worker_not_initialized")
                question = str(request.get("question", ""))
                specs_dict = request.get("specs", [])
                specs = [_source_spec_from_dict(s) for s in specs_dict]
                expansion = request.get("expansion")
                routing = request.get("routing")
                rerank_requested = False
                routing_reason_codes = ()
                policy_version = "adaptive-reranking-v1"
                if isinstance(routing, dict):
                    if routing.get("schema_version") != 1:
                        raise RuntimeError("unsupported_routing_schema_version")
                    rerank_requested = bool(routing.get("rerank_requested", False))
                    routing_reason_codes = tuple(str(c) for c in routing.get("reason_codes", ()))
                    policy_version = str(routing.get("policy_version", "adaptive-reranking-v1"))

                report = pipeline.ingest(specs)
                if report.failed_count or report.unsupported_count or report.empty_count:
                    raise RuntimeError("rag_v2_ingestion_incomplete")

                query_res = pipeline.query(
                    question,
                    specs,
                    expansion=expansion,
                    rerank_requested=rerank_requested,
                    routing_reason_codes=routing_reason_codes,
                    policy_version=policy_version,
                )
                if query_res.search_response.summary.filtered_as_stale_count:
                    raise RuntimeError("rag_v2_stale_index")

                serialized = _serialize_query_result(query_res)
                if isinstance(routing, dict):
                    serialized["routing"]["policy_version"] = policy_version
                response = {
                    "status": "ok",
                    "query_result": serialized,
                    "ingest_report": {
                        "converted_count": report.converted_count,
                        "skipped_count": report.skipped_count,
                        "failed_count": report.failed_count,
                        "indexed_chunk_count": report.indexed_chunk_count,
                    },
                }


            elif command == "close":
                if pipeline is not None:
                    pipeline.close()
                    pipeline = None
                response = {"status": "ok"}
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                break

            else:
                response = {"status": "error", "error": f"unknown_command_{command}"}

        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            response = {
                "status": "error",
                "error": f"{command or 'protocol'}_failed",
                "error_type": exc.__class__.__name__,
            }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    if pipeline is not None:
        try:
            pipeline.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
