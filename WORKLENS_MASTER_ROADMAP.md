# WorkLens Master Roadmap

Every phase uses PASS/FAIL gates. A phase is not complete until deliverables, validation, handover, and rollback notes exist.

## Phase 0 Product Governance
- Objective: Establish product direction and repo governance.
- Scope: North star, migration policy, inheritance map, acceptance criteria.
- Deliverables: Governance docs in root.
- Risk: Over-documenting without execution.
- Dependencies: Current Case Cockpit v0.1.
- Validation: Docs exist and align to daily case loop.
- Exit Criteria: PASS if all governance files exist.
- Handover: PRODUCT_NORTH_STAR and this roadmap.
- Rollback: Revert governance doc commit.

## Phase 1 Case Cockpit v0.1 Stabilization
- Objective: Make the Monday pilot usable.
- Scope: Launchers, case create/edit, evidence add, map, actions, prompts, handover, audit.
- Deliverables: Streamlit app and tests.
- Risk: UI too shallow for real work.
- Dependencies: Streamlit, pandas, openpyxl.
- Validation: compileall, pytest, import checks, launcher checks.
- Exit Criteria: PASS if UI opens and core loop works.
- Handover: docs/CASE_COCKPIT.md.
- Rollback: Revert cockpit modules while preserving docs.

## Phase 2 Real Work Pilot
- Objective: Use Cockpit on real cases locally.
- Scope: Manual daily use, no private data in git.
- Deliverables: Pilot notes kept local.
- Risk: User friction, missing workflow fields.
- Dependencies: Phase 1 PASS.
- Validation: MONDAY_PILOT_CHECKLIST.
- Exit Criteria: PASS if user completes at least one case loop.
- Handover: sanitized learnings only.
- Rollback: Pause pilot and fix blockers.

## Phase 3 Post-Pilot Hardening
- Objective: Fix pilot pain points.
- Scope: UX polish, validation, error handling.
- Deliverables: small UI fixes and tests.
- Risk: Feature creep.
- Dependencies: Pilot feedback.
- Validation: regression tests and pilot checklist.
- Exit Criteria: PASS if top blockers resolved.
- Handover: changelog.
- Rollback: revert individual fixes.

## Phase 4 4-Repo Inheritance Audit
- Objective: Harvest previous work safely.
- Scope: Read-only audit of AIOS_habbit, ABW_NVIDIA_FUSION_CONTROL, skill-Anti-brain-wiki_note, Nvidia.
- Deliverables: docs/inheritance_audit reports.
- Risk: Copying code without contracts.
- Dependencies: local repo access.
- Validation: every candidate mapped to Case → Evidence → Map → Action → Learning.
- Exit Criteria: PASS if reports exist and no code is ported prematurely.
- Handover: INHERITANCE_SUMMARY.
- Rollback: revert audit docs.

## Phase 5 WorkLens Modular Architecture
- Objective: Prepare modules without a disruptive rewrite.
- Scope: case_core, ingest, visual_graph, memory, agent_bridge, governance, export.
- Deliverables: module boundary docs and low-risk refactors.
- Risk: premature abstraction.
- Dependencies: Phase 4 audit.
- Validation: tests remain green.
- Exit Criteria: PASS if module map exists and app still works.
- Handover: WORKLENS_ARCHITECTURE.
- Rollback: keep Streamlit monolith.

## Phase 6 Visual CaseGraph + Timeline
- Objective: Improve visual reasoning.
- Scope: graph rendering, timeline model, evidence markers.
- Deliverables: better Case Map and timeline views.
- Risk: visual complexity without utility.
- Dependencies: stable case data model.
- Validation: visual smoke tests and user acceptance.
- Exit Criteria: PASS if map helps choose next action.
- Handover: UI docs.
- Rollback: fallback table.

## Phase 7 Practical Ingest Engine
- Objective: Improve real evidence capture.
- Scope: better Excel summaries, text file import, optional OCR.
- Deliverables: ingestion helpers and tests.
- Risk: ingesting private data into git.
- Dependencies: local_cases safety.
- Validation: synthetic fixtures only.
- Exit Criteria: PASS if ingestion helps current cases.
- Handover: ingest docs.
- Rollback: disable ingest path.

## Phase 8 Agent Bridge
- Objective: Connect AI assistance safely.
- Scope: copyable prompt packs first; bridge only later.
- Deliverables: prompt contracts and optional local bridge.
- Risk: over-automation and data leaks.
- Dependencies: governance and privacy audit.
- Validation: local_only exclusion tests.
- Exit Criteria: PASS if AI help improves next actions without leaking data.
- Handover: bridge contract.
- Rollback: copy-only prompts.

## Phase 9 Governance + Memory + Export
- Objective: Convert completed cases into reusable learning.
- Scope: case outcome, lessons, verified memory, export packs.
- Deliverables: memory pipeline and safe exports.
- Risk: unsupported claims become false memory.
- Dependencies: evidence validation.
- Validation: verified memory requires evidence.
- Exit Criteria: PASS if learning is evidence-backed.
- Handover: memory docs.
- Rollback: mark learnings needs_evidence.

## Phase 10 Production Failure Intelligence
- Objective: Add failure intelligence after evidence discipline matures.
- Scope: pattern library, recurrence hints, risk signals.
- Deliverables: practical recommendations, not fake predictions.
- Risk: hallucinated root cause.
- Dependencies: many completed cases.
- Validation: historical evidence and user review.
- Exit Criteria: PASS if insights are evidence-grounded.
- Handover: intelligence report.
- Rollback: disable recommendations.
