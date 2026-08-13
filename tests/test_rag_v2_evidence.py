from dataclasses import replace

from aios_habit.rag_v2.index import SearchOptions, SearchResponse, SearchResult, SearchSummary
from aios_habit.rag_v2.query_planning import extract_content_terms
from aios_habit.rag_v2.evidence import (
    EvidenceAnswerMode,
    EvidenceConfidence,
    EvidencePackConfig,
    build_evidence_pack,
    evidence_pack_to_dict,
    format_evidence_for_prompt,
)
from aios_habit.rag_v2.synthesis import (
    GroundedClaim,
    build_synthesis_plan,
    format_provider_synthesis_contract,
    synthesize_evidence,
    validate_grounded_claims,
    validate_provider_synthesis_answer,
)


def _make_result(
    chunk_id,
    document_id,
    score,
    text="sample evidence text",
    *,
    source_name="notes.txt",
    source_path="/workspace/notes.txt",
    file_type="txt",
    privacy_labels=("allowed",),
    ranking_signals=None,
    matched_terms=None,
    term_coverage=1.0,
    matched_query_variant_ids=(),
    matched_query_facets=(),
    matched_obligations=(),
    metadata=None,
):
    fixture_metadata = dict(metadata or {})
    if matched_terms is None:
        fixture_metadata["fixture_auto_query_support"] = True
        matched_terms = ()
    return SearchResult(
        chunk_id=chunk_id,
        score=score,
        text=text,
        document_id=document_id,
        source_path=source_path,
        source_name=source_name,
        file_type=file_type,
        metadata=fixture_metadata,
        privacy_labels=privacy_labels,
        ranking_signals=ranking_signals or {"lexical": score},
        matched_terms=matched_terms,
        term_coverage=term_coverage,
        matched_query_variant_ids=matched_query_variant_ids,
        matched_query_facets=matched_query_facets,
        matched_obligations=matched_obligations,
    )


def _make_response(results, query="test query", **summary_kwargs):
    defaults = dict(
        query=query,
        indexed_chunk_count=len(results),
        eligible_chunk_count=len(results),
        candidate_count=len(results),
        returned_count=len(results),
    )
    defaults.update(summary_kwargs)
    supported_terms = extract_content_terms(query)
    normalized_results = tuple(
        replace(result, matched_terms=supported_terms)
        if result.metadata.get("fixture_auto_query_support")
        else result
        for result in results
    )
    return SearchResponse(
        results=normalized_results,
        summary=SearchSummary(**defaults),
    )


# --- Citation assignment ---------------------------------------------------

def test_citation_ids_assigned_in_rank_order():
    response = _make_response([
        _make_result("c1", "d1", 10.0),
        _make_result("c2", "d2", 5.0),
        _make_result("c3", "d3", 2.0),
    ])
    pack = build_evidence_pack("test query", response)

    assert [item.citation_id for item in pack.items] == ["[1]", "[2]", "[3]"]
    assert [item.rank for item in pack.items] == [1, 2, 3]
    assert pack.item_count == 3


# --- Confidence from strong results ----------------------------------------

def test_high_confidence_from_strong_multi_document_results():
    response = _make_response([
        _make_result("c1", "d1", 12.0),
        _make_result("c2", "d2", 8.0),
    ])
    pack = build_evidence_pack("test query", response)

    assert pack.confidence == EvidenceConfidence.HIGH
    assert pack.insufficiency_reasons == ()
    assert pack.top_score == 12.0


def test_medium_confidence_from_moderate_results():
    response = _make_response([
        _make_result("c1", "d1", 5.0),
    ])
    pack = build_evidence_pack("test query", response)

    assert pack.confidence == EvidenceConfidence.MEDIUM
    assert pack.insufficiency_reasons == ()


# --- Confidence degraded by retrieval insufficiency -------------------------

