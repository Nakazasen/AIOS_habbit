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

`BrainRequest` carries question, the full enabled source snapshot, optional
consent, router state, purpose, destination and optional outbound evidence subset.
`BrainGateway.preflight_check()` is the single real-route and mock-route policy
contract. It returns a `BrainDecision` with:

- `allowed`, reason code and next action;
- a sanitized payload only when the external route is permitted.

The external Workspace Chat destination is the stable identifier
`workspace_chat_external_router`; the purpose is `workspace_chat_answer`.
Consent must match both values and the exact full enabled source-set hash. Any
retrieved outbound snippet must be authorized by that full source snapshot.

## Real Workspace Chat provider boundary

`generate_workspace_ai_answer()` turns the full Workspace Chat selection into a
`BrainRequest` before it invokes the real router. It uses Gateway approval to
create the only outbound payload. `local_only` and `confidential` hard-deny;
`unknown` and `machine_only` require matching consent. The explicit current
owner choice for external sharing maps to `cloud_safe`. Legacy `machine_only`
and `cloud_allowed` records remain non-sendable by default until deliberately
reclassified.

## Router boundary

`WorkspaceChatRouterAdapter.generate_answer()` accepts only
`SanitizedRouterPayload` and returns `(ok, text_or_safe_error)`. It builds the
provider messages internally from this approved payload and maps unsuccessful
outcomes/exceptions to localized safe messages. Keys are never an argument or
return value of this contract.

### Provider model recovery

For catalog-managed cloud model defaults, `ai_router.route_answer()` may handle
an explicit `model_not_found` response by making one content-free model metadata
probe and retrying once with a catalog-approved replacement of the same model
family. The retry reuses the same approved payload; it cannot change the source
selection, destination, purpose, consent scope, or privacy classification.

An explicit `AIOS_<PROVIDER>_MODEL` environment override is owner-controlled
and is never replaced automatically. Discovery never follows a URL supplied by
a provider response and never selects an arbitrary first model from a response.
If no approved replacement works, the normal provider health/fallback path
applies.

`aios-habit provider-check` is a diagnostic-only command. It probes only model
metadata for configured providers, prints redacted status/model results, sends
no source material, writes no configuration, and never prints API keys.

## RAG v2 index boundary

`LocalChunkIndex(db_path)` creates/opens SQLite at an explicit caller path.
`upsert_chunks`, `search`, `count`, `clear` and `close` are current contract.
Search is deterministic lexical scoring, not semantic retrieval/FTS guarantee.

## Error contract

User-facing supported UI errors must be Vietnamese-safe and must not surface raw
tracebacks, secrets or local paths. Internal exceptions remain operational
signals and must be sanitized before support sharing.

## Compatibility

The owner-facing sharing choice writes `cloud_safe`. Existing stored
`machine_only` and `cloud_allowed` labels are intentionally not reclassified or
sent externally automatically; owners must make a new explicit sharing choice.
A signature/schema change requires focused regression tests, an ADR when it
changes a material boundary, and update to
[PERSISTED_DATA_COMPATIBILITY.md](PERSISTED_DATA_COMPATIBILITY.md).
