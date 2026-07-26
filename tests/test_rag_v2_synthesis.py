from aios_habit.rag_v2.evidence import (
    EvidenceAnswerMode,
    EvidenceConfidence,
    build_evidence_pack,
)
from aios_habit.rag_v2.index import SearchResponse, SearchResult, SearchSummary
from aios_habit.rag_v2.synthesis import (
    build_synthesis_plan,
    format_provider_synthesis_contract,
    synthesize_evidence,
    validate_provider_synthesis_answer,
)


def _make_result(chunk_id, doc_id, score, text, ranking_signals=None):
    return SearchResult(
        chunk_id=chunk_id,
        score=score,
        text=text,
        document_id=doc_id,
        source_path=f"/workspace/{doc_id}.txt",
        source_name=f"{doc_id}.txt",
        file_type="txt",
        metadata={},
        privacy_labels=("allowed",),
        ranking_signals=ranking_signals or {"lexical": score},
        matched_terms=("error",),
        term_coverage=1.0,
    )


def _make_response(results):
    return SearchResponse(
        results=tuple(results),
        summary=SearchSummary(
            query="troubleshoot production error",
            indexed_chunk_count=len(results),
            eligible_chunk_count=len(results),
            candidate_count=len(results),
            returned_count=len(results),
        ),
    )


def test_synthesize_evidence_diagnosis_shape_formatting():
    results = [
        _make_result("c1", "d1", 5.0, "Error 404 occurs when database connection drops."),
        _make_result("c2", "d1", 4.0, "Verify database credentials and check network socket."),
        _make_result("c3", "d1", 3.5, "Restart connection pool to resolve the issue."),
    ]
    pack = build_evidence_pack("What errors occur and how to fix them?", _make_response(results))
    result = synthesize_evidence(pack, answer_shape="diagnosis")

    assert result.grounded is True
    assert result.abstained is False
    assert "SYMPTOMS:" in result.answer
    assert "CHECKS:" in result.answer
    assert "ACTIONS:" in result.answer
    assert "[1]" in result.answer


def test_synthesize_evidence_procedure_shape_formatting():
    results = [
        _make_result("c1", "d1", 5.0, "Step 1: Check initial system status."),
        _make_result("c2", "d1", 4.0, "Step 2: Run deployment script."),
        _make_result("c3", "d1", 3.0, "Step 3: Validate service availability."),
    ]
    pack = build_evidence_pack("How to deploy service?", _make_response(results))
    result = synthesize_evidence(pack, answer_shape="procedure")

    assert result.grounded is True
    assert "PRECHECKS:" in result.answer
    assert "STEPS:" in result.answer
    assert "POSTCHECKS:" in result.answer


def test_diagnosis_synthesis_contract_format():
    results = [_make_result("c1", "d1", 5.0, "Error code E01 requires system restart.")]
    pack = build_evidence_pack("What error handling is needed?", _make_response(results))
    plan = build_synthesis_plan(pack, answer_shape="diagnosis")
    contract = format_provider_synthesis_contract(plan)

    assert "SYMPTOMS:" in contract
    assert "CHECKS:" in contract
    assert "ACTIONS:" in contract


def test_validate_provider_diagnosis_answer_pass():
    results = [_make_result("c1", "d1", 5.0, "Error code E01 requires system restart.")]
    pack = build_evidence_pack("What error handling is needed?", _make_response(results))
    plan = build_synthesis_plan(pack, answer_shape="diagnosis")

    valid_answer = (
        "SYMPTOMS:\n- Error code E01 is observed [1]\n"
        "CHECKS:\n- Verify system logs for E01 [1]\n"
        "ACTIONS:\n- Restart system [1]"
    )
    validation = validate_provider_synthesis_answer(pack, valid_answer, plan)

    assert validation.valid is True
    assert validation.errors == ()
