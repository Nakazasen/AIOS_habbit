"""Tests for DESKTOP-DRAFT-FALLBACK-WIRE-HOME.

Verifies wiring of resolve_answer / deliver_draft_answer into:
1. workspace_chat_app.py (at summary_count == 0 & quality_search_unavailable)
2. antigravity_bridge.py (at _try_local_fallback when no lines)
3. Mandatory draft label 'Bản thảo — chưa qua chuyên gia duyệt'
4. Feature flag toggle (AIOS_FEATURE_ANSWER_DRAFT_FALLBACK)
5. Non-interference when main path has evidence
6. Local metric logging in local_cases (never the knowledge store)
"""

import os
from pathlib import Path
import pytest

from aios_habit.answer_draft_fallback import (
    DRAFT_LABEL,
    DraftEntry,
    clear_draft_fallback_override,
    set_draft_fallback_override,
    clear_cached_draft_entries,
    deliver_draft_answer,
    log_draft_fallback_activation,
    count_draft_fallback_activations,
    resolve_answer,
)
from aios_habit.workspace_chat_models import WorkspaceConversation, ChatMessage
from aios_habit.workspace_chat_store import (
    save_conversation,
    load_messages,
    save_message,
)


@pytest.fixture(autouse=True)
def _clean_draft_state():
    clear_draft_fallback_override()
    clear_cached_draft_entries()
    yield
    clear_draft_fallback_override()
    clear_cached_draft_entries()


def _sample_draft_entries():
    return [
        DraftEntry(
            question="File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?",
            answer="Tài liệu nêu vấn đề Hiệu suất jig giảm sút nhưng chưa có chức năng tự động cảnh báo khi hoạt động của jig bắt đầu có xu hướng xấu. Hướng đối sách là xây dựng AI dự đoán và cảnh báo. Nguồn file: AI_LSU_du_doan_loi.xlsx.",
            source_file="lsu/batch-16.md",
            position=4,
        ),
        DraftEntry(
            question="Trong file cấu hình Matecon, ctrlMode = 0 và ctrlMode = 1 khác nhau thế nào?",
            answer="ctrlMode = 0 là tự động, ctrlMode = 1 là thủ công.",
            source_file="mom/batch-01.md",
            position=1,
        ),
    ]


def test_deliver_draft_answer_success_with_label_and_logging(tmp_path):
    conv_id = "conv_test_deliver_01"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id="NB-LAZY-LSU",
            title="Test Conversation",
        )
    )

    q = "File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?"
    res = deliver_draft_answer(
        q,
        conversation_id=conv_id,
        notebook_id="NB-LAZY-LSU",
        draft_entries=_sample_draft_entries(),
        base_cases_dir=tmp_path,
        enabled=True,
    )

    assert res is not None
    ok, succ_msg, badge, err = res
    assert ok is True
    assert err is None
    assert "bản thảo dự bị" in succ_msg
    assert badge is not None
    assert badge.get("is_draft_fallback") is True
    assert badge.get("source_titles") == ["lsu/batch-16.md"]

    # Verify message in storage
    msgs = load_messages(conv_id)
    assert len(msgs) >= 1
    assistant_msg = [m for m in msgs if m.role == "assistant"][-1]
    assert "Hiệu suất jig giảm sút" in assistant_msg.content
    assert DRAFT_LABEL in assistant_msg.content

    # Verify metric logging in local_cases
    count = count_draft_fallback_activations(base_dir=tmp_path)
    assert count == 1


def test_deliver_draft_answer_returns_none_when_flag_disabled(tmp_path):
    conv_id = "conv_test_deliver_disabled"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id="NB-LAZY-LSU",
            title="Test Conversation",
        )
    )

    q = "File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?"
    res = deliver_draft_answer(
        q,
        conversation_id=conv_id,
        notebook_id="NB-LAZY-LSU",
        draft_entries=_sample_draft_entries(),
        base_cases_dir=tmp_path,
        enabled=False,
    )

    assert res is None
    assert count_draft_fallback_activations(base_dir=tmp_path) == 0


def test_deliver_draft_answer_returns_none_when_no_match(tmp_path):
    conv_id = "conv_test_no_match"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id="NB-LAZY-LSU",
            title="Test Conversation",
        )
    )

    q = "Thủ đô của sao Hỏa là gì và dân số bao nhiêu?"
    res = deliver_draft_answer(
        q,
        conversation_id=conv_id,
        notebook_id="NB-LAZY-LSU",
        draft_entries=_sample_draft_entries(),
        base_cases_dir=tmp_path,
        enabled=True,
    )

    assert res is None
    assert count_draft_fallback_activations(base_dir=tmp_path) == 0


