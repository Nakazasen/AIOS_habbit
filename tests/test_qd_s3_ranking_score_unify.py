"""Unit tests for ticket DESKTOP-QD-S3-RANKING-SCORE-UNIFY-HOME (QD-01, QD-07, QD-08, QD-12)."""
import pytest
from dataclasses import replace

from aios_habit.rag_v2.query_planning import (
    HybridRankingConfig,
    RetrievalQueryPlan,
    build_query_plan,
    determine_query_channel_ranking_config,
    identity_query_plan,
)
from aios_habit.rag_v2.evidence import (
    EvidenceAnswerMode,
    EvidenceConfidence,
    EvidenceItem,
    EvidencePack,
    EvidencePackConfig,
    build_evidence_pack,
)
from aios_habit.rag_v2.index import (
    SearchResponse,
    SearchResult,
    SearchSummary,
    _has_maintenance_date_or_column_range,
)
from aios_habit.rag_v2.pipeline import (
    _balance_lsu_machine_series,
    _rerank_bilingual_tri_thuc,
)
from aios_habit.rag_v2.synthesis import (
    _claim_value_score,
    _compose_grounded_claims,
)


def _make_search_result(
    chunk_id: str,
    doc_id: str,
    text: str,
    score: float,
    *,
    source_name: str = "doc.txt",
    signals: dict | None = None,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=doc_id,
        source_name=source_name,
        source_path=f"/{source_name}",
        file_type="txt",
        text=text,
        score=score,
        ranking_signals=signals or {},
        matched_terms=(),
        term_coverage=1.0,
        matched_query_facets=("query",),
        matched_obligations=(),
        matched_query_variant_ids=("v1",),
        matched_target_equivalent_variant_ids=(),
        metadata={},
        privacy_labels=(),
    )


# ---------------------------------------------------------------------------
# QD-07: Authoritative Dynamic Channel Ranking Configuration
# ---------------------------------------------------------------------------

def test_qd07_determine_query_channel_ranking_config():
    """Verify single source of truth for channel weight overrides."""
    # Date + maintenance pattern -> weights (0.2, 3.0, 1.5)
    cfg_date = determine_query_channel_ranking_config("Bảo dưỡng định kỳ 14/2 thay thế linh kiện")
    assert cfg_date is not None
    assert cfg_date.lexical_weight == 0.2
    assert cfg_date.dense_weight == 3.0
    assert cfg_date.sparse_weight == 1.5

    # Column range pattern -> weights (0.05, 2.0, 3.5)
    cfg_col = determine_query_channel_ranking_config("Kiểm tra dữ liệu từ cột -8 đến -3")
    assert cfg_col is not None
    assert cfg_col.lexical_weight == 0.05
    assert cfg_col.dense_weight == 2.0
    assert cfg_col.sparse_weight == 3.5

    # Unrelated query -> None
    cfg_none = determine_query_channel_ranking_config("Tài liệu hướng dẫn sử dụng hệ thống")
    assert cfg_none is None


def test_qd07_delegation_in_index():
    """Verify _has_maintenance_date_or_column_range delegates cleanly."""
    assert _has_maintenance_date_or_column_range("Bảo dưỡng định kỳ 14/2 thay thế linh kiện") is True
    assert _has_maintenance_date_or_column_range("Kiểm tra dữ liệu từ cột -8 đến -3") is True
    assert _has_maintenance_date_or_column_range("Tài liệu hướng dẫn sử dụng hệ thống") is False


def test_qd07_plan_carries_ranking_config():
    """Verify RetrievalQueryPlan preserves ranking_config from planning through execution."""
    plan = build_query_plan("Bảo dưỡng định kỳ 14/2 thay thế linh kiện")
    assert plan.ranking_config is not None
    assert plan.ranking_config.dense_weight == 3.0
    assert plan.ranking_config.lexical_weight == 0.2


# ---------------------------------------------------------------------------
# QD-08: Unified Diversity Policy & Per-Document Capping
# ---------------------------------------------------------------------------

