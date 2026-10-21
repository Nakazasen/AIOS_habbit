# -*- coding: utf-8 -*-
"""Bộ điều hợp tích hợp Indra OCR vào bước trích xuất chữ của đường nạp tài liệu.

Nhiệm vụ theo vé DESKTOP-HOME-INDRA-OCR-INGEST-INTEGRATE:
- Tích hợp indra-ocr (1.1.2) làm lớp bổ trợ ở tầng nạp tài liệu của AIOS_habbit.
- Mục đích: biến các PDF kỹ thuật có lớp chữ mỏng hoặc scan thuần thành tài liệu tìm được.
- Cơ chế: dùng lớp chữ sẵn nơi có, OCR bổ sung phần thiếu (hybrid / auto / ocr).
- Cổng kích hoạt:
  (a) PDF có bất kỳ trang nào 0 ký tự lớp chữ -> OCR các trang đó (gate_a_zero_char_pages).
  (b) PDF tổng số trang <= 100 -> chạy Indra cho toàn bộ tài liệu (gate_b_short_doc).
  (c) PDF > 100 trang mà mọi trang đều có lớp chữ -> GIỮ đường cũ, không chạm Indra (gate_c_skipped_long_doc).
  (d) Tài liệu không phải PDF: không đổi (non_pdf).
- Thống kê trích xuất: ghi nhận số ký tự lớp chữ sẵn, số ký tự sau Indra, số trang được OCR,
  có dùng Indra hay không, thời gian nạp.
- Cấu hình tắt/mở: AIOS_INDRA_OCR_ENABLED (mặc định mở=1). Tắt là quay về hành vi cũ 100%.

Tương thích Python 3.11: không dùng PEP 701 multiline f-strings. CPU thuần.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

LOGGER = logging.getLogger(__name__)

# Biến môi trường và cấu hình
ENV_INDRA_OCR_ENABLED = "AIOS_INDRA_OCR_ENABLED"
ENV_INDRA_MAX_PAGES_FULL_DOC = "AIOS_INDRA_MAX_PAGES_FULL_DOC"
ENV_INDRA_CPU_THREADS = "AIOS_INDRA_CPU_THREADS"
DEFAULT_MAX_PAGES_FULL_DOC = 100

# Tên các cổng kích hoạt theo chuẩn nghiệm thu
GATE_RULE_SHORT_DOC = "gate_b_short_doc"
GATE_RULE_ZERO_CHARS = "gate_a_zero_char_pages"
GATE_RULE_SKIPPED_LONG = "gate_c_skipped_long_doc"
GATE_RULE_DISABLED = "disabled_by_config"
GATE_RULE_UNAVAILABLE = "indra_unavailable"
GATE_RULE_NON_PDF = "non_pdf"

# Khóa lưu trữ cache bộ chuyển đổi và thống kê
_CONVERTER_LOCK = threading.RLock()
_CONVERTER_CACHE: Dict[str, Any] = {}
_LAST_STATS_LOCK = threading.Lock()
_LAST_INDRA_STATS: Dict[str, "IndraExtractionStats"] = {}
_MOST_RECENT_STATS: Optional["IndraExtractionStats"] = None


@dataclass(frozen=True)
class IndraExtractionStats:
    """Thống kê chi tiết cho một lần trích xuất tài liệu qua Indra OCR."""

    file_path: str
    total_pages: int
    native_chars: int
    indra_chars: int
    ocr_pages: int
    used_indra: bool
    elapsed_seconds: float
    gate_rule: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Xuất từ điển chứa đủ các trường chuẩn tiếng Việt và tiếng Anh."""
        return {
            "file_path": self.file_path,
            "so_ky_tu_lop_chu_san": self.native_chars,
            "so_ky_tu_sau_indra": self.indra_chars,
            "so_trang_ocr": self.ocr_pages,
            "co_dung_indra": self.used_indra,
            "thoi_gian_nap": round(self.elapsed_seconds, 4),
            "cong_kich_hoat": self.gate_rule,
            "tong_so_trang": self.total_pages,
            "native_chars": self.native_chars,
            "indra_chars": self.indra_chars,
            "ocr_pages": self.ocr_pages,
            "used_indra": self.used_indra,
            "elapsed_seconds": round(self.elapsed_seconds, 4),
            "gate_rule": self.gate_rule,
            "details": self.details,
        }


