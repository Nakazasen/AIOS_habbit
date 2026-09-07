from __future__ import annotations

import ast
from pathlib import Path

from aios_habit.workspace_case_models import (
    CaseActivity,
    CaseArtifactRecord,
    CaseChecklistItem,
    CaseDetail,
    CaseEvidenceReference,
    CaseLesson,
    CaseRecord,
    TraceResolution,
)
from aios_habit.workspace_case_service import CaseValidationError
from aios_habit.workspace_case_ui import case_detail_sections, case_list_rows, safe_case_error_message


def _case() -> CaseRecord:
    return CaseRecord.new(
        conversation_id="CONV-1",
        assistant_message_id="MSG-1",
        trace_id="trace-1",
        evidence_digest="digest-1",
    )


def test_case_list_and_detail_presenter_use_safe_vietnamese_metadata():
    case = _case()
    rows = case_list_rows([case])
    sections = case_detail_sections(
        CaseDetail(case=case, evidence=(), activities=(), checklist=()),
        TraceResolution(status="missing", trace_id=case.trace_id),
    )

    assert rows == [{"Mã hồ sơ": case.case_id, "Loại": "Điều tra", "Trạng thái": "Nháp", "Ưu tiên": "Bình thường", "Người phụ trách": "Chưa giao"}]
    assert sections["trace_status"] == "Thiếu dấu vết bằng chứng gốc"
    assert "Câu hỏi" not in str(sections)
    assert "Câu trả lời" not in str(sections)
    assert "Provenance" not in str(sections)
    assert "unknown" not in str(sections)


def test_workspace_chat_case_ui_is_wired_and_simulation_copy_is_removed():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    i18n_source = Path("src/aios_habit/i18n.py").read_text(encoding="utf-8")

    assert "render_case_workspace" in app_source
    assert "case_workspace" in app_source
    assert '"case_workspace": "Hồ sơ vụ việc"' in i18n_source
    assert "chế độ mô phỏng" not in i18n_source
    assert "シミュレーションモード" not in i18n_source
    assert "模拟模式" not in i18n_source


def test_internal_case_error_codes_never_reach_the_user_interface():
    message = safe_case_error_message(CaseValidationError("CASE_VERSION_CONFLICT"))

    assert message == "Hồ sơ đã được cập nhật ở nơi khác. Hãy tải lại rồi thử lại."
    assert "CASE_" not in message
    assert "Traceback" not in message

    digest_message = safe_case_error_message(CaseValidationError("CASE_EVIDENCE_DIGEST_INVALID"))
    assert digest_message == "Mã kiểm tra nội dung phải là chuỗi SHA-256 hợp lệ."
    assert "CASE_" not in digest_message


def test_timeline_and_checklist_never_show_internal_english_values():
    case = _case()
    activity = CaseActivity.new(
        event_id="ACT-1",
        case_id=case.case_id,
        event_type="case_created",
        actor_id="local_admin",
        payload_digest="digest",
        previous_event_digest="",
        occurred_at=case.created_at,
    )
    checklist_item = CaseChecklistItem(
        item_id="CHK-1",
        case_id=case.case_id,
        description="Xác minh mã lỗi",
        status="open",
        created_at=case.created_at,
    )

    sections = case_detail_sections(
        CaseDetail(case=case, evidence=(), activities=(activity,), checklist=(checklist_item,)),
        TraceResolution(status="missing", trace_id=case.trace_id),
    )

    rendered = str(sections)
    assert "Tạo hồ sơ" in rendered
    assert "Quản trị viên cục bộ" in rendered
    assert "Chưa hoàn thành" in rendered
    assert "case_created" not in rendered
    assert "local_admin" not in rendered
    assert "'open'" not in rendered


def test_detail_hides_unknown_actor_and_raw_locator_values():
    case = _case()
    activity = CaseActivity.new(
        case_id=case.case_id,
        event_type="unexpected_internal_event",
        actor_id="DOMAIN\\secret-user",
        payload_digest="digest",
    )
    reference = CaseEvidenceReference(
        reference_id="REF-1",
        case_id=case.case_id,
        trace_id=case.trace_id,
        evidence_node_id="SRC-1",
        citation_id="[E1]",
        source_locator="private/folder/document.pdf",
        source_title="Quy trình",
        reference_digest="digest",
    )

    sections = case_detail_sections(
        CaseDetail(case=case, evidence=(reference,), activities=(activity,), checklist=()),
        TraceResolution(status="missing", trace_id=case.trace_id),
    )
    rendered = str(sections)
    assert "Người dùng nội bộ" in rendered
    assert "Hoạt động hồ sơ" in rendered
    assert "Vị trí đã được lưu trong hồ sơ" in rendered
    assert "secret-user" not in rendered
    assert "private/folder" not in rendered


