from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aios_habit.mom_benchmark import MomBenchmarkRecord


@dataclass
class BenchmarkGateResult:
    attempted_50: bool
    reason: str
    questions_run: int
    notebooklm_success: int
    aios_answers_with_source_refs: int
    critical_hallucinations: int
    inconclusive: int
    average_aios_maturity_score: float
    target_90_met: bool


def weighted_maturity_score(scores: dict[str, int]) -> float:
    if not scores:
        return 0.0
    source = scores.get("source_traceability", 0) / 5 * 20
    completeness = scores.get("answer_completeness", 0) / 5 * 20
    hallucination = scores.get("hallucination_risk", 0) / 5 * 10
    actionability = scores.get("actionability", 0) / 5 * 10
    clarity = scores.get("vietnamese_clarity", 0) / 5 * 10
    alignment = scores.get("evidence_alignment", 0) / 5 * 30
    return round(source + completeness + hallucination + actionability + clarity + alignment, 2)


def score_aios_prompt_pack(pack: dict[str, Any]) -> dict[str, int]:
    """Score the local AIOS evidence answer without using NotebookLM as ground truth.

    This rewards concrete properties that reduce hallucination risk: source refs,
    file diversity, explicit answer discipline, insufficient-evidence handling,
    and an actual structured answer. Source refs alone must not be enough to
    claim a 90+ benchmark score.
    """
    refs = pack.get("source_refs") or []
    discipline = pack.get("answer_discipline") or {}
    answer_text = str(pack.get("answer_text") or pack.get("aios_answer") or "")
    source_count = len(refs)
    file_count = len(set(ref.get("relative_path") for ref in refs))
    has_prompt = bool(str(pack.get("prompt") or "").strip())
    insufficient = bool(pack.get("insufficient_evidence"))
    required_discipline = all(bool(discipline.get(key)) for key in (
        "confirmed_by_source_required",
        "insufficient_evidence_required",
        "next_checks_required",
        "notebooklm_comparator_not_ground_truth",
    ))
    has_answer = bool(answer_text.strip())
    answer_has_sections = all(token in answer_text.lower() for token in (
        "confirmed",
        "not found",
        "next checks",
        "source coverage",
    ))
    return {
        "source_traceability": 5 if source_count >= 2 else 3 if source_count == 1 else 0,
        "answer_completeness": 5 if source_count >= 3 and has_answer and answer_has_sections and not insufficient else 3 if source_count and has_prompt else 0,
        "hallucination_risk": 5 if required_discipline and source_count and (has_answer or insufficient) else 3 if source_count else 1,
        "actionability": 5 if answer_has_sections and "next checks" in answer_text.lower() else 3 if required_discipline and source_count else 0,
        "vietnamese_clarity": 5 if has_answer and ("nguồn" in answer_text.lower() or "source" in answer_text.lower()) else 3 if has_prompt else 0,
        "evidence_alignment": 5 if source_count >= 3 and file_count >= 2 and has_answer else 4 if source_count >= 2 else 2 if source_count else 0,
    }


def _record_critical_hallucination(record: MomBenchmarkRecord) -> bool:
    notes = (record.notes or "").lower()
    answer = (record.aios_answer_summary or "").lower()
    no_refs = not record.aios_source_refs
    unsupported_conclusion = "không đủ" not in answer and no_refs
    explicit_critical = any(token in notes for token in ("critical hallucination", "hallucination nghiêm trọng", "wrong source"))
    return bool(explicit_critical or unsupported_conclusion)


def evaluate_benchmark_gate(records: list[MomBenchmarkRecord], *, target_questions: int, expansion_threshold: int) -> BenchmarkGateResult:
    questions_run = len(records)
    notebooklm_success = sum(1 for record in records if record.notebooklm_query_status == "success")
    refs = sum(1 for record in records if record.aios_source_refs)
    critical = sum(1 for record in records if _record_critical_hallucination(record))
    inconclusive = sum(1 for record in records if record.winner == "Inconclusive")
    scores = [weighted_maturity_score(record.comparison_scores) for record in records]
    average = round(sum(scores) / len(scores), 2) if scores else 0.0
    target_90_met = average >= 90 and refs == questions_run and critical == 0
    stable = questions_run >= target_questions and notebooklm_success >= expansion_threshold and target_90_met
    reason = "pass" if stable else "benchmark gate not met"
    if refs != questions_run:
        reason = "not all AIOS answers have source refs"
    elif critical:
        reason = "critical hallucination detected"
    elif average < 90:
        reason = "average maturity score below 90"
    elif notebooklm_success < expansion_threshold:
        reason = "NotebookLM success below required threshold"
    return BenchmarkGateResult(
        attempted_50=stable,
        reason=reason,
        questions_run=questions_run,
        notebooklm_success=notebooklm_success,
        aios_answers_with_source_refs=refs,
        critical_hallucinations=critical,
        inconclusive=inconclusive,
        average_aios_maturity_score=average,
        target_90_met=target_90_met,
    )


def benchmark_gate_to_dict(result: BenchmarkGateResult) -> dict[str, Any]:
    return result.__dict__.copy()
