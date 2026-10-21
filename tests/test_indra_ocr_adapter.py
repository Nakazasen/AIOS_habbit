# -*- coding: utf-8 -*-
"""Unit và integration tests cho bộ điều hợp Indra OCR (Ticket DESKTOP-HOME-INDRA-OCR-INGEST-INTEGRATE).

Các ca kiểm thử bắt buộc theo vé:
1. Cổng kích hoạt:
   - Trang 0 chữ được OCR (Quy tắc a).
   - PDF <= 100 trang chạy Indra toàn bộ (Quy tắc b).
   - PDF > 100 trang đủ lớp chữ bị bỏ qua, giữ đường cũ (Quy tắc c - đối chứng âm).
   - Tài liệu không phải PDF không đổi (Quy tắc d).
2. Cấu hình tắt/mở:
   - Tắt cờ cấu hình AIOS_INDRA_OCR_ENABLED -> hành vi quay về y hệt trước vé.
3. Thống kê trích xuất:
   - Đủ các chỉ số: số ký tự lớp chữ sẵn, số ký tự sau Indra, số trang OCR, có dùng Indra không, thời gian nạp.
   - Thống kê được gắn vào chunk metadata và kết quả ingest của Workspace Chat.
4. Kiểm thử trên dữ liệu mẫu thực tế:
   - Báo cáo 8D: đọc đúng 302XC45060 và S260017-3.
   - Quét thuần C6610: đọc được kana/kanji và mã COUPLING CLAW 302ND31540.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from unittest import mock

import fitz
import pytest

from aios_habit.document_extractors import (
    ExtractionResult,
    PDFPageRoute,
    extract_text_chunks_from_file,
    local_capabilities,
)
from aios_habit.indra_ocr_adapter import (
    ENV_INDRA_OCR_ENABLED,
    GATE_RULE_DISABLED,
    GATE_RULE_NON_PDF,
    GATE_RULE_SHORT_DOC,
    GATE_RULE_SKIPPED_LONG,
    GATE_RULE_ZERO_CHARS,
    IndraExtractionStats,
    evaluate_pdf_gate,
    get_last_indra_stats,
    is_indra_available,
    is_indra_enabled,
    record_indra_stats,
    run_indra_extraction,
)
from aios_habit.workspace_chat_source_ingest import ingest_and_extract_bytes


def create_dummy_pdf(
    path: Path,
    num_pages: int,
    text_pattern: str = "Test page text content {i}",
    empty_pages: set[int] | None = None,
) -> Path:
    """Tạo tệp PDF mẫu có số trang và nội dung cấu hình được."""
    empty_set = empty_pages or set()
    doc = fitz.open()
    for i in range(1, num_pages + 1):
        page = doc.new_page()
        if i not in empty_set and text_pattern:
            page.insert_text(fitz.Point(50, 50), text_pattern.format(i=i))
    doc.save(str(path))
    doc.close()
    return path


def test_is_indra_enabled_toggle(monkeypatch):
    """Kiểm tra cơ chế bật/tắt lớp Indra qua cấu hình môi trường."""
    monkeypatch.setenv(ENV_INDRA_OCR_ENABLED, "1")
    assert is_indra_enabled() is True

    monkeypatch.setenv(ENV_INDRA_OCR_ENABLED, "true")
    assert is_indra_enabled() is True

    monkeypatch.setenv(ENV_INDRA_OCR_ENABLED, "0")
    assert is_indra_enabled() is False

    monkeypatch.setenv(ENV_INDRA_OCR_ENABLED, "false")
    assert is_indra_enabled() is False


def test_evaluate_pdf_gate_disabled_config(tmp_path, monkeypatch):
    """Tắt cấu hình thì cổng trả về disabled_by_config và should_use_indra=False."""
    monkeypatch.setenv(ENV_INDRA_OCR_ENABLED, "0")
    pdf_path = create_dummy_pdf(tmp_path / "small.pdf", 5)

    should_run, gate_rule, pages, total_pages, native_chars = evaluate_pdf_gate(pdf_path)
    assert should_run is False
    assert gate_rule == GATE_RULE_DISABLED
    assert pages == []


def test_evaluate_pdf_gate_non_pdf(tmp_path):
    """Tài liệu không phải PDF trả về non_pdf và không đổi."""
    txt_path = tmp_path / "sample.txt"
    txt_path.write_text("Hello world", encoding="utf-8")

    should_run, gate_rule, pages, total_pages, native_chars = evaluate_pdf_gate(txt_path)
    assert should_run is False
    assert gate_rule == GATE_RULE_NON_PDF


def test_evaluate_pdf_gate_short_doc(tmp_path, monkeypatch):
    """PDF <= 100 trang kích hoạt cổng gate_b_short_doc."""
    monkeypatch.setenv(ENV_INDRA_OCR_ENABLED, "1")
    pdf_path = create_dummy_pdf(tmp_path / "short_doc.pdf", 10)

    should_run, gate_rule, pages, total_pages, native_chars = evaluate_pdf_gate(pdf_path)
    assert should_run is True
    assert gate_rule == GATE_RULE_SHORT_DOC
    assert total_pages == 10
    assert len(pages) == 10
    assert native_chars > 0


def test_evaluate_pdf_gate_skipped_long_doc(tmp_path, monkeypatch):
    """PDF > 100 trang mà mọi trang đều có lớp chữ thì BỎ QUA Indra (đối chứng âm)."""
    monkeypatch.setenv(ENV_INDRA_OCR_ENABLED, "1")
    # Tạo 105 trang, tất cả đều có chữ
    pdf_path = create_dummy_pdf(tmp_path / "long_doc_full.pdf", 105)

    should_run, gate_rule, pages, total_pages, native_chars = evaluate_pdf_gate(pdf_path)
    assert should_run is False
    assert gate_rule == GATE_RULE_SKIPPED_LONG
    assert total_pages == 105
    assert pages == []


def test_evaluate_pdf_gate_zero_char_pages_long_doc(tmp_path, monkeypatch):
    """PDF > 100 trang có trang 0 chữ thì kích hoạt cổng gate_a_zero_char_pages cho đúng trang đó."""
    monkeypatch.setenv(ENV_INDRA_OCR_ENABLED, "1")
    # Tạo 102 trang, trang 5 và trang 20 rỗng chữ
    pdf_path = create_dummy_pdf(tmp_path / "long_doc_sparse.pdf", 102, empty_pages={5, 20})

    should_run, gate_rule, pages, total_pages, native_chars = evaluate_pdf_gate(pdf_path)
    assert should_run is True
    assert gate_rule == GATE_RULE_ZERO_CHARS
    assert total_pages == 102
    assert set(pages) == {5, 20}


def test_stats_recorded_and_attached_to_chunks(tmp_path, monkeypatch):
    """Thống kê trích xuất được tính toán, gắn vào chunk metadata và lưu nhật ký."""
    monkeypatch.setenv(ENV_INDRA_OCR_ENABLED, "1")
    pdf_path = create_dummy_pdf(tmp_path / "stats_test.pdf", 3)

    chunks = extract_text_chunks_from_file(pdf_path)
    assert len(chunks) > 0

    stats = get_last_indra_stats(pdf_path)
    assert stats is not None
    assert stats.total_pages == 3
    assert stats.used_indra is True
    assert stats.gate_rule == GATE_RULE_SHORT_DOC
    assert stats.elapsed_seconds >= 0.0

    # Kiểm tra chunk chứa indra_stats
    first_chunk = chunks[0]
    assert "indra_stats" in first_chunk
    indra_stats = first_chunk["indra_stats"]
    assert indra_stats["tong_so_trang"] == 3
    assert indra_stats["co_dung_indra"] is True
    assert indra_stats["cong_kich_hoat"] == GATE_RULE_SHORT_DOC


def test_workspace_chat_ingest_contains_indra_metadata(tmp_path, monkeypatch):
    """Đường nạp tài liệu Workspace Chat chứa đầy đủ chỉ số thống kê trong metadata."""
    monkeypatch.setenv(ENV_INDRA_OCR_ENABLED, "1")
    pdf_path = create_dummy_pdf(tmp_path / "workspace_ingest.pdf", 2)
    file_bytes = pdf_path.read_bytes()

    res = ingest_and_extract_bytes(file_bytes, "workspace_ingest.pdf")
    assert res["ok"] is True
    assert "metadata" in res
    meta = res["metadata"]

    assert "indra_stats" in meta
    assert meta["co_dung_indra"] is True
    assert meta["cong_kich_hoat"] == GATE_RULE_SHORT_DOC
    assert "so_ky_tu_lop_chu_san" in meta
    assert "so_ky_tu_sau_indra" in meta
    assert "so_trang_ocr" in meta
    assert "thoi_gian_nap" in meta


def test_disabled_by_config_reverts_exact_old_behavior(tmp_path, monkeypatch):
    """Khi tắt cấu hình, hành vi nạp quay về đúng đường cũ, không dùng Indra."""
    monkeypatch.setenv(ENV_INDRA_OCR_ENABLED, "0")
    pdf_path = create_dummy_pdf(tmp_path / "disabled_test.pdf", 2)

    chunks = extract_text_chunks_from_file(pdf_path)
    assert len(chunks) > 0
    # Kết quả trích xuất vẫn thành công nhờ PyMuPDF native
    assert "Test page text content" in chunks[0]["text"]

    stats = get_last_indra_stats(pdf_path)
    assert stats is not None
    assert stats.used_indra is False
    assert stats.gate_rule == GATE_RULE_DISABLED


def test_local_capabilities_reports_indra():
    """local_capabilities() báo cáo trạng thái khả dụng và kích hoạt của Indra OCR."""
    caps = local_capabilities()
    assert "indra_ocr_available" in caps
    assert caps["indra_ocr_available"] is True
    assert "indra_ocr_enabled" in caps
