# Security Policy

Status: `PROPOSED`
Owner role: Project owner / designated security contact
Last reviewed: 2026-07-25
Review cadence: Each release candidate and after a security-relevant change

## Scope

AIOS WorkLens is a local-first application. Security scope includes the tracked
source code, release artifacts, dependency configuration, local data boundaries
and optional external AI-provider integration. Private local documents, runtime
JSONL/SQLite files and credentials must never be attached to public reports.

## Supported versions

| Version line | Status |
|---|---|
| Current `main` / next release candidate | Supported for security fixes |
| Historical releases | `OWNER_DECISION_REQUIRED` |

A formal supported-version window will be defined in
[docs/release/SUPPORTED_VERSIONS.md](docs/release/SUPPORTED_VERSIONS.md).

## Reporting a vulnerability

**OWNER_DECISION_REQUIRED:** configure a private reporting channel before any
public release. Until that decision exists, do not open a public issue containing
exploit steps, API keys, local paths, private documents or sensitive logs.

A safe report contains: affected version/commit, minimal synthetic reproduction,
impact, attack preconditions and suggested remediation. It must not contain a
live credential or customer/owner data.

## Triage and disclosure

The proposed lifecycle is acknowledge → reproduce with synthetic data → contain
→ fix and test → publish a sanitized advisory/release note. Response targets and
embargo/disclosure windows remain `OWNER_DECISION_REQUIRED`; this document does
not promise an SLA.

## Security design references

- [Threat model](docs/security/THREAT_MODEL.md)
- [Privacy impact assessment](docs/security/PRIVACY_IMPACT_ASSESSMENT.md)
- [Dependency policy](docs/security/DEPENDENCY_POLICY.md)
- [Incident response](docs/operations/INCIDENT_RESPONSE.md)
