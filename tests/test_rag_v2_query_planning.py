from aios_habit.rag_v2.query_planning import (
    build_query_plan,
    detect_query_language,
    identity_query_plan,
    match_text_obligations,
)


def test_identity_plan_does_not_infer_semantic_intent_from_query_vocabulary():
    for query in (
        "How should we address a service outage?",
        "List all error codes in the table",
        "Describe the architectural components and how they integrate.",
        "How do these services exchange data through their interfaces?",
    ):
        plan = identity_query_plan(query)
        assert plan.intent_category == "general"
        assert plan.required_obligations == ("query",)


def test_identity_plan_only_splits_facets_explicitly_present_in_query_structure():
    query = "First requested topic; second requested topic; third requested topic"
    plan = identity_query_plan(query)

    assert [variant.text for variant in plan.variants] == [
        query,
        "First requested topic",
        "second requested topic",
        "third requested topic",
    ]
    assert plan.facet_ids == ("query", "facet_1", "facet_2", "facet_3")
    assert all(variant.origin == "facet" for variant in plan.variants[1:])


def test_operational_how_it_works_question_uses_procedure_shape_without_aliases():
    query = "Chế độ Manual Matecon ACR/CTU hoạt động như thế nào?"

    plan = identity_query_plan(query)

    assert plan.intent_category == "procedure"
    assert plan.required_obligations == ("query",)
    assert [variant.text for variant in plan.variants] == [query]


def test_target_terms_are_literal_query_terms_without_semantic_rewriting():
    query = "Summarize the material-handling operation procedure."
    plan = identity_query_plan(query)

    assert plan.target_terms == (
        "summarize", "material", "handling", "operation", "procedure",
    )


def test_obligation_matcher_does_not_classify_source_text_with_embedded_cues():
    matched = match_text_obligations(
        "procedure",
        "Open the model, press Save, and verify the result.",
        required_obligations=("precheck", "step", "postcheck"),
    )
    assert matched == ()


def test_query_language_detection_is_deterministic_and_query_only():
    samples = {
        "Quy trình kiểm tra trạng thái kho là gì?": "vi",
        "生産履歴の登録手順を教えてください": "ja",
        "What is the production history registration procedure?": "en",
        "12345": "unknown",
    }
    for query, expected_language in samples.items():
        plan = identity_query_plan(query)
        assert detect_query_language(query) == expected_language
        assert plan.variants[0].language_hint == expected_language


def test_identity_plan_has_no_implicit_subject_equivalents():
    plan = identity_query_plan(
        "What is the overall system architecture for production history registration?",
        status="expansion_unavailable",
    )
    assert len(plan.variants) == 1
    assert plan.variants[0].origin == "original"
    assert not plan.variants[0].target_equivalent
    assert plan.expansion_status == "expansion_unavailable"


def test_external_query_only_expansion_is_bounded_and_inspectable():
    plan = build_query_plan(
        "Explain the requested process",
        {"variants": [{
            "text": "Explain the requested workflow",
            "language_hint": "en",
            "origin": "translation",
            "target_equivalent": True,
        }]},
    )
    assert plan.expansion_status == "expanded"
    assert len(plan.variants) == 2
    expanded = plan.variants[1]
    assert expanded.variant_id == "expansion_1"
    assert expanded.origin == "translation"
    assert expanded.target_equivalent is True


def test_structural_origin_cannot_claim_target_equivalence():
    plan = build_query_plan(
        "Explain the requested process",
        {"variants": [{
            "text": "Requested process details",
            "origin": "structural_intent",
            "target_equivalent": True,
        }]},
    )
    assert len(plan.variants) == 2
    assert plan.variants[1].target_equivalent is False


def test_expansion_rejects_control_characters():
    plan = build_query_plan(
        "Explain the requested process",
        {"variants": [{"text": "unsafe\x00variant", "origin": "translation"}]},
    )
    assert len(plan.variants) == 1
    assert plan.expansion_status == "expansion_rejected"
