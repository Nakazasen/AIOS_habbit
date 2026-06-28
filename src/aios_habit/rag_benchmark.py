import hashlib
import time
import sqlite3
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from aios_habit.rag_ingest import RAGChunk
from aios_habit.rag_search import (
    RAGSearchResult, search_rag_chunks,
    create_rag_search_schema, index_rag_chunks
)
from aios_habit.rag_evidence import RAGEvidencePack, build_evidence_pack

@dataclass
class RAGBenchmarkQuestion:
    question_id: str
    question: str
    expected_answer_type: str
    expected_chunk_ids: List[str] = field(default_factory=list)
    expected_document_ids: List[str] = field(default_factory=list)
    expected_citation_labels: List[str] = field(default_factory=list)
    expected_privacy_mode: str = "cloud_safe"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass
class RAGBenchmarkResult:
    question_id: str
    question: str
    expected_answer_type: str
    retrieved_chunk_ids: List[str] = field(default_factory=list)
    retrieved_document_ids: List[str] = field(default_factory=list)
    retrieved_citation_labels: List[str] = field(default_factory=list)
    evidence_pack_id: str = ""
    evidence_item_count: int = 0
    top_score: float = 0.0
    confidence_label: str = "none"
    insufficient_evidence: bool = True
    hit_expected_chunk: bool = False
    hit_expected_document: bool = False
    hit_expected_citation: bool = False
    privacy_ok: bool = False
    latency_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass
class RAGBenchmarkSummary:
    benchmark_id: str
    question_count: int
    answerable_count: int
    insufficient_count: int
    top_chunk_hit_rate: float
    document_hit_rate: float
    citation_hit_rate: float
    insufficient_detection_rate: float
    privacy_pass_rate: float
    average_latency_ms: float
    pass_fail: str
    warnings: List[str] = field(default_factory=list)
    results: List[RAGBenchmarkResult] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

@dataclass
class RAGBenchmarkConfig:
    tier: str = "custom"
    top_k: int = 10
    min_top_chunk_hit_rate: float = 0.8
    min_document_hit_rate: float = 0.9
    min_citation_hit_rate: float = 0.8
    min_insufficient_detection_rate: float = 0.8
    min_privacy_pass_rate: float = 1.0
    max_average_latency_ms: float = 500.0

def stable_benchmark_id(questions: List[RAGBenchmarkQuestion], config: RAGBenchmarkConfig) -> str:
    h = hashlib.sha256()
    payload = {
        "config": asdict(config),
        "questions": [asdict(q) for q in questions],
    }
    h.update(json_dumps(payload).encode("utf-8"))
    return "BMK-" + h.hexdigest()[:10].upper()

def json_dumps(payload: Dict[str, Any]) -> str:
    return __import__("json").dumps(payload, sort_keys=True, separators=(",", ":"))

def score_benchmark_result(question: RAGBenchmarkQuestion, search_results: List[RAGSearchResult], evidence_pack: RAGEvidencePack, latency_ms: float) -> RAGBenchmarkResult:
    retrieved_chunk_ids = [r.chunk_id for r in search_results]
    retrieved_document_ids = [r.document_id for r in search_results if r.document_id]
    retrieved_citation_labels = [r.citation_label for r in search_results if r.citation_label]
    
    hit_expected_chunk = any(cid in retrieved_chunk_ids for cid in question.expected_chunk_ids) if question.expected_chunk_ids else False
    hit_expected_document = any(did in retrieved_document_ids for did in question.expected_document_ids) if question.expected_document_ids else False
    hit_expected_citation = any(cl in retrieved_citation_labels for cl in question.expected_citation_labels) if question.expected_citation_labels else False
    
    # Check privacy rule: if expected was local_only, pack must be local_only
    # If expected was cloud_safe, pack can be cloud_safe or local_only (which is safer)
    privacy_ok = True
    if question.expected_privacy_mode == "local_only" and evidence_pack.privacy_mode != "local_only":
        privacy_ok = False
    if question.expected_privacy_mode == "redacted" and evidence_pack.privacy_mode not in ["redacted", "local_only"]:
        privacy_ok = False
        
    return RAGBenchmarkResult(
        question_id=question.question_id,
        question=question.question,
        expected_answer_type=question.expected_answer_type,
        retrieved_chunk_ids=retrieved_chunk_ids,
        retrieved_document_ids=retrieved_document_ids,
        retrieved_citation_labels=retrieved_citation_labels,
        evidence_pack_id=evidence_pack.pack_id,
        evidence_item_count=len(evidence_pack.items),
        top_score=search_results[0].score if search_results else 0.0,
        confidence_label=evidence_pack.confidence_label,
        insufficient_evidence=evidence_pack.insufficient_evidence,
        hit_expected_chunk=hit_expected_chunk,
        hit_expected_document=hit_expected_document,
        hit_expected_citation=hit_expected_citation,
        privacy_ok=privacy_ok,
        latency_ms=latency_ms,
        warnings=[],
        metadata={}
    )

