# Hướng dẫn xác minh theo cổng

Tài liệu này mô tả lệnh nghiệm thu phải chạy sau implementation. Hiện tại G1 chưa có probe/runtime/fixture nên các lệnh G1 trở đi là contract đầu ra cho bước /speckit-tasks, không phải bằng chứng đã đạt. Chỉ dùng fixture giả lập; không trỏ vào repo làm việc hoặc dữ liệu thật.

## 1. Điều kiện chung

~~~powershell
uv run --no-sync --group dev python -c "import sys; assert sys.version_info[:2] == (3, 11); print(sys.version)"
git status --short --branch
~~~

Kỳ vọng: Python 3.11. Worktree người dùng có thể đang bẩn, nhưng test Agent phải dùng repo fixture độc lập. Không chạy lệnh dọn/reset/stash trên workspace thật.

## 2. G0 — Kiểm tra artifact và ranh giới

~~~powershell
uv run --no-sync --group dev python scripts/check_docs.py
git diff --check -- specs/009-agent-harness-adoption
git diff -- specs/009-agent-harness-adoption/tasks.md
~~~

Kỳ vọng: tài liệu UTF-8 không mojibake; diff tasks.md rỗng trong lượt /speckit-plan; ADR-0008, Gate Card và feature 009 liên kết đúng. setup-plan.ps1 phải được gọi trong ngữ cảnh feature 009 trước khi sinh task, không dùng FEATURE_SPEC 010 do nhánh hiện tại tự nhận diện.

## 3. G1 — Probe runtime chỉ đọc

Sau khi task G1 tạo script/fixture và pin runtime:

~~~powershell
uv run --no-sync --group dev python scripts/probe_opencode_runtime.py --fixture tests/fixtures/agent_harness/python_bug --bind 127.0.0.1 --mode readonly --json
uv run --no-sync --group dev pytest -q tests/test_agent_runtime_capabilities.py
uv run --no-sync --group dev pytest -q tests/test_agent_runtime_readonly.py
~~~

Probe phải ghi nhận health/version/checksum, local auth, create/get/abort/resume session, SSE/event, read/search và diff/state. Negative test phải đề nghị write/command và chứng minh:

- Request bị từ chối trước tool execution.
- Digest toàn fixture không đổi.
- Không có process command được tạo.
- Report lỗi tiếng Việt có receipt, không có raw error.

Thiếu một mục: ghi G1 BLOCKED, không chạy G2–G8 và đánh giá Cline bằng đúng rubric. Không tạo adapter “giả đạt”.

## 4. G2 — Session, event và idempotency

~~~powershell
uv run --no-sync --group dev pytest -q tests/test_agent_runtime_session.py
uv run --no-sync --group dev pytest -q tests/test_agent_runtime_protocol_contract.py
~~~

Các case bắt buộc:

- Reconnect từ cursor/sequence cuối không mất hoặc nhân đôi event.
- Cùng idempotency key/cùng payload trả receipt cũ.
- Cùng key/khác payload bị từ chối.
- Mất kết nối giữa write chuyển interrupted_unknown, không tự replay.
- Approval hết hạn không sống lại sau resume.

## 5. G3 — Worktree, proposal, partial hunk và rollback

~~~powershell
uv run --no-sync --group dev pytest -q tests/test_agent_worktree_safety.py
uv run --no-sync --group dev pytest -q tests/test_agent_runtime_recovery.py
~~~

Chạy ít nhất các fixture: sửa một file, nhiều file, create/rename/delete, đường dẫn tiếng Việt, đường dẫn có khoảng trắng, symlink thoát root, path traversal, workspace bẩn và file đổi sau approval.

Kỳ vọng:

- Runtime chỉ ghi task worktree; main workspace giữ nguyên trước apply.
- Workspace bẩn bị chặn ở chế độ ghi mà không mất dữ liệu.
- Proposal bind base/file/policy/expiry.
- Chọn một phần hunk tạo selection digest và được verifier chạy lại riêng.
- Mismatch/expiry/replay không apply.
- Rollback đưa task/apply state về snapshot đã xác minh và không rewrite Git history.

## 6. G4 — Vòng sửa–test–sửa lỗi và báo cáo lỗi

~~~powershell
uv run --no-sync --group dev pytest -q tests/test_agent_runtime_coding_e2e.py
uv run --no-sync --group dev pytest -q tests/test_agent_error_report.py
uv run --no-sync --group dev pytest -q tests/test_agent_observed_verifier.py
~~~

