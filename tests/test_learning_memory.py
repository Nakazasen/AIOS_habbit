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

def test_build_handover_markdown_local_includes_learning():
    from aios_habit.case_handover import build_handover_markdown
    c = Case(case_id="C1", title="Test Case", current_situation="Sit", privacy_level="local_only")
    card = SeniorLearningCard(learning_id="L1", case_id="C1", confidence="draft", symptoms="Symp Text", true_cause="My Cause")
    md = build_handover_markdown(c, [], card, "local")
    assert "Bản nháp" in md
    assert "Lưu ý" in md
    assert "Symp Text" in md
    assert "My Cause" in md
    assert "Cảnh báo Bảo mật" in md

def test_build_handover_markdown_cloud_safe_redacts_local_only_learning():
    from aios_habit.case_handover import build_handover_markdown
    # If case is local_only, cloud_safe handover must redact/exclude the learning raw text.
    c = Case(case_id="C1", title="Test Case", current_situation="Sit", privacy_level="local_only")
    card = SeniorLearningCard(learning_id="L1", case_id="C1", confidence="confirmed", symptoms="SECRET_HANDOVER_LOCAL_ONLY_DO_NOT_LEAK", true_cause="My Cause")
    md = build_handover_markdown(c, [], card, "cloud_safe")
    assert "SECRET_HANDOVER_LOCAL_ONLY_DO_NOT_LEAK" not in md
    assert "My Cause" not in md
    assert "bị loại bỏ vì hồ sơ chỉ lưu cục bộ" in md

def test_build_handover_markdown_redacted_does_not_include_raw_local_only():
    from aios_habit.case_handover import build_handover_markdown
    c = Case(case_id="C1", title="Test Case", current_situation="Sit", privacy_level="local_only")
    ev = EvidenceItem(evidence_id="E1", case_id="C1", source_type="note", source_path="manual", title="My Ev", extracted_text="SECRET_HANDOVER_LOCAL_ONLY_DO_NOT_LEAK", privacy_level="local_only")
    card = SeniorLearningCard(learning_id="L1", case_id="C1", confidence="confirmed", symptoms="SECRET_HANDOVER_LOCAL_ONLY_DO_NOT_LEAK")
    md = build_handover_markdown(c, [ev], card, "redacted")
    assert "SECRET_HANDOVER_LOCAL_ONLY_DO_NOT_LEAK" not in md
    assert "ĐÃ ẨN VÌ RIÊNG TƯ" in md

def test_confirmed_learning_without_verification_warns():
    c = Case(case_id="C1", title="Local Case", current_situation="Situation info", privacy_level="local_only")
    card = SeniorLearningCard(learning_id="L1", case_id="C1", confidence="confirmed", symptoms="SECRET_DATA", verification_evidence="none")
    
    # Mock load_learning_cards_for_case to return card
    import aios_habit.learning_models
    original_load = aios_habit.learning_models.load_learning_cards_for_case
    aios_habit.learning_models.load_learning_cards_for_case = lambda cid: [card]
    
    try:
        res = audit_case_cockpit_state(c, [], {})
        assert any("thiếu bằng chứng kiểm chứng" in warn for warn in res["warnings"])
    finally:
        aios_habit.learning_models.load_learning_cards_for_case = original_load

def test_prompt_pack_learning_inclusion_status():
    from aios_habit.case_prompt import get_learning_prompt_policy
    c_local = Case(case_id="C1", title="Local Case", current_situation="Sit", privacy_level="local_only")
    c_cloud = Case(case_id="C2", title="Cloud Case", current_situation="Sit", privacy_level="cloud_allowed")
    card_draft = SeniorLearningCard(learning_id="L1", case_id="C1", confidence="draft")
    card_conf = SeniorLearningCard(learning_id="L2", case_id="C2", confidence="confirmed")
    
    p1 = get_learning_prompt_policy(c_local, card_conf, "gemini")
    assert p1["include_raw"] is False
    assert "hồ sơ chỉ lưu cục bộ" in p1["status_label_vi"]
    
    p2 = get_learning_prompt_policy(c_cloud, card_draft, "gemini")
    assert p2["include_raw"] is False
    assert "chưa xác nhận" in p2["status_label_vi"]
    
    p3 = get_learning_prompt_policy(c_cloud, card_conf, "gemini")
    assert p3["include_raw"] is True
    assert "đã xác nhận và privacy cho phép" in p3["status_label_vi"]

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
