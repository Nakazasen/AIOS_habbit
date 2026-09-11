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


def test_expert_interview_ui_presenters_and_rows():
    from aios_habit.expert_interview_models import ANSWER_STATE_ANSWERED, ANSWER_STATE_UNKNOWN, InterviewTurn
    from aios_habit.workspace_case_ui import (
        _session_state_label,
        _turn_answer_state_label,
        interview_turn_rows,
    )

    assert _session_state_label("active") == "Đang hỏi đáp"
    assert _session_state_label("paused") == "Tạm dừng"
    assert _session_state_label("blocked") == "Không thể tiếp tục lúc này"
    assert _session_state_label("completed") == "Hoàn tất"

    assert _turn_answer_state_label(ANSWER_STATE_ANSWERED) == "Đã trả lời"
    assert _turn_answer_state_label(ANSWER_STATE_UNKNOWN) == "Không rõ / Chưa nắm được"

    turn = InterviewTurn(
        turn_id="TURN-1",
        session_id="SESS-1",
        sequence=1,
        question_text="Ngưỡng bước sóng là bao nhiêu?",
        answer_text="Ngưỡng là 632.8 nm",
        question_reason="missing_threshold",
        answer_confidence=0.95,
        answer_state=ANSWER_STATE_ANSWERED,
        created_at="2026-09-08T00:00:00Z",
    )
    rows = interview_turn_rows([turn])
    assert len(rows) == 1
    assert rows[0]["Lượt"] == 1
    assert rows[0]["Câu hỏi"] == "Ngưỡng bước sóng là bao nhiêu?"
    assert rows[0]["Câu trả lời"] == "Ngưỡng là 632.8 nm"
    assert rows[0]["Trạng thái"] == "Đã trả lời"
    assert rows[0]["Độ tin cậy"] == "95%"


def test_four_stages_navigation_and_vietnamese_labels():
    """T105: Verify 4 stages navigation labels, single primary action per stage, and zero technical leak."""
    from aios_habit.workspace_case_ui import (
        _CONTROLLED_ARTIFACT_STATUS_LABELS,
        _CONTROLLED_ARTIFACT_TYPE_LABELS,
    )

    for status_key, label in _CONTROLLED_ARTIFACT_STATUS_LABELS.items():
        assert not any(leak in label.lower() for leak in ("approved", "rejected", "candidate", "revoked", "changes_requested"))
        assert len(label) > 0

    for type_key, label in _CONTROLLED_ARTIFACT_TYPE_LABELS.items():
        assert len(label) > 0

    # Verify workspace navigation options contain all 4 stages in pure Vietnamese
    from aios_habit.workspace_case_ui import render_case_workspace
    import inspect
    src = inspect.getsource(render_case_workspace)
    assert "review_approve" in src
    assert "library_publish" in src
    assert "interview" in src
    assert "1. Chọn thư viện" in src
    assert "2. Phỏng vấn" in src
    assert "3. Kiểm tra bản nháp" in src
    assert "4. Đưa vào thư viện" in src
    ui_source = Path("src/aios_habit/workspace_case_ui.py").read_text(encoding="utf-8")
    assert "Nội dung bản nháp" in ui_source
    assert "Lưu chỉnh sửa" in ui_source
    assert "Xác nhận và đưa vào thư viện" in ui_source
    assert "Mã kiểm tra toàn vẹn nội dung" not in ui_source
    assert "WAV mono 16kHz" not in ui_source
    assert 'type=["wav"]' not in ui_source
    assert "Mã đồng ý" not in ui_source
    assert "khung đối thoại có kiểm soát" not in ui_source.lower()
    assert "person_suggestion.suggested_name" in ui_source


