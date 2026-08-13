# Data Model: Resumable Stage A Preparation

## Preparation checkpoint

| Field | Meaning | Validation |
|---|---|---|
| `schema_version` | Checkpoint format revision | exact supported integer |
| `status` | `building`, `failed`, or `ready` | `ready` is written only after full preparation |
| `identity` | Frozen content-addressed stage identity | exact equality required for resume |
| `completed_document_ids` | Ordered opaque committed document IDs | subset of current materialized document IDs, no duplicates |
| `total_sources` | Number of text-bearing sources | equals current staging source count |
| `last_error` | Safe failure category | no raw exception detail |
| `updated_at` | UTC checkpoint update time | written atomically |

## State transitions

```text
missing -> building -> ready
                  -> failed -> building (only with exact identity)
```

A `failed` checkpoint never qualifies as a staging manifest. A changed identity is rejected rather than transitioned.
