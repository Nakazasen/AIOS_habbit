from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from aios_habit.agent_work_artifact import create_factory_error_report, undo_factory_error_report


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "agent_harness" / "factory_error"


def test_factory_error_report_uses_source_data_and_autocompletes(tmp_path: Path) -> None:
    result = create_factory_error_report(
        source_paths=[
            FIXTURE_ROOT / "nhat_ky_lo_A17.log",
            FIXTURE_ROOT / "so_lieu_lo_A17.csv",
            FIXTURE_ROOT / "mo_ta_hien_tuong.md",
        ],
        output_dir=tmp_path,
        work_id="WORK-US1-001",
    )

    payload = result.payload
    assert result.report_path.is_file()
    assert payload["schema_version"] == "aios_factory_error_report_v1"
    assert payload["work_id"] == "WORK-US1-001"
    assert payload["status"] == "completed"
    assert result.status_vi == "Đã xong"
    assert result.approval_required is False
    assert "Duyệt" not in result.report_path.read_text(encoding="utf-8")

    assert payload["phenomenon_vi"]
    assert "nhat_ky_lo_A17.log" in payload["phenomenon_vi"]
    assert "E101" in payload["phenomenon_vi"]
    assert payload["impact_vi"]
    assert payload["analysis_vi"]
    assert payload["hypotheses"][0]["evidence_status"] == "proposal"
    assert payload["uncertainties_vi"]
    assert 1 <= len(payload["next_actions_vi"]) <= 5
    assert "đầu ép" not in " ".join(payload["next_actions_vi"]).casefold()
    assert payload["artifact_digest"]

    evidence_refs = {reference["source_file"] for reference in payload["evidence"]}
    assert {"nhat_ky_lo_A17.log", "so_lieu_lo_A17.csv", "mo_ta_hien_tuong.md"} <= evidence_refs
    assert len(payload["visuals"]) == 1
    visual = payload["visuals"][0]
    assert visual["source_refs"] == ["so_lieu_lo_A17.csv"]
    assert visual["source_columns"] == ["thời_gian", "số_lượng_lỗi"]
    assert visual["units"] == "sản phẩm"
    assert visual["aggregation"] == "giữ nguyên từng mốc thời gian"
    assert visual["data_digest"]

    undo_factory_error_report(result)
    assert not result.report_path.exists()


def test_factory_error_report_does_not_invent_chart_when_numbers_are_missing(tmp_path: Path) -> None:
    result = create_factory_error_report(
        source_paths=[FIXTURE_ROOT / "thieu_so_lieu.md"],
        output_dir=tmp_path,
        work_id="WORK-US1-002",
    )

    payload = result.payload
    assert result.status_vi == "Đã xong"
    assert payload["status"] == "completed"
    assert payload["visuals"] == []
    assert "bảng" in payload["uncertainties_vi"].lower()
    assert result.report_path.is_file()


def test_factory_error_report_accepts_latin_excel_headers_for_a_provenanced_visual(tmp_path: Path) -> None:
    workbook_path = tmp_path / "so_lieu_lo_A17.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Lỗi A17"
    sheet.append(["time", "defects", "inspected", "unit"])
    sheet.append(["2026-01-01 08:00", 2, 100, "sản phẩm"])
    sheet.append(["2026-01-01 09:00", 5, 100, "sản phẩm"])
    workbook.save(workbook_path)

    result = create_factory_error_report(
        source_paths=[workbook_path],
        output_dir=tmp_path / "out",
        work_id="WORK-US1-XLSX",
    )

    visual = result.payload["visuals"][0]
    assert visual["source_refs"] == [workbook_path.name]
    assert visual["source_columns"] == ["time", "defects"]
    assert visual["units"] == "sản phẩm"
    assert visual["filters"].startswith("sheet Lỗi A17")
    assert "excel_chart_metadata" in visual
    assert "7" in result.payload["impact_vi"]
    assert "200" in result.payload["impact_vi"]


def test_workspace_chat_wires_autocomplete_artifact_actions_without_approval() -> None:
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")

    assert "detect_agent_work_intent(" in app_source
    assert "create_factory_error_report(" in app_source
    assert "create_process_design_review(" in app_source
    assert "format_artifact_card(" in app_source
    assert "orch.enqueue_work_item(" in app_source
    assert "orch.process_next_work_item(" in app_source

    # Interactive artifact card in chat bubble has view, download, undo without approval
    assert "extract_chat_artifact_metadata(" in ui_source
    assert "agent_artifact_view_full" in ui_source
    assert "agent_artifact_download" in ui_source
    assert "agent_artifact_undo" in ui_source
    assert "approval" not in app_source.casefold() or "approval_required" not in app_source


def test_workspace_chat_removes_static_local_work_tools_for_conversational_omnibar() -> None:
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    # Verify complete removal of static work tools block and queue table in favor of Conversational Omnibar
    assert "_render_local_work_tools" not in app_source
    assert "wsc_factory_error_create_" not in app_source
    assert "wsc_process_review_create_" not in app_source

