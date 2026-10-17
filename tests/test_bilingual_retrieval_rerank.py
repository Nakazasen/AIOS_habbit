"""Unit tests for bilingual document re-ranking in warehouse tri_thuc.

Ticket requirement:
(iii) Với tài liệu song ngữ ở kho tri_thuc: khi truy vấn chứa từ khóa tiếng Việt,
các đoạn tiếng Việt chứa từ khóa đó phải được xếp hạng lại đưa vào tập trích đoạn.
Giữ nguyên mọi hành vi truy hồi khác.
"""
from dataclasses import replace
import pytest

from aios_habit.rag_v2.pipeline import _rerank_bilingual_tri_thuc
from aios_habit.rag_v2.query_planning import coerce_query_plan
from aios_habit.rag_v2.index import SearchResponse, SearchResult, SearchSummary
from aios_habit.rag_v2.evidence import build_evidence_pack


def _make_dummy_result(
    chunk_id: str,
    doc_id: str,
    source_name: str,
    text: str,
    score: float,
    *,
    is_summary: bool = False,
) -> SearchResult:
    signals = {"dense_cosine": 0.85, "dense_channel_rank": 1}
    meta = {"representation_role": "summary" if is_summary else "child"}
    return SearchResult(
        chunk_id=chunk_id,
        document_id=doc_id,
        source_name=source_name,
        source_path=f"/{source_name}",
        file_type="txt",
        text=text,
        score=score,
        ranking_signals=signals,
        matched_terms=("oricon", "10kg") if "10kg" in text.lower() else (),
        term_coverage=1.0,
        matched_query_facets=("oricon", "storage"),
        matched_obligations=("obl1",),
        matched_query_variant_ids=("var_orig",),
        matched_target_equivalent_variant_ids=(),
        metadata=meta,
        privacy_labels=(),
    )


def test_bilingual_tri_thuc_reranking_promotes_vietnamese_chunk():
    """Verify Vietnamese query against bilingual doc boosts factual Vietnamese chunk to top."""
    query = "Theo tài liệu wsc-6f049a1fdfc090dc7d439224.txt khi lưu kho thùng ORICON từ 10kg trở lên quy định đặt ở tầng mấy?"
    plan = coerce_query_plan(query)

    doc_id = "wsc-6f049a1fdfc090dc7d439224"
    doc_name = "wsc-6f049a1fdfc090dc7d439224.txt"

    # Simulate SearchResponse where Japanese chunks and summary originally ranked higher
    r_summary = _make_dummy_result(
        f"{doc_id}-summary", doc_id, doc_name,
        "[DOCUMENT ARCHITECTURE & SUMMARY]\nQuy tắc chỉ thị số giá. Thùng ORICON quy định lưu kho tầng 1, 2.",
        score=0.25,
        is_summary=True,
    )
    r_ja_top = _make_dummy_result(
        "chunk_ja_top", doc_id, doc_name,
        "保管ルール: 2階C棟のp-Rackに保管する場合、ORICONボックスの重量制限に従うこと。10kg以上は1段目に配置する。",
        score=0.22,
    )
    r_vi_target = _make_dummy_result(
        "chunk_vi_factual", doc_id, doc_name,
        "Lưu ý: Đối với thùng ORICON có trọng lượng từ 10kg trở lên, quy định phải đặt ở tầng 1 của giá p-Rack.",
        score=0.14,  # Originally lower score than Japanese chunk!
    )
    r_ja_other = _make_dummy_result(
        "chunk_ja_other", doc_id, doc_name,
        "棚番号の表記方法について。C棟2階の配置図を参照すること。",
        score=0.10,
    )

    response = SearchResponse(
        results=(r_summary, r_ja_top, r_vi_target, r_ja_other),
        summary=SearchSummary(
            query=query,
            indexed_chunk_count=10,
            eligible_chunk_count=10,
            candidate_count=4,
            returned_count=4,
            planned_obligation_ids=("obl1",),
            planned_facet_ids=("oricon", "storage"),
        ),
    )

    # Re-rank in tri_thuc context
    reranked = _rerank_bilingual_tri_thuc(plan, response, is_tri_thuc=True)

    # 1. The Vietnamese factual chunk must receive the boost and become Rank 1
    top_result = reranked.results[0]
    assert top_result.chunk_id == "chunk_vi_factual"
    assert top_result.ranking_signals.get("bilingual_vi_boost", 0.0) > 0.0
    assert "10kg" in top_result.text
    assert "tầng 1" in top_result.text

    # 2. Summary chunk must NOT be boosted
    summary_result = [r for r in reranked.results if r.chunk_id == f"{doc_id}-summary"][0]
    assert "bilingual_vi_boost" not in summary_result.ranking_signals

    # 3. In the final Evidence Pack, the boosted chunk must be Item #1
    pack = build_evidence_pack(plan, reranked)
    assert len(pack.items) >= 1
    assert pack.items[0].chunk_id == "chunk_vi_factual"
    assert "tầng 1" in pack.items[0].text
    assert "10kg" in pack.items[0].text


