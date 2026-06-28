# Full-Bundle IDE Handoff Report

## Implemented
- Added `src/aios_habit/ide_handoff_bridge.py`.
- Added local ignored full-bundle outbox/inbox/imported flow under `local_runs/ide_handoff/`.
- Added bundle files: `manifest.json`, `question.md`, `prompt.md`, `evidence_full.jsonl`, `evidence_full.md`, `source_manifest.json`, `completeness.json`, `README_FOR_IDE.md`.
- Added response import validation and case save support with route `ide_full_bundle_handoff`.
- Added Case Cockpit UI subsection: `Trả lời bằng AI IDE từ full bundle`.

## Owner usage
1. Create full bundle in Case Cockpit.
2. Tell Antigravity/IDE AI to read the complete request folder and write response JSON to inbox.
3. Import response JSON into AIOS; AIOS validates before saving.

## What send all means
- All extracted evidence items supplied for the selected scope are exported.
- Normal full-bundle mode has `omitted_items_count == 0`.
- Size guard stops export instead of silently omitting.

## Privacy behavior
- AIOS does not call cloud providers.
- `local_only` bundles are marked not externally allowed.
- Bundle includes warning that owner must approve IDE/model path.

## Response schema
Required fields include `request_id`, `model_tool_name`, `answer_text`, `evidence_ids_used`, `source_files_used`, `missing_evidence`, `confidence_label`, `risk_label`, `privacy_acknowledged`, `used_full_bundle`, and `notes`.

## Validation rules
- Request ID must match outbox.
- Evidence IDs must be subset of bundle IDs.
- `privacy_acknowledged` is required for `local_only`.
- `used_full_bundle` must be true.
- Empty evidence refs are review-required and not final.

## Tests and smoke
- Focused bridge tests added.
- Manual fake/sanitized roundtrip passed with no provider call.

## Safety
- Raw docs committed: NO.
- Raw bundles committed: NO.
- Raw answers committed: NO.
- NotebookLM parity claimed: NO.
- P1.0 opened: NO.
