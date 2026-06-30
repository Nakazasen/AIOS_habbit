from aios_habit.case_models import EvidenceItem
from aios_habit.ide_handoff_bridge import (
    convert_markdown_answer_to_ide_response,
    import_markdown_ide_response,
    save_imported_ide_answer,
    write_ide_handoff_bundle,
)


def fake_items():
    return [EvidenceItem("EVD-1", "CASE-1", "note", "manual", "Safe title", "Safe evidence text", privacy_level="local_only")]


def test_raw_markdown_converts_to_response_object():
    response = convert_markdown_answer_to_ide_response("REQ-1", "# Answer", cited_evidence_ids=["EVD-1"], privacy_acknowledged=True, used_full_bundle=True)
    assert response["request_id"] == "REQ-1"
    assert response["answer_markdown"] == "# Answer"
    assert response["cited_evidence_ids"] == ["EVD-1"]


def test_raw_markdown_without_evidence_ids_adds_limitation():
    response = convert_markdown_answer_to_ide_response("REQ-1", "# Answer")
    assert response["cited_evidence_ids"] == []
    assert "No explicit evidence IDs were provided." in response["limitations"]


def test_raw_markdown_import_fails_if_privacy_acknowledged_false(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-PRIV")
    result = import_markdown_ide_response(req.request_id, "Answer", root=tmp_path, cited_evidence_ids=["EVD-1"], used_full_bundle=True, privacy_acknowledged=False)
    assert result.ok is False
    assert "privacy_acknowledged" in "; ".join(result.errors)


def test_raw_markdown_import_fails_if_used_full_bundle_false(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-FULL")
    result = import_markdown_ide_response(req.request_id, "Answer", root=tmp_path, cited_evidence_ids=["EVD-1"], used_full_bundle=False, privacy_acknowledged=True)
    assert result.ok is False
    assert "used_full_bundle" in "; ".join(result.errors)


def test_wrong_request_id_still_rejected(tmp_path):
    result = import_markdown_ide_response("REQ-MISSING", "Answer", root=tmp_path, cited_evidence_ids=["EVD-1"], used_full_bundle=True, privacy_acknowledged=True)
    assert result.ok is False


def test_unknown_evidence_id_still_rejected(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-BADID")
    result = import_markdown_ide_response(req.request_id, "Answer", root=tmp_path, cited_evidence_ids=["UNKNOWN"], used_full_bundle=True, privacy_acknowledged=True)
    assert result.ok is False
    assert "unknown evidence_ids_used" in "; ".join(result.errors)


def test_pasted_markdown_fallback_can_save_back_after_validation(tmp_path, monkeypatch):
    saved = []
    monkeypatch.setattr("aios_habit.ide_handoff_bridge.save_evidence", lambda ev: saved.append(ev))
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-SAVE")
    result = import_markdown_ide_response(req.request_id, "Answer [EVD-1]", root=tmp_path, cited_evidence_ids=["EVD-1"], used_full_bundle=True, privacy_acknowledged=True)
    assert result.ok is True
    answer = save_imported_ide_answer("CASE-1", result, root=tmp_path)
    assert answer.final_answer is True
    assert saved[0].source_type == "ide_handoff_strong_answer"
