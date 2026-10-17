"""Regression and behavioral test suite for DESKTOP-CROSSLINGUAL-CHUNK-SELECT-FIX-HOME.

Verifies:
1. Optical LSU cross-lingual query variant generation (JA -> VI and VI -> JA).
2. Cross-lingual dense bonus in channel fusion for high semantic matches without sparse hits.
3. Vietnamese verbal/noun pairing noise tolerance ("xuất hiện hiện tượng") in synthesis.
4. Full text fragment candidate preservation in synthesis.
"""

from __future__ import annotations

import pytest

from aios_habit.rag_v2.evidence import EvidenceItem
from aios_habit.rag_v2.index import (
    HybridRankingConfig,
    SearchOptions,
    SearchResponse,
    SearchResult,
    SearchSummary,
    fuse_ranked_channels,
)
from aios_habit.rag_v2.query_planning import (
    RetrievalQueryPlan,
    RetrievalQueryVariant,
    _build_optical_lsu_crosslingual_variant,
    build_query_plan,
)
from aios_habit.rag_v2.synthesis import (
    _candidate_fragments,
    _combine_answer_value_fragments,
    _is_fragment_noise,
    _synthesis_query_terms,
)


def _make_search_result(
    chunk_id: str,
    doc_id: str,
    text: str,
    dense_cosine: float = 0.0,
    source_name: str = "doc.txt",
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        score=0.0,
        text=text,
        document_id=doc_id,
        source_path=f"/workspace/{source_name}",
        source_name=source_name,
        file_type="pptx",
        metadata={},
        privacy_labels=("allowed",),
        ranking_signals={"dense_cosine": dense_cosine},
    )


def test_optical_lsu_crosslingual_variant_ja_to_vi():
    query_ja = "Laser Powerはなぜ画像中央だけでなく周辺も確認する必要がありますか。"
    variant = _build_optical_lsu_crosslingual_variant(query_ja, language_hint="ja")
    assert variant is not None
    assert variant.language_hint == "vi"
    assert variant.origin == "crosslingual_optics"
    assert variant.target_equivalent is True
    # Should include coordinate and power terms
    assert "trung tâm" in variant.text
    assert "hai bên" in variant.text
    assert "lượng sáng" in variant.text


def test_optical_lsu_crosslingual_variant_vi_to_ja():
    query_vi = "Điều chỉnh lượng sáng và kiểm tra đường kính beam tại trung tâm ảnh"
    variant = _build_optical_lsu_crosslingual_variant(query_vi, language_hint="vi")
    assert variant is not None
    assert variant.language_hint == "ja"
    assert variant.origin == "crosslingual_optics"
    assert variant.target_equivalent is True
    assert "画像中央" in variant.text or "中央" in variant.text
    assert "Beam径" in variant.text


def test_optical_lsu_crosslingual_variant_non_optical_ignored():
    query = "Hướng dẫn cài đặt hệ điều hành và phân quyền thư mục"
    variant = _build_optical_lsu_crosslingual_variant(query, language_hint="vi")
    assert variant is None


def test_plan_retrieval_query_includes_optics_variant():
    plan = build_query_plan("Laser Powerはなぜ画像中央だけでなく周辺も確認する必要がありますか。")
    optics_variants = [v for v in plan.variants if v.origin == "crosslingual_optics"]
    assert len(optics_variants) == 1
    assert optics_variants[0].target_equivalent is True
    assert "trung tâm" in optics_variants[0].text


