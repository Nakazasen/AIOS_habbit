# Documentation Governance

Status: `ACTIVE`
Owner role: Project owner
Last reviewed: 2026-07-25
Review cadence: Each release candidate and every material architecture change

## Purpose

Keep documentation useful, traceable and non-contradictory. Documentation is a
product artifact: a control is not considered documented merely because a file
exists.

## Canonical sources

| Topic | Canonical source |
|---|---|
| Current delivery state | `ROADMAP.md` |
| Current handover and residual risk | `PROJECT_HANDOVER.md` |
| Historical change evidence | `CHANGELOG.md` |
| Product principles | `CONSTITUTION.md` |
| Logical data/memory architecture | `ARCHITECTURE.md` |
| Runtime and trust-boundary views | `docs/architecture/` |
| Security and privacy posture | `SECURITY.md`, `docs/security/` |
| Quality and verification | `docs/quality/` |
| Operational procedures | `docs/operations/` |
| Release and dependency control | `docs/release/` |

Historical evidence in `docs/archive/` is not an operational source of truth.

## Required metadata

Professional-control documents must expose: `Status`, `Owner role`, `Last
reviewed`, and `Review cadence` near the title. A document may state
`OWNER_DECISION_REQUIRED`; that status is honest and does not imply approval.

## Status vocabulary

- `ACTIVE`: maintained current policy or reference.
- `PROPOSED`: drafted control requiring owner approval.
- `PARTIAL`: some implementation exists; limitations are named.
- `PLANNED`: known work that is not implemented.
- `RETIRED`: historical only; replacement is linked.

## Change and review rules

1. Update canonical docs in the same change as a material behavior change.
2. Link claims to source, tests, Gate Card or runbook evidence where practical.
3. Do not include secrets, private document contents, screenshots, local paths or
   runtime records in tracked documentation.
4. Keep links relative inside the repository so clone/branch navigation works.
5. Use `docs/PROFESSIONALIZATION_INDEX.md` as the navigation map; do not create
   competing indexes.
6. Run `py -3 scripts/check_docs.py` before marking a documentation gate done.

## Stale-document handling

When a claim becomes obsolete: update the canonical source, leave historical
records intact, add a replacement link, and archive long historical material
rather than rewriting history. A broken or ambiguous control is logged as a risk
until corrected.
