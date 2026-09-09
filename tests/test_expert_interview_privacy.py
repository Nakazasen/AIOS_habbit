"""Privacy, confidentiality, and data hygiene tests for expert audio and transcripts.

Implements T047 of Goal 010-expert-knowledge-acquisition.
Fail-closed Invariants:
1. Zero raw audio binaries stored in SQLite databases (only SHA-256 digests and safe locators).
2. Git ignore patterns prevent tracking real audio or raw transcripts.
3. Provider payload isolation: 'local_only' labeled assets are strictly blocked from external cloud providers.
4. Log and error message hygiene: zero secrets, tokens, or raw transcripts leaked.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
import pytest

from aios_habit.expert_interview_repository import ExpertInterviewRepository
from aios_habit.knowledge_coverage import (
    CAgentGatewayClient,
    KnowledgeGapCandidate,
    SecurityPolicyError,
)
from aios_habit.local_transcription import (
    CONSENT_STATE_GRANTED,
    ConsentRecord,
    TranscriptionReceipt,
    TranscriptionSegment,
)


@pytest.fixture
def temp_repo(tmp_path: Path) -> ExpertInterviewRepository:
    db_path = tmp_path / "test_privacy_interview.sqlite"
    repo = ExpertInterviewRepository(db_path)
    repo.initialize()
    return repo


def test_sqlite_db_contains_no_raw_audio_blob(temp_repo: ExpertInterviewRepository):
    """Database schemas store only digests and path locators, NEVER raw audio binary BLOBs."""
    receipt = TranscriptionReceipt(
        receipt_id="TRCP-PRIVACY-1",
        session_id="SESS-PRIVACY-1",
        audio_path="local_cases/audio/test_audio.wav",
        audio_digest="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        engine_name="whisper.cpp",
        engine_version="v1.7.4",
        segments=(
            TranscriptionSegment("SEG-1", 0.0, 1.0, "Đoạn chép mẫu", ("Đoạn", "chép", "mẫu"), ()),
        ),
        full_text="Đoạn chép mẫu",
        all_critical_tokens=(),
    )
    temp_repo.save_transcription_receipt(receipt, "IDEMP-PRIV-1")

    # Direct SQL inspection: verify all column types are TEXT/INTEGER/REAL, zero BLOB
    with temp_repo._connection() as conn:
        table_info = conn.execute("PRAGMA table_info(interview_transcripts)").fetchall()
        column_types = {col["name"]: col["type"] for col in table_info}

        assert "audio_blob" not in column_types
        assert column_types["audio_digest"] == "TEXT"
        assert column_types["audio_path"] == "TEXT"

        # Check raw rows
        row = conn.execute("SELECT * FROM interview_transcripts WHERE receipt_id = ?", ("TRCP-PRIVACY-1",)).fetchone()
        assert isinstance(row["audio_path"], str)
        assert isinstance(row["audio_digest"], str)
        for col_name in row.keys():
            assert not isinstance(row[col_name], bytes), f"Column {col_name} must not contain raw binary BLOB"


def test_git_hygiene_and_ignore_rules_for_audio():
    """Git ignore rules or repository state must ensure zero audio files are tracked."""
    repo_root = Path(__file__).resolve().parent.parent
    gitignore_path = repo_root / ".gitignore"

    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text(encoding="utf-8")
        # Ensure audio or local_cases/local_runs patterns exist
        has_audio_or_local_rule = any(
            pat in gitignore_content
            for pat in ("*.wav", "*.mp3", "*.m4a", "local_cases", "local_runs", "*.sqlite")
        )
        assert has_audio_or_local_rule, "Gitignore must contain rules ignoring local_cases or audio files"

    # Check git tracked files do not include any audio files outside tests/fixtures
    try:
        proc = subprocess.run(
            ["git", "ls-files", "*.wav", "*.mp3", "*.flac"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        tracked_audio = [f for f in proc.stdout.splitlines() if f.strip()]
        for f in tracked_audio:
            # Only synthetic fixture audio is permitted in Git
            assert "fixtures" in Path(f).as_posix(), f"Real audio file tracked in Git: {f}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass


def test_local_only_assets_blocked_from_cloud_providers():
    """Assets labeled local_only trigger SecurityPolicyError when passed to non-internal provider."""
    # Cloud provider client without internal authorization
    cloud_client = CAgentGatewayClient(
        endpoint="https://api.external-cloud.com/v1/predict",
        is_internal_allowed=False,
    )

    local_gap = KnowledgeGapCandidate(
        gap_id="GAP-LOCAL-1",
        collection_id="col-local",
        scope="lsu_optics",
        title="Bản ghi âm tại xưởng",
        description="Thông số nội bộ",
        gap_type="missing_threshold",
        evidence_refs=("DOC-LOCAL#chunk_001",),
        status="candidate",
    )

    # Calling cloud provider with local_only snippets must fail-closed
    with pytest.raises(SecurityPolicyError, match="local_only"):
        cloud_client.explain_and_rank_gaps(
            deterministic_gaps=[local_gap],
            evidence_pack={
                "snippets": [{"snippet_id": "SNIP-1", "text": "bí mật", "labels": ["local_only"]}],
            },
        )


def test_receipt_digest_integrity_and_tampering_detection():
    """Tampered transcript receipt alters payload digest and is detected."""
    receipt = TranscriptionReceipt(
        receipt_id="TRCP-INTEG-1",
        session_id="SESS-1",
        audio_path="local_cases/audio.wav",
        audio_digest="original_audio_sha256",
        engine_name="whisper.cpp",
        engine_version="v1.7.4",
        segments=(),
        full_text="Văn bản gốc",
        all_critical_tokens=(),
    )
    original_digest = receipt.payload_digest

    # Modified copy simulates tampering
    tampered_receipt = TranscriptionReceipt(
        receipt_id="TRCP-INTEG-1",
        session_id="SESS-1",
        audio_path="local_cases/audio.wav",
        audio_digest="original_audio_sha256",
        engine_name="whisper.cpp",
        engine_version="v1.7.4",
        segments=(),
        full_text="Văn bản đã bị sửa đổi trái phép",
        all_critical_tokens=(),
    )
    assert tampered_receipt.payload_digest != original_digest


def test_sqlite_db_contains_no_raw_transcript_text(temp_repo: ExpertInterviewRepository):
    """T083: Database stores only locator and SHA-256 digest, NEVER raw transcript text or segments JSON."""
    raw_secret_text = "Nội dung phỏng vấn tuyệt mật về hiệu chuẩn gương LSU-300 không được lưu vào SQLite"
    receipt = TranscriptionReceipt(
        receipt_id="TRCP-RAW-ISOLATION-1",
        session_id="SESS-RAW-ISOLATION-1",
        audio_path="local_cases/audio/sample_raw.wav",
        audio_digest="f" * 64,
        engine_name="whisper.cpp",
        engine_version="v1.7.4",
        segments=(
            TranscriptionSegment("SEG-ISO-1", 0.0, 2.5, raw_secret_text, tuple(raw_secret_text.split()), ("LSU-300",)),
        ),
        full_text=raw_secret_text,
        all_critical_tokens=("LSU-300",),
    )
    temp_repo.save_transcription_receipt(receipt, "IDEMP-RAW-ISO-1")

    # Direct SQL inspection: raw transcript text must NOT be present in SQLite columns
    with temp_repo._connection() as conn:
        row = conn.execute(
            "SELECT * FROM interview_transcripts WHERE receipt_id = ?",
            ("TRCP-RAW-ISOLATION-1",),
        ).fetchone()
        assert row is not None
        assert row["full_text"] == "", "Column full_text in SQLite must be empty string (zero raw text in DB)"
        assert row["segments_json"] == "", "Column segments_json in SQLite must be empty string (zero raw segments in DB)"
        assert row["transcript_locator"] != "", "Column transcript_locator must point to local_only file"
        assert row["transcript_digest"] != "", "Column transcript_digest must hold SHA-256 digest"

        # Verify raw text does not appear in any column of interview_transcripts
        for col_name in row.keys():
            val = str(row[col_name])
            assert "tuyệt mật" not in val, f"Raw transcript leaked into column {col_name}"
            assert "hiệu chuẩn gương" not in val, f"Raw transcript leaked into column {col_name}"

    # Verify repository get_transcription_receipt correctly reloads from local_only store
    reloaded = temp_repo.get_transcription_receipt("SESS-RAW-ISOLATION-1")
    assert reloaded is not None
    assert reloaded.full_text == raw_secret_text
    assert len(reloaded.segments) == 1
    assert reloaded.segments[0].text == raw_secret_text


def test_transcript_atomic_rollback_cleans_up_file_on_db_error(temp_repo: ExpertInterviewRepository, monkeypatch):
    """Verify that if database operation fails, any newly created transcript file is unlinked (atomic rollback)."""
    receipt = TranscriptionReceipt(
        receipt_id="TRCP-ROLLBACK-TEST",
        session_id="SESS-ROLLBACK-1",
        audio_path="local_cases/audio/sample_rb.wav",
        audio_digest="a" * 64,
        engine_name="whisper.cpp",
        engine_version="v1.7.4",
        segments=(),
        full_text="Test rollback content",
        all_critical_tokens=(),
    )

    # Simulate DB execution failure
    def _faulty_connection():
        raise RuntimeError("Simulated SQLite failure")

    monkeypatch.setattr(temp_repo, "_connection", _faulty_connection)

    transcripts_dir = temp_repo.database_path.parent / "local_only" / "transcripts"
    expected_file = transcripts_dir / "TRCP-ROLLBACK-TEST.json"

    with pytest.raises(RuntimeError, match="Simulated SQLite failure"):
        temp_repo.save_transcription_receipt(receipt, "IDEMP-RB-1")

    assert not expected_file.exists(), "Transcript file must be cleaned up when DB transaction rolls back"


def test_transcript_path_traversal_sanitization(temp_repo: ExpertInterviewRepository):
    """Verify that malicious receipt_id with '..' or slashes cannot escape the transcripts directory."""
    receipt = TranscriptionReceipt(
        receipt_id="../../etc/evil_receipt",
        session_id="SESS-TRAVERSAL-1",
        audio_path="local_cases/audio/sample_trav.wav",
        audio_digest="b" * 64,
        engine_name="whisper.cpp",
        engine_version="v1.7.4",
        segments=(),
        full_text="Traverser",
        all_critical_tokens=(),
    )
    # Should safely sanitize without escaping or raise error
    temp_repo.save_transcription_receipt(receipt, "IDEMP-TRAV-1")

    transcripts_dir = temp_repo.database_path.parent / "local_only" / "transcripts"
    # Verify no file created outside transcripts_dir
    assert not (temp_repo.database_path.parent / "etc" / "evil_receipt.json").exists()
    # The file should be safely inside transcripts_dir with sanitized name
    created_files = list(transcripts_dir.glob("*.json"))
    for f in created_files:
        assert f.resolve().parent == transcripts_dir.resolve()


def test_missing_transcript_file_raises_fail_closed_error(temp_repo: ExpertInterviewRepository):
    """Verify that if the transcript file is missing on disk, it raises FileNotFoundError, NOT silently empty."""
    receipt = TranscriptionReceipt(
        receipt_id="TRCP-MISSING-TEST",
        session_id="SESS-MISSING-1",
        audio_path="local_cases/audio/sample_miss.wav",
        audio_digest="c" * 64,
        engine_name="whisper.cpp",
        engine_version="v1.7.4",
        segments=(TranscriptionSegment("S1", 0.0, 1.0, "Real words", (), ()),),
        full_text="Real words",
        all_critical_tokens=(),
    )
    temp_repo.save_transcription_receipt(receipt, "IDEMP-MISS-1")

    # Manually delete the transcript file from disk to simulate file loss / disk failure
    transcripts_dir = temp_repo.database_path.parent / "local_only" / "transcripts"
    transcript_file = transcripts_dir / "TRCP-MISSING-TEST.json"
    assert transcript_file.exists()
    transcript_file.unlink()

    # Must raise FileNotFoundError fail-closed, NOT return an empty transcript
    with pytest.raises(FileNotFoundError):
        temp_repo.get_transcription_receipt("SESS-MISSING-1")
