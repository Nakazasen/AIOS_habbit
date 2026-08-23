# Data Model

## SourcePreparationLedger

| Field | Meaning |
|---|---|
| `source_scope`, `source_id` | Stable notebook or temporary-source identity. |
| `source_fingerprint` | Content plus privacy version; a change invalidates readiness. |
| `model_id`, `model_revision` | BGE identity required to reuse vectors. |
| `state` | `pending`, `processing`, `ready`, `failed`, or `cancelled`. |
| `priority` | `interactive`, `normal`, or `backfill`. |
| `attempt_count`, `last_error`, `updated_at` | Retry and user-visible diagnostics. |
| `document_id` | Opaque BGE index identifier. |

State transitions: `pending -> processing -> ready`; failure becomes `failed`; retry makes `failed -> pending`; fingerprint/model change makes any prior state `pending`; stale process recovery makes `processing -> pending`.

## PendingQuestion

Session-only record: conversation id, idempotency token, question, source-selection snapshot, exact prepared source ids, creation time, and submitted flag. It expires after five minutes or a source-selection change.

## GenerationProvenance

`bridge_name`, `generation_provider`, `verified_model_id | null`, `operational_mode`, and `verification_note`. The UI must never substitute a requested alias for `verified_model_id`.

## GroupedEvidence

One group per source id: source title, chunk count, and child chunks with evidence id, text, and optional page/section.
