"""Unit and regression tests for Document Diversity Capping and Domain Spec Cache Isolation."""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from aios_habit.rag_v2.index import (
    SearchOptions,
    SearchResult,
    _select_hybrid_results,
)
from aios_habit.rag_v2.evidence import (
    EvidencePackConfig,
    build_evidence_pack,
)
from aios_habit.rag_v2.query_planning import coerce_query_plan
from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceChatRagV2CanaryConfig,
    _map_serialized_query_result,
    _get_cached_specs_for_domain,
    _DOMAIN_SPECS_QUERY_CACHE,
    _INDEX_FINGERPRINT_LOCK,
)


def _make_dummy_search_result(
    chunk_id: str,
    doc_id: str,
    source_name: str,
    score: float,
    source_path: str = "",
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
        ranking_signals={},
        matched_query_variants=(),
        matched_query_variant_ids=(),
        matched_query_facets=(),
        matched_obligations=(),
    )


def test_diversity_capping_default_3_chunks(caplog: pytest.LogCaptureFixture) -> None:
    """Kiểm tra capping mặc định 3 mảnh trên mỗi tài liệu trong tìm kiếm toàn kho."""
    plan = coerce_query_plan("Tìm kiếm thông tin lỗi linh kiện chung")
    candidates = [
        _make_dummy_search_result(f"huge_{i}", "doc_huge", "Tài liệu tổng hợp.xlsx", 10.0 - i * 0.1)
        for i in range(10)
    ]
    candidates.extend([
        _make_dummy_search_result(f"target_{i}", "doc_target", "Báo cáo lỗi chi tiết.pptx", 7.0 - i * 0.1)
        for i in range(5)
    ])

    with caplog.at_level(logging.INFO):
        selected, rejected = _select_hybrid_results(
            candidates,
            plan,
            limit=10,
            per_document_limit=3,
            near_duplicate_threshold=0.9,
        )

    huge_chunks = [c for c in selected if c.document_id == "doc_huge"]
    target_chunks = [c for c in selected if c.document_id == "doc_target"]
    assert len(huge_chunks) == 3
    assert len(target_chunks) == 3
    # Thứ tự tương đối của các item còn lại phải được giữ nguyên
    assert [c.chunk_id for c in huge_chunks] == ["huge_0", "huge_1", "huge_2"]
    assert [c.chunk_id for c in target_chunks] == ["target_0", "target_1", "target_2"]


def test_diversity_capping_canonical_duplicates() -> None:
    """Hai bản ghi khác document_id nhưng cùng tài liệu (ví dụ Dữ liệu tổng hợp.xlsx) bị gộp trần chung."""
    plan = coerce_query_plan("Tra cứu lỗi tổng thể linh kiện")
    # Giả lập 5 mảnh từ document_id A và 5 mảnh từ document_id B, cùng tên Dữ liệu tổng hợp.xlsx
    candidates = []
    for i in range(5):
        candidates.append(
            _make_dummy_search_result(f"chunk_a_{i}", "wsc-aaa111", "Dữ liệu tổng hợp.xlsx", 10.0 - i * 0.1)
        )
    for i in range(5):
        candidates.append(
            _make_dummy_search_result(f"chunk_b_{i}", "wsc-bbb222", "dữ liệu tổng hợp.xlsx", 9.5 - i * 0.1)
        )
    # Thêm tài liệu khác để kiểm tra được giải phóng chỗ
    candidates.append(
        _make_dummy_search_result("spec_0", "wsc-ccc333", "HuongDanKiemTra.pdf", 8.0)
    )

    selected, rejected = _select_hybrid_results(
        candidates,
        plan,
        limit=10,
        per_document_limit=3,
        near_duplicate_threshold=0.9,
    )

    du_lieu_th_chunks = [
        c for c in selected if c.source_name.lower() == "dữ liệu tổng hợp.xlsx"
    ]
    # Tổng số mảnh từ cả hai bản ghi của Dữ liệu tổng hợp.xlsx không được vượt quá 3
    assert len(du_lieu_th_chunks) == 3
    # Tài liệu thứ ba được lọt vào danh sách
    assert any(c.document_id == "wsc-ccc333" for c in selected)


def test_named_document_allows_higher_chunks() -> None:
    """Tài liệu được gọi tên đích danh trong câu hỏi không bị giới hạn trần 3 mảnh toàn kho."""
    query = "Xem thông tin từ Báo cáo lỗi chi tiết.pptx"
    plan = coerce_query_plan(query)
    candidates = [
        _make_dummy_search_result(f"named_{i}", "doc_named", "Báo cáo lỗi chi tiết.pptx", 10.0 - i * 0.1)
        for i in range(6)
    ]
    candidates.extend([
        _make_dummy_search_result(f"other_{i}", "doc_other", "Tài liệu khác.xlsx", 8.0 - i * 0.1)
        for i in range(5)
    ])

    selected, rejected = _select_hybrid_results(
        candidates,
        plan,
        limit=10,
        per_document_limit=3,
        near_duplicate_threshold=0.9,
    )

    named_chunks = [c for c in selected if c.document_id == "doc_named"]
    # Tài liệu được gọi tên được lấy tới 5 mảnh (effective_doc_limit = 5)
    assert len(named_chunks) == 5
    other_chunks = [c for c in selected if c.document_id == "doc_other"]
    assert len(other_chunks) == 3


