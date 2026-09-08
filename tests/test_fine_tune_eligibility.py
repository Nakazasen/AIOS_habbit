"""Tests for fine-tune eligibility assessment rubric.

Implements T071 of Goal 010-expert-knowledge-acquisition.
Guards:
- Must not use raw audio, raw transcript, or local_only data.
- Must not spawn any training jobs or background training processes.
- Must return NOT_APPLICABLE when RAG baseline is adequate or sample volume is low.
"""
from __future__ import annotations

import subprocess
from unittest.mock import patch
import pytest

from aios_habit.fine_tune_eligibility import (
    MIN_REQUIRED_SAMPLES,
    RAG_SATISFACTION_THRESHOLD,
    VERDICT_BLOCKED_PRIVACY,
    VERDICT_ELIGIBLE,
    VERDICT_NOT_APPLICABLE,
    FineTuneDatasetMetadata,
    evaluate_fine_tune_eligibility,
)


def test_privacy_violation_disqualifies_fine_tune():
    """Test invariant: Presence of raw audio, transcripts, or local_only assets blocks fine-tuning."""
    # 1. Has raw audio
    meta_audio = FineTuneDatasetMetadata(
        total_samples=1000,
        has_raw_audio=True,
        has_raw_transcripts=False,
        has_local_only_data=False,
        has_pii_or_secrets=False,
        baseline_rag_accuracy=0.60,
    )
    rep1 = evaluate_fine_tune_eligibility(meta_audio)
    assert rep1.is_eligible is False
    assert rep1.verdict == VERDICT_BLOCKED_PRIVACY
    assert "âm thanh thô" in rep1.primary_reason

    # 2. Has local_only data
    meta_local = FineTuneDatasetMetadata(
        total_samples=1000,
        has_raw_audio=False,
        has_raw_transcripts=False,
        has_local_only_data=True,
        has_pii_or_secrets=False,
        baseline_rag_accuracy=0.60,
    )
    rep2 = evaluate_fine_tune_eligibility(meta_local)
    assert rep2.is_eligible is False
    assert rep2.verdict == VERDICT_BLOCKED_PRIVACY
    assert "local_only" in rep2.primary_reason


def test_insufficient_samples_returns_not_applicable():
    """Test invariant: Sample count below 500 returns NOT_APPLICABLE."""
    meta = FineTuneDatasetMetadata(
        total_samples=42,  # Current small scale fixtures
        has_raw_audio=False,
        has_raw_transcripts=False,
        has_local_only_data=False,
        has_pii_or_secrets=False,
        baseline_rag_accuracy=0.50,
    )
    report = evaluate_fine_tune_eligibility(meta)
    assert report.is_eligible is False
    assert report.verdict == VERDICT_NOT_APPLICABLE
    assert "chưa đủ ngưỡng tối thiểu" in report.primary_reason


def test_high_rag_baseline_accuracy_returns_not_applicable():
    """Test invariant: High RAG baseline (>= 80%) makes fine-tuning NOT_APPLICABLE."""
    meta = FineTuneDatasetMetadata(
        total_samples=800,
        has_raw_audio=False,
        has_raw_transcripts=False,
        has_local_only_data=False,
        has_pii_or_secrets=False,
        baseline_rag_accuracy=0.95,  # BGE-M3 + in-context accuracy
    )
    report = evaluate_fine_tune_eligibility(meta)
    assert report.is_eligible is False
    assert report.verdict == VERDICT_NOT_APPLICABLE
    assert "đạt ngưỡng thỏa mãn" in report.primary_reason


def test_pure_function_zero_side_effects_and_no_training_spawning():
    """Test invariant: Assessment is a pure function that never spawns processes or training jobs."""
    meta = FineTuneDatasetMetadata(
        total_samples=1000,
        has_raw_audio=False,
        has_raw_transcripts=False,
        has_local_only_data=False,
        has_pii_or_secrets=False,
        baseline_rag_accuracy=0.60,
    )

    with patch("subprocess.Popen") as mock_popen, patch("subprocess.run") as mock_run:
        report = evaluate_fine_tune_eligibility(meta)
        mock_popen.assert_not_called()
        mock_run.assert_not_called()

    assert report.is_eligible is True
    assert report.verdict == VERDICT_ELIGIBLE
    assert len(report.digest) == 64
