# RAG-V2-HYBRID-PRODUCTION-ACTIVATION

Status: `COMPLETED — 2026-07-29`

## Goal

Make the strongest verified local retriever the normal Workspace Chat behavior on a 16 GB CPU office laptop while keeping the experience simple and answer quality stable.

## Product contract

The normal user sees no hybrid/lexical/legacy switch and does not need to understand feature flags. Workspace Chat automatically uses the best ready retrieval mode.

If high-quality retrieval is unavailable, the product must not silently present a materially weaker answer as equivalent. It must either recover automatically, keep the last ready runtime, or show a short nontechnical message such as: "High-quality document search is temporarily unavailable; please retry."

Technical mode names, model paths, checksums, and fallback telemetry remain in owner/operator diagnostics only.

## Scope

- Install or reference the verified local BGE-M3 artifact through stable deployment configuration.
- Reuse the materialized index and keep the model warm instead of rebuilding/reloading per question.
- Measure cold start, warm retrieval, peak RAM, index size, CPU load, and end-to-end answer latency on the target 16 GB CPU laptop class.
- Run a limited owner canary using real Workspace Chat tasks and compare answer stability against the current path.
- Define an automatic health/recovery policy that avoids unexplained quality drops.
- After owner acceptance, make best-ready hybrid retrieval the default internal behavior without adding a normal-user setting.

## Baseline sizing

- Verified BGE-M3 model artifact: approximately **2.3 GB on disk**.
- Measured warm CPU retrieval p95 in Gate H: approximately **1.8 seconds** per query.
- Reranker profiles are excluded from this gate because measured latency was approximately 174–186 seconds p95 and provided no Recall@10 gain.
- End-to-end answer time also includes the separate answer-model/provider latency.

## Acceptance criteria

- The exact model path, revision, and checksum pass readiness checks after a clean restart.
- Peak process and system memory remain safe on a 16 GB machine without sustained paging or destabilizing other office applications.
- Cold start is measured and communicated; warm retrieval meets an owner-approved target, initially p95 ≤ 3 seconds.
- Index/model initialization is not repeated for every question.
- No silent quality downgrade occurs across normal reruns, model errors, stale indexes, or source changes.
- Representative owner tasks and citations pass browser E2E.
- Privacy/gateway regressions are zero, full tests pass, and owner explicitly approves default activation.

## Non-goals

- No heavy multilingual reranker activation on the target CPU laptop.
- No normal-user technical settings or three-mode selector.
- No NotebookLM parity claim without a later same-protocol blinded answer-quality gate.

## Rollback

One internal configuration change returns Workspace Chat to the prior stable retrieval runtime. Preserve sources, indexes, model files, and evidence for diagnosis; do not expose rollback controls to normal users.

## Verification

- Clean-start and warm-query benchmark on the target laptop.
- Peak RAM/CPU/pagefile capture during indexing and repeated queries.
- Browser E2E over representative owner workflows and forced recovery paths.
- Focused adapter/runtime tests, full repository regression, docs checks, CLI audit, import check, and Git whitespace checks.

## Completion evidence

- Production benchmark status: `PASS` with the exact `bge_m3_hybrid` profile and no fallback.
- Measured warm retrieval: mean `712.345 ms`, p95 `814.25 ms` against the `3,000 ms` limit.
- Runtime initialized once across eight warm queries; preparation and query are separate worker commands.
- Measured cold preparation (`35,627.179 ms`) is scheduled before the ready state and is not treated as query latency.
- Memory gate passed on the target 16 GB machine; network and provider synthesis remained disabled.
- Workspace Chat fails closed while preparation is incomplete and exposes no normal-user technical mode selector.
- Browser acceptance confirmed the simplified source flow and production UI cleanup.
- Focused UI regression passed `74/74`; full repository regression passed `1,104/1,104`.
