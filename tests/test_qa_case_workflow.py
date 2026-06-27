import pytest

from aios_habit.case_store import load_cases, load_evidence
from aios_habit.notebook_case_actions import (
    build_safe_route_summary,
    create_case_draft_from_qa_answer,
)


@pytest.fixture(autouse=True)
def isolated_case_store(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.case_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.case_store.CASES_FILE", tmp_path / "cases.jsonl")
    monkeypatch.setattr("aios_habit.case_store.EVIDENCE_FILE", tmp_path / "evidence.jsonl")
    monkeypatch.setattr("aios_habit.case_store.ASSETS_DIR", tmp_path / "assets")


def test_qa_answer_creates_local_only_draft_case_with_source_evidence():
    confidential_excerpt = "CONFIDENTIAL_EXCERPT_MUST_NOT_BE_COPIED"
    answer = {
        "answer_text": (
            "Tóm tắt trả lời / Answer summary:\n"
            "AIOS tìm thấy nguồn cục bộ liên quan.\n\n"
            "Điều có bằng chứng / Confirmed by source:\n"
            f"{confidential_excerpt}"
        ),
        "source_refs": [
            {
                "relative_path": "docs/process_a.xlsx",
                "chunk_id": "MOM-CHUNK-1",
                "file_type": "xlsx",
            },
            {
                "relative_path": "docs/process_b.pdf",
                "chunk_id": "MOM-CHUNK-2",
                "file_type": "pdf",
            },
        ],
        "confidence_level": "medium",
        "not_found_or_insufficient_evidence": "Chưa xác nhận điều kiện ngoại lệ.",
        "next_checks": ["Mở tài liệu gốc.", "Đối chiếu bước vận hành."],
    }

    result = create_case_draft_from_qa_answer(
        question="Cần kiểm tra gì trước?",
        answer=answer,
        notebook_name="Hệ thống MOM",
        notebook_id="mom",
        workspace_id="default",
    )

    cases = load_cases()
    evidence = load_evidence()
    assert result["evidence_count"] == 2
    assert len(cases) == 1
    assert len(evidence) == 2

    case = cases[0]
    assert case.title.startswith("Điều tra từ Sổ tri thức:")
    assert "Cần kiểm tra gì trước?" in case.current_situation
    assert "Chưa xác nhận điều kiện ngoại lệ." in case.current_situation
    assert confidential_excerpt not in case.current_situation
    assert case.next_actions == ["Mở tài liệu gốc.", "Đối chiếu bước vận hành."]
    assert case.privacy_level == "local_only"
    assert case.verification_status == "draft"
    assert case.source_origin == "mom_official_local"
    assert case.linked_notebook_ids == ["mom"]
    assert len(case.evidence_items) == 2

    assert evidence[0].source_path == "docs/process_a.xlsx#MOM-CHUNK-1"
    assert evidence[0].privacy_level == "local_only"
    assert evidence[0].source_origin == "mom_official_local"
    assert evidence[0].verification_status == "draft"
    assert confidential_excerpt not in evidence[0].extracted_text


def test_qa_answer_without_refs_still_creates_insufficient_evidence_case():
    result = create_case_draft_from_qa_answer(
        question="Có quy trình payroll không?",
        answer={
            "answer_text": "Không tìm thấy nguồn phù hợp.",
            "source_refs": [],
            "confidence_level": "insufficient",
            "not_found_or_insufficient_evidence": "Không đủ bằng chứng trong sổ tri thức.",
            "next_checks": ["Kiểm tra lại từ khóa."],
        },
        notebook_name="Hệ thống MOM",
        notebook_id="mom",
        workspace_id="default",
    )

    cases = load_cases()
    assert result["evidence_count"] == 0
    assert load_evidence() == []
    assert len(cases) == 1
    assert "Không đủ bằng chứng trong sổ tri thức." in cases[0].current_situation
    assert cases[0].next_actions == ["Kiểm tra lại từ khóa."]
    assert cases[0].privacy_level == "local_only"
    assert cases[0].verification_status == "draft"


def test_qa_case_mapping_rejects_empty_question():
    with pytest.raises(ValueError, match="Câu hỏi không được để trống"):
        create_case_draft_from_qa_answer("", {}, "Sổ thử", "NB-1", "default")


def test_qa_case_stores_safe_normal_provider_route_summary():
    result = create_case_draft_from_qa_answer(
        question="Tóm tắt tài liệu thường",
        answer={"answer_text": "Có thể xử lý bằng nguồn AI ngoài.", "source_refs": []},
        notebook_name="Tài liệu thường",
        notebook_id="normal-docs",
        workspace_id="default",
        route_summary={
            "external_sent": True,
            "provider_name": "DeepSeek KEY-SHOULD-NOT-BE-STORED cloud_allowed provider policy",
            "used_fallback": False,
            "fallback_reason": "",
            "safety_mode_label": "Tài liệu thường cloud_allowed",
        },
    )

    case = result["case"]
    summary = case.route_summary
    assert summary["external_sent"] is True
    assert summary["provider_name"].startswith("DeepSeek")
    assert summary["used_fallback"] is False
    assert summary["fallback_reason"] == ""
    assert summary["safety_mode_label"] == "Tài liệu thường"
    assert summary["note_vi"] == "Có dùng nguồn AI ngoài vì đây là tài liệu thường."
    serialized = str(summary)
    assert "KEY-SHOULD-NOT-BE-STORED" not in serialized
    for raw in ("cloud_allowed", "local_only", "provider policy", "route policy"):
        assert raw not in serialized


def test_qa_case_stores_company_private_route_summary_without_provider():
    result = create_case_draft_from_qa_answer(
        question="Kiểm tra tài liệu công ty",
        answer={"answer_text": "Xử lý cục bộ.", "source_refs": []},
        notebook_name="Hệ thống MOM",
        notebook_id="mom",
        workspace_id="default",
        route_summary={
            "external_sent": False,
            "provider_name": "DeepSeek",
            "used_fallback": True,
            "fallback_reason": "blocked by local_only route policy",
            "safety_mode_label": "local_only",
        },
    )

    summary = result["case"].route_summary
    assert summary["external_sent"] is False
    assert summary["provider_name"] == ""
    assert summary["used_fallback"] is True
    assert "route policy" not in summary["fallback_reason"]
    assert summary["note_vi"] == (
        "Không gửi ra ngoài. Câu trả lời được xử lý theo chế độ công ty/mật. "
        "Có dùng trả lời cục bộ dự phòng."
    )
    serialized = str(summary)
    for raw in ("cloud_allowed", "local_only", "provider policy", "route policy"):
        assert raw not in serialized


def test_qa_case_without_route_summary_remains_backward_compatible():
    result = create_case_draft_from_qa_answer(
        question="Câu hỏi cũ",
        answer={"answer_text": "Trả lời cũ.", "source_refs": []},
        notebook_name="Sổ cũ",
        notebook_id="NB-OLD",
        workspace_id="default",
    )

    assert result["case"].route_summary == {}
    assert result["case_id"]
