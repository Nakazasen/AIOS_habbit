"""RAG v2 core generic package."""

from .schema import DocumentElement, ElementType, ExtractionStatus, TableCell, TableData
from .adapters import DocumentConverterAdapter, ConversionContext, AdapterCapabilities, BaseDocumentConverterAdapter
from .converters import (
    TextDocumentConverterAdapter,
    HTMLDocumentConverterAdapter,
    PDFDocumentConverterAdapter,
    ExcelDocumentConverterAdapter,
    WordDocumentConverterAdapter,
    PowerPointDocumentConverterAdapter
)
from .registry import ConverterRegistry

__all__ = [
    "DocumentElement",
    "ElementType",
    "ExtractionStatus",
    "TableCell",
    "TableData",
    "DocumentConverterAdapter",
    "ConversionContext",
    "AdapterCapabilities",
    "BaseDocumentConverterAdapter",
    "TextDocumentConverterAdapter",
    "HTMLDocumentConverterAdapter",
    "PDFDocumentConverterAdapter",
    "ExcelDocumentConverterAdapter",
    "WordDocumentConverterAdapter",
    "PowerPointDocumentConverterAdapter",
    "ConverterRegistry",
]
