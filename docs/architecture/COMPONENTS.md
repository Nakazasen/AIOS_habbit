# Architecture Components

Status: `ACTIVE`
Owner role: Project owner / architecture reviewer
Last reviewed: 2026-07-25
Review cadence: Before a component contract, data class or supported UI changes

## Supported component map

| Component | Role | Key evidence |
|---|---|---|
| `workspace_chat_app` | Streamlit supported UI bootstrap and owner flow | Workspace Chat import gate |
| `workspace_chat_store` | Ignored JSONL notebook/message/source persistence | Store tests and backup runbook |
| `workspace_chat_source_ingest` | Local upload extraction boundary | Ingest tests / user-facing safe errors |
| `workspace_chat_ai_answer` | Local/context answer orchestration | Workspace Chat AI tests |
| `brain_gateway` | Privacy labels, consent, sanitization and external eligibility | Router mock privacy tests |
| `workspace_chat_router_adapter` | Router outcome → safe UI message | Focused router/live smoke evidence |
| `rag_v2` | Generic element/chunk/local-index foundations | RAG v2 tests/design |
| `audit` / `cli` | Repository safety/evidence validation | CLI audit gate |

## Ownership boundary

The application owns source selection, privacy/consent decisions and user-facing
safe behavior. A provider router owns provider selection/call behavior only; a
provider owns its external service behavior and terms.

## Known legacy boundary

`case_cockpit` and shared legacy services remain present for separately planned
dependency retirement. Supported Workspace Chat code must not reintroduce public
legacy routes.

## Related records

- [Runtime interfaces](../contracts/RUNTIME_INTERFACES.md)
- [Persisted-data compatibility](../contracts/PERSISTED_DATA_COMPATIBILITY.md)
- [Quality gates](../quality/QUALITY_GATES.md)
