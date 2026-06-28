# Full-Bundle Antigravity Roundtrip Report

## Roundtrip Result
- **fake/sanitized evidence used:** YES
- **request_id:** REQ-ANTIGRAVITY-ROUNDTRIP-001
- **bundle path:** local_runs/ide_handoff/outbox/REQ-ANTIGRAVITY-ROUNDTRIP-001
- **response path:** local_runs/ide_handoff/inbox/RESP-REQ-ANTIGRAVITY-ROUNDTRIP-001.json
- **Antigravity read full bundle:** YES
- **response JSON written:** YES
- **AIOS import validation:** PASS
- **answer saved to case:** YES
- **route_summary:** ide_full_bundle_handoff
- **final answer:** True
- **evidence refs saved:** ['EVD-ROUND-001', 'EVD-ROUND-002', 'EVD-ROUND-003']
- **used_full_bundle:** True
- **privacy_acknowledged:** True

## Bundle completeness
- **FULL_BUNDLE_COMPLETE:** YES
- **omitted_items_count:** 0
- **evidence_item_count:** 3
- **chunk_count:** 3
- **bundle_sha256:** b455e60719cc602c99faaf33e969bc538fed34404f8edd2c3507bba673a90cd1
- **metadata-only handling:** Tested implicitly via logic rules
- **size guard:** Tested implicitly via logic rules

## Negative validation
- **wrong request_id rejected:** YES
- **unknown evidence ID rejected:** YES
- **privacy_acknowledged false rejected:** YES
- **used_full_bundle false rejected:** YES
- **empty evidence IDs review-required:** YES

## Visual UI
- **full bundle section visible:** NOT RUN (Backend roundtrip passed)
- **create bundle button visible:** NOT RUN
- **import response input visible:** NOT RUN
- **UI result:** Visual UI check not run; backend full-bundle roundtrip PASS.

## Validation & Safety
- **focused tests:** PASS
- **full pytest:** PASS
- **package import:** PASS
- **CLI audit:** PASS
- **real docs tracked:** NO
- **runtime outputs tracked:** NO
- **automatic provider call:** NO
- **raw bundles committed:** NO
- **raw docs committed:** NO
- **raw answers committed:** NO
- **local_runs committed:** NO
- **API keys printed:** NO

## Claims
- **NotebookLM parity claimed:** NO
- **P1.0 opened:** NO
