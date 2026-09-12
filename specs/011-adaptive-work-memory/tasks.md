# Nhiệm vụ: Vòng trí nhớ công việc thích nghi

**Đầu vào**: Các artifact trong `specs/011-adaptive-work-memory/`  
**Trạng thái**: `READY_FOR_EXECUTION`  
**Cách chạy**: Grok thực hiện liên tục T001–T030 theo thứ tự và tiếp tục từ task chưa xong nếu bị gián đoạn. Codex độc lập thực hiện T031–T032.

## Giai đoạn 1 — Cổng vào và baseline

**Mục tiêu**: Bảo toàn cây làm việc, chụp baseline và kiểm tra từng nguồn độc lập.

- [x] T001 Xác minh baseline và contract nguồn tùy chọn: Goal 011 tiếp tục dù Goal 010 chưa đóng; adapter chỉ đọc artifact đủ điều kiện và trả candidate rỗng khi nguồn không sẵn sàng trong `src/aios_habit/knowledge_publication.py` và `tests/test_workspace_memory_recall.py`
- [x] T002 Ghi branch, dirty-tree, phạm vi Goal, baseline prompt và rollback vào `docs/roadmap/backlog/AIOS-ADAPTIVE-WORK-MEMORY.md` mà không đưa `local_cases/`, `local_runs/`, `.env` hoặc file người dùng vào phạm vi
- [x] T003 Viết và chạy assertion baseline khi feature flag tắt trong `tests/test_workspace_memory_recall.py`

**Checkpoint**: T001 PASS khi Goal 010 không còn là blocker. Không sửa T106/T108/T109 trong lượt Goal 011.

---

## Giai đoạn 2 — Nền tối thiểu

**Mục tiêu**: Tạo cổng tắt, fixture và model chỉ đủ cho recall.

- [x] T004 [P] Viết test flag mặc định tắt, override cô lập và reset sạch trong `tests/test_workspace_memory_recall.py`
- [x] T005 Thêm `adaptive_work_memory` mặc định `False` và mapping tương thích ngược trong `src/aios_habit/feature_flags.py`
- [x] T006 [P] Viết đúng 30 tình huống gắn nhãn giả lập, gồm 20 câu liên quan và 10 câu không liên quan, bao phủ mọi trạng thái của bốn nguồn US1 trong `tests/fixtures/workspace_memory/fixture_manifest.json`
- [x] T007 Tạo các dataclass và validation recall request/item/result/trace trong `src/aios_habit/workspace_memory_models.py`; chưa tạo `MemoryDecision` hoặc correction

---

## Giai đoạn 3 — US1: Gọi lại tri thức đã xác nhận (P1)

**Mục tiêu**: Trước câu trả lời, gọi lại đúng bài học từ bốn nguồn hiện có mà không ghi dữ liệu.

**Kiểm thử độc lập**: Ít nhất 18/20 câu liên quan gọi lại đúng, 10/10 no-match không chèn memory; draft/revoked/missing-evidence không vào prompt.

