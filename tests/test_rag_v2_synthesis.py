from aios_habit.rag_v2.evidence import (
    EvidenceAnswerMode,
    EvidenceConfidence,
    build_evidence_pack,
)
from aios_habit.rag_v2.index import SearchResponse, SearchResult, SearchSummary
from aios_habit.rag_v2.synthesis import (
    build_synthesis_plan,
    format_provider_synthesis_contract,
    provider_validation_is_repairable,
    synthesize_evidence,
    synthesize_with_provider,
    validate_provider_synthesis_answer,
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
    source_name=None,
    source_path=None,
    file_type="txt",
    metadata=None,
):
    return SearchResult(
        chunk_id=chunk_id,
        score=score,
        text=text,
        document_id=doc_id,
        source_path=source_path or f"/workspace/{doc_id}.txt",
        source_name=source_name or f"{doc_id}.txt",
        file_type=file_type,
        metadata=metadata or {},
        privacy_labels=privacy_labels,
        ranking_signals=ranking_signals or {"lexical": score},
        matched_terms=matched_terms,
        term_coverage=1.0,
        matched_query_facets=matched_facets,
        matched_obligations=matched_obligations,
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
        _make_result(
            "c1", "d1", 5.0,
            "Error 404 occurs when database connection drops.",
            matched_terms=("errors", "occur", "fix", "them"),
            matched_obligations=("problem",),
        ),
        _make_result(
            "c2", "d1", 4.0,
            "Verify database credentials and check network socket.",
            matched_terms=("errors", "occur", "fix", "them"),
            matched_obligations=("check",),
        ),
        _make_result(
            "c3", "d1", 3.5,
            "Restart connection pool to resolve the issue.",
            matched_terms=("errors", "occur", "fix", "them"),
            matched_obligations=("action",),
        ),
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
        _make_result(
            "c1", "d1", 5.0, "Step 1: Check initial system status.",
            matched_terms=("deploy", "service"),
            matched_obligations=("precheck",),
        ),
        _make_result(
            "c2", "d1", 4.0, "Step 2: Run deployment script.",
            matched_terms=("deploy", "service"),
            matched_obligations=("step",),
        ),
        _make_result(
            "c3", "d1", 3.0, "Step 3: Validate service availability.",
            matched_terms=("deploy", "service"),
            matched_obligations=("postcheck",),
        ),
    ]
    pack = build_evidence_pack("How to deploy service?", _make_response(results))
    result = synthesize_evidence(pack, answer_shape="procedure")

    assert result.grounded is True
    assert "PRECHECKS:" in result.answer
    assert "STEPS:" in result.answer
    assert "POSTCHECKS:" in result.answer


def test_synthesize_evidence_abstains_for_unsupported_domain_specific_procedure():
    source = (
        "変更内容は３つ Workflow ERP Route ERP BOM 操作は４つ "
        "対象の Modeling を開く 対象の Rev を開く IsROR にチェック Save ボタンを押す"
    )
    pack = build_evidence_pack(
        "Create an actionable checklist for the manual RevUp procedure.",
        _make_response([
            _make_result("revup", "revup", 5.0, source, matched_terms=("manual", "revup"))
        ]),
    )

    result = synthesize_evidence(pack, answer_shape="procedure")

    assert result.abstained is True
    assert result.grounded is False
    assert "final_evidence_query_coverage_below_threshold" in result.abstention_reasons


def test_structured_synthesis_abstains_without_supported_section():
    pack = build_evidence_pack(
        "What errors occur and how to fix them?",
        _make_response([
            _make_result(
                "c1", "d1", 5.0, "A generic note is present.",
                matched_terms=("errors", "occur", "fix", "them"),
            )
        ]),
    )
    result = synthesize_evidence(pack, answer_shape="diagnosis")

    assert result.abstained is True
    assert result.grounded is False
    assert "KHÔNG ĐỦ BẰNG CHỨNG:" in result.answer
    assert "LIMITATIONS:" in result.answer
    assert "no_supported_answer_section" in result.abstention_reasons


