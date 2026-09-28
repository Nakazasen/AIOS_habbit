"""E2 round 2 (Phase A): line selection by field code and file identifier.

These tests reproduce the E2 failures with SIMULATED fixtures derived from the
real E2 evidence report (docs/phieu-viec/ket-qua/VE_E2_fix-synthesis.md):

- B5 dropped the HOUSE_METHOD definition row: the Japanese table chunk held
  several rows, and the fragment picker chose a row with more quoted values
  (ORICON_STATUS) instead of the row defining the field named in the question.
- B2 dropped YY2-Z151.exe / YY2-Z152.exe even though the evidence pack held
  them: generic identifier/value counts outranked the exact file tokens.

All fixtures are SIMULATED_* and based on the real report; they do not touch
real data or indexes.
"""
from aios_habit.rag_v2.evidence import build_evidence_pack
from aios_habit.rag_v2.index import SearchResponse, SearchResult, SearchSummary
from aios_habit.rag_v2.synthesis import synthesize_evidence


def _make_result(
    chunk_id,
    doc_id,
    score,
    text,
    ranking_signals=None,
    matched_terms=("error",),
    matched_obligations=(),
    matched_facets=(),
    privacy_labels=("allowed",),
):
    return SearchResult(
        chunk_id=chunk_id,
        score=score,
        text=text,
        document_id=doc_id,
        source_path=f"/workspace/{doc_id}.txt",
        source_name=f"{doc_id}.txt",
        file_type="txt",
        metadata={},
        privacy_labels=privacy_labels,
        ranking_signals=ranking_signals or {"lexical": score},
        matched_terms=matched_terms,
        term_coverage=1.0,
        matched_query_facets=matched_facets,
        matched_obligations=matched_obligations,
    )


def _make_response(query, results):
    return SearchResponse(
        results=tuple(results),
        summary=SearchSummary(
            query=query,
            indexed_chunk_count=len(results),
            eligible_chunk_count=len(results),
            candidate_count=len(results),
            returned_count=len(results),
        ),
    )


# SIMULATED B5 fixture: Japanese column-definition table. Row 19 defines the
# field named in the question (HOUSE_METHOD); row 18 carries more quoted
# values and must NOT win the fragment pick. Based on the real E2 [12] chunk
# (wsc-ff8304af86028eaa474a1706).
_SIMULATED_B5_TABLE = (
    "SIMULATED_ 18 \u30aa\u30ea\u30b3\u30f3\u72b6\u614b ORICON_STATUS varchar "
    "\u30aa\u30ea\u30b3\u30f3\u306e\u30c1\u30a7\u30c3\u30af\u7d50\u679c\u72b6\u614b\u3092\u793a\u3059\u30b3\u30fc\u30c9 "
    "'A':'\u81ea\u52d5' 'B':'\u624b\u52d5' 'C':'\u4fdd\u7559'\n"
    "SIMULATED_ 19 \u683c\u7d0d\u65b9\u6cd5 HOUSE_METHOD varchar "
    "'0':\u5009\u5eab\u3078\u683c\u7d0d'1':\u691c\u67fb\n"
    "SIMULATED_ 20 \u8377\u53d7 SLIP_READ_HTID varchar ID"
)

# SIMULATED false-positive guard: another field (RECEIVE_TYPE) also uses
# '0'/'1' quoted codes. Its row must not be mistaken for HOUSE_METHOD.
_SIMULATED_B5_FALSE_POSITIVE = (
    "SIMULATED_ 21 \u53d7\u5165\u7a2e\u5225 RECEIVE_TYPE varchar "
    "'0':\u901a\u5e38\u5165\u5eab'1':\u30de\u30cb\u30e5\u30a2\u30eb\u5165\u5eab"
)


def test_e2v2_b5_field_code_row_selected_mid_pack():
    """B5-like: the HOUSE_METHOD definition row must be picked from the table."""
    query = "Truong HOUSE_METHOD co y nghia gi trong bang dinh nghia cot?"
    terms = ("truong", "house_method", "y", "nghia", "bang", "dinh")
    results = [
        _make_result("c1", "d1", 30.0, "SIMULATED_ Tong quan he thong quan ly kho.",
                     matched_terms=terms),
        _make_result("c2", "d2", 25.0, "SIMULATED_ Huong dan van hanh chung.",
                     matched_terms=terms),
        _make_result("c3", "d3", 20.0, _SIMULATED_B5_TABLE, matched_terms=terms),
        _make_result("c4", "d4", 15.0, _SIMULATED_B5_FALSE_POSITIVE,
                     matched_terms=terms),
        _make_result("c5", "d5", 10.0, "SIMULATED_ Ghi chu bao tri dinh ky.",
                     matched_terms=terms),
    ]
    pack = build_evidence_pack(query, _make_response(query, results))
    result = synthesize_evidence(pack, answer_shape="grounded_summary")

    assert result.grounded is True
    assert "HOUSE_METHOD" in result.answer
    # The definition values of the asked field, not the RECEIVE_TYPE row.
    assert "\u5009\u5eab" in result.answer  # warehouse (格納)
    assert "\u691c\u67fb" in result.answer  # inspection (検査)


