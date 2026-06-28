import pytest
from aios_habit.owner_workflow_state import (
    WorkflowState,
    evaluate_owner_workflow_state,
    can_analyze,
    can_generate_ai_answer,
    can_create_full_bundle,
    build_owner_friendly_blocking_message
)

def test_empty_input_blocks_analysis():
    state = evaluate_owner_workflow_state("", 0)
    assert state == WorkflowState.START
    assert not can_analyze(state)
    assert build_owner_friendly_blocking_message(state, "analyze") == "Cần mô tả vấn đề trước. Chỉ cần 1-2 câu."

def test_issue_without_evidence_blocks_answer():
    state = evaluate_owner_workflow_state("Server down", 0)
    assert state == WorkflowState.ISSUE_ENTERED
    assert not can_generate_ai_answer(state)
    assert build_owner_friendly_blocking_message(state, "answer") == "Chưa có bằng chứng nên AIOS không trả lời như kết luận. Hãy thêm tài liệu/ảnh/log trước."
    assert build_owner_friendly_blocking_message(state, "analyze") == "Cần thêm ít nhất một tài liệu, ảnh, log, hoặc nội dung chat/email để AIOS có bằng chứng."

def test_evidence_without_issue_blocks_case_creation():
    state = evaluate_owner_workflow_state("", 1)
    assert state == WorkflowState.BLOCKED_MISSING_ISSUE
    assert not can_analyze(state)
    assert build_owner_friendly_blocking_message(state) == "Cần mô tả vấn đề trước. Chỉ cần 1–2 câu."

def test_local_only_blocks_cloud_direct_provider_path():
    state = evaluate_owner_workflow_state("Server down", 1, requested_cloud_action=True, is_local_only=True)
    assert state == WorkflowState.BLOCKED_UNSAFE_PRIVACY
    assert build_owner_friendly_blocking_message(state) == "Dữ liệu đang ở chế độ chỉ xử lý cục bộ. AIOS không tự gửi cloud."

def test_valid_issue_and_evidence_allows_analysis():
    state = evaluate_owner_workflow_state("Server down", 1)
    assert state == WorkflowState.READY_TO_ANALYZE
    assert can_analyze(state)

def test_analyzed_case_allows_map_actions():
    state = evaluate_owner_workflow_state("Server down", 1, has_analysis=True)
    assert state == WorkflowState.ANALYZED
    assert can_analyze(state)
    assert can_generate_ai_answer(state)
    assert can_create_full_bundle(state)

def test_full_bundle_blocked_missing_evidence():
    state = evaluate_owner_workflow_state("Server down", 0)
    assert state == WorkflowState.ISSUE_ENTERED
    assert not can_create_full_bundle(state)
    assert build_owner_friendly_blocking_message(state, "bundle") == "Chưa có bằng chứng để đóng gói."
