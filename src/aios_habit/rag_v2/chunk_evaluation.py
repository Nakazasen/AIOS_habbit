# -*- coding: utf-8 -*-
"""Evidence-based chunking evaluation domain for RAG v2.

Composes with the existing eval_harness.py to add chunking-strategy
comparison, multilingual boundary analysis, chunk-length distribution,
and the chunk-evaluation/v1 local report contract.

This module NEVER modifies StructureAwareChunker, retrieval defaults,
document summaries, or the active Workspace Chat index.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "chunk-evaluation/v1"

# Controlled values
LANGUAGES = {"vi", "ja", "zh-CN"}
CHALLENGE_LABELS = {
    "boundary", "table", "summary", "short-text", "cross-source",
    "cjk-punctuation", "no-safe-boundary",
}
DECISIONS = {"baseline", "improved", "neutral", "rejected", "blocked"}
SUMMARY_ROLES = {"not_used", "navigation_only", "displaced_evidence", "supplementary"}

# CJK sentence-ending punctuation for boundary analysis
CJK_SENTENCE_ENDINGS = frozenset("。！？．")


# ---------------------------------------------------------------------------
# Data model (matches data-model.md)
# ---------------------------------------------------------------------------

@dataclass
class EvaluationCase:
    """One locally stored question and its expected evidence."""

    case_id: str
    question: str
    language: str
    source_ids: Tuple[str, ...]
    expected_chunk_hints: Dict[str, Any] = field(default_factory=dict)
    challenge_labels: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("case_id must be non-empty")
        if not self.question:
            raise ValueError("question must be non-empty")
        if self.language not in LANGUAGES:
            raise ValueError(f"language must be one of {LANGUAGES}, got {self.language!r}")
        if not self.source_ids:
            raise ValueError("source_ids must have at least one entry")
        for label in self.challenge_labels:
            if label not in CHALLENGE_LABELS:
                raise ValueError(f"Unknown challenge label: {label!r}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationCase":
        copy = dict(data)
        for tuple_key in ("source_ids", "challenge_labels"):
            if tuple_key in copy and copy[tuple_key] is not None:
                copy[tuple_key] = tuple(copy[tuple_key])
        return cls(**copy)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["source_ids"] = list(d["source_ids"])
        d["challenge_labels"] = list(d["challenge_labels"])
        return d


@dataclass
class ChunkingStrategy:
    """A named, immutable evaluated behavior."""

    strategy_id: str
    boundary_policy: str
    context_policy: str
    summary_policy: str
    provenance_policy: str
    baseline_of: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ValueError("strategy_id must be non-empty")
        for attr in ("boundary_policy", "context_policy", "summary_policy", "provenance_policy"):
            if not getattr(self, attr):
                raise ValueError(f"{attr} must be non-empty")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChunkingStrategy":
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# The default baseline strategy representing the current StructureAwareChunker
BASELINE_STRATEGY = ChunkingStrategy(
    strategy_id="baseline-structure-aware-v1",
    boundary_policy="existing: max_chars=900, table_rows_per_chunk=4, no overlap",
    context_policy="existing: parent_max_chars=6000, local parent/neighbor expansion",
    summary_policy="existing: document summary as navigation aid",
    provenance_policy="existing: page/sheet/row/section/privacy preserved",
)


@dataclass
class CaseOutcome:
    """The result for one EvaluationCase in one EvaluationRun."""

    case_id: str
    retrieved_source_ids: Tuple[str, ...] = field(default_factory=tuple)
    expected_evidence_found: bool = False
    detailed_evidence_present: bool = False
    summary_used: str = "not_used"
    latency_ms: float = 0.0
    fallback_boundary_used: bool = False
    # Boundary analysis (added for US2)
    split_at_sentence_punctuation: Optional[bool] = None
    boundary_char_position: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("case_id must be non-empty")
        if self.summary_used not in SUMMARY_ROLES:
            raise ValueError(f"summary_used must be one of {SUMMARY_ROLES}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CaseOutcome":
        copy = dict(data)
        if "retrieved_source_ids" in copy and copy["retrieved_source_ids"] is not None:
            copy["retrieved_source_ids"] = tuple(copy["retrieved_source_ids"])
        return cls(**copy)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["retrieved_source_ids"] = list(d["retrieved_source_ids"])
        return d


# Length distribution bands
LENGTH_BANDS = [
    (0, 50, "0-50"),
    (51, 200, "51-200"),
    (201, 500, "201-500"),
    (501, 1000, "501-1000"),
    (1001, float("inf"), "1001+"),
]


def compute_length_distribution(chunk_lengths: Sequence[int]) -> Dict[str, int]:
    """Count chunks in agreed length bands."""
    dist: Dict[str, int] = {label: 0 for _, _, label in LENGTH_BANDS}
    for length in chunk_lengths:
        for lo, hi, label in LENGTH_BANDS:
            if lo <= length <= hi:
                dist[label] += 1
                break
    return dist


@dataclass
class LanguageMetrics:
    """Per-language breakdown of evaluation metrics."""

    language: str
    case_count: int = 0
    expected_evidence_recall: float = 0.0
    citation_support_rate: float = 0.0
    boundary_failure_count: int = 0
    average_chunk_length: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyMetrics:
    """Aggregate comparison metrics retained for an EvaluationRun."""

    expected_evidence_recall_at_k: float = 0.0
    citation_support_rate: float = 0.0
    warm_query_p95_ms: float = 0.0
    preparation_duration_ms: float = 0.0
    index_size_bytes: int = 0
    retrievable_chunk_count: int = 0
    length_distribution: Dict[str, int] = field(default_factory=dict)
    short_chunk_warnings: int = 0
    language_breakdown: Dict[str, LanguageMetrics] = field(default_factory=dict)

    @classmethod
    def compute(
        cls,
        outcomes: Sequence[CaseOutcome],
        cases: Sequence[EvaluationCase],
        chunk_lengths: Sequence[int],
        *,
        preparation_duration_ms: float = 0.0,
        index_size_bytes: int = 0,
        retrievable_chunk_count: int = 0,
    ) -> "StrategyMetrics":
        """Compute aggregate metrics from case outcomes and chunk data."""
        if not outcomes:
            return cls()

        # Overall metrics
        n = len(outcomes)
        recall = sum(1 for o in outcomes if o.expected_evidence_found) / n
        citation = sum(1 for o in outcomes if o.detailed_evidence_present) / n
        latencies = sorted(o.latency_ms for o in outcomes)
        p95_idx = min(int(len(latencies) * 0.95), len(latencies) - 1)
        p95 = latencies[p95_idx] if latencies else 0.0

        # Length distribution
        length_dist = compute_length_distribution(chunk_lengths)
        short_warnings = length_dist.get("0-50", 0)

        # Language breakdown
        case_map = {c.case_id: c for c in cases}
        lang_groups: Dict[str, List[CaseOutcome]] = {}
        for outcome in outcomes:
            case = case_map.get(outcome.case_id)
            if case:
                lang_groups.setdefault(case.language, []).append(outcome)

        lang_breakdown: Dict[str, LanguageMetrics] = {}
        for lang, lang_outcomes in lang_groups.items():
            lang_n = len(lang_outcomes)
            lang_recall = sum(1 for o in lang_outcomes if o.expected_evidence_found) / lang_n
            lang_citation = sum(1 for o in lang_outcomes if o.detailed_evidence_present) / lang_n
            boundary_failures = sum(1 for o in lang_outcomes if o.fallback_boundary_used)
            lang_breakdown[lang] = LanguageMetrics(
                language=lang,
                case_count=lang_n,
                expected_evidence_recall=lang_recall,
                citation_support_rate=lang_citation,
                boundary_failure_count=boundary_failures,
            )

        return cls(
            expected_evidence_recall_at_k=recall,
            citation_support_rate=citation,
            warm_query_p95_ms=p95,
            preparation_duration_ms=preparation_duration_ms,
            index_size_bytes=index_size_bytes,
            retrievable_chunk_count=retrievable_chunk_count,
            length_distribution=length_dist,
            short_chunk_warnings=short_warnings,
            language_breakdown=lang_breakdown,
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["language_breakdown"] = {
            k: v if isinstance(v, dict) else asdict(v)
            for k, v in self.language_breakdown.items()
        }
        return d


@dataclass
class EvaluationRun:
    """One reproducible comparison execution."""

    run_id: str
    corpus_fingerprint: str
    question_set_fingerprint: str
    strategy_id: str
    model_identity: str
    started_at: str = ""
    completed_at: str = ""
    decision: str = "blocked"
    metrics: Optional[StrategyMetrics] = None
    case_outcomes: List[CaseOutcome] = field(default_factory=list)
    supported_path: str = ""
    legacy_chunkers_active: bool = False

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must be non-empty")
        if not self.corpus_fingerprint:
            raise ValueError("corpus_fingerprint must be non-empty")
        if not self.question_set_fingerprint:
            raise ValueError("question_set_fingerprint must be non-empty")
        if not self.strategy_id:
            raise ValueError("strategy_id must be non-empty")
        if not self.model_identity:
            raise ValueError("model_identity must be non-empty")
        if self.decision not in DECISIONS:
            raise ValueError(f"decision must be one of {DECISIONS}")

    def to_report_dict(self) -> Dict[str, Any]:
        """Serialize to chunk-evaluation/v1 contract report format."""
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "corpus_fingerprint": self.corpus_fingerprint,
            "question_set_fingerprint": self.question_set_fingerprint,
            "strategy_id": self.strategy_id,
            "model_identity": self.model_identity,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "decision": self.decision,
            "metrics": self.metrics.to_dict() if self.metrics else {},
            "case_outcomes": [o.to_dict() for o in self.case_outcomes],
            "supported_path": self.supported_path,
            "legacy_chunkers_active": self.legacy_chunkers_active,
            "privacy": {
                "raw_local_only_text_exported": False,
            },
        }


# ---------------------------------------------------------------------------
# Fingerprinting utilities (T007)
# ---------------------------------------------------------------------------

def corpus_fingerprint(manifest_path: str | Path) -> str:
    """SHA-256 fingerprint of a corpus manifest file."""
    data = Path(manifest_path).read_bytes()
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def question_set_fingerprint(cases_path: str | Path) -> str:
    """SHA-256 fingerprint of a question-evidence case set file."""
    data = Path(cases_path).read_bytes()
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


# ---------------------------------------------------------------------------
# Report schema validator (T006)
# ---------------------------------------------------------------------------

_REQUIRED_REPORT_FIELDS = {
    "schema_version", "run_id", "decision", "metrics",
    "case_outcomes", "privacy",
}
_REQUIRED_METRICS_FIELDS = {
    "expected_evidence_recall_at_k", "citation_support_rate",
    "warm_query_p95_ms", "preparation_duration_ms",
    "index_size_bytes", "retrievable_chunk_count",
}
_REQUIRED_OUTCOME_FIELDS = {
    "case_id", "expected_evidence_found", "detailed_evidence_present",
    "retrieved_source_ids", "fallback_boundary_used",
}


def validate_report(report: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a report dict against the chunk-evaluation/v1 contract.

    Returns (is_valid, list_of_error_messages).
    """
    errors: List[str] = []

    # Top-level fields
    for fld in _REQUIRED_REPORT_FIELDS:
        if fld not in report:
            errors.append(f"Missing required field: {fld}")

    # Schema version
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"schema_version must be {SCHEMA_VERSION!r}, "
            f"got {report.get('schema_version')!r}"
        )

    # Decision enum
    if report.get("decision") not in DECISIONS:
        errors.append(f"decision must be one of {DECISIONS}")

    # Privacy
    privacy = report.get("privacy", {})
    if privacy.get("raw_local_only_text_exported") is not False:
        errors.append("privacy.raw_local_only_text_exported must be false")

    # Metrics
    metrics = report.get("metrics", {})
    if isinstance(metrics, dict):
        for mfld in _REQUIRED_METRICS_FIELDS:
            if mfld not in metrics:
                errors.append(f"Missing required metrics field: {mfld}")
    else:
        errors.append("metrics must be a dict")

    # Case outcomes
    outcomes = report.get("case_outcomes", [])
    if not isinstance(outcomes, list):
        errors.append("case_outcomes must be a list")
    else:
        for i, outcome in enumerate(outcomes):
            if not isinstance(outcome, dict):
                errors.append(f"case_outcomes[{i}] must be a dict")
                continue
            for ofld in _REQUIRED_OUTCOME_FIELDS:
                if ofld not in outcome:
                    errors.append(f"case_outcomes[{i}] missing field: {ofld}")

    return (len(errors) == 0, errors)


