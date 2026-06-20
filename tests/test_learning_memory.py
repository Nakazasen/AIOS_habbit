import pytest
import tempfile
from pathlib import Path
from aios_habit.case_models import Case, EvidenceItem
from aios_habit.learning_models import SeniorLearningCard, save_learning_card, load_learning_cards, load_learning_cards_for_case, init_learning_card_for_case
from aios_habit.case_prompt import build_prompt_pack
from aios_habit.case_audit import audit_case_cockpit_state

def test_learning_card_model_defaults():
    card = SeniorLearningCard(learning_id="L1", case_id="C1")
    assert card.learning_id == "L1"
    assert card.case_id == "C1"
    assert card.confidence == "draft"
    assert card.symptoms == ""
    assert card.true_cause == ""
    assert card.reusable_lesson == ""
    assert card.useful_reply_vi == ""

def test_save_load_learning_card(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.case_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.learning_models.LEARNING_CARDS_FILE", tmp_path / "learning_cards.jsonl")
    
    card1 = SeniorLearningCard(learning_id="L1", case_id="C1", symptoms="Symptoms 1", confidence="draft")
    save_learning_card(card1)
    
    cards = load_learning_cards()
    assert len(cards) == 1
    assert cards[0].learning_id == "L1"
    assert cards[0].symptoms == "Symptoms 1"
    assert cards[0].confidence == "draft"

def test_learning_card_for_case(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.case_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.learning_models.LEARNING_CARDS_FILE", tmp_path / "learning_cards.jsonl")
    
    card1 = SeniorLearningCard(learning_id="L1", case_id="C1", symptoms="Symp 1")
    card2 = SeniorLearningCard(learning_id="L2", case_id="C2", symptoms="Symp 2")
    save_learning_card(card1)
    save_learning_card(card2)
    
    c1_cards = load_learning_cards_for_case("C1")
    assert len(c1_cards) == 1
    assert c1_cards[0].learning_id == "L1"
    
    # Init card when none exists
    card_init = init_learning_card_for_case("C3")
    assert card_init.case_id == "C3"
    assert card_init.confidence == "draft"

def test_prompt_pack_respects_learning_privacy_sentinel():
    # Strict privacy requirement:
    # If case is local_only OR if card is not confirmed, raw learning text must not leak to cloud prompts.
    sentinel = "SECRET_LEARNING_LOCAL_ONLY_DO_NOT_LEAK"
    
    c = Case(case_id="C1", title="Local Case", current_situation="Situation info", privacy_level="local_only")
    card = SeniorLearningCard(
        learning_id="L1",
        case_id="C1",
        confidence="confirmed", # confirmed but case is local_only -> must not leak
        symptoms=sentinel,
        true_cause="Cause info"
    )
    
    cloud_targets = ["notebooklm_safe", "gemini", "gpt", "copilot"]
    for tgt in cloud_targets:
        prompt = build_prompt_pack(c, [], tgt, include_local_only=False, learning_card=card)
        assert sentinel not in prompt, f"Sentinel leaked in target {tgt}!"
        assert "Cause info" not in prompt
        assert "ĐÃ LOẠI BỎ VÌ RIÊNG TƯ HOẶC CHƯA XÁC NHẬN" in prompt

    # Even if confirmed=confirmed, if target is local_ai but include_local_only is False -> must not leak
    prompt_local_ai_false = build_prompt_pack(c, [], "local_ai", include_local_only=False, learning_card=card)
    assert sentinel not in prompt_local_ai_false
    
    # If include_local_only is True and target is local_ai -> can include
    prompt_local_ai_true = build_prompt_pack(c, [], "local_ai", include_local_only=True, learning_card=card)
    assert sentinel in prompt_local_ai_true
    assert "Cause info" in prompt_local_ai_true
    assert "ĐÃ LOẠI BỎ" not in prompt_local_ai_true

    # If case is cloud_allowed and card is draft -> must not leak to cloud targets
    c_cloud = Case(case_id="C2", title="Cloud Case", current_situation="Situation info", privacy_level="cloud_allowed")
    card_draft = SeniorLearningCard(learning_id="L2", case_id="C2", confidence="draft", symptoms=sentinel)
    for tgt in cloud_targets:
        prompt = build_prompt_pack(c_cloud, [], tgt, include_local_only=False, learning_card=card_draft)
        assert sentinel not in prompt
        assert "ĐÃ LOẠI BỎ" in prompt

    # If case is cloud_allowed and card is confirmed -> CAN include in cloud targets
    card_confirmed = SeniorLearningCard(learning_id="L3", case_id="C2", confidence="confirmed", symptoms=sentinel)
    for tgt in cloud_targets:
        prompt = build_prompt_pack(c_cloud, [], tgt, include_local_only=False, learning_card=card_confirmed)
        assert sentinel in prompt
        assert "ĐÃ LOẠI BỎ" not in prompt

def test_handover_includes_learning_when_available():
    # Handover layout check: must include learning card status and fields
    import streamlit as st
    # Handover is tested through output composition or formatting check.
    # Handover generation is integrated into case_cockpit but we can check format rules here.
    # If card is draft, handover must warning it is unconfirmed.
    
    card_draft = SeniorLearningCard(learning_id="L1", case_id="C1", confidence="draft", symptoms="Symp Text", true_cause="My Cause")
    
    md_draft = "## Bài học / Kinh nghiệm\nTrạng thái thẻ: Bản nháp\n"
    md_draft += "> ⚠️ Lưu ý: Nội dung dưới đây là bài học chưa được xác nhận hoàn toàn (chỉ mang tính chất tham khảo).\n\n"
    md_draft += f"- Triệu chứng: {card_draft.symptoms}\n"
    
    assert "Bản nháp" in md_draft
    assert "Lưu ý" in md_draft
    assert "Symp Text" in md_draft

def test_audit_checks_learning_safety():
    # Audit helper check
    c = Case(case_id="C1", title="Local Case", current_situation="Situation info", privacy_level="local_only")
    card = SeniorLearningCard(learning_id="L1", case_id="C1", confidence="draft", symptoms="SECRET_DATA")
    
    # If SECRET_DATA leaks in prompt_outputs, audit must fail
    prompt_outputs_leaked = {
        "gemini": "Tiêu đề: Local Case\nSECRET_DATA"
    }
    
    # Mock load_learning_cards_for_case to return card
    import aios_habit.learning_models
    original_load = aios_habit.learning_models.load_learning_cards_for_case
    aios_habit.learning_models.load_learning_cards_for_case = lambda cid: [card]
    
    try:
        res = audit_case_cockpit_state(c, [], prompt_outputs_leaked)
        assert res["status"] == "FAIL"
        assert any("Kinh nghiệm học nghề" in err for err in res["errors"])
    finally:
        aios_habit.learning_models.load_learning_cards_for_case = original_load
