"""
Generic converter adapters for RAG v2.
"""
import os
import hashlib
import datetime
import zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import List, Optional, Dict, Any, Tuple

from .schema import DocumentElement, ExtractionStatus, ElementType, TableData, TableCell
from .adapters import DocumentConverterAdapter, BaseDocumentConverterAdapter, ConversionContext, AdapterCapabilities


_OCR_USABLE_STATUSES = {"ocr_success", "ocr_partial"}


def _ocr_status(status: str) -> ExtractionStatus:
    if status == "ocr_success":
        return ExtractionStatus.SUCCESS
    if status == "ocr_partial":
        return ExtractionStatus.PARTIAL
    return ExtractionStatus.FAILED


def _ocr_element(
    *,
    path: str,
    context: ConversionContext,
    path_hash: str,
    index: int,
    text: str,
    status: str,
    warning: str,
    extractor: str,
    file_type: str,
    confidence: Optional[float] = None,
    page: Optional[int] = None,
) -> DocumentElement:
    usable = status in _OCR_USABLE_STATUSES and bool(text.strip())
    detail = warning.strip()
    if not usable and not detail:
        detail = f"OCR unusable: status={status or 'unknown'}"
    return DocumentElement(
        element_id=f"{context.document_id or f'doc_{path_hash}'}_ocr_{path_hash}_{index}",
        document_id=context.document_id or f"doc_{path_hash}",
        source_path=path,
        source_name=os.path.basename(path),
        file_type=file_type.lstrip("."),
        extractor=extractor,
        extraction_status=_ocr_status(status) if usable else ExtractionStatus.FAILED,
        element_type=ElementType.TEXT if usable else ElementType.IMAGE,
        extraction_warning=detail or None,
        text=text.strip() if usable else None,
        page=page,
        confidence=(float(confidence) / 100.0 if confidence is not None else None),
        language_hint=(context.language_hints[0] if context.language_hints else None),
        privacy_labels=context.privacy_labels,
        source_fingerprint=context.source_fingerprint,
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )

class TextDocumentConverterAdapter(BaseDocumentConverterAdapter):
    def supports(self, path: str, file_type: Optional[str] = None, mime: Optional[str] = None) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in {".txt", ".md", ".csv"}

    def convert(self, path: str, context: ConversionContext) -> List[DocumentElement]:
        if not self.supports(path):
            if context.fail_soft:
                return [self._create_failed_element(path, f"Unsupported file: {path}", context, "TextDocumentConverterAdapter")]
            raise ValueError(f"Unsupported file: {path}")

        if not os.path.exists(path):
            if context.fail_soft:
                return [self._create_failed_element(path, f"File not found: {path}", context, "TextDocumentConverterAdapter")]
            raise FileNotFoundError(f"File not found: {path}")

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            if context.fail_soft:
                return [self._create_failed_element(path, f"Read failed: {e}", context, "TextDocumentConverterAdapter")]
            raise e

        # Element-first: split by paragraphs
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [content.strip()] if content.strip() else [""]

        elements = []
        path_hash = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
        doc_id = context.document_id or f"doc_{path_hash}"

        for idx, para in enumerate(paragraphs):
            element_id = f"{doc_id}_txt_{path_hash}_{idx}"
            is_heading = para.startswith("#")
            elem_type = ElementType.HEADING if is_heading else ElementType.TEXT
            
            elements.append(DocumentElement(
                element_id=element_id,
                document_id=doc_id,
                source_path=path,
                source_name=os.path.basename(path),
                file_type=os.path.splitext(path)[1].lower()[1:],
                extractor="TextDocumentConverterAdapter",
                extraction_status=ExtractionStatus.SUCCESS,
                element_type=elem_type,
                text=para,
                privacy_labels=context.privacy_labels,
                source_fingerprint=context.source_fingerprint,
                created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
            ))
        return elements

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            adapter_name="TextDocumentConverterAdapter",
            supported_file_types=[".txt", ".md", ".csv"],
            supports_metadata=True
        )


class HTMLReadableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self.skip_depth += 1
        if tag.lower() in {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth and data.strip():
            self.parts.append(data)

    def get_text(self) -> str:
        return "".join(self.parts)


class HTMLDocumentConverterAdapter(BaseDocumentConverterAdapter):
    def supports(self, path: str, file_type: Optional[str] = None, mime: Optional[str] = None) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in {".html", ".htm"}

    def convert(self, path: str, context: ConversionContext) -> List[DocumentElement]:
        if not self.supports(path):
            if context.fail_soft:
                return [self._create_failed_element(path, f"Unsupported file: {path}", context, "HTMLDocumentConverterAdapter")]
            raise ValueError(f"Unsupported file: {path}")

        if not os.path.exists(path):
            if context.fail_soft:
                return [self._create_failed_element(path, f"File not found: {path}", context, "HTMLDocumentConverterAdapter")]
            raise FileNotFoundError(f"File not found: {path}")

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                html_content = f.read()
        except Exception as e:
            if context.fail_soft:
                return [self._create_failed_element(path, f"Read failed: {e}", context, "HTMLDocumentConverterAdapter")]
            raise e

        parser = HTMLReadableParser()
        try:
            parser.feed(html_content)
            parser.close()
            text = parser.get_text()
        except Exception as e:
            if context.fail_soft:
                return [self._create_failed_element(path, f"HTML parsing failed: {e}", context, "HTMLDocumentConverterAdapter")]
            raise e

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [""]

        elements = []
        path_hash = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
        doc_id = context.document_id or f"doc_{path_hash}"

        for idx, para in enumerate(paragraphs):
            element_id = f"{doc_id}_html_{path_hash}_{idx}"
            elements.append(DocumentElement(
                element_id=element_id,
                document_id=doc_id,
                source_path=path,
                source_name=os.path.basename(path),
                file_type=os.path.splitext(path)[1].lower()[1:],
                extractor="HTMLDocumentConverterAdapter",
                extraction_status=ExtractionStatus.SUCCESS,
                element_type=ElementType.TEXT,
                text=para,
                privacy_labels=context.privacy_labels,
                source_fingerprint=context.source_fingerprint,
                created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
            ))
        return elements

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            adapter_name="HTMLDocumentConverterAdapter",
            supported_file_types=[".html", ".htm"],
            supports_metadata=True
        )


class ImageOCRDocumentConverterAdapter(BaseDocumentConverterAdapter):
    def supports(self, path: str, file_type: Optional[str] = None, mime: Optional[str] = None) -> bool:
        return os.path.splitext(path)[1].lower() in {
            ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"
        }

    def convert(self, path: str, context: ConversionContext) -> List[DocumentElement]:
        if not self.supports(path):
            if context.fail_soft:
                return [self._create_failed_element(
                    path, f"Unsupported image: {path}", context,
                    "ImageOCRDocumentConverterAdapter",
                )]
            raise ValueError(f"Unsupported image: {path}")
        if not os.path.exists(path):
            if context.fail_soft:
                return [self._create_failed_element(
                    path, f"File not found: {path}", context,
                    "ImageOCRDocumentConverterAdapter",
                )]
            raise FileNotFoundError(f"File not found: {path}")

        from aios_habit.document_extractors import extract_text_chunks_from_file

        path_hash = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
        try:
            chunks = extract_text_chunks_from_file(path)
        except Exception as exc:
            if context.fail_soft:
                return [self._create_failed_element(
                    path, f"Image OCR failed: {exc}", context,
                    "ImageOCRDocumentConverterAdapter",
                )]
            raise
        return [
            _ocr_element(
                path=path,
                context=context,
                path_hash=path_hash,
                index=index,
                text=str(chunk.get("text") or ""),
                status=str(chunk.get("extraction_status") or "failed_with_reason"),
                warning=str(chunk.get("warning") or ""),
                extractor=str(chunk.get("extractor_name") or "local_ocr"),
                file_type=str(chunk.get("file_type") or os.path.splitext(path)[1]),
                confidence=chunk.get("ocr_confidence"),
            )
            for index, chunk in enumerate(chunks)
        ]

    def capabilities(self) -> AdapterCapabilities:
        from aios_habit.document_extractors import local_capabilities

        capability = local_capabilities()
        return AdapterCapabilities(
            adapter_name="ImageOCRDocumentConverterAdapter",
            supported_file_types=[".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"],
            supports_ocr=True,
            supports_images=True,
            supports_metadata=True,
            requires_external_dependency=True,
            dependency_status="ok" if capability["ocr_available"] else "missing",
            privacy_notes="Local OCR only; cloud OCR is not used.",
        )


