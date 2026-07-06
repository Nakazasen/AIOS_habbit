"""
Generic adapter interface for RAG v2 converters.
"""
from dataclasses import dataclass, field
from typing import Protocol, List, Dict, Any, Optional, Tuple
import datetime

from .schema import DocumentElement, ExtractionStatus, ElementType

@dataclass
class AdapterCapabilities:
    adapter_name: str
    supported_file_types: List[str] = field(default_factory=list)
    supports_tables: bool = False
    supports_layout: bool = False
    supports_ocr: bool = False
    supports_images: bool = False
    supports_metadata: bool = False
    requires_external_dependency: bool = False
    dependency_status: str = "ok"
    privacy_notes: str = ""

@dataclass
class ConversionContext:
    source_id: str = ""
    document_id: str = ""
    privacy_labels: Tuple[str, ...] = field(default_factory=tuple)
    owner_consent: bool = False
    cloud_allowed: bool = False
    source_fingerprint: str = ""
    indexing_timestamp: Optional[str] = None
    extraction_options: Dict[str, Any] = field(default_factory=dict)
    language_hints: List[str] = field(default_factory=list)
    fail_soft: bool = True

class DocumentConverterAdapter(Protocol):
    def supports(self, path: str, file_type: Optional[str] = None, mime: Optional[str] = None) -> bool:
        ...

    def convert(self, path: str, context: ConversionContext) -> List[DocumentElement]:
        ...

    def capabilities(self) -> AdapterCapabilities:
        ...

class BaseDocumentConverterAdapter:
    """Optional base class for common adapter patterns."""

    def _create_failed_element(self, path: str, error_msg: str, context: ConversionContext, extractor_name: str) -> DocumentElement:
        import hashlib
        path_hash = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]
        return DocumentElement(
            element_id=f"failed_{path_hash}",
            document_id=context.document_id,
            source_path=path,
            source_name=path.split("/")[-1] if "/" in path else path.split("\\")[-1],
            file_type="unknown",
            extractor=extractor_name,
            extraction_status=ExtractionStatus.FAILED,
            element_type=ElementType.UNKNOWN,
            extraction_warning=error_msg,
            privacy_labels=context.privacy_labels,
            source_fingerprint=context.source_fingerprint,
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
