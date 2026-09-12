"""Tests for Non-blocking RAG (Partial Ready Search) and Graceful Degradation for Deep Search."""
from pathlib import Path
import pytest

from aios_habit.rag_v2.adaptive_retrieval import (
    AdaptiveRetrievalPolicy,
    EvidenceSufficiencyAssessment,
    PostDecision,
    PreDecision,
    PreRetrievalDecision,
    RetrievalPath,
    RoutingDecision,
    SearchPreferenceMode,
    decide_final_route,
    decide_initial_route,
)
from aios_habit.rag_v2.pipeline import (
    RagV2DevConfig,
    RagV2DevPipeline,
    SourceSpec,
)
from aios_habit.rag_v2.query_planning import RetrievalQueryPlan, RetrievalQueryVariant
from aios_habit.rag_v2.semantic import DeterministicEmbeddingBackend
from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_rag_v2_adapter import (
    _PREPARATION_READY_STATE,
    WorkspaceChatRagV2CanaryConfig,
    _semantic_readiness,
    retrieve_workspace_chat_evidence,
)


def _make_plan(text: str = "tìm tài liệu", intent: str = "factual") -> RetrievalQueryPlan:
    return RetrievalQueryPlan(
        original_query=text,
        variants=(RetrievalQueryVariant(text=text, variant_id="v1", facet_id="f1"),),
        content_terms=tuple(text.lower().split()),
        intent_category=intent,
        required_obligations=("query",),
    )


def _make_source(source_id: str, title: str, text: str) -> WorkspaceAIContextSource:
    return WorkspaceAIContextSource(
        source_id=source_id,
        source_scope="notebook",
        source_type="text",
        title=title,
        privacy_label="local_only",
        text=text,
        included_chars=len(text),
        truncated=False,
    )


def test_adaptive_initial_route_degrades_when_reranker_not_configured():
    """When reranker is not configured, initial routing degrades smoothly to HYBRID."""
    policy = AdaptiveRetrievalPolicy(reranker_configured=False)
    pre_dec = PreRetrievalDecision(
        classification=PreDecision.DEEP,
        reason_codes=("user_requested_deep",),
        policy_version=policy.version,
    )

    decision = decide_initial_route(pre_dec, user_preference="deep", policy=policy)

    assert decision.requested_path == RetrievalPath.HYBRID_RERANK
    assert decision.effective_path == RetrievalPath.HYBRID
    assert decision.reranker_requested is False
    assert decision.degraded is True
    assert decision.degraded_reason == "reranker_not_configured"


def test_adaptive_final_route_preserves_reranker_not_configured_degradation():
    """Decide final route retains degraded state when initial route fell back."""
    policy = AdaptiveRetrievalPolicy(reranker_configured=False)
    initial_routing = RoutingDecision(
        user_preference=SearchPreferenceMode.DEEP,
        pre_decision=PreDecision.DEEP,
        post_decision=PostDecision.NOT_RUN,
        requested_path=RetrievalPath.HYBRID_RERANK,
        effective_path=RetrievalPath.HYBRID,
        reason_codes=("user_requested_deep",),
        reranker_requested=False,
        reranker_applied=False,
        degraded=True,
        degraded_reason="reranker_not_configured",
        policy_version=policy.version,
    )
    assessment = EvidenceSufficiencyAssessment(
        classification=PostDecision.SUFFICIENT,
        reason_codes=("post_sufficient",),
    )

    final_route = decide_final_route(
        initial_routing,
        assessment,
        reranker_applied=False,
        effective_path=RetrievalPath.HYBRID,
        policy=policy,
    )

    assert final_route.degraded is True
    assert final_route.degraded_reason == "reranker_not_configured"
    assert final_route.effective_path == RetrievalPath.HYBRID


def test_pipeline_init_falls_back_to_hybrid_when_reranker_path_is_none(tmp_path: Path):
    """Pipeline initialization does not throw when bge_reranker_model_path is None."""
    config = RagV2DevConfig(
        runtime_root=tmp_path / "rag",
        retrieval_profile="bge_m3_hybrid_rerank",
        bge_reranker_model_path=None,
        strict_semantic=True,
    )
    emb_backend = DeterministicEmbeddingBackend(dimension=8)

    pipeline = RagV2DevPipeline(config, embedding_backend=emb_backend)

    assert pipeline._effective_retrieval_profile == "hybrid"
    assert pipeline._degraded_reason == "reranker_not_configured"

    report = pipeline.inspect()
    assert report["retrieval"]["degraded"] is True
    assert report["retrieval"]["degraded_reason"] == "reranker_not_configured"
    assert report["retrieval"]["reranker"]["backend"] == "not_configured"
    assert report["retrieval"]["reranker"]["reason"] == "reranker_not_configured"


