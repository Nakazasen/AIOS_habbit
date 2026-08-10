from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DIMENSIONS = (
    "correctness", "completeness", "faithfulness", "citation_support",
    "relevance", "clarity", "actionability", "abstention_calibration",
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def _question_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        question_id = str(row.get("id", "")).strip()
        if not question_id:
            raise ValueError(f"Question without id at {path}:{line_number}")
        rows[question_id] = row
    return rows


def _score_rows(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("question_id", "")): row
        for row in report.get("per_question", [])
        if isinstance(row, dict) and row.get("question_id")
    }


def _dimension_deltas(score: dict[str, Any]) -> dict[str, float]:
    candidate = score.get("rag_v2", {})
    reference = score.get("notebooklm", {})
    return {
        dimension: round(float(reference.get(dimension, 0)) - float(candidate.get(dimension, 0)), 4)
        for dimension in DIMENSIONS
    }


def _pool_size(summary: dict[str, Any], name: str) -> int:
    value = summary.get(name, [])
    return len(value) if isinstance(value, list) else 0


def _observed_bottleneck(
    *, expected_type: str, rag: dict[str, Any], retrieval: dict[str, Any],
    pipeline: dict[str, Any], validation: dict[str, Any],
) -> tuple[str, str, list[str]]:
    errors = [str(value) for value in validation.get("errors", [])]
    hard_reasons = [str(value) for value in rag.get("hard_insufficiency_reasons", [])]
    answer_mode = str(rag.get("answer_mode", ""))
    provider_failed = bool(validation) and validation.get("valid") is False
    if expected_type == "insufficient":
        if answer_mode == "abstain" or pipeline.get("local_synthesis_abstained"):
            return "correct_abstention_path", "measured", []
        return "abstention_calibration_miss", "measured", hard_reasons
    if provider_failed:
        return "citation_contract_miss", "measured", errors
    if hard_reasons or answer_mode == "abstain":
        return "retrieval_or_evidence_gate_miss", "measured", hard_reasons
    if retrieval.get("returned_count", 0) == 0:
        return "candidate_recall_miss", "measured", ["no_returned_evidence"]
    if pipeline.get("local_synthesis_grounded") and not pipeline.get("provider_used"):
        return "synthesis_fallback_exposed", "measured", []
    return "unresolved_requires_oracle", "unresolved", []