# ---------------------------------------------------------------------------
# Boundary analysis utilities (T014)
# ---------------------------------------------------------------------------

def analyze_chunk_boundary(
    chunk_text: str,
    *,
    language: str,
) -> Dict[str, Any]:
    """Analyze whether a chunk boundary respects CJK sentence punctuation.

    Returns analysis dict with:
      - split_at_sentence_punctuation: bool
      - fallback_boundary_used: bool
      - boundary_char_position: int (position of the last char)
      - ending_char: str
    """
    if not chunk_text:
        return {
            "split_at_sentence_punctuation": False,
            "fallback_boundary_used": True,
            "boundary_char_position": 0,
            "ending_char": "",
        }

    stripped = chunk_text.rstrip()
    if not stripped:
        return {
            "split_at_sentence_punctuation": False,
            "fallback_boundary_used": True,
            "boundary_char_position": 0,
            "ending_char": "",
        }

    last_char = stripped[-1]
    at_sentence = last_char in CJK_SENTENCE_ENDINGS or last_char in ".!?"

    return {
        "split_at_sentence_punctuation": at_sentence,
        "fallback_boundary_used": not at_sentence and language in {"ja", "zh-CN"},
        "boundary_char_position": len(stripped) - 1,
        "ending_char": last_char,
    }