def test_diagnosis_synthesis_contract_format():
    results = [_make_result("c1", "d1", 5.0, "Error code E01 requires system restart.")]
    pack = build_evidence_pack("What error handling is needed?", _make_response(results))
    plan = build_synthesis_plan(pack, answer_shape="diagnosis")
    contract = format_provider_synthesis_contract(plan)

    assert "SYMPTOMS:" in contract
    assert "CHECKS:" in contract
    assert "ACTIONS:" in contract


def test_architecture_synthesis_contract_requests_explanatory_cited_structure():
    results = [_make_result(
        "architecture", "overview", 5.0,
        "The terminal records events and sends them through the linkage database to MOM.",
        matched_terms=("architecture", "components", "data", "flow", "interfaces"),
        matched_facets=("components", "data_flow", "interfaces"),
    )]
    pack = build_evidence_pack("Describe the system architecture.", _make_response(results))
    plan = build_synthesis_plan(pack, answer_shape="architecture")
    contract = format_provider_synthesis_contract(plan)

    assert "cited overview" in contract
    assert "DATA_FLOW:" in contract
    assert "Do not infer layers, hops, protocols, or component roles" in contract


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


def test_architecture_composer_is_bounded_cited_and_suppresses_raw_dump():
    query = "Describe the architecture components, data flow, and integration interfaces."
    results = [
        _make_result(
            "component", "overview", 7.0,
            "# SYSTEM OVERVIEW\n- Gateway equipment receives operator requests.\n"
            "- Gateway equipment receives operator requests.",
            matched_terms=("architecture", "components"),
            matched_facets=("components",),
        ),
        _make_result(
            "flow", "operations", 6.0,
            "A12=Raw sheet header | B12=The service registers each accepted record in the ledger. "
            "| C12=Unrelated trailing spreadsheet payload that must not be copied wholesale.",
            matched_terms=("data", "flow"),
            matched_facets=("data_flow",),
        ),
        _make_result(
            "interface", "interface-spec", 5.0,
            "The adapter sends the normalized payload to the validation interface. "
            "Verification confirms receipt before processing continues.",
            matched_terms=("integration", "interfaces"),
            matched_facets=("interfaces",),
        ),
    ]
    response = SearchResponse(
        results=tuple(results),
        summary=SearchSummary(
            query=query,
            indexed_chunk_count=3,
            eligible_chunk_count=3,
            candidate_count=3,
            returned_count=3,
            planned_facet_ids=("query", "components", "data_flow", "interfaces"),
            covered_facet_ids=("components", "data_flow", "interfaces"),
            missing_facet_ids=("query",),
        ),
    )
    pack = build_evidence_pack(query, response)
    result = synthesize_evidence(pack, answer_shape="architecture", max_claims=6)

    assert result.grounded is True
    assert result.abstained is False
    assert result.answer.startswith("COMPONENTS:\n")
    assert "The retrieved evidence supports" not in result.answer
    assert "COMPONENTS:" in result.answer
    assert "DATA_FLOW:" in result.answer
    assert "INTERFACES_AND_VERIFICATION:" in result.answer
    assert len(result.claims) <= 6
    assert len(result.answer) <= 2400
    assert "A12=" not in result.answer
    assert "B12=" not in result.answer
    assert "C12=" not in result.answer
    assert "# SYSTEM OVERVIEW" not in result.answer
    assert result.answer.count("Gateway equipment receives operator requests") == 1

    evidence_by_id = {item.evidence_id: item for item in pack.items}
    for claim in result.claims:
        assert len(claim.text) <= 300
        assert len(claim.citation_ids) == len(claim.evidence_ids) == 1
        source = evidence_by_id[claim.evidence_ids[0]]
        assert claim.citation_ids == (source.citation_id,)
        assert claim.text in source.text