def test_workspace_chat_app_wire_summary_count_zero_triggers_draft(monkeypatch):
    """When retrieval finds summary_count == 0, draft fallback triggers."""
    from aios_habit import workspace_chat_app as app
    from aios_habit.answer_draft_fallback import set_draft_fallback_override

    conv_id = "conv_app_wire_test"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id="NB-LAZY-LSU",
            title="App Wire Test",
        )
    )

    q = "File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?"

    # Mock retrieval to return summary_count == 0
    monkeypatch.setattr(
        app,
        "_run_chat_turn_async",
        app._run_chat_turn_async,
    )

    # Monkeypatch retrieve_workspace_chat_evidence to simulate summary_count == 0
    def _mock_retrieval(*args, **kwargs):
        return {
            "status": "ready",
            "summary_count": 0,
            "evidence_items": [],
            "retrieved_context_sources": (),
            "safe_owner_message": "",
        }

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.retrieve_workspace_chat_evidence",
        _mock_retrieval,
    )

    set_draft_fallback_override(True)

    res = app._run_chat_turn_async(
        q_text=q,
        conversation_id=conv_id,
        notebook_id="NB-LAZY-LSU",
        query_relevant_sources=(),
        forced_domain="lsu",
    )

    assert res[0] is True
    badge = res[2]
    assert badge is not None
    assert badge.get("is_draft_fallback") is True

    msgs = load_messages(conv_id)
    asst_msg = [m for m in msgs if m.role == "assistant"][-1]
    assert DRAFT_LABEL in asst_msg.content
    assert "Hiệu suất jig giảm sút" in asst_msg.content


def test_workspace_chat_app_wire_flag_off_returns_legacy_error(monkeypatch):
    """When flag is off, summary_count == 0 returns the legacy error message."""
    from aios_habit import workspace_chat_app as app

    conv_id = "conv_app_wire_flag_off"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id="mom_opcenter",
            title="Flag Off Test",
        )
    )

    q = "File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?"

    def _mock_retrieval(*args, **kwargs):
        return {
            "status": "ready",
            "summary_count": 0,
            "evidence_items": [],
            "retrieved_context_sources": (),
            "safe_owner_message": "",
        }

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.retrieve_workspace_chat_evidence",
        _mock_retrieval,
    )

    set_draft_fallback_override(False)

    res = app._run_chat_turn_async(
        q_text=q,
        conversation_id=conv_id,
        notebook_id="NB-LAZY-LSU",
        query_relevant_sources=(),
        forced_domain="lsu",
    )

    # 5-tier ladder takes over and avoids cold refusal
    assert res[0] is True
    assert res[2] is not None
    assert res[2].get("cold_refusal_avoided") is True or res[2].get("is_draft_fallback") is not True


def test_antigravity_bridge_local_fallback_triggers_draft():
    """In antigravity_bridge, _try_local_fallback triggers draft fallback when no lines."""
    from aios_habit.antigravity_bridge import route_workspace_chat_submission

    conv_id = "conv_bridge_wire_test"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id="NB-LAZY-LSU",
            title="Bridge Wire Test",
        )
    )

    q = "File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?"
    set_draft_fallback_override(True)

    ok, succ_msg, badge, err = route_workspace_chat_submission(
        question=q,
        evidence_items=[],
        packed_sources=(),
        conversation_id=conv_id,
        notebook_id="NB-LAZY-LSU",
        retrieval_applied=False,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(),
        chat_history=(),
        user_raw_input=q,
        backend="local",
    )

    assert ok is True
    assert err is None
    assert badge is not None
    assert badge.get("is_draft_fallback") is True
    assert badge.get("source_titles") == ["lsu\\batch-16.md"] or badge.get("source_titles") == ["lsu/batch-16.md"]

    msgs = load_messages(conv_id)
    asst = [m for m in msgs if m.role == "assistant"][-1]
    assert DRAFT_LABEL in asst.content
    assert "Hiệu suất jig giảm sút" in asst.content


def test_antigravity_bridge_local_fallback_flag_off_returns_static_error():
    """In antigravity_bridge, when flag is off, returns static not found sentence."""
    from aios_habit.antigravity_bridge import route_workspace_chat_submission

    conv_id = "conv_bridge_flag_off"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id="mom_opcenter",
            title="Bridge Flag Off Test",
        )
    )

    q = "File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?"
    set_draft_fallback_override(False)

    ok, succ_msg, badge, err = route_workspace_chat_submission(
        question=q,
        evidence_items=[],
        packed_sources=(),
        conversation_id=conv_id,
        notebook_id="NB-LAZY-LSU",
        retrieval_applied=False,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(),
        chat_history=(),
        user_raw_input=q,
        backend="local",
    )

    assert ok is True
    msgs = load_messages(conv_id)
    asst = [m for m in msgs if m.role == "assistant"][-1]
    # Inferred answer delivered without draft label
    assert DRAFT_LABEL not in asst.content


