# RAG-V2-SAME-PROTOCOL-BLINDED-ANSWER-QUALITY

Status: `ACTIVE — 2026-07-29`

## Goal

Evaluate the activated `bge_m3_hybrid` production candidate against the immutable NotebookLM reference under the same frozen twelve-question protocol, without tuning after unblinding or weakening privacy controls.

## Preconditions

- [RAG-V2-HYBRID-PRODUCTION-ACTIVATION](../completed/RAG-V2-HYBRID-PRODUCTION-ACTIVATION.md): `DONE`.
- [RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY](../completed/RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY.md): `DONE`, strict corpus audit `70/70`.
- Existing NotebookLM reference remains immutable and is not reacquired in this gate.

## Frozen baseline

- Prior same-protocol NotebookLM score: `3.807/5`.
- Prior RAG v2 score: `2.898/5`.
- Question set: canonical `BQ01`–`BQ12`; its hash must match the immutable reference.
- Production retrieval profile: `bge_m3_hybrid` with approved deployment/model identity.

## Measurement integrity remediation — 2026-07-29

- The initial `BQ01/BQ02` diagnostic is retained as historical legacy-arm
  evidence, but cannot support a quality verdict for the activated Workspace
  Chat production retriever: its declared `workspace_chat` arm invoked legacy
  lexical retrieval directly.
- The remediation runner now calls the same Workspace Chat RAG v2 adapter used
  by the UI, prepares its sources once before the question loop, and records
  the adapter backend, requested/effective profile and fallback state for every
  Workspace answer row.
- A row is technically invalid and provider synthesis is blocked unless it
  proves `rag_v2_subprocess`, requested/effective `bge_m3_hybrid`, and no
  fallback. A distinct adapter protocol marker also prevents legacy checkpoints
  from being reused.
- Only a separate `BQ01/BQ02` remediation diagnostic may run before a fresh
  twelve-question evaluation is authorized. The immutable NotebookLM reference,
  question set, corpus identity, prior artifacts, and no-tuning rule remain
  unchanged.

## Allowlist

- `ROADMAP.md`
- `docs/roadmap/RAG-V2-INTENT-RETRIEVAL-SYNTHESIS-TUNING.md`
- `docs/roadmap/active/RAG-V2-SAME-PROTOCOL-BLINDED-ANSWER-QUALITY.md`
- `docs/rag_v2/SAME_PROTOCOL_ANSWER_QUALITY_PROTOCOL.md`
- `scripts/battle_notebooklm_rag_v2.py`
- `src/aios_habit/workspace_chat_rag_v2_deployment.py`
- Focused tests for the files above

Runtime evidence belongs under ignored `local_runs/`; raw answers, evidence text and credentials must not be committed.

## Privacy constraints

- `local_only` sources cannot use live provider or NotebookLM routes.
- Live synthesis requires explicit `cloud_safe` or `public` classification plus immutable reference identity.
- The current 70-source corpus remains `local_only`; no relabeling is implied by this gate.
- Stage A is provider-free. If no separately approved live route exists, verdict is `BLOCKED_PRIVACY_ROUTE`.

## Evaluation discipline

1. Freeze candidate, model, corpus-audit, question-set and reference identities before answer generation.
2. One primary run only; retry only predeclared transport/provider failures without changing experiment identity.
3. No retrieval, prompt or synthesis tuning after viewing blind scores in this gate.
4. Independent scoring receives no system assignment map.
5. Provider failures are technical failures, not quality rows.
6. Hard privacy, citation and abstention gates cannot be offset by a high mean score.

## Acceptance criteria

All hard gates must pass:

- zero privacy/gateway regression;
- exact activated production identity;
- strict corpus audit and immutable corpus hash;
- immutable question/reference/notebook identity;
- zero fabricated citations;
- correct abstention on insufficient questions;
- no benchmark ID, filename or domain-specific hardcoding;
- aggregate publication excludes private raw content.

Quality passes only when the frozen eight-dimension rubric reaches the preregistered baseline or paired critical-workflow review proves no material quality loss. Completeness, citation support, actionability and cross-source synthesis remain separately visible.

## Verification

- Focused benchmark/eval/deployment tests.
- Full pytest, compileall, docs check, CLI audit and package import.
- Git whitespace checks.
- Provider-free Stage A dry run with `local_only`; no credential or network construction.
- Owner authorization before any Stage B live execution.

## Rollback

Remove evaluation-only identity helpers and restore the prior benchmark manifest contract. Do not alter the activated Workspace Chat deployment, model artifacts, source corpus or immutable reference.

## Closure verdicts

- `QUALITY_GATE_PASSED`
- `QUALITY_IMPROVED_NOT_PARITY`
- `QUALITY_GATE_FAILED`
- `BLOCKED_PRIVACY_ROUTE`
- `INSUFFICIENT_EVIDENCE`

A failed or blocked evaluation may create a separate planned tuning gate; it must not tune this active evaluation in place. A18 and P1.0 remain closed.