def test_confidence_capped_when_retrieval_has_insufficiency():
    response = _make_response(
        [_make_result("c1", "d1", 10.0)],
        insufficiency_reasons=("incomplete_query_term_coverage",),
    )
    pack = build_evidence_pack("test query", response)

    assert pack.confidence in {EvidenceConfidence.LOW, EvidenceConfidence.INSUFFICIENT}
    assert "incomplete_query_term_coverage" in pack.insufficiency_reasons
    assert pack.hard_insufficiency_reasons == ()
    assert pack.soft_warning_reasons == ("incomplete_query_term_coverage",)
    assert pack.answer_mode == EvidenceAnswerMode.ANSWER_WITH_LIMITS

    synthesis = synthesize_evidence(pack)
    assert synthesis.abstained is False
    assert synthesis.grounded is True
    assert synthesis.answer_mode == "answer_with_limits"
    assert synthesis.limitation_reasons == ("incomplete_query_term_coverage",)


# --- Confidence insufficient when no items ----------------------------------

def test_insufficient_confidence_when_no_results():
    response = _make_response(
        [],
        insufficiency_reasons=("no_indexed_chunks",),
    )
    pack = build_evidence_pack("test query", response)

    assert pack.confidence == EvidenceConfidence.INSUFFICIENT
    assert "no_indexed_chunks" in pack.insufficiency_reasons
    assert "no_indexed_chunks" in pack.hard_insufficiency_reasons
    assert "no_evidence_items" in pack.hard_insufficiency_reasons
    assert pack.soft_warning_reasons == ()
    assert pack.answer_mode == EvidenceAnswerMode.ABSTAIN
    assert pack.item_count == 0
    assert pack.top_score == 0.0


# --- Snippet truncation -----------------------------------------------------

def test_snippet_truncation_preserves_citation():
    long_text = "x" * 3000
    response = _make_response([
        _make_result("c1", "d1", 5.0, text=long_text),
    ])
    config = EvidencePackConfig(max_snippet_chars=100)
    pack = build_evidence_pack("test query", response, config=config)

    assert len(pack.items[0].snippet) == 103  # 100 + "..."
    assert pack.items[0].snippet.endswith("...")
    assert pack.items[0].text == long_text  # full text preserved
    assert pack.items[0].citation_id == "[1]"


# --- Privacy summary strictest-wins -----------------------------------------

def test_privacy_summary_local_only_wins():
    response = _make_response([
        _make_result("c1", "d1", 10.0, privacy_labels=("cloud_safe",)),
        _make_result("c2", "d2", 5.0, privacy_labels=("local_only",)),
    ])
    pack = build_evidence_pack("test query", response)

    assert pack.privacy_summary.local_only is True
    assert pack.privacy_summary.cloud_allowed is False
    assert pack.privacy_summary.overall_label == "local_only"


def test_privacy_summary_all_cloud_safe():
    response = _make_response([
        _make_result("c1", "d1", 10.0, privacy_labels=("cloud_safe",)),
        _make_result("c2", "d2", 5.0, privacy_labels=("cloud_safe",)),
    ])
    pack = build_evidence_pack("test query", response)

    assert pack.privacy_summary.local_only is False
    assert pack.privacy_summary.cloud_allowed is True
    assert pack.privacy_summary.overall_label == "cloud_safe"


# --- Prompt formatting ------------------------------------------------------

def test_prompt_formatting_includes_citations_and_warnings():
    response = _make_response(
        [_make_result("c1", "d1", 5.0, source_name="report.pdf")],
    )
    pack = build_evidence_pack("analysis query", response)
    text = format_evidence_for_prompt(pack)

    assert "[1]" in text
    assert "report.pdf" in text
    assert "analysis query" in text
    assert "sample evidence text" in text


def test_prompt_formatting_shows_insufficient_warning():
    response = _make_response(
        [],
        insufficiency_reasons=("no_lexical_or_metadata_match",),
    )
    pack = build_evidence_pack("missing query", response)
    text = format_evidence_for_prompt(pack)

    assert "Insufficient evidence" in text
    assert "no_lexical_or_metadata_match" in text


# --- Serialization roundtrip ------------------------------------------------

