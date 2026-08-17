"""Adaptive retrieval routing and sufficiency gates for local RAG v2.

Pure decision policies with allowlisted reason codes and no raw text leaks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Mapping, Optional, Sequence, Tuple

from .index import SearchSummary
from .query_planning import RetrievalQueryPlan


class SearchPreferenceMode(str, Enum):
    AUTO = "auto"
    DEEP = "deep"


class PreDecision(str, Enum):
    FAST = "fast"
    DEEP = "deep"
    UNCERTAIN = "uncertain"
    NOT_APPLICABLE = "not_applicable"


class PostDecision(str, Enum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    UNCERTAIN = "uncertain"
    NOT_RUN = "not_run"


class RetrievalPath(str, Enum):
    STRUCTURED_EXCEL = "structured_excel"
    HYBRID = "hybrid"
    HYBRID_RERANK = "hybrid_rerank"
    UNAVAILABLE = "unavailable"


ALLOWLISTED_REASON_CODES = frozenset({
    "user_requested_deep",
    "user_preference_auto",
    "pre_fast",
    "pre_deep",
    "pre_uncertain",
    "post_sufficient",
    "post_insufficient",
    "post_uncertain",
    "multi_facet",
    "cross_source_intent",
    "comparison_intent",
    "causality_intent",
    "contradiction_intent",
    "temporal_change_intent",
    "multi_part_query",
    "verification_requested",
    "insufficient_structure_signal",
    "missing_facets",
    "missing_obligations",
    "low_evidence_coverage",
    "insufficient_source_diversity",
    "insufficient_candidates",
    "ranking_ambiguous",
    "retrieval_report_incomplete",
    "reranker_backend_unavailable",
    "reranker_backend_timeout",
    "reranker_backend_failed",
    "reranker_timeout",
    "reranker_oom",
    "circuit_breaker_open",
    "reranker_circuit_open",
    "structured_excel_handled",
    "structured_excel_bypass",
    "invalid_preference_fallback",
})


@dataclass(frozen=True)
class AdaptiveRetrievalPolicy:
    """Immutable, versioned settings used to reproduce a routing decision."""

    version: str = "adaptive-reranking-v1"
    enabled: bool = False
    uncertain_escalates: bool = True
    min_evidence_coverage: float = 0.35
    min_distinct_sources_by_intent: Mapping[str, int] = field(
        default_factory=lambda: {
            "compare_change": 2,
            "cross_source": 2,
            "multi_doc": 2,
        }
    )
    minimum_candidate_count: int = 3
    rerank_limit: int = 30
    deep_timeout_ms: int = 300000
    circuit_breaker_failures: int = 3
    circuit_breaker_cooldown_ms: int = 30000


@dataclass(frozen=True)
class PreRetrievalDecision:
    classification: PreDecision
    reason_codes: Tuple[str, ...]
    policy_version: str
    facet_count: int = 0
    obligation_count: int = 0


@dataclass(frozen=True)
class EvidenceSufficiencyAssessment:
    classification: PostDecision
    reason_codes: Tuple[str, ...]
    evidence_coverage: float = 0.0
    distinct_source_count: int = 0
    candidate_count: int = 0
    missing_facet_count: int = 0
    missing_obligation_count: int = 0
    diversity_limited_count: int = 0


@dataclass(frozen=True)
class RoutingDecision:
    user_preference: SearchPreferenceMode
    pre_decision: PreDecision
    post_decision: PostDecision
    requested_path: RetrievalPath
    effective_path: RetrievalPath
    reason_codes: Tuple[str, ...]
    reranker_requested: bool
    reranker_applied: bool
    degraded: bool
    degraded_reason: str
    policy_version: str


_COMPARISON_PATTERNS = re.compile(
    r"\b(so sánh|khác nhau|điểm khác|phân biệt|so với|đối chiếu|tương phản|sự khác biệt|nhất quán|giữa\s+.+\s+và|"
    r"compare|comparison|difference|differences|versus|vs\.?|distinguish|contrast|between\s+.+\s+and)\b",
    re.IGNORECASE,
)

_CAUSALITY_PATTERNS = re.compile(
    r"\b(nguyên nhân|lý do|tại sao|do đâu|hậu quả|vì sao|dẫn đến|giải thích|"
    r"cause|causes|reason|reasons|why|explain why|consequence|leads? to)\b",
    re.IGNORECASE,
)

_CROSS_SOURCE_PATTERNS = re.compile(
    r"\b(tổng hợp|nhiều nguồn|tất cả các tài liệu|toàn bộ|toàn diện|xuyên suốt|các nguồn|chéo|liên văn bản|"
    r"synthesize|synthesis|cross-source|cross source|all sources|all documents|comprehensive)\b",
    re.IGNORECASE,
)

_CONTRADICTION_PATTERNS = re.compile(
    r"\b(mâu thuẫn|bất đồng|trái ngược|xung đột|không khớp|chênh lệch|"
    r"conflict|contradiction|discrepancy|inconsistent|mismatch)\b",
    re.IGNORECASE,
)

_TEMPORAL_PATTERNS = re.compile(
    r"\b(thay đổi theo thời gian|qua các phiên bản|lịch sử thay đổi|tiến trình|các giai đoạn|từ trước đến nay|"
    r"evolution|timeline|history of changes|changes over time|across versions|progression)\b",
    re.IGNORECASE,
)

_MULTI_PART_PATTERNS = re.compile(
    r"(,\s*(và|đồng thời|kèm theo|cũng như|nêu|dẫn nguồn)\b|\bvừa\b.+\bvừa\b|\bhãy\b.+\bvà\b|\bđồng thời\b|\bkèm phương án\b)",
    re.IGNORECASE,
)

_ANALYTICAL_PATTERNS = re.compile(
    r"\b(phân tích|đánh giá tác động|chiến lược|mô hình định giá|tiêu chí nghiệm thu|kiểm thử thâm nhập|phân tầng lưu trữ|"
    r"root cause|deep dive|trade-offs?|impact analysis|architecture evaluation)\b",
    re.IGNORECASE,
)

_AMBIGUOUS_PATTERNS = re.compile(
    r"\b(tồn đọng|chưa rõ|thế nào|áp dụng|hôm qua|số 01|hoàn thành|của ai|thực hiện|kiểm tra|mơ hồ|không rõ|unclear|ambiguous)\b",
    re.IGNORECASE,
)






def pre_retrieval_gate(
    query_plan: RetrievalQueryPlan,
    user_preference: str | SearchPreferenceMode = SearchPreferenceMode.AUTO,
    policy: Optional[AdaptiveRetrievalPolicy] = None,
) -> PreRetrievalDecision:
    """Classify query intent before retrieval using safe, local deterministic structural rules."""
    active_policy = policy or AdaptiveRetrievalPolicy()
    pref_str = str(getattr(user_preference, "value", user_preference)).casefold()

    facet_count = len(getattr(query_plan, "facet_ids", ()))
    obligation_count = len(getattr(query_plan, "required_obligations", ()))

    if pref_str == "deep":
        return PreRetrievalDecision(
            classification=PreDecision.DEEP,
            reason_codes=("user_requested_deep",),
            policy_version=active_policy.version,
            facet_count=facet_count,
            obligation_count=obligation_count,
        )

    q_text = str(
        getattr(query_plan, "original_query", "")
        or getattr(query_plan, "query", "")
        or ""
    ).strip()
    intent = str(getattr(query_plan, "intent_category", "") or "").casefold()

    # Isolate routing from external/cloud query expansions:
    # Always evaluate local deterministic signals from question text.
    if q_text:
        from aios_habit.rag_v2.query_planning import coerce_query_plan
        det_plan = coerce_query_plan(q_text)
        effective_intent = det_plan.intent_category.casefold()
        effective_facet_count = len(det_plan.facet_ids)
        effective_obligation_count = len(det_plan.required_obligations)
    else:
        effective_intent = intent
        effective_facet_count = facet_count
        effective_obligation_count = obligation_count

    # "Hoạt động như thế nào?" is a normal operational-procedure question,
    # not an ambiguity signal by itself.  Auto retrieves first; Deep remains
    # available explicitly and when evidence is truly insufficient.
    if (
        effective_intent == "procedure"
        and not _ANALYTICAL_PATTERNS.search(q_text)
        and not _CROSS_SOURCE_PATTERNS.search(q_text)
        and not _COMPARISON_PATTERNS.search(q_text)
        and not _CAUSALITY_PATTERNS.search(q_text)
    ):
        return PreRetrievalDecision(
            classification=PreDecision.FAST,
            reason_codes=("pre_fast",),
            policy_version=active_policy.version,
            facet_count=effective_facet_count,
            obligation_count=effective_obligation_count,
        )

    if (
        intent in {"ambiguous_lookup", "uncertain", "unclear"}
        or effective_intent in {"ambiguous_lookup", "uncertain", "unclear"}
        or _AMBIGUOUS_PATTERNS.search(q_text)
    ):
        return PreRetrievalDecision(
            classification=PreDecision.UNCERTAIN,
            reason_codes=("pre_uncertain",),
            policy_version=active_policy.version,
            facet_count=effective_facet_count,
            obligation_count=effective_obligation_count,
        )

    reasons: list[str] = []

    # 1. Comparison check
    if effective_intent in {"compare_change", "comparison"} or _COMPARISON_PATTERNS.search(q_text):
        reasons.append("comparison_intent")

    # 2. Causality / Explanation check
    if effective_intent in {"diagnosis", "root_cause"} or _CAUSALITY_PATTERNS.search(q_text):
        reasons.append("causality_intent")

    # 3. Cross-source / Multi-source check
    if (
        effective_intent in {"cross_source", "multi_doc"}
        or _CROSS_SOURCE_PATTERNS.search(q_text)
    ):
        reasons.append("cross_source_intent")


    # 4. Contradiction check
    if _CONTRADICTION_PATTERNS.search(q_text):
        reasons.append("contradiction_intent")

    # 5. Temporal change check
    if _TEMPORAL_PATTERNS.search(q_text):
        reasons.append("temporal_change_intent")

    # 6. Multi-part / Complex conjunction check
    if _MULTI_PART_PATTERNS.search(q_text) or q_text.count("?") >= 2:
        reasons.append("multi_part_query")

    # 7. Analytical / Deep dive patterns
    if _ANALYTICAL_PATTERNS.search(q_text):
        reasons.append("verification_requested")

    # 8. Facets and obligations
    if effective_facet_count >= 2:
        reasons.append("multi_facet")

    if effective_obligation_count > 1 or effective_intent in {"procedure", "citation_provenance", "actionable_output"}:
        reasons.append("verification_requested")

    if reasons:
        return PreRetrievalDecision(
            classification=PreDecision.DEEP,
            reason_codes=tuple(dict.fromkeys(reasons)),
            policy_version=active_policy.version,
            facet_count=effective_facet_count,
            obligation_count=effective_obligation_count,
        )

    # 9. Ambiguity / Under-specified check: Very short queries (<= 3 words) or vague phrasing are uncertain
    words = q_text.split()
    if (len(words) <= 3 and len(words) > 0) or _AMBIGUOUS_PATTERNS.search(q_text):
        return PreRetrievalDecision(
            classification=PreDecision.UNCERTAIN,
            reason_codes=("pre_uncertain",),
            policy_version=active_policy.version,
            facet_count=effective_facet_count,
            obligation_count=effective_obligation_count,
        )

    # Standard straightforward queries without complex triggers default to Fast
    return PreRetrievalDecision(
        classification=PreDecision.FAST,
        reason_codes=("pre_fast",),
        policy_version=active_policy.version,
        facet_count=effective_facet_count,
        obligation_count=effective_obligation_count,
    )





def decide_initial_route(
    pre_decision: PreRetrievalDecision,
    user_preference: str | SearchPreferenceMode = SearchPreferenceMode.AUTO,
    policy: Optional[AdaptiveRetrievalPolicy] = None,
) -> RoutingDecision:
    """Determine initial execution path from pre-gate decision."""
    active_policy = policy or AdaptiveRetrievalPolicy()
    pref_enum = (
        SearchPreferenceMode.DEEP
        if str(getattr(user_preference, "value", user_preference)).casefold() == "deep"
        else SearchPreferenceMode.AUTO
    )

    if (
        pre_decision.classification == PreDecision.DEEP
        or (active_policy.uncertain_escalates and pre_decision.classification == PreDecision.UNCERTAIN)
    ):
        requested_path = RetrievalPath.HYBRID_RERANK
        rerank_requested = True
    else:
        requested_path = RetrievalPath.HYBRID
        rerank_requested = False

    return RoutingDecision(
        user_preference=pref_enum,
        pre_decision=pre_decision.classification,
        post_decision=PostDecision.NOT_RUN,
        requested_path=requested_path,
        effective_path=requested_path,
        reason_codes=pre_decision.reason_codes,
        reranker_requested=rerank_requested,
        reranker_applied=False,
        degraded=False,
        degraded_reason="",
        policy_version=active_policy.version,
    )


def post_retrieval_gate(
    summary: SearchSummary,
    query_plan: RetrievalQueryPlan,
    distinct_source_count: int,
    policy: Optional[AdaptiveRetrievalPolicy] = None,
) -> EvidenceSufficiencyAssessment:
    """Assess whether fast Hybrid retrieval returned sufficient grounded evidence using real signals."""
    active_policy = policy or AdaptiveRetrievalPolicy()
    reasons: list[str] = []

    missing_facets = tuple(getattr(summary, "missing_facet_ids", ()))
    missing_obligations = tuple(getattr(summary, "missing_obligation_ids", ()))
    term_coverage = float(getattr(summary, "evidence_set_term_coverage", 0.0) or 0.0)
    candidate_count = int(getattr(summary, "candidate_count", 0))

    if missing_facets:
        reasons.append("missing_facets")
    if missing_obligations:
        reasons.append("missing_obligations")
    if term_coverage < active_policy.min_evidence_coverage:
        reasons.append("low_evidence_coverage")
    if candidate_count < active_policy.minimum_candidate_count:
        reasons.append("insufficient_candidates")

    intent = query_plan.intent_category or ""
    required_sources = active_policy.min_distinct_sources_by_intent.get(intent, 1)
    if distinct_source_count < required_sources:
        reasons.append("insufficient_source_diversity")

    if reasons:
        return EvidenceSufficiencyAssessment(
            classification=PostDecision.INSUFFICIENT,
            reason_codes=tuple(dict.fromkeys(reasons)),
            evidence_coverage=term_coverage,
            distinct_source_count=distinct_source_count,
            candidate_count=candidate_count,
            missing_facet_count=len(missing_facets),
            missing_obligation_count=len(missing_obligations),
            diversity_limited_count=max(0, required_sources - distinct_source_count),
        )

    return EvidenceSufficiencyAssessment(
        classification=PostDecision.SUFFICIENT,
        reason_codes=("post_sufficient",),
        evidence_coverage=term_coverage,
        distinct_source_count=distinct_source_count,
        candidate_count=candidate_count,
        missing_facet_count=0,
        missing_obligation_count=0,
        diversity_limited_count=0,
    )


def decide_final_route(
    initial_routing: RoutingDecision,
    post_assessment: EvidenceSufficiencyAssessment,
    reranker_applied: bool,
    effective_path: RetrievalPath | str,
    degraded: bool = False,
    degraded_reason: str = "",
    policy: Optional[AdaptiveRetrievalPolicy] = None,
) -> RoutingDecision:
    """Build the final immutable routing decision with merged reason codes."""
    active_policy = policy or AdaptiveRetrievalPolicy()
    all_reasons = list(initial_routing.reason_codes)
    for code in post_assessment.reason_codes:
        if code not in all_reasons:
            all_reasons.append(code)

    path_enum = (
        effective_path
        if isinstance(effective_path, RetrievalPath)
        else RetrievalPath(str(effective_path))
    )

    safe_degraded_reason = degraded_reason if degraded_reason in ALLOWLISTED_REASON_CODES else (
        "reranker_backend_failed" if degraded else ""
    )

    return RoutingDecision(
        user_preference=initial_routing.user_preference,
        pre_decision=initial_routing.pre_decision,
        post_decision=post_assessment.classification,
        requested_path=initial_routing.requested_path,
        effective_path=path_enum,
        reason_codes=tuple(all_reasons),
        reranker_requested=initial_routing.reranker_requested,
        reranker_applied=reranker_applied,
        degraded=degraded,
        degraded_reason=safe_degraded_reason,
        policy_version=active_policy.version,
    )


class CircuitBreaker:
    """Safeguard against repeated reranker worker crashes/timeouts to protect system RAM."""

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.last_failure_time = 0.0

    def record_success(self) -> None:
        self.failure_count = 0

    def record_failure(self) -> None:
        import time
        self.failure_count += 1
        self.last_failure_time = time.time()

    def is_open(self) -> bool:
        import time
        if self.failure_count >= self.failure_threshold:
            if time.time() - self.last_failure_time > self.cooldown_seconds:
                self.failure_count = 0
                return False
            return True
        return False
