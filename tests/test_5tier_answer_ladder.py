"""Comprehensive test suite for AIOS 5-Tier Answer Ladder (DESKTOP-SELF-LEARN-5TIER-ANSWER-LADDER).

Verifies:
1. Question intent classification into 4 groups: tra_cuu, tong_quan, tong_hop, mo_ho.
2. Tier 1: Direct evidence-backed answer.
3. Tier 2: Synthesized cross-source answer.
4. Tier 3: Ambiguity clarification with 2-4 rephrasing suggestions & provisional answer.
5. Tier 4: Inferred reasoning with mandatory fixed warning banner (eliminating cold refusals).
6. Tier 5: Actionable follow-up buttons (Dạy AIOS, Hỏi chuyên gia, Hỏi AI ngoài).
7. Metrics: Cold Refusal Rate heading to 0% and Rephrase Acceptance Rate.
8. Delivery function: deliver_5tier_ladder_answer end-to-end SQLite persistence and trace building.
"""

from __future__ import annotations

import json
from pathlib import Path
import uuid
import pytest

from aios_habit.final_answer_composer import (
    ACTION_ASK_EXPERT,
    ACTION_ASK_EXTERNAL_AI,
    ACTION_TEACH_AIOS,
    TIER_1_DIRECT,
    TIER_2_SYNTHESIS,
    TIER_3_AMBIGUOUS,
    TIER_4_INFERRED,
    TIER_4_WARNING_BANNER,
    TIER_5_DEFAULT_ACTIONS,
    AnswerLadderMetrics,
    compose_final_owner_answer,
    compute_answer_ladder_metrics,
    deliver_5tier_ladder_answer,
    determine_answer_tier,
    format_tier_3_ambiguous_answer,
    format_tier_4_inferred_answer,
    format_tier_5_actions_markdown,
    is_cold_refusal,
    log_ladder_turn,
    record_ladder_rephrase_acceptance,
    route_question_to_expert_queue,
)
from aios_habit.question_intent_classifier import (
    INTENT_MO_HO,
    INTENT_TONG_HOP,
    INTENT_TONG_QUAN,
    INTENT_TRA_CUU,
    classify_question_intent,
    suggest_rephrasings,
)
from aios_habit.rag_evidence import build_evidence_pack
from aios_habit.rag_ingest import RAGChunk
from aios_habit.rag_search import create_rag_search_schema, index_rag_chunks, search_rag_chunks


def _create_pack(query: str, chunks=None):
    import sqlite3

    effective_chunks = [
        RAGChunk(
            "C1", "D1", ["e1"],
            "Tiêu chuẩn căn chỉnh LSU: góc lệch laser không vượt quá 0.05 mrad theo SOP-LSU-01.",
            "SOP Căn chỉnh LSU", "sop_lsu.pdf", "sop_lsu.pdf", "SOP LSU Trang 1",
            "pdf", ["text"], [1], [], [], [], [], [], "cloud_safe"
        ),
        RAGChunk(
            "C2", "D2", ["e2"],
            "Bảng kiểm tra định kỳ jig: dung sai cơ khí cho phép là ±0.02 mm tại trạm Line 1.",
            "Checklist Jig", "jig_spec.xlsx", "jig_spec.xlsx", "Sheet1 Check",
            "spreadsheet", ["row"], [], ["Sheet1"], [], [], ["2:2"], ["A2:C2"], "cloud_safe"
        ),
    ] if chunks is None else chunks

    conn = sqlite3.connect(":memory:")
    try:
        create_rag_search_schema(conn)
        index_rag_chunks(conn, effective_chunks)
        results = search_rag_chunks(conn, query, limit=5)
        return build_evidence_pack(query, results)
    finally:
        conn.close()


# ==============================================================================
# 1. QUESTION INTENT CLASSIFICATION TESTS (4 GROUPS)
# ==============================================================================

def test_intent_classification_tra_cuu():
    # Specific error codes, definitions, parameters
    res1 = classify_question_intent("Mã lỗi E-041 là gì?")
    assert res1.intent == INTENT_TRA_CUU
    assert res1.confidence >= 0.8

    res2 = classify_question_intent("Thông số góc lệch tiêu chuẩn của laser LSU là bao nhiêu?")
    assert res2.intent == INTENT_TRA_CUU

    res3 = classify_question_intent("Giá trị ctrlMode = 1 nghĩa là gì?")
    assert res3.intent == INTENT_TRA_CUU


