"""E2 round 3 (Phase A): table-name noise + unnamed .exe anchor.

These tests reproduce the E2v2 failures with SIMULATED fixtures derived from
the real E2v2 dump (docs/phieu-viec/ket-qua/VE_E2_vong2_chon-dong.md):

- B5 lost the HOUSE_METHOD definition row: `_extract_field_codes` counted the
  table name T_PARTS_RECIEVE as a field code, so the table-overview fragment
  tied the definition fragment 1-1 on the field-code key and won on value
  count. Table names (T_*) must not count as field codes, and the field-code
  priority must prefer the fragment that actually defines the field
  (code + encoded '0'/'1' values) over prose that merely mentions it.
- B2 lost YY2-Z151.exe / YY2-Z152.exe: the question only said "tên tệp thực
  thi (.exe)" without naming files, so `_extract_file_identifiers` returned
  () and the file-identifier priority never fired for any fragment. When the
  question signals an executable file but names none, the pack's own *.exe
  identifiers become the anchor.

All fixtures are SIMULATED_* and based on the real report; they do not touch
real data or indexes.
"""
from aios_habit.rag_v2.evidence import build_evidence_pack
from aios_habit.rag_v2.index import SearchResponse, SearchResult, SearchSummary
from aios_habit.rag_v2.synthesis import (
    _best_fragment,
    _extract_field_codes,
    _extract_file_identifiers,
    _pack_file_identifiers,
    _synthesis_query_terms,
    synthesize_evidence,
)


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


# ---------------------------------------------------------------------------
# (a) B5-like: table-name noise must not steal the field-code priority.
# ---------------------------------------------------------------------------

# SIMULATED table-overview fragment: names T_PARTS_RECIEVE, carries many
# quoted values (like real E2v2 fragment [3], answer_value 12), but does NOT
# define HOUSE_METHOD.
_SIMULATED_V3_TABLE_OVERVIEW = (
    "SIMULATED_ Bang T_PARTS_RECIEVE quan ly thong tin nhap kho linh kien. "
    "Cac cot: RECV_ID char 'R001' 'R002' 'R003', RECV_DATE date '2024-01-01' "
    "'2024-01-02', QTY number '10' '20' '30', VENDOR_CD varchar 'V01' 'V02', "
    "STATUS_CD char 'A' 'B' 'C' 'D', WAREHOUSE_CD varchar 'W1' 'W2' 'W3'."
)

# SIMULATED definition row: HOUSE_METHOD with encoded '0'/'1' values
# (like real E2v2 fragment [12], answer_value 11).
_SIMULATED_V3_DEFINITION_ROW = (
    "SIMULATED_ 19 \u683c\u7d0d\u65b9\u6cd5 HOUSE_METHOD varchar "
    "'0':\u5009\u5eab\u3078\u683c\u7d0d '1':\u691c\u67fb"
)

# SIMULATED prose that merely mentions HOUSE_METHOD without defining it:
# it must not outrank the definition row.
_SIMULATED_V3_MERE_MENTION = (
    "SIMULATED_ Ghi chu van hanh: truong HOUSE_METHOD duoc dung trong bao cao "
    "ton kho hang ngay cua bo phan ke hoach."
)


def test_e2v3_table_names_excluded_from_field_codes():
    """Unit: T_* tokens are table names, not field codes."""
    assert _extract_field_codes(
        "Truong HOUSE_METHOD trong bang T_PARTS_RECIEVE co y nghia gi?"
    ) == ("house_method",)
    assert _extract_field_codes(
        "Bang T_IF_PROD_RESULT va T_PARTS_RECIEVE khac nhau the nao?"
    ) == ()


def test_e2v3_b5_definition_row_beats_table_overview():
    """B5-like: the definition row must win over the value-rich table fragment.

    Reproduces the real E2v2 tie: before the fix the overview fragment tied
    1-1 on the field-code key (via T_PARTS_RECIEVE) and won on value count.
    """
    query = "Truong HOUSE_METHOD trong bang T_PARTS_RECIEVE co y nghia gi?"
    terms = ("truong", "house_method", "bang", "t_parts_recieve", "y", "nghia")
    results = [
        _make_result("c1", "d1", 30.0, "SIMULATED_ Tong quan he thong.",
                     matched_terms=terms),
        _make_result("c2", "d2", 25.0, _SIMULATED_V3_TABLE_OVERVIEW,
                     matched_terms=terms),
        _make_result("c3", "d3", 20.0, _SIMULATED_V3_DEFINITION_ROW,
                     matched_terms=terms),
        _make_result("c4", "d4", 15.0, "SIMULATED_ Ghi chu bao tri.",
                     matched_terms=terms),
    ]
    pack = build_evidence_pack(query, _make_response(query, results))
    result = synthesize_evidence(pack, answer_shape="grounded_summary")

    assert result.grounded is True
    assert "HOUSE_METHOD" in result.answer
    assert "\u5009\u5eab" in result.answer  # warehouse (格納)
    assert "\u691c\u67fb" in result.answer  # inspection (検査)