class PDFDocumentConverterAdapter(BaseDocumentConverterAdapter):
    def supports(self, path: str, file_type: Optional[str] = None, mime: Optional[str] = None) -> bool:
        return os.path.splitext(path)[1].lower() == ".pdf"

    def convert(self, path: str, context: ConversionContext) -> List[DocumentElement]:
        adapter_name = "PDFDocumentConverterAdapter"
        if not self.supports(path):
            if context.fail_soft:
                return [self._create_failed_element(path, f"Unsupported file: {path}", context, adapter_name)]
            raise ValueError(f"Unsupported file: {path}")
        if not os.path.exists(path):
            if context.fail_soft:
                return [self._create_failed_element(path, f"File not found: {path}", context, adapter_name)]
            raise FileNotFoundError(f"File not found: {path}")

        from pathlib import Path
        from aios_habit.document_extractors import _extract_pdf

        path_hash = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
        doc_id = context.document_id or f"doc_{path_hash}"
        try:
            extracted = _extract_pdf(Path(path))
        except Exception as exc:
            if context.fail_soft:
                return [self._create_failed_element(path, f"PDF read failed: {exc}", context, adapter_name)]
            raise

        elements: List[DocumentElement] = []
        for index, result in enumerate(extracted):
            raw_page = getattr(result, "page", "")
            page = int(raw_page) if str(raw_page).isdigit() else None
            if str(result.extraction_status).startswith("ocr_") or result.element_type == "pdf_page_ocr":
                elements.append(_ocr_element(
                    path=path,
                    context=context,
                    path_hash=path_hash,
                    index=index,
                    text=str(result.text or ""),
                    status=str(result.extraction_status or "failed_with_reason"),
                    warning=str(result.warning or ""),
                    extractor=f"{adapter_name}+local_ocr",
                    file_type="pdf",
                    confidence=result.ocr_confidence,
                    page=page,
                ))
                continue

            text = str(result.text or "").strip()
            usable = result.extraction_status in {"extracted", "extracted_success", "success"} and bool(text)
            elements.append(DocumentElement(
                element_id=f"{doc_id}_pdf_{path_hash}_p{page or 0}_{index}",
                document_id=doc_id,
                source_path=path,
                source_name=os.path.basename(path),
                file_type="pdf",
                extractor=f"{adapter_name}+{result.extractor_name}",
                extraction_status=ExtractionStatus.SUCCESS if usable else ExtractionStatus.FAILED,
                element_type=ElementType.TEXT if usable else ElementType.UNKNOWN,
                extraction_warning=str(result.warning or "") or None,
                text=text if usable else None,
                page=page,
                privacy_labels=context.privacy_labels,
                source_fingerprint=context.source_fingerprint,
                created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ))
        return elements

    def capabilities(self) -> AdapterCapabilities:
        from aios_habit.document_extractors import local_capabilities

        capability = local_capabilities()
        parser_available = bool(capability["pdf_inspector_available"])
        render_available = bool(capability["pdf_render_available"])
        return AdapterCapabilities(
            adapter_name="PDFDocumentConverterAdapter",
            supported_file_types=[".pdf"],
            supports_tables=parser_available,
            supports_layout=parser_available,
            supports_ocr=True,
            supports_images=render_available,
            supports_metadata=True,
            requires_external_dependency=True,
            dependency_status="ok" if (parser_available or render_available) else "missing",
            privacy_notes="Local CPU parsing and OCR only; cloud services are not used.",
        )


