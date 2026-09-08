"""Comprehensive tests for Knowledge Claims extraction, provenance, conflicts, and persistence.

Implements T053 of Goal 010-expert-knowledge-acquisition.
"""
from __future__ import annotations

import pytest
from pathlib import Path
import tempfile

from aios_habit.expert_interview_models import (
    CONSENT_GRANTED,
    SESSION_STATE_ACTIVE,
    InterviewSession,
    InterviewTurn,
)
from aios_habit.expert_interview_repository import ExpertInterviewRepository
from aios_habit.knowledge_claim_extractor import (
    CLAIM_STATUS_CANDIDATE,
    CLAIM_STATUS_CONFIRMED,
    CLAIM_STATUS_CONFLICTED,
    CLAIM_STATUS_REJECTED,
    ConflictDetectionResult,
    KnowledgeClaim,
    KnowledgeClaimError,
    StaleSourceProvenanceError,
    UnconfirmedCriticalTokenError,
    UnsupportedClaimError,
    detect_claim_conflicts,
    extract_claim_from_turn,
    mark_conflicting_claims,
)
from aios_habit.local_transcription import TranscriptionReceipt, TranscriptionSegment


def make_test_session() -> InterviewSession:
    return InterviewSession(
        session_id="ses_test_01",
        plan_id="plan_01",
        expert_id="exp_01",
        principal_subject_id="sub_01",
        state=SESSION_STATE_ACTIVE,
        consent_state=CONSENT_GRANTED,
        checkpoint_seq=1,
        last_turn_digest="d1",
        started_at="2026-09-08T00:00:00Z",
        updated_at="2026-09-08T00:05:00Z",
    )


def test_unsupported_claim_rejected():
    """Test invariant: Claims lacking verified support or empty statement are rejected."""
    with pytest.raises(UnsupportedClaimError):
        KnowledgeClaim(
            claim_id="CLM-001",
            statement="Cần chỉnh áp lực về 2.5 bar.",
            scope="ep_khuon",
            source_refs=(),
        )

    with pytest.raises(ValueError, match="statement"):
        KnowledgeClaim(
            claim_id="CLM-002",
            statement="",
            scope="ep_khuon",
            source_refs=("turn:1",),
        )


def test_extract_claim_from_turn_normal():
    """Test extracting claim from a valid turn with exact source references."""
    session = make_test_session()
    turn = InterviewTurn(
        turn_id="turn_001",
        session_id=session.session_id,
        sequence=1,
        question_text="Nhiệt độ sấy tối ưu là bao nhiêu?",
        answer_text="Nhiệt độ sấy tối ưu của máy sấy MS-200 là 65 độ C trong 45 phút.",
        question_reason="Làm rõ gap sấy keo",
        trigger_refs=("gap_01",),
        answer_confidence=0.95,
        answer_state="answered",
        created_at="2026-09-08T00:01:00Z",
    )

    claim = extract_claim_from_turn(turn, session, scope="say_keo")
    assert claim.claim_id == "CLM-ses_test_01-1"
    assert claim.scope == "say_keo"
    assert "turn:turn_001" in claim.source_refs
    assert claim.confidence == 0.95
    assert claim.status == CLAIM_STATUS_CANDIDATE
    assert len(claim.validity_conditions) > 0
    assert len(claim.digest) == 64


