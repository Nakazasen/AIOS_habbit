# Definition of Ready and Done

Status: `ACTIVE`
Owner role: Project owner / maintainer
Last reviewed: 2026-07-25
Review cadence: Every Gate Card opening and closure

## Ready

Work is ready when it has a goal, non-goals, owner role, privacy classification,
architecture/repository impact, acceptance criteria, verification commands,
rollback concept and explicit dependencies/decisions. A known but unopened item
stays `PLANNED`.

## Done

Work is done only when:

1. scope allowlist is satisfied without unrelated cleanup;
2. source/tests/docs are consistent and current;
3. full quality gates pass with recorded evidence;
4. privacy/security and private-data safety are reviewed;
5. rollback and residual risk are explicit;
6. roadmap, handover and changelog are updated;
7. required reviewer/owner decision is recorded.

A test count, generated document or apparently working UI alone is not `DONE`.
