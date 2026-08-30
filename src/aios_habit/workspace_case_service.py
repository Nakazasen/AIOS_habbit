"""Use cases for creating a local case from an existing evidence trace."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional
from uuid import uuid4

from aios_habit.evidence_trace import is_insufficient_evidence
from aios_habit.workspace_case_models import CaseEvidenceReference, CaseRecord
from aios_habit.workspace_case_repository import CaseCreationResult, WorkspaceCaseRepository
from aios_habit.workspace_chat_store import load_evidence_trace


class CaseValidationError(ValueError):
    """Validation failure safe to display without a traceback."""


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class WorkspaceCaseService:
    def __init__(self, store: Optional[WorkspaceCaseRepository] = None) -> None:
        self.store = store or WorkspaceCaseRepository()

    def create_case_from_trace_id(
        self,
        trace_id: str,
        *,
        expected_conversation_id: str,
    ) -> CaseCreationResult:
        trace = load_evidence_trace(trace_id)
        if trace is None:
            raise CaseValidationError("Không tìm thấy dấu vết bằng chứng của câu trả lời này.")
        return self.create_case_from_trace(trace, expected_conversation_id=expected_conversation_id)

    def create_case_from_trace(self, trace: Any, *, expected_conversation_id: str) -> CaseCreationResult:
        if not expected_conversation_id or str(getattr(trace, "conversation_id", "")) != expected_conversation_id:
            raise CaseValidationError("Dấu vết bằng chứng không thuộc cuộc trò chuyện đang mở.")
        trace_id = str(getattr(trace, "trace_id", "") or "")
        assistant_message_id = str(getattr(trace, "assistant_message_id", "") or "")
        if not trace_id or not assistant_message_id:
            raise CaseValidationError("Dấu vết bằng chứng chưa đủ định danh để lưu hồ sơ.")
        if any(str(getattr(node, "privacy_label", "") or "") != "local_only" for node in getattr(trace, "nodes", ())):
            raise CaseValidationError("Dấu vết bằng chứng có nhãn dữ liệu không phù hợp để lưu hồ sơ cục bộ.")
        if is_insufficient_evidence(trace):
            raise CaseValidationError("Chưa thể lưu hồ sơ vì câu trả lời chưa có bằng chứng trích dẫn hợp lệ.")

        references = self._references_from_trace(trace)
        if not references:
            raise CaseValidationError("Chưa thể lưu hồ sơ vì không tìm thấy tham chiếu bằng chứng hợp lệ.")
        evidence_digest = _digest(
            {"trace_id": trace_id, "references": sorted(reference.reference_digest for reference in references)}
        )
        case = CaseRecord.new(
            conversation_id=expected_conversation_id,
            assistant_message_id=assistant_message_id,
            trace_id=trace_id,
            evidence_digest=evidence_digest,
        )
        bound_references = [
            CaseEvidenceReference(
                reference_id=reference.reference_id,
                case_id=case.case_id,
                trace_id=reference.trace_id,
                evidence_node_id=reference.evidence_node_id,
                citation_id=reference.citation_id,
                source_locator=reference.source_locator,
                source_title=reference.source_title,
                reference_digest=reference.reference_digest,
                provenance_status=reference.provenance_status,
                privacy_label=reference.privacy_label,
                created_at=reference.created_at,
            )
            for reference in references
        ]
        return self.store.create_case_with_evidence(case, bound_references)

    @staticmethod
    def _references_from_trace(trace: Any) -> list[CaseEvidenceReference]:
        references: list[CaseEvidenceReference] = []
        for node in getattr(trace, "nodes", ()):
            if str(getattr(node, "node_type", "")) != "source":
                continue
            evidence_node_id = str(getattr(node, "id", "") or "")
            citation_id = str(getattr(node, "citation_id", "") or "")
            source_locator = str(getattr(node, "source_id", "") or "")
            source_title = str(getattr(node, "title", "") or "")
            privacy_label = str(getattr(node, "privacy_label", "") or "")
            if not all((evidence_node_id, citation_id, source_locator, source_title)):
                continue
            if privacy_label != "local_only":
                continue
            reference_digest = _digest(
                {
                    "trace_id": str(getattr(trace, "trace_id", "") or ""),
                    "evidence_node_id": evidence_node_id,
                    "citation_id": citation_id,
                    "source_locator": source_locator,
                }
            )
            references.append(
                CaseEvidenceReference(
                    reference_id=f"CASE-REF-{uuid4().hex[:12].upper()}",
                    case_id="",
                    trace_id=str(getattr(trace, "trace_id", "") or ""),
                    evidence_node_id=evidence_node_id,
                    citation_id=citation_id,
                    source_locator=source_locator,
                    source_title=source_title,
                    reference_digest=reference_digest,
                    privacy_label=privacy_label,
                )
            )
        return references