# ---------------------------------------------------------------------------
# Privacy validation (T018)
# ---------------------------------------------------------------------------

def validate_report_privacy(
    report_json: str,
    source_samples: Optional[Sequence[str]] = None,
) -> Tuple[bool, List[str]]:
    """Scan a serialized report for leaked local_only content.

    Args:
        report_json: The JSON string of the report.
        source_samples: Optional list of source text snippets to check for.

    Returns (is_clean, list_of_violations).
    """
    violations: List[str] = []

    report = json.loads(report_json)
    if report.get("privacy", {}).get("raw_local_only_text_exported") is not False:
        violations.append("privacy.raw_local_only_text_exported is not false")

    if source_samples:
        report_lower = report_json.lower()
        for i, sample in enumerate(source_samples):
            if len(sample) >= 40 and sample.lower() in report_lower:
                violations.append(
                    f"Source sample {i} (len={len(sample)}) found in report output"
                )

    return (len(violations) == 0, violations)


# ---------------------------------------------------------------------------
# Case loading utility
# ---------------------------------------------------------------------------

def load_cases(cases_path: str | Path) -> List[EvaluationCase]:
    """Load evaluation cases from a JSON file."""
    raw = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    return [EvaluationCase.from_dict(item) for item in raw]


# ---------------------------------------------------------------------------
# BaselineRunner (T010 + T016)
# ---------------------------------------------------------------------------