def test_pipeline_query_degrades_gracefully_when_rerank_requested_without_reranker(tmp_path: Path):
    """Querying with rerank_requested degrades to hybrid without crashing."""
    source_file = tmp_path / "data.txt"
    source_file.write_text("Nội dung kiểm tra hệ thống AIOS habit retrieval.", encoding="utf-8")
    source = SourceSpec(source_file)

    config = RagV2DevConfig(
        runtime_root=tmp_path / "rag",
        retrieval_profile="hybrid",
        bge_reranker_model_path=None,
        strict_semantic=False,
    )
    emb_backend = DeterministicEmbeddingBackend(dimension=8)
    pipeline = RagV2DevPipeline(config, embedding_backend=emb_backend)
    pipeline.ingest((source,))

    plan = _make_plan("kiểm tra hệ thống")
    res = pipeline.query(plan, sources=(source,), rerank_requested=True)

    assert res.effective_path == "hybrid"
    assert res.degraded is True
    assert res.degraded_reason == "reranker_not_configured"
    assert res.reranker_applied is False
    assert len(res.search_response.results) > 0


def test_semantic_readiness_partial_ready_returns_ready(monkeypatch):
    """When at least one source is ready, _semantic_readiness returns READY without failing."""
    s1 = _make_source("s1", "Ready Doc", "Content of ready document.")
    s2 = _make_source("s2", "Pending Doc", "Content of pending document.")
    s3 = _make_source("s3", "Failed Doc", "Content of failed document.")

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.get_workspace_chat_source_preparation_status",
        lambda sources, config=None: {
            "notebook:s1": _PREPARATION_READY_STATE,
            "notebook:s2": "processing",
            "notebook:s3": "failed",
        },
    )

    config = WorkspaceChatRagV2CanaryConfig(enabled=True)
    status, reason = _semantic_readiness((s1, s2, s3), config)

    assert status == _PREPARATION_READY_STATE
    assert reason == ""


def test_retrieve_workspace_chat_evidence_operates_on_ready_sources_with_pending_others(monkeypatch):
    """retrieve_workspace_chat_evidence retrieves evidence on ready sources when other sources are unready."""
    ready_source = _make_source("ready_1", "Sổ tay hướng dẫn", "Quy trình vận hành chuẩn của hệ thống.")
    unready_source = _make_source("unready_1", "Tài liệu chưa xong", "Chưa hoàn tất xử lý.")

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.get_workspace_chat_source_preparation_status",
        lambda sources, config=None: {
            "notebook:ready_1": _PREPARATION_READY_STATE,
            "notebook:unready_1": "pending",
        },
    )

    called_with_sources = []

    def fake_run_profile(question, semantic_sources, *args, **kwargs):
        called_with_sources.extend(semantic_sources)
        return {
            "status": "ok",
            "retrieval_applied": True,
            "evidence_items": [
                {
                    "snippet_index": 1,
                    "source_id": "ready_1",
                    "source_scope": "notebook",
                    "source_type": "text",
                    "title": "Sổ tay hướng dẫn",
                    "text": "Quy trình vận hành chuẩn của hệ thống.",
                    "score": 0.95,
                    "citation_id": "c1",
                    "evidence_id": "e1",
                }
            ],
            "items": [],
            "retrieved_context_sources": tuple(semantic_sources),
            "summary_count": 1,
            "summary": {"evidence_set_term_coverage": 0.8},
            "citations": [],
            "rag_v2_canary": {
                "degraded": False,
                "degraded_reason": "",
                "effective_path": "hybrid",
            },
        }

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter._run_profile",
        fake_run_profile,
    )

    config = WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        adaptive_enabled=True,
        bge_reranker_model_path=None,
    )

    result = retrieve_workspace_chat_evidence(
        "vận hành chuẩn",
        (ready_source, unready_source),
        config=config,
    )

    assert result.get("status") != "quality_search_unavailable"
    assert result["retrieval_applied"] is True
    assert len(called_with_sources) == 1
    assert called_with_sources[0].source_id == "ready_1"