def test_bilingual_tri_thuc_preserves_other_behavior():
    """Verify non-Vietnamese query or monolingual document is NOT altered."""
    # Scenario A: Japanese query -> No change
    ja_query = "2階C棟のp-Rackで10kg以上のORICONボックスの配置段数"
    plan_ja = coerce_query_plan(ja_query)

    doc_id = "wsc-6f049a1fdfc090dc7d439224"
    doc_name = "wsc-6f049a1fdfc090dc7d439224.txt"
    r1 = _make_dummy_result("c1", doc_id, doc_name, "日本語テキスト 10kg", score=0.20)
    r2 = _make_dummy_result("c2", doc_id, doc_name, "Tiếng Việt 10kg tầng 1", score=0.10)
    res_ja = SearchResponse(
        results=(r1, r2),
        summary=SearchSummary(
            query=ja_query,
            indexed_chunk_count=10,
            eligible_chunk_count=10,
            candidate_count=2,
            returned_count=2,
        ),
    )

    reranked_ja = _rerank_bilingual_tri_thuc(plan_ja, res_ja, is_tri_thuc=True)
    # Order and scores must be identical
    assert reranked_ja.results[0].chunk_id == "c1"
    assert "bilingual_vi_boost" not in reranked_ja.results[1].ranking_signals

    # Scenario B: Monolingual Japanese document with Vietnamese query -> No change
    vi_query = "Quy định về thông số kỹ thuật"
    plan_vi = coerce_query_plan(vi_query)
    doc_mono = "doc_mono_ja"
    r_mono1 = _make_dummy_result("m1", doc_mono, "manual.pdf", "仕様について", score=0.15)
    r_mono2 = _make_dummy_result("m2", doc_mono, "manual.pdf", "操作手順", score=0.12)
    res_mono = SearchResponse(
        results=(r_mono1, r_mono2),
        summary=SearchSummary(
            query=vi_query,
            indexed_chunk_count=10,
            eligible_chunk_count=10,
            candidate_count=2,
            returned_count=2,
        ),
    )

    reranked_mono = _rerank_bilingual_tri_thuc(plan_vi, res_mono, is_tri_thuc=True)
    assert reranked_mono.results[0].chunk_id == "m1"
    assert reranked_mono.results[1].chunk_id == "m2"


def test_bilingual_reranking_isolated_from_non_tri_thuc():
    """Verify non-tri_thuc warehouses (lsu, dieu_tra_loi, che_do) are completely isolated."""
    query = "Tỷ lệ NG của ba JIG trọng điểm khác nhau thế nào?"
    plan = coerce_query_plan(query)
    doc_id = "wsc-msg-bilingual"
    doc_name = "RE_ Iris LSU Beam径NG多発 異常品質会議2回目.msg"
    # Even if document has both Vietnamese and Japanese/CJK, is_tri_thuc=False must prevent any boost
    r_target = _make_dummy_result("c_target", "doc_target", "AI cảnh báo lỗi LSU.pptx", "Slide tiếng Việt", score=0.35)
    r_bilingual = _make_dummy_result(
        "c_bilingual", doc_id, doc_name,
        "Biên bản cuộc họp song ngữ: Cần kiểm tra Beam径NG多発 và báo cáo kết quả.", score=0.15
    )
    res = SearchResponse(
        results=(r_target, r_bilingual),
        summary=SearchSummary(
            query=query,
            indexed_chunk_count=10,
            eligible_chunk_count=10,
            candidate_count=2,
            returned_count=2,
        ),
    )

    # When is_tri_thuc is False (default)
    reranked_default = _rerank_bilingual_tri_thuc(plan, res)
    assert reranked_default.results[0].chunk_id == "c_target"
    assert reranked_default.results[1].chunk_id == "c_bilingual"
    assert "bilingual_vi_boost" not in reranked_default.results[1].ranking_signals

    # When explicitly is_tri_thuc=False
    reranked_false = _rerank_bilingual_tri_thuc(plan, res, is_tri_thuc=False)
    assert reranked_false.results[0].chunk_id == "c_target"
    assert reranked_false.results[1].chunk_id == "c_bilingual"
    assert "bilingual_vi_boost" not in reranked_false.results[1].ranking_signals

