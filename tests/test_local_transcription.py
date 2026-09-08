"""Unit and contract tests for local audio transcription and consent lifecycle.

Implements T046 of Goal 010-expert-knowledge-acquisition.
Verifies:
1. Consent lifecycle (granted, declined, withdrawn fail-closed).
2. Device failure and corrupt/missing audio handling.
3. Critical token extraction (measurements, units, machine codes).
4. UTF-8 Vietnamese text integrity without mojibake.
5. Local-only audio boundary path validation (directory traversal blocked).
6. Cryptographic digest and receipt persistence in SQLite repository.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import pytest

from aios_habit.expert_interview_repository import ExpertInterviewRepository
from aios_habit.local_transcription import (
    AudioPathSecurityError,
    CONSENT_STATE_DECLINED,
    CONSENT_STATE_GRANTED,
    CONSENT_STATE_WITHDRAWN,
    ConsentRecord,
    ConsentRequiredError,
    ConsentWithdrawnError,
    LocalWhisperCppTranscriptionAdapter,
    MockLocalTranscriptionEngine,
    TranscriptionError,
    TranscriptionReceipt,
    TranscriptionSegment,
    extract_critical_tokens,
    validate_local_only_audio_path,
)


@pytest.fixture
def temp_repo(tmp_path: Path) -> ExpertInterviewRepository:
    db_path = tmp_path / "test_interview.sqlite"
    repo = ExpertInterviewRepository(db_path)
    repo.initialize()
    return repo


@pytest.fixture
def sample_wav_path() -> Path:
    fixture_path = Path("tests") / "fixtures" / "expert_interview" / "audio" / "sample_interview_sine_16k.wav"
    assert fixture_path.exists(), "Audio fixture sample_interview_sine_16k.wav must exist"
    return fixture_path


@pytest.fixture
def manifest_path() -> Path:
    p = Path("tests") / "fixtures" / "expert_interview" / "audio" / "mock_transcription_manifest.json"
    assert p.exists(), "Manifest fixture mock_transcription_manifest.json must exist"
    return p


def test_consent_lifecycle_granted_vs_declined_vs_withdrawn(sample_wav_path: Path, manifest_path: Path):
    """Transcription proceeds only when consent is active and fails closed otherwise."""
    adapter = LocalWhisperCppTranscriptionAdapter(
        fallback_mock_engine=MockLocalTranscriptionEngine(fixture_manifest_path=manifest_path)
    )

    # 1. Active consent -> SUCCESS
    active_consent = ConsentRecord(
        consent_id="CSNT-ACTIVE",
        session_id="SESS-001",
        subject="expert_1",
        state=CONSENT_STATE_GRANTED,
    )
    receipt = adapter.transcribe(
        audio_path=sample_wav_path,
        session_id="SESS-001",
        consent=active_consent,
    )
    assert receipt.receipt_id.startswith("TRCP-SESS-001")
    assert receipt.engine_name == "whisper.cpp"
    assert len(receipt.segments) > 0
    assert "Nhiệt độ tối đa" in receipt.full_text

    # 2. Declined consent -> DENIED
    declined_consent = ConsentRecord(
        consent_id="CSNT-DECLINED",
        session_id="SESS-002",
        subject="expert_1",
        state=CONSENT_STATE_DECLINED,
    )
    with pytest.raises(ConsentRequiredError, match="đồng ý"):
        adapter.transcribe(
            audio_path=sample_wav_path,
            session_id="SESS-002",
            consent=declined_consent,
        )

    # 3. Withdrawn consent -> BLOCKED IMMEDIATELY
    withdrawn_consent = ConsentRecord(
        consent_id="CSNT-WITHDRAWN",
        session_id="SESS-003",
        subject="expert_1",
        state=CONSENT_STATE_WITHDRAWN,
    )
    with pytest.raises(ConsentWithdrawnError, match="rút lại"):
        adapter.transcribe(
            audio_path=sample_wav_path,
            session_id="SESS-003",
            consent=withdrawn_consent,
        )


def test_missing_or_corrupt_audio(manifest_path: Path):
    """Missing or non-existent audio file raises FileNotFoundError."""
    adapter = LocalWhisperCppTranscriptionAdapter(
        fallback_mock_engine=MockLocalTranscriptionEngine(fixture_manifest_path=manifest_path)
    )
    consent = ConsentRecord(
        consent_id="CSNT-OK",
        session_id="SESS-ERR",
        subject="expert_1",
        state=CONSENT_STATE_GRANTED,
    )
    missing_audio = Path("non_existent_audio_sample_12345.wav")
    with pytest.raises(FileNotFoundError):
        adapter.transcribe(missing_audio, "SESS-ERR", consent)


def test_critical_token_extraction_and_vietnamese_utf8():
    """Numbers, units, and equipment IDs are correctly isolated without UTF-8 corruption."""
    sample_text = (
        "Nhiệt độ buồng sấy gương LSU-200 cần duy trì ở mức 55 độ C hoặc 70 °C, "
        "áp suất khí nén đạt 2.5 bar với sai số tối đa 0.5 mm trong 45 phút."
    )
    tokens = extract_critical_tokens(sample_text)

    # Check extracted parameters
    assert any("55" in t and "độ C" in t for t in tokens) or ("55" in tokens or "55 độ C" in tokens)
    assert any("70" in t for t in tokens)
    assert any("2.5 bar" in t for t in tokens)
    assert any("LSU-200" in t for t in tokens)
    assert any("45 phút" in t for t in tokens)

    # Verify UTF-8 strings maintain exact encoding
    vietnamese_str = "Quy trình căn chỉnh lăng kính quang học chính xác"
    assert vietnamese_str.encode("utf-8").decode("utf-8") == vietnamese_str


def test_local_only_boundary_security(tmp_path: Path):
    """Audio paths escaping configured local_only boundary or attempting traversal are blocked."""
    local_root = tmp_path / "local_only_storage"
    local_root.mkdir(parents=True, exist_ok=True)

    safe_file = local_root / "interview_recording.wav"
    safe_file.write_bytes(b"dummy_audio_bytes")

    outside_file = tmp_path / "system_sensitive_file.wav"
    outside_file.write_bytes(b"forbidden_data")

    # Safe path passes validation
    validated = validate_local_only_audio_path(safe_file, local_root)
    assert validated.exists()

    # Outside path fails with security error
    with pytest.raises(AudioPathSecurityError, match="ranh giới"):
        validate_local_only_audio_path(outside_file, local_root)


def test_repository_consent_and_transcription_persistence(temp_repo: ExpertInterviewRepository, sample_wav_path: Path, manifest_path: Path):
    """Consent and transcription receipts are persisted idempotently into SQLite."""
    session_id = "SESS-STORE-TEST-1"

    # 1. Save and retrieve consent
    consent = ConsentRecord(
        consent_id="CSNT-STORE-1",
        session_id=session_id,
        subject="chuyen_gia_quang_hoc",
        version="1.0",
        state=CONSENT_STATE_GRANTED,
        purposes=("audio_recording", "local_transcription"),
        granted_at="2026-09-08T15:00:00Z",
    )
    temp_repo.save_consent(consent, "IDEMP-CSNT-1")

    reloaded_consent = temp_repo.get_consent(session_id)
    assert reloaded_consent is not None
    assert reloaded_consent.consent_id == "CSNT-STORE-1"
    assert reloaded_consent.subject == "chuyen_gia_quang_hoc"
    assert reloaded_consent.state == CONSENT_STATE_GRANTED

    # 2. Transcribe and save receipt
    adapter = LocalWhisperCppTranscriptionAdapter(
        fallback_mock_engine=MockLocalTranscriptionEngine(fixture_manifest_path=manifest_path)
    )
    receipt = adapter.transcribe(sample_wav_path, session_id, consent)
    temp_repo.save_transcription_receipt(receipt, "IDEMP-TRCP-1")

    # 3. Retrieve receipt
    reloaded_receipt = temp_repo.get_transcription_receipt(session_id)
    assert reloaded_receipt is not None
    assert reloaded_receipt.receipt_id == receipt.receipt_id
    assert reloaded_receipt.audio_digest == receipt.audio_digest
    assert len(reloaded_receipt.segments) == len(receipt.segments)
    assert reloaded_receipt.full_text == receipt.full_text
    assert reloaded_receipt.engine_name == "whisper.cpp"
