from __future__ import annotations

import argparse
import json
from pathlib import Path

from aios_habit.mom_coverage import coverage_summary_to_dict, summarize_mom_coverage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit every MOM corpus source and fail closed unless each is usable or owner-approved for exclusion."
    )
    parser.add_argument("root", type=Path, help="Corpus root directory")
    parser.add_argument(
        "--dispositions",
        type=Path,
        default=None,
        help="JSON ledger of explicit owner-approved unrecoverable exclusions",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("local_cases/mom_pilot/corpus_audit.json"),
        help="Machine-readable audit report path",
    )
    parser.add_argument("--no-rebuild", action="store_true", help="Audit the currently persisted index")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = summarize_mom_coverage(
        args.root,
        rebuild=not args.no_rebuild,
        dispositions_path=args.dispositions,
    )
    payload = coverage_summary_to_dict(summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"Audit report: {args.output.resolve()}")
    if summary.strict_passed:
        print("STRICT CORPUS AUDIT: PASS")
        return 0
    print(
        "STRICT CORPUS AUDIT: FAIL "
        f"({summary.unresolved_files} unresolved, "
        f"{len(summary.disposition_validation_errors)} disposition validation errors)"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
