# Visual Knowledge Map MVP Core Audit Report

## Overall Verdict

PASS_VISUAL_MAP_CORE_FIXED_CRITICAL_ISSUES

The Visual Knowledge Map MVP core is ready for owner trial after critical fixes to claim validation and privacy-safe export identifiers. It remains MVP core only: no interactive graph UI, no graph database, no visualization library selection, no NotebookLM replacement claim, no global parity claim, and no P1.0 opening.

## Schema Audit

- Node and edge schemas are explicit dataclasses with allowed node and edge type sets.
- Unknown node types and unknown edge types are rejected.
- Generic untyped `related` edges are rejected by the validator.
- Edge reasons are required.
- Edge endpoints must point to existing graph nodes.
- Claim validation now accepts a real supporting edge in either natural direction involving the claim, or a claim-owned `has_missing_evidence` edge to a `missing_evidence` node.
- Missing evidence is first-class and no longer masks unrelated bad evidence references.

## Builder Audit

- Graph building is deterministic-first from case, evidence, final answer, imported strong answer, learning cards, claim guard result, and optional domain playbook input.
- No LLM-only graph generation is used as source of truth.
- No automatic root-cause claim generation was found.
- No hidden causality inference or confidence escalation was found.
- Domain playbook handling is generic; the manufacturing sample uses the same domain metadata path as HR, accounting, Japanese learning, and IT manual samples.
- Evidence nodes are collapsed by stable evidence node ID.
- Final owner answer and imported Antigravity strong answer are kept separate by answer metadata and verified/unverified status.
- Imported strong answer is not marked verified unless it is the final owner answer path.
- Claim guard blocks now create risk, blocked claim, missing evidence, `blocks`, and `has_missing_evidence` graph objects.
- Warnings become risk or missing-evidence nodes with limitation edges.

## Export Audit

- `local_full` preserves full local graph data for local use.
- `local_redacted`, `cloud_safe_summary`, and `notebooklm_safe` redact unsafe display data.
- `cloud_safe_summary` and `notebooklm_safe` remove `local_only` nodes and unsafe edges.
- Absolute paths, employee IDs, the test personal-name literal, and local/internal hostnames are redacted in safe modes.
- Safe JSON and Mermaid exports no longer leak unsafe local paths through node or edge identifiers.
- Mermaid labels are redacted and escaped for the current MVP scope.
- JSON export includes export mode, privacy summary, redaction summary, and warnings.
- `notebooklm_safe` includes an explicit warning that NotebookLM parity is not claimed and P1.0 is not opened.

## UI Stub Audit

- The Case Cockpit stub exposes the Vietnamese label `Bản đồ tri thức công việc`.
- The stub builds the current-case graph directly from local case/evidence/learning state and does not require CLI use.
- It exposes local JSON export and safe Mermaid export.
- It does not add a graph UI library, graph database, or interactive graph UI.
- The safe Mermaid export path now benefits from export-level identifier redaction.

## Test Audit

- Focused visual-map tests cover typed node types, typed edge types, required edge reason, invalid node/edge rejection, claim support/missing-evidence requirements, local-only removal from cloud and NotebookLM-safe modes, local path redaction, employee ID redaction, personal-name redaction, hostname redaction, safe Mermaid export, JSON export shape, multi-domain samples, Antigravity strong-answer citation edges, claim guard block handling, Vietnamese UI label, and no NotebookLM/P1.0 overclaim in safe output.
- Tests are materially stronger after this audit because they now catch evidence-ID masking and Mermaid/JSON identifier leaks.
- Remaining warning: tests are still schema-contract tests, not a full UI/browser acceptance test, and redaction is pattern-based rather than a formal DLP engine.

## Privacy Audit

- Critical privacy leak fixed: safe Mermaid and safe JSON exports no longer preserve unsafe local paths in graph identifiers.
- Hostname redaction was added for `.local`, `.lan`, and `.internal` style hostnames.
- Source display labels remain collapsed to `[LOCAL_SOURCE]` in redacted modes.
- Ignored local runtime folders remain ignored and were not staged.

## Claim Discipline Audit

- Critical claim-discipline bug fixed: a single missing-evidence node can no longer waive invalid evidence IDs across the whole graph.
- Critical builder bug fixed: claim-guard blocked claims now include first-class missing evidence and validate under the claim contract.
- No NotebookLM replacement, global parity, or P1.0 opened claim was added.
- Graph output remains MVP core only and should not be described as globally verified knowledge.

## Critical Fixes Applied

1. Tightened `validate_visual_graph` so claim support is explicit and evidence references must match graph evidence nodes.
2. Updated claim-guard graph building to attach blocked claims to first-class missing-evidence nodes.
3. Added deterministic safe source-node keys in the builder.
4. Added safe export identifiers and hostname redaction for redacted/cloud/NotebookLM-safe exports.
5. Added regression tests for evidence-to-claim support, invalid evidence references, claim-guard validation, hostname redaction, and safe Mermaid/JSON identifiers.

## Remaining Gaps

- No interactive graph UI yet.
- No owner-trial evidence from a real case yet.
- No full browser-level UI acceptance test for the Case Cockpit stub.
- Redaction is regex-pattern based and should be expanded if new identifier formats appear.
- The MVP does not yet include multi-case Work Stream Map expansion.

## Readiness

- Ready for owner trial: YES, after the critical fixes in this audit.
- Ready for interactive UI sprint: YES, as a next sprint after owner trial; core schema/privacy contracts are now stronger.
