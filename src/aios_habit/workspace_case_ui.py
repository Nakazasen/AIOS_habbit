"""Multilingual Streamlit views for the supported Workspace case workflow (vi, ja, zh-CN)."""
from __future__ import annotations

from typing import Callable, Iterable, Optional
import re

import streamlit as st

from aios_habit.workspace_case_models import CaseDetail, CaseFilter, CaseRecord, TraceResolution
from aios_habit.workspace_case_service import CaseValidationError, WorkspaceCaseService
from aios_habit.workspace_case_repository import WorkspaceCaseRepositoryError
from aios_habit.ui_safety import safe_vietnamese_ui_message
from aios_habit.i18n import DEFAULT_LOCALE, normalize_locale, t


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

_ERROR_KEY_MAP = {
    "CASE_VERSION_CONFLICT": "case_err_version_conflict",
    "CASE_TRANSITION_INVALID": "case_err_transition_invalid",
    "CASE_RATIONALE_REQUIRED": "case_err_rationale_required",
    "CASE_AUTH_DENIED": "case_err_auth_denied",
    "CASE_ACTOR_REQUIRED": "case_err_actor_required",
    "CASE_SCOPE_REQUIRED": "case_err_scope_required",
    "CASE_ACTIVITY_CHAIN_INVALID": "case_err_activity_chain_invalid",
    "CASE_EVIDENCE_DUPLICATE": "case_err_evidence_duplicate",
    "CASE_ASSIGNEE_REQUIRED": "case_err_assignee_required",
    "CASE_ASSIGNEE_NOT_AUTHORIZED": "case_err_assignee_not_authorized",
    "CASE_CHECKLIST_DESCRIPTION_REQUIRED": "case_err_checklist_desc_required",
    "CASE_EVIDENCE_DIGEST_INVALID": "case_err_evidence_digest_invalid",
    "CASE_EVIDENCE_IDENTITY_REQUIRED": "case_err_evidence_identity_required",
    "CASE_EVIDENCE_LOCATOR_INVALID": "case_err_evidence_locator_invalid",
    "CASE_EVIDENCE_PROVENANCE_INVALID": "case_err_evidence_provenance_invalid",
    "CASE_EVIDENCE_STORE_INVALID": "case_err_evidence_store_invalid",
    "CASE_EVIDENCE_TITLE_REQUIRED": "case_err_evidence_title_required",
    "CASE_NOT_FOUND": "case_err_not_found",
    "CASE_RESOLUTION_REVIEW_REQUIRED": "case_err_resolution_review_required",
}


def _type_label(case_type: str, locale: str = "vi") -> str:
    key = f"case_type_{case_type}"
    val = t(key, locale=locale)
    return val if val != key else _TYPE_LABELS.get(case_type, t("case_other", locale=locale))


def _status_label(status: str, locale: str = "vi") -> str:
    key = f"case_status_{status}"
    val = t(key, locale=locale)
    return val if val != key else _STATUS_LABELS.get(status, t("case_unknown", locale=locale))


def _priority_label(priority: str, locale: str = "vi") -> str:
    key = f"case_priority_{priority}"
    val = t(key, locale=locale)
    return val if val != key else _PRIORITY_LABELS.get(priority, t("case_priority_normal", locale=locale))


def _store_label(store: str, locale: str = "vi") -> str:
    key = f"case_store_{store}"
    val = t(key, locale=locale)
    return val if val != key else _STORE_LABELS.get(store, store)


def _provenance_label(provenance: str, locale: str = "vi") -> str:
    key = f"case_provenance_{provenance}"
    val = t(key, locale=locale)
    return val if val != key else _PROVENANCE_LABELS.get(provenance, t("case_unknown", locale=locale))


def _event_label(event_type: str, locale: str = "vi") -> str:
    key = f"case_event_{event_type}"
    val = t(key, locale=locale)
    return val if val != key else _EVENT_LABELS.get(event_type, "Hoạt động hồ sơ")


def _checklist_status_label(status: str, locale: str = "vi") -> str:
    key = f"case_checklist_status_{status}"
    val = t(key, locale=locale)
    return val if val != key else _CHECKLIST_STATUS_LABELS.get(status, "Chưa xác định")


def _safe_actor_label(actor_id: str, locale: str = "vi") -> str:
    if actor_id == "local_admin":
        return t("case_actor_local_admin", locale=locale)
    return t("case_actor_internal_user", locale=locale)


def _safe_locator_label(locator: str, locale: str = "vi") -> str:
    if re.fullmatch(r"(?:nguon|source):[0-9a-f]{8,64}", locator, re.IGNORECASE):
        loc_id = locator.split(":", 1)[1]
        return t("case_locator_pos", locale=locale, locator=loc_id)
    page_match = re.fullmatch(r"(?:page|trang)[:# -]?(\d+)", locator, re.IGNORECASE)
    if page_match:
        return t("case_locator_page", locale=locale, page=page_match.group(1))
    line_match = re.fullmatch(r"(?:line|dong|dòng)[:# -]?(\d+(?:-\d+)?)", locator, re.IGNORECASE)
    if line_match:
        return t("case_locator_line", locale=locale, line=line_match.group(1))
    return t("case_locator_saved", locale=locale)