def test_architecture_composer_surfaces_missing_facets_without_invention():
    query = "Explain the system architecture and interfaces."
    results = [
        _make_result(
            "component", "overview", 5.0,
            "The gateway is the primary system component.",
            matched_terms=("system", "architecture", "interfaces"),
            matched_facets=("components",),
        )
    ]
    response = SearchResponse(
        results=tuple(results),
        summary=SearchSummary(
            query=query,
            indexed_chunk_count=1,
            eligible_chunk_count=1,
            candidate_count=1,
            returned_count=1,
            planned_facet_ids=("query", "components", "data_flow", "interfaces"),
            covered_facet_ids=("components",),
            missing_facet_ids=("query", "data_flow", "interfaces"),
        ),
    )
    pack = build_evidence_pack(query, response)
    result = synthesize_evidence(pack, answer_shape="architecture")

    assert result.grounded is True
    assert "No grounded evidence retrieved for this section." in result.answer
    assert "LIMITATIONS:" in result.answer
    assert "data_flow" in result.limitation_reasons
    assert "interfaces" in result.limitation_reasons


def test_architecture_composer_rejects_noise_and_unscoped_multi_facet_fillers():
    query = "Map the platform components, information flow, and external interfaces."
    results = [
        _make_result(
            "component", "overview", 8.0,
            "The registration service is the central production-history component.",
            matched_terms=("platform", "components"),
            matched_facets=("components",),
        ),
        _make_result(
            "noisy-flow", "appendix", 7.0,
            "Grounded local evidence for the production workflow. | "
            "ABV（Step1対象外 | 5 ©2025 Example Document Solutions Inc.",
            matched_terms=("information", "flow", "interfaces"),
            matched_facets=("components", "data_flow", "interfaces"),
        ),
        _make_result(
            "flow", "operations", 6.0,
            "The line terminal sends each accepted history record to the registration service.",
            matched_terms=("information", "flow"),
            matched_facets=("data_flow",),
        ),
        _make_result(
            "interface", "contract", 5.0,
            "The registration service validates payloads received through the MOM interface.",
            matched_terms=("external", "interfaces"),
            matched_facets=("interfaces",),
        ),
        _make_result(
            "unscoped", "footer", 4.0,
            "Copyright 2025 Example Document Solutions Inc.",
            matched_terms=("platform",),
            matched_facets=("components", "data_flow", "interfaces"),
        ),
    ]
    response = SearchResponse(
        results=tuple(results),
        summary=SearchSummary(
            query=query,
            indexed_chunk_count=len(results),
            eligible_chunk_count=len(results),
            candidate_count=len(results),
            returned_count=len(results),
            planned_facet_ids=("query", "components", "data_flow", "interfaces"),
            covered_facet_ids=("components", "data_flow", "interfaces"),
            missing_facet_ids=("query",),
        ),
    )

    result = synthesize_evidence(build_evidence_pack(query, response), answer_shape="architecture")

    assert result.grounded is True
    assert "ABV" not in result.answer
    assert "Copyright" not in result.answer
    assert "©2025" not in result.answer
    assert "Grounded local evidence" not in result.answer
    assert "line terminal sends" in result.answer
    assert "MOM interface" in result.answer
    assert all(len(claim.facet_ids) == 1 for claim in result.claims)
    assert len({claim.evidence_ids[0] for claim in result.claims}) == len(result.claims)


def test_local_synthesis_rejects_repeated_ocr_fragment_before_facet_selection():
    """A noisy high-scoring OCR fragment must not win over clean evidence."""
    query = "Map the platform components, information flow, and external interfaces."
    results = [
        _make_result(
            "ocr-noise", "appendix", 9.0,
            "component component component platform platform platform architecture "
            "components 【【 【【 line line line",
            matched_terms=("platform", "components", "information", "flow"),
            matched_facets=("components",),
        ),
        _make_result(
            "clean-component", "overview", 8.0,
            "The platform registration component accepts production records.",
            matched_terms=("platform", "components"),
            matched_facets=("components",),
        ),
        _make_result(
            "flow", "operations", 7.0,
            "The line terminal sends each accepted history record to the registration service.",
            matched_terms=("information", "flow"),
            matched_facets=("data_flow",),
        ),
        _make_result(
            "interface", "contract", 6.0,
            "The registration service validates payloads received through the MOM interface.",
            matched_terms=("external", "interfaces"),
            matched_facets=("interfaces",),
        ),
    ]
    response = SearchResponse(
        results=tuple(results),
        summary=SearchSummary(
            query=query,
            indexed_chunk_count=len(results),
            eligible_chunk_count=len(results),
            candidate_count=len(results),
            returned_count=len(results),
            planned_facet_ids=("query", "components", "data_flow", "interfaces"),
            covered_facet_ids=("components", "data_flow", "interfaces"),
            missing_facet_ids=("query",),
        ),
    )

    result = synthesize_evidence(build_evidence_pack(query, response), answer_shape="architecture")

    assert "component component component" not in result.answer
    assert "platform registration component accepts production records" in result.answer


