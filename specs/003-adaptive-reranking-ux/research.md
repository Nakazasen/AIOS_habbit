# Research: Adaptive Reranking UX

**Date**: 2026-08-16  
**Status**: Decisions ready for implementation; measurements still required before activation

## Current-state findings

- Workspace Chat production adapter currently allow-lists only `bge_m3_hybrid` and always builds `RagV2DevConfig(retrieval_profile="bge_m3_hybrid")`.
- The underlying RAG v2 pipeline already supports `bge_m3_hybrid_rerank`, a local BGE reranker backend, bounded `rerank_limit`, rerank latency and fallback behavior in tests.
- The production deployment validator currently approves only the pinned BGE-M3 Hybrid identity and a manifest schema v2. Adaptive activation must not silently weaken these gates.
- The index compatibility fingerprint intentionally excludes query-time reranking controls, so an adaptive feature can reuse the current expensive index.
- `SearchSummary` already exposes most post-retrieval signals needed: insufficiency reasons, term/facet/obligation coverage, diversity limits, candidate pools and per-stage latency.
- Structured Excel retrieval runs before text Hybrid in the adapter and must stay there.
- The subprocess worker accepts one active pipeline configuration. Switching whole profiles per question would cause configuration mismatch or reload risk; per-query rerank selection within one initialized pipeline is the safer extension.

## Decision 1: Product control is Auto plus user Deep override

**Decision**: Show `Tự động` and `Tìm kỹ hơn (có thể chậm hơn)`. Persist the choice per conversation. User Deep always wins over auto classification.

**Why**: A user knows when certainty matters even if the query looks simple. Outcome language is understandable; technical profile selection is not.

**Rejected**:

- Expose `Hybrid`/`Reranker`: leaks implementation details and makes users tune internals.
- Fully automatic with no override: cannot represent the user's risk tolerance.
- Always rerank: wastes CPU/RAM and harms simple-query latency on the target laptop.

## Decision 2: No generative model is the sole router

**Decision**: Use deterministic pre-query signals plus a post-Hybrid sufficiency gate. An optional learned/LLM classifier may be added later only as an extra signal and may never override `user_deep` or downgrade `uncertain`.

**Why**: The decision becomes reproducible, testable and auditable. The post gate catches deceptively simple questions whose first evidence is weak.

**Rejected**:

- Ask the answer model `easy or hard?`: nondeterministic, hard to audit, may bias toward the cheaper path, and adds provider/privacy coupling.
- Keyword-only routing: language and phrasing vary; a keyword is not enough evidence that a query is safe for the fast path.
- Pre-query routing only: cannot observe weak, duplicated, single-source or contradictory evidence.

## Decision 3: Conservative three-state policy

**Decision**: Pre/post gates return `fast`, `deep` or `uncertain`. Only explicit `fast` from both applicable checks remains Hybrid-only; `deep` and `uncertain` use reranker.

**Why**: It directly prevents an unknown case from being silently treated as easy. Distribution tests can detect all-fast/all-deep regressions.

## Decision 4: Reuse one local worker and one index

**Decision**: Initialize the existing BGE worker with optional pinned reranker capability and pass a validated `rerank_requested` field per query. Base index identity stays BGE-M3 Hybrid.

**Why**: Index rebuild is unnecessary; the existing process boundary already contains heavy model failure. One worker avoids concurrent CPU/RAM spikes.

**Rejected**:

- Start a new process/model during a user request: creates cold-start stalls and violates current non-starting query behavior.
- Separate always-on reranker worker: duplicates runtime coordination and may increase peak RAM on 16 GB.
- Change `requested_profile` back and forth: incompatible with current worker config equality and deployment identity.

## Decision 5: Model and resource policy

**Decision**: Use the existing local `BAAI/bge-reranker-v2-m3` backend with pinned path, revision and checksum. Benchmark candidate windows 10, 20 and 30; activate the smallest window that meets quality gates. Use one inference worker, CPU, fp16 disabled unless measured safe, bounded timeout and circuit breaker.

**Why**: The backend and test coverage already exist. Selective query-time compute is appropriate for i5/16 GB, but activation must remain empirical.

**Activation rule**: Do not claim the laptop supports the feature until same-machine benchmark proves latency and memory gates. If it fails, keep Auto on Hybrid and expose Tìm kỹ as unavailable/degraded only if the owner explicitly accepts that experience.

## Decision 6: Backward-compatible deployment

**Decision**: Continue accepting the currently approved v2 manifest as Hybrid-only. Introduce a newer manifest shape for adaptive capability with a separate reranker artifact, policy version, resource budget and benchmark evidence. Default adaptive flag is false.

**Why**: Rollback must be one config change and restart, with no index rebuild and no invalidation of the approved Hybrid path.

## Decision 7: Safe telemetry

**Decision**: Record enum/reason codes, counts, booleans and timings only. Do not persist query text, source snippets, absolute paths, credentials or exception messages.

**Required fields**: user preference, system request, effective path, pre/post decision, reason codes, reranker requested/applied, degraded flag/reason, candidate count, source count, Hybrid/rerank/total latency and policy version.

## Decision 8: Evaluation and anti-bias audit

**Decision**: Freeze a synthetic/non-private labeled set of at least 60 route cases and a hard retrieval benchmark before threshold tuning. Report confusion matrix and route distribution, not only aggregate accuracy.

**Mandatory anti-bias checks**:

- explicit Deep success rate = 100%;
- uncertain-to-Deep rate = 100%;
- hard-to-fast false-negative count visible and blocking;
- Auto cannot pass with all cases routed to one class;
- rerank application must match effective telemetry;
- quality gain and recall non-regression measured on frozen evidence judgments.

## Measurements still required before activation

1. Current same-session Hybrid baseline on the actual i5/16 GB machine.
2. Reranker cold load time and warm per-window latency for 10/20/30 candidates.
3. Peak process RSS and available system RAM with both BGE-M3 and reranker loaded.
4. Route confusion matrix after policy thresholds are fixed.
5. MRR@10/Recall@10 and blinded answer-evidence quality on the frozen hard set.

These are implementation tasks, not unresolved product clarifications. Failure keeps the feature disabled.