class BaselineRunner:
    """Run current StructureAwareChunker against frozen cases and produce a report.

    This runner:
    - Creates a DEDICATED local SQLite index (never mutates active Workspace Chat index)
    - Uses the current StructureAwareChunker without modification
    - Executes each case's question via search_with_summary
    - Records CaseOutcome with boundary analysis
    - Computes StrategyMetrics
    - Emits a chunk-evaluation/v1 JSON report

    T016 (supported-path trace): Records which chunker class was used.
    """

    def __init__(
        self,
        *,
        corpus_manifest_path: str | Path,
        cases_path: str | Path,
        index_dir: str | Path,
        strategy: Optional[ChunkingStrategy] = None,
        embedding_backend: Optional[Any] = None,
        model_identity: str = "deterministic-eval",
    ) -> None:
        self.corpus_manifest_path = Path(corpus_manifest_path)
        self.cases_path = Path(cases_path)
        self.index_dir = Path(index_dir)
        self.strategy = strategy or BASELINE_STRATEGY
        self.embedding_backend = embedding_backend
        self.model_identity = model_identity

    def run(
        self,
        documents: Optional[Sequence["DocumentElement"]] = None,
        chunks: Optional[Sequence["DocumentChunk"]] = None,
    ) -> EvaluationRun:
        """Execute the evaluation and return a complete EvaluationRun.

        Provide either:
        - documents: raw DocumentElements to be chunked by StructureAwareChunker
        - chunks: pre-built DocumentChunks to ingest directly

        At least one must be provided.
        """
        from .chunking import DocumentChunk, StructureAwareChunker
        from .index import LocalChunkIndex, SearchOptions
        from .semantic import DeterministicEmbeddingBackend

        started_at = datetime.now(timezone.utc).isoformat()
        run_id = f"eval-{int(time.time())}"

        # Fingerprints
        corp_fp = corpus_fingerprint(self.corpus_manifest_path)
        case_fp = question_set_fingerprint(self.cases_path)

        # Create dedicated index
        self.index_dir.mkdir(parents=True, exist_ok=True)
        eval_db = self.index_dir / f"{run_id}.db"
        backend = self.embedding_backend or DeterministicEmbeddingBackend()
        index = LocalChunkIndex(
            eval_db,
            embedding_backend=backend,
            sqlite_check_same_thread=False,
        )

        # Chunk and ingest
        prep_start = time.perf_counter()
        all_chunks: List[DocumentChunk] = []
        chunker_class_name = "unknown"

        if chunks is not None:
            all_chunks = list(chunks)
            chunker_class_name = "pre-chunked"
        elif documents is not None:
            chunker = StructureAwareChunker()
            chunker_class_name = chunker.__class__.__name__
            all_chunks = chunker.chunk_elements(documents)
        else:
            raise ValueError("Either documents or chunks must be provided")

        index.upsert_chunks(all_chunks)
        prep_ms = (time.perf_counter() - prep_start) * 1000.0

        # Index stats
        index_size = eval_db.stat().st_size if eval_db.exists() else 0
        retrievable_count = sum(1 for c in all_chunks if c.retrievable)
        chunk_lengths = [len(c.text) for c in all_chunks]

        # Load cases
        cases = load_cases(self.cases_path)
        case_map = {c.case_id: c for c in cases}

        # Execute each case
        outcomes: List[CaseOutcome] = []
        search_options = SearchOptions(candidate_limit=10, per_document_limit=2)

        for case in cases:
            t0 = time.perf_counter()
            try:
                response = index.search_with_summary(
                    case.question, limit=10, options=search_options,
                )
                latency_ms = (time.perf_counter() - t0) * 1000.0

                retrieved_sources = tuple(
                    r.source_name for r in response.results
                )
                # Check if expected sources are in retrieved results
                found = any(
                    sid in retrieved_sources or
                    any(sid in rs for rs in retrieved_sources)
                    for sid in case.source_ids
                )
                # Check detailed evidence
                has_detail = len(response.results) > 0 and found

                # Boundary analysis for boundary-challenge cases
                boundary_result: Dict[str, Any] = {}
                if "boundary" in case.challenge_labels or "cjk-punctuation" in case.challenge_labels:
                    # Analyze chunks that matched this case's sources
                    relevant_chunks = [
                        c for c in all_chunks
                        if any(sid in (c.source_name, c.source_path) for sid in case.source_ids)
                    ]
                    if relevant_chunks:
                        # Analyze the last chunk boundary (most likely to be mid-sentence)
                        boundary_result = analyze_chunk_boundary(
                            relevant_chunks[-1].text, language=case.language,
                        )

                outcome = CaseOutcome(
                    case_id=case.case_id,
                    retrieved_source_ids=retrieved_sources,
                    expected_evidence_found=found,
                    detailed_evidence_present=has_detail,
                    summary_used="not_used",
                    latency_ms=latency_ms,
                    fallback_boundary_used=boundary_result.get("fallback_boundary_used", False),
                    split_at_sentence_punctuation=boundary_result.get("split_at_sentence_punctuation"),
                    boundary_char_position=boundary_result.get("boundary_char_position"),
                )
            except Exception as exc:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                outcome = CaseOutcome(
                    case_id=case.case_id,
                    expected_evidence_found=False,
                    detailed_evidence_present=False,
                    latency_ms=latency_ms,
                )
            outcomes.append(outcome)

        # Compute metrics
        metrics = StrategyMetrics.compute(
            outcomes, cases, chunk_lengths,
            preparation_duration_ms=prep_ms,
            index_size_bytes=index_size,
            retrievable_chunk_count=retrievable_count,
        )

        completed_at = datetime.now(timezone.utc).isoformat()

        # Build run
        run = EvaluationRun(
            run_id=run_id,
            corpus_fingerprint=corp_fp,
            question_set_fingerprint=case_fp,
            strategy_id=self.strategy.strategy_id,
            model_identity=self.model_identity,
            started_at=started_at,
            completed_at=completed_at,
            decision="baseline",
            metrics=metrics,
            case_outcomes=outcomes,
            supported_path=chunker_class_name,
            legacy_chunkers_active=False,
        )

        # Cleanup eval DB
        try:
            index._conn.close()
        except Exception:
            pass

        return run

    def run_and_save(
        self,
        output_dir: str | Path,
        documents: Optional[Sequence["DocumentElement"]] = None,
        chunks: Optional[Sequence["DocumentChunk"]] = None,
    ) -> Tuple[EvaluationRun, Path, Path]:
        """Run evaluation and save JSON report + Markdown summary.

        Returns (run, json_path, md_path).
        """
        run = self.run(documents=documents, chunks=chunks)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        report = run.to_report_dict()

        # Validate before writing
        valid, errors = validate_report(report)
        if not valid:
            raise ValueError(f"Report validation failed: {errors}")

        json_path = out / f"{run.run_id}_report.json"
        json_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        md_path = out / f"{run.run_id}_summary.md"
        md_path.write_text(
            format_evaluation_summary(run),
            encoding="utf-8",
        )

        return run, json_path, md_path