- [x] T008 [P] [US1] Viết test eligibility, Unicode ranking, scope, negative applicability, dedup, conflict và ngưỡng SC-002 cho bốn nguồn trong `tests/test_workspace_memory_recall.py`
- [x] T009 [P] [US1] Viết test baseline prompt, no-match, delimiter injection, provenance, privacy và consent fingerprint trong `tests/test_workspace_chat_ai_answer.py`
- [x] T010 [US1] Cài bốn bộ đọc read-only, eligibility trước scoring, bounded result và deterministic rank trong `src/aios_habit/workspace_memory_service.py`
- [x] T011 [US1] Thêm block “Sổ việc đã xác nhận” tùy chọn, tối đa 5 mục/4.000 ký tự và quy tắc memory-as-data trong `src/aios_habit/workspace_chat_ai_answer.py`
- [x] T012 [US1] Nối cùng một recall result vào direct provider, bridge, collection/provider context và consent fingerprint trong `src/aios_habit/workspace_chat_ai_answer.py`, `src/aios_habit/antigravity_bridge.py`, `src/aios_habit/workspace_chat_app.py`
- [x] T013 [P] [US1] Thêm panel “Vì sao AIOS nhớ điều này?” và test UI metadata an toàn bằng tiếng Việt trong `src/aios_habit/workspace_memory_ui.py`, `tests/test_workspace_memory_ui.py`, `tests/test_workspace_chat_ui_i18n.py`
- [x] T014 [P] [US1] Tạo benchmark 10.000 mục/100 lượt, đo p95 và working set không tải model trong `scripts/benchmark_workspace_memory_recall.py`
- [x] T015 [US1] Chạy mục 2, 3, 6 của `specs/011-adaptive-work-memory/quickstart.md`, sửa lỗi trong phạm vi và ghi checkpoint US1 vào `docs/roadmap/backlog/AIOS-ADAPTIVE-WORK-MEMORY.md`

**Checkpoint**: Test US1 và privacy phải PASS; Grok tiếp tục US2, không cần audit trung gian.

---

## Giai đoạn 4 — US2: Nhớ và quên có xác nhận (P2)

**Mục tiêu**: Người dùng chủ động tạo hoặc vô hiệu hóa memory; hội thoại thường không tự trở thành memory.

**Kiểm thử độc lập**: Preview/cancel không ghi; confirm còn hiệu lực qua restart; forget ngừng recall ngay; ghi đồng thời không tạo JSONL dở dang.

- [x] T016 [P] [US2] Viết test preview/cancel/confirm/forget, append-only, `LibraryWriterLease`, idempotency, restart và cache stale trong `tests/test_workspace_memory_commands.py`
- [x] T017 [US2] Tạo `MemoryDecision` và validation theo `data-model.md` trong `src/aios_habit/workspace_memory_models.py`
- [x] T018 [US2] Cài effective-decision resolver và append-only store tại `local_cases/workspace_memory/memory_decisions.jsonl`, tái sử dụng `LibraryWriterLease` và không tạo lock abstraction mới trong `src/aios_habit/workspace_memory_service.py`
- [x] T019 [US2] Cài luồng “Hãy nhớ:”/“Hãy quên:”, preview và xác nhận/hủy bằng tiếng Việt trong `src/aios_habit/workspace_memory_ui.py`
- [x] T020 [US2] Nối user-memory effective view vào recall và invalidation sau forget/revoke trong `src/aios_habit/workspace_memory_service.py` và `src/aios_habit/workspace_chat_app.py`
- [x] T021 [US2] Chạy mục 4 của `specs/011-adaptive-work-memory/quickstart.md`, sửa lỗi trong phạm vi và ghi checkpoint US2 vào `docs/roadmap/backlog/AIOS-ADAPTIVE-WORK-MEMORY.md`

**Checkpoint**: Test persistence, concurrency và privacy phải PASS; Grok tiếp tục US3.

---

## Giai đoạn 5 — US3: Học từ sửa sai (P3)

**Mục tiêu**: Correction rõ ràng trở thành candidate có thể duyệt; không lưu raw answer và không tạo bài học trùng âm thầm.

**Kiểm thử độc lập**: Candidate chưa xác nhận không recall; confirmed correction recall ở phiên mới; duplicate/conflict yêu cầu quyết định rõ.

