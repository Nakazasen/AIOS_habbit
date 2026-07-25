# Professionalization Index

Status: `ACTIVE`
Owner role: Project owner / maintainer
Last reviewed: 2026-07-25
Review cadence: Each Gate Card closure and release candidate

## Purpose

This index is the navigation map for professional engineering records. Current
project delivery state remains canonical in `ROADMAP.md`; this file does not
replace it.

| Domain | Canonical record | Status focus |
|---|---|---|
| Documentation control | [Documentation governance](DOCUMENTATION_GOVERNANCE.md) | Canonical source and review rules |
| Security | [Security policy](../SECURITY.md), [threat model](security/THREAT_MODEL.md) | Reporting channel and residual risks need owner review |
| Privacy/data | [Privacy impact assessment](security/PRIVACY_IMPACT_ASSESSMENT.md), [data policy](../00_governance/DATA_POLICY.md) | Legal basis/retention/provider decisions pending |
| Dependencies | [Dependency policy](security/DEPENDENCY_POLICY.md), [SBOM policy](release/SBOM_POLICY.md) | Advisory enforcement pending |
| Architecture | [Context](architecture/CONTEXT.md), [containers](architecture/CONTAINERS.md), [components](architecture/COMPONENTS.md), [deployment](architecture/DEPLOYMENT.md) | Runtime/container views current |
| Decisions | [ADR index](adr/README.md) | New material decisions require ADR |
| Requirements | [Product](requirements/PRODUCT_REQUIREMENTS.md), [NFR](requirements/NON_FUNCTIONAL_REQUIREMENTS.md), [traceability](requirements/TRACEABILITY_MATRIX.md) | Targets marked TBD remain unapproved |
| Interfaces/data | [Runtime interfaces](contracts/RUNTIME_INTERFACES.md), [persisted compatibility](contracts/PERSISTED_DATA_COMPATIBILITY.md) | Formal migration framework not implemented |
| Quality | [Test strategy](quality/TEST_STRATEGY.md), [quality gates](quality/QUALITY_GATES.md), [UX/accessibility](quality/UX_ACCESSIBILITY_ACCEPTANCE.md) | Accessibility manual review pending |
| Operations | [Backup/restore](operations/BACKUP_RESTORE.md), [incident response](operations/INCIDENT_RESPONSE.md), [troubleshooting](operations/TROUBLESHOOTING.md), [observability](operations/OBSERVABILITY.md) | Synthetic restore drill passed; RTO/RPO remain owner decisions |
| Release | [Release policy](release/RELEASE_POLICY.md), [checklist](release/RELEASE_CHECKLIST.md), [supported versions](release/SUPPORTED_VERSIONS.md) | Distribution/support window pending |
| Governance | [Risk register](governance/RISK_REGISTER.md), [ownership](governance/OWNERSHIP_AND_REVIEW.md), [DoR/DoD](governance/DEFINITION_OF_READY_DONE.md) | Named ownership pending |
| Productization | [User guide](user/WORKSPACE_CHAT_USER_GUIDE.md), [onboarding](onboarding/MAINTAINER_ONBOARDING.md), [migration](operations/DATA_MIGRATION_COMPATIBILITY.md) | Manual reviews and policy decisions pending |

## Required owner decisions

1. Private security reporting channel and disclosure process.
2. Release distribution channel and supported-version window.
3. Retention/deletion policy and recovery objectives.
4. Named reviewers/backup owner and repository CODEOWNERS handles.
5. SBOM/vulnerability advisory tool, threshold and enforcement status.

Until those decisions are recorded, corresponding policies remain `PROPOSED` or
`OWNER_DECISION_REQUIRED`, not release guarantees.
