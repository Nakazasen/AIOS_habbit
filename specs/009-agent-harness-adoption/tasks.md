# Danh sách việc: Agent lập trình và thao tác file có kiểm soát

## Giai đoạn 1 — Khóa nền và spike

- [ ] T001 Ghi phiên bản, checksum, giấy phép và notices của OpenCode/Cline/Code-OSS vào `docs/roadmap/active/AIOS-AGENT-HARNESS-ADOPTION.md`
- [ ] T002 Tạo repo fixture Python và TypeScript không chứa dữ liệu thật trong `tests/fixtures/agent_harness/`
- [ ] T003 Viết capability probe fail-closed trong `scripts/probe_opencode_runtime.py`
- [ ] T004 Viết contract test health/version/session/event/read/search/deny trong `tests/test_agent_runtime_capabilities.py`
- [ ] T005 Quyết định G1 trong `docs/roadmap/active/AIOS-AGENT-HARNESS-ADOPTION.md`; dừng `BLOCKED` hoặc cho phép G2

## Giai đoạn 2 — Nền protocol dùng chung

- [ ] T006 Định nghĩa protocol và event có version trong `src/aios_habit/agent_runtime_protocol.py`
- [ ] T007 Nâng Task Pack với base digest, runtime kind và budget trong `src/aios_habit/agent_task_pack.py`
- [ ] T008 Nâng policy theo tool/path/command/expiry trong `src/aios_habit/workspace_agent_policy.py`
- [ ] T009 Tạo adapter OpenCode chỉ sau khi T005 cho phép trong `src/aios_habit/opencode_runtime_adapter.py`
- [ ] T010 Kiểm thử idempotency, event replay, cancel và resume trong `tests/test_agent_runtime_session.py`

## Giai đoạn 3 — US1: Quan sát và lập kế hoạch (P1)

**Kiểm thử độc lập**: Agent đọc/search đúng repo fixture, tạo kế hoạch và không thể ghi hoặc chạy lệnh khi policy deny.

- [ ] T011 [US1] Ánh xạ Task Pack sang runtime session trong `src/aios_habit/workspace_agent_orchestrator.py`
- [ ] T012 [P] [US1] Thêm read/search adapter có kiểm tra root trong `src/aios_habit/opencode_runtime_adapter.py`
- [ ] T013 [P] [US1] Thêm negative tests write/command/path traversal trong `tests/test_agent_runtime_readonly.py`
- [ ] T014 [US1] Ghi receipt đọc/search đã làm sạch trong `src/aios_habit/agent_result_import.py`

## Giai đoạn 4 — US2: Coding trong worktree (P2)

**Kiểm thử độc lập**: bug fixture được sửa và test trong worktree; main workspace chỉ đổi sau khi duyệt đúng proposal digest; rollback sạch.

- [ ] T015 [US2] Tạo và xác minh Git worktree tách biệt trong `src/aios_habit/workspace_agent_orchestrator.py`
- [ ] T016 [US2] Khóa proposal patch/command bất biến trong `src/aios_habit/coding_assistant.py`
- [ ] T017 [P] [US2] Thực thi command job có allowlist, timeout và process-tree cancel trong `src/aios_habit/opencode_runtime_adapter.py`
- [ ] T018 [US2] Thêm snapshot, diff/hunk và rollback trong `src/aios_habit/workspace_agent_orchestrator.py`
- [ ] T019 [US2] Chặn apply khi base/file/proposal/approval hết hạn trong `src/aios_habit/coding_assistant.py`
- [ ] T020 [US2] Xác minh exit code và workspace state độc lập trong `src/aios_habit/agent_result_import.py`
- [ ] T021 [P] [US2] Kiểm thử dirty workspace, conflict, rename/delete và partial hunk trong `tests/test_agent_worktree_safety.py`
- [ ] T022 [P] [US2] Kiểm thử long job, cancel, restart/resume và không ghi lặp trong `tests/test_agent_runtime_recovery.py`

## Giai đoạn 5 — US3: Giao diện và bằng chứng hằng ngày (P3)

**Kiểm thử độc lập**: cùng một task hoàn tất qua Code-OSS và CLI/headless, resume được và tra cứu receipt từ hồ sơ `agent_work`.

- [ ] T023 [US3] Tạo extension Code-OSS mỏng dùng protocol chung trong `extensions/aios-agent-companion/`
- [ ] T024 [P] [US3] Tạo CLI/headless client dùng cùng protocol trong `src/aios_habit/agent_runtime_cli.py`
- [ ] T025 [US3] Liên kết receipt với hồ sơ `agent_work` trong `src/aios_habit/workspace_case_service.py`
- [ ] T026 [US3] Chỉ tạo lesson candidate từ kết quả đã duyệt trong `src/aios_habit/agent_learning.py`
- [ ] T027 [P] [US3] Kiểm thử UI tiếng Việt, secret redaction và không lộ traceback trong `tests/test_agent_companion_ui.py`
- [ ] T028 [US3] Kiểm thử E2E Windows với path khoảng trắng/tiếng Việt trong `tests/test_agent_runtime_windows_e2e.py`

## Giai đoạn 6 — An toàn, phát hành và benchmark

- [ ] T029 Cập nhật threat model và privacy review trong `docs/security/THREAT_MODEL.md` và `docs/security/PRIVACY_IMPACT_ASSESSMENT.md`
- [ ] T030 Ghi SBOM, license, notices và quy trình nâng upstream trong `docs/release/AGENT_RUNTIME_SUPPLY_CHAIN.md`
- [ ] T031 Chạy 12 tình huống và 10 task benchmark; ghi evidence vào `docs/roadmap/active/AIOS-AGENT-HARNESS-ADOPTION.md`
- [ ] T032 Chạy clean-machine Windows E2E và đóng gói lặp lại theo `specs/009-agent-harness-adoption/quickstart.md`
- [ ] T033 Đồng bộ `./ARCHITECTURE.md`, `./ROADMAP.md` và `./PROJECT_HANDOVER.md` theo trạng thái thực tế
- [ ] T034 Chạy toàn bộ quality gate trong `specs/009-agent-harness-adoption/quickstart.md` và chỉ chuyển Gate Card sang `DONE` khi không còn blocker

## Phụ thuộc và chiến lược

T001–T005 là cổng dừng sớm. T006–T010 chỉ bắt đầu khi G1 đạt. US1 là MVP; US2 phụ thuộc protocol; US3 phụ thuộc vòng coding an toàn. Các task gắn `[P]` có thể thực hiện song song khi task nền của cùng giai đoạn đã xong.
