"""Authorized use cases for durable local evidence cases."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable, Optional
from uuid import uuid4

from aios_habit.evidence_trace import is_insufficient_evidence
from aios_habit.workspace_case_authorization import (
    ActorContext,
    AuthorizationError,
    WorkspaceCaseAuthorization,
    trusted_local_actor,
)
from aios_habit.workspace_case_models import (
    CASE_STATUS_CLOSED,
    CASE_STATUS_DRAFT,
    CASE_STATUS_IN_PROGRESS,
    CASE_STATUS_RESOLVED,
    CASE_STATUS_TRIAGED,
    CASE_STATUS_WAITING_EVIDENCE,
    CaseChecklistItem,
    CaseDetail,
    CaseEvidenceReference,
    CaseFilter,
    CaseRecord,
    TraceResolution,
)
from aios_habit.workspace_case_repository import (
    CaseCreationResult,
    WorkspaceCaseRepository,
    WorkspaceCaseRepositoryError,
)
from aios_habit.workspace_chat_store import load_evidence_trace


class CaseValidationError(ValueError):
    """Validation failure safe to display without a traceback."""


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _scrub_identifier(value: str, prefix: str) -> str:
    identifier = value.strip()
    if not identifier:
        return ""
    if any(ord(character) < 32 for character in identifier):
        raise CaseValidationError("CASE_EVIDENCE_IDENTITY_REQUIRED")
    if re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", identifier) and ".." not in identifier:
        return identifier
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}:{digest}"


def _scrub_locator(value: str) -> str:
    locator = value.strip().replace("\\", "/")
    if not locator or any(ord(character) < 32 for character in locator):
        raise CaseValidationError("CASE_EVIDENCE_LOCATOR_INVALID")
    is_absolute = locator.startswith(("/", "//")) or bool(re.match(r"^[A-Za-z]:/", locator))
    has_traversal = any(part == ".." for part in locator.split("/"))
    if is_absolute or has_traversal:
        return f"nguon:{hashlib.sha256(locator.encode('utf-8')).hexdigest()[:20]}"
    return locator[:240]


def _scrub_title(value: str) -> str:
    title = " ".join(value.strip().split())
    if not title:
        raise CaseValidationError("CASE_EVIDENCE_TITLE_REQUIRED")
    if re.search(r"[A-Za-z]:[\\/]", title) or title.startswith(("/", "\\\\")):
        return f"Nguồn {hashlib.sha256(title.encode('utf-8')).hexdigest()[:8]}"
    return title[:200]


_TRANSITIONS = {
    CASE_STATUS_DRAFT: {CASE_STATUS_TRIAGED, CASE_STATUS_IN_PROGRESS, CASE_STATUS_WAITING_EVIDENCE},
    CASE_STATUS_TRIAGED: {CASE_STATUS_IN_PROGRESS, CASE_STATUS_WAITING_EVIDENCE, CASE_STATUS_RESOLVED},
    CASE_STATUS_IN_PROGRESS: {CASE_STATUS_WAITING_EVIDENCE, CASE_STATUS_RESOLVED},
    CASE_STATUS_WAITING_EVIDENCE: {CASE_STATUS_IN_PROGRESS, CASE_STATUS_RESOLVED},
    CASE_STATUS_RESOLVED: {CASE_STATUS_IN_PROGRESS, CASE_STATUS_CLOSED},
    CASE_STATUS_CLOSED: set(),
}


class WorkspaceCaseService:
    def __init__(
        self,
        store: Optional[WorkspaceCaseRepository] = None,
        *,
        actor_context: Optional[ActorContext] = None,
        trace_loader: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self.store = store or WorkspaceCaseRepository()
        self.actor = actor_context or trusted_local_actor()
        self.authorization = WorkspaceCaseAuthorization(self.store)
        self.trace_loader = trace_loader or load_evidence_trace

    def _require(self, capability: str, scope: str) -> None:
        try:
            self.authorization.require(self.actor, capability, scope)
        except AuthorizationError as error:
            raise CaseValidationError(str(error)) from error

    def create_case_from_trace_id(
        self,
        trace_id: str,
        *,
        expected_conversation_id: str,
    ) -> CaseCreationResult:
        trace = self.trace_loader(trace_id)
        if trace is None:
            raise CaseValidationError("Không tìm thấy dấu vết bằng chứng của câu trả lời này.")
        return self.create_case_from_trace(trace, expected_conversation_id=expected_conversation_id)

    def create_case_from_trace(self, trace: Any, *, expected_conversation_id: str) -> CaseCreationResult:
        self._require("case.attach_evidence", "general")
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
            created_by=self.actor.actor_id,
            scope="general",
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

    def list_cases(self, case_filter: Optional[CaseFilter] = None) -> list[CaseRecord]:
        visible: list[CaseRecord] = []
        for case in self.store.list_cases(case_filter):
            try:
                self.authorization.require(self.actor, "case.view", case.scope)
            except AuthorizationError:
                continue
            visible.append(case)
        return visible

    def get_case_detail(self, case_id: str) -> CaseDetail:
        case = self.store.load_case(case_id)
        if case is None:
            raise CaseValidationError("CASE_NOT_FOUND")
        self._require("case.view", case.scope)
        if not self.store.verify_activity_chain(case_id):
            raise CaseValidationError("CASE_ACTIVITY_CHAIN_INVALID")
        return CaseDetail(
            case=case,
            evidence=tuple(self.store.list_evidence_references(case_id)),
            activities=tuple(self.store.list_activities(case_id)),
            checklist=tuple(self.store.list_checklist_items(case_id)),
        )

    def transition_case(
        self,
        case_id: str,
        *,
        expected_version: int,
        new_status: str,
        rationale: str,
    ) -> CaseRecord:
        case = self._load_authorized(case_id, "case.transition")
        if new_status in {CASE_STATUS_RESOLVED, CASE_STATUS_CLOSED}:
            raise CaseValidationError("CASE_RESOLUTION_REVIEW_REQUIRED")
        if new_status not in _TRANSITIONS.get(case.status, set()):
            raise CaseValidationError("CASE_TRANSITION_INVALID")
        if not rationale.strip():
            raise CaseValidationError("CASE_RATIONALE_REQUIRED")
        try:
            return self.store.transition_case(
                case_id,
                expected_version=expected_version,
                new_status=new_status,
                actor_id=self.actor.actor_id,
                payload_digest=_digest({"from": case.status, "to": new_status, "rationale": rationale.strip()}),
            )
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def assign_case(self, case_id: str, *, expected_version: int, assignee_id: str) -> CaseRecord:
        case = self._load_authorized(case_id, "case.assign")
        assignee = assignee_id.strip()
        if not assignee:
            raise CaseValidationError("CASE_ASSIGNEE_REQUIRED")
        try:
            self.authorization.require(ActorContext(assignee), "case.receive", case.scope)
        except AuthorizationError as error:
            raise CaseValidationError("CASE_ASSIGNEE_NOT_AUTHORIZED") from error
        try:
            return self.store.assign_case(
                case_id,
                expected_version=expected_version,
                assignee_id=assignee,
                actor_id=self.actor.actor_id,
                payload_digest=_digest({"assignee_id": assignee}),
            )
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def add_checklist_item(self, case_id: str, *, expected_version: int, description: str) -> CaseRecord:
        self._load_authorized(case_id, "case.checklist")
        clean_description = " ".join(description.strip().split())
        if not clean_description:
            raise CaseValidationError("CASE_CHECKLIST_DESCRIPTION_REQUIRED")
        item = CaseChecklistItem(
            item_id=f"CASE-ITEM-{uuid4().hex[:12].upper()}",
            case_id=case_id,
            description=clean_description[:240],
            created_by=self.actor.actor_id,
        )
        try:
            return self.store.add_checklist_item(
                item, expected_version=expected_version, actor_id=self.actor.actor_id
            )
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def attach_evidence_reference(
        self,
        case_id: str,
        *,
        expected_version: int,
        source_store: str,
        source_id: str,
        source_version: str,
        locator: str,
        title: str,
        content_digest: str,
        provenance_status: str,
    ) -> CaseRecord:
        case = self._load_authorized(case_id, "case.attach_evidence")
        if source_store not in {"workspace_trace", "library", "line_events", "prediction", "approved_artifact"}:
            raise CaseValidationError("CASE_EVIDENCE_STORE_INVALID")
        if provenance_status not in {"suspected", "approved", "unknown", "missing"}:
            raise CaseValidationError("CASE_EVIDENCE_PROVENANCE_INVALID")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", content_digest):
            raise CaseValidationError("CASE_EVIDENCE_DIGEST_INVALID")
        clean_source_id = _scrub_identifier(source_id, "nguon")
        clean_source_version = _scrub_identifier(source_version, "phien-ban")
        if not clean_source_id or not clean_source_version:
            raise CaseValidationError("CASE_EVIDENCE_IDENTITY_REQUIRED")
        clean_locator = _scrub_locator(locator)
        clean_title = _scrub_title(title)
        reference_digest = _digest(
            {
                "content_digest": content_digest.lower(),
                "locator": clean_locator,
                "source_id": clean_source_id,
                "source_store": source_store,
                "source_version": clean_source_version,
            }
        )
        reference = CaseEvidenceReference(
            reference_id=f"CASE-REF-{uuid4().hex[:12].upper()}",
            case_id=case_id,
            trace_id=case.trace_id,
            evidence_node_id=f"{source_store}:{clean_source_id}:{clean_source_version}",
            citation_id="[BỔ SUNG]",
            source_locator=clean_locator,
            source_title=clean_title,
            reference_digest=reference_digest,
            provenance_status=provenance_status,
        )
        try:
            return self.store.attach_evidence(
                reference, expected_version=expected_version, actor_id=self.actor.actor_id
            )
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def open_trace(self, case_id: str) -> TraceResolution:
        case = self._load_authorized(case_id, "case.view")
        trace = self.trace_loader(case.trace_id)
        if trace is None:
            return TraceResolution(status="missing", trace_id=case.trace_id)
        if str(getattr(trace, "conversation_id", "")) != case.conversation_id:
            return TraceResolution(status="missing", trace_id=case.trace_id)
        return TraceResolution(status="available", trace_id=case.trace_id, trace=trace)

    def _load_authorized(self, case_id: str, capability: str) -> CaseRecord:
        case = self.store.load_case(case_id)
        if case is None:
            raise CaseValidationError("CASE_NOT_FOUND")
        self._require(capability, case.scope)
        return case

    @staticmethod
    def _references_from_trace(trace: Any) -> list[CaseEvidenceReference]:
        references: list[CaseEvidenceReference] = []
        for node in getattr(trace, "nodes", ()):
            if str(getattr(node, "node_type", "")) != "source":
                continue
            evidence_node_id = str(getattr(node, "id", "") or "")
            citation_id = str(getattr(node, "citation_id", "") or "")
            source_locator_raw = str(getattr(node, "source_id", "") or "")
            source_title_raw = str(getattr(node, "title", "") or "")
            privacy_label = str(getattr(node, "privacy_label", "") or "")
            if not all((evidence_node_id, citation_id, source_locator_raw, source_title_raw)):
                continue
            if privacy_label != "local_only":
                continue
            source_locator = _scrub_locator(source_locator_raw)
            source_title = _scrub_title(source_title_raw)
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
