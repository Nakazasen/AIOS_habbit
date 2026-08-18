# Tasks: Tìm kiếm thích ứng và chế độ Tìm kỹ

**Input**: Design documents from `/specs/003-adaptive-reranking-ux/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/adaptive-retrieval-routing.md`

**Tests**: Bắt buộc. Viết test thất bại trước implementation cho policy, IPC, UI, fallback, privacy và deployment compatibility.

**Rule**: Chỉ đánh dấu `[x]` sau khi task có bằng chứng chạy được. Không sửa, stage hoặc commit diff ngoài feature.

## Phase 1: Setup and frozen baseline

**Purpose**: Khóa trạng thái, dataset và baseline trước khi tuning.

- [x] T001 Ghi branch, `git status --short`, graph query, Python/dependency versions và danh sách diff ban đầu vào `specs/003-adaptive-reranking-ux/implementation-log.md`
- [x] T002 [P] Tạo tối thiểu 60 ca synthetic/non-private cân bằng `simple`, `hard`, `ambiguous`, `weak_evidence`, `multi_source`, `explicit_deep` cùng expected route trong `tests/fixtures/adaptive_routing_cases.json`
- [x] T003 [P] Định nghĩa schema report, policy version, dataset checksum và per-gate PASS/PARTIAL/FAIL trong `tests/fixtures/adaptive_reranking_report_schema.json`
- [x] T004 Đo lại Hybrid baseline cùng phiên trên máy tham chiếu và ghi summary đã làm sạch vào `specs/003-adaptive-reranking-ux/baseline-summary.md`, giữ raw artifact trong `local_runs/adaptive_reranking/`

**Checkpoint**: Dataset/labels/checksum và baseline đã khóa trước khi sửa ngưỡng.

---

## Phase 2: Foundational reranker capability

**Purpose**: Mở capability reranker trong cùng worker/index mà chưa thay đổi UX hoặc bật adaptive production.

**⚠️ CRITICAL**: Không bắt đầu user stories trước khi schema tương thích ngược và per-query capability hoạt động.

- [x] T005 [P] Viết test schema v2 tiếp tục load Hybrid-only và schema mới validate reranker path/revision/checksum/policy/benchmark trong `tests/test_workspace_chat_rag_v2_deployment.py`
- [x] T006 Mở rộng deployment dataclass/loader theo hướng tương thích ngược, adaptive mặc định false, trong `src/aios_habit/workspace_chat_rag_v2_deployment.py`
- [x] T007 [P] Viết test worker/client chấp nhận routing schema hợp lệ, từ chối schema/reason code không hợp lệ và không echo query/path trong `tests/test_bge_subprocess_client.py` và `tests/test_bge_subprocess_worker.py`
- [x] T008 Mở rộng query IPC với `rerank_requested`, safe reason codes, policy version và deep timeout trong `src/aios_habit/rag_v2/bge_subprocess_client.py` và `src/aios_habit/rag_v2/bge_subprocess_worker.py`
- [x] T009 [P] Viết test pipeline khởi tạo optional pinned reranker trong base Hybrid config mà không đổi index compatibility fingerprint trong `tests/test_rag_v2_pipeline.py`
- [x] T010 Thêm adaptive reranker config và query-time capability vào `src/aios_habit/rag_v2/pipeline.py`, giữ `bge_m3_hybrid` làm base identity và không tải model trong interactive query
- [x] T011 Truyền reranker artifact/policy từ deployment vào adapter config trong `src/aios_habit/workspace_chat_rag_v2_adapter.py` và cập nhật assertions trong `tests/test_workspace_chat_rag_v2_adapter.py`
- [x] T012 Chạy foundation tests và ghi lệnh/kết quả riêng vào `specs/003-adaptive-reranking-ux/implementation-log.md`


**Checkpoint**: Một worker có thể chạy per-query Hybrid hoặc Hybrid+Reranker; manifest cũ vẫn rollback được; adaptive vẫn tắt.

---

## Phase 3: User Story 1 - Tự chọn mức tìm kiếm phù hợp (Priority: P1) 🎯 MVP

**Goal**: Auto dùng cổng trước + cổng sau; chỉ giữ fast khi đủ chắc chắn, còn Deep/uncertain/weak evidence đều rerank.

**Independent Test**: Chạy fixture route; explicit Auto simple có thể fast, hard/uncertain/weak evidence phải deep; structured Excel không bị chuyển đường.

### Tests for User Story 1

