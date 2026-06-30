from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List


@dataclass(frozen=True)
class ClaimReadiness:
    allowed: bool
    claim_type: str
    reasons: List[str] = field(default_factory=list)


def _domains(corpus_domains: Iterable[str]) -> set[str]:
    return {str(domain).lower() for domain in corpus_domains}


def evaluate_claim_readiness(
    test_scope: str,
    corpus_domains: Iterable[str],
    answer_quality: str,
    model_used: str,
    human_review_status: str,
    claim_type: str = "general_notebooklm_replacement",
    owner_approved_p1: bool = False,
) -> ClaimReadiness:
    scope = (test_scope or "").lower()
    quality = (answer_quality or "").lower()
    model = (model_used or "").lower()
    review = (human_review_status or "").lower()
    domains = _domains(corpus_domains)
    reasons: List[str] = []

    if claim_type in {"general_notebooklm_replacement", "daily_replacement"}:
        if domains <= {"mom", "wms", "manufacturing", "manufacturing_mom_wms"} or "mom" in scope or "wms" in scope:
            reasons.append("MOM/WMS-only evidence cannot support a general NotebookLM replacement claim.")
        if review in {"pending", "missing", "not_done", "human_review"}:
            reasons.append("Human review is not complete.")
        if quality in {"weaker", "partial", "mixed", "unknown", "fail"}:
            reasons.append("Answer quality is not proven stronger across the requested work scope.")

    if claim_type in {"notebooklm_parity", "global_notebooklm_parity"}:
        if "deterministic" in model and "notebooklm" in scope:
            reasons.append("Deterministic AIOS synthesis is not a fair parity comparison against NotebookLM model synthesis.")
        if len(domains) < 3:
            reasons.append("Parity requires a multi-domain benchmark, not a narrow corpus.")
        if review != "passed":
            reasons.append("NotebookLM parity requires completed human review.")

    if claim_type in {"p1_opened", "p1_0_opened"} and not owner_approved_p1:
        reasons.append("P1.0 cannot be claimed open without explicit owner approval.")

    if claim_type in {"mom_specific_assistant", "mom_only_replacement"}:
        if not domains.intersection({"mom", "wms", "manufacturing", "manufacturing_mom_wms"}):
            reasons.append("MOM-specific assistant claim requires manufacturing-domain corpus evidence.")
        if claim_type == "mom_only_replacement":
            reasons.append("MOM-only replacement is not allowed without explicit non-benchmark human approval.")
        if quality in {"benchmark_score_only", "score_only"} or ("benchmark" in scope and review != "passed"):
            reasons.append("Benchmark score alone cannot support a MOM-specific replacement or assistant claim.")
        if quality in {"weaker", "fail", "unknown"}:
            reasons.append("MOM-specific assistant quality is not sufficiently proven.")

    known_claims = {
        "general_notebooklm_replacement",
        "daily_replacement",
        "notebooklm_parity",
        "global_notebooklm_parity",
        "p1_opened",
        "p1_0_opened",
        "mom_specific_assistant",
        "mom_only_replacement",
    }
    if claim_type not in known_claims:
        reasons.append(f"Unknown claim type '{claim_type}' is blocked by default.")

    return ClaimReadiness(
        allowed=not reasons,
        claim_type=claim_type,
        reasons=reasons or ["Claim is allowed for the provided scope and evidence."],
    )
