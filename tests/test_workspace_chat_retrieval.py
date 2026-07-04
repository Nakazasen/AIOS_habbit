from __future__ import annotations

import pytest
import re
import sqlite3
from pathlib import Path

from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_retrieval import (
    retrieve_local_evidence,
    chunk_source_text,
    sanitize_citation_title,
    map_workspace_privacy,
    MAX_SOURCES,
    MAX_TOTAL_INDEXED_CHARS,
    MAX_CHUNKS,
)

def test_sanitize_citation_title():
    assert sanitize_citation_title("simple_name.txt") == "simple_name.txt"
    assert sanitize_citation_title("C:\\absolute\\path\\to\\my_file.xlsx") == "my_file.xlsx"
    assert sanitize_citation_title("/usr/local/var/tmp/data.csv") == "data.csv"
    assert sanitize_citation_title("") == "unnamed-source"

def test_map_workspace_privacy():
    assert map_workspace_privacy("machine_only") == "cloud_safe"
    assert map_workspace_privacy("cloud_allowed") == "cloud_safe"
    assert map_workspace_privacy("cloud_safe") == "cloud_safe"
    assert map_workspace_privacy("public") == "cloud_safe"
    assert map_workspace_privacy("normal") == "cloud_safe"
    assert map_workspace_privacy("local_only") == "local_only"
    assert map_workspace_privacy("") == "local_only"
    assert map_workspace_privacy(None) == "local_only"
    assert map_workspace_privacy("unknown") == "local_only"

def test_chunk_source_text():
    text = "A" * 2500
    chunks = chunk_source_text(text, chunk_size=1200, overlap=120)
    # Chunk 1: 0 to 1200 (length 1200)
    # Chunk 2: (1200 - 120) = 1080 to 2280 (length 1200)
    # Chunk 3: (2280 - 120) = 2160 to end (length 340)
    assert len(chunks) == 3
    assert len(chunks[0]) == 1200
    assert len(chunks[1]) == 1200
    assert len(chunks[2]) == 340
    # Overlap check
    assert chunks[1].startswith(chunks[0][-120:])

def test_retrieve_local_evidence_txt():
    source_txt = WorkspaceAIContextSource(
        source_id="src_txt",
        source_scope="temporary",
        source_type="txt",
        title="D:\\Sandbox\\AIOS_habbit\\data.txt",
        privacy_label="machine_only",
        text="Đây là tài liệu thử nghiệm chứa thông tin bí mật về InterStock và dự án Habitant.",
        included_chars=81,
        truncated=False,
    )

    res = retrieve_local_evidence("habitant", (source_txt,))
    assert res["retrieval_applied"] is True
    assert res["summary_count"] == 1
    assert len(res["evidence_items"]) == 1

    # Path is sanitized in title/citations
    assert res["evidence_items"][0]["title"] == "data.txt"
    assert res["citations"][0]["title"] == "data.txt"
    assert "InterStock" in res["evidence_items"][0]["text"]

def test_disabled_source_not_retrieved():
    # If the source is not passed to context_sources parameter, it must never be retrieved.
    # context_sources passed represents ONLY enabled sources.
    source_enabled = WorkspaceAIContextSource(
        source_id="src_enabled",
        source_scope="temporary",
        source_type="txt",
        title="enabled.txt",
        privacy_label="machine_only",
        text="Dữ liệu quan trọng về doanh thu và kế hoạch Phase 4.",
        included_chars=51,
        truncated=False,
    )
    # Even if the query mentions "doanh thu", we only pass a dummy source.
    dummy_source = WorkspaceAIContextSource(
        source_id="src_dummy",
        source_scope="temporary",
        source_type="txt",
        title="dummy.txt",
        privacy_label="machine_only",
        text="Nội dung khác hoàn toàn không liên quan.",
        included_chars=39,
        truncated=False,
    )

    res = retrieve_local_evidence("doanh thu", (dummy_source,))
    assert res["summary_count"] == 0
    assert res["safe_owner_message"] == "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật."

