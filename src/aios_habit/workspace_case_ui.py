"""Multilingual Streamlit views for the supported Workspace case workflow (vi, ja, zh-CN)."""
from __future__ import annotations

from aios_habit.knowledge_publication import (
    KnowledgePublisher,
    LibraryWriterBusyError,
    PublicationAcceptanceError,
    PublicationError,
    PublicationPackage,
    PublicationReceipt,
    UnapprovedArtifactPublicationError,
    seal_publication_package,
)
from aios_habit.controlled_knowledge_artifact import (
    APPROVAL_ACTION_APPROVE,
    APPROVAL_ACTION_REJECT,
    APPROVAL_ACTION_REQUEST_CHANGE,
    APPROVAL_ACTION_REVOKE,
    ARTIFACT_STATUS_APPROVED,
    ARTIFACT_STATUS_CANDIDATE,
    ARTIFACT_STATUS_CHANGES_REQUESTED,
    ARTIFACT_STATUS_REJECTED,
    ARTIFACT_STATUS_REVOKED,
    ArtifactDiffReport,
    ConflictedClaimArtifactError,
    ControlledArtifactError,
    ControlledKnowledgeArtifact,
    SelfApprovalDeniedError,
    StaleArtifactDigestError,
    generate_artifact_diff,
)

from typing import Callable, Iterable, Optional
import re
from pathlib import Path

import streamlit as st

from aios_habit.knowledge_coverage import KnowledgeGapCandidate
from aios_habit.workspace_case_models import CaseDetail, CaseFilter, CaseRecord, TraceResolution
from aios_habit.workspace_case_service import CaseValidationError, WorkspaceCaseService
from aios_habit.workspace_case_repository import WorkspaceCaseRepositoryError
from aios_habit.expert_interview_models import (
    InterviewPlan,
    InterviewSession,
    InterviewTurn,
    SESSION_STATE_ACTIVE,
    SESSION_STATE_PAUSED,
    SESSION_STATE_COMPLETED,
    SESSION_STATE_STOPPED,
    SESSION_STATE_BLOCKED,
)
from aios_habit.expert_interview_service import ExpertInterviewService
from aios_habit.expert_interview_repository import ExpertInterviewRepository
from aios_habit.expert_identity import VerifiedPrincipal
from aios_habit.local_transcription import (
    ConsentRecord,
    CONSENT_STATE_GRANTED,
    CONSENT_STATE_DECLINED,
    CONSENT_STATE_WITHDRAWN,
    LocalWhisperCppTranscriptionAdapter,
    TranscriptionReceipt,
    TranscriptionSegment,
)
from aios_habit.ui_safety import safe_vietnamese_ui_message
from aios_habit.i18n import DEFAULT_LOCALE, normalize_locale, t
from aios_habit.coding_assistant import (
    CodingProposal,
    create_coding_task_pack,
    create_coding_proposal,
    approve_coding_proposal,
    reject_coding_proposal,
    build_observed_evidence,
    verify_coding_execution,
    ScopeViolationError,
    ProposalStateError,
)
from aios_habit.agent_result_import import (
    load_agent_report,
    VERIFIED_PASS,
    FAIL,
    REVIEW_REQUIRED,
    INVALID_REPORT,
)


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
_EXPERT_DECISION_LABELS = {
    "confirmed": "Xác nhận",
    "rejected": "Bác bỏ",
    "needs_more_evidence": "Cần thêm bằng chứng",
    "conflicted": "Xung đột",
}
_LESSON_STATUS_LABELS = {
    "candidate": "Ứng viên",
    "approved": "Đã duyệt",
    "revoked": "Đã thu hồi",
}
_LESSON_ERROR_MESSAGES = {
    "LESSON_PROPOSE_CONFIRMED_REVIEW_REQUIRED": "Chỉ có thể đề xuất bài học từ thẩm định đã được xác nhận (confirmed).",
    "LESSON_TITLE_REQUIRED": "Tiêu đề bài học kinh nghiệm không được để trống.",
    "LESSON_CONTENT_REQUIRED": "Nội dung bài học kinh nghiệm không được để trống.",
    "LESSON_REVOKE_REASON_REQUIRED": "Vui lòng nhập lý do thu hồi bài học kinh nghiệm.",
    "CASE_LESSON_NOT_FOUND": "Không tìm thấy bài học kinh nghiệm yêu cầu.",
    "CASE_LESSON_NOT_CANDIDATE": "Chỉ có thể phê duyệt bài học đang ở trạng thái ứng viên.",
    "CONCURRENT_UPDATE_CONFLICT": "Dữ liệu bài học đã bị thay đổi bởi thao tác khác. Vui lòng tải lại trang và thử lại.",
}
_INVESTIGATION_ERROR_MESSAGES = {
    "CLUE_RELEVANCE_INVALID": "Giá trị đánh giá độ liên quan không hợp lệ.",
    "CASE_EVIDENCE_NOT_FOUND": "Không tìm thấy manh mối hoặc bằng chứng trong hồ sơ.",
    "CLUE_RELEVANCE_RATIONALE_REQUIRED": "Vui lòng nhập lý do đánh giá độ liên quan.",
}
_ARTIFACT_TYPE_LABELS = {
    "sop": "Quy trình thao tác chuẩn",
    "report": "Báo cáo điều tra sự cố",
}
_ARTIFACT_STATUS_LABELS = {
    "draft": "Dự thảo",
    "approved": "Đã duyệt",
    "superseded": "Đã thay thế",
}
_ARTIFACT_ERROR_MESSAGES = {
    "ARTIFACT_TYPE_INVALID": "Loại tài liệu đầu ra không phù hợp. Hệ thống chỉ hỗ trợ quy trình thao tác chuẩn hoặc báo cáo điều tra.",
    "ARTIFACT_TITLE_REQUIRED": "Vui lòng nhập tiêu đề cho tài liệu đầu ra.",
    "ARTIFACT_CONTENT_REQUIRED": "Nội dung tài liệu đầu ra không được để trống.",
    "ARTIFACT_INSUFFICIENT_EVIDENCE": "Hồ sơ chưa có đủ bằng chứng hợp lệ để soạn thảo tài liệu có kiểm soát.",
    "CASE_ARTIFACT_NOT_FOUND": "Không tìm thấy tài liệu đầu ra được chỉ định.",
    "APPROVED_ARTIFACT_IMMUTABLE": "Tài liệu đã được phê duyệt không thể sửa trực tiếp. Vui lòng lập dự thảo mới.",
    "UNAPPROVED_ARTIFACT_EXPORT_FORBIDDEN": "Chỉ tài liệu đã được phê duyệt mới được phép xuất ra thư mục an toàn.",
    "CASE_ARTIFACT_NOT_DRAFT": "Chỉ tài liệu ở trạng thái dự thảo mới có thể phê duyệt.",
}
_EDITABLE_STATUSES = ("draft", "triaged", "in_progress", "waiting_evidence")

_GAP_TYPE_LABELS = {
    "missing_threshold": "Thiếu thông số kỹ thuật",
    "conflict": "Mâu thuẫn thông tin giữa các tài liệu",
    "stale": "Thông tin đã cũ hoặc hết hạn",
    "missing_source": "Thiếu tài liệu nguồn kiểm chứng",
    "unverified_claim": "Nhận định chưa được kiểm chứng",
}
_GAP_STATUS_LABELS = {
    "candidate": "Đang chờ xem xét",
    "accepted": "Đã chấp thuận để phỏng vấn",
    "merged": "Đã gộp vào nội dung khác",
    "deferred": "Tạm hoãn xem xét",
    "rejected": "Đã từ chối",
}
_GAP_DECISION_LABELS = {
    "accept": "Chấp thuận để phỏng vấn",
    "merge": "Gộp vào nội dung khác",
    "defer": "Tạm hoãn xem xét",
    "reject": "Từ chối",
}
_GAP_ERROR_MESSAGES = {
    "GAP_NOT_FOUND": "Không tìm thấy nội dung còn thiếu yêu cầu.",
    "GAP_STALE_DIGEST": "Nội dung này đã được cập nhật ở nơi khác. Vui lòng tải lại và thử lại.",
    "GAP_DECISION_INVALID": "Quyết định xem xét không hợp lệ.",
    "GAP_EVIDENCE_REQUIRED": "Nội dung còn thiếu phải có ít nhất một bằng chứng tham chiếu.",
}

_INTERVIEW_SESSION_STATE_LABELS = {
    "ready": "Sẵn sàng",
    "active": "Đang phỏng vấn",
    "paused": "Tạm dừng",
    "awaiting_confirmation": "Chờ xác nhận",
    "completed": "Hoàn tất",
    "stopped": "Đã dừng",
    "blocked": "Bị khóa thẩm quyền",
}
_INTERVIEW_ANSWER_STATE_LABELS = {
    "answered": "Đã trả lời",
    "unknown": "Không rõ / Chưa nắm được",
    "uncertain": "Chưa chắc chắn",
    "skipped": "Bỏ qua",
    "corrected": "Đã đính chính",
}


def _session_state_label(state: str, locale: str = "vi") -> str:
    return _INTERVIEW_SESSION_STATE_LABELS.get(state, state)


def _turn_answer_state_label(state: str, locale: str = "vi") -> str:
    return _INTERVIEW_ANSWER_STATE_LABELS.get(state, state)


