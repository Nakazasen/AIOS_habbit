# Copy-paste prompt for Gemini 3.7 Flash

Bạn là implementation agent cho repository `D:\Sandbox\AIOS_habbit` trên Windows PowerShell.

Mục tiêu: triển khai đầy đủ feature `003-adaptive-reranking-ux` theo spec/plan/tasks hiện có. Không thiết kế lại từ đầu và không tin các claim cũ nếu chưa kiểm tra live repo.

## Bắt buộc đọc trước khi làm

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
git branch --show-current
git status --short
graphify query "Where does Workspace Chat choose and execute RAG retrieval, persist conversation preferences, and report reranker fallback?" --budget 3500 --graph graphify-out/graph.json
```

## Không được vi phạm

- Worktree đang có nhiều thay đổi của người khác. Không reset, checkout, clean, xóa, format hàng loạt, stage hoặc commit các diff không thuộc feature.
- Không commit/push trừ khi owner ra lệnh riêng sau khi audit.
- Không bật canary production. Code/manifest mới phải adaptive-off mặc định.
- Không gửi query, tài liệu, local-only data hoặc secret ra cloud/network.
- Không để model sinh câu trả lời làm trọng tài duy nhất cho easy/hard.
- `Tìm kỹ hơn` của người dùng luôn thắng Auto; kể cả câu dễ vẫn phải request reranker.
- `uncertain` luôn nâng lên Deep.
- Không hiển thị `Đã tìm kỹ` nếu `reranker_applied` không thực sự true.
- Không tải/reload model trong interactive query.
- Structured Excel route phải được xét trước text adaptive routing.
- Không sửa task thành `[x]` nếu chưa có evidence.

## Hành vi phải đạt

```text
structured Excel phù hợp → đường Excel hiện có
user chọn Tìm kỹ hơn     → BGE-M3 Hybrid + local reranker
Auto pre-gate deep/xám   → BGE-M3 Hybrid + local reranker
Auto pre-gate fast       → Hybrid trước
Hybrid đủ bằng chứng     → giữ Hybrid
Hybrid yếu/xám           → chạy reranker
reranker lỗi/timeout     → Hybrid degraded + báo rõ
Hybrid cũng không đủ     → answer with limits/abstain
```

UI chỉ dùng `Tự động`, `Tìm kỹ hơn (có thể chậm hơn)`, `Đang tìm kỹ`, `Đã tìm kỹ` và copy degraded tiếng Việt. Tên model/profile chỉ ở developer diagnostics.

## Cách thực hiện

1. Làm tuần tự T001-T054 trong `tasks.md`.
2. Với mỗi phase: viết test trước, xác nhận fail đúng lý do, implement tối thiểu, chạy focused test, ghi evidence.
3. Giữ base/index identity là `bge_m3_hybrid`; mở reranker như capability optional trong cùng worker và chọn theo query.
4. Manifest v2 cũ phải tiếp tục load Hybrid-only. Schema adaptive mới có reranker path/revision/checksum, policy version, resource budget và sealed benchmark evidence.
5. Dataset route phải synthetic/non-private, ít nhất 60 cases cân bằng và frozen/checksummed trước tuning.
6. Benchmark windows 10,20,30; chọn window nhỏ nhất đạt quality, không mặc định 30.
7. Nếu benchmark không đạt, để adaptive disabled và báo PARTIAL/FAIL. Không hạ gate hoặc sửa labels sau khi xem kết quả.
8. Cập nhật docs canonical, handover và graph theo tasks.

## Lệnh kiểm tra bắt buộc

Focused:

```powershell
py -3 -m pytest -q tests/test_adaptive_retrieval.py tests/test_rag_v2_pipeline.py tests/test_workspace_chat_rag_v2_adapter.py tests/test_workspace_chat_rag_v2_deployment.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_ui_copy.py
py -3 -m compileall src tests
git diff --check
```

Benchmark (sau khi script tồn tại):

```powershell
py -3 scripts/benchmark_adaptive_reranking.py --cases tests/fixtures/adaptive_routing_cases.json --windows 10,20,30 --output local_runs/adaptive_reranking/report.json
```

Full gates, chạy và báo riêng từng lệnh:

```powershell
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
graphify update . --no-cluster
git diff --check
git status --short
```

Không chạy benchmark nặng song song với full pytest trên máy 16 GB.

## Gate activation

- Route accuracy >=95%.
- Explicit Deep requested rate =100%.
- Uncertain→Deep rate =100%.
- Hard-set MRR@10 gain >=5%; Recall@10 regression <=2%.
- Auto-fast p95 regression <=10% so với Hybrid baseline đo lại cùng phiên.
- Deep warm p95 <=5 giây.
- Runtime init count=1; không OOM; RAM khả dụng >=2 GB.
- Zero raw query/source/path/secret/exception leakage trong telemetry/report.
- Missing model, checksum mismatch, timeout, inference failure đều không silent fallback.
- Legacy conversation và manifest v2 vẫn hoạt động.
- Rollback không rebuild index hoặc mất data.

## Báo cáo cuối bắt buộc

```text
STATUS: PASS | PARTIAL | FAIL | BLOCKED

1. Initial state
- branch, HEAD
- dirty paths trước khi làm
- graph nodes đã dùng

2. Task progress
- completed task IDs
- incomplete task IDs + reason

3. Files changed
- feature files created/modified
- pre-existing files intentionally untouched

4. Behavior evidence
- Auto simple
- Auto hard
- Auto weak/uncertain
- User Deep on simple query
- structured Excel
- reranker failure/degraded UI

5. Route/quality/performance
- dataset checksum/balance/confusion matrix
- hard→fast false negatives
- MRR/Recall comparison
- Hybrid baseline p95, Auto-fast p95, Deep p95
- candidate window, peak RSS, available RAM, init count

6. Commands
| command | exit | duration | result |

7. Privacy/rollback/docs/graph
- scan result
- rollback rehearsal
- docs updated
- graph stats

8. Unresolved risks
- exact blockers; do not call complete if any mandatory gate is pending

9. Git
- final git status
- no commit/push unless separately authorized
```

Kết thúc bằng cách chỉ ra file `specs/003-adaptive-reranking-ux/implementation-evidence.md` để Terra tự audit. Không tự tuyên bố Terra PASS.
