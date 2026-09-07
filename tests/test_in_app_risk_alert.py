from __future__ import annotations

import sqlite3
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aios_habit.in_app_risk_alert import (
    AlertPolicy,
    InAppRiskAlert,
    acknowledge_alert,
    dismiss_alert,
    enable_in_app_alert_policy,
    ensure_alert_tables,
    evaluate_alerts_for_display,
    get_alert_response_history,
    get_in_app_alert_policy,
    grant_role_permission,
    is_kill_switch_active,
    render_in_app_risk_alerts,
    set_kill_switch,
    snooze_alert,
)
from aios_habit.production_prediction.models import (
    DataGateReport,
    DataGateStatus,
    LsuDatasetSnapshot,
)
from aios_habit.production_prediction.repository import ProductionPredictionRepository
from aios_habit.production_prediction.shadow import (
    ShadowRiskAssessment,
    save_shadow_risk_assessment,
)


@pytest.fixture
def test_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "test_prediction.sqlite"
    repo = ProductionPredictionRepository(db_file)
    ensure_alert_tables(db_file)
    # Grant role to test_admin explicitly
    grant_role_permission(
        db_file,
        actor_id="test_admin",
        role="system_owner",
        scope="workspace_chat",
    )
    # By default, enable policy with test_admin for happy-path testing
    default_policy = AlertPolicy(
        is_enabled=True,
        approved_by="test_admin",
        allowed_roles=["system_owner", "quality_manager", "admin", "local_admin", "qc_operator"],
        max_alert_age_days=7,
    )
    enable_in_app_alert_policy(db_file, default_policy, actor="test_admin", actor_role="system_owner")
    return db_file


