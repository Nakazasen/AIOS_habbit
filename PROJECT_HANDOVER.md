# Project Handover

## Mục đích

Tài liệu này là handover vận hành ngắn cho repository AIOS WorkLens. Trạng thái
Git, test và remote phải luôn được kiểm tra lại tại thời điểm nhận việc; không
coi một claim lịch sử là trạng thái runtime hiện tại.

## Trạng thái verified gần nhất

- **Primary UI:** Workspace Chat.
- **RAG v2 foundation:** element schema/adapters, converter adapters,
  structure-aware chunking và local SQLite lexical index đã hoàn thành.
- **Cleanup/legacy routes:** `DONE`. Phần triển khai nằm trong `9123caa`;
  compile, `892` tests và CLI audit đều đạt ngày 2026-07-25.
- **Nakazasen AI Router:** đã nâng lên `v0.5.1`.
  Public imports, focused regressions, live provider smoke và live call qua
  Workspace Chat adapter đều đạt. Router có bounded stale-model recovery: probe
  metadata tối đa một lần và retry một lần với model cùng family đã được duyệt;
  explicit owner model override vẫn được giữ nguyên. Focused provider/router
  regressions: `57 passed`; full repository regression sau integration: `957 passed`.
  Live smoke dùng Gemini và dừng sau lần thành công đầu tiên.
- **Professionalization Baseline:** `DONE`. Bổ sung security/privacy, ADR,
  architecture/runtime views, quality/CI parity, recovery/release/risk và
  onboarding records; không thay đổi runtime, UI hay cloud-default behavior.
  Docs contract, compile, CLI audit (không errors/warnings), Workspace Chat import
  và full suite `896 passed` đã đạt; synthetic JSONL/SQLite restore drill đã PASS.
- **P0 AI Gateway:** `DONE`. Real Workspace Chat provider requests now enter
  `BrainGateway` before the router; consent is bound to the full selected-source
  set, `workspace_chat_external_router` and `workspace_chat_answer`. The router
  receives only a sanitized typed payload. `local_only`/`confidential` stay
  hard-blocked; legacy `machine_only`/`cloud_allowed` records remain non-sendable
  until an owner explicitly reclassifies them to `cloud_safe`. Focused policy
  regressions: `155 passed`; full gate: docs PASS, compile PASS, `903 passed`,
  CLI audit PASS with no errors/warnings, Workspace Chat import PASS (expected
  Streamlit bare-mode warnings only), and Git whitespace checks PASS on
  2026-07-25.
- **Owner decisions còn chờ:** kênh báo security riêng tư, kênh phân phối/release,
  support matrix, retention/RTO-RPO, named reviewer/CODEOWNERS và dependency
  advisory enforcement.
- **Case Cockpit:** public routes đã gỡ; shared services vẫn được giữ lại để
  audit dependency riêng.
- **RAG v2 hybrid retrieval:** `DONE`. Local-only staged retrieval with
  transparent multi-signal ranking, pre-ranking privacy/source/fingerprint
  filters, per-document diversity cap, and safe insufficiency reasons. Focused
  tests: `18 passed`; full suite: `907 passed`.
- **RAG v2 evidence synthesis:** `DONE`. Generic evidence pack builder with
  numbered citations, configurable confidence assessment, insufficiency
  handling, strictest-wins privacy summary, and prompt-ready text format.
  Independent of legacy modules. Focused tests: `15 passed`; full suite:
  `921 passed`; docs/compile/audit/UI import all PASS on 2026-07-25.
- **RAG v2 eval harness:** `DONE`. Local-only benchmark runner with retrieval
  hit rates, citation source checks, insufficiency detection, privacy
  compliance, latency metrics, and PASS/FAIL verdict. Focused tests:
  `11 passed`; full suite: `931 passed`; docs/compile/audit/UI import
  all PASS on 2026-07-25.
- **RAG v2 capability benchmark:** `DONE`. Full three-arm run completed 12/12
  RAG v2 workflows, 12/12 Workspace Chat workflows, and 11/11 applicable
  NotebookLM workflows; Excel-native `BQ09` was correctly `not_applicable` for
  NotebookLM. Independent blind review imported 11 shared rows: NotebookLM won
  8, RAG v2 won 2, Workspace Chat won 1. Mean rubric score: NotebookLM 3.807/5,
  RAG v2 2.898/5, Workspace Chat 2.841/5. Conclusion: RAG v2 is a viable
  independent candidate but is not NotebookLM-equivalent and is not yet the
  active Workspace Chat retrieval path. Final validation: 977 tests, compile,
  docs contract, and CLI audit all PASS on 2026-07-25.
