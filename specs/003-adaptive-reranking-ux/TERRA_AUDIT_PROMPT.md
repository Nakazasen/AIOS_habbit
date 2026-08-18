# Copy-paste prompt for Terra independent audit

Bạn là independent audit agent cho repository `D:\Sandbox\AIOS_habbit`. Audit implementation của feature `003-adaptive-reranking-ux` dựa trên live repo và evidence hiện tại, không tin narrative của Gemini nếu không tái hiện được.

## Chế độ bắt buộc: READ-ONLY SOURCE AUDIT

- Không sửa source, tests, docs, spec, tasks, graph hoặc report.
- Không chạy formatter, migration ghi dữ liệu, activation, `graphify update`, git stage/commit/push/reset/clean/checkout.
- Được chạy read-only inspection và tests; runtime cache/pytest cache ignored có thể phát sinh nhưng không được sửa tracked files.
- Nếu thấy lỗi nhỏ cũng chỉ báo finding; không tự fix.
- Worktree có thể đã dirty từ trước. Phân biệt diff feature với diff khác; không coi mọi dirty file là do Gemini.

## Đọc và chụp trạng thái

```powershell
Set-Location D:\Sandbox\AIOS_habbit
Get-Content -Raw -Encoding utf8 AGENT_RULES.md
Get-Content -Raw -Encoding utf8 .specify/memory/constitution.md
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/spec.md
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/plan.md
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/research.md
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/data-model.md
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/contracts/adaptive-retrieval-routing.md
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/tasks.md
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/checklists/audit-requirements.md
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/audit-plan.md
Get-Content -Raw -Encoding utf8 specs/003-adaptive-reranking-ux/implementation-evidence.md
git branch --show-current
git rev-parse HEAD
git status --short
git diff --check
graphify query "Trace adaptive retrieval from Workspace Chat user preference through adapter and BGE worker to reranker telemetry and fallback" --budget 4000 --graph graphify-out/graph.json
```

Nếu implementation evidence không tồn tại, verdict tối đa là PARTIAL; vẫn audit phần code/test có thể audit.

## Ba invariant quan trọng nhất

1. Auto không được dùng một model sinh câu trả lời làm trọng tài duy nhất; unknown/uncertain phải Deep.
2. User chọn `Tìm kỹ hơn` luôn request reranker, kể cả pre-gate nói fast.
3. UI chỉ được nói `Đã tìm kỹ` khi final telemetry chứng minh `reranker_applied=true`; fallback phải explicit degraded.

Bất kỳ vi phạm nào ở trên là FAIL, ít nhất High; privacy leak hoặc false certainty có thể Critical.

## Trace code bắt buộc

- `WorkspaceConversation.search_preference` và backward-compatible loader.
- UI selector/status trong `workspace_chat_app.py`.
- preference truyền vào `retrieve_workspace_chat_evidence()`.
- structured Excel vẫn xét trước adaptive text route.
- pre/post gates và three-state decision trong `rag_v2/adaptive_retrieval.py`.
- query-time `rerank_requested` qua client JSONL → worker → pipeline → index.
- reranker scores thực sự ảnh hưởng final rank khi `reranker_applied=true`.
- timeout/circuit/fallback không reload model trong request.
- telemetry allow-list và user copy.
- manifest v2 compatibility, adaptive off default, sealed activation gates và rollback.

## Lệnh test bắt buộc

Chạy từng lệnh riêng, ghi exit code/duration; không gộp claim:

```powershell
py -3 -m pytest -q tests/test_adaptive_retrieval.py tests/test_rag_v2_pipeline.py tests/test_workspace_chat_rag_v2_adapter.py tests/test_workspace_chat_rag_v2_deployment.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_ui_copy.py
py -3 -m compileall src tests
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
git diff --check
```

Không biến focused PASS thành full-suite PASS. Nếu full suite timeout/chưa chạy, verdict tối đa PARTIAL.

## Audit benchmark và chống “lúc nào cũng dễ”

