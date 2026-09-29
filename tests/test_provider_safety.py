import pytest
from aios_habit.provider_safety import check_privacy_gate, PrivacyGateResult
from aios_habit.ai_provider_bridge import ProviderConfig
from aios_habit.rag_evidence import RAGEvidencePack, RAGEvidenceItem

def test_cloud_provider_allowed_when_evidence_is_local_only():
    """2026-09-29 owner decision: local_only evidence no longer blocks cloud providers."""
    pack = RAGEvidencePack(
        pack_id="pack1",
        query="query",
        items=[
            RAGEvidenceItem(
                evidence_id="e1", chunk_id="c1", document_id="d1", citation_id="cit1",
                citation_label="L", source_title="T", relative_path="path", file_type="txt",
                privacy_mode="local_only", text="text", snippet="snip", score=0.9, rank=1
            )
        ]
    )
    config = ProviderConfig(enabled=True, locality="cloud")
    
    result = check_privacy_gate(pack, config)
    assert result.provider_call_allowed is True
    assert result.block_reason == ""

def test_provider_not_configured_returns_safe_error():
    pack = RAGEvidencePack(pack_id="pack1", query="query", items=[])
    config = ProviderConfig(enabled=False)
    
    result = check_privacy_gate(pack, config)
    assert result.provider_call_allowed is False
    assert result.block_reason == "provider_not_configured"

def test_metadata_only_evidence_does_not_block_provider_call():
    """2026-09-29 owner decision: metadata-only evidence no longer triggers the confidential block."""
    pack = RAGEvidencePack(
        pack_id="pack1",
        query="query",
        items=[
            RAGEvidenceItem(
                evidence_id="e1", chunk_id="c1", document_id="d1", citation_id="cit1",
                citation_label="L", source_title="T", relative_path="path", file_type="txt",
                privacy_mode="cloud_safe", text="text", snippet="snip", score=0.9, rank=1,
                metadata={"_is_metadata_only": "True"}
            )
        ]
    )
    config = ProviderConfig(enabled=True, locality="cloud")
    
    result = check_privacy_gate(pack, config)
    assert result.provider_call_allowed is True
    assert result.block_reason == ""
