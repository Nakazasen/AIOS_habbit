"""Vietnamese Streamlit views for the supported Workspace case workflow."""
from __future__ import annotations

from typing import Callable, Iterable, Optional
import re

import streamlit as st

from aios_habit.workspace_case_models import CaseDetail, CaseFilter, CaseRecord, TraceResolution
from aios_habit.workspace_case_service import CaseValidationError, WorkspaceCaseService
from aios_habit.workspace_case_repository import WorkspaceCaseRepositoryError
from aios_habit.ui_safety import safe_vietnamese_ui_message


_TYPE_LABELS = {
    "investigation": "Điều tra",
    "prediction": "Dự đoán",
    "agent_work": "Công việc trợ lý AI",
}
_STATUS_LABELS = {
    "draft": "Nháp",
    "triaged": "Đã phân loại",
    "in_progress": "Đang xử lý",
    "waiting_evidence": "Chờ bằng chứng",
    "resolved": "Đã có kết luận",
    "closed": "Đã đóng",
}
_PRIORITY_LABELS = {"low": "Thấp", "normal": "Bình thường", "high": "Cao", "urgent": "Khẩn"}
_STORE_LABELS = {
    "library": "Thư viện tài liệu",
    "line_events": "Kho sự kiện dây chuyền",
    "approved_artifact": "Đầu ra đã duyệt",
    "workspace_trace": "Dấu vết Workspace Chat",
}
_PROVENANCE_LABELS = {
    "approved": "Đã duyệt",
    "suspected": "Nghi ngờ",
    "unknown": "Chưa rõ",
    "missing": "Bị thiếu",
}
_EVENT_LABELS = {
    "case_created": "Tạo hồ sơ",
    "status_transition": "Đổi trạng thái",
    "case_assigned": "Giao người phụ trách",
    "evidence_added": "Bổ sung bằng chứng",
    "checklist_added": "Thêm việc cần bổ sung",
}
_CHECKLIST_STATUS_LABELS = {
    "open": "Chưa hoàn thành",
    "completed": "Đã hoàn thành",
}
_ACTOR_LABELS = {
    "local_admin": "Quản trị viên cục bộ",
}
_EDITABLE_STATUSES = ("draft", "triaged", "in_progress", "waiting_evidence")

_ERROR_MESSAGES = {
    "CASE_VERSION_CONFLICT": "Hồ sơ đã được cập nhật ở nơi khác. Hãy tải lại rồi thử lại.",
    "CASE_TRANSITION_INVALID": "Không thể chuyển sang trạng thái đã chọn từ trạng thái hiện tại.",
    "CASE_RATIONALE_REQUIRED": "Cần nhập lý do trước khi đổi trạng thái.",
    "CASE_AUTH_DENIED": "Bạn chưa được cấp quyền cho thao tác này trong công đoạn của hồ sơ.",
    "CASE_ACTOR_REQUIRED": "Ứng dụng chưa xác định được người đang thao tác.",
    "CASE_SCOPE_REQUIRED": "Hồ sơ chưa có phạm vi công đoạn hợp lệ.",
    "CASE_ACTIVITY_CHAIN_INVALID": "Chuỗi lịch sử hồ sơ không còn toàn vẹn. Đã khóa thao tác ghi.",
    "CASE_EVIDENCE_DUPLICATE": "Tham chiếu bằng chứng này đã có trong hồ sơ.",
    "CASE_ASSIGNEE_REQUIRED": "Cần nhập mã người được giao hồ sơ.",
    "CASE_ASSIGNEE_NOT_AUTHORIZED": "Người được giao chưa có quyền làm việc trong công đoạn của hồ sơ.",
    "CASE_CHECKLIST_DESCRIPTION_REQUIRED": "Cần mô tả bằng chứng hoặc việc còn thiếu.",
    "CASE_EVIDENCE_DIGEST_INVALID": "Mã kiểm tra nội dung phải là chuỗi SHA-256 hợp lệ.",
    "CASE_EVIDENCE_IDENTITY_REQUIRED": "Cần nhập mã nguồn và phiên bản nguồn.",
    "CASE_EVIDENCE_LOCATOR_INVALID": "Vị trí nguồn không hợp lệ hoặc chưa được làm sạch.",
    "CASE_EVIDENCE_PROVENANCE_INVALID": "Trạng thái nguồn gốc bằng chứng không hợp lệ.",
    "CASE_EVIDENCE_STORE_INVALID": "Kho nguồn bằng chứng không hợp lệ.",
    "CASE_EVIDENCE_TITLE_REQUIRED": "Cần nhập tên nguồn bằng chứng.",
    "CASE_NOT_FOUND": "Không tìm thấy hồ sơ.",
    "CASE_RESOLUTION_REVIEW_REQUIRED": "Chưa thể kết luận hoặc đóng hồ sơ khi chưa có kết quả thẩm định hợp lệ.",
}


