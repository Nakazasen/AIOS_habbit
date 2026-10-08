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
    assert plan.intent_category == "cross_source_synthesis"
    assert plan.target_retrieval_limit == 25


def test_two_question_clauses_become_cross_source_facets():
    from aios_habit.rag_v2.query_planning import query_needs_broad_ready_retrieval

    plan = identity_query_plan(
        "How does data flow between connected systems, and where should an operator verify failures?"
    )
    facet_texts = [variant.text.casefold() for variant in plan.variants if variant.origin == "facet"]

    assert plan.intent_category == "cross_source_synthesis"
    assert plan.target_retrieval_limit == 25
    assert len(facet_texts) == 2
    assert any("data flow" in text for text in facet_texts)
    assert any("verify" in text for text in facet_texts)
    assert query_needs_broad_ready_retrieval(plan) is True


def test_vietnamese_two_clause_question_splits_on_question_cues():
    plan = identity_query_plan(
        "Luồng dữ liệu giữa các hệ thống đi như thế nào và chỗ nào kiểm tra lỗi?"
    )
    facet_texts = [variant.text.casefold() for variant in plan.variants if variant.origin == "facet"]

    assert plan.intent_category == "cross_source_synthesis"
    assert len(facet_texts) == 2
    assert any("luồng" in text or "dữ liệu" in text for text in facet_texts)
    assert any("kiểm" in text or "lỗi" in text for text in facet_texts)


def test_noun_phrase_and_does_not_create_false_facets():
    query = "Describe the architectural components and how they integrate."
    plan = identity_query_plan(query)

    assert plan.intent_category == "general"
    assert [variant.text for variant in plan.variants] == [query]


def test_explicit_multi_source_wording_uses_cross_source_budget():
    plan = identity_query_plan("Tổng hợp từ tất cả các tài liệu đã có")

    assert plan.intent_category == "cross_source_synthesis"
    assert plan.target_retrieval_limit == 25
    assert [variant.origin for variant in plan.variants] == ["original"]


def test_architecture_wording_uses_cross_source_budget():
    plan = identity_query_plan(
        "What is the overall system architecture for production history registration?"
    )
    assert plan.intent_category == "cross_source_synthesis"
    assert plan.target_retrieval_limit == 25


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


def test_technical_query_intent_classification_diagnosis_and_lookup():
    from aios_habit.rag_v2.query_planning import coerce_query_plan

    # Technical LSU queries (mã lỗi, hiện tượng, nguyên nhân, đối sách, bảng thông số, dung sai, ngưỡng)
    # Tất cả các câu hỏi kỹ thuật này đều thuộc diagnosis để kích hoạt ngân sách 10 luận điểm
    diag_queries = [
        "C23とC24ではどのような発生Trendでしたか。",
        "Điểm bất thường được phát hiện ở Jig nào và vị trí Camera nào?",
        "File có xác nhận chênh lệch DMT–PMT chính là nguyên nhân duy nhất gây NG không?",
        "Kết quả xác nhận 4M có phát hiện bất thường không?",
        "Tăng thời gian ép từ 3 giây lên 6 giây có hiệu quả không?",
        "SIM追加後のMagenta光路高さとC7620発生率はどうなりましたか。",
        "排查时应先调整Unit还是确认Jig相关性？",
        "C7620中Magenta相对Black的副扫描色差达到多少会成为NG？",
        "Trong bảng quy đổi Skew, Black, Cyan, Magenta và Yellow lần lượt có giá trị µm và dot bao nhiêu?",
        "Các mục tham khảo số 13–16 có nominal và dung sai thế nào?",
        "Kích thước tại các điểm Y73–Y104 có giới hạn bao nhiêu?",
        "Yellow、Cyan、Magenta分别有多少件？",
        "BeamPosX=3024,6 µm cách hai giới hạn bao nhiêu?",
    ]
    for q in diag_queries:
        plan = coerce_query_plan(q)
        assert plan.intent_category == "diagnosis", f"Query '{q}' should be diagnosis, got {plan.intent_category}"

    # Pure coordinate / location lookup queries (tra cứu vị trí ô, sheet, tài liệu)
    coord_lookup_queries = [
        "Find the supply-instruction location in the document",
        "Bảng dữ liệu này nằm ở sheet nao?",
        "Cho biết toa do o của ô tiêu đề",
        "What is the cell location of this record?",
        "Extract the source coordinate for the adjustment step",
    ]
    for q in coord_lookup_queries:
        plan = coerce_query_plan(q)
        assert plan.intent_category == "lookup", f"Query '{q}' should be lookup, got {plan.intent_category}"



def test_technical_query_intent_negative_guards():
    from aios_habit.rag_v2.query_planning import coerce_query_plan

    # Negative guards: khái niệm chung, tổng quan không bị nuốt sang diagnosis/lookup
    neg_queries = [
        "Hướng quét chính và hướng quét phụ khác nhau thế nào?",
        "Hai loại Motor Polygon được tài liệu phân biệt như thế nào?",
        "Tổng quan về khái niệm và định nghĩa hệ thống",
    ]
    for q in neg_queries:
        plan = coerce_query_plan(q)
        assert plan.intent_category == "general", f"Query '{q}' should remain general, got {plan.intent_category}"


def test_lsu_50_questions_intent_distribution_activates_claim_budget():
    import json
    from aios_habit.rag_v2.query_planning import coerce_query_plan

    with open("tests/fixtures/eval/lsu_quality_50_questions.json", encoding="utf-8") as f:
        data = json.load(f)

    counts = {}
    for item in data:
        plan = coerce_query_plan(item["question"])
        counts[plan.intent_category] = counts.get(plan.intent_category, 0) + 1

    # Khẳng định đa số câu (>= 40/50 câu) nhận diagnosis hoặc lookup để kích hoạt ngân sách 10
    budget_10_count = counts.get("diagnosis", 0) + counts.get("lookup", 0) + counts.get("cross_source_synthesis", 0)
    assert budget_10_count >= 40, f"Expected at least 40 questions to receive budget 10 intent, got {budget_10_count}"
    assert counts.get("general", 0) >= 2, "Negative controls should remain general"
    assert counts.get("procedure", 0) >= 2, "Procedural questions should remain procedure"

