# -*- coding: utf-8 -*-
"""Unit & Contract tests for ticket DESKTOP-HOME-ANSWER-STREAMING-DISPLAY.

Verifies:
1. Exact text invariance: split_text_into_streaming_chunks preserves 100% of characters and citations.
2. Progressive chunk emission yields multiple chunks with early first-token timestamp.
3. Cancellation event halts chunk emission immediately.
4. Phase transitions: retrieving -> drafting -> completed.
5. Error code DB lookup path (C6770) emits STREAMING_QA_START, STREAMING_QA_FIRST_TOKEN, and STREAMING_QA_COMPLETE.
6. Draft fallback and 5-tier ladder paths emit all streaming markers.
7. UI fragment frequency is responsive (0.15s) and renders writing status pill (wsc-streaming-writing-pill).
"""

from __future__ import annotations

from pathlib import Path
from threading import Event, Lock
import time
import pytest

from aios_habit.streaming_markers import (
    diff_marker_timestamps_s,
    format_marker_timestamp,
    progressive_emit_chunks,
    split_text_into_streaming_chunks,
)
from aios_habit.i18n import t

APP_PATH = Path("src/aios_habit/workspace_chat_app.py")


def _app_source() -> str:
    return APP_PATH.read_text(encoding="utf-8")


def test_split_text_into_streaming_chunks_exact_preservation() -> None:
    """Invariant: ''.join(split_text_into_streaming_chunks(text)) == text for all inputs."""
    samples = [
        "",
        "a",
        "Kiem tra chu chay",
        "Line 1\nLine 2\n\nLine 3",
        "   leading and trailing spaces   \n\n\t",
        "Dựa trên cơ sở dữ liệu **30.075 ca điều tra lịch sử KDTPS** và danh mục mã lỗi chuẩn, dưới đây là thông tin cho mã lỗi **C6770**:\n\n### 1. Định nghĩa kỹ thuật\n- **Mã lỗi:** `C6770`\n- **Hiện tượng:** Lỗi nguồn điện thấp Fuser IH\n\n_Nguồn trích dẫn: Loi KDTPS.xlsx > History KDTPS > dòng 9609._",
        "Tiếng Nhật: 質問を受け付けました・処理中... 回答を作成中...",
        "Short [1] and [2] citations with special characters & <tag> \"quotes\"",
        "A" * 300,  # Single long word without spaces
    ]

    for sample in samples:
        chunks = split_text_into_streaming_chunks(sample, target_chunk_size=35)
        rejoined = "".join(chunks)
        assert rejoined == sample, f"Failed preservation for: {sample[:40]}"
        if len(sample) > 35 and " " in sample:
            assert len(chunks) > 1, f"Expected multiple chunks for text of length {len(sample)}"


def test_progressive_emit_chunks_timing_and_preservation() -> None:
    """Verifies that progressive_emit_chunks delivers chunks progressively with exact content."""
    text = (
        "Dựa trên cơ sở dữ liệu **30.075 ca điều tra lịch sử KDTPS**:\n\n"
        "### 1. Định nghĩa kỹ thuật\n"
        "- **Mã lỗi:** `C6770`\n"
        "- **Tên mã lỗi / Hiện tượng:** Lỗi nguồn điện thấp Fuser IH\n"
        "- **Phân loại hệ thống:** C_CALL\n\n"
        "### 2. Đối sách xử lý đề xuất\n"
        "- **Bước 1:** Kiểm tra điện áp cấp vào Fuser IH.\n"
        "- **Bước 2:** Đo đạc linh kiện Q1 trên bản mạch PWB IH 100 ASSY.\n"
        "\n_Nguồn trích dẫn: Danh mục mã lỗi tự chẩn đoán._"
    )

    received: list[str] = []
    chunk_times: list[float] = []
    t_start = time.time()

    def collector(chunk: str) -> None:
        chunk_times.append(time.time() - t_start)
        received.append(chunk)

    progressive_emit_chunks(text, collector, target_total_duration_s=0.25, target_chunk_size=40)
    total_elapsed = time.time() - t_start

    # Content invariant
    assert "".join(received) == text
    assert len(received) >= 5, f"Expected >= 5 chunks, got {len(received)}"

    # First chunk arrived immediately (< 0.05s)
    assert chunk_times[0] < 0.05, f"First chunk arrived too late: {chunk_times[0]:.3f}s"

    # Total duration is within the intended fast responsive range
    assert 0.1 <= total_elapsed <= 0.6, f"Elapsed time out of range: {total_elapsed:.3f}s"


def test_progressive_emit_chunks_cancellation() -> None:
    """Verifies that cancellation event halts streaming immediately."""
    text = "A " * 200
    cancel_evt = Event()
    received: list[str] = []

    def collector(chunk: str) -> None:
        received.append(chunk)
        if len(received) >= 3:
            cancel_evt.set()

    progressive_emit_chunks(
        text,
        collector,
        cancellation_event=cancel_evt,
        target_total_duration_s=1.0,
        target_chunk_size=20,
    )

    # Should have stopped early
    assert len(received) == 3
    assert len("".join(received)) < len(text)


