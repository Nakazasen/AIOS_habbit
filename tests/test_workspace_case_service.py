from __future__ import annotations

import sqlite3

import pytest

from aios_habit.evidence_trace import build_evidence_trace_from_citations
from aios_habit.workspace_case_models import CaseFilter
from aios_habit.workspace_case_authorization import RoleGrant
from aios_habit.workspace_case_service import CaseValidationError, WorkspaceCaseService
from aios_habit.workspace_case_repository import WorkspaceCaseRepository


def _trace(*, conversation_id: str = "CONV-CASE-1", with_citation: bool = True):
    citation = "[E1]" if with_citation else ""
    return build_evidence_trace_from_citations(
        query="CÂU_HỎI_THÔ_KHÔNG_ĐƯỢC_COPY",
        answer_text=f"CÂU_TRẢ_LỜI_THÔ_KHÔNG_ĐƯỢC_COPY {citation}".strip(),
        evidence_items=[
            {
                "id": "E1",
                "citation_id": "[E1]",
                "title": "Quy trình thử nghiệm",
                "text": "EXCERPT_BÍ_MẬT_KHÔNG_ĐƯỢC_COPY",
                "source_path": "docs/process.pdf",
            }
        ],
        allowed_source_ids=["E1"],
        conversation_id=conversation_id,
        assistant_message_id="MSG-CASE-1",
    )


