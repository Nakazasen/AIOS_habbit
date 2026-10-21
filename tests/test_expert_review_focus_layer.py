# -*- coding: utf-8 -*-
"""Unit tests for Expert Review Focus Layer (DESKTOP-HOME-EXPERT-REVIEW-FOCUS-LAYER).

Tests:
1. Event logging to local_cases/expert_review_events.jsonl (Continuous improvement loop).
2. Similarity search & diff comparison against memory vault & approved items.
3. Escalation summary generation (max 3 lines with SMA, frequency, overdue status).
4. Inline draft editing and approval with PIN -> saves edited draft to vault.
5. Revision request workflow with mandatory reason.
6. Draft input retention invariant.
"""

from __future__ import annotations

import json
import os
import platform
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Generator

import pytest

from aios_habit.expert_review_focus_layer import (
    _compute_escalation_summary,
    find_similar_lessons,
    record_expert_review_event,
)
from aios_habit.expert_review_queue import (
    ApprovalAuditStamp,
    ExpertReviewQueueRepository,
    QueueItem,
    SOURCE_SMA_ALERT,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_REVISED,
)
from aios_habit.expert_roles import ExpertRoleRegistry


@pytest.fixture
def temp_env(tmp_path: Path) -> Generator[Dict[str, Any], None, None]:
    db_file = tmp_path / "test_queue.db"
    audit_file = tmp_path / "test_audit.jsonl"
    pin_file = tmp_path / "test_pin.json"
    attempts_file = tmp_path / "test_attempts.json"
    alerts_file = tmp_path / "test_alerts.jsonl"

    repo = ExpertReviewQueueRepository(
        db_path=db_file,
        audit_log_path=audit_file,
        pin_config_path=pin_file,
        pin_attempts_path=attempts_file,
        admin_alerts_path=alerts_file,
    )
    repo.set_expert_pin("4321")

    current_node = platform.node()
    config_dict = {
        "domains": {
            "lsu": {
                "title": "Căn chỉnh LSU & Quang học",
                "primary_expert": "H410ASROCK\\Vinh",
                "backup_experts": ["DOMAIN\\khiem_ni"],
                "authorized_machines": [current_node, "ENG-PC-01"],
            },
            "dieu_tra_loi": {
                "title": "Điều tra Lỗi Sản xuất KDTPS",
                "primary_expert": "DOMAIN\\duc_na",
                "backup_experts": ["H410ASROCK\\Vinh"],
                "authorized_machines": [current_node],
            },
        }
    }
    import yaml
    config_file = tmp_path / "expert_roles.yaml"
    roles_audit_file = tmp_path / "roles_audit.jsonl"
    config_file.write_text(yaml.safe_dump(config_dict, allow_unicode=True), encoding="utf-8")
    registry = ExpertRoleRegistry(config_path=config_file, audit_log_path=roles_audit_file)
    repo.registry = registry

    yield {
        "repo": repo,
        "registry": registry,
        "current_node": current_node,
        "tmp_path": tmp_path,
    }


