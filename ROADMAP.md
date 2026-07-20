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
| Documentation cleanup | `ACTIVE` |
| Studio/public legacy route retirement | `ACTIVE` |
| Case Cockpit monolith retirement | `PLANNED`; dependency slice bắt buộc trước delete |
| Next RAG implementation gate | `PLANNED`: `RAG-V2-HYBRID-RETRIEVAL-MIN` |
| A17A–A17D | `DONE` (historical evidence/changelog) |
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
  no-code-change. Documentation sync is `DOCS_VALIDATED / PENDING_COMMIT`.

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

## Active Gate Cards

1. [DOCS-LEGACY-CLEANUP-RESET](docs/roadmap/active/DOCS-LEGACY-CLEANUP-RESET.md)
2. [STUDIO-AND-PUBLIC-LEGACY-ROUTE-RETIREMENT](docs/roadmap/active/STUDIO-AND-PUBLIC-LEGACY-ROUTE-RETIREMENT.md)

## Planned near-term Gate Cards

1. [RAG-V2-HYBRID-RETRIEVAL-MIN](docs/roadmap/backlog/RAG-V2-HYBRID-RETRIEVAL-MIN.md)
2. [RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN](docs/roadmap/backlog/RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN.md)
3. [RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE](docs/roadmap/backlog/RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE.md)
4. [NOTEBOOKLM-BATTLE-RERUN-RAG-V2](docs/roadmap/backlog/NOTEBOOKLM-BATTLE-RERUN-RAG-V2.md)
5. [CASE-COCKPIT-DEPENDENCY-MIGRATION-AND-RETIREMENT](docs/roadmap/backlog/CASE-COCKPIT-DEPENDENCY-MIGRATION-AND-RETIREMENT.md)

## Verification policy

A Gate Card can become `DONE` only after its allowlisted changes and current
validation evidence are recorded. At minimum run:

```powershell
py -3 -m compileall src tests
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
git diff --check
git diff --cached --check
```

See [docs/roadmap/README.md](docs/roadmap/README.md) for Gate Card convention.
