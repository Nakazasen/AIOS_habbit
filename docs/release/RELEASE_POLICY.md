# Release Policy

Status: `PROPOSED`
Owner role: Release owner / project owner
Last reviewed: 2026-07-25
Review cadence: Each release candidate and hotfix

## Distribution status

Current verified workflow is local editable installation from a repository
checkout. GitHub releases, package registry publishing, signed artifacts and
automatic installers are `OWNER_DECISION_REQUIRED`; this policy does not claim
they exist.

## Versioning

Use the package version in `pyproject.toml` as release identity. Proposed scheme
is semantic versioning:

- MAJOR: incompatible supported interface/persisted-data change;
- MINOR: backward-compatible feature or supported capability;
- PATCH: backward-compatible fix/documentation/release correction.

Pre-release labels and release branch policy require owner approval.

## Release flow

1. Open/confirm an approved scope and update requirements/ADR/risk records.
2. Update version and release notes when a distributable release is intended.
3. Run [release checklist](RELEASE_CHECKLIST.md) in a clean-environment plan.
4. Review dependency/SBOM and private-data safety.
5. Obtain owner/reviewer sign-off according to governance roles.
6. Publish only through the owner-approved channel.
7. Preserve rollback reference and support evidence.

## External-provider release boundary

A release that enables or presents a real external-provider route must not claim
its privacy enforcement is production-ready unless
[AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION](../roadmap/completed/AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION.md)
is `DONE` with current route-specific tests and threat/privacy review. This does
not remove current hard blocks; it prevents a stronger unsupported release claim.

## Hotfix

A hotfix uses the same security/privacy/quality gates, reduced only by a written
risk decision. It must name the regression, tested fix, rollback target and
follow-up review.

## Rollback

Return to the last validated version/commit, restore compatible local state if
needed, rerun quality gates and document the reason. Do not downgrade/delete
persisted owner data without the compatibility plan.
