import json
from pathlib import Path
import pytest

from aios_habit.rag_v2.adaptive_retrieval import (
    AdaptiveRetrievalPolicy,
    EvidenceSufficiencyAssessment,
    PostDecision,
    PreDecision,
    PreRetrievalDecision,
    RetrievalPath,
    RoutingDecision,
    SearchPreferenceMode,
    decide_final_route,
    decide_initial_route,
    post_retrieval_gate,
    pre_retrieval_gate,
)
from aios_habit.rag_v2.index import SearchSummary
from aios_habit.rag_v2.query_planning import RetrievalQueryPlan, RetrievalQueryVariant


def _plan(
    raw_query: str = "test query",
    intent_category: str = "factual",
    facet_ids: tuple[str, ...] = ("query",),
    obligations: tuple[str, ...] = ("query",),
) -> RetrievalQueryPlan:
    variants = tuple(
        RetrievalQueryVariant(
            text=raw_query,
            variant_id=f"var_{fid}",
            facet_id=fid,
        )
        for fid in facet_ids
    )
    return RetrievalQueryPlan(
        original_query=raw_query,
        variants=variants,
        content_terms=tuple(raw_query.lower().split()),
        intent_category=intent_category,
        required_obligations=obligations,
    )


def test_pre_gate_user_deep_always_forces_deep():
    policy = AdaptiveRetrievalPolicy()
    plan = _plan("đơn giản", "factual")
    decision = pre_retrieval_gate(plan, user_preference="deep", policy=policy)
    assert decision.classification == PreDecision.DEEP
    assert "user_requested_deep" in decision.reason_codes


def test_pre_gate_multi_facet_routes_deep():
    policy = AdaptiveRetrievalPolicy()
    plan = _plan(
        "so sánh mục A và mục B",
        intent_category="compare_change",
        facet_ids=("f1", "f2"),
    )
    decision = pre_retrieval_gate(plan, user_preference="auto", policy=policy)
    assert decision.classification == PreDecision.DEEP
    assert "comparison_intent" in decision.reason_codes or "multi_facet" in decision.reason_codes


def test_pre_gate_simple_query_routes_fast():
    policy = AdaptiveRetrievalPolicy()
    plan = _plan(
        "quy định nghỉ phép",
        intent_category="factual",
        facet_ids=("f1",),
    )
    decision = pre_retrieval_gate(plan, user_preference="auto", policy=policy)
    assert decision.classification == PreDecision.FAST
    assert "pre_fast" in decision.reason_codes


def test_pre_gate_operational_procedure_routes_fast_in_auto_mode():
    policy = AdaptiveRetrievalPolicy(uncertain_escalates=True)
    plan = _plan(
        "Chế độ Manual Matecon ACR/CTU hoạt động như thế nào?",
        intent_category="procedure",
    )

    decision = pre_retrieval_gate(plan, user_preference="auto", policy=policy)

    assert decision.classification == PreDecision.FAST
    assert decision.reason_codes == ("pre_fast",)


def test_pre_gate_uncertain_escalates_to_deep_in_initial_routing():
    policy = AdaptiveRetrievalPolicy(uncertain_escalates=True)
    plan = _plan("mơ hồ không rõ nghĩa", intent_category="ambiguous_lookup")
    pre_dec = pre_retrieval_gate(plan, user_preference="auto", policy=policy)
    assert pre_dec.classification == PreDecision.UNCERTAIN
    assert "pre_uncertain" in pre_dec.reason_codes

    routing = decide_initial_route(pre_dec, user_preference="auto", policy=policy)
    assert routing.requested_path == RetrievalPath.HYBRID_RERANK
    assert routing.reranker_requested is True


def test_post_gate_detects_missing_facets_and_low_coverage():
    policy = AdaptiveRetrievalPolicy(min_evidence_coverage=0.4, minimum_candidate_count=2)
    plan = _plan(
        "chính sách bảo hiểm",
        facet_ids=("f1", "f2"),
    )
    summary = SearchSummary(
        query="chính sách bảo hiểm",
        indexed_chunk_count=10,
        eligible_chunk_count=10,
        candidate_count=5,
        returned_count=3,
        evidence_set_term_coverage=0.2,
        planned_facet_ids=("f1", "f2"),
        covered_facet_ids=("f1",),
        missing_facet_ids=("f2",),
    )
    assessment = post_retrieval_gate(summary, plan, distinct_source_count=1, policy=policy)
    assert assessment.classification == PostDecision.INSUFFICIENT
    assert "missing_facets" in assessment.reason_codes or "low_evidence_coverage" in assessment.reason_codes


def test_post_gate_passes_when_evidence_sufficient():
    policy = AdaptiveRetrievalPolicy(min_evidence_coverage=0.3, minimum_candidate_count=2)
    plan = _plan("quy trình", facet_ids=("f1",))
    summary = SearchSummary(
        query="quy trình",
        indexed_chunk_count=10,
        eligible_chunk_count=10,
        candidate_count=4,
        returned_count=3,
        evidence_set_term_coverage=0.8,
        planned_facet_ids=("f1",),
        covered_facet_ids=("f1",),
        missing_facet_ids=(),
    )
    assessment = post_retrieval_gate(summary, plan, distinct_source_count=1, policy=policy)
    assert assessment.classification == PostDecision.SUFFICIENT
    assert "post_sufficient" in assessment.reason_codes


