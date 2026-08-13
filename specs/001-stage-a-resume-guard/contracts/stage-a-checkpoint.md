# Stage A Checkpoint Contract

The benchmark staging CLI owns `workspace_stage_checkpoint.json` next to `workspace_stage_manifest.json`.

- The checkpoint is atomic JSON and ignored runtime evidence.
- The identity is the existing `workspace_stage_identity` object unchanged.
- The runner initializes a `building` checkpoint before source preparation.
- The adapter invokes its progress callback only after a source has committed successfully.
- Each callback writes ordered completed opaque `document_id` values and advances the content-free heartbeat.
- A matching incomplete checkpoint is resumable. A stale, unreadable, or mismatched checkpoint fails closed.
- A source deadline failure writes `failed` with a safe category and does not create a ready stage manifest.
- The contract does not create a provider, call NotebookLM, or invoke synthesis.
