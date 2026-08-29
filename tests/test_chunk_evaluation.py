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

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from aios_habit.rag_v2.chunk_evaluation import (
    BASELINE_STRATEGY,
    CJK_SENTENCE_ENDINGS,
    CJK_SENTENCE_STRATEGY,
    BaselineRunner,
    CaseOutcome,
    ChunkingStrategy,
    EvaluationCase,
    EvaluationRun,
    LanguageMetrics,
    StrategyMetrics,
    analyze_chunk_boundary,
    analyze_source_chunk_boundaries,
    classify_candidate_decision,
    chunker_for_strategy,
    compute_length_distribution,
    corpus_fingerprint,
    load_bge_eval_identity,
    load_corpus_manifest,
    question_set_fingerprint,
    resolve_strategy,
    validate_report,
    validate_report_privacy,
)
from aios_habit.rag_v2.schema import DocumentElement, ElementType, ExtractionStatus


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

    def test_source_boundaries_treat_no_punct_hard_cut_as_recorded_fallback(self) -> None:
        class _Chunk:
            def __init__(self, text: str) -> None:
                self.text = text
                self.source_name = "src-manufacturing-qa.md"
                self.source_path = "src-manufacturing-qa.md"
                self.document_id = "src-manufacturing-qa"
                self.retrievable = True
                self.metadata = {"representation_role": "child"}

        result = analyze_source_chunk_boundaries(
            [
                _Chunk("作業者は品質管理チェックリストを確認する。"),
                _Chunk("製造ラインの品質管理手順では工程ごとに寸法" * 20),
            ],
            language="ja",
            source_ids=["src-manufacturing-qa"],
        )
        assert result["split_at_sentence_punctuation"] is True
        assert result["fallback_boundary_used"] is True

    def test_source_boundaries_flag_punct_available_mid_sentence_cut(self) -> None:
        class _Chunk:
            def __init__(self, text: str) -> None:
                self.text = text
                self.source_name = "src-manufacturing-qa.md"
                self.source_path = "src-manufacturing-qa.md"
                self.document_id = "src-manufacturing-qa"
                self.retrievable = True
                self.metadata = {"representation_role": "child"}

        result = analyze_source_chunk_boundaries(
            [_Chunk("作業者は品質管理チェックリストを確認する。不適合があればロットを隔離")],
            language="ja",
            source_ids=["src-manufacturing-qa"],
        )
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


def _element(source_id: str, text: str) -> DocumentElement:
    return DocumentElement(
        element_id=f"{source_id}-el",
        document_id=source_id,
        source_path=f"{source_id}.md",
        source_name=f"{source_id}.md",
        file_type="md",
        extractor="fixture",
        extraction_status=ExtractionStatus.SUCCESS,
        element_type=ElementType.TEXT,
        text=text,
        privacy_labels=("public",),
    )


class TestBaselineRunnerIntegration:
    """T008: real StructureAwareChunker + DocumentElement fixtures, never fake PASS."""

    def test_in_memory_documents_use_structure_aware_chunker_and_stay_blocked(
        self,
        tmp_path: Path,
    ) -> None:
        fixtures = Path("tests/fixtures/chunk_evaluation")
        long_ja = (
            "製造ラインの品質管理手順では工程ごとに寸法と外観を確認し記録票へ記入する"
            "この文は句点なしで続く" * 8
        )
        runner = BaselineRunner(
            corpus_manifest_path=fixtures / "corpus_manifest.json",
            cases_path=fixtures / "cases_v1.json",
            index_dir=tmp_path / "index",
        )
        run = runner.run(documents=[
            _element("src-quality-process", "Quy trinh kiem tra chat luong. " * 40),
            _element("src-manufacturing-qa", long_ja + "。"),
        ])
        report = getattr(run, "_report_overlay", None) or run.to_report_dict()
        valid, errors = validate_report(report)
        assert valid, errors
        assert run.supported_path == "StructureAwareChunker"
        assert run.legacy_chunkers_active is False
        assert run.decision == "blocked"
        assert report["decision"] == "blocked"
        assert len(run.case_outcomes) == 12
        assert all(outcome.case_id for outcome in run.case_outcomes)
        assert report["privacy"]["raw_local_only_text_exported"] is False

    def test_file_backed_checksum_mismatch_is_blocked(self, tmp_path: Path) -> None:
        cases = tmp_path / "cases.json"
        cases.write_text(
            json.dumps([{
                "case_id": "vi-001",
                "question": "Quy trinh kiem tra chat luong?",
                "language": "vi",
                "source_ids": ["src-quality-process"],
                "challenge_labels": ["boundary"],
            }]),
            encoding="utf-8",
        )
        source = tmp_path / "src-quality-process.md"
        source.write_text("kiem tra chat luong " * 80, encoding="utf-8")
        manifest = tmp_path / "corpus.json"
        manifest.write_text(
            json.dumps({
                "corpus_kind": "public_evaluation",
                "synthetic": False,
                "sources": [{
                    "source_id": "src-quality-process",
                    "language": "vi",
                    "document_type": "markdown",
                    "path": "src-quality-process.md",
                    "sha256": "sha256:deadbeef",
                }],
            }),
            encoding="utf-8",
        )
        runner = BaselineRunner(
            corpus_manifest_path=manifest,
            cases_path=cases,
            index_dir=tmp_path / "index",
            require_bge_hybrid=True,
        )
        run = runner.run()
        assert run.decision == "blocked"
        overlay = getattr(run, "_report_overlay", {})
        assert overlay.get("blocked_reason") == "corpus_file_or_checksum_invalid"