def test_routing_distribution_over_test_cases_is_balanced():
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "adaptive_routing_cases.json"
    with fixture_path.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    policy = AdaptiveRetrievalPolicy()
    deep_count = 0
    fast_count = 0

    for case in cases:
        user_pref = case.get("search_preference", "auto")
        category = case.get("category", "simple")
        intent_cat = "compare_change" if category == "hard" else ("ambiguous_lookup" if category == "ambiguous" else "factual")
        plan = _plan(case["query"], intent_category=intent_cat)
        pre_dec = pre_retrieval_gate(plan, user_preference=user_pref, policy=policy)
        routing = decide_initial_route(pre_dec, user_preference=user_pref, policy=policy)

        if routing.reranker_requested:
            deep_count += 1
        else:
            fast_count += 1

    total = len(cases)
    assert total == 60
    assert fast_count >= 5, f"Too few fast routes: {fast_count}/{total}"
    assert deep_count >= 20, f"Too few deep routes: {deep_count}/{total}"


def test_regression_comparison_causality_multipart_query_routes_deep():
    from aios_habit.rag_v2.query_planning import coerce_query_plan
    query = "Hãy so sánh điểm khác nhau giữa kế hoạch A và B, nêu nguyên nhân và dẫn nguồn"
    plan = coerce_query_plan(query)
    policy = AdaptiveRetrievalPolicy()
    decision = pre_retrieval_gate(plan, user_preference="auto", policy=policy)

    assert decision.classification == PreDecision.DEEP
    assert "comparison_intent" in decision.reason_codes
    assert "causality_intent" in decision.reason_codes
    assert "multi_part_query" in decision.reason_codes


def test_privacy_allowlisted_reason_codes():
    from aios_habit.rag_v2.adaptive_retrieval import ALLOWLISTED_REASON_CODES
    # Ensure no raw paths, URLs, or exception traces in allowlist
    for code in ALLOWLISTED_REASON_CODES:
        assert "/" not in code
        assert "\\" not in code
        assert ":" not in code
        assert " " not in code
        assert code.islower()


def test_regression_pre_routing_decision_invariant_to_cloud_expansion():
    """Verify that cloud/external query expansion NEVER alters pre-retrieval routing decisions."""
    from aios_habit.rag_v2.query_planning import build_query_plan, coerce_query_plan

    test_queries = [
        ("Quy trình xin nghỉ phép", "auto"),
        ("Địa chỉ trụ sở chính Hà Nội", "auto"),
        ("Phân tích so sánh chi tiết giữa cơ chế hybrid retrieval và vector database", "auto"),
        ("Tổng hợp các điều khoản miễn trừ trách nhiệm hợp đồng", "auto"),
        ("Mơ hồ", "auto"),
        ("Quy định chung", "deep"),
    ]

    mock_expansions = [
        {
            "variants": [
                {"text": "leave request policy workflow", "language_hint": "en"},
                {"text": "đơn xin nghỉ phép nhân sự", "language_hint": "vi"},
            ],
            "intent_category": "cross_source_synthesis",
            "required_obligations": ["facet_a", "facet_b"],
        },
        {
            "variants": [
                {"text": "malicious variant attempting to force deep", "language_hint": "en"},
            ],
            "intent_category": "compare_change",
            "required_obligations": ["injected_obligation"],
        },
    ]

    policy = AdaptiveRetrievalPolicy()

    for q, pref in test_queries:
        plan_deterministic = coerce_query_plan(q)
        dec_deterministic = pre_retrieval_gate(plan_deterministic, user_preference=pref, policy=policy)

        for expansion in mock_expansions:
            plan_expanded = build_query_plan(q, expansion)
            dec_expanded = pre_retrieval_gate(plan_expanded, user_preference=pref, policy=policy)

            # Routing decision MUST be 100% identical
            assert dec_expanded.classification == dec_deterministic.classification, (
                f"Classification mismatch for query '{q}' with expansion: "
                f"{dec_expanded.classification} != {dec_deterministic.classification}"
            )
            assert set(dec_expanded.reason_codes) == set(dec_deterministic.reason_codes), (
                f"Reason codes mismatch for query '{q}' with expansion: "
                f"{dec_expanded.reason_codes} != {dec_deterministic.reason_codes}"
            )


def test_degraded_reason_sanitizer_masks_secrets_and_paths():
    """Verify that malicious worker errors never leak raw exception text, paths, or secrets."""
    from aios_habit.workspace_chat_rag_v2_adapter import _sanitize_degraded_reason

    malicious_inputs = [
        "C:\\Users\\Admin\\.ssh\\id_rsa: Permission Denied",
        "/etc/shadow: No such file or directory",
        "RuntimeError: failed with API key sk-proj-1234567890abcdef",
        "Traceback (most recent call last):\n  File 'internal.py', line 99",
        "unknown_custom_crash_reason",
        "<script>alert(1)</script>",
    ]

    for malicious in malicious_inputs:
        sanitized = _sanitize_degraded_reason(malicious)
        assert sanitized == "reranker_backend_failed"
        assert "ssh" not in sanitized
        assert "shadow" not in sanitized
        assert "sk-proj" not in sanitized
        assert "Traceback" not in sanitized

    # Allowed safe reasons must pass through intact
    assert _sanitize_degraded_reason("reranker_oom") == "reranker_oom"
    assert _sanitize_degraded_reason("reranker_backend_timeout") == "reranker_backend_timeout"
    assert _sanitize_degraded_reason("reranker_backend_unavailable") == "reranker_backend_unavailable"