def test_architecture_synthesis_ranks_facet_candidates_across_evidence_items():
    """A broad facet tag must not let the first weak fragment win selection."""
    query = "Map the platform components, information flow, and external interfaces."
    results = [
        _make_result(
            "broad-weak", "appendix", 9.0,
            "The system interface is documented for operators.",
            matched_terms=("platform",),
            matched_facets=("components",),
        ),
        _make_result(
            "component-strong", "overview", 7.0,
            "The platform registration component stores production records.",
            matched_terms=("platform", "components"),
            matched_facets=("components",),
        ),
        _make_result(
            "flow", "operations", 6.0,
            "The line terminal sends each accepted history record to the registration service.",
            matched_terms=("information", "flow"),
            matched_facets=("data_flow",),
        ),
        _make_result(
            "interface", "contract", 5.0,
            "The registration service validates payloads received through the MOM interface.",
            matched_terms=("external", "interfaces"),
            matched_facets=("interfaces",),
        ),
    ]
    response = SearchResponse(
        results=tuple(results),
        summary=SearchSummary(
            query=query,
            indexed_chunk_count=len(results),
            eligible_chunk_count=len(results),
            candidate_count=len(results),
            returned_count=len(results),
            planned_facet_ids=("query", "components", "data_flow", "interfaces"),
            covered_facet_ids=("components", "data_flow", "interfaces"),
            missing_facet_ids=("query",),
        ),
    )

    result = synthesize_evidence(build_evidence_pack(query, response), answer_shape="architecture")

    assert "platform registration component stores production records" in result.answer
    assert "system interface is documented for operators" not in result.answer


def test_provider_synthesis_accepts_only_validated_cloud_safe_answer():
    pack = build_evidence_pack(
        "Summarize the restart requirement",
        _make_response([
            _make_result(
                "c1",
                "d1",
                5.0,
                "Error code E01 requires system restart.",
                matched_terms=("restart", "requirement"),
                privacy_labels=("cloud_safe",),
            )
        ]),
    )
    requests = []

    def provider(request):
        requests.append(request)
        return "- Error code E01 requires system restart [1]"

    result = synthesize_with_provider(pack, provider)

    assert result.provider_used is True
    assert result.mode == "provider_validated"
    assert result.citation_ids == ("[1]",)
    assert len(requests) == 1
    assert requests[0].evidence_pack is pack
    assert "Allowed evidence labels: [1]" in requests[0].contract


def test_provider_synthesis_invalid_output_and_exception_fall_back_locally():
    pack = build_evidence_pack(
        "Summarize the restart requirement",
        _make_response([
            _make_result(
                "c1",
                "d1",
                5.0,
                "Error code E01 requires system restart.",
                matched_terms=("restart", "requirement"),
                privacy_labels=("cloud_safe",),
            )
        ]),
    )

    invalid = synthesize_with_provider(pack, lambda _request: "Invented answer [9]")

    def failing_provider(_request):
        raise RuntimeError(r"secret provider failure C:\\private")

    failed = synthesize_with_provider(pack, failing_provider)

    assert invalid.provider_used is False
    assert invalid.mode == "local_extractive_provider_fallback"
    assert "Invented answer" not in invalid.answer
    assert failed.provider_used is False
    assert failed.mode == "local_extractive_provider_fallback"
    assert "secret provider failure" not in str(failed)
    assert failed.answer == invalid.answer


