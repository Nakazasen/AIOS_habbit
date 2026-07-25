"""Generic evaluation harness for RAG v2 retrieval and evidence quality.

Measures retrieval hit rates, citation correctness, insufficiency detection,
privacy compliance, and latency using synthetic or private local fixtures.

This module is independent of legacy rag_benchmark, rag_evaluator, rag_search,
and query_intent modules.  It must not contain domain-specific terms.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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
    hit_expected_chunk: bool = False
    hit_expected_document: bool = False
    hit_expected_source: bool = False
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
    planned_facet_count: int = 0
    covered_facet_count: int = 0
    missing_facet_count: int = 0
    answer_mode: str = "abstain"
    hard_insufficiency_reasons: Tuple[str, ...] = ()
    soft_warning_reasons: Tuple[str, ...] = ()
    primary_error_class: str = ""
    secondary_error_classes: Tuple[str, ...] = ()
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
    warnings: List[str] = field(default_factory=list)
    results: List[BenchmarkResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

_ERROR_PRIORITY = (
    "PRIVACY_OR_STALE_BREACH",
    "LATENCY_OR_RESOURCE_FAIL",
    "CANDIDATE_RECALL_MISS",
    "FALSE_INSUFFICIENCY",
    "CITATION_MISS",
    "SYNTHESIS_COVERAGE_MISS",
    "UNSUPPORTED_CLAIM",
)


def _classify_observable_failures(
    question: BenchmarkQuestion,
    *,
    hit_chunk: bool,
    hit_doc: bool,
    hit_source: bool,
    privacy_ok: bool,
    forbidden_found: bool,
    pack: EvidencePack,
    synthesis: LocalSynthesisResult,
    citation_valid: bool,
    local_execution_ok: bool,
) -> tuple[str, Tuple[str, ...]]:
    """Classify only failures that the current harness can observe reliably.

    Retrieval output does not yet expose pre-rerank gold membership, so a missing
    expected target is conservatively attributed to CANDIDATE_RECALL_MISS. Gate 2
    candidate provenance will split this into candidate, ranking, and assembly misses.
    """
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
            classes.add("CANDIDATE_RECALL_MISS")
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
) -> BenchmarkResult:
    """Score retrieval, evidence, and local synthesis against expectations."""
    synthesis = synthesis or synthesize_evidence(pack)
    retrieved_chunks = {r.chunk_id for r in response.results}
    retrieved_docs = {r.document_id for r in response.results}
    retrieved_sources = {r.source_name for r in response.results}

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
    primary_error_class, secondary_error_classes = _classify_observable_failures(
        question,
        hit_chunk=hit_chunk,
        hit_doc=hit_doc,
        hit_source=hit_source,
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
        hit_expected_chunk=hit_chunk,
        hit_expected_document=hit_doc,
        hit_expected_source=hit_source,
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
        planned_facet_count=len(response.summary.planned_facet_ids),
        covered_facet_count=len(response.summary.covered_facet_ids),
        missing_facet_count=len(response.summary.missing_facet_ids),
        answer_mode=pack.answer_mode.value,
        hard_insufficiency_reasons=pack.hard_insufficiency_reasons,
        soft_warning_reasons=pack.soft_warning_reasons,
        primary_error_class=primary_error_class,
        secondary_error_classes=secondary_error_classes,
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
        response = index.search_with_summary(
            question.question, limit=config.top_k, options=search_options
        )
        pack = build_evidence_pack(question.question, response, config=ev_config)
        synthesis = synthesize_evidence(pack)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        result = score_question(
            question,
            response,
            pack,
            latency_ms,
            synthesis=synthesis,
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
        f"  - Document Hit Rate: {summary.document_hit_rate:.2f}",
        f"  - Citation Source Hit Rate: {summary.citation_source_hit_rate:.2f}",
        f"  - Insufficiency Detection: {summary.insufficiency_detection_rate:.2f}",
        f"  - Grounded Answer Rate: {summary.grounded_answer_rate:.2f}",
        f"  - Citation Validity Rate: {summary.citation_validity_rate:.2f}",
        f"  - Abstention Accuracy: {summary.abstention_accuracy:.2f}",
        f"  - Privacy Pass Rate: {summary.privacy_pass_rate:.2f}",
        f"  - Local Execution Pass Rate: {summary.local_execution_pass_rate:.2f}",
        f"  - Avg Latency: {summary.average_latency_ms:.2f} ms",
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
