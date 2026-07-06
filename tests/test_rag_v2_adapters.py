import pytest
from typing import List, Optional
from aios_habit.rag_v2.schema import DocumentElement, ExtractionStatus
from aios_habit.rag_v2.adapters import (
    DocumentConverterAdapter,
    BaseDocumentConverterAdapter,
    ConversionContext,
    AdapterCapabilities
)

class DummyAdapter(BaseDocumentConverterAdapter):
    def supports(self, path: str, file_type: Optional[str] = None, mime: Optional[str] = None) -> bool:
        return path.endswith(".dummy")

    def convert(self, path: str, context: ConversionContext) -> List[DocumentElement]:
        if not self.supports(path):
            if context.fail_soft:
                return [self._create_failed_element(path, "Unsupported file", context, "DummyAdapter")]
            raise ValueError("Unsupported file")

        # Mock success
        from aios_habit.rag_v2.schema import ElementType
        import datetime
        return [
            DocumentElement(
                element_id="dummy-1",
                document_id=context.document_id,
                source_path=path,
                source_name="test.dummy",
                file_type="dummy",
                extractor="DummyAdapter",
                extraction_status=ExtractionStatus.SUCCESS,
                element_type=ElementType.TEXT,
                text="Dummy content",
                privacy_labels=context.privacy_labels,
                source_fingerprint=context.source_fingerprint,
                created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
            )
        ]

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            adapter_name="DummyAdapter",
            supported_file_types=[".dummy"],
            supports_metadata=True
        )

def test_adapter_protocol():
    adapter: DocumentConverterAdapter = DummyAdapter()

    caps = adapter.capabilities()
    assert caps.adapter_name == "DummyAdapter"
    assert ".dummy" in caps.supported_file_types

    assert adapter.supports("test.dummy") is True
    assert adapter.supports("test.txt") is False

def test_adapter_convert_success():
    adapter = DummyAdapter()
    ctx = ConversionContext(
        document_id="doc-1",
        privacy_labels=("secret",),
        fail_soft=True
    )

    elements = adapter.convert("file.dummy", ctx)
    assert len(elements) == 1
    assert elements[0].text == "Dummy content"
    assert elements[0].privacy_labels == ("secret",)

def test_adapter_fail_soft_behavior():
    adapter = DummyAdapter()
    ctx = ConversionContext(
        document_id="doc-2",
        fail_soft=True
    )

    elements = adapter.convert("file.unsupported", ctx)
    assert len(elements) == 1
    assert elements[0].extraction_status == ExtractionStatus.FAILED
    assert "Unsupported file" in elements[0].extraction_warning
