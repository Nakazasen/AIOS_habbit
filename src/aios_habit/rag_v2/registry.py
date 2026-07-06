"""
Registry for RAG v2 Document Converter Adapters.
"""
import os
from typing import List, Optional, Dict, Type

from .schema import DocumentElement, ExtractionStatus, ElementType
from .adapters import DocumentConverterAdapter, ConversionContext, BaseDocumentConverterAdapter
from .converters import (
    TextDocumentConverterAdapter,
    HTMLDocumentConverterAdapter,
    PDFDocumentConverterAdapter,
    ExcelDocumentConverterAdapter,
    WordDocumentConverterAdapter,
    PowerPointDocumentConverterAdapter
)

class ConverterRegistry:
    def __init__(self) -> None:
        self._adapters: List[DocumentConverterAdapter] = [
            TextDocumentConverterAdapter(),
            HTMLDocumentConverterAdapter(),
            PDFDocumentConverterAdapter(),
            ExcelDocumentConverterAdapter(),
            WordDocumentConverterAdapter(),
            PowerPointDocumentConverterAdapter()
        ]

    def register(self, adapter: DocumentConverterAdapter) -> None:
        self._adapters.append(adapter)

    def get_adapter_for_file(self, path: str, file_type: Optional[str] = None, mime: Optional[str] = None) -> Optional[DocumentConverterAdapter]:
        for adapter in self._adapters:
            if adapter.supports(path, file_type, mime):
                return adapter
        return None

    def convert_document(self, path: str, context: ConversionContext) -> List[DocumentElement]:
        adapter = self.get_adapter_for_file(path)
        if adapter:
            return adapter.convert(path, context)
        
        # Unknown/Unsupported extension fallback
        if context.fail_soft:
            fallback = BaseDocumentConverterAdapter()
            return [fallback._create_failed_element(path, f"No supported adapter found for file: {path}", context, "ConverterRegistry")]
        
        raise ValueError(f"No supported adapter found for file: {path}")

    def list_capabilities(self) -> List[dict]:
        return [
            {
                "adapter_name": a.capabilities().adapter_name,
                "supported_file_types": a.capabilities().supported_file_types,
                "supports_tables": a.capabilities().supports_tables,
                "supports_layout": a.capabilities().supports_layout,
                "supports_ocr": a.capabilities().supports_ocr,
                "supports_images": a.capabilities().supports_images,
                "supports_metadata": a.capabilities().supports_metadata,
                "requires_external_dependency": a.capabilities().requires_external_dependency,
                "dependency_status": a.capabilities().dependency_status,
                "privacy_notes": a.capabilities().privacy_notes,
            }
            for a in self._adapters
        ]
