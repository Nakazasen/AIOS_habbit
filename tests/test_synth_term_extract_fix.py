"""Unit tests for SYNTH-TERM-EXTRACT-FIX-HOME.

Verifies that Vietnamese function and connective words are safely filtered
from evidence coverage term calculation, unblocking the wrongful abstain case Q0695
while strictly maintaining fail-closed protection for the 7 genuinely evidence-lacking
short diagnostic questions.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from aios_habit.rag_v2.query_planning import (
    VIETNAMESE_EVIDENCE_STOPWORDS,
    extract_content_terms,
    extract_evidence_terms,
    build_query_plan,
)
from aios_habit.rag_v2.evidence import (
    EvidenceItem,
    EvidencePackConfig,
    _final_evidence_relevance,
    build_evidence_pack,
)
from aios_habit.rag_v2.index import SearchResponse, SearchResult, SearchSummary


def test_vietnamese_stopwords_list_complete():
    """Ensure all required Vietnamese function/connective words are defined."""
    required = {"ủng", "hộ", "chung", "riêng", "hay", "và", "của", "hoặc"}
    assert required.issubset(VIETNAMESE_EVIDENCE_STOPWORDS)


def test_extract_evidence_terms_filters_stopwords():
    """Verify that extract_evidence_terms filters stopwords while extract_content_terms preserves them."""
    query = "Dữ liệu hiện tại ủng hộ lỗi chung của 1004 và 1035 hay lỗi riêng của 1035?"
    all_terms = extract_content_terms(query)
    filtered_terms = extract_evidence_terms(query)

    assert "ủng" in all_terms
    assert "hộ" in all_terms
    assert "chung" in all_terms
    assert "riêng" in all_terms
    assert "hay" in all_terms
    assert "và" in all_terms
    assert "của" in all_terms

    assert "ủng" not in filtered_terms
    assert "hộ" not in filtered_terms
    assert "chung" not in filtered_terms
    assert "riêng" not in filtered_terms
    assert "hay" not in filtered_terms
    assert "và" not in filtered_terms
    assert "của" not in filtered_terms

    expected = ("dữ", "liệu", "hiện", "tại", "lỗi", "1004", "1035")
    assert filtered_terms == expected


def test_q0695_wrongful_abstain_unblocked():
    """Verify that Q0695 passes the 0.60 evidence coverage threshold with filtered terms."""
    query = "Dữ liệu hiện tại ủng hộ lỗi chung của 1004 và 1035 hay lỗi riêng của 1035?"
    plan = build_query_plan(query)

    # Simulated evidence items containing beam/jig findings for 1004 and 1035
    evidence_text = (
        "Dữ liệu kiểm tra lỗi hiện tại của Jig 1035 và 1004. "
        "Y_BeamH_Camera 140_to bất thường phát sinh tại 1035."
    )
    item = EvidenceItem(
        evidence_id="EVD-01",
        citation_id="[1]",
        citation_label="Y_BeamH_Camera 140_to bất thường.pptx",
        chunk_id="chk-01",
        document_id="doc-01",
        source_name="Y_BeamH_Camera 140_to bất thường.pptx",
        source_path="",
        file_type="pptx",
        text=evidence_text,
        snippet=evidence_text,
        score=9.5,
        rank=1,
        ranking_signals={},
        matched_terms=("dữ", "liệu", "hiện", "tại", "lỗi", "1004", "1035"),
        term_coverage=1.0,
        privacy_labels=(),
        element_types=(),
    )

    cov = _final_evidence_relevance([item], plan)
    assert cov >= 0.60, f"Q0695 coverage {cov:.4f} must be >= 0.60 to pass gate"
    assert cov == 1.0, f"Q0695 coverage should be 100% (7/7 terms), got {cov:.4f}"


def test_seven_short_diagnostic_questions_remain_fail_closed():
    """Two-way protection: ensure all 7 genuine insufficient questions remain strictly blocked (< 0.60)."""
    audit_file = Path("docs/phieu-viec/ket-qua/ket-qua-synth-evidence-gate-audit-home.json")
    if not audit_file.exists():
        pytest.skip("Audit data file not found")

    with audit_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    audit_map = {c["id"]: c for c in data["chi_tiet_10_cau_kiem_toan"]}
    blocked_ids = ["Q0620", "Q0668", "Q0824", "Q0843", "Q0849", "Q0850", "Q1034"]

    for qid in blocked_ids:
        c = audit_map[qid]
        plan = build_query_plan(c["cau_hoi"])
        items = [
            EvidenceItem(
                evidence_id=f"EVD-{i}",
                citation_id=it.get("citation_id", f"[{i+1}]"),
                citation_label=it.get("source", "src"),
                chunk_id=f"chk-{i}",
                document_id=f"doc-{i}",
                source_name=it.get("source", "src"),
                source_path="",
                file_type="test",
                text=it.get("full_text") or it.get("text_snippet", ""),
                snippet=it.get("text_snippet", ""),
                score=it.get("score", 1.0),
                rank=i + 1,
                ranking_signals={},
                matched_terms=tuple(it.get("matched_terms", ())),
                term_coverage=it.get("term_coverage", 0.2),
                privacy_labels=(),
                element_types=(),
            )
            for i, it in enumerate(c.get("items", []))
        ]

        cov = _final_evidence_relevance(items, plan)
        assert cov < 0.60, (
            f"Question {qid} must remain blocked by fail-closed gate! Got coverage {cov:.4f} >= 0.60"
        )
