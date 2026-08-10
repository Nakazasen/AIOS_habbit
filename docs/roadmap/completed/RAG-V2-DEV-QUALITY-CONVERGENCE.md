# RAG-V2-DEV-QUALITY-CONVERGENCE

Status: `DONE`

## Goal

Integrate the existing independent RAG v2 primitives into a measurable Dev-only
pipeline, then improve retrieval coverage, citation quality, actionability, and
cross-source synthesis from the closed capability-benchmark baseline.

This gate may produce a candidate suitable for a later primary-UI integration
plan. It does not itself migrate or activate RAG v2 in Workspace Chat.

## Preconditions and locked baseline

- `RAG-V2-HYBRID-RETRIEVAL-MIN`: `DONE`.
- `RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN`: `DONE`.
- `RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE`: `DONE`.
- `NOTEBOOKLM-BATTLE-RERUN-RAG-V2`: `DONE`.
- Closed blind benchmark: 11 shared rows, RAG v2 **2.898/5** versus NotebookLM
  **3.807/5**.
- Gate-open focused RAG v2 regression: **61 passed** on 2026-07-25.
- Working tree contains prior approved gate changes; this gate must not reset or
  rewrite unrelated modifications.

## Scope

1. Add a Dev-only orchestration path over converter registry, structure-aware
   chunking, local index, query planning, and evidence packs.
2. Add a local command surface for ingest, query, inspect, and evaluation.
3. Replace full-table lexical candidate generation with SQLite FTS5/BM25 where
   available, retaining a deterministic local fallback.
4. Improve set-level retrieval coverage and generic source diversity.
5. Add provider-independent synthesis planning, citation validation, and a
   truthful deterministic local fallback.
6. Extend the local evaluation harness for required evidence, citations,
   cross-source coverage, actionability, forbidden claims, and abstention.
7. Replay the private local benchmark and, only after local gates pass, perform a
   separately authorized live synthesis/battle rerun.

## Non-goals and hard locks

- No changes to Workspace Chat layout, labels, owner flow, or primary runtime
  activation (`UI Freeze`).
- No migration of legacy Workspace Chat retrieval in this gate.
- No domain, customer, benchmark-answer, or private-corpus hard-code in RAG v2.
- No cloud-default behavior, hidden provider call, credential logging, A18, or
  P1.0 opening.
- No parity claim before blind benchmark evidence supports it.
- No deletion or migration of legacy local indexes.

## Allowlist

Primary implementation allowlist:

- `src/aios_habit/rag_v2/**`
- `scripts/rag_v2_dev.py`
- `scripts/battle_notebooklm_rag_v2.py` only after local Dev gates are green
- `tests/test_rag_v2_*.py`
- `tests/test_battle_notebooklm_rag_v2.py`
- synthetic fixtures under `tests/fixtures/rag_v2_dev/**`
- this Gate Card, `ROADMAP.md`, and closure documentation

Any change outside this allowlist requires an explicit scope update before edit.

## Privacy constraints

- Local-only is the default for ingestion, retrieval, evidence, and evaluation.
- The Dev path must not read `API Key.txt` or any provider credential unless an
  explicit live sub-gate is invoked.
- Private inputs and generated raw answers remain under ignored local runtime
  roots; committed fixtures must be synthetic.
- `local_only` and `confidential` evidence must never enter a cloud synthesis
  request. Missing/unknown labels fail closed.
- Safe diagnostics may contain counts, stable fingerprints, statuses, and
  aggregate metrics, but not raw private evidence or credentials.
- Source selection and expected fingerprints must be enforced before returned
  evidence is built.

## Acceptance criteria

### Dev pipeline

- Converter -> chunker -> persistent local index -> retrieval -> evidence works
  end-to-end through one independent API.
- Incremental re-index replaces stale chunks for the same document/source.
- Disabled/unselected and stale-fingerprint sources cannot appear in results.
- Unsupported conversion is fail-soft and inspectable.
- CLI defaults to an ignored local runtime root and no network/provider use.

### Retrieval and evidence

- Candidate retrieval uses FTS5/BM25 where supported and has a tested
  deterministic fallback.
- Generic query variants cannot bypass privacy, selection, or freshness filters.
- Evidence-set coverage is evaluated across returned items, not only the first
  result.
- Citation metadata preserves available page, sheet, slide, section, row,
  column, and cell coordinates without exposing unsafe paths.
- Multi-source, procedure, comparison, table, multilingual, and insufficient
  synthetic cases have deterministic expected outcomes.

### Synthesis and quality

