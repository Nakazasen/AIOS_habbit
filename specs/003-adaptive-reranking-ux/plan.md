# Implementation Plan: Tìm kiếm thích ứng và chế độ Tìm kỹ

**Branch**: `[003-adaptive-reranking-ux]` | **Date**: 2026-08-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-adaptive-reranking-ux/spec.md`

## Summary

Workspace Chat giữ `BGE-M3 Hybrid` làm đường cơ sở và chỉ thêm BGE reranker khi người dùng chọn `Tìm kỹ hơn`, câu hỏi có tín hiệu phức tạp, kết quả Hybrid đầu tiên chưa đủ chắc chắn, hoặc quyết định nằm trong vùng xám. Quyền chọn của người dùng luôn cao hơn bộ đánh giá tự động. Bộ đánh giá giai đoạn đầu là logic cục bộ, tất định và kiểm thử được; model sinh câu trả lời không được tự quyết một mình.

Triển khai tái sử dụng chỉ mục BGE-M3 hiện tại, thêm reranker cục bộ đã ghim phiên bản/checksum vào worker hiện có, truyền yêu cầu rerank theo từng câu hỏi, ghi telemetry đã làm sạch và bổ sung điều khiển `Tự động` / `Tìm kỹ hơn` tại composer. Kích hoạt bị chặn cho tới khi vượt qua benchmark chất lượng, độ trễ, RAM, privacy, rollback và audit độc lập.

## Technical Context

**Language/Version**: Python `>=3.11,<3.13`

**Primary Dependencies**: Streamlit; SQLite; BGE-M3/FlagEmbedding; PyTorch/Transformers trong extra `rag-semantic`; worker subprocess JSONL hiện có

**Storage**: JSONL cục bộ cho Workspace Chat; SQLite cục bộ cho chỉ mục RAG; manifest triển khai JSON cục bộ; không thêm dịch vụ dữ liệu ngoài

**Testing**: pytest; compileall; CLI audit; import smoke test; benchmark RAG v2 đóng băng; test UI bằng Streamlit test/mocking hiện có

**Target Platform**: Windows desktop/laptop, CPU i5, RAM 16 GB, không GPU rời; Python chạy local-first

**Project Type**: Ứng dụng Python/Streamlit một repository, có CLI, worker subprocess và thư viện RAG nội bộ

**Performance Goals**: Đường Hybrid p95 không tăng quá 10% so với baseline đo lại cùng phiên; đường Tìm kỹ ấm p95 `<=5.0s`; không OOM; RAM khả dụng còn ít nhất 2 GB trong benchmark chuẩn

**Constraints**: Không tải model trong request tương tác; không gửi nội dung ra mạng; một worker suy luận bị chặn; cửa sổ rerank mặc định thử nghiệm ở 10/20/30 và chỉ chọn mức nhỏ nhất đạt gate chất lượng; timeout/circuit breaker bắt buộc; hạ cấp phải hiển thị

**Scale/Scope**: Workspace Chat; một người dùng cục bộ; một worker BGE; ít nhất 60 ca định tuyến gắn nhãn; bộ benchmark khó đóng băng; không thay ingestion/chunking hoặc model sinh câu trả lời

## Constitution Check

*GATE: PASS before Phase 0 research; re-checked PASS after Phase 1 design.*

| Gate | Status | Evidence in this design |
|---|---|---|
| Evidence Before Assertion | PASS | Mỗi quyết định có reason code; activation cần report chất lượng/hiệu năng; không đạt ghi PARTIAL/FAIL, không tự nhận PASS. |
| Local-First Privacy and Consent | PASS | Router, Hybrid và reranker chạy local; telemetry không chứa query/source text/path; không thêm network call. |
| Portable, Pattern-Based Knowledge | PASS | Policy, contract, benchmark và report dùng Python/Markdown/JSON; không phụ thuộc provider sinh câu trả lời. |
| User-Centered Workspace Chat | PASS | UI tiếng Việt, không lộ mode kỹ thuật, có `Tự động` và `Tìm kỹ hơn`; không khôi phục UI đã nghỉ hưu. |
| Change Discipline and Verifiable Quality | PASS | Spec/plan/tasks/checklist trước code; có test, benchmark, Terra audit, docs canonical và graphify refresh. |
| Python/dependency constraints | PASS | Giữ Python 3.11-3.12; dùng dependency group hiện có; mọi thay đổi dependency qua `pyproject.toml` và `uv.lock`. |
| Privacy/rollback | PASS | Manifest tương thích ngược; feature flag local; rollback về Hybrid không rebuild index. |
| Graph-first investigation | PASS | Đã query `graphify-out/graph.json`; implementer phải query graph trước sửa và chạy `graphify update . --no-cluster` sau sửa. |

Không có ngoại lệ constitution cần biện minh.

## UX Decision

Giao diện không hiển thị `BGE-M3`, `Hybrid`, `reranker` hoặc tên profile ở luồng chính.

```text
Mức tìm kiếm
◉ Tự động
○ Tìm kỹ hơn (có thể chậm hơn)
```

- `Tự động`: hệ thống dùng hai cổng đánh giá và ưu tiên Tìm kỹ khi không chắc chắn.
- `Tìm kỹ hơn`: luôn yêu cầu reranker, kể cả câu hỏi đơn giản. Lựa chọn giữ trong cuộc hội thoại cho tới khi người dùng đổi lại.
- Trạng thái trong khi chạy: `Đang tìm trong nguồn...` hoặc `Đang tìm kỹ trong nguồn...`.
- Trạng thái hoàn tất chỉ dùng `Đã tìm kỹ` khi `reranker_applied=true`.
- Hạ cấp: `Đã tìm theo chế độ thường vì Tìm kỹ hiện chưa sẵn sàng.`
- Công cụ developer có thể hiển thị profile kỹ thuật; UI người dùng không hiển thị.

## Routing Algorithm

### 1. Quyền ưu tiên

```text
structured_excel_applicable → đường Excel hiện có
user_preference=deep        → Hybrid + Reranker
pre_gate=deep/uncertain     → Hybrid + Reranker
pre_gate=fast               → Hybrid → post gate
post_gate=insufficient      → Hybrid + Reranker
post_gate=sufficient        → giữ Hybrid
```

`user_preference=deep` không được đi qua logic hạ xuống `fast`. Nếu reranker không thực hiện được, kết quả phải là `degraded`, không phải `fast` thành công.

### 2. Cổng trước truy xuất

Tạo module thuần `src/aios_habit/rag_v2/adaptive_retrieval.py`. Cổng dùng `RetrievalQueryPlan` và metadata cấu trúc, không gọi model sinh câu trả lời và không xem nội dung tài liệu.

Tín hiệu nâng lên `deep`:

- `intent_category` thuộc nhóm nhiều nguồn, so sánh thay đổi, chẩn đoán, quy trình, truy vết nguồn hoặc đầu ra hành động;
- nhiều hơn một facet hoặc obligation bắt buộc;
- query expansion/faceting cho thấy nhiều mục tiêu;
- người dùng yêu cầu đầy đủ, kiểm chứng, đối chiếu, mâu thuẫn, nguồn/citation hoặc quan hệ theo thời gian qua intent planner đã kiểm thử;
- policy không có đủ bằng chứng để kết luận `fast`.

Không dùng độ dài câu hỏi hoặc từ khóa đơn lẻ làm bằng chứng đủ để chọn `fast`. Kết quả cổng là `fast`, `deep` hoặc `uncertain`; `uncertain` luôn ánh xạ sang Tìm kỹ.

### 3. Cổng sau Hybrid

Cổng sau đọc `SearchSummary`, không đọc raw source text. Nâng lên reranker khi có một trong các điều kiện:

- `insufficiency_reasons` không rỗng;
- có `missing_facet_ids` hoặc `missing_obligation_ids`;
- độ phủ tập bằng chứng dưới ngưỡng policy;
- số nguồn khác nhau không đạt yêu cầu của intent;
- ứng viên bị giới hạn đa dạng hoặc pool có dấu hiệu trùng lặp cao;
- top candidates quá sát nhau để coi thứ hạng là chắc chắn;
- candidate/returned count không đủ;
- chính sách đánh giá trả `uncertain`.

Ngưỡng là cấu hình versioned, không rải magic number trong adapter. Bộ test route phải chứng minh cổng không luôn trả `fast` và cũng không luôn trả `deep`.

### 4. Thực thi reranker

- Giữ `retrieval_profile="bge_m3_hybrid"` làm danh tính/index cơ sở.
- Thêm `adaptive_reranking_enabled` và cấu hình model reranker vào `RagV2DevConfig`/deployment.
- Worker tải model reranker trong bước khởi tạo/background preparation, không trong lần bấm gửi câu hỏi.
- `RagV2DevPipeline.query()` nhận lựa chọn theo query (`rerank_requested`) và chỉ truyền backend reranker vào `hybrid_search_with_summary()` khi cần.
- Query đã được cổng trước nâng cấp chạy một lượt Hybrid+Reranker.
- Query `fast` chạy Hybrid trước. Chỉ khi cổng sau thất bại mới chạy lượt Hybrid+Reranker thứ hai. Tối ưu tái sử dụng fused candidates là việc ưu tiên nếu benchmark 5 giây không đạt, nhưng không được thay đổi thứ hạng/assembly contract mà không có test.
- Reranker chỉ xếp hạng lại cửa sổ ứng viên có giới hạn; không làm tăng số nguồn được phép và không bỏ privacy/source filters.
- Lỗi reranker trả về Hybrid có telemetry `degraded=true`; lỗi Hybrid vẫn fail closed theo hành vi hiện tại.

## Implementation Phases

### Phase A - Baseline và khóa dữ liệu đánh giá

1. Ghi trạng thái git hiện tại và không trộn các diff ngoài feature.
2. Query graph cho adapter, pipeline, UI, deployment và test hubs.
3. Đo lại baseline Hybrid trên đúng máy i5/16 GB: warm p50/p95, peak process RSS, RAM khả dụng, Recall@10, MRR@10, source diversity.
4. Tạo bộ route fixture tối thiểu 60 câu không chứa dữ liệu riêng: simple, hard, ambiguous, weak-evidence, multi-source, explicit-deep.
5. Đóng băng corpus/câu hỏi/label/checksum trước khi tuning; giữ artifact runtime trong `local_runs/`.

**Exit gate**: baseline và dataset có checksum; không sửa policy sau khi xem kết quả cuối mà không tạo phiên bản benchmark mới.

### Phase B - Core policy thuần và contract

1. Tạo enums/dataclasses policy, pre-decision, sufficiency assessment và routing decision.
2. Viết pre-gate/post-gate thuần, reason codes allow-list, vùng `uncertain` bảo thủ.
3. Thêm unit tests theo bảng quyết định, gồm test chống bias `all-fast`/`all-deep` và test user override.
4. Không log query text trong module policy.

**Exit gate**: unit test policy pass; 100% explicit deep được route deep; 100% uncertain route deep.

### Phase C - Pipeline, worker và fallback

1. Mở cấu hình reranker cục bộ đã ghim path/revision/checksum trong deployment/config.
2. Cho pipeline giữ base index Hybrid nhưng nhận `rerank_requested` theo query.
3. Mở rộng JSONL IPC với `routing` object có schema kiểm tra chặt; response trả telemetry đã làm sạch.
4. Adapter xét Excel trước, sau đó user override/pre-gate, rồi post-gate.
5. Thêm timeout riêng cho query deep, một worker lock, cache model, circuit breaker sau lỗi tài nguyên lặp lại.
6. Nếu reranker lỗi, dùng Hybrid result an toàn và đánh dấu hạ cấp; không khởi động lại model trong request.

**Exit gate**: focused pipeline/adapter/worker tests pass, không có network call, không có hạ cấp im lặng.

### Phase D - UI và persistence tương thích ngược

1. Thêm `search_preference="auto"` vào `WorkspaceConversation`; loader cũ mặc định `auto`.
2. Thêm selector tiếng Việt ở composer, lưu theo conversation khi người dùng đổi.
3. Truyền preference vào adapter và hiển thị trạng thái đang chạy/hoàn tất/hạ cấp.
4. Chỉ hiển thị `Đã tìm kỹ` khi response xác nhận reranker đã áp dụng.
5. Thêm UI copy, persistence migration và owner-flow tests.

**Exit gate**: mở dữ liệu hội thoại cũ không lỗi; lựa chọn người dùng thắng Auto; UI không lộ profile kỹ thuật.

### Phase E - Deployment, benchmark và canary

1. Giữ manifest schema v2 hợp lệ ở trạng thái Hybrid-only; thêm schema mới cho adaptive reranking thay vì làm hỏng rollback cũ.
2. Manifest mới chứa artifact reranker, checksum, policy version, budget, benchmark evidence và feature state.
3. Benchmark cửa sổ rerank 10/20/30; chọn số nhỏ nhất đạt chất lượng. Không mặc định chọn 30 chỉ vì config hiện có là 30.
4. Gate chất lượng: hard set cải thiện >=5% MRR@10 hoặc metric chính đã đóng băng; Recall@10 giảm không quá 2%; route accuracy >=95%.
5. Gate hiệu năng: fast p95 regression <=10%; deep warm p95 <=5s; còn >=2 GB RAM; runtime init count=1; không OOM/hang.
6. Gate privacy/UX/rollback: 0 raw content trong telemetry, mọi fallback hiển thị, schema v2 rollback load được.
7. Canary tắt mặc định; chỉ bật sau Gemini report + Terra độc lập PASS.

**Exit gate**: tất cả gate PASS. Nếu bất kỳ gate nào không đạt, trạng thái là PARTIAL/BLOCKED và adaptive flag giữ tắt.

### Phase F - Documentation, handover và graph

1. Cập nhật `ARCHITECTURE.md` nếu tồn tại, nếu không cập nhật canonical architecture docs đang dùng; cập nhật `ROADMAP.md`, `PROJECT_HANDOVER.md`.
2. Cập nhật `docs/OPERATOR_RUNBOOK.md`, `docs/operations/PERFORMANCE_CAPACITY_BASELINE.md`, `docs/operations/TROUBLESHOOTING.md`, `docs/quality/TEST_STRATEGY.md`, `docs/quality/UX_ACCESSIBILITY_ACCEPTANCE.md` và tài liệu RAG v2 liên quan.
3. Ghi rollback: tắt adaptive flag, dùng schema v2/Hybrid manifest, restart app, xác minh effective path.
4. Chạy `graphify update . --no-cluster` và kiểm tra graph có symbol/edge mới.
5. Không đánh dấu roadmap hoàn tất nếu full suite, CLI audit, import smoke hoặc Terra audit chưa PASS.

## Files Expected to Change

```text
src/aios_habit/rag_v2/adaptive_retrieval.py              # new pure policy
src/aios_habit/rag_v2/pipeline.py                        # query-time rerank request
src/aios_habit/rag_v2/index.py                           # only if candidate reuse is required
src/aios_habit/rag_v2/bge_subprocess_client.py           # routing IPC + timeout
src/aios_habit/rag_v2/bge_subprocess_worker.py           # validate/forward routing
src/aios_habit/workspace_chat_rag_v2_adapter.py           # orchestration + safe telemetry
src/aios_habit/workspace_chat_rag_v2_deployment.py        # compatible manifest extension
src/aios_habit/workspace_chat_models.py                   # conversation preference
src/aios_habit/workspace_chat_store.py                    # backward-compatible persistence
src/aios_habit/workspace_chat_app.py                      # nontechnical selector/status
scripts/workspace_chat_rag_v2_activation.py               # stage/activate/rollback evidence
scripts/benchmark_adaptive_reranking.py                    # new frozen comparison harness
tests/fixtures/adaptive_routing_cases.json                 # synthetic labeled route set
tests/test_adaptive_retrieval.py                           # new policy tests
tests/test_rag_v2_pipeline.py                              # per-query rerank/fallback
tests/test_workspace_chat_rag_v2_adapter.py                # routing orchestration
tests/test_workspace_chat_rag_v2_deployment.py             # schema/rollback
tests/test_workspace_chat_source_selection_owner_flow.py   # UI owner flow
tests/test_workspace_chat_ui_copy.py                       # Vietnamese copy
docs/...                                                   # operations/quality/architecture
ROADMAP.md
PROJECT_HANDOVER.md
graphify-out/graph.json
```

`pyproject.toml`/`uv.lock` chỉ thay đổi nếu benchmark chứng minh extra hiện có không tải được BGE reranker; không thêm dependency trước khi có lỗi tái hiện.

## Validation Matrix

| Layer | Required evidence | Blocking condition |
|---|---|---|
| Policy | Decision table + 60 route cases + bias distribution | Explicit deep bị hạ; uncertain đi fast; accuracy <95% |
| Retrieval quality | Hybrid vs adaptive on frozen hard set | MRR gain <5% hoặc Recall regression >2% |
| Fast latency | Same-session Hybrid baseline vs Auto-fast | p95 regression >10% |
| Deep latency | Warm deep benchmark on reference machine | p95 >5s, init count !=1, timeout/hang |
| Memory | Peak process RSS + available system RAM | OOM hoặc available RAM <2 GB |
| Failure | Missing model, invalid checksum, timeout, inference error | Silent fallback or false `Đã tìm kỹ` |
| Privacy | Scan logs/reports/telemetry | Query/source text/path/secret appears |
| Persistence | Load old conversation JSONL | Error or non-auto default without user choice |
| Structured Excel | Existing focused tests | Excel route diverted to text reranker |
| Rollback | Adaptive off + old manifest | Index rebuild or data loss required |
| Full project | compileall, full pytest, CLI audit, import smoke | Any command nonzero or audit !=PASS |
| Architecture | graphify refresh and diff review | Graph stale or unrelated generated churn |

## Rollout and Rollback

1. Ship code with `adaptive_reranking_enabled=false`.
2. Stage local reranker artifact and validate checksum; do not download during chat.
3. Run frozen benchmark and create sanitized report.
4. Gemini marks implementation complete only if focused tests pass; full-suite status reported separately.
5. Terra audits read-only and returns PASS/PARTIAL/FAIL by gate.
6. Owner activates canary only after Terra PASS.
7. Rollback: set adaptive flag false or use the approved Hybrid-only manifest, restart Workspace Chat, verify `requested_retrieval_path=hybrid` and `reranker_applied=false`. Existing index remains compatible.

## Project Structure

### Documentation (this feature)

```text
specs/003-adaptive-reranking-ux/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── audit-plan.md
├── GEMINI_IMPLEMENTATION_PROMPT.md
├── TERRA_AUDIT_PROMPT.md
├── contracts/
│   └── adaptive-retrieval-routing.md
├── checklists/
│   ├── requirements.md
│   └── audit-requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/aios_habit/
├── rag_v2/
│   ├── adaptive_retrieval.py
│   ├── pipeline.py
│   ├── index.py
│   ├── bge_subprocess_client.py
│   └── bge_subprocess_worker.py
├── workspace_chat_app.py
├── workspace_chat_models.py
├── workspace_chat_store.py
├── workspace_chat_rag_v2_adapter.py
└── workspace_chat_rag_v2_deployment.py

scripts/
├── benchmark_adaptive_reranking.py
└── workspace_chat_rag_v2_activation.py

tests/
├── fixtures/adaptive_routing_cases.json
├── test_adaptive_retrieval.py
├── test_rag_v2_pipeline.py
├── test_workspace_chat_rag_v2_adapter.py
├── test_workspace_chat_rag_v2_deployment.py
├── test_workspace_chat_source_selection_owner_flow.py
└── test_workspace_chat_ui_copy.py
```

**Structure Decision**: Mở rộng các module RAG v2 và Workspace Chat hiện có; chỉ thêm một module policy thuần và một benchmark script. Không tạo service mới, database mới hoặc frontend riêng.

## Complexity Tracking

Không có vi phạm constitution. Phần phức tạp cần kiểm soát là hai lượt truy xuất ở trường hợp post-gate nâng cấp; nó được chấp nhận ban đầu để giữ logic rõ và rollback nhỏ, nhưng phải được tối ưu tái sử dụng candidates nếu gate p95 5 giây không đạt.
