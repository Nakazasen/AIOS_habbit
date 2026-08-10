# AI Routing Resilience

## Boundary

AIOS owns privacy, consent, source/evidence boundaries, answer validation, and
benchmark promotion. The delegated router is a provider-routing dependency only.
It may select an eligible transport route but it cannot authorize egress or make
an answer promotable.

## Three failure scopes

| Scope | Trigger examples | Isolation behavior |
|---|---|---|
| Provider circuit | Timeouts, network errors, 5xx bursts | Marks the provider degraded/open; healthy providers remain eligible; one half-open probe is admitted after expiry. |
| Key cooldown | 429/quota and `Retry-After` | Cools down only the affected masked key; other keys remain eligible. Auth failures disable only that key. |
| Model lockout | Retired/unsupported model or repeatedly invalid provider output | Locks only `(provider, masked key, model)`; approved model substitution or another model/key/provider can continue. |

The state contains no raw API key, prompt, evidence/source content, raw external
exception, or source ID. Persisted JSON uses only masked IDs, safe error classes,
timestamps and reliability aggregates.

## Route selection

After AIOS policy eligibility, production orders routes deterministically by:

1. Circuit/key/model availability.
2. Valid last-known-good session affinity (opaque, scoped to task/language/privacy
   label, and short-lived).
3. VI/JA/EN language fit.
4. Observed success reliability and latency EWMA.
5. Explicit configuration priority and provider ID tie-breakers.

The authoritative blind benchmark intentionally retains a configured ordered
provider pool for repeatability. It still receives provider/key/model recovery,
redacted attempt telemetry and persisted router state.

## Outcome integrity

`success`, `retry_later`, `infrastructure_invalid`, `policy_blocked`, and
`local_renderer` are distinct internal states.

- Citation-invalid synthesis may take the existing validated local renderer path;
  it is labelled `provider_validation_fallback`, not a provider-wide outage.
- Any unavailable/exhausted benchmark synthesis pool is
  `INFRASTRUCTURE_INVALID`. The run is non-promotable and must not be scored as a
  RAG quality loss.
- Live phase closure still needs the 12/12 benchmark to complete validly, with no
  infrastructure-invalid row, the language-route checks, and the existing
  independent NotebookLM comparison gates.

## Verification matrix

Use injected/fake clients and clocks before live credentials:

- Provider 5xx → circuit opens, alternative provider succeeds.
- Expired circuit → exactly one half-open probe; success closes it.
- Key 429 with `Retry-After` → only that key sleeps for upstream duration.
- Auth failure → only that key is disabled.
- Model unavailable → configured substitute or an alternative remains eligible.
- Provider output fails validation → model-only signal/local validated renderer.
- VI, JA, EN, and mixed query classification remains query-only and plan carries
  the canonical language field.
- All routes unavailable → benchmark infra-invalid/non-promotable.
