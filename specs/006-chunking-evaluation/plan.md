# Implementation Plan: Evidence-Based Chunking Evaluation

**Branch**: `006-chunking-evaluation` | **Date**: 2026-08-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-chunking-evaluation/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Establish a local, reproducible evaluation harness before changing RAG v2
chunking. It will compare the current structure-aware, zero-overlap baseline
with bounded candidates on identical Vietnamese, Japanese, and Chinese
question-evidence cases. Adoption is evidence-gated: no candidate becomes the
default unless it improves source retrieval or fixes a confirmed boundary fault
within the agreed CPU, latency, and index-size limits.

The work is deliberately separated from BGE runtime restoration, Desktop/VPS
packaging, provider routing, expert learning, and general UI work. It operates
on a dedicated evaluation runtime and never mutates the active Workspace Chat
index.

## Technical Context


**Language/Version**: Python 3.11

**Primary Dependencies**: Existing RAG v2 chunker, local SQLite index, BGE-M3
embedding backend, existing evidence-pack/trace contracts, pytest

**Storage**: Dedicated local SQLite evaluation indexes plus UTF-8 JSON reports;
no active Workspace Chat index mutation

**Testing**: pytest unit, integration, deterministic fixture, and local
benchmark/report checks

**Target Platform**: Windows CPU developer environment first; portable local
runtime compatible with later Desktop/VPS packaging

**Project Type**: Existing Python Workspace Chat / local RAG application

**Performance Goals**: Candidate must improve expected-evidence retrieval by at
least 5 percentage points or fix a confirmed multilingual boundary fault, while
increasing warm-query latency and index size by no more than 25% over baseline

**Constraints**: Local-first; no cloud transmission of source text; preserve
table/page/sheet/row/privacy provenance; no default behavior change before an
accepted evaluation record

**Scale/Scope**: Start with a frozen representative subset plus multilingual
boundary fixtures, then run the accepted strategy against the user-selected
Workspace Chat corpus before promotion

## Constitution Check

*GATE: Pass before Phase 0 research; re-checked after Phase 1 design.*

| Principle | Plan response | Status |
|---|---|---|
| Evidence Before Assertion | Every comparison emits a reproducible local run record. A strategy is rejected by default when no measurable gain is demonstrated. | Pass |
| Local-First Privacy and Consent | Evaluation corpus, index, logs, and reports remain local. Reports use source IDs and local paths only; raw `local_only` text never leaves the workspace. | Pass |
| Portable, Pattern-Based Knowledge | Evaluation cases and reports use versioned UTF-8 JSON/Markdown contracts and are not tied to an answer provider. | Pass |
| User-Centered Workspace Chat | This phase changes no user flow. Any later user-facing status is Vietnamese-first and distinguishes pilot from approved behavior. | Pass |
| Change Discipline and Verifiable Quality | The feature is spec-first, staged into audited commits, and blocks promotion without test/benchmark evidence and rollback metadata. | Pass |

Post-design review: pass. The plan introduces no external data egress, no new
provider dependency, and no mutation of production/default retrieval state.

## Project Structure

### Documentation (this feature)

```text
specs/006-chunking-evaluation/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/aios_habit/rag_v2/
├── chunking.py                    # Structure-aware baseline and candidates
├── pipeline.py                    # Ingestion/query orchestration
├── index.py                       # Lexical, dense, sparse, hybrid retrieval
└── chunk_evaluation.py            # Planned isolated evaluation domain

scripts/
└── evaluate_chunking.py           # Planned local runner; no production mutation

tests/
├── test_rag_v2_chunking.py        # Existing structural coverage
├── test_chunk_evaluation.py       # Planned metrics and decision tests
└── fixtures/chunk_evaluation/     # Planned multilingual local fixtures

specs/006-chunking-evaluation/
├── research.md
├── data-model.md
├── contracts/chunk-evaluation-v1.md
└── quickstart.md
```

**Structure Decision**: Keep evaluation beside RAG v2, but isolate its runtime,
fixtures, and reports from Workspace Chat's active indexes. Existing chunking
and retrieval modules remain the only production-path touchpoints.

## Complexity Tracking

No constitutional violations or complexity exceptions are required.

## Delivery Sequence

### Commit E1 — Baseline and measurement contract (first implementation only)

- Add frozen local evaluation-case schema, result schema, and CLI/report runner.
- Capture current zero-overlap RAG v2 behavior, chunk-length distribution,
  expected-evidence retrieval, citation support, latency, preparation time, and
  index size.
- Add Vietnamese/Japanese/Chinese boundary fixtures and a supported-path trace.
- Do **not** alter `StructureAwareChunker`, search defaults, document summaries,
  or legacy chunkers.

**Audit gate**: The same run can be repeated locally and produces baseline
evidence. If it cannot, stop here; do not implement an algorithm change.

### Commit E2 — Boundary candidates, evaluated not assumed

- Add sentence-aware candidate segmentation that recognises Vietnamese and CJK
  sentence punctuation.
- Compare baseline and candidates on the E1 corpus; retain a fallback record
  when no safe boundary exists.
- Promote no candidate by default in this commit.

**Audit gate**: Candidate meets SC-002 and SC-003, retains provenance, and has
no table/Excel regression.

### Commit E3 — Context and summary decision

- Evaluate bounded contextual overlap versus existing parent/neighbor expansion.
- Evaluate document-summary selection separately from detailed evidence.
- Adopt only the measured winning policy; reject summary promotion when it
  displaces precise evidence.

**Audit gate**: Detailed evidence remains in every qualifying precise/procedure
case and accepted changes satisfy the resource gates.

### Commit E4 — Controlled promotion and legacy disposition

- Rebuild a fresh, versioned index only for an accepted strategy.
- Show the strategy/evaluation identity in local diagnostics and retain a
  rollback route to baseline.
- Record whether legacy chunkers are inactive, migrated, or separately scoped.

**Audit gate**: Fresh-index smoke, selected real-document checks, rollback, and
full affected test suite pass. Update the project roadmap/handover only after
this evidence exists.
