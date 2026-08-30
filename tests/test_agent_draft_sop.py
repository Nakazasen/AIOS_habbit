from pathlib import Path
import pytest
from aios_habit.agent_draft_sop import (
    DRAFT_STATUS_APPROVED,
    DRAFT_STATUS_DRAFT,
    FactoryFileProtectionError,
    approve_draft_document,
    compose_draft_from_evidence,
    guard_factory_file_action,
    save_draft_document,
)
from aios_habit.workspace_chat_connector_guard import (
    connector_blocks_image_files,
)


def test_compose_draft_from_evidence_pack_includes_text_and_suspected_log():
    evidence_pack = {
        "evidence_items": [
            {
                "source_id": "sop-01",
                "source_type": "rag_text",
                "title": "SOP Căn chỉnh Bow Skew",
                "location_info": "tailieugoc/SOP_Bow_Skew.docx",
                "text": "Kiểm tra giới hạn Bow <= 25um trước khi nghiệm thu.",
                "provenance": "verified_text",
            },
            {
                "source_id": "line-events",
                "source_type": "line_log",
                "title": "Log điều tra (nghi ngờ)",
                "location_info": "line_events.sqlite",
                "text": "Sự kiện: 2026-08-30 08:00 | lsu_cam | mã ERR-104 | trạm CAM_1 | suspected",
                "provenance": "suspected",
            },
        ],
        "citations": [
            {
                "title": "SOP Căn chỉnh Bow Skew",
                "snippet": "Kiểm tra giới hạn Bow <= 25um",
                "location": "tailieugoc/SOP_Bow_Skew.docx",
            }
        ],
    }

    draft = compose_draft_from_evidence(
        evidence_pack=evidence_pack,
        doc_type="sop",
        title="Quy trình xử lý lỗi Bow Skew",
        target_station="CAM_1",
    )

    assert draft.status == DRAFT_STATUS_DRAFT
    assert "Quy trình xử lý lỗi Bow Skew" in draft.title
    assert "NHÁP (Chưa phê duyệt)" in draft.content_markdown
    assert "SOP Căn chỉnh Bow Skew" in draft.content_markdown
    assert "ERR-104" in draft.content_markdown
    assert "suspected" in draft.content_markdown
    assert len(draft.provenance_items) == 2


def test_factory_file_unapproved_write_fails_closed(tmp_path):
    out_file = tmp_path / "sop_draft.md"
    with pytest.raises(FactoryFileProtectionError) as exc_info:
        guard_factory_file_action("write", out_file, approved=False)
    assert "fail-closed" in str(exc_info.value) or "phê duyệt" in str(exc_info.value)


def test_factory_file_deletion_is_always_prohibited(tmp_path):
    target = tmp_path / "factory_log.csv"
    target.write_text("a,b,c\n1,2,3\n", encoding="utf-8")

    with pytest.raises(FactoryFileProtectionError) as exc_info:
        guard_factory_file_action("delete", target, approved=True)
    assert "Không được xóa file nhà máy" in str(exc_info.value)

    with pytest.raises(FactoryFileProtectionError) as exc_info_unapproved:
        guard_factory_file_action("delete", target, approved=False)
    assert "Không được xóa file nhà máy" in str(exc_info_unapproved.value)


def test_factory_file_approved_draft_write_and_lifecycle(tmp_path):
    evidence_pack = {
        "evidence_items": [
            {
                "source_id": "sop-02",
                "source_type": "rag_text",
                "title": "Tiêu chuẩn kiểm tra",
                "location_info": "tailieugoc/Tieuchuan.docx",
                "text": "Điện áp danh định 5V.",
                "provenance": "verified_text",
            }
        ]
    }
    draft = compose_draft_from_evidence(
        evidence_pack=evidence_pack,
        doc_type="report",
        title="Báo cáo kiểm tra điện áp",
    )
    assert draft.status == DRAFT_STATUS_DRAFT

    out_file = tmp_path / "drafts" / "report.md"

    # Cannot save unapproved draft
    with pytest.raises(FactoryFileProtectionError):
        save_draft_document(draft, out_file, approved=False)

    # Approve draft on Vietnamese UI
    approved_doc = approve_draft_document(
        draft,
        approver="Nguyễn Văn A - Kỹ sư trưởng",
        notes="Đã đối chiếu tiêu chuẩn",
    )
    assert approved_doc.status == DRAFT_STATUS_APPROVED
    assert approved_doc.approval_metadata["approver"] == "Nguyễn Văn A - Kỹ sư trưởng"

    # Write approved draft
    saved_path = save_draft_document(approved_doc, out_file, approved=True)
    assert Path(saved_path).is_file()
    saved_text = Path(saved_path).read_text(encoding="utf-8")
    assert "ĐÃ DUYỆT" in saved_text
    assert "Nguyễn Văn A - Kỹ sư trưởng" in saved_text

    # Cannot write directly into protected factory source directories
    protected_target = tmp_path / "tailieugoc" / "new.pdf"
    with pytest.raises(FactoryFileProtectionError):
        save_draft_document(approved_doc, protected_target, approved=True)


def test_factory_source_extensions_and_existing_files_are_never_overwritten(tmp_path):
    draft = compose_draft_from_evidence(evidence_pack={"evidence_items": []})
    approved_doc = approve_draft_document(draft, approver="Máy duyệt thử nghiệm")

    raw_log_target = tmp_path / "copied_log.csv"
    with pytest.raises(FactoryFileProtectionError):
        save_draft_document(approved_doc, raw_log_target, approved=True)

    existing_draft = tmp_path / "drafts" / "existing.md"
    existing_draft.parent.mkdir(parents=True)
    existing_draft.write_text("Nội dung phải được giữ nguyên", encoding="utf-8")
    with pytest.raises(FactoryFileProtectionError):
        save_draft_document(approved_doc, existing_draft, approved=True)
    assert existing_draft.read_text(encoding="utf-8") == "Nội dung phải được giữ nguyên"


def test_workspace_ui_exposes_explicit_evidence_draft_approval():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "def _render_agent_draft_from_evidence" in app_source
    assert "compose_draft_from_evidence(" in app_source
    assert "approve_draft_document(" in app_source
    assert "agent_draft_approve_btn" in app_source
    assert "st.download_button(" in app_source


def test_gemini_and_router_still_block_images_gate_c():
    assert connector_blocks_image_files("gemini_web") is True
    assert connector_blocks_image_files("nakazasen_router") is True
    assert connector_blocks_image_files("cagent_api") is False
