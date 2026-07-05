# Gate A17 — IDE Agent Bridge Prompt

Bạn là implementation executor cho repo `AIOS_habbit`.

## Mục tiêu

Triển khai task-pack export và agent-report import parser theo:

- `docs/design/AIOS_BRAIN_GATEWAY_DESIGN.md`
- `docs/design/AIOS_IDE_AGENT_BRIDGE_DESIGN.md`
- `docs/design/AIOS_AGENT_RESULT_IMPORT_DESIGN.md`

Không triển khai autonomous agent execution.

## Baseline

Chạy và ghi lại branch, HEAD, origin/main, status, staged/untracked và forbidden/runtime state. Nếu baseline owner cung cấp không khớp, dừng; không tự reset/clean.

## Phạm vi

### Task pack export

Hỗ trợ schema versioned với:

- repo path;
- branch/baseline head;
- agent class;
- objective;
- allowed/forbidden files;
- allowed commands;
- required tests/report fields;
- PASS/FAIL rule;
- anti-overeager rule;
- no secret/key access;
- `.ai`/`local_cases` cleanliness;
- task-pack hash.

Agent classes: `audit-only`, `implementation`, `push-safety`, `smoke-test`.

### Report import

Parse và normalize:

- status;
- branch/head/commit;
- files touched;
- commands/tests;
- audit result;
- forbidden/runtime dirty;
- untracked scratch;
- risks/next step.

Phát hiện:

- scope violation;
- malformed/missing evidence;
- fake PASS;
- test count change không giải thích;
- forbidden/runtime dirty;
- claim không có command;
- commit/head mismatch.

Kết quả import không tự động tạo verified memory. Senior Learning Card, nếu có, chỉ là draft/review-required.

## Tái sử dụng

Tái sử dụng request ID, checksum, outbox/inbox và validation patterns trong `ide_bridge.py`/`ide_handoff_bridge.py` khi phù hợp. Giữ schema answer handoff hiện có tương thích; task-report là schema riêng.

## Không được

- Không tự chạy agent.
- Không launch external process, shell job, IDE hoặc MCP trừ khi owner phê duyệt gate riêng.
- Không đọc secret/key/env credential.
- Không thực thi command lấy từ report.
- Không checkout/reset/delete.
- Không sửa legacy UI nếu không cần.
- Không commit/push nếu owner chưa phê duyệt.

## Tests bắt buộc

- task pack round-trip UTF-8;
- required fields/schema/hash;
- PASS/FAIL/REVIEW_REQUIRED parsing;
- allowed file pass;
- file ngoài scope fail;
- forbidden file fail;
- `.ai`/`local_cases` dirty fail;
- untracked scratch fail;
- branch/head/commit mismatch;
- missing test evidence;
- changed test count unexplained;
- claims without commands;
- path traversal/unsafe report path;
- safe summary không leak secret sentinel;
- không process/network launch;
- optional learning card luôn draft.

## Validation

```powershell
git diff --name-only
git diff --stat
git diff --check
uv run --no-sync pytest -q
$env:PYTHONPATH="src"; uv run --no-sync python -m aios_habit.cli audit
py -m compileall src scripts
git status --short -- .ai local_cases task.md walkthrough.md implementation_plan.md
```

Không fake PASS. Nếu validation không chạy được, ghi command, exit code và blocker.

## Output

```text
FINAL_STATUS:
BASELINE:
TASK_PACK_SCHEMA:
REPORT_IMPORT_SCHEMA:
FAKE_PASS_DETECTION:
FILES_TOUCHED:
TESTS:
AUDIT:
FORBIDDEN_DIRTY:
RISKS:
COMMIT_CREATED: NO (trừ khi owner phê duyệt)
PUSH_PERFORMED: NO
NEXT_STEP:
```