def interview_turn_rows(turns: Sequence[InterviewTurn], locale: str = "vi") -> list[dict[str, Any]]:
    norm_loc = normalize_locale(locale)
    return [
        {
            "Lượt": turn.sequence,
            "Câu hỏi": turn.question_text,
            "Câu trả lời": turn.answer_text,
            "Trạng thái": _turn_answer_state_label(turn.answer_state, locale=norm_loc),
            "Độ tin cậy": f"{int(turn.answer_confidence * 100)}%",
            "Thời điểm": turn.created_at,
        }
        for turn in turns
    ]

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
    "EXPERT_RATIONALE_REQUIRED": "case_err_expert_rationale_required",
    "EVIDENCE_DIGEST_MISMATCH": "case_err_evidence_digest_mismatch",
    "EXPERT_REQUEST_NOT_FOUND": "case_err_expert_request_not_found",
    "EXPERT_DECISION_INVALID": "case_err_expert_decision_invalid",
    "EXPERT_MISMATCH": "case_err_expert_mismatch",
    "EXPERT_QUESTION_REQUIRED": "case_err_expert_question_required",
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


def _expert_decision_label(decision: str, locale: str = "vi") -> str:
    key = f"case_expert_decision_{decision}"
    val = t(key, locale=locale)
    return val if val != key else _EXPERT_DECISION_LABELS.get(decision, decision)


def _checklist_status_label(status: str, locale: str = "vi") -> str:
    key = f"case_checklist_status_{status}"
    val = t(key, locale=locale)
    return val if val != key else _CHECKLIST_STATUS_LABELS.get(status, "Chưa xác định")


def _lesson_status_label(status: str, locale: str = "vi") -> str:
    return _LESSON_STATUS_LABELS.get(status, "Chưa xác định")


def _artifact_type_label(artifact_type: str, locale: str = "vi") -> str:
    return _ARTIFACT_TYPE_LABELS.get(artifact_type, "Tài liệu")


def _artifact_status_label(status: str, locale: str = "vi") -> str:
    return _ARTIFACT_STATUS_LABELS.get(status, status)


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
    if text in _LESSON_ERROR_MESSAGES:
        return _LESSON_ERROR_MESSAGES[text]
    if text in _INVESTIGATION_ERROR_MESSAGES:
        return _INVESTIGATION_ERROR_MESSAGES[text]
    if text in _ARTIFACT_ERROR_MESSAGES:
        return _ARTIFACT_ERROR_MESSAGES[text]
    if text in _GAP_ERROR_MESSAGES:
        return _GAP_ERROR_MESSAGES[text]
    if text in _ERROR_KEY_MAP:
        return t(_ERROR_KEY_MAP[text], locale=norm_loc)
    if isinstance(error, (ConnectionError, TimeoutError)) or "connection" in text.lower() or "timed out" in text.lower():
        return "Không thể kết nối hoặc đã hết thời gian chờ. Hãy kiểm tra kết nối và thử lại."
    fallback = t("case_err_safe_fallback", locale=norm_loc)
    if re.fullmatch(r"[A-Z][A-Z0-9_]+", text) or "Traceback" in text or re.search(r"[A-Za-z]:[\\/]", text):
        return fallback
    return safe_vietnamese_ui_message(text, fallback)


def _gap_type_label(gap_type: str, locale: str = "vi") -> str:
    return _GAP_TYPE_LABELS.get(gap_type, "Nội dung cần làm rõ")


def _gap_status_label(status: str, locale: str = "vi") -> str:
    return _GAP_STATUS_LABELS.get(status, "Đang chờ xem xét")


def _gap_decision_label(decision: str, locale: str = "vi") -> str:
    return _GAP_DECISION_LABELS.get(decision, decision)


def gap_list_rows(gaps: Iterable[KnowledgeGapCandidate], locale: str = "vi") -> list[dict[str, str]]:
    norm_loc = normalize_locale(locale)
    rows = []
    for gap in gaps:
        evidence_count = len(gap.evidence_refs)
        evidence_text = f"{evidence_count} tài liệu nguồn" if evidence_count > 0 else "Chưa có bằng chứng"
        rows.append(
            {
                "Mã nội dung": gap.gap_id,
                "Tiêu đề": gap.title,
                "Công đoạn": gap.scope,
                "Loại thiếu sót": _gap_type_label(gap.gap_type, locale=norm_loc),
                "Mức ưu tiên": _priority_label(gap.priority, locale=norm_loc),
                "Trạng thái": _gap_status_label(gap.status, locale=norm_loc),
                "Bằng chứng": evidence_text,
            }
        )
    return rows



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

    decisions = [r.decision for r in detail.expert_reviews]
    has_conflict = (
        ("confirmed" in decisions and "rejected" in decisions)
        or ("conflicted" in decisions)
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
        "expert_requests": [
            {
                "Mã yêu cầu": req.request_id,
                "Câu hỏi": req.question_text,
                "Công đoạn": req.required_scope,
                "Chuyên gia chỉ định": req.requested_expert_id or "Tùy chọn",
                "Trạng thái": req.status,
                "Hạn": req.due_at or "Không đặt",
            }
            for req in detail.expert_requests
        ],
        "expert_reviews": [
            {
                "Mã thẩm định": rev.review_id,
                "Quyết định": _expert_decision_label(rev.decision, locale=norm_loc),
                "Người thẩm định": _safe_actor_label(rev.reviewer_id, locale=norm_loc),
                "Lý do": rev.rationale,
                "Thời điểm": rev.reviewed_at,
                "Thay thế": rev.supersedes_review_id or "Bản gốc",
            }
            for rev in detail.expert_reviews
        ],
        "has_conflict": has_conflict,
        "lessons": [
            {
                "Mã bài học": les.lesson_id,
                "Tiêu đề": les.title,
                "Nội dung": les.content,
                "Trạng thái": _lesson_status_label(les.status, locale=norm_loc),
                "Phiên bản": les.version,
                "Người tạo": _safe_actor_label(les.created_by, locale=norm_loc),
                "Người duyệt": _safe_actor_label(les.approved_by, locale=norm_loc) if les.approved_by else "Chưa duyệt",
                "Thời điểm": les.updated_at,
            }
            for les in getattr(detail, "lessons", ())
        ],
        "artifacts": [
            {
                "Mã đầu ra": art.artifact_id,
                "Loại đầu ra": _artifact_type_label(art.artifact_type, locale=norm_loc),
                "Tiêu đề": art.title,
                "Trạng thái": _artifact_status_label(art.status, locale=norm_loc),
                "Phiên bản": art.version,
                "Người tạo": _safe_actor_label(art.created_by, locale=norm_loc),
                "Người duyệt": _safe_actor_label(art.approved_by, locale=norm_loc) if art.approved_by else "Chưa duyệt",
                "Đường dẫn xuất": art.exported_path or "Chưa xuất",
                "Thời điểm": art.updated_at,
            }
            for art in getattr(detail, "artifacts", ())
        ],
    }



def render_knowledge_coverage_view(
    service: WorkspaceCaseService,
    *,
    locale: str = "vi",
) -> None:
    norm_loc = normalize_locale(locale)
    st.subheader("Kiểm kê tri thức và nội dung còn thiếu")
    st.caption("Kiểm tra phạm vi tài liệu đã có, tỷ lệ bao phủ và xem xét các nội dung cần chuyên gia bổ sung.")

    col1, col2 = st.columns(2)
    with col1:
        selected_scope = st.selectbox(
            "Công đoạn cần kiểm tra",
            options=(None, "all", "lsu_optical_assembly", "lsu_mirror_mount"),
            format_func=lambda s: "Tất cả công đoạn" if s in (None, "all") else s,
            key="wsc_gap_filter_scope",
        )
    with col2:
        selected_status = st.selectbox(
            "Trạng thái nội dung thiếu",
            options=(None, "all", *tuple(_GAP_STATUS_LABELS)),
            format_func=lambda s: "Tất cả trạng thái" if s in (None, "all") else _gap_status_label(s, locale=norm_loc),
            key="wsc_gap_filter_status",
        )

    scope_filter = None if selected_scope in (None, "all") else selected_scope
    status_filter = None if selected_status in (None, "all") else selected_status

    try:
        gaps = service.list_gap_candidates(scope=scope_filter, status=status_filter)
    except Exception as error:
        st.error(safe_case_error_message(error, locale=norm_loc))
        return

    if not gaps:
        st.info("Hiện không có nội dung còn thiếu nào theo bộ lọc đã chọn.")
        return

    st.dataframe(gap_list_rows(gaps, locale=norm_loc), use_container_width=True, hide_index=True)

    gap_by_id = {g.gap_id: g for g in gaps}
    selected_gap_id = st.selectbox(
        "Chọn nội dung để xem xét",
        options=tuple(gap_by_id),
        format_func=lambda gid: f"{gid} · {gap_by_id[gid].title}",
        key="wsc_selected_gap_id",
    )

    selected_gap = gap_by_id[selected_gap_id]
    with st.expander(f"Chi tiết nội dung: {selected_gap.title}", expanded=True):
        st.write(f"**Mô tả:** {selected_gap.description}")
        st.write(f"**Công đoạn:** {selected_gap.scope}")
        st.write(f"**Loại thiếu sót:** {_gap_type_label(selected_gap.gap_type, locale=norm_loc)}")
        st.write(f"**Mức ưu tiên:** {_priority_label(selected_gap.priority, locale=norm_loc)}")
        st.write(f"**Trạng thái hiện tại:** {_gap_status_label(selected_gap.status, locale=norm_loc)}")

        if selected_gap.evidence_refs:
            st.write("**Bằng chứng tham chiếu:**")
            for ref in selected_gap.evidence_refs:
                st.markdown(f"- `{ref}`")
        else:
            st.caption("Chưa có bằng chứng đính kèm.")

        with st.form(f"wsc_review_gap_form_{selected_gap_id}"):
            decision = st.selectbox(
                "Quyết định xử lý",
                options=("accept", "merge", "defer", "reject"),
                format_func=lambda d: _gap_decision_label(d, locale=norm_loc),
            )
            rationale = st.text_area("Lý do hoặc ghi chú của người kiểm duyệt (tùy chọn)")
            submitted = st.form_submit_button("Lưu kết quả thẩm định")
            if submitted:
                try:
                    service.review_gap_candidate(
                        gap_id=selected_gap_id,
                        decision=decision,
                        rationale=rationale,
                        expected_digest=selected_gap.digest,
                    )
                    st.success("Đã cập nhật trạng thái nội dung còn thiếu thành công.")
                    st.rerun()
                except CaseValidationError as error:
                    st.error(safe_case_error_message(error, locale=norm_loc))



