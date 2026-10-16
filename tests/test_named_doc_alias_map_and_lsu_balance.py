"""Tests for DESKTOP-NAMED-DOC-CATALOG-ALIAS-MAP-FIX-HOME.

Verifies:
1. Alias mapping from wsc-... document IDs to original filenames via bundled JSON map and source header scanning.
2. TT11 named document matching: "生産履歴登録システム_変更確認チェックリスト_20260914.xlsx" matches wsc-573a0a68739534ed9860dcec.
3. Fallback on named document mismatch: when a named document does not match catalog, it does not abort with Honest Refusal.
4. LSU machine series balancing: query without machine line labels (Q0696) balances Sirius and Iris LSU candidates in top-6 evidence.
5. Regression preservation: queries with explicit machine line labels (Sirius / Iris) are not altered by LSU balancing.
"""

from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, Optional
import pytest

from aios_habit.index_domain import (
    _get_spec_original_alias,
    clean_named_doc_token,
    detect_domain_from_question,
    extract_named_document_candidates,
    load_all_index_specs,
    load_domain_document_alias_map,
    match_named_documents,
)
from aios_habit.rag_v2.index import SearchResponse, SearchResult, SearchSummary
from aios_habit.rag_v2.pipeline import (
    RagV2DevPipeline,
    SourceSpec,
    _balance_lsu_machine_series,
)
from aios_habit.rag_v2.query_planning import coerce_query_plan


def _make_result(
    chunk_id: str,
    document_id: str,
    text: str,
    score: float,
    source_name: str,
    ranking_signals: Optional[Dict[str, Any]] = None,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        score=score,
        text=text,
        document_id=document_id,
        source_path=source_name,
        source_name=source_name,
        file_type="xlsx" if source_name.endswith(".xlsx") else "msg",
        metadata={},
        privacy_labels=("local_only",),
        ranking_signals=ranking_signals or {},
    )


def _make_summary(query: str = "") -> SearchSummary:
    return SearchSummary(
        query=query,
        indexed_chunk_count=100,
        eligible_chunk_count=100,
        candidate_count=20,
        returned_count=10,
    )


def test_alias_map_loaded_and_contains_expected_mappings():
    alias_map = load_domain_document_alias_map()
    assert isinstance(alias_map, dict)
    assert len(alias_map) >= 20
    # Must contain TT11 target document mapping
    assert "wsc-573a0a68739534ed9860dcec" in alias_map
    assert alias_map["wsc-573a0a68739534ed9860dcec"] == "生産履歴登録システム_変更確認チェックリスト_20260914.xlsx"
    # Must contain TANABAN master mapping
    assert "wsc-ef0d393c086c7f07627ca8b8" in alias_map
    assert alias_map["wsc-ef0d393c086c7f07627ca8b8"] == "TANABAN_Master.xlsx"


def test_spec_original_alias_resolution():
    dummy_spec = SourceSpec(
        path=Path("D:/Sandbox/fake_dir/wsc-573a0a68739534ed9860dcec.txt"),
        source_id="wsc-573a0a68739534ed9860dcec",
        document_id="wsc-573a0a68739534ed9860dcec",
    )
    alias = _get_spec_original_alias(dummy_spec)
    assert alias == "生産履歴登録システム_変更確認チェックリスト_20260914.xlsx"


def test_tt11_named_document_matching_and_domain_detection():
    q_tt11 = (
        "Trong tài liệu 生産履歴登録システム_変更確認チェックリスト_20260914.xlsx, "
        "server mới (máy chủ Linux) có tên máy là gì?"
    )
    matched, missing = match_named_documents(q_tt11)
    assert len(matched) >= 1
    matched_ids = [getattr(s, "document_id", "") for s in matched]
    assert "wsc-573a0a68739534ed9860dcec" in matched_ids
    assert len(missing) == 0

    det = detect_domain_from_question(q_tt11)
    assert det.confidence == 1.0
    assert "生産履歴登録システム_変更確認チェックリスト_20260914.xlsx" in det.reason or "573a" in det.reason


def test_fallback_on_unmatched_named_doc_does_not_raise_or_block():
    # If a document is completely missing from the library, match_named_documents identifies it in missing
    q_missing = "Trong tài liệu document_khong_ton_tai_xyz999.xlsx, kết quả kiểm tra là gì?"
    matched, missing = match_named_documents(q_missing)
    assert len(matched) == 0
    assert "document_khong_ton_tai_xyz999.xlsx" in missing

    # detect_domain_from_question records low confidence with missing document info
    det = detect_domain_from_question(q_missing)
    assert det.confidence == 0.0
    assert "document_khong_ton_tai_xyz999.xlsx" in det.reason