def test_intent_classification_tong_quan():
    # High-level workflows, procedures, steps, architecture
    res1 = classify_question_intent("Quy trình kiểm tra LSU gồm những bước nào?")
    assert res1.intent == INTENT_TONG_QUAN
    assert res1.confidence >= 0.8

    res2 = classify_question_intent("Tổng quan về kiến trúc giao tiếp MOM và WMS")
    assert res2.intent == INTENT_TONG_QUAN

    res3 = classify_question_intent("Hướng dẫn chung về các bước vận hành jig tự động")
    assert res3.intent == INTENT_TONG_QUAN


def test_intent_classification_tong_hop():
    # Comparisons, differences, multi-dimensional trends
    res1 = classify_question_intent("So sánh tỷ lệ lỗi giữa Line 1 và Line 2 trong tháng 9")
    assert res1.intent == INTENT_TONG_HOP
    assert res1.confidence >= 0.8

    res2 = classify_question_intent("Khác nhau giữa ctrlMode = 0 và ctrlMode = 1 như thế nào?")
    assert res2.intent == INTENT_TONG_HOP

    res3 = classify_question_intent("Tổng hợp các nguyên nhân và phân tích xu hướng suy giảm jig")
    assert res3.intent == INTENT_TONG_HOP


def test_intent_classification_mo_ho():
    # Very short, missing context or cry-for-help
    res1 = classify_question_intent("LSU bị lỗi")
    assert res1.intent == INTENT_MO_HO
    assert 2 <= len(res1.suggested_rephrasings) <= 4

    res2 = classify_question_intent("Lỗi")
    assert res2.intent == INTENT_MO_HO

    res3 = classify_question_intent("Giúp tôi với")
    assert res3.intent == INTENT_MO_HO

    res4 = classify_question_intent("Hư rồi làm sao?")
    assert res4.intent == INTENT_MO_HO


def test_suggest_rephrasings_domain_anchored():
    # Anchoring on LSU
    sug_lsu = suggest_rephrasings("LSU bị hỏng")
    assert 2 <= len(sug_lsu) <= 4
    assert any("LSU" in s for s in sug_lsu)

    # Anchoring on MOM
    sug_mom = suggest_rephrasings("MOM không chạy")
    assert 2 <= len(sug_mom) <= 4
    assert any("MOM" in s or "Matecon" in s for s in sug_mom)

    # Generic fallback
    sug_gen = suggest_rephrasings("Cái này sao thế")
    assert 2 <= len(sug_gen) <= 4


# ==============================================================================
# 2. 5-TIER RESPONSE LADDER TESTS (TIER 1 - TIER 5)
# ==============================================================================

def test_tier_1_direct_evidence_backed_answer():
    # When query matches evidence precisely
    pack = _create_pack(query="Thông số góc lệch tiêu chuẩn của laser LSU là bao nhiêu?")
    answer = compose_final_owner_answer(pack)

    assert answer.tier in (TIER_1_DIRECT, TIER_2_SYNTHESIS)
    assert "[E1]" in answer.answer_text
    assert "Ket luan ngan" in answer.answer_text
    assert "Bang chung chinh" in answer.answer_text
    # Tier 5 actions attached
    assert "Hành động tiếp nối" in answer.answer_text
    assert "Dạy AIOS điều này" in answer.answer_text
    assert answer.has_warning_banner is False


def test_tier_2_synthesis_cross_source_answer():
    # When query is synthesis/comparison with evidence
    pack = _create_pack(query="So sánh tiêu chuẩn góc lệch LSU và dung sai kiểm tra jig")
    answer = compose_final_owner_answer(pack)

    assert answer.tier == TIER_2_SYNTHESIS
    assert answer.intent == INTENT_TONG_HOP
    assert "Bang chung chinh" in answer.answer_text
    assert "Hành động tiếp nối" in answer.answer_text


def test_tier_3_ambiguous_question_suggestions_and_provisional_answer():
    # Empty evidence pack with ambiguous query -> Tier 3
    empty_pack = _create_pack(query="LSU bị lỗi", chunks=[])
    answer = compose_final_owner_answer(empty_pack)

    assert answer.tier == TIER_3_AMBIGUOUS
    assert answer.intent == INTENT_MO_HO
    assert "Làm rõ ý định câu hỏi" in answer.answer_text
    assert "Gợi ý diễn đạt lại" in answer.answer_text or "👉" in answer.answer_text
    assert len(answer.suggested_rephrasings) >= 2
    # Tier 5 actions attached
    assert "Hành động tiếp nối" in answer.answer_text
    assert answer.has_warning_banner is False


