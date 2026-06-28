from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FINAL_ANSWER_KINDS = {"strong_model_answer", "pasted_strong_model_answer", "human_approved_answer"}


@dataclass
class EvaluationResult:
    retrieval_coverage: float
    evidence_relevance: float
    metadata_only_rate: float
    answer_groundedness: float
    source_intent_match: float
    abstention_correctness: float
    heuristic_only: bool = True
    final_answer_eligible: bool = False
    warnings: list[str] | None = None


def _tokens(text: str) -> set[str]:
    import re
    return {t.lower() for t in re.findall(r"[A-Za-z0-9À-ỹ一-龯ぁ-んァ-ン]{2,}", text or "")}


def evaluate_grounded_answer(answer: Any, evidence_pack: Any, detected_intent: str = "") -> EvaluationResult:
    items = list(getattr(evidence_pack, "items", []) or [])
    valid = [i for i in items if getattr(i, "metadata", {}).get("_is_metadata_only") != "True"]
    metadata_rate = 1.0 - (len(valid) / len(items)) if items else 1.0
    answer_text = getattr(answer, "answer_text", "") or ""
    answer_kind = getattr(answer, "answer_kind", "") or ""
    final_eligible = answer_kind in FINAL_ANSWER_KINDS and bool(getattr(answer, "final_answer", False))
    ev_text = " ".join(getattr(i, "text", "") or getattr(i, "snippet", "") or "" for i in valid)
    overlap = len(_tokens(answer_text) & _tokens(ev_text))
    denom = max(1, len(_tokens(answer_text)))
    grounded = min(1.0, overlap / denom)
    relevance = min(1.0, overlap / max(1, len(_tokens(ev_text)))) if valid else 0.0
    coverage = min(1.0, len(valid) / 3)
    source_match = 0.0
    if detected_intent:
        for i in valid:
            explain = str(getattr(i, "metadata", {}).get("_score_explanation", ""))
            if "intent=" in explain or detected_intent.lower() in explain.lower():
                source_match = 1.0
                break
    abstain = "chưa đủ bằng chứng" in answer_text.lower() or "không đủ bằng chứng" in answer_text.lower()
    abstention = 1.0 if (metadata_rate == 1.0 and abstain) or (metadata_rate < 1.0 and not abstain) else 0.0
    warnings = []
    if answer_kind == "local_evidence_draft":
        warnings.append("local_evidence_draft is not a final answer and must not compete against NotebookLM final answers")
        final_eligible = False
    if metadata_rate == 1.0:
        grounded = 0.0
        warnings.append("metadata-only evidence cannot support grounded final answers")
    return EvaluationResult(coverage, relevance, metadata_rate, grounded, source_match, abstention, True, final_eligible, warnings)
