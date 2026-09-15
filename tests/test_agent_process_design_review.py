from pathlib import Path

from aios_habit.agent_work_artifact import (
    ProcessDesignReviewResult,
    create_process_design_review,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "agent_harness" / "process_design"


def test_process_design_review_separates_roles_and_preserves_findings(tmp_path: Path) -> None:
    result = create_process_design_review(
        source_paths=sorted(FIXTURE_DIR.glob("*.md")),
        output_dir=tmp_path,
        work_id="WORK-US2-001",
    )

    payload = result.payload
    assert payload["schema_version"] == "aios_process_design_review_v1"
    assert payload["work_id"] == "WORK-US2-001"
    assert payload["status"] == "verified_draft"
    assert result.status_vi == "Đã xong"
    assert isinstance(result, ProcessDesignReviewResult)
    assert result.approval_required is False
    assert {item["source_file"] for item in payload["guideline_refs"]} == {
        "guideline_han_v1_cu.md",
        "guideline_han_v2.md",
    }
    assert [item["source_file"] for item in payload["design_refs"]] == [
        "sop_nhap_cong_doan_han.md"
    ]
    assert [item["source_file"] for item in payload["context_refs"]] == [
        "mom_bo_sung.md"
    ]

    verdicts = {item["verdict"] for item in payload["checks"]}
    statuses = {item["evidence_status"] for item in payload["checks"]}
    assert {"violate", "insufficient"} <= verdicts
    assert "conflicting" in statuses
    assert all(item["source_refs"] for item in payload["checks"] if item["verdict"] != "insufficient")
    assert payload["proposals"][0]["evidence_status"] == "proposal"
    assert payload["expert_questions_vi"]
    assert payload["artifact_digest"]
    assert result.report_path.is_file()
    report_text = result.report_path.read_text(encoding="utf-8")
    for heading in ("Hiện trạng", "Kết quả đối chiếu", "Ảnh hưởng", "Đề xuất", "Câu hỏi cần xác nhận"):
        assert heading in report_text

    result.undo()
    assert not result.report_path.exists()


def test_process_design_review_marks_all_checks_insufficient_without_guideline(tmp_path: Path) -> None:
    result = create_process_design_review(
        source_paths=[FIXTURE_DIR / "sop_nhap_cong_doan_han.md"],
        output_dir=tmp_path,
        work_id="WORK-US2-002",
    )

    payload = result.payload
    assert payload["guideline_refs"] == []
    assert payload["design_refs"] == []
    assert payload["context_refs"]
    assert payload["checks"][0]["verdict"] == "insufficient"
    assert "Chưa tách" in payload["checks"][0]["statement_vi"]


def test_process_design_review_compares_real_mm_limits_without_temperature_hardcode(tmp_path: Path) -> None:
    guideline = tmp_path / "guideline_kich_thuoc_v3.md"
    design = tmp_path / "sop_kich_thuoc.md"
    guideline.write_text("# Guideline v3\n\nChiều rộng không vượt quá 10 mm.\n", encoding="utf-8")
    design.write_text("# SOP nháp\n\nChiều rộng đặt là 12 mm.\n", encoding="utf-8")

    result = create_process_design_review(
        source_paths=[guideline, design],
        output_dir=tmp_path / "out",
        work_id="WORK-US2-MM-001",
    )

    violation = next(item for item in result.payload["checks"] if item["verdict"] == "violate")
    assert "10 mm" in violation["statement_vi"]
    assert "12 mm" in violation["statement_vi"]
    assert {ref["source_file"] for ref in violation["source_refs"]} == {
        guideline.name,
        design.name,
    }
    assert "nhiệt độ" not in violation["statement_vi"].casefold()


def test_process_design_review_marks_unmatched_unit_as_insufficient(tmp_path: Path) -> None:
    guideline = tmp_path / "standard_do_am.md"
    design = tmp_path / "sop_do_am.md"
    guideline.write_text("# Standard v1\n\nĐộ ẩm không quá 5 %.\n", encoding="utf-8")
    design.write_text("# SOP\n\nĐộ ẩm được ghi là 6 mm.\n", encoding="utf-8")

    result = create_process_design_review(
        source_paths=[guideline, design],
        output_dir=tmp_path / "out",
        work_id="WORK-US2-UNIT-001",
    )

    assert any(item["verdict"] == "insufficient" for item in result.payload["checks"])


def test_process_design_review_verdicts_localized_to_vietnamese(tmp_path: Path) -> None:
    from aios_habit.agent_work_artifact import format_artifact_card

    result = create_process_design_review(
        source_paths=sorted(FIXTURE_DIR.glob("*.md")),
        output_dir=tmp_path,
        work_id="WORK-US2-LANG-001",
    )
    report_text = result.report_path.read_text(encoding="utf-8")
    assert "[VI PHẠM]" in report_text or "[THIẾU DỮ LIỆU]" in report_text or "[ĐẠT]" in report_text
    assert "- violate:" not in report_text
    assert "- pass:" not in report_text
    assert "- insufficient:" not in report_text

    card_text = format_artifact_card(
        work_type="process_design_review",
        work_id="WORK-US2-LANG-001",
        result_path=str(result.report_path),
        checkpoint_path=str(result.report_path),
        payload=result.payload,
        status_vi="Đã xong (Bản nháp)",
    )
    assert "[VI PHẠM]" in card_text or "[THIẾU DỮ LIỆU]" in card_text or "[ĐẠT]" in card_text
    assert "[VIOLATE]" not in card_text
    assert "[PASS]" not in card_text
    assert "[INSUFFICIENT]" not in card_text