def is_indra_enabled() -> bool:
    """Kiểm tra cờ cấu hình bật/tắt Indra OCR (mặc định MỞ)."""
    raw = os.environ.get(ENV_INDRA_OCR_ENABLED, "1").strip().lower()
    return raw not in {"0", "false", "no", "off", "disable", "disabled"}


def is_indra_available() -> bool:
    """Kiểm tra thư viện indra_ocr có được cài đặt trong môi trường hiện tại không."""
    return importlib.util.find_spec("indra_ocr") is not None


def indra_cpu_threads() -> int:
    """Số luồng CPU sử dụng cho Indra OCR (mặc định tối đa 8)."""
    default = min(8, os.cpu_count() or 4)
    try:
        return max(1, min(16, int(os.environ.get(ENV_INDRA_CPU_THREADS, str(default)))))
    except (TypeError, ValueError):
        return default


def max_pages_full_doc() -> int:
    """Ngưỡng số trang tối đa để chạy toàn bộ tài liệu (Cổng b, mặc định 100 trang)."""
    try:
        return max(1, int(os.environ.get(ENV_INDRA_MAX_PAGES_FULL_DOC, str(DEFAULT_MAX_PAGES_FULL_DOC))))
    except (TypeError, ValueError):
        return DEFAULT_MAX_PAGES_FULL_DOC


def clear_indra_cache() -> None:
    """Xóa bộ nhớ đệm converter khi cần giải phóng RAM."""
    with _CONVERTER_LOCK:
        _CONVERTER_CACHE.clear()


def record_indra_stats(stats: IndraExtractionStats) -> None:
    """Ghi nhận thống kê vào bộ nhớ và tệp nhật ký nạp local_runs/indra_ingest.jsonl."""
    global _MOST_RECENT_STATS
    with _LAST_STATS_LOCK:
        _LAST_INDRA_STATS[stats.file_path] = stats
        _MOST_RECENT_STATS = stats

    # Ghi nhận vào tệp nhật ký nếu có thể
    try:
        log_dir = Path("local_runs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "indra_ingest.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(stats.to_dict(), ensure_ascii=False) + "\n")
    except Exception as exc:
        LOGGER.debug("Could not append to indra_ingest.jsonl: %s", exc)

    LOGGER.info(
        "Indra OCR Ingest Stats: file=%s, native_chars=%d, indra_chars=%d, ocr_pages=%d, used_indra=%s, gate=%s, time=%.3fs",
        stats.file_path,
        stats.native_chars,
        stats.indra_chars,
        stats.ocr_pages,
        stats.used_indra,
        stats.gate_rule,
        stats.elapsed_seconds,
    )


def get_last_indra_stats(path: str | Path | None = None) -> Optional[IndraExtractionStats]:
    """Lấy thống kê trích xuất Indra gần nhất theo đường dẫn tệp hoặc phiên nạp gần nhất."""
    with _LAST_STATS_LOCK:
        if path is not None:
            return _LAST_INDRA_STATS.get(str(path))
        return _MOST_RECENT_STATS