- [x] T013 [P] [US1] Viết decision-table tests cho pre-gate, post-gate, vùng uncertain và chống kết quả all-fast/all-deep trong `tests/test_adaptive_retrieval.py`
- [x] T014 [P] [US1] Viết tests query-time `rerank_requested` dùng reranker scores và `False` không gọi backend trong `tests/test_rag_v2_pipeline.py`
- [x] T015 [P] [US1] Viết adapter tests cho pre-deep một lượt, fast Hybrid một lượt và post-insufficient nâng lên lượt rerank trong `tests/test_workspace_chat_rag_v2_adapter.py`
- [x] T016 [P] [US1] Bổ sung regression tests giữ structured Excel trước text routing trong `tests/test_workspace_chat_rag_v2_adapter.py`

### Implementation for User Story 1

- [x] T017 [US1] Tạo enums/dataclasses/versioned policy và pure pre/post gates với allow-listed reason codes trong `src/aios_habit/rag_v2/adaptive_retrieval.py`
- [x] T018 [US1] Cho `RagV2DevPipeline.query()` áp dụng reranker theo query và trả `reranker_requested/applied`, effective path, degraded state trong `src/aios_habit/rag_v2/pipeline.py`
- [x] T019 [US1] Thực hiện priority order `structured Excel → pre gate/user policy → Hybrid → post gate → optional rerank` trong `src/aios_habit/workspace_chat_rag_v2_adapter.py`
- [x] T020 [US1] Nếu post-gate cần lượt thứ hai, bảo toàn filters/source constraints và chỉ refactor candidate reuse trong `src/aios_habit/rag_v2/index.py` khi benchmark chứng minh cần thiết
- [x] T021 [US1] Chạy `tests/test_adaptive_retrieval.py`, pipeline/adapter focused tests và ghi confusion matrix sơ bộ vào `specs/003-adaptive-reranking-ux/implementation-log.md`


**Checkpoint**: Auto không phụ thuộc model sinh câu trả lời, không coi unknown là easy, và đạt independent route tests.

---

## Phase 4: User Story 2 - Người dùng chủ động Tìm kỹ hơn (Priority: P1)

**Goal**: Người dùng chọn `Tìm kỹ hơn`; lựa chọn giữ theo conversation và luôn thắng Auto.

**Independent Test**: Bật Deep rồi gửi câu đơn giản; telemetry phải requested deep và reranker applied hoặc explicit degraded. Đổi Auto thì câu sau trở lại policy.

### Tests for User Story 2

- [x] T022 [P] [US2] Viết backward-compatible model/store tests: record cũ mặc định `auto`, `deep` round-trip, invalid value fail-safe trong `tests/test_workspace_chat_store.py`
- [x] T023 [P] [US2] Viết UI flow tests cho selector, trạng thái hiển thị và persistence theo conversation trong `tests/test_workspace_chat_source_selection_owner_flow.py`
- [x] T024 [P] [US2] Viết copy tests đảm bảo UI dùng `Tự động`/`Tìm kỹ hơn` và không lộ profile/model trong `tests/test_workspace_chat_ui_copy.py`
- [x] T025 [P] [US2] Viết adapter test chứng minh `search_preference=deep` thắng một pre-gate `fast` giả lập trong `tests/test_workspace_chat_rag_v2_adapter.py`

### Implementation for User Story 2

- [x] T026 [US2] Thêm `search_preference="auto"` và validation tương thích ngược vào `src/aios_habit/workspace_chat_models.py` và `src/aios_habit/workspace_chat_store.py`
- [x] T027 [US2] Thêm selector `Tự động` / `Tìm kỹ hơn (có thể chậm hơn)` ở composer, lưu lựa chọn khi đổi và giữ trạng thái rõ trong `src/aios_habit/workspace_chat_app.py`
- [x] T028 [US2] Truyền conversation preference vào `retrieve_workspace_chat_evidence()` và đảm bảo `deep` bỏ qua mọi downgrade của Auto trong `src/aios_habit/workspace_chat_app.py` và `src/aios_habit/workspace_chat_rag_v2_adapter.py`
- [x] T029 [US2] Chạy store/UI/adapter focused tests và ghi evidence vào `specs/003-adaptive-reranking-ux/implementation-log.md`


**Checkpoint**: User override hoạt động độc lập cho cả câu dễ và khó; UI không yêu cầu kiến thức kỹ thuật.

---

## Phase 5: User Story 3 - Hạ cấp minh bạch và bảo vệ máy (Priority: P2)

**Goal**: Reranker lỗi/timeout/thiếu tài nguyên không treo app, không giả Deep success và không làm lộ dữ liệu.

**Independent Test**: Inject missing model, checksum mismatch, timeout, inference error và circuit-open; kết quả là explicit Hybrid degraded hoặc unavailable, copy đúng và không raw error.

### Tests for User Story 3

