# Implementation Plan: Resumable Stage A Preparation

**Branch**: `001-stage-a-resume-guard` | **Date**: 2026-08-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-stage-a-resume-guard/spec.md`

## Summary

Make the provider-free Workspace Chat Stage A flow durable at source boundaries. A content-addressed, identity-bound checkpoint records only opaque source progress. The adapter emits progress after each successful commit, accepts a verified completed-source set, and enforces a caller-provided per-source deadline. The benchmark runner resumes exactly matching incomplete stages, updates its heartbeat per source, and fails closed otherwise. An explicit unsealed mode permits local BQ01/BQ02 diagnosis only; it never enables Stage B or fabricates sealed evidence.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Standard library and the existing RAG v2 subprocess adapter

**Storage**: Atomic JSON checkpoint under the ignored local staging cache; existing SQLite workspace index

**Testing**: pytest

**Target Platform**: Local Windows operator workstation

**Project Type**: Single Python application and benchmark CLI

**Performance Goals**: Persist one checkpoint per successful source and avoid repeat preparation calls for completed sources after interruption

**Constraints**: Provider-free local-only Stage A; unsealed mode restricted to BQ01/BQ02; no source text, filename, credential or provider response in checkpoint; per-source deadline fails closed; Stage B locked

**Scale/Scope**: 70-source production corpus; compact synthetic fixtures for unit tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Privacy is preserved: checkpoint metadata contains only content-derived opaque IDs, never source text, titles, paths, credentials or provider data.
- Stage A remains local-only and provider-free. The design does not open a provider route or change corpus labels.
- Existing public adapter behavior remains fail-closed for unprepared sources; focused regression tests are required.
- The change is specified, planned, tasked, and will update the code graph after implementation as required by the project constitution.

**Result: PASS.** Rechecked after design: PASS.

## Project Structure

### Documentation

```text
specs/001-stage-a-resume-guard/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/stage-a-checkpoint.md
└── tasks.md
```

### Source Code

```text
src/aios_habit/workspace_chat_rag_v2_adapter.py
scripts/battle_notebooklm_rag_v2.py
tests/test_workspace_chat_rag_v2_adapter.py
tests/test_battle_notebooklm_rag_v2.py
```

**Structure Decision**: Extend the existing Workspace Chat adapter and existing benchmark CLI. Add focused regression tests beside current coverage; local run artifacts remain ignored.

## Complexity Tracking

No constitution violations.