def test_long_source_relevant_tail():
    # Verify that a long source does not get truncated at the first chunk, and tail is searchable
    head_text = "Không liên quan. " * 300  # ~5100 chars
    tail_text = " Từ khóa đặc biệt: Opcenter Error Code 9999!"
    long_text = head_text + tail_text

    source = WorkspaceAIContextSource(
        source_id="src_long",
        source_scope="notebook",
        source_type="txt",
        title="long_log.log",
        privacy_label="cloud_allowed",
        text=long_text,
        included_chars=len(long_text),
        truncated=False,
    )

    res = retrieve_local_evidence("Opcenter Error Code", (source,))
    assert res["summary_count"] >= 1
    # Check that retrieved text contains the tail text
    found = any("Opcenter Error Code" in item["text"] for item in res["evidence_items"])
    assert found is True

def test_xlsx_docx_style_retrieval():
    xlsx_src = WorkspaceAIContextSource(
        source_id="src_xlsx",
        source_scope="temporary",
        source_type="xlsx",
        title="data.xlsx",
        privacy_label="machine_only",
        text="[Sheet1] Row 1: Nguyễn Văn A | Developer\n[Sheet1] Row 2: Trần Thị B | Designer",
        included_chars=81,
        truncated=False,
    )
    docx_src = WorkspaceAIContextSource(
        source_id="src_docx",
        source_scope="temporary",
        source_type="docx",
        title="report.docx",
        privacy_label="machine_only",
        text="Habitant Phase 4: Thiết lập Workspace Chat Local Retrieval.",
        included_chars=59,
        truncated=False,
    )

    res = retrieve_local_evidence("Nguyễn Văn A", (xlsx_src, docx_src))
    assert res["summary_count"] == 1
    assert res["evidence_items"][0]["source_id"] == "src_xlsx"

    res_docx = retrieve_local_evidence("Habitant Phase 4", (xlsx_src, docx_src))
    assert res_docx["summary_count"] == 1
    assert res_docx["evidence_items"][0]["source_id"] == "src_docx"

def test_deterministic_ranking():
    src1 = WorkspaceAIContextSource(
        source_id="src_1",
        source_scope="temporary",
        source_type="txt",
        title="doc1.txt",
        privacy_label="machine_only",
        text="Từ khóa Từ khóa Từ khóa. Đây là văn bản chứa từ khóa rất nhiều lần.",
        included_chars=67,
        truncated=False,
    )
    src2 = WorkspaceAIContextSource(
        source_id="src_2",
        source_scope="temporary",
        source_type="txt",
        title="doc2.txt",
        privacy_label="machine_only",
        text="Từ khóa. Chỉ có một từ khóa ở đây.",
        included_chars=34,
        truncated=False,
    )

    res = retrieve_local_evidence("Từ khóa", (src1, src2))
    assert res["summary_count"] >= 2
    # doc1 should have a higher score because of frequency, or deterministic sort
    assert res["evidence_items"][0]["source_id"] == "src_1"

def test_no_legacy_or_streamlit_imports():
    source_file = Path(__file__).parent.parent / "src" / "aios_habit" / "workspace_chat_retrieval.py"
    content = source_file.read_text(encoding="utf-8")

    forbidden = ["streamlit", "studio", "case_cockpit", "provider", "router", "network"]
    for word in forbidden:
        import_match = re.search(r"^\s*(import\s+.*" + word + r"|from\s+.*" + word + r"\s+import)", content, re.MULTILINE)
        assert import_match is None, f"Forbidden import statement containing '{word}' found in retrieval adapter!"

def test_ui_copy_and_no_jargon():
    app_file = Path(__file__).parent.parent / "src" / "aios_habit" / "workspace_chat_app.py"
    app_content = app_file.read_text(encoding="utf-8")

    ret_file = Path(__file__).parent.parent / "src" / "aios_habit" / "workspace_chat_retrieval.py"
    ret_content = ret_file.read_text(encoding="utf-8")

    # 1. Verify exact required Vietnamese copy
    assert "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật." in app_content
    assert "Chi tiết các đoạn tài liệu được sử dụng" in app_content

    assert "Đã dùng" in ret_content
    assert "đoạn liên quan từ" in ret_content
    assert "nguồn." in ret_content

    # 2. Verify no owner-facing technical jargon in Streamlit calls of app code
    st_render_patterns = [r"st\.write", r"st\.info", r"st\.error", r"st\.success", r"st\.warning", r"st\.markdown", r"st\.text_area"]
    jargons = ["rag", "fts", "chunk", "embedding"]

    for line in app_content.splitlines():
        if "#" in line:
            line = line.split("#")[0]

        is_render_call = any(re.search(pattern, line) for pattern in st_render_patterns)
        if is_render_call:
            for jargon in jargons:
                assert jargon not in line.lower(), f"Forbidden jargon '{jargon}' found in UI render statement: {line}"

