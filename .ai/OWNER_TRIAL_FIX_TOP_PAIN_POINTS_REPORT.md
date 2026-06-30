# OWNER_TRIAL_FIX_TOP_PAIN_POINTS_REPORT

## Pain points addressed
1. Manual request_id tracking is reduced by pending request discovery from `local_runs/ide_handoff/outbox`.
2. Manual response JSON assembly is reduced by a Markdown paste fallback.
3. Pending response discovery now scans inbox paths for `response.json`.
4. JSON escaping risk is reduced because pasted Markdown is converted into structured response draft JSON by AIOS.
5. Visual Map preview now appears after IDE answer save-back in the owner flow.

## What changed
- Added pending request helpers in `ide_handoff_bridge.py`.
- Added strict Markdown-to-IDE-response conversion and import validation.
- Updated Case Cockpit Antigravity bridge UI with Vietnamese labels, pending request list, inbox scan, Markdown fallback, owner confirmations, and save-back flow.
- Added Visual Map preview helper and inline preview after save-back.
- Added tests for pending request discovery, Markdown import, UI labels, and preview counts.

## Owner workflow before
- Owner created a bundle, manually copied request_id, navigated to inbox/outbox folders, assembled JSON manually, and separately opened map exports.

## Owner workflow after
- Owner creates bundle, chooses a pending request from the UI, scans inbox automatically, or pastes Markdown and confirms privacy/full-bundle usage. AIOS validates citations and shows a Visual Map preview after save-back.

## Remaining manual steps
- Owner still runs Antigravity manually.
- Owner still confirms the model used the full evidence bundle.
- Owner may still copy/paste Markdown if no `response.json` is produced.

## Bridge behavior
- Pending outbox requests are listed with request_id, case_id, question, privacy, state, and response availability.
- Malformed folders are ignored safely.
- Existing response.json workflow is preserved.

## Markdown fallback behavior
- Markdown is preserved as `answer_markdown`.
- Evidence IDs are never invented.
- Missing evidence IDs add a limitation.
- Privacy acknowledgement and full-bundle confirmation must be explicitly true or validation fails.

## Visual Map preview behavior
- Preview includes node count, edge count, missing evidence count, risk/claim count, top node types, local JSON export, and safe Mermaid text.
- This is MVP core + preview only, not an interactive graph UI.

## Tests
- Added `tests/test_ide_handoff_pending_requests.py`.
- Added `tests/test_ide_handoff_markdown_import.py`.
- Updated UI/helper tests in existing files.
- Focused and full pytest were run successfully.

## Safety
- `local_runs`, `local_cases`, and `API Key.txt` remain ignored.
- No local case data, raw answer data, screenshots, API keys, or local-only runtime files were staged or committed.
- No NotebookLM replacement, global parity, or P1.0 claim was made.

## Remaining gaps
- Antigravity execution remains manual.
- Visual Map is still preview-only.
- A later UI interaction sprint can add a richer graph view without changing this MVP core.