def test_e2v2_b5_field_code_beats_richer_row():
    """The asked field-code row wins even when a sibling row has more values."""
    query = "Giai thich y nghia truong ORICON_STATUS?"
    terms = ("giai", "thich", "y", "nghia", "truong", "oricon_status")
    results = [
        _make_result("c1", "d1", 30.0, "SIMULATED_ Tong quan.", matched_terms=terms),
        _make_result("c2", "d2", 20.0, _SIMULATED_B5_TABLE, matched_terms=terms),
        _make_result("c3", "d3", 10.0, "SIMULATED_ Ghi chu.", matched_terms=terms),
    ]
    pack = build_evidence_pack(query, _make_response(query, results))
    result = synthesize_evidence(pack, answer_shape="grounded_summary")

    assert result.grounded is True
    assert "ORICON_STATUS" in result.answer


# SIMULATED B2 fixture: the chunk names the two installer files. Based on the
# real E2 [1] chunk (wsc-5035a3d752d88cc0e20eb4c3).
_SIMULATED_B2_CHUNK = (
    "SIMULATED_ [Trong truong hop cua Matecon CTU] YY2-Z151.exe YY2-Z152.exe "
    "la bo cai dat can thiet."
)


def test_e2v2_b2_exe_identifiers_not_demoted():
    """B2-like: *.exe tokens named in the question must survive value ranking."""
    query = "File YY2-Z151.exe va YY2-Z152.exe dung de lam gi?"
    terms = ("file", "yy2-z151.exe", "yy2-z152.exe", "dung", "lam")
    results = [
        _make_result(
            "c1", "d1", 40.0,
            "SIMULATED_ Bao cao tong hop nhieu ma: ABC-123 XYZ-999 QWE-456 "
            "voi cac gia tri 'x1' 'x2' 'x3' 'x4'.",
            matched_terms=terms,
        ),
        _make_result(
            "c2", "d2", 35.0,
            "SIMULATED_ Danh sach phien ban: v1.2.3 v2.0.1 v3.4.5 "
            "ma so 111 222 333 444.",
            matched_terms=terms,
        ),
        _make_result("c3", "d3", 29.0, _SIMULATED_B2_CHUNK, matched_terms=terms),
        _make_result(
            "c4", "d4", 20.0,
            "SIMULATED_ Tai lieu ky thuat chung khong lien quan.",
            matched_terms=terms,
        ),
        _make_result(
            "c5", "d5", 15.0,
            "SIMULATED_ Ghi chu van hanh hang ngay.",
            matched_terms=terms,
        ),
    ]
    pack = build_evidence_pack(query, _make_response(query, results))
    result = synthesize_evidence(pack, answer_shape="grounded_summary")

    assert result.grounded is True
    assert "YY2-Z151.exe" in result.answer
    assert "YY2-Z152.exe" in result.answer


def test_e2v2_b5_fragment_picker_prefers_asked_field_code():
    """Unit: _best_fragment must pick the row defining the asked field code.

    The ORICON_STATUS row carries more quoted values; without the field-code
    priority the picker chooses it and the HOUSE_METHOD definition is lost.
    """
    from aios_habit.rag_v2.synthesis import (
        _best_fragment,
        _extract_field_codes,
        _synthesis_query_terms,
    )

    query = "Truong HOUSE_METHOD co y nghia gi?"
    query_terms = _synthesis_query_terms(query, prioritize_literals=True)
    field_codes = _extract_field_codes(query)

    class _Item:
        snippet = _SIMULATED_B5_TABLE
        text = _SIMULATED_B5_TABLE

    fragment = _best_fragment(
        _Item(),
        query_terms=query_terms,
        prioritize_literals=True,
        field_codes=field_codes,
    )
    assert "HOUSE_METHOD" in fragment
    assert "\u5009\u5eab" in fragment


def test_e2v2_b1_b3_regression_values_preserved():
    """B1/B3-like: previously passing literal values must not be lost."""
    query = "Cac ma loi 11922 12860 12626 va kieu nvarchar(4000) co y nghia gi?"
    terms = ("ma", "loi", "11922", "12860", "12626", "kieu", "nvarchar(4000)")
    results = [
        _make_result(
            "c1", "d1", 30.0,
            "SIMULATED_ Ma loi 11922 12860 12626 xuat hien trong nhat ky.",
            matched_terms=terms,
        ),
        _make_result(
            "c2", "d2", 25.0,
            "SIMULATED_ Cot mo ta kieu nvarchar(4000) trong bang.",
            matched_terms=terms,
        ),
        _make_result(
            "c3", "d3", 20.0,
            "SIMULATED_ Ghi chu chung khong co ma cu the.",
            matched_terms=terms,
        ),
    ]
    pack = build_evidence_pack(query, _make_response(query, results))
    result = synthesize_evidence(pack, answer_shape="grounded_summary")

    assert result.grounded is True
    assert "11922" in result.answer
    assert "12860" in result.answer
    assert "12626" in result.answer
    assert "nvarchar(4000)" in result.answer
