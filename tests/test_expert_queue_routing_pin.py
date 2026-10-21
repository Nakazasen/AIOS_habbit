"""Comprehensive unit and integration test suite for DESKTOP-SELF-LEARN-EXPERT-QUEUE-ROUTING-PIN.

Tests:
1. Expert role registry (config/expert_roles.yaml, domain resolution, admin audit logging).
2. Windows identity provider integration & subject normalization (DOMAIN\\user vs user).
3. Anti-congestion throttling valve (SMA(20) alert, draft promotion, 1-off noise filtering).
4. Priority scoring (dislike count x service frequency, queue sorting).
5. Aging escalation (48h reminder, 7-day escalation to backup expert & admin alerts).
6. Public queue health metrics (pending counts, oldest item age, overdue rate).
7. Protected approval operation:
   - Salted SHA-256 PIN authentication.
   - Lockout after 5 failed attempts.
   - Machine name binding verification (authorized vs rogue hostname).
   - Full audit stamp logging (account + machine + ISO timestamp + destination).
   - Writing to corporate memory vault.
8. Rejection workflow with mandatory reason.
9. Non-blocking guarantee: ordinary user Q&A unaffected by queue or absent experts.
"""

from __future__ import annotations

import json
import os
import platform
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from aios_habit.expert_identity_windows import WindowsOSIdentityProvider
from aios_habit.expert_review_queue import (
    AGING_ESCALATION_SECONDS,
    AGING_REMINDER_SECONDS,
    DEFAULT_PIN_CONFIG,
    LOCK_DURATION_SECONDS,
    MAX_FAILED_ATTEMPTS,
    SOURCE_DRAFT_PROMOTION,
    SOURCE_SMA_ALERT,
    SOURCE_TIER5_INQUIRY,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    ExpertReviewQueueRepository,
    compute_priority_score,
)
from aios_habit.expert_roles import (
    DomainRoleConfig,
    ExpertRoleRegistry,
    extract_username,
    matches_subject,
    normalize_subject,
)


@pytest.fixture
def temp_workspace(tmp_path: Path):
    """Provides isolated configuration, db, and audit paths for each test."""
    config_file = tmp_path / "expert_roles.yaml"
    roles_audit_file = tmp_path / "expert_role_audit.jsonl"
    db_file = tmp_path / "test_queue.db"
    approval_audit_file = tmp_path / "approval_audit.jsonl"
    admin_alerts_file = tmp_path / "admin_alerts.jsonl"
    pin_cfg_file = tmp_path / "pin_cfg.json"
    pin_att_file = tmp_path / "pin_attempts.json"

    # Pre-seed YAML
    initial_yaml = {
        "domains": {
            "lsu": {
                "title": "Miền Kiểm tra & Căn chỉnh LSU",
                "primary_expert": "DOMAIN\\khiem_ni",
                "backup_experts": ["DOMAIN\\thao_nt"],
                "matching_rules": {
                    "collections": ["lsu_master", "lsu_tuning"],
                    "keywords": ["lsu", "laser", "polygon", "aperture"],
                },
                "authorized_machines": ["ENG-PC-01", "ENG-PC-02"],
            },
            "dieu_tra_loi": {
                "title": "Miền Phân tích & Điều tra Lỗi Sản xuất",
                "primary_expert": "DOMAIN\\duc_na",
                "backup_experts": ["DOMAIN\\khiem_ni"],
                "matching_rules": {
                    "collections": ["dieutraloi", "error_codes"],
                    "keywords": ["nguyen nhan", "bien ban", "4m", "doi sach"],
                },
                "authorized_machines": ["*"],
            },
            "mom_opcenter": {
                "title": "Miền Hệ thống Quản lý Sản xuất MOM/Opcenter",
                "primary_expert": "DOMAIN\\tuan_pa",
                "backup_experts": ["DOMAIN\\admin_local"],
                "matching_rules": {
                    "collections": ["mom_wms", "work_orders"],
                    "keywords": ["wo", "lenh san xuat", "material", "opcenter"],
                },
                "authorized_machines": ["*"],
            },
            "general_fallback": {
                "title": "Miền Tri thức Chung / Tổng hợp",
                "primary_expert": "DOMAIN\\admin_local",
                "backup_experts": [],
                "matching_rules": {
                    "collections": ["*"],
                    "keywords": ["*"],
                },
                "authorized_machines": ["*"],
            },
        }
    }
    config_file.write_text(yaml.safe_dump(initial_yaml, allow_unicode=True), encoding="utf-8")

    registry = ExpertRoleRegistry(
        config_path=config_file,
        audit_log_path=roles_audit_file,
    )

    repo = ExpertReviewQueueRepository(
        db_path=db_file,
        registry=registry,
        audit_log_path=approval_audit_file,
        admin_alerts_path=admin_alerts_file,
        pin_config_path=pin_cfg_file,
        pin_attempts_path=pin_att_file,
    )

    return {
        "tmp_path": tmp_path,
        "config_file": config_file,
        "roles_audit_file": roles_audit_file,
        "registry": registry,
        "repo": repo,
        "approval_audit_file": approval_audit_file,
        "admin_alerts_file": admin_alerts_file,
    }


