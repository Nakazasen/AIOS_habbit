import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import pytest

from aios_habit.case_models import EvidenceItem
from aios_habit.ide_handoff_bridge import (
    REQ_STATE_COMPLETED,
    REQ_STATE_FAILED,
    REQ_STATE_PENDING,
    block_cloud_provider_for_local_only,
    check_handoff_request_timeouts,
    expected_inbox_response_path,
    import_pending_ide_response,
    is_request_expired,
    save_imported_ide_answer,
    validate_handoff_bundle,
    verify_bundle_integrity,
    vietnamese_next_step_instruction,
    write_ide_handoff_bundle,
)


def fake_items():
    return [EvidenceItem("EVD-1", "CASE-1", "note", "manual", "Safe title", "Safe evidence text", privacy_level="local_only")]


def write_schema_response(path, request_id, evidence_ids, **overrides):
    response = {
        "schema_version": "ide_handoff_response_v1",
        "request_id": request_id,
        "status": "completed",
        "answer_markdown": "Answer with citation [EVD-1]",
        "answer_text": "Answer with citation [EVD-1]",
        "cited_evidence_ids": evidence_ids,
        "evidence_ids_used": evidence_ids,
        "limitations": [],
        "confidence": "high",
        "privacy_acknowledged": True,
        "used_full_bundle": True,
        "unsupported_claims": [],
        "recommended_next_actions": ["Review"],
        "model_tool_name": "Antigravity IDE AI",
    }
    response.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_ui_flow_creates_outbox_bundle_prompt_and_status(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-UI")
    assert req.bundle_dir == tmp_path / "outbox" / "REQ-UI"
    assert req.outbox_dir == req.bundle_dir
    assert req.ok is True
    assert req.error_message == ""
    assert (req.bundle_dir / "evidence_bundle.json").exists()
    assert (req.bundle_dir / "prompt_for_antigravity.md").exists()
    assert (req.bundle_dir / "request_status.json").exists()
    bundle = json.loads((req.bundle_dir / "evidence_bundle.json").read_text(encoding="utf-8"))
    assert bundle["case_id"] == "CASE-1"
    assert bundle["request_id"] == "REQ-UI"
    assert bundle["allowed_source_ids"] == ["EVD-1"]
    assert bundle["local_only"] is True
    assert bundle["expected_response_schema"] == "ide_handoff_response_v1"
    assert "timeout_seconds" in bundle
    assert "expires_at" in bundle
    prompt = (req.bundle_dir / "prompt_for_antigravity.md").read_text(encoding="utf-8")
    assert "response.json" in prompt
    assert "answer_markdown" in prompt
    assert "cited_evidence_ids" in prompt
    status = json.loads((req.bundle_dir / "request_status.json").read_text(encoding="utf-8"))
    assert status["state"] == REQ_STATE_PENDING


def test_inbox_response_imports_and_processed_result_written(tmp_path, monkeypatch):
    saved = []
    monkeypatch.setattr("aios_habit.ide_handoff_bridge.save_evidence", lambda ev: saved.append(ev))
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-INBOX")
    write_schema_response(expected_inbox_response_path(req.request_id, root=tmp_path), req.request_id, ["EVD-1"])
    result = import_pending_ide_response(req.request_id, root=tmp_path)
    assert result.ok is True
    answer = save_imported_ide_answer("CASE-1", result, root=tmp_path)
    assert answer.final_answer is True
    assert saved[0].source_type == "ide_handoff_strong_answer"
    assert (tmp_path / "processed" / req.request_id / "response.json").exists()
    import_result = json.loads((tmp_path / "processed" / req.request_id / "import_result.json").read_text(encoding="utf-8"))
    assert import_result["ok"] is True
    status = json.loads((req.bundle_dir / "request_status.json").read_text(encoding="utf-8"))
    assert status["state"] == REQ_STATE_COMPLETED
    assert status["saved_answer_id"] == answer.draft_id


def test_wrong_request_unknown_id_missing_privacy_and_full_bundle_false_rejected(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-VALID")
    write_schema_response(tmp_path / "inbox" / "REQ-MISSING" / "response.json", "REQ-MISSING", ["EVD-1"])
    assert import_pending_ide_response("REQ-MISSING", root=tmp_path).ok is False
    write_schema_response(expected_inbox_response_path(req.request_id, root=tmp_path), req.request_id, ["UNKNOWN"])
    assert import_pending_ide_response(req.request_id, root=tmp_path).ok is False
    write_schema_response(expected_inbox_response_path(req.request_id, root=tmp_path), req.request_id, ["EVD-1"], privacy_acknowledged=False)
    assert import_pending_ide_response(req.request_id, root=tmp_path).ok is False
    write_schema_response(expected_inbox_response_path(req.request_id, root=tmp_path), req.request_id, ["EVD-1"], used_full_bundle=False)
    assert import_pending_ide_response(req.request_id, root=tmp_path).ok is False


def test_local_only_cloud_provider_blocked_and_vi_instruction(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-PRIV")
    blocked, message = block_cloud_provider_for_local_only(req.manifest)
    assert blocked is True
    assert "local_only" in message
    assert "Bị chặn" in message
    instruction = vietnamese_next_step_instruction(req.request_id, req.bundle_dir, req.inbox_response_path, req.manifest["privacy_mode"])
    assert "Mở Antigravity" in instruction
    assert "Kiểm tra phản hồi từ Antigravity" in instruction
    assert ("C" + "?u") not in instruction
    assert ("m" + "?nh") not in instruction


def test_ui_handoff_timeout_expiration_flow(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-UI-EXP", timeout_seconds=5)
    past = datetime.now() - timedelta(seconds=10)
    status = json.loads((req.bundle_dir / "request_status.json").read_text(encoding="utf-8"))
    status["created_at"] = past.isoformat()
    status["expires_at"] = (past + timedelta(seconds=5)).isoformat()
    (req.bundle_dir / "request_status.json").write_text(json.dumps(status), encoding="utf-8")

    expired = check_handoff_request_timeouts(tmp_path)
    assert "REQ-UI-EXP" in expired

    updated_status = json.loads((req.bundle_dir / "request_status.json").read_text(encoding="utf-8"))
    assert updated_status["state"] == REQ_STATE_FAILED
    assert updated_status["error_reason"] == "timeout"


def test_no_local_runs_tracked_by_git():
    tracked = subprocess.run(["git", "ls-files", "local_runs/"], text=True, capture_output=True, check=True, timeout=10.0)
    assert tracked.stdout.strip() == ""
    ignored = subprocess.run(["git", "check-ignore", "-v", "local_runs/"], text=True, capture_output=True, check=True, timeout=10.0)
    assert "local_runs/" in ignored.stdout


def test_bridge_manual_step_report_is_utf8_and_not_mojibake():
    report = Path(".ai/BRIDGE_MANUAL_STEP_REDUCTION_REPORT.md").read_text(encoding="utf-8")
    assert "Cầu nối model mạnh qua Antigravity" in report
    assert ("C" + "?u n" + "?i") not in report
    assert ("m" + "?nh") not in report


def test_route_workspace_chat_direct_mode_success_and_attribution(monkeypatch, tmp_path):
    from aios_habit.antigravity_bridge import (
        AntigravityHealthStatus,
        AntigravityBridgeResponse,
        route_workspace_chat_submission,
    )

    saved_messages = []
    monkeypatch.setattr("aios_habit.workspace_chat_store.save_message", lambda msg: saved_messages.append(msg))
    monkeypatch.setattr(
        "aios_habit.antigravity_bridge.call_antigravity_bridge",
        lambda **kwargs: AntigravityBridgeResponse(ok=True, answer_text="Direct answer from IDE", model="gpt-4o"),
    )

    health = AntigravityHealthStatus(status="direct_ready", mode="direct", capabilities=["direct_chat"])
    evidence = [{"title": "Doc 1", "text": "Content 1"}]

    ok, msg, badge, err = route_workspace_chat_submission(
        question="What is the plan?",
        evidence_items=evidence,
        packed_sources=(),
        conversation_id="conv_test",
        notebook_id="nb_test",
        retrieval_applied=True,
        retrieved_sources=(),
        retrieval_summary="Summary",
        current_keys=(),
        chat_history=(),
        user_raw_input="What is the plan?",
        health_status=health,
    )

    assert ok is True
    assert badge is not None
    assert badge["ai_source"] == "Antigravity IDE"
    assert badge["operational_mode"] == "direct"
    assert badge["model_tool_name"] == "gpt-4o"
    assert len(saved_messages) == 2
    assert saved_messages[0].role == "user"
    assert saved_messages[1].role == "assistant"
    assert saved_messages[1].content == "Direct answer from IDE"


def test_route_workspace_chat_direct_mode_fail_closed_never_fallbacks(monkeypatch):
    """Direct mode failure must fail closed with sanitized error and 0 fallback calls."""
    from aios_habit.antigravity_bridge import (
        AntigravityHealthStatus,
        AntigravityBridgeResponse,
        route_workspace_chat_submission,
    )

    fallback_called = []
    monkeypatch.setattr(
        "aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer",
        lambda req, client: fallback_called.append(req),
    )
    monkeypatch.setattr(
        "aios_habit.antigravity_bridge.call_antigravity_bridge",
        lambda **kwargs: AntigravityBridgeResponse(ok=False, answer_text="", error_message="Connection refused"),
    )

    health = AntigravityHealthStatus(status="direct_ready", mode="direct", capabilities=["direct_chat"])
    ok, msg, badge, err = route_workspace_chat_submission(
        question="Fail closed question",
        evidence_items=[],
        packed_sources=(),
        conversation_id="conv_test",
        notebook_id="nb_test",
        retrieval_applied=True,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(),
        chat_history=(),
        user_raw_input="Fail closed question",
        health_status=health,
    )

    assert ok is False
    assert err is not None
    assert "Lỗi cầu nối Antigravity IDE: Connection refused" in err
    assert len(fallback_called) == 0


def test_route_workspace_chat_handoff_mode_pending_state(monkeypatch, tmp_path):
    from aios_habit.antigravity_bridge import (
        AntigravityHealthStatus,
        route_workspace_chat_submission,
    )

    saved_messages = []
    monkeypatch.setattr("aios_habit.workspace_chat_store.save_message", lambda msg: saved_messages.append(msg))

    health = AntigravityHealthStatus(status="handoff_ready", mode="handoff", capabilities=["handoff_chat"])
    evidence = [{"title": "Doc 1", "text": "Content 1"}]

    ok, msg, badge, err = route_workspace_chat_submission(
        question="Handoff question?",
        evidence_items=evidence,
        packed_sources=(),
        conversation_id="conv_test",
        notebook_id="nb_test",
        retrieval_applied=True,
        retrieved_sources=(),
        retrieval_summary="Summary",
        current_keys=(),
        chat_history=(),
        user_raw_input="Handoff question?",
        health_status=health,
        handoff_root=tmp_path,
    )

    assert ok is True
    assert err is None
    assert badge is not None
    assert badge["type"] == "handoff_pending"
    assert "request_id" in badge
    assert badge["outbox_dir"] != ""
    assert len(saved_messages) == 2
    assert saved_messages[1].content == "⏳ Đang chờ Antigravity IDE xử lý..."


def test_render_bridge_header_status_truthfulness():
    import streamlit as st
    from aios_habit.antigravity_bridge import AntigravityHealthStatus
    from aios_habit.workspace_chat_ui import render_bridge_header_status

    rendered_messages = []
    st.info = lambda msg: rendered_messages.append(("info", msg))
    st.warning = lambda msg: rendered_messages.append(("warning", msg))
    st.error = lambda msg: rendered_messages.append(("error", msg))

    # Direct ready
    render_bridge_header_status(AntigravityHealthStatus("direct_ready", "direct", ["direct"]))
    assert any("🟢 **Cầu nối sẵn sàng** (Trực tiếp)" in m[1] for m in rendered_messages)

    # Handoff ready
    rendered_messages.clear()
    render_bridge_header_status(AntigravityHealthStatus("handoff_ready", "handoff", ["handoff"]))
    assert any("🟢 **Cầu nối sẵn sàng** (Chuyển giao)" in m[1] for m in rendered_messages)

    # Handoff pending
    rendered_messages.clear()
    render_bridge_header_status(AntigravityHealthStatus("handoff_pending", "handoff", []))
    assert any("🟡 **Đang chờ Antigravity IDE xử lý** (Chuyển giao)" in m[1] for m in rendered_messages)

    # Failed
    rendered_messages.clear()
    render_bridge_header_status(AntigravityHealthStatus("failed", "none", [], reason="Timeout 504"))
    assert any("🔴 **Cầu nối lỗi**: Timeout 504" in m[1] for m in rendered_messages)

    # Unavailable
    rendered_messages.clear()
    render_bridge_header_status(AntigravityHealthStatus("unavailable", "none", []))
    assert any("⚪ **Cầu nối chưa kết nối**" in m[1] for m in rendered_messages)


# ============================================================================
# Tier 5 Adversarial Stress & Hardening Test Suites
# ============================================================================


class TestTier5AdversarialBundleManifestTampering:
    """Tier 5 Adversarial: Cryptographic SHA-256 tampering and bundle corruption."""

    def test_bundle_evidence_tamper_detected_by_sha256(self, tmp_path):
        """Altering even a single character in evidence_full.jsonl must trigger SHA-256 mismatch."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-TAMPER")

        jsonl_path = req.bundle_dir / "evidence_full.jsonl"
        lines = jsonl_path.read_text(encoding="utf-8").splitlines()
        corrupt_first = json.loads(lines[0])
        corrupt_first["text"] = "MODIFIED_UNAUTHORIZED_CONTENT_PAYLOAD"
        lines[0] = json.dumps(corrupt_first, ensure_ascii=False)
        jsonl_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        ok, errors = verify_bundle_integrity(req.bundle_dir)
        assert ok is False
        assert any("SHA-256 mismatch" in err for err in errors)

    def test_bundle_manifest_completeness_sha_discrepancy(self, tmp_path):
        """Mismatched bundle_sha256 between manifest.json and completeness.json must be caught."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-SHA-DISCREP")

        comp_path = req.bundle_dir / "completeness.json"
        comp_data = json.loads(comp_path.read_text(encoding="utf-8"))
        comp_data["bundle_sha256"] = "f" * 64
        comp_path.write_text(json.dumps(comp_data), encoding="utf-8")

        ok, errors = verify_bundle_integrity(req.bundle_dir)
        assert ok is False
        assert any("bundle_sha256 mismatch" in err for err in errors)

    def test_bundle_zero_byte_manifest_resilience(self, tmp_path):
        """Zero-byte or empty manifest must return fail-closed error without unhandled exception."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-ZERO-MAN")
        (req.bundle_dir / "manifest.json").write_text("", encoding="utf-8")

        ok, errors = verify_bundle_integrity(req.bundle_dir)
        assert ok is False
        assert any("Corrupted manifest.json" in err for err in errors)

    def test_bundle_missing_completeness_flag(self, tmp_path):
        """FULL_BUNDLE_COMPLETE != 'YES' in manifest or completeness must fail verification."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-FLAG-FAIL")
        man_path = req.bundle_dir / "manifest.json"
        man_data = json.loads(man_path.read_text(encoding="utf-8"))
        man_data["FULL_BUNDLE_COMPLETE"] = "NO"
        man_path.write_text(json.dumps(man_data), encoding="utf-8")

        ok, errors = verify_bundle_integrity(req.bundle_dir)
        assert ok is False
        assert any("FULL_BUNDLE_COMPLETE is not YES" in err for err in errors)

    def test_bundle_oversize_guard_rejection(self, tmp_path):
        """Bundles exceeding max_total_text_chars (2,000,000) must immediately trigger size guard."""
        huge_evidence = [
            EvidenceItem("EVD-HUGE", "CASE-1", "note", "manual", "Huge doc", "X" * 2_500_000, privacy_level="local_only")
        ]
        with pytest.raises(ValueError, match="size guard triggered"):
            write_ide_handoff_bundle("CASE-1", "question", "active_case_all", huge_evidence, root=tmp_path, request_id="REQ-OVERSIZE")


class TestTier5AdversarialMalformedInboxResponses:
    """Tier 5 Adversarial: Schema violations, non-dict payloads, and malicious failure strings."""

    def test_inbox_response_invalid_version_rejected(self, tmp_path):
        """Unsupported schema version (e.g. ide_handoff_response_v2 or invalid_version) must be rejected."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-VER")
        write_schema_response(
            expected_inbox_response_path(req.request_id, root=tmp_path),
            req.request_id,
            ["EVD-1"],
            schema_version="invalid_version",
        )
        res = import_pending_ide_response(req.request_id, root=tmp_path)
        assert res.ok is False
        assert any("invalid schema_version" in err for err in res.errors)

    def test_inbox_response_non_dict_root_array(self, tmp_path):
        """JSON root formatted as a list instead of a dict must be rejected."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-ARRAY")
        resp_file = expected_inbox_response_path(req.request_id, root=tmp_path)
        resp_file.parent.mkdir(parents=True, exist_ok=True)
        resp_file.write_text(json.dumps(["malformed", "array", "payload"]), encoding="utf-8")

        res = import_pending_ide_response(req.request_id, root=tmp_path)
        assert res.ok is False
        assert any("must be an object/dict" in err for err in res.errors)

    def test_inbox_response_empty_answer_markdown(self, tmp_path):
        """Empty or whitespace-only answer markdown must fail validation."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-BLANK-ANS")
        write_schema_response(
            expected_inbox_response_path(req.request_id, root=tmp_path),
            req.request_id,
            ["EVD-1"],
            answer_markdown="   ",
            answer_text="",
        )

        res = import_pending_ide_response(req.request_id, root=tmp_path)
        assert res.ok is False
        assert any("answer_markdown is required" in err for err in res.errors)

    def test_inbox_response_missing_model_tool_name(self, tmp_path):
        """Missing model_tool_name header in response must be rejected."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-NO-MODEL")
        write_schema_response(
            expected_inbox_response_path(req.request_id, root=tmp_path),
            req.request_id,
            ["EVD-1"],
            model_tool_name="",
        )

        res = import_pending_ide_response(req.request_id, root=tmp_path)
        assert res.ok is False
        assert any("model_tool_name is required" in err for err in res.errors)

    def test_inbox_response_corrupted_json_syntax(self, tmp_path):
        """Corrupted, unparseable JSON file in inbox must be handled safely without crashing."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-CORRUPT-JSON")
        resp_file = expected_inbox_response_path(req.request_id, root=tmp_path)
        resp_file.parent.mkdir(parents=True, exist_ok=True)
        resp_file.write_text('{"schema_version": "ide_handoff_response_v1", "incomplete": ', encoding="utf-8")

        res = import_pending_ide_response(req.request_id, root=tmp_path)
        assert res.ok is False
        assert any("malformed JSON response" in err for err in res.errors)

    def test_inbox_response_explicit_failure_sanitizes_paths_in_status(self, tmp_path):
        """Explicit IDE failure reporting sensitive crash paths must sanitize paths before writing request_status.json."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-FAIL-SAN")
        write_schema_response(
            expected_inbox_response_path(req.request_id, root=tmp_path),
            req.request_id,
            [],
            status="failed",
            error="CUDA crash at D:\\AIOS\\Vault\\secret.key with Bearer sk-ant-secret-12345678",
        )

        res = import_pending_ide_response(req.request_id, root=tmp_path)
        assert res.ok is False
        status = json.loads((req.bundle_dir / "request_status.json").read_text(encoding="utf-8"))
        assert status["state"] == REQ_STATE_FAILED
        assert "D:\\AIOS\\Vault" not in status["error"]
        assert "<path>" in status["error"]
        assert "sk-ant-secret-12345678" not in status["error"]

    def test_inbox_response_unauthorized_citations_sorted(self, tmp_path):
        """Citations not in allowed_source_ids must be rejected with deterministic alphabetical sorting in error message."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-UNAUTH-SORT")
        write_schema_response(
            expected_inbox_response_path(req.request_id, root=tmp_path),
            req.request_id,
            ["EVD-Z", "EVD-A", "EVD-M"],
        )

        res = import_pending_ide_response(req.request_id, root=tmp_path)
        assert res.ok is False
        assert any("unknown evidence_ids_used: EVD-A, EVD-M, EVD-Z" in err for err in res.errors)


class TestTier5AdversarialTimeoutClockJumpsAndExpirations:
    """Tier 5 Adversarial: Clock leap jumps, NTP backward steps, and expiration race conditions."""

    def test_timeout_clock_jump_forward_expires_request(self, tmp_path):
        """Simulated 2-hour forward jump marks pending request as failed with error_reason='timeout'."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-LEAP-FWD", timeout_seconds=300)

        now_future = datetime.now() + timedelta(hours=2)
        expired = check_handoff_request_timeouts(tmp_path, now=now_future)
        assert "REQ-LEAP-FWD" in expired

        status = json.loads((req.bundle_dir / "request_status.json").read_text(encoding="utf-8"))
        assert status["state"] == REQ_STATE_FAILED
        assert status["error_reason"] == "timeout"

    def test_timeout_clock_jump_backward_preserves_pending(self, tmp_path):
        """Simulated backward clock step (NTP adjustment) must NOT prematurely expire pending requests."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-LEAP-BWD", timeout_seconds=300)

        now_past = datetime.now() - timedelta(minutes=10)
        expired = check_handoff_request_timeouts(tmp_path, now=now_past)
        assert "REQ-LEAP-BWD" not in expired

        status = json.loads((req.bundle_dir / "request_status.json").read_text(encoding="utf-8"))
        assert status["state"] == REQ_STATE_PENDING

    def test_timeout_corrupted_expires_at_fallback(self, tmp_path):
        """Corrupted expires_at string gracefully falls back to created_at + timeout_seconds calculation."""
        past_created = (datetime.now() - timedelta(seconds=400)).isoformat()
        status_payload = {
            "state": "handoff_pending",
            "expires_at": "CORRUPTED_NON_ISO_STRING",
            "created_at": past_created,
            "timeout_seconds": 300,
        }
        assert is_request_expired(status_payload, now=datetime.now()) is True

    def test_timeout_completed_or_failed_are_immutable(self, tmp_path):
        """Requests already in completed or failed state must never be re-expired or modified by timeout sweeps."""
        req_comp = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-IMMUTABLE-COMP")
        status_file = req_comp.bundle_dir / "request_status.json"
        status = json.loads(status_file.read_text(encoding="utf-8"))
        status["state"] = REQ_STATE_COMPLETED
        status_file.write_text(json.dumps(status), encoding="utf-8")

        now_future = datetime.now() + timedelta(days=30)
        expired = check_handoff_request_timeouts(tmp_path, now=now_future)
        assert "REQ-IMMUTABLE-COMP" not in expired

        status_after = json.loads(status_file.read_text(encoding="utf-8"))
        assert status_after["state"] == REQ_STATE_COMPLETED

    def test_timeout_inbox_response_arrival_prevents_expiration(self, tmp_path):
        """If inbox response.json has arrived, timeout scanner must NOT mark the request failed."""
        req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-INBOX-ARRIVED", timeout_seconds=5)
        write_schema_response(expected_inbox_response_path(req.request_id, root=tmp_path), req.request_id, ["EVD-1"])

        now_future = datetime.now() + timedelta(hours=1)
        expired = check_handoff_request_timeouts(tmp_path, now=now_future)
        assert "REQ-INBOX-ARRIVED" not in expired

        status = json.loads((req.bundle_dir / "request_status.json").read_text(encoding="utf-8"))
        assert status["state"] == REQ_STATE_PENDING


class TestTier5AdversarialFailClosedUIRouting:
    """Tier 5 Adversarial: Verification that under all failure conditions, 0 fallback calls occur."""

    def test_workspace_chat_handoff_creation_failure_fails_closed(self, monkeypatch):
        """When handoff bundle creation fails, submission returns error and makes 0 calls to fallback AI."""
        from aios_habit.antigravity_bridge import AntigravityHealthStatus, route_workspace_chat_submission

        fallback_invocations = []
        monkeypatch.setattr(
            "aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer",
            lambda req, client: fallback_invocations.append(req),
        )
        monkeypatch.setattr(
            "aios_habit.ide_handoff_bridge.write_ide_handoff_bundle",
            lambda **kwargs: type("BundleRes", (), {"ok": False, "error_message": "Disk Full or Permission Denied"})(),
        )

        health = AntigravityHealthStatus(status="handoff_ready", mode="handoff", capabilities=["local_handoff"])
        ok, msg, badge, err = route_workspace_chat_submission(
            question="Test handoff write failure",
            evidence_items=[],
            packed_sources=(),
            conversation_id="conv_err",
            notebook_id="nb_err",
            retrieval_applied=True,
            retrieved_sources=(),
            retrieval_summary="",
            current_keys=(),
            chat_history=(),
            user_raw_input="Test handoff write failure",
            health_status=health,
        )

        assert ok is False
        assert err is not None
        assert "Lỗi tạo gói yêu cầu Antigravity IDE: Disk Full" in err
        assert len(fallback_invocations) == 0

    def test_workspace_chat_handoff_creation_exception_fails_closed(self, monkeypatch):
        """When write_ide_handoff_bundle raises an exception (e.g. size guard or IO error), it fails closed with 0 fallback calls."""
        from aios_habit.antigravity_bridge import AntigravityHealthStatus, route_workspace_chat_submission

        fallback_invocations = []
        monkeypatch.setattr(
            "aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer",
            lambda req, client: fallback_invocations.append(req),
        )

        def _raise_error(**kwargs):
            raise ValueError("full bundle size guard triggered; export stopped without omission")

        monkeypatch.setattr("aios_habit.ide_handoff_bridge.write_ide_handoff_bundle", _raise_error)

        health = AntigravityHealthStatus(status="handoff_ready", mode="handoff", capabilities=["local_handoff"])
        ok, msg, badge, err = route_workspace_chat_submission(
            question="Test size guard crash",
            evidence_items=[],
            packed_sources=(),
            conversation_id="conv_exc",
            notebook_id="nb_exc",
            retrieval_applied=True,
            retrieved_sources=(),
            retrieval_summary="",
            current_keys=(),
            chat_history=(),
            user_raw_input="Test size guard crash",
            health_status=health,
        )

        assert ok is False
        assert badge is None
        assert err is not None
        assert "Lỗi tạo gói yêu cầu Antigravity IDE: full bundle size guard triggered" in err
        assert len(fallback_invocations) == 0

    def test_workspace_chat_direct_mode_exception_fails_closed_zero_fallback(self, monkeypatch):
        """Unexpected exception in direct adapter call fails closed cleanly with 0 fallback calls."""
        from aios_habit.antigravity_bridge import AntigravityHealthStatus, route_workspace_chat_submission

        fallback_invocations = []
        monkeypatch.setattr(
            "aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer",
            lambda req, client: fallback_invocations.append(req),
        )
        def _raise_crash(**kwargs):
            raise RuntimeError("Unexpected daemon socket drop")

        monkeypatch.setattr("aios_habit.antigravity_bridge.call_antigravity_bridge", _raise_crash)

        health = AntigravityHealthStatus(status="direct_ready", mode="direct", capabilities=["direct_chat"])
        ok, msg, badge, err = route_workspace_chat_submission(
            question="Test direct crash failure",
            evidence_items=[],
            packed_sources=(),
            conversation_id="conv_crash",
            notebook_id="nb_crash",
            retrieval_applied=True,
            retrieved_sources=(),
            retrieval_summary="",
            current_keys=(),
            chat_history=(),
            user_raw_input="Test direct crash failure",
            health_status=health,
        )

        assert ok is False
        assert err is not None
        assert "Lỗi cầu nối Antigravity IDE:" in err
        assert len(fallback_invocations) == 0
