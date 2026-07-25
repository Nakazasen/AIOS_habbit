# Risk Register

Status: `ACTIVE`
Owner role: Project owner / risk reviewer
Last reviewed: 2026-07-25
Review cadence: Every release candidate, incident and material architecture change

| ID | Risk | Likelihood | Impact | Owner role | Mitigation | Trigger | Residual status |
|---|---|---:|---:|---|---|---|---|
| RSK-01 | Private data/paths reach provider or public channel | Medium | High | Privacy reviewer | Gateway default deny, consent/sanitization tests, safe diagnostics | Unexpected route/log/audit finding | Open |
| RSK-02 | Prompt injection or malicious document influences answer flow | Medium | High | Security reviewer | Local-first, evidence discipline, threat-model review | New parser/synthesis route | Open |
| RSK-03 | Credential leak or unauthorized provider use | Low-Medium | High | Security/release reviewer | Ignore/audit, temporary env live test, revocation procedure | Secret scan, public exposure | Open |
| RSK-04 | Local JSONL/index corruption or owner data loss | Medium | High | Data owner | Backup/restore procedure and drill | Parse/index failure | Open |
| RSK-05 | Provider outage/quota/model behavior breaks optional answer route | Medium | Medium | Integration reviewer | Safe failure messages, local-only fallback | Router/provider error | Accepted operational risk |
| RSK-06 | Dependency compromise/drift | Medium | High | Release/security reviewer | Pinning, review, SBOM/advisory policy | Update advisory or unexpected install | Open |
| RSK-07 | Weak bilingual retrieval or unsupported OCR misleads owner | High | Medium | RAG reviewer | Limitations documented, evidence/insufficiency behavior | Evaluation miss | Open planned RAG work |
| RSK-08 | Single-maintainer knowledge loss | Medium | High | Project owner | Handover, ADRs, runbooks, ownership decision | Owner unavailable | Open |
| RSK-09 | Docs diverge from code | Medium | Medium | Maintainer | Docs contract check, release review | Broken link/stale claim | Controlled |
| RSK-10 | Real Workspace Chat provider route diverges from Gateway sanitizer/preflight policy | Medium | High | Architecture + privacy reviewer | Dedicated P0 consolidation gate, route-specific regression tests and threat-model review | Provider-route or consent/sanitization change | Open |

## Review rule

Each open risk needs a next review date/decision in the release or Gate Card
evidence. A mitigation reduces risk; it does not make a risk disappear without
validation.
