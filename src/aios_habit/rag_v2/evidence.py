"""Generic evidence pack builder for RAG v2 retrieval results.

Converts SearchResponse results into structured evidence packs with citations,
confidence assessment, insufficiency handling, and prompt-ready text format.

This module is intentionally independent of legacy rag_evidence, rag_search,
and query_intent modules.  It must not contain domain-specific terms.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .index import SearchResponse, SearchResult, SearchSummary
from .query_planning import (
    RetrievalQueryPlan,
    coerce_query_plan,
    extract_content_terms,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvidencePackConfig:
    """Tunable thresholds for evidence pack construction."""

    max_items: int = 15
    min_items_for_sufficient: int = 1
    min_top_score: float = 0.1
    min_term_coverage: float = 0.3
    min_final_evidence_term_coverage: float = 0.6
    min_semantic_support_score: float = 0.55
    max_snippet_chars: int = 1500
    per_document_limit: int = 3
    high_score_threshold: float = 8.0
    medium_score_threshold: float = 3.0

    def __post_init__(self) -> None:
        if self.max_items < 1:
            raise ValueError("max_items must be at least 1")
        if not 0.0 <= self.min_final_evidence_term_coverage <= 1.0:
            raise ValueError("min_final_evidence_term_coverage must be between 0 and 1")
        if not -1.0 <= self.min_semantic_support_score <= 1.0:
            raise ValueError("min_semantic_support_score must be between -1 and 1")
        if self.max_snippet_chars < 1:
            raise ValueError("max_snippet_chars must be at least 1")


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class EvidenceConfidence(str, Enum):
    """Overall confidence assessment for an evidence pack."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class EvidenceAnswerMode(str, Enum):
    """Operational decision separated from diagnostic confidence."""

    ANSWER = "answer"
    ANSWER_WITH_LIMITS = "answer_with_limits"
    ABSTAIN = "abstain"


_SOFT_WARNING_REASON_CODES = frozenset({
    "incomplete_query_term_coverage",
    "weak_query_term_coverage",
    "top_score_below_threshold",
    "too_few_evidence_items",
    "weak_term_coverage",
    "missing_required_obligations",
    "cross_lingual_structural_corroboration",
    "cross_lingual_target_equivalent_corroboration",
    "expansion_unavailable",
    "expansion_rejected",
})


@dataclass(frozen=True)
class EvidenceItem:
    """One ranked evidence excerpt with citation and provenance."""

    evidence_id: str
    citation_id: str
    citation_label: str
    chunk_id: str
    document_id: str
    source_name: str
    source_path: str
    file_type: str
    text: str
    snippet: str
    score: float
    rank: int
    ranking_signals: Dict[str, float]
    matched_terms: Tuple[str, ...]
    term_coverage: float
    privacy_labels: Tuple[str, ...]
    element_types: Tuple[str, ...] = ()
    page: Optional[int] = None
    sheet: Optional[str] = None
    slide: Optional[int] = None
    row_range: Optional[Tuple[int, int]] = None
    column_range: Optional[Tuple[int, int]] = None
    cell_range: Optional[str] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    section_path: Tuple[str, ...] = ()
    matched_query_variant_ids: Tuple[str, ...] = ()
    matched_target_equivalent_variant_ids: Tuple[str, ...] = ()
    matched_query_facets: Tuple[str, ...] = ()
    matched_obligations: Tuple[str, ...] = ()
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceFacetCoverage:
    """Privacy-safe evidence coverage for one stable query facet."""

    facet_id: str
    status: str
    evidence_ids: Tuple[str, ...]
    citation_ids: Tuple[str, ...]
    document_count: int


@dataclass(frozen=True)
class EvidenceObligationCoverage:
    """Privacy-safe evidence coverage for one stable answer obligation."""

    obligation_id: str
    status: str
    evidence_ids: Tuple[str, ...]
    citation_ids: Tuple[str, ...]
    document_count: int


@dataclass(frozen=True)
class PrivacySummary:
    """Strictest-wins privacy assessment across all evidence items."""

    overall_label: str
    local_only: bool
    cloud_allowed: bool
    labels_present: Tuple[str, ...]