- [x] T030 [P] [US3] Viết pipeline/worker tests cho missing reranker, timeout, inference failure và no-reload-inside-query trong `tests/test_rag_v2_pipeline.py` và `tests/test_bge_subprocess_client.py`
- [x] T031 [P] [US3] Viết adapter invariants: false `Đã tìm kỹ` bị cấm, degraded reason allow-listed, Hybrid fallback giữ evidence trong `tests/test_workspace_chat_rag_v2_adapter.py`
- [x] T032 [P] [US3] Viết UI tests cho `Đang tìm kỹ`, `Đã tìm kỹ` và thông báo degraded tiếng Việt trong `tests/test_workspace_chat_source_selection_owner_flow.py` và `tests/test_workspace_chat_ui_copy.py`
- [x] T033 [P] [US3] Viết privacy regression scan cho telemetry/log payload không chứa query, snippet, title, absolute path, secret hoặc exception text trong `tests/test_workspace_chat_rag_v2_adapter.py`

### Implementation for User Story 3

- [x] T034 [US3] Thêm bounded deep timeout, one-worker lock, failure counter/cooldown circuit state vào `src/aios_habit/rag_v2/bge_subprocess_client.py` và `src/aios_habit/rag_v2/adaptive_retrieval.py`
- [x] T035 [US3] Thực hiện reranker-to-Hybrid degraded fallback và fail-closed khi Hybrid cũng lỗi trong `src/aios_habit/rag_v2/pipeline.py` và `src/aios_habit/workspace_chat_rag_v2_adapter.py`
- [x] T036 [US3] Render trạng thái chỉ từ `reranker_applied/degraded`, không suy đoán từ user choice, trong `src/aios_habit/workspace_chat_app.py`
- [x] T037 [US3] Chạy failure/privacy/UI focused tests và ghi từng lỗi giả lập cùng effective path vào `specs/003-adaptive-reranking-ux/implementation-log.md`


**Checkpoint**: Không silent fallback, không false assurance, không model reload trong request và không privacy regression.

---

## Phase 6: User Story 4 - Audit được và kích hoạt có gate (Priority: P3)

**Goal**: Có safe telemetry, benchmark chống bias, deployment evidence và rollback kiểm chứng được.

**Independent Test**: Một auditor đọc report có thể xác định requested/effective path, route distribution, quality, latency, memory, fallback và privacy mà không thấy nội dung người dùng.

### Tests for User Story 4

- [x] T038 [P] [US4] Viết report-schema/fixture checksum/confusion-matrix tests cho benchmark trong `tests/test_benchmark_adaptive_reranking.py`
- [x] T039 [P] [US4] Viết deployment activation tests chặn route accuracy/quality/latency/RAM/privacy/rollback failure trong `tests/test_workspace_chat_rag_v2_deployment.py`
- [x] T040 [P] [US4] Viết telemetry contract tests cho requested/effective path, reranker applied, reason codes và compatibility fields trong `tests/test_workspace_chat_rag_v2_adapter.py`

### Implementation for User Story 4

- [x] T041 [US4] Tạo benchmark CLI có route confusion matrix, Hybrid-vs-rerank quality, p50/p95, RSS/RAM, init count, fallback và privacy scan trong `scripts/benchmark_adaptive_reranking.py`
- [x] T042 [US4] Mở rộng safe telemetry theo contract trong `src/aios_habit/rag_v2/bge_subprocess_worker.py` và `src/aios_habit/workspace_chat_rag_v2_adapter.py`
- [x] T043 [US4] Mở rộng stage/activate/status/rollback để chỉ activate adaptive khi report sealed PASS trong `scripts/workspace_chat_rag_v2_activation.py` và `src/aios_habit/workspace_chat_rag_v2_deployment.py`
- [x] T044 [US4] Chạy benchmark frozen cho windows 10/20/30, chọn window nhỏ nhất đạt gate và ghi sanitized decision vào `specs/003-adaptive-reranking-ux/benchmark-decision.md`
- [x] T045 [US4] Tạo implementation evidence manifest gồm file diff, commands, exit codes, report digests và unresolved gates trong `specs/003-adaptive-reranking-ux/implementation-evidence.md`


**Checkpoint**: Report đủ để Terra audit độc lập; adaptive vẫn off nếu bất kỳ gate nào không PASS.

---

## Phase 7: Polish, documentation and release gates

**Purpose**: Đồng bộ tài liệu, graph, full test và handover; không nhập nhằng focused pass với full pass.