# =============================================================================
# TEST 1: EXPERT ROLE REGISTRY & SUBJECT MATCHING
# =============================================================================

def test_expert_role_registry_loading_and_resolution(temp_workspace):
    registry: ExpertRoleRegistry = temp_workspace["registry"]
    domains = registry.list_domains()
    assert len(domains) == 4

    lsu = registry.get_domain("lsu")
    assert lsu is not None
    assert lsu.title == "Miền Kiểm tra & Căn chỉnh LSU"
    assert lsu.primary_expert == "DOMAIN\\khiem_ni"
    assert "DOMAIN\\thao_nt" in lsu.backup_experts

    # Resolution by collection
    assert registry.resolve_domain(collection_id="lsu_master") == "lsu"
    assert registry.resolve_domain(collection_id="dieutraloi") == "dieu_tra_loi"
    assert registry.resolve_domain(collection_id="mom_wms") == "mom_opcenter"

    # Resolution by keywords in question
    assert registry.resolve_domain(question="Cách căn chỉnh laser LSU bị lệch?") == "lsu"
    assert registry.resolve_domain(question="Biên bản điều tra nguyên nhân lỗi 4M") == "dieu_tra_loi"
    assert registry.resolve_domain(question="Lệnh sản xuất WO-20261020 trên opcenter") == "mom_opcenter"

    # Fallback resolution
    assert registry.resolve_domain(question="Hôm nay thời tiết thế nào?") == "general_fallback"


def test_subject_matching_variations():
    # Case-insensitive
    assert matches_subject("domain\\khiem_ni", "DOMAIN\\KHIEM_NI")
    # Cross domain / local username matching
    assert matches_subject("khiem_ni", "DOMAIN\\khiem_ni")
    assert matches_subject("DOMAIN\\khiem_ni", "khiem_ni")
    assert matches_subject("PC123\\khiem_ni", "DOMAIN\\khiem_ni")
    # Non-match
    assert not matches_subject("thao_nt", "DOMAIN\\khiem_ni")
    assert not matches_subject("", "DOMAIN\\khiem_ni")


def test_expert_role_registry_admin_audit_logging(temp_workspace):
    registry: ExpertRoleRegistry = temp_workspace["registry"]
    audit_file: Path = temp_workspace["roles_audit_file"]

    # Update role
    updated = registry.update_domain_roles(
        "lsu",
        primary_expert="DOMAIN\\new_expert",
        backup_experts=["DOMAIN\\sub_1", "DOMAIN\\sub_2"],
        authorized_machines=["MACHINE-A"],
        actor="ADMIN_SUPERVISOR",
        reason="Điều chuyển nhân sự ca 1",
    )
    assert updated.primary_expert == "DOMAIN\\new_expert"
    assert updated.authorized_machines == ["MACHINE-A"]

    # Check persistence in YAML
    cfg_file: Path = temp_workspace["config_file"]
    reloaded = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    assert reloaded["domains"]["lsu"]["primary_expert"] == "DOMAIN\\new_expert"

    # Check audit log written
    assert audit_file.exists()
    lines = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").strip().splitlines() if line]
    assert len(lines) >= 1
    last_log = lines[-1]
    assert last_log["actor"] == "ADMIN_SUPERVISOR"
    assert last_log["domain_id"] == "lsu"
    assert last_log["reason"] == "Điều chuyển nhân sự ca 1"
    assert last_log["new_data"]["primary_expert"] == "DOMAIN\\new_expert"