def test_case_list_and_detail_presenter_japanese():
    case = _case()
    rows = case_list_rows([case], locale="ja")
    sections = case_detail_sections(
        CaseDetail(case=case, evidence=(), activities=(), checklist=()),
        TraceResolution(status="missing", trace_id=case.trace_id),
        locale="ja",
    )

    assert rows == [{"ケースID": case.case_id, "種別": "調査", "ステータス": "下書き", "優先度": "通常", "担当者": "未割り当て"}]
    assert sections["status"] == "下書き"
    assert sections["assignee"] == "未割り当て"
    assert sections["trace_status"] == "元の証拠トレースが不足しています"


def test_case_list_and_detail_presenter_chinese():
    case = _case()
    rows = case_list_rows([case], locale="zh-CN")
    sections = case_detail_sections(
        CaseDetail(case=case, evidence=(), activities=(), checklist=()),
        TraceResolution(status="missing", trace_id=case.trace_id),
        locale="zh-CN",
    )

    assert rows == [{"案例编号": case.case_id, "类型": "调查", "状态": "草稿", "优先级": "正常", "负责人": "未分配"}]
    assert sections["status"] == "草稿"
    assert sections["assignee"] == "未分配"
    assert sections["trace_status"] == "缺失原始证据追踪记录"


def test_case_error_messages_multilingual():
    err = CaseValidationError("CASE_VERSION_CONFLICT")
    assert safe_case_error_message(err, locale="vi") == "Hồ sơ đã được cập nhật ở nơi khác. Hãy tải lại rồi thử lại."
    assert safe_case_error_message(err, locale="ja") == "ケースは別の場所で更新されました。再読み込みしてから再試行してください。"
    assert safe_case_error_message(err, locale="zh-CN") == "案例已在其他位置更新。请刷新后重试。"


def test_all_supported_workspace_modules_forbid_legacy_imports():
    supported = sorted(Path("src/aios_habit").glob("workspace_chat*.py")) + sorted(
        Path("src/aios_habit").glob("workspace_case*.py")
    )
    assert supported
    for path in supported:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        assert not any(name.endswith("studio") or "case_cockpit" in name for name in imported), path


def test_expert_review_ui_sections_and_error_handling():
    from aios_habit.workspace_case_models import ExpertRequest, ExpertReview

    case = _case()

    # 1. Trạng thái trống
    detail_empty = CaseDetail(
        case=case,
        evidence=(),
        activities=(),
        checklist=(),
        expert_requests=(),
        expert_reviews=(),
    )
    sec_empty = case_detail_sections(detail_empty, TraceResolution(status="available", trace_id=case.trace_id))
    assert sec_empty["expert_requests"] == []
    assert sec_empty["expert_reviews"] == []
    assert sec_empty["has_conflict"] is False

    # 2. Trạng thái chờ thẩm định
    req = ExpertRequest(
        request_id="EXP-REQ-1",
        case_id=case.case_id,
        claim_digest="dig-1",
        question_text="Có phải biến dạng quang sai?",
        required_scope="lsu_optics",
    )
    detail_waiting = CaseDetail(
        case=case,
        evidence=(),
        activities=(),
        checklist=(),
        expert_requests=(req,),
        expert_reviews=(),
    )
    sec_waiting = case_detail_sections(detail_waiting, TraceResolution(status="available", trace_id=case.trace_id))
    assert len(sec_waiting["expert_requests"]) == 1
    assert sec_waiting["expert_requests"][0]["Mã yêu cầu"] == "EXP-REQ-1"
    assert sec_waiting["has_conflict"] is False

    # 3. Trạng thái thành công (đã xác nhận)
    rev_confirmed = ExpertReview(
        review_id="EXP-REV-1",
        request_id="EXP-REQ-1",
        case_id=case.case_id,
        claim_digest="dig-1",
        evidence_digest="dig-1",
        decision="confirmed",
        reviewer_id="local_admin",
        reviewer_role="expert",
        scope="lsu_optics",
        rationale="Đã xác nhận góc lệch quang học.",
    )
    detail_confirmed = CaseDetail(
        case=case,
        evidence=(),
        activities=(),
        checklist=(),
        expert_requests=(req,),
        expert_reviews=(rev_confirmed,),
    )
    sec_confirmed = case_detail_sections(detail_confirmed, TraceResolution(status="available", trace_id=case.trace_id))
    assert sec_confirmed["expert_reviews"][0]["Quyết định"] == "Xác nhận"
    assert sec_confirmed["has_conflict"] is False

    # 4. Trạng thái xung đột (2 ý kiến trái chiều)
    rev_rejected = ExpertReview(
        review_id="EXP-REV-2",
        request_id="EXP-REQ-1",
        case_id=case.case_id,
        claim_digest="dig-1",
        evidence_digest="dig-1",
        decision="rejected",
        reviewer_id="local_admin",
        reviewer_role="expert",
        scope="lsu_optics",
        rationale="Không đủ căn cứ biến dạng quang học.",
    )
    detail_conflict = CaseDetail(
        case=case,
        evidence=(),
        activities=(),
        checklist=(),
        expert_requests=(req,),
        expert_reviews=(rev_confirmed, rev_rejected),
    )
    sec_conflict = case_detail_sections(detail_conflict, TraceResolution(status="available", trace_id=case.trace_id))
    assert sec_conflict["has_conflict"] is True

    # 5. Kiểm tra thông báo lỗi an toàn tiếng Việt
    assert safe_case_error_message(CaseValidationError("EXPERT_RATIONALE_REQUIRED")) == "Cần nhập lý do thẩm định cụ thể."
    assert safe_case_error_message(CaseValidationError("EVIDENCE_DIGEST_MISMATCH")) == "Bằng chứng của hồ sơ đã thay đổi so với khi yêu cầu thẩm định."
    assert safe_case_error_message(CaseValidationError("EXPERT_REQUEST_NOT_FOUND")) == "Không tìm thấy yêu cầu thẩm định chuyên gia."
    assert safe_case_error_message(CaseValidationError("EXPERT_QUESTION_REQUIRED")) == "Cần nhập câu hỏi thẩm định cho chuyên gia."


