# NOTEBOOKLM-BATTLE-RERUN-RAG-V2

Status: `DONE`

## Goal

Produce comparable, identity-blind evidence for NotebookLM, the current Workspace
Chat path, and the independent RAG v2 candidate. This gate closes the evaluation
protocol and evidence run; it does not claim product parity or migrate RAG v2 into
the primary UI.

## Implemented protocol

- Replaced hard 48-source parity blocking with a capability audit. Source-count
  differences remain visible but do not invalidate workflows whose required
  evidence exists.
- Classified source/workflow applicability independently for NotebookLM,
  Workspace Chat, and RAG v2.
- Exercised the current Workspace Chat arm and the independent RAG v2
  converter/chunker/index/evidence/synthesis arm separately.
- Restricted local benchmark ingestion to canonical `tailieugoc` content and
  excluded generated state, caches, drafts, and prior answers.
- Added deterministic checkpoint/resume and bounded NotebookLM retry handling.
- Produced a stable blinded three-system bundle and kept assignments separate
  until the independent review was complete.
- Imported eight-dimension 0–5 scores only for shared, successfully completed
  rows. Provider failures and non-applicable workflows are excluded.

## Acceptance evidence

Private evidence is retained under ignored local artifacts in
`local_runs/battle_rag_v2/BATTLE-RAGv2-1784990862-e33e5670/`.
No raw answer, private corpus content, assignment, or credential is committed.

- Notebook identity and authenticated CLI access: PASS.
- Local canonical corpus: 53 converted documents / 767 RAG chunks.
- Frozen question set: 12 questions; hash suffix `e33e5670`.
- RAG v2: 12/12 applicable workflows completed.
- Workspace Chat: 12/12 applicable workflows completed.
- NotebookLM: 11/11 applicable workflows completed.
- `BQ09`: NotebookLM `not_applicable` because it is an Excel-native workflow;
  excluded from shared-corpus quality and represented in native utility coverage.
- Provider errors in the final recovered checkpoints: 0.
- Independent blind review: 11 shared rows, all imported successfully.
- Wins: NotebookLM 8, RAG v2 2, Workspace Chat 1, ties 0.
- Mean of eight rubric-dimension means: NotebookLM 3.807/5, RAG v2 2.898/5,
  Workspace Chat 2.841/5.
- RAG v2 improved slightly over the current product path on this run, but did
  not reach NotebookLM quality. The largest measured gaps are completeness,
  citation support, actionability, and cross-source synthesis.
- Focused benchmark/RAG regressions: 57 passed.
- Full repository regression: 977 passed.
- Documentation contract: PASS.
- Compile: PASS.
- CLI audit: PASS, no errors or warnings.

## Decision

The benchmark phase is complete and reproducible enough to close. The evidence
supports the following product conclusion:

- `RAG_V2_READY_BUT_NOT_IN_PRIMARY_UI` as an engineering candidate;
- `NOT_READY` for a NotebookLM-parity claim;
- Workspace Chat must not be advertised as equivalent to NotebookLM from this
  single notebook/run.

## Follow-up work

- Improve RAG v2 retrieval recall and evidence coverage for answerable questions;
  several losses were caused by false insufficiency.
- Improve cross-document synthesis, citation granularity, and procedure-oriented
  answer construction.
- Define and validate the next integration gate before replacing Workspace Chat's
  production retrieval path.
- Preserve local-first privacy boundaries and the existing BrainGateway contract.

## Explicit exclusions

- No NotebookLM upload or source synchronization.
- No cloud route for `local_only` or `confidential` evidence.
- No raw private benchmark artifact committed to Git.
- No automatic RAG v2 activation in Workspace Chat.
- No A18 or P1.0 opening.