def safe_case_error_message(error: BaseException, locale: str = "vi") -> str:
    """Convert internal codes into safe localized text and hide paths or tracebacks."""
    text = str(error).strip()
    norm_loc = normalize_locale(locale)
    if text in _ERROR_KEY_MAP:
        return t(_ERROR_KEY_MAP[text], locale=norm_loc)
    fallback = t("case_err_safe_fallback", locale=norm_loc)
    if re.fullmatch(r"[A-Z][A-Z0-9_]+", text) or "Traceback" in text or re.search(r"[A-Za-z]:[\\/]", text):
        return fallback
    return safe_vietnamese_ui_message(text, fallback)


def case_list_rows(cases: Iterable[CaseRecord], locale: str = "vi") -> list[dict[str, str]]:
    norm_loc = normalize_locale(locale)
    col_id = t("case_col_case_id", locale=norm_loc)
    col_type = t("case_col_type", locale=norm_loc)
    col_status = t("case_col_status", locale=norm_loc)
    col_priority = t("case_col_priority", locale=norm_loc)
    col_assignee = t("case_col_assignee", locale=norm_loc)
    unassigned = t("case_unassigned", locale=norm_loc)

    return [
        {
            col_id: case.case_id,
            col_type: _type_label(case.case_type, locale=norm_loc),
            col_status: _status_label(case.status, locale=norm_loc),
            col_priority: _priority_label(case.priority, locale=norm_loc),
            col_assignee: case.assignee_id or unassigned,
        }
        for case in cases
    ]


def case_detail_sections(detail: CaseDetail, trace: TraceResolution, locale: str = "vi") -> dict[str, object]:
    norm_loc = normalize_locale(locale)
    col_source = t("case_col_source", locale=norm_loc)
    col_location = t("case_col_location", locale=norm_loc)
    col_provenance = t("case_col_provenance", locale=norm_loc)
    col_time = t("case_col_time", locale=norm_loc)
    col_event = t("case_col_event", locale=norm_loc)
    col_actor = t("case_col_actor", locale=norm_loc)
    col_missing = t("case_col_missing_item", locale=norm_loc)
    col_status = t("case_col_status", locale=norm_loc)

    trace_status_msg = (
        t("case_trace_available", locale=norm_loc)
        if trace.status == "available"
        else t("case_trace_missing", locale=norm_loc)
    )

    return {
        "title": detail.case.title,
        "status": _status_label(detail.case.status, locale=norm_loc),
        "assignee": detail.case.assignee_id or t("case_unassigned", locale=norm_loc),
        "trace_status": trace_status_msg,
        "evidence": [
            {
                col_source: reference.source_title,
                col_location: _safe_locator_label(reference.source_locator, locale=norm_loc),
                col_provenance: _provenance_label(reference.provenance_status, locale=norm_loc),
            }
            for reference in detail.evidence
        ],
        "timeline": [
            {
                col_time: activity.occurred_at,
                col_event: _event_label(activity.event_type, locale=norm_loc),
                col_actor: _safe_actor_label(activity.actor_id, locale=norm_loc),
            }
            for activity in detail.activities
        ],
        "checklist": [
            {
                col_missing: item.description,
                col_status: _checklist_status_label(item.status, locale=norm_loc),
            }
            for item in detail.checklist
        ],
    }