def safe_case_error_message(error: BaseException) -> str:
    """Convert internal codes into Vietnamese and hide paths or tracebacks."""
    text = str(error).strip()
    if text in _ERROR_MESSAGES:
        return _ERROR_MESSAGES[text]
    if re.fullmatch(r"[A-Z][A-Z0-9_]+", text) or "Traceback" in text or re.search(r"[A-Za-z]:[\\/]", text):
        return "Không thể hoàn tất thao tác hồ sơ một cách an toàn."
    return safe_vietnamese_ui_message(text, "Không thể hoàn tất thao tác hồ sơ một cách an toàn.")


def case_list_rows(cases: Iterable[CaseRecord]) -> list[dict[str, str]]:
    return [
        {
            "Mã hồ sơ": case.case_id,
            "Loại": _TYPE_LABELS.get(case.case_type, "Khác"),
            "Trạng thái": _STATUS_LABELS.get(case.status, "Chưa rõ"),
            "Ưu tiên": _PRIORITY_LABELS.get(case.priority, "Bình thường"),
            "Người phụ trách": case.assignee_id or "Chưa giao",
        }
        for case in cases
    ]


def _safe_actor_label(actor_id: str) -> str:
    return _ACTOR_LABELS.get(actor_id, "Người dùng nội bộ")


def _safe_locator_label(locator: str) -> str:
    if re.fullmatch(r"(?:nguon|source):[0-9a-f]{8,64}", locator, re.IGNORECASE):
        return f"Mã vị trí {locator.split(':', 1)[1]}"
    page_match = re.fullmatch(r"(?:page|trang)[:# -]?(\d+)", locator, re.IGNORECASE)
    if page_match:
        return f"Trang {page_match.group(1)}"
    line_match = re.fullmatch(r"(?:line|dong|dòng)[:# -]?(\d+(?:-\d+)?)", locator, re.IGNORECASE)
    if line_match:
        return f"Dòng {line_match.group(1)}"
    return "Vị trí đã được lưu trong hồ sơ"


def case_detail_sections(detail: CaseDetail, trace: TraceResolution) -> dict[str, object]:
    return {
        "title": detail.case.title,
        "status": _STATUS_LABELS.get(detail.case.status, "Chưa rõ"),
        "assignee": detail.case.assignee_id or "Chưa giao",
        "trace_status": (
            "Có thể mở dấu vết bằng chứng gốc"
            if trace.status == "available"
            else "Thiếu dấu vết bằng chứng gốc"
        ),
        "evidence": [
            {
                "Nguồn": reference.source_title,
                "Vị trí": _safe_locator_label(reference.source_locator),
                "Nguồn gốc": _PROVENANCE_LABELS.get(reference.provenance_status, "Chưa rõ"),
            }
            for reference in detail.evidence
        ],
        "timeline": [
            {
                "Thời điểm": activity.occurred_at,
                "Sự kiện": _EVENT_LABELS.get(activity.event_type, "Hoạt động hồ sơ"),
                "Người thực hiện": _safe_actor_label(activity.actor_id),
            }
            for activity in detail.activities
        ],
        "checklist": [
            {
                "Việc còn thiếu": item.description,
                "Trạng thái": _CHECKLIST_STATUS_LABELS.get(item.status, "Chưa xác định"),
            }
            for item in detail.checklist
        ],
    }


