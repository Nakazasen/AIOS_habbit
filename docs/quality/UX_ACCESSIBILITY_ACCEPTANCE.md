# UX and Accessibility Acceptance

Status: `PROPOSED`
Owner role: Project owner / UI reviewer
Last reviewed: 2026-07-25
Review cadence: Before supported UI release or material interaction change

## Scope

This checklist applies to the supported Vietnamese-first Workspace Chat flow. It
is an acceptance baseline, not a claim of completed accessibility certification.

## Required acceptance checks

| Area | Check | Current evidence/status |
|---|---|---|
| Language | User-facing primary flow is Vietnamese-first; technical constants are explained nearby. | `PARTIAL` — policy and UI labels exist; manual review required |
| Keyboard | Owner can reach primary actions, dialogs and destructive confirmations without pointer-only interaction. | `PLANNED` manual check |
| Focus | Focus moves predictably after create/select/archive/delete and error state. | `PLANNED` manual check |
| Labels | Inputs/buttons have meaningful labels rather than icon-only meaning. | `PLANNED` manual check |
| Contrast | Text, error, warning and selected-state contrast is reviewed in supported theme. | `PLANNED` manual check |
| Error state | Errors are Vietnamese-safe; no raw traceback/secret/path reaches user UI. | `PARTIAL` — architecture/tests cover safe errors; manual UI check required |
| Empty/loading/offline | Owner understands no-source, insufficient-evidence, extraction failure and optional-provider failure states. | `PARTIAL` — copy exists; workflow review required |
| Long content | Source list and long answer remain understandable without hiding citation context. | `PLANNED` manual check |
| Consent clarity | Privacy label/consent effect is explained before external route. | `PARTIAL` — policy boundary documented; UI review required |

## Manual review protocol

Use synthetic safe content only. Record browser/Streamlit version, scenario,
pass/fail, issue ID and sanitized screenshot only if the owner explicitly permits
it outside Git. Do not use private notebooks, keys or provider calls.

## Exit rule

A user-facing release cannot claim accessibility conformance until the relevant
checks are performed, issues are triaged and an owner review is recorded.