def evaluate_pdf_gate(
    path: Path,
    routes: Optional[Sequence[Any]] = None,
) -> Tuple[bool, str, List[int], int, int]:
    """Đánh giá cổng kích hoạt cho tài liệu PDF.

    Trả về tuple:
        (should_use_indra: bool, gate_rule: str, pages_to_ocr: List[int], total_pages: int, native_chars: int)
    """
    if path.suffix.lower() != ".pdf":
        return (False, GATE_RULE_NON_PDF, [], 0, 0)

    if not is_indra_enabled():
        return (False, GATE_RULE_DISABLED, [], 0, 0)

    if not is_indra_available():
        return (False, GATE_RULE_UNAVAILABLE, [], 0, 0)

    # Đếm số trang và số ký tự lớp chữ sẵn
    total_pages = 0
    native_chars = 0
    zero_char_pages: List[int] = []

    if routes is not None and len(routes) > 0:
        total_pages = len(routes)
        for route in routes:
            page_num = getattr(route, "page", 1)
            text = str(getattr(route, "text", "") or "").strip()
            char_count = len(text)
            native_chars += char_count
            if char_count == 0:
                zero_char_pages.append(page_num)
    else:
        # Tự quét nhanh bằng PyMuPDF
        try:
            import fitz

            doc = fitz.open(str(path))
            try:
                total_pages = len(doc)
                for page_idx in range(total_pages):
                    text = str(doc[page_idx].get_text("text") or "").strip()
                    char_count = len(text)
                    native_chars += char_count
                    if char_count == 0:
                        zero_char_pages.append(page_idx + 1)
            finally:
                doc.close()
        except Exception:
            # Fallback nếu fitz lỗi: dùng pypdfium2
            try:
                import pypdfium2 as pdfium

                doc = pdfium.PdfDocument(str(path))
                total_pages = len(doc)
                for page_idx in range(total_pages):
                    text = str(doc[page_idx].get_textpage().get_text_range() or "").strip()
                    char_count = len(text)
                    native_chars += char_count
                    if char_count == 0:
                        zero_char_pages.append(page_idx + 1)
            except Exception:
                pass

    if total_pages == 0:
        return (False, "empty_pdf", [], 0, 0)

    limit_full = max_pages_full_doc()

    # Quy tắc (b): PDF tổng số trang <= 100 -> chạy Indra cho toàn bộ tài liệu
    if total_pages <= limit_full:
        pages_all = list(range(1, total_pages + 1))
        return (True, GATE_RULE_SHORT_DOC, pages_all, total_pages, native_chars)

    # PDF > 100 trang:
    # Quy tắc (c): PDF > 100 trang mà mọi trang đều có lớp chữ -> GIỮ đường cũ, không chạm Indra
    if len(zero_char_pages) == 0:
        return (False, GATE_RULE_SKIPPED_LONG, [], total_pages, native_chars)

    # Quy tắc (a): PDF > 100 trang và có trang 0 ký tự lớp chữ -> OCR các trang đó
    return (True, GATE_RULE_ZERO_CHARS, zero_char_pages, total_pages, native_chars)


def get_indra_converter(mode: str = "auto") -> Any:
    """Lấy đối tượng indra_ocr.Converter từ cache hoặc khởi tạo mới."""
    import indra_ocr

    cache_key = f"{mode}_{indra_cpu_threads()}"
    with _CONVERTER_LOCK:
        if cache_key not in _CONVERTER_CACHE:
            _CONVERTER_CACHE[cache_key] = indra_ocr.load(
                mode=mode,
                threads=indra_cpu_threads(),
            )
        return _CONVERTER_CACHE[cache_key]


