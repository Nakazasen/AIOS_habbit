from aios_habit.claim_guard import evaluate_claim_readiness


def test_mom_only_blocks_general_notebooklm_replacement():
    result = evaluate_claim_readiness(
        test_scope="MOM/WMS 12Q",
        corpus_domains=["manufacturing_mom_wms"],
        answer_quality="strong",
        model_used="deterministic",
        human_review_status="passed",
        claim_type="general_notebooklm_replacement",
    )
    assert result.allowed is False
    assert any("MOM/WMS-only" in reason for reason in result.reasons)


def test_deterministic_vs_notebooklm_model_blocks_parity():
    result = evaluate_claim_readiness(
        test_scope="AIOS deterministic vs NotebookLM model",
        corpus_domains=["hr_policy", "accounting", "it_ops"],
        answer_quality="strong",
        model_used="deterministic_composer",
        human_review_status="passed",
        claim_type="notebooklm_parity",
    )
    assert result.allowed is False
    assert any("Deterministic AIOS" in reason for reason in result.reasons)


def test_human_review_pending_blocks_replacement():
    result = evaluate_claim_readiness(
        test_scope="multi-domain",
        corpus_domains=["hr_policy", "accounting", "it_ops"],
        answer_quality="strong",
        model_used="model_assisted",
        human_review_status="pending",
        claim_type="daily_replacement",
    )
    assert result.allowed is False
    assert any("Human review" in reason for reason in result.reasons)


def test_p1_claim_blocked_without_explicit_owner_approval():
    result = evaluate_claim_readiness(
        test_scope="release",
        corpus_domains=["general"],
        answer_quality="strong",
        model_used="model_assisted",
        human_review_status="passed",
        claim_type="p1_opened",
        owner_approved_p1=False,
    )
    assert result.allowed is False
    assert any("P1.0" in reason for reason in result.reasons)


def test_replacement_claim_blocked_when_aios_weaker():
    result = evaluate_claim_readiness(
        test_scope="multi-domain",
        corpus_domains=["hr_policy", "accounting", "it_ops"],
        answer_quality="weaker",
        model_used="model_assisted",
        human_review_status="passed",
        claim_type="daily_replacement",
    )
    assert result.allowed is False
    assert any("quality" in reason.lower() for reason in result.reasons)


def test_claim_guard_returns_clear_reason():
    result = evaluate_claim_readiness(
        test_scope="MOM/WMS 12Q",
        corpus_domains=["manufacturing"],
        answer_quality="partial",
        model_used="deterministic",
        human_review_status="pending",
        claim_type="general_notebooklm_replacement",
    )
    assert result.allowed is False
    assert result.reasons
    assert all(isinstance(reason, str) and reason for reason in result.reasons)
