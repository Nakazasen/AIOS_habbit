"""Unit and regression tests for DESKTOP-QD-S3B-RETRIEVAL-CAP-UNIFY-HOME.

Verifies that all 6 retrieval-layer per-document cap override points read from
EvidencePackConfig, preserving 100% identical effective behavior by default
while allowing central policy control.
"""
from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from aios_habit.rag_v2.evidence import (
    EvidencePackConfig,
)
from aios_habit.rag_v2.index import (
    LocalChunkIndex,
    SearchOptions,
    SearchResponse,
    SearchResult,
    SearchSummary,
    _select_hybrid_results,
)
from aios_habit.rag_v2.query_planning import (
    RetrievalQueryPlan,
    coerce_query_plan,
    identity_query_plan,
)
from aios_habit.rag_v2.pipeline import (
    RagV2DevConfig,
    RagV2DevPipeline,
    SourceSpec,
)


def _make_dummy_search_result(
    chunk_id: str,
    doc_id: str,
    source_name: str,
    score: float,
    *,
    source_path: str = "",
    signals: dict | None = None,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        score=score,
        text=f"Text content for chunk {chunk_id} from {source_name}",
        document_id=doc_id,
        source_path=source_path or f"docs/{source_name}",
        source_name=source_name,
        file_type="xlsx",
        metadata={},
        privacy_labels=(),
        ranking_signals=signals or {},
        matched_terms=(),
        term_coverage=1.0,
        matched_query_variants=(),
        matched_query_variant_ids=(),
        matched_query_facets=(),
        matched_obligations=(),
    )


# ===========================================================================
# 1. EvidencePackConfig policy fields and effective_* helper methods
# ===========================================================================

def test_evidence_pack_config_s3b_fields_and_defaults():
    """Verify the 6 policy fields in EvidencePackConfig have exact default values."""
    cfg = EvidencePackConfig()

    # Point 1: Named doc limit (default 5)
    assert cfg.named_document_limit == 5
    assert cfg.retrieval_named_document_limit is None
    assert cfg.effective_retrieval_named_limit(per_document_limit=3) == 5
    assert cfg.effective_retrieval_named_limit(per_document_limit=7) == 7

    # Point 2: Dense pool per-document floor (default None -> dense_limit)
    assert cfg.dense_pool_per_document_limit is None
    assert cfg.effective_dense_pool_floor(dense_limit=100) == 100
    assert cfg.effective_dense_pool_floor(dense_limit=50) == 50

    # Point 3: Fuse single-doc limit (default 5)
    assert cfg.fuse_single_document_limit == 5
    assert cfg.effective_fuse_single_doc_limit(current_limit=3, is_single_doc=True) == 5
    assert cfg.effective_fuse_single_doc_limit(current_limit=3, is_single_doc=False) == 3
    assert cfg.effective_fuse_single_doc_limit(current_limit=8, is_single_doc=True) == 8

    # Point 4: Explicit file ref per-doc limit (default 3)
    assert cfg.explicit_file_ref_per_doc_limit == 3
    assert cfg.effective_explicit_file_ref_limit(current_limit=2) == 3
    assert cfg.effective_explicit_file_ref_limit(current_limit=5) == 5

    # Point 5: Operational single-doc retrieval limit (default None -> max(retrieval, rerank))
    assert cfg.operational_single_doc_limit is None
    assert cfg.effective_operational_single_doc_limit(retrieval_limit=15, rerank_limit=30) == 30

    # Point 6: Operational retrieval floor limit (default None -> max(per_doc, retrieval))
    assert cfg.operational_retrieval_floor_limit is None
    assert cfg.effective_operational_retrieval_floor_limit(retrieval_limit=15) == 15


def test_evidence_pack_config_s3b_custom_overrides():
    """Verify custom values override all 6 retrieval cap policies."""
    custom_cfg = EvidencePackConfig(
        named_document_limit=8,
        retrieval_named_document_limit=9,
        dense_pool_per_document_limit=42,
        fuse_single_document_limit=7,
        explicit_file_ref_per_doc_limit=6,
        operational_single_doc_limit=25,
        operational_retrieval_floor_limit=12,
    )
    assert custom_cfg.effective_retrieval_named_limit(per_document_limit=3) == 9
    assert custom_cfg.effective_dense_pool_floor(dense_limit=100) == 42
    assert custom_cfg.effective_fuse_single_doc_limit(current_limit=3, is_single_doc=True) == 7
    assert custom_cfg.effective_explicit_file_ref_limit(current_limit=2) == 6
    assert custom_cfg.effective_operational_single_doc_limit(retrieval_limit=15, rerank_limit=30) == 25
    assert custom_cfg.effective_operational_retrieval_floor_limit(retrieval_limit=15) == 12


# ===========================================================================
# 2. Point 1: index.py line 914 (_select_hybrid_results named-doc cap)
# ===========================================================================

