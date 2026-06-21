from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

MAX_CHUNKS_PER_FILE = 30


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
        return " ".join(_clean_lines("".join(self._parts).splitlines()))


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


def _chunk_result(result: ExtractionResult, path: Path, root: Path | None, max_chars_per_chunk: int) -> list[dict[str, Any]]:
    text = result.text.strip()
    rel = path.relative_to(root).as_posix() if root else path.name
    if result.extraction_status != "success" or not text:
        return [{
            "text": "",
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
        }]
    chunks: list[dict[str, Any]] = []
    for idx, start in enumerate(range(0, len(text), max_chars_per_chunk)):
        if idx >= MAX_CHUNKS_PER_FILE:
            break
        part = text[start:start + max_chars_per_chunk]
        section = result.section or f"chars {start}-{start + len(part)}"
        chunks.append({
            "text": part,
            "source_file": path.name,
            "relative_path": rel,
            "file_type": result.file_type,
            "section": section,
            "page": result.page,
            "slide": result.slide,
            "sheet": result.sheet,
            "row_range": result.row_range,
            "privacy_level": "local_only",
            "extractor_name": result.extractor_name,
            "extraction_status": result.extraction_status,
            "warning": result.warning,
        })
    return chunks


def _extract_html(path: Path) -> ExtractionResult:
    parser = _ReadableHTMLParser()
    parser.feed(path.read_text(encoding="utf-8-sig", errors="ignore"))
    parser.close()
    text = parser.text()
    if not text:
        return ExtractionResult("", path.suffix.lower(), "html_parser", "failed", "html has no visible text")
    return ExtractionResult(text, path.suffix.lower(), "html_parser", "success", section="visible text")


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
        return ExtractionResult("", ".pptx", "pptx_zip_xml", "failed", "invalid pptx zip container")
    sections: list[str] = []
    if slide_lines:
        sections.append("Slide text:\n" + "\n".join(slide_lines[:120]))
    if note_lines:
        sections.append("Speaker notes:\n" + "\n".join(note_lines[:60]))
    if media_count:
        sections.append(f"Embedded media/images: {media_count}")
    if not sections:
        return ExtractionResult("", ".pptx", "pptx_zip_xml", "unsupported", "pptx has no extractable text payload")
    return ExtractionResult("\n\n".join(sections), ".pptx", "pptx_zip_xml", "success", section="slides/notes")


def _extract_excel(path: Path) -> list[ExtractionResult]:
    try:
        import openpyxl
    except Exception as exc:  # noqa: BLE001
        return [ExtractionResult("", path.suffix.lower(), "openpyxl", "unsupported", f"openpyxl unavailable: {exc}")]
    try:
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True, keep_vba=False)
    except Exception as exc:  # noqa: BLE001
        return [ExtractionResult("", path.suffix.lower(), "openpyxl", "failed", f"excel read failed: {exc}")]
    results: list[ExtractionResult] = []
    try:
        for sheet_name in workbook.sheetnames[:12]:
            sheet = workbook[sheet_name]
            lines: list[str] = [f"Excel sheet: {sheet_name}"]
            row_count = 0
            for row in sheet.iter_rows(max_row=25, values_only=True):
                values = [str(cell) for cell in row if cell is not None and str(cell).strip()]
                if values:
                    row_count += 1
                    lines.append(" | ".join(values))
            if row_count:
                results.append(ExtractionResult("\n".join(lines), path.suffix.lower(), "openpyxl", "success", section=f"sheet {sheet_name} preview", sheet=sheet_name, row_range=f"1-{row_count}"))
    finally:
        workbook.close()
    if not results:
        return [ExtractionResult("", path.suffix.lower(), "openpyxl", "unsupported", "excel workbook has no readable values")]
    return results


def _extract_pdf(path: Path) -> list[ExtractionResult]:
    reader_cls = None
    backend = ""
    try:
        from pypdf import PdfReader  # type: ignore
        reader_cls = PdfReader
        backend = "pypdf"
    except Exception:
        try:
            from PyPDF2 import PdfReader  # type: ignore
            reader_cls = PdfReader
            backend = "PyPDF2"
        except Exception as exc:  # noqa: BLE001
            return [ExtractionResult("", ".pdf", "pdf_optional", "unsupported", f"pdf text dependency unavailable: {exc}")]
    try:
        reader = reader_cls(str(path))
        results: list[ExtractionResult] = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            lines = _clean_lines(page_text.splitlines(), limit=120)
            if lines:
                results.append(ExtractionResult("\n".join(lines), ".pdf", backend, "success", section=f"page {index}", page=str(index)))
        if not results:
            return [ExtractionResult("", ".pdf", backend, "unsupported", "pdf has no extractable text layer")]
        return results
    except Exception as exc:  # noqa: BLE001
        return [ExtractionResult("", ".pdf", backend or "pdf_optional", "failed", f"pdf read failed: {exc}")]


def extract_text_chunks_from_file(path: str | Path, *, root: str | Path | None = None, max_chars_per_chunk: int = 1200) -> list[dict[str, Any]]:
    file_path = Path(path)
    root_path = Path(root).resolve() if root else None
    ext = file_path.suffix.lower()
    if ext in {".html", ".htm"}:
        results = [_extract_html(file_path)]
    elif ext == ".pptx":
        results = [_extract_pptx(file_path)]
    elif ext in {".xlsx", ".xlsm"}:
        results = _extract_excel(file_path)
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
            "extraction_status": "unsupported",
            "warning": "unsupported file type",
        }]
    chunks: list[dict[str, Any]] = []
    for result in results:
        chunks.extend(_chunk_result(result, file_path, root_path, max_chars_per_chunk))
    return chunks


def is_potentially_extractable(ext: str) -> bool:
    return ext.lower() in {".html", ".htm", ".pptx", ".pdf", ".xlsx", ".xlsm"}
