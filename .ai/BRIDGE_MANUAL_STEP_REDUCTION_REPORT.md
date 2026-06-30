# Bridge Manual Step Reduction Report

## Before workflow
AIOS exported an evidence pack, then the owner manually copied/pasted a prompt or manually supplied a response JSON path. Saving the response was coupled to import.

## After workflow
Case Cockpit creates a local Antigravity handoff bundle under ignored `local_runs/ide_handoff/outbox/<request_id>/`, shows the outbox folder and expected inbox path, and checks `local_runs/ide_handoff/inbox/<request_id>/response.json` from the UI. After validation, the owner can save the strong answer into the case.

## Manual steps removed
- No raw JSON paste is required as the default path.
- No CLI is required for normal owner flow.
- The expected inbox path is generated and displayed by AIOS.

## Manual steps remaining
- The owner still runs Antigravity manually on the local bundle.
- The owner/model still saves `response.json` to the shown inbox path.
- AIOS does not yet drive the IDE automatically.

## Privacy behavior
`local_only` bundles remain blocked from automatic cloud/provider calls. The prompt and UI warn the owner to use only approved local/IDE routes.

## Citation validation behavior
Import validates request_id, privacy acknowledgement, full-bundle usage, and cited evidence IDs against allowed evidence IDs from the bundle.

## Save-back behavior
A validated answer is saved as `ide_handoff_strong_answer` in the case and a processed import result is written locally.

## UI behavior
The owner section is labeled ÅgC?u n?i model m?nh qua AntigravityÅh and provides buttons to create the bundle, check Antigravity response, and save the validated strong answer.

## Remaining gap to 100% daily-use ready
The bridge is owner-pilot ready but not fully automated: Antigravity execution and writing `response.json` are still manual steps.
