# Non-functional Requirements Baseline

Status: `PARTIAL`
Owner role: Project owner / architecture and release reviewer
Last reviewed: 2026-07-25
Review cadence: Before release or a material runtime boundary change

| ID | Category | Requirement | Status | Evidence / gap |
|---|---|---|---|---|
| NFR-01 | Privacy | Local-first by default; external data route needs policy eligibility. | `PARTIAL` | Gateway policy is implemented for preflight/mock path; real provider route has separate label/consent guard and needs P0 convergence/sanitization evidence. |
| NFR-02 | Security | Credentials/private runtime data must not be tracked or exposed by normal diagnostics. | `PARTIAL` | Ignore/audit controls; heuristic scan limits remain |
| NFR-03 | Reliability | Local provider outage does not prevent local-only usage. | `PARTIAL` | Safe adapter failures; no availability target |
| NFR-04 | Recovery | Operator can back up/restore supported local state with validation. | `PARTIAL` | 2026-07-25 synthetic restore drill passed for six JSONL categories and one SQLite index/search; RTO/RPO, real-data and cross-version recovery remain unproven. |
| NFR-05 | Performance | Retrieval and ingest performance is measured before an external release claim. | `PLANNED` | Benchmark protocol only; no current thresholds |
| NFR-06 | Compatibility | Support matrix is explicit and validated before release. | `PROPOSED` | Windows/Python matrix pending owner approval |
| NFR-07 | Accessibility | Supported UI has documented keyboard/focus/error-state acceptance. | `PROPOSED` | Checklist established; manual review needed |
| NFR-08 | Observability | Diagnostics are privacy-safe and do not require telemetry. | `PROPOSED` | Local procedure/log catalog needed |
| NFR-09 | Maintainability | Material decisions, interfaces and release evidence are traceable. | `ACTIVE` | ADRs/contracts/quality gates |

## Measurement rule

Unmeasured latency, capacity, RTO/RPO and availability values remain `TBD`.
They must not be represented as production commitments.

## Related records

- [Performance capacity baseline](../operations/PERFORMANCE_CAPACITY_BASELINE.md)
- [Supported versions](../release/SUPPORTED_VERSIONS.md)
- [Accessibility acceptance](../quality/UX_ACCESSIBILITY_ACCEPTANCE.md)