def render_expert_interview_view(
    service: WorkspaceCaseService,
    *,
    locale: str = "vi",
) -> None:
    norm_loc = normalize_locale(locale)
    st.subheader("Phỏng vấn chuyên gia thu thập tri thức kỹ thuật")
    st.caption("Khung đối thoại có kiểm soát và thích nghi nhằm làm rõ các khoảng trống tri thức công đoạn.")

    interview_repo = ExpertInterviewRepository(service.repository.database_path)
    interview_svc = ExpertInterviewService(store=service.repository, interview_repo=interview_repo, actor_context=service.actor_context)

    # Hiển thị danh sách các phiên hiện có
    existing_sessions = interview_repo.list_sessions()
    session_options = [s.session_id for s in existing_sessions]

    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        selected_session_id = st.selectbox(
            "Chọn phiên phỏng vấn hiện có",
            options=["new"] + session_options,
            format_func=lambda sid: "Tạo phiên phỏng vấn mới" if sid == "new" else f"Phiên {sid} ({_session_state_label(next((s.state for s in existing_sessions if s.session_id == sid), ''))})",
            key="wsc_interview_sel_session",
        )

    # Tạo phiên mới
    if selected_session_id == "new":
        st.markdown("#### Khởi tạo phiên phỏng vấn mới từ khoảng trống tri thức đã chấp thuận")
        accepted_gaps = service.list_gap_candidates(status="accepted")
        if not accepted_gaps:
            st.info("Chưa có khoảng trống tri thức nào ở trạng thái 'Đã chấp thuận' (accepted). Vui lòng thẩm định tại tab Kiểm kê tri thức trước.")
            return

        with st.form("wsc_create_interview_session_form"):
            gap_choices = {g.gap_id: g for g in accepted_gaps}
            sel_gap_id = st.selectbox(
                "Khoảng trống tri thức mục tiêu",
                options=tuple(gap_choices),
                format_func=lambda gid: f"{gid} · {gap_choices[gid].title} ({gap_choices[gid].scope})",
            )
            sel_gap = gap_choices[sel_gap_id]
            eligible = interview_svc.resolve_eligible_experts(sel_gap.scope)
            if not eligible:
                st.warning(f"Chưa có chuyên gia nào có thẩm quyền cho công đoạn '{sel_gap.scope}'.")
                sel_expert = ""
            else:
                sel_expert = st.selectbox("Chuyên gia thực hiện phỏng vấn", options=eligible)

            turns_budget = st.number_input("Số lượt tối đa (ngân sách)", min_value=1, max_value=50, value=10)
            create_btn = st.form_submit_button("Tạo kế hoạch và bắt đầu phiên phỏng vấn")

            if create_btn:
                if not sel_expert:
                    st.error("Không thể bắt đầu phiên khi chưa chọn chuyên gia đủ thẩm quyền.")
                else:
                    try:
                        from aios_habit.expert_interview_models import InterviewBudget, CompletionRubric
                        plan = interview_svc.create_interview_plan(
                            gap_id=sel_gap_id,
                            budget=InterviewBudget(max_turns=int(turns_budget), max_minutes=30, token_budget=4000),
                            completion_rubric=CompletionRubric(
                                required_aspects=("threshold", "unit", "exceptions"),
                                escalation_owner=service.actor_context.actor_id,
                            ),
                        )
                        principal = VerifiedPrincipal(
                            subject=sel_expert,
                            provider_name="local_interactive",
                            display_name=sel_expert,
                        )
                        new_sess = interview_svc.start_interview_session(
                            plan_id=plan.plan_id,
                            principal=principal,
                            expert_id=sel_expert,
                            idempotency_key=f"START-{plan.plan_id}",
                        )
                        st.success(f"Đã khởi tạo phiên phỏng vấn thành công: {new_sess.session_id}")
                        st.session_state["wsc_active_interview_session_id"] = new_sess.session_id
                        st.rerun()
                    except Exception as err:
                        st.error(safe_vietnamese_ui_message(str(err)))
        return

    # Phiên đang được chọn
    curr_session = interview_repo.get_session(selected_session_id)
    if curr_session is None:
        st.error("Không tìm thấy dữ liệu của phiên đã chọn.")
        return

    plan = interview_svc.get_interview_plan(curr_session.plan_id)
    max_turns = plan.budget.max_turns if plan else 10

    # Hiển thị thanh trạng thái & tiến độ
    turns = interview_repo.list_turns(curr_session.session_id)
    turns_count = len(turns)
    progress_pct = min(1.0, turns_count / max_turns)

    m1, m2, m3 = st.columns(3)
    m1.metric("Trạng thái phiên", _session_state_label(curr_session.state, locale=norm_loc))
    m2.metric("Tiến độ lượt phỏng vấn", f"{turns_count} / {max_turns} lượt")
    m3.metric("Chuyên gia tham gia", curr_session.expert_id)

    st.progress(progress_pct, text=f"Tiến độ hoàn thành: {int(progress_pct * 100)}%")

    if curr_session.state == SESSION_STATE_PAUSED:
        st.warning("Phiên phỏng vấn hiện đang tạm dừng.")
        if st.button("Tiếp tục phiên phỏng vấn", type="primary"):
            try:
                principal = VerifiedPrincipal(
                    subject=curr_session.principal_subject_id,
                    provider_name="local_interactive",
                    display_name=curr_session.expert_id,
                )
                interview_svc.resume_interview_session(curr_session.session_id, principal=principal)
                st.success("Đã tiếp tục lại phiên phỏng vấn.")
                st.rerun()
            except Exception as err:
                st.error(safe_vietnamese_ui_message(str(err)))

    elif curr_session.state in (SESSION_STATE_COMPLETED, SESSION_STATE_STOPPED, SESSION_STATE_BLOCKED):
        st.info(f"Phiên phỏng vấn đã kết thúc với trạng thái: {_session_state_label(curr_session.state, locale=norm_loc)}. Lý do: {curr_session.stop_reason or 'Hoàn tất quy trình'}.")

    # Khung hiển thị lịch sử hội thoại
    st.markdown("#### Lịch sử các lượt trao đổi")
    if turns:
        for t_item in turns:
            with st.chat_message("assistant"):
                st.write(f"**Hệ thống (Lượt {t_item.sequence}):** {t_item.question_text}")
            with st.chat_message("user"):
                status_lbl = _turn_answer_state_label(t_item.answer_state, locale=norm_loc)
                st.write(f"**Chuyên gia ({curr_session.expert_id}):** {t_item.answer_text}")
                st.caption(f"Trạng thái ghi nhận: {status_lbl} | Thời điểm: {t_item.created_at}")
    else:
        st.caption("Chưa có lượt trao đổi nào trong phiên này.")

    # Nếu phiên đang active thì cho phép trả lời
    if curr_session.state == SESSION_STATE_ACTIVE:
        st.markdown("#### Đồng ý ghi âm và chép lời cục bộ (Tùy chọn)")
        current_consent = interview_repo.get_consent(curr_session.session_id)
        consent_is_granted = current_consent is not None and current_consent.is_active

        if consent_is_granted:
            st.success("🔴 Đang kích hoạt ghi âm âm thanh cục bộ (an toàn, không tải lên mạng).")
            st.caption(f"Mã đồng ý: {current_consent.consent_id} · Phiên bản: {current_consent.version} · Lưu trữ: Chỉ trong máy nội bộ")
            if st.button("Rút lại sự đồng ý ghi âm", key=f"btn_withdraw_{curr_session.session_id}"):
                withdrawn_consent = ConsentRecord(
                    consent_id=current_consent.consent_id,
                    session_id=current_consent.session_id,
                    subject=current_consent.subject,
                    version=current_consent.version,
                    state=CONSENT_STATE_WITHDRAWN,
                    purposes=current_consent.purposes,
                    retention_policy=current_consent.retention_policy,
                    granted_at=current_consent.granted_at,
                    withdrawn_at=datetime.now(timezone.utc).isoformat(),
                )
                interview_repo.save_consent(withdrawn_consent, f"IDEMP-WITHDRAW-{curr_session.session_id}")
                st.warning("Đã rút lại sự đồng ý ghi âm. Hệ thống chuyển sang chế độ trả lời bằng văn bản thuần túy.")
                st.rerun()

            # Khung chép lời âm thanh khi đã đồng ý
            st.markdown("##### Tải lên tệp âm thanh để chép lời tự động")
            uploaded_audio = st.file_uploader(
                "Chọn tệp âm thanh (định dạng WAV mono 16kHz)",
                type=["wav"],
                key=f"audio_upload_{curr_session.session_id}",
            )
            col_tr1, col_tr2 = st.columns([2, 1])
            with col_tr1:
                use_fixture = st.checkbox("Sử dụng bản ghi âm mẫu kiểm chuẩn (fixture 16kHz)", value=True, key=f"chk_fix_{curr_session.session_id}")
            with col_tr2:
                btn_run_transcribe = st.button("Chép lời âm thanh cục bộ", key=f"btn_transcribe_{curr_session.session_id}")

            if btn_run_transcribe:
                audio_file_path = None
                if uploaded_audio is not None:
                    # Save temporarily into local_cases
                    temp_dir = Path("local_cases") / "audio_uploads"
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    target_file = temp_dir / uploaded_audio.name
                    target_file.write_bytes(uploaded_audio.getvalue())
                    audio_file_path = target_file
                elif use_fixture:
                    fixture_audio = Path("tests") / "fixtures" / "expert_interview" / "audio" / "sample_interview_sine_16k.wav"
                    if fixture_audio.exists():
                        audio_file_path = fixture_audio

                if audio_file_path and audio_file_path.exists():
                    manifest_path = Path("tests") / "fixtures" / "expert_interview" / "audio" / "mock_transcription_manifest.json"
                    adapter = LocalWhisperCppTranscriptionAdapter(
                        fallback_mock_engine=MockLocalTranscriptionEngine(fixture_manifest_path=manifest_path)
                    )
                    try:
                        receipt = adapter.transcribe(
                            audio_path=audio_file_path,
                            session_id=curr_session.session_id,
                            consent=current_consent,
                        )
                        interview_repo.save_transcription_receipt(receipt, f"IDEMP-TRCP-{receipt.receipt_id}")
                        st.session_state[f"last_receipt_{curr_session.session_id}"] = receipt
                        st.success("Chép lời âm thanh cục bộ thành công.")
                    except Exception as exc:
                        thong_bao_loi = safe_vietnamese_ui_message(str(exc))
                        st.error(thong_bao_loi)
                else:
                    st.error("Vui lòng chọn hoặc tải lên tệp âm thanh hợp lệ.")

            # Hiển thị kết quả chép lời và xác nhận mã máy, con số, đơn vị (T045)
            last_receipt = st.session_state.get(f"last_receipt_{curr_session.session_id}")
            if last_receipt:
                st.markdown("##### Kết quả chép lời và xác nhận thông số kỹ thuật")
                st.info(f"**Văn bản nhận dạng:** {last_receipt.full_text}")
                if last_receipt.all_critical_tokens:
                    st.write("**Các thông số, mã thiết bị và đơn vị đo được nhận dạng:**")
                    st.write(", ".join(f"`{tok}`" for tok in last_receipt.all_critical_tokens))

                # Xác nhận đưa vào câu trả lời
                if st.button("Xác nhận thông số và điền vào ô câu trả lời", key=f"btn_confirm_tokens_{curr_session.session_id}"):
                    st.session_state[f"ans_text_{curr_session.session_id}"] = last_receipt.full_text
                    st.success("Đã điền nội dung chép lời đã xác nhận vào ô phản hồi.")
                    st.rerun()

        else:
            st.info("Chế độ ghi âm hiện đang tắt. Chuyên gia có thể trả lời trực tiếp bằng văn bản bên dưới hoặc cấp quyền ghi âm.")
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                if st.button("Chấp thuận ghi âm và chép lời (Phiên bản 1.0)", key=f"btn_grant_{curr_session.session_id}"):
                    new_consent = ConsentRecord(
                        consent_id=f"CSNT-{curr_session.session_id}-{int(datetime.now(timezone.utc).timestamp())}",
                        session_id=curr_session.session_id,
                        subject=curr_session.principal_subject_id,
                        version="1.0",
                        state=CONSENT_STATE_GRANTED,
                        purposes=("audio_recording", "local_transcription"),
                        retention_policy="local_only_retained",
                        granted_at=datetime.now(timezone.utc).isoformat(),
                    )
                    interview_repo.save_consent(new_consent, f"IDEMP-GRANT-{curr_session.session_id}")
                    st.success("Đã kích hoạt đồng ý ghi âm thành công.")
                    st.rerun()
            with col_c2:
                if st.button("Từ chối ghi âm (Tiếp tục bằng văn bản)", key=f"btn_decline_{curr_session.session_id}"):
                    declined_consent = ConsentRecord(
                        consent_id=f"CSNT-{curr_session.session_id}-{int(datetime.now(timezone.utc).timestamp())}",
                        session_id=curr_session.session_id,
                        subject=curr_session.principal_subject_id,
                        version="1.0",
                        state=CONSENT_STATE_DECLINED,
                        purposes=("text_only",),
                        retention_policy="local_only_retained",
                        granted_at=None,
                        withdrawn_at=None,
                    )
                    interview_repo.save_consent(declined_consent, f"IDEMP-DECLINE-{curr_session.session_id}")
                    st.info("Đã ghi nhận lựa chọn chỉ sử dụng văn bản.")
                    st.rerun()

        st.markdown("#### Phản hồi lượt phỏng vấn tiếp theo")
        next_q = plan.seed_questions[0].text if (plan and plan.seed_questions and not turns) else f"Câu hỏi làm rõ lượt {turns_count + 1}"
        st.info(f"**Câu hỏi hiện tại:** {next_q}")

        with st.form(f"wsc_answer_turn_form_{curr_session.session_id}"):
            ans_input = st.text_area("Nhập câu trả lời của chuyên gia", key=f"ans_text_{curr_session.session_id}")
            col_b1, col_b2, col_b3, col_b4 = st.columns(4)
            with col_b1:
                submit_ans = st.form_submit_button("Gửi câu trả lời", type="primary")
            with col_b2:
                btn_unknown = st.form_submit_button("Chưa rõ thông tin")
            with col_b3:
                btn_pause = st.form_submit_button("Tạm dừng phiên")
            with col_b4:
                btn_stop = st.form_submit_button("Dừng phiên phỏng vấn")

            final_ans = None
            if submit_ans:
                final_ans = ans_input.strip()
            elif btn_unknown:
                final_ans = "không rõ"
            elif btn_pause:
                final_ans = "tạm dừng"
            elif btn_stop:
                final_ans = "dừng"

            if final_ans:
                try:
                    principal = VerifiedPrincipal(
                        subject=curr_session.principal_subject_id,
                        provider_name="local_interactive",
                        display_name=curr_session.expert_id,
                    )
                    from uuid import uuid4
                    interview_svc.submit_interview_turn(
                        session_id=curr_session.session_id,
                        answer_text=final_ans,
                        principal=principal,
                        idempotency_key=f"TURN-{curr_session.session_id}-{turns_count + 1}-{uuid4().hex[:6]}",
                        question_override=next_q,
                    )
                    st.success("Đã ghi nhận phản hồi thành công.")
                    st.rerun()
                except Exception as err:
                    st.error(safe_vietnamese_ui_message(str(err)))


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

    view_mode = st.radio(
        "Khu vực làm việc",
        options=("cases", "coverage", "interview"),
        format_func=lambda m: "Hồ sơ sự vụ" if m == "cases" else ("Kiểm kê tri thức & Nội dung còn thiếu" if m == "coverage" else "Phỏng vấn chuyên gia"),
        horizontal=True,
        label_visibility="collapsed",
        key="wsc_workspace_view_mode",
    )
    if view_mode == "coverage":
        render_knowledge_coverage_view(service, locale=norm_loc)
        return
    elif view_mode == "interview":
        render_expert_interview_view(service, locale=norm_loc)
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

    st.markdown(f"### {t('case_section_expert_review', locale=norm_loc)}")
    if sections.get("has_conflict"):
        st.warning(t("case_expert_conflict_warning", locale=norm_loc))

    if sections.get("expert_requests"):
        st.dataframe(sections["expert_requests"], use_container_width=True, hide_index=True)
    if sections.get("expert_reviews"):
        st.markdown(f"#### {t('case_expert_reviews_heading', locale=norm_loc)}")
        st.dataframe(sections["expert_reviews"], use_container_width=True, hide_index=True)
    if not sections.get("expert_requests") and not sections.get("expert_reviews"):
        st.info(t("case_expert_empty", locale=norm_loc))

    with st.expander(t("case_expert_request_expander", locale=norm_loc), expanded=False):
        with st.form(f"wsc_case_expert_req_{selected_case_id}"):
            req_question = st.text_area(t("case_expert_req_question", locale=norm_loc))
            req_scope = st.text_input(t("case_expert_req_scope", locale=norm_loc), value=detail.case.scope)
            has_second_expert = st.checkbox("Chỉ định chuyên gia cụ thể", value=False)
            req_assignee = ""
            if has_second_expert:
                req_assignee = st.text_input(t("case_expert_req_assignee", locale=norm_loc))
            req_due = st.text_input(t("case_expert_req_due", locale=norm_loc), placeholder="YYYY-MM-DD")
            if st.form_submit_button(t("case_expert_btn_request", locale=norm_loc)):
                try:
                    service.request_expert_review(
                        selected_case_id,
                        claim_digest=detail.case.evidence_digest,
                        question=req_question,
                        required_scope=req_scope or detail.case.scope,
                        requested_expert_id=req_assignee if has_second_expert else None,
                        due_at=req_due if req_due.strip() else None,
                    )
                    st.success("Đã tạo yêu cầu thẩm định chuyên gia thành công.")
                    st.rerun()
                except CaseValidationError as error:
                    st.error(safe_case_error_message(error, locale=norm_loc))

    open_requests = [r for r in detail.expert_requests if r.status == "open"]
    if open_requests:
        with st.expander(t("case_expert_review_expander", locale=norm_loc), expanded=False):
            with st.form(f"wsc_case_expert_rev_{selected_case_id}"):
                req_choice = st.selectbox(
                    "Chọn yêu cầu cần thẩm định",
                    options=[r.request_id for r in open_requests],
                    format_func=lambda rid: f"{rid} - {next((r.question_text[:40] for r in open_requests if r.request_id == rid), '')}",
                )
                rev_decision = st.selectbox(
                    "Quyết định thẩm định",
                    options=["confirmed", "rejected", "needs_more_evidence"],
                    format_func=lambda d: _expert_decision_label(d, locale=norm_loc),
                )
                rev_rationale = st.text_area("Lý do thẩm định (bắt buộc)")
                supersedes_choice = None
                if detail.expert_reviews:
                    supersede_check = st.checkbox("Đính chính ý kiến thẩm định trước đó", value=False)
                    if supersede_check:
                        supersedes_choice = st.selectbox(
                            "Ý kiến bị thay thế",
                            options=[r.review_id for r in detail.expert_reviews],
                        )
                if st.form_submit_button(t("case_expert_btn_review", locale=norm_loc)):
                    try:
                        service.record_expert_review(
                            req_choice,
                            decision=rev_decision,
                            rationale=rev_rationale,
                            supersedes_review_id=supersedes_choice,
                        )
                        st.success("Đã lưu kết quả thẩm định thành công.")
                        st.rerun()
                    except CaseValidationError as error:
                        st.error(safe_case_error_message(error, locale=norm_loc))

    if sections.get("has_conflict"):
        with st.expander(t("case_expert_conflict_expander", locale=norm_loc), expanded=True):
            with st.form(f"wsc_case_conflict_{selected_case_id}"):
                st.caption("Chuyên viên trưởng có thẩm quyền phân xử ý kiến thẩm định trái chiều.")
                conf_decision = st.selectbox(
                    "Quyết định phân xử cuối cùng",
                    options=["confirmed", "rejected", "needs_more_evidence"],
                    format_func=lambda d: _expert_decision_label(d, locale=norm_loc),
                )
                conf_rationale = st.text_area("Lý do và căn cứ phân xử")
                if st.form_submit_button(t("case_expert_btn_resolve", locale=norm_loc)):
                    try:
                        service.resolve_review_conflict(
                            selected_case_id,
                            review_ids=[r.review_id for r in detail.expert_reviews],
                            decision=conf_decision,
                            rationale=conf_rationale,
                        )
                        st.success("Đã ghi nhận kết quả phân xử thành công.")
                        st.rerun()
                    except CaseValidationError as error:
                        st.error(safe_case_error_message(error, locale=norm_loc))

    st.markdown("### Bài học kinh nghiệm từ thẩm định")
    if sections.get("lessons"):
        st.dataframe(sections["lessons"], use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có bài học kinh nghiệm nào được liên kết với hồ sơ này.")

    confirmed_reviews = [r for r in detail.expert_reviews if r.decision == "confirmed"]
    if confirmed_reviews:
        with st.expander("Đề xuất bài học kinh nghiệm mới", expanded=False):
            with st.form(f"wsc_case_lesson_propose_{selected_case_id}"):
                sel_rev = st.selectbox(
                    "Chọn thẩm định xác nhận gốc",
                    options=[r.review_id for r in confirmed_reviews],
                    format_func=lambda rid: f"{rid} · {next((r.rationale[:50] for r in confirmed_reviews if r.review_id == rid), '')}",
                )
                les_title = st.text_input("Tiêu đề bài học kinh nghiệm")
                les_content = st.text_area("Nội dung bài học và giải pháp khuyến nghị")
                if st.form_submit_button("Lưu bài học ứng viên"):
                    try:
                        service.propose_lesson(
                            selected_case_id,
                            sel_rev,
                            title=les_title,
                            content=les_content,
                        )
                        st.success("Đã lưu bài học kinh nghiệm ứng viên thành công.")
                        st.rerun()
                    except CaseValidationError as error:
                        st.error(safe_case_error_message(error, locale=norm_loc))

    candidate_lessons = [l for l in getattr(detail, "lessons", ()) if l.status == "candidate"]
    if candidate_lessons:
        with st.expander("Phê duyệt hoặc thu hồi bài học kinh nghiệm (Quản lý QC)", expanded=False):
            with st.form(f"wsc_case_lesson_manage_{selected_case_id}"):
                sel_lesson_id = st.selectbox(
                    "Chọn bài học ứng viên",
                    options=[l.lesson_id for l in candidate_lessons],
                    format_func=lambda lid: f"{lid} · {next((l.title for l in candidate_lessons if l.lesson_id == lid), '')}",
                )
                sel_lesson = next((l for l in candidate_lessons if l.lesson_id == sel_lesson_id), None)
                action = st.radio("Hành động", options=["Phê duyệt bài học", "Thu hồi bài học"], horizontal=True)
                revoke_reason = st.text_input("Lý do thu hồi (nếu chọn thu hồi)", value="")
                if st.form_submit_button("Xác nhận thực hiện"):
                    if sel_lesson:
                        try:
                            if action == "Phê duyệt bài học":
                                service.approve_lesson(sel_lesson.lesson_id, expected_version=sel_lesson.version)
                                st.success("Đã phê duyệt bài học kinh nghiệm thành công.")
                            else:
                                service.revoke_lesson(
                                    sel_lesson.lesson_id,
                                    expected_version=sel_lesson.version,
                                    reason=revoke_reason,
                                )
                                st.success("Đã thu hồi bài học kinh nghiệm thành công.")
                            st.rerun()
                        except CaseValidationError as error:
                            st.error(safe_case_error_message(error, locale=norm_loc))

    st.markdown("### Tra cứu thư viện bài học kinh nghiệm đã duyệt")
    lesson_query = st.text_input("Nhập từ khóa tìm kiếm bài học", key=f"wsc_lesson_search_input_{selected_case_id}")
    if lesson_query.strip():
        approved_hits = service.search_approved_lessons(lesson_query.strip())
        if approved_hits:
            hit_rows = [
                {
                    "Mã bài học": hit.lesson_id,
                    "Tiêu đề": hit.title,
                    "Nội dung": hit.content,
                    "Hồ sơ gốc": hit.case_id,
                    "Người duyệt": _safe_actor_label(hit.approved_by, locale=norm_loc) if hit.approved_by else "",
                    "Ngày duyệt": hit.approved_at or "",
                }
                for hit in approved_hits
            ]
            st.dataframe(hit_rows, use_container_width=True, hide_index=True)
        else:
            st.info("Không tìm thấy bài học kinh nghiệm đã duyệt nào phù hợp với từ khóa.")

    st.markdown("### Trợ lý điều tra sự kiện dây chuyền")
    with st.expander("Tra cứu sự kiện và manh mối dây chuyền", expanded=False):
        with st.form(f"wsc_case_line_investigation_{selected_case_id}"):
            col1, col2 = st.columns(2)
            with col1:
                inv_station = st.text_input("Trạm máy", value=detail.case.scope if detail.case.scope else "")
                inv_code = st.text_input("Mã lỗi hoặc sự cố", value="")
            with col2:
                inv_start = st.text_input("Thời gian bắt đầu (tùy chọn)", placeholder="YYYY-MM-DDTHH:MM:SS")
                inv_end = st.text_input("Thời gian kết thúc (tùy chọn)", placeholder="YYYY-MM-DDTHH:MM:SS")
            inv_submit = st.form_submit_button("Truy vấn sự kiện")

        if inv_submit:
            if not inv_station.strip() and not inv_code.strip():
                st.warning("Vui lòng nhập trạm máy hoặc mã lỗi để bắt đầu tra cứu.")
            else:
                try:
                    from aios_habit.line_log_parser import line_events_db_path
                    from aios_habit.line_investigation import LineInvestigationScope, build_investigation_pack

                    db_path = line_events_db_path()
                    scope = LineInvestigationScope(
                        station=inv_station.strip(),
                        error_code=inv_code.strip(),
                        start_time=inv_start.strip() or None,
                        end_time=inv_end.strip() or None,
                    )
                    pack = build_investigation_pack(db_path, scope)
                    st.session_state[f"investigation_pack_{selected_case_id}"] = pack
                except Exception:
                    st.error("Không thể tải sự kiện dây chuyền. Vui lòng kiểm tra dữ liệu kho sự kiện.")

        cached_pack = st.session_state.get(f"investigation_pack_{selected_case_id}")
        if cached_pack:
            st.markdown("#### Trục thời gian sự kiện")
            if cached_pack.timeline_events:
                event_rows = [
                    {
                        "Mã sự kiện": ev.event_id,
                        "Trạm máy": ev.station,
                        "Mã lỗi": ev.code,
                        "Thời điểm": ev.occurred_at,
                        "Phân loại": ev.dialect,
                        "Trạng thái": "Nghi ngờ",
                    }
                    for ev in cached_pack.timeline_events
                ]
                st.dataframe(event_rows, use_container_width=True, hide_index=True)
                with st.form(f"wsc_case_attach_clue_{selected_case_id}"):
                    sel_event_id = st.selectbox(
                        "Chọn sự kiện để gắn vào hồ sơ vụ việc",
                        options=[ev.event_id for ev in cached_pack.timeline_events],
                        format_func=lambda eid: f"{eid} - {next((f'{ev.station} {ev.code} ({ev.occurred_at})' for ev in cached_pack.timeline_events if ev.event_id == eid), '')}",
                    )
                    if st.form_submit_button("Gắn manh mối nghi ngờ vào hồ sơ"):
                        sel_ev = next((ev for ev in cached_pack.timeline_events if ev.event_id == sel_event_id), None)
                        if sel_ev:
                            try:
                                service.attach_line_investigation_clue(
                                    selected_case_id,
                                    expected_version=detail.case.version,
                                    event_id=sel_ev.event_id,
                                    station=sel_ev.station,
                                    code=sel_ev.code,
                                    occurred_at=sel_ev.occurred_at,
                                    dialect=sel_ev.dialect,
                                    relevance="suspected",
                                )
                                st.success("Đã gắn manh mối sự kiện nghi ngờ vào hồ sơ thành công.")
                                st.rerun()
                            except CaseValidationError as error:
                                st.error(safe_case_error_message(error, locale=norm_loc))
            else:
                st.info("Không tìm thấy sự kiện nào trong phạm vi tra cứu đã chọn.")

            st.markdown("#### Nhóm hiện tượng lặp lại")
            if cached_pack.repeated_patterns:
                pattern_rows = [
                    {
                        "Trạm máy": p.station,
                        "Mã lỗi": p.code,
                        "Số lần xuất hiện": p.occurrence_count,
                        "Lần đầu": p.first_seen,
                        "Lần cuối": p.last_seen,
                    }
                    for p in cached_pack.repeated_patterns
                ]
                st.dataframe(pattern_rows, use_container_width=True, hide_index=True)
            else:
                st.caption("Chưa phát hiện hiện tượng lặp lại bất thường.")

            st.markdown("#### Dữ kiện và câu hỏi còn thiếu")
            if cached_pack.missing_clues:
                for mc in cached_pack.missing_clues:
                    st.warning(f"**{mc.field_name}**: {mc.description}\n\n*Hành động khuyến nghị*: {mc.suggested_action}")
            else:
                st.caption("Đầy đủ dữ kiện ban đầu phục vụ điều tra.")

    suspected_clues = [
        r for r in detail.evidence
        if r.evidence_node_id.startswith("line_events:")
    ]
    if suspected_clues:
        with st.expander("Thẩm định độ liên quan của manh mối dây chuyền", expanded=False):
            with st.form(f"wsc_case_clue_review_{selected_case_id}"):
                sel_ref_id = st.selectbox(
                    "Chọn manh mối sự kiện cần đánh giá",
                    options=[r.reference_id for r in suspected_clues],
                    format_func=lambda rid: f"{rid} - {next((r.source_title for r in suspected_clues if r.reference_id == rid), '')} [{next((_provenance_label(r.provenance_status, locale=norm_loc) for r in suspected_clues if r.reference_id == rid), '')}]",
                )
                clue_decision = st.selectbox(
                    "Kết luận độ liên quan",
                    options=["confirmed", "rejected"],
                    format_func=lambda d: "Xác nhận liên quan" if d == "confirmed" else "Bác bỏ liên quan",
                )
                clue_note = st.text_area("Căn cứ và lý do đánh giá")
                if st.form_submit_button("Lưu kết quả thẩm định manh mối"):
                    try:
                        service.review_clue_relevance(
                            selected_case_id,
                            sel_ref_id,
                            expected_version=detail.case.version,
                            relevance=clue_decision,
                            note=clue_note,
                        )
                        st.success("Đã cập nhật đánh giá độ liên quan của manh mối thành công.")
                        st.rerun()
                    except CaseValidationError as error:
                        st.error(safe_case_error_message(error, locale=norm_loc))

    st.markdown("### Đầu ra có kiểm soát (Báo cáo điều tra & Quy trình thao tác chuẩn)")
    if sections.get("artifacts"):
        st.dataframe(sections["artifacts"], use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có báo cáo điều tra hoặc quy trình thao tác chuẩn nào trong hồ sơ này.")

    with st.expander("Soạn dự thảo tài liệu có kiểm soát mới", expanded=False):
        with st.form(f"wsc_case_artifact_draft_{selected_case_id}"):
            art_type = st.selectbox(
                "Loại tài liệu đầu ra",
                options=["sop", "report"],
                format_func=lambda t_code: "Quy trình thao tác chuẩn" if t_code == "sop" else "Báo cáo điều tra sự cố",
            )
            art_title = st.text_input("Tiêu đề tài liệu")
            art_conclusions = st.text_area("Căn cứ bổ sung hoặc kết luận khuyến nghị (tùy chọn)")
            if st.form_submit_button("Tạo dự thảo từ bằng chứng"):
                try:
                    service.draft_case_artifact(
                        selected_case_id,
                        artifact_type=art_type,
                        title=art_title,
                        conclusions_or_grounds=art_conclusions,
                    )
                    st.success("Đã tạo dự thảo tài liệu có kiểm soát thành công.")
                    st.rerun()
                except CaseValidationError as error:
                    st.error(safe_case_error_message(error, locale=norm_loc))

    case_artifacts = getattr(detail, "artifacts", ())
    draft_artifacts = [a for a in case_artifacts if a.status == "draft"]
    if draft_artifacts:
        with st.expander("Chỉnh sửa nội dung dự thảo", expanded=False):
            sel_art_id = st.selectbox(
                "Chọn dự thảo cần sửa",
                options=[a.artifact_id for a in draft_artifacts],
                format_func=lambda aid: f"{aid} · {next((a.title for a in draft_artifacts if a.artifact_id == aid), '')}",
                key=f"wsc_sel_art_edit_{selected_case_id}",
            )
            sel_art = next((a for a in draft_artifacts if a.artifact_id == sel_art_id), None)
            if sel_art:
                with st.form(f"wsc_case_artifact_edit_{selected_case_id}_{sel_art.artifact_id}"):
                    edit_title = st.text_input("Tiêu đề", value=sel_art.title)
                    edit_content = st.text_area("Nội dung tài liệu (Markdown)", value=sel_art.content_markdown, height=250)
                    if st.form_submit_button("Lưu thay đổi dự thảo"):
                        try:
                            service.update_case_artifact(
                                sel_art.artifact_id,
                                expected_version=sel_art.version,
                                content_markdown=edit_content,
                                title=edit_title,
                            )
                            st.success("Đã lưu nội dung dự thảo mới thành công.")
                            st.rerun()
                        except CaseValidationError as error:
                            st.error(safe_case_error_message(error, locale=norm_loc))

        with st.expander("Phê duyệt tài liệu có kiểm soát (Quản lý QC)", expanded=False):
            with st.form(f"wsc_case_artifact_approve_{selected_case_id}"):
                app_art_id = st.selectbox(
                    "Chọn dự thảo cần phê duyệt",
                    options=[a.artifact_id for a in draft_artifacts],
                    format_func=lambda aid: f"{aid} · {next((a.title for a in draft_artifacts if a.artifact_id == aid), '')}",
                    key=f"wsc_sel_art_app_{selected_case_id}",
                )
                app_art = next((a for a in draft_artifacts if a.artifact_id == app_art_id), None)
                app_notes = st.text_area("Ghi chú phê duyệt của Quản lý QC", value="Đã kiểm tra bằng chứng và phê duyệt ban hành.")
                if st.form_submit_button("Xác nhận phê duyệt ban hành"):
                    if app_art:
                        try:
                            service.approve_case_artifact(
                                app_art.artifact_id,
                                expected_version=app_art.version,
                                notes=app_notes,
                            )
                            st.success("Đã phê duyệt ban hành tài liệu thành công.")
                            st.rerun()
                        except CaseValidationError as error:
                            st.error(safe_case_error_message(error, locale=norm_loc))

    approved_artifacts = [a for a in case_artifacts if a.status == "approved"]
    if approved_artifacts:
        with st.expander("Xuất tài liệu đã duyệt ra thư mục an toàn", expanded=False):
            with st.form(f"wsc_case_artifact_export_{selected_case_id}"):
                exp_art_id = st.selectbox(
                    "Chọn tài liệu đã duyệt để xuất file",
                    options=[a.artifact_id for a in approved_artifacts],
                    format_func=lambda aid: f"{aid} · {next((a.title for a in approved_artifacts if a.artifact_id == aid), '')}",
                    key=f"wsc_sel_art_exp_{selected_case_id}",
                )
                exp_art = next((a for a in approved_artifacts if a.artifact_id == exp_art_id), None)
                def_name = f"{exp_art.artifact_type}_{selected_case_id.lower().replace('-', '_')}.md" if exp_art else "tai_lieu.md"
                exp_filename = st.text_input("Tên file xuất tương đối", value=def_name)
                if st.form_submit_button("Xuất file an toàn"):
                    if exp_art:
                        try:
                            exported_rec, exported_path = service.export_case_artifact(
                                exp_art.artifact_id,
                                relative_filename=exp_filename,
                            )
                            st.success(f"Đã xuất tài liệu thành công ra file: {exported_path.name}")
                            st.rerun()
                        except CaseValidationError as error:
                            st.error(safe_case_error_message(error, locale=norm_loc))

    st.markdown("### Trợ lý lập trình trong không gian cách ly")

    with st.expander("Tạo gói công việc lập trình (Task Pack)", expanded=False):
        with st.form(f"wsc_case_coding_pack_{selected_case_id}"):
            cp_task_id = st.text_input(
                "Mã gói công việc",
                value=f"TASK_{selected_case_id.upper().replace('-', '_')}_001",
            )
            cp_objective = st.text_area(
                "Mục tiêu lập trình",
                value=f"Khắc phục sự cố theo hồ sơ {selected_case_id}",
            )
            cp_allowed_files = st.text_area(
                "Tệp tin được phép sửa đổi (mỗi dòng một tệp)",
                value="src/aios_habit/calculator.py",
            )
            cp_allowed_commands = st.text_area(
                "Lệnh kiểm thử được phép (mỗi dòng một lệnh)",
                value="uv run pytest tests/test_calc.py -v",
            )
            cp_required_tests = st.text_area(
                "Kiểm thử bắt buộc (mỗi dòng một tệp)",
                value="tests/test_calc.py",
            )
            if st.form_submit_button("Xuất gói công việc an toàn"):
                try:
                    files = [f.strip() for f in cp_allowed_files.splitlines() if f.strip()]
                    cmds = [c.strip() for c in cp_allowed_commands.splitlines() if c.strip()]
                    tests = [t.strip() for t in cp_required_tests.splitlines() if t.strip()]
                    pack, pack_sha, exp_p = create_coding_task_pack(
                        task_id=cp_task_id.strip(),
                        case_id=selected_case_id,
                        objective=cp_objective.strip(),
                        allowed_files=files,
                        allowed_commands=cmds,
                        required_tests=tests,
                    )
                    pack["pack_sha256"] = pack_sha
                    st.session_state[f"coding_task_pack_{selected_case_id}"] = pack
                    st.success("Đã tạo và xuất gói công việc thành công ra thư mục an toàn.")
                except Exception as err:
                    st.error(f"Lỗi tạo gói công việc: {err}")

    active_pack = st.session_state.get(f"coding_task_pack_{selected_case_id}")
    if active_pack:
        st.caption(f"Gói công việc hiện hành: **{active_pack['task_id']}** (Mã kiểm tra: `{active_pack['pack_sha256'][:12]}...`)")

    with st.expander("Đề xuất thay đổi mã nguồn (Coding Proposal & Diff)", expanded=False):
        if not active_pack:
            st.info("Vui lòng tạo gói công việc (Task Pack) trước khi lập đề xuất sửa đổi.")
        else:
            with st.form(f"wsc_case_coding_prop_create_{selected_case_id}"):
                prop_diff = st.text_area("Nội dung diff sửa đổi (Unified Diff)", height=150)
                prop_cmds = st.text_area(
                    "Lệnh dự kiến chạy (mỗi dòng một lệnh)",
                    value="uv run pytest tests/test_calc.py -v",
                )
                prop_risk = st.text_area("Đánh giá rủi ro", value="Rủi ro thấp, chỉ sửa đổi cục bộ trong phạm vi.")
                if st.form_submit_button("Tạo đề xuất sửa đổi"):
                    try:
                        cmds = [c.strip() for c in prop_cmds.splitlines() if c.strip()]
                        proposal = create_coding_proposal(
                            task_pack=active_pack,
                            case_id=selected_case_id,
                            diff_content=prop_diff,
                            commands_to_run=cmds,
                            risk_assessment=prop_risk,
                        )
                        st.session_state[f"coding_proposal_{selected_case_id}"] = proposal
                        st.success("Đã tạo đề xuất sửa đổi thành công.")
                        st.rerun()
                    except (ScopeViolationError, Exception) as err:
                        st.error(f"Lỗi đề xuất: {err}")

    active_proposal = st.session_state.get(f"coding_proposal_{selected_case_id}")
    if active_proposal:
        with st.expander("Thẩm định và cấp phép đề xuất lập trình", expanded=False):
            prop_status_lbl = "Chờ phê duyệt" if active_proposal.status == "pending" else ("Đã phê duyệt" if active_proposal.status == "approved" else "Đã từ chối")
            st.write(f"Mã đề xuất: **{active_proposal.proposal_id}** (Trạng thái: **{prop_status_lbl}**)")
            st.write(f"Mã kiểm tra nội dung (Digest): `{active_proposal.proposal_digest}`")
            st.code(active_proposal.diff_content, language="diff")
            st.write(f"Đánh giá rủi ro: {active_proposal.risk_assessment}")

            if active_proposal.status == "pending":
                col_app, col_rej = st.columns(2)
                with col_app:
                    with st.form(f"wsc_prop_approve_{selected_case_id}"):
                        app_note = st.text_input("Ghi chú phê duyệt", value="Đã kiểm tra diff và đồng ý.")
                        if st.form_submit_button("Cấp phép áp dụng"):
                            try:
                                approved = approve_coding_proposal(
                                    active_proposal,
                                    expected_digest=active_proposal.proposal_digest,
                                    approver="local_admin",
                                    notes=app_note,
                                )
                                st.session_state[f"coding_proposal_{selected_case_id}"] = approved
                                st.success("Đã cấp phép đề xuất thành công.")
                                st.rerun()
                            except Exception as err:
                                st.error(f"Lỗi phê duyệt: {err}")
                with col_rej:
                    with st.form(f"wsc_prop_reject_{selected_case_id}"):
                        rej_reason = st.text_input("Lý do từ chối", value="Chưa đạt yêu cầu kỹ thuật.")
                        if st.form_submit_button("Từ chối đề xuất"):
                            try:
                                rejected = reject_coding_proposal(
                                    active_proposal,
                                    reviewer="local_admin",
                                    reason=rej_reason,
                                )
                                st.session_state[f"coding_proposal_{selected_case_id}"] = rejected
                                st.warning("Đã từ chối đề xuất.")
                                st.rerun()
                            except Exception as err:
                                st.error(f"Lỗi từ chối: {err}")
            elif active_proposal.status == "approved":
                st.success(f"Đề xuất đã được cấp phép bởi: {_safe_actor_label(active_proposal.approved_by, locale=norm_loc)}")
            elif active_proposal.status == "rejected":
                st.error(f"Đề xuất đã bị từ chối. Lý do: {active_proposal.rejection_reason}")

        with st.expander("Nghiệm thu kết quả lập trình và bằng chứng thực thi", expanded=False):
            with st.form(f"wsc_verify_execution_{selected_case_id}"):
                rep_path = st.text_input("Đường dẫn tệp báo cáo kết quả thực thi (JSON)")
                has_obs = st.checkbox("Có bằng chứng kiểm thử thực tế từ bộ chạy kiểm thử cục bộ", value=True)
                if st.form_submit_button("Nghiệm thu kết quả"):
                    if not rep_path.strip():
                        st.warning("Vui lòng nhập đường dẫn tệp báo cáo kết quả.")
                    else:
                        try:
                            rep_file = Path(rep_path.strip())
                            report_dict = load_agent_report(rep_file)
                            obs_evidence = None
                            if has_obs:
                                obs_evidence = build_observed_evidence(
                                    tests_passed=True,
                                    changed_files=report_dict.get("declared_files", {}).get("changed_files", []),
                                    worktree_clean=True,
                                )
                            decision = verify_coding_execution(
                                task_pack=active_pack,
                                proposal=active_proposal,
                                report_dict=report_dict,
                                observed_evidence=obs_evidence,
                            )
                            if decision.verdict == VERIFIED_PASS:
                                st.success(f"Nghiệm thu thành công: Đạt kiểm chứng độc lập ({decision.safe_summary})")
                            elif decision.verdict == REVIEW_REQUIRED:
                                st.warning(f"Cần xem xét lại: {decision.safe_summary} - {decision.evidence_summary}")
                            else:
                                st.error(f"Nghiệm thu thất bại: {decision.safe_summary} - {decision.evidence_summary}")
                        except Exception as err:
                            st.error(f"Lỗi kiểm tra báo cáo: {err}")

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


_CONTROLLED_ARTIFACT_STATUS_LABELS = {
    "candidate": "Đang chờ phê duyệt",
    "approved": "Đã phê duyệt",
    "rejected": "Đã từ chối",
    "changes_requested": "Yêu cầu chỉnh sửa",
    "revoked": "Đã thu hồi",
}

_CONTROLLED_ARTIFACT_TYPE_LABELS = {
    "sop": "Quy trình thao tác chuẩn (SOP)",
    "lesson": "Bài học kinh nghiệm",
}


def render_controlled_artifacts_management(
    service: ExpertInterviewService,
    actor_principal: VerifiedPrincipal,
    locale: str = "vi",
) -> None:
    """Render preview, provenance map, version diff, and approval interface for controlled knowledge artifacts (T058)."""
    norm_loc = normalize_locale(locale)
    st.subheader("Quản lý Quy trình & Bài học Tri thức Chuẩn hóa")

    artifacts = service.interview_repo.list_artifacts()
    if not artifacts:
        st.info("Chưa có tài liệu quy chuẩn (SOP hoặc Bài học) nào được tạo.")
        return

    artifact_titles = [f"{a.artifact_id} - {a.title} (v{a.version}) [{_CONTROLLED_ARTIFACT_STATUS_LABELS.get(a.status, a.status)}]" for a in artifacts]
    selected_idx = st.selectbox("Chọn tài liệu cần kiểm tra / phê duyệt:", range(len(artifacts)), format_func=lambda i: artifact_titles[i])
    selected_artifact = artifacts[selected_idx]

    # Tabs: Preview, Provenance Map, Version Diff, Approval
    tab_view, tab_prov, tab_diff, tab_action = st.tabs([
        "Xem trước Nội dung",
        "Bản đồ Nguồn chứng minh",
        "So sánh Phiên bản",
        "Quyết định Phê duyệt",
    ])

    with tab_view:
        st.markdown(selected_artifact.content_markdown)
        st.caption(f"Mã kiểm tra nội dung (SHA-256 Digest): `{selected_artifact.digest}`")

    with tab_prov:
        st.write("**Danh sách phát biểu tri thức (Claims) cấu thành:**")
        for cid, stmt in selected_artifact.claim_map.items():
            st.markdown(f"- **`{cid}`**: {stmt}")
        if not selected_artifact.claim_map:
            for cid in selected_artifact.claim_ids:
                st.markdown(f"- **`{cid}`**")

    with tab_diff:
        same_id_artifacts = [a for a in artifacts if a.artifact_id == selected_artifact.artifact_id]
        if len(same_id_artifacts) > 1:
            diff_options = [f"v{a.version}" for a in same_id_artifacts]
            target_v_idx = st.selectbox("So sánh với phiên bản:", range(len(same_id_artifacts)), format_func=lambda i: diff_options[i])
            compare_artifact = same_id_artifacts[target_v_idx]
            if compare_artifact.version != selected_artifact.version:
                report = generate_artifact_diff(compare_artifact, selected_artifact)
                st.code(report.content_diff, language="diff")
                if report.conflict_decision_items:
                    st.warning("Các điểm cần lưu ý khi chuyển phiên bản:")
                    for item in report.conflict_decision_items:
                        st.markdown(f"- {item}")
            else:
                st.info("Đang chọn cùng một phiên bản.")
        else:
            st.info("Tài liệu hiện tại chỉ có một phiên bản duy nhất.")

    with tab_action:
        st.write(f"**Trạng thái hiện tại:** {_CONTROLLED_ARTIFACT_STATUS_LABELS.get(selected_artifact.status, selected_artifact.status)}")
        with st.form(f"form_approval_{selected_artifact.artifact_id}"):
            action_choice = st.selectbox(
                "Hành động phê duyệt:",
                [
                    ("approve", "Phê duyệt ban hành"),
                    ("reject", "Từ chối tài liệu"),
                    ("request_change", "Yêu cầu chỉnh sửa bổ sung"),
                    ("revoke", "Thu hồi tài liệu đã duyệt"),
                ],
                format_func=lambda x: x[1],
            )
            reason = st.text_area("Lý do / Căn cứ ra quyết định:")
            submitted = st.form_submit_button("Xác nhận Quyết định")

            if submitted:
                if not reason.strip():
                    st.error("Vui lòng nhập lý do phê duyệt hoặc từ chối.")
                else:
                    try:
                        approval_id = f"APP-{selected_artifact.artifact_id}-{int(st.session_state.get('app_seq', 1))}"
                        service.submit_artifact_approval(
                            approval_id=approval_id,
                            artifact_id=selected_artifact.artifact_id,
                            action=action_choice[0],
                            actor_id=actor_principal.subject,
                            expected_digest=selected_artifact.digest,
                            reason=reason.strip(),
                            idempotency_key=f"IDEMP-{approval_id}",
                        )
                        st.success(f"Đã ghi nhận quyết định thành công cho tài liệu '{selected_artifact.artifact_id}'.")
                        st.rerun()
                    except (SelfApprovalDeniedError, StaleArtifactDigestError, ConflictedClaimArtifactError, ControlledArtifactError) as exc:
                        thong_bao_loi = safe_vietnamese_ui_message(str(exc))
                        st.error(thong_bao_loi)


def render_knowledge_publication_management(
    service: ExpertInterviewService,
    publisher: KnowledgePublisher,
    actor_principal: VerifiedPrincipal,
    locale: str = "vi",
) -> None:
    """Render publication pipeline, backup status, and revocation UI for approved knowledge artifacts (T066)."""
    norm_loc = normalize_locale(locale)
    st.subheader("Xuất bản Tri thức vào Thư viện Dùng chung")

    artifacts = service.interview_repo.list_artifacts(status=ARTIFACT_STATUS_APPROVED)
    if not artifacts:
        st.info("Chưa có tài liệu quy chuẩn nào được phê duyệt (approved) để xuất bản.")
        return

    art_options = [f"{a.artifact_id} - {a.title} (v{a.version})" for a in artifacts]
    selected_idx = st.selectbox("Chọn tài liệu đã duyệt để xuất bản:", range(len(artifacts)), format_func=lambda i: art_options[i])
    selected_artifact = artifacts[selected_idx]

    tab_pub, tab_revoke = st.tabs(["Tiến trình Xuất bản", "Thu hồi khỏi Thư viện"])

    with tab_pub:
        st.write(f"**Tài liệu:** {selected_artifact.title} (`{selected_artifact.artifact_id}`)")
        st.write(f"**Phạm vi:** {selected_artifact.scope} | **Phiên bản:** {selected_artifact.version}")
        st.caption(f"Mã băm tài liệu: `{selected_artifact.digest}`")

        with st.form(f"form_publish_{selected_artifact.artifact_id}"):
            q1 = st.text_input("Câu hỏi kiểm tra nghiệm thu 1:", value=f"Quy trình {selected_artifact.scope} yêu cầu thông số gì?")
            q2 = st.text_input("Câu hỏi kiểm tra nghiệm thu 2:", value=f"Cách thực hiện {selected_artifact.title} chi tiết thế nào?")
            submitted = st.form_submit_button("Tiến hành Niêm phong & Xuất bản")

            if submitted:
                questions = [q.strip() for q in [q1, q2] if q.strip()]
                if len(questions) < 1:
                    st.error("Vui lòng nhập ít nhất một câu hỏi nghiệm thu.")
                else:
                    try:
                        pkg = seal_publication_package(
                            artifact=selected_artifact,
                            acceptance_questions=questions,
                            sealed_by=actor_principal.subject,
                        )
                        st.info("Đã niêm phong gói xuất bản. Đang sao lưu và nạp vào thư viện...")

                        pub_pkg, receipt = publisher.publish_package(pkg, actor=actor_principal.subject)
                        st.success(f"Xuất bản thành công! Mã biên nhận: '{receipt.receipt_id}'.")
                        st.write(f"- Trạng thái kiểm tra toàn vẹn cơ sở dữ liệu: **{receipt.quick_check_status}**")
                        st.write(f"- Mã bản sao lưu phục hồi an toàn: `{receipt.backup_id}`")
                        st.write("- Kết quả nghiệm thu truy xuất:")
                        for q_text, passed in receipt.acceptance_results.items():
                            st.write(f"  + *{q_text}*: {'Đạt' if passed else 'Không đạt'}")
                    except (UnapprovedArtifactPublicationError, LibraryWriterBusyError, PublicationAcceptanceError, PublicationError) as exc:
                        thong_bao_loi = safe_vietnamese_ui_message(str(exc))
                        st.error(thong_bao_loi)

    with tab_revoke:
        with st.form(f"form_revoke_{selected_artifact.artifact_id}"):
            package_id_to_revoke = st.text_input(
                "Mã gói xuất bản cần thu hồi:",
                value=f"PKG-{selected_artifact.artifact_id}-V{selected_artifact.version.replace('.', '_')}",
            )
            revoke_reason = st.text_area("Lý do thu hồi gói xuất bản:")
            btn_revoke = st.form_submit_button("Xác nhận Thu hồi khỏi Thư viện")

            if btn_revoke:
                if not revoke_reason.strip():
                    st.error("Vui lòng nhập lý do thu hồi.")
                else:
                    try:
                        rev_receipt = publisher.revoke_publication(
                            package_id=package_id_to_revoke.strip(),
                            collection_id=DEFAULT_COLLECTION_ID,
                            reason=revoke_reason.strip(),
                            actor=actor_principal.subject,
                        )
                        st.success(f"Đã thu hồi gói '{package_id_to_revoke}' thành công. Biên nhận thu hồi: '{rev_receipt.receipt_id}'.")
                    except (LibraryWriterBusyError, PublicationError) as exc:
                        thong_bao_loi = safe_vietnamese_ui_message(str(exc))
                        st.error(thong_bao_loi)
