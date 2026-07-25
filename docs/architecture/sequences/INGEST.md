# Sequence: Local Source Ingest

Status: `ACTIVE`
Owner role: Project owner / architecture reviewer
Last reviewed: 2026-07-25
Review cadence: Before changing upload, extraction or source persistence

```mermaid
sequenceDiagram
    participant O as Owner
    participant UI as Workspace Chat
    participant X as Local ingest/extractor
    participant S as Local JSONL store
    O->>UI: Select file or paste text and choose privacy label
    UI->>X: Read local bytes/text
    X-->>UI: Safe extraction result or owner-facing failure
    UI->>S: Save selected source locally
    UI-->>O: Show source state and context summary
```

The upload path is local by default. A privacy label is selected/stored before a
source is eligible for later answer routing. Extraction errors should be shown as
localized owner messages, not raw tracebacks.

## Failure behavior

Unreadable input remains a local failure with a safe message. It does not trigger
provider fallback or source upload.

## Related records

- [Threat model](../../security/THREAT_MODEL.md)
- [User guide](../../user/WORKSPACE_CHAT_USER_GUIDE.md)
