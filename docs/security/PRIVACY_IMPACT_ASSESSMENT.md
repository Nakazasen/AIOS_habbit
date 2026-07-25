# Privacy Impact Assessment

Status: `PARTIAL`
Owner role: Project owner / privacy decision maker
Last reviewed: 2026-07-25
Review cadence: Before any new external recipient, data class or cloud route

## Purpose and limits

This is an engineering privacy assessment, not legal advice or a compliance
certification. It documents current behavior and owner decisions still required.

## Processing inventory

| Data class | Local handling | External recipient | Condition | Retention reality |
|---|---|---|---|---|
| Workspace Chat notebooks, messages and sources | JSONL under ignored `local_cases/workspace_chat/` | None by default | Local use | Owner-managed filesystem data; no automatic retention/deletion engine proven |
| RAG v2 chunks/index | Local SQLite path chosen by caller | None by default | Local retrieval | Rebuildable from available source/chunk input where caller preserves it |
| `local_only` / `confidential` source text | Local only | Blocked | Gateway hard deny | Owner-managed |
| `unknown` / `machine_only` source text | Local by default | Optional provider | Real Workspace Chat path requires cloud mode, allowed label and consent snapshot; Gateway mock/preflight path requires consent bound to source set, destination and purpose | Owner-managed; consent is request authorization, not retention policy |
| `cloud_safe` / `public` source text | Local or optional provider | Configured provider | Router enabled + normal request flow | Provider terms/retention are external and must be reviewed by owner |
| API keys | Process environment for router integration | Provider authentication only | Explicit live route | Not stored by application contract; do not commit |
| Logs/diagnostics | Local/operator controlled | None by default | Sanitized collection only | No formal automatic retention policy |

## Route-specific policy coverage

`BrainGateway.preflight_check()` implements the following verified behavior for
its router-enabled preflight/mock path:

1. router disabled or no sources → deny;
2. `local_only` / `confidential` → hard deny external route;
3. `unknown` / `machine_only` → deny until valid `OwnerConsent` matches source
   set hash, destination and purpose;
4. allowed payloads are sanitized; sensitive source titles/text are redacted and
   metadata is allow-listed/opaque.

The current real Workspace Chat router path has a separate verified guard: it
requires cloud mode, blocks non-sendable labels, requires an explicit confirmation
and rejects a changed enabled-source set. It currently constructs the provider
prompt directly after that guard and is **not proven to call the Gateway
sanitizer/preflight**. This is a P0 design-consistency gap, not an assertion that
local-only data is currently sent; it is tracked in
[AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION](../roadmap/backlog/AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION.md).

The gateway remains the intended privacy/consent policy authority. The
Nakazasen Router is a provider-routing dependency and must not be treated as a
consent authority.

## Owner decisions required

| Decision | Status |
|---|---|
| Legal basis and jurisdiction-specific privacy obligations | `OWNER_DECISION_REQUIRED` |
| Named external providers and their terms/subprocessors | `OWNER_DECISION_REQUIRED` |
| Retention duration / deletion schedule | `OWNER_DECISION_REQUIRED` |
| Security disclosure contact and incident communications | `OWNER_DECISION_REQUIRED` |
| Whether external routing is enabled for normal users | `OWNER_DECISION_REQUIRED` |

## Privacy test expectations

- Tests cover hard deny, default deny, source-set-bound consent and sanitization.
- CI uses only synthetic fixtures and has no provider credential.
- Live provider smoke is opt-in and uses a generic prompt without project/source
  context. Evidence records status/model only, never a key or raw request.

## Related controls

- [Data policy](../../00_governance/DATA_POLICY.md)
- [Threat model](THREAT_MODEL.md)
- [Operations and incidents](../operations/INCIDENT_RESPONSE.md)