class ExcelDocumentConverterAdapter(BaseDocumentConverterAdapter):
    def supports(self, path: str, file_type: Optional[str] = None, mime: Optional[str] = None) -> bool:
        return os.path.splitext(path)[1].lower() in {".xlsx", ".xlsm", ".xls"}

    def convert(self, path: str, context: ConversionContext) -> List[DocumentElement]:
        from aios_habit.excel_extractors import extract_excel

        if not self.supports(path):
            if context.fail_soft:
                return [self._create_failed_element(path, f"Unsupported file: {path}", context, "ExcelDocumentConverterAdapter")]
            raise ValueError(f"Unsupported file: {path}")
        if not os.path.exists(path):
            if context.fail_soft:
                return [self._create_failed_element(path, f"File not found: {path}", context, "ExcelDocumentConverterAdapter")]
            raise FileNotFoundError(path)

        extracted = extract_excel(path, include_images=True, include_charts=True)
        if extracted.dependency_missing or extracted.error:
            detail = extracted.error or f"Missing dependency: {extracted.dependency_missing}"
            if os.path.splitext(path)[1].lower() == ".xls" and extracted.dependency_missing:
                detail += "; convert to .xlsx or install rag-ingestion-xls"
            if context.fail_soft:
                return [self._create_failed_element(path, detail, context, "ExcelDocumentConverterAdapter")]
            raise ValueError(detail)

        path_hash = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
        doc_id = context.document_id or f"doc_{path_hash}"
        file_type = os.path.splitext(path)[1].lower()[1:]
        warning = "; ".join(dict.fromkeys([*extracted.warnings, *extracted.truncated_reasons])) or None
        status = ExtractionStatus.PARTIAL if extracted.partial else ExtractionStatus.SUCCESS
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        elements: List[DocumentElement] = []

        for index, region in enumerate(extracted.regions):
            table = TableData(
                headers=list(region.headers),
                rows=[list(row) for row in region.rows],
                cells=[TableCell(
                    row_index=cell.row - region.row_range[0],
                    column_index=cell.column - region.column_range[0],
                    text=cell.text,
                    is_header=cell.is_header,
                    row_span=cell.row_span,
                    col_span=cell.col_span,
                    coordinate=cell.coordinate,
                    merge_range=cell.merge_range or None,
                ) for cell in region.cells],
                header_rows=[list(row) for row in region.header_rows],
                merged_ranges=list(region.merged_ranges),
                region_id=f"{region.sheet}!{region.cell_range}",
            )
            elements.append(DocumentElement(
                element_id=f"{doc_id}_xls_{path_hash}_region_{index}", document_id=doc_id,
                source_path=path, source_name=os.path.basename(path), file_type=file_type,
                extractor="ExcelDocumentConverterAdapter", extraction_status=status,
                extraction_warning=warning, element_type=ElementType.TABLE, table=table,
                sheet=region.sheet, row_range=region.row_range,
                column_range=region.column_range, cell_range=region.cell_range,
                privacy_labels=context.privacy_labels, source_fingerprint=context.source_fingerprint,
                created_at=now,
            ))

        for chart in extracted.charts:
            elements.append(DocumentElement(
                element_id=f"{doc_id}_xls_{path_hash}_chart_{chart.index}", document_id=doc_id,
                source_path=path, source_name=os.path.basename(path), file_type=file_type,
                extractor="ExcelDocumentConverterAdapter", extraction_status=status,
                extraction_warning=warning, element_type=ElementType.CHART,
                text=chart.as_text(), sheet=chart.sheet,
                section_path=(f"chart {chart.index}", chart.anchor or "unknown anchor"),
                privacy_labels=context.privacy_labels, source_fingerprint=context.source_fingerprint,
                created_at=now,
            ))

        if extracted.images:
            from io import BytesIO
            from PIL import Image
            from aios_habit.document_extractors import _ocr_image_object

            for image_data in extracted.images:
                try:
                    with Image.open(BytesIO(image_data.data)) as image:
                        image.load()
                        ocr = _ocr_image_object(image, file_type=image_data.extension, page=f"{image_data.sheet}!{image_data.anchor}")
                    usable = ocr.extraction_status in _OCR_USABLE_STATUSES and bool(ocr.text.strip())
                    elements.append(DocumentElement(
                        element_id=f"{doc_id}_xls_{path_hash}_image_{image_data.index}", document_id=doc_id,
                        source_path=path, source_name=os.path.basename(path), file_type=file_type,
                        extractor=f"ExcelDocumentConverterAdapter+{ocr.extractor_name}",
                        extraction_status=_ocr_status(ocr.extraction_status) if usable else ExtractionStatus.PARTIAL,
                        extraction_warning="; ".join(item for item in (ocr.warning, warning) if item) or None,
                        element_type=ElementType.TEXT if usable else ElementType.IMAGE,
                        text=ocr.text.strip() if usable else None, sheet=image_data.sheet,
                        confidence=(ocr.ocr_confidence / 100.0 if ocr.ocr_confidence is not None else None),
                        section_path=(f"embedded image {image_data.index}", image_data.anchor or "unknown anchor"),
                        privacy_labels=context.privacy_labels, source_fingerprint=context.source_fingerprint,
                        created_at=now,
                    ))
                except Exception as exc:
                    elements.append(DocumentElement(
                        element_id=f"{doc_id}_xls_{path_hash}_image_{image_data.index}", document_id=doc_id,
                        source_path=path, source_name=os.path.basename(path), file_type=file_type,
                        extractor="ExcelDocumentConverterAdapter", extraction_status=ExtractionStatus.PARTIAL,
                        extraction_warning=f"embedded image OCR failed: {exc}", element_type=ElementType.IMAGE,
                        sheet=image_data.sheet, privacy_labels=context.privacy_labels,
                        source_fingerprint=context.source_fingerprint, created_at=now,
                    ))
        return elements

    def capabilities(self) -> AdapterCapabilities:
        from aios_habit.excel_extractors import legacy_xls_available

        return AdapterCapabilities(
            adapter_name="ExcelDocumentConverterAdapter",
            supported_file_types=[".xlsx", ".xlsm", ".xls"],
            supports_tables=True, supports_ocr=True, supports_images=True,
            supports_metadata=True, requires_external_dependency=True,
            dependency_status="ok; xls=available" if legacy_xls_available() else "ok; xls=optional-missing",
            privacy_notes="Local parsing and OCR only; legacy .xls requires the optional xlrd extra.",
        )


