# Independent Audit Plan: Adaptive Reranking

## Audit objective

Xác minh implementation đáp ứng đúng ba lời hứa sản phẩm:

1. Auto không thể âm thầm coi mọi câu hỏi là dễ.
2. `Tìm kỹ hơn` của người dùng luôn yêu cầu reranker.
3. Khi reranker không chạy được, hạ cấp được báo rõ và hệ thống không giả vờ đã tìm kỹ.

Terra thực hiện audit độc lập, read-only đối với source/docs. Test có thể tạo cache/runtime ignored, nhưng Terra không sửa code, không format, không cập nhật graph, không stage và không commit.

## Verdict rules

- **PASS**: Tất cả gate bắt buộc có evidence hiện tại và pass; không có Critical/High finding; full suite/CLI audit/import/benchmark/rollback đều xác minh được.
- **PARTIAL**: Behavior chính có vẻ đúng nhưng thiếu hoặc chưa chạy một gate bắt buộc, benchmark không đúng máy, full suite timeout, docs/graph/handover chưa đồng bộ, hoặc evidence không đủ tái hiện.
- **FAIL**: User Deep bị downgrade; uncertain đi fast; hạ cấp im lặng; false `Đã tìm kỹ`; privacy/network violation; manifest cũ hỏng; quality/performance gate fail nhưng feature vẫn bật; test bắt buộc fail.
- **BLOCKED**: Chỉ dùng khi môi trường thực sự ngăn audit (ví dụ model artifact không có) và phải liệt kê chính xác phần vẫn audit được. Không đổi BLOCKED thành PASS dựa trên report kể lại.

## Audit stages

### A. Provenance and scope

- Read spec/plan/tasks/contracts/checklists and implementation evidence.
- Capture branch, HEAD, worktree and feature-file diff.
- Separate pre-existing dirty changes from files Gemini claims to modify.
- Verify every checked task has a command, artifact or diff evidence.

### B. Static design audit

- Trace UI preference → persistence → adapter → IPC → pipeline → index reranker → telemetry → UI status.
- Verify structured Excel remains first.
- Verify one initialized worker; no model/network load inside interactive query.
- Verify privacy/source filters apply before rerank and cannot be broadened.
- Verify policy returns three states and unknown/uncertain escalates.
- Verify user Deep bypasses Auto downgrade.

### C. Focused behavior tests

- Run the focused suite from `quickstart.md`.
- Add no tests during audit; if a gap exists, report the exact missing test and expected assertion.
- Inspect route distribution and confusion matrix; reject a misleading high accuracy caused by class imbalance.
- Inject/execute existing tests for missing model, timeout, inference failure, invalid IPC and old manifest.

### D. Benchmark evidence

- Verify dataset/checksum were frozen before threshold decision.
- Verify Hybrid and Deep use the same corpus/questions/filters.
- Verify route accuracy >=95%, explicit Deep=100%, uncertain escalation=100%.
- Verify hard-set MRR improvement >=5% and Recall regression <=2%.
- Verify fast p95 regression <=10%, deep warm p95 <=5s, runtime init count=1, available RAM >=2 GB and no OOM.
- Verify raw report is local/ignored and sanitized report has no content/path leakage.

### E. Failure, privacy and UX

- Verify `reranker_applied` is evidence of execution, not copied from requested mode.
- Verify all degraded paths have allow-listed reason code and Vietnamese copy.
- Scan tracked reports/log fixtures for raw query, source snippet/title/path, secrets and exception strings.
- Verify technical profile names are absent from normal UI copy.

### F. Compatibility and rollback

- Load legacy conversation without preference → `auto`.
- Load v2 Hybrid manifest → adaptive false and Hybrid works.
- Disable adaptive/new manifest and restart → no index rebuild/data loss.
- Verify user Deep during disabled adaptive does not show false Deep success.

### G. Project gates and docs

- Run compileall, full pytest, CLI audit and import smoke separately.
- Verify docs reflect actual status, not intended status.
- Verify `ROADMAP.md` and `PROJECT_HANDOVER.md` do not say complete while any gate is pending.
- Verify graph was refreshed after code changes and contains adaptive routing symbols.

## Required audit output

```text
VERDICT: PASS | PARTIAL | FAIL | BLOCKED

EXECUTIVE SUMMARY
- 3-6 bullets

GATE TABLE
| Gate | Status | Evidence | Command/artifact |

FINDINGS (ordered Critical → High → Medium → Low)
| ID | Severity | File:line | Requirement | Evidence | Required correction |

ANTI-ALL-EASY CHECK
- dataset balance
- confusion matrix
- hard→fast false negatives
- uncertain→deep rate
- explicit deep→requested/applied rates

PERFORMANCE/MEMORY
- machine identity
- Hybrid baseline p95
- Auto-fast p95/regression
- Deep warm p95
- candidate window
- peak RSS / available RAM
- runtime init count

PRIVACY/FALLBACK/ROLLBACK
- raw-content scan
- network/model-load check
- injected failures
- legacy manifest/conversation
- rollback result

COMMAND RESULTS
| Command | Exit | Duration | Result |

TASK CLAIM AUDIT
- checked without evidence
- implemented but unchecked
- out-of-scope changes

FINAL DECISION
- Can owner enable canary: YES/NO
- Blocking actions
```

Every PASS claim needs a current command or reviewable artifact. Historical numbers may be context only.
