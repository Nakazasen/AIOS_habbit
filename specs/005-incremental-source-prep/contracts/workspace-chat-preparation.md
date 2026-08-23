# Workspace Chat Preparation Contract

## Readiness summary

```json
{
  "total": 75,
  "ready": 12,
  "processing": {"source_id": "SRC-...", "title": "..."},
  "pending": 61,
  "failed": 2,
  "bge_available": true
}
```

If `bge_available` is false, no source may be represented as processing.

## Source actions

- `retry_source(source_id)` changes only a failed/stale source to `pending`.
- `retry_failed()` requeues failed enabled sources.
- `cancel_pending_question(token)` cancels only the question; it never drops the source from the background queue.

## Provenance

```json
{
  "bridge_name": "Antigravity Sidecar",
  "generation_provider": "Gemini Web",
  "verified_model_id": null,
  "operational_mode": "direct"
}
```

`verified_model_id: null` renders as “Chưa xác minh tên model”, never an invented name.
