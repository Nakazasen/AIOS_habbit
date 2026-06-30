import json
from aios_habit.case_models import EvidenceItem
from aios_habit.ide_handoff_bridge import (
    find_response_for_request,
    get_latest_pending_ide_request,
    list_pending_ide_requests,
    summarize_pending_request,
    write_ide_handoff_bundle,
)


def fake_items():
    return [EvidenceItem("EVD-1", "CASE-1", "note", "manual", "Safe title", "Safe evidence text", privacy_level="local_only")]


def test_pending_outbox_requests_are_listed(tmp_path):
    write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-A")
    requests = list_pending_ide_requests(tmp_path)
    assert [r.request_id for r in requests] == ["REQ-A"]
    assert summarize_pending_request(requests[0])["response_json_exists"] is False


def test_latest_pending_request_is_selected_deterministically(tmp_path):
    a = write_ide_handoff_bundle("CASE-1", "old", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-A")
    b = write_ide_handoff_bundle("CASE-1", "new", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-B")
    ma = json.loads((a.bundle_dir / "manifest.json").read_text(encoding="utf-8")); ma["created_at"] = "2026-01-01T00:00:00"
    mb = json.loads((b.bundle_dir / "manifest.json").read_text(encoding="utf-8")); mb["created_at"] = "2026-01-02T00:00:00"
    (a.bundle_dir / "manifest.json").write_text(json.dumps(ma), encoding="utf-8")
    (b.bundle_dir / "manifest.json").write_text(json.dumps(mb), encoding="utf-8")
    assert get_latest_pending_ide_request(tmp_path).request_id == "REQ-B"


def test_inbox_response_detection_works(tmp_path):
    req = write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-INBOX")
    req.inbox_response_path.write_text("{}", encoding="utf-8")
    assert find_response_for_request("REQ-INBOX", tmp_path) == req.inbox_response_path
    listed = list_pending_ide_requests(tmp_path)[0]
    assert listed.response_exists is True


def test_malformed_request_folder_is_ignored_safely(tmp_path):
    bad = tmp_path / "outbox" / "BAD"
    bad.mkdir(parents=True)
    (bad / "manifest.json").write_text("not json", encoding="utf-8")
    write_ide_handoff_bundle("CASE-1", "question", "active_case_all", fake_items(), root=tmp_path, request_id="REQ-OK")
    assert [r.request_id for r in list_pending_ide_requests(tmp_path)] == ["REQ-OK"]
