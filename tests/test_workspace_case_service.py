from __future__ import annotations

import sqlite3

import pytest

from aios_habit.evidence_trace import build_evidence_trace_from_citations
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