def test_deep_search_gracefully_degrades_when_reranker_not_configured(monkeypatch):
    """Deep search preference degrades to hybrid when adaptive_enabled is true but reranker is absent."""
    source = _make_source("s1", "Tài liệu", "Nội dung tài liệu.")

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.get_workspace_chat_source_preparation_status",
        lambda sources, config=None: {
            "notebook:s1": _PREPARATION_READY_STATE,
        },
    )

    passed_rerank_requested = []

    def fake_run_profile(question, semantic_sources, resolved, profile, *args, **kwargs):
        passed_rerank_requested.append(kwargs.get("rerank_requested"))
        return {
            "status": "ok",
            "retrieval_applied": True,
            "evidence_items": [
                {
                    "snippet_index": 1,
                    "source_id": "s1",
                    "source_scope": "notebook",
                    "source_type": "text",
                    "title": "Tài liệu",
                    "text": "Nội dung.",
                    "score": 0.9,
                    "citation_id": "c1",
                    "evidence_id": "e1",
                }
            ],
            "items": [],
            "retrieved_context_sources": tuple(semantic_sources),
            "summary_count": 1,
            "summary": {},
            "citations": [],
            "rag_v2_canary": {
                "degraded": False,
                "degraded_reason": "",
                "effective_path": "hybrid",
            },
        }

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter._run_profile",
        fake_run_profile,
    )

    config = WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        adaptive_enabled=True,
        bge_reranker_model_path=None,
    )

    result = retrieve_workspace_chat_evidence(
        "chi tiết sâu",
        (source,),
        config=config,
        search_preference="deep",
    )

    assert result.get("status") != "quality_search_unavailable"
    assert result["retrieval_applied"] is True
    # Reranker was not requested in _run_profile because routing degraded it
    assert passed_rerank_requested == [False]
    assert result["rag_v2_canary"]["degraded"] is True
    assert result["rag_v2_canary"]["degraded_reason"] == "reranker_not_configured"


def test_sanitize_degraded_reason_allows_reranker_not_configured():
    """_sanitize_degraded_reason must preserve reranker_not_configured without falling back to reranker_backend_failed."""
    from aios_habit.workspace_chat_rag_v2_adapter import _sanitize_degraded_reason
    assert _sanitize_degraded_reason("reranker_not_configured") == "reranker_not_configured"
    assert _sanitize_degraded_reason("unknown_code") == "reranker_backend_failed"


def test_pipeline_expand_profile_degrades_gracefully_with_strict_semantic(tmp_path: Path):
    """bge_m3_hybrid_rerank_expand with strict_semantic=True degrades to hybrid when reranker is None."""
    config = RagV2DevConfig(
        runtime_root=tmp_path / "rag",
        retrieval_profile="bge_m3_hybrid_rerank_expand",
        bge_reranker_model_path=None,
        strict_semantic=True,
    )
    emb_backend = DeterministicEmbeddingBackend(dimension=8)
    pipeline = RagV2DevPipeline(config, embedding_backend=emb_backend)

    assert pipeline._effective_retrieval_profile == "hybrid"
    assert pipeline._degraded_reason == "reranker_not_configured"


def test_retrieve_workspace_chat_evidence_updates_collection_id_for_ready_subset(monkeypatch):
    """retrieve_workspace_chat_evidence updates collection_id and query scope to ready_subset."""
    s1 = _make_source("s1", "Ready Doc", "Nội dung sẵn sàng.")
    s2 = _make_source("s2", "Pending Doc", "Nội dung chưa xong.")

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.get_workspace_chat_source_preparation_status",
        lambda sources, config=None: {
            "notebook:s1": _PREPARATION_READY_STATE,
            "notebook:s2": "pending",
        },
    )

    captured_args = {}

    def fake_run_profile(question, semantic_sources, resolved, profile, *args, **kwargs):
        captured_args["sources"] = semantic_sources
        return {
            "status": "ok",
            "retrieval_applied": True,
            "evidence_items": [],
            "items": [],
            "retrieved_context_sources": tuple(semantic_sources),
            "summary_count": 0,
            "summary": {},
            "citations": [],
            "rag_v2_canary": {
                "degraded": False,
                "degraded_reason": "",
                "effective_path": "hybrid",
            },
        }

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter._run_profile",
        fake_run_profile,
    )

    config = WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        adaptive_enabled=True,
        bge_reranker_model_path=None,
    )

    result = retrieve_workspace_chat_evidence(
        "hỏi đáp",
        (s1, s2),
        config=config,
    )

    assert result["retrieval_applied"] is True
    assert len(captured_args["sources"]) == 1
    assert captured_args["sources"][0].source_id == "s1"

