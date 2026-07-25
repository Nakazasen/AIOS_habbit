# Ownership and Review Model

Status: `PROPOSED`
Owner role: Project owner
Last reviewed: 2026-07-25
Review cadence: Each release candidate and when team membership changes

## Role model

This repository does not name individuals or GitHub handles without owner
approval. The roles below describe required accountability.

| Role | Responsibilities |
|---|---|
| Project owner | Product scope, data owner decisions, release approval |
| Maintainer | Code/docs changes, test/audit evidence, stale-doc correction |
| Architecture reviewer | ADRs, interfaces, migration and legacy-boundary review |
| Privacy/security reviewer | Threat model, consent/data route, dependency and incident review |
| Release reviewer | Version, checklist, environment, rollback and SBOM review |
| Operator/data owner | Local backup, restore drill, private-data handling |

## Review triggers

| Change | Required review |
|---|---|
| New provider/data egress | Project + privacy/security |
| Persisted data/schema | Architecture + operator/data owner |
| Dependency or release | Release + security |
| Public UI route | Project + architecture |
| Incident/secret exposure | Project + security |

## CODEOWNERS

`.github/CODEOWNERS` remains a placeholder until the owner supplies valid GitHub
handles or teams. A role document is not a substitute for Git hosting access
control.
