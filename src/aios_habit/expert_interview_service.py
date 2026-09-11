"""Service layer for expert interview planning, sessions, turns, and adaptive guardrails.

Implements T026, T028, T032, T035 of 010-expert-knowledge-acquisition.
Follows ADR-0009 and data-model.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any, Callable, Optional, Sequence
from uuid import uuid4

from aios_habit.adaptive_interview_engine import (
    generate_seed_questions,
    propose_next_action,
    validate_candidate_question,
    validate_session_transition,
)
from aios_habit.expert_identity import VerifiedPrincipal
from aios_habit.expert_interview_models import (
    ACTION_COMPLETE,
    ACTION_ESCALATE,
    ACTION_PAUSE,
    ANSWER_STATE_ANSWERED,
    ANSWER_STATE_CORRECTED,
    ANSWER_STATE_SKIPPED,
    ANSWER_STATE_UNCERTAIN,
    ANSWER_STATE_UNKNOWN,
    CONSENT_GRANTED,
    CONSENT_NOT_REQUESTED,
    PLAN_STATUS_APPROVED,
    PLAN_STATUS_DRAFT,
    SESSION_STATE_ACTIVE,
    SESSION_STATE_BLOCKED,
    SESSION_STATE_COMPLETED,
    SESSION_STATE_PAUSED,
    SESSION_STATE_READY,
    SESSION_STATE_STOPPED,
    CompletionRubric,
    InterviewBudget,
    InterviewCheckpoint,
    InterviewPlan,
    InterviewPlanError,
    InterviewSession,
    InterviewSessionError,
    InterviewTurn,
    NextActionDecision,
    REASON_EXPERT_PAUSE,
    REASON_EXPERT_STOP,
)
from aios_habit.expert_interview_repository import ExpertInterviewRepository
from aios_habit.controlled_knowledge_artifact import (
    APPROVAL_ACTION_APPROVE,
    APPROVAL_ACTION_REJECT,
    APPROVAL_ACTION_REQUEST_CHANGE,
    APPROVAL_ACTION_REVOKE,
    ARTIFACT_STATUS_APPROVED,
    ARTIFACT_STATUS_CANDIDATE,
    ARTIFACT_STATUS_CHANGES_REQUESTED,
    ARTIFACT_STATUS_REJECTED,
    ARTIFACT_STATUS_REVOKED,
    ARTIFACT_TYPE_LESSON,
    DECISION_CONFIRM,
    DECISION_REJECT,
    DECISION_REQUEST_CHANGE,
    DECISION_REVOKE,
    ConflictedClaimArtifactError,
    ControlledArtifactError,
    ControlledKnowledgeArtifact,
    DecisionRecord,
    StaleArtifactDigestError,
)
from aios_habit.knowledge_claim_extractor import CLAIM_STATUS_CONFLICTED, extract_claim_from_turn

from aios_habit.knowledge_coverage import GAP_STATUS_ACCEPTED, KnowledgeGapCandidate
from aios_habit.workspace_case_authorization import ActorContext, trusted_local_actor
from aios_habit.workspace_case_repository import WorkspaceCaseRepository


class ExpertInterviewService:
    """Service governing verified expert interview lifecycle."""

    def __init__(
        self,
        store: Optional[WorkspaceCaseRepository] = None,
        interview_repo: Optional[ExpertInterviewRepository] = None,
        *,
        actor_context: Optional[ActorContext] = None,
        gateway_client: Optional[Any] = None,
    ) -> None:
        self.store = store or WorkspaceCaseRepository()
        self.interview_repo = interview_repo or ExpertInterviewRepository(self.store.database_path)
        self.actor = actor_context or trusted_local_actor()
        self.gateway_client = gateway_client
        self._plan_cache: dict[str, InterviewPlan] = {}

    def create_interview_plan(
        self,
        gap_id: str,
        *,
        expected_gap_digest: Optional[str] = None,
        budget: Optional[InterviewBudget] = None,
        completion_rubric: Optional[CompletionRubric] = None,
        actor: Optional[ActorContext] = None,
    ) -> InterviewPlan:
        """Create a versioned interview plan for an accepted knowledge gap."""
        actor_ctx = actor or self.actor

        gap = self.store.get_gap_candidate(gap_id)
        if gap is None:
            raise InterviewPlanError(f"Không tìm thấy khoảng trống tri thức '{gap_id}'.")

        if expected_gap_digest is not None and gap.digest != expected_gap_digest:
            raise InterviewPlanError("Khoảng trống tri thức đã bị thay đổi (stale digest).")

        if not gap.evidence_refs:
            raise InterviewPlanError("Khoảng trống tri thức thiếu bằng chứng tham chiếu.")

        if gap.status != GAP_STATUS_ACCEPTED:
            raise InterviewPlanError(
                f"Chỉ có thể lập kế hoạch phỏng vấn cho khoảng trống đã được chấp thuận (accepted). Trạng thái hiện tại: '{gap.status}'."
            )

        recorded_person = actor_ctx.actor_id.strip() or "người dùng"

        plan_budget = budget or InterviewBudget(max_turns=10, max_minutes=30, token_budget=4000)

        escalation_owner = (
            completion_rubric.escalation_owner.strip()
            if completion_rubric and completion_rubric.escalation_owner
            else actor_ctx.actor_id
        )
        if not escalation_owner:
            raise InterviewPlanError("Người tiếp nhận xử lý leo thang (escalation_owner) không được để trống.")

        plan_rubric = CompletionRubric(
            required_aspects=completion_rubric.required_aspects if completion_rubric else ("threshold", "unit", "exceptions"),
            min_grounded_claims=completion_rubric.min_grounded_claims if completion_rubric else 1,
            allow_unknown=completion_rubric.allow_unknown if completion_rubric else True,
            stop_on_repeated_unknowns=completion_rubric.stop_on_repeated_unknowns if completion_rubric else 2,
            escalation_owner=escalation_owner,
        )

        seed_questions = generate_seed_questions(gap)
        now_iso = datetime.now(timezone.utc).isoformat()
        plan_id = f"PLAN-{gap.gap_id}-{int(datetime.now(timezone.utc).timestamp())}-{uuid4().hex[:8]}"

        plan = InterviewPlan(
            plan_id=plan_id,
            version=1,
            gap_ids=(gap.gap_id,),
            required_scope=gap.scope,
            eligible_expert_ids=(recorded_person,),
            seed_questions=seed_questions,
            budget=plan_budget,
            completion_rubric=plan_rubric,
            status=PLAN_STATUS_DRAFT,
            created_by=actor_ctx.actor_id,
            created_at=now_iso,
        )

        self.interview_repo.save_interview_plan(plan, f"PLAN-{plan.plan_id}-{plan.digest}")
        self._plan_cache[plan.plan_id] = plan
        return plan

    def get_interview_plan(self, plan_id: str) -> Optional[InterviewPlan]:
        cached = self._plan_cache.get(plan_id)
        if cached is not None:
            return cached
        persisted = self.interview_repo.get_interview_plan(plan_id)
        if persisted is not None:
            self._plan_cache[plan_id] = persisted
        return persisted

    def start_interview_session(
        self,
        plan_id: str,
        principal: VerifiedPrincipal,
        expert_id: str,
        idempotency_key: str,
    ) -> InterviewSession:
        """Start a new interview session binding plan, expert, and verified principal.

        Implements T032.
        """
        plan = self.get_interview_plan(plan_id)
        if plan is None:
            raise InterviewSessionError(f"Không tìm thấy kế hoạch phỏng vấn '{plan_id}'.")

        now_iso = datetime.now(timezone.utc).isoformat()
        session_id = f"SESS-{plan.plan_id}-{int(datetime.now(timezone.utc).timestamp())}-{uuid4().hex[:6]}"

        session = InterviewSession(
            session_id=session_id,
            plan_id=plan.plan_id,
            expert_id=expert_id,
            principal_subject_id=principal.subject,
            state=SESSION_STATE_ACTIVE,
            consent_state=CONSENT_GRANTED,
            checkpoint_seq=0,
            last_turn_digest="",
            started_at=now_iso,
            updated_at=now_iso,
        )

        self.interview_repo.save_session(session, idempotency_key)

        # Initial checkpoint
        checkpoint = InterviewCheckpoint(
            checkpoint_id=f"CHK-{session_id}-0",
            session_id=session_id,
            sequence=0,
            state=SESSION_STATE_ACTIVE,
            snapshot_json=json.dumps({"state": SESSION_STATE_ACTIVE, "seq": 0}),
            digest="initial_checkpoint_digest",
            created_at=now_iso,
        )
        self.interview_repo.save_checkpoint(checkpoint)
        return session

    def submit_interview_turn(
        self,
        session_id: str,
        answer_text: str,
        principal: VerifiedPrincipal,
        idempotency_key: str,
        *,
        question_override: Optional[str] = None,
        question_reason: str = "seed_question",
        answer_confidence: float = 1.0,
        supersedes_turn_id: Optional[str] = None,
    ) -> tuple[InterviewTurn, NextActionDecision]:
        """Submit an expert turn, recheck authorization, and compute next adaptive action.

        Implements T032, T034, T035.
        """
        session = self.interview_repo.get_session(session_id)
        if session is None:
            raise InterviewSessionError(f"Không tìm thấy phiên phỏng vấn '{session_id}'.")

        if session.state != SESSION_STATE_ACTIVE:
            raise InterviewSessionError(
                f"Không thể gửi câu trả lời khi phiên đang ở trạng thái '{session.state}'."
            )

        plan = self.get_interview_plan(session.plan_id)
        if plan is None:
            raise InterviewSessionError("Không tìm thấy kế hoạch liên kết của phiên.")

        # T035: Check special commands (pause / stop)
        clean_ans = answer_text.strip().lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        if clean_ans in ("pause", "tạm dừng"):
            paused_session = InterviewSession(
                session_id=session.session_id,
                plan_id=session.plan_id,
                expert_id=session.expert_id,
                principal_subject_id=session.principal_subject_id,
                state=SESSION_STATE_PAUSED,
                consent_state=session.consent_state,
                checkpoint_seq=session.checkpoint_seq + 1,
                last_turn_digest=session.last_turn_digest,
                started_at=session.started_at,
                updated_at=now_iso,
                stop_reason="expert_paused",
            )
            self.interview_repo.save_session(paused_session, f"IDEMP-PAUSE-{session.session_id}-{now_iso}")
            turn = InterviewTurn(
                turn_id=f"TURN-{session.session_id}-{session.checkpoint_seq + 1}",
                session_id=session.session_id,
                sequence=session.checkpoint_seq + 1,
                question_text=question_override or "Yêu cầu tạm dừng phiên",
                answer_text=answer_text,
                question_reason=question_reason,
                answer_state=ANSWER_STATE_SKIPPED,
                created_at=now_iso,
            )
            self.interview_repo.save_turn(turn, idempotency_key)
            return turn, NextActionDecision(action=ACTION_PAUSE, reason=REASON_EXPERT_PAUSE, question="Phiên đã được tạm dừng an toàn.")

        if clean_ans in ("stop", "dừng", "kết thúc"):
            stopped_session = InterviewSession(
                session_id=session.session_id,
                plan_id=session.plan_id,
                expert_id=session.expert_id,
                principal_subject_id=session.principal_subject_id,
                state=SESSION_STATE_STOPPED,
                consent_state=session.consent_state,
                checkpoint_seq=session.checkpoint_seq + 1,
                last_turn_digest=session.last_turn_digest,
                started_at=session.started_at,
                updated_at=now_iso,
                ended_at=now_iso,
                stop_reason="expert_stopped",
            )
            self.interview_repo.save_session(stopped_session, f"IDEMP-STOP-{session.session_id}-{now_iso}")
            turn = InterviewTurn(
                turn_id=f"TURN-{session.session_id}-{session.checkpoint_seq + 1}",
                session_id=session.session_id,
                sequence=session.checkpoint_seq + 1,
                question_text=question_override or "Yêu cầu kết thúc phiên",
                answer_text=answer_text,
                question_reason=question_reason,
                answer_state=ANSWER_STATE_SKIPPED,
                created_at=now_iso,
            )
            self.interview_repo.save_turn(turn, idempotency_key)
            return turn, NextActionDecision(action=ACTION_COMPLETE, reason=REASON_EXPERT_STOP, question="Phiên đã dừng theo yêu cầu của chuyên gia.")

        # Determine answer state
        if (
            clean_ans in ("unknown", "không rõ", "không biết", "chưa rõ", "chưa nắm rõ")
            or any(clean_ans.startswith(p) for p in ("không rõ", "chưa rõ", "vẫn không rõ", "tôi chưa rõ", "tôi không rõ", "không biết", "vẫn chưa rõ"))
        ):
            ans_state = ANSWER_STATE_UNKNOWN
        elif clean_ans in ("uncertain", "không chắc", "chưa chắc"):
            ans_state = ANSWER_STATE_UNCERTAIN
        elif clean_ans in ("skip", "bỏ qua"):
            ans_state = ANSWER_STATE_SKIPPED
        elif supersedes_turn_id:
            ans_state = ANSWER_STATE_CORRECTED
        else:
            ans_state = ANSWER_STATE_ANSWERED

        past_turns = self.interview_repo.list_turns(session_id)
        current_seq = len(past_turns) + 1

        # Enforce budget max_turns
        if current_seq > plan.budget.max_turns:
            raise InterviewSessionError("Đã đạt giới hạn số lượt phỏng vấn tối đa của ngân sách.")

        # Determine question text
        if question_override:
            q_text = question_override
        elif past_turns:
            q_text = f"Câu hỏi làm rõ lượt {current_seq}"
        elif plan.seed_questions:
            q_text = plan.seed_questions[0].text
        else:
            q_text = "Vui lòng cho biết chi tiết quy trình?"

        # Validate candidate question
        past_q_texts = [t.question_text for t in past_turns]
        validate_candidate_question(q_text, past_q_texts, len(past_turns), plan.budget.max_turns)

        turn = InterviewTurn(
            turn_id=f"TURN-{session_id}-{current_seq}",
            session_id=session_id,
            sequence=current_seq,
            question_text=q_text,
            answer_text=answer_text,
            question_reason=question_reason,
            answer_confidence=answer_confidence,
            answer_state=ans_state,
            created_at=now_iso,
            supersedes_turn_id=supersedes_turn_id,
        )

        self.interview_repo.save_turn(turn, idempotency_key)

        # Get gap for context
        gap = self.store.get_gap_candidate(plan.gap_ids[0])
        turns_payload = [
            {"sequence": t.sequence, "question_text": t.question_text, "answer_text": t.answer_text, "state": t.answer_state}
            for t in [*past_turns, turn]
        ]

        next_decision = propose_next_action(
            turns_history=turns_payload,
            budget=plan.budget,
            rubric=plan.completion_rubric,
            latest_answer=answer_text,
            gap=gap or KnowledgeGapCandidate("G", "C", plan.required_scope, "T", "D", "missing_threshold", ("DOC-1",)),
            gateway_client=self.gateway_client,
        )

        # Check if terminal
        new_state = session.state
        ended_at = None
        stop_reason = None
        if next_decision.action == ACTION_COMPLETE:
            new_state = SESSION_STATE_COMPLETED
            ended_at = now_iso
            stop_reason = "rubric_completed"
        elif next_decision.action == ACTION_ESCALATE:
            new_state = SESSION_STATE_STOPPED
            ended_at = now_iso
            stop_reason = "escalated_due_to_uncertainty"

        updated_session = InterviewSession(
            session_id=session.session_id,
            plan_id=session.plan_id,
            expert_id=session.expert_id,
            principal_subject_id=session.principal_subject_id,
            state=new_state,
            consent_state=session.consent_state,
            checkpoint_seq=current_seq,
            last_turn_digest=turn.payload_digest,
            started_at=session.started_at,
            updated_at=now_iso,
            ended_at=ended_at,
            stop_reason=stop_reason,
        )
        self.interview_repo.save_session(updated_session, f"IDEMP-SESS-{session_id}-{current_seq}")

        # Save checkpoint
        checkpoint = InterviewCheckpoint(
            checkpoint_id=f"CHK-{session_id}-{current_seq}",
            session_id=session_id,
            sequence=current_seq,
            state=new_state,
            snapshot_json=json.dumps({"seq": current_seq, "last_turn": turn.turn_id, "state": new_state}),
            digest=turn.payload_digest,
            created_at=now_iso,
        )
        self.interview_repo.save_checkpoint(checkpoint)

        return turn, next_decision

    def resume_interview_session(
        self,
        session_id: str,
        principal: VerifiedPrincipal,
    ) -> InterviewSession:
        """Resume a paused interview session."""
        session = self.interview_repo.get_session(session_id)
        if session is None:
            raise InterviewSessionError(f"Không tìm thấy phiên phỏng vấn '{session_id}'.")

        if session.state != SESSION_STATE_PAUSED:
            raise InterviewSessionError(
                f"Chỉ có thể tiếp tục lại phiên đang tạm dừng. Trạng thái hiện tại: '{session.state}'."
            )

        plan = self.get_interview_plan(session.plan_id)
        if plan is None:
            raise InterviewSessionError("Không tìm thấy kế hoạch của phiên.")

        now_iso = datetime.now(timezone.utc).isoformat()
        resumed_session = InterviewSession(
            session_id=session.session_id,
            plan_id=session.plan_id,
            expert_id=session.expert_id,
            principal_subject_id=session.principal_subject_id,
            state=SESSION_STATE_ACTIVE,
            consent_state=session.consent_state,
            checkpoint_seq=session.checkpoint_seq,
            last_turn_digest=session.last_turn_digest,
            started_at=session.started_at,
            updated_at=now_iso,
        )
        self.interview_repo.save_session(resumed_session, f"IDEMP-RESUME-{session_id}-{now_iso}")
        return resumed_session

    def create_controlled_artifact(
        self,
        artifact: ControlledKnowledgeArtifact,
        idempotency_key: str,
    ) -> ControlledKnowledgeArtifact:
        """Create and persist a candidate controlled knowledge artifact."""
        self.interview_repo.save_artifact(artifact, idempotency_key)
        return artifact

    def _draft_artifact_id(self, session_id: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id).strip("_")[:40]
        return f"ART-{safe or 'session'}"

    def create_draft_from_session(self, session_id: str) -> ControlledKnowledgeArtifact:
        """Build a user-facing draft from answered interview turns without exposing internal tokens."""
        session = self.interview_repo.get_session(session_id)
        if session is None:
            raise ControlledArtifactError("Không tìm thấy buổi hỏi đáp để tạo bản nháp.")
        artifact_id = self._draft_artifact_id(session_id)
        existing = self.interview_repo.get_artifact(artifact_id)
        if existing is not None:
            return existing
        turns = [
            turn
            for turn in self.interview_repo.list_turns(session_id)
            if turn.answer_text.strip() and turn.answer_state != ANSWER_STATE_SKIPPED
        ]
        if not turns:
            raise ControlledArtifactError("Chưa có câu trả lời để tạo bản nháp.")
        plan = self.get_interview_plan(session.plan_id)
        scope = plan.required_scope if plan else "chia_se_kinh_nghiem"
        title = "Kiến thức vừa ghi lại"
        if plan and plan.gap_ids:
            gap = self.store.get_gap_candidate(plan.gap_ids[0])
            if gap and gap.title.strip():
                title = gap.title.strip()
        claims = []
        for turn in turns:
            claim = extract_claim_from_turn(
                turn,
                session,
                scope,
                require_confirmed_tokens=False,
            )
            self.interview_repo.save_claim(claim, f"IDEMP-{claim.claim_id}")
            claims.append(claim)
        lines = [
            f"# {title}",
            "",
            "Đây là bản nháp, chưa phải tri thức chính thức.",
            "",
            f"Người tham gia: {session.expert_id}",
            "",
            "## Nội dung đã ghi lại",
        ]
        uncertain_notes: list[str] = []
        for turn in turns:
            lines.append(f"**Câu hỏi:** {turn.question_text}")
            lines.append(turn.answer_text.strip())
            if turn.answer_state == ANSWER_STATE_UNCERTAIN:
                lines.append("*Phần này chưa chắc chắn — hãy kiểm tra lại trước khi đưa vào thư viện.*")
                uncertain_notes.append(turn.answer_text.strip())
            elif turn.answer_state == ANSWER_STATE_UNKNOWN:
                lines.append("*Người tham gia chưa rõ phần này.*")
            lines.append("")
        if uncertain_notes:
            lines.append("## Điểm cần kiểm tra")
            for note in uncertain_notes:
                lines.append(f"- {note}")
            lines.append("")
        lines.extend(["## Nguồn", f"Buổi hỏi đáp với {session.expert_id}."])
        artifact = ControlledKnowledgeArtifact(
            artifact_id=artifact_id,
            artifact_type=ARTIFACT_TYPE_LESSON,
            title=title,
            scope=scope,
            version="1",
            content_markdown="\n".join(lines),
            claim_ids=tuple(claim.claim_id for claim in claims),
            claim_map={claim.claim_id: claim.statement for claim in claims},
            status=ARTIFACT_STATUS_CANDIDATE,
            created_by=session.expert_id,
        )
        self.interview_repo.save_artifact(artifact, f"IDEMP-{artifact_id}")
        return artifact

    def ensure_drafts_from_answered_sessions(self) -> list[ControlledKnowledgeArtifact]:
        """Create missing drafts for sessions that already have answers."""
        created: list[ControlledKnowledgeArtifact] = []
        for session in self.interview_repo.list_sessions():
            try:
                created.append(self.create_draft_from_session(session.session_id))
            except ControlledArtifactError:
                continue
        return created

    def submit_artifact_approval(
        self,
        approval_id: str,
        artifact_id: str,
        action: str,
        actor_id: str,
        expected_digest: str,
        reason: str,
        idempotency_key: str,
        *,
        machine_ref: Optional[str] = None,
        confidence: Optional[str] = None,
        checked_source_refs: Optional[Sequence[str]] = None,
        responsibility_acknowledged: Optional[bool] = None,
    ) -> ControlledKnowledgeArtifact:
        """Record a responsibility decision bound to the exact artifact version."""
        artifact = self.interview_repo.get_artifact(artifact_id)
        if artifact is None:
            raise ControlledArtifactError(f"Không tìm thấy tài liệu quy chuẩn '{artifact_id}'.")

        missing_responsibility = any(
            value is None
            for value in (machine_ref, confidence, checked_source_refs, responsibility_acknowledged)
        )
        # A decision is valid only for the exact content version the person reviewed.
        if expected_digest != artifact.digest:
            raise StaleArtifactDigestError(
                f"Mã kiểm tra tài liệu không khớp (kỳ vọng: {expected_digest[:8]}..., thực tế: {artifact.digest[:8]}...). Tài liệu có thể đã bị sửa đổi."
            )

        if missing_responsibility:
            raise ValueError("Quyết định phải có máy, độ tự tin, nguồn đã kiểm tra và xác nhận trách nhiệm.")

        # Conflicted source material still requires resolution before confirmation.
        if action == APPROVAL_ACTION_APPROVE:
            for claim_id in artifact.claim_ids:
                claim = self.interview_repo.get_claim(claim_id)
                if claim and claim.status == CLAIM_STATUS_CONFLICTED:
                    raise ConflictedClaimArtifactError(
                        f"Không thể phê duyệt tài liệu '{artifact_id}' vì phát biểu tri thức '{claim_id}' đang trong trạng thái xung đột chưa giải quyết."
                    )

        # Determine new status
        if action == APPROVAL_ACTION_APPROVE:
            new_status = ARTIFACT_STATUS_APPROVED
        elif action == APPROVAL_ACTION_REJECT:
            new_status = ARTIFACT_STATUS_REJECTED
        elif action == APPROVAL_ACTION_REQUEST_CHANGE:
            new_status = ARTIFACT_STATUS_CHANGES_REQUESTED
        elif action == APPROVAL_ACTION_REVOKE:
            new_status = ARTIFACT_STATUS_REVOKED
        else:
            raise ValueError(f"Hành động phê duyệt '{action}' không hợp lệ.")

        decision_kind = {
            APPROVAL_ACTION_APPROVE: DECISION_CONFIRM,
            APPROVAL_ACTION_REJECT: DECISION_REJECT,
            APPROVAL_ACTION_REQUEST_CHANGE: DECISION_REQUEST_CHANGE,
            APPROVAL_ACTION_REVOKE: DECISION_REVOKE,
        }[action]
        decision = DecisionRecord(
            decision_id=approval_id,
            subject_id=artifact_id,
            subject_digest=artifact.digest,
            subject_version=artifact.version,
            decision=decision_kind,
            recorded_name=actor_id,
            machine_ref=machine_ref or "",
            confidence=confidence or "",
            rationale=reason,
            checked_source_refs=tuple(checked_source_refs or ()),
            responsibility_acknowledged=bool(responsibility_acknowledged),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Update artifact status
        updated_artifact = ControlledKnowledgeArtifact(
            artifact_id=artifact.artifact_id,
            artifact_type=artifact.artifact_type,
            title=artifact.title,
            scope=artifact.scope,
            version=artifact.version,
            content_markdown=artifact.content_markdown,
            claim_ids=artifact.claim_ids,
            claim_map=artifact.claim_map,
            status=new_status,
            created_by=artifact.created_by,
            created_at=artifact.created_at,
            approvals=artifact.approvals,
            decisions=tuple(list(artifact.decisions) + [decision]),
        )
        self.interview_repo.save_decision_and_artifact(decision, updated_artifact, idempotency_key)
        persisted_artifact = self.interview_repo.get_artifact(artifact_id)
        if persisted_artifact is None:
            raise ControlledArtifactError(f"Không thể đọc lại tài liệu quy chuẩn '{artifact_id}' sau khi lưu quyết định.")
        return persisted_artifact