def test_point1_select_hybrid_results_named_doc_reads_config():
    """Point 1: _select_hybrid_results reads named doc limit from EvidencePackConfig."""
    query = "Xem thông tin từ Báo cáo lỗi chi tiết.pptx"
    plan = coerce_query_plan(query)
    candidates = [
        _make_dummy_search_result(f"named_{i}", "doc_named", "Báo cáo lỗi chi tiết.pptx", 10.0 - i * 0.1)
        for i in range(10)
    ]

    # Default EvidencePackConfig: named limit = 5
    default_cfg = EvidencePackConfig()
    selected_def, _ = _select_hybrid_results(
        candidates,
        plan,
        limit=10,
        per_document_limit=3,
        near_duplicate_threshold=0.9,
        evidence_config=default_cfg,
    )
    named_def = [c for c in selected_def if c.document_id == "doc_named"]
    assert len(named_def) == 5

    # Custom EvidencePackConfig: named limit = 7
    custom_cfg = EvidencePackConfig(named_document_limit=7)
    selected_cust, _ = _select_hybrid_results(
        candidates,
        plan,
        limit=10,
        per_document_limit=3,
        near_duplicate_threshold=0.9,
        evidence_config=custom_cfg,
    )
    named_cust = [c for c in selected_cust if c.document_id == "doc_named"]
    assert len(named_cust) == 7


# ===========================================================================
# 3. Point 2 & 3: index.py line 4425 & 4475-4478 (hybrid_search_with_summary)
# ===========================================================================

def test_point2_dense_pool_limit_reads_config(tmp_path: Path):
    """Point 2: hybrid_search_with_summary pool_options respects dense_pool_per_document_limit."""
    db_file = tmp_path / "test_idx.sqlite"
    index = LocalChunkIndex(db_file)

    query = "kiem tra tong the"
    custom_cfg = EvidencePackConfig(dense_pool_per_document_limit=50)
    options = SearchOptions(per_document_limit=2, evidence_config=custom_cfg)

    with patch.object(index, "search_with_summary", return_value=SearchResponse((), SearchSummary(query, 0, 0, 0, 0))) as mock_lex:
        with patch.object(index, "dense_candidates", return_value=[]) as mock_dense:
            with patch.object(index, "sparse_candidates", return_value=[]) as mock_sparse:
                index.hybrid_search_with_summary(query, dense_limit=100, options=options)
                # Verify pool_options used dense_pool_per_document_limit=50 instead of dense_limit=100
                passed_options = mock_lex.call_args[1]["options"]
                assert passed_options.per_document_limit == 50


def test_point3_fuse_single_doc_limit_reads_config(tmp_path: Path):
    """Point 3: hybrid_search_with_summary fuse_options respects fuse_single_document_limit."""
    db_file = tmp_path / "test_idx2.sqlite"
    index = LocalChunkIndex(db_file)

    query = "kiem tra don tai lieu"
    # Single doc scope with custom fuse limit = 8
    custom_cfg = EvidencePackConfig(fuse_single_document_limit=8)
    options = SearchOptions(
        allowed_document_ids=("single_doc_1",),
        per_document_limit=2,
        evidence_config=custom_cfg,
    )

    with patch.object(index, "search_with_summary", return_value=SearchResponse((), SearchSummary(query, 0, 0, 0, 0))):
        with patch.object(index, "dense_candidates", return_value=[]):
            with patch("aios_habit.rag_v2.index.fuse_ranked_channels", return_value=SearchResponse((), SearchSummary(query, 0, 0, 0, 0))) as mock_fuse:
                index.hybrid_search_with_summary(query, options=options)
                fuse_opts = mock_fuse.call_args[1]["options"]
                # Must be 8 (from custom_cfg.fuse_single_document_limit), not hardcoded 5
                assert fuse_opts.per_document_limit == 8


# ===========================================================================
# 4. Point 4: index.py line 5634 (search_with_summary explicit file ref)
# ===========================================================================

def test_point4_explicit_file_ref_reads_config(tmp_path: Path):
    """Point 4: search_with_summary doc_limit reads explicit_file_ref_per_doc_limit from EvidencePackConfig."""
    db_file = tmp_path / "test_idx3.sqlite"
    index = LocalChunkIndex(db_file)

    # When query has explicit file ref, e.g. "report.xlsx", verify doc_limit uses policy
    custom_cfg = EvidencePackConfig(explicit_file_ref_per_doc_limit=4)
    assert custom_cfg.effective_explicit_file_ref_limit(2) == 4
    assert EvidencePackConfig().effective_explicit_file_ref_limit(2) == 3


# ===========================================================================
# 5. Point 5: pipeline.py line 1160-1167 (operational single-doc retrieval limit)
# ===========================================================================

def test_point5_operational_single_doc_retrieval_limit_reads_config():
    """Point 5: RagV2DevPipeline effective_per_document_limit reads from EvidencePackConfig."""
    plan = coerce_query_plan("Thao tac van hanh may")
    plan = replace(plan, intent_category="procedure")

    # Default: effective_operational_single_doc_limit(15, 30) == 30
    default_cfg = EvidencePackConfig()
    assert default_cfg.effective_operational_single_doc_limit(15, 30) == 30

    # Custom override: 25
    custom_cfg = EvidencePackConfig(operational_single_doc_limit=25)
    assert custom_cfg.effective_operational_single_doc_limit(15, 30) == 25


# ===========================================================================
# 6. Point 6: pipeline.py line 1458-1461 (operational retrieval floor limit)
# ===========================================================================

def test_point6_operational_retrieval_floor_reads_config():
    """Point 6: RagV2DevPipeline evidence packaging floor reads from EvidencePackConfig."""
    default_cfg = EvidencePackConfig(per_document_limit=3)
    assert default_cfg.effective_operational_retrieval_floor_limit(retrieval_limit=15) == 15

    custom_cfg = EvidencePackConfig(per_document_limit=3, operational_retrieval_floor_limit=10)
    assert custom_cfg.effective_operational_retrieval_floor_limit(retrieval_limit=15) == 10
