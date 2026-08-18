# Contract: Adaptive Retrieval Routing

## Public adapter contract

```python
def retrieve_workspace_chat_evidence(
    question: str,
    context_sources: Iterable[WorkspaceAIContextSource],
    *,
    search_preference: Literal["auto", "deep"] = "auto",
    config: WorkspaceChatRagV2CanaryConfig | None = None,
    pipeline_factory: Callable[[RagV2DevConfig], RagV2DevPipeline] = RagV2DevPipeline,
    expansion: Mapping[str, Any] | None = None,
) -> dict[str, Any]: ...
```

Rules:

1. Validate `search_preference`; invalid input becomes `auto` plus safe reason code, never a technical exception shown to the user.
2. Structured Excel is evaluated first.
3. `deep` always requests reranker.
4. `auto` uses deterministic pre/post gates.
5. Return shape remains backward compatible; new fields live under `rag_v2_canary.routing` and optional user-safe status fields.

## Pipeline contract

```python
def query(
    self,
    question: str | RetrievalQueryPlan,
    sources: Iterable[SourceSpec],
    *,
    rerank_requested: bool = False,
    routing_reason_codes: tuple[str, ...] = (),
    expansion: Mapping[str, Any] | None = None,
    evidence_config: EvidencePackConfig | None = None,
) -> RagV2QueryResult: ...
```

- `rerank_requested=True` requires adaptive capability and an available pinned backend.
- A reranker runtime failure may produce a Hybrid response only with explicit degraded metadata.
- Privacy/source allow-lists are applied before reranking and cannot be broadened by routing.

## Worker request schema

```json
{
  "command": "query",
  "question": "local IPC only; never copied to telemetry",
  "specs": [],
  "expansion": {},
  "routing": {
    "schema_version": 1,
    "rerank_requested": true,
    "reason_codes": ["user_requested_deep"],
    "policy_version": "adaptive-reranking-v1"
  }
}
```

Validation:

- reject unknown routing schema version;
- require boolean `rerank_requested`;
- reason codes must be strings from an allow-list, maximum 8 values, maximum 48 characters each;
- policy version maximum 64 safe characters;
- do not echo `question`, source paths or exception strings in response/error telemetry.

## Worker response extension

```json
{
  "status": "ok",
  "query_result": {
    "summary": {},
    "items": [],
    "routing": {
      "reranker_requested": true,
      "reranker_applied": true,
      "effective_path": "hybrid_rerank",
      "degraded": false,
      "degraded_reason": "",
      "rerank_latency_ms": 842.1,
      "policy_version": "adaptive-reranking-v1"
    }
  }
}
```

## Workspace Chat safe telemetry

```json
{
  "rag_v2_canary": {
    "canary_enabled": true,
    "backend": "rag_v2_subprocess",
    "requested_profile": "bge_m3_hybrid",
    "effective_profile": "bge_m3_hybrid",
    "fallback_applied": false,
    "fallback_reason": "",
    "routing": {
      "search_preference": "deep",
      "pre_decision": "not_applicable",
      "post_decision": "not_run",
      "requested_path": "hybrid_rerank",
      "effective_path": "hybrid_rerank",
      "reason_codes": ["user_requested_deep"],
      "reranker_requested": true,
      "reranker_applied": true,
      "degraded": false,
      "degraded_reason": "",
      "policy_version": "adaptive-reranking-v1"
    },
    "latency_ms": 1640.2,
    "hybrid_latency_ms": 731.4,
    "rerank_latency_ms": 842.1,
    "candidate_count": 20,
    "returned_count": 10
  }
}
```

Compatibility fields `requested_profile`, `effective_profile`, `fallback_applied` and `fallback_reason` remain present. New consumers should use `routing.requested_path/effective_path` to distinguish per-query reranking.

## User-facing status contract

| Condition | Required copy |
|---|---|
| Auto, Hybrid success | `Đã tìm trong nguồn đang bật.` |
| Deep requested/running | `Đang tìm kỹ trong nguồn...` |
| Reranker applied | `Đã tìm kỹ trong nguồn đang bật.` |
| Deep degraded to Hybrid | `Đã tìm theo chế độ thường vì Tìm kỹ hiện chưa sẵn sàng.` |
| No sufficient evidence | Existing Vietnamese limitation/abstention copy; must not imply Deep success. |

## Forbidden behavior

- A generative provider is the sole route authority.
- `deep` is changed to Hybrid without `degraded=true`.
- UI displays `Đã tìm kỹ` when `reranker_applied=false`.
- Model load or network download starts inside interactive query.
- Telemetry includes raw question, evidence text, source title/path, secret or exception detail.