def test_fuse_ranked_channels_crosslingual_dense_bonus():
    query_ja = "Laser Powerはなぜ画像中央だけでなく周辺も確認する必要がありますか。"
    doc_vi = (
        "Điều chỉnh lượng sáng ( Điều chỉnh LASER POWER ) Điều chỉnh lượng sáng là điều chỉnh lượng đầu ra "
        "của LASER DIODE ở vị trí phần trung tâm ảnh của ảnh trên DRUM. Phần trung tâm ảnh hầu như tương đương "
        "với phần trung tâm của Lens F, về cơ bản ở phần đó lượng sáng là lớn nhất. Xuất hiện hiện tượng nồng độ "
        "ở hai bên ảnh bị nhạt. Nói cách khác lượng sáng càng xa trung tâm càng yếu."
    )
    result = _make_search_result(
        chunk_id="chunk_test_crosslingual",
        doc_id="doc_lsu_test",
        text=doc_vi,
        dense_cosine=0.595,
    )
    lexical_response = SearchResponse(
        results=(),
        summary=SearchSummary(
            query=query_ja,
            indexed_chunk_count=0,
            eligible_chunk_count=0,
            candidate_count=0,
            returned_count=0,
            candidate_backend="bm25",
        ),
    )
    fused_response = fuse_ranked_channels(
        query=query_ja,
        lexical_response=lexical_response,
        dense_results=(result,),
        sparse_results=(),
        config=HybridRankingConfig(),
        limit=5,
        options=SearchOptions(),
    )
    assert len(fused_response.results) == 1
    fused_res = fused_response.results[0]
    assert fused_res.ranking_signals["crosslingual_dense_bonus"] == 0.008
    assert fused_res.ranking_signals["boosted_rrf"] > fused_res.ranking_signals["fused_rrf"]


def test_fuse_ranked_channels_monolingual_no_dense_bonus():
    query_vi = "Điều chỉnh lượng sáng ở phần trung tâm"
    doc_vi = "Phần trung tâm ảnh hầu như tương đương với phần trung tâm của Lens F"
    result = _make_search_result(
        chunk_id="chunk_test_mono",
        doc_id="doc_lsu_test",
        text=doc_vi,
        dense_cosine=0.65,
    )
    lexical_response = SearchResponse(
        results=(),
        summary=SearchSummary(
            query=query_vi,
            indexed_chunk_count=0,
            eligible_chunk_count=0,
            candidate_count=0,
            returned_count=0,
            candidate_backend="bm25",
        ),
    )
    fused_response = fuse_ranked_channels(
        query=query_vi,
        lexical_response=lexical_response,
        dense_results=(result,),
        sparse_results=(),
        config=HybridRankingConfig(),
        limit=5,
        options=SearchOptions(),
    )
    assert len(fused_response.results) == 1
    assert fused_response.results[0].ranking_signals["crosslingual_dense_bonus"] == 0.0


def test_is_fragment_noise_allows_vietnamese_xuat_hien_hien_tuong():
    frag = "Xuất hiện hiện tượng nồng độ ở hai bên ảnh bị nhạt."
    assert _is_fragment_noise(frag) is False

    # True stutter/noise with repeating word should still be flagged
    frag_noise = "nồng độ độ hai bên bên ảnh"
    assert _is_fragment_noise(frag_noise) is True


def test_candidate_fragments_uses_full_text():
    full_text = (
        "2-3 Điều chỉnh lượng sáng ( Điều chỉnh LASER POWER ). "
        "Phần trung tâm ảnh hầu như tương đương với phần trung tâm của Lens F, về cơ bản ở phần đó lượng sáng là lớn nhất. "
        "Xuất hiện hiện tượng nồng độ ở hai bên ảnh bị nhạt. "
        "Nói cách khác lượng sáng càng xa trung tâm càng yếu."
    )
    item = EvidenceItem(
        evidence_id="evd-1",
        citation_id="[1]",
        citation_label="doc1",
        chunk_id="chk1",
        document_id="doc1",
        source_name="doc1.pptx",
        source_path="/workspace/doc1.pptx",
        file_type="pptx",
        text=full_text,
        snippet="2-3 Điều chỉnh lượng sáng ( Điều chỉnh LASER POWER ) Điều chỉnh lượng sáng là điều chỉnh lượng đầu ra của LASER DIODE ở vị trí phần trung tâm ảnh của ảnh trên DRUM. Phần trung tâm ảnh hầu như tương đương với phần trung tâm của Lens F, về cơ",
        score=10.0,
        rank=1,
        ranking_signals={},
        matched_terms=("lượng", "sáng"),
        term_coverage=1.0,
        privacy_labels=(),
        element_types=(),
    )
    fragments = _candidate_fragments(item)
    # Ensure complete sentences from full text are preserved
    assert any("hai bên ảnh bị nhạt" in f for f in fragments)
    assert any("lượng sáng càng xa trung tâm càng yếu" in f for f in fragments)
