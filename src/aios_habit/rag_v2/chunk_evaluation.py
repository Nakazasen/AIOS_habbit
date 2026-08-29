# -*- coding: utf-8 -*-
"""Evidence-based chunking evaluation domain for RAG v2.

Composes with the existing eval_harness.py to add chunking-strategy
comparison, multilingual boundary analysis, chunk-length distribution,
and the chunk-evaluation/v1 local report contract.

Default Workspace Chat chunking is unchanged. E2 may evaluate an opt-in
sentence-punctuation candidate on a dedicated index; it never writes the
active Workspace Chat index.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
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


# Frozen E1 comparison splitter (legacy `. `/newline/space). Production default
# StructureAwareChunker after E2 v2 uses sentence_punctuation_v1; eval baseline
# still constructs BOUNDARY_POLICY_LEGACY explicitly.
BASELINE_STRATEGY = ChunkingStrategy(
    strategy_id="baseline-structure-aware-v1",
    boundary_policy="existing: max_chars=900, table_rows_per_chunk=4, no overlap",
    context_policy="existing: parent_max_chars=6000, local parent/neighbor expansion",
    summary_policy="existing: document summary as navigation aid",
    provenance_policy="existing: page/sheet/row/section/privacy preserved",
)

CJK_SENTENCE_STRATEGY = ChunkingStrategy(
    strategy_id="cjk-sentence-punctuation-v1",
    baseline_of="baseline-structure-aware-v1",
    boundary_policy="sentence_punctuation_v1: CJK/VI sentence endings before char fallback, no overlap",
    context_policy="existing: parent_max_chars=6000, local parent/neighbor expansion",
    summary_policy="existing: document summary as navigation aid",
    provenance_policy="existing: page/sheet/row/section/privacy preserved",
)

STRATEGIES = {
    "baseline": BASELINE_STRATEGY,
    BASELINE_STRATEGY.strategy_id: BASELINE_STRATEGY,
    CJK_SENTENCE_STRATEGY.strategy_id: CJK_SENTENCE_STRATEGY,
}

# Confirmed E1 CJK text-boundary failures (not table/cross-source-only cases).
CJK_BOUNDARY_CASE_IDS = frozenset({"ja-001", "ja-004", "zh-001", "zh-004"})
MAX_LATENCY_RATIO = 1.25
MAX_INDEX_RATIO = 1.25
MIN_RECALL_GAIN = 0.05


def resolve_strategy(name: str) -> ChunkingStrategy:
    strategy = STRATEGIES.get(name)
    if strategy is None:
        raise ValueError(f"unknown chunking strategy: {name!r}")
    return strategy


def chunker_for_strategy(strategy: ChunkingStrategy, *, max_chars: int = 900) -> Any:
    from .chunking import (
        BOUNDARY_POLICY_LEGACY,
        BOUNDARY_POLICY_SENTENCE_PUNCTUATION,
        StructureAwareChunker,
    )

    if strategy.strategy_id == CJK_SENTENCE_STRATEGY.strategy_id:
        return StructureAwareChunker(
            max_chars,
            boundary_policy=BOUNDARY_POLICY_SENTENCE_PUNCTUATION,
        )
    return StructureAwareChunker(max_chars, boundary_policy=BOUNDARY_POLICY_LEGACY)


def classify_candidate_decision(
    candidate: Dict[str, Any],
    baseline: Dict[str, Any],
) -> Tuple[str, str]:
    """Return ``(decision, reason)`` for an E2 candidate vs a frozen E1 report."""
    for key in ("corpus_fingerprint", "question_set_fingerprint"):
        if candidate.get(key) != baseline.get(key):
            return "blocked", f"fingerprint_mismatch:{key}"
    if candidate.get("model_identity") != baseline.get("model_identity"):
        return "blocked", "model_identity_mismatch"

    cand_metrics = candidate.get("metrics") or {}
    base_metrics = baseline.get("metrics") or {}
    cand_recall = float(cand_metrics.get("expected_evidence_recall_at_k") or 0.0)
    base_recall = float(base_metrics.get("expected_evidence_recall_at_k") or 0.0)
    if cand_recall + 1e-12 < base_recall:
        return "rejected", "recall_regressed"

    base_found = {
        row["case_id"]
        for row in baseline.get("case_outcomes") or []
        if row.get("expected_evidence_found")
    }
    cand_found = {
        row["case_id"]
        for row in candidate.get("case_outcomes") or []
        if row.get("expected_evidence_found")
    }
    lost = sorted(base_found - cand_found)
    if lost:
        return "rejected", "lost_evidence:" + ",".join(lost)

    base_p95 = float(base_metrics.get("warm_query_p95_ms") or 0.0) or 1.0
    cand_p95 = float(cand_metrics.get("warm_query_p95_ms") or 0.0)
    if cand_p95 / base_p95 > MAX_LATENCY_RATIO:
        return "rejected", "warm_p95_over_budget"
    base_index = float(base_metrics.get("index_size_bytes") or 0.0) or 1.0
    cand_index = float(cand_metrics.get("index_size_bytes") or 0.0)
    if cand_index / base_index > MAX_INDEX_RATIO:
        return "rejected", "index_size_over_budget"

    cand_outcomes = {
        row.get("case_id"): row for row in candidate.get("case_outcomes") or []
    }
    cjk_fixed = all(
        bool((cand_outcomes.get(case_id) or {}).get("split_at_sentence_punctuation"))
        for case_id in CJK_BOUNDARY_CASE_IDS
    )
    recall_gain = (cand_recall - base_recall) >= MIN_RECALL_GAIN
    if cjk_fixed or recall_gain:
        reason = "cjk_boundary_fixed" if cjk_fixed else "recall_gain"
        if cjk_fixed and recall_gain:
            reason = "cjk_boundary_fixed_and_recall_gain"
        return "improved", reason
    return "neutral", "no_sc003_gain"


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
# Case / corpus loading
# ---------------------------------------------------------------------------

DETERMINISTIC_MODEL_IDENTITY = "deterministic-eval"
SYNTHETIC_CORPUS_KIND = "synthetic_identities"
PUBLIC_CORPUS_KIND = "public_evaluation"
OWNER_CORPUS_KIND = "owner_local"


@dataclass
class CorpusSource:
    """One source row from a chunk-evaluation corpus manifest."""

    source_id: str
    language: str
    document_type: str
    description: str = ""
    has_tables: bool = False
    path: Optional[Path] = None
    sha256: str = ""


@dataclass
class CorpusManifest:
    """Loaded corpus identity. Missing files keep the corpus synthetic."""

    path: Path
    kind: str
    sources: List[CorpusSource]
    synthetic: bool
    raw_local_only_text_exported: bool = False


def file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def load_cases(cases_path: str | Path) -> List[EvaluationCase]:
    """Load evaluation cases from a JSON file."""
    raw = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("evaluation cases file must contain a non-empty list")
    return [EvaluationCase.from_dict(item) for item in raw]


def load_corpus_manifest(manifest_path: str | Path) -> CorpusManifest:
    """Load a corpus manifest and classify it as synthetic or file-backed."""
    path = Path(manifest_path).resolve()
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("sources")
    if not isinstance(rows, list) or not rows:
        raise ValueError("corpus manifest must contain a non-empty sources list")
    sources: List[CorpusSource] = []
    missing_files = False
    for item in rows:
        relative = str(item.get("path") or "").strip()
        resolved = (path.parent / relative).resolve() if relative else None
        source = CorpusSource(
            source_id=str(item.get("source_id") or "").strip(),
            language=str(item.get("language") or "").strip(),
            document_type=str(item.get("document_type") or "").strip(),
            description=str(item.get("description") or ""),
            has_tables=bool(item.get("has_tables")),
            path=resolved,
            sha256=str(item.get("sha256") or "").strip(),
        )
        if not source.source_id:
            raise ValueError("corpus source_id must be non-empty")
        if source.path is None or not source.path.is_file():
            missing_files = True
        sources.append(source)
    declared_kind = str(raw.get("corpus_kind") or "").strip()
    synthetic_flag = bool(raw.get("synthetic", missing_files or declared_kind == SYNTHETIC_CORPUS_KIND))
    if missing_files or synthetic_flag or declared_kind == SYNTHETIC_CORPUS_KIND:
        kind = SYNTHETIC_CORPUS_KIND
        synthetic = True
    elif declared_kind == OWNER_CORPUS_KIND:
        kind = OWNER_CORPUS_KIND
        synthetic = False
    else:
        kind = declared_kind or PUBLIC_CORPUS_KIND
        synthetic = False
    return CorpusManifest(
        path=path,
        kind=kind,
        sources=sources,
        synthetic=synthetic,
        raw_local_only_text_exported=bool(raw.get("raw_local_only_text_exported", False)),
    )


def source_id_matches(retrieved: str, expected_id: str) -> bool:
    """Match opaque source identities without requiring basename equality."""
    if not retrieved or not expected_id:
        return False
    if expected_id == retrieved or expected_id in retrieved:
        return True
    stem = Path(retrieved).stem
    return expected_id == stem or expected_id in stem


def inspect_summary_role(results: Sequence[Any], expected_found: bool) -> str:
    """Classify whether a document summary crowded out detailed evidence."""
    if not results:
        return "not_used"
    summary_hits = 0
    detailed_hits = 0
    for result in results:
        metadata = getattr(result, "metadata", {}) or {}
        file_type = str(getattr(result, "file_type", "") or "")
        is_summary = bool(metadata.get("is_document_summary")) or file_type == "document_summary"
        if is_summary:
            summary_hits += 1
        else:
            detailed_hits += 1
    if summary_hits and not detailed_hits:
        return "displaced_evidence" if expected_found else "navigation_only"
    if summary_hits and detailed_hits:
        return "supplementary"
    return "not_used"


def analyze_source_chunk_boundaries(
    chunks: Sequence[Any],
    *,
    language: str,
    source_ids: Sequence[str],
) -> Dict[str, Any]:
    """Measure whether retrievable children end at sentence punctuation."""
    relevant = []
    for chunk in chunks:
        source_name = str(getattr(chunk, "source_name", "") or "")
        source_path = str(getattr(chunk, "source_path", "") or "")
        document_id = str(getattr(chunk, "document_id", "") or "")
        if not any(
            source_id_matches(source_name, sid)
            or source_id_matches(source_path, sid)
            or source_id_matches(document_id, sid)
            for sid in source_ids
        ):
            continue
        metadata = getattr(chunk, "metadata", {}) or {}
        if metadata.get("is_document_summary"):
            continue
        if metadata.get("representation_role") == "parent":
            continue
        if not getattr(chunk, "retrievable", True):
            continue
        relevant.append(chunk)
    if not relevant:
        return {
            "split_at_sentence_punctuation": None,
            "fallback_boundary_used": False,
            "boundary_char_position": None,
        }
    fallback = False
    split_at = True
    position = None
    true_mid_sentence = False
    for chunk in relevant:
        text = getattr(chunk, "text", "") or ""
        analysis = analyze_chunk_boundary(text, language=language)
        if position is None:
            position = analysis["boundary_char_position"]
        if analysis["split_at_sentence_punctuation"]:
            continue
        if language not in {"ja", "zh-CN"}:
            continue
        stripped = text.rstrip()
        body = stripped[:-1] if stripped else ""
        punct_available = any(
            char in CJK_SENTENCE_ENDINGS or char in ".!?" for char in body
        )
        fallback = True
        position = analysis["boundary_char_position"]
        if punct_available:
            true_mid_sentence = True
    if true_mid_sentence:
        split_at = False
    elif fallback:
        # Hard-cut recorded, but no recognised punctuation sat in the window.
        split_at = True
    return {
        "split_at_sentence_punctuation": split_at,
        "fallback_boundary_used": fallback,
        "boundary_char_position": position,
    }


def materialize_table_source(source: CorpusSource, dest_dir: Path) -> Path:
    """Turn a committed JSON table into a local .xlsx for spreadsheet cases."""
    if source.path is None:
        raise ValueError(f"table source {source.source_id} has no path")
    payload = json.loads(source.path.read_text(encoding="utf-8"))
    headers = list(payload.get("headers") or [])
    rows = list(payload.get("rows") or [])
    if not headers or not rows:
        raise ValueError(f"table source {source.source_id} is empty")
    from openpyxl import Workbook

    dest_dir.mkdir(parents=True, exist_ok=True)
    xlsx_path = dest_dir / f"{source.source_id}.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    raw_title = str(payload.get("sheet") or "inspection").strip() or "inspection"
    for banned in (":", "\\", "/", "?", "*", "[", "]"):
        raw_title = raw_title.replace(banned, " ")
    sheet.title = raw_title[:31]
    sheet.append(headers)
    for row in rows:
        sheet.append(list(row))
    workbook.save(xlsx_path)
    return xlsx_path


_EVAL_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVAL_DEPLOYMENT_MANIFEST = (
    _EVAL_PROJECT_ROOT / "config" / "workspace_chat_rag_v2.local.json"
)


def load_bge_eval_identity(manifest_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Read pinned BGE-M3 identity from the local JSON manifest.

    Evaluation stays inside ``rag_v2``: it does not import Workspace Chat
    deployment loaders and does not require ``activation_state == activated``.
    """
    payload_path = Path(manifest_path) if manifest_path else DEFAULT_EVAL_DEPLOYMENT_MANIFEST
    if not payload_path.is_file():
        raise FileNotFoundError("bge_deployment_manifest_missing")
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    model = payload.get("model") or {}
    model_path = Path(str(model.get("path") or ""))
    revision = str(model.get("revision") or "")
    checksum = str(model.get("checksum") or "")
    device = str(model.get("device") or "cpu")
    use_fp16 = bool(model.get("use_fp16", False))
    if not model_path.is_dir():
        raise FileNotFoundError("bge_m3_model_path_missing")
    if not revision or not checksum:
        raise ValueError("bge_m3_model_identity_incomplete")
    return {
        "model_path": model_path,
        "revision": revision,
        "checksum": checksum,
        "device": device or "cpu",
        "use_fp16": use_fp16,
        "identity": f"bge-m3:{revision[:12]}:{checksum.split(':')[-1][:16]}",
    }