def test_qd08_evidence_pack_config_diversity_defaults():
    """Verify EvidencePackConfig unified diversity thresholds and helper methods."""
    cfg = EvidencePackConfig()
    assert cfg.per_document_limit == 3
    assert cfg.named_document_limit == 5
    assert cfg.focused_document_limit == 15
    assert cfg.synthesis_per_doc_limit == 3
    assert cfg.synthesis_named_per_doc_limit == 5

    # Helper methods
    assert cfg.effective_document_limit(is_named_doc=False, is_focused=False) == 3
    assert cfg.effective_document_limit(is_named_doc=True, is_focused=False) == 5
    assert cfg.effective_document_limit(is_named_doc=False, is_focused=True) == 15
    assert cfg.effective_synthesis_claim_limit(is_named_doc=False) == 3
    assert cfg.effective_synthesis_claim_limit(is_named_doc=True) == 5


def test_qd08_evidence_pack_retains_config():
    """Verify EvidencePack carries the configuring EvidencePackConfig."""
    plan = identity_query_plan("Test query")
    res1 = _make_search_result("c1", "d1", "Test content chunk 1", 0.9)
    resp = SearchResponse(
        results=(res1,),
        summary=SearchSummary(
            query="Test query",
            indexed_chunk_count=1,
            eligible_chunk_count=1,
            candidate_count=1,
            returned_count=1,
        ),
    )
    custom_cfg = EvidencePackConfig(per_document_limit=4, synthesis_per_doc_limit=4)
    pack = build_evidence_pack(plan, resp, config=custom_cfg)
    assert pack.config.per_document_limit == 4
    assert pack.config.synthesis_per_doc_limit == 4


def test_qd08_synthesis_per_doc_cap_allows_3_chunks_for_open_ended():
    """Verify synthesis does not prematurely truncate multi-chunk answers for open-ended queries."""
    # When query does not name doc, previous behavior capped at 1 chunk in first pass.
    # Now unified policy defaults to 3 chunks.
    plan = identity_query_plan("Các mục tham khảo số 13–16 có nominal và dung sai thế nào?")
    item1 = EvidenceItem(
        evidence_id="ev1", citation_id="cit1", citation_label="[1]", chunk_id="c1",
        document_id="doc_specs", source_name="specs.xlsx", source_path="/specs.xlsx",
        file_type="xlsx", text="Hạng mục 13 nominal 10.0, hạng mục 14 nominal 20.0",
        snippet="Hạng mục 13 nominal 10.0, hạng mục 14 nominal 20.0", score=0.85,
        rank=1, ranking_signals={}, matched_terms=(), term_coverage=0.9, privacy_labels=(),
        matched_query_facets=("query",), matched_obligations=(),
        matched_query_variant_ids=("v1",), matched_target_equivalent_variant_ids=(),
    )
    item2 = EvidenceItem(
        evidence_id="ev2", citation_id="cit2", citation_label="[2]", chunk_id="c2",
        document_id="doc_specs", source_name="specs.xlsx", source_path="/specs.xlsx",
        file_type="xlsx", text="Hạng mục 15 nominal 30.0, hạng mục 16 nominal 40.0",
        snippet="Hạng mục 15 nominal 30.0, hạng mục 16 nominal 40.0", score=0.80,
        rank=2, ranking_signals={}, matched_terms=(), term_coverage=0.8, privacy_labels=(),
        matched_query_facets=("query",), matched_obligations=(),
        matched_query_variant_ids=("v1",), matched_target_equivalent_variant_ids=(),
    )
    pack = EvidencePack(
        pack_id="pack_test", query="Các mục tham khảo số 13–16 có nominal và dung sai thế nào?",
        items=(item1, item2), confidence=EvidenceConfidence.HIGH,
        privacy_summary=None, insufficiency_reasons=(), hard_insufficiency_reasons=(),
        soft_warning_reasons=(), answer_mode=EvidenceAnswerMode.ANSWER,
        retrieval_summary=SearchSummary(query="test", indexed_chunk_count=2, eligible_chunk_count=2, candidate_count=2, returned_count=2),
        coverage_map=(), obligation_coverage_map=(), source_count=1, document_count=1,
        item_count=2, top_score=0.85, best_term_coverage=0.9, final_evidence_term_coverage=0.9,
        semantic_support_score=0.85, semantic_support_used=True, relevance_gate_basis="dense",
        relevance_telemetry=None, supported_obligation_count=0, planned_obligation_count=0,
        created_at="2026-10-18T00:00:00",
    )
    claims = _compose_grounded_claims(pack, answer_shape="table", max_claims=5)
    # Both chunks from doc_specs should now be included in claims
    assert len(claims) == 2
    claim_texts = " ".join(c.text for c in claims)
    assert "Hạng mục 13" in claim_texts
    assert "Hạng mục 15" in claim_texts


