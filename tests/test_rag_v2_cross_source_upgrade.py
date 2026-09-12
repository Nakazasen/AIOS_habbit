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
    assert plan.target_retrieval_limit == 15
    assert plan.target_per_document_limit == 5


def test_two_clause_query_retrieves_both_facet_documents(tmp_path):
    from tests.test_rag_v2_index import make_ranked_chunk

    chunks = [
        make_ranked_chunk(
            "flow",
            "doc-flow",
            "Data flows through the interface table to connected systems.",
            source_name="flow.txt",
            source_path="/workspace/flow.txt",
        ),
        make_ranked_chunk(
            "verify",
            "doc-verify",
            "Operators verify failures on the status screen.",
            source_name="verify.txt",
            source_path="/workspace/verify.txt",
        ),
        make_ranked_chunk(
            "noise",
            "doc-noise",
            "Unrelated archive of leftover notes.",
            source_name="noise.txt",
            source_path="/workspace/noise.txt",
        ),
    ]
    query = (
        "How does data flow between connected systems, and where should an operator verify failures?"
    )
    plan = identity_query_plan(query)
    with LocalChunkIndex(tmp_path / "index.sqlite") as index:
        index.upsert_chunks(chunks)
        response = index.search_with_summary(plan, limit=2)

    assert plan.intent_category == "cross_source_synthesis"
    assert {result.chunk_id for result in response.results} >= {"flow", "verify"}
    assert "facet_1" in response.summary.covered_facet_ids
    assert "facet_2" in response.summary.covered_facet_ids
    assert "facet_1" not in response.summary.missing_facet_ids
    assert "facet_2" not in response.summary.missing_facet_ids