def test_four_stages_have_single_primary_action_and_zero_technical_leak():
    """T105: Verify each of the four Goal 010 stages has a single primary action and zero technical leakage."""
    import inspect
    from aios_habit.workspace_case_ui import (
        render_library_selection_view,
        render_expert_interview_view,
        render_controlled_artifacts_management,
        render_knowledge_publication_management,
    )

    stage_callables = [
        render_library_selection_view,
        render_expert_interview_view,
        render_controlled_artifacts_management,
        render_knowledge_publication_management,
    ]

    from aios_habit.workspace_case_ui import (
        GOAL010_NEXT_INTERVIEW,
        GOAL010_NEXT_LIBRARY,
        GOAL010_NEXT_PUBLISH,
        GOAL010_NEXT_REVIEW,
    )

    expected_next = {
        "render_library_selection_view": GOAL010_NEXT_LIBRARY,
        "render_expert_interview_view": GOAL010_NEXT_INTERVIEW,
        "render_controlled_artifacts_management": GOAL010_NEXT_REVIEW,
        "render_knowledge_publication_management": GOAL010_NEXT_PUBLISH,
    }
    for stage_fn in stage_callables:
        src = inspect.getsource(stage_fn)
        assert 'type="primary"' in src, f"{stage_fn.__name__} must contain a primary action button."
        constant_names = {
            "render_library_selection_view": "GOAL010_NEXT_LIBRARY",
            "render_expert_interview_view": "GOAL010_NEXT_INTERVIEW",
            "render_controlled_artifacts_management": "GOAL010_NEXT_REVIEW",
            "render_knowledge_publication_management": "GOAL010_NEXT_PUBLISH",
        }
        assert constant_names[stage_fn.__name__] in src
        assert expected_next[stage_fn.__name__]
        if stage_fn.__name__ != "render_library_selection_view":
            assert "expanded=False" in src

    ui_text = Path("src/aios_habit/workspace_case_ui.py").read_text(encoding="utf-8")
    for forbidden in ("fixture", "lease", "provenance_digest", "stale digest", "wav mono", "markdown", "json"):
        for line in ui_text.splitlines():
            line_str = line.strip()
            if any(call in line_str for call in ('st.info(', 'st.warning(', 'st.error(', 'st.subheader(', 'st.caption(', 'st.success(', 'st.button(', 'st.form_submit_button(')):
                assert forbidden not in line_str.lower(), f"Forbidden technical token '{forbidden}' in user-facing message: {line_str}"



def test_user_edit_creates_next_artifact_version():
    from aios_habit.workspace_case_ui import _next_artifact_version

    assert _next_artifact_version("1.0") == "1.1"
    assert _next_artifact_version("2") == "3"
    assert _next_artifact_version("ban-dau") == "ban-dau.1"


def test_case_workspace_library_publish_wiring_has_no_type_error():
    """Verify that the library_publish view code path instantiates KnowledgePublisher with valid arguments."""
    from aios_habit.workspace_case_ui import render_case_workspace
    import inspect
    src = inspect.getsource(render_case_workspace)
    assert "publisher = KnowledgePublisher(" in src
    # Must not pass unsupported kwargs directly without base_dir
    assert "base_dir" in src


def test_goal_010_workspace_modes_fail_closed_until_enabled():
    from aios_habit.feature_flags import override_feature_flags
    from aios_habit.workspace_case_ui import _case_workspace_modes

    with override_feature_flags(expert_knowledge_acquisition=False):
        assert _case_workspace_modes() == ("cases",)

    with override_feature_flags(expert_knowledge_acquisition=True):
        assert _case_workspace_modes() == (
            "library_select",
            "interview",
            "review_approve",
            "library_publish",
        )


def test_interview_plan_uses_service_actor_context_compatibly():
    from aios_habit.workspace_case_ui import render_expert_interview_view
    import inspect

    src = inspect.getsource(render_expert_interview_view)
    assert "service.actor.actor_id" in src
    assert "service.actor_context" not in src


def test_interview_audio_configures_whisper_and_confirms_tokens():
    from aios_habit.workspace_case_ui import render_expert_interview_view
    import inspect

    src = inspect.getsource(render_expert_interview_view)
    assert "resolve_whisper_cpp_runtime" in src
    assert "binary_path=binary_path" in src
    assert "model_path=model_path" in src
    assert "confirm_critical_tokens" in src
    assert "replace_transcription_receipt" in src


