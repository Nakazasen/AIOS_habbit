# Gate A16 — Router Mock Integration Prompt

Bạn là implementation executor cho repo `AIOS_habbit`.

## Mục tiêu

Triển khai Brain Gateway seam và **chỉ mock Router Adapter** để Workspace Chat có thể tái sử dụng đường AI answer hiện tại qua một boundary thống nhất. Không kết nối provider thật.

Đọc trước:

- `docs/design/AIOS_EXISTING_AI_INVENTORY.md`
- `docs/design/AIOS_BRAIN_GATEWAY_DESIGN.md`
- `docs/design/AIOS_ROUTER_ADAPTER_DESIGN.md`

## Baseline bắt buộc

Trước khi sửa:

```powershell
git status -sb
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git diff --name-only
git diff --cached --name-only
git ls-files --others --exclude-standard
git status --short -- .ai local_cases task.md walkthrough.md implementation_plan.md
git diff --check
```

Nếu branch/head/worktree khác baseline owner cung cấp, dừng và báo FAIL; không tự reset/clean.

## Phạm vi implementation

1. Tạo interface Brain Gateway/Router Adapter nhỏ nhất cần thiết.
2. Tạo `DisabledRouterAdapter` và `MockRouterAdapter`.
3. Integration disabled mặc định.
4. Reuse/migrate đường Workspace Chat AI answer nếu có thể; không tạo UI AI thứ hai.
5. Giữ local retrieval/evidence hiện tại.
6. Chuẩn hóa privacy fail-closed:
   - `local_only`, `confidential`, `unknown`: deny;
   - thiếu metadata: deny;
   - mixed sources: strictest wins;
   - `machine_only`: deny mặc định, chỉ qua mock khi có explicit matching consent;
   - `cloud_safe`, `public`: có thể qua mock.
7. Adapter chỉ nhận sanitized prompt và allow-listed metadata.
8. Có audit receipt metadata không chứa raw prompt/evidence.

## Tuyệt đối không được

- Không provider/network thật.
- Không API key/secret.
- Không sửa repo `nakazasen-ai-router`.
- Không bật integration mặc định.
- Không gửi raw evidence/company docs tới adapter.
- Không xóa AI code cũ hoặc legacy Studio/Case Cockpit.
- Không autonomous agent/process launch.
- Không sửa `.ai`, `local_cases` hay runtime artifacts.
- Không commit/push nếu owner chưa phê duyệt.

## Tests bắt buộc

- mock success/failure/empty response;
- disabled-by-default và không live transport;
- metadata allow-list assertions;
- missing privacy metadata deny;
- local-only/confidential/unknown deny;
- mixed sources strictest-wins;
- machine-only default deny và consent fingerprint mismatch deny;
- sanitized prompt test;
- raw evidence/company sentinel không xuất hiện trong adapter request, audit, error;
- source-set change làm consent hết hiệu lực;
- Workspace Chat compatibility/local fallback.

Không dùng real provider trong test.

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

Nếu full pytest không khả thi, chạy targeted tests và ghi chính xác blocker môi trường. Không fake PASS.

## Báo cáo bắt buộc

```text
FINAL_STATUS: PASS_READY_FOR_REVIEW | FAIL_NEEDS_FIX
BASELINE:
FILES_TOUCHED:
DESIGN_CONFORMANCE:
PRIVACY_DENIAL_TESTS:
SANITIZATION_LEAK_TESTS:
VALIDATION:
FORBIDDEN_DIRTY:
RISKS_OR_GAPS:
COMMIT_CREATED: NO (trừ khi owner phê duyệt)
PUSH_PERFORMED: NO
NEXT_STEP:
```
