from __future__ import annotations

import sqlite3
from pathlib import Path
import pytest

from aios_habit.line_investigation import (
    LineInvestigationScope,
    build_investigation_pack,
)
from aios_habit.line_log_parser import _ensure_schema
from aios_habit.workspace_case_authorization import trusted_local_actor
from aios_habit.workspace_case_models import (
    CASE_PRIVACY_LOCAL_ONLY,
    CASE_PROVENANCE_UNKNOWN,
    CASE_SCOPE_GENERAL,
    CaseEvidenceReference,
    CaseRecord,
)
from aios_habit.workspace_case_repository import WorkspaceCaseRepository
from aios_habit.workspace_case_service import CaseValidationError, WorkspaceCaseService


def _setup_sample_line_events_db(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_schema(conn)
        # Sample events: Jam and C-call
        events = [
            ("EV-001", "jam_log.csv", "jam", "2026-09-06T08:01:00", "STATION_A", "JAM_01", "SN_101", 1.5, "suspected", "2026-09-06T08:00:00Z"),
            ("EV-002", "jam_log.csv", "jam", "2026-09-06T08:05:00", "STATION_A", "JAM_01", "", 2.0, "suspected", "2026-09-06T08:00:00Z"),
            ("EV-003", "jam_log.csv", "jam", "2026-09-06T08:10:00", "STATION_A", "JAM_01", "SN_103", 1.8, "suspected", "2026-09-06T08:00:00Z"),
            ("EV-004", "ccall_log.csv", "c_call", "2026-09-06T09:00:00", "STATION_B", "CCALL_09", "SN_201", None, "suspected", "2026-09-06T09:00:00Z"),
            ("EV-005", "jam_log.csv", "jam", "2026-09-06T10:15:00", "STATION_C", "JAM_02", "SN_301", 3.2, "suspected", "2026-09-06T10:00:00Z"),
        ]
        conn.executemany(
            """
            INSERT OR IGNORE INTO line_events (
                event_id, source_name, dialect, occurred_at, station, code,
                serial, duration_s, provenance, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            events,
        )
        conn.commit()
    finally:
        conn.close()


def test_line_investigation_timeline(tmp_path: Path) -> None:
    db_path = tmp_path / "line_events.sqlite"
    _setup_sample_line_events_db(db_path)

    # 1. Empty scope must return empty pack (no events, no hallucinated defaults)
    empty_scope = LineInvestigationScope()
    pack_empty = build_investigation_pack(db_path, empty_scope)
    assert pack_empty.total_matched == 0
    assert len(pack_empty.events) == 0
    assert len(pack_empty.timeline) == 0

    # 2. Scope with non-matching criteria must return empty (NEVER falls back to recent 5 events)
    non_matching_scope = LineInvestigationScope(station="STATION_XYZ", code="UNKNOWN_CODE")
    pack_non_match = build_investigation_pack(db_path, non_matching_scope)
    assert pack_non_match.total_matched == 0
    assert len(pack_non_match.events) == 0

    # 3. Scope matching STATION_A and JAM_01 returns chronological timeline
    scope = LineInvestigationScope(station="STATION_A", code="JAM_01")
    pack = build_investigation_pack(db_path, scope)
    assert pack.total_matched == 3
    assert len(pack.events) == 3
    assert len(pack.timeline) == 3

    # Verify chronological ordering
    timestamps = [e.occurred_at for e in pack.events]
    assert timestamps == sorted(timestamps)

    # Verify all events start as suspected
    for ev in pack.events:
        assert ev.provenance == "suspected"

    for item in pack.timeline:
        assert item["Trạng thái"] == "Nghi ngờ"
        assert item["Trạm / Máy"] == "STATION_A"
        assert item["Mã lỗi / Cảnh báo"] == "JAM_01"


def test_line_investigation_repeated_patterns_and_missing_clues(tmp_path: Path) -> None:
    db_path = tmp_path / "line_events.sqlite"
    _setup_sample_line_events_db(db_path)

    # Query for JAM_01 across line
    scope = LineInvestigationScope(code="JAM_01")
    pack = build_investigation_pack(db_path, scope)

    # Repeated pattern should identify JAM_01 appearing 3 times
    assert len(pack.repeated_patterns) == 1
    pattern = pack.repeated_patterns[0]
    assert pattern.key == "JAM_01"
    assert pattern.count == 3
    assert "lặp lại 3 lần" in pattern.description_vi

    # Missing clues should identify that EV-002 had an empty serial
    missing_fields = {c.field_name for c in pack.missing_clues}
    assert "serial" in missing_fields


def test_clue_relevance_review_contract(tmp_path: Path) -> None:
    db_path = tmp_path / "workspace_cases.sqlite"
    repo = WorkspaceCaseRepository(db_path)
    service = WorkspaceCaseService(repo, actor_context=trusted_local_actor())

    case_id = "CASE-US4-001"
    case = CaseRecord(
        case_id=case_id,
        conversation_id="conv-us4-1",
        assistant_message_id="msg-us4-1",
        trace_id="trace-us4-1",
        evidence_digest="c" * 64,
        title="Hồ sơ điều tra kẹt giấy dây chuyền",
        created_by="local_admin",
        owner_id="local_admin",
        scope=CASE_SCOPE_GENERAL,
    )
    ref = CaseEvidenceReference(
        reference_id="REF-US4-INITIAL",
        case_id=case_id,
        trace_id="trace-us4-1",
        evidence_node_id="library:sop-jam:v1",
        citation_id="[1]",
        source_locator="docs/jam_sop.pdf",
        source_title="SOP xử lý kẹt giấy",
        reference_digest="d" * 64,
        provenance_status=CASE_PROVENANCE_UNKNOWN,
        privacy_label=CASE_PRIVACY_LOCAL_ONLY,
    )
    repo.create_case_with_evidence(case, [ref])

    # Attach line event clue to case (initially suspected)
    case_updated = service.attach_line_investigation_clue(
        case_id,
        expected_version=1,
        event_id="EV-001",
        station="STATION_A",
        code="JAM_01",
        occurred_at="2026-09-06T08:01:00",
        dialect="jam",
        relevance="suspected",
    )
    assert case_updated.version == 2

    # Check that clue is present with suspected provenance
    detail = service.get_case_detail(case_id)
    clue_ref = next(r for r in detail.evidence if r.evidence_node_id.startswith("line_events:"))
    assert clue_ref.provenance_status == "suspected"

    # Expert confirms relevance
    case_confirmed = service.review_clue_relevance(
        case_id,
        clue_ref.reference_id,
        expected_version=2,
        relevance="confirmed",
        note="Xác nhận sự kiện kẹt giấy tại trạm A trùng thời điểm xảy ra lỗi.",
    )
    assert case_confirmed.version == 3

    detail_after = service.get_case_detail(case_id)
    clue_after = next(r for r in detail_after.evidence if r.reference_id == clue_ref.reference_id)
    assert clue_after.provenance_status == "approved"

    # Check activity chain integrity
    assert repo.verify_activity_chain(case_id) is True

    # Test invalid relevance value raises error
    with pytest.raises(CaseValidationError, match="CLUE_RELEVANCE_INVALID"):
        service.review_clue_relevance(
            case_id,
            clue_ref.reference_id,
            expected_version=3,
            relevance="invalid_status",
        )
