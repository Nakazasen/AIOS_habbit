from __future__ import annotations

from pathlib import Path
import hashlib
import pytest

from aios_habit.agent_draft_sop import (
    DRAFT_STATUS_APPROVED,
    DRAFT_STATUS_DRAFT,
    FactoryFileProtectionError,
    compose_draft_from_evidence,
    save_draft_document,
)
from aios_habit.workspace_case_authorization import ActorContext, trusted_local_actor
from aios_habit.workspace_case_migrations import migrate_store
from aios_habit.workspace_case_models import CaseEvidenceReference, CaseRecord
from aios_habit.workspace_case_repository import WorkspaceCaseRepository
from aios_habit.workspace_case_service import CaseValidationError, WorkspaceCaseService


def _init_service(tmp_path: Path, actor_id: str = "local_admin") -> tuple[WorkspaceCaseService, WorkspaceCaseRepository]:
    db_path = tmp_path / "workspace_cases.sqlite"
    migrate_store(db_path)
    repo = WorkspaceCaseRepository(db_path)
    actor = ActorContext(actor_id)
    service = WorkspaceCaseService(repo, actor_context=actor)
    return service, repo


def _create_case_with_evidence(service: WorkspaceCaseService, repo: WorkspaceCaseRepository) -> str:
    rag_digest = hashlib.sha256(b"SOP-SENSOR-01-CONTENT").hexdigest()
    case = CaseRecord.new(
        conversation_id="CONV-SOP-1",
        assistant_message_id="MSG-SOP-1",
        trace_id="TR-SOP-1",
        evidence_digest=rag_digest,
        created_by="local_admin",
        scope="general",
    )
    ref = CaseEvidenceReference(
        reference_id="CASE-REF-SOP-01",
        case_id=case.case_id,
        trace_id="TR-SOP-1",
        evidence_node_id="line_events:EV-101:CAM_1",
        citation_id="[E1]",
        source_locator="docs/SOP_Sensor.md",
        source_title="Tiêu chuẩn kiểm tra Sensor",
        reference_digest=rag_digest,
        provenance_status="approved",
        privacy_label="local_only",
    )
    repo.create_case_with_evidence(case, [ref])
    case_id = case.case_id

    # Attach verified RAG reference
    service.attach_evidence_reference(
        case_id,
        expected_version=1,
        source_store="library",
        source_id="SOP-SENSOR-01",
        source_version="v1",
        locator="docs/SOP_Sensor.md",
        title="Tiêu chuẩn kiểm tra Sensor",
        content_digest=rag_digest,
        provenance_status="approved",
    )

    # Attach suspected line event clue
    service.attach_line_investigation_clue(
        case_id,
        expected_version=2,
        event_id="EV-101",
        station="CAM_1",
        code="ERR_SENSOR_TIMEOUT",
        occurred_at="2026-09-06T08:30:00",
        dialect="jam",
        relevance="suspected",
    )
    return case_id


def test_report_sop_drafting(tmp_path):
    service, repo = _init_service(tmp_path)
    case_id = _create_case_with_evidence(service, repo)

    # 1. Draft SOP
    sop_artifact = service.draft_case_artifact(
        case_id,
        artifact_type="sop",
        title="Quy trình hiệu chuẩn Sensor CAM_1",
        conclusions_or_grounds="Cần vệ sinh đầu dò quang học trước ca làm việc.",
    )
    assert sop_artifact.status == DRAFT_STATUS_DRAFT
    assert sop_artifact.artifact_type == "sop"
    assert sop_artifact.version == 1
    assert case_id in sop_artifact.content_markdown
    assert "v1" in sop_artifact.content_markdown
    assert "ERR_SENSOR_TIMEOUT" in sop_artifact.content_markdown
    assert "Tiêu chuẩn kiểm tra Sensor" in sop_artifact.content_markdown
    assert "suspected" in sop_artifact.content_markdown

    # 2. Draft Investigation Report
    report_artifact = service.draft_case_artifact(
        case_id,
        artifact_type="report",
        title="Báo cáo điều tra sự cố Sensor CAM_1",
    )
    assert report_artifact.status == DRAFT_STATUS_DRAFT
    assert report_artifact.artifact_type == "report"
    assert report_artifact.version == 1
    assert "BÁO CÁO ĐIỀU TRA" in report_artifact.content_markdown.upper()

    # 3. Reject invalid artifact type
    with pytest.raises(CaseValidationError, match="ARTIFACT_TYPE_INVALID"):
        service.draft_case_artifact(case_id, artifact_type="unsupported_type", title="Test")

    # 4. Reject empty title
    with pytest.raises(CaseValidationError, match="ARTIFACT_TITLE_REQUIRED"):
        service.draft_case_artifact(case_id, artifact_type="sop", title="")

    # 5. Reject drafting on case with no valid evidence
    unverified_case = CaseRecord.new(
        conversation_id="CONV-EMPTY",
        assistant_message_id="MSG-EMPTY",
        trace_id="TR-EMPTY",
        evidence_digest="c" * 64,
        created_by="local_admin",
        scope="general",
    )
    unverified_ref = CaseEvidenceReference(
        reference_id="CASE-REF-REJECTED",
        case_id=unverified_case.case_id,
        trace_id="TR-EMPTY",
        evidence_node_id="line_events:EV-999:NONE",
        citation_id="[E99]",
        source_locator="docs/dummy.md",
        source_title="Tài liệu không xác thực",
        reference_digest="d" * 64,
        provenance_status="unknown",
        privacy_label="local_only",
    )
    repo.create_case_with_evidence(unverified_case, [unverified_ref])
    with pytest.raises(CaseValidationError, match="ARTIFACT_INSUFFICIENT_EVIDENCE"):
        service.draft_case_artifact(unverified_case.case_id, artifact_type="sop", title="SOP Rỗng")


