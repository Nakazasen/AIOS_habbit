from aios_habit.source_router import classify_query_profile


def test_hr_policy_question_does_not_classify_as_manufacturing():
    profile = classify_query_profile("What does the HR leave policy say about parental leave?")
    assert profile.profile_id == "factual_lookup"


def test_accounting_invoice_question_does_not_use_manufacturing_profile():
    profile = classify_query_profile("Extract invoice number, tax amount, and vendor from this accounting invoice")
    assert profile.profile_id == "extract_fields"


def test_japanese_learning_question_does_not_trigger_workflow():
    profile = classify_query_profile("Summarize this Japanese grammar lesson and rewrite examples")
    assert profile.profile_id in {"translation_or_rewrite", "summarize_document"}


def test_legal_contract_question_uses_decision_or_lookup_not_manufacturing():
    profile = classify_query_profile("What termination risk should we consider in this legal contract?")
    assert profile.profile_id == "decision_support"


def test_generic_pdf_manual_uses_procedure_steps():
    profile = classify_query_profile("What are the procedure steps in this printer PDF manual?")
    assert profile.profile_id == "procedure_steps"


def test_screenshot_question_maps_to_generic_image_visible_facts():
    profile = classify_query_profile("What does this screenshot show?")
    assert profile.profile_id == "image_visible_facts"


def test_schema_question_maps_to_generic_schema_question():
    profile = classify_query_profile("Which tables and fields are defined in this SQL schema?")
    assert profile.profile_id == "schema_question"


def test_troubleshooting_question_maps_to_generic_without_manufacturing_terms():
    profile = classify_query_profile("Give a troubleshooting path for this application error")
    assert profile.profile_id == "troubleshooting_general"