Các case chặn:

1. Model khai PASS nhưng verifier quan sát exit code 1: verdict không được đạt, main workspace không đổi, report VERIFICATION_FAILED bằng tiếng Việt.
2. Test lỗi lần đầu, Agent sửa trong budget, verifier chạy lại đạt, người dùng duyệt đúng digest rồi apply.
3. UI checkbox hoặc report tự khai không thể tạo observed evidence.
4. Runtime trả traceback/absolute path/secret/stdout thô: persistence/UI chỉ nhận error report đã redaction.
5. Cancel giữa command dài: cây process dừng; nếu còn residue, trạng thái cancelled_with_residue và không hiển thị thành công.

## 7. G5 — Cùng protocol qua CLI và Code-OSS

~~~powershell
uv run --no-sync --group dev pytest -q tests/test_agent_runtime_client_parity.py
uv run --no-sync --group dev pytest -q tests/test_agent_companion_ui.py
~~~

Chạy cùng một fixture qua CLI/headless và extension. Kỳ vọng: cùng task/session/proposal/decision/receipt; UI chỉ dùng tiếng Việt, lỗi không gọi nhánh success, không cần sửa JSON thủ công. Extension dùng editor/diff/terminal sẵn có và không có đường gọi runtime bỏ qua Gateway.

## 8. G6 — Persistence, privacy và learning

~~~powershell
uv run --no-sync --group dev pytest -q tests/test_agent_work_record_persistence.py
uv run --no-sync --group dev pytest -q tests/test_agent_runtime_privacy.py
uv run --no-sync --group dev pytest -q tests/test_agent_learning_gate.py
~~~

Kỳ vọng sau restart: đọc lại binding, proposal/decision/verification/receipt/error report đã làm sạch; digest truy ngược được; transcript/diff/output thô không có trong workspace_cases.sqlite; kết quả rejected, revoked hoặc chưa verified không tạo lesson.

## 9. G7 — Supply chain, privacy và gói Windows

~~~powershell
uv run --no-sync --group dev pytest -q tests/test_agent_runtime_supply_chain.py
uv run --no-sync --group dev pytest -q tests/test_agent_runtime_windows_e2e.py
uv run --no-sync --group dev python scripts/agent_runtime_clean_machine_smoke.py --fixture tests/fixtures/agent_harness/python_bug
~~~

Kỳ vọng: binary/runtime khớp version/checksum/notices; server chỉ bind loopback và có xác thực; environment dùng allowlist; path khoảng trắng/tiếng Việt đúng UTF-8; package cài lại được trên máy sạch.

## 10. G8 — Benchmark và cổng đầy đủ

~~~powershell
uv run --no-sync --group dev python scripts/benchmark_agent_runtime.py --fixtures tests/fixtures/agent_harness/benchmarks --runs 10 --json
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
git diff --check
git diff --cached --check
~~~

Benchmark phải chạy 10 task cố định với cùng model, thời gian và quyền; 12/12 tình huống permission/privacy/resume/rollback/observed evidence là điều kiện tuyệt đối. CLI audit phải trả status PASS. Clean-machine E2E và reviewer độc lập vẫn là điều kiện trước khi đổi trạng thái Goal.

## 11. Ma trận kết quả tối thiểu

| Tình huống | Main workspace | Verification | Báo cáo |
|---|---|---|---|
| Read-only probe | Không đổi | Capability receipt | Thành công kỹ thuật hoặc BLOCKED có lý do |
| Model khai PASS, test thực lỗi | Không đổi | failed | Lỗi tiếng Việt, VERIFICATION_FAILED |
| Partial hunk test lỗi | Không đổi | failed trên selection | Nêu đúng selection, cho tạo proposal mới |
| Base đổi sau approval | Không đổi | không chạy apply | BASELINE_CHANGED |
| Cancel còn process | Không apply | unknown/residue | cancelled_with_residue |
| Full patch verified và apply | Chỉ đổi file đã duyệt | passed | Receipt apply; không dùng error report |
| Rollback sau apply lỗi | Khớp snapshot trước apply | rollback observed | ROLLBACK_FAILED nếu không khớp |

Không dòng nào được ghi PASS dựa trên lời model, report tự khai hoặc trạng thái do UI tự dựng.
