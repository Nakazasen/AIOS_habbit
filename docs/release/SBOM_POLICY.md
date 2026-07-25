# SBOM Policy

Status: `PROPOSED`
Owner role: Release owner / security reviewer
Last reviewed: 2026-07-25
Review cadence: Each distributable release and dependency update

## Purpose

A software bill of materials (SBOM) records resolved package names/versions for
an environment or release candidate. It improves supply-chain review; it does
not prove the absence of vulnerabilities or provide signed provenance.

## Current procedure

Use the repository stdlib tool:

```powershell
py -3 scripts/generate_sbom.py --output local_runs/sbom/aios-habit-sbom.json
```

The default output is ignored runtime data. Inspect it before sharing; do not add
private package indexes, credentials, local paths or environment variables.

## Publication and enforcement

SBOM publication, format requirements, vulnerability scanner, severity threshold,
exception process and CI merge-blocking behavior are `OWNER_DECISION_REQUIRED`.
Until approved, SBOM/advisory checks are review evidence rather than a required
remote artifact.

## Retention

Keep release SBOMs according to owner release policy. Do not place them in Git by
default unless the owner explicitly approves a sanitized, reproducible release
artifact workflow.
