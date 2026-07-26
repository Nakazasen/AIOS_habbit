from aios_habit.rag_v2.query_planning import identity_query_plan


def test_diagnosis_intent_recognizes_generic_outage_and_recovery_paraphrases():
    for query in (
        "How should we address a service outage?",
        "Why is the service unavailable and what should operators do?",
        "What went wrong and how can I recover?",
        "Các dấu hiệu bất thường là gì và xử lý thế nào?",
    ):
        plan = identity_query_plan(query)
        assert plan.intent_category == "diagnosis"
        assert plan.required_obligations == ("problem", "check", "action")


def test_lookup_precedence_prevents_error_terms_from_forcing_diagnosis():
    plan = identity_query_plan("List all error codes in the table")

    assert plan.intent_category == "lookup"
    assert plan.required_obligations == ("lookup_target", "data_value")