def test_e2v3_b5_definition_row_beats_mere_mention():
    """Unit: a fragment defining the field beats one that only names it."""
    query = "Truong HOUSE_METHOD trong bang T_PARTS_RECIEVE co y nghia gi?"
    query_terms = _synthesis_query_terms(query, prioritize_literals=True)
    field_codes = _extract_field_codes(query)
    assert field_codes == ("house_method",)

    class _Item:
        snippet = (
            _SIMULATED_V3_MERE_MENTION + "\n" + _SIMULATED_V3_DEFINITION_ROW
        )
        text = snippet

    fragment = _best_fragment(
        _Item(),
        query_terms=query_terms,
        prioritize_literals=True,
        field_codes=field_codes,
    )
    assert "HOUSE_METHOD" in fragment
    assert "\u5009\u5eab" in fragment


# ---------------------------------------------------------------------------
# (b) B2-like: unnamed .exe anchor falls back to the pack's own identifiers.
# ---------------------------------------------------------------------------

# SIMULATED B2 chunk: names the two installer files (real E2 chunk [1]).
_SIMULATED_V3_B2_CHUNK = (
    "SIMULATED_ [Trong truong hop cua Matecon CTU] YY2-Z151.exe YY2-Z152.exe "
    "la bo cai dat can thiet."
)


def test_e2v3_unnamed_exe_question_extracts_no_identifiers():
    """Unit: a generic '*.exe' question yields no named identifiers..."""
    query = "Ten tep thuc thi (.exe) nao can thiet de cai dat?"
    assert _extract_file_identifiers(query) == ()


def test_e2v3_pack_file_identifiers_collects_exe_names():
    """Unit: the pack fallback collects *.exe names from pack text."""
    query = "Ten tep thuc thi (.exe) nao can thiet de cai dat?"
    terms = ("ten", "tep", "thuc", "thi", "exe", "can", "thiet", "cai", "dat")
    results = [
        _make_result("c1", "d1", 30.0, _SIMULATED_V3_B2_CHUNK,
                     matched_terms=terms),
        _make_result("c2", "d2", 20.0, "SIMULATED_ Tai lieu chung.",
                     matched_terms=terms),
    ]
    pack = build_evidence_pack(query, _make_response(query, results))
    assert _pack_file_identifiers(pack) == ("yy2-z151.exe", "yy2-z152.exe")


def test_e2v3_b2_unnamed_exe_fragment_selected():
    """B2-like: a generic '.exe' question must select the fragment holding
    the pack's *.exe identifiers, even against value-rich decoys."""
    query = "Ten tep thuc thi (.exe) nao can thiet de cai dat?"
    terms = ("ten", "tep", "thuc", "thi", "exe", "can", "thiet", "cai", "dat")
    results = [
        _make_result(
            "c1", "d1", 40.0,
            "SIMULATED_ Bao cao tong hop nhieu ma: ABC-123 XYZ-999 QWE-456 "
            "voi cac gia tri 'x1' 'x2' 'x3' 'x4' 'x5' 'x6'.",
            matched_terms=terms,
        ),
        _make_result(
            "c2", "d2", 35.0,
            "SIMULATED_ Danh sach phien ban: v1.2.3 v2.0.1 v3.4.5 "
            "ma so 111 222 333 444 555.",
            matched_terms=terms,
        ),
        _make_result("c3", "d3", 29.0, _SIMULATED_V3_B2_CHUNK,
                     matched_terms=terms),
        _make_result(
            "c4", "d4", 20.0,
            "SIMULATED_ Tai lieu ky thuat chung khong lien quan.",
            matched_terms=terms,
        ),
    ]
    pack = build_evidence_pack(query, _make_response(query, results))
    result = synthesize_evidence(pack, answer_shape="grounded_summary")

    assert result.grounded is True
    assert "YY2-Z151.exe" in result.answer
    assert "YY2-Z152.exe" in result.answer