Kiểm tra raw report trong `local_runs/adaptive_reranking/report.json` nếu có và sanitized decision/evidence trong feature directory. Có thể chạy lại benchmark tuần tự nếu model/corpus hiện diện và không làm thay đổi tracked data:

```powershell
py -3 scripts/benchmark_adaptive_reranking.py --cases tests/fixtures/adaptive_routing_cases.json --windows 10,20,30 --output local_runs/adaptive_reranking/terra-report.json
```

Phải báo:

- tổng case và phân bố từng class;
- confusion matrix;
- hard→fast false negatives;
- uncertain→Deep rate (phải 100%);
- explicit Deep requested rate (phải 100%);
- explicit Deep applied rate và degraded reasons;
- kiểm tra classifier all-fast/all-deep;
- dataset checksum có khớp evidence và labels có bị sửa sau benchmark không;
- MRR@10 gain >=5%, Recall@10 regression <=2%;
- Auto-fast p95 regression <=10%, Deep warm p95 <=5s;
- peak RSS, RAM khả dụng >=2 GB, runtime init count=1;
- máy benchmark có đúng i5/16 GB/CPU-only và cùng phiên baseline không.

Nếu chỉ có số kể lại, report thiếu checksum/machine identity hoặc benchmark trên máy khác, không PASS gate đó.

## Failure/privacy/rollback

- Xác minh test/evidence cho missing reranker, bad checksum, timeout, inference error, resource/circuit-open.
- Scan telemetry/reports/fixtures/log output: không raw query, snippets, source title/path, credentials, exception text hoặc query-derived short hash.
- Xác minh không network/model download trong interactive query.
- Load legacy conversation thiếu preference → Auto.
- Load v2 manifest → Hybrid-only.
- Disable adaptive/restart rehearsal → không rebuild index, không mất conversation/source.
- User Deep khi capability unavailable → explicit degraded/unavailable, không false success.

## Docs/graph/task truthfulness

- Mỗi task `[x]` phải có code/evidence tương ứng; liệt kê checked-without-evidence.
- Liệt kê code đã làm nhưng task chưa check.
- So docs/ROADMAP/PROJECT_HANDOVER với kết quả live; claim completed khi gate pending là finding.
- Xác minh graph có symbol/edge adaptive mới và mtime/update evidence sau code changes; không tự update graph.

## Verdict rules

- PASS chỉ khi mọi mandatory gate current PASS, không Critical/High, full suite/CLI/import/benchmark/rollback đều xác minh.
- PARTIAL khi behavior chính pass nhưng thiếu full suite, benchmark đúng máy, docs/graph/handover hoặc evidence.
- FAIL khi invariant sai, privacy/network vi phạm, hạ cấp im lặng, false `Đã tìm kỹ`, compatibility hỏng, gate fail nhưng feature bật, hoặc test bắt buộc fail.
- BLOCKED chỉ khi môi trường ngăn tái hiện; vẫn phải audit phần còn lại và không đổi thiếu evidence thành PASS.

## Format báo cáo bắt buộc

```text
VERDICT: PASS | PARTIAL | FAIL | BLOCKED

EXECUTIVE SUMMARY
- ...

GATE TABLE
| Gate | Status | Evidence | Command/artifact |

FINDINGS (Critical → High → Medium → Low)
| ID | Severity | File:line | Requirement | Evidence | Required correction |

ANTI-ALL-EASY CHECK
- dataset balance:
- confusion matrix:
- hard→fast:
- uncertain→deep:
- explicit deep requested/applied:

PERFORMANCE/MEMORY
- machine:
- baseline/fast/deep p95:
- window:
- RSS/free RAM/init count:

PRIVACY/FALLBACK/ROLLBACK
- ...

COMMAND RESULTS
| Command | Exit | Duration | Result |

TASK CLAIM AUDIT
- checked without evidence:
- implemented but unchecked:
- out-of-scope changes:

FINAL DECISION
- Can owner enable canary: YES/NO
- Blocking actions:
```

Không sửa gì. Kết thúc bằng `git status --short` để chứng minh audit không tạo tracked diff mới.
