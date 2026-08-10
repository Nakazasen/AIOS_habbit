# RAG-V2-GATE-H-HYBRID-CANARY

Status: `DONE`

## Goal

Select the strongest local retrieval profile, integrate it safely into Workspace Chat, and prove a production canary without complicating the normal-user experience.

## Completed scope

- Evaluated lexical, BGE-M3 dense, BGE-M3 hybrid, rerank, and parent-expansion profiles on the frozen local corpus.
- Selected `bge_m3_hybrid`: Recall@10 `1.000`, MRR@10 `0.620`, measured CPU p95 retrieval latency `1.792s` after readiness.
- Completed H4 with verdict `ADVANCE_TO_CANARY`.
- Added the Workspace Chat adapter, model-pin verification, source/index lifecycle, telemetry, privacy-preserving fallback, and rollback.
- Repaired cached SQLite pipeline reuse across Streamlit rerun threads.

## Product behavior

The normal-user flow remains one simple path:

```text
Open Workspace Chat → select sources → ask → receive the best evidence-backed answer
```

Canary flags and fallback stages are internal operational controls, not normal-user choices. A degraded fallback must not silently masquerade as the selected high-quality retriever.

## Closure evidence

- Focused affected regression: **87/87 passed**.
- Full repository regression: **1094/1094 passed**.
- Browser E2E passed for default, lexical canary, rollback, missing-model fallback, and three successive Streamlit reruns.
- Post-fix logs contained no SQLite thread error and no lexical fallback failure.
- Brain Gateway privacy, consent, sanitization, and provider boundaries remained intact.

## Closure decision

Gate H is complete with verdict **`ADVANCE_TO_CANARY_WITH_LIMITATIONS`**.

This authorizes a controlled production activation gate. It does **not** establish NotebookLM generated-answer parity and does not authorize a silent default switch.

## Residual limitations transferred forward

- 17 PNG sources remain unsupported without OCR.
- Two PDF sources are empty and require source recovery or explicit exclusion.
- Final deployment model pins, cold-start time, memory use, answer stability, and rollout acceptance must be verified on the target 16 GB CPU laptop class.
- NotebookLM same-protocol answer parity remains unproven.

## Rollback

Disable the internal Workspace Chat RAG v2 canary configuration to preserve the legacy retrieval path. Runtime indexes and model artifacts remain rebuildable, local, and outside version control.

## Evidence links

- `docs/roadmap/RAG-V2-INTENT-RETRIEVAL-SYNTHESIS-TUNING.md`
- `src/aios_habit/workspace_chat_rag_v2_adapter.py`
- Private runtime evidence remains under ignored `local_runs/`.