def test_unconfirmed_critical_tokens_block_extraction():
    """Test invariant: Audio transcripts with unconfirmed critical tokens fail-closed."""
    session = make_test_session()
    turn = InterviewTurn(
        turn_id="turn_002",
        session_id=session.session_id,
        sequence=2,
        question_text="Áp suất bao nhiêu?",
        answer_text="Cài đặt 3.5 bar cho van V-102",
        question_reason="Xác minh áp suất",
        trigger_refs=("gap_02",),
        answer_confidence=0.9,
        answer_state="answered",
        created_at="2026-09-08T00:02:00Z",
    )

    unconfirmed_segment = TranscriptionSegment(
        segment_id="seg_01",
        start_time=0.0,
        end_time=3.5,
        text="Cài đặt 3.5 bar cho van V-102",
        tokens=("Cài", "đặt", "3.5", "bar"),
        critical_tokens=("3.5", "bar", "V-102"),
        is_confirmed=False,  # Chưa xác nhận
    )

    receipt = TranscriptionReceipt(
        receipt_id="rec_001",
        session_id=session.session_id,
        audio_path="local_only/audio/rec_001.wav",
        audio_digest="sha_audio_001",
        engine_name="whisper.cpp",
        engine_version="v1.7.4",
        segments=(unconfirmed_segment,),
        full_text="Cài đặt 3.5 bar cho van V-102",
        all_critical_tokens=("3.5", "bar", "V-102"),
        state="completed",
        created_at="2026-09-08T00:02:05Z",
    )

    with pytest.raises(UnconfirmedCriticalTokenError, match="chưa được chuyên gia xác nhận"):
        extract_claim_from_turn(turn, session, scope="ap_suat", transcript_receipt=receipt)


def test_confirmed_critical_tokens_allow_extraction():
    """Test confirmed audio transcript allows claim extraction with provenance links."""
    session = make_test_session()
    turn = InterviewTurn(
        turn_id="turn_003",
        session_id=session.session_id,
        sequence=3,
        question_text="Áp suất bao nhiêu?",
        answer_text="Cài đặt 3.5 bar cho van V-102",
        question_reason="Xác minh áp suất",
        trigger_refs=("gap_02",),
        answer_confidence=0.9,
        answer_state="answered",
        created_at="2026-09-08T00:03:00Z",
    )

    confirmed_segment = TranscriptionSegment(
        segment_id="seg_02",
        start_time=0.0,
        end_time=3.5,
        text="Cài đặt 3.5 bar cho van V-102",
        tokens=("Cài", "đặt", "3.5", "bar"),
        critical_tokens=("3.5", "bar", "V-102"),
        is_confirmed=True,  # Đã xác nhận
    )

    receipt = TranscriptionReceipt(
        receipt_id="rec_002",
        session_id=session.session_id,
        audio_path="local_only/audio/rec_002.wav",
        audio_digest="sha_audio_002",
        engine_name="whisper.cpp",
        engine_version="v1.7.4",
        segments=(confirmed_segment,),
        full_text="Cài đặt 3.5 bar cho van V-102",
        all_critical_tokens=("3.5", "bar", "V-102"),
        state="completed",
        created_at="2026-09-08T00:03:05Z",
    )

    claim = extract_claim_from_turn(turn, session, scope="ap_suat", transcript_receipt=receipt)
    assert "transcript:rec_002" in claim.source_refs
    assert "segment:seg_02" in claim.source_refs


def test_uncertain_and_skipped_turn_handling():
    """Test uncertainty handling and skipped turn rejection."""
    session = make_test_session()

    # Uncertain turn lowers confidence
    uncertain_turn = InterviewTurn(
        turn_id="turn_004",
        session_id=session.session_id,
        sequence=4,
        question_text="Tốc độ ép?",
        answer_text="Hình như tốc độ ép là 120 mm/s nhưng tôi không chắc lắm.",
        question_reason="Hỏi tốc độ ép",
        trigger_refs=(),
        answer_confidence=0.8,
        answer_state="uncertain",
        created_at="2026-09-08T00:04:00Z",
    )
    claim = extract_claim_from_turn(uncertain_turn, session, scope="ep_nhua")
    assert claim.confidence <= 0.6
    assert "chưa hoàn toàn chắc chắn" in claim.uncertainty_note

    # Skipped turn cannot produce claim
    skipped_turn = InterviewTurn(
        turn_id="turn_005",
        session_id=session.session_id,
        sequence=5,
        question_text="Mã dầu bôi trơn?",
        answer_text="Bỏ qua câu này",
        question_reason="Hỏi dầu",
        trigger_refs=(),
        answer_confidence=0.0,
        answer_state="skipped",
        created_at="2026-09-08T00:05:00Z",
    )
    with pytest.raises(KnowledgeClaimError, match="bỏ qua hoặc chưa rõ"):
        extract_claim_from_turn(skipped_turn, session, scope="ep_nhua")