def test_lesson_learned_ui_presenter_and_error_messages():
    case = _case()
    lesson_cand = CaseLesson(
        lesson_id="LES-1",
        case_id=case.case_id,
        review_id="EXP-REV-1",
        claim_digest="dig-1",
        evidence_digest="dig-1",
        title="Lệch góc quét do đệm JIG 04",
        content="Kiểm tra đệm JIG 04 trước khi thay mô tơ.",
        status="candidate",
        created_by="local_admin",
        updated_by="local_admin",
    )
    lesson_appr = CaseLesson(
        lesson_id="LES-2",
        case_id=case.case_id,
        review_id="EXP-REV-1",
        claim_digest="dig-1",
        evidence_digest="dig-1",
        title="Vệ sinh gương phản xạ Iris",
        content="Vệ sinh bằng cồn 99% trước khi đo.",
        status="approved",
        approved_by="local_admin",
        approved_at="2026-09-06T00:00:00+00:00",
        created_by="local_admin",
        updated_by="local_admin",
    )
    detail = CaseDetail(
        case=case,
        evidence=(),
        activities=(),
        checklist=(),
        expert_requests=(),
        expert_reviews=(),
        lessons=(lesson_cand, lesson_appr),
    )
    sections = case_detail_sections(detail, TraceResolution(status="available", trace_id=case.trace_id))
    lessons_ui = sections["lessons"]
    assert len(lessons_ui) == 2
    assert lessons_ui[0]["Trạng thái"] == "Ứng viên"
    assert lessons_ui[0]["Người duyệt"] == "Chưa duyệt"
    assert lessons_ui[1]["Trạng thái"] == "Đã duyệt"
    assert lessons_ui[1]["Người duyệt"] == "Quản trị viên cục bộ"

    # Verify error messages
    assert (
        safe_case_error_message(CaseValidationError("LESSON_PROPOSE_CONFIRMED_REVIEW_REQUIRED"))
        == "Chỉ có thể đề xuất bài học từ thẩm định đã được xác nhận (confirmed)."
    )
    assert safe_case_error_message(CaseValidationError("LESSON_TITLE_REQUIRED")) == "Tiêu đề bài học kinh nghiệm không được để trống."
    assert safe_case_error_message(CaseValidationError("LESSON_CONTENT_REQUIRED")) == "Nội dung bài học kinh nghiệm không được để trống."
    assert (
        safe_case_error_message(CaseValidationError("LESSON_REVOKE_REASON_REQUIRED"))
        == "Vui lòng nhập lý do thu hồi bài học kinh nghiệm."
    )
    assert safe_case_error_message(CaseValidationError("CASE_LESSON_NOT_CANDIDATE")) == "Chỉ có thể phê duyệt bài học đang ở trạng thái ứng viên."