def test_artifact_versioning_and_diff(tmp_path):
    service, repo = _init_service(tmp_path)
    case_id = _create_case_with_evidence(service, repo)

    art = service.draft_case_artifact(
        case_id,
        artifact_type="sop",
        title="Quy trình bảo dưỡng CAM_1",
    )
    assert art.version == 1

    # Update draft content
    new_content = art.content_markdown + "\n\n## 6. Ghi chú bổ sung\nThực hiện kiểm tra kép."
    updated = service.update_case_artifact(
        art.artifact_id,
        expected_version=1,
        content_markdown=new_content,
        title="Quy trình bảo dưỡng CAM_1 (Đã chỉnh sửa)",
    )
    assert updated.version == 2
    assert updated.title == "Quy trình bảo dưỡng CAM_1 (Đã chỉnh sửa)"
    assert "Thực hiện kiểm tra kép." in updated.content_markdown
    assert updated.status == DRAFT_STATUS_DRAFT

    # Verify optimistic lock conflict
    with pytest.raises(CaseValidationError, match="CONCURRENT_UPDATE_CONFLICT"):
        service.update_case_artifact(
            art.artifact_id,
            expected_version=1,
            content_markdown="Content conflict",
        )

    # Verify activity chain is valid
    assert repo.verify_activity_chain(case_id) is True


def test_artifact_approval_and_export(tmp_path):
    service, repo = _init_service(tmp_path)
    case_id = _create_case_with_evidence(service, repo)

    art = service.draft_case_artifact(
        case_id,
        artifact_type="report",
        title="Báo cáo kỹ thuật tổng kết",
    )

    # 1. Unapproved export is strictly forbidden (fail-closed)
    export_dir = tmp_path / "exports"
    with pytest.raises(CaseValidationError, match="UNAPPROVED_ARTIFACT_EXPORT_FORBIDDEN"):
        service.export_case_artifact(art.artifact_id, output_root=export_dir)

    # 2. Operator without permission cannot approve
    operator_actor = ActorContext("operator_user")
    operator_service = WorkspaceCaseService(repo, actor_context=operator_actor)
    with pytest.raises(Exception):
        operator_service.approve_case_artifact(art.artifact_id, expected_version=1)

    # 3. Quality manager approves artifact
    approved = service.approve_case_artifact(
        art.artifact_id,
        expected_version=1,
        notes="Phê duyệt ban hành báo cáo kỹ thuật.",
    )
    assert approved.status == DRAFT_STATUS_APPROVED
    assert approved.version == 2
    assert "ĐÃ DUYỆT" in approved.content_markdown
    assert approved.approved_by == service.actor.actor_id

    # 4. Approved artifact cannot be directly modified without re-drafting
    with pytest.raises(CaseValidationError, match="APPROVED_ARTIFACT_IMMUTABLE"):
        service.update_case_artifact(
            art.artifact_id,
            expected_version=2,
            content_markdown="Sửa đè nội dung đã duyệt",
        )

    # 5. Export approved artifact to configured safe output_root
    exported_art, exported_file = service.export_case_artifact(
        art.artifact_id,
        output_root=export_dir,
        relative_filename="report_cam1.md",
    )
    assert exported_file.exists()
    assert exported_file.parent == export_dir.resolve()
    saved_text = exported_file.read_text(encoding="utf-8")
    assert "ĐÃ DUYỆT" in saved_text
    assert exported_art.exported_path == str(exported_file)

    # 6. Re-export creates versioned file without overwriting
    _, second_file = service.export_case_artifact(
        art.artifact_id,
        output_root=export_dir,
        relative_filename="report_cam1.md",
    )
    assert second_file.exists()
    assert second_file != exported_file
    assert "v2" in second_file.name

    # 7. Output root escape attempts are blocked
    with pytest.raises(FactoryFileProtectionError):
        save_draft_document(
            draft := compose_draft_from_evidence(
                evidence_pack={"evidence_items": [{"title": "X", "text": "Y"}]},
            ),
            tmp_path / "outside" / "hack.md",
            approved=True,
            output_root=tmp_path / "safe_zone",
        )

    # 8. Activity chain is valid
    assert repo.verify_activity_chain(case_id) is True