def test_provider_failure_uses_citation_first_fallback_for_compact_evidence():
    pack = build_evidence_pack(
        "Summarize APS",
        _make_response([
            _make_result(
                "c1",
                "d1",
                5.0,
                "APS",
                matched_terms=("aps",),
                privacy_labels=("cloud_safe",),
            )
        ]),
    )

    result = synthesize_with_provider(
        pack,
        lambda _request: (_ for _ in ()).throw(RuntimeError("provider timeout")),
    )

    assert result.provider_used is False
    assert result.grounded is False
    assert result.abstained is True
    assert result.mode == "local_extractive_provider_not_called"
    assert "final_evidence_query_coverage_below_threshold" in result.abstention_reasons



def test_provider_synthesis_never_calls_provider_for_local_only_or_insufficient_pack():
    calls = []

    def provider(_request):
        calls.append(True)
        return "- Must not be used [1]"

    local_pack = build_evidence_pack(
        "Summarize the restart requirement",
        _make_response([
            _make_result(
                "c1",
                "d1",
                5.0,
                "Error code E01 requires system restart.",
                matched_terms=("restart", "requirement"),
                privacy_labels=("local_only",),
            )
        ]),
    )
    insufficient_pack = build_evidence_pack(
        "missing evidence",
        _make_response([]),
    )

    local = synthesize_with_provider(local_pack, provider)
    insufficient = synthesize_with_provider(insufficient_pack, provider)

    assert calls == []
    assert local.provider_used is False
    assert local.mode == "local_extractive_provider_privacy_blocked"
    assert insufficient.provider_used is False
    assert insufficient.mode == "local_extractive_provider_not_called"


def test_provider_failure_renders_compare_sections_from_facet_tagged_evidence():
    pack = build_evidence_pack(
        "Compare APS process-plan procedure with production completion procedure",
        _make_response([
            _make_result(
                "aps-plan",
                "d1",
                5.0,
                "APS calendar registration covers every process for the main and dependent items.",
                matched_terms=("compare", "aps", "process", "plan", "production", "completion", "procedure"),
                matched_facets=("side_a",),
                privacy_labels=("cloud_safe",),
            ),
            _make_result(
                "completion",
                "d2",
                4.0,
                "Production completion records the completed operation and serial number in MOM.",
                matched_terms=("compare", "aps", "process", "plan", "production", "completion", "procedure"),
                matched_facets=("side_b",),
                privacy_labels=("cloud_safe",),
            ),
            _make_result(
                "difference",
                "d3",
                3.0,
                "The APS plan is verified before supply planning, while completion is recorded after the operation.",
                matched_terms=("compare", "aps", "process", "plan", "production", "completion", "procedure"),
                matched_facets=("differences",),
                privacy_labels=("cloud_safe",),
            ),
        ]),
    )

    result = synthesize_with_provider(
        pack,
        lambda _request: (_ for _ in ()).throw(RuntimeError("provider timeout")),
        answer_shape="compare_change",
        max_claims=3,
    )

    assert result.mode == "local_extractive_provider_fallback"
    assert "SIDE_A:\n- APS calendar registration" in result.answer
    assert "SIDE_B:\n- Production completion records" in result.answer
    assert "DIFFERENCES:\n- The APS plan is verified" in result.answer
    assert "Sheet:" not in result.answer


def test_diagnosis_synthesis_uses_distinct_obligation_specific_fragments():
    pack = build_evidence_pack(
        "Why did the production import fail and how can it be recovered?",
        _make_response([
            _make_result(
                "incident",
                "d1",
                5.0,
                "Error E24 is raised when the import file is unavailable. "
                "Verify the transfer log and source file path. "
                "Restart the import service after the file is restored.",
                matched_terms=("production", "import", "fail", "recovered"),
                matched_obligations=("problem", "check", "action"),
            ),
        ]),
    )

    result = synthesize_evidence(pack, answer_shape="diagnosis")

    assert result.abstained is True
    assert result.grounded is False
    assert "final_evidence_query_coverage_below_threshold" in result.abstention_reasons