- [x] T022 [P] [US3] Viết test candidate isolation, message/trace refs, no-raw-answer, duplicate digest và conflict choices trong `tests/test_workspace_memory_corrections.py`
- [x] T023 [US3] Tạo `CorrectionLessonCandidate` và chuyển đổi sang `MemoryDecision` sau confirm trong `src/aios_habit/workspace_memory_models.py`
- [x] T024 [US3] Cài duplicate/conflict resolver xác định và provenance merge trong `src/aios_habit/workspace_memory_service.py`
- [x] T025 [US3] Thêm hành động “Sửa để AIOS học”, form phạm vi, preview và nối đúng message/trace metadata trong `src/aios_habit/workspace_memory_ui.py` và `src/aios_habit/workspace_chat_app.py`
- [x] T026 [US3] Chạy mục 5 của `specs/011-adaptive-work-memory/quickstart.md`, sửa lỗi trong phạm vi và ghi checkpoint US3 vào `docs/roadmap/backlog/AIOS-ADAPTIVE-WORK-MEMORY.md`

---

## Giai đoạn 6 — Kiểm chứng toàn Goal và bàn giao

**Mục tiêu**: Grok hoàn tất Execution một lần; Codex audit độc lập sau đó.

- [x] T027 [P] Mở rộng kiểm tra tiếng Việt cho UI memory và chạy test tương ứng trong `scripts/check_user_facing_vietnamese.py` và `tests/test_workspace_memory_ui.py`
- [x] T028 Chạy toàn bộ `specs/011-adaptive-work-memory/quickstart.md`, full quality gates, benchmark và `git diff --check`; ghi command/exit code/test count vào `docs/roadmap/backlog/AIOS-ADAPTIVE-WORK-MEMORY.md`
- [x] T029 Chạy `graphify update .` sau thay đổi code và ghi kết quả vào `docs/roadmap/backlog/AIOS-ADAPTIVE-WORK-MEMORY.md`
- [x] T030 Đồng bộ trạng thái `IMPLEMENTED_PENDING_INDEPENDENT_AUDIT`, kiến trúc, rollback và rủi ro trong `ARCHITECTURE.md`, `ROADMAP.md`, `PROJECT_HANDOVER.md`, rồi bàn giao đầy đủ cho Codex mà không tự tuyên bố PASS cuối
- [x] T030A Theo phản hồi người dùng, thêm lựa chọn “Cho AIOS ghi nhớ để hỗ trợ tôi tốt hơn” trong thanh bên Workspace Chat; lưu lựa chọn cục bộ qua lần mở sau, không yêu cầu lệnh PowerShell và không thêm database
- [ ] T031 Codex làm Audit Specialist độc lập, đọc diff/evidence, chạy lại test trọng điểm, kiểm tra privacy/persistence/prompt/rollback và ghi finding vào `docs/roadmap/backlog/AIOS-ADAPTIVE-WORK-MEMORY.md`
- [ ] T032 Chỉ khi T031 không còn finding mức chặn, Codex cập nhật trạng thái cuối đúng `PASS`, `PARTIAL`, `FAIL` hoặc `BLOCKED` trong `docs/roadmap/backlog/AIOS-ADAPTIVE-WORK-MEMORY.md`, `ROADMAP.md` và `PROJECT_HANDOVER.md`

## Phụ thuộc và đường chạy duy nhất

```text
baseline + kiểm tra nguồn tùy chọn
  -> flag
  -> US1 recall
  -> US2 remember/forget
  -> US3 correction
  -> full gates + cập nhật graph + bàn giao Codex
  -> Codex audit
  -> đóng Goal
```

- Grok chạy T001–T030 theo thứ tự; checkpoint không phải audit gate.
- Nếu bị gián đoạn, Grok đọc checkbox và evidence rồi tiếp tục từ task đầu tiên chưa hoàn tất; không làm lại task đã có bằng chứng.
- `[P]` chỉ cho biết task khác file; một Grok có thể làm tuần tự, không cần agent phụ.
- Không triển khai bàn giao phiên, vector search, GraphRAG, reranker, fine-tune, provider mới hoặc database mới.

## Tổng hợp

- Tổng: 33 task.
- Nền và cổng: 7 task.
- US1: 8 task.
- US2: 6 task.
- US3: 5 task.
- Kiểm chứng/bàn giao/audit: 7 task.
- Grok: T001–T030. Codex: T031–T032.
