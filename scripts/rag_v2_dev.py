#!/usr/bin/env python3
"""Local-only command surface for the independent RAG v2 Dev pipeline."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aios_habit.rag_v2 import (  # noqa: E402
    BenchmarkConfig,
    BenchmarkQuestion,
    RagV2DevConfig,
    RagV2DevPipeline,
    SourceSpec,
    benchmark_summary_to_dict,
)
from aios_habit.rag_v2.eval_harness import score_question, summarize_results  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RAG v2 Dev CLI (local-only; no provider or credential access)",
    )
    parser.add_argument(
        "--runtime-root",
        default="local_runs/rag_v2_dev",
        help="Ignored local runtime directory (default: local_runs/rag_v2_dev)",
    )
    parser.add_argument("--max-chunk-chars", type=int, default=1200)
    parser.add_argument("--retrieval-limit", type=int, default=10)
    parser.add_argument(
        "--allowed-privacy-label",
        action="append",
        choices=("local_only", "confidential", "cloud_safe", "public"),
        dest="allowed_labels",
        help="Repeat to restrict query/evaluation; defaults to all canonical labels",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="Convert, chunk, and incrementally index sources")
    _add_sources(ingest, required=True)

    query = commands.add_parser("query", help="Retrieve a filtered local evidence pack")
    query.add_argument("question")
    _add_sources(query, required=True)

    inspect = commands.add_parser("inspect", help="Show safe counts, fingerprints, and statuses")
    _add_sources(inspect, required=False)

    evaluate = commands.add_parser("evaluate", help="Run local retrieval/evidence questions")
    evaluate.add_argument("--questions", required=True, help="Local JSON question fixture")
    _add_sources(evaluate, required=True)
    return parser


def _add_sources(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument("--source", action="append", required=required, default=[])
    parser.add_argument(
        "--privacy-label",
        action="append",
        choices=("local_only", "confidential", "cloud_safe", "public"),
        default=None,
        help="Labels applied to every selected source; defaults to local_only",
    )


def _config(args: argparse.Namespace) -> RagV2DevConfig:
    labels = tuple(args.allowed_labels) if args.allowed_labels else (
        "local_only", "confidential", "cloud_safe", "public",
    )
    return RagV2DevConfig(
        runtime_root=Path(args.runtime_root),
        max_chunk_chars=args.max_chunk_chars,
        retrieval_limit=args.retrieval_limit,
        allowed_privacy_labels=labels,
    )


def _sources(args: argparse.Namespace) -> tuple[SourceSpec, ...]:
    labels = tuple(args.privacy_label or ("local_only",))
    return tuple(SourceSpec(Path(value), privacy_labels=labels) for value in args.source)


def _safe_evidence(result: Any) -> dict[str, Any]:
    pack = result.evidence_pack
    synthesis = result.synthesis_result
    return {
        "route": result.route,
        "provider_used": result.provider_used,
        "pack_id": pack.pack_id,
        "query": pack.query,
        "confidence": pack.confidence.value,
        "insufficiency_reasons": list(pack.insufficiency_reasons),
        "source_count": pack.source_count,
        "document_count": pack.document_count,
        "item_count": pack.item_count,
        "best_term_coverage": pack.best_term_coverage,
        "retrieval_summary": asdict(result.search_response.summary),
        "synthesis": {
            "answer": synthesis.answer,
            "grounded": synthesis.grounded,
            "abstained": synthesis.abstained,
            "citation_ids": list(synthesis.citation_ids),
            "abstention_reasons": list(synthesis.abstention_reasons),
            "mode": synthesis.mode,
            "provider_used": synthesis.provider_used,
        },
        "items": [
            {
                "citation_id": item.citation_id,
                "citation_label": item.citation_label,
                "document_id": item.document_id,
                "source_name": item.source_name,
                "snippet": item.snippet,
                "score": item.score,
                "term_coverage": item.term_coverage,
                "privacy_labels": list(item.privacy_labels),
                "page": item.page,
                "sheet": item.sheet,
                "slide": item.slide,
                "row_range": list(item.row_range) if item.row_range is not None else None,
                "column_range": list(item.column_range) if item.column_range is not None else None,
                "cell_range": item.cell_range,
                "bbox": list(item.bbox) if item.bbox is not None else None,
                "section_path": list(item.section_path),
            }
            for item in pack.items
        ],
    }


def _load_questions(path: Path) -> list[BenchmarkQuestion]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("questions") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise ValueError("questions JSON must be a non-empty list or {questions: [...]} object")
    questions = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each question must be an object")
        answer_type = str(row.get("expected_answer_type", "answerable"))
        if answer_type not in {"answerable", "insufficient"}:
            raise ValueError("expected_answer_type must be answerable or insufficient")
        questions.append(BenchmarkQuestion(
            question_id=str(row["question_id"]),
            question=str(row["question"]),
            expected_answer_type=answer_type,
            expected_chunk_ids=tuple(row.get("expected_chunk_ids", ())),
            expected_document_ids=tuple(row.get("expected_document_ids", ())),
            expected_source_names=tuple(row.get("expected_source_names", ())),
            expected_privacy=str(row.get("expected_privacy", "any")),
            forbidden_terms=tuple(row.get("forbidden_terms", ())),
            tags=tuple(row.get("tags", ())),
        ))
    return questions


def _evaluate(
    pipeline: RagV2DevPipeline,
    sources: tuple[SourceSpec, ...],
    questions_path: Path,
) -> tuple[dict[str, Any], int]:
    questions = _load_questions(questions_path)
    config = BenchmarkConfig(
        top_k=pipeline.config.retrieval_limit,
        per_document_limit=pipeline.config.per_document_limit,
    )
    scored = []
    for question in questions:
        started = time.perf_counter()
        outcome = pipeline.query(question.question, sources)
        latency_ms = (time.perf_counter() - started) * 1000.0
        scored.append(score_question(
            question,
            outcome.search_response,
            outcome.evidence_pack,
            latency_ms,
            synthesis=outcome.synthesis_result,
        ))
    summary = summarize_results(scored, config)
    identity = json.dumps([
        {"id": question.question_id, "question": question.question}
        for question in questions
    ], sort_keys=True, ensure_ascii=False).encode("utf-8")
    summary.benchmark_id = f"DEV-{hashlib.sha256(identity).hexdigest()[:10].upper()}"
    payload = benchmark_summary_to_dict(summary)
    payload["mode"] = "local_only"
    payload["provider_used"] = False
    return payload, 0 if summary.pass_fail in {"PASS", "PASS_WITH_WARNINGS"} else 2


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    sources = _sources(args)
    try:
        with RagV2DevPipeline(_config(args)) as pipeline:
            if args.command == "ingest":
                payload = pipeline.ingest(sources).to_safe_dict()
                exit_code = 0 if payload["failed_count"] == 0 else 2
            elif args.command == "query":
                payload = _safe_evidence(pipeline.query(args.question, sources))
                exit_code = 0
            elif args.command == "inspect":
                payload = pipeline.inspect(sources)
                exit_code = 0
            else:
                payload, exit_code = _evaluate(pipeline, sources, Path(args.questions))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        payload = {"status": "error", "error_type": type(exc).__name__, "message": str(exc)}
        exit_code = 2
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
