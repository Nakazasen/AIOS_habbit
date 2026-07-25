# Runtime Interface Contracts

Status: `ACTIVE`
Owner role: Project owner / integration reviewer
Last reviewed: 2026-07-25
Review cadence: Before changing a public module boundary or provider contract

## Workspace Chat persistence boundary

`workspace_chat_store` owns notebook, conversation, message, source and source
selection persistence under ignored `local_cases/workspace_chat/`. Callers use
model objects and store functions; files are implementation details, not a
public synchronization API.

## Privacy gateway boundary

`BrainRequest` carries question, sources, optional consent, router state, purpose
and destination. `BrainGateway.preflight_check()` returns `BrainDecision` with:

- `allowed`, reason code and next action;
- a sanitized payload only when its external route is permitted.

This is the canonical target policy contract and is currently exercised by the
router-enabled mock/preflight path.

## Real Workspace Chat provider boundary

The current `real_router_enabled` path in `generate_workspace_ai_answer()` uses a
separate guard: cloud mode, sendable-label check, explicit confirmation and exact
enabled-source snapshot. Tests prove it blocks `local_only`, `confidential` and
`unknown` labels before calling a provider client. It does not currently prove a
Gateway sanitizer/preflight call before prompt construction. Treat this as a P0
convergence requirement, not as an undocumented equivalent contract.

## Router boundary

`WorkspaceChatRouterAdapter.generate_answer()` returns `(ok, text_or_safe_error)`.
The adapter creates the router from environment, sends messages in request
metadata and maps unsuccessful outcomes/exceptions to localized safe messages.
Keys are never an argument or return value of this contract.

## RAG v2 index boundary

`LocalChunkIndex(db_path)` creates/opens SQLite at an explicit caller path.
`upsert_chunks`, `search`, `count`, `clear` and `close` are current contract.
Search is deterministic lexical scoring, not semantic retrieval/FTS guarantee.

## Error contract

User-facing supported UI errors must be Vietnamese-safe and must not surface raw
tracebacks, secrets or local paths. Internal exceptions remain operational
signals and must be sanitized before support sharing.

## Compatibility

A signature/schema change requires focused regression tests, an ADR when it
changes a material boundary, and update to
[PERSISTED_DATA_COMPATIBILITY.md](PERSISTED_DATA_COMPATIBILITY.md).
