# AIOS WorkLens Roadmap

`ROADMAP.md` là **nguồn trạng thái canonical duy nhất** cho công việc hiện tại.
Historical design/audit evidence nằm trong `docs/archive/`; không đọc nó như
hướng dẫn vận hành hoặc status runtime.

## Product direction

AIOS WorkLens là local-first work intelligence. Luồng owner:

```text
Mở Workspace Chat → thêm/chọn nguồn → hỏi tự nhiên → kiểm tra nguồn/citation
```

Workspace Chat là primary UI. Case Cockpit/Habit Studio không còn là user route
được hỗ trợ; xem [RETIREMENT_MANIFEST.md](docs/legacy/RETIREMENT_MANIFEST.md).

Future long-term vision reference: [Production Intelligence Vision](docs/design/PRODUCTION_INTELLIGENCE_VISION.md) (`PLANNED`; design reference only, does not open a delivery gate).


## Current position

| Field | Status |
|---|---|
| Current phase | Phase 4 — Workspace Chat Foundation & AI Gateway Preparation |
| Primary UI | Workspace Chat |
| Documentation cleanup | `DONE` — implementation `9123caa`, current validation passed |
| Studio/public legacy route retirement | `DONE` — implementation `9123caa`, current validation passed |
| Nakazasen AI Router | `v0.5.1`; offline and live Workspace Chat integration verified with bounded stale-model recovery |
| Professionalization baseline | `DONE` — docs/CI/recovery evidence validated; P0 real-route policy consolidation is complete |
| Case Cockpit monolith retirement | `PLANNED`; dependency audit required before deletion |
| Current P0 implementation gate | `DONE`: `AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION` |
| RAG v2 hybrid retrieval | `DONE`: `RAG-V2-HYBRID-RETRIEVAL-MIN` — 18 focused, 907 full tests |
| RAG v2 evidence synthesis | `DONE`: `RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN` — 15 focused, 921 full tests |
| RAG v2 eval harness | `DONE`: `RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE` — 11 focused, 931 full tests |
| RAG v2 capability benchmark | `DONE`: `NOTEBOOKLM-BATTLE-RERUN-RAG-V2` — 11 blind-scored shared rows; RAG v2 2.898/5 vs NotebookLM 3.807/5 |
| RAG v2 Dev quality convergence | `DONE`: `RAG-V2-DEV-QUALITY-CONVERGENCE` — `DEV_READY_WITH_LIMITATIONS` |
| Gate H hybrid canary | `DONE`: `RAG-V2-GATE-H-HYBRID-CANARY` — `ADVANCE_TO_CANARY_WITH_LIMITATIONS`; 87 focused, 1094 full tests |
| RAG v2 corpus OCR & source recovery | `DONE`: 70/70 usable, strict local-only audit PASS, 49 focused and 1108 full tests |
| A17A–A17D | `DONE`; A17D revalidated live with router `v0.5.1` |
| A18 | `PLANNED` / not opened |
| P1.0 | `LOCKED` |

## Completed foundations

- `RAG-V2-ELEMENT-SCHEMA-AND-ADAPTER-INTERFACE` — `DONE`
  ([commit `7db254a`](CHANGELOG.md)).
- `RAG-V2-DOC-CONVERTER-ADAPTERS-MIN` — `DONE`
  ([commit `e2e3942`](CHANGELOG.md)).
- `RAG-V2-STRUCTURE-AWARE-CHUNKING-AND-LOCAL-INDEX-MIN` — `DONE`
  ([commit `c75c319`](CHANGELOG.md)).
- `RM-SYNC-RAG-V2-STRUCTURE-AWARE-CHUNKING-AND-LOCAL-INDEX-MIN` — `DONE`
  ([commit `30e722e`](CHANGELOG.md)).
- `COMPANY-68-RAG-V2-LOCAL-SMOKE-READONLY` — `RECORDED`, local-only,
  no-code-change. Documentation was committed in `9123caa`.

## Known limitations and hard locks

- Gate H selected `bge_m3_hybrid` for controlled activation, but NotebookLM
  generated-answer parity remains unproven.
- The 70-source production corpus now has 100% usable/disposition coverage through
  native extraction or bounded local OCR; continued OCR quality monitoring remains required.
- The normal user must not see a hybrid/lexical/legacy mode selector. Workspace
  Chat should use the best ready retriever automatically and must not silently
  disguise a material quality downgrade.
- RAG v2 core must stay generic/local-first/element-first/privacy-first.
  No MOM/WMS/customer/domain hard-code in core.
- No cloud-default behavior, dependency change, A18 or P1.0 opening through the
  remaining production-activation gate.
- `local_cases/`, `local_runs/`, private sources and credentials remain Git
  ignored and outside cleanup source deletion.

## Active Gate Card

1. [RAG-V2-SAME-PROTOCOL-BLINDED-ANSWER-QUALITY](docs/roadmap/active/RAG-V2-SAME-PROTOCOL-BLINDED-ANSWER-QUALITY.md) — `ACTIVE`; provider-free Stage A is open. Any live Stage B remains blocked until an explicitly approved `cloud_safe`/`public` route exists.

## Recently completed Gate Cards

1. [RAG-V2-HYBRID-PRODUCTION-ACTIVATION](docs/roadmap/completed/RAG-V2-HYBRID-PRODUCTION-ACTIVATION.md)
2. [RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY](docs/roadmap/completed/RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY.md)
3. [RAG-V2-GATE-H-HYBRID-CANARY](docs/roadmap/completed/RAG-V2-GATE-H-HYBRID-CANARY.md)
4. [RAG-V2-DEV-QUALITY-CONVERGENCE](docs/roadmap/completed/RAG-V2-DEV-QUALITY-CONVERGENCE.md)
5. [NOTEBOOKLM-BATTLE-RERUN-RAG-V2](docs/roadmap/completed/NOTEBOOKLM-BATTLE-RERUN-RAG-V2.md)
6. [RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE](docs/roadmap/completed/RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE.md)
7. [RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN](docs/roadmap/completed/RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN.md)
8. [RAG-V2-HYBRID-RETRIEVAL-MIN](docs/roadmap/completed/RAG-V2-HYBRID-RETRIEVAL-MIN.md)
9. [AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION](docs/roadmap/completed/AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION.md)
10. [PROFESSIONALIZATION-BASELINE](docs/roadmap/completed/PROFESSIONALIZATION-BASELINE.md)
11. [DOCS-LEGACY-CLEANUP-RESET](docs/roadmap/completed/DOCS-LEGACY-CLEANUP-RESET.md)
12. [STUDIO-AND-PUBLIC-LEGACY-ROUTE-RETIREMENT](docs/roadmap/completed/STUDIO-AND-PUBLIC-LEGACY-ROUTE-RETIREMENT.md)

## Planned near-term Gate Cards

1. [CASE-COCKPIT-DEPENDENCY-MIGRATION-AND-RETIREMENT](docs/roadmap/backlog/CASE-COCKPIT-DEPENDENCY-MIGRATION-AND-RETIREMENT.md) — `PLANNED`, not opened by the active quality gate.



## Verification policy

A Gate Card can become `DONE` only after its allowlisted changes and current
validation evidence are recorded. At minimum run:

```powershell
py -3 scripts/check_docs.py
py -3 -m compileall src tests
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
git diff --check
git diff --cached --check
```

See [docs/roadmap/README.md](docs/roadmap/README.md) for Gate Card convention.
