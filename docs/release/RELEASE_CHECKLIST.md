# Release Checklist

Status: `ACTIVE`
Owner role: Release owner / reviewer
Last reviewed: 2026-07-25
Review cadence: Every intended release or hotfix

## Scope and traceability

- [ ] Gate Card scope, non-goals and rollback are current.
- [ ] Requirements/ADRs/contracts/risks reflect the change.
- [ ] CHANGELOG and PROJECT_HANDOVER state are factual.

## Quality

- [ ] `py -3 scripts/check_docs.py` passes.
- [ ] `py -3 -m compileall src tests` passes.
- [ ] `py -3 -m pytest -q` passes.
- [ ] CLI audit passes with no errors/warnings.
- [ ] Workspace Chat import passes.
- [ ] `git diff --check` and `git diff --cached --check` pass.
- [ ] Focused tests cover changed contracts.

## Privacy and security

- [ ] No credential, private runtime file, raw document, screenshot or local
      diagnostic artifact is staged/tracked.
- [ ] Threat/privacy/dependency impact has been reviewed.
- [ ] If the release enables or advertises a real external-provider route,
      `AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION` is `DONE` with current route-specific
      threat/privacy and regression evidence.
- [ ] Any provider live smoke was explicit, generic, sanitized and recorded
      without a key or private source content.
- [ ] Security disclosure and incident contact decisions are reviewed if release
      is public.

## Delivery and rollback

- [ ] Supported environment has been selected/validated per policy.
- [ ] Clean install/build and SBOM steps are performed if distribution is in
      scope; otherwise release is labelled checkout-only.
- [ ] Prior validated version/commit is named as rollback target.
- [ ] Backup/migration impact is assessed before persistent-data change.
- [ ] Synthetic backup/restore drill is current for changed JSONL/SQLite behavior;
      do not claim RTO/RPO or cross-version recovery without separate evidence.

A checkbox is evidence, not a substitute for command logs/reviewer decision.
