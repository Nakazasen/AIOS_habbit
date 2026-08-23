# -*- coding: utf-8 -*-
"""Tests for the chunk_evaluation domain module.

Covers:
- T002: Schema validation for all dataclasses
- T008: Baseline runner report schema validation
- T009: StrategyMetrics aggregation
- T013: Multilingual boundary detection measurement
- T017: Supported-path trace verification
- T018: Privacy validation
"""
from __future__ import annotations

import json
import subprocess
import sys
import pytest

from aios_habit.rag_v2.chunk_evaluation import (
    BASELINE_STRATEGY,
    CJK_SENTENCE_ENDINGS,
    CaseOutcome,
    ChunkingStrategy,
    EvaluationCase,
    EvaluationRun,
    LanguageMetrics,
    StrategyMetrics,
    analyze_chunk_boundary,
    compute_length_distribution,
    corpus_fingerprint,
    question_set_fingerprint,
    validate_report,
    validate_report_privacy,
)


# ---------------------------------------------------------------------------
# T002: Schema validation — EvaluationCase
# ---------------------------------------------------------------------------

class TestEvaluationCaseSchema:
    """Validate EvaluationCase field types, required fields, and controlled values."""

    def test_valid_case_vi(self) -> None:
        case = EvaluationCase(
            case_id="case-vi-001",
            question="Quy trình vận hành máy CNC là gì?",
            language="vi",
            source_ids=("src-001",),
            challenge_labels=("boundary",),
        )
        assert case.case_id == "case-vi-001"
        assert case.language == "vi"

    def test_valid_case_ja(self) -> None:
        case = EvaluationCase(
            case_id="case-ja-001",
            question="CNC加工手順は何ですか？",
            language="ja",
            source_ids=("src-002",),
            challenge_labels=("cjk-punctuation",),
        )
        assert case.language == "ja"

    def test_valid_case_zh(self) -> None:
        case = EvaluationCase(
            case_id="case-zh-001",
            question="CNC加工程序是什么？",
            language="zh-CN",
            source_ids=("src-003",),
        )
        assert case.language == "zh-CN"

    def test_empty_case_id_raises(self) -> None:
        with pytest.raises(ValueError, match="case_id"):
            EvaluationCase(case_id="", question="q", language="vi", source_ids=("s",))

    def test_empty_question_raises(self) -> None:
        with pytest.raises(ValueError, match="question"):
            EvaluationCase(case_id="c1", question="", language="vi", source_ids=("s",))

    def test_invalid_language_raises(self) -> None:
        with pytest.raises(ValueError, match="language"):
            EvaluationCase(case_id="c1", question="q", language="en", source_ids=("s",))

    def test_empty_source_ids_raises(self) -> None:
        with pytest.raises(ValueError, match="source_ids"):
            EvaluationCase(case_id="c1", question="q", language="vi", source_ids=())

    def test_invalid_challenge_label_raises(self) -> None:
        with pytest.raises(ValueError, match="challenge label"):
            EvaluationCase(
                case_id="c1", question="q", language="vi",
                source_ids=("s",), challenge_labels=("invalid_label",),
            )

    def test_roundtrip_dict(self) -> None:
        case = EvaluationCase(
            case_id="c1", question="q", language="vi",
            source_ids=("s1", "s2"), challenge_labels=("boundary",),
        )
        d = case.to_dict()
        restored = EvaluationCase.from_dict(d)
        assert restored.case_id == case.case_id
        assert restored.source_ids == case.source_ids
        assert restored.challenge_labels == case.challenge_labels


# ---------------------------------------------------------------------------
# T002: Schema validation — ChunkingStrategy
# ---------------------------------------------------------------------------

