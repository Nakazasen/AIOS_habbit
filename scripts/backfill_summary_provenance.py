"""Backfill document-summary provenance from body chunks.

Dry-run by default. Writes only with ``--apply``. See
``aios_habit.rag_v2.summary_provenance`` for the rules.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aios_habit.rag_v2.summary_provenance import (
    apply_summary_provenance,
    plan_summary_provenance,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path, help="Path to a RAG v2 chunks sqlite file")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the plan. Without this flag nothing is written.",
    )
    parser.add_argument("--json", action="store_true", help="Print the plan as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = plan_summary_provenance(args.index)
    if args.json:
        sys.stdout.write(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2) + "\n")
    else:
        print(f"index: {args.index}")
        print(f"summaries: {plan.summary_count}")
        print(f"would_update_fields: {plan.update_count}")
        print(f"skipped_ambiguous: {len(plan.skipped_ambiguous)}")
        print(f"skipped_no_body_value: {len(plan.skipped_no_body_value)}")
        for chunk_id, name, reason in plan.skipped_ambiguous:
            print(f"  ambiguous {chunk_id} {name}: {reason}")
    if not args.apply:
        print("dry_run: no changes written")
        return 0
    changed = apply_summary_provenance(args.index, plan)
    print(f"applied_rows_changed: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
