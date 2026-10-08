from aios_habit.rag_v2.evidence import (
    EvidenceAnswerMode,
    EvidenceConfidence,
    build_evidence_pack,
)
from aios_habit.rag_v2.index import SearchResponse, SearchResult, SearchSummary
from aios_habit.rag_v2.synthesis import (
    build_synthesis_plan,
    format_provider_synthesis_contract,
    format_provider_synthesis_repair_contract,
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


def test_synthesis_plan_claim_budget_expansion_for_diagnosis_and_lookup():
    results = [_make_result("c1", "d1", 5.0, "Sample diagnostic evidence snippet.")]
    pack = build_evidence_pack("Diagnosis query", _make_response(results))

    # Diagnosis and lookup shapes expand effective budget to 10 when max_claims < 10
    diag_plan = build_synthesis_plan(pack, answer_shape="diagnosis", max_claims=5)
    assert diag_plan.max_claims == 10

    lookup_plan = build_synthesis_plan(pack, answer_shape="lookup", max_claims=5)
    assert lookup_plan.max_claims == 10

    # Architecture and integration shapes maintain existing precedent of expanding to 10
    arch_plan = build_synthesis_plan(pack, answer_shape="architecture", max_claims=5)
    assert arch_plan.max_claims == 10

    integ_plan = build_synthesis_plan(pack, answer_shape="integration", max_claims=5)
    assert integ_plan.max_claims == 10

    # Other shapes keep their requested compact budget
    summary_plan = build_synthesis_plan(pack, answer_shape="grounded_summary", max_claims=5)
    assert summary_plan.max_claims == 5

    proc_plan = build_synthesis_plan(pack, answer_shape="procedure", max_claims=5)
    assert proc_plan.max_claims == 5

    compare_plan = build_synthesis_plan(pack, answer_shape="compare_change", max_claims=5)
    assert compare_plan.max_claims == 5

    action_plan = build_synthesis_plan(pack, answer_shape="actionable_output", max_claims=5)
    assert action_plan.max_claims == 5

    # If higher budget is requested, it is respected
    high_diag_plan = build_synthesis_plan(pack, answer_shape="diagnosis", max_claims=12)
    assert high_diag_plan.max_claims == 12


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
    # Facets may now carry several claims within budget; the ranking contract is
    # that the strong candidate is selected before the weak one for the same facet.
    components_section = result.answer.split("INTERFACES_AND_VERIFICATION:")[0]
    strong_pos = components_section.find(
        "platform registration component stores production records"
    )
    weak_pos = components_section.find("system interface is documented for operators")
    assert strong_pos != -1 and (weak_pos == -1 or strong_pos < weak_pos)


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



def test_provider_synthesis_insufficient_pack_never_calls_provider():
    calls = []

    def provider(_request):
        calls.append(True)
        return "- Must not be used [1]"

    insufficient_pack = build_evidence_pack(
        "missing evidence",
        _make_response([]),
    )

    insufficient = synthesize_with_provider(insufficient_pack, provider)

    assert calls == []
    assert insufficient.provider_used is False
    assert insufficient.mode == "local_extractive_provider_not_called"


def test_provider_synthesis_local_only_labels_do_not_block_provider():
    """Ingest-time labels are provenance only (DATA_POLICY 2026-09-29).

    A pack whose items carry only local_only labels no longer blocks the
    provider route; the operator opt-in at the factory/provider layer is
    the gate, not the label. Owner re-confirmed 2026-10-02.
    """
    calls = []

    def provider(_request):
        calls.append(True)
        return "- Error code E01 requires system restart [1]"

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

    local = synthesize_with_provider(local_pack, provider)

    assert len(calls) == 1
    assert local.provider_used is True
    assert local.mode == "provider_validated"


def test_provider_synthesis_unlabeled_pack_stays_blocked_without_opt_in(monkeypatch):
    """Fail-closed default: unlabeled pack never reaches a provider."""
    monkeypatch.delenv("AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS", raising=False)
    calls = []

    def provider(request):
        calls.append(request)
        return "- Error code E01 requires system restart [1]"

    pack = build_evidence_pack(
        "Summarize the restart requirement",
        _make_response([
            _make_result(
                "c1",
                "d1",
                5.0,
                "Error code E01 requires system restart.",
                matched_terms=("restart", "requirement"),
                privacy_labels=(),
            )
        ]),
    )

    result = synthesize_with_provider(pack, provider)

    assert calls == []
    assert result.provider_used is False
    assert result.mode == "local_extractive_provider_privacy_blocked"


def test_provider_synthesis_opt_in_calls_provider_for_unlabeled_pack(monkeypatch):
    """Owner opt-in overrides an unlabeled (cloud_allowed=False) pack.

    Without labels the evidence layer marks the pack local_only /
    cloud_allowed=False. AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1 is the
    operator switch that opens the provider route anyway.
    """
    monkeypatch.setenv("AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS", "1")
    calls = []

    def provider(request):
        calls.append(request)
        return "- Error code E01 requires system restart [1]"

    pack = build_evidence_pack(
        "Summarize the restart requirement",
        _make_response([
            _make_result(
                "c1",
                "d1",
                5.0,
                "Error code E01 requires system restart.",
                matched_terms=("restart", "requirement"),
                privacy_labels=(),
            )
        ]),
    )

    result = synthesize_with_provider(pack, provider)

    assert result.provider_used is True
    assert result.mode == "provider_validated"
    assert result.citation_ids == ("[1]",)
    assert len(calls) == 1


def test_provider_synthesis_opt_in_provider_error_falls_back_locally(monkeypatch):
    """Under the opt-in, a provider failure still falls back locally."""
    monkeypatch.setenv("AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS", "1")
    pack = build_evidence_pack(
        "Summarize the restart requirement",
        _make_response([
            _make_result(
                "c1",
                "d1",
                5.0,
                "Error code E01 requires system restart.",
                matched_terms=("restart", "requirement"),
                privacy_labels=(),
            )
        ]),
    )

    def failing_provider(_request):
        raise RuntimeError("network down")

    result = synthesize_with_provider(pack, failing_provider)

    assert result.provider_used is False
    assert result.mode == "local_extractive_provider_fallback"
    assert "cloud_privacy_blocked" not in result.limitation_reasons


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


def test_provider_drops_single_uncited_line_and_keeps_valid_lines():
    """A single uncited line is dropped surgically; valid lines are kept.

    E2 item 5: one bad line must not discard the whole provider answer.
    """
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
        return (
            "PRECHECKS:\n- Verify access\n"
            "STEPS:\n- Deploy the release package [2]\n"
            "POSTCHECKS:\n- Validate service availability [3]"
        )

    result = synthesize_with_provider(pack, provider, answer_shape="procedure", max_claims=3)

    assert len(calls) == 1
    assert result.provider_used is True
    assert result.mode == "provider_validated"
    assert "Verify access\n" not in result.answer
    assert "Deploy the release package [2]" in result.answer
    assert "Validate service availability [3]" in result.answer


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

def test_fallback_fragment_truncates_at_punctuation():
    from aios_habit.rag_v2.synthesis import _fallback_fragment
    pack = build_evidence_pack("query", _make_response([_make_result("c1", "d1", 5.0, "Word. " * 50 + "NoPunctuationHere" * 20)]))
    fragment = _fallback_fragment(pack.items[0], query_terms=set(), selected=())
    assert fragment.endswith("...")

def test_citation_first_fallback_groups_claims():
    from aios_habit.rag_v2.synthesis import _citation_first_fallback
    # To get same citation ID, we mock their citation_ids after building pack
    pack = build_evidence_pack(
        "query",
        _make_response([
            _make_result("c1", "d1", 5.0, "Claim 1"),
            _make_result("c2", "d1", 4.0, "Claim 2"),
        ]),
    )
    for item in pack.items:
        object.__setattr__(item, "citation_id", "[1]")
        object.__setattr__(item, "citation_ids", ("[1]",))

    result = _citation_first_fallback(pack, answer_shape="unknown", max_claims=5)
    assert "- [1]:" in result.answer
    assert "  * Claim 1" in result.answer
    assert "  * Claim 2" in result.answer


def test_cross_source_synthesis_renders_each_facet():
    from aios_habit.rag_v2.query_planning import identity_query_plan

    query = (
        "How does data flow between connected systems, and where should an operator verify failures?"
    )
    plan = identity_query_plan(query)
    results = [
        _make_result(
            "c1", "d1", 5.0,
            "Data flows through the interface table to connected systems.",
            matched_terms=("data", "flow", "systems", "verify", "failures"),
            matched_facets=("query", "facet_1"),
        ),
        _make_result(
            "c2", "d2", 4.5,
            "Operators verify failures on the status screen.",
            matched_terms=("data", "flow", "systems", "verify", "failures"),
            matched_facets=("query", "facet_2"),
        ),
    ]
    response = SearchResponse(
        results=tuple(results),
        summary=SearchSummary(
            query=query,
            indexed_chunk_count=2,
            eligible_chunk_count=2,
            candidate_count=2,
            returned_count=2,
            planned_facet_ids=plan.facet_ids,
            covered_facet_ids=("query", "facet_1", "facet_2"),
            missing_facet_ids=(),
        ),
    )
    pack = build_evidence_pack(plan, response)
    result = synthesize_evidence(pack, answer_shape="cross_source_synthesis")

    assert plan.intent_category == "cross_source_synthesis"
    assert result.grounded is True
    assert result.abstained is False
    assert "Ý 1:" in result.answer
    assert "Ý 2:" in result.answer
    assert "[1]" in result.answer
    assert "[2]" in result.answer
    assert "Còn thiếu:" not in result.answer


def test_cross_source_synthesis_marks_missing_facet():
    from aios_habit.rag_v2.query_planning import identity_query_plan

    query = (
        "How does data flow between connected systems, and where should an operator verify failures?"
    )
    plan = identity_query_plan(query)
    results = [
        _make_result(
            "c1", "d1", 5.0,
            "Data flows through the interface table to connected systems.",
            matched_terms=("data", "flow", "systems", "verify", "failures"),
            matched_facets=("query", "facet_1"),
        ),
    ]
    response = SearchResponse(
        results=tuple(results),
        summary=SearchSummary(
            query=query,
            indexed_chunk_count=1,
            eligible_chunk_count=1,
            candidate_count=1,
            returned_count=1,
            planned_facet_ids=plan.facet_ids,
            covered_facet_ids=("query", "facet_1"),
            missing_facet_ids=("facet_2",),
        ),
    )
    pack = build_evidence_pack(plan, response)
    result = synthesize_evidence(pack, answer_shape="cross_source_synthesis")

    assert result.grounded is True
    assert "Ý 1:" in result.answer
    assert "Ý 2:" in result.answer
    assert "Còn thiếu:" in result.answer
    assert "Ý 2" in result.answer

def test_provider_limitations_contain_accurate_reasons(monkeypatch):
    monkeypatch.delenv("AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS", raising=False)
    from aios_habit.rag_v2.evidence import PrivacySummary
    from dataclasses import replace
    pack = build_evidence_pack("query", _make_response([_make_result("c1", "d1", 5.0, "Claim 1", matched_terms=("query",))]))
    pack_blocked = replace(pack, privacy_summary=PrivacySummary(overall_label="strict", local_only=True, cloud_allowed=False, labels_present=()))

    def provider(req): return "Answer"

    result_blocked = synthesize_with_provider(pack_blocked, provider)
    assert "cloud_privacy_blocked" in result_blocked.limitation_reasons
    assert result_blocked.mode == "local_citation_first_provider_fallback"

    def fail_provider(req): raise ValueError("Network Error")
    result_failed = synthesize_with_provider(pack, fail_provider)
    assert "provider_network_error" in result_failed.limitation_reasons
    assert result_failed.mode == "local_citation_first_provider_fallback"


def test_full_mode_synthesis_prioritizes_body_chunks_and_answer_literals():
    query = "T_IF_PROD_RESULT XML 150 item"
    summaries = [
        _make_result(
            f"summary-{index}",
            f"summary-doc-{index}",
            10.0 - index,
            f"Tổng quan nội dung tài liệu vận hành sản xuất, giai đoạn {index}.",
            file_type="document_summary",
            metadata={"is_document_summary": True},
        )
        for index in range(5)
    ]
    body = _make_result(
        "answer-chunk",
        "answer-doc",
        1.0,
        "T_IF_PROD_RESULT là bảng trung gian nhận dữ liệu thực tích sản xuất. "
        "Khi có khoảng 150 item tiêu hao, XML của T_IF_PROD_RESULT vượt giới hạn "
        "nvarchar(4000), khiến thủ tục không lưu được dữ liệu.",
        matched_terms=("150", "item", "mom", "t_if_prod_result", "xml"),
    )
    pack = build_evidence_pack(query, _make_response([*summaries, body]))
    result = synthesize_evidence(pack, prioritize_body_evidence=True)
    answer_item = next(item for item in pack.items if item.chunk_id == "answer-chunk")

    assert "nvarchar(4000)" in result.answer
    assert result.claims[0].citation_ids == (answer_item.citation_id,)
    assert "nvarchar(4000)" in result.claims[0].text


def test_full_mode_synthesis_preserves_values_late_in_a_long_chunk():
    query = "Mã số Oricon ngày 16/6/2026"
    summaries = [
        _make_result(
            f"summary-{index}",
            f"summary-doc-{index}",
            10.0 - index,
            f"Tổng quan sự cố Oricon ngày 16/6/2026, giai đoạn {index}.",
            matched_terms=("mã", "số", "oricon", "16", "6", "2026"),
            file_type="document_summary",
        )
        for index in range(5)
    ]
    body = _make_result(
        "long-answer",
        "incident",
        1.0,
        "Ghi chú quy trình vận hành thủ công và trạng thái thiết bị trong kho " * 18
        + "Trong sự cố ngày 16/6/2026, thùng Oricon cũ mang mã 11922 và 12860; "
        "thùng mới mã 12626.",
        matched_terms=("mã", "số", "oricon", "16", "6", "2026"),
    )
    pack = build_evidence_pack(query, _make_response([*summaries, body]))
    result = synthesize_evidence(pack, prioritize_body_evidence=True)
    answer_item = next(item for item in pack.items if item.chunk_id == "long-answer")

    assert result.claims[0].citation_ids == (answer_item.citation_id,)
    assert all(code in result.claims[0].text for code in ("11922", "12860", "12626"))


def test_full_mode_synthesis_prioritizes_last_requested_field_identifier():
    query = "T_PARTS_RECIEVE HOUSE_METHOD value"
    general_chunks = [
        _make_result(
            f"general-{index}",
            f"general-doc-{index}",
            10.0 - index,
            "T_PARTS_RECIEVE stores general warehouse and receiving information.",
            matched_terms=("t_parts_recieve", "value"),
        )
        for index in range(5)
    ]
    target = _make_result(
        "house-method",
        "field-definition",
        1.0,
        "T_PARTS_RECIEVE defines HOUSE_METHOD as “0” for warehouse storage. "
        "The field value “1” means inspection.",
        matched_terms=("t_parts_recieve", "house_method", "value"),
    )
    pack = build_evidence_pack(query, _make_response([*general_chunks, target]))
    result = synthesize_evidence(pack, prioritize_body_evidence=True)
    target_item = next(item for item in pack.items if item.chunk_id == "house-method")

    assert result.claims[0].citation_ids == (target_item.citation_id,)
    assert "HOUSE_METHOD" in result.claims[0].text
    assert "“0”" in result.claims[0].text
    assert "“1”" in result.claims[0].text


def test_e2_value_based_selection_beats_pack_order_by_default():
    """E1 A1: five summaries head the pack, the real answer sits last.

    E2 item 1+3: without any explicit flag, the claim carrying the literal
    answer codes must be selected instead of the first five pack items.
    """
    query = "Mã thùng Oricon trong sự cố ngày 16/6/2026"
    summaries = [
        _make_result(
            f"summary-{index}",
            f"summary-doc-{index}",
            10.0 - index,
            f"Tổng quan nội dung tài liệu vận hành, giai đoạn {index}.",
            file_type="document_summary",
            metadata={"is_document_summary": True},
        )
        for index in range(5)
    ]
    body = [
        _make_result(
            "answer-a",
            "incident-doc",
            1.0,
            "Trong sự cố ngày 16/6/2026, thùng Oricon cũ mang mã 11922 và 12860.",
            matched_terms=("mã", "oricon", "16", "6", "2026"),
        ),
        _make_result(
            "answer-b",
            "incident-doc",
            0.9,
            "Thùng mới trong cùng sự cố mang mã 12626, đã thay thế thùng cũ.",
            matched_terms=("mã", "oricon", "16", "6", "2026"),
        ),
    ]
    pack = build_evidence_pack(query, _make_response([*summaries, *body]))
    result = synthesize_evidence(pack)

    assert result.grounded is True
    assert "11922" in result.answer
    assert "12860" in result.answer or "12626" in result.answer


def test_e2_summary_claim_quota_bounds_overview_claims():
    """E2 item 1: at most two summary claims may occupy the claim budget."""
    query = "Mã thùng Oricon trong sự cố ngày 16/6/2026"
    summaries = [
        _make_result(
            f"summary-{index}",
            f"summary-doc-{index}",
            10.0 - index,
            f"Tổng quan sự cố Oricon ngày 16/6/2026, giai đoạn {index}.",
            matched_terms=("mã", "oricon", "16", "6", "2026"),
            file_type="document_summary",
            metadata={"is_document_summary": True},
        )
        for index in range(5)
    ]
    pack = build_evidence_pack(query, _make_response(summaries))
    result = synthesize_evidence(pack, max_claims=5)

    summary_claims = sum(
        1
        for claim in result.claims
        if next(
            item for item in pack.items if item.evidence_id in claim.evidence_ids
        ).file_type == "document_summary"
    )
    assert summary_claims <= 2


def test_e2_repair_contract_instructs_compression_not_deletion():
    """E2 item 4: the repair contract must say compress, never drop cited facts."""
    pack = build_evidence_pack(
        "release procedure",
        _make_response([_make_result(
            "release", "d1", 5.0, "Verify access, deploy, then validate.",
            matched_terms=("release", "procedure"),
        )]),
    )
    plan = build_synthesis_plan(pack, max_claims=3)
    contract = format_provider_synthesis_repair_contract(
        plan, "draft", ("provider_answer_claim_budget_exceeded",)
    )

    assert "COMPRESS" in contract
    assert "keeping every cited value" in contract
    assert "do not drop cited facts" in contract


def test_e2_provider_validation_drops_only_offending_lines():
    """E2 item 5: one line with an unknown citation is dropped; the rest stays."""
    pack = build_evidence_pack(
        "release procedure",
        _make_response([
            _make_result(
                "release-a", "d1", 5.0, "Verify access before release.",
                matched_terms=("release", "procedure"),
            ),
            _make_result(
                "release-b", "d1", 4.0, "Deploy the release package.",
                matched_terms=("release", "procedure"),
            ),
        ]),
    )
    calls = []

    def provider(request):
        calls.append(request)
        return (
            "- Verify access before release [1]\n"
            "- Invented step without a source [99]\n"
            "- Deploy the release package [2]"
        )

    result = synthesize_with_provider(pack, provider, answer_shape="grounded_summary")

    assert len(calls) == 1
    assert result.provider_used is True
    assert "[99]" not in result.answer
    assert "Verify access before release [1]" in result.answer
    assert "Deploy the release package [2]" in result.answer


def test_e2_facet_sections_allow_multiple_claims_within_budget():
    """E2 item 6: a facet may carry more than one claim inside the budget."""
    query = "Map the platform components and their external interfaces."
    results = [
        _make_result(
            "component-a", "doc-a", 9.0,
            "The registration service stores production records.",
            matched_terms=("platform", "components"),
            matched_facets=("components",),
        ),
        _make_result(
            "component-b", "doc-b", 8.0,
            "The terminal gateway forwards history records to the warehouse.",
            matched_terms=("platform", "components"),
            matched_facets=("components",),
        ),
        _make_result(
            "interface", "doc-c", 7.0,
            "The MOM interface exposes the production API to operators.",
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
            planned_facet_ids=("query", "components", "interfaces"),
            covered_facet_ids=("components", "interfaces"),
            missing_facet_ids=("query",),
        ),
    )
    result = synthesize_evidence(
        build_evidence_pack(query, response),
        answer_shape="architecture",
        max_claims=5,
    )

    assert "registration service stores production records" in result.answer
    assert "terminal gateway forwards history records" in result.answer
    assert "MOM interface exposes the production API" in result.answer


def test_e2_b3_keeps_nvarchar_literal_for_length_question():
    """P1.4 B3 evidence: a '4000 ký tự' question must keep the nvarchar(4000)
    literal from the evidence instead of only naming the 4000 limit."""
    query = "Độ dài tối đa cho phép của trường dữ liệu là 4000 ký tự?"
    general = _make_result(
        "general-doc", "overview", 9.0,
        "Tài liệu MOM mô tả giới hạn độ dài cho các trường dữ liệu, "
        "vượt quá 4000 ký tự sẽ bị từ chối.",
        matched_terms=("độ", "dài", "4000", "ký", "tự"),
    )
    precise = _make_result(
        "field-def", "spec", 1.0,
        "Trường RESULT_TEXT có kiểu nvarchar(4000); vượt quá 4000 ký tự "
        "thì thủ tục không lưu được dữ liệu.",
        matched_terms=("độ", "dài", "4000", "ký", "tự"),
    )
    pack = build_evidence_pack(query, _make_response([general, precise]))
    result = synthesize_evidence(pack)

    assert result.grounded is True
    assert "nvarchar(4000)" in result.answer


def test_e2_b5_selects_house_method_definition_line():
    """P1.4 B5 evidence: the HOUSE_METHOD definition line present in the pack
    must be selected by the extractive composer."""
    query = "HOUSE_METHOD được định nghĩa như thế nào?"
    noise = _make_result(
        "noise", "glossary", 9.0,
        "Bảng thuật ngữ kho liệt kê các trường dữ liệu chung của hệ thống.",
        matched_terms=("house_method", "được", "định", "nghĩa", "như", "thế", "nào"),
    )
    definition = _make_result(
        "def-12", "glossary", 1.0,
        "Định nghĩa HOUSE_METHOD: '0':倉庫へ格納 (nhập kho), "
        "'1':検査 (kiểm tra).",
        matched_terms=("house_method", "được", "định", "nghĩa", "như", "thế", "nào"),
    )
    pack = build_evidence_pack(query, _make_response([noise, definition]))
    result = synthesize_evidence(pack)

    assert result.grounded is True
    assert "HOUSE_METHOD" in result.answer
    assert "倉庫へ格納" in result.answer


def _make_release_pair_pack():
    return build_evidence_pack(
        "release procedure",
        _make_response([
            _make_result(
                "release-a", "d1", 5.0, "Verify access before release.",
                matched_terms=("release", "procedure"),
            ),
            _make_result(
                "release-b", "d1", 4.0, "Deploy the release package.",
                matched_terms=("release", "procedure"),
            ),
        ]),
    )


def test_combined_droppable_and_repairable_failure_recovers_via_surgery_then_repair():
    """Combined failures drop the fabricated line first, then hand the
    remaining presentation error to the single repair attempt."""
    pack = _make_release_pair_pack()
    calls = []

    def provider(request):
        calls.append(request)
        if len(calls) == 1:
            return (
                "- Verify access before release [1]\n"
                "- Invented step without a source [99]\n"
                "- Deploy the release package [2]"
            )
        return "- Verify access before release [1]"

    result = synthesize_with_provider(
        pack, provider, answer_shape="grounded_summary", max_claims=1
    )

    assert len(calls) == 2
    assert calls[0].repair_errors == ()
    assert calls[1].repair_candidate == (
        "- Verify access before release [1]\n- Deploy the release package [2]"
    )
    assert calls[1].repair_errors == ("provider_answer_claim_budget_exceeded",)
    assert result.provider_used is True
    assert result.mode == "provider_validated_after_repair"
    assert result.answer == "- Verify access before release [1]"
    assert "[99]" not in result.answer


def test_combined_failure_with_only_fabricated_lines_stays_fail_closed():
    """Every offending line is fabricated (bad literal + unknown source): line
    surgery keeps nothing citeable and the answer must fall back without any
    repair attempt."""
    pack = _make_release_pair_pack()
    calls = []

    def provider(request):
        calls.append(request)
        return (
            "- Invented step 2026-01-01 [1]\n"
            "- Invented step two [98]"
        )

    result = synthesize_with_provider(
        pack, provider, answer_shape="grounded_summary", max_claims=1
    )

    assert len(calls) == 1
    assert result.provider_used is False
    assert result.mode.startswith("local_")
    assert "Invented" not in result.answer
    assert "[98]" not in result.answer


def test_pure_repairable_and_pure_droppable_keep_previous_routing():
    """Single-category failures keep their original routes: droppable-only
    failures are fixed by line surgery without a repair call, repairable-only
    failures still use exactly one repair attempt."""
    pack = _make_release_pair_pack()
    drop_calls = []

    def drop_provider(request):
        drop_calls.append(request)
        return (
            "- Verify access before release [1]\n"
            "- Invented step [99]\n"
            "- Deploy the release package [2]"
        )

    dropped = synthesize_with_provider(
        pack, drop_provider, answer_shape="grounded_summary", max_claims=3
    )

    assert len(drop_calls) == 1
    assert dropped.provider_used is True
    assert dropped.mode == "provider_validated"
    assert dropped.answer == (
        "- Verify access before release [1]\n- Deploy the release package [2]"
    )

    repair_calls = []

    def repair_provider(request):
        repair_calls.append(request)
        if len(repair_calls) == 1:
            return (
                "- Verify access before release [1]\n"
                "- Deploy the release package [2]"
            )
        return "- Verify access before release [1]"

    repaired = synthesize_with_provider(
        pack, repair_provider, answer_shape="grounded_summary", max_claims=1
    )

    assert len(repair_calls) == 2
    assert repair_calls[0].repair_errors == ()
    assert repair_calls[1].repair_errors == ("provider_answer_claim_budget_exceeded",)
    assert repaired.mode == "provider_validated_after_repair"
    assert repaired.answer == "- Verify access before release [1]"


def test_budget_contract_counts_lines_and_bans_uncited_openers():
    """RAG-CLAIM-BUDGET-HOME: the attempt-1 contract names the line budget and
    bans uncited opening lines (lane proof: every budget miss carried an
    uncited opener beside cited lines)."""
    pack = _make_release_pair_pack()
    plan = build_synthesis_plan(pack, answer_shape="grounded_summary", max_claims=1)
    contract = format_provider_synthesis_contract(plan)

    assert "Maximum material claims: 1" in contract
    assert "at most 1 such lines" in contract
    assert "uncited" in contract


def test_pure_budget_miss_after_repair_recovers_via_deterministic_merge():
    """RAG-CLAIM-BUDGET-HOME (a): a pure budget miss after the repair attempt
    merges same-label cited lines deterministically (Q0703/Q0693 lane shape);
    cited values stay verbatim and the answer is accepted only when valid."""
    pack = _make_release_pair_pack()
    calls = []

    def provider(request):
        calls.append(request)
        return (
            "- Verify access before release [1]\n"
            "- Deploy the release package [1]"
        )

    result = synthesize_with_provider(
        pack, provider, answer_shape="grounded_summary", max_claims=1
    )

    assert len(calls) == 2
    assert calls[1].repair_errors == ("provider_answer_claim_budget_exceeded",)
    assert result.provider_used is True
    assert result.mode == "provider_validated_after_repair"
    assert result.answer == (
        "- Verify access before release [1]; Deploy the release package [1]"
    )


def test_budget_miss_with_fabricated_literal_never_merges():
    """RAG-CLAIM-BUDGET-HOME (b): a budget overrun carrying an unsupported
    literal or unknown source is never merged into grounded text — the
    literal line stays drop-only and an all-fabricated answer stays
    fail-closed."""
    pack = _make_release_pair_pack()
    calls = []

    def provider(request):
        calls.append(request)
        return (
            "- Invented step 2026-01-01 [1]\n"
            "- Deploy the release package [1]"
        )

    result = synthesize_with_provider(
        pack, provider, answer_shape="grounded_summary", max_claims=1
    )

    assert len(calls) == 1
    assert result.provider_used is True
    assert result.mode == "provider_validated"
    assert result.answer == "- Deploy the release package [1]"
    assert "2026-01-01" not in result.answer

    fail_calls = []

    def fail_provider(request):
        fail_calls.append(request)
        return (
            "- Invented step 2026-01-01 [1]\n"
            "- Invented step two [98]"
        )

    failed = synthesize_with_provider(
        pack, fail_provider, answer_shape="grounded_summary", max_claims=1
    )

    assert len(fail_calls) == 1
    assert failed.provider_used is False
    assert failed.mode.startswith("local_")


def test_disciplined_citation_contract_format(monkeypatch):
    """SYNTH-CONTRACT-FREE-HOME: disciplined citation contract variant enforces
    anti-opener discipline, end-of-line citations, claim budget and mandatory limitations
    under AIOS_SYNTHESIS_STRICT_CITATION_CONTRACT flag, while preserving legacy contract
    when disabled."""
    from dataclasses import replace
    from aios_habit.rag_v2.synthesis import (
        disciplined_citation_contract_enabled,
        format_provider_synthesis_contract,
        format_provider_synthesis_repair_contract,
    )

    pack = _make_release_pair_pack()
    plan = build_synthesis_plan(pack, answer_shape="grounded_summary", max_claims=2)

    # 1. Default / Disabled: legacy behavior 100% intact
    monkeypatch.delenv("AIOS_SYNTHESIS_STRICT_CITATION_CONTRACT", raising=False)
    assert disciplined_citation_contract_enabled() is False
    legacy_contract = format_provider_synthesis_contract(plan)
    assert "CRITICAL DISCIPLINE RULES" not in legacy_contract
    assert "Count every factual bullet or paragraph as one material claim: emit at most 2 such lines in total." in legacy_contract

    # 2. Enabled via environment flag
    monkeypatch.setenv("AIOS_SYNTHESIS_STRICT_CITATION_CONTRACT", "1")
    assert disciplined_citation_contract_enabled() is True
    disciplined_contract = format_provider_synthesis_contract(plan)

    assert "CRITICAL DISCIPLINE RULES" in disciplined_contract
    assert "NO UNCITED OPENERS OR INTROS" in disciplined_contract
    assert "EVERY FACTUAL LINE MUST END WITH A CITATION" in disciplined_contract
    assert "STRICT CLAIM BUDGET: Emit at most 2 factual lines in total." in disciplined_contract
    assert "Prioritize fewer, highly certain lines over many lines" in disciplined_contract

    # 3. Enabled with limitations
    plan_with_limitations = replace(plan, limitation_reasons=("unsupported_scope",))
    contract_with_limits = format_provider_synthesis_contract(
        plan_with_limitations, disciplined_citation=True
    )
    assert "MANDATORY FINAL LINE: End with exactly `LIMITATIONS: unsupported_scope`" in contract_with_limits

    # 4. Repair contract includes strict repair discipline hint
    repair = format_provider_synthesis_repair_contract(
        plan, "draft", ["provider_answer_uncited_material_claim"], disciplined_citation=True
    )
    assert "STRICT REPAIR DISCIPLINE" in repair
    assert "Delete any uncited opening or conversational sentences" in repair

