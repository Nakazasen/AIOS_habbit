# AIOS Router Synthesizer Patch Audit Report

Scope: audit the source-aware router and profile-specific RAG synthesis patch
introduced at commit `bca82f1`, using the current workspace state on
`2026-06-30`.

This audit checks readiness for a full NotebookLM 12Q rerun. It does not claim
NotebookLM replacement, global NotebookLM parity, or P1.0 opening.

## Baseline

- Repo: `[LOCAL_WORKSPACE]\AIOS_habbit`
- Branch: `main`
- Commit under audit: `bca82f1`
- Current HEAD before this audit report update: `5b33337`
- Current `origin/main` before this audit report update: `5b33337`
- Ancestry: `bca82f1` is an ancestor of current HEAD.
- Baseline caveat: dirty tracked files existed before this audit continuation.
  The tree was not clean, so any commit/push must be scoped carefully and cannot
  be treated as a clean baseline audit.
- Untracked file observed: `uv.lock`

## Implementation Verdict

Verdict: `PASS_PATCH_VALID_BUT_BASELINE_DIRTY`.

- Source router: implemented in `src/aios_habit/source_router.py`.
  `route_evidence_by_profile()` separates primary, supporting, and demoted
  evidence and emits `source_type_pass` plus warnings.
- Query profile classifier: implemented through
  `classify_generic_query_profile()` and normalized legacy labels in
  `src/aios_habit/rag_core_profiles.py`.
- Screenshot behavior: screenshot/image profiles prefer screenshot evidence and
  demote schema/HTML evidence. This is covered by
  `test_image_visible_facts_prefers_png_and_demotes_html`.
- Process behavior: procedure/process questions prefer document-like sources.
  This is covered by `test_procedure_steps_prefers_document_sources`.
- Spreadsheet mapping behavior: field/table/mapping questions prefer
  spreadsheet/table-like sources and are synthesized with field/key/table
  reminders.
- Mixed troubleshooting and handover behavior: troubleshooting and handover
  intents beat broad export/mapping keywords. This is covered by
  `test_troubleshooting_intent_beats_mapping_keyword` and
  `test_handover_intent_beats_export_mapping_keyword`.
- Profile-specific composer: `compose_final_owner_answer()` calls
  `classify_query_profile()` and `route_evidence_by_profile()`, orders routed
  primary/supporting evidence, writes role-marked evidence lines, and records
  `answer_profile`, `generic_profile`, `domain_playbook`, and
  `source_type_pass` metadata.
- Wrong source warning: missing required source types add route warnings,
  answer warnings, unsupported-conclusion text, and low confidence.
- `local_only` safety: preserved. The deterministic final composer does not call
  a provider or NotebookLM, and local-only warnings remain covered by tests.

## Evaluator Caps Verdict

Verdict: PASS for requested hard-cap mechanics in the current test suite.

- Generic/local draft max <= 6/12: implemented and tested.
- Wrong profile / process answered as table mapping max <= 6/12: implemented
  and tested.
- Wrong primary source type max <= 6/12: implemented through
  `source_type_pass=FAIL` and tested.
- Screenshot answer using HTML/schema primary max <= 5/12: implemented and
  tested.
- Process question answered as table mapping max <= 6/12: implemented and
  tested.
- Excel mapping without concrete fields/keys/table terms max <= 7/12: intended
  cap is documented; current implementation caps this path at 6/12, which is
  stricter than the requested maximum.
- Citations only in source table max <= 7/12: implemented and tested.
- Generic check-logs-only troubleshooting max <= 6/12: implemented through the
  concrete-steps cap and tested.
- Missing target source type without admitting missing evidence max <= 6/12:
  implemented and tested.
- HUMAN_REVIEW handling: side-by-side `HUMAN_REVIEW` metadata is capped and is
  not treated as a pass/win signal.

## 4Q Rerun Report Validity Verdict

Verdict: corrected and usable as a smoke report, not a full benchmark.

- Report valid as full 12Q rerun: NO.
- Report valid as representative smoke check: YES, with caveats.
- Q04: valid for process-boundary routing and missing-evidence honesty. A
  `source_type_pass=FAIL` path proves safety/capping, not answer quality by
  itself.
- Q06: corrected to spreadsheet mapping in the smoke check, not screenshot
  visible facts.
- Q10: corrected to screenshot visible facts in the smoke check, not mixed
  troubleshooting.
- Q12: valid for owner handover and classifier priority.
- Exact 4Q smoke queries classify in current code as:
  - Q04: `procedure_steps`
  - Q06: `extract_fields`
  - Q10: `image_visible_facts`
  - Q12: `handover_general`
- Misleading claims corrected: YES.

## Validation

- `py -3 -m pytest tests/test_source_router.py -vv`: 5 passed.
- `py -3 -m pytest tests/test_final_answer_composer.py -vv`: 11 passed.
- `py -3 -m pytest tests/test_notebooklm_compare.py -vv`: 21 passed.
- `py -3 -m pytest tests/test_rag_answer_composer.py -vv`: 9 passed.
- `py -3 -m pytest tests/test_citation_answer.py -vv`: 6 passed.
- `py -3 -m pytest tests/test_case_cockpit_ui_copy.py -vv`: 32 passed.
- Full pytest command: `py -3 -m pytest`
- Full pytest count: 450 passed.
- Package import:
  `py -3 -c "import sys; sys.path.insert(0, 'src'); import aios_habit.case_cockpit; print('package import ok')"`
  printed `package import ok` with a benign Streamlit bare-mode warning.
- CLI audit:
  `cmd /c "set PYTHONPATH=src&& py -3 -m aios_habit.cli audit"` returned
  `{"errors": [], "status": "PASS", "warnings": []}`.

The current repo has 400+ tests. The earlier 30/30 result was only a focused
subset, not the full test suite.

## Safety

- `local_runs`: ignored by `.gitignore`.
- `API Key.txt`: ignored by `.gitignore`.
- Tracked runtime/raw-output pattern scan: no matches for `local_runs`,
  `notebooklm_answers`, `aios_answers`, `questions.jsonl`, `evaluation.json`,
  database files, API key files, env files, or image extensions.
- Secret grep: no matches for real API-token/private-key patterns after
  excluding sanitizer-test fixtures.
- Extra local-path/name grep: no matches for local workspace paths, source-root
  names, personal name, or local hostnames in tracked files.
- Dirty tracked files remain in the workspace. They must be reviewed or scoped
  before any clean commit/push claim.

## Readiness

- Ready for full redacted NotebookLM 12Q rerun: YES for the router/synthesizer
  patch mechanics, assuming the rerun starts from a reviewed clean or scoped
  workspace.
- Ready to claim NotebookLM replacement: NO / NOT YET.
- Ready to claim global NotebookLM parity: NO.
- P1.0 opened: NO.

## Recommended Next

1. `RERUN_NOTEBOOKLM_12Q_AFTER_ROUTER_SYNTHESIZER_PATCH`
2. `FIX_REMAINING_RAG_GAPS`
3. `VISUAL_KNOWLEDGE_MAP_90_INTERACTIVE_SPRINT`
4. `OWNER_EXPLICIT_P1_APPROVAL`
5. `P1_OPENING_PLAN_EXECUTION`
