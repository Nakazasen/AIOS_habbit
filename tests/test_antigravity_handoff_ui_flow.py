import json
import subprocess
from pathlib import Path

from aios_habit.case_models import EvidenceItem
from aios_habit.ide_handoff_bridge import (
    block_cloud_provider_for_local_only,
    expected_inbox_response_path,
    import_pending_ide_response,
    save_imported_ide_answer,
    vietnamese_next_step_instruction,
    write_ide_handoff_bundle,
)


def fake_items():
    return [EvidenceItem("EVD-1", "CASE-1", "note", "manual", "Safe title", "Safe evidence text", privacy_level="local_only")]


def write_schema_response(path, request_id, evidence_ids, **overrides):
    response = {"request_id": request_id, "answer_markdown": "Answer with citation [EVD-1]", "cited_evidence_ids": evidence_ids, "limitations": [], "confidence": "high", "privacy_acknowledged": True, "used_full_bundle": True, "unsupported_claims": [], "recommended_next_actions": ["Review"], "model_tool_name": "Antigravity IDE AI"}
    response.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(response), encoding="utf-8")
    return path


def test_ui_flow_creates_outbox_bundle_prompt_and_status(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-UI")
    assert req.bundle_dir == tmp_path / "outbox" / "REQ-UI"
    assert (req.bundle_dir / "evidence_bundle.json").exists()
    assert (req.bundle_dir / "prompt_for_antigravity.md").exists()
    assert (req.bundle_dir / "request_status.json").exists()
    bundle = json.loads((req.bundle_dir / "evidence_bundle.json").read_text(encoding="utf-8"))
    assert bundle["case_id"] == "CASE-1"
    assert bundle["request_id"] == "REQ-UI"
    assert bundle["allowed_source_ids"] == ["EVD-1"]
    assert bundle["local_only"] is True
    assert bundle["expected_response_schema"] == "ide_handoff_response_v1"
    prompt = (req.bundle_dir / "prompt_for_antigravity.md").read_text(encoding="utf-8")
    assert "response.json" in prompt
    assert "answer_markdown" in prompt
    assert "cited_evidence_ids" in prompt


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
    assert status["state"] == "imported"


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


def test_no_local_runs_tracked_by_git():
    tracked = subprocess.run(["git", "ls-files", "local_runs/"], text=True, capture_output=True, check=True)
    assert tracked.stdout.strip() == ""
    ignored = subprocess.run(["git", "check-ignore", "-v", "local_runs/"], text=True, capture_output=True, check=True)
    assert "local_runs/" in ignored.stdout


def test_case_cockpit_ui_first_flow_keeps_manual_json_fallback_secondary():
    source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")
    create_idx = source.index('key="create_ide_full_bundle"')
    check_idx = source.index('key="check_ide_full_bundle_response"')
    fallback_idx = source.index("Fallback thủ công")
    manual_import_idx = source.index('key="import_ide_full_bundle_response"')
    assert create_idx < check_idx < fallback_idx < manual_import_idx
    assert "Cầu nối model mạnh qua Antigravity" in source
    assert "Không cần CLI" in source
    assert "không cần dán JSON ở luồng mặc định" in source


def test_bridge_manual_step_report_is_utf8_and_not_mojibake():
    report = Path(".ai/BRIDGE_MANUAL_STEP_REDUCTION_REPORT.md").read_text(encoding="utf-8")
    assert "Cầu nối model mạnh qua Antigravity" in report
    assert ("C" + "?u n" + "?i") not in report
    assert ("m" + "?nh") not in report



def test_owner_trial_pain_point_labels_and_no_raw_json_default():
    source = Path("src/aios_habit/case_cockpit.py").read_text(encoding="utf-8")
    assert "Gói đang chờ phản hồi" in source
    assert "Quét phản hồi trong thư mục inbox" in source
    assert "Dán câu trả lời Markdown từ Antigravity" in source
    assert "Tôi xác nhận model đã dùng đúng gói bằng chứng" in source
    assert "Tôi xác nhận không đưa dữ liệu local_only ra cloud" in source
    assert "Xem nhanh bản đồ tri thức" in source
    markdown_idx = source.index('key="import_ide_markdown_answer"')
    fallback_idx = source.index("Fallback thủ công")
    assert markdown_idx < fallback_idx
    assert "NotebookLM replacement: YES" not in source
    assert "P1.0 opened: YES" not in source
