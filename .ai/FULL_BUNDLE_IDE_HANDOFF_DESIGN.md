# Full-Bundle IDE Handoff Design

## Current limitation
- Current Strong Answer flow is manual prompt copy/paste.
- Existing prompt export is evidence-pack/top-results oriented and can behave like partial snippet handoff.
- Owner requirement is a full-bundle mode where the IDE AI can read the complete selected local evidence package.

## Owner requirement
- Full bundle, not partial snippet handoff.
- "Send all" means all extracted evidence in the explicit selected scope.
- Scope must be auditable and completeness must be visible.

## Local filesystem architecture
1. AIOS writes a request bundle under ignored `local_runs/ide_handoff/outbox/REQ-.../`.
2. Antigravity/IDE AI reads local bundle files from disk.
3. IDE AI writes response JSON/Markdown under ignored `local_runs/ide_handoff/inbox/`.
4. AIOS validates and imports the response into the case.

## Privacy model
- AIOS does not call cloud providers.
- `local_only` evidence is included only in local handoff files.
- Bundle includes explicit owner warning: use IDE/model path only if owner approves.
- NotebookLM parity claimed: NO.
- P1.0 opened: NO.

## Bundle scopes
- `active_case_all`: all evidence currently attached to the active case.
- `selected_folder_all`: all extracted evidence from a selected local folder if supplied by caller/UI.
- `current_question_retrieval_plus_full_scope_manifest`: retrieval/ranking summary plus full source manifest for the scope.

## Completeness checks
- Full bundle export includes all supplied evidence items.
- `omitted_items_count` must be `0` unless a size guard blocks export or explicit override is added later.
- Normal mode stops on size guard instead of silently omitting content.
- Manifest includes `FULL_BUNDLE_COMPLETE` and counts for sources, evidence items, chunks, total text chars, and formats.
- Bundle SHA-256 covers the exported evidence payload and changes when evidence changes.

## Response import checks
- `request_id` must match an existing outbox request.
- `answer_text` and `model_tool_name` must be non-empty.
- For `local_only`, `privacy_acknowledged` must be true.
- `used_full_bundle` must be true.
- `evidence_ids_used` must be a subset of bundle evidence IDs.
- Empty evidence IDs import only as review-required/non-final or is blocked by strict final validation.

## UI changes
- Add `Trả lời bằng AI IDE từ full bundle` under Strong Answer area.
- User can create full bundle, copy IDE instruction, enter response JSON path, and import response.
- UI must say full bundle in selected scope, no automatic cloud call, owner responsible for IDE cloud use, and AIOS validates response before saving.

## Non-goals
- No cloud provider call from AIOS.
- No NotebookLM call.
- No vector DB or graph DB.
- No RAG architecture rewrite.
- No raw bundles/docs committed.