# =============================================================================
# TEST 2: WINDOWS IDENTITY PROVIDER INTEGRATION
# =============================================================================

def test_windows_os_identity_provider_integration():
    provider = WindowsOSIdentityProvider()
    principal = provider.resolve_current_principal()
    assert principal is not None
    assert len(principal.subject) > 0
    assert principal.provider_name == "windows_os"
    assert "node" in principal.metadata


# =============================================================================
# TEST 3: THROTTLING VALVE (VAN TIẾT LƯU CHỐNG TẮC NGHẼN)
# =============================================================================

def test_throttling_valve_filtering(temp_workspace):
    repo: ExpertReviewQueueRepository = temp_workspace["repo"]

    # 1. 1-off noise: 1 dislike, 5 samples (20% ratio) -> REJECTED
    res1 = repo.submit_to_queue(
        SOURCE_SMA_ALERT,
        "Đèn báo laser nhấp nháy?",
        dislike_count=1,
        sample_count=5,
    )
    assert not res1.accepted
    assert "Chưa qua van tiết lưu" in res1.reason

    # 2. 2 dislikes without specific reason category -> REJECTED
    res2 = repo.submit_to_queue(
        SOURCE_SMA_ALERT,
        "Đèn báo laser nhấp nháy?",
        dislike_count=2,
        sample_count=10,
        reason_category="",
    )
    assert not res2.accepted

    # 3. SMA alert: Dislike >= 3 and ratio >= 30% -> ACCEPTED
    res3 = repo.submit_to_queue(
        SOURCE_SMA_ALERT,
        "Đèn báo laser nhấp nháy trên Sirius LSU?",
        dislike_count=3,
        sample_count=10,
        collection_id="lsu_master",
    )
    assert res3.accepted
    assert res3.item_id is not None

    # 4. SMA alert: Dislike >= 2 with explicit category ('sai') -> ACCEPTED
    res4 = repo.submit_to_queue(
        SOURCE_SMA_ALERT,
        "Quy trình căn chỉnh 4M bị ngược bước?",
        dislike_count=2,
        sample_count=8,
        reason_category="sai",
        collection_id="dieutraloi",
    )
    assert res4.accepted

    # 5. Draft promotion: Under-qualified (< 3 invocations) -> REJECTED
    res5 = repo.submit_to_queue(
        SOURCE_DRAFT_PROMOTION,
        "Kỹ năng xử lý lỗi E-999",
        invocation_count=2,
        like_count=2,
        dislike_count=0,
    )
    assert not res5.accepted

    # 6. Draft promotion: Qualified (> 3 invocations, high like ratio) -> ACCEPTED
    res6 = repo.submit_to_queue(
        SOURCE_DRAFT_PROMOTION,
        "Kỹ năng xử lý lỗi E-999",
        invocation_count=4,
        like_count=3,
        dislike_count=0,
        domain_id="mom_opcenter",
    )
    assert res6.accepted

    # 7. Tier 5 Inquiry: Always accepted (user explicit escalation)
    res7 = repo.submit_to_queue(
        SOURCE_TIER5_INQUIRY,
        "Tôi cần chuyên gia giải thích thông số Bow Skew",
        domain_id="lsu",
    )
    assert res7.accepted


# =============================================================================
# TEST 4: PRIORITY SCORING & ORDERING
# =============================================================================