# ---------------------------------------------------------------------------
# QD-12: Retrieval Score Integration into Claim Value Scoring
# ---------------------------------------------------------------------------

def test_qd12_claim_value_score_incorporates_retrieval_score():
    """Verify retrieval confidence score acts as a deterministic priority weight."""
    item_high = EvidenceItem(
        evidence_id="ev_hi", citation_id="cit1", citation_label="[1]", chunk_id="c_hi",
        document_id="d1", source_name="doc.txt", source_path="/doc.txt", file_type="txt",
        text="Thông tin kỹ thuật A", snippet="Thông tin kỹ thuật A", score=0.9123,
        rank=1, ranking_signals={}, matched_terms=(), term_coverage=0.5, privacy_labels=(),
        matched_query_facets=(), matched_obligations=(),
        matched_query_variant_ids=(), matched_target_equivalent_variant_ids=(),
    )
    item_low = EvidenceItem(
        evidence_id="ev_lo", citation_id="cit2", citation_label="[2]", chunk_id="c_lo",
        document_id="d1", source_name="doc.txt", source_path="/doc.txt", file_type="txt",
        text="Thông tin kỹ thuật A", snippet="Thông tin kỹ thuật A", score=0.4567,
        rank=2, ranking_signals={}, matched_terms=(), term_coverage=0.5, privacy_labels=(),
        matched_query_facets=(), matched_obligations=(),
        matched_query_variant_ids=(), matched_target_equivalent_variant_ids=(),
    )
    q = "Thông tin kỹ thuật"
    q_terms = {"thông", "tin", "kỹ", "thuật"}

    score_hi = _claim_value_score(item_high, item_high.text, q, q_terms)
    score_lo = _claim_value_score(item_low, item_low.text, q, q_terms)

    # Retrieval score sits at index 9 (before term overlap count at index 10)
    assert score_hi[9] == 0.9123
    assert score_lo[9] == 0.4567
    assert score_hi > score_lo


# ---------------------------------------------------------------------------
# QD-01: Normalized Bounded Ranking & Disambiguation
# ---------------------------------------------------------------------------

def test_qd01_bilingual_rerank_bounded():
    """Verify bilingual boost is bounded in [0, 1] scale without massive additive jumps."""
    plan = identity_query_plan("Quy định lưu kho thùng ORICON 10kg")
    r1 = _make_search_result("c1", "doc_bi", "Văn bản tiếng Nhật 保管ルール", 0.50, source_name="doc_bi.txt")
    r2 = _make_search_result("c2", "doc_bi", "Quy định lưu kho thùng ORICON 10kg đặt tầng 1", 0.40, source_name="doc_bi.txt")
    resp = SearchResponse(
        results=(r1, r2),
        summary=SearchSummary(query="test", indexed_chunk_count=2, eligible_chunk_count=2, candidate_count=2, returned_count=2),
    )
    reranked = _rerank_bilingual_tri_thuc(plan, resp, is_tri_thuc=True)
    # The Vietnamese chunk receives a bounded boost <= 0.40 and score is capped at 1.0
    top = reranked.results[0]
    assert top.chunk_id == "c2"
    assert 0.0 < top.ranking_signals["bilingual_vi_boost"] <= 0.40
    assert top.score <= 1.0
    assert top.score > r1.score


def test_qd01_lsu_balance_threshold_normalized():
    """Verify _balance_lsu_machine_series uses 0.02 threshold on normalized scale."""
    plan = identity_query_plan("Quy trình cân chỉnh máy")
    r_sirius = _make_search_result("s1", "sirius_doc", "Sirius doc", 0.045, source_name="Sirius2.xlsx")
    r_iris_close = _make_search_result(
        "i1", "iris_doc", "Iris doc", 0.038, source_name="Iris.xlsx",
        signals={"dense_channel_rank": 3, "dense_cosine": 0.60},
    )
    resp = SearchResponse(
        results=(r_sirius, r_iris_close),
        summary=SearchSummary(query="test", indexed_chunk_count=2, eligible_chunk_count=2, candidate_count=2, returned_count=2),
    )
    # score diff = 0.007 < 0.02 -> balancing evaluates candidates
    balanced = _balance_lsu_machine_series(plan, resp, is_lsu=True)
    assert len(balanced.results) == 2