def render_case_workspace(
    service: WorkspaceCaseService,
    *,
    on_close: Optional[Callable[[], None]] = None,
    on_open_trace: Optional[Callable[[TraceResolution], None]] = None,
    locale: str = "vi",
) -> None:
    norm_loc = normalize_locale(locale)
    header_col, close_col = st.columns([5, 1])
    with header_col:
        st.title(t("case_workspace_title", locale=norm_loc))
        st.caption(t("case_workspace_caption", locale=norm_loc))
    with close_col:
        if on_close and st.button(t("case_btn_back", locale=norm_loc), use_container_width=True):
            on_close()
            return

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        selected_type = st.selectbox(
            t("case_filter_type_label", locale=norm_loc),
            options=(None, "investigation", "prediction", "agent_work"),
            format_func=lambda value: t("case_filter_all", locale=norm_loc) if value is None else _type_label(value, locale=norm_loc),
            key="wsc_case_filter_type",
        )
    with filter_col2:
        selected_status = st.selectbox(
            t("case_filter_status_label", locale=norm_loc),
            options=(None, *tuple(_STATUS_LABELS)),
            format_func=lambda value: t("case_filter_all", locale=norm_loc) if value is None else _status_label(value, locale=norm_loc),
            key="wsc_case_filter_status",
        )

    try:
        cases = service.list_cases(CaseFilter(case_type=selected_type, status=selected_status))
    except (CaseValidationError, WorkspaceCaseRepositoryError):
        st.error(t("case_error_read_list", locale=norm_loc))
        return
    if not cases:
        st.info(t("case_empty_filter", locale=norm_loc))
        return

    st.dataframe(case_list_rows(cases, locale=norm_loc), use_container_width=True, hide_index=True)
    by_id = {case.case_id: case for case in cases}
    requested_case = str(st.query_params.get("case") or "")
    default_index = next((index for index, case in enumerate(cases) if case.case_id == requested_case), 0)
    selected_case_id = st.selectbox(
        t("case_select_detail_label", locale=norm_loc),
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
        st.error(t("case_error_read_detail", locale=norm_loc))
        return

    sections = case_detail_sections(detail, trace, locale=norm_loc)
    st.subheader(str(sections["title"]))
    metric_status, metric_assignee, metric_version = st.columns(3)
    metric_status.metric(t("case_metric_status", locale=norm_loc), str(sections["status"]))
    metric_assignee.metric(t("case_metric_assignee", locale=norm_loc), str(sections["assignee"]))
    metric_version.metric(t("case_metric_version", locale=norm_loc), detail.case.version)

    if trace.status == "available":
        if on_open_trace and st.button(t("case_btn_open_trace", locale=norm_loc), type="primary"):
            on_open_trace(trace)
            return
    else:
        st.warning(t("case_trace_missing_warning", locale=norm_loc))

    st.markdown(f"### {t('case_section_evidence', locale=norm_loc)}")
    if sections["evidence"]:
        st.dataframe(sections["evidence"], use_container_width=True, hide_index=True)
    else:
        st.info(t("case_evidence_empty", locale=norm_loc))

    st.markdown(f"### {t('case_section_timeline', locale=norm_loc)}")
    st.dataframe(sections["timeline"], use_container_width=True, hide_index=True)

    st.markdown(f"### {t('case_section_checklist', locale=norm_loc)}")
    if sections["checklist"]:
        st.dataframe(sections["checklist"], use_container_width=True, hide_index=True)
    else:
        st.caption(t("case_checklist_empty", locale=norm_loc))

    with st.expander(t("case_expander_update", locale=norm_loc), expanded=False):
        with st.form(f"wsc_case_transition_{selected_case_id}"):
            new_status = st.selectbox(
                t("case_label_new_status", locale=norm_loc),
                options=_EDITABLE_STATUSES,
                format_func=lambda value: _status_label(value, locale=norm_loc),
            )
            rationale = st.text_area(t("case_label_rationale", locale=norm_loc))
            if st.form_submit_button(t("case_btn_submit_update", locale=norm_loc)):
                try:
                    service.transition_case(
                        selected_case_id,
                        expected_version=detail.case.version,
                        new_status=new_status,
                        rationale=rationale,
                    )
                    st.success(t("case_update_success", locale=norm_loc))
                    st.rerun()
                except CaseValidationError as error:
                    st.error(safe_case_error_message(error, locale=norm_loc))

        with st.form(f"wsc_case_assign_{selected_case_id}"):
            assignee = st.text_input(t("case_assign_assignee_id_label", locale=norm_loc))
            if st.form_submit_button(t("case_assign_submit_btn", locale=norm_loc)):
                try:
                    service.assign_case(
                        selected_case_id, expected_version=detail.case.version, assignee_id=assignee
                    )
                    st.success(t("case_assign_success", locale=norm_loc))
                    st.rerun()
                except CaseValidationError as error:
                    st.error(safe_case_error_message(error, locale=norm_loc))

        with st.form(f"wsc_case_checklist_{selected_case_id}"):
            description = st.text_input(t("case_checklist_input_label", locale=norm_loc))
            if st.form_submit_button(t("case_checklist_submit_btn", locale=norm_loc)):
                try:
                    service.add_checklist_item(
                        selected_case_id,
                        expected_version=detail.case.version,
                        description=description,
                    )
                    st.success(t("case_checklist_success", locale=norm_loc))
                    st.rerun()
                except CaseValidationError as error:
                    st.error(safe_case_error_message(error, locale=norm_loc))

    with st.expander(t("case_attach_expander", locale=norm_loc), expanded=False):
        st.caption(t("case_attach_caption", locale=norm_loc))
        with st.form(f"wsc_case_evidence_{selected_case_id}"):
            source_store = st.selectbox(
                t("case_attach_store_label", locale=norm_loc),
                tuple(_STORE_LABELS),
                format_func=lambda value: _store_label(value, locale=norm_loc),
            )
            source_id = st.text_input(t("case_attach_source_id_label", locale=norm_loc))
            source_version = st.text_input(t("case_attach_version_label", locale=norm_loc))
            locator = st.text_input(t("case_attach_locator_label", locale=norm_loc))
            title = st.text_input(t("case_attach_title_label", locale=norm_loc))
            content_digest = st.text_input(t("case_attach_digest_label", locale=norm_loc))
            provenance = st.selectbox(
                t("case_attach_provenance_label", locale=norm_loc),
                tuple(_PROVENANCE_LABELS),
                format_func=lambda value: _provenance_label(value, locale=norm_loc),
            )
            if st.form_submit_button(t("case_attach_submit_btn", locale=norm_loc)):
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
                    st.success(t("case_attach_success", locale=norm_loc))
                    st.rerun()
                except CaseValidationError as error:
                    st.error(safe_case_error_message(error, locale=norm_loc))
