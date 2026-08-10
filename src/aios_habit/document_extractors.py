from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

MAX_CHUNKS_PER_FILE = 30
MAX_OCR_IMAGE_BYTES = 8 * 1024 * 1024
MAX_PDF_OCR_PAGES = 3
OCR_TIMEOUT_SECONDS = 20
OCR_MIN_USABLE_CONFIDENCE = 35.0
OCR_SUCCESS_CONFIDENCE = 60.0
DEFAULT_OCR_LANG = "eng"
COMMON_TESSERACT_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"D:\Tools\Tesseract-OCR\tesseract.exe",
)
USABLE_STATUSES = {"success", "extracted_success", "extracted_partial", "ocr_success", "ocr_partial", "extracted"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


class PDFDependencyMissingError(RuntimeError):
    """Raised only when no installed local dependency can open PDFs."""


@dataclass
class ExtractionResult:
    text: str
    file_type: str
    extractor_name: str
    extraction_status: str
    warning: str = ""
    section: str = ""
    page: str = ""
    slide: str = ""
    sheet: str = ""
    row_range: str = ""
    ocr_engine: str = ""
    ocr_lang: str = ""
    ocr_confidence: float | None = None
    ocr_confidence_samples: int = 0
    ocr_preprocessing: str = ""
    ocr_attempts: int = 0
    ocr_quality_reason: str = ""
    element_type: str = ""


@dataclass(frozen=True)
class PDFPageRoute:
    """Normalized, 1-based native extraction and OCR decision for one page."""

    page: int
    text: str = ""
    needs_ocr: bool = False
    extractor: str = "pdf_inspector"
    warning: str = ""
    has_table: bool = False
    has_columns: bool = False


def route_pdf_pages(path: str | Path) -> list[PDFPageRoute]:
    """Use PDF Inspector first, then fail softly to PyMuPDF native text."""
    pdf_path = Path(path)
    try:
        import pdf_inspector

        extracted = pdf_inspector.extract_pages_markdown(str(pdf_path))
        table_pages = {int(value) for value in getattr(extracted, "pages_with_tables", [])}
        column_pages = {int(value) for value in getattr(extracted, "pages_with_columns", [])}
        routes: list[PDFPageRoute] = []
        for raw_page in getattr(extracted, "pages", []):
            page_number = int(getattr(raw_page, "page", len(routes))) + 1
            markdown = str(getattr(raw_page, "markdown", "") or "").strip()
            routes.append(PDFPageRoute(
                page=page_number,
                text=markdown,
                needs_ocr=bool(getattr(raw_page, "needs_ocr", False)) or not _has_meaningful_text(markdown),
                has_table=page_number in table_pages,
                has_columns=page_number in column_pages,
            ))
        if routes:
            if any(route.needs_ocr for route in routes):
                try:
                    import fitz

                    document = fitz.open(str(pdf_path))
                    try:
                        rescued: list[PDFPageRoute] = []
                        for route in routes:
                            if not route.needs_ocr or route.page > len(document):
                                rescued.append(route)
                                continue
                            native_text = str(document[route.page - 1].get_text("text") or "").strip()
                            if _has_meaningful_text(native_text):
                                rescued.append(PDFPageRoute(
                                    page=route.page,
                                    text=native_text,
                                    needs_ocr=False,
                                    extractor="pymupdf_native_rescue",
                                    warning="PDF Inspector requested OCR; PyMuPDF recovered native text",
                                    has_table=route.has_table,
                                    has_columns=route.has_columns,
                                ))
                            else:
                                rescued.append(route)
                        routes = rescued
                    finally:
                        document.close()
                except Exception:
                    pass
            return routes
        raise ValueError("pdf-inspector returned no pages")
    except Exception as exc:  # optional dependency, malformed PDF, or native parser error
        reason = f"{type(exc).__name__}: {exc}"

    try:
        import fitz
    except ImportError as exc:
        raise PDFDependencyMissingError(
            f"PDF extraction unavailable: pdf-inspector failed ({reason}); PyMuPDF is missing"
        ) from exc

    routes = []
    document = fitz.open(str(pdf_path))
    try:
        for page_number, page in enumerate(document, start=1):
            try:
                text = str(page.get_text("text") or "").strip()
            except Exception:
                text = ""
            routes.append(PDFPageRoute(
                page=page_number,
                text=text,
                needs_ocr=not _has_meaningful_text(text),
                extractor="pymupdf_fallback",
                warning=f"pdf-inspector unavailable; used PyMuPDF fallback: {reason}",
            ))
    finally:
        document.close()
    return routes


class _ReadableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag.lower() in {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag.lower() in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and data.strip():
            self._parts.append(data)

    def text(self) -> str:
        return "\n".join(_clean_lines("".join(self._parts).splitlines()))


def _clean_lines(lines: list[str], *, limit: int = 200) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for line in lines:
        text = html.unescape(str(line or ""))
        text = re.sub(r"<[^>\n]{1,160}>", " ", text)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def _has_meaningful_text(text: str) -> bool:
    tokens = re.findall(r"[A-Za-z0-9À-ỹ]{2,}", text or "")
    return len(tokens) >= 2


def _xml_local_name(tag: str) -> str:
    return str(tag or "").rsplit("}", 1)[-1]


def _xml_root_from_zip(archive: zipfile.ZipFile, name: str):
    try:
        return ET.fromstring(archive.read(name))
    except (KeyError, ET.ParseError):
        return None


def _extract_xml_text(xml_text: str) -> list[str]:
    values = re.findall(r"<[^>]*t[^>]*>(.*?)</[^>]*t>", str(xml_text or ""), flags=re.IGNORECASE | re.DOTALL)
    return _clean_lines([html.unescape(value) for value in values], limit=200)


def _text_nodes(element) -> str:
    parts: list[str] = []
    for node in element.iter():
        if _xml_local_name(node.tag) == "t" and node.text:
            parts.append(node.text)
    return " ".join(_clean_lines(parts, limit=200)).strip()


def normalize_extracted_text(text: str, *, max_chars: int = 12000) -> str:
    """Clean noisy extractor output while preserving Vietnamese/Japanese text."""
    lines = []
    for line in str(text or "").splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if not cleaned:
            continue
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[ ,;:/|-]+[-+]?\d+(?:\.\d+)?){3,}", cleaned):
            continue
        if len(cleaned) <= 2 and cleaned.isdigit():
            continue
        lines.append(cleaned)
    normalized = "\n".join(lines)
    return normalized[:max_chars]


def _chunk_result(result: ExtractionResult, path: Path, root: Path | None, max_chars_per_chunk: int) -> list[dict[str, Any]]:
    text = normalize_extracted_text(result.text)
    rel = path.relative_to(root).as_posix() if root else path.name
    base = {
        "source_file": path.name,
        "relative_path": rel,
        "file_type": result.file_type,
        "section": result.section,
        "page": result.page,
        "slide": result.slide,
        "sheet": result.sheet,
        "row_range": result.row_range,
        "privacy_level": "local_only",
        "extractor_name": result.extractor_name,
        "extraction_status": result.extraction_status,
        "warning": result.warning,
        "ocr_engine": result.ocr_engine,
        "ocr_lang": result.ocr_lang,
        "ocr_confidence": result.ocr_confidence,
        "ocr_confidence_samples": result.ocr_confidence_samples,
        "ocr_preprocessing": result.ocr_preprocessing,
        "ocr_attempts": result.ocr_attempts,
        "ocr_quality_reason": result.ocr_quality_reason,
        "element_type": result.element_type,
    }
    if result.extraction_status not in USABLE_STATUSES or not text:
        return [{"text": "", **base}]
    chunks: list[dict[str, Any]] = []
    for idx, start in enumerate(range(0, len(text), max_chars_per_chunk)):
        if idx >= MAX_CHUNKS_PER_FILE:
            break
        part = text[start:start + max_chars_per_chunk]
        section = result.section or f"chars {start}-{start + len(part)}"
        chunks.append({"text": part, **{**base, "section": section}})
    return chunks


def _extract_html(path: Path) -> ExtractionResult:
    parser = _ReadableHTMLParser()
    parser.feed(path.read_text(encoding="utf-8-sig", errors="ignore"))
    parser.close()
    text = parser.text()
    if not _has_meaningful_text(text):
        return ExtractionResult("", path.suffix.lower(), "html_parser", "failed_with_reason", "html has no visible text")
    return ExtractionResult(text, path.suffix.lower(), "html_parser", "extracted_success", section="visible text")


def _extract_pptx(path: Path) -> ExtractionResult:
    slide_lines: list[str] = []
    note_lines: list[str] = []
    media_count = 0
    try:
        with zipfile.ZipFile(path, "r") as archive:
            for name in archive.namelist():
                lowered = name.lower()
                if lowered.startswith("ppt/media/"):
                    media_count += 1
                    continue
                if not lowered.endswith(".xml"):
                    continue
                try:
                    xml_text = archive.read(name).decode("utf-8", errors="ignore")
                except KeyError:
                    continue
                tokens = _extract_xml_text(xml_text)
                if lowered.startswith("ppt/slides/"):
                    slide_lines.extend(tokens)
                elif lowered.startswith("ppt/notesslides/"):
                    note_lines.extend(tokens)
    except zipfile.BadZipFile:
        return ExtractionResult("", ".pptx", "pptx_zip_xml", "failed_with_reason", "invalid pptx zip container")
    sections: list[str] = []
    if slide_lines:
        sections.append("Slide text:\n" + "\n".join(slide_lines[:120]))
    if note_lines:
        sections.append("Speaker notes:\n" + "\n".join(note_lines[:60]))
    if media_count:
        sections.append(f"Embedded media/images: {media_count}")
    if not sections:
        return ExtractionResult("", ".pptx", "pptx_zip_xml", "unsupported_no_local_tool", "pptx has no extractable text payload")
    return ExtractionResult("\n\n".join(sections), ".pptx", "pptx_zip_xml", "extracted_success", section="slides/notes")


def _extract_excel(path: Path) -> list[ExtractionResult]:
    from aios_habit.excel_extractors import extract_excel

    extracted = extract_excel(path, include_images=True, include_charts=True)
    file_type = path.suffix.lower()
    if extracted.dependency_missing:
        message = f"Missing optional Excel dependency: {extracted.dependency_missing}"
        if file_type == ".xls":
            message += "; convert the workbook to .xlsx or install the rag-ingestion-xls extra"
        return [ExtractionResult("", file_type, "excel_structured", "dependency_missing", message)]
    if extracted.error:
        return [ExtractionResult("", file_type, "excel_structured", "failed_with_reason", extracted.error)]

    warnings = [*extracted.warnings, *extracted.truncated_reasons]
    common_warning = "; ".join(dict.fromkeys(warnings))
    status = "extracted_partial" if extracted.partial else "extracted_success"
    results: list[ExtractionResult] = []
    for region in extracted.regions:
        lines = [
            f"Excel sheet: {region.sheet}",
            f"Table range: {region.cell_range}",
        ]
        if region.headers:
            lines.append("Columns: " + " | ".join(region.headers))
        data_offset = len(region.header_rows)
        for offset, row in enumerate(region.rows[data_offset:], start=region.row_range[0] + data_offset):
            lines.append(f"Row {offset}: " + " | ".join(row))
        if not region.rows[data_offset:] and region.rows:
            lines.extend(" | ".join(row) for row in region.rows)
        results.append(ExtractionResult(
            "\n".join(lines), file_type, "excel_structured", status,
            warning=common_warning,
            section=f"table {region.cell_range}",
            sheet=region.sheet,
            row_range=f"{region.row_range[0]}-{region.row_range[1]}",
            element_type="excel_table_region",
        ))

    for chart in extracted.charts:
        results.append(ExtractionResult(
            chart.as_text(), file_type, "excel_structured", status,
            warning=common_warning,
            section=f"chart {chart.index} at {chart.anchor or 'unknown anchor'}",
            sheet=chart.sheet,
            element_type="excel_chart_metadata",
        ))

    if extracted.images:
        try:
            from io import BytesIO
            from PIL import Image
        except ImportError as exc:
            results.append(ExtractionResult(
                "", file_type, "excel_embedded_image", "dependency_missing",
                f"embedded image OCR unavailable: {exc}", element_type="excel_embedded_image",
            ))
        else:
            for embedded in extracted.images:
                try:
                    with Image.open(BytesIO(embedded.data)) as image:
                        image.load()
                        ocr = _ocr_image_object(
                            image,
                            file_type=embedded.extension,
                            page=f"{embedded.sheet}!{embedded.anchor or ('image-' + str(embedded.index))}",
                        )
                except Exception as exc:  # noqa: BLE001
                    ocr = ExtractionResult(
                        "", embedded.extension, "excel_embedded_image", "failed_with_reason",
                        f"embedded image decode failed: {exc}",
                        ocr_engine="none", ocr_lang=_ocr_lang(),
                        ocr_quality_reason="image_decode_failed",
                    )
                ocr.file_type = file_type
                ocr.extractor_name = f"excel_embedded_image+{ocr.extractor_name}"
                ocr.sheet = embedded.sheet
                ocr.section = f"embedded image {embedded.index} at {embedded.anchor or 'unknown anchor'}"
                ocr.element_type = "excel_embedded_image_ocr"
                if common_warning:
                    ocr.warning = "; ".join(item for item in (ocr.warning, common_warning) if item)
                results.append(ocr)

    # Preserve DrawingML text boxes/shapes that are not represented as cell values.
    if file_type in {".xlsx", ".xlsm"}:
        try:
            with zipfile.ZipFile(path, "r") as archive:
                drawing_names = [
                    name for name in archive.namelist()
                    if name.lower().startswith("xl/drawings/drawing") and name.lower().endswith(".xml")
                ]
                shape_texts: list[str] = []
                for drawing_name in drawing_names:
                    shape_texts.extend(_extract_xml_text(archive.read(drawing_name).decode("utf-8", errors="ignore")))
                clean_shapes = _clean_lines(shape_texts, limit=300)
                if clean_shapes:
                    results.append(ExtractionResult(
                        "Excel Shapes/Text Boxes:\n" + "\n".join(clean_shapes),
                        file_type, "excel_structured+zipfile", status,
                        warning=common_warning, section="shapes and text boxes",
                        element_type="excel_drawing_text",
                    ))
        except Exception:
            pass

    if not results:
        return [ExtractionResult("", file_type, "excel_structured", "failed_with_reason", "excel workbook has no readable values, images, charts, or shapes")]
    return results


def _extract_docx(path: Path) -> ExtractionResult:
    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = ["word/document.xml"]
            names.extend(sorted(n for n in archive.namelist() if re.fullmatch(r"word/(header|footer)\d+\.xml", n, flags=re.IGNORECASE)))
            sections: list[str] = []
            for name in names:
                root = _xml_root_from_zip(archive, name)
                if root is None:
                    continue
                lines: list[str] = []
                for child in root.iter():
                    local = _xml_local_name(child.tag)
                    if local in {"p", "tbl"}:
                        text = _text_nodes(child)
                        if text:
                            lines.append(text)
                clean = _clean_lines(lines, limit=300)
                if clean:
                    label = "Document" if name == "word/document.xml" else Path(name).stem
                    sections.append(f"{label}:\n" + "\n".join(clean))
    except zipfile.BadZipFile:
        return ExtractionResult("", ".docx", "docx_zip_xml", "failed_with_reason", "invalid docx zip container")
    text = "\n\n".join(sections)
    if not _has_meaningful_text(text):
        return ExtractionResult("", ".docx", "docx_zip_xml", "failed_with_reason", "docx has no readable text")
    return ExtractionResult(text, ".docx", "docx_zip_xml", "extracted_success", section="word/document.xml")


def _discover_tesseract_cmd() -> str | None:
    env_cmd = os.environ.get("AIOS_TESSERACT_CMD", "").strip().strip('"')
    if env_cmd and Path(env_cmd).exists():
        return env_cmd
    path_cmd = shutil.which("tesseract")
    if path_cmd:
        return path_cmd
    for candidate in COMMON_TESSERACT_PATHS:
        if Path(candidate).exists():
            return candidate
    return None


def _ocr_lang() -> str:
    return os.environ.get("AIOS_OCR_LANG", DEFAULT_OCR_LANG).strip() or DEFAULT_OCR_LANG


def _max_pdf_ocr_pages() -> int:
    try:
        return max(1, int(os.environ.get("AIOS_MAX_PDF_OCR_PAGES", MAX_PDF_OCR_PAGES)))
    except (TypeError, ValueError):
        return MAX_PDF_OCR_PAGES


def _tesseract_available() -> tuple[bool, str, str]:
    cmd = _discover_tesseract_cmd()
    lang = _ocr_lang()
    if not cmd:
        return False, "none", "local OCR unavailable: tesseract executable not found; set AIOS_TESSERACT_CMD or add Tesseract to PATH"
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = cmd
        pytesseract.get_tesseract_version()
        return True, "tesseract", cmd
    except Exception as exc:  # noqa: BLE001
        return False, "none", f"local OCR unavailable with {cmd}: {exc}; OCR lang={lang}"


def _ocr_preprocessing_attempts(image):
    """Return a small deterministic set of local preprocessing attempts."""
    from PIL import ImageEnhance, ImageFilter, ImageOps

    yield "original", image.copy(), "--psm 3"
    grayscale = ImageOps.grayscale(image)
    enhanced = ImageOps.autocontrast(grayscale)
    max_dimension = max(enhanced.size)
    if max_dimension < 2400:
        scale = min(3, max(2, 1200 // max(1, max_dimension)))
        enhanced = enhanced.resize((enhanced.width * scale, enhanced.height * scale))
    yield "grayscale_autocontrast_upscale", enhanced, "--psm 3"
    yield "grayscale_autocontrast_upscale_psm6", enhanced, "--psm 6"
    yield "grayscale_autocontrast_upscale_psm11", enhanced, "--psm 11"
    sharp = ImageEnhance.Contrast(enhanced.filter(ImageFilter.SHARPEN)).enhance(1.8)
    yield "sharpened_contrast_psm11", sharp, "--psm 11"


def _run_tesseract_engine(image):
    """Run the legacy engine and return the neutral OCR adapter contract."""
    from aios_habit.ocr_engines import OCREngineResult

    available, engine, detail = _tesseract_available()
    if not available:
        return OCREngineResult(engine="tesseract", failure_reason=detail)
    lang = _ocr_lang()
    try:
        import pytesseract
        from pytesseract import Output

        if detail and Path(detail).exists():
            pytesseract.pytesseract.tesseract_cmd = detail
        candidates: list[dict[str, Any]] = []
        for profile, prepared, config in _ocr_preprocessing_attempts(image):
            data = pytesseract.image_to_data(
                prepared, lang=lang, config=config,
                timeout=OCR_TIMEOUT_SECONDS, output_type=Output.DICT,
            )
            words: list[str] = []
            confidences: list[float] = []
            for raw_text, raw_conf in zip(data.get("text", []), data.get("conf", [])):
                word = str(raw_text or "").strip()
                try:
                    confidence = float(raw_conf)
                except (TypeError, ValueError):
                    confidence = -1.0
                if word and confidence >= 0:
                    words.append(word)
                    confidences.append(confidence)
            text = " ".join(words).strip()
            candidates.append({
                "text": text,
                "confidence": sum(confidences) / len(confidences) if confidences else 0.0,
                "samples": len(confidences),
                "profile": profile,
                "meaningful": _has_meaningful_text(text),
            })
        best = max(
            (item for item in candidates if item["meaningful"]),
            key=lambda item: (item["confidence"], item["samples"], len(item["text"])),
            default={},
        )
        text = str(best.get("text") or "")
        return OCREngineResult(
            text=text,
            confidence=float(best.get("confidence") or 0.0),
            confidence_samples=int(best.get("samples") or 0),
            engine=engine,
            backend="tesseract-cli",
            model=lang,
            preprocessing=str(best.get("profile") or ""),
            failure_reason="" if text else "no_meaningful_text",
        )
    except Exception as exc:  # noqa: BLE001
        return OCREngineResult(
            engine="tesseract", backend="tesseract-cli",
            failure_reason=f"tesseract_failed: {type(exc).__name__}: {exc}",
        )


def _ocr_image_object(image, *, file_type: str, page: str = "") -> ExtractionResult:
    from aios_habit.ocr_engines import run_ocr_router

    lang = _ocr_lang()
    result, attempts = run_ocr_router(
        image,
        meaningful=_has_meaningful_text,
        minimum_confidence=OCR_MIN_USABLE_CONFIDENCE,
        tesseract_fallback=_run_tesseract_engine,
    )
    common = {
        "page": page,
        "ocr_engine": result.engine,
        "ocr_lang": lang,
        "ocr_confidence": round(result.confidence, 2),
        "ocr_confidence_samples": result.confidence_samples,
        "ocr_preprocessing": result.preprocessing or result.backend,
        "ocr_attempts": attempts,
    }
    text = result.text.strip()
    if not _has_meaningful_text(text):
        unavailable = attempts == 0
        return ExtractionResult(
            "", file_type, "local_ocr",
            "unsupported_no_local_ocr" if unavailable else "failed_with_reason",
            result.warning or result.failure_reason or "OCR ran but returned no meaningful text",
            ocr_quality_reason="ocr_engine_unavailable" if unavailable else "no_meaningful_text",
            **common,
        )
    if result.confidence < OCR_MIN_USABLE_CONFIDENCE:
        return ExtractionResult(
            "", file_type, "local_ocr", "failed_with_reason",
            f"OCR confidence {result.confidence:.2f} is below usable threshold {OCR_MIN_USABLE_CONFIDENCE:.2f}",
            ocr_quality_reason="confidence_below_usable_threshold", **common,
        )
    status = "ocr_success" if result.confidence >= OCR_SUCCESS_CONFIDENCE else "ocr_partial"
    warnings = [item for item in [result.warning, "OCR confidence is moderate; review important claims" if status == "ocr_partial" else ""] if item]
    return ExtractionResult(
        text, file_type, "local_ocr", status, warning="; ".join(warnings),
        section=f"page {page} OCR" if page else "ocr text",
        ocr_quality_reason="passed_quality_gate", **common,
    )


def _ocr_image(path: Path, *, page: str = "") -> ExtractionResult:
    if path.stat().st_size > MAX_OCR_IMAGE_BYTES:
        return ExtractionResult(
            "", path.suffix.lower(), "local_ocr", "unsupported_no_local_ocr",
            f"image exceeds OCR size guard: {MAX_OCR_IMAGE_BYTES} bytes", page=page,
            ocr_engine="none", ocr_lang=_ocr_lang(), ocr_quality_reason="image_size_guard",
        )
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.load()
            return _ocr_image_object(image, file_type=path.suffix.lower(), page=page)
    except Exception as exc:  # noqa: BLE001
        return ExtractionResult(
            "", path.suffix.lower(), "local_ocr", "failed_with_reason",
            f"image read failed: {exc}", page=page, ocr_engine="none", ocr_lang=_ocr_lang(),
            ocr_quality_reason="image_decode_failed",
        )


def _deep_pdf_result(path: Path, routes: list[PDFPageRoute]) -> ExtractionResult | None:
    from aios_habit.ocr_engines import ocr_mode

    mode = ocr_mode()
    should_run = mode in {"deep", "offline_max"} or (
        mode == "auto_deep" and any(route.has_table or route.has_columns for route in routes)
    )
    if not should_run:
        return None

    from aios_habit.deep_document_parsers import run_deep_parser

    parsed = run_deep_parser(path, mode)
    if not parsed.succeeded:
        return ExtractionResult(
            "", ".pdf", parsed.parser, "failed_with_reason",
            parsed.failure_reason or parsed.warning or "deep parser returned no usable text",
            ocr_engine=parsed.parser, ocr_lang=_ocr_lang(),
            ocr_quality_reason="deep_parser_failed", element_type="pdf_deep_document",
        )
    return ExtractionResult(
        parsed.text, ".pdf", parsed.parser, "extracted_success",
        warning=parsed.warning, section="deep document parse",
        ocr_engine=parsed.parser, ocr_lang=_ocr_lang(),
        ocr_quality_reason="deep_parser_passed", element_type="pdf_deep_document",
    )


def _extract_pdf(path: Path) -> list[ExtractionResult]:
    try:
        routes = route_pdf_pages(path)
    except Exception as exc:  # noqa: BLE001
        status = "dependency_missing" if isinstance(exc, PDFDependencyMissingError) else "parse_failed"
        return [ExtractionResult(
            "", ".pdf", "pdf_router", status,
            str(exc), element_type="pdf_page_text",
        )]

    deep_result = _deep_pdf_result(path, routes)
    if deep_result is not None and deep_result.text:
        return [deep_result]
    deep_warning = deep_result.warning if deep_result is not None else ""

    try:
        import fitz
    except ImportError:
        fitz = None

    results: list[ExtractionResult] = []
    document = None
    ocr_pages_attempted = 0
    try:
        for route in routes:
            native_text = str(route.text or "").strip()
            if not route.needs_ocr and _has_meaningful_text(native_text):
                results.append(ExtractionResult(
                    native_text, ".pdf", route.extractor, "extracted",
                    warning=route.warning,
                    section=f"page {route.page}", page=str(route.page),
                    element_type="pdf_markdown_page",
                ))
                continue

            if ocr_pages_attempted >= _max_pdf_ocr_pages():
                results.append(ExtractionResult(
                    "", ".pdf", "pdf_image_ocr", "failed_with_reason",
                    f"document exceeds PDF OCR workload guard: {_max_pdf_ocr_pages()} pages",
                    section=f"page {route.page}", page=str(route.page), ocr_engine="none",
                    ocr_lang=_ocr_lang(), ocr_quality_reason="pdf_page_guard",
                    element_type="pdf_page_ocr",
                ))
                continue
            if fitz is None:
                results.append(ExtractionResult(
                    "", ".pdf", "pdf_image_ocr", "dependency_missing",
                    "fitz is required to render PDF pages for OCR",
                    section=f"page {route.page}", page=str(route.page),
                    ocr_engine="none", ocr_lang=_ocr_lang(),
                    ocr_quality_reason="pdf_render_unavailable", element_type="pdf_page_ocr",
                ))
                continue

            if document is None:
                document = fitz.open(str(path))
            page = document[route.page - 1]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            from PIL import Image
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            ocr_pages_attempted += 1
            ocr_result = _ocr_image_object(image, file_type=".pdf", page=str(route.page))
            ocr_result.extractor_name = f"pymupdf_render+{ocr_result.ocr_engine or 'local_ocr'}"
            ocr_result.section = f"page {route.page} OCR"
            ocr_result.element_type = "pdf_page_ocr"
            if (
                not ocr_result.text
                and ocr_result.ocr_quality_reason == "no_meaningful_text"
                and not page.get_images(full=True)
            ):
                ocr_result.extraction_status = "empty_text"
                ocr_result.warning = "pdf page has no native text or raster image"
            results.append(ocr_result)
    except Exception as exc:  # noqa: BLE001
        return [ExtractionResult(
            "", ".pdf", "pdf_router", "parse_failed", f"pdf read failed: {exc}",
            element_type="pdf_page_text",
        )]
    finally:
        if document is not None:
            document.close()

    if deep_warning and results:
        results[0].warning = "; ".join(item for item in [deep_warning, results[0].warning] if item)
    if not results:
        return [ExtractionResult(
            "", ".pdf", "pdf_router", "empty_text", "pdf has no pages",
            element_type="pdf_page_text",
        )]
    return results


def extract_text_chunks_from_file(path: str | Path, *, root: str | Path | None = None, max_chars_per_chunk: int = 1200) -> list[dict[str, Any]]:
    file_path = Path(path)
    root_path = Path(root).resolve() if root else None
    ext = file_path.suffix.lower()
    if ext in {".html", ".htm"}:
        results = [_extract_html(file_path)]
    elif ext == ".pptx":
        results = [_extract_pptx(file_path)]
    elif ext in {".xlsx", ".xlsm", ".xls"}:
        results = _extract_excel(file_path)
    elif ext == ".docx":
        results = [_extract_docx(file_path)]
    elif ext in IMAGE_EXTS:
        results = [_ocr_image(file_path)]
    elif ext == ".pdf":
        results = _extract_pdf(file_path)
    else:
        rel = file_path.relative_to(root_path).as_posix() if root_path else file_path.name
        return [{
            "text": "",
            "source_file": file_path.name,
            "relative_path": rel,
            "file_type": ext or "[no_ext]",
            "section": "",
            "page": "",
            "slide": "",
            "sheet": "",
            "row_range": "",
            "privacy_level": "local_only",
            "extractor_name": "document_extractors",
            "extraction_status": "unsupported_no_local_tool",
            "warning": "unsupported file type",
            "ocr_engine": "",
            "ocr_lang": "",
            "ocr_confidence": None,
            "ocr_confidence_samples": 0,
            "ocr_preprocessing": "",
            "ocr_attempts": 0,
            "ocr_quality_reason": "unsupported_file_type",
            "element_type": "metadata_only",
        }]
    chunks: list[dict[str, Any]] = []
    for result in results:
        result.text = normalize_extracted_text(result.text)
        chunks.extend(_chunk_result(result, file_path, root_path, max_chars_per_chunk))
    return chunks


# Register adapters for capability checks and alternate callers.
def _registry_adapter(path: Path, root: Path | None):
    from aios_habit.extractor_registry import ExtractorElement
    elements = []
    for chunk in extract_text_chunks_from_file(path, root=root):
        elements.append(ExtractorElement(
            source_path=str(path),
            relative_path=chunk.get("relative_path", path.name),
            element_type=chunk.get("element_type", "text") or "text",
            text=chunk.get("text", ""),
            metadata={k: v for k, v in chunk.items() if k not in {"text"}},
            extraction_status=chunk.get("extraction_status", "metadata_only"),
            extractor_name=chunk.get("extractor_name", "document_extractors"),
            confidence=(
                f"{float(chunk['ocr_confidence']):.2f}"
                if chunk.get("ocr_confidence") is not None
                else ("medium" if chunk.get("text") else "none")
            ),
            page=chunk.get("page", ""),
            sheet=chunk.get("sheet", ""),
            slide=chunk.get("slide", ""),
        ))
    return elements

try:
    from aios_habit.extractor_registry import register_adapter
    for _ext in [".pdf", ".pptx", ".docx", ".html", ".htm", ".xlsx", ".xlsm", ".xls", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"]:
        register_adapter(_ext, "document_extractors", _registry_adapter)
except Exception:
    pass


def is_potentially_extractable(ext: str) -> bool:
    return ext.lower() in {".html", ".htm", ".pptx", ".pdf", ".xlsx", ".xlsm", ".xls", ".docx"} | IMAGE_EXTS


def local_capabilities() -> dict[str, Any]:
    import importlib.util
    from aios_habit.ocr_engines import ocr_capabilities

    engine_caps = ocr_capabilities()
    tesseract_available, _, tesseract_detail = _tesseract_available()
    availability = dict(engine_caps["ocr_engine_availability"])
    availability["tesseract"] = tesseract_available
    selected = next((name for name in engine_caps["ocr_engine_order"] if availability.get(name)), "none")
    ocr_available = selected != "none"
    return {
        "ocr_available": ocr_available,
        "ocr_engine": selected,
        "tesseract_cmd": tesseract_detail if tesseract_available else "",
        "ocr_lang": _ocr_lang(),
        "ocr_warning": "" if ocr_available else "no configured local OCR engine is available",
        "ocr_mode": engine_caps["ocr_mode"],
        "ocr_engine_order": engine_caps["ocr_engine_order"],
        "ocr_engine_availability": availability,
        "ocr_cpu_threads": engine_caps["ocr_cpu_threads"],
        "pdf_inspector_available": importlib.util.find_spec("pdf_inspector") is not None,
        "pdf_render_available": importlib.util.find_spec("fitz") is not None,
        "docling_available": importlib.util.find_spec("docling") is not None,
        "marker_available": shutil.which("marker_single") is not None,
        "image_size_guard_bytes": MAX_OCR_IMAGE_BYTES,
        "pdf_ocr_page_guard": _max_pdf_ocr_pages(),
        "ocr_min_usable_confidence": OCR_MIN_USABLE_CONFIDENCE,
        "ocr_success_confidence": OCR_SUCCESS_CONFIDENCE,
        "ocr_preprocessing_profiles": ["rapidocr_original", "paddleocr_original", "tesseract_legacy_profiles"],
        "cloud_ocr_used": False,
    }
