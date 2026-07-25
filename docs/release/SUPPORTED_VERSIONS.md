# Supported Versions and Environments

Status: `PROPOSED`
Owner role: Release owner / project owner
Last reviewed: 2026-07-25
Review cadence: Each release candidate or Python/dependency update

## Proposed baseline

| Area | Proposed status | Evidence needed before approval |
|---|---|---|
| Windows 10/11 | Candidate supported local environment | Clean install + full quality gates |
| Python 3.11 | CI baseline | Current GitHub Actions workflow |
| Python 3.12 | Candidate | Clean install + full quality gates |
| Python 3.13 | Candidate | Local validated environment evidence |
| macOS/Linux | Not committed | Owner decision and validation matrix |
| Package registry/installers | Not committed | Distribution ADR/release process |

## Support policy

Only environments explicitly promoted to `APPROVED` after validation are support
commitments. Current source declares `requires-python >=3.11`; that is a
compatibility floor, not proof that every later Python/platform combination is
supported.

## Security support window

The maintenance/security window for released versions is
`OWNER_DECISION_REQUIRED`. Until then, the current main/release candidate is the
only version line expected to receive fixes.
