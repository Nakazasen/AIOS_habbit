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
| `unknown` / `machine_only` source text | Local by default | Optional provider | Gateway requires consent bound to full source set, destination and purpose; sensitive outbound text remains redacted | Owner-managed; consent is request authorization, not retention policy |
| `cloud_safe` / `public` source text | Local or optional provider | Configured provider | Gateway approval + normal explicit request flow | Provider terms/retention are external and must be reviewed by owner |
| API keys | Process environment for router integration | Provider authentication only | Explicit live route | Not stored by application contract; do not commit |
| Logs/diagnostics | Local/operator controlled | None by default | Sanitized collection only | No formal automatic retention policy |

## Route-specific policy coverage

`BrainGateway.preflight_check()` implements the verified policy for both the
router-enabled mock path and the real Workspace Chat provider path:

1. router disabled or no sources → deny;
2. `local_only` / `confidential` → hard deny external route;
3. `unknown` / `machine_only` → deny until valid `OwnerConsent` matches the full
   source-set hash, destination and purpose;
4. retrieved outbound evidence must match a source in the full enabled snapshot;
5. approved payloads are sanitized; sensitive source titles/text are redacted and
   metadata is allow-listed/opaque.

The real route uses destination `workspace_chat_external_router` and passes only
`SanitizedRouterPayload` to the router adapter. The adapter builds provider
messages itself, never from caller-provided raw prompts. The owner-facing
external-sharing selection writes `cloud_safe`; existing `machine_only` and
`cloud_allowed` records stay non-sendable until an owner explicitly reclassifies
them. The Nakazasen Router remains a provider-routing dependency and is never a
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
