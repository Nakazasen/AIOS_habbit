"""Local SQLite index and generic local retrieval for RAG v2 chunks."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import sqlite3
import struct
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .chunking import DocumentChunk
from .query_planning import (
    RetrievalQueryPlan,
    coerce_query_plan,
    extract_content_terms,
    match_text_obligations,
)
from .semantic import (
    EmbeddingBackend,
    MultiVector,
    MultiVectorDescriptor,
    MultiVectorEmbeddingBackend,
    RerankerBackend,
    SemanticBackendError,
    SemanticCapability,
    SparseEmbeddingBackend,
    SparseVector,
    cosine_similarity,
    late_interaction_maxsim,
    normalize_multivector,
    normalize_sparse_vector,
    normalize_vector,
    sparse_dot_similarity,
)

_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)
# CJK text is not whitespace-delimited. Add searchable overlapping n-grams so
# Japanese compound terms can match both FTS candidates and local scoring.
_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]+")


def _tokens(value: str) -> List[str]:
    text = value or ""
    tokens = [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]
    for match in _CJK_RE.finditer(text):
        compound = match.group(0).lower()
        if len(compound) < 2:
            continue
        tokens.extend(compound[index:index + width] for width in (2, 3, 4) for index in range(len(compound) - width + 1))
    return tokens


def _unique_tokens(value: str) -> Tuple[str, ...]:
    seen = set()
    ordered = []
    for token in _tokens(value):
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return tuple(ordered)


def _normalized_terms(value: str) -> str:
    return " ".join(_tokens(value))


def _embedding_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pack_vector(vector: Sequence[float], dimension: int) -> bytes:
    normalized = normalize_vector(vector, dimension=dimension)
    return struct.pack(f"<{dimension}f", *normalized)


def _unpack_vector(payload: bytes, dimension: int) -> tuple[float, ...]:
    expected_size = struct.calcsize(f"<{dimension}f")
    if len(payload) != expected_size:
        raise SemanticBackendError(
            f"embedding payload size mismatch: expected {expected_size}, received {len(payload)}"
        )
    return tuple(float(value) for value in struct.unpack(f"<{dimension}f", payload))


def _pack_multivector(vectors: Sequence[Sequence[float]], descriptor: MultiVectorDescriptor) -> bytes:
    matrix = normalize_multivector(
        vectors,
        dimension=descriptor.dimension,
        max_tokens=descriptor.max_tokens,
    )
    code = "f" if descriptor.dtype == "float32-le" else "e"
    values = tuple(value for token_vector in matrix for value in token_vector)
    try:
        return struct.pack(f"<{len(values)}{code}", *values)
    except (OverflowError, struct.error) as exc:
        raise SemanticBackendError("multi-vector cannot be represented by configured dtype") from exc


def _unpack_multivector(
    payload: bytes,
    *,
    dimension: int,
    token_count: int,
    dtype: str,
) -> MultiVector:
    if dimension < 1 or token_count < 1 or dtype not in {"float32-le", "float16-le"}:
        raise SemanticBackendError("invalid persisted multi-vector metadata")
    code = "f" if dtype == "float32-le" else "e"
    value_count = dimension * token_count
    expected_size = struct.calcsize(f"<{value_count}{code}")
    if len(payload) != expected_size:
        raise SemanticBackendError(
            f"multi-vector payload size mismatch: expected {expected_size}, received {len(payload)}"
        )
    values = struct.unpack(f"<{value_count}{code}", payload)
    return tuple(
        tuple(float(value) for value in values[offset:offset + dimension])
        for offset in range(0, value_count, dimension)
    )


def _contains_phrase(value: str, phrase: str) -> bool:
    return bool(phrase and phrase in _normalized_terms(value))


def _text_values(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if isinstance(item, (str, int, float))]
    return []


def _numeric_metadata(metadata: Mapping[str, Any], key: str) -> Optional[float]:
    nested = metadata.get("metadata")
    value = metadata.get(key)
    if value is None and isinstance(nested, Mapping):
        value = nested.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return min(1.0, max(0.0, float(value)))
    return None


def _metadata_flag(metadata: Mapping[str, Any], key: str) -> bool:
    nested = metadata.get("metadata")
    value = metadata.get(key)
    if value is None and isinstance(nested, Mapping):
        value = nested.get(key)
    return value is True


@dataclass(frozen=True)
class SearchOptions:
    """Generic, local-only constraints for a RAG v2 retrieval request."""

    allowed_privacy_labels: Optional[Tuple[str, ...]] = None
    allowed_document_ids: Optional[Tuple[str, ...]] = None
    allowed_source_paths: Optional[Tuple[str, ...]] = None
    expected_source_fingerprints: Mapping[str, str] = field(default_factory=dict)
    candidate_limit: int = 100
    per_document_limit: int = 2

    def __post_init__(self) -> None:
        if self.candidate_limit < 1:
            raise ValueError("candidate_limit must be at least 1")
        if self.per_document_limit < 1:
            raise ValueError("per_document_limit must be at least 1")


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    score: float
    text: str
    document_id: str
    source_path: str
    source_name: str
    file_type: str
    metadata: Dict[str, Any]
    privacy_labels: tuple[str, ...]
    ranking_signals: Dict[str, float] = field(default_factory=dict)
    matched_terms: tuple[str, ...] = field(default_factory=tuple)
    term_coverage: float = 0.0
    matched_query_variants: tuple[str, ...] = field(default_factory=tuple)
    matched_query_variant_ids: tuple[str, ...] = field(default_factory=tuple)
    matched_target_equivalent_variant_ids: tuple[str, ...] = field(default_factory=tuple)
    matched_query_facets: tuple[str, ...] = field(default_factory=tuple)
    matched_obligations: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SearchSummary:
    """Inspectable local retrieval outcome without exposing source text or vectors."""

    query: str
    indexed_chunk_count: int
    eligible_chunk_count: int
    candidate_count: int
    returned_count: int
    filtered_by_source_count: int = 0
    filtered_by_privacy_count: int = 0
    filtered_as_stale_count: int = 0
    diversity_limited_count: int = 0
    best_term_coverage: float = 0.0
    insufficiency_reasons: tuple[str, ...] = field(default_factory=tuple)
    query_variant_count: int = 1
    query_plan_fingerprint: str = ""
    expansion_status: str = "identity"
    candidate_backend: str = "deterministic_scan"
    evidence_set_term_coverage: float = 0.0
    planned_facet_ids: tuple[str, ...] = field(default_factory=tuple)
    covered_facet_ids: tuple[str, ...] = field(default_factory=tuple)
    missing_facet_ids: tuple[str, ...] = field(default_factory=tuple)
    planned_obligation_ids: tuple[str, ...] = field(default_factory=tuple)
    covered_obligation_ids: tuple[str, ...] = field(default_factory=tuple)
    missing_obligation_ids: tuple[str, ...] = field(default_factory=tuple)
    lexical_pool: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)
    dense_pool: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)
    sparse_pool: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)
    fused_pool: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)
    ranked_pool: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)
    expanded_pool: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)
    assembly_rejected_pool: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)
    lexical_latency_ms: float = 0.0
    dense_latency_ms: float = 0.0
    sparse_latency_ms: float = 0.0
    multivector_load_latency_ms: float = 0.0
    multivector_maxsim_latency_ms: float = 0.0
    fusion_latency_ms: float = 0.0
    rerank_latency_ms: float = 0.0
    assembly_latency_ms: float = 0.0
    context_expansion_latency_ms: float = 0.0
    context_expansion_added_chunk_count: int = 0


@dataclass(frozen=True)
class SearchResponse:
    results: tuple[SearchResult, ...]
    summary: SearchSummary


@dataclass(frozen=True)
class HybridRankingConfig:
    """Bounded, scale-independent ranking controls for three retrieval channels."""

    rrf_k: int = 60
    lexical_weight: float = 1.0
    dense_weight: float = 1.0
    sparse_weight: float = 1.0
    rerank_limit: int = 30
    near_duplicate_threshold: float = 0.92
    multivector_score_band: float = 0.15

    def __post_init__(self) -> None:
        if self.rrf_k < 1 or self.rerank_limit < 1:
            raise ValueError("ranking limits must be positive")
        if (
            self.lexical_weight <= 0.0
            or self.dense_weight <= 0.0
            or self.sparse_weight <= 0.0
        ):
            raise ValueError("channel weights must be positive")
        if not 0.0 <= self.near_duplicate_threshold <= 1.0:
            raise ValueError("near_duplicate_threshold must be between zero and one")
        if self.multivector_score_band < 0.0:
            raise ValueError("multivector_score_band must be non-negative")


def _ordered_union(*values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for group in values for item in group))


def _hybrid_result_is_safe(result: SearchResult, options: SearchOptions) -> bool:
    """Recheck every fused candidate against the original safety constraints."""
    document_is_allowed = (
        options.allowed_document_ids is None
        or result.document_id in options.allowed_document_ids
    )
    if not document_is_allowed:
        return False
    if (
        options.allowed_document_ids is None
        and options.allowed_source_paths is not None
        and result.source_path not in options.allowed_source_paths
    ):
        return False
    if options.allowed_privacy_labels is not None:
        allowed = set(options.allowed_privacy_labels)
        if not result.privacy_labels or any(label not in allowed for label in result.privacy_labels):
            return False
    expected = options.expected_source_fingerprints
    if result.document_id in expected:
        expected_fingerprint = expected[result.document_id]
    elif result.source_path in expected:
        expected_fingerprint = expected[result.source_path]
    else:
        return True
    return result.metadata.get("source_fingerprint") == expected_fingerprint


def _merge_search_results(current: SearchResult, incoming: SearchResult) -> SearchResult:
    """Merge channel provenance while retaining lexical diagnostics when present."""
    signals = dict(current.ranking_signals)
    signals.update(incoming.ranking_signals)
    merged_equivalents = _ordered_union(
        current.matched_target_equivalent_variant_ids,
        incoming.matched_target_equivalent_variant_ids,
    )
    merged_facets = _ordered_union(
        current.matched_query_facets, incoming.matched_query_facets
    )
    return replace(
        current,
        ranking_signals=signals,
        matched_terms=_ordered_union(current.matched_terms, incoming.matched_terms),
        term_coverage=max(current.term_coverage, incoming.term_coverage),
        matched_query_variants=_ordered_union(
            current.matched_query_variants, incoming.matched_query_variants
        ),
        matched_query_variant_ids=_ordered_union(
            current.matched_query_variant_ids, incoming.matched_query_variant_ids
        ),
        matched_target_equivalent_variant_ids=merged_equivalents,
        matched_query_facets=merged_facets,
        matched_obligations=_ordered_union(
            current.matched_obligations, incoming.matched_obligations
        ),
    )


def _result_tokens(text: str) -> set[str]:
    return {match.group(0).casefold() for match in _TOKEN_RE.finditer(text or "")}


def _is_near_duplicate(
    candidate: SearchResult,
    selected: Sequence[SearchResult],
    threshold: float,
) -> bool:
    candidate_tokens = _result_tokens(candidate.text)
    if not candidate_tokens:
        return any(candidate.text == result.text for result in selected)
    for result in selected:
        existing_tokens = _result_tokens(result.text)
        union = candidate_tokens | existing_tokens
        if union and len(candidate_tokens & existing_tokens) / len(union) >= threshold:
            return True
    return False


def _rerank_hybrid_window(
    query: str,
    ranked: Sequence[SearchResult],
    backend: RerankerBackend,
    limit: int,
) -> list[SearchResult]:
    backend.capability.require()
    depth = min(len(ranked), limit)
    head = list(ranked[:depth])
    scores = backend.score_pairs(tuple((query, result.text) for result in head))
    if len(scores) != len(head) or any(not math.isfinite(float(score)) for score in scores):
        raise SemanticBackendError(
            f"reranker score count mismatch: expected {len(head)}, received {len(scores)}"
        )
    rescored = []
    for result, score in zip(head, scores):
        signals = dict(result.ranking_signals)
        signals["reranker_score"] = float(score)
        rescored.append(replace(result, ranking_signals=signals))
    rescored.sort(key=lambda result: (
        -result.ranking_signals["reranker_score"],
        -result.ranking_signals["fused_rrf"],
        result.chunk_id,
    ))
    return rescored + list(ranked[depth:])


def _select_hybrid_results(
    ranked: Sequence[SearchResult],
    plan: RetrievalQueryPlan,
    *,
    limit: int,
    per_document_limit: int,
    near_duplicate_threshold: float,
    semantic_floor: Optional[float] = None,
) -> tuple[list[SearchResult], list[SearchResult]]:
    selected: list[SearchResult] = []
    selected_ids: set[str] = set()
    rejected_ids: set[str] = set()
    document_counts: Counter[str] = Counter()

    def add(result: SearchResult, reason: str) -> bool:
        if result.chunk_id in selected_ids or result.chunk_id in rejected_ids:
            return False
        document_key = result.document_id or result.source_path
        if document_counts[document_key] >= per_document_limit or _is_near_duplicate(
            result, selected, near_duplicate_threshold
        ):
            rejected_ids.add(result.chunk_id)
            return False
        signals = dict(result.ranking_signals)
        signals[reason] = 1.0
        selected.append(replace(result, ranking_signals=signals))
        selected_ids.add(result.chunk_id)
        document_counts[document_key] += 1
        return True

    def has_target_support(result: SearchResult) -> bool:
        if semantic_floor is not None:
            return result.ranking_signals.get("multivector_score", -math.inf) >= semantic_floor
        return (
            plan.intent_category != "procedure"
            or not plan.target_terms
            or result.ranking_signals.get("target_term_match_count", 0.0) > 0.0
            or bool(result.matched_target_equivalent_variant_ids)
        )

    def has_equivalent_facet_support(result: SearchResult, facet_id: str) -> bool:
        """Require a validated target-equivalent variant assigned to the facet."""
        if facet_id not in result.matched_query_facets:
            return False
        variants_by_id = {variant.variant_id: variant for variant in plan.variants}
        return any(
            (variant := variants_by_id.get(variant_id)) is not None
            and variant.facet_id == facet_id
            for variant_id in result.matched_target_equivalent_variant_ids
        )

    obligations = tuple(item for item in plan.required_obligations if item != "query")
    facets = tuple(item for item in plan.facet_ids if item != "query")
    for obligation_id in obligations:
        for result in ranked:
            if (
                has_target_support(result)
                and obligation_id in result.matched_obligations
                and add(result, "selected_for_obligation")
            ):
                break
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        for facet_id in facets:
            for result in ranked:
                if has_equivalent_facet_support(result, facet_id) and add(result, "selected_for_equivalent_facet"):
                    break
            if len(selected) >= limit:
                break
        for facet_id in facets:
            if any(facet_id in item.matched_query_facets for item in selected):
                continue
            for result in ranked:
                if (
                    has_target_support(result)
                    and facet_id in result.matched_query_facets
                    and add(result, "selected_for_facet")
                ):
                    break
            if len(selected) >= limit:
                break
    if len(selected) < limit:
        for result in ranked:
            add(result, "selected_by_rank")
            if len(selected) >= limit:
                break

    finalized = []
    for final_rank, result in enumerate(selected, 1):
        signals = dict(result.ranking_signals)
        signals["final_rank"] = float(final_rank)
        finalized.append(replace(result, ranking_signals=signals))
    rejected = [result for result in ranked if result.chunk_id in rejected_ids]
    return finalized, rejected


def fuse_ranked_channels(
    query: str | RetrievalQueryPlan,
    lexical_response: SearchResponse,
    dense_results: Sequence[SearchResult],
    *,
    limit: int,
    options: SearchOptions,
    sparse_results: Sequence[SearchResult] = (),
    config: Optional[HybridRankingConfig] = None,
    reranker: Optional[RerankerBackend] = None,
    multivector_scores: Optional[Mapping[str, float]] = None,
    multivector_load_latency_ms: float = 0.0,
    multivector_maxsim_latency_ms: float = 0.0,
) -> SearchResponse:
    """Fuse pre-filtered channel ranks without mixing raw score scales."""
    ranking = config or HybridRankingConfig()
    plan = coerce_query_plan(query)
    if limit <= 0:
        return SearchResponse(
            results=(),
            summary=replace(
                lexical_response.summary,
                candidate_count=0,
                returned_count=0,
                candidate_backend="hybrid_rrf",
                insufficiency_reasons=("non_positive_limit",),
            ),
        )

    fusion_started = perf_counter()
    records: Dict[str, Dict[str, Any]] = {}
    channel_pools: dict[str, list[SearchResult]] = {
        "lexical": [], "dense": [], "sparse": [],
    }
    channels = (
        ("lexical", lexical_response.results, ranking.lexical_weight),
        ("dense", dense_results, ranking.dense_weight),
        ("sparse", sparse_results, ranking.sparse_weight),
    )
    for channel, results, weight in channels:
        for rank, result in enumerate(results, 1):
            if not _hybrid_result_is_safe(result, options):
                continue
            channel_pools[channel].append(result)
            record = records.setdefault(result.chunk_id, {
                "result": result,
                "rrf": 0.0,
                "lexical_rank": 0,
                "dense_rank": 0,
                "sparse_rank": 0,
            })
            if channel == "lexical":
                record["result"] = _merge_search_results(result, record["result"])
            else:
                record["result"] = _merge_search_results(record["result"], result)
            record["rrf"] += weight / (ranking.rrf_k + rank)
            record[f"{channel}_rank"] = rank

    fused = []
    for record in records.values():
        result = record["result"]
        signals = dict(result.ranking_signals)
        signals.update({
            "lexical_channel_rank": float(record["lexical_rank"]),
            "dense_channel_rank": float(record["dense_rank"]),
            "sparse_channel_rank": float(record["sparse_rank"]),
            "fused_rrf": float(record["rrf"]),
        })
        fused.append(replace(result, ranking_signals=signals))
    fused.sort(key=lambda result: (
        -result.ranking_signals["fused_rrf"],
        result.chunk_id,
    ))
    fused_pre_rerank = tuple(fused)
    fusion_latency_ms = (perf_counter() - fusion_started) * 1000.0

    candidate_backend = "hybrid_rrf"
    rerank_latency_ms = 0.0
    if multivector_scores is not None and fused:
        rescored = []
        for result in fused:
            score = multivector_scores.get(result.chunk_id)
            if score is None:
                rescored.append(result)
                continue
            if not math.isfinite(float(score)):
                raise SemanticBackendError("multi-vector score is non-finite")
            signals = dict(result.ranking_signals)
            signals["multivector_score"] = float(score)
            rescored.append(replace(result, ranking_signals=signals, score=float(score)))
        fused = rescored
        fused.sort(key=lambda result: (
            0 if "multivector_score" in result.ranking_signals else 1,
            -result.ranking_signals.get("multivector_score", -math.inf),
            result.ranking_signals.get("dense_channel_rank", 0.0) or math.inf,
            result.ranking_signals.get("sparse_channel_rank", 0.0) or math.inf,
            -result.ranking_signals["fused_rrf"],
            result.chunk_id,
        ))
        multivector_rank = 0
        ranked_with_signals = []
        for result in fused:
            if "multivector_score" in result.ranking_signals:
                multivector_rank += 1
                signals = dict(result.ranking_signals)
                signals["multivector_rank"] = float(multivector_rank)
                result = replace(result, ranking_signals=signals)
            ranked_with_signals.append(result)
        fused = ranked_with_signals
        candidate_backend = "hybrid_rrf_multivector"
    elif reranker is not None and fused:
        rerank_started = perf_counter()
        fused = _rerank_hybrid_window(plan.original_query, fused, reranker, ranking.rerank_limit)
        rerank_latency_ms = (perf_counter() - rerank_started) * 1000.0
        candidate_backend = "hybrid_rrf_rerank"

    semantic_scores = [
        result.ranking_signals["multivector_score"]
        for result in fused
        if "multivector_score" in result.ranking_signals
    ]
    semantic_floor = (
        max(semantic_scores) - ranking.multivector_score_band if semantic_scores else None
    )
    assembly_started = perf_counter()
    final_results, assembly_rejected = _select_hybrid_results(
        fused,
        plan,
        limit=limit,
        per_document_limit=options.per_document_limit,
        near_duplicate_threshold=ranking.near_duplicate_threshold,
        semantic_floor=semantic_floor,
    )
    assembly_latency_ms = (perf_counter() - assembly_started) * 1000.0
    content_terms = set(plan.content_terms)
    matched_terms = {
        term
        for result in final_results
        for term in result.matched_terms
        if term in content_terms
    }
    evidence_coverage = len(matched_terms) / len(content_terms) if content_terms else 0.0
    best_coverage = max((result.term_coverage for result in final_results), default=0.0)
    reasons = [
        reason
        for reason in lexical_response.summary.insufficiency_reasons
        if reason not in {"incomplete_query_term_coverage", "weak_query_term_coverage"}
        and not (final_results and reason == "no_lexical_or_metadata_match")
    ]
    if final_results and len(content_terms) > 1 and evidence_coverage < 1.0:
        reasons.append("incomplete_query_term_coverage")
    if final_results and len(content_terms) > 1 and evidence_coverage < 0.5:
        reasons.append("weak_query_term_coverage")

    planned_facets = plan.facet_ids
    planned_obligations = tuple(item for item in plan.required_obligations if item != "query")
    covered_facets = tuple(
        facet for facet in planned_facets
        if any(facet in result.matched_query_facets for result in final_results)
    )
    covered_obligations = tuple(
        obligation for obligation in planned_obligations
        if any(obligation in result.matched_obligations for result in final_results)
    )
    identity = lambda result: (result.chunk_id, result.document_id, result.source_name)
    summary = replace(
        lexical_response.summary,
        candidate_count=len(fused),
        returned_count=len(final_results),
        diversity_limited_count=len(assembly_rejected),
        best_term_coverage=best_coverage,
        insufficiency_reasons=tuple(dict.fromkeys(reasons)),
        candidate_backend=candidate_backend,
        evidence_set_term_coverage=evidence_coverage,
        planned_facet_ids=planned_facets,
        covered_facet_ids=covered_facets,
        missing_facet_ids=tuple(item for item in planned_facets if item not in covered_facets),
        planned_obligation_ids=planned_obligations,
        covered_obligation_ids=covered_obligations,
        missing_obligation_ids=tuple(
            item for item in planned_obligations if item not in covered_obligations
        ),
        lexical_pool=tuple(identity(result) for result in channel_pools["lexical"]),
        dense_pool=tuple(identity(result) for result in channel_pools["dense"]),
        sparse_pool=tuple(identity(result) for result in channel_pools["sparse"]),
        fused_pool=tuple(identity(result) for result in fused_pre_rerank),
        ranked_pool=tuple(identity(result) for result in fused),
        assembly_rejected_pool=tuple(identity(result) for result in assembly_rejected),
        fusion_latency_ms=fusion_latency_ms,
        rerank_latency_ms=rerank_latency_ms,
        multivector_load_latency_ms=multivector_load_latency_ms,
        multivector_maxsim_latency_ms=multivector_maxsim_latency_ms,
        assembly_latency_ms=assembly_latency_ms,
    )
    return SearchResponse(results=tuple(final_results), summary=summary)


class LocalChunkIndex:
    def __init__(
        self,
        db_path: str | Path,
        *,
        enable_fts5: bool = True,
        embedding_backend: Optional[EmbeddingBackend] = None,
        sparse_backend: Optional[SparseEmbeddingBackend] = None,
        multivector_backend: Optional[MultiVectorEmbeddingBackend] = None,
        sqlite_check_same_thread: bool = True,
        ensure_embeddings_on_open: bool = True,
        read_only: bool = False,
    ) -> None:
        self.db_path = Path(db_path)
        self._read_only = bool(read_only)
        if self._read_only:
            if not self.db_path.is_file():
                raise FileNotFoundError(f"read-only index does not exist: {self.db_path}")
            uri = f"file:{self.db_path.resolve().as_posix()}?mode=ro"
            self._conn = sqlite3.connect(
                uri,
                uri=True,
                check_same_thread=sqlite_check_same_thread,
            )
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=sqlite_check_same_thread,
            )
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.row_factory = sqlite3.Row
        self._fts5_requested = enable_fts5
        self._embedding_backend = embedding_backend
        self._sparse_backend = sparse_backend or (
            embedding_backend if isinstance(embedding_backend, SparseEmbeddingBackend) else None
        )
        self._multivector_backend = multivector_backend or (
            embedding_backend if isinstance(embedding_backend, MultiVectorEmbeddingBackend) else None
        )
        if self._read_only:
            self._fts5_available = bool(enable_fts5 and self._conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'chunks_fts'"
            ).fetchone())
        else:
            self._fts5_available = False
            self._create_schema()
            if (
                ensure_embeddings_on_open
                and embedding_backend is not None
                and embedding_backend.capability.available
            ):
                self.ensure_embeddings()

    @property
    def retrieval_backend(self) -> str:
        return "fts5_bm25" if self._fts5_available else "deterministic_scan"

    def _create_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                source_path TEXT NOT NULL,
                source_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                text TEXT NOT NULL,
                normalized_text TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                privacy_labels_json TEXT NOT NULL,
                source_fingerprint TEXT,
                checksum TEXT,
                retrievable INTEGER NOT NULL DEFAULT 1 CHECK (retrievable IN (0, 1))
            )
            """
        )
        chunk_columns = {
            str(row["name"])
            for row in self._conn.execute("PRAGMA table_info(chunks)").fetchall()
        }
        if "retrievable" not in chunk_columns:
            self._conn.execute(
                "ALTER TABLE chunks ADD COLUMN retrievable INTEGER NOT NULL DEFAULT 1"
            )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_retrievable ON chunks(retrievable, document_id)"
        )
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chunk_embeddings (
                chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
                model_fingerprint TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                model_id TEXT NOT NULL,
                model_revision TEXT NOT NULL,
                runtime TEXT NOT NULL,
                runtime_version TEXT NOT NULL,
                dimension INTEGER NOT NULL CHECK (dimension > 0),
                dtype TEXT NOT NULL CHECK (dtype = 'float32-le'),
                normalized INTEGER NOT NULL CHECK (normalized IN (0, 1)),
                vector_blob BLOB NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (chunk_id, model_fingerprint)
            );
            CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_model
            ON chunk_embeddings(model_fingerprint, chunk_id);
            CREATE TABLE IF NOT EXISTS chunk_sparse_embeddings (
                chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
                model_fingerprint TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                sparse_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (chunk_id, model_fingerprint)
            );
            CREATE INDEX IF NOT EXISTS idx_chunk_sparse_embeddings_model
            ON chunk_sparse_embeddings(model_fingerprint, chunk_id);
            CREATE TABLE IF NOT EXISTS chunk_multivector_embeddings (
                chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
                model_fingerprint TEXT NOT NULL,
                representation_fingerprint TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                dimension INTEGER NOT NULL CHECK (dimension > 0),
                token_count INTEGER NOT NULL CHECK (token_count > 0),
                dtype TEXT NOT NULL CHECK (dtype IN ('float32-le', 'float16-le')),
                schema_version INTEGER NOT NULL CHECK (schema_version > 0),
                vector_blob BLOB NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (chunk_id, model_fingerprint)
            );
            CREATE INDEX IF NOT EXISTS idx_chunk_multivector_embeddings_model
            ON chunk_multivector_embeddings(model_fingerprint, chunk_id);
            CREATE TRIGGER IF NOT EXISTS chunks_embeddings_content_update
            AFTER UPDATE OF text, normalized_text, checksum ON chunks
            WHEN old.text IS NOT new.text
              OR old.normalized_text IS NOT new.normalized_text
              OR old.checksum IS NOT new.checksum
            BEGIN
                DELETE FROM chunk_embeddings WHERE chunk_id = old.chunk_id;
                DELETE FROM chunk_sparse_embeddings WHERE chunk_id = old.chunk_id;
                DELETE FROM chunk_multivector_embeddings WHERE chunk_id = old.chunk_id;
            END;
            """
        )
        if self._fts5_requested:
            try:
                self._conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                        chunk_id UNINDEXED,
                        normalized_text,
                        source_name,
                        source_path,
                        metadata_json,
                        tokenize='unicode61'
                    )
                    """
                )
                self._conn.executescript(
                    """
                    DROP TRIGGER IF EXISTS chunks_fts_insert;
                    DROP TRIGGER IF EXISTS chunks_fts_delete;
                    DROP TRIGGER IF EXISTS chunks_fts_update;
                    CREATE TRIGGER chunks_fts_insert AFTER INSERT ON chunks
                    WHEN new.retrievable = 1 BEGIN
                        INSERT INTO chunks_fts(chunk_id, normalized_text, source_name, source_path, metadata_json)
                        VALUES (new.chunk_id, new.normalized_text, new.source_name, new.source_path, new.metadata_json);
                    END;
                    CREATE TRIGGER chunks_fts_delete AFTER DELETE ON chunks BEGIN
                        DELETE FROM chunks_fts WHERE chunk_id = old.chunk_id;
                    END;
                    CREATE TRIGGER chunks_fts_update AFTER UPDATE ON chunks BEGIN
                        DELETE FROM chunks_fts WHERE chunk_id = old.chunk_id;
                        INSERT INTO chunks_fts(chunk_id, normalized_text, source_name, source_path, metadata_json)
                        SELECT new.chunk_id, new.normalized_text, new.source_name, new.source_path, new.metadata_json
                        WHERE new.retrievable = 1;
                    END;
                    """
                )
                chunk_count = int(self._conn.execute(
                    "SELECT COUNT(*) FROM chunks WHERE retrievable = 1"
                ).fetchone()[0])
                fts_count = int(self._conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0])
                if chunk_count != fts_count:
                    self._conn.execute("DELETE FROM chunks_fts")
                    self._conn.execute(
                        """
                        INSERT INTO chunks_fts(chunk_id, normalized_text, source_name, source_path, metadata_json)
                        SELECT chunk_id, normalized_text, source_name, source_path, metadata_json
                        FROM chunks WHERE retrievable = 1
                        """
                    )
                self._fts5_available = True
            except sqlite3.OperationalError:
                self._fts5_available = False
        self._conn.commit()

    def upsert_chunks(self, chunks: Iterable[DocumentChunk]) -> int:
        prepared = tuple(chunks)
        rows = [self._chunk_row(chunk) for chunk in prepared]
        if not rows:
            return 0
        with self._conn:
            self._upsert_rows(rows)
            self._ensure_embeddings(tuple(chunk.chunk_id for chunk in prepared))
        return sum(1 for chunk in prepared if chunk.retrievable)

    def replace_document_chunks(
        self,
        document_id: str,
        chunks: Iterable[DocumentChunk],
    ) -> int:
        """Atomically replace one document while preserving valid embedding cache rows."""
        normalized_id = (document_id or "").strip()
        if not normalized_id:
            raise ValueError("document_id is required")
        prepared = tuple(chunks)
        if any(chunk.document_id != normalized_id for chunk in prepared):
            raise ValueError("all chunks must belong to document_id")
        rows = [self._chunk_row(chunk) for chunk in prepared]
        chunk_ids = tuple(chunk.chunk_id for chunk in prepared)
        with self._conn:
            if rows:
                self._upsert_rows(rows)
                placeholders = ",".join("?" for _ in chunk_ids)
                self._conn.execute(
                    f"DELETE FROM chunks WHERE document_id = ? AND chunk_id NOT IN ({placeholders})",
                    (normalized_id, *chunk_ids),
                )
                self._ensure_embeddings(chunk_ids)
            else:
                self._conn.execute("DELETE FROM chunks WHERE document_id = ?", (normalized_id,))
        return sum(1 for chunk in prepared if chunk.retrievable)

    def replace_document_chunks_with_embeddings(
        self,
        document_id: str,
        chunks: Iterable[DocumentChunk],
        dense_vectors: Mapping[str, Sequence[float]],
        sparse_vectors: Mapping[str, SparseVector],
        multivector_vectors: Optional[Mapping[str, MultiVector]] = None,
    ) -> int:
        """Atomically publish a fully staged document and its precomputed vectors.

        Callers must provide vectors for every retrievable chunk. Validation happens
        before the transaction so a timeout or worker failure cannot expose a
        partially embedded document.
        """
        normalized_id = (document_id or "").strip()
        if not normalized_id:
            raise ValueError("document_id is required")
        prepared = tuple(chunks)
        if any(chunk.document_id != normalized_id for chunk in prepared):
            raise ValueError("all chunks must belong to document_id")
        backend = self._embedding_backend
        if backend is None or not backend.capability.available:
            if dense_vectors or sparse_vectors:
                raise SemanticBackendError("staged vectors require an available embedding backend")
            return self.replace_document_chunks(normalized_id, prepared)
        descriptor = backend.descriptor
        retrievable = tuple(chunk for chunk in prepared if chunk.retrievable)
        expected_ids = {chunk.chunk_id for chunk in retrievable}
        if set(dense_vectors) != expected_ids:
            raise SemanticBackendError("staged dense vector coverage mismatch")
        sparse_required = (
            self._sparse_backend is not None
            and self._sparse_backend.sparse_capability.available
        )
        if sparse_required and set(sparse_vectors) != expected_ids:
            raise SemanticBackendError("staged sparse vector coverage mismatch")
        if not sparse_required and sparse_vectors:
            raise SemanticBackendError("staged sparse vectors supplied without sparse backend")
        multivector_backend = self._multivector_backend
        multivector_required = (
            multivector_backend is not None
            and multivector_backend.multivector_capability.available
        )
        supplied_multivectors = multivector_vectors or {}
        if multivector_required and set(supplied_multivectors) != expected_ids:
            raise SemanticBackendError("staged multi-vector coverage mismatch")
        if not multivector_required and supplied_multivectors:
            raise SemanticBackendError("staged multi-vectors supplied without multi-vector backend")

        rows = [self._chunk_row(chunk) for chunk in prepared]
        chunk_ids = tuple(chunk.chunk_id for chunk in prepared)
        created_at = datetime.now(timezone.utc).isoformat()
        dense_records = [
            (
                chunk.chunk_id,
                descriptor.fingerprint,
                _embedding_content_hash(chunk.text),
                descriptor.model_id,
                descriptor.revision,
                descriptor.runtime,
                descriptor.runtime_version,
                descriptor.dimension,
                "float32-le",
                int(descriptor.normalized),
                _pack_vector(dense_vectors[chunk.chunk_id], descriptor.dimension),
                created_at,
            )
            for chunk in retrievable
        ]
        sparse_records = [
            (
                chunk.chunk_id,
                descriptor.fingerprint,
                _embedding_content_hash(chunk.text),
                json.dumps(
                    normalize_sparse_vector(sparse_vectors[chunk.chunk_id]),
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                created_at,
            )
            for chunk in retrievable
        ] if sparse_required else []
        multivector_records = []
        if multivector_required and multivector_backend is not None:
            multivector_descriptor = multivector_backend.multivector_descriptor
            multivector_records = [
                (
                    chunk.chunk_id,
                    descriptor.fingerprint,
                    multivector_descriptor.fingerprint,
                    _embedding_content_hash(chunk.text),
                    multivector_descriptor.dimension,
                    len(supplied_multivectors[chunk.chunk_id]),
                    multivector_descriptor.dtype,
                    multivector_descriptor.schema_version,
                    _pack_multivector(
                        supplied_multivectors[chunk.chunk_id], multivector_descriptor
                    ),
                    created_at,
                )
                for chunk in retrievable
            ]
        with self._conn:
            if rows:
                self._upsert_rows(rows)
                placeholders = ",".join("?" for _ in chunk_ids)
                self._conn.execute(
                    f"DELETE FROM chunks WHERE document_id = ? AND chunk_id NOT IN ({placeholders})",
                    (normalized_id, *chunk_ids),
                )
            else:
                self._conn.execute("DELETE FROM chunks WHERE document_id = ?", (normalized_id,))
                return 0
            self._conn.executemany(
                """
                INSERT INTO chunk_embeddings (
                    chunk_id, model_fingerprint, content_hash, model_id, model_revision,
                    runtime, runtime_version, dimension, dtype, normalized, vector_blob, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id, model_fingerprint) DO UPDATE SET
                    content_hash=excluded.content_hash, model_id=excluded.model_id,
                    model_revision=excluded.model_revision, runtime=excluded.runtime,
                    runtime_version=excluded.runtime_version, dimension=excluded.dimension,
                    dtype=excluded.dtype, normalized=excluded.normalized,
                    vector_blob=excluded.vector_blob, created_at=excluded.created_at
                """,
                dense_records,
            )
            if sparse_records:
                self._conn.executemany(
                    """
                    INSERT INTO chunk_sparse_embeddings (
                        chunk_id, model_fingerprint, content_hash, sparse_json, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(chunk_id, model_fingerprint) DO UPDATE SET
                        content_hash=excluded.content_hash, sparse_json=excluded.sparse_json,
                        created_at=excluded.created_at
                    """,
                    sparse_records,
                )
            if multivector_records:
                self._conn.executemany(
                    """
                    INSERT INTO chunk_multivector_embeddings (
                        chunk_id, model_fingerprint, representation_fingerprint,
                        content_hash, dimension, token_count, dtype, schema_version,
                        vector_blob, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(chunk_id, model_fingerprint) DO UPDATE SET
                        representation_fingerprint=excluded.representation_fingerprint,
                        content_hash=excluded.content_hash, dimension=excluded.dimension,
                        token_count=excluded.token_count, dtype=excluded.dtype,
                        schema_version=excluded.schema_version,
                        vector_blob=excluded.vector_blob, created_at=excluded.created_at
                    """,
                    multivector_records,
                )
        return len(retrievable)

    def delete_document(self, document_id: str) -> int:
        """Delete one selected document and return removed retrieval chunk count."""
        normalized_id = (document_id or "").strip()
        if not normalized_id:
            raise ValueError("document_id is required")
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM chunks WHERE document_id = ? AND retrievable = 1",
            (normalized_id,),
        ).fetchone()
        retrievable_count = int(row["count"] or 0)
        with self._conn:
            self._conn.execute("DELETE FROM chunks WHERE document_id = ?", (normalized_id,))
        return retrievable_count

    def document_state(self, document_id: str) -> Dict[str, Any]:
        """Return safe incremental-index state without returning source text."""
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS chunk_count,
                   MIN(source_fingerprint) AS min_fingerprint,
                   MAX(source_fingerprint) AS max_fingerprint
            FROM chunks WHERE document_id = ? AND retrievable = 1
            """,
            (document_id,),
        ).fetchone()
        count = int(row["chunk_count"] or 0)
        fingerprint = row["min_fingerprint"] if count and row["min_fingerprint"] == row["max_fingerprint"] else None
        return {
            "document_id": document_id,
            "chunk_count": count,
            "source_fingerprint": fingerprint,
        }

    def _upsert_rows(self, rows: Iterable[tuple[Any, ...]]) -> None:
        self._conn.executemany(
            """
            INSERT INTO chunks (
                chunk_id, document_id, source_path, source_name, file_type,
                text, normalized_text, metadata_json, privacy_labels_json,
                source_fingerprint, checksum, retrievable
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                document_id=excluded.document_id,
                source_path=excluded.source_path,
                source_name=excluded.source_name,
                file_type=excluded.file_type,
                text=excluded.text,
                normalized_text=excluded.normalized_text,
                metadata_json=excluded.metadata_json,
                privacy_labels_json=excluded.privacy_labels_json,
                source_fingerprint=excluded.source_fingerprint,
                checksum=excluded.checksum,
                retrievable=excluded.retrievable
            """,
            rows,
        )
        self._conn.execute(
            """
            DELETE FROM chunk_embeddings
            WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE retrievable = 0)
            """
        )
        self._conn.execute(
            """
            DELETE FROM chunk_sparse_embeddings
            WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE retrievable = 0)
            """
        )
        self._conn.execute(
            """
            DELETE FROM chunk_multivector_embeddings
            WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE retrievable = 0)
            """
        )

    @property
    def semantic_capability(self) -> Optional[SemanticCapability]:
        backend = self._embedding_backend
        return backend.capability if backend is not None else None

    def ensure_embeddings(self) -> int:
        """Persist only missing or stale vectors for the configured local model."""
        with self._conn:
            return self._ensure_embeddings()

    def _ensure_embeddings(self, chunk_ids: Sequence[str] = ()) -> int:
        backend = self._embedding_backend
        if backend is None or not backend.capability.available:
            return 0
        descriptor = backend.descriptor
        parameters: list[Any] = [descriptor.fingerprint]
        where = "WHERE c.retrievable = 1"
        if chunk_ids:
            placeholders = ",".join("?" for _ in chunk_ids)
            where += f" AND c.chunk_id IN ({placeholders})"
            parameters.extend(chunk_ids)
        rows = self._conn.execute(
            f"""
            SELECT c.chunk_id, c.text, e.content_hash,
                   s.content_hash AS sparse_content_hash,
                   m.content_hash AS multivector_content_hash,
                   m.representation_fingerprint AS multivector_representation_fingerprint
            FROM chunks AS c
            LEFT JOIN chunk_embeddings AS e
              ON e.chunk_id = c.chunk_id AND e.model_fingerprint = ?
            LEFT JOIN chunk_sparse_embeddings AS s
              ON s.chunk_id = c.chunk_id AND s.model_fingerprint = ?
            LEFT JOIN chunk_multivector_embeddings AS m
              ON m.chunk_id = c.chunk_id AND m.model_fingerprint = ?
            {where}
            ORDER BY c.chunk_id
            """,
            [
                descriptor.fingerprint,
                descriptor.fingerprint,
                descriptor.fingerprint,
                *parameters[1:],
            ],
        ).fetchall()
        sparse_required = (
            self._sparse_backend is not None
            and self._sparse_backend.sparse_capability.available
        )
        multivector_backend = self._multivector_backend
        multivector_required = (
            multivector_backend is not None
            and multivector_backend.multivector_capability.available
        )
        multivector_descriptor = (
            multivector_backend.multivector_descriptor if multivector_required else None
        )
        pending = [
            row for row in rows
            if row["content_hash"] != _embedding_content_hash(str(row["text"]))
            or (
                sparse_required
                and row["sparse_content_hash"] != _embedding_content_hash(str(row["text"]))
            )
            or (
                multivector_required
                and (
                    row["multivector_content_hash"]
                    != _embedding_content_hash(str(row["text"]))
                    or row["multivector_representation_fingerprint"]
                    != multivector_descriptor.fingerprint
                )
            )
        ]
        if not pending:
            return 0
        vectors = backend.embed_documents(tuple(str(row["text"]) for row in pending))
        if len(vectors) != len(pending):
            raise SemanticBackendError(
                f"embedding count mismatch: expected {len(pending)}, received {len(vectors)}"
            )
        created_at = datetime.now(timezone.utc).isoformat()
        records = []
        for row, vector in zip(pending, vectors):
            records.append((
                str(row["chunk_id"]),
                descriptor.fingerprint,
                _embedding_content_hash(str(row["text"])),
                descriptor.model_id,
                descriptor.revision,
                descriptor.runtime,
                descriptor.runtime_version,
                descriptor.dimension,
                "float32-le",
                int(descriptor.normalized),
                _pack_vector(vector, descriptor.dimension),
                created_at,
            ))
        self._conn.executemany(
            """
            INSERT INTO chunk_embeddings (
                chunk_id, model_fingerprint, content_hash, model_id, model_revision,
                runtime, runtime_version, dimension, dtype, normalized, vector_blob, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id, model_fingerprint) DO UPDATE SET
                content_hash=excluded.content_hash,
                model_id=excluded.model_id,
                model_revision=excluded.model_revision,
                runtime=excluded.runtime,
                runtime_version=excluded.runtime_version,
                dimension=excluded.dimension,
                dtype=excluded.dtype,
                normalized=excluded.normalized,
                vector_blob=excluded.vector_blob,
                created_at=excluded.created_at
            """,
            records,
        )
        sparse_backend = self._sparse_backend
        if sparse_backend is not None and sparse_backend.sparse_capability.available:
            texts = tuple(str(row["text"]) for row in pending)
            sparse_vectors = sparse_backend.sparse_documents(texts)
            if len(sparse_vectors) != len(pending):
                raise SemanticBackendError(
                    f"sparse embedding count mismatch: expected {len(pending)}, "
                    f"received {len(sparse_vectors)}"
                )
            sparse_records = [
                (
                    str(row["chunk_id"]),
                    descriptor.fingerprint,
                    _embedding_content_hash(str(row["text"])),
                    json.dumps(
                        normalize_sparse_vector(vector),
                        ensure_ascii=True,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    created_at,
                )
                for row, vector in zip(pending, sparse_vectors)
            ]
            self._conn.executemany(
                """
                INSERT INTO chunk_sparse_embeddings (
                    chunk_id, model_fingerprint, content_hash, sparse_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id, model_fingerprint) DO UPDATE SET
                    content_hash=excluded.content_hash,
                    sparse_json=excluded.sparse_json,
                    created_at=excluded.created_at
                """,
                sparse_records,
            )
        if multivector_required and multivector_backend is not None:
            texts = tuple(str(row["text"]) for row in pending)
            multivectors = multivector_backend.multivector_documents(texts)
            if len(multivectors) != len(pending):
                raise SemanticBackendError(
                    f"multi-vector embedding count mismatch: expected {len(pending)}, "
                    f"received {len(multivectors)}"
                )
            assert multivector_descriptor is not None
            multivector_records = [
                (
                    str(row["chunk_id"]),
                    descriptor.fingerprint,
                    multivector_descriptor.fingerprint,
                    _embedding_content_hash(str(row["text"])),
                    multivector_descriptor.dimension,
                    len(vector),
                    multivector_descriptor.dtype,
                    multivector_descriptor.schema_version,
                    _pack_multivector(vector, multivector_descriptor),
                    created_at,
                )
                for row, vector in zip(pending, multivectors)
            ]
            self._conn.executemany(
                """
                INSERT INTO chunk_multivector_embeddings (
                    chunk_id, model_fingerprint, representation_fingerprint,
                    content_hash, dimension, token_count, dtype, schema_version,
                    vector_blob, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id, model_fingerprint) DO UPDATE SET
                    representation_fingerprint=excluded.representation_fingerprint,
                    content_hash=excluded.content_hash, dimension=excluded.dimension,
                    token_count=excluded.token_count, dtype=excluded.dtype,
                    schema_version=excluded.schema_version,
                    vector_blob=excluded.vector_blob, created_at=excluded.created_at
                """,
                multivector_records,
            )
        return len(records)

    def embedding_status(self) -> Dict[str, Any]:
        """Return vector coverage/provenance without exposing text or vectors."""
        backend = self._embedding_backend
        total = self.count()
        if backend is None:
            return {
                "configured": False,
                "available": False,
                "indexed_chunk_count": total,
                "embedded_chunk_count": 0,
                "model": None,
            }
        descriptor = backend.descriptor

        def optional_embedding_count(table_name: str) -> int:
            table_exists = self._conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table_name,),
            ).fetchone()
            if table_exists is None:
                return 0
            return int(self._conn.execute(
                f"SELECT COUNT(*) FROM {table_name} WHERE model_fingerprint = ?",
                (descriptor.fingerprint,),
            ).fetchone()[0])

        embedded = int(self._conn.execute(
            "SELECT COUNT(*) FROM chunk_embeddings WHERE model_fingerprint = ?",
            (descriptor.fingerprint,),
        ).fetchone()[0])
        sparse_embedded = optional_embedding_count("chunk_sparse_embeddings")
        multivector_embedded = optional_embedding_count("chunk_multivector_embeddings")
        multivector_backend = self._multivector_backend
        multivector_available = bool(
            multivector_backend is not None
            and multivector_backend.multivector_capability.available
        )
        return {
            "configured": True,
            "available": backend.capability.available,
            "reason": backend.capability.reason,
            "indexed_chunk_count": total,
            "embedded_chunk_count": embedded,
            "sparse_embedded_chunk_count": sparse_embedded,
            "multivector_embedded_chunk_count": multivector_embedded,
            "dense_ready": embedded == total,
            "sparse_ready": sparse_embedded == total,
            "multivector_ready": multivector_available and multivector_embedded == total,
            "model": descriptor.to_safe_dict(),
        }

    def verify_index_coverage(
        self,
        *,
        sparse_required: bool = False,
        multivector_required: bool = False,
        expected_document_fingerprints: Mapping[str, str] | None = None,
    ) -> Dict[str, Any]:
        """Verify SQLite, document identity, and active-model vectors read-only."""
        integrity_rows = self._conn.execute("PRAGMA integrity_check").fetchall()
        integrity_messages = tuple(str(row[0]) for row in integrity_rows)
        integrity_ok = integrity_messages == ("ok",)
        retrievable_chunks = self.count()
        document_rows = self._conn.execute(
            """
            SELECT document_id,
                   MIN(source_fingerprint) AS min_fingerprint,
                   MAX(source_fingerprint) AS max_fingerprint
            FROM chunks
            GROUP BY document_id
            ORDER BY document_id
            """
        ).fetchall()
        actual_document_fingerprints = {
            str(row["document_id"]): (
                str(row["min_fingerprint"])
                if row["min_fingerprint"] is not None
                and row["min_fingerprint"] == row["max_fingerprint"]
                else ""
            )
            for row in document_rows
        }
        expected = (
            {str(key): str(value) for key, value in expected_document_fingerprints.items()}
            if expected_document_fingerprints is not None
            else None
        )
        missing_document_ids: tuple[str, ...] = ()
        unexpected_document_ids: tuple[str, ...] = ()
        fingerprint_mismatch_document_ids: tuple[str, ...] = ()
        documents_complete = True
        if expected is not None:
            missing_document_ids = tuple(sorted(set(expected) - set(actual_document_fingerprints)))
            unexpected_document_ids = tuple(sorted(set(actual_document_fingerprints) - set(expected)))
            fingerprint_mismatch_document_ids = tuple(sorted(
                document_id
                for document_id in set(expected) & set(actual_document_fingerprints)
                if actual_document_fingerprints[document_id] != expected[document_id]
            ))
            documents_complete = not (
                missing_document_ids
                or unexpected_document_ids
                or fingerprint_mismatch_document_ids
            )
        backend = self._embedding_backend
        model_fingerprint = ""
        dense_count = 0
        sparse_count = 0
        multivector_count = 0
        stale_dense_count = 0
        stale_sparse_count = 0
        stale_multivector_count = 0
        semantic_required = backend is not None
        if backend is not None:
            descriptor = backend.descriptor
            model_fingerprint = descriptor.fingerprint
            dense_rows = self._conn.execute(
                """
                SELECT c.text, e.content_hash FROM chunks AS c
                JOIN chunk_embeddings AS e ON c.chunk_id = e.chunk_id
                WHERE c.retrievable = 1 AND e.model_fingerprint = ?
                """,
                (model_fingerprint,),
            ).fetchall()
            dense_count = sum(
                str(row["content_hash"]) == _embedding_content_hash(str(row["text"]))
                for row in dense_rows
            )
            stale_dense_count = int(self._conn.execute(
                "SELECT COUNT(*) FROM chunk_embeddings WHERE model_fingerprint != ?",
                (model_fingerprint,),
            ).fetchone()[0])
            sparse_rows = self._conn.execute(
                """
                SELECT c.text, s.content_hash FROM chunks AS c
                JOIN chunk_sparse_embeddings AS s ON c.chunk_id = s.chunk_id
                WHERE c.retrievable = 1 AND s.model_fingerprint = ?
                """,
                (model_fingerprint,),
            ).fetchall()
            sparse_count = sum(
                str(row["content_hash"]) == _embedding_content_hash(str(row["text"]))
                for row in sparse_rows
            )
            stale_sparse_count = int(self._conn.execute(
                "SELECT COUNT(*) FROM chunk_sparse_embeddings WHERE model_fingerprint != ?",
                (model_fingerprint,),
            ).fetchone()[0])
            multivector_backend = self._multivector_backend
            multivector_descriptor = (
                multivector_backend.multivector_descriptor
                if multivector_required
                and multivector_backend is not None
                and multivector_backend.multivector_capability.available
                else None
            )
            multivector_rows = self._conn.execute(
                """
                SELECT c.text, m.content_hash, m.representation_fingerprint
                FROM chunks AS c
                JOIN chunk_multivector_embeddings AS m ON c.chunk_id = m.chunk_id
                WHERE c.retrievable = 1 AND m.model_fingerprint = ?
                """,
                (model_fingerprint,),
            ).fetchall()
            multivector_count = sum(
                str(row["content_hash"]) == _embedding_content_hash(str(row["text"]))
                and multivector_descriptor is not None
                and str(row["representation_fingerprint"])
                == multivector_descriptor.fingerprint
                for row in multivector_rows
            )
            stale_multivector_count = int(self._conn.execute(
                "SELECT COUNT(*) FROM chunk_multivector_embeddings WHERE model_fingerprint != ?",
                (model_fingerprint,),
            ).fetchone()[0])
        else:
            multivector_count = 0
            stale_multivector_count = 0
        dense_complete = not semantic_required or dense_count == retrievable_chunks
        sparse_complete = not sparse_required or sparse_count == retrievable_chunks
        multivector_complete = (
            not multivector_required or multivector_count == retrievable_chunks
        )
        valid = (
            integrity_ok
            and retrievable_chunks > 0
            and documents_complete
            and dense_complete
            and sparse_complete
            and multivector_complete
        )
        return {
            "valid": valid,
            "integrity_ok": integrity_ok,
            "integrity_messages": integrity_messages,
            "document_count": len(actual_document_fingerprints),
            "expected_document_count": len(expected) if expected is not None else None,
            "documents_complete": documents_complete,
            "missing_document_ids": missing_document_ids,
            "unexpected_document_ids": unexpected_document_ids,
            "fingerprint_mismatch_document_ids": fingerprint_mismatch_document_ids,
            "retrievable_chunk_count": retrievable_chunks,
            "semantic_required": semantic_required,
            "sparse_required": sparse_required,
            "multivector_required": multivector_required,
            "model_fingerprint": model_fingerprint,
            "dense_embedding_count": dense_count,
            "sparse_embedding_count": sparse_count,
            "multivector_embedding_count": multivector_count,
            "dense_complete": dense_complete,
            "sparse_complete": sparse_complete,
            "multivector_complete": multivector_complete,
            "stale_dense_embedding_count": stale_dense_count,
            "stale_sparse_embedding_count": stale_sparse_count,
            "stale_multivector_embedding_count": stale_multivector_count,
        }

    def dense_candidates(
        self,
        query: str | RetrievalQueryPlan,
        *,
        limit: int = 100,
        options: Optional[SearchOptions] = None,
        ensure_embeddings: bool = True,
    ) -> List[SearchResult]:
        """Return filtered local cosine candidates fused only across query variants."""
        backend = self._embedding_backend
        if backend is None:
            raise SemanticBackendError("embedding backend is not configured")
        backend.capability.require()
        if limit <= 0:
            return []
        options = options or SearchOptions()
        plan = coerce_query_plan(query)
        if ensure_embeddings and not self._read_only:
            self.ensure_embeddings()
        descriptor = backend.descriptor
        rows = self._conn.execute(
            """
            SELECT c.*, e.dimension AS embedding_dimension, e.vector_blob
            FROM chunks AS c
            JOIN chunk_embeddings AS e ON e.chunk_id = c.chunk_id
            WHERE c.retrievable = 1
              AND e.model_fingerprint = ? AND e.dtype = 'float32-le' AND e.normalized = 1
            """,
            (descriptor.fingerprint,),
        ).fetchall()
        eligible = []
        for row in rows:
            privacy_labels = tuple(json.loads(row["privacy_labels_json"] or "[]"))
            if not self._is_selected(row, options):
                continue
            if not self._privacy_is_allowed(privacy_labels, options):
                continue
            if self._is_stale(row, options):
                continue
            eligible.append((row, privacy_labels))

        fused: dict[str, dict[str, Any]] = {}
        for variant in plan.variants:
            query_vector = normalize_vector(
                backend.embed_query(variant.text),
                dimension=descriptor.dimension,
            )
            ranked = []
            for row, privacy_labels in eligible:
                dimension = int(row["embedding_dimension"])
                if dimension != descriptor.dimension:
                    continue
                vector = _unpack_vector(bytes(row["vector_blob"]), dimension)
                similarity = cosine_similarity(query_vector, vector)
                ranked.append((similarity, row, privacy_labels))
            ranked.sort(key=lambda item: (
                -item[0], item[1]["document_id"], item[1]["source_path"], item[1]["chunk_id"]
            ))
            variant_weight = 1.25 if variant.origin == "original" else 1.0
            for rank, (similarity, row, privacy_labels) in enumerate(
                ranked[: options.candidate_limit], 1
            ):
                key = str(row["chunk_id"])
                record = fused.setdefault(key, {
                    "rrf_score": 0.0,
                    "best_similarity": similarity,
                    "row": row,
                    "privacy_labels": privacy_labels,
                    "variants": [],
                    "variant_ids": [],
                    "facet_ids": [],
                })
                record["rrf_score"] += variant_weight / (60.0 + rank)
                record["variants"].append(variant.text)
                record["variant_ids"].append(variant.variant_id)
                record["facet_ids"].append(variant.facet_id)
                if similarity > record["best_similarity"]:
                    record["best_similarity"] = similarity
                    record["row"] = row
                    record["privacy_labels"] = privacy_labels

        ordered = sorted(fused.values(), key=lambda item: (
            -item["rrf_score"], -item["best_similarity"], item["row"]["document_id"],
            item["row"]["source_path"], item["row"]["chunk_id"],
        ))[:limit]
        results = []
        for record in ordered:
            row = record["row"]
            metadata = json.loads(row["metadata_json"])
            section_text = " ".join(_text_values(metadata.get("section_path")))
            obligations = match_text_obligations(
                plan.intent_category,
                (str(row["normalized_text"]), section_text),
                required_obligations=plan.required_obligations,
            )
            results.append(SearchResult(
                chunk_id=row["chunk_id"],
                score=float(record["best_similarity"]),
                text=row["text"],
                document_id=row["document_id"],
                source_path=row["source_path"],
                source_name=row["source_name"],
                file_type=row["file_type"],
                metadata=metadata,
                privacy_labels=record["privacy_labels"],
                ranking_signals={
                    "dense_cosine": float(record["best_similarity"]),
                    "dense_multi_variant_rrf": float(record["rrf_score"]),
                },
                matched_query_variants=tuple(record["variants"]),
                matched_query_variant_ids=tuple(dict.fromkeys(record["variant_ids"])),
                matched_query_facets=tuple(dict.fromkeys(record["facet_ids"])),
                matched_obligations=tuple(obligations),
            ))
        return results

    def dense_search_with_summary(
        self,
        query: str | RetrievalQueryPlan,
        *,
        limit: int = 10,
        options: Optional[SearchOptions] = None,
        dense_limit: int = 100,
        ranking_config: Optional[HybridRankingConfig] = None,
    ) -> SearchResponse:
        """Run a true dense-only channel while preserving standard assembly telemetry."""
        options = options or SearchOptions()
        plan = coerce_query_plan(query)
        dense_started = perf_counter()
        dense_results = self.dense_candidates(
            plan,
            limit=dense_limit,
            options=options,
        )
        dense_latency_ms = (perf_counter() - dense_started) * 1000.0
        base = SearchResponse(
            results=(),
            summary=SearchSummary(
                query=plan.original_query,
                indexed_chunk_count=self.count(),
                eligible_chunk_count=len(dense_results),
                candidate_count=0,
                returned_count=0,
                query_variant_count=len(plan.variants),
                query_plan_fingerprint=plan.fingerprint,
                expansion_status=plan.expansion_status,
                candidate_backend="bge_m3_dense",
                dense_latency_ms=dense_latency_ms,
            ),
        )
        fused = fuse_ranked_channels(
            plan,
            base,
            dense_results,
            limit=limit,
            options=options,
            config=ranking_config,
        )
        return SearchResponse(
            results=fused.results,
            summary=replace(
                fused.summary,
                candidate_backend="bge_m3_dense",
                lexical_pool=(),
                sparse_pool=(),
                lexical_latency_ms=0.0,
                sparse_latency_ms=0.0,
            ),
        )

    def hybrid_search_with_summary(
        self,
        query: str | RetrievalQueryPlan,
        *,
        limit: int = 10,
        dense_limit: int = 100,
        options: Optional[SearchOptions] = None,
        ranking_config: Optional[HybridRankingConfig] = None,
        reranker: Optional[RerankerBackend] = None,
        use_multivector: bool = False,
        precomputed_only: bool = False,
    ) -> SearchResponse:
        """Run bounded hybrid retrieval with optional precomputed MaxSim authority."""
        options = options or SearchOptions()
        pool_options = replace(
            options,
            candidate_limit=max(options.candidate_limit, dense_limit),
            per_document_limit=max(options.per_document_limit, dense_limit),
        )
        lexical_started = perf_counter()
        lexical = self.search_with_summary(
            query,
            limit=pool_options.candidate_limit,
            options=pool_options,
        )
        lexical_latency_ms = (perf_counter() - lexical_started) * 1000.0
        dense_started = perf_counter()
        dense = self.dense_candidates(
            query,
            limit=dense_limit,
            options=pool_options,
            ensure_embeddings=not precomputed_only,
        )
        dense_latency_ms = (perf_counter() - dense_started) * 1000.0
        sparse: Sequence[SearchResult] = ()
        sparse_latency_ms = 0.0
        if self._sparse_backend is not None:
            sparse_started = perf_counter()
            sparse = self.sparse_candidates(
                query,
                limit=dense_limit,
                options=pool_options,
                ensure_embeddings=not precomputed_only,
            )
            sparse_latency_ms = (perf_counter() - sparse_started) * 1000.0
        multivector_scores: Optional[Mapping[str, float]] = None
        multivector_load_latency_ms = 0.0
        multivector_maxsim_latency_ms = 0.0
        if use_multivector:
            plan = coerce_query_plan(query)
            ranking = ranking_config or HybridRankingConfig()
            window = self._balanced_multivector_window(
                lexical.results,
                dense,
                sparse,
                ranking.rerank_limit,
            )
            (
                multivector_scores,
                multivector_load_latency_ms,
                multivector_maxsim_latency_ms,
            ) = self._multivector_rerank_scores(plan, window)
        response = fuse_ranked_channels(
            query,
            lexical,
            dense,
            limit=limit,
            options=pool_options,
            sparse_results=sparse,
            config=ranking_config,
            reranker=reranker,
            multivector_scores=multivector_scores,
            multivector_load_latency_ms=multivector_load_latency_ms,
            multivector_maxsim_latency_ms=multivector_maxsim_latency_ms,
        )
        return SearchResponse(
            results=response.results,
            summary=replace(
                response.summary,
                lexical_latency_ms=lexical_latency_ms,
                dense_latency_ms=dense_latency_ms,
                sparse_latency_ms=sparse_latency_ms,
            ),
        )

    def expand_context(
        self,
        response: SearchResponse,
        *,
        options: Optional[SearchOptions] = None,
        neighbor_window: int = 1,
        parent_limit: int = 1,
    ) -> SearchResponse:
        """Append safe parent/neighbor text without changing winner identities or ranks."""
        if neighbor_window < 0 or parent_limit < 0:
            raise ValueError("context expansion limits must be non-negative")
        if not response.results:
            return response
        options = options or SearchOptions()
        started = perf_counter()
        document_ids = tuple(dict.fromkeys(result.document_id for result in response.results))
        placeholders = ",".join("?" for _ in document_ids)
        rows = self._conn.execute(
            f"SELECT * FROM chunks WHERE document_id IN ({placeholders}) ORDER BY chunk_id",
            document_ids,
        ).fetchall()

        eligible: dict[str, tuple[sqlite3.Row, Dict[str, Any]]] = {}
        for row in rows:
            labels = tuple(json.loads(row["privacy_labels_json"] or "[]"))
            if (
                self._is_selected(row, options)
                and self._privacy_is_allowed(labels, options)
                and not self._is_stale(row, options)
            ):
                eligible[str(row["chunk_id"])] = (row, json.loads(row["metadata_json"]))

        def values(metadata: Mapping[str, Any], key: str) -> tuple[str, ...]:
            raw = metadata.get(key, ())
            if isinstance(raw, (list, tuple)):
                return tuple(str(value) for value in raw if str(value))
            return ()

        def nested(metadata: Mapping[str, Any]) -> Mapping[str, Any]:
            raw = metadata.get("metadata")
            return raw if isinstance(raw, Mapping) else {}

        def integer(value: Any, default: int = -1) -> int:
            return int(value) if isinstance(value, int) and not isinstance(value, bool) else default

        def structural_key(item: tuple[sqlite3.Row, Mapping[str, Any]]) -> tuple[Any, ...]:
            row, metadata = item
            detail = nested(metadata)
            element_ids = values(metadata, "element_ids")
            sheet_names = values(metadata, "sheet_names")
            row_range = metadata.get("row_range")
            column_range = metadata.get("column_range")
            return (
                str(detail.get("element_id") or (element_ids[0] if element_ids else "")),
                integer(detail.get("part_index")),
                integer(detail.get("page")),
                integer(detail.get("slide")),
                str(detail.get("sheet") or (sheet_names[0] if sheet_names else "")),
                integer(row_range[0]) if isinstance(row_range, (list, tuple)) and row_range else -1,
                integer(column_range[0]) if isinstance(column_range, (list, tuple)) and column_range else -1,
                str(row["chunk_id"]),
            )

        expanded_results: list[SearchResult] = []
        added_count = 0
        for result in response.results:
            winner_item = eligible.get(result.chunk_id)
            if winner_item is None:
                expanded_results.append(result)
                continue
            winner_row, winner_metadata = winner_item
            winner_elements = set(values(winner_metadata, "element_ids"))
            winner_parents = set(values(winner_metadata, "parent_element_ids"))
            winner_section = values(winner_metadata, "section_path")
            winner_sheets = values(winner_metadata, "sheet_names")
            winner_types = {value.casefold() for value in values(winner_metadata, "element_types")}

            def relation(item: tuple[sqlite3.Row, Mapping[str, Any]]) -> str:
                row, metadata = item
                chunk_id = str(row["chunk_id"])
                if chunk_id == result.chunk_id:
                    return "winner"
                candidate_elements = set(values(metadata, "element_ids"))
                if candidate_elements & winner_parents:
                    return "parent"
                return "neighbor"

            def same_boundary(item: tuple[sqlite3.Row, Mapping[str, Any]]) -> bool:
                row, metadata = item
                if str(row["document_id"]) != result.document_id:
                    return False
                candidate_elements = set(values(metadata, "element_ids"))
                if candidate_elements & winner_parents:
                    return True
                if "table" in winner_types:
                    return (
                        values(metadata, "section_path") == winner_section
                        and values(metadata, "sheet_names") == winner_sheets
                        and bool(candidate_elements & winner_elements)
                    )
                if winner_section:
                    return values(metadata, "section_path") == winner_section
                if winner_parents:
                    return bool(
                        set(values(metadata, "parent_element_ids")) & winner_parents
                        or candidate_elements & winner_parents
                    )
                if winner_elements:
                    return bool(candidate_elements & winner_elements)
                return True

            scoped = sorted(
                (item for item in eligible.values() if same_boundary(item)),
                key=structural_key,
            )
            winner_position = next(
                (index for index, item in enumerate(scoped) if str(item[0]["chunk_id"]) == result.chunk_id),
                -1,
            )
            selected: dict[str, tuple[sqlite3.Row, Mapping[str, Any]]] = {
                result.chunk_id: winner_item,
            }
            if winner_position >= 0 and neighbor_window:
                start = max(0, winner_position - neighbor_window)
                stop = min(len(scoped), winner_position + neighbor_window + 1)
                for item in scoped[start:stop]:
                    selected[str(item[0]["chunk_id"])] = item
            if parent_limit and winner_parents:
                parents = sorted(
                    (
                        item for item in eligible.values()
                        if set(values(item[1], "element_ids")) & winner_parents
                    ),
                    key=structural_key,
                )
                for item in parents[:parent_limit]:
                    selected[str(item[0]["chunk_id"])] = item

            ordered = sorted(selected.values(), key=structural_key)
            context_rows = [
                {
                    "chunk_id": str(row["chunk_id"]),
                    "checksum": str(row["checksum"] or ""),
                    "relation": relation((row, metadata)),
                    "structural_order_key": list(structural_key((row, metadata))),
                    "element_ids": list(values(metadata, "element_ids")),
                    "parent_element_ids": list(values(metadata, "parent_element_ids")),
                    "section_path": list(values(metadata, "section_path")),
                }
                for row, metadata in ordered
            ]
            context_text = "\n\n".join(str(row["text"]) for row, _metadata in ordered)
            expansion_metadata = dict(result.metadata)
            expansion_metadata["context_expansion"] = {
                "status": "expanded" if len(ordered) > 1 else "identity",
                "winner_chunk_id": result.chunk_id,
                "context_chunk_ids": [row["chunk_id"] for row in context_rows],
                "context_chunks": context_rows,
                "context_checksum": _embedding_content_hash(context_text),
            }
            signals = dict(result.ranking_signals)
            signals["context_chunk_count"] = float(len(ordered))
            signals["context_expanded"] = float(len(ordered) > 1)
            added_count += max(0, len(ordered) - 1)
            expanded_results.append(replace(
                result,
                text=context_text,
                metadata=expansion_metadata,
                ranking_signals=signals,
            ))

        identity = lambda result: (result.chunk_id, result.document_id, result.source_name)
        return SearchResponse(
            results=tuple(expanded_results),
            summary=replace(
                response.summary,
                expanded_pool=tuple(identity(result) for result in expanded_results),
                context_expansion_latency_ms=(perf_counter() - started) * 1000.0,
                context_expansion_added_chunk_count=added_count,
            ),
        )

    def sparse_candidates(
        self,
        query: str | RetrievalQueryPlan,
        *,
        limit: int = 100,
        options: Optional[SearchOptions] = None,
        ensure_embeddings: bool = True,
    ) -> List[SearchResult]:
        """Return filtered learned-sparse candidates fused across query variants."""
        backend = self._sparse_backend
        embedding_backend = self._embedding_backend
        if backend is None or embedding_backend is None:
            raise SemanticBackendError("sparse embedding backend is not configured")
        backend.sparse_capability.require()
        if limit <= 0:
            return []
        options = options or SearchOptions()
        plan = coerce_query_plan(query)
        if ensure_embeddings and not self._read_only:
            self.ensure_embeddings()
        descriptor = embedding_backend.descriptor
        rows = self._conn.execute(
            """
            SELECT c.*, s.sparse_json
            FROM chunks AS c
            JOIN chunk_sparse_embeddings AS s ON s.chunk_id = c.chunk_id
            WHERE c.retrievable = 1 AND s.model_fingerprint = ?
            """,
            (descriptor.fingerprint,),
        ).fetchall()
        eligible = []
        for row in rows:
            privacy_labels = tuple(json.loads(row["privacy_labels_json"] or "[]"))
            if not self._is_selected(row, options):
                continue
            if not self._privacy_is_allowed(privacy_labels, options):
                continue
            if self._is_stale(row, options):
                continue
            eligible.append((row, privacy_labels, normalize_sparse_vector(json.loads(row["sparse_json"]))))

        fused: dict[str, dict[str, Any]] = {}
        for variant in plan.variants:
            query_vector = normalize_sparse_vector(backend.sparse_query(variant.text))
            ranked = [
                (sparse_dot_similarity(query_vector, vector), row, privacy_labels)
                for row, privacy_labels, vector in eligible
            ]
            ranked = [item for item in ranked if item[0] > 0.0]
            ranked.sort(key=lambda item: (
                -item[0], item[1]["document_id"], item[1]["source_path"], item[1]["chunk_id"]
            ))
            variant_weight = 1.25 if variant.origin == "original" else 1.0
            for rank, (similarity, row, privacy_labels) in enumerate(
                ranked[: options.candidate_limit], 1
            ):
                key = str(row["chunk_id"])
                record = fused.setdefault(key, {
                    "rrf_score": 0.0,
                    "best_similarity": similarity,
                    "row": row,
                    "privacy_labels": privacy_labels,
                    "variants": [],
                    "variant_ids": [],
                    "facet_ids": [],
                })
                record["rrf_score"] += variant_weight / (60.0 + rank)
                record["variants"].append(variant.text)
                record["variant_ids"].append(variant.variant_id)
                record["facet_ids"].append(variant.facet_id)
                record["best_similarity"] = max(record["best_similarity"], similarity)

        ordered = sorted(fused.values(), key=lambda item: (
            -item["rrf_score"], -item["best_similarity"], item["row"]["document_id"],
            item["row"]["source_path"], item["row"]["chunk_id"],
        ))[:limit]
        results = []
        for record in ordered:
            row = record["row"]
            metadata = json.loads(row["metadata_json"])
            section_text = " ".join(_text_values(metadata.get("section_path")))
            obligations = match_text_obligations(
                plan.intent_category,
                (str(row["normalized_text"]), section_text),
                required_obligations=plan.required_obligations,
            )
            results.append(SearchResult(
                chunk_id=row["chunk_id"], score=float(record["best_similarity"]),
                text=row["text"], document_id=row["document_id"],
                source_path=row["source_path"], source_name=row["source_name"],
                file_type=row["file_type"], metadata=metadata,
                privacy_labels=record["privacy_labels"],
                ranking_signals={
                    "sparse_dot": float(record["best_similarity"]),
                    "sparse_multi_variant_rrf": float(record["rrf_score"]),
                },
                matched_query_variants=tuple(record["variants"]),
                matched_query_variant_ids=tuple(dict.fromkeys(record["variant_ids"])),
                matched_query_facets=tuple(dict.fromkeys(record["facet_ids"])),
                matched_obligations=tuple(obligations),
            ))
        return results

    def _multivector_rerank_scores(
        self,
        query: RetrievalQueryPlan,
        candidate_ids: Sequence[str],
    ) -> tuple[dict[str, float], float, float]:
        backend = self._multivector_backend
        embedding_backend = self._embedding_backend
        if backend is None or embedding_backend is None:
            raise SemanticBackendError("multi-vector embedding backend is not configured")
        backend.multivector_capability.require()
        if not candidate_ids:
            return {}, 0.0, 0.0
        descriptor = backend.multivector_descriptor
        model_fingerprint = embedding_backend.descriptor.fingerprint
        unique_ids = tuple(dict.fromkeys(str(value) for value in candidate_ids))
        placeholders = ",".join("?" for _ in unique_ids)
        load_started = perf_counter()
        rows = self._conn.execute(
            f"""
            SELECT c.chunk_id, c.text, m.content_hash, m.representation_fingerprint,
                   m.dimension, m.token_count, m.dtype, m.schema_version, m.vector_blob
            FROM chunks AS c
            JOIN chunk_multivector_embeddings AS m ON m.chunk_id = c.chunk_id
            WHERE c.retrievable = 1 AND m.model_fingerprint = ?
              AND c.chunk_id IN ({placeholders})
            """,
            (model_fingerprint, *unique_ids),
        ).fetchall()
        by_id = {str(row["chunk_id"]): row for row in rows}
        missing = tuple(chunk_id for chunk_id in unique_ids if chunk_id not in by_id)
        if missing:
            raise SemanticBackendError(
                f"multi-vector index coverage incomplete for rerank window: {len(missing)} missing"
            )
        documents: dict[str, MultiVector] = {}
        for chunk_id in unique_ids:
            row = by_id[chunk_id]
            if (
                str(row["content_hash"]) != _embedding_content_hash(str(row["text"]))
                or str(row["representation_fingerprint"]) != descriptor.fingerprint
                or int(row["dimension"]) != descriptor.dimension
                or int(row["schema_version"]) != descriptor.schema_version
                or str(row["dtype"]) != descriptor.dtype
                or int(row["token_count"]) > descriptor.max_tokens
            ):
                raise SemanticBackendError("persisted multi-vector is stale or incompatible")
            documents[chunk_id] = _unpack_multivector(
                bytes(row["vector_blob"]),
                dimension=int(row["dimension"]),
                token_count=int(row["token_count"]),
                dtype=str(row["dtype"]),
            )
        load_latency_ms = (perf_counter() - load_started) * 1000.0
        query_vectors = backend.multivector_query(query.original_query)
        maxsim_started = perf_counter()
        scores = {
            chunk_id: late_interaction_maxsim(
                query_vectors,
                documents[chunk_id],
                dimension=descriptor.dimension,
            )
            for chunk_id in unique_ids
        }
        maxsim_latency_ms = (perf_counter() - maxsim_started) * 1000.0
        return scores, load_latency_ms, maxsim_latency_ms

    @staticmethod
    def _balanced_multivector_window(
        lexical: Sequence[SearchResult],
        dense: Sequence[SearchResult],
        sparse: Sequence[SearchResult],
        limit: int,
    ) -> tuple[str, ...]:
        if limit < 1:
            return ()
        pools = (dense, sparse, lexical)
        selected: list[str] = []
        seen: set[str] = set()
        depth = 0
        while len(selected) < limit and any(depth < len(pool) for pool in pools):
            for pool in pools:
                if depth >= len(pool):
                    continue
                chunk_id = pool[depth].chunk_id
                if chunk_id not in seen:
                    seen.add(chunk_id)
                    selected.append(chunk_id)
                    if len(selected) >= limit:
                        break
            depth += 1
        return tuple(selected)

    def search(
        self,
        query: str | RetrievalQueryPlan,
        limit: int = 10,
        options: Optional[SearchOptions] = None,
    ) -> List[SearchResult]:
        """Return generic local results while preserving the original list API."""
        return list(self.search_with_summary(query, limit=limit, options=options).results)

    def search_with_summary(
        self,
        query: str | RetrievalQueryPlan,
        limit: int = 10,
        options: Optional[SearchOptions] = None,
    ) -> SearchResponse:
        """Run filter, candidate, ranking, and diversity stages locally."""
        options = options or SearchOptions()
        query_plan = coerce_query_plan(query)
        query_text = query_plan.original_query
        terms = extract_content_terms(query_text)
        indexed_rows = self._conn.execute(
            "SELECT * FROM chunks WHERE retrievable = 1"
        ).fetchall()

        if not terms:
            return self._empty_response(
                query=query_text,
                indexed_chunk_count=len(indexed_rows),
                reason="empty_or_tokenless_query",
            )
        if limit <= 0:
            return self._empty_response(
                query=query_text,
                indexed_chunk_count=len(indexed_rows),
                reason="non_positive_limit",
            )

        eligible_rows: List[sqlite3.Row] = []
        filtered_by_source = 0
        filtered_by_privacy = 0
        filtered_as_stale = 0
        for row in indexed_rows:
            privacy_labels = tuple(json.loads(row["privacy_labels_json"] or "[]"))
            if not self._is_selected(row, options):
                filtered_by_source += 1
                continue
            if not self._privacy_is_allowed(privacy_labels, options):
                filtered_by_privacy += 1
                continue
            if self._is_stale(row, options):
                filtered_as_stale += 1
                continue
            eligible_rows.append(row)

        # Rank each validated query variant independently, then fuse by rank.
        # Filtering is already complete above, so FTS and variants can never bypass
        # privacy, source-selection, or stale-fingerprint constraints.
        per_variant_candidates: list[tuple[Any, list[tuple[float, sqlite3.Row, Dict[str, Any], tuple[str, ...], Dict[str, float], tuple[str, ...], float]]]] = []
        candidate_backend = self.retrieval_backend
        for variant in query_plan.variants:
            variant_terms = extract_content_terms(variant.text)
            if not variant_terms:
                continue
            candidate_rows, backend = self._candidate_rows(
                variant.text,
                eligible_rows,
                options.candidate_limit,
            )
            if backend != "fts5_bm25":
                candidate_backend = "deterministic_scan"
            ranked = []
            for candidate_position, row in enumerate(candidate_rows):
                candidate = self._score_candidate(row, variant_terms, query_plan=query_plan)
                if candidate is not None:
                    ranked.append((candidate_position, candidate))
            ranked.sort(
                key=lambda item: (
                    -item[1][0],
                    item[0],
                    item[1][1]["document_id"],
                    item[1][1]["source_path"],
                    item[1][1]["chunk_id"],
                )
            )
            per_variant_candidates.append(
                (variant, [item[1] for item in ranked[: options.candidate_limit]])
            )

        fused: dict[str, dict[str, Any]] = {}
        for variant, candidates_for_variant in per_variant_candidates:
            variant_weight = 1.25 if variant.origin == "original" else 1.0
            for rank, candidate in enumerate(candidates_for_variant, 1):
                score, row, metadata, privacy_labels, signals, matched_terms, coverage = candidate
                key = str(row["chunk_id"])
                record = fused.setdefault(
                    key,
                    {
                        "rrf_score": 0.0,
                        "best_score": score,
                        "row": row,
                        "metadata": metadata,
                        "privacy_labels": privacy_labels,
                        "signals": dict(signals),
                        "matched_terms": matched_terms,
                        "coverage": coverage,
                        "variants": [],
                        "variant_ids": [],
                        "facet_ids": [],
                        "target_equivalent_variant_ids": [],
                        "equivalent_variant_match_counts": {},
                        "variant_term_matches": {},
                        "target_match_count": float(signals.get("target_term_match_count", 0.0)),
                    },
                )
                record["rrf_score"] += (1.0 / (60.0 + rank)) * variant_weight
                record["target_match_count"] = max(
                    float(record["target_match_count"]),
                    float(signals.get("target_term_match_count", 0.0)),
                )
                record["variants"].append(variant.text)
                record["variant_ids"].append(variant.variant_id)
                record["facet_ids"].append(variant.facet_id)
                if variant.target_equivalent and len(matched_terms) >= 2:
                    # Named aliases are query-only translations.  They may broaden
                    # recall, but a single generic token (for example 手順 / procedure)
                    # is not sufficient to attest that a candidate addresses the
                    # named target.  Require two alias anchors before it can affect
                    # target-support selection or cross-lingual relevance gates.
                    record["target_equivalent_variant_ids"].append(variant.variant_id)
                    matched_count = float(len(matched_terms))
                    record["equivalent_variant_match_counts"][variant.variant_id] = max(
                        float(record["equivalent_variant_match_counts"].get(variant.variant_id, 0.0)),
                        matched_count,
                    )
                    record["signals"]["equivalent_target_term_match_count"] = max(
                        float(record["signals"].get("equivalent_target_term_match_count", 0.0)),
                        matched_count,
                    )
                record["variant_term_matches"][variant.text] = matched_terms
                if score > record["best_score"]:
                    record.update(
                        best_score=score,
                        row=row,
                        metadata=metadata,
                        privacy_labels=privacy_labels,
                        signals=dict(signals),
                        matched_terms=matched_terms,
                        coverage=coverage,
                    )

        for candidate in fused.values():
            row = candidate["row"]
            metadata = candidate["metadata"]
            section_text = " ".join(_text_values(metadata.get("section_path")))
            candidate["obligation_ids"] = match_text_obligations(
                query_plan.intent_category,
                (str(row["normalized_text"]), section_text),
                required_obligations=query_plan.required_obligations,
            )

        planned_obligation_ids = tuple(
            obligation
            for obligation in query_plan.required_obligations
            if obligation != "query"
        )
        candidates = sorted(
            fused.values(),
            key=lambda item: (
                -int(bool(item.get("target_equivalent_variant_ids"))),
                -float(item.get("target_match_count", 0.0))
                if query_plan.intent_category == "lookup" else 0.0,
                -item["rrf_score"],
                -item["best_score"],
                item["row"]["document_id"],
                item["row"]["source_path"],
                item["row"]["chunk_id"],
            ),
        )[: options.candidate_limit]

        def candidate_has_target_support(candidate: Mapping[str, Any]) -> bool:
            if query_plan.intent_category != "procedure" or not query_plan.target_terms:
                return True
            return (
                float(candidate.get("target_match_count", 0.0)) > 0.0
                or bool(candidate.get("target_equivalent_variant_ids"))
            )

        obligation_first = []
        obligation_selected_keys = set()
        for obligation_id in planned_obligation_ids:
            match = next(
                (
                    candidate
                    for candidate in candidates
                    if candidate_has_target_support(candidate)
                    and obligation_id in candidate["obligation_ids"]
                    and str(candidate["row"]["chunk_id"]) not in obligation_selected_keys
                ),
                None,
            )
            if match is not None:
                obligation_first.append(match)
                obligation_selected_keys.add(str(match["row"]["chunk_id"]))
        candidates = obligation_first + [
            candidate
            for candidate in candidates
            if str(candidate["row"]["chunk_id"]) not in obligation_selected_keys
        ]

        structural_facets = tuple(
            facet_id for facet_id in query_plan.facet_ids if facet_id != "query"
        )

        def has_equivalent_facet_support(candidate: Mapping[str, Any], facet_id: str) -> bool:
            """Require a validated target-equivalent variant assigned to the facet."""
            if facet_id not in candidate["facet_ids"]:
                return False
            variants_by_id = {variant.variant_id: variant for variant in query_plan.variants}
            return any(
                (variant := variants_by_id.get(variant_id)) is not None
                and variant.facet_id == facet_id
                for variant_id in candidate["target_equivalent_variant_ids"]
            )

        if structural_facets:
            facet_first = []
            facet_selected_keys = set()
            for facet_id in structural_facets:
                match = next(
                    (
                        candidate
                        for candidate in candidates
                        if candidate_has_target_support(candidate)
                        and str(candidate["row"]["chunk_id"]) not in facet_selected_keys
                        and (
                            has_equivalent_facet_support(candidate, facet_id)
                            if any(
                                variant.target_equivalent and variant.facet_id == facet_id
                                for variant in query_plan.variants
                            )
                            else facet_id in candidate["facet_ids"]
                        )
                    ),
                    None,
                )
                if match is not None:
                    facet_first.append(match)
                    facet_selected_keys.add(str(match["row"]["chunk_id"]))
            candidates = facet_first + [
                candidate
                for candidate in candidates
                if str(candidate["row"]["chunk_id"]) not in facet_selected_keys
            ]

        results: List[SearchResult] = []
        returned_candidates: List[Dict[str, Any]] = []
        document_counts: Counter[str] = Counter()
        diversity_limited = 0
        for candidate in candidates:

            row = candidate["row"]
            document_key = row["document_id"] or row["source_path"]
            if document_counts[document_key] >= options.per_document_limit:
                diversity_limited += 1
                continue
            document_counts[document_key] += 1
            signals = dict(candidate["signals"])
            signals["multi_variant_rrf"] = candidate["rrf_score"]
            for variant_id, match_count in candidate["equivalent_variant_match_counts"].items():
                signals[f"equivalent_variant_match_count:{variant_id}"] = float(match_count)
            results.append(
                SearchResult(
                    chunk_id=row["chunk_id"],
                    score=float(candidate["best_score"]),
                    text=row["text"],
                    document_id=row["document_id"],
                    source_path=row["source_path"],
                    source_name=row["source_name"],
                    file_type=row["file_type"],
                    metadata=candidate["metadata"],
                    privacy_labels=candidate["privacy_labels"],
                    ranking_signals=signals,
                    matched_terms=candidate["matched_terms"],
                    term_coverage=float(candidate["coverage"]),
                    matched_query_variants=tuple(candidate["variants"]),
                    matched_query_variant_ids=tuple(dict.fromkeys(candidate["variant_ids"])),
                    matched_target_equivalent_variant_ids=tuple(
                        dict.fromkeys(candidate["target_equivalent_variant_ids"])
                    ),
                    matched_query_facets=tuple(dict.fromkeys(candidate["facet_ids"])),
                    matched_obligations=tuple(candidate["obligation_ids"]),
                )
            )
            returned_candidates.append(candidate)
            if len(results) >= limit:
                break

        best_term_coverage = max((result.term_coverage for result in results), default=0.0)
        evidence_set_coverage = self._evidence_set_term_coverage(returned_candidates, query_plan)

        reasons = self._insufficiency_reasons(
            indexed_count=len(indexed_rows),
            eligible_count=len(eligible_rows),
            candidate_count=len(candidates),
            result_count=len(results),
            filtered_by_source=filtered_by_source,
            filtered_by_privacy=filtered_by_privacy,
            filtered_as_stale=filtered_as_stale,
            best_coverage=evidence_set_coverage,
            term_count=len(query_plan.content_terms) or len(terms),
        )
        if query_plan.expansion_status not in {"identity", "faceted", "expanded"}:
            reasons = tuple(dict.fromkeys((*reasons, query_plan.expansion_status)))
        planned_facet_ids = query_plan.facet_ids
        covered_facet_ids = tuple(
            facet_id
            for facet_id in planned_facet_ids
            if any(facet_id in result.matched_query_facets for result in results)
        )
        missing_facet_ids = tuple(
            facet_id for facet_id in planned_facet_ids if facet_id not in covered_facet_ids
        )
        covered_obligation_ids = tuple(
            obligation_id
            for obligation_id in planned_obligation_ids
            if any(obligation_id in result.matched_obligations for result in results)
        )
        missing_obligation_ids = tuple(
            obligation_id
            for obligation_id in planned_obligation_ids
            if obligation_id not in covered_obligation_ids
        )
        candidate_identities = tuple(
            (
                str(candidate["row"]["chunk_id"]),
                str(candidate["row"]["document_id"]),
                str(candidate["row"]["source_name"]),
            )
            for candidate in candidates
        )
        returned_ids = {result.chunk_id for result in results}
        assembly_rejected = tuple(
            identity for identity in candidate_identities if identity[0] not in returned_ids
        )
        summary = SearchSummary(
            query=query_text,
            indexed_chunk_count=len(indexed_rows),
            eligible_chunk_count=len(eligible_rows),
            candidate_count=len(candidates),
            returned_count=len(results),
            filtered_by_source_count=filtered_by_source,
            filtered_by_privacy_count=filtered_by_privacy,
            filtered_as_stale_count=filtered_as_stale,
            diversity_limited_count=diversity_limited,
            best_term_coverage=best_term_coverage,
            insufficiency_reasons=reasons,
            query_variant_count=len(query_plan.variants),
            query_plan_fingerprint=query_plan.fingerprint,
            expansion_status=query_plan.expansion_status,
            candidate_backend=candidate_backend,
            evidence_set_term_coverage=evidence_set_coverage,
            planned_facet_ids=planned_facet_ids,
            covered_facet_ids=covered_facet_ids,
            missing_facet_ids=missing_facet_ids,
            planned_obligation_ids=planned_obligation_ids,
            covered_obligation_ids=covered_obligation_ids,
            missing_obligation_ids=missing_obligation_ids,
            lexical_pool=candidate_identities,
            fused_pool=candidate_identities,
            ranked_pool=candidate_identities,
            assembly_rejected_pool=assembly_rejected,
        )
        return SearchResponse(results=tuple(results), summary=summary)

    def clear(self) -> None:
        self._conn.execute("DELETE FROM chunks")
        self._conn.commit()

    def count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM chunks WHERE retrievable = 1"
        ).fetchone()
        return int(row["count"])

    def _candidate_rows(
        self,
        query: str,
        eligible_rows: List[sqlite3.Row],
        limit: int,
    ) -> tuple[List[sqlite3.Row], str]:
        if not self._fts5_available or not eligible_rows:
            return list(eligible_rows), "deterministic_scan"
        terms = extract_content_terms(query)
        if not terms:
            return [], "fts5_bm25"
        # SQLite's default FTS tokenizer does not segment CJK compounds. For a
        # compact named-procedure query, a deterministic local scan is both
        # bounded and safer: _score_candidate's CJK n-grams then evaluate every
        # eligible chunk instead of silently dropping an exact Japanese match.
        if _CJK_RE.search(query):
            return list(eligible_rows), "deterministic_scan"
        match_query = " OR ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)
        try:
            self._conn.execute(
                "CREATE TEMP TABLE IF NOT EXISTS rag_v2_eligible_chunks (chunk_id TEXT PRIMARY KEY)"
            )
            self._conn.execute("DELETE FROM rag_v2_eligible_chunks")
            self._conn.executemany(
                "INSERT INTO rag_v2_eligible_chunks(chunk_id) VALUES (?)",
                ((row["chunk_id"],) for row in eligible_rows),
            )
            ranked_ids = self._conn.execute(
                """
                SELECT f.chunk_id
                FROM chunks_fts AS f
                JOIN rag_v2_eligible_chunks AS eligible ON eligible.chunk_id = f.chunk_id
                WHERE chunks_fts MATCH ?
                ORDER BY bm25(chunks_fts, 0.0, 1.0, 2.0, 1.0, 0.75), f.chunk_id
                LIMIT ?
                """,
                (match_query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            self._fts5_available = False
            return list(eligible_rows), "deterministic_scan"
        by_id = {str(row["chunk_id"]): row for row in eligible_rows}
        return [by_id[str(row["chunk_id"])] for row in ranked_ids if str(row["chunk_id"]) in by_id], "fts5_bm25"

    @staticmethod
    def _evidence_set_term_coverage(
        candidates: List[Dict[str, Any]],
        query_plan: RetrievalQueryPlan,
    ) -> float:
        coverages = []
        for variant in query_plan.variants:
            terms = set(extract_content_terms(variant.text))
            if not terms:
                continue
            matched = set()
            for candidate in candidates:
                matched.update(candidate["variant_term_matches"].get(variant.text, ()))
            coverages.append(len(matched & terms) / len(terms))
        return max(coverages, default=0.0)

    def close(self) -> None:
        self._conn.close()

    def _chunk_row(self, chunk: DocumentChunk) -> tuple[Any, ...]:
        metadata = chunk.to_dict()
        return (
            chunk.chunk_id,
            chunk.document_id,
            chunk.source_path,
            chunk.source_name,
            chunk.file_type,
            chunk.text,
            chunk.normalized_text,
            json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            json.dumps(list(chunk.privacy_labels), ensure_ascii=False),
            chunk.source_fingerprint,
            chunk.checksum,
            int(chunk.retrievable),
        )

    @staticmethod
    def _is_selected(row: sqlite3.Row, options: SearchOptions) -> bool:
        # A document ID is the canonical selection key. Absolute paths can change
        # when a sealed index is moved or a workspace is cloned; the independent
        # fingerprint validation still rejects altered source content.
        if options.allowed_document_ids is not None:
            return row["document_id"] in options.allowed_document_ids
        if options.allowed_source_paths is not None:
            return row["source_path"] in options.allowed_source_paths
        return True

    @staticmethod
    def _privacy_is_allowed(privacy_labels: tuple[str, ...], options: SearchOptions) -> bool:
        if options.allowed_privacy_labels is None:
            return True
        allowed = set(options.allowed_privacy_labels)
        return bool(privacy_labels) and all(label in allowed for label in privacy_labels)

    @staticmethod
    def _is_stale(row: sqlite3.Row, options: SearchOptions) -> bool:
        expected = options.expected_source_fingerprints
        if row["document_id"] in expected:
            return row["source_fingerprint"] != expected[row["document_id"]]
        if row["source_path"] in expected:
            return row["source_fingerprint"] != expected[row["source_path"]]
        return False

    @staticmethod
    def _insufficiency_reasons(
        *,
        indexed_count: int,
        eligible_count: int,
        candidate_count: int,
        result_count: int,
        filtered_by_source: int,
        filtered_by_privacy: int,
        filtered_as_stale: int,
        best_coverage: float,
        term_count: int,
    ) -> tuple[str, ...]:
        reasons = []
        if indexed_count == 0:
            reasons.append("no_indexed_chunks")
        if eligible_count == 0 and filtered_by_source:
            reasons.append("source_filter_excluded_all_chunks")
        if eligible_count == 0 and filtered_by_privacy:
            reasons.append("privacy_filter_excluded_all_chunks")
        if eligible_count == 0 and filtered_as_stale:
            reasons.append("stale_fingerprint_excluded_all_chunks")
        if eligible_count > 0 and candidate_count == 0:
            reasons.append("no_lexical_or_metadata_match")
        if result_count > 0 and term_count > 1 and best_coverage < 1.0:
            reasons.append("incomplete_query_term_coverage")
        if result_count > 0 and term_count > 1 and best_coverage < 0.5:
            reasons.append("weak_query_term_coverage")
        return tuple(reasons)

    @staticmethod
    def _empty_response(query: str, indexed_chunk_count: int, reason: str) -> SearchResponse:
        return SearchResponse(
            results=(),
            summary=SearchSummary(
                query=query,
                indexed_chunk_count=indexed_chunk_count,
                eligible_chunk_count=0,
                candidate_count=0,
                returned_count=0,
                insufficiency_reasons=(reason,),
            ),
        )

    @staticmethod
    def _score_candidate(
        row: sqlite3.Row,
        terms: tuple[str, ...],
        query_plan: Optional[RetrievalQueryPlan] = None,
    ) -> Optional[tuple[float, sqlite3.Row, Dict[str, Any], tuple[str, ...], Dict[str, float], tuple[str, ...], float]]:
        metadata = json.loads(row["metadata_json"])
        privacy_labels = tuple(json.loads(row["privacy_labels_json"] or "[]"))
        text = row["normalized_text"]
        source_name = row["source_name"]
        source_path = row["source_path"]
        section_text = " ".join(_text_values(metadata.get("section_path")))
        sheet_text = " ".join(_text_values(metadata.get("sheet_names")))
        element_types = tuple(value.lower() for value in _text_values(metadata.get("element_types")))

        all_tokens = _tokens(text)
        text_counts = Counter(all_tokens)
        title_tokens = set(_tokens(source_name))
        path_tokens = set(_tokens(source_path))
        section_tokens = set(_tokens(section_text))
        sheet_tokens = set(_tokens(sheet_text))
        searchable_tokens = set(text_counts) | title_tokens | path_tokens | section_tokens | sheet_tokens
        normalized_text = text.lower()
        matched_terms = tuple(
            term
            for term in terms
            if term in searchable_tokens
            or (_CJK_RE.search(term) is not None and term in normalized_text)
        )
        if not matched_terms:
            return None

        phrase = " ".join(terms)
        signals: Dict[str, float] = {}
        original_target_terms = set(
            query_plan.target_terms
            if query_plan and query_plan.target_terms
            else extract_content_terms(query_plan.original_query if query_plan else "")
        )
        target_matches = tuple(term for term in matched_terms if term in original_target_terms)
        raw_lexical_count = float(sum(
            text_counts[term]
            if term in text_counts
            else normalized_text.count(term)
            if _CJK_RE.search(term) is not None
            else 0
            for term in terms
        ))
        lexical_count = min(5.0, raw_lexical_count)
        if lexical_count:
            signals["lexical_term_count"] = lexical_count
        if raw_lexical_count > lexical_count:
            signals["lexical_frequency_capped"] = raw_lexical_count - lexical_count

        source_token_matches = sum(term in title_tokens or term in path_tokens for term in terms)
        if source_token_matches:
            signals["source_metadata_match"] = float(source_token_matches) * 2.0

        structure_token_matches = sum(term in section_tokens or term in sheet_tokens for term in terms)
        if structure_token_matches:
            signals["structure_metadata_match"] = float(structure_token_matches)

        if len(terms) > 1 and _contains_phrase(text, phrase):
            signals["exact_text_phrase"] = 4.0
        if len(terms) > 1 and (_contains_phrase(source_name, phrase) or _contains_phrase(source_path, phrase)):
            signals["exact_source_phrase"] = 3.0
        if len(terms) > 1 and (_contains_phrase(section_text, phrase) or _contains_phrase(sheet_text, phrase)):
            signals["exact_structure_phrase"] = 1.5
        if "table" in element_types and lexical_count:
            signals["table_structure_match"] = min(1.0, lexical_count) * 0.5

        confidence = _numeric_metadata(metadata, "confidence")
        if confidence is not None:
            signals["confidence_metadata"] = confidence * 0.25
        freshness = _numeric_metadata(metadata, "freshness_score")
        if freshness is not None:
            signals["freshness_metadata"] = freshness * 0.25
        if _metadata_flag(metadata, "metadata_only") or _metadata_flag(metadata, "content_unavailable"):
            signals["metadata_only_penalty"] = -3.0

        # Domain-neutral intent & obligation scoring
        intent = query_plan.intent_category if query_plan else "general"
        action_words = {"check", "verify", "action", "handle", "handling", "step", "steps", "fix", "resolution", "solution", "xử", "khắc", "bước", "kiểm", "quản", "thực"}
        problem_words = {"error", "errors", "fault", "faults", "failure", "failures", "exception", "symptom", "issue", "lỗi", "sự", "hỏng", "thất"}

        has_problem = bool(set(text_counts) & problem_words) or any(w in section_text.lower() for w in problem_words)
        has_action = bool(set(text_counts) & action_words) or any(w in section_text.lower() for w in action_words)

        is_repetitive_dump = False
        if len(all_tokens) > 30 and text_counts:
            top_freq = max(text_counts.values())
            is_repetitive_dump = (top_freq / len(all_tokens)) > 0.25

        if intent == "diagnosis":
            if has_problem and has_action and not is_repetitive_dump:
                signals["actionable_diagnosis_match"] = 3.5
            elif has_problem and not has_action:
                signals["unactionable_problem_penalty"] = -0.25

        if intent in ("procedure", "actionable_output"):
            if has_action or "procedure" in section_text.lower() or "quy trình" in section_text.lower():
                signals["procedural_structure_boost"] = 2.0

        if intent in ("lookup", "table"):
            if "table" in element_types or sheet_text:
                signals["lookup_table_boost"] = 1.5

        # Check for repetitive / process log dumps
        if is_repetitive_dump and not has_action:
            signals["repetitive_dump_penalty"] = -4.0
        elif is_repetitive_dump:
            signals["repetitive_dump_penalty"] = -2.0

        if target_matches:
            signals["target_term_match_count"] = float(len(target_matches))
            signals["original_target_term_match_count"] = float(len(target_matches))
        score = float(
            sum(
                value
                for name, value in signals.items()
                if name not in {
                    "target_term_match_count",
                    "original_target_term_match_count",
                    "equivalent_target_term_match_count",
                }
            )
        )
        if is_repetitive_dump:
            score = min(score, 1.0)
        if score <= 0:
            return None
        coverage = len(matched_terms) / len(terms)
        return score, row, metadata, privacy_labels, signals, matched_terms, coverage

    def __enter__(self) -> "LocalChunkIndex":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
