"""Local SQLite index and generic local retrieval for RAG v2 chunks."""
from __future__ import annotations

from array import array
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import struct
import threading
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .chunking import DocumentChunk
from .query_planning import (
    RetrievalQueryPlan,
    coerce_query_plan,
    detect_retrieval_mode,
    extract_content_terms,
    match_text_obligations,
)
from .script_family import (
    MISMATCH_CHANNEL_WEIGHTS,
    plan_has_cjk_variants,
    should_retry_thin_results,
    uses_script_mismatch_ranking,
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
_EXACT_IDENTIFIER_RE = re.compile(
    r"(?<!\w)[A-Za-z][A-Za-z0-9]*(?:[_-][A-Za-z0-9]+)+(?!\w)"
)
_SPECIAL_ENTITY_RES = (
    re.compile(r"(?<![A-Za-z0-9])C\d{2,5}(?![A-Za-z0-9])", re.IGNORECASE),
    re.compile(r"(?<!\w)[0-9][A-Z0-9]{5,}(?!\w)", re.IGNORECASE),
    re.compile(r"\b(?:Sirius(?:\s*2)?|OKNGUNIT|Camera(?:\s*140)?|MOUNT(?:\s*LD)?\s*BLOCK|NanoScan|Bow_Skew)\b", re.IGNORECASE),
    re.compile(r"\b(?:SIM(?:\s*tape)?|LSU(?:\s*Line)?|COVER\s*GLASS)\b", re.IGNORECASE),
    re.compile(r"\b(?:g1|g2|OHP)\b", re.IGNORECASE),
    re.compile(r"\b(?:1035|1004)\b"),
    re.compile(r"(?<!\w)[A-Za-z][A-Za-z0-9]*(?:[_-][A-Za-z0-9]+)+(?!\w)"),
)
MAX_ENTITY_BOOST = 0.060
_EXACT_IDENTIFIER_QUOTA = 16


def _extract_query_entities(query: str) -> tuple[str, ...]:
    text = query or ""
    entities = []
    seen = set()
    for pattern in _SPECIAL_ENTITY_RES:
        for match in pattern.finditer(text):
            val = match.group(0).strip()
            key = val.lower()
            if key not in seen and len(val) >= 2:
                seen.add(key)
                entities.append(val)
    return tuple(entities)


def _compute_entity_boost(
    entities: Sequence[str],
    source_name: str,
    source_path: str,
    text: str,
) -> float:
    if not entities:
        return 0.0
    boost = 0.0
    source_name_lower = (source_name or "").lower()
    source_path_lower = (source_path or "").lower()
    prefix_text_lower = (text or "")[:500].lower()
    text_lower = (text or "").lower()
    for entity in entities:
        ent_lower = entity.lower()
        ent_stem = ent_lower.replace(" tape", "").replace(" line", "").strip()
        if ent_lower in source_name_lower or ent_lower in source_path_lower or (len(ent_stem) >= 3 and ent_stem in source_name_lower):
            boost += 0.015
        elif ent_lower in prefix_text_lower or (len(ent_stem) >= 3 and ent_stem in prefix_text_lower):
            boost += 0.008
        elif re.search(rf"(?<!\w){re.escape(ent_lower)}(?!\w)", text_lower):
            boost += 0.018
    return min(boost, MAX_ENTITY_BOOST)


def _query_carries_exact_values(query: str) -> bool:
    """Return True when the query contains an identifier/code/number token.

    Such queries ask for a concrete value, so document summaries must not be
    prepended ahead of the body chunks that hold the literal answer.
    """
    text = query or ""
    if _extract_query_entities(text):
        return True
    return bool(re.search(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)", text))


def _identifier_patterns(query: str) -> tuple[re.Pattern[str], ...]:
    entities = _extract_query_entities(query or "")
    if entities:
        return tuple(
            re.compile(rf"(?<!\w){re.escape(ent)}(?!\w)", re.IGNORECASE)
            for ent in entities
        )
    return tuple(
        re.compile(rf"(?<!\w){re.escape(match.group(0))}(?!\w)", re.IGNORECASE)
        for match in _EXACT_IDENTIFIER_RE.finditer(query or "")
    )


def _identifier_match_priority(
    text: str,
    patterns: Sequence[re.Pattern[str]],
) -> tuple[int, int]:
    matches = tuple(pattern.search(text or "") is not None for pattern in patterns)
    if not matches:
        return 0, 0
    return sum(matches), int(matches[-1])


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


LOGGER = logging.getLogger(__name__)
NUMPY_DENSE_FLAG = "AIOS_RAG_V2_NUMPY_DENSE"
NUMPY_DENSE_MAX_BYTES_FLAG = "AIOS_RAG_V2_NUMPY_DENSE_MAX_BYTES"
DEFAULT_NUMPY_DENSE_MAX_BYTES = 2 * 1024 * 1024 * 1024
CJK_PREFILTER_FLAG = "AIOS_RAG_V2_CJK_PREFILTER"


def cjk_prefilter_enabled() -> bool:
    """Return whether the V1-A2 CJK LIKE prefilter is enabled.

    Kill-switch for OPT-RAGV2-PYLOOPS V1-A2: set to "0" to fall back to the
    full deterministic scan if the prefilter's top-15 ever diverges from the
    baseline on production (the prefilter drops chunks that match only
    shorter variant terms, so divergence is possible by design).
    """
    return os.environ.get(CJK_PREFILTER_FLAG, "1") != "0"


# --- OPT-RAGV2-LEXICAL Phase B2: optional lexical hot-path optimizations ---
# Master kill-switch: AIOS_RAGV2_LEXICAL_V2=1 enables the V2 code paths.
# Each optimization below has its own sub-toggle so OMP can A/B them
# independently on PC0575. V2=0 (default) keeps the pre-B2 code path intact.
_LEX_V2_MASTER_ENV = "AIOS_RAGV2_LEXICAL_V2"


def _lexical_v2_flags() -> Optional[Dict[str, bool]]:
    """Read Phase-B2 toggles once per search.

    Returns None when the master switch is off; otherwise a dict of
    sub-toggle name -> enabled.
    """
    if os.environ.get(_LEX_V2_MASTER_ENV, "1") != "1":
        return None

    def _opt(name: str, default: str = "1") -> bool:
        return os.environ.get(f"AIOS_RAGV2_LEX_V2_{name}", default) == "1"

    return {
        # (a) explicit single transaction around the temp-table build.
        "TEMP_TXN": _opt("TEMP_TXN"),
        # (b) skip the temp table + JOIN when eligibility covers every
        # retrievable chunk; MATCH directly with JOIN chunks(retrievable=1).
        "SKIP_FULL_ELIGIBLE": _opt("SKIP_FULL_ELIGIBLE"),
        # Narrow eligibility SELECT (filter columns only); full rows are
        # fetched lazily for candidates only.
        "NARROW_ELIGIBILITY": _opt("NARROW_ELIGIBILITY"),
        # Skip the per-row privacy_labels_json parse when no privacy filter
        # is configured (_privacy_is_allowed returns True unconditionally).
        "PRIVACY_LAZY": _opt("PRIVACY_LAZY"),
        # (c) hoist per-search invariants out of _score_candidate.
        "SCORE_HOIST": _opt("SCORE_HOIST"),
        # (c) cache term-independent per-row work across query variants.
        "SCORE_CACHE": _opt("SCORE_CACHE"),
        # CJK: trigram-FTS prefilter instead of LIKE; needs a
        # chunks_fts_trigram table built by OMP (index write lane).
        # Default 0: falls back to the LIKE prefilter when the table is
        # missing, so enabling it early is harmless but useless.
        "CJK_TRIGRAM": _opt("CJK_TRIGRAM", "0"),
        # (d) Selective FTS terms: prune high-frequency Vietnamese stopwords from FTS match query
        "SELECTIVE_TERMS": _opt("SELECTIVE_TERMS"),
    }


# Intent word sets hoisted out of _score_candidate (B2 SCORE_HOIST).
# Same elements as the per-call literals they replace.
_LEX_ACTION_WORDS = frozenset(
    {
        "check", "verify", "action", "handle", "handling", "step", "steps",
        "fix", "resolution", "solution", "xử", "khắc", "bước", "kiểm",
        "quản", "thực",
    }
)
_LEX_PROBLEM_WORDS = frozenset(
    {
        "error", "errors", "fault", "faults", "failure", "failures",
        "exception", "symptom", "issue", "lỗi", "sự", "hỏng", "thất",
    }
)
_VIETNAMESE_COMMON_STOPWORDS = frozenset(
    {
        "và", "của", "có", "là", "được", "trong", "cho", "về", "với", "các", "những", "này",
        "khi", "để", "từ", "ở", "sau", "trước", "như", "thế", "nào", "gì", "ai", "đâu",
        "bao", "nhiêu", "ngày", "điểm", "đáng", "chú", "ý",
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    }
)


def _identifier_literals(query: str) -> tuple[str, ...]:
    """Extract literal entity strings for fast FTS identifier candidate lookup."""
    entities = _extract_query_entities(query or "")
    if entities:
        return tuple(dict.fromkeys(ent.strip() for ent in entities if ent.strip()))
    return tuple(
        dict.fromkeys(
            m.group(0).strip()
            for m in _EXACT_IDENTIFIER_RE.finditer(query or "")
            if m.group(0).strip()
        )
    )

# Float32 matmul on this machine disagreed with the Python cosine by at most
# ~1e-7 on real 1024-d vectors. The band keeps a near-cutoff chunk in the
# exact-rescore pool so published top-k order stays identical.
_NUMPY_SCORE_TIE_BAND = 1e-5


def _is_numpy_available() -> bool:
    """Kiểm tra thư viện numpy có cài đặt và import được không."""
    try:
        import numpy  # noqa: F401

        return True
    except ImportError:
        return False


def numpy_dense_search_enabled() -> bool:
    """Return whether the in-process numpy dense scan is enabled.

    Đường numpy là mặc định khi numpy khả dụng trong môi trường.
    Biến môi trường AIOS_RAG_V2_NUMPY_DENSE cho phép tắt về đường Python cũ
    khi đặt giá trị 0, false, no, off (hỗ trợ rollback 1 dòng).
    Khi numpy không khả dụng: tự rơi về đường Python và ghi log tiếng Việt rõ ràng, không sập.
    """
    raw = os.environ.get(NUMPY_DENSE_FLAG, "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if not _is_numpy_available():
        LOGGER.warning(
            "Thư viện numpy không khả dụng trong môi trường; tự động chuyển sang đường quét dense tuần tự Python."
        )
        return False
    return True


def numpy_dense_max_bytes() -> int:
    """Return the float32 matrix budget. Over budget falls back to the Python scan."""
    raw = os.environ.get(NUMPY_DENSE_MAX_BYTES_FLAG, "").strip()
    if not raw:
        return DEFAULT_NUMPY_DENSE_MAX_BYTES
    try:
        return max(0, int(raw))
    except ValueError:
        LOGGER.warning("Ignoring invalid %s=%r", NUMPY_DENSE_MAX_BYTES_FLAG, raw)
        return DEFAULT_NUMPY_DENSE_MAX_BYTES


SPARSE_CACHE_MAX_BYTES_FLAG = "AIOS_RAG_V2_SPARSE_MAX_BYTES"
DEFAULT_SPARSE_CACHE_MAX_BYTES = 1_500_000_000


def sparse_cache_max_bytes() -> int:
    """Return the sparse inverted-index budget. Over budget keeps the Python scan."""
    raw = os.environ.get(SPARSE_CACHE_MAX_BYTES_FLAG, "").strip()
    if not raw:
        return DEFAULT_SPARSE_CACHE_MAX_BYTES
    try:
        return max(0, int(raw))
    except ValueError:
        LOGGER.warning("Ignoring invalid %s=%r", SPARSE_CACHE_MAX_BYTES_FLAG, raw)
        return DEFAULT_SPARSE_CACHE_MAX_BYTES


@dataclass(frozen=True)
class _DenseMatrixCache:
    token: tuple[int, int]
    fingerprint: str
    dimension: int
    matrix: Any
    chunk_ids: tuple[str, ...]
    document_ids: tuple[str, ...]
    source_paths: tuple[str, ...]
    source_fingerprints: tuple[str | None, ...]
    privacy_labels: tuple[tuple[str, ...], ...]


_PROCESS_DENSE_MATRIX_LOCK = threading.Lock()
_PROCESS_DENSE_MATRIX_CACHE: dict[tuple[str, str, int], _DenseMatrixCache] = {}


def clear_process_dense_matrix_cache() -> None:
    """Xóa bộ nhớ đệm ma trận dense cấp tiến trình (hỗ trợ kiểm thử và giải phóng RAM)."""
    with _PROCESS_DENSE_MATRIX_LOCK:
        _PROCESS_DENSE_MATRIX_CACHE.clear()



@dataclass(frozen=True)
class _SparseVectorCache:
    """Parsed sparse vectors as an inverted index (OPT-RAGV2-PYLOOPS V3-A).

    ``postings`` maps each term to ``(doc_positions, weights)``: parallel
    ``array("I")`` / ``array("d")`` posting lists. Scoring a query variant only
    touches documents sharing at least one query term; a document with no
    shared term has an exact dot of 0 and is filtered out either way, so the
    ranked output is identical to the full Python scan. Weights stay float64
    so dots match the legacy path bit-for-bit in the common case.
    """

    token: tuple[int, int]
    fingerprint: str
    chunk_ids: tuple[str, ...]
    document_ids: tuple[str, ...]
    source_paths: tuple[str, ...]
    source_fingerprints: tuple[str | None, ...]
    privacy_labels: tuple[tuple[str, ...], ...]
    postings: dict[str, tuple[array, array]]


def _numpy_candidate_pool(scores: Any, candidate_limit: int) -> Any:
    """Return local indices that can affect the exact top-k, including score ties."""
    import numpy as np

    count = int(scores.shape[0])
    if count == 0 or candidate_limit <= 0:
        return np.empty(0, dtype=np.int64)
    limit = min(int(candidate_limit), count)
    if limit == count:
        return np.arange(count, dtype=np.int64)
    partitioned = np.argpartition(scores, -limit)[-limit:]
    cutoff = float(scores[partitioned].min())
    return np.flatnonzero(scores >= cutoff - _NUMPY_SCORE_TIE_BAND)

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
    # OPT-RAGV2-LEXICAL Phase B1: per-part lexical timings as
    # ((part_name, milliseconds), ...). Wall-clock metadata only; excluded from
    # determinism comparisons in tests. Empty when the lexical channel is idle.
    lexical_breakdown_ms: Tuple[Tuple[str, float], ...] = ()
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
    # ``hybrid_search_with_summary`` uses a multi-variant RRF signal whose
    # key predates the generic channel-fusion name.  It remains a valid
    # deterministic tie-breaker after the cross-encoder has scored the pair.
    def fused_tiebreak(result: SearchResult) -> float:
        value = result.ranking_signals.get(
            "fused_rrf",
            result.ranking_signals.get("multi_variant_rrf", result.score),
        )
        return float(value) if math.isfinite(float(value)) else float(result.score)
    rescored.sort(key=lambda result: (
        -result.ranking_signals["reranker_score"],
        -fused_tiebreak(result),
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
            if document_counts[document_key] >= per_document_limit:
                LOGGER.info(
                    "rag_v2.diversity_cap_triggered document_id=%s source=%s limit=%d chunk_id=%s",
                    result.document_id,
                    result.source_name,
                    per_document_limit,
                    result.chunk_id,
                )
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
        if plan_has_cjk_variants(plan) or uses_script_mismatch_ranking(
            plan.original_query,
            tuple((item.source_name or "") + " " + (item.text or "")[:200] for item in ranked),
        ):
            # Latin query terms must not veto CJK procedure manuals.
            return True
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

    query_text = plan.original_query if hasattr(plan, "original_query") else str(query)
    entities = _extract_query_entities(query_text)
    fused = []
    for record in records.values():
        result = record["result"]
        entity_boost = _compute_entity_boost(
            entities,
            result.source_name,
            result.source_path,
            result.text,
        )
        signals = dict(result.ranking_signals)
        signals.update({
            "lexical_channel_rank": float(record["lexical_rank"]),
            "dense_channel_rank": float(record["dense_rank"]),
            "sparse_channel_rank": float(record["sparse_rank"]),
            "fused_rrf": float(record["rrf"]),
            "entity_match_boost": float(entity_boost),
            "boosted_rrf": float(record["rrf"] + entity_boost),
        })
        fused.append(replace(result, ranking_signals=signals))
    fused.sort(key=lambda result: (
        -result.ranking_signals["boosted_rrf"],
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
        try:
            self._conn.execute("PRAGMA cache_size = -262144")
            self._conn.execute("PRAGMA mmap_size = 2147483648")
        except sqlite3.Error:
            pass
        self._conn.row_factory = sqlite3.Row
        self._fts5_requested = enable_fts5
        self._embedding_backend = embedding_backend
        self._sparse_backend = sparse_backend or (
            embedding_backend if isinstance(embedding_backend, SparseEmbeddingBackend) else None
        )
        # ``MultiVectorEmbeddingBackend`` is a runtime-checkable protocol.
        # ``isinstance`` probes every protocol attribute, including the BGE
        # descriptor property.  For a normal dense+sparse BGE-M3 profile that
        # property correctly rejects access because ColBERT vectors are off,
        # but the protocol probe used to turn that optional capability into a
        # pipeline-startup failure.  Resolve it from the cheap capability flag
        # instead; callers that actually request multivector retrieval still
        # fail explicitly if it is unavailable.
        selected_multivector = multivector_backend or embedding_backend
        multivector_capability = (
            getattr(selected_multivector, "multivector_capability", None)
            if selected_multivector is not None
            else None
        )
        if (
            multivector_capability is not None
            and bool(getattr(multivector_capability, "available", False))
            and callable(getattr(selected_multivector, "multivector_documents", None))
            and callable(getattr(selected_multivector, "multivector_query", None))
        ):
            self._multivector_backend = selected_multivector
        else:
            self._multivector_backend = None
        self._dense_matrix_cache: _DenseMatrixCache | None = None
        self._dense_matrix_lock = threading.Lock()
        self._sparse_vector_cache: _SparseVectorCache | None = None
        self._sparse_vector_lock = threading.Lock()
        # OPT-RAGV2-LEXICAL Phase A: so thu tu cac lan ghi bang main (chunks /
        # chunk_*_embeddings) thuc hien qua instance nay. PRAGMA data_version ma
        # connection tu doc KHONG BAO GIO doi sau write cua chinh no (da kiem
        # chung tren SQLite 3.45.1: chi doi khi connection KHAC commit) -> can
        # bo dem rieng de write cung-connection van invalidate cache.
        # Ghi bang TEMP (vd rag_v2_eligible_chunks cua nhanh lexical FTS) khong
        # cham vao bo dem nay.
        self._main_write_seq = 0
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
        # Knowledge-domain label (lsu / dieu_tra_loi / mom). Nullable so legacy
        # rows stay valid; populated by _upsert_rows via index_domain.
        if "domain" not in chunk_columns:
            self._conn.execute("ALTER TABLE chunks ADD COLUMN domain TEXT")
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
        self._note_main_db_write()
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
        self._note_main_db_write()
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
                self._note_main_db_write()
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
        self._note_main_db_write()
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
        if retrievable_count:
            self._note_main_db_write()
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
        # Label each chunk with its knowledge domain at ingest time. The label
        # comes from index_domain.classify_document (source_name/source_path +
        # chunk text sample); re-ingests recompute it, legacy rows keep NULL.
        from aios_habit.index_domain import classify_document

        labeled: list[tuple[Any, ...]] = []
        for row in rows:
            (
                chunk_id,
                document_id,
                source_path,
                source_name,
                file_type,
                text,
                normalized_text,
                metadata_json,
                privacy_labels_json,
                source_fingerprint,
                checksum,
                retrievable,
            ) = row[:12]
            domain = classify_document(
                str(source_name or ""), str(source_path or ""), str(text or "")[:2000]
            ).domain
            labeled.append(
                (
                    chunk_id,
                    document_id,
                    source_path,
                    source_name,
                    file_type,
                    text,
                    normalized_text,
                    metadata_json,
                    privacy_labels_json,
                    source_fingerprint,
                    checksum,
                    retrievable,
                    domain,
                )
            )
        self._conn.executemany(
            """
            INSERT INTO chunks (
                chunk_id, document_id, source_path, source_name, file_type,
                text, normalized_text, metadata_json, privacy_labels_json,
                source_fingerprint, checksum, retrievable, domain
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                retrievable=excluded.retrievable,
                domain=excluded.domain
            """,
            labeled,
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
            written = self._ensure_embeddings()
        if written:
            self._note_main_db_write()
        return written

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

    def get_document_fingerprint(self, document_id: str) -> Optional[str]:
        """Return the stored source fingerprint for an indexed document, if available."""
        if not document_id:
            return None
        row = self._conn.execute(
            "SELECT source_fingerprint FROM chunks WHERE document_id = ? AND retrievable = 1 AND source_fingerprint IS NOT NULL LIMIT 1",
            (str(document_id).strip(),),
        ).fetchone()
        return str(row[0]).strip() if row and row[0] else None

    def verify_selected_document_coverage(
        self,
        document_ids: Sequence[str],
        *,
        expected_document_fingerprints: Mapping[str, str] | None = None,
        sparse_required: bool = False,
        multivector_required: bool = False,
    ) -> Dict[str, Any]:
        """Verify semantic coverage for exactly the documents a query may use.

        A Workspace query is deliberately read-only: it must never create
        embeddings as a side effect.  Checking the entire shared runtime would
        be too broad because that runtime can hold unrelated, independently
        prepared owner sources.  This method therefore validates only the
        caller-authorized document set and never exposes document text or
        vector values in its report.
        """
        selected = tuple(dict.fromkeys(
            str(document_id).strip()
            for document_id in document_ids
            if str(document_id).strip()
        ))
        expected = (
            {str(key): str(value) for key, value in expected_document_fingerprints.items()}
            if expected_document_fingerprints is not None
            else {}
        )
        if not selected:
            return {
                "valid": False,
                "reason": "no_selected_documents",
                "document_count": 0,
                "retrievable_chunk_count": 0,
                "dense_embedding_count": 0,
                "sparse_embedding_count": 0,
                "multivector_embedding_count": 0,
                "dense_complete": False,
                "sparse_complete": not sparse_required,
                "multivector_complete": not multivector_required,
                "documents_complete": False,
            }

        placeholders = ",".join("?" for _ in selected)
        rows = self._conn.execute(
            f"""
            SELECT document_id,
                   MIN(source_fingerprint) AS min_fingerprint,
                   MAX(source_fingerprint) AS max_fingerprint,
                   COUNT(*) AS chunk_count
            FROM chunks
            WHERE retrievable = 1 AND document_id IN ({placeholders})
            GROUP BY document_id
            """,
            selected,
        ).fetchall()
        actual_fingerprints = {
            str(row["document_id"]): (
                str(row["min_fingerprint"])
                if row["min_fingerprint"] is not None
                and row["min_fingerprint"] == row["max_fingerprint"]
                else ""
            )
            for row in rows
        }
        missing_document_ids = tuple(sorted(set(selected) - set(actual_fingerprints)))
        fingerprint_mismatch_document_ids = tuple(sorted(
            document_id
            for document_id, fingerprint in expected.items()
            if document_id in set(selected)
            and fingerprint != ""
            and actual_fingerprints.get(document_id) != fingerprint
        ))
        documents_complete = not missing_document_ids and not fingerprint_mismatch_document_ids
        retrievable_chunk_count = sum(int(row["chunk_count"]) for row in rows)

        backend = self._embedding_backend
        if backend is None:
            return {
                "valid": False,
                "reason": "embedding_backend_not_configured",
                "document_count": len(actual_fingerprints),
                "retrievable_chunk_count": retrievable_chunk_count,
                "missing_document_ids": missing_document_ids,
                "fingerprint_mismatch_document_ids": fingerprint_mismatch_document_ids,
                "documents_complete": documents_complete,
                "dense_embedding_count": 0,
                "sparse_embedding_count": 0,
                "multivector_embedding_count": 0,
                "dense_complete": False,
                "sparse_complete": not sparse_required,
                "multivector_complete": not multivector_required,
            }

        descriptor = backend.descriptor
        dense_rows = self._conn.execute(
            f"""
            SELECT c.text, e.content_hash
            FROM chunks AS c
            JOIN chunk_embeddings AS e ON e.chunk_id = c.chunk_id
            WHERE c.retrievable = 1
              AND c.document_id IN ({placeholders})
              AND e.model_fingerprint = ?
            """,
            (*selected, descriptor.fingerprint),
        ).fetchall()
        dense_embedding_count = sum(
            str(row["content_hash"]) == _embedding_content_hash(str(row["text"]))
            for row in dense_rows
        )
        sparse_embedding_count = 0
        if sparse_required:
            sparse_rows = self._conn.execute(
                f"""
                SELECT c.text, s.content_hash
                FROM chunks AS c
                JOIN chunk_sparse_embeddings AS s ON s.chunk_id = c.chunk_id
                WHERE c.retrievable = 1
                  AND c.document_id IN ({placeholders})
                  AND s.model_fingerprint = ?
                """,
                (*selected, descriptor.fingerprint),
            ).fetchall()
            sparse_embedding_count = sum(
                str(row["content_hash"]) == _embedding_content_hash(str(row["text"]))
                for row in sparse_rows
            )
        multivector_embedding_count = 0
        if multivector_required:
            multivector_backend = self._multivector_backend
            multivector_descriptor = (
                multivector_backend.multivector_descriptor
                if multivector_backend is not None
                and multivector_backend.multivector_capability.available
                else None
            )
            if multivector_descriptor is not None:
                multivector_rows = self._conn.execute(
                    f"""
                    SELECT c.text, m.content_hash, m.representation_fingerprint
                    FROM chunks AS c
                    JOIN chunk_multivector_embeddings AS m ON m.chunk_id = c.chunk_id
                    WHERE c.retrievable = 1
                      AND c.document_id IN ({placeholders})
                      AND m.model_fingerprint = ?
                    """,
                    (*selected, descriptor.fingerprint),
                ).fetchall()
                multivector_embedding_count = sum(
                    str(row["content_hash"]) == _embedding_content_hash(str(row["text"]))
                    and str(row["representation_fingerprint"])
                    == multivector_descriptor.fingerprint
                    for row in multivector_rows
                )

        dense_complete = dense_embedding_count == retrievable_chunk_count
        sparse_complete = not sparse_required or sparse_embedding_count == retrievable_chunk_count
        multivector_complete = (
            not multivector_required
            or multivector_embedding_count == retrievable_chunk_count
        )
        return {
            "valid": bool(
                documents_complete
                and retrievable_chunk_count > 0
                and dense_complete
                and sparse_complete
                and multivector_complete
            ),
            "reason": "" if documents_complete else "document_identity_mismatch",
            "document_count": len(actual_fingerprints),
            "retrievable_chunk_count": retrievable_chunk_count,
            "missing_document_ids": missing_document_ids,
            "fingerprint_mismatch_document_ids": fingerprint_mismatch_document_ids,
            "documents_complete": documents_complete,
            "model_fingerprint": descriptor.fingerprint,
            "dense_embedding_count": dense_embedding_count,
            "sparse_embedding_count": sparse_embedding_count,
            "multivector_embedding_count": multivector_embedding_count,
            "dense_complete": dense_complete,
            "sparse_complete": sparse_complete,
            "multivector_complete": multivector_complete,
        }

    def _note_main_db_write(self) -> None:
        """Ghi nhan 1 lan ghi bang main qua instance nay (OPT-RAGV2-LEXICAL Phase A).

        Chi goi sau khi transaction ghi that su commit. Ghi bang TEMP khong goi.
        """
        self._main_write_seq += 1

    def _index_cache_token(self) -> tuple[int, int]:
        # OPT-RAGV2-LEXICAL Phase A: token = (data_version, write_seq).
        # - data_version cua DB chinh: bat duoc write tu connection/process khac
        #   (mo hinh merge production: process rieng + restart app). Ghi bang
        #   TEMP khong lam data_version cua main nhay.
        # - write_seq: bat duoc write tren chinh connection nay, vi data_version
        #   ma connection tu doc khong doi sau write cua chinh no.
        # Bo `connection.total_changes`: no dem ca ghi bang TEMP giua query
        # (DELETE+INSERT ~120k dong vao rag_v2_eligible_chunks o nhanh lexical
        # FTS) lam cache dense/sparse am bi vo hieu va nap lai ma tran 100+s
        # vo ich ngay trong query do.
        # GIA DINH AN TOAN (da chot trong ve): worker khong bao gio ghi cac bang
        # embedding giua query; moi merge deu restart app nen cache duoc xay lai.
        row = self._conn.execute("PRAGMA data_version").fetchone()
        return (int(row[0]), self._main_write_seq)


    def _load_dense_matrix_cache(self, fingerprint: str, dimension: int) -> _DenseMatrixCache | None:
        """Load normalized float32 vectors once. None means use the Python scan."""
        try:
            import numpy as np
        except ImportError:
            LOGGER.warning(
                "Thư viện numpy không khả dụng trong môi trường; tự động chuyển sang đường quét dense tuần tự Python."
            )
            return None
        fetch_started = perf_counter()
        rows = self._conn.execute(
            """
            SELECT c.chunk_id, c.document_id, c.source_path, c.source_fingerprint,
                   c.privacy_labels_json, e.dimension AS embedding_dimension, e.vector_blob
            FROM chunks AS c
            JOIN chunk_embeddings AS e ON e.chunk_id = c.chunk_id
            WHERE c.retrievable = 1
              AND e.model_fingerprint = ? AND e.dtype = 'float32-le' AND e.normalized = 1
            """,
            (fingerprint,),
        ).fetchall()
        fetch_ms = (perf_counter() - fetch_started) * 1000.0
        kept = [row for row in rows if int(row["embedding_dimension"]) == dimension]
        count = len(kept)
        matrix_bytes = count * dimension * 4
        if matrix_bytes > numpy_dense_max_bytes():
            LOGGER.info(
                "rag_v2 numpy dense cache skipped: bytes=%s limit=%s chunks=%s",
                matrix_bytes,
                numpy_dense_max_bytes(),
                count,
            )
            return None
        build_started = perf_counter()
        matrix = np.empty((count, dimension), dtype=np.float32)
        chunk_ids: list[str] = []
        document_ids: list[str] = []
        source_paths: list[str] = []
        source_fingerprints: list[str | None] = []
        privacy_labels: list[tuple[str, ...]] = []
        expected_size = dimension * 4
        for index, row in enumerate(kept):
            payload = bytes(row["vector_blob"])
            if len(payload) != expected_size:
                raise SemanticBackendError(
                    f"embedding payload size mismatch: expected {expected_size}, received {len(payload)}"
                )
            matrix[index] = np.frombuffer(payload, dtype="<f4", count=dimension)
            chunk_ids.append(str(row["chunk_id"]))
            document_ids.append(str(row["document_id"]))
            source_paths.append(str(row["source_path"]))
            source_fingerprints.append(row["source_fingerprint"])
            privacy_labels.append(tuple(json.loads(row["privacy_labels_json"] or "[]")))
        LOGGER.info(
            "rag_v2 dense cache load timings: fetch_ms=%.1f build_ms=%.1f chunks=%s",
            fetch_ms,
            (perf_counter() - build_started) * 1000.0,
            count,
        )
        return _DenseMatrixCache(
            token=self._index_cache_token(),
            fingerprint=fingerprint,
            dimension=dimension,
            matrix=matrix,
            chunk_ids=tuple(chunk_ids),
            document_ids=tuple(document_ids),
            source_paths=tuple(source_paths),
            source_fingerprints=tuple(source_fingerprints),
            privacy_labels=tuple(privacy_labels),
        )

    def _dense_matrix_cache_for(self, fingerprint: str, dimension: int) -> _DenseMatrixCache | None:
        token = self._index_cache_token()
        cached = self._dense_matrix_cache
        if (
            cached is not None
            and cached.fingerprint == fingerprint
            and cached.dimension == dimension
            and cached.token == token
        ):
            return cached

        db_key = str(self.db_path.resolve()) if hasattr(self, "db_path") and self.db_path else ""
        cache_key = (db_key, fingerprint, dimension)

        with _PROCESS_DENSE_MATRIX_LOCK:
            proc_cached = _PROCESS_DENSE_MATRIX_CACHE.get(cache_key)
            if (
                proc_cached is not None
                and proc_cached.fingerprint == fingerprint
                and proc_cached.dimension == dimension
                and proc_cached.token == token
            ):
                self._dense_matrix_cache = proc_cached
                return proc_cached

            with self._dense_matrix_lock:
                cached = self._dense_matrix_cache
                token = self._index_cache_token()
                if (
                    cached is not None
                    and cached.fingerprint == fingerprint
                    and cached.dimension == dimension
                    and cached.token == token
                ):
                    return cached
                loaded = self._load_dense_matrix_cache(fingerprint, dimension)
                if loaded is not None:
                    self._dense_matrix_cache = loaded
                    _PROCESS_DENSE_MATRIX_CACHE[cache_key] = loaded
                return loaded

    def preload_dense_matrix_cache(self) -> tuple[int, float]:
        """Eagerly load the numpy dense matrix cache (OPT-RAGV2-PYLOOPS V2-A).

        Moves the first-load cost out of the first ("cold") query's timeout and
        into worker init. Returns ``(chunk_count, elapsed_ms)``; ``(0, 0.0)``
        when the numpy dense path is disabled or the cache cannot be built.
        A preload failure never raises: the lazy query-time load still applies,
        so retrieval semantics never change.
        """
        started = perf_counter()
        if not numpy_dense_search_enabled():
            return 0, 0.0
        backend = self._embedding_backend
        if backend is None:
            return 0, 0.0
        try:
            backend.capability.require()
        except Exception:
            LOGGER.warning("rag_v2 dense preload skipped: embedding backend unavailable")
            return 0, 0.0
        descriptor = backend.descriptor
        try:
            cache = self._dense_matrix_cache_for(descriptor.fingerprint, descriptor.dimension)
        except Exception:
            LOGGER.warning("rag_v2 dense preload failed", exc_info=True)
            return 0, 0.0
        elapsed_ms = (perf_counter() - started) * 1000.0
        count = len(cache.chunk_ids) if cache is not None else 0
        LOGGER.info(
            "rag_v2 dense matrix preloaded: chunks=%s elapsed_ms=%.1f",
            count,
            elapsed_ms,
        )
        return count, elapsed_ms

    def _load_sparse_vector_cache(self, fingerprint: str) -> _SparseVectorCache | None:
        """Parse every sparse vector once and build a term inverted index.

        None means keep the legacy per-query Python scan. Posting lists use
        compact ``array("I")`` / ``array("d")`` storage so ~108k documents stay
        within the ``AIOS_RAG_V2_SPARSE_MAX_BYTES`` budget.
        """
        fetch_started = perf_counter()
        rows = self._conn.execute(
            """
            SELECT c.chunk_id, c.document_id, c.source_path, c.source_fingerprint,
                   c.privacy_labels_json, s.sparse_json
            FROM chunks AS c
            JOIN chunk_sparse_embeddings AS s ON s.chunk_id = c.chunk_id
            WHERE c.retrievable = 1 AND s.model_fingerprint = ?
            """,
            (fingerprint,),
        ).fetchall()
        fetch_ms = (perf_counter() - fetch_started) * 1000.0
        posting_positions: dict[str, array] = {}
        posting_weights: dict[str, array] = {}
        chunk_ids: list[str] = []
        document_ids: list[str] = []
        source_paths: list[str] = []
        source_fingerprints: list[str | None] = []
        privacy_labels: list[tuple[str, ...]] = []
        for doc_index, row in enumerate(rows):
            vector = normalize_sparse_vector(json.loads(row["sparse_json"]))
            for term, weight in vector.items():
                positions = posting_positions.get(term)
                if positions is None:
                    positions = posting_positions[term] = array("I")
                    weights = posting_weights[term] = array("d")
                else:
                    weights = posting_weights[term]
                positions.append(doc_index)
                weights.append(weight)
            chunk_ids.append(str(row["chunk_id"]))
            document_ids.append(str(row["document_id"]))
            source_paths.append(str(row["source_path"]))
            source_fingerprints.append(row["source_fingerprint"])
            privacy_labels.append(tuple(json.loads(row["privacy_labels_json"] or "[]")))
        estimated_bytes = sum(
            len(positions) * positions.itemsize + len(weights) * weights.itemsize
            for positions, weights in zip(
                posting_positions.values(), posting_weights.values()
            )
        )
        # Per-term dict/array/tuple overhead allowance on top of raw postings.
        estimated_bytes += len(posting_positions) * 512
        if estimated_bytes > sparse_cache_max_bytes():
            LOGGER.info(
                "rag_v2 sparse cache skipped: bytes=%s limit=%s chunks=%s terms=%s",
                estimated_bytes,
                sparse_cache_max_bytes(),
                len(chunk_ids),
                len(posting_positions),
            )
            return None
        postings = {
            term: (posting_positions[term], posting_weights[term])
            for term in posting_positions
        }
        LOGGER.info(
            "rag_v2 sparse cache load timings: fetch_ms=%.1f build_ms=%.1f chunks=%s terms=%s",
            fetch_ms,
            (perf_counter() - fetch_started) * 1000.0 - fetch_ms,
            len(chunk_ids),
            len(posting_positions),
        )
        return _SparseVectorCache(
            token=self._index_cache_token(),
            fingerprint=fingerprint,
            chunk_ids=tuple(chunk_ids),
            document_ids=tuple(document_ids),
            source_paths=tuple(source_paths),
            source_fingerprints=tuple(source_fingerprints),
            privacy_labels=tuple(privacy_labels),
            postings=postings,
        )

    def _sparse_vector_cache_for(self, fingerprint: str) -> _SparseVectorCache | None:
        token = self._index_cache_token()
        cached = self._sparse_vector_cache
        if (
            cached is not None
            and cached.fingerprint == fingerprint
            and cached.token == token
        ):
            return cached
        with self._sparse_vector_lock:
            cached = self._sparse_vector_cache
            token = self._index_cache_token()
            if (
                cached is not None
                and cached.fingerprint == fingerprint
                and cached.token == token
            ):
                return cached
            loaded = self._load_sparse_vector_cache(fingerprint)
            if loaded is not None:
                self._sparse_vector_cache = loaded
            return loaded

    def preload_sparse_vector_cache(self) -> tuple[int, float]:
        """Eagerly build the sparse inverted-index cache (OPT-RAGV2-PYLOOPS V3-A).

        Returns ``(chunk_count, elapsed_ms)``; ``(0, 0.0)`` when sparse search
        is unavailable or the cache does not fit the budget. Never raises: the
        legacy per-query scan still applies, so retrieval semantics never
        change.
        """
        started = perf_counter()
        backend = self._sparse_backend
        embedding_backend = self._embedding_backend
        if backend is None or embedding_backend is None:
            return 0, 0.0
        try:
            backend.sparse_capability.require()
        except Exception:
            LOGGER.warning("rag_v2 sparse preload skipped: sparse backend unavailable")
            return 0, 0.0
        try:
            cache = self._sparse_vector_cache_for(embedding_backend.descriptor.fingerprint)
        except Exception:
            LOGGER.warning("rag_v2 sparse preload failed", exc_info=True)
            return 0, 0.0
        elapsed_ms = (perf_counter() - started) * 1000.0
        count = len(cache.chunk_ids) if cache is not None else 0
        LOGGER.info(
            "rag_v2 sparse vectors preloaded: chunks=%s terms=%s elapsed_ms=%.1f",
            count,
            len(cache.postings) if cache is not None else 0,
            elapsed_ms,
        )
        return count, elapsed_ms

    def _sparse_candidates_cached(
        self,
        plan: RetrievalQueryPlan,
        *,
        cache: _SparseVectorCache,
        limit: int,
        options: SearchOptions,
    ) -> List[SearchResult]:
        """Score sparse candidates through the inverted index (V3-A).

        Only documents sharing at least one query term are scored; a document
        with no shared term has an exact dot of 0 and is filtered out either
        way, so the ranked output is identical to the legacy full scan.
        Per-document dots accumulate in query-term order, matching
        ``sparse_dot_similarity`` whenever the query vector is the smaller
        side (the common case for short questions).
        """
        backend = self._sparse_backend
        assert backend is not None
        eligible: list[int] = []
        for index in range(len(cache.chunk_ids)):
            row = {
                "document_id": cache.document_ids[index],
                "source_path": cache.source_paths[index],
                "source_fingerprint": cache.source_fingerprints[index],
            }
            if not self._is_selected(row, options):
                continue
            if not self._privacy_is_allowed(cache.privacy_labels[index], options):
                continue
            if self._is_stale(row, options):
                continue
            eligible.append(index)
        eligible_mask = bytearray(len(cache.chunk_ids))
        for index in eligible:
            eligible_mask[index] = 1
        fused: dict[str, dict[str, Any]] = {}
        for variant in plan.variants:
            query_vector = normalize_sparse_vector(backend.sparse_query(variant.text))
            scores: dict[int, float] = {}
            for term, query_weight in query_vector.items():
                posting = cache.postings.get(term)
                if posting is None:
                    continue
                positions, weights = posting
                for doc_index, doc_weight in zip(positions, weights):
                    if eligible_mask[doc_index]:
                        scores[doc_index] = (
                            scores.get(doc_index, 0.0) + query_weight * doc_weight
                        )
            ranked = [
                (score, doc_index)
                for doc_index, score in scores.items()
                if score > 0.0
            ]
            ranked.sort(key=lambda item: (
                -item[0],
                cache.document_ids[item[1]],
                cache.source_paths[item[1]],
                cache.chunk_ids[item[1]],
            ))
            variant_weight = 1.25 if variant.origin == "original" else 1.0
            for rank, (similarity, doc_index) in enumerate(
                ranked[: options.candidate_limit], 1
            ):
                key = cache.chunk_ids[doc_index]
                record = fused.setdefault(key, {
                    "rrf_score": 0.0,
                    "best_similarity": similarity,
                    "doc_index": doc_index,
                    "privacy_labels": cache.privacy_labels[doc_index],
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
            -item["rrf_score"],
            -item["best_similarity"],
            cache.document_ids[item["doc_index"]],
            cache.source_paths[item["doc_index"]],
            cache.chunk_ids[item["doc_index"]],
        ))[:limit]
        by_id = self._chunk_rows_by_id(
            cache.chunk_ids[record["doc_index"]] for record in ordered
        )
        results = []
        for record in ordered:
            chunk_id = cache.chunk_ids[record["doc_index"]]
            row = by_id[chunk_id]
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


    def _numpy_rank_variant(
        self,
        cache: _DenseMatrixCache,
        eligible: Sequence[int],
        query_vector: Sequence[float],
        candidate_limit: int,
    ) -> list[tuple[float, int]]:
        import numpy as np

        if not eligible or candidate_limit <= 0:
            return []
        positions = np.asarray(eligible, dtype=np.int64)
        approx = cache.matrix[positions] @ np.asarray(query_vector, dtype=np.float32)
        pool = _numpy_candidate_pool(approx, candidate_limit)
        local_indexes = pool.astype(np.int64, copy=False)
        global_indexes = positions[local_indexes]
        scores = cache.matrix[global_indexes].astype(np.float64, copy=False) @ np.asarray(
            query_vector, dtype=np.float64
        )
        ranked = [
            (float(scores[offset]), int(global_indexes[offset]))
            for offset in range(int(global_indexes.shape[0]))
        ]
        ranked.sort(key=lambda item: (
            -item[0],
            cache.document_ids[item[1]],
            cache.source_paths[item[1]],
            cache.chunk_ids[item[1]],
        ))
        ranked = ranked[:candidate_limit]
        # Float64 dots match the Python cosine to ~1e-15. Exact-rescore only
        # neighbours close enough that rounding could swap their order.
        for offset, (similarity, global_index) in enumerate(ranked):
            previous = ranked[offset - 1][0] if offset else None
            nxt = ranked[offset + 1][0] if offset + 1 < len(ranked) else None
            near_previous = previous is not None and abs(previous - similarity) <= _NUMPY_SCORE_TIE_BAND
            near_next = nxt is not None and abs(nxt - similarity) <= _NUMPY_SCORE_TIE_BAND
            if not near_previous and not near_next:
                continue
            vector = tuple(float(value) for value in cache.matrix[global_index])
            ranked[offset] = (cosine_similarity(query_vector, vector), global_index)
        ranked.sort(key=lambda item: (
            -item[0],
            cache.document_ids[item[1]],
            cache.source_paths[item[1]],
            cache.chunk_ids[item[1]],
        ))
        return ranked[:candidate_limit]


    def _dense_candidates_numpy(
        self,
        query: str | RetrievalQueryPlan,
        *,
        limit: int,
        options: SearchOptions,
        ensure_embeddings: bool,
    ) -> List[SearchResult] | None:
        """Score cached float32 rows with a matrix product, then exact-rescore top-k."""
        backend = self._embedding_backend
        if backend is None:
            raise SemanticBackendError("embedding backend is not configured")
        backend.capability.require()
        if limit <= 0:
            return []
        plan = coerce_query_plan(query)
        started = perf_counter()
        if ensure_embeddings and not self._read_only:
            self.ensure_embeddings()
        descriptor = backend.descriptor
        load_started = perf_counter()
        cache = self._dense_matrix_cache_for(descriptor.fingerprint, descriptor.dimension)
        load_ms = (perf_counter() - load_started) * 1000.0
        if cache is None:
            return None
        eligible: list[int] = []
        for index, privacy_labels in enumerate(cache.privacy_labels):
            row = {
                "document_id": cache.document_ids[index],
                "source_path": cache.source_paths[index],
                "source_fingerprint": cache.source_fingerprints[index],
            }
            if not self._is_selected(row, options):
                continue
            if not self._privacy_is_allowed(privacy_labels, options):
                continue
            if self._is_stale(row, options):
                continue
            eligible.append(index)
        fused: dict[str, dict[str, Any]] = {}
        embed_ms = 0.0
        score_ms = 0.0
        query_vectors: list[tuple[float, ...]] = []
        for variant_offset, variant in enumerate(plan.variants):
            embed_started = perf_counter()
            query_vector = normalize_vector(
                backend.embed_query(variant.text),
                dimension=descriptor.dimension,
            )
            query_vectors.append(query_vector)
            embed_ms += (perf_counter() - embed_started) * 1000.0
            score_started = perf_counter()
            ranked = self._numpy_rank_variant(
                cache,
                eligible,
                query_vector,
                options.candidate_limit,
            )
            score_ms += (perf_counter() - score_started) * 1000.0
            variant_weight = 1.25 if variant.origin == "original" else 1.0
            for rank, (similarity, global_index) in enumerate(ranked, 1):
                key = cache.chunk_ids[global_index]
                record = fused.setdefault(key, {
                    "rrf_score": 0.0,
                    "best_similarity": similarity,
                    "chunk_id": key,
                    "document_id": cache.document_ids[global_index],
                    "source_path": cache.source_paths[global_index],
                    "privacy_labels": cache.privacy_labels[global_index],
                    "variants": [],
                    "variant_ids": [],
                    "facet_ids": [],
                    "variant_offsets": [],
                })
                record["rrf_score"] += variant_weight / (60.0 + rank)
                record["variants"].append(variant.text)
                record["variant_ids"].append(variant.variant_id)
                record["facet_ids"].append(variant.facet_id)
                record["variant_offsets"].append(variant_offset)
                if similarity > record["best_similarity"]:
                    record["best_similarity"] = similarity
                    record["privacy_labels"] = cache.privacy_labels[global_index]
        fuse_started = perf_counter()
        ordered = sorted(fused.values(), key=lambda item: (
            -item["rrf_score"],
            -item["best_similarity"],
            item["document_id"],
            item["source_path"],
            item["chunk_id"],
        ))[:limit]
        index_by_chunk = {chunk_id: index for index, chunk_id in enumerate(cache.chunk_ids)}
        for record in ordered:
            vector = tuple(float(value) for value in cache.matrix[index_by_chunk[record["chunk_id"]]])
            record["best_similarity"] = max(
                cosine_similarity(query_vectors[offset], vector)
                for offset in record["variant_offsets"]
            )
        ordered = sorted(ordered, key=lambda item: (
            -item["rrf_score"],
            -item["best_similarity"],
            item["document_id"],
            item["source_path"],
            item["chunk_id"],
        ))
        by_id = self._chunk_rows_by_id(record["chunk_id"] for record in ordered)
        results = []
        for record in ordered:
            row = by_id[record["chunk_id"]]
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
        fuse_ms = (perf_counter() - fuse_started) * 1000.0
        LOGGER.info(
            "rag_v2.stage search path=numpy chunks=%s variants=%s embed_ms=%.3f load_ms=%.3f score_ms=%.3f fuse_ms=%.3f total_ms=%.3f",
            cache.matrix.shape[0],
            len(plan.variants),
            embed_ms,
            load_ms,
            score_ms,
            fuse_ms,
            (perf_counter() - started) * 1000.0,
        )
        return results

    def _chunk_rows_by_id(self, chunk_ids: Iterable[str]) -> dict[str, sqlite3.Row]:
        ids = tuple(dict.fromkeys(chunk_ids))
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"SELECT * FROM chunks WHERE chunk_id IN ({placeholders})",
            ids,
        ).fetchall()
        return {str(row["chunk_id"]): row for row in rows}

    def dense_candidates(
        self,
        query: str | RetrievalQueryPlan,
        *,
        limit: int = 100,
        options: Optional[SearchOptions] = None,
        ensure_embeddings: bool = True,
    ) -> List[SearchResult]:
        """Return filtered local cosine candidates fused only across query variants."""
        if numpy_dense_search_enabled():
            try:
                numpy_results = self._dense_candidates_numpy(
                    query,
                    limit=limit,
                    options=options or SearchOptions(),
                    ensure_embeddings=ensure_embeddings,
                )
                if numpy_results is not None:
                    return numpy_results
            except Exception as exc:
                LOGGER.warning(
                    "Đường quét dense numpy gặp lỗi; tự động chuyển sang đường quét dense tuần tự Python: %s",
                    exc,
                )
        python_started = perf_counter()
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
        LOGGER.info(
            "rag_v2.stage search path=python dense_candidates_ms=%.3f variants=%s",
            (perf_counter() - python_started) * 1000.0,
            len(plan.variants),
        )
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
        thin_retry: bool = False,
    ) -> SearchResponse:
        """Run bounded hybrid retrieval with optional precomputed MaxSim authority."""
        plan = coerce_query_plan(query)
        retrieval_mode = (
            plan.retrieval_mode
            if plan.retrieval_mode != "full"
            else detect_retrieval_mode(
                plan.original_query,
                plan.intent_category,
                plan.target_terms,
            )
        )
        if plan.intent_category == "cross_source_synthesis":
            limit = max(limit, getattr(plan, "target_retrieval_limit", limit))
        if plan_has_cjk_variants(plan):
            limit = max(limit, 25)
        if ranking_config is None:
            source_names = self._sample_source_names()
            if uses_script_mismatch_ranking(plan.original_query, source_names):
                lexical_w, dense_w, sparse_w = MISMATCH_CHANNEL_WEIGHTS
                ranking_config = HybridRankingConfig(
                    lexical_weight=lexical_w,
                    dense_weight=dense_w,
                    sparse_weight=sparse_w,
                )

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
        is_single_doc = bool(
            (options.allowed_document_ids and len(options.allowed_document_ids) == 1)
            or (options.allowed_source_paths and len(options.allowed_source_paths) == 1)
        )
        fuse_options = replace(
            options,
            per_document_limit=options.per_document_limit if is_single_doc else min(options.per_document_limit, 3),
        )
        response = fuse_ranked_channels(
            query,
            lexical,
            dense,
            limit=limit,
            options=fuse_options,
            sparse_results=sparse,
            config=ranking_config,
            reranker=reranker,
            multivector_scores=multivector_scores,
            multivector_load_latency_ms=multivector_load_latency_ms,
            multivector_maxsim_latency_ms=multivector_maxsim_latency_ms,
        )
        if plan.intent_category in ("cross_source_synthesis", "general"):
            doc_ids = list(dict.fromkeys(r.document_id for r in response.results))
            if doc_ids:
                summary_chunks = self._fetch_document_summaries(doc_ids, plan)
                if summary_chunks:
                    summary_ids = {sc.chunk_id for sc in summary_chunks}
                    filtered = tuple(r for r in response.results if r.chunk_id not in summary_ids)
                    # A query carrying an identifier/code/number asks for a concrete
                    # value: keep summaries after the body chunks (as in full mode)
                    # so overview text cannot starve the literal answer of budget.
                    summary_after_body = (
                        retrieval_mode == "full"
                        or _query_carries_exact_values(plan.original_query)
                    )
                    combined = (
                        filtered + tuple(summary_chunks)
                        if summary_after_body
                        else tuple(summary_chunks) + filtered
                    )
                    response = replace(response, results=combined)
        unique_docs = {result.document_id for result in response.results}
        if should_retry_thin_results(
            unique_document_count=len(unique_docs),
            indexed_document_count=self._distinct_document_count(),
            already_retried=thin_retry,
        ):
            lexical_w, dense_w, sparse_w = MISMATCH_CHANNEL_WEIGHTS
            return self.hybrid_search_with_summary(
                query,
                limit=max(limit, 25),
                dense_limit=max(dense_limit, 150),
                options=options,
                ranking_config=HybridRankingConfig(
                    lexical_weight=lexical_w,
                    dense_weight=dense_w,
                    sparse_weight=sparse_w,
                ),
                reranker=reranker,
                use_multivector=use_multivector,
                precomputed_only=precomputed_only,
                thin_retry=True,
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
        cache = self._sparse_vector_cache_for(descriptor.fingerprint)
        if cache is not None:
            return self._sparse_candidates_cached(
                plan, cache=cache, limit=limit, options=options
            )
        rows = self._conn.execute(
            """
            SELECT c.chunk_id, c.document_id, c.source_path, c.source_fingerprint,
                   c.privacy_labels_json, s.sparse_json
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
        # The scan above only fetched narrow rows (no text/metadata blobs);
        # refetch the full rows for the finalists, like the numpy dense path.
        by_id = self._chunk_rows_by_id(
            str(record["row"]["chunk_id"]) for record in ordered
        )
        results = []
        for record in ordered:
            row = by_id[str(record["row"]["chunk_id"])]
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

    def _fetch_document_summaries(self, document_ids: list[str], plan: RetrievalQueryPlan) -> list[SearchResult]:
        if not document_ids:
            return []

        placeholders = ",".join("?" for _ in document_ids)
        rows = self._conn.execute(
            f"SELECT * FROM chunks WHERE document_id IN ({placeholders}) AND retrievable = 1",
            document_ids
        ).fetchall()

        summaries = []
        for row in rows:
            full_meta = json.loads(row["metadata_json"])
            if full_meta.get("metadata", {}).get("is_document_summary"):
                # Trick the relevance gate by artificially injecting the target terms
                # and providing a high dense score so semantic fallback accepts it.
                terms = tuple(plan.target_terms) if plan.target_terms else ()
                variant_ids = tuple(v.variant_id for v in plan.variants if v.variant_id)

                summaries.append(SearchResult(
                    chunk_id=str(row["chunk_id"]),
                    score=2.0, # Artificial high score
                    text=str(row["text"]),
                    document_id=str(row["document_id"]),
                    source_path=str(row["source_path"]),
                    source_name=str(row["source_name"]),
                    file_type=str(row["file_type"]),
                    metadata=full_meta.get("metadata", {}),
                    privacy_labels=tuple(json.loads(row["privacy_labels_json"])),
                    matched_terms=terms,
                    matched_query_variant_ids=variant_ids,
                    ranking_signals={"dense_cosine": 1.0, "dense_channel_rank": 1},
                ))
        return summaries

    def search_summaries_with_summary(
        self,
        query: str | RetrievalQueryPlan,
        limit: int = 15,
        options: Optional[SearchOptions] = None,
    ) -> SearchResponse:
        """Rank document-summary chunks only. Does not scan body chunks or embed."""
        options = options or SearchOptions()
        plan = coerce_query_plan(query)
        started = perf_counter()
        indexed_count = self.count()
        rows = self._conn.execute(
            "SELECT * FROM chunks WHERE retrievable = 1 AND file_type = ?",
            ("document_summary",),
        ).fetchall()
        eligible: list[sqlite3.Row] = []
        for row in rows:
            privacy_labels = tuple(json.loads(row["privacy_labels_json"] or "[]"))
            if not self._is_selected(row, options):
                continue
            if not self._privacy_is_allowed(privacy_labels, options):
                continue
            if self._is_stale(row, options):
                continue
            eligible.append(row)
        if limit <= 0 or not eligible:
            response = self._empty_response(
                query=plan.original_query,
                indexed_chunk_count=indexed_count,
                reason="no_document_summaries" if limit > 0 else "non_positive_limit",
            )
            LOGGER.info(
                "rag_v2.stage search path=summary_only chunks=%s variants=%s search_ms=%.3f",
                indexed_count,
                len(plan.variants),
                (perf_counter() - started) * 1000.0,
            )
            return response
        terms = extract_content_terms(plan.original_query)
        scored: list[tuple[float, sqlite3.Row, Dict[str, Any], tuple[str, ...], Dict[str, float], tuple[str, ...], float]] = []
        for row in eligible:
            candidate = self._score_candidate(row, terms, plan) if terms else None
            if candidate is None:
                metadata = json.loads(row["metadata_json"])
                privacy_labels = tuple(json.loads(row["privacy_labels_json"] or "[]"))
                scored.append((0.01, row, metadata, privacy_labels, {"summary_fallback": 0.01}, (), 0.0))
                continue
            scored.append(candidate)
        scored.sort(key=lambda item: (
            -item[0],
            str(item[1]["document_id"]),
            str(item[1]["chunk_id"]),
        ))
        chosen = scored[: max(1, limit)]
        variant_ids = tuple(variant.variant_id for variant in plan.variants if variant.variant_id)
        results: list[SearchResult] = []
        for score, row, metadata, privacy_labels, signals, matched_terms, coverage in chosen:
            nested = dict(metadata.get("metadata") or {}) if isinstance(metadata.get("metadata"), dict) else {}
            nested["is_document_summary"] = True
            result_metadata = dict(metadata)
            result_metadata["metadata"] = nested
            result_metadata["is_document_summary"] = True
            results.append(SearchResult(
                chunk_id=str(row["chunk_id"]),
                score=float(score),
                text=str(row["text"]),
                document_id=str(row["document_id"]),
                source_path=str(row["source_path"]),
                source_name=str(row["source_name"]),
                file_type=str(row["file_type"]),
                metadata=result_metadata,
                privacy_labels=privacy_labels,
                ranking_signals=dict(signals),
                matched_terms=matched_terms,
                matched_query_variant_ids=variant_ids,
                matched_query_facets=tuple(dict.fromkeys(variant.facet_id for variant in plan.variants)),
                matched_obligations=tuple(plan.required_obligations),
            ))
        elapsed_ms = (perf_counter() - started) * 1000.0
        LOGGER.info(
            "rag_v2.stage search path=summary_only chunks=%s summaries=%s variants=%s search_ms=%.3f",
            indexed_count,
            len(eligible),
            len(plan.variants),
            elapsed_ms,
        )
        return SearchResponse(
            results=tuple(results),
            summary=SearchSummary(
                query=plan.original_query,
                indexed_chunk_count=indexed_count,
                eligible_chunk_count=len(eligible),
                candidate_count=len(scored),
                returned_count=len(results),
                query_variant_count=len(plan.variants),
                query_plan_fingerprint=plan.fingerprint,
                expansion_status=plan.expansion_status,
                candidate_backend="summary_only",
                planned_facet_ids=plan.facet_ids,
                planned_obligation_ids=plan.required_obligations,
                lexical_latency_ms=elapsed_ms,
            ),
        )

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
        # OPT-RAGV2-LEXICAL B2: read the kill-switch + sub-toggles once per
        # search. None when V2 is off -> pre-B2 code path runs unchanged.
        lex_v2 = _lexical_v2_flags()
        identifier_patterns = _identifier_patterns(query_plan.original_query)
        if query_plan.intent_category == "cross_source_synthesis":
            effective_limit = max(limit, getattr(query_plan, "target_retrieval_limit", limit))
            effective_per_doc_limit = max(
                options.per_document_limit,
                getattr(query_plan, "target_per_document_limit", options.per_document_limit),
            )
        else:
            effective_limit = limit
            effective_per_doc_limit = options.per_document_limit
        query_text = query_plan.original_query
        terms = extract_content_terms(query_text)
        # OPT-RAGV2-LEXICAL B1: per-part lexical timings. Always-on and light
        # (a few perf_counter calls); OMP reads the split from
        # SearchSummary.lexical_breakdown_ms on PC0575.
        lex_timings: Dict[str, float] = {}
        eligibility_start = perf_counter()
        # OPT-RAGV2-LEXICAL B2 NARROW_ELIGIBILITY: the filter loop below only
        # needs these columns; full rows are fetched lazily for candidates.
        # Identifier queries keep the full-row path (the rescue scan needs
        # normalized_text for every eligible row).
        narrow_eligibility = (
            lex_v2 is not None
            and lex_v2["NARROW_ELIGIBILITY"]
        )
        if narrow_eligibility:
            indexed_rows = self._conn.execute(
                "SELECT chunk_id, document_id, source_path,"
                " privacy_labels_json, source_fingerprint"
                " FROM chunks WHERE retrievable = 1"
            ).fetchall()
        else:
            indexed_rows = self._conn.execute(
                "SELECT * FROM chunks WHERE retrievable = 1"
            ).fetchall()
        lex_timings["indexed_rows"] = float(len(indexed_rows))

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
            if not self._is_selected(row, options):
                filtered_by_source += 1
                continue
            # OPT-RAGV2-LEXICAL B2 PRIVACY_LAZY: skip the per-row JSON parse
            # when no privacy filter is configured -- _privacy_is_allowed
            # returns True unconditionally then, so counts are unchanged.
            if (
                lex_v2 is not None
                and lex_v2["PRIVACY_LAZY"]
                and options.allowed_privacy_labels is None
            ):
                pass
            else:
                privacy_labels = tuple(json.loads(row["privacy_labels_json"] or "[]"))
                if not self._privacy_is_allowed(privacy_labels, options):
                    filtered_by_privacy += 1
                    continue
            if self._is_stale(row, options):
                filtered_as_stale += 1
                continue
            eligible_rows.append(row)
        lex_timings["eligibility_ms"] = (perf_counter() - eligibility_start) * 1000.0
        lex_timings["eligible_rows"] = float(len(eligible_rows))
        # OPT-RAGV2-LEXICAL B2: ids + completeness flag for the V2 path.
        eligible_ids = [str(row["chunk_id"]) for row in eligible_rows]
        eligible_complete = (
            filtered_by_source == 0
            and filtered_by_privacy == 0
            and filtered_as_stale == 0
        )

        # Rank each validated query variant independently, then fuse by rank.
        # Filtering is already complete above, so FTS and variants can never bypass
        # privacy, source-selection, or stale-fingerprint constraints.
        per_variant_candidates: list[tuple[Any, list[tuple[float, sqlite3.Row, Dict[str, Any], tuple[str, ...], Dict[str, float], tuple[str, ...], float]]]] = []
        candidate_backend = self.retrieval_backend
        # OPT-RAGV2-LEXICAL B2: per-search hoisted values (SCORE_HOIST) and a
        # per-row bundle cache shared across variants (SCORE_CACHE).
        score_hoisted = None
        if lex_v2 is not None and lex_v2["SCORE_HOIST"]:
            score_hoisted = (
                frozenset(query_plan.target_terms)
                if query_plan.target_terms
                else frozenset(extract_content_terms(query_plan.original_query)),
                query_plan.intent_category,
            )
        use_score_cache = lex_v2 is not None and lex_v2["SCORE_CACHE"]
        row_bundle_cache: Dict[str, Dict[str, Any]] = {}
        for variant in query_plan.variants:
            variant_terms = extract_content_terms(variant.text)
            if not variant_terms:
                continue
            rescue_patterns = identifier_patterns if variant.origin == "original" else ()
            if lex_v2 is not None:
                candidate_rows, backend = self._candidate_rows_v2(
                    variant.text,
                    eligible_ids,
                    options.candidate_limit,
                    timings=lex_timings,
                    eligible_complete=eligible_complete,
                    lex_v2=lex_v2,
                    identifier_patterns=rescue_patterns,
                    query_plan=query_plan,
                )
            else:
                candidate_rows, backend = self._candidate_rows(
                    variant.text,
                    eligible_rows,
                    options.candidate_limit,
                    identifier_patterns=rescue_patterns,
                    query_plan=query_plan,
                    timings=lex_timings,
                )
            if backend != "fts5_bm25":
                candidate_backend = "deterministic_scan"
            ranked = []
            # OPT-RAGV2-LEXICAL B1: (c) per-row Python scoring.
            score_start = perf_counter()
            score_calls = 0
            for candidate_position, row in enumerate(candidate_rows):
                if use_score_cache:
                    cache_key = str(row["chunk_id"])
                    bundle = row_bundle_cache.get(cache_key)
                    if bundle is None:
                        bundle = LocalChunkIndex._score_candidate_bundle(row)
                        row_bundle_cache[cache_key] = bundle
                    candidate = self._score_candidate(
                        row,
                        variant_terms,
                        query_plan=query_plan,
                        _bundle=bundle,
                        _hoisted=score_hoisted,
                    )
                else:
                    candidate = self._score_candidate(
                        row,
                        variant_terms,
                        query_plan=query_plan,
                        _hoisted=score_hoisted,
                    )
                score_calls += 1
                if candidate is not None:
                    identifier_priority = _identifier_match_priority(
                        str(row["normalized_text"] or ""),
                        rescue_patterns,
                    )
                    ranked.append((candidate_position, candidate, identifier_priority))
            lex_timings["python_score_ms"] = lex_timings.get("python_score_ms", 0.0) + (
                perf_counter() - score_start
            ) * 1000.0
            lex_timings["score_candidate_calls"] = lex_timings.get("score_candidate_calls", 0.0) + float(
                score_calls
            )
            ranked.sort(
                key=lambda item: (
                    -item[2][0],
                    -item[2][1],
                    -item[1][0],
                    item[0],
                    item[1][1]["document_id"],
                    item[1][1]["source_path"],
                    item[1][1]["chunk_id"],
                )
            )
            exact_matches = [
                item for item in ranked if item[2][1]
            ][:_EXACT_IDENTIFIER_QUOTA]
            exact_ids = {str(item[1][1]["chunk_id"]) for item in exact_matches}
            selected = [item[1] for item in exact_matches]
            selected.extend(
                item[1]
                for item in ranked
                if str(item[1][1]["chunk_id"]) not in exact_ids
            )
            per_variant_candidates.append(
                (variant, selected[: options.candidate_limit])
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
            if plan_has_cjk_variants(query_plan):
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
            if document_counts[document_key] >= effective_per_doc_limit:
                LOGGER.info(
                    "rag_v2.diversity_cap_triggered document_id=%s source=%s limit=%d chunk_id=%s",
                    row["document_id"],
                    row["source_name"],
                    effective_per_doc_limit,
                    row["chunk_id"],
                )
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
            if len(results) >= effective_limit:
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
        # OPT-RAGV2-LEXICAL B1: expose the per-part split in a fixed order.
        # B2 adds temp_build_skipped / trigram_match_ms when the V2 path runs.
        breakdown_order = (
            "eligibility_ms",
            "indexed_rows",
            "eligible_rows",
            "temp_build_ms",
            "temp_build_skipped",
            "temp_inserted_rows",
            "fts_match_ms",
            "like_prefilter_ms",
            "trigram_match_ms",
            "identifier_rescue_ms",
            "python_score_ms",
            "score_candidate_calls",
        )
        lexical_breakdown = tuple(
            (key, lex_timings[key]) for key in breakdown_order if key in lex_timings
        )
        LOGGER.debug(
            "rag_v2 lexical breakdown ms: %s",
            ", ".join(f"{key}={value:.1f}" for key, value in lexical_breakdown),
        )
        if lex_v2 is not None:
            LOGGER.debug(
                "rag_v2 lexical v2 flags: %s",
                ", ".join(f"{key}={int(value)}" for key, value in lex_v2.items()),
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
            lexical_breakdown_ms=lexical_breakdown,
        )
        return SearchResponse(results=tuple(results), summary=summary)

    def clear(self) -> None:
        self._conn.execute("DELETE FROM chunks")
        self._conn.commit()
        self._note_main_db_write()

    def count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM chunks WHERE retrievable = 1"
        ).fetchone()
        return int(row["count"])

    def _distinct_document_count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(DISTINCT document_id) AS count FROM chunks WHERE retrievable = 1"
        ).fetchone()
        return int(row["count"])

    def _sample_source_names(self, limit: int = 40) -> tuple[str, ...]:
        rows = self._conn.execute(
            """
            SELECT DISTINCT source_name
            FROM chunks
            WHERE retrievable = 1
            LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()
        return tuple(str(row["source_name"] or "") for row in rows)

    @staticmethod
    def _escape_like_term(term: str) -> str:
        return (
            term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )

    def _cjk_like_prefilter_ids(
        self,
        eligible_ids: List[str],
        terms: tuple[str, ...],
        timings: Optional[Dict[str, float]] = None,
    ) -> Optional[List[str]]:
        """Ids version of the V1-A2 CJK LIKE prefilter (OPT-RAGV2-LEXICAL B2).

        Returns the eligible chunk ids (in eligible order) whose searchable
        text contains one of the 1-2 longest query terms, or None under the
        same conditions as _cjk_like_prefilter_rows. Same match set and order
        as the row version; lets the V2 path avoid materializing full rows.
        """
        if not cjk_prefilter_enabled():
            return None
        entities = _extract_query_entities(" ".join(terms))
        generic_stop = {"data", "file", "sheet", "line", "view", "part", "this", "from", "unit"}
        filtered = [
            term for term in terms
            if term and term.lower() not in generic_stop and (len(term) <= 6 or not _CJK_RE.search(term))
        ]
        # Entities are candidates, not the whole filter: a narrow entity
        # such as a lone short code must not hide the longest content terms.
        candidates = {term for term in filtered if term} | set(entities)
        usable_terms = sorted(
            candidates,
            key=lambda term: (-len(term), term),
        )[:2]
        if not usable_terms or not eligible_ids:
            return None
        search_expression = (
            "COALESCE(normalized_text, '') || ' ' || COALESCE(source_name, '')"
            " || ' ' || COALESCE(source_path, '')"
            " || ' ' || COALESCE(metadata_json, '')"
        )
        clauses = []
        parameters: list[str] = []
        for term in usable_terms:
            clauses.append("((" + search_expression + ") LIKE ? ESCAPE '\\')")
            parameters.append("%" + self._escape_like_term(term) + "%")
        start = perf_counter()
        try:
            matched_ids = {
                str(row["chunk_id"])
                for row in self._conn.execute(
                    "SELECT chunk_id FROM chunks WHERE retrievable = 1 AND ("
                    + " OR ".join(clauses)
                    + ") LIMIT 500",
                    parameters,
                ).fetchall()
            }
        except sqlite3.Error:
            LOGGER.warning(
                "rag_v2 CJK LIKE prefilter failed; using full scan",
                exc_info=True,
            )
            return None
        finally:
            if timings is not None:
                timings["like_prefilter_ms"] = timings.get("like_prefilter_ms", 0.0) + (
                    perf_counter() - start
                ) * 1000.0
        return [chunk_id for chunk_id in eligible_ids if chunk_id in matched_ids]

    def _cjk_like_prefilter_rows(
        self,
        eligible_rows: List[sqlite3.Row],
        terms: tuple[str, ...],
    ) -> Optional[List[sqlite3.Row]]:
        """Narrow CJK deterministic-scan candidates with SQL LIKE (V1-A2).

        Returns the eligible rows (in their original order) whose searchable
        text contains one of the 1-2 longest query terms, or None when the
        prefilter cannot run (the caller then falls back to the full scan).

        ``LIKE '%term%'`` over
        ``(normalized_text, source_name, source_path, metadata_json)`` is a
        superset of each kept term's match condition in ``_score_candidate``
        (substring match for CJK terms, token occurrence for latin terms --
        a token is always a substring of the column it came from), and
        ``_score_candidate`` remains the final scorer, so ranking among the
        kept rows is unchanged.

        Accepted tradeoff (per the ticket): only the 1-2 longest terms are
        used because they are the most selective -- that is what makes the
        scan cheaper. Rows matching *only* shorter variant terms are dropped
        by the prefilter. The ticket's acceptance bar is top-15 agreement
        with the full scan on the six sample questions (L1-L3/E1-E3),
        verified by test. If the prefilter ever diverges from the baseline
        on production, set ``AIOS_RAG_V2_CJK_PREFILTER=0`` to disable it.
        """
        ids = self._cjk_like_prefilter_ids(
            [str(row["chunk_id"]) for row in eligible_rows], terms
        )
        if ids is None:
            return None
        by_id = {str(row["chunk_id"]): row for row in eligible_rows}
        return [by_id[chunk_id] for chunk_id in ids if chunk_id in by_id]

    def _candidate_rows(
        self,
        query: str,
        eligible_rows: List[sqlite3.Row],
        limit: int,
        *,
        identifier_patterns: Sequence[re.Pattern[str]] = (),
        query_plan: Optional[RetrievalQueryPlan] = None,
        timings: Optional[Dict[str, float]] = None,
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
        # OPT-RAGV2-PYLOOPS V1-A2: narrow that scan with a SQL LIKE prefilter
        # first, on the 1-2 longest variant terms (the most selective ones;
        # see _cjk_like_prefilter_rows for the accepted tradeoff).
        # _score_candidate remains the final scorer, so ranking among the kept
        # rows is unchanged while chunks that cannot match skip the expensive
        # per-row Python tokenization.
        if _CJK_RE.search(query):
            # OPT-RAGV2-LEXICAL B1: time the CJK LIKE prefilter separately.
            prefilter_start = perf_counter()
            prefiltered = self._cjk_like_prefilter_rows(eligible_rows, terms)
            if timings is not None:
                timings["like_prefilter_ms"] = timings.get("like_prefilter_ms", 0.0) + (
                    perf_counter() - prefilter_start
                ) * 1000.0
            if prefiltered is not None:
                return prefiltered, "deterministic_scan"
            return list(eligible_rows), "deterministic_scan"
        match_query = " OR ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)
        try:
            self._conn.execute(
                "CREATE TEMP TABLE IF NOT EXISTS rag_v2_eligible_chunks (chunk_id TEXT PRIMARY KEY)"
            )
            self._conn.execute("DELETE FROM rag_v2_eligible_chunks")
            # OPT-RAGV2-LEXICAL B1: (a) temp-table build vs (b) FTS MATCH+bm25.
            build_start = perf_counter()
            self._conn.executemany(
                "INSERT INTO rag_v2_eligible_chunks(chunk_id) VALUES (?)",
                ((row["chunk_id"],) for row in eligible_rows),
            )
            if timings is not None:
                timings["temp_build_ms"] = timings.get("temp_build_ms", 0.0) + (
                    perf_counter() - build_start
                ) * 1000.0
                timings["temp_inserted_rows"] = timings.get("temp_inserted_rows", 0.0) + float(
                    len(eligible_rows)
                )
            match_start = perf_counter()
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
            if timings is not None:
                timings["fts_match_ms"] = timings.get("fts_match_ms", 0.0) + (
                    perf_counter() - match_start
                ) * 1000.0
        except sqlite3.OperationalError:
            self._fts5_available = False
            return list(eligible_rows), "deterministic_scan"
        by_id = {str(row["chunk_id"]): row for row in eligible_rows}
        ranked = [
            by_id[str(row["chunk_id"])]
            for row in ranked_ids
            if str(row["chunk_id"]) in by_id
        ]
        if not identifier_patterns:
            return ranked, "fts5_bm25"

        ranked_ids_set = {str(row["chunk_id"]) for row in ranked}
        exact_matches = []
        # OPT-RAGV2-LEXICAL B1: identifier-rescue scan is part of (c).
        rescue_start = perf_counter()
        for row in eligible_rows:
            if str(row["chunk_id"]) in ranked_ids_set:
                continue
            match_priority = _identifier_match_priority(
                str(row["normalized_text"] or ""),
                identifier_patterns,
            )
            if not match_priority[1]:
                continue
            candidate = self._score_candidate(row, terms, query_plan=query_plan)
            if candidate is not None:
                exact_matches.append((match_priority[0], match_priority[1], candidate[0], row))
        exact_matches.sort(
            key=lambda item: (
                -item[0],
                -item[1],
                -item[2],
                str(item[3]["document_id"]),
                str(item[3]["chunk_id"]),
            )
        )
        rescued_per_doc: Dict[str, int] = {}
        for item in exact_matches:
            if sum(rescued_per_doc.values()) >= _EXACT_IDENTIFIER_QUOTA:
                break
            doc_id = str(item[3]["document_id"])
            if rescued_per_doc.get(doc_id, 0) < 3:
                ranked.append(item[3])
                rescued_per_doc[doc_id] = rescued_per_doc.get(doc_id, 0) + 1
        if timings is not None:
            timings["identifier_rescue_ms"] = timings.get("identifier_rescue_ms", 0.0) + (
                perf_counter() - rescue_start
            ) * 1000.0
        return ranked, "fts5_bm25"

    # --- OPT-RAGV2-LEXICAL Phase B2 helpers (V2 paths only) ---

    def _fetch_chunk_rows(self, chunk_ids: Sequence[str]) -> List[sqlite3.Row]:
        """Fetch full chunk rows for ids, preserving the given id order.

        Used by the V2 narrow-eligibility path: the eligibility scan only
        reads filter columns, and full rows are materialized lazily for the
        (much smaller) candidate set. Batches stay under
        SQLITE_MAX_VARIABLE_NUMBER.
        """
        ids = [str(chunk_id) for chunk_id in chunk_ids]
        if not ids:
            return []
        by_id: Dict[str, sqlite3.Row] = {}
        for start in range(0, len(ids), 500):
            batch = ids[start : start + 500]
            placeholders = ", ".join(["?"] * len(batch))
            for row in self._conn.execute(
                f"SELECT * FROM chunks WHERE chunk_id IN ({placeholders})", batch
            ).fetchall():
                by_id[str(row["chunk_id"])] = row
        return [by_id[chunk_id] for chunk_id in ids if chunk_id in by_id]

    def _cjk_trigram_candidate_ids(
        self,
        terms: tuple[str, ...],
        eligible_ids: List[str],
        timings: Optional[Dict[str, float]] = None,
    ) -> Optional[List[str]]:
        """Trigram-FTS replacement for the CJK LIKE prefilter (B2, opt-in).

        Returns None when the ``chunks_fts_trigram`` table does not exist --
        the caller then falls back to the LIKE prefilter, so enabling
        ``AIOS_RAGV2_LEX_V2_CJK_TRIGRAM=1`` before OMP builds the table is
        harmless. Otherwise returns eligible ids (in eligible order) whose
        trigram-indexed text contains one of the 1-2 longest terms.

        Expected table (built by OMP in the index-write lane; read-only here):
        ``CREATE VIRTUAL TABLE chunks_fts_trigram USING
        fts5(chunk_id UNINDEXED, text, tokenize='trigram')`` where ``text`` is
        the same concatenated searchable expression the LIKE prefilter uses:
        ``COALESCE(normalized_text,'') || ' ' || COALESCE(source_name,'') ||
        ' ' || COALESCE(source_path,'') || ' ' || COALESCE(metadata_json,'')``.
        """
        try:
            table = self._conn.execute(
                "SELECT name FROM sqlite_master"
                " WHERE type = 'table' AND name = 'chunks_fts_trigram'"
            ).fetchone()
        except sqlite3.Error:
            return None
        if table is None:
            return None
        usable_terms = sorted(
            {term for term in terms if term}, key=lambda term: (-len(term), term)
        )[:2]
        if not usable_terms or not eligible_ids:
            return None
        match_query = " OR ".join(
            f'"{term.replace(chr(34), chr(34) * 2)}"' for term in usable_terms
        )
        start = perf_counter()
        try:
            rows = self._conn.execute(
                "SELECT chunk_id FROM chunks_fts_trigram"
                " WHERE chunks_fts_trigram MATCH ?",
                (match_query,),
            ).fetchall()
        except sqlite3.Error:
            LOGGER.warning(
                "rag_v2 CJK trigram prefilter failed; using LIKE fallback",
                exc_info=True,
            )
            return None
        if timings is not None:
            timings["trigram_match_ms"] = timings.get("trigram_match_ms", 0.0) + (
                perf_counter() - start
            ) * 1000.0
        matched_ids = {str(row["chunk_id"]) for row in rows}
        return [chunk_id for chunk_id in eligible_ids if chunk_id in matched_ids]

    def _fts_ranked_ids_v2(
        self,
        match_query: str,
        eligible_ids: List[str],
        limit: int,
        timings: Optional[Dict[str, float]] = None,
        use_txn: bool = True,
    ) -> Optional[List[str]]:
        """V2 FTS branch: temp-table build (+ optional explicit txn) + MATCH.

        Returns the ranked chunk ids, or None when FTS5 is unavailable (the
        caller falls back to the deterministic scan, mirroring _candidate_rows).
        """
        try:
            self._conn.execute(
                "CREATE TEMP TABLE IF NOT EXISTS rag_v2_eligible_chunks (chunk_id TEXT PRIMARY KEY)"
            )
            began_txn = bool(use_txn) and not self._conn.in_transaction
            if began_txn:
                self._conn.execute("BEGIN")
            try:
                self._conn.execute("DELETE FROM rag_v2_eligible_chunks")
                build_start = perf_counter()
                self._conn.executemany(
                    "INSERT INTO rag_v2_eligible_chunks(chunk_id) VALUES (?)",
                    ((chunk_id,) for chunk_id in eligible_ids),
                )
                build_ms = (perf_counter() - build_start) * 1000.0
            except Exception:
                if began_txn:
                    self._conn.execute("ROLLBACK")
                raise
            if began_txn:
                self._conn.execute("COMMIT")
            match_start = perf_counter()
            ranked = self._conn.execute(
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
            match_ms = (perf_counter() - match_start) * 1000.0
        except sqlite3.OperationalError:
            self._fts5_available = False
            return None
        if timings is not None:
            timings["temp_build_ms"] = timings.get("temp_build_ms", 0.0) + build_ms
            timings["temp_inserted_rows"] = timings.get("temp_inserted_rows", 0.0) + float(
                len(eligible_ids)
            )
            timings["fts_match_ms"] = timings.get("fts_match_ms", 0.0) + match_ms
        return [str(row["chunk_id"]) for row in ranked]

    def _candidate_rows_v2(
        self,
        query: str,
        eligible_ids: List[str],
        limit: int,
        *,
        timings: Optional[Dict[str, float]] = None,
        eligible_complete: bool = False,
        lex_v2: Dict[str, bool],
        identifier_patterns: Sequence[re.Pattern[str]] = (),
        query_plan: Optional[RetrievalQueryPlan] = None,
    ) -> tuple[List[sqlite3.Row], str]:
        """Phase-B2 candidate path: same results as _candidate_rows.

        Works from eligible chunk ids (narrow eligibility) and fetches full
        rows lazily for candidates only. Fast identifier-rescue path uses
        FTS token lookup for instant candidate filtering without full scan.
        Every optimization is gated by its own lex_v2 sub-toggle.
        """
        if not self._fts5_available or not eligible_ids:
            return self._fetch_chunk_rows(eligible_ids), "deterministic_scan"
        terms = extract_content_terms(query)
        if not terms:
            return [], "fts5_bm25"
        if _CJK_RE.search(query):
            if lex_v2["CJK_TRIGRAM"]:
                trigram_ids = self._cjk_trigram_candidate_ids(
                    terms, eligible_ids, timings
                )
                if trigram_ids is not None:
                    return (
                        self._fetch_chunk_rows(trigram_ids),
                        "deterministic_scan",
                    )
            like_ids = self._cjk_like_prefilter_ids(eligible_ids, terms, timings)
            target_ids = like_ids if like_ids is not None else eligible_ids
            return self._fetch_chunk_rows(target_ids), "deterministic_scan"
        
        fts_terms = terms
        if lex_v2.get("SELECTIVE_TERMS", True) and len(terms) > 8:
            selective = [t for t in terms if t.lower() not in _VIETNAMESE_COMMON_STOPWORDS]
            if len(selective) >= 2:
                fts_terms = tuple(selective)

        match_query = " OR ".join(
            f'"{term.replace(chr(34), chr(34) * 2)}"' for term in fts_terms
        )
        ranked_ids: Optional[List[str]]
        if lex_v2["SKIP_FULL_ELIGIBLE"] and eligible_complete:
            # Eligible covers every retrievable chunk, so the temp-table JOIN
            # is a no-op: join chunks directly on retrievable = 1 instead.
            # Same MATCH, same bm25 weights, same ORDER BY/LIMIT -> identical
            # ranking, without building the temp table.
            try:
                match_start = perf_counter()
                fts_rows = self._conn.execute(
                    """
                    SELECT f.chunk_id
                    FROM chunks_fts AS f
                    JOIN chunks AS c ON c.chunk_id = f.chunk_id AND c.retrievable = 1
                    WHERE chunks_fts MATCH ?
                    ORDER BY bm25(chunks_fts, 0.0, 1.0, 2.0, 1.0, 0.75), f.chunk_id
                    LIMIT ?
                    """,
                    (match_query, limit),
                ).fetchall()
                if timings is not None:
                    timings["fts_match_ms"] = timings.get("fts_match_ms", 0.0) + (
                        perf_counter() - match_start
                    ) * 1000.0
                    timings["temp_build_skipped"] = (
                        timings.get("temp_build_skipped", 0.0) + 1.0
                    )
            except sqlite3.OperationalError:
                self._fts5_available = False
                return self._fetch_chunk_rows(eligible_ids), "deterministic_scan"
            ranked_ids = [str(row["chunk_id"]) for row in fts_rows]
        else:
            ranked_ids = self._fts_ranked_ids_v2(
                match_query,
                eligible_ids,
                limit,
                timings,
                use_txn=lex_v2["TEMP_TXN"],
            )
            if ranked_ids is None:
                return self._fetch_chunk_rows(eligible_ids), "deterministic_scan"
        ranked = self._fetch_chunk_rows(ranked_ids)
        if not identifier_patterns:
            return ranked, "fts5_bm25"

        ranked_ids_set = {str(row["chunk_id"]) for row in ranked}
        rescue_start = perf_counter()
        literals = _identifier_literals(query)
        rescue_candidate_ids = set()
        if literals:
            rescue_subqueries = []
            for lit in literals:
                sub_terms = re.findall(r"\w+", lit)
                if sub_terms:
                    rescue_subqueries.append(" OR ".join(f'"{st}"' for st in sub_terms))
            if rescue_subqueries:
                rescue_match = " OR ".join(rescue_subqueries)
                try:
                    r_rows = self._conn.execute(
                        """
                        SELECT f.chunk_id
                        FROM chunks_fts AS f
                        JOIN chunks AS c ON c.chunk_id = f.chunk_id AND c.retrievable = 1
                        WHERE chunks_fts MATCH ?
                        LIMIT 500
                        """,
                        (rescue_match,),
                    ).fetchall()
                    rescue_candidate_ids = {str(r["chunk_id"]) for r in r_rows} - ranked_ids_set
                except sqlite3.OperationalError:
                    pass

        if not rescue_candidate_ids and len(eligible_ids) <= 1000:
            rescue_candidate_ids = set(eligible_ids) - ranked_ids_set

        rescue_cand_rows = self._fetch_chunk_rows(list(rescue_candidate_ids))
        exact_matches = []
        for r in rescue_cand_rows:
            match_priority = _identifier_match_priority(
                str(r["normalized_text"] or ""),
                identifier_patterns,
            )
            if not match_priority[1]:
                continue
            candidate = self._score_candidate(r, terms, query_plan=query_plan)
            if candidate is not None:
                exact_matches.append((match_priority[0], match_priority[1], candidate[0], r))

        exact_matches.sort(
            key=lambda item: (
                -item[0],
                -item[1],
                -item[2],
                str(item[3]["document_id"]),
                str(item[3]["chunk_id"]),
            )
        )
        rescued_per_doc: Dict[str, int] = {}
        for item in exact_matches:
            if sum(rescued_per_doc.values()) >= _EXACT_IDENTIFIER_QUOTA:
                break
            doc_id = str(item[3]["document_id"])
            if rescued_per_doc.get(doc_id, 0) < 3:
                ranked.append(item[3])
                rescued_per_doc[doc_id] = rescued_per_doc.get(doc_id, 0) + 1
        if timings is not None:
            timings["identifier_rescue_ms"] = timings.get("identifier_rescue_ms", 0.0) + (
                perf_counter() - rescue_start
            ) * 1000.0
        return ranked, "fts5_bm25"

    @staticmethod
    def _score_candidate_bundle(row: sqlite3.Row) -> Dict[str, Any]:
        """Term-independent per-row precomputations for _score_candidate (B2).

        The expensive parts of scoring a row -- JSON parsing, full-text
        tokenization (_tokens, incl. CJK n-grams), Counters, lower() -- depend
        only on the row, not on the query variant. With SCORE_CACHE the
        variant loop builds each row's bundle once and reuses it across
        variants. Values are identical to the inline computations in
        _score_candidate.
        """
        metadata = json.loads(row["metadata_json"])
        privacy_labels = tuple(json.loads(row["privacy_labels_json"] or "[]"))
        text = row["normalized_text"]
        source_name = row["source_name"]
        source_path = row["source_path"]
        section_text = " ".join(_text_values(metadata.get("section_path")))
        sheet_text = " ".join(_text_values(metadata.get("sheet_names")))
        element_types = tuple(
            value.lower() for value in _text_values(metadata.get("element_types"))
        )
        all_tokens = _tokens(text)
        text_counts = Counter(all_tokens)
        title_tokens = set(_tokens(source_name))
        path_tokens = set(_tokens(source_path))
        section_tokens = set(_tokens(section_text))
        sheet_tokens = set(_tokens(sheet_text))
        return {
            "metadata": metadata,
            "privacy_labels": privacy_labels,
            "text": text,
            "source_name": source_name,
            "source_path": source_path,
            "section_text": section_text,
            "sheet_text": sheet_text,
            "element_types": element_types,
            "all_tokens": all_tokens,
            "text_counts": text_counts,
            "title_tokens": title_tokens,
            "path_tokens": path_tokens,
            "section_tokens": section_tokens,
            "sheet_tokens": sheet_tokens,
            "searchable_tokens": (
                set(text_counts)
                | title_tokens
                | path_tokens
                | section_tokens
                | sheet_tokens
            ),
            "normalized_text": text.lower(),
        }

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
        self._dense_matrix_cache = None
        self._sparse_vector_cache = None
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
        row_fp = row["source_fingerprint"]
        if not row_fp:
            return False
        expected = options.expected_source_fingerprints
        if row["document_id"] in expected:
            exp = expected[row["document_id"]]
            return bool(exp and row_fp != exp)
        if row["source_path"] in expected:
            exp = expected[row["source_path"]]
            return bool(exp and row_fp != exp)
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
        _bundle: Optional[Dict[str, Any]] = None,
        _hoisted: Optional[tuple[frozenset, str]] = None,
    ) -> Optional[tuple[float, sqlite3.Row, Dict[str, Any], tuple[str, ...], Dict[str, float], tuple[str, ...], float]]:
        # OPT-RAGV2-LEXICAL B2: with SCORE_CACHE the caller passes a
        # precomputed per-row bundle (see _score_candidate_bundle); otherwise
        # the bundle is built inline -- identical values, identical order.
        # With SCORE_HOIST the caller passes (target_terms, intent_category)
        # computed once per search instead of once per row.
        b = _bundle if _bundle is not None else LocalChunkIndex._score_candidate_bundle(row)
        metadata = b["metadata"]
        privacy_labels = b["privacy_labels"]
        text = b["text"]
        source_name = b["source_name"]
        source_path = b["source_path"]
        section_text = b["section_text"]
        sheet_text = b["sheet_text"]
        element_types = b["element_types"]
        all_tokens = b["all_tokens"]
        text_counts = b["text_counts"]
        title_tokens = b["title_tokens"]
        path_tokens = b["path_tokens"]
        section_tokens = b["section_tokens"]
        sheet_tokens = b["sheet_tokens"]
        searchable_tokens = b["searchable_tokens"]
        normalized_text = b["normalized_text"]
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
        if _hoisted is not None:
            original_target_terms = _hoisted[0]
        else:
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
        if _hoisted is not None:
            intent = _hoisted[1]
            action_words = _LEX_ACTION_WORDS
            problem_words = _LEX_PROBLEM_WORDS
        else:
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

        query_text = query_plan.original_query if query_plan else ""
        entities = _extract_query_entities(query_text)
        if entities:
            src_lower = (source_name or "").lower() + " " + (source_path or "").lower()
            title_hits = 0
            prefix_hits = 0
            prefix_lower = (text or "")[:500].lower()
            text_lower = (text or "").lower()
            body_hits = 0
            for ent in entities:
                ent_lower = ent.lower()
                ent_stem = ent_lower.replace(" tape", "").replace(" line", "").strip()
                if ent_lower in src_lower or (len(ent_stem) >= 3 and ent_stem in src_lower):
                    title_hits += 1
                elif ent_lower in prefix_lower or (len(ent_stem) >= 3 and ent_stem in prefix_lower):
                    prefix_hits += 1
                elif re.search(rf"(?<!\w){re.escape(ent_lower)}(?!\w)", text_lower):
                    body_hits += 1
            if title_hits:
                signals["entity_title_match"] = min(3.0 * float(title_hits), 4.0)
            if prefix_hits:
                signals["entity_prefix_match"] = min(1.5 * float(prefix_hits), 2.0)
            if body_hits:
                signals["exact_entity_body_boost"] = min(3.5 * float(body_hits), 7.0)

            query_lower = query_text.lower()
            is_summary = bool(metadata.get("is_document_summary")) or "[document architecture & summary]" in text_lower[:200]
            if not is_summary and any(k in query_lower for k in ("nominal", "dung sai", "giới hạn", "kích thước")):
                has_spec_formula = (
                    ("=e" in text_lower and any(sym in text_lower for sym in ("+0.", "-0.", "±")))
                    or ("+0." in text_lower and "-0." in text_lower)
                    or "dung sai" in text_lower
                )
                if has_spec_formula:
                    signals["exact_spec_tolerance_boost"] = 4.0
                    if len(entities) >= 2 and (title_hits + prefix_hits + body_hits) >= len(entities):
                        signals["exact_all_entities_match_boost"] = 4.0

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