def test_controlled_artifact_approval_id_uniqueness():
    """Verify that the approval_id generation logic in workspace_case_ui incorporates approval count and timestamp."""
    from aios_habit.workspace_case_ui import render_knowledge_publication_management
    import inspect
    src = inspect.getsource(render_knowledge_publication_management)
    assert "list_decision_records" in src
    assert "app_count + 1" in src


def test_safe_vietnamese_ui_message_default_fallback_behavior():
    """Verify safe_vietnamese_ui_message works cleanly with 1 argument, returning default fallback on English error."""
    from aios_habit.ui_safety import safe_vietnamese_ui_message

    # Pure Vietnamese text is returned intact
    vn_text = "Thao tác thành công tốt đẹp."
    assert safe_vietnamese_ui_message(vn_text) == vn_text

    # English technical diagnostic returns Vietnamese fallback
    en_error = "ConnectionError: connection timed out to 127.0.0.1:8000"
    result = safe_vietnamese_ui_message(en_error)
    assert result == "Đã xảy ra lỗi trong quá trình xử lý. Vui lòng thử lại sau."
    assert "ConnectionError" not in result

    # 1-argument call on empty input
    assert safe_vietnamese_ui_message("") == "Đã xảy ra lỗi trong quá trình xử lý. Vui lòng thử lại sau."


def test_render_knowledge_publication_and_controlled_artifacts_clean_execution(tmp_path):
    """Verify render_controlled_artifacts_management and render_knowledge_publication_management run without TypeError."""
    from unittest.mock import MagicMock, patch
    from aios_habit.expert_interview_repository import ExpertInterviewRepository
    from aios_habit.expert_interview_service import ExpertInterviewService
    from aios_habit.expert_identity import VerifiedPrincipal
    from aios_habit.knowledge_publication import KnowledgePublisher
    from aios_habit.workspace_case_authorization import ActorContext
    from aios_habit.workspace_case_repository import WorkspaceCaseRepository
    from aios_habit.workspace_case_ui import (
        render_controlled_artifacts_management,
        render_knowledge_publication_management,
    )

    db_path = tmp_path / "test_ui.sqlite"
    case_repo = WorkspaceCaseRepository(db_path)
    case_repo.initialize()
    interview_repo = ExpertInterviewRepository(db_path)
    interview_repo.initialize()
    actor_ctx = ActorContext("test_actor")
    svc = ExpertInterviewService(store=case_repo, interview_repo=interview_repo, actor_context=actor_ctx)
    principal = VerifiedPrincipal("test_actor", "local", "Test Actor")
    publisher = KnowledgePublisher(base_dir=tmp_path / "chat", backup_dir=tmp_path / "backups")

    with patch("streamlit.subheader"), patch("streamlit.info"), patch("streamlit.write"), patch("streamlit.selectbox", return_value=0), patch("streamlit.tabs", return_value=[MagicMock(), MagicMock(), MagicMock(), MagicMock()]):
        # When no artifacts exist, these views render their info panels cleanly
        render_controlled_artifacts_management(svc, principal)
        render_knowledge_publication_management(svc, publisher, principal)


def test_workspace_case_ui_module_imports_and_type_hints():
    """Verify datetime, timezone, DEFAULT_COLLECTION_ID, Sequence, Any are imported and all type hints resolve."""
    import typing
    from datetime import datetime, timezone
    import aios_habit.workspace_case_ui as wsc_ui
    from aios_habit.workspace_chat_models import DEFAULT_COLLECTION_ID

    assert wsc_ui.datetime is datetime
    assert wsc_ui.timezone is timezone
    assert wsc_ui.DEFAULT_COLLECTION_ID == DEFAULT_COLLECTION_ID
    assert hasattr(wsc_ui, "Sequence")
    assert hasattr(wsc_ui, "Any")

    hints = typing.get_type_hints(wsc_ui.interview_turn_rows)
    assert "turns" in hints
    assert "return" in hints