def test_priority_scoring_and_ordering(temp_workspace):
    repo: ExpertReviewQueueRepository = temp_workspace["repo"]

    # Item A: 3 dislikes, freq 1 -> score = (3 * 1) + 3.0 = 6.0
    res_a = repo.submit_to_queue(
        SOURCE_SMA_ALERT,
        "Vấn đề A",
        dislike_count=3,
        service_frequency=1,
        sample_count=10,
        domain_id="lsu",
    )
    # Item B: 8 dislikes, freq 5 -> score = (8 * 5) + 8.0 = 48.0 (HOT ISSUE)
    res_b = repo.submit_to_queue(
        SOURCE_SMA_ALERT,
        "Vấn đề B cực kỳ cấp bách",
        dislike_count=8,
        service_frequency=5,
        sample_count=10,
        domain_id="lsu",
    )
    # Item C: 4 dislikes, freq 2 -> score = (4 * 2) + 4.0 = 12.0
    res_c = repo.submit_to_queue(
        SOURCE_SMA_ALERT,
        "Vấn đề C vừa phải",
        dislike_count=4,
        service_frequency=2,
        sample_count=10,
        domain_id="lsu",
    )

    pending = repo.list_pending_items(domain_id="lsu")
    assert len(pending) == 3
    # Top item must be B, followed by C, then A
    assert pending[0].item_id == res_b.item_id
    assert pending[0].priority_score >= pending[1].priority_score
    assert pending[1].item_id == res_c.item_id
    assert pending[2].item_id == res_a.item_id


# =============================================================================
# TEST 5: AGING ESCALATION (48H REMINDER & 7-DAY BACKUP ESCALATION)
# =============================================================================

def test_aging_escalation_workflow(temp_workspace):
    repo: ExpertReviewQueueRepository = temp_workspace["repo"]
    alerts_file: Path = temp_workspace["admin_alerts_file"]

    # Submit an item into LSU domain (Primary: khiem_ni, Backup: thao_nt)
    res = repo.submit_to_queue(
        SOURCE_SMA_ALERT,
        "Lỗi lệch tâm thấu kính F-Theta",
        dislike_count=5,
        sample_count=10,
        domain_id="lsu",
    )
    item_id = res.item_id

    item = repo.get_item(item_id)
    assert item.escalation_level == 0
    assert item.assigned_expert == "DOMAIN\\khiem_ni"

    now_base = datetime.fromisoformat(item.created_at)
    if now_base.tzinfo is None:
        now_base = now_base.replace(tzinfo=timezone.utc)

    # 1. At 24 hours: No escalation
    t_24h = now_base + timedelta(hours=24)
    events_24h = repo.check_and_apply_escalations(reference_time=t_24h)
    assert len(events_24h) == 0
    assert repo.get_item(item_id).escalation_level == 0

    # 2. At 49 hours (> 48h): Trigger level 1 (In-app reminder)
    t_49h = now_base + timedelta(hours=49)
    events_49h = repo.check_and_apply_escalations(reference_time=t_49h)
    assert len(events_49h) == 1
    assert events_49h[0]["action"] == "reminder_48h"
    assert events_49h[0]["level"] == 1

    item_after_48h = repo.get_item(item_id)
    assert item_after_48h.escalation_level == 1
    assert item_after_48h.assigned_expert == "DOMAIN\\khiem_ni"  # Still primary

    # 3. At 8 days (> 7 days): Trigger level 2 (Escalate to backup + Admin alert)
    t_8d = now_base + timedelta(days=8)
    events_8d = repo.check_and_apply_escalations(reference_time=t_8d)
    assert len(events_8d) == 1
    assert events_8d[0]["action"] == "escalate_to_backup"
    assert events_8d[0]["level"] == 2
    assert events_8d[0]["escalated_to"] == "DOMAIN\\thao_nt"

    item_after_7d = repo.get_item(item_id)
    assert item_after_7d.escalation_level == 2
    assert item_after_7d.escalated_to == "DOMAIN\\thao_nt"
    assert item_after_7d.admin_alerted == 1

    # Verify admin alert JSONL was written
    assert alerts_file.exists()
    alerts = [json.loads(line) for line in alerts_file.read_text(encoding="utf-8").strip().splitlines() if line]
    assert len(alerts) >= 1
    assert alerts[-1]["escalated_to"] == "DOMAIN\\thao_nt"
    assert alerts[-1]["original_expert"] == "DOMAIN\\khiem_ni"


