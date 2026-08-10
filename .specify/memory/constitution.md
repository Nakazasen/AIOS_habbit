<!--
Sync Impact Report
- Version change: template (unversioned) → 1.0.0
- Modified principles: none; initial adoption derived from CONSTITUTION.md and AGENT_RULES.md
- Added sections: Operational Constraints; Development Workflow and Quality Gates
- Removed sections: none
- Follow-up TODOs: none
-->
# AIOS WorkLens Constitution

## Core Principles

### I. Evidence Before Assertion
Every durable memory, user-facing answer, PASS result, and project decision MUST
cite an evidence record or a reviewable artifact. A claim without sufficient
evidence MUST remain `candidate`, `PARTIAL`, `FAIL`, or `BLOCKED`; it MUST NOT be
presented as verified. Raw AI output is not evidence unless its original source
is retained and traceable. This protects the platform from invented knowledge
and false completion signals.

### II. Local-First Privacy and Consent
User data, local evidence, raw transcripts, spreadsheets, logs, screenshots,
and private configuration MUST remain local by default. `local_only` content and
unconfirmed learning material MUST NOT enter an external-cloud prompt, export,
or handover. Cloud use requires an explicit policy and the user's affirmative
consent; local AI use requires the explicit `include_local_only=True` choice
when applicable. Private runtime data, credentials, `.env`, and local case data
MUST NOT be committed to version control.

### III. Portable, Pattern-Based Knowledge
The product MUST preserve validated operational patterns rather than archival
chat wording. Durable knowledge MUST use documented open formats such as
Markdown, JSON, or YAML with a clear schema and provenance. No core knowledge
workflow may depend exclusively on one AI provider, opaque proprietary memory,
or non-exportable conversation history. This keeps the user's knowledge usable
across models and over time.

### IV. User-Centered Workspace Chat
Workspace Chat is the supported user-facing surface. User-visible functionality
MUST be Vietnamese-first, explain necessary technical constants in Vietnamese,
and transform internal failures into safe, clear localized messages. New work
MUST NOT restore retired Case Cockpit or Habit Studio paths, imports, launchers,
or test expectations without an explicitly approved architectural decision.

### V. Change Discipline and Verifiable Quality
Every non-trivial change MUST be audited and designed before implementation,
executed against an approved plan, covered by proportionate tests, and validated
with reproducible commands. Architecture, roadmap, and behavioral changes MUST
update their respective canonical records: `ARCHITECTURE.md`, `ROADMAP.md`, and
`PROJECT_HANDOVER.md`. A phase MUST be closed with recorded evidence before a
subsequent phase opens.

## Operational Constraints

- Python support MUST remain compatible with the declared project requirement
  (`>=3.11`), and dependencies MUST be managed through `pyproject.toml` and
  `uv.lock`.
- Supported modules MUST NOT import retired `studio` or `case_cockpit` code.
  Removing a legacy slice MUST remove its supported launch path and stale tests.
- New durable memory MUST follow this provenance path: `Raw Source → Evidence
  Record → Extracted Pattern → Validated Memory → Export Profile`.
- The priority order for conflicts is: user-data safety; evidence and
  correctness; long-term portability; extensibility; delivery speed.
- Complexity, external integrations, and data egress MUST have a documented
  rationale and a safe rollback or remediation path.

## Development Workflow and Quality Gates

1. Feature work MUST start with `/speckit-specify`; architecture-affecting or
   multi-step work MUST continue through `/speckit-plan` and `/speckit-tasks`
   before `/speckit-implement`.
2. Before merge or release, applicable changes MUST pass:
   `py -3 -m compileall src tests`, `py -3 -m pytest -q`,
   `$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit`, and
   `$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"`.
3. The CLI audit MUST report `"status": "PASS"`; otherwise the change MUST be
   recorded as `FAIL`, `BLOCKED`, or `PARTIAL` with the next corrective action.
4. Reviewers MUST inspect modified files, test evidence, privacy boundaries,
   and migration/rollback implications. Audit-only agents MUST NOT write feature
   code unless the user explicitly authorizes a minor correction.
5. Where `graphify-out/graph.json` exists, implementation and architectural
   investigation MUST query the graph before broad source inspection; code
   changes MUST refresh it with `graphify update .`.

## Governance

This constitution supersedes conflicting development habits and informal agent
instructions within AIOS WorkLens. `CONSTITUTION.md`, `AGENT_RULES.md`,
`ARCHITECTURE.md`, `ROADMAP.md`, and `PROJECT_HANDOVER.md` remain canonical
project records; their material governance requirements are incorporated here
for Spec Kit workflows, not replaced.

Amendments MUST be documented in this file, include a Sync Impact Report,
identify affected templates or workflows, and use semantic versioning: MAJOR for
incompatible principle redefinitions/removals, MINOR for new principles or
materially expanded obligations, and PATCH for clarifications only. Every plan,
task list, implementation review, and release assessment MUST verify compliance
with these principles; exceptions require explicit user approval, a bounded
scope, and recorded remediation or rollback.

**Version**: 1.0.0 | **Ratified**: 2026-08-04 | **Last Amended**: 2026-08-04