def _seed_snapshot_and_assessment(
    db_path: Path,
    *,
    snapshot_id: str = "SNAP_001",
    risk_level: str = "HIGH",
    unit_serial: str = "UNIT_LSU_999",
    gate_status: DataGateStatus = DataGateStatus.PASS,
    future_leak_count: int = 0,
    as_of_time: str | None = None,
    future_leakage_detected: bool = False,
) -> tuple[str, str]:
    repo = ProductionPredictionRepository(db_path)
    now_iso = as_of_time or datetime.now(timezone.utc).isoformat()
    content_digest = "a" * 64

    snap = LsuDatasetSnapshot(
        snapshot_id=snapshot_id,
        created_at=datetime.now(timezone.utc),
        content_digest=content_digest,
        source_files={"file": "sample.csv"},
        component_measurements=[],
        unit_links=[],
        jig_outcomes=[],
    )
    gate_rep = DataGateReport(
        rubric_version="lsu_iris_gate_v1",
        source_digest=snap.content_digest,
        status=gate_status,
        total_rows=10,
        join_coverage_percent=100.0,
        conflicting_primary_keys_count=0,
        future_leak_count=future_leak_count,
        time_parse_valid_percent=100.0,
        unit_recognition_percent=100.0,
        ok_count=8,
        ng_count=2,
        unknown_count=0,
    )

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO lsu_snapshots (snapshot_id, created_at, content_digest, source_files_json)
            VALUES (?, ?, ?, '{}')
            """,
            (snap.snapshot_id, snap.created_at.isoformat(), snap.content_digest),
        )
        report_id = f"dgr_{snapshot_id}"
        conn.execute(
            """
            INSERT OR REPLACE INTO data_gate_reports (
                report_id, snapshot_id, status, rubric_version, source_digest,
                total_rows, join_coverage_percent, conflicting_primary_keys_count,
                future_leak_count, ok_count, ng_count, unknown_count,
                action_items_json, guidance, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', '', ?)
            """,
            (
                report_id,
                snap.snapshot_id,
                gate_rep.status.value,
                gate_rep.rubric_version,
                gate_rep.source_digest,
                gate_rep.total_rows,
                gate_rep.join_coverage_percent,
                gate_rep.conflicting_primary_keys_count,
                gate_rep.future_leak_count,
                gate_rep.ok_count,
                gate_rep.ng_count,
                gate_rep.unknown_count,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    idem_key = f"IDEM_{unit_serial}_{snapshot_id}"
    assessment = ShadowRiskAssessment(
        idempotency_key=idem_key,
        snapshot_id=snap.snapshot_id,
        unit_serial=unit_serial,
        as_of_time=now_iso,
        risk_level=risk_level,
        factors=[{"component_lot_id": "LOT_01", "metric_name": "BOW_VALUE", "z_score": 3.4}],
        reason="BOW_VALUE",
        link_status="pending_case_link",
        future_leakage_detected=future_leakage_detected,
    )
    save_shadow_risk_assessment(repo, assessment)
    return snap.snapshot_id, idem_key


# --- PROBE 1: Fail-Open Gate Verification ---

def test_probe1_gate_suppresses_blocked_data(test_db: Path):
    """Cổng cảnh báo phải chặn dữ liệu có trạng thái BLOCKED_DATA hoặc FAIL_TECHNICAL."""
    _seed_snapshot_and_assessment(
        test_db,
        snapshot_id="SNAP_BLOCKED",
        risk_level="HIGH",
        unit_serial="UNIT_BLOCKED",
        gate_status=DataGateStatus.BLOCKED_DATA,
    )
    alerts, kill_sw, msg = evaluate_alerts_for_display(test_db, actor_role="qc_operator")
    assert len(alerts) == 0, "Dữ liệu BLOCKED_DATA tuyệt đối không được sinh cảnh báo nguy cơ!"


def test_probe1_gate_suppresses_future_leakage_on_gate(test_db: Path):
    """Cổng cảnh báo phải chặn nếu phát hiện có rò rỉ tương lai trên data gate report (future_leak_count > 0)."""
    _seed_snapshot_and_assessment(
        test_db,
        snapshot_id="SNAP_LEAK_GATE",
        risk_level="HIGH",
        unit_serial="UNIT_LEAK_GATE",
        gate_status=DataGateStatus.PASS,
        future_leak_count=3,
    )
    alerts, kill_sw, msg = evaluate_alerts_for_display(test_db, actor_role="qc_operator")
    assert len(alerts) == 0, "Dữ liệu có rò rỉ tương lai trên gate report tuyệt đối không được sinh cảnh báo!"


def test_probe1_gate_suppresses_future_leakage_on_assessment_itself(test_db: Path):
    """Cổng cảnh báo phải chặn nếu bản thân shadow assessment bị gắn cờ future_leakage_detected = True dù gate PASS."""
    _seed_snapshot_and_assessment(
        test_db,
        snapshot_id="SNAP_LEAK_SRA",
        risk_level="HIGH",
        unit_serial="UNIT_LEAK_SRA",
        gate_status=DataGateStatus.PASS,
        future_leak_count=0,
        future_leakage_detected=True,
    )
    alerts, kill_sw, msg = evaluate_alerts_for_display(test_db, actor_role="qc_operator")
    assert len(alerts) == 0, "Đánh giá có future_leakage_detected=True tuyệt đối không được sinh cảnh báo nguy cơ!"


def test_probe1_gate_suppresses_expired_alerts(test_db: Path):
    """Cổng cảnh báo phải loại trừ các bản ghi đã quá hạn TTL (ví dụ từ năm 2020)."""
    old_time_2020 = "2020-05-01T12:00:00+00:00"
    _seed_snapshot_and_assessment(
        test_db,
        snapshot_id="SNAP_2020",
        risk_level="HIGH",
        unit_serial="UNIT_2020",
        gate_status=DataGateStatus.PASS,
        as_of_time=old_time_2020,
    )
    current_time_2026 = "2026-09-06T12:00:00+00:00"
    alerts, kill_sw, msg = evaluate_alerts_for_display(test_db, current_time_iso=current_time_2026, actor_role="qc_operator")
    assert len(alerts) == 0, "Bản ghi từ năm 2020 đã hết hạn TTL (max 7 ngày) và phải bị chặn hoàn toàn!"


def test_probe1_gate_suppresses_when_policy_disabled(test_db: Path):
    """Nếu chính sách cảnh báo chưa được phê duyệt hoặc đang tắt, không có cảnh báo nào hiển thị."""
    _seed_snapshot_and_assessment(
        test_db,
        snapshot_id="SNAP_VALID",
        risk_level="HIGH",
        unit_serial="UNIT_VALID",
        gate_status=DataGateStatus.PASS,
    )
    disabled_policy = AlertPolicy(is_enabled=False, approved_by="test_admin")
    enable_in_app_alert_policy(test_db, disabled_policy, actor="test_admin", actor_role="system_owner")

    alerts, kill_sw, msg = evaluate_alerts_for_display(test_db, actor_role="qc_operator")
    assert len(alerts) == 0
    assert "chưa được phê duyệt hoặc đang tắt" in msg


# --- PROBE 2: Append-Only Responses Verification ---

def test_probe2_append_only_response_audit_trail(test_db: Path):
    """Bảng phản hồi in_app_alert_responses phải là append-only, lưu từng phản hồi thành dòng mới."""
    snap_id, idem_key = _seed_snapshot_and_assessment(
        test_db, snapshot_id="SNAP_APPEND", risk_level="HIGH", unit_serial="UNIT_APPEND"
    )
    alerts, _, _ = evaluate_alerts_for_display(test_db, actor_role="qc_operator")
    assert len(alerts) == 1
    alert = alerts[0]

    # Action 1: Snooze for 30 minutes
    snooze_until_1 = snooze_alert(
        test_db,
        alert_id=alert.alert_id,
        idempotency_key=alert.idempotency_key,
        unit_serial=alert.unit_serial,
        actor="operator_1",
        duration_minutes=30,
        notes="Snooze lần 1: đang đợi kiểm tra",
    )
    assert snooze_until_1 is not None

    # Action 2: Snooze for another 60 minutes
    snooze_until_2 = snooze_alert(
        test_db,
        alert_id=alert.alert_id,
        idempotency_key=alert.idempotency_key,
        unit_serial=alert.unit_serial,
        actor="operator_2",
        duration_minutes=60,
        notes="Snooze lần 2: cần hội chẩn thêm",
    )
    assert snooze_until_2 is not None
    assert snooze_until_2 > snooze_until_1

    # Action 3: Acknowledge alert
    resp3_id = acknowledge_alert(
        test_db,
        alert_id=alert.alert_id,
        idempotency_key=alert.idempotency_key,
        unit_serial=alert.unit_serial,
        actor="qc_manager",
        notes="Tiếp nhận chính thức",
    )
    assert resp3_id.startswith("RESP-ACK-")

    # Verify: History contains exactly 3 distinct rows in chronological order!
    history = get_alert_response_history(test_db, idempotency_key=alert.idempotency_key)
    assert len(history) == 3, f"Bảng phản hồi phải lưu đủ 3 bản ghi append-only, nhận được: {len(history)}"
    assert history[0]["response_id"].startswith("RESP-SNZ-")
    assert history[1]["response_id"].startswith("RESP-SNZ-")
    assert history[2]["response_id"] == resp3_id
    assert history[0]["action"] == "snoozed"
    assert history[1]["action"] == "snoozed"
    assert history[2]["action"] == "acknowledged"

    # Next evaluation: suppressed because latest chronological action is 'acknowledged'
    alerts_after, _, _ = evaluate_alerts_for_display(test_db, actor_role="qc_operator")
    assert len(alerts_after) == 0


# --- PROBE 3: Role & Policy Authorization Verification ---

def test_probe3_enable_in_app_alert_policy_fail_closed_authorization(test_db: Path):
    """Chỉ có role owner/admin/quality_manager được cấp phép mới được phê duyệt policy. Thiếu role hoặc role khách bị chặn với PermissionError."""
    policy = AlertPolicy(is_enabled=True, approved_by="hacker")

    # Caller without role or None fails closed
    with pytest.raises(PermissionError):
        enable_in_app_alert_policy(test_db, policy, actor="guest_without_grant", actor_role=None)

    # Unauthorized guest role raises PermissionError
    with pytest.raises(PermissionError):
        enable_in_app_alert_policy(test_db, policy, actor="guest_without_grant", actor_role="khách_vãng_lai")

    with pytest.raises(PermissionError):
        enable_in_app_alert_policy(test_db, policy, actor="investigator_user", actor_role="investigator")

    # Grant role to owner_user then approve succeeds
    grant_role_permission(test_db, actor_id="owner_user", role="system_owner", scope="workspace_chat")
    saved = enable_in_app_alert_policy(test_db, policy, actor="owner_user", actor_role="system_owner")
    assert saved.approved_by == "owner_user"
    assert saved.is_enabled is True

    # Check persistence
    loaded = get_in_app_alert_policy(test_db)
    assert loaded is not None
    assert loaded.approved_by == "owner_user"


def test_probe3_kill_switch_fail_closed_authorization(test_db: Path):
    """Công tắc ngắt khẩn cấp bắt buộc vai trò người vận hành có thẩm quyền; khách hoặc người không quyền bị chặn."""
    # Caller without role or guest role fails closed
    with pytest.raises(PermissionError):
        set_kill_switch(test_db, active=True, actor="visitor_without_grant", actor_role=None, reason="Cố ý tắt lén")

    with pytest.raises(PermissionError):
        set_kill_switch(test_db, active=True, actor="visitor_without_grant", actor_role="khách_vãng_lai", reason="Cố ý tắt")

    with pytest.raises(PermissionError):
        set_kill_switch(test_db, active=True, actor="operator_unauth", actor_role="operator", reason="Thợ không đủ quyền")

    # Grant role to admin_user then authorized admin succeeds
    grant_role_permission(test_db, actor_id="admin_user", role="local_admin", scope="workspace_chat")
    set_kill_switch(test_db, active=True, actor="admin_user", actor_role="local_admin", reason="Quản trị viên thao tác hợp lệ")
    assert is_kill_switch_active(test_db) is True

    # Restore switch
    set_kill_switch(test_db, active=False, actor="admin_user", actor_role="local_admin", reason="Khôi phục")
    assert is_kill_switch_active(test_db) is False


def test_probe3_actor_role_scoping_in_alert_display(test_db: Path):
    """Người dùng có role không nằm trong policy.allowed_roles sẽ không được xem cảnh báo."""
    _seed_snapshot_and_assessment(
        test_db, snapshot_id="SNAP_ROLE", risk_level="HIGH", unit_serial="UNIT_ROLE"
    )
    # Role in allowed list: can see alert
    alerts_ok, _, _ = evaluate_alerts_for_display(test_db, actor_role="qc_operator")
    assert len(alerts_ok) == 1

    # Role NOT in allowed list (e.g. visitor): 0 alerts
    alerts_denied, _, msg = evaluate_alerts_for_display(test_db, actor_role="visitor")
    assert len(alerts_denied) == 0
    assert "không có quyền nhận cảnh báo" in msg


# --- PROBE 4: Kill Switch & Vietnamese UI Verification ---

def test_probe4_kill_switch_immediate_cutoff_and_reactivation(test_db: Path):
    """Công tắc ngắt khẩn cấp cắt lập tức toàn bộ cảnh báo và có thể phục hồi ngay."""
    _seed_snapshot_and_assessment(test_db, snapshot_id="SNAP_KS", risk_level="HIGH", unit_serial="UNIT_KS")

    # Before switch
    alerts_before, ks1, _ = evaluate_alerts_for_display(test_db, actor_role="qc_operator")
    assert len(alerts_before) == 1
    assert not ks1

    # Grant role to plant_manager
    grant_role_permission(test_db, actor_id="plant_manager", role="quality_manager", scope="workspace_chat")
    # Activate kill switch by authorized manager
    set_kill_switch(test_db, active=True, actor="plant_manager", actor_role="quality_manager", reason="Sự cố lưới điện")
    assert is_kill_switch_active(test_db) is True

    alerts_cut, ks2, msg2 = evaluate_alerts_for_display(test_db, actor_role="qc_operator")
    assert len(alerts_cut) == 0
    assert ks2 is True
    assert "công tắc ngắt khẩn cấp" in msg2

    # Deactivate kill switch
    set_kill_switch(test_db, active=False, actor="plant_manager", actor_role="quality_manager", reason="Đã xử lý xong sự cố")
    assert is_kill_switch_active(test_db) is False

    alerts_restored, ks3, _ = evaluate_alerts_for_display(test_db, actor_role="qc_operator")
    assert len(alerts_restored) == 1
    assert not ks3


def test_probe4_dismiss_requires_mandatory_justification(test_db: Path):
    """Bác bỏ cảnh báo bắt buộc phải có lý do giải trình, không được để trống."""
    snap_id, idem_key = _seed_snapshot_and_assessment(
        test_db, snapshot_id="SNAP_DIS", risk_level="HIGH", unit_serial="UNIT_DIS"
    )
    alerts, _, _ = evaluate_alerts_for_display(test_db, actor_role="qc_operator")
    alert = alerts[0]

    with pytest.raises(ValueError, match="lý do"):
        dismiss_alert(
            test_db,
            alert_id=alert.alert_id,
            idempotency_key=alert.idempotency_key,
            unit_serial=alert.unit_serial,
            actor="qc_op",
            notes="   ",
        )


def test_ui_wiring_and_vietnamese_labels():
    """Kiểm tra wiring và 100% tiếng Việt, loại bỏ hoàn toàn cụm tiếng Anh 'Kill Switch'."""
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    alert_source = Path("src/aios_habit/in_app_risk_alert.py").read_text(encoding="utf-8")

    assert "render_in_app_risk_alerts" in app_source
    assert "actor=current_actor" in app_source
    assert "actor_role=current_role" in app_source

    assert "Tiếp nhận" in alert_source
    assert "Bác bỏ" in alert_source
    assert "Tạm ẩn 60p" in alert_source
    assert "Mở hồ sơ" in alert_source
    assert "Công tắc ngắt khẩn cấp" in alert_source
    assert "Quản lý công tắc ngắt khẩn cấp" in alert_source

    # Ensure no English 'kill switch' leaks into user-facing text
    for line in alert_source.splitlines():
        if "st.markdown" in line or "st.info" in line or "st.warning" in line or "st.error" in line or "st.button" in line:
            assert "kill switch" not in line.lower(), f"Phát hiện rò rỉ chuỗi tiếng Anh 'kill switch' trong UI: {line}"

    for forbidden in ["Gemini", "GPT", "Claude", "EWMA internal", "traceback", "stack trace"]:
        assert forbidden.lower() not in alert_source.lower()


# --- PROBE NEGATIVE TESTS: Yêu cầu của Audit Độc Lập ---

def test_negative_missing_role_fails_closed(test_db: Path):
    """Khi actor_role là None hoặc rỗng, evaluate_alerts_for_display bắt buộc fail-closed trả về 0 cảnh báo (MISSING_ROLE_ALERTS == 0)."""
    _seed_snapshot_and_assessment(
        test_db, snapshot_id="SNAP_MISSING_ROLE", risk_level="HIGH", unit_serial="UNIT_MISSING"
    )
    # Gọi không truyền actor_role (actor_role=None)
    alerts_none, _, msg_none = evaluate_alerts_for_display(test_db, actor_role=None)
    assert len(alerts_none) == 0, f"Bị rò rỉ cảnh báo khi thiếu role: {len(alerts_none)}"
    assert "Yêu cầu vai trò người dùng" in msg_none

    # Gọi với actor_role rỗng
    alerts_empty, _, msg_empty = evaluate_alerts_for_display(test_db, actor_role="")
    assert len(alerts_empty) == 0
    assert "Yêu cầu vai trò người dùng" in msg_empty


def test_negative_self_claimed_owner_rejected(test_db: Path):
    """Người gọi tự xưng actor_role='system_owner' mà không có RoleGrant trong scope sẽ bị ném PermissionError (SELF_CLAIM_APPROVED_BY không thể là intruder)."""
    fake_policy = AlertPolicy(
        is_enabled=True,
        approved_by="intruder",
        allowed_roles=["system_owner", "qc_operator"],
    )
    with pytest.raises(PermissionError, match="không có cấp quyền"):
        enable_in_app_alert_policy(
            test_db,
            fake_policy,
            actor="intruder",
            actor_role="system_owner",
            scope="workspace_chat",
        )

    # Kiểm tra policy không bị ghi đè bởi intruder
    current_policy = get_in_app_alert_policy(test_db)
    assert current_policy is not None
    assert current_policy.approved_by != "intruder"

    # Tương tự cho kill switch: kẻ xâm nhập không thể tự khai role để ngắt hệ thống
    with pytest.raises(PermissionError, match="không có cấp quyền"):
        set_kill_switch(
            test_db,
            active=True,
            actor="intruder",
            actor_role="system_owner",
            reason="Phá hoại",
            scope="workspace_chat",
        )


def test_probe_intruder_forged_viewer_role_rejected(test_db: Path):
    """Chặn rò rỉ khi kẻ xâm nhập truyền role hợp lệ (qc_operator) nhưng không có RoleGrant trong kho authorization."""
    _seed_snapshot_and_assessment(
        test_db, snapshot_id="SNAP_INTRUDER", risk_level="HIGH", unit_serial="UNIT_INTRUDER"
    )
    # Intruder gọi với actor_id="intruder" và actor_role="qc_operator"
    alerts, ks, msg = evaluate_alerts_for_display(
        test_db,
        actor_id="intruder",
        actor_role="qc_operator",
        scope="workspace_chat",
    )
    assert len(alerts) == 0, f"LỖ HỔNG: Kẻ xâm nhập xem được {len(alerts)} cảnh báo!"
    assert ks is False
    assert "không có quyền" in msg or "không sở hữu vai trò" in msg