def test_evidence_pack_to_dict_produces_plain_dict():
    response = _make_response([
        _make_result("c1", "d1", 8.0),
    ])
    pack = build_evidence_pack("test query", response)
    d = evidence_pack_to_dict(pack)

    assert isinstance(d, dict)
    assert d["confidence"] == "medium"
    assert isinstance(d["items"], list)
    assert d["items"][0]["citation_id"] == "[1]"
    assert isinstance(d["privacy_summary"], dict)
    assert d["answer_mode"] == "answer"
    assert d["hard_insufficiency_reasons"] == []
    assert d["soft_warning_reasons"] == []
    assert d["pack_id"].startswith("PACK-")


# --- Per-document limit respected -------------------------------------------

def test_per_document_limit_caps_evidence_from_single_document():
    response = _make_response([
        _make_result("c1", "d1", 10.0),
        _make_result("c2", "d1", 9.0),
        _make_result("c3", "d1", 8.0),
        _make_result("c4", "d1", 7.0),
        _make_result("c5", "d2", 6.0),
    ])
    config = EvidencePackConfig(per_document_limit=2)
    pack = build_evidence_pack("test query", response, config=config)

    d1_items = [item for item in pack.items if item.document_id == "d1"]
    assert len(d1_items) == 2
    d2_items = [item for item in pack.items if item.document_id == "d2"]
    assert len(d2_items) == 1
    assert pack.item_count == 3


# --- Source and document counts ---------------------------------------------

def test_source_and_document_counts():
    response = _make_response([
        _make_result("c1", "d1", 10.0, source_name="report.pdf"),
        _make_result("c2", "d1", 5.0, source_name="report.pdf"),
        _make_result("c3", "d2", 3.0, source_name="notes.txt"),
    ])
    pack = build_evidence_pack("test query", response)

    assert pack.source_count == 2
    assert pack.document_count == 2
    assert pack.best_term_coverage == 1.0


# --- Location metadata extraction ------------------------------------------

def test_location_metadata_extracted():
    response = _make_response([
        _make_result(
            "c1", "d1", 5.0,
            metadata={"page": 3, "sheet": "Summary", "section_path": ["Chapter 1", "Intro"]},
        ),
    ])
    pack = build_evidence_pack("test query", response)

    item = pack.items[0]
    assert item.page == 3
    assert item.sheet == "Summary"
    assert item.section_path == ("Chapter 1", "Intro")


def test_granular_coordinates_survive_evidence_and_prompt_formatting():
    response = _make_response([
        _make_result(
            "table-1",
            "document-1",
            6.0,
            metadata={
                "sheet": "Metrics",
                "row_range": [2, 4],
                "column_range": [1, 3],
                "cell_range": "B3:D5",
                "bbox": [10, 20.5, 30, 40],
            },
        ),
    ])
    pack = build_evidence_pack("table query", response)
    item = pack.items[0]
    prompt = format_evidence_for_prompt(pack)
    serialized = evidence_pack_to_dict(pack)

    assert item.row_range == (2, 4)
    assert item.column_range == (1, 3)
    assert item.cell_range == "B3:D5"
    assert item.bbox == (10.0, 20.5, 30.0, 40.0)
    assert serialized["items"][0]["cell_range"] == "B3:D5"
    assert "Rows: 2-4" in prompt
    assert "Columns: 1-3" in prompt
    assert "Cells: B3:D5" in prompt


def test_evidence_confidence_uses_coverage_across_the_selected_set():
    response = _make_response(
        [
            _make_result("alpha", "d1", 5.0, term_coverage=0.5),
            _make_result("omega", "d2", 4.0, term_coverage=0.5),
        ],
        evidence_set_term_coverage=1.0,
    )
    pack = build_evidence_pack(
        "alpha omega",
        response,
        config=EvidencePackConfig(min_term_coverage=0.75),
    )

    assert pack.best_term_coverage == 1.0
    assert "weak_term_coverage" not in pack.insufficiency_reasons
    assert pack.confidence != EvidenceConfidence.INSUFFICIENT