def summarize_benchmark_results(results: List[RAGBenchmarkResult], config: RAGBenchmarkConfig) -> RAGBenchmarkSummary:
    answerable_results = [r for r in results if r.expected_answer_type == "answerable"]
    insufficient_results = [r for r in results if r.expected_answer_type == "insufficient"]
    
    q_count = len(results)
    ans_count = len(answerable_results)
    ins_count = len(insufficient_results)
    
    top_chunk_hit_rate = sum(1 for r in answerable_results if r.hit_expected_chunk) / ans_count if ans_count > 0 else 1.0
    document_hit_rate = sum(1 for r in answerable_results if r.hit_expected_document) / ans_count if ans_count > 0 else 1.0
    citation_hit_rate = sum(1 for r in answerable_results if r.hit_expected_citation) / ans_count if ans_count > 0 else 1.0
    
    insufficient_detection_rate = sum(1 for r in insufficient_results if r.insufficient_evidence) / ins_count if ins_count > 0 else 1.0
    privacy_pass_rate = sum(1 for r in results if r.privacy_ok) / q_count if q_count > 0 else 1.0
    average_latency_ms = sum(r.latency_ms for r in results) / q_count if q_count > 0 else 0.0
    
    warnings = []
    if top_chunk_hit_rate < config.min_top_chunk_hit_rate:
        warnings.append(f"Top chunk hit rate {top_chunk_hit_rate:.2f} < {config.min_top_chunk_hit_rate}")
    if document_hit_rate < config.min_document_hit_rate:
        warnings.append(f"Document hit rate {document_hit_rate:.2f} < {config.min_document_hit_rate}")
    if citation_hit_rate < config.min_citation_hit_rate:
        warnings.append(f"Citation hit rate {citation_hit_rate:.2f} < {config.min_citation_hit_rate}")
    if insufficient_detection_rate < config.min_insufficient_detection_rate:
        warnings.append(f"Insufficient detection rate {insufficient_detection_rate:.2f} < {config.min_insufficient_detection_rate}")
    if privacy_pass_rate < config.min_privacy_pass_rate:
        warnings.append(f"Privacy pass rate {privacy_pass_rate:.2f} < {config.min_privacy_pass_rate}")
    if average_latency_ms > config.max_average_latency_ms:
        warnings.append(f"Average latency {average_latency_ms:.2f}ms > {config.max_average_latency_ms}ms")
        
    if privacy_pass_rate < config.min_privacy_pass_rate:
        pass_fail = "FAIL"
    elif len(warnings) == 0:
        pass_fail = "PASS"
    elif any("hit rate" in w or "detection rate" in w for w in warnings):
        pass_fail = "FAIL"
    else:
        pass_fail = "PASS_WITH_WARNINGS"
        
    return RAGBenchmarkSummary(
        benchmark_id="", # filled by runner
        question_count=q_count,
        answerable_count=ans_count,
        insufficient_count=ins_count,
        top_chunk_hit_rate=top_chunk_hit_rate,
        document_hit_rate=document_hit_rate,
        citation_hit_rate=citation_hit_rate,
        insufficient_detection_rate=insufficient_detection_rate,
        privacy_pass_rate=privacy_pass_rate,
        average_latency_ms=average_latency_ms,
        pass_fail=pass_fail,
        warnings=warnings,
        results=results
    )

def run_rag_benchmark(chunks: List[RAGChunk], questions: List[RAGBenchmarkQuestion], config: Optional[RAGBenchmarkConfig] = None) -> RAGBenchmarkSummary:
    if config is None:
        config = RAGBenchmarkConfig()
    if config.tier not in {"20Q", "50Q", "100Q", "custom"}:
        raise ValueError(f"Unsupported benchmark tier: {config.tier}")
        
    conn = sqlite3.connect(":memory:")
    create_rag_search_schema(conn)
    index_rag_chunks(conn, chunks)
    
    results = []
    for q in questions:
        t0 = time.time()
        search_results = search_rag_chunks(conn, q.question, limit=config.top_k)
        evidence_pack = build_evidence_pack(q.question, search_results)
        latency_ms = (time.time() - t0) * 1000.0
        
        result = score_benchmark_result(q, search_results, evidence_pack, latency_ms)
        results.append(result)
        
    conn.close()
    
    summary = summarize_benchmark_results(results, config)
    summary.benchmark_id = stable_benchmark_id(questions, config)
    return summary

def benchmark_summary_to_dict(summary: RAGBenchmarkSummary) -> Dict[str, Any]:
    return asdict(summary)

def format_benchmark_summary(summary: RAGBenchmarkSummary) -> str:
    lines = []
    lines.append(f"AIOS RAG Benchmark Summary: {summary.benchmark_id}")
    lines.append(f"Result: {summary.pass_fail}")
    lines.append("Note: This measures retrieval/evidence only, NOT an LLM generation parity claim vs NotebookLM.")
    lines.append(f"Questions: {summary.question_count} ({summary.answerable_count} answerable, {summary.insufficient_count} insufficient)")
    lines.append(f"Metrics:")
    lines.append(f" - Top Chunk Hit Rate: {summary.top_chunk_hit_rate:.2f}")
    lines.append(f" - Document Hit Rate: {summary.document_hit_rate:.2f}")
    lines.append(f" - Citation Hit Rate: {summary.citation_hit_rate:.2f}")
    lines.append(f" - Insuff Detection: {summary.insufficient_detection_rate:.2f}")
    lines.append(f" - Privacy Pass Rate: {summary.privacy_pass_rate:.2f}")
    lines.append(f" - Avg Latency: {summary.average_latency_ms:.2f} ms")
    if summary.warnings:
        lines.append("Warnings:")
        for w in summary.warnings:
            lines.append(f" - {w}")
    return "\n".join(lines)
