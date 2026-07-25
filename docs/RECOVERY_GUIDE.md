# Recovery Guide

Status: `ACTIVE`
Owner role: Operator / local data owner
Last reviewed: 2026-07-25
Review cadence: Before release and after persistent-store changes

Use [Backup and Restore](operations/BACKUP_RESTORE.md) as the canonical recovery
procedure and [Incident Response](operations/INCIDENT_RESPONSE.md) for suspected
privacy, credential, data-loss or public-exposure events.

If private data is staged, remove it from Git tracking without deleting the owner
copy unless explicitly required. Do not claim a backup is recoverable until a
synthetic restore drill has been completed.