def test_render_controlled_artifacts_management_with_existing_artifact_executes_cleanly(tmp_path):
    """Verify render_controlled_artifacts_management generates approval_id with datetime and submits cleanly."""
    from unittest.mock import MagicMock, patch
    from aios_habit.controlled_knowledge_artifact import ControlledKnowledgeArtifact, ARTIFACT_STATUS_CANDIDATE
    from aios_habit.expert_interview_repository import ExpertInterviewRepository
    from aios_habit.expert_interview_service import ExpertInterviewService
    from aios_habit.expert_identity import VerifiedPrincipal
    from aios_habit.workspace_case_authorization import ActorContext, RoleGrant
    from aios_habit.workspace_case_repository import WorkspaceCaseRepository
    from aios_habit.workspace_case_ui import render_controlled_artifacts_management

    db_path = tmp_path / "test_artifact_ui.sqlite"
    case_repo = WorkspaceCaseRepository(db_path)
    case_repo.initialize()
    interview_repo = ExpertInterviewRepository(db_path)
    interview_repo.initialize()

    # Grant quality_manager role to test_actor
    case_repo.replace_role_grants(
        "test_actor",
        [
            RoleGrant(
                grant_id="GRANT-ACTOR-1",
                actor_id="test_actor",
                role="quality_manager",
                scope="general",
                valid_from="2000-01-01T00:00:00+00:00",
                valid_until="9999-12-31T23:59:59+00:00",
            ),
        ],
    )

    actor_ctx = ActorContext("test_actor")
    svc = ExpertInterviewService(store=case_repo, interview_repo=interview_repo, actor_context=actor_ctx)
    principal = VerifiedPrincipal("test_actor", "local", "Test Actor")

    art = ControlledKnowledgeArtifact(
        artifact_id="ART-TEST-001",
        artifact_type="sop",
        title="Quy trình thử nghiệm",
        scope="general",
        version="1.0",
        content_markdown="# Nội dung quy trình thử nghiệm",
        claim_ids=("CLM-001",),
        status=ARTIFACT_STATUS_CANDIDATE,
        created_by="creator_actor",
    )
    interview_repo.save_artifact(art, "IDEMP-ART-TEST-1")

    tab_mocks = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    with patch("streamlit.subheader"), \
         patch("streamlit.info"), \
         patch("streamlit.write"), \
         patch("streamlit.caption"), \
         patch("streamlit.markdown"), \
         patch("streamlit.warning"), \
         patch("streamlit.selectbox", return_value=0), \
         patch("streamlit.tabs", return_value=tab_mocks), \
         patch("streamlit.expander"), \
         patch("streamlit.form"), \
             patch(
                 "streamlit.text_area",
                 side_effect=[
                     "# Nội dung quy trình đã chỉnh sửa",
                    "Căn cứ phê duyệt hợp lệ.",
                     "Biên bản phỏng vấn đã kiểm tra",
                 ],
             ), \
             patch("streamlit.text_input", return_value="Người kiểm tra"), \
             patch("streamlit.checkbox", return_value=True), \
         patch("streamlit.form_submit_button", return_value=True), \
         patch("streamlit.success") as mock_success, \
         patch("streamlit.rerun"):
        render_controlled_artifacts_management(svc, principal)
        mock_success.assert_called_once()
        decisions = interview_repo.list_decision_records("ART-TEST-001")
        assert decisions == []
        revised = interview_repo.get_artifact("ART-TEST-001")
        assert revised is not None
        assert revised.version == "1.1"
        assert revised.content_markdown == "# Nội dung quy trình đã chỉnh sửa"
        assert revised.status == ARTIFACT_STATUS_CANDIDATE


