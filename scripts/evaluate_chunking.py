#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI runner for chunk evaluation baseline measurement.

Usage:
    python scripts/evaluate_chunking.py --strategy baseline \\
        --corpus tests/fixtures/chunk_evaluation/corpus_public_v3.json \\
        --cases tests/fixtures/chunk_evaluation/cases_v1.json \\
        --output-dir local_runs/chunk_evaluation

    python scripts/evaluate_chunking.py --strategy cjk-sentence-punctuation-v1 \\
        --corpus tests/fixtures/chunk_evaluation/corpus_public_v3.json \\
        --compare-to local_runs/chunk_evaluation/e1_run2/<report>.json

A baseline report is written only for strategy baseline when the corpus is
file-backed and retrieval uses BGE-M3 hybrid. Candidates require --compare-to
a frozen E1 report. Synthetic identity manifests stay BLOCKED. The runner
NEVER modifies the active Workspace Chat index.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is importable
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run chunk evaluation baseline measurement.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--strategy", default="baseline",
        help="Strategy id: baseline | cjk-sentence-punctuation-v1",
    )
    parser.add_argument(
        "--corpus",
        default="tests/fixtures/chunk_evaluation/corpus_manifest.json",
        help="Path to corpus manifest JSON.",
    )
    parser.add_argument(
        "--cases",
        default="tests/fixtures/chunk_evaluation/cases_v1.json",
        help="Path to evaluation cases JSON.",
    )
    parser.add_argument(
        "--output-dir",
        default="local_runs/chunk_evaluation",
        help="Directory for output reports.",
    )
    parser.add_argument(
        "--deployment-manifest",
        default="config/workspace_chat_rag_v2.local.json",
        help="Local BGE-M3 deployment manifest (activation is not required for E1).",
    )
    parser.add_argument(
        "--compare-to",
        default="",
        help="Frozen E1 report JSON. Required for candidate strategies.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate inputs without running evaluation.",
    )
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    cases_path = Path(args.cases)
    output_dir = Path(args.output_dir)

    if not corpus_path.exists():
        print(f"ERROR: Corpus manifest not found: {corpus_path}", file=sys.stderr)
        return 1
    if not cases_path.exists():
        print(f"ERROR: Cases file not found: {cases_path}", file=sys.stderr)
        return 1

    from aios_habit.rag_v2.chunk_evaluation import (
        BASELINE_STRATEGY,
        BaselineRunner,
        SYNTHETIC_CORPUS_KIND,
        corpus_fingerprint,
        load_cases,
        load_corpus_manifest,
        question_set_fingerprint,
        resolve_strategy,
    )

    cases = load_cases(cases_path)
    corpus = load_corpus_manifest(corpus_path)
    print(f"Loaded {len(cases)} evaluation cases from {cases_path}")
    print(f"  Languages: {sorted(set(c.language for c in cases))}")
    print(f"  Corpus kind: {corpus.kind}")
    print(f"  Corpus fingerprint: {corpus_fingerprint(corpus_path)}")
    print(f"  Cases fingerprint: {question_set_fingerprint(cases_path)}")

    if args.dry_run:
        print("\n[DRY RUN] Input validation complete. No evaluation executed.")
        return 0

    try:
        strategy = resolve_strategy(args.strategy)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    baseline_report = None
    if args.compare_to:
        compare_path = Path(args.compare_to)
        if not compare_path.is_file():
            print(f"ERROR: Compare-to report not found: {compare_path}", file=sys.stderr)
            return 1
        baseline_report = json.loads(compare_path.read_text(encoding="utf-8"))

    if strategy.strategy_id != BASELINE_STRATEGY.strategy_id and baseline_report is None:
        print(
            "ERROR: Candidate strategies require --compare-to a frozen E1 report.",
            file=sys.stderr,
        )
        return 1

    if corpus.kind == SYNTHETIC_CORPUS_KIND or corpus.synthetic:
        print(
            "BLOCKED: E1 refuses synthetic identities. The committed identity-only "
            "fixture must not produce a baseline report. Pass a file-backed corpus "
            "such as tests/fixtures/chunk_evaluation/corpus_public_v3.json."
        )
        return 2

    runner = BaselineRunner(
        corpus_manifest_path=corpus_path,
        cases_path=cases_path,
        index_dir=output_dir / "indexes",
        strategy=strategy,
        require_bge_hybrid=True,
        deployment_manifest=args.deployment_manifest,
        baseline_report=baseline_report,
    )
    run, json_path, md_path = runner.run_and_save(output_dir)
    report = getattr(run, "_report_overlay", None) or run.to_report_dict()
    print(f"Decision: {run.decision}")
    print(f"Strategy: {run.strategy_id}")
    print(f"Model: {run.model_identity}")
    print(f"Chunker: {run.supported_path}")
    print(f"Report: {json_path}")
    print(f"Summary: {md_path}")
    if report.get("comparison_reason"):
        print(f"Comparison: {report['comparison_reason']}")
    if run.decision == "blocked":
        print(f"BLOCKED: {report.get('blocked_reason', 'incomplete_run')}")
        return 2
    metrics = run.metrics
    if metrics is not None:
        print(
            f"Recall@K={metrics.expected_evidence_recall_at_k:.3f} "
            f"citation={metrics.citation_support_rate:.3f} "
            f"p95={metrics.warm_query_p95_ms:.1f}ms "
            f"chunks={metrics.retrievable_chunk_count}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