class TestChunkingStrategySchema:
    """Validate ChunkingStrategy fields."""

    def test_baseline_strategy_valid(self) -> None:
        assert BASELINE_STRATEGY.strategy_id == "baseline-structure-aware-v1"
        assert "no overlap" in BASELINE_STRATEGY.boundary_policy

    def test_empty_strategy_id_raises(self) -> None:
        with pytest.raises(ValueError, match="strategy_id"):
            ChunkingStrategy(
                strategy_id="", boundary_policy="b",
                context_policy="c", summary_policy="s",
                provenance_policy="p",
            )

    def test_empty_policy_raises(self) -> None:
        with pytest.raises(ValueError, match="boundary_policy"):
            ChunkingStrategy(
                strategy_id="s1", boundary_policy="",
                context_policy="c", summary_policy="s",
                provenance_policy="p",
            )


# ---------------------------------------------------------------------------
# T002: Schema validation — CaseOutcome
# ---------------------------------------------------------------------------

class TestCaseOutcomeSchema:
    """Validate CaseOutcome fields and controlled values."""

    def test_valid_outcome(self) -> None:
        outcome = CaseOutcome(
            case_id="c1",
            retrieved_source_ids=("s1",),
            expected_evidence_found=True,
            detailed_evidence_present=True,
            summary_used="not_used",
        )
        assert outcome.expected_evidence_found is True

    def test_empty_case_id_raises(self) -> None:
        with pytest.raises(ValueError, match="case_id"):
            CaseOutcome(case_id="")

    def test_invalid_summary_role_raises(self) -> None:
        with pytest.raises(ValueError, match="summary_used"):
            CaseOutcome(case_id="c1", summary_used="invalid")

    def test_roundtrip_dict(self) -> None:
        outcome = CaseOutcome(
            case_id="c1", retrieved_source_ids=("s1", "s2"),
            expected_evidence_found=True,
        )
        d = outcome.to_dict()
        restored = CaseOutcome.from_dict(d)
        assert restored.case_id == outcome.case_id
        assert restored.retrieved_source_ids == outcome.retrieved_source_ids


# ---------------------------------------------------------------------------
# T002: Schema validation — EvaluationRun
# ---------------------------------------------------------------------------

class TestEvaluationRunSchema:
    """Validate EvaluationRun construction and report serialization."""

    def _make_run(self, **overrides: Any) -> EvaluationRun:
        defaults = dict(
            run_id="run-001",
            corpus_fingerprint="sha256:abc123",
            question_set_fingerprint="sha256:def456",
            strategy_id="baseline-structure-aware-v1",
            model_identity="bge-m3-local",
            decision="baseline",
        )
        defaults.update(overrides)
        return EvaluationRun(**defaults)

    def test_valid_run(self) -> None:
        run = self._make_run()
        assert run.run_id == "run-001"

    def test_empty_run_id_raises(self) -> None:
        with pytest.raises(ValueError, match="run_id"):
            self._make_run(run_id="")

    def test_invalid_decision_raises(self) -> None:
        with pytest.raises(ValueError, match="decision"):
            self._make_run(decision="unknown")

    def test_report_dict_has_schema_version(self) -> None:
        run = self._make_run()
        report = run.to_report_dict()
        assert report["schema_version"] == "chunk-evaluation/v1"
        assert report["privacy"]["raw_local_only_text_exported"] is False


# ---------------------------------------------------------------------------
# T006: Report schema validator
# ---------------------------------------------------------------------------