@dataclass(frozen=True)
class EvidenceRelevanceTelemetry:
    """Content-free diagnostics for lexical/semantic relevance decisions."""

    lexical_coverage: float
    lexical_threshold: float
    lexical_passed: bool
    semantic_threshold: float
    semantic_max_score: float
    selected_item_count: int
    dense_score_item_count: int
    dense_channel_item_count: int
    current_variant_item_count: int
    qualifying_semantic_item_count: int
    semantic_rejection_reasons: Tuple[str, ...]
    cross_lingual_structural_supported: bool
    cross_lingual_required_facet_count: int
    cross_lingual_covered_facet_count: int
    cross_lingual_document_count: int
    cross_lingual_rejection_reasons: Tuple[str, ...]
    cross_lingual_target_equivalent_supported: bool
    cross_lingual_target_equivalent_item_count: int
    cross_lingual_target_equivalent_rejection_reasons: Tuple[str, ...]


@dataclass(frozen=True)
class EvidencePack:
    """Collection of ranked, cited evidence items with quality metadata."""

    pack_id: str
    query: str
    items: Tuple[EvidenceItem, ...]
    confidence: EvidenceConfidence
    privacy_summary: PrivacySummary
    insufficiency_reasons: Tuple[str, ...]
    hard_insufficiency_reasons: Tuple[str, ...]
    soft_warning_reasons: Tuple[str, ...]
    answer_mode: EvidenceAnswerMode
    retrieval_summary: SearchSummary
    coverage_map: Tuple[EvidenceFacetCoverage, ...]
    obligation_coverage_map: Tuple[EvidenceObligationCoverage, ...]
    source_count: int
    document_count: int
    item_count: int
    top_score: float
    best_term_coverage: float
    final_evidence_term_coverage: float
    semantic_support_score: float
    semantic_support_used: bool
    relevance_gate_basis: str
    relevance_telemetry: EvidenceRelevanceTelemetry
    supported_obligation_count: int
    planned_obligation_count: int
    created_at: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_BLOCKED_PRIVACY_LABELS = frozenset({"local_only", "confidential"})


def _stable_pack_id(query: str, results: Tuple[SearchResult, ...]) -> str:
    parts = [query]
    for r in results:
        parts.append(f"{r.chunk_id}:{r.score:.4f}")
    raw = ":".join(parts).encode("utf-8")
    return f"PACK-{hashlib.sha256(raw).hexdigest()[:12].upper()}"


def _stable_evidence_id(pack_id: str, chunk_id: str, rank: int) -> str:
    raw = f"{pack_id}:{chunk_id}:{rank}".encode("utf-8")
    return f"EVD-{hashlib.md5(raw).hexdigest()[:8].upper()}"


