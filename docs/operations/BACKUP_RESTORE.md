# Backup and Restore

Status: `ACTIVE`
Owner role: Local data owner / operator
Last reviewed: 2026-07-25
Review cadence: Before release and after a persistent-store change
Last synthetic drill: 2026-07-25 — PASS (six Workspace Chat JSONL entity types and one SQLite index/search)

## Scope and limits

AIOS WorkLens is local-first. Backups are owner-operated and may contain private
information. Never store a backup in Git, CI artifacts, public cloud or a support
issue unless the owner has separately approved a protected destination.

This procedure covers the supported Workspace Chat JSONL state and a
caller-managed RAG SQLite index. It does not promise recovery of source material
that the owner no longer possesses or of an index whose rebuild input is gone.

## State inventory

| State | Location concept | Backup recommendation | Rebuildability |
|---|---|---|---|
| Workspace notebooks, messages, sources, selections | `local_cases/workspace_chat/` | Backup as one directory | Not automatically rebuildable from source files |
| RAG v2 SQLite index | Explicit caller-selected database path | Backup when rebuilding is costly | Rebuildable only from available source/chunk inputs |
| Private source documents | Owner-selected local locations | Owner policy decides | Original source; do not copy into repository |
| Configuration/credentials | Environment/owner secret store | Follow owner secret policy | Never include in app backup by default |
| `local_runs/` benchmarks/diagnostics | Ignored local output | Optional, case-by-case | Often regenerable |

## Backup procedure

1. Close Workspace Chat and any process using the selected SQLite database.
2. Choose an encrypted or otherwise owner-controlled destination outside the
   repository and outside a public sync folder unless explicitly approved.
3. Copy the complete `local_cases/workspace_chat/` directory as a timestamped
   unit. Preserve file names and UTF-8 encoding; do not edit JSONL during copy.
4. If needed, copy the selected RAG SQLite database together with any SQLite
   journal/WAL files while the database is closed.
5. Record only non-sensitive evidence locally: backup date, store category,
   success/failure and restore-test result. Do not record source contents or keys.
6. Verify the destination is not tracked: run `git status --short --ignored` in
   the repository and confirm no backup path was staged.

## Restore procedure

1. Stop Workspace Chat and make a safety copy of the current local directory.
2. Restore the backup into the exact local store location; do not merge partial
   JSONL files by hand.
3. Start Workspace Chat and verify that the expected notebook/conversation list
   is visible without exposing source content to a provider.
4. For a SQLite index, open it only with the matching/current application
   version, run a count/search smoke with synthetic or owner-approved local
   query, then close it cleanly.
5. If restore fails, preserve the failed copy, record the safe error summary and
   follow [troubleshooting](TROUBLESHOOTING.md). Do not delete the only owner
   copy as a recovery attempt.

## Corruption and rebuild

- JSONL parsing failures are an incident: preserve the affected file and restore
  a known-good backup; do not silently discard records.
- A corrupt RAG index may be replaced only after the owner confirms source/chunk
  input exists for rebuild. The new index must be created at an explicit local
  path and checked with count/search evidence.
- Automatic migration/rebuild is not a current guarantee.

## Restore drill evidence

A synthetic drill ran on 2026-07-25 in a temporary directory only. It wrote and
restored one synthetic record in each Workspace Chat persistent category
(notebook, conversation, message, temporary source, notebook source and source
selection), then restored one synthetic RAG SQLite chunk and verified
`count()` plus lexical `search()`.

The drill did not read, write or delete `local_cases/`, real owner files, API
keys or production-like runtime data. It proves the documented manual copy/
restore shape against the current loader/index contract; it does **not** prove
real-data completeness, backup encryption, RTO/RPO, cross-version compatibility
or a provider-free app startup on owner data.

Before claiming this procedure effective for a changed persistent schema, run a
new synthetic drill and follow
[data migration compatibility](DATA_MIGRATION_COMPATIBILITY.md). A drill using
real owner data remains optional and must remain local.

## Recovery objectives

RTO and RPO are `OWNER_DECISION_REQUIRED`. This document defines a manual,
best-effort local procedure; it does not promise a recovery duration or zero data
loss.