- Provider-independent synthesis planning maps required facets to evidence and
  reports missing/conflicting facets.
- Material claims must map to real citation IDs; unsupported or missing citations
  are detected.
- Local fallback is labeled as an evidence digest/checklist or insufficiency
  response, never as an unverified LLM answer.
- Continuous local evaluation records versioned thresholds and deterministic
  aggregate output.
- No regression in privacy or abstention can be offset by a higher average score.

### Promotion decision

A primary-UI integration plan may be proposed only if all local gates and full
repository validation pass and the authorized blind rerun either reaches the
closed NotebookLM mean (**3.807/5**) or paired evidence no longer shows a quality
loss on critical workflows. Otherwise the final verdict remains
`DEV_READY_WITH_LIMITATIONS` or `NOT_READY_FOR_PRIMARY_UI` with residual gaps.

## Verification

```powershell
py -3 -m pytest -q tests/test_rag_v2_schema.py tests/test_rag_v2_adapters.py tests/test_rag_v2_converters.py tests/test_rag_v2_chunking.py
py -3 -m pytest -q tests/test_rag_v2_index.py tests/test_rag_v2_evidence.py tests/test_rag_v2_eval_harness.py tests/test_rag_v2_hardcode_guard.py
py -3 -m pytest -q tests/test_rag_v2_pipeline.py tests/test_rag_v2_synthesis.py tests/test_rag_v2_dev_cli.py
py -3 -m pytest -q tests/test_battle_notebooklm_rag_v2.py
py -3 -m compileall src tests scripts
py -3 -m pytest -q
py -3 scripts/check_docs.py
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
git diff --check
git diff --cached --check
```

Private replay and live rerun commands must be recorded without credentials or
raw corpus contents.

## Rollback

- RAG v2 Dev remains disconnected from Workspace Chat and is removable without a
  product runtime migration.
- Dev indexes are rebuildable local artifacts; the canonical chunk table remains
  intact if FTS5 is unavailable.
- Provider synthesis is disabled by default and may be rolled back independently.
- Revert only the smallest failing gate; preserve previous baseline artifacts.
- Never delete legacy indexes, private sources, or prior benchmark checkpoints as
  part of rollback.

## Closure evidence

- Independent Dev orchestration, CLI, FTS5/BM25 candidate retrieval with
  deterministic fallback, set-level evidence coverage, provider-independent
  synthesis planning, citation validation, and continuous local evaluation are
  implemented and covered by the RAG v2 regression suite.
- Private offline replay: `BATTLE-RAGv2-1784998427-e33e5670`; preflight `PASS`;
  canonical `tailieugoc` corpus fingerprint `78957a10...`; frozen 12-question
  hash `e33e5670...`.
- Replay ingestion: 70 files seen, 53 converted, 17 fail-soft, 767 chunks
  indexed through `RagV2DevPipeline`.
- Replay privacy: router `SKIPPED_LOCAL_ONLY`, no key configured, no provider
  constructed, and no credential read. All 12 rows were correctly labeled
  `DRY_RUN_ONLY`; generated-answer quality therefore remains
  `INSUFFICIENT_EVIDENCE` in this replay.
- Focused RAG v2 regression: 79 passed. Full repository compile and regression:
  998 passed. Documentation contract, CLI audit, Workspace Chat import, and Git
  whitespace checks: PASS on 2026-07-25.
- No Workspace Chat UI or primary-runtime migration was made.

## Closure decision

The Dev implementation phase is complete and this Gate Card may close. The
final verdict is `DEV_READY_WITH_LIMITATIONS` and `NOT_READY_FOR_PRIMARY_UI`:

- local Dev integration and privacy/correctness gates are green;
- the prior blind benchmark remains the latest generated-answer quality evidence
  (RAG v2 2.898/5 versus NotebookLM 3.807/5);
- this local-only replay cannot support a new parity claim; and
- no live synthesis rerun was implicitly authorized or attempted.

A later owner-approved gate may plan a live blinded rerun or primary-UI
integration only after new paired quality evidence satisfies the promotion
criteria. Closing this gate does not open A18/P1.0.

## Evidence links

- Architecture: `docs/rag_v2/RAG_V2_DESIGN.md`
- Baseline benchmark:
  `docs/roadmap/completed/NOTEBOOKLM-BATTLE-RERUN-RAG-V2.md`
- Private aggregate replay metadata remains under ignored local runtime root:
  `local_runs/rag_v2_dev_gate5_offline/BATTLE-RAGv2-1784998427-e33e5670/`.