def test_line_investigation_ui_presenter_and_error_messages():
    case = _case()
    ev_clue = CaseEvidenceReference(
        reference_id="REF-LINE-1",
        case_id=case.case_id,
        trace_id="TR-1",
        evidence_node_id="line_events:EV-001:v1",
        citation_id="CIT-1",
        source_locator="line_events:EV-001",
        source_title="Sự kiện dây chuyền STATION_A [JAM_01]",
        reference_digest="dig-ev-1",
        provenance_status="suspected",
    )
    detail = CaseDetail(
        case=case,
        evidence=(ev_clue,),
        activities=(),
        checklist=(),
        expert_requests=(),
        expert_reviews=(),
        lessons=(),
    )
    sections = case_detail_sections(detail, TraceResolution(status="available", trace_id=case.trace_id))
    evidence_ui = sections["evidence"]
    assert len(evidence_ui) == 1
    assert evidence_ui[0]["Nguồn gốc"] == "Nghi ngờ"

    # Test error messages
    assert (
        safe_case_error_message(CaseValidationError("CLUE_RELEVANCE_INVALID"))
        == "Giá trị đánh giá độ liên quan không hợp lệ."
    )
    assert (
        safe_case_error_message(CaseValidationError("CASE_EVIDENCE_NOT_FOUND"))
        == "Không tìm thấy manh mối hoặc bằng chứng trong hồ sơ."
    )
    assert (
        safe_case_error_message(CaseValidationError("CLUE_RELEVANCE_RATIONALE_REQUIRED"))
        == "Vui lòng nhập lý do đánh giá độ liên quan."
    )


def test_controlled_artifacts_ui_presenter_and_error_messages():
    case = _case()
    art_draft = CaseArtifactRecord(
        artifact_id="ART-1",
        case_id=case.case_id,
        artifact_type="sop",
        title="Quy trình hiệu chuẩn Sensor CAM_1",
        content_markdown="# SOP\nNội dung",
        content_digest="dig-1",
        version=1,
        status="draft",
        created_by="local_admin",
        updated_by="local_admin",
    )
    art_appr = CaseArtifactRecord(
        artifact_id="ART-2",
        case_id=case.case_id,
        artifact_type="report",
        title="Báo cáo kỹ thuật sự cố",
        content_markdown="# Báo cáo\nĐã duyệt",
        content_digest="dig-2",
        version=2,
        status="approved",
        created_by="local_admin",
        updated_by="local_admin",
        approved_by="local_admin",
        exported_path="exports/report.md",
    )
    detail = CaseDetail(
        case=case,
        evidence=(),
        activities=(),
        checklist=(),
        expert_requests=(),
        expert_reviews=(),
        lessons=(),
        artifacts=(art_draft, art_appr),
    )
    sections = case_detail_sections(detail, TraceResolution(status="available", trace_id=case.trace_id))
    artifacts_ui = sections["artifacts"]
    assert len(artifacts_ui) == 2
    assert artifacts_ui[0]["Loại đầu ra"] == "Quy trình thao tác chuẩn"
    assert artifacts_ui[0]["Trạng thái"] == "Dự thảo"
    assert artifacts_ui[0]["Người duyệt"] == "Chưa duyệt"
    assert artifacts_ui[0]["Đường dẫn xuất"] == "Chưa xuất"
    assert artifacts_ui[1]["Loại đầu ra"] == "Báo cáo điều tra sự cố"
    assert artifacts_ui[1]["Trạng thái"] == "Đã duyệt"
    assert artifacts_ui[1]["Người duyệt"] == "Quản trị viên cục bộ"
    assert artifacts_ui[1]["Đường dẫn xuất"] == "exports/report.md"

    # Test error messages
    assert (
        safe_case_error_message(CaseValidationError("ARTIFACT_TYPE_INVALID"))
        == "Loại tài liệu đầu ra không phù hợp. Hệ thống chỉ hỗ trợ quy trình thao tác chuẩn hoặc báo cáo điều tra."
    )
    assert (
        safe_case_error_message(CaseValidationError("ARTIFACT_INSUFFICIENT_EVIDENCE"))
        == "Hồ sơ chưa có đủ bằng chứng hợp lệ để soạn thảo tài liệu có kiểm soát."
    )
    assert (
        safe_case_error_message(CaseValidationError("APPROVED_ARTIFACT_IMMUTABLE"))
        == "Tài liệu đã được phê duyệt không thể sửa trực tiếp. Vui lòng lập dự thảo mới."
    )
    assert (
        safe_case_error_message(CaseValidationError("UNAPPROVED_ARTIFACT_EXPORT_FORBIDDEN"))
        == "Chỉ tài liệu đã được phê duyệt mới được phép xuất ra thư mục an toàn."
    )
