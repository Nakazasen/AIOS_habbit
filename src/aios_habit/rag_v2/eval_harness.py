"""Generic evaluation harness for RAG v2 retrieval and evidence quality.

Measures retrieval hit rates, citation correctness, insufficiency detection,
privacy compliance, and latency using synthetic or private local fixtures.

This module is independent of legacy rag_benchmark, rag_evaluator, rag_search,
and query_intent modules.  It must not contain domain-specific terms.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from dataclasses import asdict, dataclass, field

from statistics import median
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .evidence import (
    EvidenceAnswerMode,
    EvidenceConfidence,
    EvidencePack,
    EvidencePackConfig,
    build_evidence_pack,
)
from .index import LocalChunkIndex, SearchOptions, SearchResponse
from .synthesis import (
    LocalSynthesisResult,
    synthesize_evidence,
    validate_grounded_claims,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BenchmarkConfig:
    """Thresholds and parameters for a benchmark run."""

    top_k: int = 10
    per_document_limit: int = 2
    min_retrieval_hit_rate: float = 0.8
    min_document_hit_rate: float = 0.9
    min_citation_source_hit_rate: float = 0.8
    min_insufficiency_detection_rate: float = 0.8
    min_grounded_answer_rate: float = 0.8
    min_citation_validity_rate: float = 1.0
    min_abstention_accuracy: float = 0.8
    min_privacy_pass_rate: float = 1.0
    min_local_execution_pass_rate: float = 1.0
    max_negative_control_false_support_rate: float = 0.0
    max_average_latency_ms: float = 500.0
    evidence_config: Optional[EvidencePackConfig] = None


# ---------------------------------------------------------------------------
# Question / Result / Summary types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BenchmarkQuestion:
    """One evaluation question with expected outcomes."""

    question_id: str
    question: str
    expected_answer_type: str  # "answerable" | "insufficient"
    expected_chunk_ids: Tuple[str, ...] = ()
    expected_document_ids: Tuple[str, ...] = ()
    expected_source_names: Tuple[str, ...] = ()
    required_sources: Tuple[str, ...] = ()
    required_spans: Tuple[str, ...] = ()
    required_facets: Tuple[str, ...] = ()
    expected_privacy: str = "any"  # "local_only" | "cloud_safe" | "any"
    forbidden_terms: Tuple[str, ...] = ()
    tags: Tuple[str, ...] = ()


@dataclass
class BenchmarkResult:
    """Scored outcome for one question."""

    question_id: str
    question: str
    expected_answer_type: str
    expected_target_defined: bool = False
    exact_identifier_target_defined: bool = False
    exact_identifier_hit: bool = False
    hit_expected_chunk: bool = False
    hit_expected_document: bool = False
    hit_expected_source: bool = False
    lexical_candidate_hit: bool = False
    dense_candidate_hit: bool = False
    fused_candidate_hit: bool = False
    fused_first_relevant_rank: int = 0
    reranked_first_relevant_rank: int = 0
    first_relevant_rank: int = 0
    reciprocal_rank: float = 0.0
    recall_at_5: bool = False
    recall_at_10: bool = False
    rerank_rank_delta: int = 0
    rerank_outcome: str = "not_applicable"
    insufficiency_detected: bool = False
    privacy_ok: bool = True
    forbidden_term_found: bool = False
    forbidden_terms_present: Tuple[str, ...] = ()
    evidence_confidence: str = "insufficient"
    evidence_item_count: int = 0
    top_score: float = 0.0
    synthesis_grounded: bool = False
    synthesis_abstained: bool = False
    citation_valid: bool = False
    local_execution_ok: bool = True
    synthesis_citation_ids: Tuple[str, ...] = ()
    synthesis_abstention_reasons: Tuple[str, ...] = ()
    retrieval_candidate_count: int = 0
    retrieval_result_count: int = 0
    lexical_pool_count: int = 0
    dense_pool_count: int = 0
    fused_pool_count: int = 0
    planned_facet_count: int = 0
    covered_facet_count: int = 0
    missing_facet_count: int = 0
    answer_mode: str = "abstain"
    final_evidence_term_coverage: float = 0.0
    planned_obligation_count: int = 0
    supported_obligation_count: int = 0
    missing_obligation_count: int = 0
    false_support: bool = False
    false_support_reason: str = ""
    hard_insufficiency_reasons: Tuple[str, ...] = ()
    soft_warning_reasons: Tuple[str, ...] = ()
    primary_error_class: str = ""
    secondary_error_classes: Tuple[str, ...] = ()
    lexical_latency_ms: float = 0.0
    dense_latency_ms: float = 0.0
    sparse_latency_ms: float = 0.0
    fusion_latency_ms: float = 0.0
    rerank_latency_ms: float = 0.0
    context_expansion_latency_ms: float = 0.0
    assembly_latency_ms: float = 0.0
    search_latency_ms: float = 0.0
    evidence_latency_ms: float = 0.0
    synthesis_latency_ms: float = 0.0
    latency_ms: float = 0.0


@dataclass
class BenchmarkSummary:
    """Aggregate metrics and PASS/FAIL verdict."""

    benchmark_id: str
    question_count: int
    answerable_count: int
    insufficient_count: int
    retrieval_hit_rate: float
    document_hit_rate: float
    citation_source_hit_rate: float
    insufficiency_detection_rate: float
    grounded_answer_rate: float
    citation_validity_rate: float
    abstention_accuracy: float
    privacy_pass_rate: float
    local_execution_pass_rate: float
    average_latency_ms: float
    pass_fail: str
    exact_identifier_target_count: int = 0
    exact_identifier_recall: float = 1.0
    lexical_candidate_recall: float = 1.0
    dense_candidate_recall: float = 1.0
    fused_candidate_recall: float = 1.0
    recall_at_5: float = 1.0
    recall_at_10: float = 1.0
    mrr_at_10: float = 1.0
    mean_first_relevant_rank: float = 0.0
    median_first_relevant_rank: float = 0.0
    negative_control_false_support_rate: float = 0.0
    average_lexical_latency_ms: float = 0.0
    average_dense_latency_ms: float = 0.0
    average_sparse_latency_ms: float = 0.0
    average_fusion_latency_ms: float = 0.0
    average_rerank_latency_ms: float = 0.0
    average_context_expansion_latency_ms: float = 0.0
    average_assembly_latency_ms: float = 0.0
    average_search_latency_ms: float = 0.0
    average_evidence_latency_ms: float = 0.0
    average_synthesis_latency_ms: float = 0.0
    error_class_counts: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    results: List[BenchmarkResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

_ERROR_PRIORITY = (
    "PRIVACY_OR_STALE_BREACH",
    "LATENCY_OR_RESOURCE_FAIL",
    "CANDIDATE_RECALL_MISS",
    "FUSION_MISS",
    "RERANKING_MISS",
    "ASSEMBLY_MISS",
    "RANKING_MISS",
    "FALSE_INSUFFICIENCY",
    "CITATION_MISS",
    "SYNTHESIS_COVERAGE_MISS",
    "UNSUPPORTED_CLAIM",
)


def _identity_matches(question: BenchmarkQuestion, identity: Sequence[str]) -> bool:
    """Match the most specific available expected identity without source content."""
    chunk_id, document_id, source_name = identity
    if question.expected_chunk_ids:
        return chunk_id in question.expected_chunk_ids
    if question.expected_document_ids:
        return document_id in question.expected_document_ids
    if question.expected_source_names:
        return source_name in question.expected_source_names
    return False


def _first_relevant_rank(
    question: BenchmarkQuestion,
    identities: Sequence[Sequence[str]],
) -> int:
    return next(
        (rank for rank, identity in enumerate(identities, 1) if _identity_matches(question, identity)),
        0,
    )


def _exact_identifier_matches(
    question: BenchmarkQuestion,
    identity: Sequence[str],
) -> bool:
    """Match an explicit document ID, or a source name when no document ID exists."""
    _chunk_id, document_id, source_name = identity
    if question.expected_document_ids:
        return document_id in question.expected_document_ids
    if question.expected_source_names:
        return source_name in question.expected_source_names
    return False


def _exact_identifier_rank(
    question: BenchmarkQuestion,
    identities: Sequence[Sequence[str]],
) -> int:
    return next(
        (
            rank
            for rank, identity in enumerate(identities, 1)
            if _exact_identifier_matches(question, identity)
        ),
        0,
    )


def _classify_observable_failures(
    question: BenchmarkQuestion,
    *,
    hit_chunk: bool,
    hit_doc: bool,
    hit_source: bool,
    lexical_candidate_hit: bool,
    dense_candidate_hit: bool,
    fused_candidate_hit: bool,
    reranked_candidate_hit: bool,
    assembly_rejected_hit: bool,
    final_target_hit: bool,
    privacy_ok: bool,
    forbidden_found: bool,
    pack: EvidencePack,
    synthesis: LocalSynthesisResult,
    citation_valid: bool,
    local_execution_ok: bool,
) -> tuple[str, Tuple[str, ...]]:
    """Attribute observable failures to the earliest retrieval or answer stage."""
    classes: set[str] = set()
    if not privacy_ok or forbidden_found:
        classes.add("PRIVACY_OR_STALE_BREACH")
    if not local_execution_ok:
        classes.add("LATENCY_OR_RESOURCE_FAIL")

    if question.expected_answer_type == "answerable":
        expected_target_missed = any((
            bool(question.expected_chunk_ids) and not hit_chunk,
            bool(question.expected_document_ids) and not hit_doc,
            bool(question.expected_source_names) and not hit_source,
        ))
        if expected_target_missed:
            if not (lexical_candidate_hit or dense_candidate_hit):
                classes.add("CANDIDATE_RECALL_MISS")
            elif not fused_candidate_hit:
                classes.add("FUSION_MISS")
            elif not reranked_candidate_hit:
                classes.add("RERANKING_MISS")
            elif assembly_rejected_hit:
                classes.add("ASSEMBLY_MISS")
            elif not final_target_hit:
                classes.add("RANKING_MISS")
        elif pack.answer_mode == EvidenceAnswerMode.ABSTAIN:
            classes.add("FALSE_INSUFFICIENCY")

        if not citation_valid and not synthesis.abstained:
            classes.add("CITATION_MISS")
        if not synthesis.grounded and not synthesis.abstained:
            classes.add("SYNTHESIS_COVERAGE_MISS")
    elif not synthesis.abstained or synthesis.grounded:
        classes.add("UNSUPPORTED_CLAIM")

    ordered = tuple(code for code in _ERROR_PRIORITY if code in classes)
    if not ordered:
        return "", ()
    return ordered[0], ordered[1:]


def score_question(
    question: BenchmarkQuestion,
    response: SearchResponse,
    pack: EvidencePack,
    latency_ms: float,
    synthesis: Optional[LocalSynthesisResult] = None,
    *,
    search_latency_ms: float = 0.0,
    evidence_latency_ms: float = 0.0,
    synthesis_latency_ms: float = 0.0,
) -> BenchmarkResult:
    """Score retrieval, evidence, and local synthesis against expectations."""
    synthesis = synthesis or synthesize_evidence(pack)
    retrieved_chunks = {r.chunk_id for r in response.results}
    retrieved_docs = {r.document_id for r in response.results}
    retrieved_sources = {r.source_name for r in response.results}
    summary = response.summary
    final_pool = tuple((r.chunk_id, r.document_id, r.source_name) for r in response.results)
    lexical_candidate_hit = _first_relevant_rank(question, summary.lexical_pool) > 0
    dense_candidate_hit = _first_relevant_rank(question, summary.dense_pool) > 0
    fused_first_rank = _first_relevant_rank(question, summary.fused_pool)
    reranked_first_rank = _first_relevant_rank(question, summary.ranked_pool)
    final_first_rank = _first_relevant_rank(question, final_pool)
    exact_identifier_rank = _exact_identifier_rank(question, final_pool)
    exact_identifier_target_defined = bool(
        question.expected_document_ids or question.expected_source_names
    )
    fused_candidate_hit = fused_first_rank > 0
    reranked_candidate_hit = reranked_first_rank > 0
    assembly_rejected_hit = _first_relevant_rank(question, summary.assembly_rejected_pool) > 0
    final_target_hit = final_first_rank > 0
    reciprocal_rank = 1.0 / final_first_rank if 0 < final_first_rank <= 10 else 0.0
    if fused_first_rank and reranked_first_rank:
        rerank_delta = fused_first_rank - reranked_first_rank
        rerank_outcome = "gain" if rerank_delta > 0 else "loss" if rerank_delta < 0 else "stable"
    else:
        rerank_delta = 0
        rerank_outcome = "not_applicable"

    hit_chunk = bool(
        question.expected_chunk_ids
        and retrieved_chunks & set(question.expected_chunk_ids)
    )
    hit_doc = bool(
        question.expected_document_ids
        and retrieved_docs & set(question.expected_document_ids)
    )
    hit_source = bool(
        question.expected_source_names
        and retrieved_sources & set(question.expected_source_names)
    )

    # Insufficiency detection: for "insufficient" questions, the pack should
    # report insufficient confidence or non-empty insufficiency reasons.
    insufficiency_detected = (
        pack.confidence == EvidenceConfidence.INSUFFICIENT
        or bool(pack.insufficiency_reasons)
    )

    # Privacy check: strictest-wins is always acceptable.
    privacy_ok = True
    if question.expected_privacy == "local_only":
        privacy_ok = pack.privacy_summary.local_only
    elif question.expected_privacy == "cloud_safe":
        # cloud_safe expectation is satisfied by either cloud_safe or local_only
        privacy_ok = True

    # Forbidden terms are checked across both supplied evidence and synthesized answer.
    forbidden_found: List[str] = []
    if question.forbidden_terms:
        all_text = " ".join(
            [*(item.snippet.lower() for item in pack.items), synthesis.answer.lower()]
        )
        for term in question.forbidden_terms:
            if term.lower() in all_text:
                forbidden_found.append(term)

    citation_errors = validate_grounded_claims(pack, synthesis.claims)
    known_citations = {item.citation_id for item in pack.items}
    citation_valid = (
        not citation_errors
        and all(citation in known_citations for citation in synthesis.citation_ids)
        and (
            synthesis.abstained
            or (synthesis.grounded and bool(synthesis.citation_ids))
        )
    )
    local_execution_ok = not synthesis.provider_used
    false_support = bool(
        question.expected_answer_type == "insufficient"
        and (
            synthesis.grounded
            or not synthesis.abstained
            or synthesis.claims
            or synthesis.citation_ids
        )
    )
    false_support_reason = (
        "insufficient_question_material_answer" if false_support else ""
    )
    primary_error_class, secondary_error_classes = _classify_observable_failures(
        question,
        hit_chunk=hit_chunk,
        hit_doc=hit_doc,
        hit_source=hit_source,
        lexical_candidate_hit=lexical_candidate_hit,
        dense_candidate_hit=dense_candidate_hit,
        fused_candidate_hit=fused_candidate_hit,
        reranked_candidate_hit=reranked_candidate_hit,
        assembly_rejected_hit=assembly_rejected_hit,
        final_target_hit=final_target_hit,
        privacy_ok=privacy_ok,
        forbidden_found=bool(forbidden_found),
        pack=pack,
        synthesis=synthesis,
        citation_valid=citation_valid,
        local_execution_ok=local_execution_ok,
    )

    return BenchmarkResult(
        question_id=question.question_id,
        question=question.question,
        expected_answer_type=question.expected_answer_type,
        expected_target_defined=bool(
            question.expected_chunk_ids
            or question.expected_document_ids
            or question.expected_source_names
        ),
        exact_identifier_target_defined=exact_identifier_target_defined,
        exact_identifier_hit=(
            exact_identifier_target_defined and 0 < exact_identifier_rank <= 10
        ),
        hit_expected_chunk=hit_chunk,
        hit_expected_document=hit_doc,
        hit_expected_source=hit_source,
        lexical_candidate_hit=lexical_candidate_hit,
        dense_candidate_hit=dense_candidate_hit,
        fused_candidate_hit=fused_candidate_hit,
        fused_first_relevant_rank=fused_first_rank,
        reranked_first_relevant_rank=reranked_first_rank,
        first_relevant_rank=final_first_rank,
        reciprocal_rank=reciprocal_rank,
        recall_at_5=0 < final_first_rank <= 5,
        recall_at_10=0 < final_first_rank <= 10,
        rerank_rank_delta=rerank_delta,
        rerank_outcome=rerank_outcome,
        insufficiency_detected=insufficiency_detected,
        privacy_ok=privacy_ok,
        forbidden_term_found=bool(forbidden_found),
        forbidden_terms_present=tuple(forbidden_found),
        evidence_confidence=pack.confidence.value,
        evidence_item_count=pack.item_count,
        top_score=pack.top_score,
        synthesis_grounded=synthesis.grounded,
        synthesis_abstained=synthesis.abstained,
        citation_valid=citation_valid,
        local_execution_ok=local_execution_ok,
        synthesis_citation_ids=synthesis.citation_ids,
        synthesis_abstention_reasons=synthesis.abstention_reasons,
        retrieval_candidate_count=response.summary.candidate_count,
        retrieval_result_count=len(response.results),
        lexical_pool_count=len(summary.lexical_pool),
        dense_pool_count=len(summary.dense_pool),
        fused_pool_count=len(summary.fused_pool),
        planned_facet_count=len(pack.coverage_map),
        covered_facet_count=sum(
            facet.status == "covered" for facet in pack.coverage_map
        ),
        missing_facet_count=sum(
            facet.status == "missing" for facet in pack.coverage_map
        ),
        answer_mode=pack.answer_mode.value,
        final_evidence_term_coverage=pack.final_evidence_term_coverage,
        planned_obligation_count=len(pack.obligation_coverage_map),
        supported_obligation_count=sum(
            obligation.status == "covered"
            for obligation in pack.obligation_coverage_map
        ),
        missing_obligation_count=sum(
            obligation.status == "missing"
            for obligation in pack.obligation_coverage_map
        ),
        false_support=false_support,
        false_support_reason=false_support_reason,
        hard_insufficiency_reasons=pack.hard_insufficiency_reasons,
        soft_warning_reasons=pack.soft_warning_reasons,
        primary_error_class=primary_error_class,
        secondary_error_classes=secondary_error_classes,
        lexical_latency_ms=summary.lexical_latency_ms,
        dense_latency_ms=summary.dense_latency_ms,
        sparse_latency_ms=summary.sparse_latency_ms,
        fusion_latency_ms=summary.fusion_latency_ms,
        rerank_latency_ms=summary.rerank_latency_ms,
        context_expansion_latency_ms=summary.context_expansion_latency_ms,
        assembly_latency_ms=summary.assembly_latency_ms,
        search_latency_ms=search_latency_ms,
        evidence_latency_ms=evidence_latency_ms,
        synthesis_latency_ms=synthesis_latency_ms,
        latency_ms=latency_ms,
    )


def summarize_results(
    results: List[BenchmarkResult],
    config: BenchmarkConfig,
) -> BenchmarkSummary:
    """Aggregate per-question results into metrics and PASS/FAIL verdict."""
    answerable = [r for r in results if r.expected_answer_type == "answerable"]
    insufficient = [r for r in results if r.expected_answer_type == "insufficient"]

    q_count = len(results)
    ans_count = len(answerable)
    ins_count = len(insufficient)

    retrieval_hit = (
        sum(1 for r in answerable if r.hit_expected_chunk or r.hit_expected_document)
        / ans_count
        if ans_count > 0
        else 1.0
    )
    doc_hit = (
        sum(1 for r in answerable if r.hit_expected_document) / ans_count
        if ans_count > 0
        else 1.0
    )
    source_hit = (
        sum(1 for r in answerable if r.hit_expected_source) / ans_count
        if ans_count > 0
        else 1.0
    )
    insuf_detection = (
        sum(1 for r in insufficient if r.insufficiency_detected) / ins_count
        if ins_count > 0
        else 1.0
    )
    grounded_rate = (
        sum(1 for r in answerable if r.synthesis_grounded and not r.synthesis_abstained)
        / ans_count
        if ans_count > 0
        else 1.0
    )
    citation_validity = (
        sum(1 for r in answerable if r.citation_valid) / ans_count
        if ans_count > 0
        else 1.0
    )
    abstention_accuracy = (
        sum(1 for r in insufficient if r.synthesis_abstained and not r.synthesis_grounded)
        / ins_count
        if ins_count > 0
        else 1.0
    )
    privacy_pass = (
        sum(1 for r in results if r.privacy_ok) / q_count if q_count > 0 else 1.0
    )
    local_execution_pass = (
        sum(1 for r in results if r.local_execution_ok) / q_count
        if q_count > 0
        else 1.0
    )
    avg_latency = (
        sum(r.latency_ms for r in results) / q_count if q_count > 0 else 0.0
    )
    target_answerable = [
        result for result in answerable if result.expected_target_defined
    ]
    target_count = len(target_answerable)
    exact_identifier_answerable = [
        result
        for result in answerable
        if result.exact_identifier_target_defined
    ]
    exact_identifier_target_count = len(exact_identifier_answerable)
    exact_identifier_recall = (
        sum(1 for result in exact_identifier_answerable if result.exact_identifier_hit)
        / exact_identifier_target_count
        if exact_identifier_target_count
        else 1.0
    )
    channel_rate = lambda attribute: (
        sum(1 for result in target_answerable if getattr(result, attribute)) / target_count
        if target_count else 1.0
    )
    lexical_candidate_recall = channel_rate("lexical_candidate_hit")
    dense_candidate_recall = channel_rate("dense_candidate_hit")
    fused_candidate_recall = channel_rate("fused_candidate_hit")
    recall_at_5 = channel_rate("recall_at_5")
    recall_at_10 = channel_rate("recall_at_10")
    mrr_at_10 = (
        sum(result.reciprocal_rank for result in target_answerable) / target_count
        if target_count else 1.0
    )
    relevant_ranks = [result.first_relevant_rank for result in target_answerable if result.first_relevant_rank]
    mean_first_rank = sum(relevant_ranks) / len(relevant_ranks) if relevant_ranks else 0.0
    median_first_rank = float(median(relevant_ranks)) if relevant_ranks else 0.0
    false_support_rate = (
        sum(1 for result in insufficient if result.false_support)
        / ins_count
        if ins_count else 0.0
    )
    average = lambda attribute: (
        sum(float(getattr(result, attribute)) for result in results) / q_count if q_count else 0.0
    )
    error_class_counts: Dict[str, int] = {}
    for result in results:
        for error_class in (result.primary_error_class, *result.secondary_error_classes):
            if error_class:
                error_class_counts[error_class] = error_class_counts.get(error_class, 0) + 1

    warnings: List[str] = []
    if retrieval_hit < config.min_retrieval_hit_rate:
        warnings.append(
            f"Retrieval hit rate {retrieval_hit:.2f} < {config.min_retrieval_hit_rate}"
        )
    if doc_hit < config.min_document_hit_rate:
        warnings.append(
            f"Document hit rate {doc_hit:.2f} < {config.min_document_hit_rate}"
        )
    if source_hit < config.min_citation_source_hit_rate:
        warnings.append(
            f"Citation source hit rate {source_hit:.2f} < {config.min_citation_source_hit_rate}"
        )
    if insuf_detection < config.min_insufficiency_detection_rate:
        warnings.append(
            f"Insufficiency detection rate {insuf_detection:.2f} < {config.min_insufficiency_detection_rate}"
        )
    if grounded_rate < config.min_grounded_answer_rate:
        warnings.append(
            f"Grounded answer rate {grounded_rate:.2f} < {config.min_grounded_answer_rate}"
        )
    if citation_validity < config.min_citation_validity_rate:
        warnings.append(
            f"Citation validity rate {citation_validity:.2f} < {config.min_citation_validity_rate}"
        )
    if abstention_accuracy < config.min_abstention_accuracy:
        warnings.append(
            f"Abstention accuracy {abstention_accuracy:.2f} < {config.min_abstention_accuracy}"
        )
    if privacy_pass < config.min_privacy_pass_rate:
        warnings.append(
            f"Privacy pass rate {privacy_pass:.2f} < {config.min_privacy_pass_rate}"
        )
    if local_execution_pass < config.min_local_execution_pass_rate:
        warnings.append(
            f"Local execution pass rate {local_execution_pass:.2f} < {config.min_local_execution_pass_rate}"
        )
    if false_support_rate > config.max_negative_control_false_support_rate:
        warnings.append(
            "Negative-control false support rate "
            f"{false_support_rate:.2f} > {config.max_negative_control_false_support_rate}"
        )
    if avg_latency > config.max_average_latency_ms:
        warnings.append(
            f"Average latency {avg_latency:.2f}ms > {config.max_average_latency_ms}ms"
        )

    quality_failed = any((
        retrieval_hit < config.min_retrieval_hit_rate,
        doc_hit < config.min_document_hit_rate,
        source_hit < config.min_citation_source_hit_rate,
        insuf_detection < config.min_insufficiency_detection_rate,
        grounded_rate < config.min_grounded_answer_rate,
        citation_validity < config.min_citation_validity_rate,
        abstention_accuracy < config.min_abstention_accuracy,
        false_support_rate > config.max_negative_control_false_support_rate,
        privacy_pass < config.min_privacy_pass_rate,
        local_execution_pass < config.min_local_execution_pass_rate,
    ))
    if quality_failed:
        pass_fail = "FAIL"
    elif warnings:
        pass_fail = "PASS_WITH_WARNINGS"
    else:
        pass_fail = "PASS"

    return BenchmarkSummary(
        benchmark_id="",
        question_count=q_count,
        answerable_count=ans_count,
        insufficient_count=ins_count,
        retrieval_hit_rate=retrieval_hit,
        document_hit_rate=doc_hit,
        citation_source_hit_rate=source_hit,
        insufficiency_detection_rate=insuf_detection,
        grounded_answer_rate=grounded_rate,
        citation_validity_rate=citation_validity,
        abstention_accuracy=abstention_accuracy,
        privacy_pass_rate=privacy_pass,
        local_execution_pass_rate=local_execution_pass,
        average_latency_ms=avg_latency,
        pass_fail=pass_fail,
        exact_identifier_target_count=exact_identifier_target_count,
        exact_identifier_recall=exact_identifier_recall,
        lexical_candidate_recall=lexical_candidate_recall,
        dense_candidate_recall=dense_candidate_recall,
        fused_candidate_recall=fused_candidate_recall,
        recall_at_5=recall_at_5,
        recall_at_10=recall_at_10,
        mrr_at_10=mrr_at_10,
        mean_first_relevant_rank=mean_first_rank,
        median_first_relevant_rank=median_first_rank,
        negative_control_false_support_rate=false_support_rate,
        average_lexical_latency_ms=average("lexical_latency_ms"),
        average_dense_latency_ms=average("dense_latency_ms"),
        average_sparse_latency_ms=average("sparse_latency_ms"),
        average_fusion_latency_ms=average("fusion_latency_ms"),
        average_rerank_latency_ms=average("rerank_latency_ms"),
        average_context_expansion_latency_ms=average("context_expansion_latency_ms"),
        average_assembly_latency_ms=average("assembly_latency_ms"),
        average_search_latency_ms=average("search_latency_ms"),
        average_evidence_latency_ms=average("evidence_latency_ms"),
        average_synthesis_latency_ms=average("synthesis_latency_ms"),
        error_class_counts=error_class_counts,
        warnings=warnings,
        results=results,
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _stable_benchmark_id(
    questions: List[BenchmarkQuestion], config: BenchmarkConfig
) -> str:
    payload = {
        "config": {
            "top_k": config.top_k,
            "per_document_limit": config.per_document_limit,
            "min_retrieval_hit_rate": config.min_retrieval_hit_rate,
            "min_document_hit_rate": config.min_document_hit_rate,
            "min_citation_source_hit_rate": config.min_citation_source_hit_rate,
            "min_insufficiency_detection_rate": config.min_insufficiency_detection_rate,
            "min_grounded_answer_rate": config.min_grounded_answer_rate,
            "min_citation_validity_rate": config.min_citation_validity_rate,
            "min_abstention_accuracy": config.min_abstention_accuracy,
            "min_privacy_pass_rate": config.min_privacy_pass_rate,
            "min_local_execution_pass_rate": config.min_local_execution_pass_rate,
            "max_average_latency_ms": config.max_average_latency_ms,
        },
        "questions": [
            {
                "id": q.question_id,
                "q": q.question,
                "type": q.expected_answer_type,
                "chunks": list(q.expected_chunk_ids),
                "docs": list(q.expected_document_ids),
                "sources": list(q.expected_source_names),
                "req_sources": list(q.required_sources),
                "req_spans": list(q.required_spans),
                "req_facets": list(q.required_facets),
            }
            for q in questions
        ],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"BMK-{hashlib.sha256(raw).hexdigest()[:10].upper()}"


def run_benchmark(
    index: LocalChunkIndex,
    questions: List[BenchmarkQuestion],
    config: Optional[BenchmarkConfig] = None,
) -> BenchmarkSummary:
    """Run all benchmark questions against a pre-built index."""
    if config is None:
        config = BenchmarkConfig()

    ev_config = config.evidence_config or EvidencePackConfig(
        per_document_limit=config.per_document_limit,
    )
    search_options = SearchOptions(
        candidate_limit=config.top_k,
        per_document_limit=config.per_document_limit,
    )

    results: List[BenchmarkResult] = []
    for question in questions:
        t0 = time.perf_counter()
        search_started = time.perf_counter()
        response = index.search_with_summary(
            question.question, limit=config.top_k, options=search_options
        )
        search_latency_ms = (time.perf_counter() - search_started) * 1000.0
        evidence_started = time.perf_counter()
        pack = build_evidence_pack(question.question, response, config=ev_config)
        evidence_latency_ms = (time.perf_counter() - evidence_started) * 1000.0
        synthesis_started = time.perf_counter()
        synthesis = synthesize_evidence(pack)
        synthesis_latency_ms = (time.perf_counter() - synthesis_started) * 1000.0
        latency_ms = (time.perf_counter() - t0) * 1000.0

        result = score_question(
            question,
            response,
            pack,
            latency_ms,
            synthesis=synthesis,
            search_latency_ms=search_latency_ms,
            evidence_latency_ms=evidence_latency_ms,
            synthesis_latency_ms=synthesis_latency_ms,
        )
        results.append(result)

    summary = summarize_results(results, config)
    summary.benchmark_id = _stable_benchmark_id(questions, config)
    return summary


# ---------------------------------------------------------------------------
# Formatting and serialization
# ---------------------------------------------------------------------------

def format_benchmark_summary(summary: BenchmarkSummary) -> str:
    """Human-readable text report of benchmark results."""
    lines = [
        f"RAG v2 Benchmark Summary: {summary.benchmark_id}",
        f"Result: {summary.pass_fail}",
        "Note: Measures retrieval, evidence, and local deterministic synthesis quality; not LLM generation.",
        f"Questions: {summary.question_count} "
        f"({summary.answerable_count} answerable, "
        f"{summary.insufficient_count} insufficient)",
        "Metrics:",
        f"  - Retrieval Hit Rate: {summary.retrieval_hit_rate:.2f}",
        f"  - Lexical Candidate Recall: {summary.lexical_candidate_recall:.2f}",
        f"  - Dense Candidate Recall: {summary.dense_candidate_recall:.2f}",
        f"  - Fused Candidate Recall: {summary.fused_candidate_recall:.2f}",
        f"  - Recall@5 / Recall@10: {summary.recall_at_5:.2f} / {summary.recall_at_10:.2f}",
        f"  - MRR@10: {summary.mrr_at_10:.3f}",
        f"  - Mean / Median First Relevant Rank: {summary.mean_first_relevant_rank:.2f} / {summary.median_first_relevant_rank:.2f}",
        f"  - Negative-Control False Support: {summary.negative_control_false_support_rate:.2f}",
        f"  - Document Hit Rate: {summary.document_hit_rate:.2f}",
        f"  - Citation Source Hit Rate: {summary.citation_source_hit_rate:.2f}",
        f"  - Insufficiency Detection: {summary.insufficiency_detection_rate:.2f}",
        f"  - Grounded Answer Rate: {summary.grounded_answer_rate:.2f}",
        f"  - Citation Validity Rate: {summary.citation_validity_rate:.2f}",
        f"  - Abstention Accuracy: {summary.abstention_accuracy:.2f}",
        f"  - Privacy Pass Rate: {summary.privacy_pass_rate:.2f}",
        f"  - Local Execution Pass Rate: {summary.local_execution_pass_rate:.2f}",
        f"  - Avg Latency: {summary.average_latency_ms:.2f} ms",
        f"  - Avg Search / Evidence / Synthesis: {summary.average_search_latency_ms:.2f} / {summary.average_evidence_latency_ms:.2f} / {summary.average_synthesis_latency_ms:.2f} ms",
    ]
    if summary.warnings:
        lines.append("Warnings:")
        for w in summary.warnings:
            lines.append(f"  - {w}")
    return "\n".join(lines)


def benchmark_summary_to_dict(summary: BenchmarkSummary) -> Dict[str, Any]:
    """JSON-compatible plain dict serialization."""
    raw = asdict(summary)
    # Convert any tuple leftovers to lists
    def _listify(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _listify(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_listify(i) for i in obj]
        return obj

    return _listify(raw)


def generate_adaptive_audit_report(
    fixtures_path: Optional[str | Path] = None,
    output_path: Optional[str | Path] = None,
    policy_version: str = "adaptive-reranking-v1",
) -> dict[str, Any]:
    """Evaluate the 60-query adaptive retrieval benchmark and generate an audit report."""
    from datetime import datetime, timezone
    import hashlib
    from aios_habit.rag_v2.adaptive_retrieval import (
        AdaptiveRetrievalPolicy,
        PostDecision,
        PreDecision,
        decide_final_route,
        decide_initial_route,
        post_retrieval_gate,
        pre_retrieval_gate,
    )

    from aios_habit.rag_v2.index import SearchSummary
    from aios_habit.rag_v2.query_planning import RetrievalQueryPlan, RetrievalQueryVariant

    path = Path(fixtures_path or "tests/fixtures/adaptive_routing_cases.json")
    from scripts.benchmark_adaptive_reranking import run_benchmark
    return run_benchmark(
        fixture_path=path,
        output_path=Path(output_path) if output_path is not None else None,
        policy_version=policy_version,
    )
