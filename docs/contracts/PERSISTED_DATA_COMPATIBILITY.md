# Persisted Data Compatibility

Status: `PARTIAL`
Owner role: Project owner / storage reviewer
Last reviewed: 2026-07-25
Review cadence: Before changing persisted models, JSONL fields or SQLite schema

## Current persistent forms

| Store | Location / form | Compatibility statement |
|---|---|---|
| Workspace Chat state | Ignored JSONL under `local_cases/workspace_chat/` | Model-backed local implementation; no published stable external API/version marker yet |
| RAG v2 index | Caller-selected SQLite `chunks` table | Schema creation is idempotent for current fields; no explicit schema-version migration framework |
| Evidence/memory runtime | Ignored JSONL paths | Governed by schemas; local owner data remains outside Git |
| Build/release metadata | `pyproject.toml` and tracked docs | Version is package metadata, not runtime-data migration version |

## Compatibility rules

1. Additive field changes require defaults and tests for old/unknown data where
   models support it.
2. Destructive rename/removal needs backup, migration plan, rollback and release
   note before implementation.
3. SQLite changes need migration detection/versioning before claiming in-place
   compatibility.
4. Store corruption must be handled as an operational recovery event, not hidden
   by silently deleting owner data.

## Current limits

Automatic schema migration, cross-device sync and formal backward compatibility
are not implemented claims. See
[Data migration compatibility](../operations/DATA_MIGRATION_COMPATIBILITY.md).

## Related records

- [ADR-0003](../adr/0003-local-sqlite-lexical-index.md)
- [Backup and restore](../operations/BACKUP_RESTORE.md)