def test_lookup_synthesis_returns_cited_spreadsheet_provenance_only():
    pack = build_evidence_pack(
        "Find the supply-line values in the table",
        _make_response([
            _make_result(
                "sheet-range",
                "workbook",
                5.0,
                "Row 12: C31 | source staging value",
                source_name="supply.xlsx",
                file_type="xlsx",
                metadata={
                    "sheet": "Staging",
                    "row_range": [12, 12],
                    "cell_range": "A12:C12",
                },
                matched_terms=("supply", "line", "values", "table"),
            ),
        ]),
    )

    result = synthesize_evidence(pack, answer_shape="lookup")

    assert result.grounded is True
    assert result.answer == (
        "DOCUMENTED_LOCATIONS:\n"
        "- supply.xlsx — Sheet: Staging; Rows: 12-12; Cells: A12:C12. [1]"
    )
    assert "source staging value" not in result.answer


def test_lookup_with_provider_uses_deterministic_coordinate_renderer():
    pack = build_evidence_pack(
        "Find the supply-instruction location",
        _make_response([
            _make_result(
                "broad-table-range",
                "broad-workbook",
                6.0,
                "Row 3: generic supply line overview",
                source_name="broad.xlsx",
                file_type="xlsx",
                metadata={
                    "sheet": "Overview",
                    "row_range": [3, 4],
                    "cell_range": "A3:C4",
                },
                matched_terms=("supply",),
                privacy_labels=("cloud_safe",),
            ),
            _make_result(
                "sheet-range",
                "workbook",
                5.0,
                "Row 6: 供給指示 deletion",
                source_name="supply.xlsx",
                file_type="xlsx",
                metadata={
                    "sheet": "MOM processing",
                    "row_range": [6, 6],
                    "cell_range": "A6:C6",
                },
                matched_terms=("supply", "instruction", "location"),
                privacy_labels=("cloud_safe",),
            ),
        ]),
    )
    calls = []

    result = synthesize_with_provider(
        pack,
        lambda _request: calls.append(True) or "Invented location [1]",
        answer_shape="lookup",
    )

    assert calls == []
    assert result.provider_used is False
    assert result.answer == (
        "DOCUMENTED_LOCATIONS:\n"
        "- supply.xlsx — Sheet: MOM processing; Rows: 6-6; Cells: A6:C6. [2]"
    )


def test_supply_instruction_lookup_abstains_without_target_anchor():
    pack = build_evidence_pack(
        "Find the supply-instruction location",
        _make_response([
            _make_result(
                "unrelated-range",
                "workbook",
                5.0,
                "Row 3: generic supply line overview",
                source_name="broad.xlsx",
                file_type="xlsx",
                metadata={
                    "sheet": "Overview",
                    "row_range": [3, 4],
                    "cell_range": "A3:C4",
                },
                matched_terms=("supply", "instruction", "location"),
            ),
        ]),
    )

    provider_calls = []
    result = synthesize_with_provider(
        pack,
        lambda _request: provider_calls.append(True) or "Invented lookup [1]",
        answer_shape="lookup",
    )

    assert provider_calls == []
    assert result.abstained is False
    assert result.grounded is True
    assert "broad.xlsx" in result.answer
    assert result.citation_ids == ("[1]",)


def test_provider_repairs_shape_only_failure_once_before_accepting_answer():
    pack = build_evidence_pack(
        "How to deploy service?",
        _make_response([
            _make_result(
                "pre", "d1", 5.0, "Verify access before deployment.",
                matched_terms=("deploy", "service"),
                matched_obligations=("precheck",),
            ),
            _make_result(
                "step", "d1", 4.0, "Deploy the release package.",
                matched_terms=("deploy", "service"),
                matched_obligations=("step",),
            ),
            _make_result(
                "post", "d1", 3.0, "Validate service availability.",
                matched_terms=("deploy", "service"),
                matched_obligations=("postcheck",),
            ),
        ]),
    )
    calls = []

    def provider(request):
        calls.append(request)
        if len(calls) == 1:
            return (
                "PRECHECKS:\n- Verify access\n"
                "STEPS:\n- Deploy the release package [2]\n"
                "POSTCHECKS:\n- Validate service availability [3]"
            )
        return (
            "PRECHECKS:\n- Verify access [1]\n"
            "STEPS:\n- Deploy the release package [2]\n"
            "POSTCHECKS:\n- Validate service availability [3]"
        )

    result = synthesize_with_provider(pack, provider, answer_shape="procedure", max_claims=3)

    assert len(calls) == 2
    assert calls[1].repair_candidate
    assert "provider_answer_uncited_material_claim" in calls[1].repair_errors
    assert result.provider_used is True
    assert result.mode == "provider_validated_after_repair"
    assert "PRECHECKS:" in result.answer


