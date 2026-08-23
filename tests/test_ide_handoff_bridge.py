import json
from datetime import datetime, timedelta
from pathlib import Path
import pytest

from aios_habit.case_models import EvidenceItem
from aios_habit.ide_handoff_bridge import (
    DEFAULT_HANDOFF_TIMEOUT_SECONDS,
    REQ_STATE_COMPLETED,
    REQ_STATE_FAILED,
    REQ_STATE_PENDING,
    RESPONSE_SCHEMA_VERSION,
    check_handoff_request_timeouts,
    import_ide_response,
    is_request_expired,
    save_imported_ide_answer,
    update_request_status,
    validate_handoff_bundle,
    verify_bundle_integrity,
    write_ide_handoff_bundle,
    _normalize_request_state,
)


def fake_items():
    return [
        EvidenceItem(
            "EVD-1",
            "CASE-1",
            "note",
            "manual",
            "ManualShipping_ExistingLineAuto_InboundDownload",
            "Resource / ResourceGroup / Operation / Spec / WorkflowStep and Sup_Line Oricon Container evidence",
            privacy_level="local_only",
        ),
        EvidenceItem("EVD-2", "CASE-1", "pdf", "doc.pdf", "Metadata PDF", "", privacy_level="local_only"),
    ]


def write_response(tmp_path, request_id, evidence_ids, **overrides):
    response = {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "request_id": request_id,
        "status": "completed",
        "model_tool_name": "IDE AI",
        "answer_text": "Answer referencing [EVD-1]",
        "answer_markdown": "Answer referencing [EVD-1]",
        "evidence_ids_used": evidence_ids,
        "cited_evidence_ids": evidence_ids,
        "source_files_used": [],
        "missing_evidence": [],
        "confidence": "high",
        "confidence_label": "high",
        "risk_label": "low",
        "privacy_acknowledged": True,
        "used_full_bundle": True,
        "limitations": [],
        "unsupported_claims": [],
        "recommended_next_actions": ["Review in Case"],
    }
    response.update(overrides)
    path = tmp_path / "inbox" / request_id / "response.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_full_bundle_export_includes_all_evidence_items(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path)
    records = [json.loads(x) for x in (req.bundle_dir / "evidence_full.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2
    assert req.manifest["evidence_item_count"] == 2
    assert req.manifest["omitted_items_count"] == 0
    assert req.manifest["FULL_BUNDLE_COMPLETE"] == "YES"
    assert req.manifest["timeout_seconds"] == DEFAULT_HANDOFF_TIMEOUT_SECONDS
    assert "expires_at" in req.manifest


def test_bundle_creation_has_pending_status_and_timeout(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, timeout_seconds=180)
    status_path = req.bundle_dir / "request_status.json"
    assert status_path.exists()
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["request_id"] == req.request_id
    assert status["state"] == REQ_STATE_PENDING
    assert status["timeout_seconds"] == 180
    assert "expires_at" in status
    assert status["completed_at"] == ""
    assert status["failed_at"] == ""
    assert status["error"] == ""


def test_manifest_completeness_hash_changes_if_evidence_changes(tmp_path):
    a = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-A")
    changed = fake_items()
    changed[0].extracted_text += " changed"
    b = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", changed, root=tmp_path, request_id="REQ-B")
    assert a.manifest["bundle_sha256"] != b.manifest["bundle_sha256"]


def test_verify_bundle_integrity_success_and_tamper_detection(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-INT")
    ok, errors = verify_bundle_integrity(req.bundle_dir)
    assert ok is True
    assert len(errors) == 0

    # Tamper evidence_full.jsonl
    (req.bundle_dir / "evidence_full.jsonl").write_text('{"evidence_id": "EVD-1", "text": "tampered"}\n', encoding="utf-8")
    tampered_ok, tampered_errors = verify_bundle_integrity(req.bundle_dir)
    assert tampered_ok is False
    assert any("SHA-256 mismatch" in err for err in tampered_errors)


def test_metadata_only_evidence_is_included_but_flagged(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path)
    text = (req.bundle_dir / "evidence_full.jsonl").read_text(encoding="utf-8")
    assert '"metadata_only": true' in text
    assert "Metadata-only evidence" in text


def test_local_only_privacy_warning_and_prompt_instruction(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path)
    assert req.manifest["allowed_external"] is False
    assert "local_only evidence" in req.ide_instruction
    prompt = (req.bundle_dir / "prompt.md").read_text(encoding="utf-8")
    assert "Read every file" in prompt
    assert "evidence_ids_used" in prompt
    assert RESPONSE_SCHEMA_VERSION in prompt


def test_validate_handoff_bundle_all_11_files(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path)
    val = validate_handoff_bundle(req.bundle_dir)
    assert val["ok"] is True
    assert len(val["missing"]) == 0


@pytest.mark.parametrize("file_to_remove", [
    "manifest.json",
    "evidence_bundle.json",
    "question.md",
    "prompt.md",
    "prompt_for_antigravity.md",
    "evidence_full.jsonl",
    "evidence_full.md",
    "source_manifest.json",
    "completeness.json",
    "README_FOR_IDE.md",
    "request_status.json",
])
def test_validate_handoff_bundle_fails_on_missing_file(tmp_path, file_to_remove):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path)
    target = req.bundle_dir / file_to_remove
    target.unlink()
    val = validate_handoff_bundle(req.bundle_dir)
    assert val["ok"] is False
    assert file_to_remove in val["missing"]


def test_response_import_succeeds_when_valid(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-OK")
    path = write_response(tmp_path, req.request_id, ["EVD-1"])
    result = import_ide_response(path, root=tmp_path)
    assert result.ok is True
    assert result.final_answer is True
    assert len(result.errors) == 0


def test_response_import_fails_if_request_id_mismatches(tmp_path):
    path = write_response(tmp_path, "REQ-MISSING", ["EVD-1"])
    result = import_ide_response(path, root=tmp_path)
    assert result.ok is False
    assert any("outbox request not found" in err for err in result.errors)


def test_response_import_fails_on_schema_version_mismatch(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-SCHEMA")
    path = write_response(tmp_path, req.request_id, ["EVD-1"], schema_version="v2_unsupported")
    result = import_ide_response(path, root=tmp_path)
    assert result.ok is False
    assert any("invalid schema_version" in err for err in result.errors)


def test_response_import_handles_explicit_ide_failure(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-FAIL")
    path = write_response(tmp_path, req.request_id, [], status="failed", error="Model out of memory on D:/Sandbox/file.txt")
    result = import_ide_response(path, root=tmp_path)
    assert result.ok is False
    assert any("IDE processing failed" in err for err in result.errors)
    # Check status transitioned to failed with sanitized path
    status = json.loads((req.bundle_dir / "request_status.json").read_text(encoding="utf-8"))
    assert status["state"] == REQ_STATE_FAILED
    assert "D:/Sandbox" not in status["error"]


def test_response_import_no_evidence_is_review_required(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-NOREF")
    result = import_ide_response(write_response(tmp_path, req.request_id, []), root=tmp_path)
    assert result.ok is True
    assert result.final_answer is False
    assert any("No evidence_ids_used" in w for w in result.warnings)


def test_response_import_fails_if_privacy_not_acknowledged(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-PRIV")
    result = import_ide_response(write_response(tmp_path, req.request_id, ["EVD-1"], privacy_acknowledged=False), root=tmp_path)
    assert result.ok is False
    assert any("privacy_acknowledged" in err for err in result.errors)


def test_response_import_fails_if_full_bundle_not_used(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-FULL")
    result = import_ide_response(write_response(tmp_path, req.request_id, ["EVD-1"], used_full_bundle=False), root=tmp_path)
    assert result.ok is False
    assert any("used_full_bundle" in err for err in result.errors)


def test_response_import_rejects_unknown_evidence_ids(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-BADID")
    result = import_ide_response(write_response(tmp_path, req.request_id, ["UNKNOWN"]), root=tmp_path)
    assert result.ok is False
    assert any("unknown evidence_ids_used: UNKNOWN" in err for err in result.errors)
    status = json.loads((req.bundle_dir / "request_status.json").read_text(encoding="utf-8"))
    assert status["state"] == REQ_STATE_FAILED


def test_multiple_unauthorized_citations_sorted_in_error(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-MULTI-BAD")
    result = import_ide_response(write_response(tmp_path, req.request_id, ["EVD-Z", "EVD-A"]), root=tmp_path)
    assert result.ok is False
    assert any("unknown evidence_ids_used: EVD-A, EVD-Z" in err for err in result.errors)


def test_malformed_json_response_resilience(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-MALFORM")
    resp_path = tmp_path / "inbox" / req.request_id / "response.json"
    resp_path.parent.mkdir(parents=True, exist_ok=True)
    resp_path.write_text("{ corrupt json ...", encoding="utf-8")
    result = import_ide_response(resp_path, root=tmp_path)
    assert result.ok is False
    assert any("malformed JSON response" in err for err in result.errors)


def test_empty_json_response_resilience(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-EMPTY")
    resp_path = tmp_path / "inbox" / req.request_id / "response.json"
    resp_path.parent.mkdir(parents=True, exist_ok=True)
    resp_path.write_text("", encoding="utf-8")
    result = import_ide_response(resp_path, root=tmp_path)
    assert result.ok is False
    assert any("response file is empty" in err for err in result.errors)


def test_non_dict_json_root_resilience(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-LIST")
    resp_path = tmp_path / "inbox" / req.request_id / "response.json"
    resp_path.parent.mkdir(parents=True, exist_ok=True)
    resp_path.write_text(json.dumps(["item1", "item2"]), encoding="utf-8")
    result = import_ide_response(resp_path, root=tmp_path)
    assert result.ok is False
    assert any("root must be an object/dict" in err for err in result.errors)


def test_saved_answer_has_route_summary_and_transitions_status_to_completed(tmp_path, monkeypatch):
    saved = []
    monkeypatch.setattr("aios_habit.ide_handoff_bridge.save_evidence", lambda ev: saved.append(ev))
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-SAVE")
    result = import_ide_response(write_response(tmp_path, req.request_id, ["EVD-1"]), root=tmp_path)
    answer = save_imported_ide_answer("CASE-1", result, root=tmp_path)
    assert answer.route_summary == "ide_full_bundle_handoff"
    assert answer.final_answer is True
    assert saved[0].source_type == "ide_handoff_strong_answer"
    # Status transitioned to completed
    status = json.loads((req.bundle_dir / "request_status.json").read_text(encoding="utf-8"))
    assert status["state"] == REQ_STATE_COMPLETED
    assert status["completed_at"] != ""
    assert status["saved_answer_id"] == answer.draft_id


def test_timeout_expiration_detection_and_transition(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-EXP", timeout_seconds=10)
    # Simulate past creation
    past_time = datetime.now() - timedelta(seconds=20)
    past_iso = past_time.isoformat()
    expires_iso = (past_time + timedelta(seconds=10)).isoformat()

    manifest = json.loads((req.bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["created_at"] = past_iso
    manifest["expires_at"] = expires_iso
    (req.bundle_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    status = json.loads((req.bundle_dir / "request_status.json").read_text(encoding="utf-8"))
    status["created_at"] = past_iso
    status["expires_at"] = expires_iso
    (req.bundle_dir / "request_status.json").write_text(json.dumps(status), encoding="utf-8")

    assert is_request_expired(status) is True

    expired_ids = check_handoff_request_timeouts(tmp_path)
    assert "REQ-EXP" in expired_ids

    updated_status = json.loads((req.bundle_dir / "request_status.json").read_text(encoding="utf-8"))
    assert updated_status["state"] == REQ_STATE_FAILED
    assert updated_status["error_reason"] == "timeout"
    assert "timed out after 10 seconds" in updated_status["error"]


def test_completed_request_not_expired_by_timeout(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-COMPL")
    update_request_status(req.status_path, REQ_STATE_COMPLETED, saved_answer_id="IDE-12345")

    # Set past timestamps
    past_time = datetime.now() - timedelta(days=10)
    status = json.loads(req.status_path.read_text(encoding="utf-8"))
    status["expires_at"] = past_time.isoformat()
    req.status_path.write_text(json.dumps(status), encoding="utf-8")

    assert is_request_expired(status) is False
    expired_ids = check_handoff_request_timeouts(tmp_path)
    assert "REQ-COMPL" not in expired_ids
    assert json.loads(req.status_path.read_text(encoding="utf-8"))["state"] == REQ_STATE_COMPLETED


def test_backward_compatibility_state_normalization():
    assert _normalize_request_state("created") == REQ_STATE_PENDING
    assert _normalize_request_state("imported") == REQ_STATE_COMPLETED
    assert _normalize_request_state("handoff_pending") == REQ_STATE_PENDING
    assert _normalize_request_state("completed") == REQ_STATE_COMPLETED
    assert _normalize_request_state("failed") == REQ_STATE_FAILED
    assert _normalize_request_state("unknown_state") == REQ_STATE_PENDING


def test_size_guard_stops_without_omission(tmp_path):
    try:
        write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, max_total_text_chars=1)
    except ValueError as exc:
        assert "size guard" in str(exc)
    else:
        raise AssertionError("expected size guard")
