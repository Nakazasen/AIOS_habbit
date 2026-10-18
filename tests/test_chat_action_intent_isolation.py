"""Regression tests for DESKTOP-ROUTER-INTENT-KEYWORD-ISOLATION-HOME.

Ensures:
1. TH04 question containing action-like words ("gửi báo cáo", "báo cáo tuần") routes to RAG (not chat_action).
2. 5+ self-composed variant document lookup questions containing "báo cáo" / "gửi" / "tạo" all route to RAG.
3. 5+ real commands representing existing actions still trigger the appropriate action.
"""

from __future__ import annotations

import pytest

from aios_habit import chat_action
from aios_habit.chat_action import (
    ChatActionRequest,
    is_document_lookup_query,
    load_builtin_actions,
    match_action,
    reset_actions,
)
from aios_habit.feature_flags import reset_feature_flags

TH04_QUESTION = (
    "Trong email FW 2021 11 20週報.msg, người gửi báo cáo tuần (週報) ngày 2021-11-30 "
    "là ai và thuộc bộ phận nào của KDTVN?"
)

VARIANT_LOOKUP_QUESTIONS = [
    (
        "variant_1_tao",
        "Ai đã tạo báo cáo tuần vào ngày 2021-11-30 trong tài liệu lưu trữ?",
    ),
    (
        "variant_2_gui",
        "Biên bản gửi báo cáo sự cố máy dán nhãn line A15 nằm ở thư mục nào?",
    ),
    (
        "variant_3_tao_bao_cao",
        "Theo quy định kiểm tra, ai là người nhận báo cáo từ tổ trưởng khi tạo ca điều tra mới?",
    ),
    (
        "variant_4_bao_cao_gui",
        "Báo cáo tuần FW 2021 11 20 được gửi bởi bộ phận nào của nhà máy KDTVN?",
    ),
    (
        "variant_5_gui_ngay",
        "Nội dung chính trong báo cáo gửi ngày 2021-11-30 đề cập đến lỗi gì của linh kiện?",
    ),
]

REAL_COMMANDS = [
    (
        "cmd_1_case_form_blank",
        "nhập báo cáo lỗi",
        "nhap_bao_cao_loi",
    ),
    (
        "cmd_2_case_form_submit",
        "nộp báo cáo\nModel: 6th Next\nLine: A15\nCông đoạn: A4.2\nError code: C0030\nHiện tượng: màn hình báo lỗi",
        "nhap_bao_cao_loi",
    ),
    (
        "cmd_3_knowledge_intake",
        "mở phiên thu tri thức",
        "thu_tri_thuc_chuyen_gia",
    ),
    (
        "cmd_4_investigation",
        "tạo vụ điều tra lỗi kẹt giấy line 1",
        "tao_vu_dieu_tra",
    ),
    (
        "cmd_5_feedback",
        "xem phản hồi",
        "bao_cao_phan_hoi",
    ),
    (
        "cmd_6_agent_report_create",
        "tạo báo cáo bc.docx: dòng mở đầu",
        "tao_sua_bao_cao",
    ),
    (
        "cmd_7_agent_report_edit",
        "sửa báo cáo sl.pptx: thêm vào slide 2: bổ sung số liệu tháng 10",
        "tao_sua_bao_cao",
    ),
    (
        "cmd_8_system_suggestion",
        "tiếp theo nên làm gì",
        "goi_y_viec_tiep_theo",
    ),
]


@pytest.fixture(autouse=True)
def _setup_registry():
    reset_feature_flags()
    reset_actions()
    load_builtin_actions()
    yield
    reset_feature_flags()
    reset_actions()


def test_th04_regression_routes_to_rag_not_chat_action():
    """TH04 must be recognized as a document lookup query and bypass chat_action."""
    assert is_document_lookup_query(TH04_QUESTION) is True
    req = ChatActionRequest(question=TH04_QUESTION)
    action = match_action(req)
    assert action is None, f"Expected no chat_action match for TH04, got {action.name if action else None}"
    assert chat_action.dispatch(req) is None


@pytest.mark.parametrize("name,question", VARIANT_LOOKUP_QUESTIONS)
def test_variant_lookup_questions_route_to_rag(name: str, question: str):
    """Informational lookup questions with action verbs must all route to RAG."""
    assert is_document_lookup_query(question) is True, f"Failed is_document_lookup_query for {name}"
    req = ChatActionRequest(question=question)
    action = match_action(req)
    assert action is None, f"Expected no chat_action match for {name}, got {action.name if action else None}"
    assert chat_action.dispatch(req) is None


@pytest.mark.parametrize("name,command,expected_action", REAL_COMMANDS)
def test_real_commands_still_trigger_correct_action(name: str, command: str, expected_action: str):
    """Real imperative commands must NOT be classified as lookup queries and must match expected action."""
    req = ChatActionRequest(question=command)
    action = match_action(req)
    assert action is not None, f"Expected action {expected_action} for command {name}, but got None"
    assert action.name == expected_action, f"Expected action {expected_action}, got {action.name}"