def test_load_bge_eval_identity_reads_json_without_workspace_chat(tmp_path: Path) -> None:
    """Eval identity comes from the pinned JSON, not Workspace Chat loaders."""
    model_dir = tmp_path / "bge-m3"
    model_dir.mkdir()
    manifest = tmp_path / "workspace_chat_rag_v2.local.json"
    manifest.write_text(
        json.dumps({
            "activation_state": "rolled_back",
            "model": {
                "path": str(model_dir),
                "revision": "5617a9f61b028005a4858fdac845db406aefb181",
                "checksum": "sha256:b1d887e03f13547609b4c6498ce8f357242edb5079a448c62d31d4caac320b61",
                "device": "cpu",
                "use_fp16": False,
            },
        }),
        encoding="utf-8",
    )
    identity = load_bge_eval_identity(manifest)
    assert identity["revision"].startswith("5617a9f")
    assert identity["identity"].startswith("bge-m3:5617a9f61b02:")
    assert identity["device"] == "cpu"
    source = Path("src/aios_habit/rag_v2/chunk_evaluation.py").read_text(encoding="utf-8")
    assert "from aios_habit.workspace_chat" not in source
    assert "import aios_habit.workspace_chat" not in source


def _gate_report(*, recall: float, p95: float, index_size: int, cjk_ok: bool, found_extra: bool = True) -> dict:
    def outcome(case_id: str, *, found: bool, split: bool) -> dict:
        return {
            "case_id": case_id,
            "retrieved_source_ids": ["src"],
            "expected_evidence_found": found,
            "detailed_evidence_present": found,
            "summary_used": "not_used",
            "latency_ms": 10.0,
            "fallback_boundary_used": not split,
            "split_at_sentence_punctuation": split,
        }

    found = True
    return {
        "corpus_fingerprint": "sha256:corpus",
        "question_set_fingerprint": "sha256:cases",
        "model_identity": "bge-m3:test",
        "metrics": {
            "expected_evidence_recall_at_k": recall,
            "warm_query_p95_ms": p95,
            "index_size_bytes": index_size,
        },
        "case_outcomes": [
            outcome("vi-001", found=True, split=True),
            outcome("vi-002", found=found_extra, split=True),
            outcome("ja-001", found=True, split=cjk_ok),
            outcome("ja-004", found=True, split=cjk_ok),
            outcome("zh-001", found=True, split=cjk_ok),
            outcome("zh-004", found=True, split=cjk_ok),
        ],
    }


def test_resolve_strategy_and_chunker_policy() -> None:
    from aios_habit.rag_v2.chunking import (
        BOUNDARY_POLICY_LEGACY,
        BOUNDARY_POLICY_SENTENCE_PUNCTUATION,
    )

    assert resolve_strategy("baseline").strategy_id == BASELINE_STRATEGY.strategy_id
    assert resolve_strategy("cjk-sentence-punctuation-v1") is CJK_SENTENCE_STRATEGY
    assert chunker_for_strategy(BASELINE_STRATEGY).boundary_policy == BOUNDARY_POLICY_LEGACY
    assert (
        chunker_for_strategy(CJK_SENTENCE_STRATEGY).boundary_policy
        == BOUNDARY_POLICY_SENTENCE_PUNCTUATION
    )


def test_classify_candidate_improved_when_cjk_fixed() -> None:
    baseline = _gate_report(recall=0.917, p95=500.0, index_size=1000, cjk_ok=False)
    candidate = _gate_report(recall=0.917, p95=510.0, index_size=1100, cjk_ok=True)
    decision, reason = classify_candidate_decision(candidate, baseline)
    assert decision == "improved"
    assert reason == "cjk_boundary_fixed"


