from aios_habit.rag_rerank import rerank_search_results, tokenize_query
from aios_habit.rag_search import RAGSearchResult


def _result(chunk_id, text, score, rank):
    return RAGSearchResult(
        chunk_id=chunk_id, document_id="D"+chunk_id, text=text, score=score, rank=rank,
        citation_label="Citation "+chunk_id, source_title="Source", relative_path="safe.txt",
        file_type="text", privacy_mode="cloud_safe", page_numbers=[], sheet_names=[],
        slide_numbers=[], element_types=["text"], metadata={},
    )


def test_tokenize_query_is_stable_and_unique():
    assert tokenize_query("Route route code, export!") == ["route", "code", "export"]


def test_rerank_search_results_promotes_better_overlap_without_external_calls():
    results = [
        _result("1", "generic dispatch note", 1.0, 1),
        _result("2", "export mapping route code missing", 0.8, 2),
    ]
    reranked = rerank_search_results("export mapping route code", results)
    assert reranked.provider_call is False
    assert reranked.vector_db is False
    assert reranked.graph_db is False
    assert [r.chunk_id for r in reranked.results] == ["2", "1"]
    assert reranked.results[0].rank == 1
    assert reranked.traces[0].matched_terms == ["export", "mapping", "route", "code"]


def test_rerank_search_results_is_deterministic_for_ties():
    results = [
        _result("B", "same token", 1.0, 1),
        _result("A", "same token", 1.0, 2),
    ]
    first = rerank_search_results("same", results)
    second = rerank_search_results("same", results)
    assert [r.chunk_id for r in first.results] == [r.chunk_id for r in second.results]
    assert [r.chunk_id for r in first.results] == ["B", "A"]