class TestReportValidator:
    """Validate the chunk-evaluation/v1 report contract validator."""

    def _valid_report(self) -> dict:
        return {
            "schema_version": "chunk-evaluation/v1",
            "run_id": "run-001",
            "decision": "baseline",
            "metrics": {
                "expected_evidence_recall_at_k": 0.8,
                "citation_support_rate": 0.7,
                "warm_query_p95_ms": 120.0,
                "preparation_duration_ms": 5000.0,
                "index_size_bytes": 1024000,
                "retrievable_chunk_count": 50,
            },
            "case_outcomes": [
                {
                    "case_id": "c1",
                    "expected_evidence_found": True,
                    "detailed_evidence_present": True,
                    "retrieved_source_ids": ["s1"],
                    "fallback_boundary_used": False,
                },
            ],
            "privacy": {"raw_local_only_text_exported": False},
        }

    def test_valid_report_passes(self) -> None:
        valid, errors = validate_report(self._valid_report())
        assert valid is True
        assert errors == []

    def test_missing_field_fails(self) -> None:
        report = self._valid_report()
        del report["decision"]
        valid, errors = validate_report(report)
        assert valid is False
        assert any("decision" in e for e in errors)

    def test_wrong_schema_version_fails(self) -> None:
        report = self._valid_report()
        report["schema_version"] = "wrong/v1"
        valid, errors = validate_report(report)
        assert valid is False

    def test_privacy_exported_true_fails(self) -> None:
        report = self._valid_report()
        report["privacy"]["raw_local_only_text_exported"] = True
        valid, errors = validate_report(report)
        assert valid is False
        assert any("exported" in e.lower() for e in errors)

    def test_missing_metrics_field_fails(self) -> None:
        report = self._valid_report()
        del report["metrics"]["warm_query_p95_ms"]
        valid, errors = validate_report(report)
        assert valid is False
        assert any("warm_query_p95_ms" in e for e in errors)

    def test_missing_outcome_field_fails(self) -> None:
        report = self._valid_report()
        del report["case_outcomes"][0]["case_id"]
        valid, errors = validate_report(report)
        assert valid is False


# ---------------------------------------------------------------------------
# T007: Fingerprinting utilities
# ---------------------------------------------------------------------------

class TestFingerprinting:
    """Verify corpus and question-set fingerprinting."""

    def test_corpus_fingerprint_deterministic(self, tmp_path) -> None:
        manifest = tmp_path / "manifest.json"
        manifest.write_text('{"sources": ["s1"]}', encoding="utf-8")
        fp1 = corpus_fingerprint(manifest)
        fp2 = corpus_fingerprint(manifest)
        assert fp1 == fp2
        assert fp1.startswith("sha256:")

    def test_question_set_fingerprint_deterministic(self, tmp_path) -> None:
        cases = tmp_path / "cases.json"
        cases.write_text('[{"case_id": "c1"}]', encoding="utf-8")
        fp1 = question_set_fingerprint(cases)
        fp2 = question_set_fingerprint(cases)
        assert fp1 == fp2
        assert fp1.startswith("sha256:")

    def test_different_content_different_fingerprint(self, tmp_path) -> None:
        f1 = tmp_path / "a.json"
        f2 = tmp_path / "b.json"
        f1.write_text('{"v": 1}', encoding="utf-8")
        f2.write_text('{"v": 2}', encoding="utf-8")
        assert corpus_fingerprint(f1) != corpus_fingerprint(f2)


# ---------------------------------------------------------------------------
# T009: StrategyMetrics aggregation
# ---------------------------------------------------------------------------