# =============================================================================
# TEST 6: PUBLIC QUEUE HEALTH METRICS
# =============================================================================

def test_queue_health_metrics(temp_workspace):
    repo: ExpertReviewQueueRepository = temp_workspace["repo"]

    # Seed 3 items with different ages
    r1 = repo.submit_to_queue(SOURCE_SMA_ALERT, "Item 1", dislike_count=3, sample_count=10, domain_id="lsu")
    r2 = repo.submit_to_queue(SOURCE_SMA_ALERT, "Item 2", dislike_count=4, sample_count=10, domain_id="dieu_tra_loi")
    r3 = repo.submit_to_queue(SOURCE_SMA_ALERT, "Item 3", dislike_count=5, sample_count=10, domain_id="lsu")

    # Fast forward item 1 to 50 hours ago
    now = datetime.now(timezone.utc)
    old_time = (now - timedelta(hours=50)).isoformat()
    with repo._connection() as conn:
        conn.execute("UPDATE queue_items SET created_at = ? WHERE item_id = ?", (old_time, r1.item_id))

    metrics = repo.get_queue_health_metrics(reference_time=now)
    assert metrics.total_pending == 3
    assert metrics.pending_by_domain["lsu"] == 2
    assert metrics.pending_by_domain["dieu_tra_loi"] == 1
    assert metrics.oldest_item_id == r1.item_id
    assert metrics.oldest_item_age_hours >= 49.0
    assert metrics.overdue_48h_count == 1
    assert metrics.overdue_rate == pytest.approx(1 / 3, 0.01)


# =============================================================================
# TEST 7: PROTECTED APPROVAL OPERATION & SECURITY CONTROLS
# =============================================================================

def test_pin_setup_and_security(temp_workspace):
    repo: ExpertReviewQueueRepository = temp_workspace["repo"]

    # PIN must be 4-6 digits
    assert not repo.set_expert_pin("12")["ok"]
    assert not repo.set_expert_pin("abcdef")["ok"]
    assert not repo.set_expert_pin("1234567")["ok"]

    set_res = repo.set_expert_pin("5678")
    assert set_res["ok"]

    # Correct PIN verify
    assert repo.verify_expert_pin("5678")["ok"]

    # Wrong PIN verify
    wrong = repo.verify_expert_pin("0000")
    assert not wrong["ok"]
    assert "Mã PIN chưa đúng" in wrong["error_vi"]


def test_pin_lockout_after_5_failed_attempts(temp_workspace):
    repo: ExpertReviewQueueRepository = temp_workspace["repo"]
    repo.set_expert_pin("1234")

    # Fail 4 times -> still not locked
    for i in range(4):
        res = repo.verify_expert_pin("9999")
        assert not res["ok"]
        assert not repo.is_pin_locked()

    # 5th failure -> LOCKED
    res5 = repo.verify_expert_pin("9999")
    assert not res5["ok"]
    assert repo.is_pin_locked()
    assert "tạm khóa" in res5["error_vi"]

    # 6th attempt while locked -> blocked immediately without checking
    res6 = repo.verify_expert_pin("1234")
    assert not res6["ok"]
    assert "bị khóa tạm" in res6["error_vi"]