def test_local_synthesis_emits_only_validated_cited_claims():
    pack = build_evidence_pack(
        "test query",
        _make_response([_make_result("c1", "d1", 5.0)]),
    )
    synthesis = synthesize_evidence(pack)

    assert synthesis.grounded is True
    assert synthesis.abstained is False
    assert synthesis.provider_used is False
    assert synthesis.citation_ids == ("[1]",)
    assert "[1]" in synthesis.answer
    assert validate_grounded_claims(pack, synthesis.claims) == ()

    invalid = GroundedClaim(
        text="unsupported claim",
        citation_ids=("[99]",),
        evidence_ids=("EVD-NOT-PRESENT",),
    )
    errors = validate_grounded_claims(pack, [invalid])
    assert "claim_1_unknown_citation" in errors
    assert "claim_1_evidence_mismatch" in errors


def test_local_synthesis_abstains_when_no_citable_evidence_exists():
    pack = build_evidence_pack(
        "missing query",
        _make_response([], insufficiency_reasons=("no_lexical_or_metadata_match",)),
    )
    synthesis = synthesize_evidence(pack)

    assert synthesis.abstained is True
    assert synthesis.grounded is False
    assert synthesis.claims == ()
    assert synthesis.citation_ids == ()
    assert synthesis.answer_mode == "abstain"
    assert "evidence_pack_insufficient" in synthesis.abstention_reasons
    assert "no_citable_evidence" in synthesis.abstention_reasons


def test_unknown_insufficiency_reason_fails_closed():
    pack = build_evidence_pack(
        "test query",
        _make_response(
            [_make_result("c1", "d1", 5.0)],
            insufficiency_reasons=("future_unclassified_condition",),
        ),
    )

    assert pack.answer_mode == EvidenceAnswerMode.ABSTAIN
    assert pack.hard_insufficiency_reasons == ("future_unclassified_condition",)
    assert synthesize_evidence(pack).abstained is True


def test_high_score_unrelated_evidence_abstains_with_final_relevance_reason():
    response = _make_response(
        [
            _make_result(
                "unrelated",
                "d1",
                100.0,
                text="Quarterly office catering was approved.",
                matched_terms=(),
            ),
        ],
        query="quantum propulsion verification protocol",
    )

    pack = build_evidence_pack("quantum propulsion verification protocol", response)
    synthesis = synthesize_evidence(pack)

    assert pack.final_evidence_term_coverage == 0.0
    assert "no_direct_query_evidence" in pack.hard_insufficiency_reasons
    assert pack.answer_mode == EvidenceAnswerMode.ABSTAIN
    assert synthesis.abstained is True
    assert synthesis.grounded is False
    assert synthesis.citation_ids == ()


def test_evidence_coverage_map_serializes_stable_ids_without_facet_text():
    response = _make_response(
        [
            _make_result(
                "alpha",
                "d1",
                5.0,
                matched_query_variant_ids=("facet_1",),
                matched_query_facets=("facet_1",),
            ),
            _make_result(
                "omega",
                "d2",
                4.0,
                matched_query_variant_ids=("facet_2",),
                matched_query_facets=("facet_2",),
            ),
        ],
        planned_facet_ids=("query", "facet_1", "facet_2", "facet_3"),
        covered_facet_ids=("facet_1", "facet_2"),
        missing_facet_ids=("query", "facet_3"),
    )
    pack = build_evidence_pack("private facet wording", response)
    serialized = evidence_pack_to_dict(pack)

    assert [item.status for item in pack.coverage_map] == [
        "missing",
        "covered",
        "covered",
        "missing",
    ]
    assert pack.coverage_map[1].citation_ids == ("[1]",)
    assert pack.coverage_map[2].citation_ids == ("[2]",)
    assert serialized["coverage_map"][1]["facet_id"] == "facet_1"
    assert "private facet wording" not in str(serialized["coverage_map"])


