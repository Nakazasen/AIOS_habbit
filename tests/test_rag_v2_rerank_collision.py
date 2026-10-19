from dataclasses import replace

from aios_habit.rag_v2.chunking import DocumentChunk
from aios_habit.rag_v2.index import (
    HybridRankingConfig,
    LocalChunkIndex,
    SearchOptions,
    SearchResponse,
    SearchResult,
    SearchSummary,
    _select_hybrid_results,
    fuse_ranked_channels,
)
from aios_habit.rag_v2.query_planning import identity_query_plan


def _make_search_result(
    chunk_id: str,
    document_id: str,
    source_name: str,
    text: str,
    *,
    score: float = 10.0,
    dense_cosine: float = 0.0,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        score=score,
        text=text,
        document_id=document_id,
        source_path=f"/workspace/{source_name}",
        source_name=source_name,
        file_type="pptx",
        metadata={},
        privacy_labels=("allowed",),
        ranking_signals={"dense_cosine": dense_cosine} if dense_cosine else {},
    )


def _make_empty_summary() -> SearchSummary:
    return SearchSummary(
        query="",
        indexed_chunk_count=0,
        eligible_chunk_count=0,
        candidate_count=0,
        returned_count=0,
    )


def test_short_string_duration_vs_date_fraction_disambiguation():
    query = "Tại sao khi che cảm biến 3s/6s thì cần lưu ý gì?"
    plan = identity_query_plan(query)

    date_collision = _make_search_result(
        "date-chunk",
        "doc-date",
        "Schedule_Report.pptx",
        "Lịch kiểm tra ngày 3/6 và 14/2 tại nhà máy.",
        score=12.0,
    )
    duration_match = _make_search_result(
        "duration-chunk",
        "doc-duration",
        "Sensor_Guide.pptx",
        "Khi che cảm biến 3s hoặc 6s, hệ thống báo lỗi timeout.",
        score=10.0,
    )
    lex_resp = SearchResponse(
        results=(date_collision, duration_match),
        summary=_make_empty_summary(),
    )
    fused = fuse_ranked_channels(
        plan,
        lex_resp,
        dense_results=(),
        limit=5,
        options=SearchOptions(),
        config=HybridRankingConfig(),
    )
    assert [r.chunk_id for r in fused.results] == ["duration-chunk", "date-chunk"]
    assert "duration_unit_match_boost" in fused.results[0].ranking_signals
    assert "date_fraction_collision_penalty" in fused.results[1].ranking_signals


def test_numeric_outlier_dump_saturation_and_multiterm_cooccurrence(tmp_path):
    noisy_csv = DocumentChunk(
        chunk_id="csv-dump",
        document_id="doc-csv",
        source_path="/workspace/2026_08_UnitTest.csv",
        source_name="2026_08_UnitTest.csv",
        file_type="csv",
        text="Mode: UnitTest S/N: 61C1 " + "14 2 999.0 " * 25,
        normalized_text=("Mode: UnitTest S/N: 61C1 " + "14 2 999.0 " * 25).lower(),
        element_ids=("e-csv",),
        element_types=("table",),
        section_path=(),
        privacy_labels=("allowed",),
        source_fingerprint="fp-csv",
        checksum="chk-csv",
    )
    target_slide = DocumentChunk(
        chunk_id="slide-16",
        document_id="doc-sirius",
        source_path="/workspace/Sirius 2 _ C7620.pptx",
        source_name="Sirius 2 _ C7620.pptx",
        file_type="pptx",
        text="Sirius 2 C7620 LSU HOUSING LOT Magenta MIRROR A MIRROR BOW MIRROR C 14.02.2025 Lot 14.2",
        normalized_text="sirius 2 c7620 lsu housing lot magenta mirror a mirror bow mirror c 14.02.2025 lot 14.2",
        element_ids=("e-slide",),
        element_types=("text",),
        section_path=(),
        privacy_labels=("allowed",),
        source_fingerprint="fp-sirius",
        checksum="chk-sirius",
    )
    with LocalChunkIndex(tmp_path / "collision.sqlite") as index:
        index.upsert_chunks([noisy_csv, target_slide])
        results = index.search("Sau ngày bảo dưỡng khuôn 14/2, Housing màu Magenta có điểm gì đáng chú ý?")

    assert results[0].chunk_id == "slide-16"
    assert "distinct_content_term_boost" in results[0].ranking_signals
    for res in results:
        assert res.ranking_signals.get("lexical_frequency_capped", 0.0) <= 2.0


def test_document_series_collision_and_sequence_disambiguation():
    query = "Trong tài liệu họp bất thường chất lượng lần 3 (3回目), nội dung chính là gì?"
    plan = identity_query_plan(query)

    m2_a = _make_search_result("m2-a", "doc-m2", "品質異常会議2回目.pptx", "Nội dung họp chất lượng A", score=15.0)
    m2_b = _make_search_result("m2-b", "doc-m2", "品質異常会議2回目.pptx", "Nội dung họp chất lượng B", score=14.5)
    m5_a = _make_search_result("m5-a", "doc-m5", "品質異常会議5回目.pptx", "Nội dung họp chất lượng C", score=14.0)
    m3_a = _make_search_result("m3-a", "doc-m3", "品質異常会議3回目.pptx", "Nội dung họp chất lượng lần 3 chính thức", score=12.0)

    lex_resp = SearchResponse(
        results=(m2_a, m2_b, m5_a, m3_a),
        summary=_make_empty_summary(),
    )
    fused = fuse_ranked_channels(
        plan,
        lex_resp,
        dense_results=(),
        limit=5,
        options=SearchOptions(),
        config=HybridRankingConfig(),
    )
    assert fused.results[0].chunk_id == "m3-a"
    assert "series_sequence_match_boost" in fused.results[0].ranking_signals

    selected, _rejected = _select_hybrid_results(
        [m2_a, m2_b, replace(m2_b, chunk_id="m2-c"), m5_a],
        identity_query_plan("Tài liệu họp bất thường chất lượng"),
        limit=4,
        per_document_limit=3,
        near_duplicate_threshold=0.99,
    )
    assert len(selected) <= 2