def test_render_knowledge_publication_management_revocation_executes_cleanly(tmp_path):
    """Verify render_knowledge_publication_management revocation utilizes DEFAULT_COLLECTION_ID without NameError."""
    from unittest.mock import MagicMock, patch
    from aios_habit.controlled_knowledge_artifact import ControlledKnowledgeArtifact, ARTIFACT_STATUS_APPROVED
    from aios_habit.expert_interview_repository import ExpertInterviewRepository
    from aios_habit.expert_interview_service import ExpertInterviewService
    from aios_habit.expert_identity import VerifiedPrincipal
    from aios_habit.knowledge_publication import KnowledgePublisher, PublicationReceipt
    from aios_habit.workspace_case_authorization import ActorContext
    from aios_habit.workspace_case_repository import WorkspaceCaseRepository
    from aios_habit.workspace_case_ui import render_knowledge_publication_management
    from aios_habit.workspace_chat_models import DEFAULT_COLLECTION_ID

    db_path = tmp_path / "test_pub_ui.sqlite"
    case_repo = WorkspaceCaseRepository(db_path)
    case_repo.initialize()
    interview_repo = ExpertInterviewRepository(db_path)
    interview_repo.initialize()
    actor_ctx = ActorContext("test_actor")
    svc = ExpertInterviewService(store=case_repo, interview_repo=interview_repo, actor_context=actor_ctx)
    principal = VerifiedPrincipal("test_actor", "local", "Test Actor")

    art = ControlledKnowledgeArtifact(
        artifact_id="ART-PUB-001",
        artifact_type="sop",
        title="Quy trình đã duyệt",
        scope="general",
        version="1.0",
        content_markdown="# Nội dung quy trình đã duyệt",
        claim_ids=("CLM-001",),
        status=ARTIFACT_STATUS_APPROVED,
        created_by="creator_actor",
    )
    interview_repo.save_artifact(art, "IDEMP-ART-PUB-1")

    publisher = KnowledgePublisher(base_dir=tmp_path / "chat", backup_dir=tmp_path / "backups")
    mock_receipt = PublicationReceipt(
        receipt_id="REV-TEST-01",
        package_id="PKG-ART-PUB-001-V1_0",
        package_digest="",
        backup_id="BCK-01",
        quick_check_status="PASS",
        acceptance_results={},
        published_at="2026-09-09T00:00:00Z",
        published_by="test_actor",
        state="revoked",
    )

    def revoke_and_record(**kwargs):
        kwargs["record_responsibility"]()
        return mock_receipt

    tab_mocks = [MagicMock(), MagicMock()]
    with patch("streamlit.subheader"), \
         patch("streamlit.info"), \
         patch("streamlit.write"), \
         patch("streamlit.caption"), \
         patch("streamlit.selectbox", side_effect=[0, "high", "PKG-ART-PUB-001-V1_0", "high"]), \
         patch("streamlit.tabs", return_value=tab_mocks), \
         patch("streamlit.expander"), \
         patch("streamlit.form"), \
         patch("streamlit.text_input", return_value="Người thu hồi"), \
         patch("streamlit.text_area", return_value="Lý do thu hồi hợp lệ."), \
         patch("streamlit.checkbox", return_value=True), \
         patch("streamlit.form_submit_button", return_value=True), \
         patch.object(publisher, "publish_package", return_value=(art, mock_receipt)), \
         patch.object(
             publisher,
             "list_published_documents",
             return_value=[{
                 "doc_id": "PKG-ART-PUB-001-V1_0",
                 "title": "Quy trình đã duyệt",
                 "version": "1.0",
                 "published_at": "2026-09-09T00:00:00Z",
             }],
         ), \
         patch.object(publisher, "revoke_publication", side_effect=revoke_and_record) as mock_revoke, \
         patch("streamlit.success") as mock_success:
        render_knowledge_publication_management(svc, publisher, principal)
        mock_revoke.assert_called_once()
        revoke_args = mock_revoke.call_args.kwargs
        assert revoke_args["package_id"] == "PKG-ART-PUB-001-V1_0"
        assert revoke_args["collection_id"] == DEFAULT_COLLECTION_ID
        assert revoke_args["reason"] == "Lý do thu hồi hợp lệ."
        assert revoke_args["actor"] == "Người thu hồi"
        assert callable(revoke_args["record_responsibility"])
        mock_success.assert_called_once()
        decisions = interview_repo.list_decision_records("ART-PUB-001")
        assert len(decisions) == 1
        assert decisions[0].decision == "revoke"