- [x] T046 [P] Cập nhật kiến trúc/sequence RAG trong `docs/architecture/COMPONENTS.md`, `docs/architecture/sequences/RETRIEVAL.md` và tài liệu canonical architecture hiện hành
- [x] T047 [P] Cập nhật vận hành/performance/troubleshooting trong `docs/OPERATOR_RUNBOOK.md`, `docs/operations/PERFORMANCE_CAPACITY_BASELINE.md` và `docs/operations/TROUBLESHOOTING.md`
- [x] T048 [P] Cập nhật test/UX acceptance và RAG design trong `docs/quality/TEST_STRATEGY.md`, `docs/quality/UX_ACCESSIBILITY_ACCEPTANCE.md` và `docs/rag_v2/RAG_V2_DESIGN.md`
- [x] T049 Cập nhật trạng thái thật, rollback và next action trong `ROADMAP.md` và `PROJECT_HANDOVER.md`; không ghi completed nếu còn gate pending
- [x] T050 Chạy focused suite trong `specs/003-adaptive-reranking-ux/quickstart.md`, `py -3 -m compileall src tests` và `git diff --check`; ghi từng kết quả vào `specs/003-adaptive-reranking-ux/implementation-evidence.md`
- [x] T051 Chạy `py -3 -m pytest -q`, CLI audit và Workspace Chat import smoke; ghi collection count, pass/fail/timeout riêng vào `specs/003-adaptive-reranking-ux/implementation-evidence.md`
- [x] T052 Diễn tập rollback về Hybrid-only manifest/flag, xác minh không rebuild index hoặc mất data, và ghi kết quả vào `specs/003-adaptive-reranking-ux/implementation-evidence.md`
- [x] T053 Chạy `graphify update . --no-cluster`, kiểm tra symbol/edges adaptive mới và ghi graph stats vào `specs/003-adaptive-reranking-ux/implementation-evidence.md`
- [x] T054 Đối chiếu toàn bộ FR/SC/tasks, để task chưa đạt ở `[ ]`, rồi bàn giao cho Terra bằng `specs/003-adaptive-reranking-ux/TERRA_AUDIT_PROMPT.md`


---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 khóa baseline/dataset trước mọi tuning.
- Phase 2 phụ thuộc Phase 1 và chặn tất cả user stories.
- US1 và US2 đều P1; thực hiện US1 trước để có route contract, sau đó US2 thêm quyền người dùng.
- US3 phụ thuộc effective telemetry từ US1/US2.
- US4 phụ thuộc cả ba story để benchmark/audit đầy đủ.
- Phase 7 chỉ bắt đầu khi scope triển khai mong muốn đã xong.

### User Story Dependencies

- **US1**: Foundation → pure policy → pipeline → adapter.
- **US2**: Foundation + adapter signature; model/store và UI tests có thể chuẩn bị song song với US1 policy.
- **US3**: Reranker per-query và UI status fields từ US1/US2.
- **US4**: Safe execution records từ US1-US3.

### Parallel Opportunities

- T002 và T003 khác file, có thể chạy song song.
- Trong từng story, test files khác nhau có thể viết song song trước implementation.
- T046-T048 là các nhóm docs khác nhau, có thể cập nhật song song sau khi behavior ổn định.
- Không chạy benchmark nặng song song với full pytest trên máy 16 GB; số liệu sẽ sai và có nguy cơ thiếu RAM.

## Parallel Example: User Story 1

```text
T013: policy decision-table tests in tests/test_adaptive_retrieval.py
T014: per-query pipeline tests in tests/test_rag_v2_pipeline.py
T015/T016: adapter and Excel regression tests in tests/test_workspace_chat_rag_v2_adapter.py
```

Sau khi các test trên tồn tại và fail đúng lý do, thực hiện tuần tự T017 → T018 → T019 → T020 → T021.

## Implementation Strategy

### MVP First

1. Phase 1 + Phase 2.
2. US1 Auto routing với policy conservative.
3. Dừng và chứng minh route tests/structured Excel regression.
4. Thêm US2 user Deep override trước khi gọi UX là hoàn chỉnh.

### Incremental Activation

1. Merge behavior dưới flag off.
2. Verify US1-US3 bằng focused tests.
3. Run US4 frozen benchmark một mình trên máy tham chiếu.
4. Update docs/graph/full gates.
5. Terra read-only audit.
6. Chỉ owner mới bật canary sau Terra PASS.

## Task Count and Format Validation

- Total: 54 tasks.
- Setup: 4; Foundation: 8; US1: 9; US2: 8; US3: 8; US4: 8; Polish/release: 9.
- All tasks use checkbox + sequential ID + optional `[P]` + required story label in story phases + exact file path.
- Suggested first demonstrable scope: Phase 1, Phase 2, US1 and US2. Production activation additionally requires US3, US4 and all release gates.
