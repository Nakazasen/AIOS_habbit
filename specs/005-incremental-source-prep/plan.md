# Implementation Plan: Incremental Source Preparation

**Branch**: `005-incremental-source-prep` | **Date**: 2026-08-22 | **Spec**: [spec.md](spec.md)

## Summary

Prepare every new or changed Workspace Chat source asynchronously when BGE is genuinely enabled. A durable, single-worker queue continues through the library while the application is open and resumes unfinished work after restart. Ready sources remain usable immediately. A question can promote one relevant source, but a broad question cannot create a second whole-library job. Correct misleading AI provenance and repeated-evidence UI in the same surface.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Streamlit, existing BGE-M3 subprocess client, SQLite

**Storage**: Existing local Workspace Chat JSONL store and BGE SQLite runtime; add a SQLite preparation ledger; pending question is session-scoped only

**Testing**: pytest

**Target Platform**: Local Windows desktop browser

**Project Type**: Local Streamlit application

**Performance Goals**: Upload returns without waiting for embeddings; a specific ready-source question is not blocked by unrelated preparation; each source is scheduled at most once per content fingerprint; one CPU worker drains the queue; an interactive question promotes at most one source automatically.

**Constraints**: Preserve deployment fail-closed behavior; never send local-only content externally; no whole-library preparation from a broad question.

**Scale/Scope**: Existing notebooks with tens to hundreds of sources; source preparation is one document at a time on this CPU-constrained machine.

## Constitution Check

- Evidence before assertion: pending submission is only replayed after readiness is explicitly verified; tests cover one-answer behavior.
- Local-first: pending state holds only question, conversation ID and source keys; no new cloud traffic or durable private memory.
- User-centered: all messages are Vietnamese and distinguish source preparation from BGE deployment failure.
- Change discipline: focused adapter and UI tests precede implementation; architecture, roadmap and handover receive concise updates.

**Result**: PASS. No exception is required.

## Design

1. Add a durable `source_preparation_ledger` to `workspace_chat.sqlite`, keyed by source scope/id, content fingerprint and BGE model revision. It records `pending`, `processing`, `ready`, `failed`, and retry metadata. A stale `processing` state becomes `pending` after restart.
2. After upload, restore, replace, or notebook open, reconcile enabled sources against the ledger and durable BGE index. Enqueue every new/changed/unready searchable source as normal priority. Never re-embed a matching ready fingerprint.
3. Run one long-lived background drain loop in the existing preparation executor. It processes one source per committed unit, emits progress, then immediately claims the next pending source. It must not pretend to run while BGE is unavailable.
4. Add priorities: `interactive` for the source selected by a pending question, `normal` for uploads/restores, and `backfill` for notebook-open reconciliation. Ready questions bypass the queue.
5. Keep an idempotent session-only pending submission. It captures the exact checked source scope, then submits once only after that scope is ready. Cancel stops only the question, not indexing.
6. Render a compact `BGE-M3: 12/75 sẵn sàng · đang đọc … · 2 lỗi` status and per-source state without moving the composer below the fold.
7. Change provenance to show bridge, generation provider, and verified model identity separately. Do not display `antigravity-brain-pro` as a model.
8. Group evidence by source id and show `3 đoạn từ 1 tài liệu`, with expandable chunk locations.

## Project Structure

```text
src/aios_habit/
├── workspace_chat_app.py             # upload scheduling, pending submission and Vietnamese UX
├── workspace_chat_rag_v2_adapter.py  # bounded question source scope and readiness helpers
└── workspace_chat_ui.py              # source readiness copy if required

tests/
├── test_workspace_chat_rag_v2_adapter.py
└── test_workspace_chat_source_selection_owner_flow.py
```

**Structure Decision**: Keep all retrieval lifecycle behavior in the adapter and keep Streamlit session/UI behavior in the application module.

## Complexity Tracking

No constitution violations.