def test_adapter_map_serialized_query_result_capping() -> None:
    """_map_serialized_query_result áp trần N mảnh và giữ nguyên thứ tự tương đối."""
    originals = {
        "doc_a": WorkspaceAIContextSource(
            source_id="src_a",
            source_scope="collection",
            source_type="plain_text",
            title="Tệp A.xlsx",
            privacy_label="local_only",
            text="",
            included_chars=0,
            managed_path="path/to/Tệp A.xlsx",
            truncated=False,
        ),
        "doc_b": WorkspaceAIContextSource(
            source_id="src_b",
            source_scope="collection",
            source_type="plain_text",
            title="Tệp B.docx",
            privacy_label="local_only",
            text="",
            included_chars=0,
            managed_path="path/to/Tệp B.docx",
            truncated=False,
        ),
    }

    # Giả lập 5 mảnh từ doc_a và 2 mảnh từ doc_b
    items = [
        {"document_id": "doc_a", "text": f"Đoạn A{i}", "score": 9.0 - i, "citation_id": f"c_a_{i}", "evidence_id": f"e_a_{i}"}
        for i in range(5)
    ] + [
        {"document_id": "doc_b", "text": f"Đoạn B{i}", "score": 4.0 - i, "citation_id": f"c_b_{i}", "evidence_id": f"e_b_{i}"}
        for i in range(2)
    ]
    query_result = {"items": items, "summary": {"candidate_count": 7}}

    # Chạy với per_document_limit = 3
    mapped = _map_serialized_query_result(
        query_result,
        originals,
        requested_profile="bge_m3_hybrid",
        effective_profile="bge_m3_hybrid",
        fallback_reason="",
        latency_ms=10.0,
        per_document_limit=3,
        question="câu hỏi tìm kiếm chung không gọi tên tệp",
        is_named_document_query=False,
    )

    ev_items = mapped["evidence_items"]
    # doc_a chỉ còn 3 mảnh, doc_b có 2 mảnh -> tổng 5 mảnh
    assert len(ev_items) == 5
    doc_a_items = [it for it in ev_items if it["source_id"] == "src_a"]
    doc_b_items = [it for it in ev_items if it["source_id"] == "src_b"]
    assert len(doc_a_items) == 3
    assert len(doc_b_items) == 2
    # Thứ tự ban đầu được bảo toàn
    assert [it["text"] for it in doc_a_items] == ["Đoạn A0", "Đoạn A1", "Đoạn A2"]
    assert [it["text"] for it in doc_b_items] == ["Đoạn B0", "Đoạn B1"]
    # Snippet index liên tục 1..5 không bị nhảy bậc
    assert [it["snippet_index"] for it in ev_items] == [1, 2, 3, 4, 5]


def test_domain_specs_cache_not_poisoned_by_named_doc(tmp_path: Path) -> None:
    """Truy vấn có tài liệu gọi tên không được đầu độc cache của truy vấn toàn kho tiếp theo."""
    db_file = tmp_path / "mock_library.sqlite"
    db_file.write_text("dummy sqlite header", encoding="utf-8")

    from aios_habit import index_domain
    spec_all_1 = MagicMock(document_id="doc_all_1", source_id="src_1")
    spec_all_2 = MagicMock(document_id="doc_all_2", source_id="src_2")
    spec_named = MagicMock(document_id="doc_named_only", source_id="src_named")

    def mock_get_specs(domain, path, question=None):
        if question and "named_doc.xlsx" in question:
            return (spec_named,)
        return (spec_all_1, spec_all_2)

    def mock_match_named(question, db_path=None, sources=None):
        if question and "named_doc.xlsx" in question:
            return ([spec_named], [])
        return ([], [])

    orig_get_specs = index_domain.get_specs_for_domain
    orig_match_named = index_domain.match_named_documents
    index_domain.get_specs_for_domain = mock_get_specs
    index_domain.match_named_documents = mock_match_named

    try:
        with _INDEX_FINGERPRINT_LOCK:
            _DOMAIN_SPECS_QUERY_CACHE.clear()

        # Lượt 1: Câu hỏi gọi tên named_doc.xlsx
        res_named = _get_cached_specs_for_domain(
            "tong_hop",
            db_file,
            question="Tra cứu trong file named_doc.xlsx",
        )
        assert len(res_named) == 1
        assert res_named[0].document_id == "doc_named_only"

        # Lượt 2: Câu hỏi tìm kiếm toàn kho (không gọi tên tài liệu)
        res_general = _get_cached_specs_for_domain(
            "tong_hop",
            db_file,
            question="Tra cứu lỗi tổng thể linh kiện chung",
        )
        # BẮT BUỘC phải trả về toàn bộ tài liệu (spec_all_1, spec_all_2), không được dính named_doc_only
        assert len(res_general) == 2
        assert {s.document_id for s in res_general} == {"doc_all_1", "doc_all_2"}
    finally:
        index_domain.get_specs_for_domain = orig_get_specs
        index_domain.match_named_documents = orig_match_named
        with _INDEX_FINGERPRINT_LOCK:
            _DOMAIN_SPECS_QUERY_CACHE.clear()
