import json
from pathlib import Path
from aios_habit.case_models import EvidenceItem
from aios_habit.ide_handoff_bridge import import_ide_response, save_imported_ide_answer, validate_handoff_bundle, write_ide_handoff_bundle


def fake_items():
    return [
        EvidenceItem("EVD-1", "CASE-1", "note", "manual", "ManualShipping_ExistingLineAuto_InboundDownload", "Resource / ResourceGroup / Operation / Spec / WorkflowStep and Sup_Line Oricon Container evidence", privacy_level="local_only"),
        EvidenceItem("EVD-2", "CASE-1", "pdf", "doc.pdf", "Metadata PDF", "", privacy_level="local_only"),
    ]


def test_full_bundle_export_includes_all_evidence_items(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path)
    records = [json.loads(x) for x in (req.bundle_dir / "evidence_full.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2
    assert req.manifest["evidence_item_count"] == 2
    assert req.manifest["omitted_items_count"] == 0
    assert req.manifest["FULL_BUNDLE_COMPLETE"] == "YES"


def test_manifest_completeness_hash_changes_if_evidence_changes(tmp_path):
    a = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-A")
    changed = fake_items(); changed[0].extracted_text += " changed"
    b = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", changed, root=tmp_path, request_id="REQ-B")
    assert a.manifest["bundle_sha256"] != b.manifest["bundle_sha256"]


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


def test_validate_handoff_bundle(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path)
    assert validate_handoff_bundle(req.bundle_dir)["ok"] is True


def write_response(tmp_path, request_id, evidence_ids, **overrides):
    response = {"request_id": request_id, "model_tool_name": "IDE AI", "answer_text": "Answer", "evidence_ids_used": evidence_ids, "source_files_used": [], "missing_evidence": [], "confidence_label": "high", "risk_label": "low", "privacy_acknowledged": True, "used_full_bundle": True, "notes": ""}
    response.update(overrides)
    path = tmp_path / "inbox" / f"RESP-{request_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(response), encoding="utf-8")
    return path


def test_response_import_succeeds_when_valid(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-OK")
    path = write_response(tmp_path, req.request_id, ["EVD-1"])
    result = import_ide_response(path, root=tmp_path)
    assert result.ok is True
    assert result.final_answer is True


def test_response_import_fails_if_request_id_mismatches(tmp_path):
    path = write_response(tmp_path, "REQ-MISSING", ["EVD-1"])
    assert import_ide_response(path, root=tmp_path).ok is False


def test_response_import_no_evidence_is_review_required(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-NOREF")
    result = import_ide_response(write_response(tmp_path, req.request_id, []), root=tmp_path)
    assert result.ok is True
    assert result.final_answer is False


def test_response_import_fails_if_privacy_not_acknowledged(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-PRIV")
    result = import_ide_response(write_response(tmp_path, req.request_id, ["EVD-1"], privacy_acknowledged=False), root=tmp_path)
    assert result.ok is False


def test_response_import_fails_if_full_bundle_not_used(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-FULL")
    result = import_ide_response(write_response(tmp_path, req.request_id, ["EVD-1"], used_full_bundle=False), root=tmp_path)
    assert result.ok is False


def test_response_import_rejects_unknown_evidence_ids(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-BADID")
    result = import_ide_response(write_response(tmp_path, req.request_id, ["UNKNOWN"]), root=tmp_path)
    assert result.ok is False


def test_saved_answer_has_route_summary_and_final_only_with_refs(tmp_path, monkeypatch):
    saved = []
    monkeypatch.setattr("aios_habit.ide_handoff_bridge.save_evidence", lambda ev: saved.append(ev))
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-SAVE")
    result = import_ide_response(write_response(tmp_path, req.request_id, ["EVD-1"]), root=tmp_path)
    answer = save_imported_ide_answer("CASE-1", result, root=tmp_path)
    assert answer.route_summary == "ide_full_bundle_handoff"
    assert answer.final_answer is True
    assert saved[0].source_type == "ide_handoff_strong_answer"


def test_size_guard_stops_without_omission(tmp_path):
    try:
        write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, max_total_text_chars=1)
    except ValueError as exc:
        assert "size guard" in str(exc)
    else:
        raise AssertionError("expected size guard")
