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

    # 2026-09-29: chu so huu go han che local_only/confidential (DATA_POLICY.md).
    # Cong khong con chan provider ngoai; nhan chi con y nghia phan loai noi bo.
    return PrivacyGateResult(True, "")
