# Dependency and Supply-Chain Policy

Status: `PROPOSED`
Owner role: Release owner with security reviewer
Last reviewed: 2026-07-25
Review cadence: Each dependency update and release candidate

## Policy

1. Add a dependency only when it supports an approved Gate Card and its license,
   support status, privacy implications and rollback are recorded.
2. Pin Git dependencies to an explicit immutable release tag or commit. The
   current router dependency is pinned to `nakazasen-ai-router@v0.4.0`.
3. Use bounded version ranges only where a clean-install validation and rollback
   path exist. `pyproject.toml` alone is not a lockfile.
4. Never put credentials, private package indexes or owner data in dependency
   metadata, CI logs or SBOM output.
5. Review direct dependencies on upgrade for API compatibility, security notes,
   licenses and changelog impact. Run focused plus full tests.

## Required upgrade evidence

- Source/version/reference changed.
- Reason and risk assessment.
- Focused compatibility tests and full quality gates.
- Clean-install/build check when a distributable release is in scope.
- Rollback target (prior known-good version/commit).
- Changelog and release-note entry.

## SBOM and advisory posture

`SBOM_POLICY.md` defines proposed generation and publication rules. Automated
vulnerability scanning is advisory until the owner sets a tool, severity
threshold, exception process and merge-blocking policy. Advisory findings are
recorded in the risk register; they are not silently ignored.

## License and provenance

Before external distribution, create a third-party license inventory from the
resolved environment or generated SBOM and review license compatibility with the
repository `LICENSE`. This repository does not yet claim a signed-provenance or
reproducible-lockfile control.

## Rollback

Revert the dependency declaration to the last validated version, reinstall in a
clean environment, rerun the quality gates, and record the cause in the
changelog/risk register. Never use a provider credential to diagnose a package
installation issue.