class TestStrategyMetricsAggregation:
    """Verify StrategyMetrics.compute produces correct aggregates."""

    def test_basic_aggregation(self) -> None:
        cases = [
            EvaluationCase(case_id="c1", question="q1", language="vi", source_ids=("s1",)),
            EvaluationCase(case_id="c2", question="q2", language="ja", source_ids=("s2",)),
            EvaluationCase(case_id="c3", question="q3", language="zh-CN", source_ids=("s3",)),
            EvaluationCase(case_id="c4", question="q4", language="vi", source_ids=("s4",)),
        ]
        outcomes = [
            CaseOutcome(case_id="c1", expected_evidence_found=True, detailed_evidence_present=True, latency_ms=100),
            CaseOutcome(case_id="c2", expected_evidence_found=False, detailed_evidence_present=False, latency_ms=200),
            CaseOutcome(case_id="c3", expected_evidence_found=True, detailed_evidence_present=True, latency_ms=150),
            CaseOutcome(case_id="c4", expected_evidence_found=True, detailed_evidence_present=False, latency_ms=300, fallback_boundary_used=True),
        ]
        chunk_lengths = [30, 100, 250, 500, 800, 1200]

        metrics = StrategyMetrics.compute(
            outcomes, cases, chunk_lengths,
            preparation_duration_ms=5000.0,
            index_size_bytes=1024000,
            retrievable_chunk_count=6,
        )

        # 3 of 4 found evidence
        assert metrics.expected_evidence_recall_at_k == pytest.approx(0.75)
        # 2 of 4 have detailed evidence
        assert metrics.citation_support_rate == pytest.approx(0.5)
        # P95 of [100, 150, 200, 300] = 300 (index 3)
        assert metrics.warm_query_p95_ms == pytest.approx(300.0)
        assert metrics.preparation_duration_ms == 5000.0
        assert metrics.index_size_bytes == 1024000
        assert metrics.retrievable_chunk_count == 6

    def test_length_distribution(self) -> None:
        lengths = [10, 20, 80, 150, 300, 450, 700, 1500]
        dist = compute_length_distribution(lengths)
        assert dist["0-50"] == 2
        assert dist["51-200"] == 2
        assert dist["201-500"] == 2
        assert dist["501-1000"] == 1
        assert dist["1001+"] == 1

    def test_short_chunk_warnings(self) -> None:
        cases = [EvaluationCase(case_id="c1", question="q", language="vi", source_ids=("s",))]
        outcomes = [CaseOutcome(case_id="c1", expected_evidence_found=True, latency_ms=10)]
        chunk_lengths = [5, 10, 20, 100, 500]
        metrics = StrategyMetrics.compute(outcomes, cases, chunk_lengths)
        assert metrics.short_chunk_warnings == 3  # 5, 10, 20 are ≤50

    def test_language_breakdown(self) -> None:
        cases = [
            EvaluationCase(case_id="c1", question="q1", language="vi", source_ids=("s1",)),
            EvaluationCase(case_id="c2", question="q2", language="ja", source_ids=("s2",)),
            EvaluationCase(case_id="c3", question="q3", language="ja", source_ids=("s3",)),
        ]
        outcomes = [
            CaseOutcome(case_id="c1", expected_evidence_found=True, detailed_evidence_present=True, latency_ms=100),
            CaseOutcome(case_id="c2", expected_evidence_found=True, detailed_evidence_present=True, latency_ms=200, fallback_boundary_used=True),
            CaseOutcome(case_id="c3", expected_evidence_found=False, detailed_evidence_present=False, latency_ms=150),
        ]
        metrics = StrategyMetrics.compute(outcomes, cases, [100, 200, 300])
        assert "vi" in metrics.language_breakdown
        assert "ja" in metrics.language_breakdown
        ja = metrics.language_breakdown["ja"]
        assert ja.case_count == 2
        assert ja.expected_evidence_recall == pytest.approx(0.5)
        assert ja.boundary_failure_count == 1

    def test_empty_outcomes(self) -> None:
        metrics = StrategyMetrics.compute([], [], [])
        assert metrics.expected_evidence_recall_at_k == 0.0


# ---------------------------------------------------------------------------
# T013: Multilingual boundary detection (measurement only)
# ---------------------------------------------------------------------------

class TestBoundaryAnalysis:
    """Verify boundary analysis detects CJK sentence punctuation endings."""

    def test_japanese_sentence_ending(self) -> None:
        text = "これはテスト文です。"
        result = analyze_chunk_boundary(text, language="ja")
        assert result["split_at_sentence_punctuation"] is True
        assert result["fallback_boundary_used"] is False
        assert result["ending_char"] == "。"

    def test_japanese_mid_sentence(self) -> None:
        text = "これはテスト文で"
        result = analyze_chunk_boundary(text, language="ja")
        assert result["split_at_sentence_punctuation"] is False
        assert result["fallback_boundary_used"] is True

    def test_chinese_exclamation(self) -> None:
        text = "这是一个测试！"
        result = analyze_chunk_boundary(text, language="zh-CN")
        assert result["split_at_sentence_punctuation"] is True
        assert result["fallback_boundary_used"] is False

    def test_chinese_question(self) -> None:
        text = "这是什么？"
        result = analyze_chunk_boundary(text, language="zh-CN")
        assert result["split_at_sentence_punctuation"] is True

    def test_chinese_mid_sentence(self) -> None:
        text = "这是一个测试句子的中间部分"
        result = analyze_chunk_boundary(text, language="zh-CN")
        assert result["split_at_sentence_punctuation"] is False
        assert result["fallback_boundary_used"] is True

    def test_vietnamese_english_punctuation(self) -> None:
        text = "Đây là một câu thử nghiệm."
        result = analyze_chunk_boundary(text, language="vi")
        assert result["split_at_sentence_punctuation"] is True
        # Vietnamese uses English punctuation, no CJK fallback
        assert result["fallback_boundary_used"] is False

    def test_empty_text(self) -> None:
        result = analyze_chunk_boundary("", language="ja")
        assert result["split_at_sentence_punctuation"] is False
        assert result["fallback_boundary_used"] is True

    def test_cjk_sentence_endings_constant(self) -> None:
        assert "。" in CJK_SENTENCE_ENDINGS
        assert "！" in CJK_SENTENCE_ENDINGS
        assert "？" in CJK_SENTENCE_ENDINGS
        assert "．" in CJK_SENTENCE_ENDINGS


