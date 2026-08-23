#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI runner for chunk evaluation baseline measurement.

Usage:
    python scripts/evaluate_chunking.py --strategy baseline \\
        --corpus tests/fixtures/chunk_evaluation/corpus_manifest.json \\
        --cases tests/fixtures/chunk_evaluation/cases_v1.json \\
        --output-dir local_runs/chunk_evaluation

The E1 scaffold currently validates the committed schema only. It will create
an isolated index and write a baseline report only after an approved local
real-corpus adapter is implemented. It NEVER modifies the active Workspace
Chat index.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is importable
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run chunk evaluation baseline measurement.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--strategy", default="baseline",
        help="Strategy name (default: baseline). Only 'baseline' is supported in E1.",
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
        "--dry-run", action="store_true",
        help="Validate inputs without running evaluation.",
    )
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    cases_path = Path(args.cases)
    output_dir = Path(args.output_dir)

    # Validate inputs
    if not corpus_path.exists():
        print(f"ERROR: Corpus manifest not found: {corpus_path}", file=sys.stderr)
        return 1
    if not cases_path.exists():
        print(f"ERROR: Cases file not found: {cases_path}", file=sys.stderr)
        return 1

    from aios_habit.rag_v2.chunk_evaluation import (
        load_cases,
        corpus_fingerprint,
        question_set_fingerprint,
    )

    # Load and validate cases
    cases = load_cases(cases_path)
    print(f"Loaded {len(cases)} evaluation cases from {cases_path}")
    print(f"  Languages: {sorted(set(c.language for c in cases))}")
    print(f"  Corpus fingerprint: {corpus_fingerprint(corpus_path)}")
    print(f"  Cases fingerprint: {question_set_fingerprint(cases_path)}")

    if args.dry_run:
        print("\n[DRY RUN] Input validation complete. No evaluation executed.")
        return 0

    if args.strategy != "baseline":
        print(f"ERROR: Only 'baseline' strategy is supported in E1, got: {args.strategy}", file=sys.stderr)
        return 1

    print(
        "BLOCKED: E1 has no approved local real-corpus adapter yet. "
        "The committed fixture uses synthetic identities only and must not "
        "produce a baseline report. Use --dry-run to validate its schema."
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