def _make_snippet(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def _extract_location(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Extract generic page/sheet/slide/section from chunk metadata."""
    location: Dict[str, Any] = {}
    nested = metadata.get("metadata", {})
    combined = {**metadata, **(nested if isinstance(nested, dict) else {})}

    for key in ("page", "page_number"):
        val = combined.get(key)
        if isinstance(val, int):
            location["page"] = val
            break

    for key in ("sheet", "sheet_name"):
        val = combined.get(key)
        if isinstance(val, str) and val:
            location["sheet"] = val
            break

    for key in ("slide", "slide_number"):
        val = combined.get(key)
        if isinstance(val, int):
            location["slide"] = val
            break

    section = combined.get("section_path")
    if isinstance(section, (list, tuple)):
        location["section_path"] = tuple(str(s) for s in section)

    for key in ("row_range", "column_range"):
        value = combined.get(key)
        if (
            isinstance(value, (list, tuple))
            and len(value) == 2
            and all(isinstance(item, int) for item in value)
        ):
            location[key] = tuple(value)

    cell_range = combined.get("cell_range")
    if isinstance(cell_range, str) and cell_range:
        location["cell_range"] = cell_range

    bbox = combined.get("bbox")
    if (
        isinstance(bbox, (list, tuple))
        and len(bbox) == 4
        and all(isinstance(item, (int, float)) for item in bbox)
    ):
        location["bbox"] = tuple(float(item) for item in bbox)

    return location


def _compute_privacy_summary(
    items: Tuple[EvidenceItem, ...],
) -> PrivacySummary:
    if not items:
        return PrivacySummary(
            overall_label="local_only",
            local_only=True,
            cloud_allowed=False,
            labels_present=(),
        )

    all_labels: set[str] = set()
    for item in items:
        all_labels.update(item.privacy_labels)

    has_blocked = bool(all_labels & _BLOCKED_PRIVACY_LABELS)

    if has_blocked or not all_labels:
        return PrivacySummary(
            overall_label="local_only",
            local_only=True,
            cloud_allowed=False,
            labels_present=tuple(sorted(all_labels)),
        )

    return PrivacySummary(
        overall_label="cloud_safe",
        local_only=False,
        cloud_allowed=True,
        labels_present=tuple(sorted(all_labels)),
    )


def _compute_confidence(
    items: Tuple[EvidenceItem, ...],
    summary: SearchSummary,
    config: EvidencePackConfig,
) -> Tuple[EvidenceConfidence, Tuple[str, ...]]:
    reasons: List[str] = list(summary.insufficiency_reasons)

    if not items:
        if not reasons:
            reasons.append("no_evidence_items")
        return EvidenceConfidence.INSUFFICIENT, tuple(reasons)

    top_score = items[0].score
    item_coverage = max((item.term_coverage for item in items), default=0.0)
    evidence_set_coverage = max(summary.evidence_set_term_coverage, item_coverage)
    unique_docs = len({item.document_id for item in items})

    if top_score < config.min_top_score:
        reasons.append("top_score_below_threshold")

    if len(items) < config.min_items_for_sufficient:
        reasons.append("too_few_evidence_items")

    if evidence_set_coverage < config.min_term_coverage:
        reasons.append("weak_term_coverage")
    if summary.missing_obligation_ids:
        reasons.append("missing_required_obligations")

    if reasons:
        if top_score < config.min_top_score or not items:
            return EvidenceConfidence.INSUFFICIENT, tuple(reasons)
        return EvidenceConfidence.LOW, tuple(dict.fromkeys(reasons))

    if top_score >= config.high_score_threshold and unique_docs > 1:
        return EvidenceConfidence.HIGH, ()

    if top_score >= config.medium_score_threshold:
        return EvidenceConfidence.MEDIUM, ()

    return EvidenceConfidence.LOW, ()


def _final_evidence_relevance(
    items: Sequence[EvidenceItem],
    query_plan: RetrievalQueryPlan,
) -> float:
    """Return proportion of query terms supported by final evidence text."""
    if not items:
        return 0.0
    target_terms = set(
        query_plan.target_terms or extract_content_terms(query_plan.original_query)
    )
    if not target_terms:
        return 1.0
    matched_terms = {
        term.casefold()
        for item in items
        for term in item.matched_terms
        if term.casefold() in target_terms
    }
    # Target support must come from the original query vocabulary. Structural
    # expansion aliases remain useful for recall, but cannot prove an answer.
    for item in items:
        item_text_tokens = set(extract_content_terms(item.text))
        matched_terms.update(target_terms & item_text_tokens)
    return len(matched_terms) / len(target_terms)


def _cross_lingual_structural_support(
    items: Sequence[EvidenceItem],
    query_plan: RetrievalQueryPlan,
    response: SearchResponse,
) -> tuple[bool, int, int, int, Tuple[str, ...]]:
    """Corroborate multilingual architecture/integration evidence without lowering lexical proof.

    This bounded fallback is intentionally unavailable to procedures, lookups,
    and general questions.  A structural alias only establishes recall; it is
    accepted here only with original target support, complete planned structural
    facets, and support spread over multiple documents.
    """
    if query_plan.intent_category not in {"architecture", "integration"}:
        return False, 0, 0, 0, ("intent_not_eligible",)

    required_facets = tuple(
        facet_id
        for facet_id in response.summary.planned_facet_ids
        if facet_id != "query"
    )
    if not required_facets:
        return False, 0, 0, 0, ("no_structural_facets_planned",)

    target_terms = set(query_plan.target_terms)
    valid_target_equivalent_ids = {
        variant.variant_id
        for variant in query_plan.variants
        if variant.variant_id and variant.target_equivalent
    }
    target_supported = tuple(
        item
        for item in items
        if (
            item.ranking_signals.get("target_term_match_count", 0.0) > 0.0
            or bool(target_terms.intersection(term.casefold() for term in item.matched_terms))
            # A named query equivalent is a bounded translation/romanisation of
            # the original subject. It can corroborate target relevance here only
            # when its ID is still present in this exact query plan; generic
            # structural aliases never enter this set.
            or bool(
                valid_target_equivalent_ids.intersection(
                    item.matched_target_equivalent_variant_ids
                )
            )
        )
    )
    covered_facets = {
        facet_id
        for item in items
        for facet_id in item.matched_query_facets
        if facet_id in required_facets
    }
    facet_documents = {
        item.document_id
        for item in items
        if set(item.matched_query_facets).intersection(required_facets)
    }
    reasons: List[str] = []
    if not target_supported:
        reasons.append("missing_original_target_support")
    if len(covered_facets) != len(required_facets):
        reasons.append("incomplete_structural_facet_coverage")
    if len(facet_documents) < 2:
        reasons.append("insufficient_structural_document_diversity")
    return (
        not reasons,
        len(required_facets),
        len(covered_facets),
        len(facet_documents),
        tuple(reasons),
    )


def _cross_lingual_target_equivalent_support(
    items: Sequence[EvidenceItem],
    query_plan: RetrievalQueryPlan,
) -> tuple[bool, int, Tuple[str, ...]]:
    """Validate a query-only multilingual target equivalent for bounded intents.

    A generic structural alias cannot enter this path: every accepted item must
    carry an ID from a validated target-equivalent expansion in the current plan.
    """
    if query_plan.intent_category not in {"procedure", "diagnosis", "compare_change"}:
        return False, 0, ("intent_not_eligible",)
    valid_ids = {
        variant.variant_id
        for variant in query_plan.variants
        if variant.variant_id and variant.target_equivalent
    }
    if not valid_ids:
        return False, 0, ("no_validated_target_equivalent_variant",)
    supported_items = tuple(
        item for item in items
        if valid_ids.intersection(item.matched_target_equivalent_variant_ids)
    )
    if not supported_items:
        return False, 0, ("missing_target_equivalent_evidence",)
    obligations = {
        obligation
        for item in supported_items
        for obligation in item.matched_obligations
    }
    if query_plan.intent_category == "procedure":
        required = {"step"}
    elif query_plan.intent_category == "diagnosis":
        required = {"problem", "action"}
    else:
        required = {"side_a", "side_b"}
    if not required.issubset(obligations):
        return False, len(supported_items), ("insufficient_target_equivalent_obligation_coverage",)
    return True, len(supported_items), ()


def _semantic_evidence_support(
    items: Sequence[EvidenceItem],
    query_plan: RetrievalQueryPlan,
    config: EvidencePackConfig,
    *,
    lexical_coverage: float,
) -> EvidenceRelevanceTelemetry:
    """Return content-free channel diagnostics with strict provenance checks."""
    structural_intent = query_plan.intent_category in {"architecture", "integration"}
    target_bearing_variant_ids = {
        variant.variant_id
        for variant in query_plan.variants
        if variant.variant_id
        and (variant.origin == "original" or variant.target_equivalent)
    }
    named_target_equivalent_ids = {
        variant.variant_id
        for variant in query_plan.variants
        if variant.variant_id and variant.target_equivalent
    }
    dense_scores: List[float] = []
    dense_score_count = 0
    dense_channel_count = 0
    current_variant_count = 0
    qualifying_count = 0
    for item in items:
        dense_score = item.ranking_signals.get("dense_cosine")
        dense_rank = item.ranking_signals.get("dense_channel_rank")
        has_dense_score = isinstance(dense_score, (int, float))
        has_dense_channel = isinstance(dense_rank, (int, float)) and dense_rank > 0
        # Structural-intent aliases are retrieval-only. Dense similarity against
        # them can broaden recall but cannot prove the original subject is in
        # scope. A semantic bypass therefore needs either the original wording
        # or a named, target-equivalent formulation validated in this plan.
        matched_variant_ids = set(item.matched_query_variant_ids)
        has_current_variant = bool(target_bearing_variant_ids.intersection(matched_variant_ids))
        # Architecture/integration terms such as "protocol" and "interface"
        # are especially generic. For those intents, cross-language dense support
        # must be anchored by a query-only named subject equivalent. Without one,
        # only lexical target proof can open the final relevance gate.
        has_named_structural_subject = bool(
            named_target_equivalent_ids.intersection(matched_variant_ids)
        )
        semantic_subject_eligible = has_current_variant and (
            not structural_intent or has_named_structural_subject
        )
        dense_score_count += int(has_dense_score)
        dense_channel_count += int(has_dense_channel)
        current_variant_count += int(semantic_subject_eligible)
        if has_dense_score:
            dense_scores.append(float(dense_score))
        if (
            has_dense_score
            and float(dense_score) >= config.min_semantic_support_score
            and has_dense_channel
            and semantic_subject_eligible
        ):
            qualifying_count += 1

    rejection_reasons: List[str] = []
    if items and not dense_score_count:
        rejection_reasons.append("missing_dense_score")
    if items and not dense_channel_count:
        rejection_reasons.append("missing_dense_channel_provenance")
    if items and not current_variant_count:
        rejection_reasons.append("missing_current_query_variant")
    if dense_scores and max(dense_scores) < config.min_semantic_support_score:
        rejection_reasons.append("semantic_score_below_threshold")
    if items and not qualifying_count and not rejection_reasons:
        rejection_reasons.append("semantic_provenance_not_corroborated")

    return EvidenceRelevanceTelemetry(
        lexical_coverage=lexical_coverage,
        lexical_threshold=config.min_final_evidence_term_coverage,
        lexical_passed=lexical_coverage >= config.min_final_evidence_term_coverage,
        semantic_threshold=config.min_semantic_support_score,
        semantic_max_score=max(dense_scores, default=0.0),
        selected_item_count=len(items),
        dense_score_item_count=dense_score_count,
        dense_channel_item_count=dense_channel_count,
        current_variant_item_count=current_variant_count,
        qualifying_semantic_item_count=qualifying_count,
        semantic_rejection_reasons=tuple(rejection_reasons),
        cross_lingual_structural_supported=False,
        cross_lingual_required_facet_count=0,
        cross_lingual_covered_facet_count=0,
        cross_lingual_document_count=0,
        cross_lingual_rejection_reasons=(),
        cross_lingual_target_equivalent_supported=False,
        cross_lingual_target_equivalent_item_count=0,
        cross_lingual_target_equivalent_rejection_reasons=(),
    )


def _classify_evidence_reasons(
    items: Sequence[EvidenceItem],
    reasons: Sequence[str],
) -> Tuple[Tuple[str, ...], Tuple[str, ...], EvidenceAnswerMode]:
    """Split diagnostics into vetoes and warnings, failing closed on unknown codes."""
    ordered = tuple(dict.fromkeys(reasons))
    if not items:
        hard = tuple(dict.fromkeys((*ordered, "no_evidence_items")))
        return hard, (), EvidenceAnswerMode.ABSTAIN

    soft = tuple(reason for reason in ordered if reason in _SOFT_WARNING_REASON_CODES)
    hard = tuple(reason for reason in ordered if reason not in _SOFT_WARNING_REASON_CODES)
    if hard:
        mode = EvidenceAnswerMode.ABSTAIN
    elif soft:
        mode = EvidenceAnswerMode.ANSWER_WITH_LIMITS
    else:
        mode = EvidenceAnswerMode.ANSWER
    return hard, soft, mode


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_evidence_pack(
    query: str | RetrievalQueryPlan,
    response: SearchResponse,
    config: Optional[EvidencePackConfig] = None,
) -> EvidencePack:
    """Convert a SearchResponse into a structured EvidencePack."""
    if config is None:
        config = EvidencePackConfig()

    query_plan = coerce_query_plan(query)
    query_text = query_plan.original_query
    results = response.results
    pack_id = _stable_pack_id(query_text, results)

    # Maximize usable answer coverage within the bounded evidence budget.  The
    # selector is deterministic: total new coverage wins, then obligation gain,
    # facet gain, and finally the original retrieval rank.
    doc_counts: Dict[str, int] = {}
    selected: List[SearchResult] = []
    selected_chunk_ids: set[str] = set()

    def add_result(result: SearchResult) -> bool:
        if result.chunk_id in selected_chunk_ids:
            return False
        doc_count = doc_counts.get(result.document_id, 0)
        if doc_count >= config.per_document_limit:
            return False
        doc_counts[result.document_id] = doc_count + 1
        selected_chunk_ids.add(result.chunk_id)
        selected.append(result)
        return True

    def has_direct_target_support(result: SearchResult) -> bool:
        return (
            not query_plan.target_terms
            or result.ranking_signals.get("target_term_match_count", 0.0) > 0.0
            or bool(set(result.matched_terms).intersection(query_plan.target_terms))
            or bool(result.matched_target_equivalent_variant_ids)
        )

    target_supported_results = tuple(
        result for result in results if has_direct_target_support(result)
    )
    selection_results = (
        target_supported_results
        if query_plan.intent_category in {"procedure", "diagnosis", "compare_change"}
        and target_supported_results
        else results
    )
    uncovered_obligations = set(response.summary.planned_obligation_ids)
    uncovered_facets = {
        facet_id
        for facet_id in response.summary.planned_facet_ids
        if facet_id != "query"
    }
    while len(selected) < config.max_items and (
        uncovered_obligations or uncovered_facets
    ):
        best_result: Optional[SearchResult] = None
        best_key: Optional[Tuple[int, int, int, int]] = None
        for rank_index, result in enumerate(selection_results):
            if result.chunk_id in selected_chunk_ids:
                continue
            if doc_counts.get(result.document_id, 0) >= config.per_document_limit:
                continue
            obligation_gain = len(
                uncovered_obligations.intersection(result.matched_obligations)
            )
            facet_gain = len(
                uncovered_facets.intersection(result.matched_query_facets)
            )
            if not obligation_gain and not facet_gain:
                continue
            key = (
                obligation_gain + facet_gain,
                obligation_gain,
                facet_gain,
                -rank_index,
            )
            if best_key is None or key > best_key:
                best_key = key
                best_result = result
        if best_result is None:
            break
        add_result(best_result)
        uncovered_obligations.difference_update(best_result.matched_obligations)
        uncovered_facets.difference_update(best_result.matched_query_facets)

    # Preserve retrieval rank for the non-coverage remainder, excluding unrelated
    # structural-only chunks whenever target-supported evidence is available.
    for result in selection_results:
        if len(selected) >= config.max_items:
            break
        add_result(result)

    # Build evidence items
    items: List[EvidenceItem] = []
    source_names: set[str] = set()
    document_ids: set[str] = set()

    for rank_index, result in enumerate(selected):
        rank = rank_index + 1
        evidence_id = _stable_evidence_id(pack_id, result.chunk_id, rank)
        citation_id = f"[{rank}]"
        citation_label = result.source_name or result.source_path or "unknown"
        snippet = _make_snippet(result.text, config.max_snippet_chars)
        location = _extract_location(result.metadata)

        # Extract element types from metadata
        raw_types = result.metadata.get("element_types")
        if isinstance(raw_types, (list, tuple)):
            element_types = tuple(str(t) for t in raw_types)
        else:
            element_types = ()

        item = EvidenceItem(
            evidence_id=evidence_id,
            citation_id=citation_id,
            citation_label=citation_label,
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            source_name=result.source_name,
            source_path=result.source_path,
            file_type=result.file_type,
            text=result.text,
            snippet=snippet,
            score=result.score,
            rank=rank,
            ranking_signals=dict(result.ranking_signals),
            matched_terms=result.matched_terms,
            term_coverage=result.term_coverage,
            privacy_labels=result.privacy_labels,
            element_types=element_types,
            page=location.get("page"),
            sheet=location.get("sheet"),
            slide=location.get("slide"),
            row_range=location.get("row_range"),
            column_range=location.get("column_range"),
            cell_range=location.get("cell_range"),
            bbox=location.get("bbox"),
            section_path=location.get("section_path", ()),
            matched_query_variant_ids=result.matched_query_variant_ids,
            matched_target_equivalent_variant_ids=(
                result.matched_target_equivalent_variant_ids
            ),
            matched_query_facets=result.matched_query_facets,
            matched_obligations=result.matched_obligations,
            metadata={
                k: v
                for k, v in result.metadata.items()
                if isinstance(v, (str, int, float, bool))
            },
        )
        items.append(item)
        source_names.add(result.source_name or result.source_path)
        document_ids.add(result.document_id)

    items_tuple = tuple(items)
    coverage_map = tuple(
        EvidenceFacetCoverage(
            facet_id=facet_id,
            status="covered" if matching else "missing",
            evidence_ids=tuple(item.evidence_id for item in matching),
            citation_ids=tuple(item.citation_id for item in matching),
            document_count=len({item.document_id for item in matching}),
        )
        for facet_id in response.summary.planned_facet_ids
        for matching in [tuple(item for item in items_tuple if facet_id in item.matched_query_facets)]
    )

    obligation_coverage_map = tuple(
        EvidenceObligationCoverage(
            obligation_id=obligation_id,
            status="covered" if matching else "missing",
            evidence_ids=tuple(item.evidence_id for item in matching),
            citation_ids=tuple(item.citation_id for item in matching),
            document_count=len({item.document_id for item in matching}),
        )
        for obligation_id in response.summary.planned_obligation_ids
        for matching in [tuple(item for item in items_tuple if obligation_id in item.matched_obligations)]
    )

    final_evidence_coverage = _final_evidence_relevance(items_tuple, query_plan)
    relevance_telemetry = _semantic_evidence_support(
        items_tuple,
        query_plan,
        config,
        lexical_coverage=final_evidence_coverage,
    )
    semantic_support_score = (
        relevance_telemetry.semantic_max_score
        if relevance_telemetry.qualifying_semantic_item_count
        else 0.0
    )
    semantic_support_used = bool(
        items_tuple
        and not relevance_telemetry.lexical_passed
        and relevance_telemetry.qualifying_semantic_item_count
    )
    (
        cross_lingual_structural_supported,
        cross_lingual_required_facet_count,
        cross_lingual_covered_facet_count,
        cross_lingual_document_count,
        cross_lingual_rejection_reasons,
    ) = _cross_lingual_structural_support(items_tuple, query_plan, response)
    (
        target_equivalent_supported,
        target_equivalent_item_count,
        target_equivalent_rejection_reasons,
    ) = _cross_lingual_target_equivalent_support(items_tuple, query_plan)
    relevance_telemetry = EvidenceRelevanceTelemetry(
        **{
            **asdict(relevance_telemetry),
            "cross_lingual_structural_supported": cross_lingual_structural_supported,
            "cross_lingual_required_facet_count": cross_lingual_required_facet_count,
            "cross_lingual_covered_facet_count": cross_lingual_covered_facet_count,
            "cross_lingual_document_count": cross_lingual_document_count,
            "cross_lingual_rejection_reasons": cross_lingual_rejection_reasons,
            "cross_lingual_target_equivalent_supported": target_equivalent_supported,
            "cross_lingual_target_equivalent_item_count": target_equivalent_item_count,
            "cross_lingual_target_equivalent_rejection_reasons": target_equivalent_rejection_reasons,
        }
    )
    target_equivalent_support_used = bool(
        items_tuple
        and not relevance_telemetry.lexical_passed
        and not semantic_support_used
        and target_equivalent_supported
    )
    cross_lingual_support_used = bool(
        items_tuple
        and not relevance_telemetry.lexical_passed
        and not semantic_support_used
        and not target_equivalent_support_used
        and cross_lingual_structural_supported
    )
    if final_evidence_coverage >= config.min_final_evidence_term_coverage:
        relevance_gate_basis = "lexical"
    elif semantic_support_used:
        relevance_gate_basis = "semantic_dense"
    elif target_equivalent_support_used:
        relevance_gate_basis = "cross_lingual_target_equivalent"
    elif cross_lingual_support_used:
        relevance_gate_basis = "cross_lingual_structural"
    else:
        relevance_gate_basis = "insufficient"
    supported_obligation_count = sum(
        item.status == "covered" for item in obligation_coverage_map
    )
    planned_obligation_count = len(obligation_coverage_map)
    confidence, insufficiency_reasons = _compute_confidence(
        items_tuple, response.summary, config
    )
    relevance_reasons: List[str] = []
    if target_equivalent_support_used:
        relevance_reasons.append("cross_lingual_target_equivalent_corroboration")
    elif cross_lingual_support_used:
        relevance_reasons.append("cross_lingual_structural_corroboration")
    elif (
        items_tuple
        and len(query_plan.target_terms) >= 2
        and not target_supported_results
        and not semantic_support_used
    ):
        relevance_reasons.extend((
            "no_target_query_evidence",
            "no_direct_query_evidence",
            "final_evidence_query_coverage_below_threshold",
        ))
    elif (
        items_tuple
        and len(query_plan.target_terms) >= 2
        and not target_supported_results
        and final_evidence_coverage < config.min_final_evidence_term_coverage
        and not semantic_support_used
    ):
        relevance_reasons.append("final_evidence_query_coverage_below_threshold")
    elif items_tuple and final_evidence_coverage == 0.0 and not semantic_support_used:
        relevance_reasons.append("no_direct_query_evidence")
    elif (
        items_tuple
        and final_evidence_coverage < config.min_final_evidence_term_coverage
        and not semantic_support_used
    ):
        relevance_reasons.append("final_evidence_query_coverage_below_threshold")
    if planned_obligation_count and not supported_obligation_count:
        # A qualifying dense result with current-query provenance is usable as
        # bounded evidence even when obligation cue matching is language-local
        # and misses every facet. Keep the missing-obligation warning visible,
        # but reserve the hard veto for evidence without an independent
        # relevance signal.
        if semantic_support_used or target_equivalent_support_used or cross_lingual_support_used:
            relevance_reasons.append("missing_required_obligations")
        else:
            relevance_reasons.append("all_required_obligations_missing")
    insufficiency_reasons = tuple(
        dict.fromkeys((*insufficiency_reasons, *relevance_reasons))
    )
    hard_reasons, soft_reasons, answer_mode = _classify_evidence_reasons(
        items_tuple, insufficiency_reasons
    )
    privacy_summary = _compute_privacy_summary(items_tuple)

    return EvidencePack(
        pack_id=pack_id,
        query=query_text,
        items=items_tuple,
        confidence=confidence,
        privacy_summary=privacy_summary,
        insufficiency_reasons=insufficiency_reasons,
        hard_insufficiency_reasons=hard_reasons,
        soft_warning_reasons=soft_reasons,
        answer_mode=answer_mode,
        retrieval_summary=response.summary,
        coverage_map=coverage_map,
        obligation_coverage_map=obligation_coverage_map,
        source_count=len(source_names),
        document_count=len(document_ids),
        item_count=len(items_tuple),
        top_score=items_tuple[0].score if items_tuple else 0.0,
        best_term_coverage=max(
            response.summary.evidence_set_term_coverage,
            max((item.term_coverage for item in items_tuple), default=0.0),
        ),
        final_evidence_term_coverage=final_evidence_coverage,
        semantic_support_score=semantic_support_score,
        semantic_support_used=semantic_support_used,
        relevance_gate_basis=relevance_gate_basis,
        relevance_telemetry=relevance_telemetry,
        supported_obligation_count=supported_obligation_count,
        planned_obligation_count=planned_obligation_count,
        created_at=datetime.now().isoformat(),
    )


def format_evidence_for_prompt(pack: EvidencePack) -> str:
    """Format an EvidencePack as plain text suitable for prompt inclusion."""
    lines: List[str] = []
    lines.append(f"### Evidence Pack (Query: '{pack.query}')")

    if pack.answer_mode == EvidenceAnswerMode.ABSTAIN:
        lines.append("\nWARNING: Insufficient evidence. Reasons:")
        for reason in pack.hard_insufficiency_reasons:
            lines.append(f"  - {reason}")
    elif pack.answer_mode == EvidenceAnswerMode.ANSWER_WITH_LIMITS:
        lines.append("\nLIMITS: Evidence is usable with warnings:")
        for reason in pack.soft_warning_reasons:
            lines.append(f"  - {reason}")

    covered_facets = sum(item.status == "covered" for item in pack.coverage_map)
    if pack.coverage_map:
        lines.append(f"Facet coverage: {covered_facets}/{len(pack.coverage_map)}")
    lines.append(
        f"Confidence: {pack.confidence.value.upper()} | "
        f"Sources: {pack.source_count} | "
        f"Documents: {pack.document_count} | "
        f"Items: {pack.item_count}"
    )

    if pack.privacy_summary.local_only:
        lines.append(
            "PRIVACY: Contains local-only data. External export NOT allowed."
        )
    else:
        lines.append("PRIVACY: Content is cloud-safe.")

    lines.append("---")

    for item in pack.items:
        location_parts: List[str] = []
        if item.page is not None:
            location_parts.append(f"Page: {item.page}")
        if item.sheet:
            location_parts.append(f"Sheet: {item.sheet}")
        if item.slide is not None:
            location_parts.append(f"Slide: {item.slide}")
        if item.row_range is not None:
            location_parts.append(f"Rows: {item.row_range[0]}-{item.row_range[1]}")
        if item.column_range is not None:
            location_parts.append(f"Columns: {item.column_range[0]}-{item.column_range[1]}")
        if item.cell_range:
            location_parts.append(f"Cells: {item.cell_range}")
        if item.bbox is not None:
            location_parts.append("BBox: " + ",".join(f"{value:g}" for value in item.bbox))
        if item.section_path:
            location_parts.append(f"Section: {' > '.join(item.section_path)}")

        location_str = f" ({'; '.join(location_parts)})" if location_parts else ""

        lines.append(f"Citation: {item.citation_id}")
        lines.append(f"Source: {item.citation_label}{location_str}")
        lines.append(f"Score: {item.score:.2f} | Coverage: {item.term_coverage:.0%}")
        lines.append(f"Snippet:\n{item.snippet}")
        lines.append("---")

    return "\n".join(lines)


def _to_json_compatible(value: Any) -> Any:
    """Recursively convert tuples to lists for JSON-compatible output."""
    if isinstance(value, dict):
        return {k: _to_json_compatible(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_compatible(item) for item in value]
    return value


def evidence_pack_to_dict(pack: EvidencePack) -> Dict[str, Any]:
    """Serialize an EvidencePack to a plain dict for logging/export."""
    raw = _to_json_compatible(asdict(pack))
    raw["confidence"] = pack.confidence.value
    raw["answer_mode"] = pack.answer_mode.value
    return raw