class WordDocumentConverterAdapter(BaseDocumentConverterAdapter):
    def supports(self, path: str, file_type: Optional[str] = None, mime: Optional[str] = None) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext == ".docx"

    def convert(self, path: str, context: ConversionContext) -> List[DocumentElement]:
        if not self.supports(path):
            if context.fail_soft:
                return [self._create_failed_element(path, f"Unsupported file: {path}", context, "WordDocumentConverterAdapter")]
            raise ValueError(f"Unsupported file: {path}")

        if not os.path.exists(path):
            if context.fail_soft:
                return [self._create_failed_element(path, f"File not found: {path}", context, "WordDocumentConverterAdapter")]
            raise FileNotFoundError(f"File not found: {path}")

        elements = []
        path_hash = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
        doc_id = context.document_id or f"doc_{path_hash}"

        try:
            with zipfile.ZipFile(path, "r") as archive:
                if "word/document.xml" not in archive.namelist():
                    if context.fail_soft:
                        return [self._create_failed_element(path, "Missing word/document.xml", context, "WordDocumentConverterAdapter")]
                    raise ValueError("Invalid docx zip container")

                content_xml = archive.read("word/document.xml")
                root = ET.fromstring(content_xml)
                
                paragraphs = []
                for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                    texts = []
                    for t in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                        if t.text:
                            texts.append(t.text)
                    para_text = "".join(texts).strip()
                    if para_text:
                        paragraphs.append(para_text)

                if not paragraphs:
                    paragraphs = [""]

                for idx, para in enumerate(paragraphs):
                    element_id = f"{doc_id}_docx_{path_hash}_{idx}"
                    elements.append(DocumentElement(
                        element_id=element_id,
                        document_id=doc_id,
                        source_path=path,
                        source_name=os.path.basename(path),
                        file_type="docx",
                        extractor="WordDocumentConverterAdapter",
                        extraction_status=ExtractionStatus.SUCCESS,
                        element_type=ElementType.TEXT,
                        text=para,
                        privacy_labels=context.privacy_labels,
                        source_fingerprint=context.source_fingerprint,
                        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
                    ))
        except Exception as e:
            if context.fail_soft:
                return [self._create_failed_element(path, f"Word read failed: {e}", context, "WordDocumentConverterAdapter")]
            raise e

        return elements

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            adapter_name="WordDocumentConverterAdapter",
            supported_file_types=[".docx"],
            supports_metadata=True
        )


