# -*- coding: utf-8 -*-
"""Regression and boundary tests for draft fallback relevance gate.

Verifies:
1. Functional words ('la', 'gi', 'the', 'nao'...) do not count toward relevance.
2. Short queries like 'erp router la gi?' do not match circuit board drafts
   (dieuchinh/batch-60.md) or partial 1-word hits below coverage threshold.
3. Legitimate domain queries matching significant tokens (ctrlMode, jig suy giam)
   continue to be served with mandatory label.
"""

import pytest
from aios_habit import answer_draft_fallback as fallback


@pytest.fixture(autouse=True)
def _clean_flag():
    fallback.clear_draft_fallback_override()
    yield
    fallback.clear_draft_fallback_override()


def test_functional_words_alone_cannot_pass_gate():
    """Draft sharing only functional words ('la', 'gi') must be rejected."""
    entries = [
        fallback.DraftEntry(
            question="ASSY No., Rev., PWB No. và ngày của bản Human Detect PP này là gì?",
            answer="ASSY No.=302V847060, Rev.=06, PWB No.=7PA1111BSS+GH01",
            source_file="dieuchinh/batch-60.md",
            position=1,
        )
    ]
    # Query has 'la' and 'gi', but significant tokens 'erp', 'router' do not match
    hits = fallback.search_drafts("erp router la gi?", entries)
    assert len(hits) == 0

    decision = fallback.resolve_answer(
        "erp router la gi?",
        rag_ok=False,
        draft_entries=entries,
        enabled=True,
    )
    assert decision.lane == "not_found"
    assert decision.has_draft_label is False
    assert fallback.NOT_FOUND_MESSAGE in decision.answer_text


def test_partial_match_below_coverage_threshold_rejected():
    """Partial 1-word match for a 2-word query (coverage 50% < 60%) must be rejected."""
    entries = [
        fallback.DraftEntry(
            question="ERP trong tài liệu quản lý những nghiệp vụ chính nào?",
            answer="Quản lý kế hoạch sản xuất.",
            source_file="mom/batch-02.md",
            position=1,
        )
    ]
    # Query: 'erp router' (2 tokens). Matched: 'erp' (1 token). Coverage: 1/2 = 0.5 < 0.6
    hits = fallback.search_drafts("erp router la gi?", entries)
    assert len(hits) == 0

    decision = fallback.resolve_answer(
        "erp router la gi?",
        rag_ok=False,
        draft_entries=entries,
        enabled=True,
    )
    assert decision.lane == "not_found"


def test_significant_token_match_above_coverage_threshold_accepted():
    """Questions sharing substantive tokens above threshold are accepted with label."""
    entries = [
        fallback.DraftEntry(
            question="Trong file cấu hình Matecon, ctrlMode = 0 và ctrlMode = 1 khác nhau thế nào?",
            answer="ctrlMode 0 là sản xuất tự động, ctrlMode 1 là thủ công.",
            source_file="mom/batch-01.md",
            position=1,
        )
    ]
    hits = fallback.search_drafts("ctrlMode 0 và 1 khác nhau thế nào?", entries)
    assert len(hits) == 1
    assert hits[0].source_file == "mom/batch-01.md"

    decision = fallback.resolve_answer(
        "ctrlMode 0 và 1 khác nhau thế nào?",
        rag_ok=False,
        draft_entries=entries,
        enabled=True,
    )
    assert decision.lane == "draft_fallback"
    assert decision.has_draft_label is True
    assert fallback.DRAFT_LABEL in decision.answer_text


def test_real_draft_store_erp_router_returns_honest_not_found():
    """Verify against full real 3392 draft catalog: 'erp router la gi?' never matches Iris draft."""
    real_entries = fallback.get_default_draft_entries()
    assert len(real_entries) > 0

    hits = fallback.search_drafts("erp router la gi?", real_entries)
    # Must NOT match dieuchinh/batch-60.md
    matched_sources = [h.source_file for h in hits]
    assert "dieuchinh\\batch-60.md" not in matched_sources
    assert "dieuchinh/batch-60.md" not in matched_sources
    assert len(hits) == 0

    decision = fallback.resolve_answer(
        "erp router la gi?",
        rag_ok=False,
        draft_entries=real_entries,
        enabled=True,
    )
    assert decision.lane == "not_found"
    assert "ASSY No." not in decision.answer_text


def test_real_draft_store_positive_control_jig_accepted():
    """Verify real draft catalog serves legitimate match with label."""
    real_entries = fallback.get_default_draft_entries()
    q = "File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?"
    hits = fallback.search_drafts(q, real_entries)
    assert len(hits) == 1
    assert "lsu" in hits[0].source_file
    assert "batch-16" in hits[0].source_file

    decision = fallback.resolve_answer(
        q,
        rag_ok=False,
        draft_entries=real_entries,
        enabled=True,
    )
    assert decision.lane == "draft_fallback"
    assert decision.has_draft_label is True
    assert fallback.DRAFT_LABEL in decision.answer_text
    assert "AI_LSU_du_doan_loi.xlsx" in decision.answer_text
