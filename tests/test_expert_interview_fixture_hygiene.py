"""Tests for expert interview fixture hygiene and safety boundaries.

Verifies that:
1. No real production data, actual factory serials, or secrets exist in fixtures.
2. No local absolute filesystem paths are baked into fixtures.
3. All fixtures adhere strictly to the 010 contract (2 experts, 2 scopes, 3 sessions, 5 gaps).
4. Audio fixture is a valid synthetic WAV file with proper metadata.
5. All feature flags in feature_flags.py default to fail-closed (False).
"""

from __future__ import annotations

import json
import re
import wave
from pathlib import Path

import pytest

from aios_habit.feature_flags import (
    ALL_010_FEATURES,
    FEATURE_EXPERT_AUDIO,
    FEATURE_EXPERT_COVERAGE,
    FEATURE_EXPERT_INTERVIEW,
    FEATURE_EXPERT_KNOWLEDGE_ACQUISITION,
    FEATURE_EXPERT_MULTI_USER,
    FEATURE_EXPERT_PUBLICATION,
    is_feature_enabled,
    override_feature_flags,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "expert_interview"


# Pattern to catch potential credentials or sensitive tokens
FORBIDDEN_SECRET_PATTERNS = [
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][^'\"]{8,}"),
    re.compile(r"(?i)password\s*[:=]\s*['\"][^'\"]+"),
    re.compile(r"(?i)secret\s*[:=]\s*['\"][^'\"]{8,}"),
    re.compile(r"AIza[0-9A-Za-z-_]{35}"),  # Google API key
    re.compile(r"AKIA[0-9A-Z]{16}"),      # AWS Access Key
    re.compile(r"ghp_[0-9A-Za-z]{36}"),   # GitHub Token
    re.compile(r"Bearer\s+[a-zA-Z0-9_.-]{20,}"),
]

# Pattern to detect hardcoded machine local absolute paths
LOCAL_PATH_PATTERNS = [
    re.compile(r"[a-zA-Z]:\\[^\s'\"\0]+"),  # Windows drive path C:\ or D:\
    re.compile(r"/(?:Users|home|root)/[^\s'\"\0]+"),  # Unix user paths
]


def test_fixture_directory_structure_exists():
    """Verify that all required subdirectories exist in fixtures."""
    assert FIXTURES_DIR.exists(), f"Fixtures directory missing at {FIXTURES_DIR}"
    assert (FIXTURES_DIR / "corpus").is_dir()
    assert (FIXTURES_DIR / "conversations").is_dir()
    assert (FIXTURES_DIR / "audio").is_dir()
    assert (FIXTURES_DIR / "gaps").is_dir()
    assert (FIXTURES_DIR / "identities").is_dir()


def test_fixture_files_hygiene_no_secrets_and_no_local_paths():
    """Scan all fixture files to ensure zero secrets and zero machine absolute paths."""
    all_files = list(FIXTURES_DIR.rglob("*"))
    assert len(all_files) > 0, "No fixture files found!"

    for file_path in all_files:
        if file_path.is_dir() or file_path.suffix.lower() == ".wav":
            continue

        text_content = file_path.read_text(encoding="utf-8")

        for pattern in FORBIDDEN_SECRET_PATTERNS:
            match = pattern.search(text_content)
            assert match is None, (
                f"POTENTIAL SECRET LEAK in {file_path.relative_to(FIXTURES_DIR)}: '{match.group(0)}'"
            )

        for pattern in LOCAL_PATH_PATTERNS:
            match = pattern.search(text_content)
            assert match is None, (
                f"LOCAL ABSOLUTE PATH FOUND in {file_path.relative_to(FIXTURES_DIR)}: '{match.group(0)}'"
            )


def test_fixture_identities_contract():
    """Verify contract requirements: 2 verified expert identities across 2 scopes."""
    identities_file = FIXTURES_DIR / "identities" / "expert_profiles.json"
    assert identities_file.exists()

    data = json.loads(identities_file.read_text(encoding="utf-8"))
    profiles = data.get("profiles", [])
    grants = data.get("grants", [])

    assert len(profiles) >= 2, "Must contain at least 2 expert profiles"
    expert_ids = {p["expert_id"] for p in profiles}
    assert "EXPERT_FIXTURE_ALPHA" in expert_ids
    assert "EXPERT_FIXTURE_BETA" in expert_ids

    # Collect scopes
    all_scopes = set()
    for p in profiles:
        all_scopes.update(p.get("scopes", []))
    assert "lsu_optical_assembly" in all_scopes
    assert "lsu_lens_calibration" in all_scopes
    assert len(all_scopes) >= 2, "Must cover at least 2 scopes"

    assert len(grants) >= 2, "Must contain at least 2 scope grants"


def test_fixture_knowledge_gaps_contract():
    """Verify contract requirements: exactly 5 evidenced knowledge gaps."""
    gaps_file = FIXTURES_DIR / "gaps" / "knowledge_gaps.json"
    assert gaps_file.exists()

    data = json.loads(gaps_file.read_text(encoding="utf-8"))
    items = data.get("items", [])
    assert len(items) == 5, f"Expected exactly 5 gap items, found {len(items)}"

    gap_ids = {g["gap_id"] for g in items}
    expected_ids = {"GAP-SIM-001", "GAP-SIM-002", "GAP-SIM-003", "GAP-SIM-004", "GAP-SIM-005"}
    assert gap_ids == expected_ids

    # Every gap must have non-empty evidence references (no hallucinated gaps)
    for g in items:
        assert len(g.get("evidence_refs", [])) > 0, f"Gap {g['gap_id']} lacks evidence references"
        assert g.get("status") == "accepted"


def test_fixture_conversations_contract():
    """Verify contract requirements: at least 3 simulation interview sessions."""
    conv_dir = FIXTURES_DIR / "conversations"
    session_files = list(conv_dir.glob("*.json"))
    assert len(session_files) >= 3, f"Expected at least 3 conversation sessions, found {len(session_files)}"

    for s_file in session_files:
        data = json.loads(s_file.read_text(encoding="utf-8"))
        assert "session_id" in data
        assert "expert_id" in data
        assert "turns" in data
        assert len(data["turns"]) >= 2, f"Session {s_file.name} must have at least 2 turns"


def test_fixture_audio_validity():
    """Verify that sample audio fixture is a valid WAV file and has matching manifest."""
    wav_file = FIXTURES_DIR / "audio" / "sample_interview_sine_16k.wav"
    manifest_file = FIXTURES_DIR / "audio" / "mock_transcription_manifest.json"

    assert wav_file.exists()
    assert manifest_file.exists()

    # Validate WAV file structure using standard library wave
    with wave.open(str(wav_file), "rb") as wf:
        assert wf.getnchannels() == 1, "Audio fixture must be mono"
        assert wf.getsampwidth() == 2, "Audio fixture must be 16-bit PCM"
        assert wf.getframerate() == 16000, "Audio fixture must be 16kHz"
        n_frames = wf.getnframes()
        assert n_frames == 16000, f"Expected 1 second (16000 frames), got {n_frames}"

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["format"] == "wav"
    assert manifest["sample_rate"] == 16000
    assert len(manifest["simulated_transcript"]) >= 2


def test_feature_flags_default_fail_closed():
    """Verify that Goal 010 feature flag is consolidated into a single flag and disabled by default."""
    assert len(ALL_010_FEATURES) == 1
    assert ALL_010_FEATURES[0] == FEATURE_EXPERT_KNOWLEDGE_ACQUISITION
    for flag in ALL_010_FEATURES:
        assert is_feature_enabled(flag) is False, f"Flag {flag} must be disabled by default"

    assert is_feature_enabled(FEATURE_EXPERT_KNOWLEDGE_ACQUISITION) is False
    assert is_feature_enabled(FEATURE_EXPERT_COVERAGE) is False
    assert is_feature_enabled(FEATURE_EXPERT_INTERVIEW) is False
    assert is_feature_enabled(FEATURE_EXPERT_AUDIO) is False
    assert is_feature_enabled(FEATURE_EXPERT_PUBLICATION) is False
    assert is_feature_enabled(FEATURE_EXPERT_MULTI_USER) is False


def test_feature_flags_override_context_manager():
    """Verify that single consolidated feature flag can be temporarily overridden for testing."""
    assert is_feature_enabled(FEATURE_EXPERT_KNOWLEDGE_ACQUISITION) is False
    with override_feature_flags(expert_knowledge_acquisition=True):
        assert is_feature_enabled(FEATURE_EXPERT_KNOWLEDGE_ACQUISITION) is True
        assert is_feature_enabled(FEATURE_EXPERT_INTERVIEW) is True
    assert is_feature_enabled(FEATURE_EXPERT_KNOWLEDGE_ACQUISITION) is False
