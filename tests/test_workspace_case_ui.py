from __future__ import annotations

import ast
from pathlib import Path

from aios_habit.workspace_case_models import (
    CaseActivity,
    CaseChecklistItem,
    CaseDetail,
    CaseEvidenceReference,
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
