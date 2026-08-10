# Sequence: Workspace Chat External Preflight

Status: `ACTIVE`
Owner role: Project owner / privacy reviewer
Last reviewed: 2026-07-25
Review cadence: Before changing labels, consent or external destinations

```mermaid
sequenceDiagram
    participant UI as Workspace Chat
    participant G as BrainGateway
    participant O as Owner consent
    participant A as Router adapter
    participant P as Optional provider
    UI->>G: BrainRequest(full sources, retrieved evidence, destination, purpose)
    G->>G: Verify full source set and strictest privacy label
    alt local_only or confidential
        G-->>UI: Deny: use local-only path
    else unknown or machine_only
        G->>O: Validate source-set/destination/purpose consent
        alt invalid or missing consent
            G-->>UI: Deny: request classification or consent
        else valid
            G->>G: Authorize evidence against full source set
            G->>G: Sanitize payload
            G-->>A: SanitizedRouterPayload
        end
    else cloud_safe or public
        G->>G: Authorize evidence and sanitize payload
        G-->>A: SanitizedRouterPayload
    end
    A->>A: Build provider messages from sanitized payload only
    A->>P: Optional provider request
    P-->>A: Result or safe failure
    A-->>UI: Vietnamese-safe response
```

This sequence documents the implemented optional route; it does not enable any
provider by default. The route remains blocked when router configuration is
unavailable, policy denies, or retrieval yields no eligible evidence.

## Related records

- [ADR-0004](../../adr/0004-brain-gateway-privacy-ownership.md)
- [Privacy impact assessment](../../security/PRIVACY_IMPACT_ASSESSMENT.md)