def test_service_creates_case_from_valid_trace_without_copying_raw_chat_or_excerpt(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    service = WorkspaceCaseService(store=store)
    trace = _trace()

    result = service.create_case_from_trace(trace, expected_conversation_id="CONV-CASE-1")

    persisted = store.load_case(result.case_id)
    assert persisted is not None
    assert persisted.conversation_id == "CONV-CASE-1"
    assert persisted.trace_id == trace.trace_id
    assert result.evidence_count == 1
    references = store.list_evidence_references(result.case_id)
    assert references[0].source_locator == "docs/process.pdf"
    assert references[0].source_title == "Quy trình thử nghiệm"

    with sqlite3.connect(store.database_path) as connection:
        serialized = "\n".join(
            str(row)
            for table in ("cases", "case_evidence_references", "case_audit_events")
            for row in connection.execute(f"SELECT * FROM {table}")
        )
    assert "CÂU_HỎI_THÔ_KHÔNG_ĐƯỢC_COPY" not in serialized
    assert "CÂU_TRẢ_LỜI_THÔ_KHÔNG_ĐƯỢC_COPY" not in serialized
    assert "EXCERPT_BÍ_MẬT_KHÔNG_ĐƯỢC_COPY" not in serialized


def test_service_refuses_trace_without_cited_evidence(tmp_path):
    service = WorkspaceCaseService(store=WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite"))

    with pytest.raises(CaseValidationError, match="bằng chứng"):
        service.create_case_from_trace(_trace(with_citation=False), expected_conversation_id="CONV-CASE-1")


def test_service_refuses_trace_for_another_conversation(tmp_path):
    service = WorkspaceCaseService(store=WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite"))

    with pytest.raises(CaseValidationError, match="cuộc trò chuyện"):
        service.create_case_from_trace(_trace(conversation_id="CONV-OTHER"), expected_conversation_id="CONV-CASE-1")


def test_service_refuses_any_trace_node_not_marked_local_only(tmp_path):
    service = WorkspaceCaseService(store=WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite"))
    trace = _trace()
    trace.nodes[0].privacy_label = "cloud_safe"

    with pytest.raises(CaseValidationError, match="nhãn dữ liệu"):
        service.create_case_from_trace(trace, expected_conversation_id="CONV-CASE-1")


def test_service_creates_only_one_case_for_the_same_trace(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    service = WorkspaceCaseService(store=store)
    trace = _trace()

    first = service.create_case_from_trace(trace, expected_conversation_id="CONV-CASE-1")
    second = service.create_case_from_trace(trace, expected_conversation_id="CONV-CASE-1")

    assert second.case_id == first.case_id
    with sqlite3.connect(store.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 1


def test_service_lists_filters_and_reads_case_detail_after_restart(tmp_path):
    database_path = tmp_path / "workspace_cases.sqlite"
    first_service = WorkspaceCaseService(store=WorkspaceCaseRepository(database_path))
    result = first_service.create_case_from_trace(_trace(), expected_conversation_id="CONV-CASE-1")

    restarted = WorkspaceCaseService(store=WorkspaceCaseRepository(database_path))
    cases = restarted.list_cases(CaseFilter(status="draft"))
    detail = restarted.get_case_detail(result.case_id)

    assert [case.case_id for case in cases] == [result.case_id]
    assert detail.case.case_id == result.case_id
    assert len(detail.evidence) == 1
    assert detail.activities[-1].event_type == "case_created"


def test_service_transition_is_optimistic_and_stale_write_adds_no_activity(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    service = WorkspaceCaseService(store=store)
    result = service.create_case_from_trace(_trace(), expected_conversation_id="CONV-CASE-1")
    original = store.load_case(result.case_id)
    assert original is not None

    updated = service.transition_case(result.case_id, expected_version=original.version, new_status="triaged", rationale="Đã phân loại")
    activity_count = len(store.list_activities(result.case_id))
    with pytest.raises(CaseValidationError, match="CASE_VERSION_CONFLICT"):
        service.transition_case(result.case_id, expected_version=original.version, new_status="in_progress", rationale="Ghi cũ")

    assert updated.status == "triaged"
    assert updated.version == original.version + 1
    assert len(store.list_activities(result.case_id)) == activity_count


def test_service_requires_review_flow_before_resolving_case(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    service = WorkspaceCaseService(store=store)
    result = service.create_case_from_trace(_trace(), expected_conversation_id="CONV-CASE-1")
    case = store.load_case(result.case_id)
    assert case is not None

    with pytest.raises(CaseValidationError, match="CASE_RESOLUTION_REVIEW_REQUIRED"):
        service.transition_case(
            result.case_id,
            expected_version=case.version,
            new_status="resolved",
            rationale="Đề nghị kết luận",
        )


def test_service_assigns_only_investigator_with_active_matching_scope(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    service = WorkspaceCaseService(store=store)
    result = service.create_case_from_trace(_trace(), expected_conversation_id="CONV-CASE-1")
    case = store.load_case(result.case_id)
    assert case is not None

    with pytest.raises(CaseValidationError, match="CASE_ASSIGNEE_NOT_AUTHORIZED"):
        service.assign_case(result.case_id, expected_version=case.version, assignee_id="worker-1")

    store.replace_role_grants(
        "worker-1",
        [
            RoleGrant(
                "WORKER-1",
                "worker-1",
                "investigator",
                case.scope,
                "2000-01-01T00:00:00+00:00",
                "9999-12-31T23:59:59+00:00",
            )
        ],
    )
    updated = service.assign_case(result.case_id, expected_version=case.version, assignee_id="worker-1")
    assert updated.assignee_id == "worker-1"


def test_service_attaches_only_scrubbed_evidence_metadata(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    service = WorkspaceCaseService(store=store)
    trace = _trace()
    result = service.create_case_from_trace(trace, expected_conversation_id="CONV-CASE-1")
    case = store.load_case(result.case_id)
    assert case is not None

    updated = service.attach_evidence_reference(
        result.case_id,
        expected_version=case.version,
        source_store="library",
        source_id=r"C:\Users\Admin\secret\SOP-1",
        source_version="../v1",
        locator=r"C:\Users\Admin\secret\sop.pdf",
        title="SOP công đoạn",
        content_digest="a" * 64,
        provenance_status="approved",
    )

    references = store.list_evidence_references(result.case_id)
    assert updated.version == case.version + 1
    assert references[-1].source_locator.startswith("nguon:")
    assert r"C:\Users\Admin" not in references[-1].evidence_node_id
    assert "../v1" not in references[-1].evidence_node_id
    assert updated.evidence_digest != case.evidence_digest
    with sqlite3.connect(store.database_path) as connection:
        serialized = "\n".join(str(row) for row in connection.execute("SELECT * FROM case_evidence_references"))
    assert r"C:\Users\Admin" not in serialized
    assert store.verify_activity_chain(result.case_id) is True

    repeated = service.create_case_from_trace(trace, expected_conversation_id="CONV-CASE-1")
    assert repeated.case_id == result.case_id


def test_service_reports_missing_trace_without_recreating_content(tmp_path):
    store = WorkspaceCaseRepository(tmp_path / "workspace_cases.sqlite")
    service = WorkspaceCaseService(store=store, trace_loader=lambda _trace_id: None)
    result = service.create_case_from_trace(_trace(), expected_conversation_id="CONV-CASE-1")

    resolution = service.open_trace(result.case_id)

    assert resolution.status == "missing"
    assert resolution.trace is None