# Failure handling tests
def test_retrieve_local_evidence_sqlite_failure_handling(monkeypatch):
    source_txt = WorkspaceAIContextSource(
        source_id="src_txt",
        source_scope="temporary",
        source_type="txt",
        title="data.txt",
        privacy_label="machine_only",
        text="Đây là tài liệu thử nghiệm.",
        included_chars=28,
        truncated=False,
    )

    # 1. Mock schema creation failure
    def mock_create_schema_fail(*args, **kwargs):
        raise sqlite3.OperationalError("Mock database creation error")
    monkeypatch.setattr("aios_habit.workspace_chat_retrieval.create_rag_search_schema", mock_create_schema_fail)

    res = retrieve_local_evidence("tài liệu", (source_txt,))
    # Must not raise exception, instead return graceful empty result
    assert res["retrieval_applied"] is True
    assert res["summary_count"] == 0
    assert res["evidence_items"] == []
    assert res["safe_owner_message"] == "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật."

    # 2. Mock search failure
    monkeypatch.undo()
    def mock_search_fail(*args, **kwargs):
        raise sqlite3.OperationalError("Mock query error")
    monkeypatch.setattr("aios_habit.workspace_chat_retrieval.search_rag_chunks", mock_search_fail)

    res2 = retrieve_local_evidence("tài liệu", (source_txt,))
    assert res2["retrieval_applied"] is True
    assert res2["summary_count"] == 0
    assert res2["evidence_items"] == []
    assert res2["safe_owner_message"] == "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật."

# Real guard tests
def test_guards_max_sources_cap_real():
    # Limit: MAX_SOURCES = 20
    sources = []
    for i in range(25):
        sources.append(WorkspaceAIContextSource(
            source_id=f"src_{i}",
            source_scope="temporary",
            source_type="txt",
            title=f"doc_{i}.txt",
            privacy_label="machine_only",
            text=f"Văn bản số {i}",
            included_chars=12,
            truncated=False,
        ))
    res = retrieve_local_evidence("văn bản", tuple(sources))
    assert res["indexed_source_count"] == 20
    assert res["truncated_by_guard"] is True

def test_guards_max_chunks_cap_real():
    # Limit: MAX_CHUNKS = 500. We create 20 sources, each 40,000 characters.
    # Each source yields ~37 chunks. 20 * 37 = 740 chunks, which exceeds 500.
    large_text = "A" * 40000
    sources = []
    for i in range(20):
        sources.append(WorkspaceAIContextSource(
            source_id=f"src_{i}",
            source_scope="temporary",
            source_type="txt",
            title=f"doc_{i}.txt",
            privacy_label="machine_only",
            text=large_text,
            included_chars=len(large_text),
            truncated=False,
        ))
    res = retrieve_local_evidence("dummy_query", tuple(sources))
    assert res["indexed_chunk_count"] == 500
    assert res["truncated_by_guard"] is True

def test_guards_max_chars_cap_real(monkeypatch):
    # Set MAX_TOTAL_INDEXED_CHARS to a lower value (e.g., 100,000 chars)
    # so that character limit is hit before chunk limit (500 chunks * 1200 = 600,000 chars)
    monkeypatch.setattr("aios_habit.workspace_chat_retrieval.MAX_TOTAL_INDEXED_CHARS", 100000)

    long_text = "A" * 150000
    source = WorkspaceAIContextSource(
        source_id="src_huge",
        source_scope="temporary",
        source_type="txt",
        title="huge.txt",
        privacy_label="machine_only",
        text=long_text,
        included_chars=len(long_text),
        truncated=False,
    )
    res = retrieve_local_evidence("dummy_query", (source,))
    assert res["indexed_char_count"] == 100000
    assert res["truncated_by_guard"] is True
