from __future__ import annotations

import sqlite3

import pytest

from aios_habit.workspace_case_models import CaseChecklistItem, CaseEvidenceReference, CaseRecord
from aios_habit.workspace_case_repository import WorkspaceCaseRepository, WorkspaceCaseRepositoryError


def _case() -> CaseRecord:
    return CaseRecord.new(
        conversation_id="CONV-CASE-1",
        assistant_message_id="MSG-CASE-1",
        trace_id="trc-case-1",
        evidence_digest="evidence-digest-1",
    )


def _reference(case_id: str, reference_id: str = "REF-CASE-1") -> CaseEvidenceReference:
    return CaseEvidenceReference(
        reference_id=reference_id,
        case_id=case_id,
        trace_id="trc-case-1",
        evidence_node_id="src-case-1",
        citation_id="[E1]",
        source_locator="docs/process.pdf",
        source_title="Quy trình đã duyệt",
        reference_digest="reference-digest-1",
    )


def test_create_case_commits_references_and_audit_event_atomically(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    case = _case()
    reference = _reference(case.case_id)

    result = store.create_case_with_evidence(case, [reference])

    assert result.case_id == case.case_id
    assert result.evidence_count == 1
    persisted = store.load_case(case.case_id)
    assert persisted is not None
    assert persisted.case_id == case.case_id
    assert persisted.evidence_digest == case.evidence_digest
    assert persisted.activity_head_digest
    assert store.verify_activity_chain(case.case_id) is True
    assert store.list_evidence_references(case.case_id) == [reference]
    events = store.list_audit_events(case.case_id)
    assert len(events) == 1
    assert events[0].event_type == "case_created"


def test_failed_reference_insert_rolls_back_case_and_audit_event(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    case = _case()
    duplicate_reference_id = "REF-DUPLICATE"

    with pytest.raises(WorkspaceCaseRepositoryError):
        store.create_case_with_evidence(
            case,
            [
                _reference(case.case_id, duplicate_reference_id),
                _reference(case.case_id, duplicate_reference_id),
            ],
        )

    assert store.load_case(case.case_id) is None
    assert store.list_evidence_references(case.case_id) == []
    assert store.list_audit_events(case.case_id) == []


def test_case_database_has_only_case_metadata_tables_not_library_tables(tmp_path):
    database_path = tmp_path / "workspace_cases.sqlite"
    store = WorkspaceCaseRepository(database_path)
    store.initialize()

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }

    assert {"cases", "case_evidence_references", "case_audit_events"} <= table_names
    assert "chunks" not in table_names
    assert "library" not in table_names


def test_repository_closes_connections_so_database_and_wal_files_can_be_removed(tmp_path):
    database_path = tmp_path / "workspace_cases.sqlite"
    store = WorkspaceCaseRepository(database_path)
    case = _case()

    store.create_case_with_evidence(case, [_reference(case.case_id)])
    persisted = store.load_case(case.case_id)
    assert persisted is not None and persisted.case_id == case.case_id
    for path in (database_path, database_path.with_name(f"{database_path.name}-wal"), database_path.with_name(f"{database_path.name}-shm")):
        if path.exists():
            path.unlink()
    assert not database_path.exists()


def test_same_trace_identity_with_changed_evidence_digest_fails_closed(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    case = _case()
    store.create_case_with_evidence(case, [_reference(case.case_id)])
    changed = CaseRecord.new(
        conversation_id=case.conversation_id,
        assistant_message_id=case.assistant_message_id,
        trace_id=case.trace_id,
        evidence_digest="changed-digest",
    )

    with pytest.raises(WorkspaceCaseRepositoryError, match="CASE_TRACE_EVIDENCE_CONFLICT"):
        store.create_case_with_evidence(changed, [_reference(changed.case_id, "REF-CHANGED")])


def test_activity_chain_detects_tampered_last_event(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    case = _case()
    store.create_case_with_evidence(case, [_reference(case.case_id)])
    with sqlite3.connect(store.database_path) as connection:
        connection.execute("UPDATE case_activities SET payload_digest = 'tampered' WHERE case_id = ?", (case.case_id,))
        connection.commit()

    assert store.verify_activity_chain(case.case_id) is False

    with pytest.raises(WorkspaceCaseRepositoryError, match="CASE_ACTIVITY_CHAIN_INVALID"):
        store.add_checklist_item(
            CaseChecklistItem("ITEM-1", case.case_id, "Bổ sung ảnh"),
            expected_version=case.version,
            actor_id=case.created_by,
        )