def test_synthesis_plan_is_bounded_and_does_not_copy_private_query_text():
    response = _make_response(
        [
            _make_result(
                "alpha fact",
                "d1",
                5.0,
                matched_query_variant_ids=("facet_1",),
                matched_query_facets=("facet_1",),
            ),
        ],
        planned_facet_ids=("query", "facet_1", "facet_2"),
        covered_facet_ids=("facet_1",),
        missing_facet_ids=("query", "facet_2"),
    )
    pack = build_evidence_pack("private customer acquisition wording", response)

    plan = build_synthesis_plan(pack, answer_shape="actionable_output", max_claims=3)
    contract = format_provider_synthesis_contract(plan)

    assert plan.answer_shape == "actionable_output"
    assert plan.max_claims == 3
    assert plan.allowed_citation_ids == ("[1]",)
    assert plan.required_facet_ids == ("facet_1",)
    assert plan.missing_facet_ids == ("facet_2",)
    assert "private customer acquisition wording" not in contract
    assert "alpha fact" not in contract


def test_provider_synthesis_validation_accepts_cited_multi_facet_answer():
    response = _make_response(
        [
            _make_result(
                "alpha fact",
                "d1",
                5.0,
                matched_query_variant_ids=("facet_1",),
                matched_query_facets=("facet_1",),
            ),
            _make_result(
                "omega fact",
                "d2",
                4.0,
                matched_query_variant_ids=("facet_2",),
                matched_query_facets=("facet_2",),
            ),
        ],
        planned_facet_ids=("query", "facet_1", "facet_2"),
        covered_facet_ids=("facet_1", "facet_2"),
    )
    pack = build_evidence_pack("alpha omega", response)
    plan = build_synthesis_plan(pack, max_claims=2)

    validation = validate_provider_synthesis_answer(
        pack,
        "- Alpha is documented [1]\n- Omega is documented [2]",
        plan,
    )

    assert validation.valid is True
    assert validation.citation_ids == ("[1]", "[2]")
    assert validation.material_claim_count == 2
    assert validation.covered_facet_ids == ("facet_1", "facet_2")
    assert validation.errors == ()


def test_provider_synthesis_validation_rejects_unknown_uncited_and_uncovered_claims():
    response = _make_response(
        [
            _make_result(
                "alpha fact",
                "d1",
                5.0,
                matched_query_variant_ids=("facet_1",),
                matched_query_facets=("facet_1",),
            ),
            _make_result(
                "omega fact",
                "d2",
                4.0,
                matched_query_variant_ids=("facet_2",),
                matched_query_facets=("facet_2",),
            ),
        ],
        planned_facet_ids=("query", "facet_1", "facet_2"),
        covered_facet_ids=("facet_1", "facet_2"),
    )
    pack = build_evidence_pack("alpha omega", response)
    plan = build_synthesis_plan(pack, max_claims=2)

    validation = validate_provider_synthesis_answer(
        pack,
        "Unsupported line\nOnly alpha [1]\nUnknown source [99]",
        plan,
    )

    assert validation.valid is False
    assert "provider_answer_unknown_citation" in validation.errors
    assert "provider_answer_uncited_material_claim" in validation.errors
    assert "provider_answer_claim_budget_exceeded" in validation.errors
    assert "provider_answer_missing_required_facet_citation" in validation.errors


def test_provider_synthesis_validation_requires_exact_limitation_marker():
    response = _make_response(
        [_make_result("alpha fact", "d1", 5.0)],
        planned_facet_ids=("query", "facet_1"),
        missing_facet_ids=("query", "facet_1"),
        insufficiency_reasons=("weak_query_term_coverage",),
    )
    pack = build_evidence_pack("alpha omega", response)
    plan = build_synthesis_plan(pack, max_claims=1)

    missing_marker = validate_provider_synthesis_answer(
        pack,
        "Only alpha is documented [1]",
        plan,
    )
    marker = f"LIMITATIONS: {', '.join(plan.limitation_reasons)}"
    valid = validate_provider_synthesis_answer(
        pack,
        f"Only alpha is documented [1]\n{marker}",
        plan,
    )

    assert "provider_answer_missing_required_limitations" in missing_marker.errors
    assert valid.valid is True
    assert valid.material_claim_count == 1