# ---------------------------------------------------------------------------
# BaselineRunner (T010 + T016)
# ---------------------------------------------------------------------------

class BaselineRunner:
    """Run current StructureAwareChunker against frozen cases and produce a report.

    Dedicated evaluation indexes never mutate the active Workspace Chat index.
    A report may be labelled ``baseline`` only when file-backed sources were
    ingested through StructureAwareChunker and BGE-M3 hybrid retrieval. Synthetic
    identities and deterministic embeddings always finish as ``blocked``.
    """

    def __init__(
        self,
        *,
        corpus_manifest_path: str | Path,
        cases_path: str | Path,
        index_dir: str | Path,
        strategy: Optional[ChunkingStrategy] = None,
        embedding_backend: Optional[Any] = None,
        model_identity: str = DETERMINISTIC_MODEL_IDENTITY,
        require_bge_hybrid: bool = False,
        deployment_manifest: Optional[str | Path] = None,
        baseline_report: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.corpus_manifest_path = Path(corpus_manifest_path)
        self.cases_path = Path(cases_path)
        self.index_dir = Path(index_dir)
        self.strategy = strategy or BASELINE_STRATEGY
        self.embedding_backend = embedding_backend
        self.model_identity = model_identity
        self.require_bge_hybrid = require_bge_hybrid
        self.deployment_manifest = deployment_manifest
        self.baseline_report = baseline_report

    def _is_baseline_strategy(self) -> bool:
        return self.strategy.strategy_id == BASELINE_STRATEGY.strategy_id

    def _make_chunker(self) -> Any:
        return chunker_for_strategy(self.strategy)

    def _blocked_run(
        self,
        *,
        run_id: str,
        started_at: str,
        reason: str,
        cases: Sequence[EvaluationCase],
        outcomes: Optional[Sequence[CaseOutcome]] = None,
        metrics: Optional[StrategyMetrics] = None,
        supported_path: str = "",
        model_identity: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> EvaluationRun:
        completed_at = datetime.now(timezone.utc).isoformat()
        recorded = list(outcomes or [
            CaseOutcome(case_id=case.case_id) for case in cases
        ])
        run = EvaluationRun(
            run_id=run_id,
            corpus_fingerprint=corpus_fingerprint(self.corpus_manifest_path),
            question_set_fingerprint=question_set_fingerprint(self.cases_path),
            strategy_id=self.strategy.strategy_id,
            model_identity=model_identity or self.model_identity,
            started_at=started_at,
            completed_at=completed_at,
            decision="blocked",
            metrics=metrics or StrategyMetrics.compute(recorded, cases, []),
            case_outcomes=recorded,
            supported_path=supported_path,
            legacy_chunkers_active=False,
        )
        report = run.to_report_dict()
        report["blocked_reason"] = reason
        report["corpus_kind"] = extra.get("corpus_kind") if extra else SYNTHETIC_CORPUS_KIND
        if extra:
            report.update(extra)
        run._report_overlay = report  # type: ignore[attr-defined]
        return run

    def run(
        self,
        documents: Optional[Sequence["DocumentElement"]] = None,
        chunks: Optional[Sequence["DocumentChunk"]] = None,
    ) -> EvaluationRun:
        """Execute the evaluation and return a complete EvaluationRun."""
        from .chunking import DocumentChunk
        from .index import LocalChunkIndex, SearchOptions
        from .pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec
        from .semantic import DeterministicEmbeddingBackend

        started_at = datetime.now(timezone.utc).isoformat()
        run_id = f"chunk-eval-{int(time.time())}"
        cases = load_cases(self.cases_path)
        corpus = load_corpus_manifest(self.corpus_manifest_path)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        if documents is None and chunks is None and corpus.synthetic:
            return self._blocked_run(
                run_id=run_id,
                started_at=started_at,
                reason="synthetic_identities_cannot_be_baseline",
                cases=cases,
                extra={"corpus_kind": corpus.kind},
            )

        if self.require_bge_hybrid or (
            documents is None and chunks is None and not corpus.synthetic
        ):
            return self._run_bge_hybrid(run_id, started_at, cases, corpus)

        backend = self.embedding_backend or DeterministicEmbeddingBackend()
        eval_db = self.index_dir / f"{run_id}.db"
        index = LocalChunkIndex(
            eval_db,
            embedding_backend=backend,
            sqlite_check_same_thread=False,
        )
        prep_start = time.perf_counter()
        all_chunks: List[DocumentChunk] = []
        chunker_class_name = "unknown"
        try:
            if chunks is not None:
                all_chunks = list(chunks)
                chunker_class_name = "pre-chunked"
            elif documents is not None:
                chunker = self._make_chunker()
                chunker_class_name = chunker.__class__.__name__
                all_chunks = chunker.chunk_elements(documents)
            else:
                raise ValueError("file-backed corpus requires BGE-M3 hybrid retrieval")
            index.upsert_chunks(all_chunks)
            prep_ms = (time.perf_counter() - prep_start) * 1000.0
            index_size = eval_db.stat().st_size if eval_db.exists() else 0
            retrievable_count = sum(1 for chunk in all_chunks if chunk.retrievable)
            chunk_lengths = [len(chunk.text) for chunk in all_chunks]
            search_options = SearchOptions(candidate_limit=10, per_document_limit=2)
            index.search_with_summary(cases[0].question, limit=10, options=search_options)
            outcomes = self._search_cases(
                cases,
                lambda question: index.search_with_summary(
                    question, limit=10, options=search_options,
                ),
                all_chunks,
            )
            metrics = StrategyMetrics.compute(
                outcomes, cases, chunk_lengths,
                preparation_duration_ms=prep_ms,
                index_size_bytes=index_size,
                retrievable_chunk_count=retrievable_count,
            )
            self._fill_language_chunk_lengths(metrics, cases, all_chunks)
        finally:
            index.close()

        identity = self.model_identity
        hybrid_ready = (
            chunker_class_name == "StructureAwareChunker"
            and not identity.startswith("deterministic")
            and not corpus.synthetic
        )
        decision = "baseline" if hybrid_ready else "blocked"
        run = EvaluationRun(
            run_id=run_id,
            corpus_fingerprint=corpus_fingerprint(self.corpus_manifest_path),
            question_set_fingerprint=question_set_fingerprint(self.cases_path),
            strategy_id=self.strategy.strategy_id,
            model_identity=identity,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            decision=decision,
            metrics=metrics,
            case_outcomes=outcomes,
            supported_path=chunker_class_name,
            legacy_chunkers_active=False,
        )
        overlay = run.to_report_dict()
        overlay["corpus_kind"] = corpus.kind
        overlay["retrieval_path"] = "lexical_or_deterministic"
        if decision == "blocked":
            overlay["blocked_reason"] = "synthetic_or_non_hybrid_backend"
        run._report_overlay = overlay  # type: ignore[attr-defined]
        return run

    def _run_bge_hybrid(
        self,
        run_id: str,
        started_at: str,
        cases: Sequence[EvaluationCase],
        corpus: CorpusManifest,
    ) -> EvaluationRun:
        from .pipeline import RagV2DevConfig, RagV2DevPipeline, SourceSpec

        if corpus.synthetic:
            return self._blocked_run(
                run_id=run_id,
                started_at=started_at,
                reason="synthetic_identities_cannot_be_baseline",
                cases=cases,
                extra={"corpus_kind": corpus.kind},
            )

        materialized_dir = self.index_dir / "materialized"
        source_specs: List[SourceSpec] = []
        source_samples: List[str] = []
        checksum_errors: List[str] = []
        for source in corpus.sources:
            if source.path is None or not source.path.is_file():
                checksum_errors.append(source.source_id)
                continue
            digest = file_sha256(source.path)
            if source.sha256 and source.sha256 != digest:
                checksum_errors.append(source.source_id)
                continue
            sample = source.path.read_text(encoding="utf-8", errors="ignore")[:400]
            if len(sample) >= 40:
                source_samples.append(sample)
            if source.document_type == "spreadsheet" or source.path.name.endswith(".table.json"):
                live_path = materialize_table_source(source, materialized_dir)
            else:
                live_path = source.path
            source_specs.append(SourceSpec(
                path=live_path,
                source_id=source.source_id,
                document_id=source.source_id,
                privacy_labels=("public",),
                language_hints=(source.language,),
            ))
        if checksum_errors or len(source_specs) != len(corpus.sources):
            return self._blocked_run(
                run_id=run_id,
                started_at=started_at,
                reason="corpus_file_or_checksum_invalid",
                cases=cases,
                extra={"corpus_kind": corpus.kind, "invalid_sources": checksum_errors},
            )
        try:
            bge = load_bge_eval_identity(self.deployment_manifest)
        except Exception as exc:
            return self._blocked_run(
                run_id=run_id,
                started_at=started_at,
                reason=f"bge_identity_unavailable:{type(exc).__name__}",
                cases=cases,
                extra={"corpus_kind": corpus.kind},
            )

        runtime_root = self.index_dir / run_id
        config = RagV2DevConfig(
            runtime_root=runtime_root,
            index_filename="chunk_eval.sqlite",
            max_chunk_chars=900,
            retrieval_profile="bge_m3_hybrid",
            bge_m3_model_path=bge["model_path"],
            bge_m3_model_revision=bge["revision"],
            bge_m3_model_checksum=bge["checksum"],
            retrieval_device=bge["device"],
            bge_m3_use_fp16=bge["use_fp16"],
            bge_m3_batch_size=1,
            strict_semantic=True,
            sqlite_check_same_thread=False,
            allowed_privacy_labels=("public", "cloud_safe", "local_only", "confidential"),
        )
        try:
            pipeline = RagV2DevPipeline(config, chunker=self._make_chunker())
        except Exception as exc:
            return self._blocked_run(
                run_id=run_id,
                started_at=started_at,
                reason=f"bge_backend_unavailable:{type(exc).__name__}",
                cases=cases,
                extra={"corpus_kind": corpus.kind},
            )
        chunker_name = pipeline.chunker.__class__.__name__
        try:
            prep_start = time.perf_counter()
            report = pipeline.ingest(source_specs)
            if report.failed_count or report.unsupported_count or report.converted_count == 0:
                return self._blocked_run(
                    run_id=run_id,
                    started_at=started_at,
                    reason="ingestion_failed",
                    cases=cases,
                    supported_path=chunker_name,
                    model_identity=bge["identity"],
                    extra={"corpus_kind": corpus.kind},
                )
            prep_ms = (time.perf_counter() - prep_start) * 1000.0
            pipeline.query(cases[0].question, source_specs)
            all_chunks = list(pipeline.index.iter_chunks()) if hasattr(pipeline.index, "iter_chunks") else []
            if not all_chunks:
                all_chunks = self._load_chunks_from_index(pipeline)
            outcomes: List[CaseOutcome] = []
            query_failures = 0
            for case in cases:
                t0 = time.perf_counter()
                try:
                    result = pipeline.query(case.question, source_specs)
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    if result.effective_path != "hybrid" or result.degraded:
                        query_failures += 1
                    outcomes.append(self._outcome_from_search(
                        case,
                        result.search_response,
                        all_chunks,
                        latency_ms,
                    ))
                except Exception:
                    query_failures += 1
                    outcomes.append(CaseOutcome(
                        case_id=case.case_id,
                        latency_ms=(time.perf_counter() - t0) * 1000.0,
                    ))
            index_path = config.index_path
            index_size = index_path.stat().st_size if index_path.is_file() else 0
            retrievable_count = sum(1 for chunk in all_chunks if getattr(chunk, "retrievable", True))
            chunk_lengths = [len(getattr(chunk, "text", "") or "") for chunk in all_chunks]
            metrics = StrategyMetrics.compute(
                outcomes, cases, chunk_lengths,
                preparation_duration_ms=prep_ms,
                index_size_bytes=index_size,
                retrievable_chunk_count=retrievable_count,
            )
            self._fill_language_chunk_lengths(metrics, cases, all_chunks)
        finally:
            pipeline.close()

        decision = "blocked" if query_failures else self._decision_for_successful_run()
        run = EvaluationRun(
            run_id=run_id,
            corpus_fingerprint=corpus_fingerprint(self.corpus_manifest_path),
            question_set_fingerprint=question_set_fingerprint(self.cases_path),
            strategy_id=self.strategy.strategy_id,
            model_identity=bge["identity"],
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            decision=decision,
            metrics=metrics,
            case_outcomes=outcomes,
            supported_path=chunker_name,
            legacy_chunkers_active=chunker_name != "StructureAwareChunker",
        )
        overlay = run.to_report_dict()
        overlay["corpus_kind"] = corpus.kind
        overlay["retrieval_path"] = "hybrid"
        overlay["legacy_chunkers_active"] = run.legacy_chunkers_active
        if decision == "blocked":
            overlay["blocked_reason"] = "hybrid_query_failure"
        privacy_ok, privacy_violations = validate_report_privacy(
            json.dumps(overlay, ensure_ascii=False),
            source_samples=source_samples,
        )
        overlay["privacy"] = {
            "raw_local_only_text_exported": not privacy_ok,
            "violations": privacy_violations,
        }
        if not privacy_ok:
            run.decision = "blocked"
            overlay["decision"] = "blocked"
            overlay["blocked_reason"] = "raw_local_only_text_exported"
        elif (
            not query_failures
            and not self._is_baseline_strategy()
            and self.baseline_report is not None
        ):
            decision, reason = classify_candidate_decision(overlay, self.baseline_report)
            run.decision = decision
            overlay["decision"] = decision
            overlay["comparison_reason"] = reason
            if decision == "blocked":
                overlay["blocked_reason"] = reason
        elif not query_failures and not self._is_baseline_strategy() and self.baseline_report is None:
            run.decision = "blocked"
            overlay["decision"] = "blocked"
            overlay["blocked_reason"] = "missing_baseline_comparison"
        overlay["boundary_policy"] = self.strategy.boundary_policy
        run._report_overlay = overlay  # type: ignore[attr-defined]
        return run

    def _decision_for_successful_run(self) -> str:
        if self._is_baseline_strategy():
            return "baseline"
        if self.baseline_report is None:
            return "blocked"
        return "neutral"

    def _load_chunks_from_index(self, pipeline: Any) -> List[Any]:
        rows = pipeline.index._conn.execute(
            "SELECT chunk_id, document_id, source_path, source_name, file_type, "
            "text, retrievable, metadata_json FROM chunks"
        ).fetchall()
        from .chunking import DocumentChunk

        chunks = []
        for row in rows:
            metadata = json.loads(row["metadata_json"] or "{}")
            chunks.append(DocumentChunk(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                source_path=row["source_path"],
                source_name=row["source_name"],
                file_type=row["file_type"],
                text=row["text"],
                normalized_text=(row["text"] or "").lower(),
                element_ids=tuple(metadata.get("element_ids") or ()),
                element_types=tuple(metadata.get("element_types") or ()),
                retrievable=bool(row["retrievable"]),
                metadata=metadata,
            ))
        return chunks

    def _search_cases(
        self,
        cases: Sequence[EvaluationCase],
        search_fn: Any,
        all_chunks: Sequence[Any],
    ) -> List[CaseOutcome]:
        outcomes: List[CaseOutcome] = []
        for case in cases:
            t0 = time.perf_counter()
            response = search_fn(case.question)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            outcomes.append(self._outcome_from_search(case, response, all_chunks, latency_ms))
        return outcomes

    def _outcome_from_search(
        self,
        case: EvaluationCase,
        response: Any,
        all_chunks: Sequence[Any],
        latency_ms: float,
    ) -> CaseOutcome:
        results = getattr(response, "results", ())
        retrieved_sources = tuple(dict.fromkeys(
            str(getattr(item, "source_name", "") or "")
            for item in results
            if getattr(item, "source_name", "")
        ))
        found = any(
            any(source_id_matches(retrieved, expected) for retrieved in retrieved_sources)
            or any(
                source_id_matches(str(getattr(item, "document_id", "")), expected)
                or source_id_matches(str(getattr(item, "source_path", "")), expected)
                for item in results
            )
            for expected in case.source_ids
        )
        detailed = found and any(
            not (
                (getattr(item, "metadata", {}) or {}).get("is_document_summary")
                or str(getattr(item, "file_type", "") or "") == "document_summary"
            )
            for item in results
        )
        boundary = {}
        if "boundary" in case.challenge_labels or "cjk-punctuation" in case.challenge_labels:
            boundary = analyze_source_chunk_boundaries(
                all_chunks, language=case.language, source_ids=case.source_ids,
            )
        return CaseOutcome(
            case_id=case.case_id,
            retrieved_source_ids=retrieved_sources,
            expected_evidence_found=found,
            detailed_evidence_present=bool(detailed),
            summary_used=inspect_summary_role(results, found),
            latency_ms=latency_ms,
            fallback_boundary_used=bool(boundary.get("fallback_boundary_used", False)),
            split_at_sentence_punctuation=boundary.get("split_at_sentence_punctuation"),
            boundary_char_position=boundary.get("boundary_char_position"),
        )

    @staticmethod
    def _fill_language_chunk_lengths(
        metrics: StrategyMetrics,
        cases: Sequence[EvaluationCase],
        chunks: Sequence[Any],
    ) -> None:
        source_lang = {}
        for case in cases:
            for source_id in case.source_ids:
                source_lang.setdefault(source_id, case.language)
        lengths: Dict[str, List[int]] = {}
        for chunk in chunks:
            language = None
            for source_id, lang in source_lang.items():
                if source_id_matches(str(getattr(chunk, "source_name", "")), source_id) or (
                    source_id_matches(str(getattr(chunk, "source_path", "")), source_id)
                ):
                    language = lang
                    break
            if language:
                lengths.setdefault(language, []).append(len(getattr(chunk, "text", "") or ""))
        for lang, values in lengths.items():
            breakdown = metrics.language_breakdown.get(lang)
            if breakdown is not None and values:
                breakdown.average_chunk_length = sum(values) / len(values)

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

        report = getattr(run, "_report_overlay", None) or run.to_report_dict()

        valid, errors = validate_report(report)
        if not valid:
            raise ValueError(f"Report validation failed: {errors}")
        privacy_ok, privacy_violations = validate_report_privacy(
            json.dumps(report, ensure_ascii=False),
        )
        if not privacy_ok:
            raise ValueError(f"Report privacy validation failed: {privacy_violations}")

        json_path = out / f"{run.run_id}_report.json"
        json_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        md_path = out / f"{run.run_id}_summary.md"
        md_path.write_text(
            format_evaluation_summary(run, extra=report),
            encoding="utf-8",
        )

        return run, json_path, md_path


# ---------------------------------------------------------------------------
# Markdown summary formatter
# ---------------------------------------------------------------------------

def format_evaluation_summary(
    run: EvaluationRun,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate human-readable Markdown summary of an evaluation run."""
    m = run.metrics or StrategyMetrics()
    extra = extra or {}
    lines = [
        f"# Chunk Evaluation Report: {run.run_id}",
        "",
        f"**Strategy**: {run.strategy_id}",
        f"**Decision**: {run.decision}",
        f"**Model**: {run.model_identity}",
        f"**Active Chunker**: {run.supported_path}",
        f"**Legacy Active**: {run.legacy_chunkers_active}",
        f"**Corpus kind**: {extra.get('corpus_kind', '')}",
        f"**Retrieval path**: {extra.get('retrieval_path', '')}",
        "",
    ]
    if extra.get("blocked_reason"):
        lines.extend([f"**Blocked reason**: `{extra['blocked_reason']}`", ""])
    if extra.get("comparison_reason"):
        lines.extend([f"**Comparison**: `{extra['comparison_reason']}`", ""])
    lines.extend([
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
    ])
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
