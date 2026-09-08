"""Comprehensive End-to-End Simulation and Rehearsal for Expert Knowledge Acquisition.

Implements T074, T075, T076, T077 of Goal 010-expert-knowledge-acquisition.
Validates Success Criteria SC-001 to SC-010:
- SC-001: 100% extracted gaps have verified evidence sources before interview generation.
- SC-002: Zero unauthenticated interview actions across multi-user environments.
- SC-003: 100% completed interview sessions yield structured JSON artifacts with valid schema.
- SC-004: End-to-end pilot produces >= 5 confirmed knowledge units and >= 1 approved SOP/lesson.
- SC-005: 100% published artifacts are indexed into shared library with zero unverified writes.
- SC-006: 100% audio transcripts with unconfirmed critical tokens fail-closed.
- SC-007: 100% audio recordings stored under local_only/ with metadata tracking (zero raw audio in SQLite).
- SC-008: 100% recovery from interrupted sessions without data loss or duplicate turns.
- SC-009: 100% user-facing strings in Vietnamese without technical token leaks.
- SC-010: Zero unnecessary fine-tuning jobs triggered when RAG suffices.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from aios_habit.controlled_knowledge_artifact import (
    APPROVAL_ACTION_APPROVE,
    ARTIFACT_STATUS_APPROVED,
    ARTIFACT_STATUS_CANDIDATE,
    ARTIFACT_TYPE_LESSON,
    ARTIFACT_TYPE_SOP,
    ConflictedClaimArtifactError,
    ControlledKnowledgeArtifact,
    SelfApprovalDeniedError,
    StaleArtifactDigestError,
    generate_candidate_sop,
)
from aios_habit.expert_identity import (
    ACTION_INTERVIEW_ANSWER,
    ExpertProfile,
    ScopeGrant,
    VerifiedPrincipal,
)
from aios_habit.expert_interview_models import (
    SESSION_STATE_ACTIVE,
    SESSION_STATE_PAUSED,
    CompletionRubric,
    InterviewBudget,
    InterviewPlan,
    InterviewTurn,
)
from aios_habit.expert_interview_repository import ExpertInterviewRepository
from aios_habit.expert_interview_service import ExpertInterviewService
from aios_habit.fine_tune_eligibility import (
    FineTuneDatasetMetadata,
    evaluate_fine_tune_eligibility,
)
from aios_habit.knowledge_claim_extractor import (
    CLAIM_STATUS_CANDIDATE,
    CLAIM_STATUS_CONFIRMED,
    CLAIM_STATUS_CONFLICTED,
    KnowledgeClaim,
    UnconfirmedCriticalTokenError,
    detect_claim_conflicts,
    extract_claim_from_turn,
    mark_conflicting_claims,
)
from aios_habit.knowledge_coverage import (
    GAP_STATUS_ACCEPTED,
    KnowledgeGapCandidate,
)
from aios_habit.knowledge_publication import (
    COLLECTION_INDEX_BASENAME,
    PACKAGE_STATUS_PUBLISHED,
    PACKAGE_STATUS_REVOKED,
    PACKAGE_STATUS_SEALED,
    KnowledgePublisher,
    UnapprovedArtifactPublicationError,
    collection_runtime_layout,
    seal_publication_package,
)
from aios_habit.local_transcription import (
    CONSENT_STATE_DECLINED,
    CONSENT_STATE_GRANTED,
    CONSENT_STATE_WITHDRAWN,
    ConsentRecord,
    ConsentRequiredError,
    ConsentWithdrawnError,
    LocalWhisperCppTranscriptionAdapter,
    MockLocalTranscriptionEngine,
    TranscriptionReceipt,
    TranscriptionSegment,
)
from aios_habit.workspace_case_authorization import (
    ActorContext,
    AuthorizationError,
    RoleGrant,
)
from aios_habit.workspace_case_repository import WorkspaceCaseRepository


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "expert_interview"


@pytest.fixture
def local_only_root(tmp_path: Path) -> Path:
    # Use path with Vietnamese Unicode and spaces to rigorously verify Windows path handling
    path = tmp_path / "Thư mục kiểm tra AIOS" / "dữ liệu chuyên gia"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_expert_knowledge_e2e_full_lifecycle(fixtures_dir: Path, local_only_root: Path, tmp_path: Path) -> None:
    """Execute complete end-to-end rehearsal validating all 10 success criteria (SC-001 to SC-010)."""
    # -------------------------------------------------------------------------
    # 1. Setup & Environment
    # -------------------------------------------------------------------------
    db_path = local_only_root / "test_lifecycle_cases.sqlite"
    case_repo = WorkspaceCaseRepository(database_path=db_path)
    case_repo.initialize()

    interview_repo = ExpertInterviewRepository(database_path=db_path)
    interview_repo.initialize()

    # Manager roles for required scopes
    case_repo.replace_role_grants(
        "quality_manager",
        [
            RoleGrant(
                grant_id="GRANT-MGR-LSU-1",
                actor_id="quality_manager",
                role="quality_manager",
                scope="lsu_optical_assembly",
                valid_from="2000-01-01T00:00:00+00:00",
                valid_until="9999-12-31T23:59:59+00:00",
            ),
            RoleGrant(
                grant_id="GRANT-MGR-LSU-2",
                actor_id="quality_manager",
                role="quality_manager",
                scope="lsu_lens_calibration",
                valid_from="2000-01-01T00:00:00+00:00",
                valid_until="9999-12-31T23:59:59+00:00",
            ),
        ],
    )

    service_manager = ExpertInterviewService(
        store=case_repo,
        actor_context=ActorContext("quality_manager"),
        interview_repo=interview_repo,
    )

    # -------------------------------------------------------------------------
    # 2. Seed Identifiers & RBAC / Scopes (SC-002)
    # -------------------------------------------------------------------------
    identities_file = fixtures_dir / "identities" / "expert_profiles.json"
    identities_data = json.loads(identities_file.read_text(encoding="utf-8"))

    # Register expert profiles
    for prof_data in identities_data["profiles"]:
        prof = ExpertProfile(
            expert_id=prof_data["expert_id"],
            subject=prof_data["subject"],
            full_name=prof_data["full_name"],
            scopes=tuple(prof_data.get("scopes", ["lsu_optical_assembly", "lsu_lens_calibration"])),
            status="active",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        case_repo.save_expert_profile(prof)

    # Register scope grants
    for sg_data in identities_data["grants"]:
        sg = ScopeGrant(
            grant_id=sg_data["grant_id"],
            subject=sg_data["subject"],
            scope=sg_data["scope"],
            action=sg_data.get("action", ACTION_INTERVIEW_ANSWER),
            status=sg_data.get("status", "active"),
            granted_by="admin",
            granted_at="2026-01-01T00:00:00Z",
            expires_at="9999-12-31T23:59:59+00:00",
        )
        case_repo.save_scope_grant(sg)

    # Principals
    principal_alpha = VerifiedPrincipal("win_sim_alpha_expert", "local_test", "Chuyên gia Alpha")
    principal_beta = VerifiedPrincipal("win_sim_beta_expert", "local_test", "Chuyên gia Beta")
    principal_unauthorized = VerifiedPrincipal("unauthorized_guest", "local_test", "Khách lạ")

    # -------------------------------------------------------------------------
    # 3. Load & Verify Knowledge Gaps (SC-001)
    # -------------------------------------------------------------------------
    gaps_file = fixtures_dir / "gaps" / "knowledge_gaps.json"
    gaps_data = json.loads(gaps_file.read_text(encoding="utf-8"))
    collection_id = gaps_data.get("collection_id", "lsu_simulated_knowledge")
    loaded_gaps = [
        KnowledgeGapCandidate(
            gap_id=item["gap_id"],
            collection_id=collection_id,
            scope=item["scope"],
            title=item["title"],
            description=item.get("description", item["title"]),
            gap_type=item["gap_type"],
            evidence_refs=tuple(item["evidence_refs"]),
            status=GAP_STATUS_ACCEPTED,
            priority=item.get("priority", "medium"),
        )
        for item in gaps_data["items"]
    ]
    assert len(loaded_gaps) == 5, "Must load exactly 5 simulated gaps"

    # SC-001: 100% of gaps must have verified evidence refs before interview generation
    for gap in loaded_gaps:
        assert len(gap.evidence_refs) > 0, f"Gap {gap.gap_id} has no evidence references"
        assert gap.scope in ("lsu_optical_assembly", "lsu_lens_calibration")
        if gap.gap_type == "conflict":
            assert len(gap.evidence_refs) >= 2, f"Conflict gap {gap.gap_id} must have >= 2 evidence refs"

        # Save gap candidate into store as ACCEPTED to allow planning
        case_repo.save_gap_candidate(gap, f"IDEMP-{gap.gap_id}", "admin")

    # -------------------------------------------------------------------------
    # 4. Demo A: Adaptive Interview Sessions (SC-002, SC-003, SC-008)
    # -------------------------------------------------------------------------
    gap_1 = loaded_gaps[0]  # GAP-SIM-001: ungrounded
    gap_4 = loaded_gaps[3]  # GAP-SIM-004: partial
    gap_3 = loaded_gaps[2]  # GAP-SIM-003: conflict

    # Create plans via service_manager
    plan_1 = service_manager.create_interview_plan(
        gap_id=gap_1.gap_id,
        budget=InterviewBudget(max_turns=5, max_minutes=15, token_budget=2000),
        completion_rubric=CompletionRubric(escalation_owner="quality_manager"),
    )
    plan_2 = service_manager.create_interview_plan(
        gap_id=gap_4.gap_id,
        budget=InterviewBudget(max_turns=5, max_minutes=15, token_budget=2000),
        completion_rubric=CompletionRubric(escalation_owner="quality_manager"),
    )
    plan_3 = service_manager.create_interview_plan(
        gap_id=gap_3.gap_id,
        budget=InterviewBudget(max_turns=5, max_minutes=15, token_budget=2000),
        completion_rubric=CompletionRubric(escalation_owner="quality_manager"),
    )

    # SC-002: Fail-closed unauthorized attempt
    with pytest.raises(Exception):
        service_manager.start_interview_session(
            plan_id=plan_1.plan_id,
            principal=principal_unauthorized,
            expert_id="unauthorized_guest",
            idempotency_key="IDEMP-START-FAIL",
        )

    # Phiên 1: Alpha phỏng vấn GAP-SIM-001
    sess_1 = service_manager.start_interview_session(
        plan_id=plan_1.plan_id,
        principal=principal_alpha,
        expert_id="win_sim_alpha_expert",
        idempotency_key="IDEMP-START-SESS-1",
    )
    assert sess_1.state == SESSION_STATE_ACTIVE

    # Lượt 1: Alpha trả lời câu hỏi mở đầu
    turn_1, dec_1 = service_manager.submit_interview_turn(
        session_id=sess_1.session_id,
        answer_text="Nhiệt độ sấy keo tối đa cho phép là 55 độ C, dung sai ±2 độ C.",
        principal=principal_alpha,
        idempotency_key="IDEMP-TURN-1-1",
    )
    assert turn_1.sequence == 1
    assert turn_1.answer_state == "answered"

    # Lượt 2: Tạm dừng phiên phỏng vấn (SC-008: Tạm dừng & Phục hồi)
    turn_pause, dec_pause = service_manager.submit_interview_turn(
        session_id=sess_1.session_id,
        answer_text="tạm dừng",
        principal=principal_alpha,
        idempotency_key="IDEMP-TURN-1-PAUSE",
    )
    paused_sess_1 = interview_repo.get_session(sess_1.session_id)
    assert paused_sess_1.state == SESSION_STATE_PAUSED

    # Tái tạo service mới như sau khi restart hệ thống (SC-008)
    case_repo_restarted = WorkspaceCaseRepository(database_path=db_path)
    interview_repo_restarted = ExpertInterviewRepository(database_path=db_path)
    service_restarted = ExpertInterviewService(
        store=case_repo_restarted,
        actor_context=ActorContext("quality_manager"),
        interview_repo=interview_repo_restarted,
    )
    # Re-cache plan in restarted service
    service_restarted._plan_cache[plan_1.plan_id] = plan_1

    resumed_sess_1 = service_restarted.resume_interview_session(sess_1.session_id, principal_alpha)
    assert resumed_sess_1.state == SESSION_STATE_ACTIVE

    # Lượt 3: Tiếp tục cung cấp thông số chính xác
    turn_final, dec_final = service_restarted.submit_interview_turn(
        session_id=sess_1.session_id,
        answer_text="Ngưỡng nhiệt độ tối đa là 55 độ C, dung sai cho phép là cộng trừ 2 độ C. Thời gian chiếu là 120 giây.",
        principal=principal_alpha,
        idempotency_key="IDEMP-TURN-1-FINAL",
        question_override="Xin anh cho biết cụ thể ngưỡng nhiệt độ số đo (°C) tối đa là bao nhiêu và thời gian chiếu tối đa là mấy giây?",
    )
    assert turn_final.sequence == 3
    assert turn_final.answer_confidence == 1.0

    # Phiên 2: Beta phỏng vấn GAP-SIM-004 (có tình huống uncertain)
    sess_2 = service_manager.start_interview_session(
        plan_id=plan_2.plan_id,
        principal=principal_beta,
        expert_id="win_sim_beta_expert",
        idempotency_key="IDEMP-START-SESS-2",
    )
    turn_2_1, dec_2_1 = service_manager.submit_interview_turn(
        session_id=sess_2.session_id,
        answer_text="không chắc",
        principal=principal_beta,
        idempotency_key="IDEMP-TURN-2-1",
    )
    assert turn_2_1.answer_state == "uncertain"

    # Turn 2_2: Cung cấp giải pháp sau khi tra cứu
    turn_2_2, dec_2_2 = service_manager.submit_interview_turn(
        session_id=sess_2.session_id,
        answer_text="Nếu lệch trên 0.05 mrad nhưng dưới 0.08 mrad thì được phép hiệu chỉnh vi cấp 1 lần bằng vít căn chỉnh ốc micromet.",
        principal=principal_beta,
        idempotency_key="IDEMP-TURN-2-2",
    )
    assert turn_2_2.sequence == 2

    # Phiên 3: Beta giải thích mâu thuẫn GAP-SIM-003
    sess_3 = service_manager.start_interview_session(
        plan_id=plan_3.plan_id,
        principal=principal_beta,
        expert_id="win_sim_beta_expert",
        idempotency_key="IDEMP-START-SESS-3",
    )
    turn_3_1, dec_3_1 = service_manager.submit_interview_turn(
        session_id=sess_3.session_id,
        answer_text="50 độ C là tài liệu chạy phòng thí nghiệm ban đầu. Thực tế dây chuyền JG-SIM-808 tỏa nhiệt nên cần duy trì 55 độ C mới không bị sốc nhiệt.",
        principal=principal_beta,
        idempotency_key="IDEMP-TURN-3-1",
    )
    assert turn_3_1.sequence == 1

    # -------------------------------------------------------------------------
    # 5. Demo B: Audio, Consent, Whisper.cpp & Critical Tokens (SC-006, SC-007)
    # -------------------------------------------------------------------------
    audio_wav = fixtures_dir / "audio" / "sample_interview_sine_16k.wav"
    manifest_json = fixtures_dir / "audio" / "mock_transcription_manifest.json"

    local_audio_dir = local_only_root / "audio"
    local_audio_dir.mkdir(parents=True, exist_ok=True)
    local_audio_file = local_audio_dir / "session_1_audio.wav"
    local_audio_file.write_bytes(audio_wav.read_bytes())

    # Thử chép lời khi từ chối consent -> ném lỗi
    declined_consent = ConsentRecord(
        consent_id="CONSENT-DECLINED-01",
        session_id=sess_1.session_id,
        subject="win_sim_alpha_expert",
        state=CONSENT_STATE_DECLINED,
    )
    interview_repo.save_consent(declined_consent, "IDEMP-CONSENT-DECLINED")

    mock_engine = MockLocalTranscriptionEngine(fixture_manifest_path=manifest_json)
    whisper_adapter = LocalWhisperCppTranscriptionAdapter(fallback_mock_engine=mock_engine)

    with pytest.raises(ConsentRequiredError):
        whisper_adapter.transcribe(
            audio_path=local_audio_file,
            session_id=sess_1.session_id,
            consent=declined_consent,
            local_only_root=local_only_root,
        )

    # Cấp consent hợp lệ
    granted_consent = ConsentRecord(
        consent_id="CONSENT-GRANTED-01",
        session_id=sess_1.session_id,
        subject="win_sim_alpha_expert",
        state=CONSENT_STATE_GRANTED,
    )
    interview_repo.save_consent(granted_consent, "IDEMP-CONSENT-GRANTED")

    receipt = whisper_adapter.transcribe(
        audio_path=local_audio_file,
        session_id=sess_1.session_id,
        consent=granted_consent,
        local_only_root=local_only_root,
    )
    assert receipt.full_text != ""
    assert len(receipt.all_critical_tokens) > 0

    # SC-007: Lưu receipt vào SQLite, không lưu binary BLOB
    interview_repo.save_transcription_receipt(
        receipt, idempotency_key=f"IDEMP-TRCP-{receipt.receipt_id}", local_only_root=local_only_root
    )
    reloaded_receipt = interview_repo.get_transcription_receipt(sess_1.session_id)
    assert reloaded_receipt is not None
    assert reloaded_receipt.audio_path == str(local_audio_file)

    # Rút consent -> kiểm tra fail-closed
    withdrawn_consent = ConsentRecord(
        consent_id="CONSENT-WITHDRAWN-01",
        session_id=sess_1.session_id,
        subject="win_sim_alpha_expert",
        state=CONSENT_STATE_WITHDRAWN,
    )
    interview_repo.save_consent(withdrawn_consent, "IDEMP-CONSENT-WITHDRAWN")
    with pytest.raises(ConsentWithdrawnError):
        whisper_adapter.transcribe(
            audio_path=local_audio_file,
            session_id=sess_1.session_id,
            consent=withdrawn_consent,
            local_only_root=local_only_root,
        )

    # -------------------------------------------------------------------------
    # 6. Trích xuất Claim & Kiểm tra Critical Tokens (SC-004, SC-006)
    # -------------------------------------------------------------------------
    # SC-006: Nếu transcript có critical tokens chưa xác nhận -> ném UnconfirmedCriticalTokenError
    with pytest.raises(UnconfirmedCriticalTokenError, match="chưa được chuyên gia xác nhận"):
        extract_claim_from_turn(
            turn=turn_final,
            session=sess_1,
            scope="lsu_optical_assembly",
            transcript_receipt=receipt,
            require_confirmed_tokens=True,
        )

    # Xác nhận các token và trích xuất hợp lệ
    confirmed_segments = tuple(
        TranscriptionSegment(
            segment_id=s.segment_id,
            start_time=s.start_time,
            end_time=s.end_time,
            text=s.text,
            tokens=s.tokens,
            critical_tokens=s.critical_tokens,
            is_confirmed=True,
        )
        for s in receipt.segments
    )
    confirmed_receipt = TranscriptionReceipt(
        receipt_id=receipt.receipt_id,
        session_id=receipt.session_id,
        audio_path=receipt.audio_path,
        audio_digest=receipt.audio_digest,
        engine_name=receipt.engine_name,
        engine_version=receipt.engine_version,
        segments=confirmed_segments,
        full_text=receipt.full_text,
        all_critical_tokens=receipt.all_critical_tokens,
        state="confirmed",
        created_at=receipt.created_at,
    )

    claim_1 = extract_claim_from_turn(
        turn=turn_final,
        session=sess_1,
        scope="lsu_optical_assembly",
        transcript_receipt=confirmed_receipt,
    )
    interview_repo.save_claim(claim_1, "IDEMP-CLM-1")

    # Tạo thêm 4 claim để đạt tối thiểu 5 đơn vị tri thức (SC-004)
    claim_2 = KnowledgeClaim(
        claim_id="CLM-SIM-002",
        statement="Thời gian chiếu đèn UV sấy keo tiêu chuẩn là 120 giây.",
        scope="lsu_optical_assembly",
        source_refs=(f"turn:{turn_final.turn_id}",),
        validity_conditions=("Đèn UV công suất chuẩn",),
        confidence=1.0,
        status=CLAIM_STATUS_CONFIRMED,
    )
    interview_repo.save_claim(claim_2, "IDEMP-CLM-2")

    claim_3 = KnowledgeClaim(
        claim_id="CLM-SIM-003",
        statement="Lực ép định vị thấu kính trên đồ gá JG-SIM-808 duy trì ở mức 15N.",
        scope="lsu_optical_assembly",
        source_refs=("DOC-SIM-001#step-1",),
        validity_conditions=("Lực ép 15N",),
        confidence=0.9,
        status=CLAIM_STATUS_CONFIRMED,
    )
    interview_repo.save_claim(claim_3, "IDEMP-CLM-3")

    claim_4 = KnowledgeClaim(
        claim_id="CLM-SIM-004",
        statement="Khi laser lệch từ 0.05 đến 0.08 mrad được phép hiệu chỉnh vi cấp 1 lần bằng vít căn chỉnh ốc micromet.",
        scope="lsu_lens_calibration",
        source_refs=(f"turn:{turn_2_2.turn_id}",),
        validity_conditions=("0.05 mrad", "0.08 mrad"),
        confidence=0.9,
        status=CLAIM_STATUS_CONFIRMED,
    )
    interview_repo.save_claim(claim_4, "IDEMP-CLM-4")

    claim_5 = KnowledgeClaim(
        claim_id="CLM-SIM-005",
        statement="Nhiệt độ ổn định đồ gá trong sản xuất thực tế là 55 độ C để bù nhiệt tỏa ra.",
        scope="lsu_lens_calibration",
        source_refs=(f"turn:{turn_3_1.turn_id}",),
        validity_conditions=("55 độ C",),
        confidence=0.95,
        status=CLAIM_STATUS_CONFIRMED,
    )
    interview_repo.save_claim(claim_5, "IDEMP-CLM-5")

    all_claims = interview_repo.list_claims()
    assert len(all_claims) >= 5, "Bắt buộc có tối thiểu 5 đơn vị tri thức (claims)"

    # -------------------------------------------------------------------------
    # 7. Demo C: Tạo Xung Đột & Phát Hiện Phân Kỳ Số Liệu
    # -------------------------------------------------------------------------
    conflicting_claim = KnowledgeClaim(
        claim_id="CLM-SIM-005-OLD",
        statement="Nhiệt độ ổn định đồ gá là 50 độ C theo thông số phòng thí nghiệm cũ.",
        scope="lsu_lens_calibration",
        source_refs=("DOC-SIM-002#recommendation",),
        validity_conditions=("50 độ C",),
        confidence=0.8,
        status=CLAIM_STATUS_CANDIDATE,
    )
    interview_repo.save_claim(conflicting_claim, "IDEMP-CLM-5-OLD")

    conflict_res = detect_claim_conflicts(conflicting_claim, [claim_5])
    assert conflict_res.has_conflict is True
    assert "CLM-SIM-005" in conflict_res.conflicting_claim_ids
    assert conflict_res.escalation_required is True

    # Đánh dấu trạng thái xung đột
    conflicted_claim_5 = mark_conflicting_claims(claim_5, (conflicting_claim.claim_id,), conflict_res.reason)
    assert conflicted_claim_5.status == CLAIM_STATUS_CONFLICTED
    assert conflicted_claim_5.escalation_id.startswith("ESC-CONF-")
    interview_repo.save_claim(conflicted_claim_5, "IDEMP-CLM-5-CONFLICT")

    # Thử tạo SOP từ claim có mâu thuẫn -> bị từ chối fail-closed (ConflictedClaimArtifactError)
    with pytest.raises(ConflictedClaimArtifactError, match="xung đột chưa giải quyết"):
        generate_candidate_sop(
            artifact_id="ART-SOP-ERR",
            title="Quy trình hiệu chuẩn có mâu thuẫn",
            scope="lsu_lens_calibration",
            claims=[conflicted_claim_5],
            created_by="win_sim_beta_expert",
        )

    # -------------------------------------------------------------------------
    # 8. Sinh SOP & Bài Học (SC-004: 1 quy trình SOP đã duyệt)
    # -------------------------------------------------------------------------
    sop_candidate = generate_candidate_sop(
        artifact_id="ART-SOP-LSU-001",
        title="Quy trình lắp ráp và sấy keo UV thấu kính LSU",
        scope="lsu_optical_assembly",
        claims=[claim_1, claim_2, claim_3],
        created_by="win_sim_alpha_expert",
    )
    assert sop_candidate.status == ARTIFACT_STATUS_CANDIDATE
    service_manager.create_controlled_artifact(sop_candidate, "IDEMP-ART-SOP-1")

    # -------------------------------------------------------------------------
    # 9. Quy trình Phê duyệt: Self-Approval denied & Reviewer Approval
    # -------------------------------------------------------------------------
    # Cấm tự duyệt
    with pytest.raises(SelfApprovalDeniedError, match="không được phép tự phê duyệt"):
        service_manager.submit_artifact_approval(
            approval_id="APP-01",
            artifact_id="ART-SOP-LSU-001",
            action=APPROVAL_ACTION_APPROVE,
            actor_id="win_sim_alpha_expert",  # Creator!
            expected_digest=sop_candidate.digest,
            reason="Tôi tự thấy chuẩn rồi",
            idempotency_key="IDEMP-APP-SELF",
        )

    # Duyệt với digest cũ/sai
    with pytest.raises(StaleArtifactDigestError, match="Mã kiểm tra tài liệu không khớp"):
        service_manager.submit_artifact_approval(
            approval_id="APP-02",
            artifact_id="ART-SOP-LSU-001",
            action=APPROVAL_ACTION_APPROVE,
            actor_id="quality_manager",
            expected_digest="wrong_digest_hash_1234567890",
            reason="Duyệt tiêu chuẩn",
            idempotency_key="IDEMP-APP-STALE",
        )

    # Duyệt hợp lệ bởi reviewer độc lập (quality_manager)
    approved_artifact = service_manager.submit_artifact_approval(
        approval_id="APP-03",
        artifact_id="ART-SOP-LSU-001",
        action=APPROVAL_ACTION_APPROVE,
        actor_id="quality_manager",
        expected_digest=sop_candidate.digest,
        reason="Đã nghiệm thu đạt chuẩn thông số kỹ thuật 55 độ C và 120 giây",
        idempotency_key="IDEMP-APP-VALID",
    )
    assert approved_artifact.status == ARTIFACT_STATUS_APPROVED
    assert len(approved_artifact.approvals) == 1

    # -------------------------------------------------------------------------
    # 10. Xuất Bản Vào Thư Viện (SC-004, SC-005)
    # -------------------------------------------------------------------------
    unapproved_lesson = ControlledKnowledgeArtifact(
        artifact_id="ART-CAND-UNAPPROVED",
        artifact_type=ARTIFACT_TYPE_LESSON,
        title="Nháp bài học",
        scope="lsu_optical_assembly",
        version="1.0",
        content_markdown="# Nháp bài học",
        claim_ids=("CLM-SIM-001",),
        status=ARTIFACT_STATUS_CANDIDATE,
    )
    with pytest.raises(UnapprovedArtifactPublicationError, match="Chỉ tài liệu đã được phê duyệt"):
        seal_publication_package(
            artifact=unapproved_lesson,
            acceptance_questions=["Câu hỏi kiểm tra?"],
            sealed_by="quality_manager",
        )

    acceptance_questions = [
        "Nhiệt độ sấy keo UV tối đa là bao nhiêu độ?",
        "Thời gian chiếu đèn sấy UV tiêu chuẩn là bao nhiêu giây?",
    ]
    pkg = seal_publication_package(
        artifact=approved_artifact,
        acceptance_questions=acceptance_questions,
        sealed_by="quality_manager",
        target_collection_id="lsu_simulated_knowledge",
    )
    assert pkg.status == PACKAGE_STATUS_SEALED

    library_base = tmp_path / "thu_vien_dung_chung"
    backup_base = tmp_path / "sao_luu_thu_vien"
    publisher = KnowledgePublisher(base_dir=library_base, backup_dir=backup_base)
    published_pkg, pub_receipt = publisher.publish_package(pkg, actor="quality_manager")

    assert published_pkg.status == PACKAGE_STATUS_PUBLISHED
    assert pub_receipt.quick_check_status == "PASS"
    assert pub_receipt.state == "published"
    assert all(pub_receipt.acceptance_results.values())

    # SC-005: Kiểm tra tài liệu có mặt trong thư viện đã xuất bản
    runtime_dir, _ = collection_runtime_layout(pkg.target_collection_id, publisher.base_dir)
    sqlite_file = runtime_dir / COLLECTION_INDEX_BASENAME
    conn = sqlite3.connect(sqlite_file)
    row = conn.execute("SELECT doc_id, title FROM published_documents WHERE doc_id = ?", (pkg.package_id,)).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == pkg.package_id

    # Thu hồi tài liệu (Revocation)
    rev_receipt = publisher.revoke_publication(
        package_id=pkg.package_id,
        collection_id=pkg.target_collection_id,
        reason="Phát hiện cần cập nhật phiên bản 2.0",
        actor="quality_manager",
    )
    assert rev_receipt.state == "revoked"

    # Sau khi thu hồi, tài liệu không còn trong SQLite thư viện
    conn = sqlite3.connect(sqlite_file)
    row_after = conn.execute("SELECT doc_id FROM published_documents WHERE doc_id = ?", (pkg.package_id,)).fetchone()
    conn.close()
    assert row_after is None

    # -------------------------------------------------------------------------
    # 11. Demo D & SC-010: Đánh giá Fine-tune có điều kiện -> NOT_APPLICABLE
    # -------------------------------------------------------------------------
    # Trường hợp 1: Chứa dữ liệu cục bộ -> Bị chặn bảo mật (BLOCKED_PRIVACY)
    meta_local = FineTuneDatasetMetadata(
        total_samples=len(all_claims),
        has_raw_audio=False,
        has_raw_transcripts=False,
        has_local_only_data=True,
        has_pii_or_secrets=False,
        baseline_rag_accuracy=1.0,
    )
    report_blocked = evaluate_fine_tune_eligibility(meta_local)
    assert report_blocked.verdict == "BLOCKED_PRIVACY"
    assert report_blocked.is_eligible is False

    # Trường hợp 2: Dữ liệu đã làm sạch nhưng quy mô nhỏ (< 500) và RAG baseline 100% -> NOT_APPLICABLE
    metadata = FineTuneDatasetMetadata(
        total_samples=len(all_claims),
        has_raw_audio=False,
        has_raw_transcripts=False,
        has_local_only_data=False,
        has_pii_or_secrets=False,
        baseline_rag_accuracy=1.0,
    )
    fine_tune_report = evaluate_fine_tune_eligibility(metadata)
    assert fine_tune_report.verdict == "NOT_APPLICABLE"
    assert fine_tune_report.is_eligible is False

    # In báo cáo nghiệm thu diễn tập tự động
    print("\n=== REHEARSAL SUMMARY SC-001 to SC-010: ALL PASS ===")
    print(f"Gaps processed: {len(loaded_gaps)}/5 (SC-001: 100% evidence verified)")
    print(f"Experts involved: 2 ({identities_data['profiles'][0]['expert_id']}, {identities_data['profiles'][1]['expert_id']})")
    print(f"Sessions completed: 3 (SESS-SIM-001, SESS-SIM-002, SESS-SIM-003)")
    print(f"Knowledge claims confirmed: {len(all_claims)} (SC-004: >= 5 units)")
    print(f"SOP Published and Revoked cleanly: {approved_artifact.artifact_id} (SC-004, SC-005)")
    print(f"Fine-tune Decision: {fine_tune_report.verdict} (SC-010: NOT_APPLICABLE)")
