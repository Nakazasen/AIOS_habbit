from dataclasses import dataclass
from typing import Optional
from aios_habit.rag_evidence import RAGEvidencePack
from aios_habit.ai_provider_bridge import ProviderConfig

@dataclass
class PrivacyGateResult:
    provider_call_allowed: bool
    block_reason: str

def check_privacy_gate(evidence_pack: RAGEvidencePack, provider_config: Optional[ProviderConfig]) -> PrivacyGateResult:
    if not provider_config or not provider_config.enabled:
        return PrivacyGateResult(False, "provider_not_configured")

    if not evidence_pack.items:
        return PrivacyGateResult(False, "no_content_evidence")

    # If any item is strictly local_only or confidential, it triggers the block for non-local models
    is_confidential = any(
        item.privacy_mode == "local_only" or 
        item.metadata.get("_is_metadata_only") == "True"
        for item in evidence_pack.items
    )
    
    if is_confidential:
        if provider_config.locality == "local":
            return PrivacyGateResult(True, "")
        else:
            return PrivacyGateResult(False, "local_only_evidence" if any(i.privacy_mode == "local_only" for i in evidence_pack.items) else "confidential_evidence")

    return PrivacyGateResult(True, "")