def test_classify_candidate_rejected_on_recall_drop() -> None:
    baseline = _gate_report(recall=0.917, p95=500.0, index_size=1000, cjk_ok=False)
    candidate = _gate_report(recall=0.80, p95=400.0, index_size=1000, cjk_ok=True)
    decision, reason = classify_candidate_decision(candidate, baseline)
    assert decision == "rejected"
    assert reason == "recall_regressed"


def test_classify_candidate_blocked_on_fingerprint_mismatch() -> None:
    baseline = _gate_report(recall=0.917, p95=500.0, index_size=1000, cjk_ok=False)
    candidate = _gate_report(recall=0.917, p95=500.0, index_size=1000, cjk_ok=True)
    candidate["corpus_fingerprint"] = "sha256:other"
    decision, reason = classify_candidate_decision(candidate, baseline)
    assert decision == "blocked"
    assert reason.startswith("fingerprint_mismatch")


def test_cli_candidate_requires_compare_to() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_chunking.py",
            "--strategy",
            "cjk-sentence-punctuation-v1",
            "--corpus",
            "tests/fixtures/chunk_evaluation/corpus_public_v1.json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
    )
    assert result.returncode == 1
    assert "compare-to" in result.stderr.lower()


def test_public_v3_manifest_checksums_match_files() -> None:
    root = Path("tests/fixtures/chunk_evaluation")
    manifest_path = root / "corpus_public_v3.json"
    corpus = load_corpus_manifest(manifest_path)
    assert corpus.kind == "public_evaluation"
    assert corpus.synthetic is False
    for source in corpus.sources:
        assert source.path is not None
        assert source.path.is_file()
        digest = "sha256:" + hashlib.sha256(source.path.read_bytes()).hexdigest()
        assert source.sha256 == digest, source.source_id


def test_lengthened_cjk_docs_exercise_900_char_sentence_split() -> None:
    from aios_habit.rag_v2.adapters import ConversionContext
    from aios_habit.rag_v2.chunking import (
        BOUNDARY_POLICY_LEGACY,
        BOUNDARY_POLICY_SENTENCE_PUNCTUATION,
        StructureAwareChunker,
    )
    from aios_habit.rag_v2.converters import TextDocumentConverterAdapter

    adapter = TextDocumentConverterAdapter()
    docs = Path("tests/fixtures/chunk_evaluation/docs")
    cases = (
        ("src-manufacturing-qa.md", "ja", "src-manufacturing-qa"),
        ("src-troubleshooting-ja.md", "ja", "src-troubleshooting-ja"),
        ("src-production-qa-zh.md", "zh-CN", "src-production-qa-zh"),
        ("src-troubleshooting-zh.md", "zh-CN", "src-troubleshooting-zh"),
    )
    for name, language, source_id in cases:
        path = docs / name
        elements = adapter.convert(
            str(path),
            ConversionContext(document_id=source_id, source_id=source_id),
        )
        longest = max((len((element.text or "").strip()) for element in elements), default=0)
        assert longest > 900, f"{name} longest element is {longest}"
        legacy = StructureAwareChunker(
            boundary_policy=BOUNDARY_POLICY_LEGACY,
        ).chunk_elements(elements)
        sentence = StructureAwareChunker(
            boundary_policy=BOUNDARY_POLICY_SENTENCE_PUNCTUATION,
        ).chunk_elements(elements)
        legacy_boundary = analyze_source_chunk_boundaries(
            legacy, language=language, source_ids=[source_id],
        )
        sentence_boundary = analyze_source_chunk_boundaries(
            sentence, language=language, source_ids=[source_id],
        )
        assert legacy_boundary["split_at_sentence_punctuation"] is False, name
        assert sentence_boundary["split_at_sentence_punctuation"] is True, name
        assert sentence_boundary["fallback_boundary_used"] is True, name


def test_vietnamese_material_standards_table_contains_query_terms(
    tmp_path: Path,
) -> None:
    from aios_habit.rag_v2.adapters import ConversionContext
    from aios_habit.rag_v2.chunk_evaluation import materialize_table_source
    from aios_habit.rag_v2.chunking import StructureAwareChunker
    from aios_habit.rag_v2.converters import ExcelDocumentConverterAdapter

    corpus = load_corpus_manifest(
        Path("tests/fixtures/chunk_evaluation/corpus_public_v3.json"),
    )
    source = next(
        item for item in corpus.sources if item.source_id == "src-material-standards"
    )
    xlsx = materialize_table_source(source, tmp_path)
    elements = ExcelDocumentConverterAdapter().convert(
        str(xlsx),
        ConversionContext(document_id=source.source_id, source_id=source.source_id),
    )
    chunks = StructureAwareChunker().chunk_elements(elements)
    blob = " ".join(chunk.text for chunk in chunks)
    assert "nguyên liệu" in blob
    assert "nhập kho" in blob
    assert "Tiêu chuẩn" in blob
