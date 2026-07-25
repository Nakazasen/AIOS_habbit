# Maintainer Onboarding

Status: `ACTIVE`
Owner role: Project owner / maintainer
Last reviewed: 2026-07-25
Review cadence: Before handover and each release candidate

## First 30 minutes

1. Read `README.md`, `CONSTITUTION.md`, `ROADMAP.md` and `PROJECT_HANDOVER.md`.
2. Read [professionalization index](../PROFESSIONALIZATION_INDEX.md) and note
   all `OWNER_DECISION_REQUIRED` items.
3. Install locally with `py -3 -m pip install -e .`.
4. Run the required [quality gates](../quality/QUALITY_GATES.md).
5. Confirm Git status contains no staged private/runtime material.

## First working task

1. Find or open a Gate Card; do not infer that a planned item is active.
2. Read relevant ADR, requirements, contracts, threat/privacy records and tests.
3. Keep source/runtime data local; use synthetic fixtures.
4. Make the smallest scoped change with focused regression coverage.
5. Update roadmap/handover/changelog only with current validation evidence.

## Before release or handover

- Follow [release checklist](../release/RELEASE_CHECKLIST.md).
- Review [risk register](../governance/RISK_REGISTER.md).
- Review backup/restore and incident procedures; do not claim they were drilled
  unless a synthetic drill record exists.
- Obtain owner decisions for security reporting, distribution, support matrix,
  retention and dependency advisory enforcement.

## Escalate instead of guessing

Ask the project owner before enabling a provider for normal use, changing privacy
labels/consent semantics, migrating local data, publishing artifacts, altering
Git-ignore rules for private data or deleting legacy shared services.