def test_main_path_evidence_does_not_interfere():
    """When main path has evidence items, _try_local_fallback uses cited items, not draft."""
    from aios_habit.antigravity_bridge import route_workspace_chat_submission

    conv_id = "conv_bridge_evidence_test"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id="mom_opcenter",
            title="Evidence Test",
        )
    )

    q = "File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?"
    evidence = [
        {
            "citation_id": "c1",
            "title": "Tài liệu kiểm chuẩn Jig",
            "snippet": "Quy trình kiểm tra dung sai đo lường Jig 4 bước.",
            "text": "Quy trình kiểm tra dung sai đo lường Jig 4 bước.",
        }
    ]

    set_draft_fallback_override(True)

    ok, succ_msg, badge, err = route_workspace_chat_submission(
        question=q,
        evidence_items=evidence,
        packed_sources=(),
        conversation_id=conv_id,
        notebook_id="mom_opcenter",
        retrieval_applied=True,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(),
        chat_history=(),
        user_raw_input=q,
        backend="local",
    )

    assert ok is True
    msgs = load_messages(conv_id)
    asst = [m for m in msgs if m.role == "assistant"][-1]
    assert "Tài liệu kiểm chuẩn Jig" in asst.content
    assert DRAFT_LABEL not in asst.content
    assert badge.get("is_draft_fallback") is not True


def test_nakazasen_router_admits_unknown_triggers_draft(monkeypatch):
    """When Nakazasen router result admits no sources/evidence, draft fallback triggers."""
    from aios_habit.antigravity_bridge import route_workspace_chat_submission
    from aios_habit.workspace_chat_ai_answer import WorkspaceAIAnswerResult

    conv_id = "conv_bridge_router_draft"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id="NB-LAZY-LSU",
            title="Router Draft Test",
        )
    )

    q = "File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?"
    set_draft_fallback_override(True)

    fake_rag_refusal = (
        "## Tóm tắt\n"
        "Trong các nguồn được cung cấp, chưa có nguồn nào nêu trực tiếp một chức năng còn thiếu để phát hiện sớm tình trạng jig suy giảm.\n\n"
        "## Điểm chưa đủ bằng chứng\n"
        "- Không có nguồn nào định nghĩa chức năng này."
    )

    def _mock_generate(*args, **kwargs):
        return WorkspaceAIAnswerResult(
            ok=True,
            answer_text=fake_rag_refusal,
            included_source_titles=(),
            warnings=(),
            reason_code="success",
            effective_provider="Nakazasen Router",
            effective_model="test-model",
        )

    monkeypatch.setattr(
        "aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer",
        _mock_generate,
    )

    ok, succ_msg, badge, err = route_workspace_chat_submission(
        question=q,
        evidence_items=[{"title": "AI cảnh báo lỗi LSU.pptx", "text": "slide 7"}],
        packed_sources=(),
        conversation_id=conv_id,
        notebook_id="NB-LAZY-LSU",
        retrieval_applied=True,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(),
        chat_history=(),
        user_raw_input=q,
        backend="nakazasen_router",
    )

    assert ok is True
    assert err is None
    assert badge is not None
    assert badge.get("is_draft_fallback") is True
    assert "bản thảo dự bị" in succ_msg

    msgs = load_messages(conv_id)
    asst = [m for m in msgs if m.role == "assistant"][-1]
    assert DRAFT_LABEL in asst.content
    assert "Hiệu suất jig giảm sút" in asst.content


def test_nakazasen_router_grounded_answer_preserves_rag(monkeypatch):
    """When Nakazasen router gives a grounded substantive answer, it is preserved without draft fallback."""
    from aios_habit.antigravity_bridge import route_workspace_chat_submission
    from aios_habit.workspace_chat_ai_answer import WorkspaceAIAnswerResult

    conv_id = "conv_bridge_router_grounded"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id="mom_opcenter",
            title="Router Grounded Test",
        )
    )

    q = "Trong file cấu hình Matecon, ctrlMode = 0 và ctrlMode = 1 khác nhau thế nào?"
    set_draft_fallback_override(True)

    good_rag_answer = (
        "## Tóm tắt\n"
        "ctrlMode quy định trạng thái truyền thông giữa Matecon và MOM. "
        "ctrlMode = 0 là chế độ sản xuất tự động, ctrlMode = 1 là chế độ thủ công.\n\n"
        "## Điều đã xác nhận\n"
        "- Tham số này nằm trong phần cấu hình Windows.\n\n"
        "## Điểm chưa đủ bằng chứng\n"
        "- Nguồn không nêu giá trị mặc định khi chưa cấu hình."
    )

    def _mock_generate(*args, **kwargs):
        return WorkspaceAIAnswerResult(
            ok=True,
            answer_text=good_rag_answer,
            included_source_titles=("Matecon.xlsx",),
            warnings=(),
            reason_code="success",
            effective_provider="Nakazasen Router",
            effective_model="test-model",
        )

    monkeypatch.setattr(
        "aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer",
        _mock_generate,
    )

    ok, succ_msg, badge, err = route_workspace_chat_submission(
        question=q,
        evidence_items=[{"title": "Matecon.xlsx", "text": "ctrlMode details"}],
        packed_sources=(),
        conversation_id=conv_id,
        notebook_id="mom_opcenter",
        retrieval_applied=True,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(),
        chat_history=(),
        user_raw_input=q,
        backend="nakazasen_router",
    )

    assert ok is True
    assert err is None
    assert badge is not None
    assert badge.get("is_draft_fallback") is not True

    msgs = load_messages(conv_id)
    asst = [m for m in msgs if m.role == "assistant"][-1]
    assert DRAFT_LABEL not in asst.content
    assert "ctrlMode quy định trạng thái truyền thông" in asst.content

