"""Tests for RAG v2 Cross-Source Multi-Document Synthesis Upgrades."""
import pytest
from aios_habit.rag_v2.query_planning import (
    build_query_plan,
    identity_query_plan,
    RetrievalQueryPlan,
)
from aios_habit.rag_v2.index import LocalChunkIndex, SearchOptions, SearchResult
from aios_habit.rag_v2.evidence import (
    build_evidence_pack,
    EvidencePackConfig,
)


def test_cross_source_plan_with_expansion():
    """Verify that build_query_plan properly configures cross_source_synthesis intent."""
    q = "How does the warehouse management (WMS) system connect to production management?"
    plan = build_query_plan(
        q,
        expansion={
            "intent_category": "cross_source_synthesis",
            "required_obligations": ["query", "synthesis"],
            "variants": [
                {"text": "WMS InterStock supply to production", "origin": "facet"},
                {"text": "Production management MOM Opcenter link", "origin": "facet"},
            ],
        },
    )
    assert plan.intent_category == "cross_source_synthesis"
    assert plan.target_retrieval_limit == 25
    assert plan.target_per_document_limit == 5
    assert "synthesis" in plan.required_obligations
    assert len(plan.variants) == 3


def test_standard_identity_plan_defaults():
    """Verify standard identity plan defaults to general intent and standard limits."""
    q = "Check status"
    plan = identity_query_plan(q)
    assert plan.intent_category == "general"
    assert plan.target_retrieval_limit == 10
    assert plan.target_per_document_limit == 3