def build_audit(battle_dir: Path, quality_report_path: Path) -> dict[str, Any]:
    questions = _question_rows(battle_dir / "questions.jsonl")
    battle_report = _read_json(battle_dir / "battle_report.json")
    quality_report = _read_json(quality_report_path)
    scores = _score_rows(quality_report)
    rows: list[dict[str, Any]] = []
    pareto: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"question_count": 0, "normalized_score_gap_sum": 0.0}
    )
    for question_id, question in questions.items():
        checkpoint_path = battle_dir / "checkpoints" / f"{question_id}.json"
        checkpoint = _read_json(checkpoint_path)
        rag = checkpoint.get("rag_v2", {})
        retrieval = rag.get("evidence_pack", {}).get("retrieval_summary", {})
        pipeline = rag.get("pipeline", {})
        validation = rag.get("provider_validation", {})
        score = scores.get(question_id, {})
        bottleneck, attribution_status, reasons = _observed_bottleneck(
            expected_type=str(question.get("expected_type", "")), rag=rag,
            retrieval=retrieval, pipeline=pipeline, validation=validation,
        )
        candidate_overall = float(score.get("rag_v2_overall", 0))
        reference_overall = float(score.get("notebooklm_overall", 0))
        normalized_gap = round(reference_overall - candidate_overall, 4)
        pareto[bottleneck]["question_count"] = int(pareto[bottleneck]["question_count"]) + 1
        pareto[bottleneck]["normalized_score_gap_sum"] = round(
            float(pareto[bottleneck]["normalized_score_gap_sum"]) + normalized_gap, 4
        )
        rows.append({
            "question_id": question_id,
            "category": question.get("category"),
            "expected_type": question.get("expected_type"),
            "quality": {
                "candidate_overall_normalized": candidate_overall,
                "reference_overall_normalized": reference_overall,
                "normalized_gap": normalized_gap,
                "dimension_gap_reference_minus_candidate": _dimension_deltas(score),
            },
            "ingestion": {
                "battle_status": battle_report.get("rag_v2_ingestion", {}).get("status"),
                "files_usable": battle_report.get("rag_v2_ingestion", {}).get("files_usable"),
                "files_seen": battle_report.get("rag_v2_ingestion", {}).get("files_seen"),
            },
            "retrieval": {
                "candidate_count": retrieval.get("candidate_count"),
                "returned_count": retrieval.get("returned_count"),
                "best_term_coverage": retrieval.get("best_term_coverage"),
                "evidence_set_term_coverage": retrieval.get("evidence_set_term_coverage"),
                "lexical_pool_size": _pool_size(retrieval, "lexical_pool"),
                "dense_pool_size": _pool_size(retrieval, "dense_pool"),
                "sparse_pool_size": _pool_size(retrieval, "sparse_pool"),
                "ranked_pool_size": _pool_size(retrieval, "ranked_pool"),
                "assembly_rejected_pool_size": _pool_size(retrieval, "assembly_rejected_pool"),
                "answer_mode": rag.get("answer_mode"),
                "hard_insufficiency_reasons": rag.get("hard_insufficiency_reasons", []),
                "soft_warning_reasons": rag.get("soft_warning_reasons", []),
            },
            "synthesis": {
                "pipeline_route": pipeline.get("route"),
                "provider_used": pipeline.get("provider_used"),
                "local_synthesis_grounded": pipeline.get("local_synthesis_grounded"),
                "local_synthesis_abstained": pipeline.get("local_synthesis_abstained"),
                "llm_error": rag.get("llm_error"),
                "provider_validation": validation,
            },
            "attribution": {
                "observed_bottleneck": bottleneck,
                "status": attribution_status,
                "reasons": reasons,
                "gold_evidence_presence": "not_measured",
                "gold_evidence_rank": None,
                "oracle_required": bottleneck not in {"correct_abstention_path", "abstention_calibration_miss"},
            },
            "source_artifact": str(checkpoint_path.resolve()),
        })
    pareto_rows = [
        {"bottleneck": name, **values}
        for name, values in sorted(
            pareto.items(), key=lambda item: (-float(item[1]["normalized_score_gap_sum"]), item[0])
        )
    ]
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "audit_kind": "diagnostic_failure_attribution",
        "limitations": [
            "Observed telemetry is not a substitute for gold-evidence recall labels.",
            "Gold-evidence presence and rank remain unmeasured until an oracle ledger is supplied.",
            "Engineering status and blind answer-quality scores are reported separately.",
        ],
        "identity": {
            "battle_id": battle_report.get("battle_id"),
            "corpus_fingerprint": battle_report.get("corpus_fingerprint"),
            "question_set_hash": battle_report.get("question_set_hash"),
            "candidate_fingerprint": battle_report.get("candidate", {}).get("candidate_fingerprint"),
            "production_identity_sha256": battle_report.get("candidate", {}).get("production_identity", {}).get("identity_sha256"),
        },
        "engineering_gates": {
            "ingestion_status": battle_report.get("rag_v2_ingestion", {}).get("status"),
            "workspace_ingestion_status": battle_report.get("workspace_ingestion", {}).get("status"),
            "router_status": battle_report.get("router", {}).get("status"),
            "production_stage_status": battle_report.get("workspace_production_preparation", {}).get("status"),
        },
        "blind_answer_quality": {
            "aggregate": quality_report.get("aggregate", {}),
            "judge_disagreement": quality_report.get("judge_disagreement", {}),
            "gate": quality_report.get("gate", {}),
        },
        "questions": rows,
        "observed_bottleneck_pareto": pareto_rows,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a generic per-question RAG quality plateau attribution audit from sealed battle artifacts."
    )
    parser.add_argument("battle_dir", type=Path, help="Completed battle directory")
    parser.add_argument("quality_report", type=Path, help="Blind quality report JSON")
    parser.add_argument("--output", type=Path, required=True, help="Output audit JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = build_audit(args.battle_dir, args.quality_report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["observed_bottleneck_pareto"], ensure_ascii=False, indent=2))
    print(f"Quality plateau audit: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