def test_detect_claim_conflicts_numerical_divergence():
    """Test invariant: Conflicting thresholds in same scope trigger conflict detection and escalation."""
    claim_a = KnowledgeClaim(
        claim_id="CLM-01",
        statement="Nhiệt độ sấy khuôn phải duy trì ở mức 65 độ C.",
        scope="khuon_duc",
        source_refs=("turn:1",),
    )

    claim_b = KnowledgeClaim(
        claim_id="CLM-02",
        statement="Nhiệt độ sấy khuôn không được vượt quá 85 độ C, khuyến nghị 80 độ C.",
        scope="khuon_duc",
        source_refs=("turn:2",),
    )

    res = detect_claim_conflicts(claim_b, [claim_a])
    assert res.has_conflict is True
    assert "CLM-01" in res.conflicting_claim_ids
    assert res.escalation_required is True
    assert "Xung đột thông số kỹ thuật" in res.reason


def test_mark_conflicting_claims_creates_escalation():
    """Test invariant: Conflicting claims are marked conflicted with escalation_id, never auto-resolved."""
    claim = KnowledgeClaim(
        claim_id="CLM-01",
        statement="Nhiệt độ 65 độ C.",
        scope="khuon_duc",
        source_refs=("turn:1",),
        status=CLAIM_STATUS_CANDIDATE,
    )

    conflicted_claim = mark_conflicting_claims(
        claim,
        conflicting_ids=("CLM-02",),
        reason="Mâu thuẫn thông số 65 độ C vs 80 độ C",
    )

    assert conflicted_claim.status == CLAIM_STATUS_CONFLICTED
    assert "CLM-02" in conflicted_claim.conflict_claim_ids
    assert conflicted_claim.escalation_id is not None
    assert conflicted_claim.escalation_id.startswith("ESC-CONF-")
    assert "XUNG ĐỘT" in conflicted_claim.uncertainty_note


def test_claim_repository_persistence_and_decisions():
    """Test saving, retrieving, listing and review decisions for claims."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_claims.sqlite"
        repo = ExpertInterviewRepository(database_path=db_path)
        repo.initialize()

        claim = KnowledgeClaim(
            claim_id="CLM-REC-01",
            statement="Cài áp suất máy dập 4.2 bar.",
            scope="may_dap",
            source_refs=("turn:10", "segment:s10"),
            validity_conditions=("4.2 bar",),
            confidence=0.9,
            status=CLAIM_STATUS_CANDIDATE,
        )

        # 1. Save claim
        repo.save_claim(claim, idempotency_key="idemp_c1")

        # 2. Get claim
        fetched = repo.get_claim("CLM-REC-01")
        assert fetched is not None
        assert fetched.claim_id == "CLM-REC-01"
        assert fetched.statement == "Cài áp suất máy dập 4.2 bar."
        assert fetched.scope == "may_dap"
        assert fetched.source_refs == ("turn:10", "segment:s10")
        assert fetched.validity_conditions == ("4.2 bar",)
        assert fetched.confidence == 0.9

        # 3. Idempotent re-save
        repo.save_claim(claim, idempotency_key="idemp_c1_retry")
        claims_list = repo.list_claims(scope="may_dap")
        assert len(claims_list) == 1

        # 4. Filter by status and scope
        assert len(repo.list_claims(scope="khac")) == 0
        assert len(repo.list_claims(status=CLAIM_STATUS_CANDIDATE)) == 1

        # 5. Record review decision
        repo.save_claim_review_decision(
            decision_id="dec_01",
            claim_id="CLM-REC-01",
            decision="approved",
            reviewer_id="lead_engineer",
            reason="Thông số chính xác theo tài liệu chuẩn của hãng",
            idempotency_key="idemp_dec_01",
        )
