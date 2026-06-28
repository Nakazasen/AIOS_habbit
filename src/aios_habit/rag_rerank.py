from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

from aios_habit.rag_search import RAGSearchResult


@dataclass(frozen=True)
class RerankTrace:
    chunk_id: str
    original_rank: int
    reranked_rank: int
    original_score: float
    rerank_score: float
    matched_terms: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class RerankResult:
    results: List[RAGSearchResult]
    traces: List[RerankTrace]
    reranker_name: str = "deterministic_token_overlap_v1"
    provider_call: bool = False
    vector_db: bool = False
    graph_db: bool = False


def tokenize_query(query: str) -> List[str]:
    tokens = re.findall(r"[\w]+", query.lower())
    seen = set()
    ordered = []
    for token in tokens:
        if len(token) < 2 or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def rerank_search_results(query: str, results: List[RAGSearchResult]) -> RerankResult:
    """Rerank search results with a deterministic local token-overlap heuristic."""
    terms = tokenize_query(query)
    scored = []
    for index, result in enumerate(results):
        haystack = f"{result.text} {result.source_title} {result.citation_label}".lower()
        matched = [term for term in terms if term in haystack]
        coverage = len(matched) / len(terms) if terms else 0.0
        rerank_score = result.score + coverage + (0.05 * len(matched))
        scored.append((result, matched, rerank_score, index))

    scored.sort(key=lambda row: (-row[2], row[3], row[0].chunk_id))
    reranked = []
    traces = []
    for new_rank, (result, matched, score, _index) in enumerate(scored, start=1):
        reranked_result = RAGSearchResult(
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            text=result.text,
            score=score,
            rank=new_rank,
            citation_label=result.citation_label,
            source_title=result.source_title,
            relative_path=result.relative_path,
            file_type=result.file_type,
            privacy_mode=result.privacy_mode,
            page_numbers=result.page_numbers,
            sheet_names=result.sheet_names,
            slide_numbers=result.slide_numbers,
            element_types=result.element_types,
            metadata={**result.metadata, "reranker": "deterministic_token_overlap_v1"},
        )
        reranked.append(reranked_result)
        traces.append(RerankTrace(result.chunk_id, result.rank, new_rank, result.score, score, matched))
    return RerankResult(reranked, traces)