def test_provider_never_repairs_unknown_or_uncited_factual_output():
    pack = build_evidence_pack(
        "How to deploy service?",
        _make_response([_make_result(
            "pre", "d1", 5.0, "Verify access before deployment.",
            matched_terms=("deploy", "service"),
        )]),
    )
    calls = []

    result = synthesize_with_provider(
        pack,
        lambda request: calls.append(request) or "Invented instruction without a source [99]",
        answer_shape="grounded_summary",
    )

    assert len(calls) == 1
    assert result.provider_used is False
    assert result.mode.startswith("local_")


def test_provider_validation_classifies_only_presentation_errors_as_repairable():
    pack = build_evidence_pack(
        "release procedure",
        _make_response([_make_result(
            "release", "d1", 5.0, "Verify access, deploy, then validate.",
            matched_terms=("release", "procedure"),
        )]),
    )
    plan = build_synthesis_plan(pack, answer_shape="procedure", max_claims=3)

    presentation_failure = validate_provider_synthesis_answer(
        pack, "Verify access [1]", plan
    )
    unsafe_failure = validate_provider_synthesis_answer(
        pack, "Invented fact [99]", plan
    )

    assert provider_validation_is_repairable(presentation_failure) is True
    assert provider_validation_is_repairable(unsafe_failure) is False

    uncited_failure = validate_provider_synthesis_answer(
        pack,
        "PRECHECKS:\n- Verify access\nSTEPS:\n- Deploy [1]\nPOSTCHECKS:\n- Validate [1]",
        plan,
    )
    assert provider_validation_is_repairable(uncited_failure) is True


def test_lookup_synthesis_returns_explicit_header_value_pairs_when_requested():
    pack = build_evidence_pack(
        "Show the values in this spreadsheet table",
        _make_response([
            _make_result(
                "table-row",
                "workbook",
                5.0,
                "Sheet: Operations\nColumns: Product | Status | Quantity\nRow 12: Kit-A | Ready | 24",
                source_name="operations.xlsx",
                file_type="xlsx",
                metadata={"sheet": "Operations", "row_range": [12, 12], "cell_range": "A12:C12"},
                matched_terms=("spreadsheet", "table", "values"),
            ),
        ]),
    )

    result = synthesize_evidence(pack, answer_shape="lookup")

    assert result.grounded is True
    assert "DOCUMENTED_VALUES:" in result.answer
    assert "Product: Kit-A" in result.answer
    assert "Status: Ready" in result.answer
    assert "Quantity: 24" in result.answer
    assert "Sheet: Operations" in result.answer
    assert "[1]" in result.answer


def test_lookup_synthesis_does_not_assert_values_from_malformed_row():
    pack = build_evidence_pack(
        "Show the values in this spreadsheet table",
        _make_response([
            _make_result(
                "malformed-table-row",
                "workbook",
                5.0,
                "Columns: Product | Status | Quantity\nRow 12: Kit-A | Ready",
                source_name="operations.xlsx",
                file_type="xlsx",
                metadata={"sheet": "Operations", "row_range": [12, 12], "cell_range": "A12:C12"},
                matched_terms=("spreadsheet", "table", "values"),
            ),
        ]),
    )

    result = synthesize_evidence(pack, answer_shape="lookup")

    assert "DOCUMENTED_LOCATIONS:" in result.answer
    assert "Kit-A" not in result.answer
    assert "Quantity" not in result.answer


def test_abstention_explains_scope_and_required_evidence_without_facts():
    pack = build_evidence_pack("unrelated target relationship", _make_response([]))

    result = synthesize_evidence(pack)

    assert result.abstained is True
    assert result.citation_ids == ()
    assert "KHÔNG ĐỦ BẰNG CHỨNG:" in result.answer
    assert "Cần nguồn trực tiếp" in result.answer
    assert "LIMITATIONS:" in result.answer
