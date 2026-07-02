from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from aios_habit.workspace_chat_answer_preview import (
    MAX_PREVIEW_CHARS_PER_SOURCE,
    MAX_SOURCES_IN_ANSWER,
    WorkspaceTrialSourceInput,
    build_trial_answer_preview,
)

FORBIDDEN_COPY = [
    "RAG", "vector", "embedding", "chunk", "retrieval", "citation", "claim",
    "provider router", "Mermaid", "Nguồn AIOS đã dùng", "Nguồn chứng minh",
    "AIOS đã phân tích", "AIOS đã đối chiếu", "AIOS đã trích dẫn",
    "Kết luận từ tài liệu", "Dựa trên tài liệu, kết luận là",
]


def _source(**kwargs):
    defaults = dict(
        source_id="SRC-TEST",
        source_scope="display-scope",
        source_type="text",
        title="Nguồn thử nghiệm",
        content_preview="Đoạn xem trước ngắn",
        content_text="Nội dung đầy đủ",
    )
    defaults.update(kwargs)
    return WorkspaceTrialSourceInput(**defaults)


def test_no_enabled_sources_copy():
    preview = build_trial_answer_preview("Câu hỏi là gì?", [])
    assert "Chỉ xem trước trên máy" in preview.answer_text
    assert "AIOS chưa nối AI thật ở bước này." in preview.answer_text
    assert "Chưa có nguồn nào đang bật cho cuộc trò chuyện này." in preview.answer_text
    assert "Đây chưa phải câu trả lời phân tích cuối cùng." in preview.answer_text


def test_enabled_notebook_source_shows_friendly_fields_without_ids_or_internal_scope():
    preview = build_trial_answer_preview("Hỏi", [_source(source_id="SRC-SECRET", source_scope="notebook", title="Sổ vận hành", content_preview="Dữ liệu ca sáng")])
    assert "Sổ vận hành" in preview.answer_text
    assert "Văn bản" in preview.answer_text
    assert "Dữ liệu ca sáng" in preview.answer_text
    assert "SRC-SECRET" not in preview.answer_text
    assert "notebook" not in preview.answer_text


def test_temporary_pasted_text_does_not_include_full_long_text():
    long_text = "A" * 500
    preview = build_trial_answer_preview("Hỏi", [_source(title="Log tạm", content_preview="", content_text=long_text)])
    assert "Log tạm" in preview.answer_text
    assert "A" * MAX_PREVIEW_CHARS_PER_SOURCE in preview.answer_text
    assert long_text not in preview.answer_text


def test_xlsx_uses_persisted_preview_without_reparse(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Excel parser must not be called")

    import aios_habit.workspace_chat_excel as excel
    monkeypatch.setattr(excel, "extract_xlsx_text", fail)
    preview = build_trial_answer_preview("Hỏi", [_source(source_type="xlsx", title="bang.xlsx", content_preview="Preview đã lưu", content_text="Full")])
    assert "bang.xlsx" in preview.answer_text
    assert "Excel" in preview.answer_text
    assert "Preview đã lưu" in preview.answer_text
    assert "Full" not in preview.answer_text


def test_blank_preview_fallback_caps_from_content_text():
    text = "  Nội dung   dài  " + "x" * 400
    preview = build_trial_answer_preview("Hỏi", [_source(content_preview="", content_text=text)])
    source_preview = preview.enabled_sources[0].preview
    assert source_preview.startswith("Nội dung dài")
    assert len(source_preview) == MAX_PREVIEW_CHARS_PER_SOURCE


def test_unicode_is_preserved():
    preview = build_trial_answer_preview("質問 tiếng Việt", [_source(title="メール 日本", content_preview="Lỗi vận hành 日本語")])
    assert "質問 tiếng Việt" in preview.answer_text
    assert "メール 日本" in preview.answer_text
    assert "Lỗi vận hành 日本語" in preview.answer_text


def test_many_sources_are_capped_and_report_remaining_count():
    sources = [_source(source_id=f"SRC-{i}", title=f"Nguồn {i}", content_preview="p" * 350) for i in range(23)]
    preview = build_trial_answer_preview("Hỏi", sources)
    assert len(preview.enabled_sources) == MAX_SOURCES_IN_ANSWER
    assert "Nguồn 19" in preview.answer_text
    assert "Nguồn 20" not in preview.answer_text
    assert "Còn 3 nguồn đang bật chưa hiển thị trong bản xem trước." in preview.answer_text
    assert all(len(item.preview) <= MAX_PREVIEW_CHARS_PER_SOURCE for item in preview.enabled_sources)


def test_forbidden_copy_scan():
    preview = build_trial_answer_preview("Hỏi", [_source()])
    lowered = preview.answer_text.lower()
    for phrase in FORBIDDEN_COPY:
        assert phrase.lower() not in lowered


def test_helper_is_pure_architecture():
    module_path = Path("src/aios_habit/workspace_chat_answer_preview.py")
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_imports = ("streamlit", "workspace_chat_store", "workspace_chat_excel", "openpyxl", "requests", "urllib", "socket")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(alias.name.startswith(name) for name in forbidden_imports)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not any(module.startswith(name) or name in module for name in forbidden_imports)
    forbidden_calls = {"open", "write", "request", "urlopen"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden_calls