def render_case_workspace(
    service: WorkspaceCaseService,
    *,
    on_close: Optional[Callable[[], None]] = None,
    on_open_trace: Optional[Callable[[TraceResolution], None]] = None,
) -> None:
    header_col, close_col = st.columns([5, 1])
    with header_col:
        st.title("Hồ sơ vụ việc")
        st.caption("Hồ sơ cục bộ chỉ giữ thông tin mô tả và tham chiếu bằng chứng, không sao chép hội thoại hoặc đoạn trích gốc.")
    with close_col:
        if on_close and st.button("Quay lại", use_container_width=True):
            on_close()
            return

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        selected_type = st.selectbox(
            "Loại hồ sơ",
            options=(None, "investigation", "prediction", "agent_work"),
            format_func=lambda value: "Tất cả" if value is None else _TYPE_LABELS[value],
            key="wsc_case_filter_type",
        )
    with filter_col2:
        selected_status = st.selectbox(
            "Trạng thái",
            options=(None, *tuple(_STATUS_LABELS)),
            format_func=lambda value: "Tất cả" if value is None else _STATUS_LABELS[value],
            key="wsc_case_filter_status",
        )

    try:
        cases = service.list_cases(CaseFilter(case_type=selected_type, status=selected_status))
    except (CaseValidationError, WorkspaceCaseRepositoryError):
        st.error("Không thể đọc danh sách hồ sơ cục bộ một cách an toàn.")
        return
    if not cases:
        st.info("Chưa có hồ sơ phù hợp với bộ lọc.")
        return

    st.dataframe(case_list_rows(cases), use_container_width=True, hide_index=True)
    by_id = {case.case_id: case for case in cases}
    requested_case = str(st.query_params.get("case") or "")
    default_index = next((index for index, case in enumerate(cases) if case.case_id == requested_case), 0)
    selected_case_id = st.selectbox(
        "Chọn hồ sơ để xem chi tiết",
        options=tuple(by_id),
        index=default_index,
        format_func=lambda case_id: f"{case_id} · {by_id[case_id].title}",
        key="wsc_selected_case_id",
    )
    st.query_params["case"] = selected_case_id
    try:
        detail = service.get_case_detail(selected_case_id)
        trace = service.open_trace(selected_case_id)
    except (CaseValidationError, WorkspaceCaseRepositoryError):
        st.error("Không thể đọc chi tiết hồ sơ hoặc lịch sử kiểm toán không còn hợp lệ.")
        return

    sections = case_detail_sections(detail, trace)
    st.subheader(str(sections["title"]))
    metric_status, metric_assignee, metric_version = st.columns(3)
    metric_status.metric("Trạng thái", str(sections["status"]))
    metric_assignee.metric("Người phụ trách", str(sections["assignee"]))
    metric_version.metric("Phiên bản", detail.case.version)

    if trace.status == "available":
        if on_open_trace and st.button("Mở cuộc trò chuyện và dấu vết gốc", type="primary"):
            on_open_trace(trace)
            return
    else:
        st.warning("Dấu vết bằng chứng gốc không còn tồn tại. Hệ thống không tái tạo nội dung bằng AI.")

    st.markdown("### Bằng chứng")
    if sections["evidence"]:
        st.dataframe(sections["evidence"], use_container_width=True, hide_index=True)
    else:
        st.info("Hồ sơ chưa có tham chiếu bằng chứng.")

    st.markdown("### Dòng thời gian")
    st.dataframe(sections["timeline"], use_container_width=True, hide_index=True)

    st.markdown("### Việc còn thiếu")
    if sections["checklist"]:
        st.dataframe(sections["checklist"], use_container_width=True, hide_index=True)
    else:
        st.caption("Chưa có mục cần bổ sung.")

    with st.expander("Cập nhật hồ sơ", expanded=False):
        with st.form(f"wsc_case_transition_{selected_case_id}"):
            new_status = st.selectbox(
                "Chuyển trạng thái",
                options=_EDITABLE_STATUSES,
                format_func=lambda value: _STATUS_LABELS[value],
            )
            rationale = st.text_area("Lý do")
            if st.form_submit_button("Lưu trạng thái"):
                try:
                    service.transition_case(
                        selected_case_id,
                        expected_version=detail.case.version,
                        new_status=new_status,
                        rationale=rationale,
                    )
                    st.success("Đã cập nhật trạng thái hồ sơ.")
                    st.rerun()
                except CaseValidationError as error:
                    st.error(safe_case_error_message(error))

        with st.form(f"wsc_case_assign_{selected_case_id}"):
            assignee = st.text_input("Mã người được giao")
            if st.form_submit_button("Giao việc"):
                try:
                    service.assign_case(
                        selected_case_id, expected_version=detail.case.version, assignee_id=assignee
                    )
                    st.success("Đã giao hồ sơ.")
                    st.rerun()
                except CaseValidationError as error:
                    st.error(safe_case_error_message(error))

        with st.form(f"wsc_case_checklist_{selected_case_id}"):
            description = st.text_input("Bằng chứng hoặc việc còn thiếu")
            if st.form_submit_button("Thêm vào danh sách"):
                try:
                    service.add_checklist_item(
                        selected_case_id,
                        expected_version=detail.case.version,
                        description=description,
                    )
                    st.success("Đã thêm việc cần bổ sung.")
                    st.rerun()
                except CaseValidationError as error:
                    st.error(safe_case_error_message(error))

    with st.expander("Gắn thêm tham chiếu bằng chứng", expanded=False):
        st.caption("Chỉ nhập thông tin mô tả của nguồn đã có; không dán nội dung thô, ảnh hoặc nhật ký máy vào biểu mẫu này.")
        with st.form(f"wsc_case_evidence_{selected_case_id}"):
            source_store = st.selectbox(
                "Kho nguồn",
                tuple(_STORE_LABELS),
                format_func=lambda value: _STORE_LABELS[value],
            )
            source_id = st.text_input("Mã nguồn")
            source_version = st.text_input("Phiên bản nguồn")
            locator = st.text_input("Vị trí đã làm sạch")
            title = st.text_input("Tên nguồn")
            content_digest = st.text_input("Mã kiểm tra nội dung SHA-256")
            provenance = st.selectbox(
                "Trạng thái nguồn gốc",
                tuple(_PROVENANCE_LABELS),
                format_func=lambda value: _PROVENANCE_LABELS[value],
            )
            if st.form_submit_button("Gắn bằng chứng"):
                try:
                    service.attach_evidence_reference(
                        selected_case_id,
                        expected_version=detail.case.version,
                        source_store=source_store,
                        source_id=source_id,
                        source_version=source_version,
                        locator=locator,
                        title=title,
                        content_digest=content_digest,
                        provenance_status=provenance,
                    )
                    st.success("Đã gắn tham chiếu bằng chứng.")
                    st.rerun()
                except CaseValidationError as error:
                    st.error(safe_case_error_message(error))
