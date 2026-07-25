# Sequence: Router Call and Safe Failure

Status: `ACTIVE`
Owner role: Project owner / integration reviewer
Last reviewed: 2026-07-25
Review cadence: Each router/provider upgrade or error-contract change

```mermaid
sequenceDiagram
    participant C as Approved caller
    participant A as WorkspaceChatRouterAdapter
    participant R as Nakazasen Router
    participant P as Configured provider
    C->>A: question + system/user prompt
    A->>R: create router from environment
    A->>R: route_outcome(AIRequest)
    R->>P: Optional provider request
    P-->>R: Result or provider error
    R-->>A: Normalized outcome
    alt success
        A-->>C: Answer text
    else failure
        A-->>C: Safe Vietnamese error message
    end
```

Keys are read from process environment at call time. The adapter must not print
keys, raw authorization data or provider request payloads. Provider failure is
mapped to a safe user message.

## Related records

- [ADR-0005](../../adr/0005-router-provider-routing-boundary.md)
- [Incident response](../../operations/INCIDENT_RESPONSE.md)
