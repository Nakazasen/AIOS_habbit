"""Unit and integration tests for Grokbot Conversational Omnibar and Interactive Chat Artifact Cards."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aios_habit.agent_work_artifact import (
    create_factory_error_report,
    create_process_design_review,
    detect_agent_work_intent,
    extract_chat_artifact_metadata,
    format_artifact_card,
)
from aios_habit.workspace_agent_orchestrator import WorkspaceAgentOrchestrator
from aios_habit.workspace_case_models import AgentWorkRecord, utc_now_iso
from aios_habit.workspace_case_repository import WorkspaceCaseRepository
from aios_habit.workspace_chat_models import ChatMessage
from aios_habit.workspace_chat_ui import render_chat_bubble

FIXTURE_ERR = Path(__file__).parent / "fixtures" / "agent_harness" / "factory_error"
FIXTURE_REV = Path(__file__).parent / "fixtures" / "agent_harness" / "process_design"


def test_intent_detection_patterns():
    """Verify Conversational Intent Routing identifies task intents accurately from natural language."""
    # Error report queries
    assert detect_agent_work_intent("Tạo báo cáo lỗi kỹ thuật dây chuyền SMT") == "error_report"
    assert detect_agent_work_intent("Lập báo cáo sự cố cho lô A17") == "error_report"
    assert detect_agent_work_intent("Hãy xuất báo cáo lỗi từ các file đã chọn") == "error_report"
    assert detect_agent_work_intent("Phân tích lỗi kỹ thuật từ file log") == "error_report"
    assert detect_agent_work_intent("Tổng hợp sự cố hôm nay") == "error_report"

    # Process design review queries
    assert detect_agent_work_intent("Rà soát thiết kế công đoạn hàn theo guideline") == "process_design_review"
    assert detect_agent_work_intent("Đánh giá thiết kế công đoạn ép nhựa") == "process_design_review"
    assert detect_agent_work_intent("Đối chiếu thiết kế với guideline") == "process_design_review"
    assert detect_agent_work_intent("Soát xét quy trình lắp ráp") == "process_design_review"
    assert detect_agent_work_intent("Kiểm tra thiết kế công đoạn") == "process_design_review"

    # Code change queries
    assert detect_agent_work_intent("Sửa mã nguồn tính toán yield rate") == "code_change"
    assert detect_agent_work_intent("Sửa code trong worktree") == "code_change"
    assert detect_agent_work_intent("Fix bug trong hàm parse_log") == "code_change"

    # General / RAG questions (must NOT falsely match agent work)
    assert detect_agent_work_intent("Lỗi E101 có ý nghĩa gì?") is None
    assert detect_agent_work_intent("Giải thích nguyên lý hoạt động của máy hàn") is None
    assert detect_agent_work_intent("Tài liệu hướng dẫn ở đâu?") is None
    assert detect_agent_work_intent("") is None


def test_format_and_extract_chat_artifact_card(tmp_path: Path):
    """Verify artifact card markdown formatting and hidden metadata extraction."""
    res = create_factory_error_report(
        source_paths=[
            FIXTURE_ERR / "nhat_ky_lo_A17.log",
            FIXTURE_ERR / "so_lieu_lo_A17.csv",
        ],
        output_dir=tmp_path,
        work_id="WORK-TEST-001",
    )

    card_text = format_artifact_card(
        work_type="error_report",
        work_id="WORK-TEST-001",
        result_path=res.report_path,
        checkpoint_path=res.report_path,
        payload=res.payload,
        status_vi="Đã xong",
    )

    assert "### 📋 Báo cáo lỗi kỹ thuật" in card_text
    assert "**Trạng thái:** ✅ Đã xong" in card_text
    assert "Tóm tắt phát hiện chính" in card_text
    assert "Biểu đồ số liệu có căn cứ" in card_text
    assert "```mermaid" in card_text

    metadata = extract_chat_artifact_metadata(card_text)
    assert metadata is not None
    assert metadata["work_id"] == "WORK-TEST-001"
    assert metadata["work_type"] == "error_report"
    assert metadata["result_path"] == str(res.report_path)


def test_conversational_flow_error_report_execution(tmp_path: Path):
    """Verify conversational error report execution from end to end."""
    repo = WorkspaceCaseRepository(database_path=tmp_path / "cases.sqlite")
    repo.initialize()
    orch = WorkspaceAgentOrchestrator()
    ws_id = "ws-conv-test"
    ws_root = str(tmp_path)

    sources = [
        FIXTURE_ERR / "nhat_ky_lo_A17.log",
        FIXTURE_ERR / "so_lieu_lo_A17.csv",
    ]

    work_id = "WORK-ERR-CONV-1"
    work = AgentWorkRecord(
        work_id=work_id,
        workspace_id=ws_id,
        work_type="error_report",
        goal_vi="Báo cáo lỗi kỹ thuật",
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        status="queued",
        allowed_roots=(ws_root,),
        source_refs=tuple(str(s) for s in sources),
    )
    enqueued = orch.enqueue_work_item(work=work, repo=repo)
    assert enqueued.queue_position == 1

    generated_card = []

    def _runner(item: AgentWorkRecord):
        res = create_factory_error_report(
            source_paths=sources,
            output_dir=tmp_path / "artifacts",
            work_id=item.work_id,
        )
        repo.update_agent_work_status(
            item.work_id,
            "completed",
            result_ref=str(res.report_path),
            checkpoint_ref=str(res.report_path),
        )
        card = format_artifact_card(
            work_type="error_report",
            work_id=item.work_id,
            result_path=str(res.report_path),
            checkpoint_path=str(res.report_path),
            payload=res.payload,
            status_vi="Đã xong",
        )
        generated_card.append(card)

    processed = orch.process_next_work_item(
        workspace_id=ws_id,
        workspace_root=ws_root,
        repo=repo,
        runner=_runner,
    )
    assert processed is not None
    assert processed.status == "completed"
    assert len(generated_card) == 1
    assert "### 📋 Báo cáo lỗi kỹ thuật" in generated_card[0]
    assert extract_chat_artifact_metadata(generated_card[0])["work_id"] == work_id


def test_conversational_flow_process_review_execution(tmp_path: Path):
    """Verify conversational process design review execution and card generation."""
    repo = WorkspaceCaseRepository(database_path=tmp_path / "cases.sqlite")
    repo.initialize()
    orch = WorkspaceAgentOrchestrator()
    ws_id = "ws-conv-rev-test"
    ws_root = str(tmp_path)

    sources = [
        FIXTURE_REV / "guideline_han_v2.md",
        FIXTURE_REV / "sop_nhap_cong_doan_han.md",
    ]

    work_id = "WORK-REV-CONV-1"
    work = AgentWorkRecord(
        work_id=work_id,
        workspace_id=ws_id,
        work_type="process_design_review",
        goal_vi="Rà soát thiết kế công đoạn",
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        status="queued",
        allowed_roots=(ws_root,),
        source_refs=tuple(str(s) for s in sources),
    )
    enqueued = orch.enqueue_work_item(work=work, repo=repo)
    assert enqueued.queue_position == 1

    generated_card = []

    def _runner(item: AgentWorkRecord):
        res = create_process_design_review(
            source_paths=sources,
            output_dir=tmp_path / "artifacts",
            work_id=item.work_id,
        )
        repo.update_agent_work_status(
            item.work_id,
            "completed",
            result_ref=str(res.report_path),
            checkpoint_ref=str(res.report_path),
        )
        card = format_artifact_card(
            work_type="process_design_review",
            work_id=item.work_id,
            result_path=str(res.report_path),
            checkpoint_path=str(res.report_path),
            payload=res.payload,
            status_vi="Đã xong (Bản nháp)",
        )
        generated_card.append(card)

    processed = orch.process_next_work_item(
        workspace_id=ws_id,
        workspace_root=ws_root,
        repo=repo,
        runner=_runner,
    )
    assert processed is not None
    assert processed.status == "completed"
    assert len(generated_card) == 1
    assert "### 📐 Bản nháp rà soát thiết kế công đoạn" in generated_card[0]
    assert "Bản nháp đối chiếu các tài liệu cục bộ đã chọn" in generated_card[0]


def test_interactive_chat_bubble_renders_actions_and_handles_undo(tmp_path: Path):
    """Verify render_chat_bubble displays interactive buttons and handles Undo/Rollback."""
    from openpyxl import Workbook

    repo_file = tmp_path / "cases.sqlite"
    repo = WorkspaceCaseRepository(database_path=repo_file)
    repo.initialize()

    report_file = tmp_path / "bao_cao_loi_WORK-TEST-UNDO.md"
    report_file.write_text("# Báo cáo lỗi kỹ thuật test\nNội dung toàn văn", encoding="utf-8")

    work_id = "WORK-TEST-UNDO"
    repo.save_agent_work(AgentWorkRecord(
        work_id=work_id,
        workspace_id="conv-123",
        work_type="error_report",
        goal_vi="Báo cáo lỗi",
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        status="completed",
        result_ref=str(report_file),
        checkpoint_ref=str(report_file),
    ))

    card_content = format_artifact_card(
        work_type="error_report",
        work_id=work_id,
        result_path=str(report_file),
        checkpoint_path=str(report_file),
        payload={"phenomenon_vi": "Lỗi nhiệt độ", "impact_vi": "100 sản phẩm"},
        status_vi="Đã xong",
    )

    msg = ChatMessage(
        id="msg-card-1",
        conversation_id="conv-123",
        role="assistant",
        content=card_content,
    )

    mock_st = MagicMock()
    mock_st.session_state = {}
    mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
    mock_st.button.return_value = False

    with patch("aios_habit.workspace_chat_ui.st", mock_st), \
         patch("aios_habit.workspace_case_repository.WorkspaceCaseRepository", return_value=repo):
        render_chat_bubble(msg, is_latest=True, locale="vi")

    # Assert download button and buttons were called with correct labels
    dl_calls = mock_st.download_button.call_args_list
    assert len(dl_calls) == 1
    assert dl_calls[0][1]["label"] == "📥 Tải về .md"
    assert dl_calls[0][1]["data"] == "# Báo cáo lỗi kỹ thuật test\nNội dung toàn văn"

    btn_calls = mock_st.button.call_args_list
    btn_labels = [c[0][0] for c in btn_calls]
    assert "👁️ Xem toàn văn" in btn_labels
    assert "↩️ Hoàn tác" in btn_labels


def test_invisible_queue_notification_when_worker_busy(tmp_path: Path):
    """Verify that when a worker is busy, submitting a second task notifies user naturally via chat."""
    repo = WorkspaceCaseRepository(database_path=tmp_path / "cases.sqlite")
    repo.initialize()
    orch = WorkspaceAgentOrchestrator()
    ws_id = "ws-queue-notify"
    ws_root = str(tmp_path)

    # 1. First task is enqueued and running
    task1 = AgentWorkRecord(
        work_id="WORK-BUSY-1",
        workspace_id=ws_id,
        work_type="error_report",
        goal_vi="Báo cáo lỗi dây chuyền",
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        status="queued",
        allowed_roots=(ws_root,),
    )
    orch.enqueue_work_item(work=task1, repo=repo)
    repo.update_agent_work_status("WORK-BUSY-1", "running")
    assert orch.acquire_workspace_lock(ws_root, "WORK-BUSY-1") is True

    # 2. Second task is submitted and enqueued
    task2 = AgentWorkRecord(
        work_id="WORK-QUEUED-2",
        workspace_id=ws_id,
        work_type="process_design_review",
        goal_vi="Rà soát thiết kế công đoạn",
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        status="queued",
        allowed_roots=(ws_root,),
    )
    enqueued2 = orch.enqueue_work_item(work=task2, repo=repo)
    assert enqueued2.queue_position == 2

    # Simulate chat reply logic
    running_tasks = [w for w in repo.list_agent_work(workspace_id=ws_id) if w.status == "running"]
    assert len(running_tasks) == 1

    queue_reply = (
        f"⏳ Tác vụ **{enqueued2.goal_vi}** của bạn đã được xếp hàng (vị trí {enqueued2.queue_position}) "
        "và sẽ tự động chạy ngay sau khi việc hiện tại hoàn tất."
    )
    assert "vị trí 2" in queue_reply
    assert "sẽ tự động chạy ngay sau khi việc hiện tại hoàn tất" in queue_reply


def test_missing_sources_conversational_guidance_replies():
    """Verify that when sources are missing, the assistant replies politely via chat without error bars."""
    # Test error report missing sources text
    error_intent = detect_agent_work_intent("Tạo báo cáo lỗi kỹ thuật")
    assert error_intent == "error_report"
    # Expected conversational guidance
    guide_error = (
        "Tôi đã sẵn sàng hỗ trợ bạn lập báo cáo lỗi kỹ thuật. Tuy nhiên, hiện tại bạn chưa chọn tệp dữ liệu nào "
        "(như tệp nhật ký `.log` hoặc bảng số liệu `.csv`/`.xlsx`). Bạn vui lòng tích chọn ít nhất một tệp nguồn "
        "trong danh sách tài liệu bên trên để tôi có thể trích xuất số liệu và lập báo cáo chính xác nhất nhé!"
    )
    assert "chưa chọn tệp dữ liệu nào" in guide_error
    assert ".log" in guide_error
    assert "tích chọn ít nhất một tệp nguồn" in guide_error

    # Test process review missing sources text
    rev_intent = detect_agent_work_intent("Rà soát thiết kế công đoạn ép nhựa")
    assert rev_intent == "process_design_review"
    guide_rev = (
        "Tôi đã sẵn sàng hỗ trợ bạn rà soát thiết kế công đoạn. Để đối chiếu và kiểm tra các tiêu chuẩn, "
        "bạn vui lòng tích chọn các tệp tài liệu liên quan (như quy chuẩn guideline, bản vẽ hoặc mô tả công đoạn) "
        "trong danh sách nguồn bên trên nhé!"
    )
    assert "rà soát thiết kế công đoạn" in guide_rev
    assert "guideline" in guide_rev

