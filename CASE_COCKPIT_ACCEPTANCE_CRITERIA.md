# Case Cockpit Acceptance Criteria

## v0.1 Criteria
- App opens via `.bat` launcher.
- User can create a case.
- User can add evidence: Excel/CSV, image/screenshot, paste/log, note.
- Case Map renders a visual graph or Mermaid graph plus fallback table.
- Next Actions are generated from case state.
- Prompt Pack includes situation, evidence summary, unknowns/hypotheses, requested output, and no invented facts instruction.
- Handover is generated as Markdown.
- Audit shows PASS/FAIL table.
- Local-only safety is visible and enforced.

## v0.2 Criteria
- Better timeline editing and ordering.
- Better graph rendering with evidence type markers.
- Excel abnormal row/column hints.
- Optional OCR hook, not mandatory.
- Basic case similarity from local completed cases.