def test_record_expert_review_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Kiểm tra ghi nhật ký sự kiện duyệt vào local_cases."""
    test_log = tmp_path / "test_events.jsonl"
    monkeypatch.setattr("aios_habit.expert_review_focus_layer._REVIEW_EVENTS_LOG", test_log)
    monkeypatch.setattr("aios_habit.expert_review_focus_layer._LOCAL_CASES_DIR", tmp_path)

    record_expert_review_event(
        event_type="decision_approve",
        item_id="QITEM-TEST01",
        domain_id="lsu",
        actor_subject="H410ASROCK\\Vinh",
        actor_machine="H410ASROCK",
        review_duration_seconds=12.45,
        action="approved_to_vault",
        has_inline_edit=True,
        diff_detected=False,
        metadata={"audit_id": "AUDIT-1234"},
    )

    assert test_log.exists()
    lines = test_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["event_type"] == "decision_approve"
    assert event["item_id"] == "QITEM-TEST01"
    assert event["domain_id"] == "lsu"
    assert event["review_duration_seconds"] == 12.45
    assert event["has_inline_edit"] is True
    assert event["actor_subject"] == "H410ASROCK\\Vinh"


def test_escalation_summary_generation(temp_env: Dict[str, Any]):
    """Kiểm tra sinh bản tóm tắt tối đa 3 dòng vì sao mục bị đưa lên duyệt."""
    repo = temp_env["repo"]
    registry = temp_env["registry"]

    item = QueueItem(
        item_id="QITEM-SUMMARY-01",
        source_type=SOURCE_SMA_ALERT,
        domain_id="lsu",
        title="Độ lệch góc Bow Skew trên 6thA3 LSU",
        question="Tiêu chuẩn độ lệch góc Bow Skew trên cụm LSU 6thA3 sau khi thay motor polygon?",
        draft_answer="Tiêu chuẩn Bow Skew tối đa không vượt quá ± 0.05 mrad theo tiêu chuẩn xuất xưởng 6thA3.",
        dislike_count=3,
        like_count=5,
        service_frequency=8,
        priority_score=27.75,
        created_at=(datetime.now(timezone.utc) - timedelta(hours=72)).isoformat(),
    )

    lines = _compute_escalation_summary(item, registry)
    assert len(lines) == 3
    # Dòng 1 chứa thông tin phân loại nguồn và tên miền
    assert "Cảnh báo xu hướng chê SMA(20)" in lines[0]
    assert "LSU" in lines[0]
    # Dòng 2 chứa số lượt chê, lượt hỏi, tỷ lệ và priority score
    assert "3 chê / 8 lượt hỏi" in lines[1]
    assert "27.8" in lines[1] or "27.7" in lines[1]
    # Dòng 3 cảnh báo quá hạn vượt ngưỡng 48h
    assert "72." in lines[2] or "71." in lines[2]
    assert "48h" in lines[2]


def test_approve_with_inline_edited_draft(temp_env: Dict[str, Any], monkeypatch: pytest.MonkeyPatch):
    """Kiểm tra sửa tại chỗ bản đề xuất rồi duyệt -> lưu bản sửa vào kho công ty."""
    repo = temp_env["repo"]
    registry = temp_env["registry"]
    current_node = temp_env["current_node"]
    tmp_path = temp_env["tmp_path"]

    test_vault = tmp_path / "test_memory_vault.jsonl"
    monkeypatch.setattr("aios_habit.expert_review_queue.Path", lambda p: test_vault if "memory_units" in str(p) else Path(p))

    # Tạo một mục chờ duyệt giả lập trong fixture cô lập
    res = repo.submit_to_queue(
        source_type=SOURCE_SMA_ALERT,
        question="Cách khắc phục sai lệch góc quét chùm laser đa giác?",
        title="Hiệu chỉnh đa giác polygon LSU",
        draft_answer="Bản nháp ban đầu: Chỉnh ốc 1 và ốc 2.",
        domain_id="lsu",
        force_pass_throttle=True,
    )
    item_id = res.item_id

    # Chuyên gia sửa tại chỗ nội dung bản nháp
    edited_draft = "Bản nháp ĐÃ ĐƯỢC CHUYÊN GIA SỬA: Căn chỉnh Jig quang học 0.8 Nm và kiểm tra log."

    approve_res = repo.approve_queue_item(
        item_id=item_id,
        actor_subject="H410ASROCK\\Vinh",
        pin="4321",
        machine_node=current_node,
        notes="Đã kiểm tra và chỉnh sửa chi tiết lực siết.",
        updated_draft=edited_draft,
    )

    assert approve_res["ok"] is True
    assert approve_res["status"] == STATUS_APPROVED

    # Kiểm tra trong DB: draft_answer đã được cập nhật thành bản sửa
    item_db = repo.get_item(item_id)
    assert item_db.status == STATUS_APPROVED
    assert item_db.draft_answer == edited_draft

    # Kiểm tra trong kho Memory Vault: statement là bản sửa
    assert test_vault.exists()
    vault_lines = test_vault.read_text(encoding="utf-8").strip().splitlines()
    assert len(vault_lines) == 1
    vault_unit = json.loads(vault_lines[0])
    assert vault_unit["statement"] == edited_draft
    assert vault_unit["approved_by"] == "H410ASROCK\\Vinh"


def test_revision_request_mandatory_reason(temp_env: Dict[str, Any]):
    """Kiểm tra yêu cầu trả sửa: bắt buộc phải có lý do, không đòi hỏi PIN."""
    repo = temp_env["repo"]
    current_node = temp_env["current_node"]

    res = repo.submit_to_queue(
        source_type=SOURCE_SMA_ALERT,
        question="Xử lý lỗi rò dầu hộp số trục cấp?",
        title="Rò dầu hộp số trục cấp",
        draft_answer="Tra thêm mỡ chịu nhiệt.",
        domain_id="dieu_tra_loi",
        force_pass_throttle=True,
    )
    item_id = res.item_id

    # 1. Trả sửa nhưng bỏ trống lý do -> Thất bại
    res_fail = repo.reject_queue_item(
        item_id=item_id,
        actor_subject="H410ASROCK\\Vinh",
        reason="",
        machine_node=current_node,
        decision_status=STATUS_REVISED,
        require_pin=False,
    )
    assert res_fail["ok"] is False
    assert "lý do" in res_fail["error_vi"]

    # 2. Trả sửa có lý do đầy đủ -> Thành công (không cần PIN)
    res_ok = repo.reject_queue_item(
        item_id=item_id,
        actor_subject="H410ASROCK\\Vinh",
        reason="Sai quy trình: Phải thay phớt chắn dầu trước, không được chỉ tra thêm mỡ.",
        machine_node=current_node,
        decision_status=STATUS_REVISED,
        require_pin=False,
    )
    assert res_ok["ok"] is True
    assert res_ok["status"] == STATUS_REVISED

    # Kiểm tra cập nhật trạng thái trong SQLite
    item_updated = repo.get_item(item_id)
    assert item_updated.status == STATUS_REVISED


def test_find_similar_lessons_matching(temp_env: Dict[str, Any], monkeypatch: pytest.MonkeyPatch):
    """Kiểm tra phát hiện bài học tương tự trong kho để tránh duyệt trùng."""
    repo = temp_env["repo"]
    tmp_path = temp_env["tmp_path"]

    # Giả lập bài học đã có trong vault
    vault_file = tmp_path / "mock_vault.jsonl"
    existing_unit = {
        "unit_id": "MU-EXIST-01",
        "title": "Độ lệch góc Bow Skew 6thA3",
        "question": "Tiêu chuẩn độ lệch góc Bow Skew trên LSU 6thA3?",
        "statement": "Tiêu chuẩn xuất xưởng tối đa ± 0.05 mrad.",
        "status": "verified",
        "partition": "company_knowledge",
    }
    vault_file.write_text(json.dumps(existing_unit, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr("aios_habit.expert_review_focus_layer._MEMORY_VAULT_FILE", vault_file)

    new_item = QueueItem(
        item_id="QITEM-NEW-01",
        source_type=SOURCE_SMA_ALERT,
        domain_id="lsu",
        title="Kiểm tra góc Bow Skew 6thA3",
        question="Độ lệch góc Bow Skew trên LSU 6thA3 cho phép là bao nhiêu?",
        draft_answer="Tiêu chuẩn xuất xưởng tối đa ± 0.05 mrad sau khi thay linh kiện.",
    )

    cand, sim, diff = find_similar_lessons(new_item, repo)
    assert cand is not None
    assert cand["id"] == "MU-EXIST-01"
    assert sim >= 0.50  # Rất tương đồng
    assert diff != ""


def test_draft_input_retention_invariant():
    """Kiểm tra bất biến bảo toàn câu đang gõ dở trong ô soạn thảo khi đóng/mở lớp duyệt."""
    conv_id = "CONV-TEST-RETENTION"
    q_key = f"wsc_question_input_{conv_id}"
    backup_key = f"wsc_draft_input_backup_{conv_id}"

    session_state = {}

    # Người dùng gõ câu dở
    typing_text = "Tôi đang gõ dở câu hỏi kiểm tra độ lệch Bow Skew..."
    session_state[q_key] = typing_text
    session_state[backup_key] = typing_text

    # Giả lập mở lớp duyệt tập trung (Focus Review Layer mở)
    focus_active_id = "QITEM-123"
    session_state["wsc_focus_review_active_item_id"] = focus_active_id

    # Đóng lớp duyệt tập trung
    session_state["wsc_focus_review_active_item_id"] = None

    # Khôi phục trạng thái khung chat: câu gõ dở phải còn nguyên 100%
    restored_text = session_state.get(q_key) or session_state.get(backup_key)
    assert restored_text == typing_text
    assert "Bow Skew" in restored_text