def test_tier_4_inferred_reasoning_with_mandatory_warning_banner():
    # Concrete technical question with NO evidence in knowledge store -> Tier 4
    empty_pack = _create_pack(query="Mã lỗi E-999 trên máy hàn laser là gì?", chunks=[])
    answer = compose_final_owner_answer(empty_pack)

    assert answer.tier == TIER_4_INFERRED
    assert answer.has_warning_banner is True
    # Mandatory warning banner must be strictly present
    assert TIER_4_WARNING_BANNER in answer.answer_text
    assert "LƯU Ý: CÂU TRẢ LỜI ĐƯỢC SUY LUẬN TỰ ĐỘNG BỞI AI" in answer.answer_text
    # Must NOT be a cold refusal
    assert not is_cold_refusal(answer.answer_text)
    # Tier 5 actions attached
    assert "Hành động tiếp nối" in answer.answer_text


def test_tier_5_actionable_followups_attached_to_all_tiers():
    # Tier 5 actions markdown formatting
    md = format_tier_5_actions_markdown(TIER_5_DEFAULT_ACTIONS)
    assert "Hành động tiếp nối" in md
    assert "[🎓 Dạy AIOS điều này]" in md
    assert "[👨‍💼 Hỏi chuyên gia miền]" in md
    assert "[🌐 Hỏi AI ngoài]" in md

    # Check that compose_final_owner_answer includes Tier 5 action items in metadata
    pack = _create_pack("LSU tiêu chuẩn")
    answer = compose_final_owner_answer(pack)
    assert len(answer.action_items) == 3
    action_ids = [a["id"] for a in answer.action_items]
    assert ACTION_TEACH_AIOS in action_ids
    assert ACTION_ASK_EXPERT in action_ids
    assert ACTION_ASK_EXTERNAL_AI in action_ids


# ==============================================================================
# 3. METRICS & COLD REFUSAL RATE TESTS
# ==============================================================================

def test_is_cold_refusal_detection():
    # Bare refusal phrases MUST be detected as cold refusal
    assert is_cold_refusal("Tôi không tìm thấy trong tài liệu có nội dung trả lời câu hỏi này.") is True
    assert is_cold_refusal("Không tìm thấy dữ liệu trích xuất phù hợp trong kho tài liệu để trả lời câu hỏi này.") is True
    assert is_cold_refusal("Chưa tìm thấy đoạn phù hợp trong nguồn đang bật.") is True

    # Tier 4 inferred answer with warning banner is NEVER a cold refusal
    t4_text = format_tier_4_inferred_answer(
        question="Lỗi X",
        inferred_content="Đây là phân tích suy luận kỹ thuật.",
        reasoning_steps=["Bước 1 kiểm tra"],
    )
    assert is_cold_refusal(t4_text) is False

    # Tier 3 ambiguous clarification is NEVER a cold refusal
    t3_text = format_tier_3_ambiguous_answer(
        question="Lỗi",
        suggested_rephrasings=["Quy trình 1", "Quy trình 2"],
        provisional_answer="Trả lời tạm.",
    )
    assert is_cold_refusal(t3_text) is False


def test_compute_answer_ladder_metrics_cold_refusal_zero():
    # Scenario: 5 queries, all handled via Tier 1, 2, 3, or 4 -> 0 cold refusals
    records = [
        {"tier": TIER_1_DIRECT, "answer_text": "Trích dẫn [E1] chuẩn.", "has_tier_5_actions": True},
        {"tier": TIER_2_SYNTHESIS, "answer_text": "Tổng hợp đa nguồn [E1][E2].", "has_tier_5_actions": True},
        {
            "tier": TIER_3_AMBIGUOUS,
            "answer_text": "Làm rõ ý định câu hỏi: gợi ý 1, gợi ý 2.",
            "suggested_rephrasings": ["Quy trình A?", "Quy trình B?"],
            "rephrase_accepted": True,
            "has_tier_5_actions": True,
        },
        {
            "tier": TIER_4_INFERRED,
            "answer_text": f"{TIER_4_WARNING_BANNER}\n\nSuy luận kỹ thuật tham khảo.",
            "has_tier_5_actions": True,
        },
        {
            "tier": TIER_4_INFERRED,
            "answer_text": f"{TIER_4_WARNING_BANNER}\n\nSuy luận kỹ thuật tham khảo 2.",
            "has_tier_5_actions": True,
        },
    ]

    metrics = compute_answer_ladder_metrics(records)
    assert metrics.total_queries == 5
    assert metrics.cold_refusal_count == 0
    assert metrics.cold_refusal_rate == 0.0  # Goal achieved: 0% cold refusal!
    assert metrics.tier_1_count == 1
    assert metrics.tier_2_count == 1
    assert metrics.tier_3_count == 1
    assert metrics.tier_4_count == 2
    assert metrics.tier_5_action_count == 5
    assert metrics.rephrase_offered_count == 1
    assert metrics.rephrase_accepted_count == 1
    assert metrics.rephrase_acceptance_rate == 100.0


