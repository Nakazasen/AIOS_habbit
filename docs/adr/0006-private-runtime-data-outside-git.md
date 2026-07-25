# ADR-0006: Private Runtime Data Remains Outside Git

Status: `ACCEPTED`
Owner role: Project owner / privacy reviewer
Last reviewed: 2026-07-25
Review cadence: Before adding a storage path, export or CI artifact

## Context

Tracked source/history is not an appropriate destination for owner documents,
chat state, credentials, screenshots or generated private evaluation output.

## Decision

Keep runtime/private paths Git-ignored. The repository tracks code, schemas,
templates, synthetic examples and sanitized documentation only. CI must not
upload private runtime content or invoke providers with owner data.

## Consequences

- Operators must run backup/restore themselves for local data.
- Tests require synthetic fixtures.
- A staged private file is a release blocker, not a harmless warning.

## Security and privacy impact

This provides a baseline against accidental disclosure but cannot protect a file
that an owner intentionally shares outside the repository.

## Migration and rollback

If a private file is staged, remove it from the Git index and update ignore rules
without deleting owner data unless explicitly authorized. If already committed,
contain access and follow the incident procedure; history rewriting needs owner
review.

## Evidence

- [Git-ignore rules](../../.gitignore)
- [Backup and restore](../operations/BACKUP_RESTORE.md)
- [Incident response](../operations/INCIDENT_RESPONSE.md)