class PowerPointDocumentConverterAdapter(BaseDocumentConverterAdapter):
    def supports(self, path: str, file_type: Optional[str] = None, mime: Optional[str] = None) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext == ".pptx"

    def convert(self, path: str, context: ConversionContext) -> List[DocumentElement]:
        if not self.supports(path):
            if context.fail_soft:
                return [self._create_failed_element(path, f"Unsupported file: {path}", context, "PowerPointDocumentConverterAdapter")]
            raise ValueError(f"Unsupported file: {path}")

        if not os.path.exists(path):
            if context.fail_soft:
                return [self._create_failed_element(path, f"File not found: {path}", context, "PowerPointDocumentConverterAdapter")]
            raise FileNotFoundError(f"File not found: {path}")

        elements = []
        path_hash = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
        doc_id = context.document_id or f"doc_{path_hash}"

        try:
            with zipfile.ZipFile(path, "r") as archive:
                slide_names = sorted(
                    [n for n in archive.namelist() if n.lower().startswith("ppt/slides/slide") and n.lower().endswith(".xml")],
                    key=lambda x: int(''.join(c for c in x if c.isdigit()))
                )

                if not slide_names:
                    if context.fail_soft:
                        return [self._create_failed_element(path, "No slide XMLs found", context, "PowerPointDocumentConverterAdapter")]
                    raise ValueError("Invalid pptx container or no slides found")

                for slide_idx, slide_name in enumerate(slide_names, start=1):
                    content_xml = archive.read(slide_name)
                    root = ET.fromstring(content_xml)
                    
                    texts = []
                    for t in root.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t'):
                        if t.text:
                            texts.append(t.text)
                    
                    slide_text = " ".join(texts).strip()
                    paragraphs = [p.strip() for p in slide_text.split("\n\n") if p.strip()]
                    if not paragraphs:
                        paragraphs = [""]

                    for idx, para in enumerate(paragraphs):
                        element_id = f"{doc_id}_pptx_{path_hash}_s{slide_idx}_{idx}"
                        elements.append(DocumentElement(
                            element_id=element_id,
                            document_id=doc_id,
                            source_path=path,
                            source_name=os.path.basename(path),
                            file_type="pptx",
                            extractor="PowerPointDocumentConverterAdapter",
                            extraction_status=ExtractionStatus.SUCCESS,
                            element_type=ElementType.TEXT,
                            text=para,
                            slide=slide_idx,
                            privacy_labels=context.privacy_labels,
                            source_fingerprint=context.source_fingerprint,
                            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
                        ))
        except Exception as e:
            if context.fail_soft:
                return [self._create_failed_element(path, f"PowerPoint read failed: {e}", context, "PowerPointDocumentConverterAdapter")]
            raise e

        return elements

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            adapter_name="PowerPointDocumentConverterAdapter",
            supported_file_types=[".pptx"],
            supports_metadata=True
        )