def test_rephrase_acceptance_and_expert_routing_logging(tmp_path: Path):
    # Test recording rephrase acceptance
    evt = record_ladder_rephrase_acceptance(
        conversation_id="conv-test-1",
        message_id="msg-test-1",
        chosen_rephrase="Quy trình xử lý mã lỗi LSU",
        base_cases_dir=tmp_path,
    )
    assert evt["chosen_rephrase"] == "Quy trình xử lý mã lỗi LSU"
    rephrase_file = tmp_path / "rephrase_events.jsonl"
    assert rephrase_file.exists()
    assert "Quy trình xử lý mã lỗi LSU" in rephrase_file.read_text(encoding="utf-8")

    # Test routing to expert queue
    inq = route_question_to_expert_queue(
        conversation_id="conv-test-1",
        message_id="msg-test-1",
        question="Lỗi E-999 máy hàn",
        domain="kho_lsu",
        base_cases_dir=tmp_path,
    )
    assert inq["domain"] == "kho_lsu"
    inq_file = tmp_path / "expert_queue.jsonl"
    assert inq_file.exists()
    assert "Lỗi E-999 máy hàn" in inq_file.read_text(encoding="utf-8")


# ==============================================================================
# 4. DELIVERY INTEGRATION TESTS (END-TO-END SQLITE PERSISTENCE)
# ==============================================================================

def test_deliver_5tier_ladder_answer_ambiguous_tier_3():
    from aios_habit.workspace_chat_store import load_messages
    conv_id = f"CONV-T3-{uuid.uuid4().hex[:8]}"

    chunks_collected = []
    def on_chunk(chunk: str):
        chunks_collected.append(chunk)

    ok, msg, badge, err = deliver_5tier_ladder_answer(
        question="LSU bị lỗi",
        conversation_id=conv_id,
        notebook_id="NB-LSU",
        user_raw_input="LSU bị lỗi",
        on_chunk=on_chunk,
    )

    assert ok is True
    assert err is None
    assert badge is not None
    assert badge["tier"] == TIER_3_AMBIGUOUS
    assert badge["has_warning_banner"] is False
    assert len(badge["suggested_rephrasings"]) >= 2
    assert len(chunks_collected) >= 1

    # Verify messages persisted in SQLite
    saved_msgs = load_messages(conv_id)
    assert len(saved_msgs) >= 1
    asst_msg = next(m for m in saved_msgs if m.role == "assistant")
    assert "Làm rõ ý định câu hỏi" in asst_msg.content
    assert "Hành động tiếp nối" in asst_msg.content
    assert asst_msg.metadata.get("tier") == TIER_3_AMBIGUOUS


def test_deliver_5tier_ladder_answer_missing_evidence_tier_4():
    from aios_habit.workspace_chat_store import load_messages
    conv_id = f"CONV-T4-{uuid.uuid4().hex[:8]}"

    chunks_collected = []
    def on_chunk(chunk: str):
        chunks_collected.append(chunk)

    ok, msg, badge, err = deliver_5tier_ladder_answer(
        question="Mã lỗi E-099 trên bộ điều khiển robot hàn",
        conversation_id=conv_id,
        notebook_id="NB-ROBOT",
        user_raw_input="Mã lỗi E-099 trên bộ điều khiển robot hàn",
        on_chunk=on_chunk,
    )

    assert ok is True
    assert err is None
    assert badge is not None
    assert badge["tier"] == TIER_4_INFERRED
    assert badge["has_warning_banner"] is True
    assert len(chunks_collected) >= 1

    # Verify messages persisted in SQLite
    saved_msgs = load_messages(conv_id)
    assert len(saved_msgs) >= 1
    asst_msg = next(m for m in saved_msgs if m.role == "assistant")
    # Verify mandatory fixed warning banner is in the saved assistant message
    assert TIER_4_WARNING_BANNER in asst_msg.content
    assert "Hành động tiếp nối" in asst_msg.content
    assert asst_msg.metadata.get("has_warning_banner") is True
    assert not is_cold_refusal(asst_msg.content)