# ---------------------------------------------------------------------------
# T017: Supported-path trace
# ---------------------------------------------------------------------------

class TestSupportedPathTrace:
    """Verify EvaluationRun records the active chunking path."""

    def test_baseline_report_identifies_structure_aware_chunker(self) -> None:
        run = EvaluationRun(
            run_id="run-path-001",
            corpus_fingerprint="sha256:abc",
            question_set_fingerprint="sha256:def",
            strategy_id="baseline-structure-aware-v1",
            model_identity="bge-m3-local",
            decision="baseline",
            supported_path="StructureAwareChunker",
            legacy_chunkers_active=False,
        )
        report = run.to_report_dict()
        assert report["supported_path"] == "StructureAwareChunker"
        assert report["legacy_chunkers_active"] is False

    def test_report_schema_includes_path_fields(self) -> None:
        run = EvaluationRun(
            run_id="run-path-002",
            corpus_fingerprint="sha256:abc",
            question_set_fingerprint="sha256:def",
            strategy_id="baseline-structure-aware-v1",
            model_identity="bge-m3-local",
            decision="baseline",
            supported_path="StructureAwareChunker",
        )
        report = run.to_report_dict()
        assert "supported_path" in report
        assert "legacy_chunkers_active" in report


# ---------------------------------------------------------------------------
# T018: Privacy validation
# ---------------------------------------------------------------------------

class TestPrivacyValidation:
    """Verify privacy scanning of serialized reports."""

    def test_clean_report_passes(self) -> None:
        report = {"privacy": {"raw_local_only_text_exported": False}, "data": "safe"}
        is_clean, violations = validate_report_privacy(json.dumps(report))
        assert is_clean is True
        assert violations == []

    def test_exported_true_fails(self) -> None:
        report = {"privacy": {"raw_local_only_text_exported": True}}
        is_clean, violations = validate_report_privacy(json.dumps(report))
        assert is_clean is False

    def test_source_sample_detected(self) -> None:
        long_sample = "This is a very long local-only source text that should never appear in reports at all"
        report = {"privacy": {"raw_local_only_text_exported": False}, "leaked": long_sample}
        is_clean, violations = validate_report_privacy(
            json.dumps(report), source_samples=[long_sample]
        )
        assert is_clean is False
        assert any("Source sample" in v for v in violations)

    def test_short_sample_ignored(self) -> None:
        """Samples under 40 chars are too short to be meaningful leaks."""
        short = "short"
        report = {"privacy": {"raw_local_only_text_exported": False}, "text": short}
        is_clean, _ = validate_report_privacy(
            json.dumps(report), source_samples=[short]
        )
        assert is_clean is True


def test_cli_fails_closed_until_real_corpus_adapter_exists() -> None:
    """Synthetic fixtures must never be reported as an E1 baseline."""
    result = subprocess.run(
        [sys.executable, "scripts/evaluate_chunking.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
    )

    assert result.returncode == 2
    assert "BLOCKED" in result.stdout
    assert "synthetic identities" in result.stdout
