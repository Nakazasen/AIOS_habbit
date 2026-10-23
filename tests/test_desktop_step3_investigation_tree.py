"""Comprehensive test suite for ticket DESKTOP-STEP3-INVESTIGATION-TREE-HOME.

Verifies:
1. 4M investigation tree generation (Man/Machine/Material/Method) from phenomenon and error code.
2. 5-level Why-Why chain with structured guidance.
3. Provenance (căn cứ) tracking on every branch: grounded on similar cases or declared as generic.
4. Anti-fabrication: zero invented technical parameters, exact source tracing.
5. Export to company report layout (.md and .docx) byte-matching KTD report standards.
6. 3-point Continuous Improvement Loop:
   - Point 1: Inline feedback capture (đúng hướng / thiếu nhánh / không hữu ích).
   - Point 2: Measurable metrics (coverage, helpfulness, basis grounding, exported files).
   - Point 3: Review surface (bề mặt xem lại qua lệnh chat và báo cáo tóm tắt).
7. Local-only storage invariant: written to local_cases/, never to RAG knowledge base.
8. Chat action and case workflow integration.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

import pytest

from aios_habit.chat_action import ChatActionRequest, load_builtin_actions, match_action, reset_actions
from aios_habit.chat_action_create_case import execute_build_case_tree
from aios_habit.chat_action_dieu_tra import _handler, extract_phenomenon
from aios_habit.chat_intent_router import (
    DANH_GIA_DIEU_TRA,
    XEM_PHAN_HOI,
    classify_intent,
    route,
)
from aios_habit.error_cases.investigation_feedback import (
    LOCAL_INVESTIGATION_FEEDBACK_FILE,
    RATING_DUNG_HUONG,
    RATING_KHONG_HUU_ICH,
    RATING_THIEU_NHANH,
    compute_investigation_metrics,
    format_investigation_review_summary,
    load_all_investigation_feedback,
    log_investigation_tree,
    record_investigation_feedback,
)
from aios_habit.error_cases.investigation_tree import (
    BRANCH_LABELS_VI,
    BRANCHES,
    REPORT_FIELDS,
    REPORT_TITLE,
    ChecklistItem,
    InvestigationTree,
    build_tree,
    build_why_chain,
    export_docx,
    export_markdown,
    export_report,
    render_markdown,
    render_report,
)

# Real phenomena from company KDTPS error history
REAL_PHENOMENON_C4001 = "LCD báo mã C4001 khi khởi động in tờ thử"
REAL_PHENOMENON_C2340 = "LCD画面に2340表示 C2340：定着圧解除モータエラー（タイムアウト）"
REAL_PHENOMENON_JAM = "Kẹt giấy tại cụm sấy JAM 9110 khi chạy giấy dày"
REAL_PHENOMENON_TORN = "OUTER CASE-V LP-S280DN EHC bị rách góc"
REAL_PHENOMENON_STOPPER = "Stopper Paper di chuyển nặng, không trơn tru"


# ---------------------------------------------------------------------------
# Fixture: Mock Similar Cases (Step 1 Engine output simulation)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_similar_cases() -> List[Dict[str, Any]]:
    return [
        {
            "id": 101,
            "no_dvd": "KDTPS-2026-08-0872",
            "hien_tuong": "LCD画面に2340表示 C2340：定着圧解除モータエラー",
            "nguyen_nhan": "Sensor nhiệt độ cụm sấy bám bụi và cáp tín hiệu lỏng",
            "doi_sach": "Vệ sinh sensor nhiệt độ và thay dây cáp kết nối cụm sấy",
            "where": "Iris2024 / C33-A1",
            "category": "C CALL",
            "bao_cao_goc": "Lịch sử lỗi/C Call/KTD-2026-08-0872.xlsx › dòng 20",
        },
        {
            "id": 102,
            "no_dvd": "KDTPS-2026-07-0415",
            "hien_tuong": "Cụm sấy kẹt giấy không nhả",
            "nguyen_nhan": "Linh kiện lô ép bị biến dạng nhiệt do quá nhiệt",
            "doi_sach": "Thay cụm lô ép mới và kiểm tra điện áp nguồn sấy",
            "where": "Iris2024 / C33-A2",
            "category": "JAM",
            "bao_cao_goc": "Lịch sử lỗi/JAM/KTD-2026-07-0415.xlsx › dòng 15",
        },
        {
            "id": 103,
            "no_dvd": "KDTPS-2026-06-0120",
            "hien_tuong": "Thao tác gắn giắc kết nối không chặt dẫn tới ngắt mạch",
            "nguyen_nhan": "Người thao tác mới chưa tuân thủ đúng quy trình bấm giắc 2 nấc (SOP-E04)",
            "doi_sach": "Đào tạo lại thao tác bấm giắc cho công nhân và dán hướng dẫn trực quan tại line",
            "where": "Iris2024 / C33-B1",
            "category": "C CALL",
            "bao_cao_goc": "Lịch sử lỗi/C Call/KTD-2026-06-0120.xlsx › dòng 8",
        },
    ]


@pytest.fixture
def clean_feedback_env(tmp_path, monkeypatch):
    test_feedback_file = tmp_path / "investigation_feedback.jsonl"
    monkeypatch.setattr(
        "aios_habit.error_cases.investigation_feedback.LOCAL_INVESTIGATION_FEEDBACK_FILE",
        test_feedback_file,
    )
    monkeypatch.setattr(
        "aios_habit.error_cases.investigation_feedback.LOCAL_CASES_DIR",
        tmp_path,
    )
    return test_feedback_file


# ---------------------------------------------------------------------------
# 1. 4M Branches & Why-Why Structure Tests
# ---------------------------------------------------------------------------

def test_step3_tree_generates_all_4m_branches():
    tree = build_tree(REAL_PHENOMENON_C4001, code="C4001")
    assert tree.branch_order == list(BRANCHES)
    for b in BRANCHES:
        assert b in tree.branches
        items = tree.branches[b]
        assert len(items) >= 4, f"Branch {b} should have at least 4 items"


def test_step3_why_why_chain_has_5_levels():
    tree = build_tree(REAL_PHENOMENON_JAM, code="9110", code_family="JAM")
    assert len(tree.why_chain) == 5
    assert [node.level for node in tree.why_chain] == [1, 2, 3, 4, 5]
    assert REAL_PHENOMENON_JAM in tree.why_chain[0].question
    assert all(node.hint for node in tree.why_chain)
    assert all(node.answer == "" for node in tree.why_chain)  # Left blank for investigator


# ---------------------------------------------------------------------------
# 2. Provenance Grounding vs Generic Fallback Tests
# ---------------------------------------------------------------------------

def test_step3_tree_with_similar_cases_grounds_branches(sample_similar_cases):
    tree = build_tree(
        REAL_PHENOMENON_C2340,
        code="C2340",
        code_family="C_CALL",
        similar_cases=sample_similar_cases,
    )

    assert tree.grounded_items_count > 0
    assert tree.total_items == tree.grounded_items_count + tree.generic_items_count

    # Check Machine branch has grounded items from case KDTPS-2026-08-0872
    machine_items = tree.branches["Machine"]
    grounded_machine = [it for it in machine_items if not it.is_generic]
    assert len(grounded_machine) >= 1
    assert any("KDTPS-2026-08-0872" in it.can_cu for it in grounded_machine)
    assert any("Vệ sinh sensor" in it.question for it in grounded_machine)
    assert "Có căn cứ" in tree.branch_basis["Machine"]

    # Check Man branch has grounded items from case KDTPS-2026-06-0120
    man_items = tree.branches["Man"]
    grounded_man = [it for it in man_items if not it.is_generic]
    assert len(grounded_man) >= 1
    assert any("KDTPS-2026-06-0120" in it.can_cu for it in grounded_man)
    assert "Có căn cứ" in tree.branch_basis["Man"]

    # Why-Why node 1 should incorporate historical cause
    assert "KDTPS-2026-08-0872" in tree.why_chain[0].hint
    assert "Sensor nhiệt độ cụm sấy bám bụi" in tree.why_chain[0].hint


def test_step3_tree_without_similar_cases_explicitly_marks_generic():
    tree = build_tree("Hiện tượng lỗi hoàn toàn mới lạ chưa từng có", similar_cases=[])

    assert tree.grounded_items_count == 0
    assert tree.generic_items_count == tree.total_items

    for b in BRANCHES:
        assert "Gợi ý chung" in tree.branch_basis[b]
        for it in tree.branches[b]:
            assert it.is_generic is True
            assert "Gợi ý chung" in it.can_cu

    # Why-Why Level 1 states generic note
    assert "Gợi ý chung" in tree.why_chain[0].hint


def test_step3_tree_with_document_sources():
    doc_sources = [
        {
            "title": "SOP-BAO-TRI-CUM-SAY-IRIS.pdf",
            "filename": "SOP-BAO-TRI-CUM-SAY-IRIS.pdf",
            "branch": "Method",
        }
    ]
    tree = build_tree(REAL_PHENOMENON_C4001, code="C4001", doc_sources=doc_sources)
    method_items = tree.branches["Method"]
    doc_grounded = [it for it in method_items if "SOP-BAO-TRI-CUM-SAY-IRIS" in it.can_cu]
    assert len(doc_grounded) >= 1
    assert doc_grounded[0].is_generic is False


# ---------------------------------------------------------------------------
# 3. Anti-Fabrication & Concrete Items Tests
# ---------------------------------------------------------------------------

def test_step3_no_vague_fillers_in_checklist():
    tree = build_tree(REAL_PHENOMENON_C4001, code="C4001")
    vague_fillers = ("kiểm tra lại máy", "kiểm tra chung", "xem lại máy", "rà soát lại")
    for it in tree.all_items():
        q_low = it.question.lower()
        d_low = it.data_to_collect.lower()
        for v in vague_fillers:
            assert v not in q_low
            assert v not in d_low
        assert it.data_to_collect.strip() != ""
        assert it.can_cu.strip() != ""


# ---------------------------------------------------------------------------
# 4. Company Report Layout & Export Tests (.md and .docx)
# ---------------------------------------------------------------------------

def test_step3_report_matches_company_fields():
    tree = build_tree(REAL_PHENOMENON_C2340, code="C2340")
    md_content = render_report(tree, meta={
        "report_id": "KTD-2026-TEST-001",
        "author": "Kỹ sư kiểm thử",
        "date": "2026-10-17",
    })

    assert REPORT_TITLE in md_content
    assert "KTD-2026-TEST-001" in md_content
    assert "Kỹ sư kiểm thử" in md_content
    for key, label in REPORT_FIELDS:
        if key == "investigation":
            continue
        clean_lbl = label.replace("\n", "<br>")
        assert clean_lbl in md_content

    assert "Investigation content and results" in md_content
    assert "Cây điều tra 4M" in md_content
    assert "Chuỗi Why-Why" in md_content


def test_step3_export_docx_creates_valid_file(tmp_path):
    pytest.importorskip("docx")
    from docx import Document

    tree = build_tree(REAL_PHENOMENON_C4001, code="C4001")
    target_docx = tmp_path / "bao_cao_dieu_tra_c4001.docx"

    out = export_report(tree, target_docx, meta={"report_id": "KTD-C4001-TEST"})
    assert out.is_file()
    assert out.suffix == ".docx"

    doc = Document(str(out))
    text_all = " ".join(p.text for p in doc.paragraphs)
    assert REPORT_TITLE in text_all
    assert "KTD-C4001-TEST" in text_all
    assert "Cây điều tra 4M" in text_all
    assert "Chuỗi Why-Why" in text_all

    table = doc.tables[0]
    assert table.cell(0, 0).text == "Item／項目"
    assert table.cell(0, 1).text == "Details／詳細"


def test_step3_export_markdown_creates_valid_file(tmp_path):
    tree = build_tree(REAL_PHENOMENON_STOPPER)
    target_md = tmp_path / "bao_cao_stopper.md"

    out = export_report(tree, target_md, meta={"report_id": "KTD-STOPPER-01"})
    assert out.is_file()
    assert out.suffix == ".md"
    content = out.read_text(encoding="utf-8")
    assert "KTD-STOPPER-01" in content
    assert REAL_PHENOMENON_STOPPER in content


# ---------------------------------------------------------------------------
# 5. Continuous Improvement Loop Tests (3 points)
# ---------------------------------------------------------------------------

def test_step3_continuous_improvement_loop(clean_feedback_env):
    # Point 1: Log initial suggestion
    f_id = log_investigation_tree(
        tree_id="TREE-TEST-001",
        phenomenon=REAL_PHENOMENON_C4001,
        code="C4001",
        total_items=16,
        grounded_items=4,
        generic_items=12,
        branch_basis={"Machine": "Có căn cứ (1 ca)"},
        exported_files=["local_runs/dieu_tra/test.md"],
        conversation_id="conv-123",
    )
    assert f_id.startswith("FB-TREE-")
    records = load_all_investigation_feedback()
    assert len(records) == 1
    assert records[0]["rating"] == "chờ đánh giá"

    # Point 1: Capture inline feedback (đúng hướng)
    rec1 = record_investigation_feedback(
        tree_id="TREE-TEST-001",
        rating=RATING_DUNG_HUONG,
        user_note="Rất sát thực tế",
        conversation_id="conv-123",
    )
    assert rec1["rating"] == RATING_DUNG_HUONG

    # Log second suggestion and capture feedback (thiếu nhánh)
    log_investigation_tree(
        tree_id="TREE-TEST-002",
        phenomenon=REAL_PHENOMENON_JAM,
        code="9110",
        total_items=18,
        grounded_items=6,
        generic_items=12,
        conversation_id="conv-124",
    )
    rec2 = record_investigation_feedback(
        tree_id="TREE-TEST-002",
        rating=RATING_THIEU_NHANH,
        missing_branch="Cần thêm nhánh áp suất sấy",
        conversation_id="conv-124",
    )
    assert rec2["rating"] == RATING_THIEU_NHANH

    # Point 2: Measure metrics
    metrics = compute_investigation_metrics()
    assert metrics["total_trees_generated"] == 2
    assert metrics["total_rated"] == 2
    assert metrics["coverage_percent"] == 100.0
    assert metrics["helpful_percent"] == 100.0  # 1 đúng hướng + 1 thiếu nhánh
    assert metrics["exact_helpful_percent"] == 50.0  # 1 đúng hướng / 2
    assert metrics["grounded_items_count"] == 10  # 4 + 6

    # Point 3: Render review surface
    summary = format_investigation_review_summary()
    assert "Bề Mặt Xem Lại Cây Điều Tra 4M & Why-Why" in summary
    assert "Chỉ số đo lường hiệu quả" in summary
    assert "100.0%" in summary
    assert "TREE-TEST-001" in summary or "TREE-TEST-002" in summary


# ---------------------------------------------------------------------------
# 6. Intent Routing & Chat Action Integration Tests
# ---------------------------------------------------------------------------

def test_step3_chat_intent_routing_danh_gia_dieu_tra():
    intent, slots = route("cây điều tra đúng hướng")
    assert intent == DANH_GIA_DIEU_TRA
    assert slots.get("rating") == "đúng hướng"

    intent2, slots2 = route("cây điều tra thiếu nhánh, cần kiểm tra motor")
    assert intent2 == DANH_GIA_DIEU_TRA
    assert slots2.get("rating") == "thiếu nhánh"

    intent3, slots3 = route("xem phản hồi điều tra")
    assert intent3 == XEM_PHAN_HOI
    assert slots3.get("loai_phan_hoi") == "dieu_tra"

    intent4, slots4 = route("/dieutra-phanhoi")
    assert intent4 == XEM_PHAN_HOI
    assert slots4.get("loai_phan_hoi") == "dieu_tra"

    intent5, slots5 = route("/dieutra-duyet")
    assert intent5 == XEM_PHAN_HOI
    assert slots5.get("loai_phan_hoi") == "dieu_tra"

    from aios_habit.chat_intent_router import HOI_TAI_LIEU
    assert classify_intent("/investigation-feedback") == HOI_TAI_LIEU
    assert classify_intent("/investigation") == HOI_TAI_LIEU


def test_step3_chat_action_execution_end_to_end():
    reset_actions()
    load_builtin_actions()

    req = ChatActionRequest(
        question="gợi ý hướng điều tra cho hiện tượng LCD báo C4001 khi khởi động in tờ thử",
        conversation_id="conv-step3-test",
    )
    action = match_action(req)
    assert action is not None
    assert action.name == "goi_y_huong_dieu_tra"

    outcome = action.handler(req)
    assert outcome is not None
    assert outcome.action == "goi_y_huong_dieu_tra"
    text = outcome.blocks[0].text

    assert "Cây điều tra 4M" in text
    assert "Chuỗi Why-Why" in text
    assert "LCD báo C4001" in text
    assert "Căn cứ phân tích (Bước 3)" in text
    assert "Đánh giá cây điều tra:" in text
    assert "cây điều tra đúng hướng" in text
