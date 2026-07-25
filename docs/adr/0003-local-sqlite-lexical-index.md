# ADR-0003: Local SQLite Lexical Index for RAG V2 Foundation

Status: `ACCEPTED`
Owner role: Project owner / RAG architecture reviewer
Last reviewed: 2026-07-25
Review cadence: Before changing retrieval storage, ranking or adding a vector service

## Context

RAG v2 needs generic, inspectable retrieval without cloud-default behavior or a
new mandatory vector dependency. Current foundation implements a local SQLite
chunk store with deterministic lexical scoring.

## Options considered

1. Cloud/vector database as initial index.
2. Local SQLite lexical index.
3. Reuse domain-specific legacy MOM index as generic core.

## Decision

Use local SQLite lexical indexing for the current generic foundation. The index
stores chunk text and metadata at a caller-selected path. It is not currently a
full FTS/BM25 implementation; the roadmap accurately records deterministic
lexical behavior and bilingual-ranking limitations.

## Consequences

- The index is inspectable and local but ranking is intentionally limited.
- PNG OCR and semantic/vector retrieval are not current guarantees.
- Callers must own index-path lifecycle, backup decision and rebuild input.

## Security and privacy impact

No source is sent to a provider merely by indexing. The local database can still
contain sensitive material and must be protected/ignored as runtime data.

## Migration and rollback

Index schema is created idempotently for the current chunk table. If an index is
corrupt or incompatible, preserve evidence as appropriate and rebuild from
available safe source/chunk input; do not claim lossless reconstruction without
that input.

## Evidence

- [RAG v2 design](../rag_v2/RAG_V2_DESIGN.md)
- [Persisted-data compatibility](../contracts/PERSISTED_DATA_COMPATIBILITY.md)
- [Backup and restore](../operations/BACKUP_RESTORE.md)