- **RAG v2 fail-closed corpus remediation and live rerun:** `DONE`.
  `resolve_benchmark_source_root()` now fail-closed (rejects workspace root
  fallback). `EXPECTED_SOURCE_COUNT` updated 48 → 70.
  `build_local_manifest()` validates exact 70-file count. Gold obligation
  fields (`required_sources`, `required_spans`, `required_facets`) added to
  eval harness. Live benchmark `BATTLE-RAGv2-1785003571-e33e5670` completed
  on clean 70-file corpus: NotebookLM **4.27/5**, RAG v2 **3.15/5**,
  Workspace Chat **2.68/5**. NotebookLM won 11/11 shared rows.
  Verdict: **HOLD** — RAG v2 remains `NOT_READY_FOR_PRIMARY_UI`.
  Gap to NotebookLM: -1.12 points (26% deficit).
- **Known limitation:** RAG v2 retrieval occasionally returns irrelevant content
  (BQ04: raw BOP dumps instead of error handling procedures). Synthesis depth
  and cross-source synthesis lag NotebookLM by ~1.5 points. Generated-answer
  parity, multilingual semantic retrieval, and PNG OCR remain unresolved.
- **AI Gateway:** A15 design, A16 và A17A–A17D đã hoàn thành; A18 chưa mở;
  P1.0 vẫn locked.

## Điều cần kiểm tra trước khi tiếp tục

```powershell
git status --short --branch
git log -1 --oneline
git diff --check
git diff --cached --check
py -3 scripts/check_docs.py
py -3 -m compileall src tests
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
```

- Không reset, stage, commit hoặc discard thay đổi không do gate hiện tại tạo ra.
- Đặc biệt xem xét lại staged documentation trước khi đưa vào lịch sử chính thức.
- Giữ `local_cases/`, `local_runs/`, dữ liệu gốc, secrets và runtime artifacts
  ngoài Git.

## Bước tiếp theo

1. Owner xem xét các policy `OWNER_DECISION_REQUIRED` còn mở: security disclosure,
   distribution/support, retention/RTO-RPO, named reviewer/CODEOWNERS và advisory
   enforcement.
2. P0
   [AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION.md](docs/roadmap/completed/AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION.md)
   is `DONE`; keep its privacy contract intact for every provider-route change.
3. `RAG-V2-HYBRID-RETRIEVAL-MIN` is `DONE`;
   [completed gate card](docs/roadmap/completed/RAG-V2-HYBRID-RETRIEVAL-MIN.md)
   records scope and evidence.
4. `RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN` is `DONE`;
   [completed gate card](docs/roadmap/completed/RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN.md)
   records scope and evidence.
5. `RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE` is `DONE`;
   [completed gate card](docs/roadmap/completed/RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE.md)
   records scope and evidence.
6. `NOTEBOOKLM-BATTLE-RERUN-RAG-V2` is `DONE`;
   [completed gate card](docs/roadmap/completed/NOTEBOOKLM-BATTLE-RERUN-RAG-V2.md)
   records the full blinded evidence and explicit non-parity decision.
7. `RAG-V2-DEV-QUALITY-CONVERGENCE` is `DONE`;
   [completed gate card](docs/roadmap/completed/RAG-V2-DEV-QUALITY-CONVERGENCE.md)
   records the private local replay, full validation, and the explicit
   `DEV_READY_WITH_LIMITATIONS` / `NOT_READY_FOR_PRIMARY_UI` decision. Do not plan
   primary-UI migration or claim parity without a later owner-approved live blind
   rerun that satisfies the promotion criteria.
8. Case Cockpit dependency retirement remains backlog; do not delete shared
   services before dependency/capability matrix approval.

## Phiên làm việc tiếp theo (2026-07-26 sáng)

Kết quả benchmark mới nhất cho thấy RAG v2 thua NotebookLM ở 3 điểm chính:

1. **Retrieval quality** — BQ04 trả lời sai hoàn toàn (dump raw BOP thay vì
   error handling). Cần xem lại ranking/rerank logic và query understanding.
2. **Synthesis depth** — câu trả lời ngắn hơn và ít cấu trúc hơn NotebookLM.
   Cần cải thiện synthesis prompt hoặc evidence selection.
3. **Cross-source synthesis** — kém 1.46 điểm. Cần cải thiện khả năng kết
   hợp thông tin từ nhiều tài liệu khác nhau.

Điểm số chính thức:
- NotebookLM: **4.27/5** (trước: 3.807)
- RAG v2: **3.15/5** (trước: 2.898)
- Gap: **-1.12 điểm** (26%)

Run reference: `BATTLE-RAGv2-1785003571-e33e5670` trong `local_runs/battle_rag_v2/`.
