# Matecon Manual Retrieval Operations

## Purpose

Keep answers about Matecon ACR/CTU manual mode grounded in the retrieved
sections of the approved source, rather than in the first pages of a long
document.

## What is known from the staged corpus

The materialized Matecon guide contains the full manual-mode procedure,
including `ctrlMode`, disconnection from MOM, ACR/CTU startup, AGV-status
confirmation, and manual-drive preparation. A response saying chapter 11 is
only a table-of-contents entry is a retrieval failure, not a source-content
limitation.

## Safe runtime behaviour

- `Auto` uses the validated BGE-M3 hybrid retrieval path.
- `Tìm kỹ` is permitted only when the adaptive manifest is activated and its
  pinned BGE reranker is available.
- On the CPU-only deployment, Deep reranks at most 10 candidates and receives
  an isolated five-minute IPC budget. Auto remains on its 30-second budget.
- For one user-selected manual, retrieval may return the normal evidence
  window from that manual instead of stopping at the multi-document diversity
  cap of three chunks, but only for procedural, actionable, or diagnostic
  questions. A simple fact lookup retains the smaller cap.
- The offline planner recognizes the form of a question such as "how does this
  work?" / "hoạt động như thế nào?" without adding document-specific aliases.
  This permits definition, prerequisite, execution, and safety evidence from
  the same selected manual to reach the answer provider.
- If semantic retrieval or the deep reranker is unavailable, Workspace Chat
  stops before the provider call. It never submits the complete source set,
  because source capping could leave only a table of contents or leading pages.

## Before enabling deep mode

1. Run the application and diagnostics from `.venv\\Scripts\\python.exe`, the
   pinned Python 3.11 environment, with the pinned `rag-retrieval-lab`
   dependencies. Verify `import FlagEmbedding` in that exact environment; the
   system `py -3` Python 3.13 currently lacks it.
2. Verify the BGE-M3 and reranker model-tree digests against the deployment
   constants. Do not replace a digest with a placeholder.
3. Prepare a separate candidate manifest using
   `scripts/workspace_chat_rag_v2_activation.py prepare --enable-adaptive`.
4. Run `scripts/benchmark_adaptive_reranking.py` against that candidate. A
   `BLOCKED`, `FAIL`, synthetic result, or missing gate is not activation
   evidence.
5. Activate only with the resulting authentic `PASS` report, then restart the
   Workspace Chat process using the same Python environment.

If the sealed selected-profile evidence is absent on the host, use an unsealed
diagnostic manifest only to investigate. It can never activate production.

## Fast, source-scoped acceptance diagnostic

This check rebuilds no 73-source corpus and never changes production. It
reuses the isolated Matecon runtime when its semantic coverage is valid:

```powershell
.\.venv\Scripts\python.exe scripts\diagnose_matecon_manual_retrieval.py `
  --prepare-diagnostic-runtime `
  --diagnostic-runtime-root local_runs\matecon_semantic_diagnostic_run\runtime

.\.venv\Scripts\python.exe scripts\diagnose_matecon_manual_retrieval.py `
  --prepare-diagnostic-runtime `
  --diagnostic-runtime-root local_runs\matecon_semantic_diagnostic_run\runtime `
  --with-reranker --rerank-limit 10
```

Accept `Auto` only if it reports `retrieval_applied=true`, at least the bounded
ten-item procedure window, and no degradation. Accept `Deep` only if the same
holds and `reranker_applied=true`. Otherwise keep the UI fail-closed; do not
claim that chapter 11 is absent.

## Acceptance check

Ask: `Chế độ Manual Matecon ACR/CTU hoạt động như thế nào?`

For `Auto`, the evidence must include relevant manual-mode material. For
`Tìm kỹ`, acceptance additionally requires `reranker_applied=true` and
`effective_path=hybrid_rerank`; the evidence should cover `ctrlMode=1`, MOM
disconnection, and manual AGV operation. If the evidence cannot be retrieved,
the UI must say retrieval is unavailable rather than claim the source lacks
the chapter.