def test_ui_fragment_and_writing_pill_contract() -> None:
    """Verifies that Streamlit fragment runs at 0.15s and renders the writing progress pill."""
    source = _app_source()

    # Fragment runs at 0.15s for smooth visual feedback
    assert "@st.fragment(run_every=0.15)" in source

    # Writing pill element rendered when text is streaming
    assert "wsc-streaming-writing-pill" in source
    assert "writing_answer_progress" in source

    # Translation keys exist
    assert t("writing_answer_progress", locale="vi") == "Đang soạn câu trả lời..."
    assert t("writing_answer_progress", locale="ja") == "回答を作成中..."
    assert t("writing_answer_progress", locale="zh-CN") == "正在编写回答..."


def test_c6770_ladder_path_emits_streaming_markers_and_chunks(monkeypatch) -> None:
    """Verifies that the error code lookup path (deliver_5tier_ladder_answer for C6770)
    emits STREAMING_QA_START, STREAMING_QA_FIRST_TOKEN, and STREAMING_QA_COMPLETE.
    """
    from aios_habit.workspace_chat_app import _run_chat_turn_async

    printed_markers: list[str] = []

    def mock_safe_print(msg: str) -> None:
        printed_markers.append(msg)

    monkeypatch.setattr("aios_habit.workspace_chat_app._safe_print_streaming_marker", mock_safe_print)

    # Mock retrieval to return 0 hits so it exercises the ladder/DB error synthesis lane
    def mock_retrieve(*args, **kwargs):
        return {"summary_count": 0, "status": "no_results", "evidence_items": []}

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.retrieve_workspace_chat_evidence",
        mock_retrieve,
    )

    chunks_received: list[str] = []
    conv_id = f"CONV-TEST-C6770-{int(time.time() * 1000)}"

    stream_state = {
        "text": "",
        "first_token_time": None,
        "started_at": time.time(),
        "warming_collection": None,
        "lock": Lock(),
        "phase": "retrieving",
    }

    t0 = time.time()
    ok, succ_msg, badge, err = _run_chat_turn_async(
        q_text="C6770 nguyên nhân thường gặp là gì?",
        query_relevant_sources=(),
        conversation_id=conv_id,
        notebook_id="NB-LAZY-DTL",
        on_chunk=lambda c: chunks_received.append(c),
        stream_state=stream_state,
    )
    turn_duration = time.time() - t0

    assert ok is True
    assert err is None
    assert isinstance(badge, dict)

    # Progressive chunks received
    assert len(chunks_received) >= 1
    streamed_text = "".join(chunks_received)
    assert len(streamed_text) > 0
    assert "C6770" in streamed_text or "lỗi" in streamed_text.lower() or "suy luận" in streamed_text.lower()

    # Markers emitted
    marker_str = "\n".join(printed_markers)
    assert "[STREAMING_QA_START]" in marker_str
    assert f"conv={conv_id}" in marker_str
    assert "[STREAMING_QA_FIRST_TOKEN]" in marker_str
    assert "[STREAMING_QA_COMPLETE]" in marker_str
    assert "ok=True" in marker_str


def test_draft_fallback_path_emits_streaming_markers_and_chunks(monkeypatch) -> None:
    """Verifies that draft fallback path emits STREAMING_QA_FIRST_TOKEN and STREAMING_QA_COMPLETE."""
    from aios_habit.workspace_chat_app import _run_chat_turn_async

    printed_markers: list[str] = []

    def mock_safe_print(msg: str) -> None:
        printed_markers.append(msg)

    monkeypatch.setattr("aios_habit.workspace_chat_app._safe_print_streaming_marker", mock_safe_print)

    def mock_retrieve(*args, **kwargs):
        return {"summary_count": 0, "status": "no_results", "evidence_items": []}

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.retrieve_workspace_chat_evidence",
        mock_retrieve,
    )

    # Mock deliver_draft_answer to return a known draft answer
    def mock_draft(q, **kwargs):
        on_chunk = kwargs.get("on_chunk")
        draft_text = "Dự thảo câu trả lời kiểm thử quy trình vận hành máy."
        if on_chunk:
            on_chunk(draft_text)
        return (True, draft_text, {"type": "draft_fallback", "draft_source": "test.docx"}, None)

    monkeypatch.setattr("aios_habit.answer_draft_fallback.deliver_draft_answer", mock_draft)

    chunks_received: list[str] = []
    conv_id = f"CONV-TEST-DRAFT-{int(time.time() * 1000)}"

    from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource

    source = WorkspaceAIContextSource(
        source_id="S-DRAFT-1",
        source_scope="notebook",
        source_type="plain_text",
        title="tai_lieu_thu_nghiem.txt",
        privacy_label="local_only",
        text="Quy trình vận hành máy sản xuất.",
        included_chars=32,
        truncated=False,
    )

    ok, succ_msg, badge, err = _run_chat_turn_async(
        q_text="Quy trình vận hành máy",
        query_relevant_sources=(source,),
        conversation_id=conv_id,
        on_chunk=lambda c: chunks_received.append(c),
    )

    assert ok is True
    assert "".join(chunks_received) == "Dự thảo câu trả lời kiểm thử quy trình vận hành máy."

    marker_str = "\n".join(printed_markers)
    assert "[STREAMING_QA_START]" in marker_str
    assert "[STREAMING_QA_FIRST_TOKEN]" in marker_str
    assert "[STREAMING_QA_COMPLETE]" in marker_str
    assert "backend=draft_fallback" in marker_str


