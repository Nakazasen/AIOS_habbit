# Data Model: Adaptive Retrieval

## SearchPreference

Conversation-scoped user choice.

| Field | Type | Allowed | Default | Notes |
|---|---|---|---|---|
| `mode` | string | `auto`, `deep` | `auto` | User-facing choice; no technical profile name. |
| `updated_at` | ISO timestamp | valid local timestamp | conversation update time | Optional for migration; do not infer user intent from absence. |

Persistence target: add a backward-compatible field to `WorkspaceConversation`. Old JSONL records without it load as `auto`. Invalid values fail safely to `auto` and produce only a safe diagnostic code.

## AdaptiveRetrievalPolicy

Immutable, versioned settings used to reproduce a decision.

| Field | Type | Constraint |
|---|---|---|
| `version` | string | non-empty stable identifier |
| `enabled` | bool | false by default |
| `uncertain_escalates` | bool | must be true in production |
| `min_evidence_coverage` | float | 0..1; set by frozen benchmark |
| `min_distinct_sources_by_intent` | mapping | bounded integer values |
| `minimum_candidate_count` | int | positive |
| `rerank_limit` | int | one of benchmark-approved bounds |
| `deep_timeout_ms` | int | positive, bounded |
| `circuit_breaker_failures` | int | positive |
| `circuit_breaker_cooldown_ms` | int | positive |

Policy values belong in deployment/config, not conversation data.

## PreRetrievalDecision

| Field | Type | Values |
|---|---|---|
| `classification` | enum | `fast`, `deep`, `uncertain` |
| `reason_codes` | tuple[string] | allow-listed, content-free codes |
| `policy_version` | string | policy used |
| `facet_count` | int | non-negative |
| `obligation_count` | int | non-negative |

Example reason codes: `user_requested_deep`, `multi_facet`, `cross_source_intent`, `comparison_intent`, `verification_requested`, `insufficient_structure_signal`.

## EvidenceSufficiencyAssessment

Created only after a Hybrid-first query on the Auto fast candidate path.

| Field | Type | Values/constraint |
|---|---|---|
| `classification` | enum | `sufficient`, `insufficient`, `uncertain` |
| `reason_codes` | tuple[string] | allow-listed |
| `evidence_coverage` | float | 0..1 |
| `distinct_source_count` | int | non-negative |
| `candidate_count` | int | non-negative |
| `missing_facet_count` | int | non-negative |
| `missing_obligation_count` | int | non-negative |
| `diversity_limited_count` | int | non-negative |

Example reason codes: `missing_facets`, `missing_obligations`, `low_evidence_coverage`, `insufficient_source_diversity`, `insufficient_candidates`, `ranking_ambiguous`, `retrieval_report_incomplete`.

## RoutingDecision

One decision per submitted question; does not persist raw question.

| Field | Type | Values |
|---|---|---|
| `user_preference` | enum | `auto`, `deep` |
| `pre_decision` | enum | `fast`, `deep`, `uncertain`, `not_applicable` |
| `post_decision` | enum | `sufficient`, `insufficient`, `uncertain`, `not_run` |
| `requested_path` | enum | `structured_excel`, `hybrid`, `hybrid_rerank` |
| `effective_path` | enum | `structured_excel`, `hybrid`, `hybrid_rerank`, `unavailable` |
| `reason_codes` | tuple[string] | ordered union of safe codes |
| `reranker_requested` | bool | derived from priority rules |
| `reranker_applied` | bool | true only after scores were used for final ranking |
| `degraded` | bool | requested and effective paths differ |
| `degraded_reason` | string | allow-listed safe code |
| `policy_version` | string | reproducibility |

### Invariants

1. `user_preference=deep` implies `requested_path=hybrid_rerank`.
2. `pre_decision=uncertain` implies `requested_path=hybrid_rerank`.
3. `post_decision in {insufficient, uncertain}` implies reranker requested unless circuit breaker already blocks it; blocked execution is degraded.
4. `reranker_applied=true` iff `effective_path=hybrid_rerank`.
5. `requested_path=hybrid_rerank` and `effective_path=hybrid` implies `degraded=true` and non-empty safe reason.
6. UI may say `Đã tìm kỹ` only when invariant 4 holds.

## RetrievalExecutionRecord

Ephemeral/loggable safe record for audit.

| Field | Type | Privacy |
|---|---|---|
| `routing` | RoutingDecision sans content | safe |
| `candidate_count` | int | safe |
| `returned_count` | int | safe |
| `distinct_source_count` | int | safe |
| `hybrid_latency_ms` | float | safe |
| `rerank_latency_ms` | float | safe |
| `total_latency_ms` | float | safe |
| `runtime_init_count` | int | safe |
| `circuit_state` | enum | safe |

Forbidden: question text/hash derived from short query, snippet text, titles, source paths, credentials, exception strings and model cache paths.

## State transitions

```text
SUBMITTED
  ├─ structured Excel applies ──> STRUCTURED_COMPLETE
  └─ text retrieval
       ├─ user deep/pre deep/uncertain ──> DEEP_REQUESTED
       │     ├─ reranker success ──> DEEP_COMPLETE
       │     └─ reranker failure ──> HYBRID_DEGRADED or UNAVAILABLE
       └─ pre fast ──> HYBRID_COMPLETE
             ├─ post sufficient ──> FAST_COMPLETE
             └─ post insufficient/uncertain ──> DEEP_REQUESTED
```

## Migration

- Existing conversation record without `search_preference`: load `auto`.
- Existing deployment manifest schema v2: adaptive capability false, Hybrid behavior unchanged.
- New manifest: validate both BGE-M3 and reranker artifacts plus benchmark evidence.
- Disabling adaptive capability does not remove conversation preference; execution reports a safe unavailable/degraded state if user still requests Deep, and UI explains it.
