# Traceability Matrix

Status: `ACTIVE`
Owner role: Project owner / quality reviewer
Last reviewed: 2026-07-25
Review cadence: Every Gate Card closure and release candidate

| Requirement | Decision/design | Component | Test/evidence | Runbook/release control |
|---|---|---|---|---|
| PR-01 | ADR-0002, architecture containers | `workspace_chat_app` | Workspace Chat import gate | Install/user guide |
| PR-03/04 | ADR-0004, cloud preflight sequence | `brain_gateway` | Gateway/router mock tests | Privacy assessment/incident response |
| PR-06 | ADR-0005, router call sequence | `workspace_chat_router_adapter` | Workspace router tests/live smoke evidence | Dependency/release policy |
| PR-07 | ADR-0001, deployment view | local stores/retrieval | Full test/audit | Backup/restore/operator guide |
| PR-08 | ADR-0002 | launchers/package routes | Legacy boundary tests | Retirement manifest |
| NFR-02 | ADR-0006, threat model | `.gitignore`, audit | CLI audit/secret fixture tests | Incident response |
| NFR-04 | ADR-0001/0003 | local JSONL/SQLite | 2026-07-25 synthetic restore drill: six JSONL entity types + one SQLite count/search | Backup/restore |
| NFR-09 | Documentation governance | docs checker/CI | `test_documentation_contract.py` | Release checklist |

## Maintenance rule

A missing link in this matrix is a documentation/quality gap, not proof that a
requirement is satisfied. Planned controls retain their status until evidence is
recorded.
