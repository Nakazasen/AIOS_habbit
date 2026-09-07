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
    ALLOWED_EXPERT_DECISIONS,
    ALLOWED_ARTIFACT_TYPES,
    CaseActivity,
    CaseArtifactRecord,
    CaseChecklistItem,
    CaseDetail,
    CaseEvidenceReference,
    CaseFilter,
    CaseLesson,
    CaseRecord,
    ExpertRequest,
    ExpertReview,
    EXPERT_DECISION_CONFIRMED,
    LESSON_STATUS_APPROVED,
    LESSON_STATUS_CANDIDATE,
    LESSON_STATUS_REVOKED,
    TraceResolution,
    utc_now_iso,
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
            expert_requests=tuple(self.store.list_expert_requests(case_id)),
            expert_reviews=tuple(self.store.list_expert_reviews(case_id)),
            lessons=tuple(self.store.list_case_lessons(case_id)),
            artifacts=tuple(self.store.list_case_artifacts(case_id)),
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

    def request_expert_review(
        self,
        case_id: str,
        *,
        claim_digest: str,
        question: str,
        required_scope: str,
        requested_expert_id: Optional[str] = None,
        due_at: Optional[str] = None,
    ) -> ExpertRequest:
        self._require("expert.request", required_scope)
        case = self._load_authorized(case_id, "case.view")
        q = question.strip()
        if not q:
            raise CaseValidationError("EXPERT_QUESTION_REQUIRED")
        if claim_digest != case.evidence_digest:
            raise CaseValidationError("EVIDENCE_DIGEST_MISMATCH")

        request_id = f"EXP-REQ-{uuid4().hex[:12].upper()}"
        req = ExpertRequest(
            request_id=request_id,
            case_id=case_id,
            claim_digest=claim_digest,
            question_text=q,
            required_scope=required_scope,
            requested_expert_id=requested_expert_id.strip() if requested_expert_id else None,
            due_at=due_at,
            created_by=self.actor.actor_id,
        )
        activity = CaseActivity.new(
            case_id=case_id,
            event_type="expert_review_requested",
            actor_id=self.actor.actor_id,
            payload_digest=_digest({"request_id": request_id, "question": q}),
            previous_event_digest=case.activity_head_digest,
        )
        try:
            return self.store.create_expert_request(req, activity=activity)
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def record_expert_review(
        self,
        request_id: str,
        *,
        decision: str,
        rationale: str,
        confidence: float = 1.0,
        supersedes_review_id: Optional[str] = None,
    ) -> ExpertReview:
        if decision not in ALLOWED_EXPERT_DECISIONS:
            raise CaseValidationError("EXPERT_DECISION_INVALID")
        rat = rationale.strip()
        if not rat:
            raise CaseValidationError("EXPERT_RATIONALE_REQUIRED")

        req = self.store.load_expert_request(request_id)
        if req is None:
            raise CaseValidationError("EXPERT_REQUEST_NOT_FOUND")

        self._require("expert.review", req.required_scope)
        if req.requested_expert_id and req.requested_expert_id != self.actor.actor_id:
            raise CaseValidationError("EXPERT_MISMATCH")

        case = self.store.load_case(req.case_id)
        if case is None:
            raise CaseValidationError("CASE_NOT_FOUND")
        if case.evidence_digest != req.claim_digest:
            raise CaseValidationError("EVIDENCE_DIGEST_MISMATCH")

        review_id = f"EXP-REV-{uuid4().hex[:12].upper()}"
        review = ExpertReview(
            review_id=review_id,
            request_id=request_id,
            case_id=req.case_id,
            claim_digest=req.claim_digest,
            evidence_digest=case.evidence_digest,
            decision=decision,
            reviewer_id=self.actor.actor_id,
            reviewer_role="expert",
            scope=req.required_scope,
            rationale=rat,
            confidence=confidence,
            supersedes_review_id=supersedes_review_id,
        )
        activity = CaseActivity.new(
            case_id=case.case_id,
            event_type="expert_review_recorded",
            actor_id=self.actor.actor_id,
            payload_digest=_digest({"review_id": review_id, "decision": decision, "rationale": rat}),
            previous_event_digest=case.activity_head_digest,
        )
        try:
            return self.store.record_expert_review(review, updated_request_status="answered", activity=activity)
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def resolve_review_conflict(
        self,
        case_id: str,
        *,
        review_ids: list[str],
        decision: str,
        rationale: str,
    ) -> ExpertReview:
        case = self._load_authorized(case_id, "case.view")
        self._require("expert.resolve_conflict", case.scope)
        if decision not in ALLOWED_EXPERT_DECISIONS:
            raise CaseValidationError("EXPERT_DECISION_INVALID")
        rat = rationale.strip()
        if not rat:
            raise CaseValidationError("EXPERT_RATIONALE_REQUIRED")
        if not review_ids:
            raise CaseValidationError("EXPERT_REVIEW_IDS_REQUIRED")

        req_id = ""
        for rid in review_ids:
            r = self.store.load_expert_review(rid)
            if not r:
                raise CaseValidationError(f"EXPERT_REVIEW_NOT_FOUND: {rid}")
            if r.case_id != case.case_id:
                raise CaseValidationError(
                    f"EXPERT_REVIEW_WRONG_CASE: Review {rid} thuộc case {r.case_id}, không thuộc case {case.case_id}"
                )
            if req_id and r.request_id != req_id:
                raise CaseValidationError(
                    "EXPERT_REVIEW_REQUEST_MISMATCH: Các review xung đột phải thuộc cùng một yêu cầu tham vấn."
                )
            req_id = r.request_id

        if not req_id:
            requests = self.store.list_expert_requests(case_id)
            if requests:
                req_id = requests[0].request_id
            else:
                req_id = f"EXP-REQ-{uuid4().hex[:12].upper()}"

        review_id = f"EXP-REV-{uuid4().hex[:12].upper()}"
        review = ExpertReview(
            review_id=review_id,
            request_id=req_id,
            case_id=case_id,
            claim_digest=case.evidence_digest,
            evidence_digest=case.evidence_digest,
            decision=decision,
            reviewer_id=self.actor.actor_id,
            reviewer_role="lead_specialist",
            scope=case.scope,
            rationale=rat,
            confidence=1.0,
        )
        activity = CaseActivity.new(
            case_id=case.case_id,
            event_type="review_conflict_resolved",
            actor_id=self.actor.actor_id,
            payload_digest=_digest({"review_id": review_id, "decision": decision, "resolved_reviews": review_ids}),
            previous_event_digest=case.activity_head_digest,
        )
        try:
            return self.store.record_expert_review(review, updated_request_status="answered", activity=activity)
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def propose_lesson(
        self,
        case_id: str,
        review_id: str,
        *,
        title: str,
        content: str,
    ) -> CaseLesson:
        case = self._load_authorized(case_id, "learning.propose")
        rev = self.store.load_expert_review(review_id)
        if rev is None:
            raise CaseValidationError("EXPERT_REVIEW_NOT_FOUND")
        if rev.case_id != case_id:
            raise CaseValidationError("EXPERT_REVIEW_WRONG_CASE")
        if rev.decision != EXPERT_DECISION_CONFIRMED:
            raise CaseValidationError("LESSON_PROPOSE_CONFIRMED_REVIEW_REQUIRED")
        clean_title = title.strip()
        clean_content = content.strip()
        if not clean_title:
            raise CaseValidationError("LESSON_TITLE_REQUIRED")
        if not clean_content:
            raise CaseValidationError("LESSON_CONTENT_REQUIRED")

        lesson_id = f"LES-{uuid4().hex[:12].upper()}"
        now = utc_now_iso()
        lesson = CaseLesson(
            lesson_id=lesson_id,
            case_id=case_id,
            review_id=review_id,
            claim_digest=rev.claim_digest,
            evidence_digest=rev.evidence_digest,
            title=clean_title,
            content=clean_content,
            status=LESSON_STATUS_CANDIDATE,
            version=1,
            created_by=self.actor.actor_id,
            created_at=now,
            updated_by=self.actor.actor_id,
            updated_at=now,
        )
        activity = CaseActivity.new(
            case_id=case_id,
            event_type="lesson_proposed",
            actor_id=self.actor.actor_id,
            payload_digest=_digest({"lesson_id": lesson_id, "title": clean_title}),
            previous_event_digest=case.activity_head_digest,
        )
        try:
            return self.store.create_case_lesson(lesson, activity=activity)
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def update_lesson(
        self,
        lesson_id: str,
        *,
        expected_version: int,
        title: str,
        content: str,
    ) -> CaseLesson:
        lesson = self.store.load_case_lesson(lesson_id)
        if lesson is None:
            raise CaseValidationError("CASE_LESSON_NOT_FOUND")
        case = self._load_authorized(lesson.case_id, "learning.propose")
        clean_title = title.strip()
        clean_content = content.strip()
        if not clean_title:
            raise CaseValidationError("LESSON_TITLE_REQUIRED")
        if not clean_content:
            raise CaseValidationError("LESSON_CONTENT_REQUIRED")
        activity = CaseActivity.new(
            case_id=lesson.case_id,
            event_type="lesson_updated",
            actor_id=self.actor.actor_id,
            payload_digest=_digest({"lesson_id": lesson_id, "title": clean_title, "version": expected_version + 1}),
            previous_event_digest=case.activity_head_digest,
        )
        try:
            return self.store.update_case_lesson(
                lesson_id,
                expected_version=expected_version,
                title=clean_title,
                content=clean_content,
                actor_id=self.actor.actor_id,
                activity=activity,
            )
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def approve_lesson(
        self,
        lesson_id: str,
        *,
        expected_version: int,
    ) -> CaseLesson:
        lesson = self.store.load_case_lesson(lesson_id)
        if lesson is None:
            raise CaseValidationError("CASE_LESSON_NOT_FOUND")
        case = self._load_authorized(lesson.case_id, "learning.approve")
        if lesson.status != LESSON_STATUS_CANDIDATE:
            raise CaseValidationError("CASE_LESSON_NOT_CANDIDATE")
        activity = CaseActivity.new(
            case_id=lesson.case_id,
            event_type="lesson_approved",
            actor_id=self.actor.actor_id,
            payload_digest=_digest({"lesson_id": lesson_id, "status": LESSON_STATUS_APPROVED}),
            previous_event_digest=case.activity_head_digest,
        )
        try:
            return self.store.promote_case_lesson(
                lesson_id,
                expected_version=expected_version,
                actor_id=self.actor.actor_id,
                activity=activity,
            )
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def revoke_lesson(
        self,
        lesson_id: str,
        *,
        expected_version: int,
        reason: str,
    ) -> CaseLesson:
        lesson = self.store.load_case_lesson(lesson_id)
        if lesson is None:
            raise CaseValidationError("CASE_LESSON_NOT_FOUND")
        case = self._load_authorized(lesson.case_id, "learning.revoke")
        clean_reason = reason.strip()
        if not clean_reason:
            raise CaseValidationError("LESSON_REVOKE_REASON_REQUIRED")
        activity = CaseActivity.new(
            case_id=lesson.case_id,
            event_type="lesson_revoked",
            actor_id=self.actor.actor_id,
            payload_digest=_digest({"lesson_id": lesson_id, "reason": clean_reason}),
            previous_event_digest=case.activity_head_digest,
        )
        try:
            return self.store.revoke_case_lesson(
                lesson_id,
                expected_version=expected_version,
                actor_id=self.actor.actor_id,
                reason=clean_reason,
                activity=activity,
            )
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def search_approved_lessons(self, query: str) -> list[CaseLesson]:
        clean_q = query.strip()
        if not clean_q:
            return []
        return self.store.search_approved_lessons(clean_q)

    def list_case_lessons(self, case_id: str) -> list[CaseLesson]:
        case = self._load_authorized(case_id, "case.view")
        return self.store.list_case_lessons(case.case_id)

    def list_all_lessons(self, *, status: Optional[str] = None) -> list[CaseLesson]:
        self._require("learning.propose", "general")
        return self.store.list_all_lessons(status=status)

    def review_clue_relevance(
        self,
        case_id: str,
        reference_id: str,
        *,
        expected_version: int,
        relevance: str,
        note: str = "",
    ) -> CaseRecord:
        case = self._load_authorized(case_id, "case.attach_evidence")
        clean_note = note.strip()
        if relevance not in {"confirmed", "rejected", "suspected"}:
            raise CaseValidationError("CLUE_RELEVANCE_INVALID")
        provenance_map = {
            "confirmed": "approved",
            "rejected": "unknown",
            "suspected": "suspected",
        }
        new_provenance = provenance_map[relevance]
        try:
            return self.store.update_evidence_provenance(
                case_id,
                reference_id,
                expected_version=expected_version,
                new_provenance=new_provenance,
                actor_id=self.actor.actor_id,
                note=clean_note,
            )
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def attach_line_investigation_clue(
        self,
        case_id: str,
        *,
        expected_version: int,
        event_id: str,
        station: str,
        code: str,
        occurred_at: str,
        dialect: str = "line_log",
        relevance: str = "suspected",
    ) -> CaseRecord:
        case = self._load_authorized(case_id, "case.attach_evidence")
        clean_event_id = _scrub_identifier(event_id, "su-kien")
        clean_station = _scrub_identifier(station or "unassigned", "tram")
        locator = f"line_event:{clean_event_id}:{clean_station}"
        title = f"Sự kiện {dialect} - Trạm {station} - Mã {code} ({occurred_at})"
        content_digest = hashlib.sha256(f"{clean_event_id}:{station}:{code}:{occurred_at}".encode("utf-8")).hexdigest()
        prov_map = {
            "confirmed": "approved",
            "rejected": "unknown",
            "suspected": "suspected",
        }
        provenance_status = prov_map.get(relevance, "suspected")
        return self.attach_evidence_reference(
            case_id,
            expected_version=expected_version,
            source_store="line_events",
            source_id=clean_event_id,
            source_version="v1",
            locator=locator,
            title=title,
            content_digest=content_digest,
            provenance_status=provenance_status,
        )

    def draft_case_artifact(
        self,
        case_id: str,
        *,
        artifact_type: str,
        title: str,
        conclusions_or_grounds: str = "",
    ) -> CaseArtifactRecord:
        case = self._load_authorized(case_id, "artifact.draft")
        clean_type = str(artifact_type or "").strip().lower()
        if clean_type not in ALLOWED_ARTIFACT_TYPES:
            raise CaseValidationError("ARTIFACT_TYPE_INVALID")
        clean_title = str(title or "").strip()
        if not clean_title:
            raise CaseValidationError("ARTIFACT_TITLE_REQUIRED")

        detail = self.get_case_detail(case_id)
        valid_refs = [ref for ref in detail.evidence if ref.provenance_status in {"approved", "suspected"}]
        if not valid_refs:
            raise CaseValidationError("ARTIFACT_INSUFFICIENT_EVIDENCE")

        from aios_habit.agent_draft_sop import compose_draft_from_evidence

        evidence_items = []
        for ref in valid_refs:
            evidence_items.append({
                "source_id": ref.reference_id,
                "source_type": "line_log" if ref.evidence_node_id.startswith("line_events:") else "rag_text",
                "title": ref.source_title,
                "location_info": ref.source_locator,
                "text": f"Bằng chứng tham chiếu {ref.citation_id}: {ref.source_title}",
                "provenance": ref.provenance_status,
            })

        evidence_pack = {
            "evidence_items": evidence_items,
            "line_events_matched": {},
        }

        try:
            draft_doc = compose_draft_from_evidence(
                evidence_pack=evidence_pack,
                doc_type=clean_type,
                title=clean_title,
                author=self.actor.actor_id,
                target_station=case.scope,
                case_id=case_id,
                version=1,
                evidence_digest=case.evidence_digest,
                required_approver_role="quality_manager",
                conclusions_or_grounds=conclusions_or_grounds,
                require_evidence=True,
            )
        except ValueError as exc:
            raise CaseValidationError("ARTIFACT_INSUFFICIENT_EVIDENCE") from exc

        content_digest = hashlib.sha256(draft_doc.content_markdown.encode("utf-8")).hexdigest()
        artifact = CaseArtifactRecord(
            artifact_id=f"ART-{uuid4().hex[:10].upper()}",
            case_id=case_id,
            artifact_type=clean_type,
            title=clean_title,
            content_markdown=draft_doc.content_markdown,
            content_digest=content_digest,
            version=1,
            status="draft",
            created_by=self.actor.actor_id,
            updated_by=self.actor.actor_id,
            provenance_digest=case.evidence_digest,
        )
        activity = CaseActivity.new(
            case_id=case_id,
            event_type="artifact_drafted",
            actor_id=self.actor.actor_id,
            payload_digest=_digest({"artifact_id": artifact.artifact_id, "digest": content_digest, "type": clean_type}),
            previous_event_digest=case.activity_head_digest,
        )
        return self.store.insert_artifact(artifact, activity=activity)

    def update_case_artifact(
        self,
        artifact_id: str,
        *,
        expected_version: int,
        content_markdown: str,
        title: Optional[str] = None,
    ) -> CaseArtifactRecord:
        artifact = self.store.load_case_artifact(artifact_id)
        if artifact is None:
            raise CaseValidationError("CASE_ARTIFACT_NOT_FOUND")
        case = self._load_authorized(artifact.case_id, "artifact.draft")
        if artifact.status == "approved":
            raise CaseValidationError("APPROVED_ARTIFACT_IMMUTABLE")
        if not content_markdown.strip():
            raise CaseValidationError("ARTIFACT_CONTENT_REQUIRED")

        content_digest = hashlib.sha256(content_markdown.encode("utf-8")).hexdigest()
        activity = CaseActivity.new(
            case_id=artifact.case_id,
            event_type="artifact_updated",
            actor_id=self.actor.actor_id,
            payload_digest=_digest({"artifact_id": artifact_id, "digest": content_digest, "expected_version": expected_version}),
            previous_event_digest=case.activity_head_digest,
        )
        try:
            return self.store.update_artifact_content(
                artifact_id,
                expected_version=expected_version,
                title=title,
                content_markdown=content_markdown,
                content_digest=content_digest,
                updated_by=self.actor.actor_id,
                activity=activity,
            )
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def approve_case_artifact(
        self,
        artifact_id: str,
        *,
        expected_version: int,
        notes: str = "",
    ) -> CaseArtifactRecord:
        artifact = self.store.load_case_artifact(artifact_id)
        if artifact is None:
            raise CaseValidationError("CASE_ARTIFACT_NOT_FOUND")
        case = self._load_authorized(artifact.case_id, "artifact.approve")

        from aios_habit.agent_draft_sop import DraftDocument, approve_draft_document

        draft = DraftDocument(
            draft_id=artifact.artifact_id,
            doc_type=artifact.artifact_type,
            title=artifact.title,
            status="draft",
            content_markdown=artifact.content_markdown,
            author=artifact.created_by,
            created_at=artifact.created_at,
            case_id=artifact.case_id,
            version=artifact.version,
            evidence_digest=artifact.provenance_digest,
            required_approver_role="quality_manager",
        )
        approved_doc = approve_draft_document(draft, approver=self.actor.actor_id, notes=notes)
        activity = CaseActivity.new(
            case_id=artifact.case_id,
            event_type="artifact_approved",
            actor_id=self.actor.actor_id,
            payload_digest=_digest({"artifact_id": artifact_id, "approver": self.actor.actor_id}),
            previous_event_digest=case.activity_head_digest,
        )
        try:
            return self.store.approve_artifact(
                artifact_id,
                expected_version=expected_version,
                approved_by=self.actor.actor_id,
                approval_notes=notes,
                approved_content=approved_doc.content_markdown,
                activity=activity,
            )
        except WorkspaceCaseRepositoryError as error:
            raise CaseValidationError(str(error)) from error

    def export_case_artifact(
        self,
        artifact_id: str,
        *,
        output_root: Optional[Any] = None,
        relative_filename: Optional[str] = None,
    ) -> tuple[CaseArtifactRecord, Any]:
        from pathlib import Path
        artifact = self.store.load_case_artifact(artifact_id)
        if artifact is None:
            raise CaseValidationError("CASE_ARTIFACT_NOT_FOUND")
        if artifact.status != "approved":
            raise CaseValidationError("UNAPPROVED_ARTIFACT_EXPORT_FORBIDDEN")
        case = self._load_authorized(artifact.case_id, "case.view")

        from aios_habit.agent_draft_sop import DraftDocument, save_draft_document

        out_root = Path(output_root).resolve() if output_root else (Path.cwd() / "exports" / "artifacts").resolve()
        out_root.mkdir(parents=True, exist_ok=True)

        if relative_filename:
            clean_name = Path(relative_filename).name
            if not clean_name.endswith(".md"):
                clean_name += ".md"
        else:
            clean_name = f"{artifact.artifact_type}_{artifact.case_id}_{artifact.artifact_id}.md"

        target_file = out_root / clean_name
        draft = DraftDocument(
            draft_id=artifact.artifact_id,
            doc_type=artifact.artifact_type,
            title=artifact.title,
            status="approved",
            content_markdown=artifact.content_markdown,
            author=artifact.created_by,
            created_at=artifact.created_at,
            case_id=artifact.case_id,
            version=artifact.version,
            evidence_digest=artifact.provenance_digest,
            required_approver_role="quality_manager",
        )
        saved_str = save_draft_document(
            draft,
            target_file,
            approved=True,
            output_root=out_root,
            auto_version_existing=True,
        )
        saved_path = Path(saved_str)
        activity = CaseActivity.new(
            case_id=artifact.case_id,
            event_type="artifact_exported",
            actor_id=self.actor.actor_id,
            payload_digest=_digest({"artifact_id": artifact_id, "path": saved_path.name}),
            previous_event_digest=case.activity_head_digest,
        )
        updated = self.store.record_artifact_export(artifact_id, exported_path=str(saved_path), activity=activity)
        return updated, saved_path

    def list_case_artifacts(self, case_id: str) -> list[CaseArtifactRecord]:
        self._load_authorized(case_id, "case.view")
        return self.store.list_case_artifacts(case_id)

    def load_case_artifact(self, artifact_id: str) -> Optional[CaseArtifactRecord]:
        artifact = self.store.load_case_artifact(artifact_id)
        if artifact is not None:
            self._load_authorized(artifact.case_id, "case.view")
        return artifact

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