def test_provider_synthesis_validation_traces_critical_literals_to_cited_evidence():
    pack = build_evidence_pack(
        "launch date",
        _make_response([
            _make_result(
                "launch-fact",
                "d1",
                5.0,
                text="The project launch date is 2031-04-09 and the release code is REL-42.",
            ),
        ]),
    )
    plan = build_synthesis_plan(pack, max_claims=1)

    supported = validate_provider_synthesis_answer(
        pack,
        "The launch date is 2031-04-09 under release REL-42 [1]",
        plan,
    )
    unsupported = validate_provider_synthesis_answer(
        pack,
        "The launch date is 2032-05-10 under release REL-99 [1]",
        plan,
    )

    assert supported.valid is True
    assert "provider_answer_unsupported_critical_literal" in unsupported.errors


def test_provider_synthesis_validation_enforces_actionable_shape_markers():
    pack = build_evidence_pack(
        "release procedure",
        _make_response([_make_result("Verify access, deploy, then validate.", "d1", 5.0)]),
    )
    plan = build_synthesis_plan(pack, answer_shape="procedure", max_claims=3)

    missing_shape = validate_provider_synthesis_answer(
        pack,
        "Verify access, deploy, then validate [1]",
        plan,
    )
    valid = validate_provider_synthesis_answer(
        pack,
        "PRECHECKS:\n- Verify access [1]\nSTEPS:\n- Deploy [1]\nPOSTCHECKS:\n- Validate [1]",
        plan,
    )

    assert "provider_answer_shape_contract_failed" in missing_shape.errors
    assert valid.valid is True
    assert valid.material_claim_count == 3


def test_missing_required_obligation_becomes_a_limit_and_never_an_invented_claim():
    response = _make_response(
        [
            _make_result(
                "problem",
                "d1",
                5.0,
                text="A service outage is reported.",
                matched_terms=("service", "unavailable", "recover"),
                matched_obligations=("problem",),
            )
        ],
        planned_obligation_ids=("problem", "check", "action"),
        covered_obligation_ids=("problem",),
        missing_obligation_ids=("check", "action"),
    )
    pack = build_evidence_pack("Why is service unavailable and how do I recover?", response)
    synthesis = synthesize_evidence(pack, answer_shape="diagnosis")

    assert pack.answer_mode == EvidenceAnswerMode.ABSTAIN
    assert "final_evidence_query_coverage_below_threshold" in pack.hard_insufficiency_reasons
    assert synthesis.abstained is True
    assert synthesis.grounded is False
    assert "Verify log and operational status" not in synthesis.answer
    assert "Refer to documented resolution steps" not in synthesis.answer


def test_evidence_obligation_coverage_serializes_without_source_text():
    response = _make_response(
        [_make_result("check", "d1", 5.0, matched_obligations=("check",))],
        planned_obligation_ids=("problem", "check", "action"),
        covered_obligation_ids=("check",),
        missing_obligation_ids=("problem", "action"),
    )
    pack = build_evidence_pack("private question", response)
    serialized = evidence_pack_to_dict(pack)

    assert [item.status for item in pack.obligation_coverage_map] == ["missing", "covered", "missing"]
    assert serialized["obligation_coverage_map"][1]["obligation_id"] == "check"
    assert "private question" not in str(serialized["obligation_coverage_map"])
def test_generic_query_boilerplate_does_not_count_as_final_evidence_support():
    query = "What specific blockchain-based quality assurance mechanism does the system use?"
    response = _make_response([
        _make_result(
            "c1", "d1", 8.0,
            "The system uses a documented quality procedure.",
            matched_terms=("system", "use"),
        )
    ], query=query)

    pack = build_evidence_pack(query, response)
    result = synthesize_evidence(pack)

    assert pack.final_evidence_term_coverage < 0.6
    assert "final_evidence_query_coverage_below_threshold" in pack.hard_insufficiency_reasons
    assert result.abstained is True
    assert result.grounded is False