def test_machine_binding_and_authority_check(temp_workspace):
    repo: ExpertReviewQueueRepository = temp_workspace["repo"]
    repo.set_expert_pin("1234")

    # In our temp config:
    # LSU authorized_machines: ["ENG-PC-01", "ENG-PC-02"]
    # LSU primary_expert: "DOMAIN\\khiem_ni"

    res = repo.submit_to_queue(
        SOURCE_SMA_ALERT,
        "Sirius LSU aperture misalignment",
        dislike_count=4,
        sample_count=10,
        domain_id="lsu",
    )
    item_id = res.item_id

    # 1. Intruder account (not an expert of LSU) -> DENIED
    denied_actor = repo.approve_queue_item(
        item_id,
        actor_subject="DOMAIN\\intruder_user",
        pin="1234",
        machine_node="ENG-PC-01",
    )
    assert not denied_actor["ok"]
    assert "không thuộc danh sách chuyên gia" in denied_actor["error_vi"]

    # 2. Legitimate expert on unauthorized machine -> DENIED
    denied_mach = repo.approve_queue_item(
        item_id,
        actor_subject="DOMAIN\\khiem_ni",
        pin="1234",
        machine_node="ROGUE-HOME-PC",
    )
    assert not denied_mach["ok"]
    assert "không được cấp phép" in denied_mach["error_vi"]

    # 3. Legitimate expert on authorized machine with wrong PIN -> DENIED
    denied_pin = repo.approve_queue_item(
        item_id,
        actor_subject="DOMAIN\\khiem_ni",
        pin="9999",
        machine_node="ENG-PC-01",
    )
    assert not denied_pin["ok"]
    assert "Mã PIN chưa đúng" in denied_pin["error_vi"]

    # 4. Legitimate expert on authorized machine with correct PIN -> APPROVED!
    approved = repo.approve_queue_item(
        item_id,
        actor_subject="DOMAIN\\khiem_ni",
        pin="1234",
        machine_node="ENG-PC-01",
        notes="Đã hiệu chỉnh và chuẩn hóa quy trình.",
    )
    assert approved["ok"]
    assert approved["status"] == STATUS_APPROVED

    # Check audit stamp
    stamp = approved["audit_stamp"]
    assert stamp["actor_subject"] == "DOMAIN\\khiem_ni"
    assert stamp["actor_machine"] == "ENG-PC-01"
    assert "lsu:primary_expert" in stamp["actor_role"]
    assert stamp["destination"] == "company_knowledge"

    # Verify audit log JSONL
    audit_log_file: Path = temp_workspace["approval_audit_file"]
    assert audit_log_file.exists()
    logs = [json.loads(line) for line in audit_log_file.read_text(encoding="utf-8").strip().splitlines() if line]
    assert len(logs) == 1
    assert logs[0]["audit_id"] == stamp["audit_id"]

    # Item in DB is now approved
    assert repo.get_item(item_id).status == STATUS_APPROVED


def test_rejection_workflow(temp_workspace):
    repo: ExpertReviewQueueRepository = temp_workspace["repo"]
    repo.set_expert_pin("1234")

    res = repo.submit_to_queue(
        SOURCE_SMA_ALERT,
        "Yêu cầu không chính xác về dung sai",
        dislike_count=4,
        sample_count=10,
        domain_id="mom_opcenter",
    )
    item_id = res.item_id

    # Rejection without reason -> FAIL
    rej_no_reason = repo.reject_queue_item(
        item_id,
        actor_subject="DOMAIN\\tuan_pa",
        pin="1234",
        reason="",
    )
    assert not rej_no_reason["ok"]

    # Valid rejection
    rej_ok = repo.reject_queue_item(
        item_id,
        actor_subject="DOMAIN\\tuan_pa",
        pin="1234",
        reason="Dung sai này trái với tiêu chuẩn BOM hiện hành.",
    )
    assert rej_ok["ok"]
    assert rej_ok["status"] == STATUS_REJECTED
    assert repo.get_item(item_id).status == STATUS_REJECTED


# =============================================================================
# TEST 8: NON-BLOCKING INVARIANT
# =============================================================================

def test_non_blocking_invariant(temp_workspace):
    """Absence of experts or populated queue must never block system Q&A."""
    repo: ExpertReviewQueueRepository = temp_workspace["repo"]

    # Put multiple high-priority items in queue
    for i in range(5):
        repo.submit_to_queue(
            SOURCE_SMA_ALERT,
            f"Tồn đọng {i}",
            dislike_count=5,
            sample_count=10,
            domain_id="lsu",
        )

    # Health check is non-blocking and queries fast (< 50ms)
    t0 = time.perf_counter()
    metrics = repo.get_queue_health_metrics()
    dt_ms = (time.perf_counter() - t0) * 1000.0
    assert metrics.total_pending == 5
    assert dt_ms < 50.0  # Ultra-fast SQLite query
