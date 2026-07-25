# Data Migration and Compatibility

Status: `PROPOSED`
Owner role: Project owner / storage reviewer
Last reviewed: 2026-07-25
Review cadence: Before any persisted-data schema migration

## Scope

This document governs Workspace Chat JSONL and RAG index compatibility. It is
separate from root `MIGRATION_POLICY.md`, which governs harvesting code/features
from other repositories.

## Current state

There is no implemented automatic migration framework or persisted schema-version
marker for Workspace Chat JSONL/RAG SQLite. Therefore in-place migration,
backward compatibility and downgrade are not current guarantees.

## Required migration plan

Before changing persisted fields/tables:

1. Assign a migration ID and state source/target versions.
2. Inventory affected stores and classify fields as additive, transformed or
   destructive.
3. Back up owner data and prove restore on synthetic data first.
4. Define idempotence, transaction/atomicity expectations and partial-failure
   behavior.
5. Define forward path, rollback path and user-visible safe messaging.
6. Add old/new fixture tests and a clean-store test.
7. Record release notes and compatibility window.

## Safety rules

- Never silently delete malformed/private data to make startup succeed.
- Never run migration logic from a provider route or CI against owner data.
- A schema change without migration evidence is a release blocker.

## Related records

- [Persisted-data compatibility](../contracts/PERSISTED_DATA_COMPATIBILITY.md)
- [Backup and restore](BACKUP_RESTORE.md)
- [Release checklist](../release/RELEASE_CHECKLIST.md)