def run_indra_extraction(
    path: Path,
    routes: Optional[Sequence[Any]] = None,
) -> Tuple[List[Any], IndraExtractionStats]:
    """Thực thi trích xuất tài liệu qua Indra OCR theo đúng quy chuẩn cổng kích hoạt.

    Trả về (results: list[ExtractionResult], stats: IndraExtractionStats).
    Nếu cổng kích hoạt trả về False, results trả về danh sách rỗng để bộ trích xuất gốc tiếp tục.
    """
    from aios_habit.document_extractors import ExtractionResult

    started = time.perf_counter()
    file_path_str = str(path)

    should_run, gate_rule, pages_to_ocr, total_pages, native_chars = evaluate_pdf_gate(path, routes=routes)

    if not should_run:
        elapsed = time.perf_counter() - started
        stats = IndraExtractionStats(
            file_path=file_path_str,
            total_pages=total_pages,
            native_chars=native_chars,
            indra_chars=native_chars,
            ocr_pages=0,
            used_indra=False,
            elapsed_seconds=elapsed,
            gate_rule=gate_rule,
            details={"skipped_reason": gate_rule},
        )
        record_indra_stats(stats)
        return ([], stats)

    # Thực thi trích xuất bằng Indra OCR
    results: List[ExtractionResult] = []
    ocr_page_count = 0
    total_indra_chars = 0

    try:
        # Trường hợp 1: Chạy cho toàn bộ tài liệu (gate_b_short_doc: tổng số trang <= 100)
        if gate_rule == GATE_RULE_SHORT_DOC:
            # Nếu toàn bộ tài liệu không có chữ sẵn (scan thuần) -> dùng mode='ocr'
            mode = "ocr" if native_chars == 0 else "auto"
            conv = get_indra_converter(mode=mode)
            pages = list(conv.convert(file_path_str))

            for page_idx, page in pages:
                page_num = page_idx + 1
                page_text = str(page.markdown or "").strip()
                page_source = str(getattr(page, "source", "unknown") or "unknown")

                is_ocr_page = page_source in {"ocr", "hybrid"}
                if is_ocr_page:
                    ocr_page_count += 1
                total_indra_chars += len(page_text)

                extractor_name = f"indra_ocr_{page_source}"
                element_type = "pdf_page_ocr" if is_ocr_page else "pdf_markdown_page"
                status = "extracted" if page_text else "empty_text"

                res = ExtractionResult(
                    text=page_text,
                    file_type=".pdf",
                    extractor_name=extractor_name,
                    extraction_status=status,
                    warning=str(getattr(page, "note", "") or ""),
                    section=f"page {page_num}",
                    page=str(page_num),
                    ocr_engine="indra_ocr",
                    ocr_lang="auto",
                    element_type=element_type,
                )
                results.append(res)

        # Trường hợp 2: PDF > 100 trang có một số trang 0 chữ (gate_a_zero_char_pages)
        elif gate_rule == GATE_RULE_ZERO_CHARS:
            import pypdfium2 as pdfium

            conv = get_indra_converter(mode="ocr")
            pdfium_doc = pdfium.PdfDocument(file_path_str)
            ocr_set = set(pages_to_ocr)

            # Bản đồ văn bản gốc theo trang
            native_map: Dict[int, Any] = {}
            if routes is not None:
                for r in routes:
                    native_map[getattr(r, "page", 1)] = r

            for page_num in range(1, total_pages + 1):
                if page_num in ocr_set:
                    # OCR trang 0 chữ
                    page_obj = conv.pdf_page(file_path_str, pdfium_doc, page_num - 1)
                    page_text = str(page_obj.markdown or "").strip()
                    page_source = str(getattr(page_obj, "source", "ocr") or "ocr")
                    ocr_page_count += 1
                    total_indra_chars += len(page_text)

                    results.append(
                        ExtractionResult(
                            text=page_text,
                            file_type=".pdf",
                            extractor_name=f"indra_ocr_{page_source}",
                            extraction_status="extracted" if page_text else "empty_text",
                            warning=str(getattr(page_obj, "note", "") or ""),
                            section=f"page {page_num}",
                            page=str(page_num),
                            ocr_engine="indra_ocr",
                            ocr_lang="auto",
                            element_type="pdf_page_ocr",
                        )
                    )
                else:
                    # Giữ nguyên văn bản gốc
                    route_obj = native_map.get(page_num)
                    native_page_text = str(getattr(route_obj, "text", "") or "").strip() if route_obj else ""
                    total_indra_chars += len(native_page_text)
                    results.append(
                        ExtractionResult(
                            text=native_page_text,
                            file_type=".pdf",
                            extractor_name=getattr(route_obj, "extractor", "pymupdf_native") if route_obj else "pymupdf_native",
                            extraction_status="extracted" if native_page_text else "empty_text",
                            warning=getattr(route_obj, "warning", "") if route_obj else "",
                            section=f"page {page_num}",
                            page=str(page_num),
                            element_type="pdf_markdown_page",
                        )
                    )

        elapsed = time.perf_counter() - started
        stats = IndraExtractionStats(
            file_path=file_path_str,
            total_pages=total_pages,
            native_chars=native_chars,
            indra_chars=total_indra_chars,
            ocr_pages=ocr_page_count,
            used_indra=True,
            elapsed_seconds=elapsed,
            gate_rule=gate_rule,
            details={"ocr_page_count": ocr_page_count, "pages_requested": pages_to_ocr},
        )
        record_indra_stats(stats)
        return (results, stats)

    except Exception as exc:
        LOGGER.exception("Indra OCR extraction encountered an error for %s: %s", file_path_str, exc)
        elapsed = time.perf_counter() - started
        stats = IndraExtractionStats(
            file_path=file_path_str,
            total_pages=total_pages,
            native_chars=native_chars,
            indra_chars=native_chars,
            ocr_pages=0,
            used_indra=False,
            elapsed_seconds=elapsed,
            gate_rule=f"error_{type(exc).__name__}",
            details={"error": str(exc)},
        )
        record_indra_stats(stats)
        return ([], stats)
