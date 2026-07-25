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

## Current position

| Field | Status |
|---|---|
| Current phase | Phase 4 — Workspace Chat Foundation & AI Gateway Preparation |
| Primary UI | Workspace Chat |
| Documentation cleanup | `DONE` — implementation `9123caa`, current validation passed |
| Studio/public legacy route retirement | `DONE` — implementation `9123caa`, current validation passed |
| Nakazasen AI Router | `v0.4.0`; offline and live Workspace Chat integration verified |
| Professionalization baseline | `DONE` — docs/CI/recovery evidence validated; runtime policy-consolidation remains planned |
| Case Cockpit monolith retirement | `PLANNED`; dependency audit required before deletion |
| Next priority before external-provider release claim | `PLANNED`: `AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION` |
| Next RAG implementation gate | `PLANNED`: `RAG-V2-HYBRID-RETRIEVAL-MIN` |
| A17A–A17D | `DONE`; A17D revalidated live with router `v0.4.0` |
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

- Current local index is deterministic lexical retrieval, not semantic/vector
  retrieval. Vietnamese/Japanese bilingual ranking is weak in the recorded
  Company-68 smoke; PNG OCR is not supported.
- RAG v2 core must stay generic/local-first/element-first/privacy-first.
  No MOM/WMS/customer/domain hard-code in core.
- No new normal-user technical panel, cloud-default behavior, dependency change,
  A18 or P1.0 opening through the next retrieval gate.
- `local_cases/`, `local_runs/`, private sources and credentials remain Git
  ignored and outside cleanup source deletion.

## Active Gate Card

No implementation Gate Card is currently `ACTIVE`. The P0 provider-policy
consolidation and RAG cards remain `PLANNED` until explicitly opened.

## Recently completed Gate Cards

1. [PROFESSIONALIZATION-BASELINE](docs/roadmap/completed/PROFESSIONALIZATION-BASELINE.md)
2. [DOCS-LEGACY-CLEANUP-RESET](docs/roadmap/completed/DOCS-LEGACY-CLEANUP-RESET.md)
3. [STUDIO-AND-PUBLIC-LEGACY-ROUTE-RETIREMENT](docs/roadmap/completed/STUDIO-AND-PUBLIC-LEGACY-ROUTE-RETIREMENT.md)

## Planned near-term Gate Cards

1. [AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION](docs/roadmap/backlog/AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION.md)
   — P0 before an external-provider release.
2. [RAG-V2-HYBRID-RETRIEVAL-MIN](docs/roadmap/backlog/RAG-V2-HYBRID-RETRIEVAL-MIN.md)
3. [RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN](docs/roadmap/backlog/RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN.md)
4. [RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE](docs/roadmap/backlog/RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE.md)
5. [NOTEBOOKLM-BATTLE-RERUN-RAG-V2](docs/roadmap/backlog/NOTEBOOKLM-BATTLE-RERUN-RAG-V2.md)
6. [CASE-COCKPIT-DEPENDENCY-MIGRATION-AND-RETIREMENT](docs/roadmap/backlog/CASE-COCKPIT-DEPENDENCY-MIGRATION-AND-RETIREMENT.md)

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