def test_lsu_series_balancing_for_unlabeled_query_q0696():
    # Simulate fused retrieval response where Sirius chunks monopolize top 5
    # and Iris chunk is ranked at #8 despite strong dense relevance
    results = [
        _make_result(
            chunk_id="sirius_chunk_1",
            document_id="sirius_doc_1",
            text="Sirius 2 Unit調整と確認",
            score=0.046,
            source_name="Sirius2_Unit_Adjust.xlsx",
            ranking_signals={"dense_channel_rank": 23, "sparse_channel_rank": 1},
        ),
        _make_result(
            chunk_id="sirius_chunk_2",
            document_id="sirius_doc_2",
            text="Sirius 2 相関分析データ",
            score=0.045,
            source_name="Sirius2_Correlation.xlsx",
            ranking_signals={"dense_channel_rank": 32, "sparse_channel_rank": 2},
        ),
        _make_result(
            chunk_id="sirius_chunk_3",
            document_id="sirius_doc_3",
            text="Sirius 2 Beam径測定",
            score=0.044,
            source_name="Sirius2_Beam.xlsx",
            ranking_signals={"dense_channel_rank": 40, "sparse_channel_rank": 3},
        ),
        _make_result(
            chunk_id="iris_target_chunk",
            document_id="iris_doc_target",
            text="RE: Iris LSU Beam径NG多発 異常品質会議5回目 Correlation JIG Nano Scan JIG BEAM JIG BOW UNIT OK/UNIT NG",
            score=0.038,
            source_name="RE_ Iris LSU Beam径NG多発　異常品質会議5回目.msg",
            ranking_signals={"dense_channel_rank": 3, "dense_cosine": 0.58, "sparse_channel_rank": 18},
        ),
    ]
    resp = SearchResponse(results=tuple(results), summary=_make_summary())
    plan = coerce_query_plan("排查时应先调整Unit还是确认Jig相关性？")

    balanced_resp = _balance_lsu_machine_series(plan, resp, is_lsu=True)

    # Top 1 remains top 1 (Sirius)
    assert balanced_resp.results[0].chunk_id == "sirius_chunk_1"
    # Natural top 2 is preserved, not forcibly replaced without Iris label
    assert balanced_resp.results[1].chunk_id == "sirius_chunk_2"
    # Iris candidate is promoted into slot #3 due to strong dense relevance and similar scores
    assert balanced_resp.results[2].chunk_id == "iris_target_chunk"
    assert "machine_series_balance_boost" in balanced_resp.results[2].ranking_signals
    # Expected Iris keywords are now accessible in top slots
    assert "Correlation" in balanced_resp.results[2].text
    assert "JIG Nano Scan" in balanced_resp.results[2].text


def test_lsu_series_balancing_skips_when_scores_not_similar():
    # When top candidate has score 35.0 and Iris candidate has score 15.0 (diff = 20.0 >= 2.0),
    # balancing must NOT intervene.
    results = [
        _make_result(
            chunk_id="target_chunk_1",
            document_id="target_doc_1",
            text="High scoring target",
            score=35.0,
            source_name="AI cảnh báo lỗi LSU.pptx",
        ),
        _make_result(
            chunk_id="target_chunk_2",
            document_id="target_doc_1",
            text="Second high scoring target",
            score=25.0,
            source_name="AI cảnh báo lỗi LSU.pptx",
        ),
        _make_result(
            chunk_id="iris_candidate",
            document_id="iris_doc",
            text="Iris meeting notes",
            score=15.0,
            source_name="RE_ Iris LSU Beam径NG多発　異常品質会議.msg",
            ranking_signals={"dense_channel_rank": 3, "dense_cosine": 0.58},
        ),
    ]
    resp = SearchResponse(results=tuple(results), summary=_make_summary())
    plan = coerce_query_plan("Tỷ lệ NG của ba JIG trọng điểm khác nhau thế nào?")
    balanced = _balance_lsu_machine_series(plan, resp, is_lsu=True)
    # Order must remain completely unchanged
    assert [r.chunk_id for r in balanced.results] == ["target_chunk_1", "target_chunk_2", "iris_candidate"]


def test_lsu_series_balancing_preserves_explicit_series_queries():
    # When query mentions 'Sirius' explicitly (e.g. Q0700)
    plan_sirius = coerce_query_plan("Lỗi lệch chùm tia trên máy Sirius 2 LSU nguyên nhân do đâu?")
    results = [
        _make_result(
            chunk_id="c1",
            document_id="d1",
            text="Sirius 2 text",
            score=0.05,
            source_name="Sirius2.xlsx",
        ),
        _make_result(
            chunk_id="c2",
            document_id="d2",
            text="Iris text",
            score=0.04,
            source_name="Iris.xlsx",
            ranking_signals={"dense_channel_rank": 2, "dense_cosine": 0.6},
        ),
    ]
    resp = SearchResponse(results=tuple(results), summary=_make_summary())
    balanced = _balance_lsu_machine_series(plan_sirius, resp, is_lsu=True)
    # Must NOT alter results when series is explicitly named
    assert [r.chunk_id for r in balanced.results] == ["c1", "c2"]

    # When query mentions 'Iris' explicitly (e.g. Q0703)
    plan_iris = coerce_query_plan("Iris LSU beam diameter NG meeting notes")
    balanced_iris = _balance_lsu_machine_series(plan_iris, resp, is_lsu=True)
    assert [r.chunk_id for r in balanced_iris.results] == ["c1", "c2"]