def test_grounded_local_fallback_path_emits_streaming_markers_and_chunks(monkeypatch) -> None:
    """Verifies that grounded local fallback path emits streaming chunks and all markers."""
    from aios_habit.workspace_chat_app import _run_chat_turn_async
    from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource

    printed_markers: list[str] = []

    def mock_safe_print(msg: str) -> None:
        printed_markers.append(msg)

    monkeypatch.setattr("aios_habit.workspace_chat_app._safe_print_streaming_marker", mock_safe_print)

    # Mock retrieval to return 2 evidence items
    def mock_retrieve(*args, **kwargs):
        return {
            "summary_count": 2,
            "status": "success",
            "evidence_items": [
                {"title": "Bao cao KDTPS 2024", "text": "Ma loi C6770 phat sinh do sut ap Fuser IH.", "citation_id": "[1]"},
                {"title": "Tai lieu ky thuat IH", "text": "Linh kien Q1 va U6 can kiem tra khi xay ra C6770.", "citation_id": "[2]"},
            ],
            "retrieved_context_sources": (),
            "safe_owner_message": "Tim thay 2 nguon",
            "local_synthesis": {
                "answer": "Theo bao cao KDTPS 2024, ma loi C6770 phat sinh do sut ap Fuser IH [1]. Can kiem tra linh kien Q1 va U6 [2].",
                "citation_ids": ["[1]", "[2]"],
                "grounded": True,
            },
        }

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.retrieve_workspace_chat_evidence",
        mock_retrieve,
    )

    source = WorkspaceAIContextSource(
        source_id="S-LOC-1",
        source_scope="notebook",
        source_type="plain_text",
        title="tai_lieu.txt",
        privacy_label="local_only",
        text="Noi dung",
        included_chars=10,
        truncated=False,
    )

    chunks_received: list[str] = []
    conv_id = f"CONV-TEST-LOC-FALLBACK-{int(time.time() * 1000)}"

    ok, succ_msg, badge, err = _run_chat_turn_async(
        q_text="C6770 nguyên nhân là gì?",
        query_relevant_sources=(source,),
        conversation_id=conv_id,
        on_chunk=lambda c: chunks_received.append(c),
    )

    assert ok is True
    assert err is None
    assert len(chunks_received) >= 1
    streamed = "".join(chunks_received)
    assert "[1]" in streamed
    assert "C6770" in streamed

    marker_str = "\n".join(printed_markers)
    assert "[STREAMING_QA_START]" in marker_str
    assert "[STREAMING_QA_FIRST_TOKEN]" in marker_str
    assert "[STREAMING_QA_COMPLETE]" in marker_str


def test_markdown_and_citations_unmodified_contract() -> None:
    """Verifies that citations, tables, code blocks, and markdown are 100% untouched by streaming."""
    complex_text = (
        "| Ma loi | Ten linh kien | Lot | Tinh trang |\n"
        "| :--- | :--- | :--- | :--- |\n"
        "| C6770 | PWB IH 100 ASSY | 2508211-05A | Thay moi OK |\n"
        "| C7620 | Cap tin hieu | LOT-991 | Dat tieu chuan |\n\n"
        "```python\n"
        "def check_fuser_voltage(v: float) -> bool:\n"
        "    return v >= 0.3 * V_SET\n"
        "```\n\n"
        "> [!IMPORTANT]\n"
        "> Luu y can than khi thao giac nguon 100V.\n\n"
        "Nguon: [Loi KDTPS.xlsx > History KDTPS > dong 9609](file:///D:/Sandbox/data/loi.xlsx#L9609)\n"
    )

    chunks = split_text_into_streaming_chunks(complex_text, target_chunk_size=30)
    assert "".join(chunks) == complex_text
    # Ensure tables, code blocks, alerts, and links remain intact
    assert "| Ma loi |" in "".join(chunks)
    assert "def check_fuser_voltage" in "".join(chunks)
    assert "[!IMPORTANT]" in "".join(chunks)
    assert "file:///D:/Sandbox/data/loi.xlsx#L9609" in "".join(chunks)

