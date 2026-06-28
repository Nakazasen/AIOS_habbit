# Single-Screen Owner Workflow Design

## Core Product Truth
The current AIOS Case Cockpit UI has failed due to excessive tabs and asking the owner to understand backend systems. The daily owner workflow must be a single screen.

## Target Experience: "Xử lý việc hôm nay"
- "Làm việc hằng ngày" and "Nhập nhanh sự việc" are merged into a single entry point.
- The workflow must be progressively revealed. Users only see what they need now.
- NotebookLM-like simplicity is the target: documents → question → answer with sources.

## AIOS Differentiators vs. NotebookLM
While copying the simplicity, AIOS maintains its strengths:
- Excel / XLSX / XLSM robust support
- Screenshots / pasted images
- Logs / txt / html
- `local_only` privacy blocks
- Full-bundle IDE handoff
- Case memory and learning memory

## Progressive State Machine
The app must block invalid/missing input and not ask users to understand backend concepts.
States:
1. `START`: No issue, no evidence.
2. `ISSUE_ENTERED`: Issue present, no evidence.
3. `EVIDENCE_ADDED`: Issue + evidence.
4. `READY_TO_ANALYZE`: Valid inputs exist.
5. `ANALYZED`: Summary/extraction done.
6. `ANSWER_READY`: AI answer or local draft ready.
7. `CASE_SAVED`: Final save.

Errors/Blocks:
- `BLOCKED_MISSING_ISSUE`
- `BLOCKED_MISSING_EVIDENCE`
- `BLOCKED_UNSAFE_PRIVACY`

## Technical Details Hidden
Technical terminology (RAG, chunk, manifest, provider, route log, prompt pack, raw JSON) will be hidden behind a "Chi tiết kỹ thuật" expander.

- NotebookLM parity claimed: NO
- P1.0 opened: NO
