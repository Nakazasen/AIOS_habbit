# AIOS Router & Synthesizer: 4Q Rerun Report

## Overview

This report documents a strict representative 4Q smoke check after the
`source_router` and `final_answer_composer` patch. It is not a full NotebookLM
12Q rerun and must not be used as a NotebookLM replacement or global parity
claim.

## Rerun Parameters

- Branch: main
- Strategy: `QueryProfile` matched routing and `source_type_pass` evaluation.
- Privacy mode: local_only
- Full benchmark parity: NO
- P1.0 opened: NO

## Audit Correction

The earlier 4Q wording overstated the run. The IDs were representative labels,
but they did not exactly match the failure-analysis meanings for every question:

- Q04 still represents process boundary behavior.
- Q06 in this smoke check is spreadsheet mapping, not screenshot visible facts.
- Q10 in this smoke check is screenshot visible facts, not mixed troubleshooting.
- Q12 represents owner handover, but the original query text included `export`
  and `process`, which exposed a classifier-priority risk. That risk is now
  covered by tests so handover/troubleshooting intents beat generic export or
  mapping keywords.

## Rerun Results

### Q04: Process Boundary

Query: "Quy trinh xu ly automatic manual boundary nhu the nao?"

- Profile: `process_boundary`
- Expected source type: `document`
- Behavior before patch: AIOS could retrieve spreadsheet snippets and use a
  table-mapping style answer for a process question.
- Behavior after patch: Router prefers document evidence. If the required
  document source type is missing, `source_type_pass=FAIL` and the answer must
  explicitly admit missing primary evidence.
- Strict result: safety mechanism works, but `source_type_pass=FAIL` proves a
  cap/honesty path, not improved answer quality by itself.

### Q06: Spreadsheet Mapping

Query: "Export mapping cho truong route code la gi?"

- Profile: `excel_mapping`
- Expected source type: `spreadsheet`
- Behavior before patch: AIOS could answer from generic PDF/process text without
  extracting spreadsheet fields or keys.
- Behavior after patch: Router prefers spreadsheet evidence, and evaluator caps
  Excel mapping answers that do not mention concrete fields, keys, mapping, or
  table terms.
- Strict result: targeted spreadsheet behavior is improved in fixture coverage,
  but this is not the screenshot-visible-facts benchmark slot.

### Q10: Screenshot Visible Facts

Query: "What does the WMS screenshot show for the error message?"

- Profile: `screenshot_visible_facts`
- Expected source type: `screenshot` (`png`, `jpg`)
- Behavior before patch: HTML/schema evidence could be treated like visible
  screenshot facts.
- Behavior after patch: Router demotes schema/HTML evidence for screenshot
  profiles, and evaluator caps screenshot answers that rely on HTML/schema as
  primary evidence.
- Strict result: screenshot routing is improved in fixture coverage, but this
  is not the mixed-troubleshooting benchmark slot.

### Q12: Owner Handover / Next Actions

Query: "Owner next actions and handover process for missing export route"

- Profile: `owner_handover`
- Expected source type: mixed
- Behavior before patch: broad `export` matching could classify this as
  `excel_mapping`.
- Behavior after patch: owner handover and troubleshooting intents are checked
  before generic export/mapping keywords. Composer adds owner-facing next
  actions and handover fields for the `owner_handover` profile.
- Strict result: classifier risk corrected and covered by tests. Still requires
  full 12Q rerun on redacted benchmark inputs.

## Global Parity Status

- NotebookLM parity reached: NO
- P1.0 opened: NO
- Replace NotebookLM claim: NO / NOT YET

## Conclusion

The focused patch now has stronger source-type routing, profile-specific answer
synthesis, and hard evaluator caps for common wrong-profile/wrong-source
failures. The 4Q smoke check is useful evidence for readiness, but it is not a
complete benchmark and does not prove NotebookLM parity. Next step remains a
full redacted 12Q rerun with strict evaluator caps and human review.