# ---------------------------------------------------------------------------
# Markdown summary formatter
# ---------------------------------------------------------------------------

def format_evaluation_summary(run: EvaluationRun) -> str:
    """Generate human-readable Markdown summary of an evaluation run."""
    m = run.metrics or StrategyMetrics()
    lines = [
        f"# Chunk Evaluation Report: {run.run_id}",
        "",
        f"**Strategy**: {run.strategy_id}",
        f"**Decision**: {run.decision}",
        f"**Model**: {run.model_identity}",
        f"**Active Chunker**: {run.supported_path}",
        f"**Legacy Active**: {run.legacy_chunkers_active}",
        "",
        "## Fingerprints",
        f"- Corpus: `{run.corpus_fingerprint}`",
        f"- Question Set: `{run.question_set_fingerprint}`",
        "",
        "## Aggregate Metrics",
        f"- Evidence Recall@K: {m.expected_evidence_recall_at_k:.2%}",
        f"- Citation Support Rate: {m.citation_support_rate:.2%}",
        f"- Warm Query P95: {m.warm_query_p95_ms:.1f} ms",
        f"- Preparation: {m.preparation_duration_ms:.1f} ms",
        f"- Index Size: {m.index_size_bytes:,} bytes",
        f"- Retrievable Chunks: {m.retrievable_chunk_count}",
        f"- Short Chunk Warnings (≤50 chars): {m.short_chunk_warnings}",
        "",
        "## Chunk Length Distribution",
    ]
    for band, count in m.length_distribution.items():
        lines.append(f"- {band}: {count}")

    if m.language_breakdown:
        lines.extend(["", "## Language Breakdown", ""])
        lines.append("| Language | Cases | Recall | Citation | Boundary Failures |")
        lines.append("|----------|-------|--------|----------|-------------------|")
        for lang, lm in m.language_breakdown.items():
            lines.append(
                f"| {lang} | {lm.case_count} | {lm.expected_evidence_recall:.2%} | "
                f"{lm.citation_support_rate:.2%} | {lm.boundary_failure_count} |"
            )

    lines.extend([
        "",
        "## Case Outcomes",
        "",
        "| Case | Found | Detailed | Latency | Boundary |",
        "|------|-------|----------|---------|----------|",
    ])
    for o in run.case_outcomes:
        boundary = "✓" if o.split_at_sentence_punctuation else ("✗" if o.fallback_boundary_used else "—")
        lines.append(
            f"| {o.case_id} | {'✓' if o.expected_evidence_found else '✗'} | "
            f"{'✓' if o.detailed_evidence_present else '✗'} | "
            f"{o.latency_ms:.1f}ms | {boundary} |"
        )

    lines.extend([
        "",
        "---",
        f"Generated: {run.completed_at}",
    ])
    return "\n".join(lines) + "\n"
