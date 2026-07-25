# Sequence: Optional Cloud Preflight

Status: `ACTIVE`
Owner role: Project owner / privacy reviewer
Last reviewed: 2026-07-25
Review cadence: Before changing labels, consent or external destinations

```mermaid
sequenceDiagram
    participant UI as Caller
    participant G as BrainGateway
    participant O as Owner consent
    participant A as Router adapter
    UI->>G: BrainRequest(question, sources, destination, purpose)
    G->>G: Determine strictest privacy label
    alt local_only or confidential
        G-->>UI: Deny: local-only response path
    else unknown or machine_only
        G->>O: Validate source-set/destination/purpose consent
        alt invalid or missing consent
            G-->>UI: Deny: request classification/consent
        else valid
            G->>G: Sanitize payload
            G-->>A: Allowed sanitized payload
        end
    else cloud_safe or public
        G->>G: Sanitize payload
        G-->>A: Allowed sanitized payload
    end
```

This sequence documents the policy contract; it does not enable providers by
default. The route must remain blocked if router configuration is disabled.

## Related records

- [ADR-0004](../../adr/0004-brain-gateway-privacy-ownership.md)
- [Privacy impact assessment](../../security/PRIVACY_IMPACT_ASSESSMENT.md)
