# WORKSPACE_CHAT_PHASE2H_OWNER_SMOKE_GAP_TRIAGE

## 1. Kết luận

Audit date: `2026-07-04` (`Asia/Bangkok`).

Smoke status: `PASS_WITH_GAPS`.

Phase 2H có thể được xem là owner-smoke `PASS_WITH_GAPS`: luồng chính đã được owner kiểm tra đến trạng thái provider chưa cấu hình, source checker không giả làm câu trả lời AI, quick paste không tự gọi AI, và zero-source hiển thị đúng trạng thái thiếu ngữ cảnh. Ba khoảng trống mới không chứng minh regression của Phase 2H:

1. chưa có thao tác xóa sổ tài liệu;
2. owner chưa có cách gán privacy label bị chặn để tự smoke privacy block;
3. môi trường owner chưa cấu hình provider nên chưa smoke được câu trả lời thành công.

Khuyến nghị mở Phase 2I ở mức design gate. Không mở lại implementation Phase 2H và không cấu hình cloud/provider như một phần của audit này.

## 2. Baseline

| Check | Evidence |
|---|---|
| Repo | `D:\Sandbox\AIOS_habbit` |
| Branch | `main` |
| HEAD | `83713ee904c676776f1e62651ac6a12725b6e499` |
| `origin/main` | `83713ee904c676776f1e62651ac6a12725b6e499` |
| Latest commit | `83713ee Implement Workspace Chat Phase 2H answer clarity` |
| Tracking state | `## main...origin/main` |
| Worktree before audit | clean |
| Runtime paths before audit | clean |

## 3. Owner smoke evidence

Owner xác nhận PASS:

- mở Workspace Chat;
- tạo/mở sổ tài liệu;
- tạo/mở cuộc trò chuyện;
- bật một nguồn trong sổ;
- dùng `Dán nhanh nhiều nguồn` để thêm một nguồn tạm;
- xác nhận quick paste không tự gọi AI;
- bấm `Kiểm tra nguồn trước` và thấy `AI chưa trả lời`;
- gửi câu hỏi bằng `Hỏi AI với nguồn đang bật`;
- khi provider chưa cấu hình, UI hiển thị `Chưa gửi tới AI. AI chưa được cấu hình.`;
- đường dẫn không có nguồn hiển thị `Thiếu ngữ cảnh`.

Các kết quả này phù hợp với Phase 2H design: source check nằm ngoài chat answer, không gọi provider; zero/empty source không gọi provider; chỉ provider response thành công mới được lưu và hiển thị như assistant answer.

## 4. Đường dẫn chưa được owner test

Owner chưa test được provider success path:

- badge `AI đã trả lời`;
- summary `Nguồn gửi cùng câu hỏi: N`;
- assistant answer thật từ provider.

Nguyên nhân là môi trường owner không có cấu hình `AIOS_LLM_PROVIDER`. Đây là coverage gap của manual smoke, không phải bằng chứng rằng success path hỏng. Success/error behavior đã có automated coverage trong nhóm `tests/test_workspace_chat_ai_answer.py` và các structural/owner-flow tests, nhưng automated tests không thay thế hoàn toàn một smoke test với provider do owner phê duyệt.

## 5. Câu hỏi audit và bằng chứng

### 5.1 Provider chưa cấu hình có đúng và owner-safe không?

Kết luận: **Có**.

- `RealWorkspaceAIProviderClient.generate()` gọi `is_llm_configured()` trước network call.
- Nếu chưa cấu hình, client raise lỗi cấu hình trước khi gọi `complete_chat`.
- `generate_workspace_ai_answer()` chuyển lỗi này thành copy cố định `Chưa gửi tới AI. AI chưa được cấu hình.`
- UI không tạo assistant message, không gắn badge `AI đã trả lời`, và không hiển thị raw exception/provider payload.
- Provider chỉ được dựng sau khi đã qua zero/empty-source và privacy/consent gates.

Copy này trung thực: request chưa được gửi tới AI vì chưa có provider configuration. Nó cũng phù hợp với design gate: provider-unconfigured là trạng thái không có answer bubble.

### 5.2 Có cách owner-facing để cấu hình provider không?

Kết luận: **Không có trong Workspace Chat hiện tại**.

Repo có technical configuration path trong `src/aios_habit/llm_client.py`:

- `AIOS_LLM_PROVIDER`;
- `AIOS_LLM_BASE_URL`;
- `AIOS_LLM_API_KEY`;
- `AIOS_LLM_MODEL`;
- `AIOS_LLM_LOCALITY`;
- các biến timeout/maximum prompt tùy chọn.

Tuy nhiên, không có settings panel, guided owner flow, hay tài liệu Workspace Chat smoke setup được tìm thấy cho các biến này. Vì vậy không nên gọi đây là owner-facing configuration. Audit cũng không xác nhận một provider endpoint/model cụ thể là an toàn hoặc được owner phê duyệt.

Phân loại: Phase 2H follow-up **documentation/test-fixture decision**, không phải blocker buộc sửa production Phase 2H. Nếu owner muốn real-provider smoke, cần một task riêng để thiết kế hướng dẫn cấu hình local/dev có redaction, secret handling và explicit approval; không tự thêm key hoặc cloud config.

### 5.3 Có cách owner-facing để tạo nguồn privacy bị chặn không?

Kết luận: **Không**.

- `NotebookSource` và `TemporaryConversationSource` có trường `privacy_label`.
- Giá trị mặc định khi owner tạo/paste/upload trong Workspace Chat là `machine_only`.
- Backend cho phép cloud với `machine_only` và `cloud_allowed`; nó fail closed với `local_only`, `confidential`, blank, `None`, whitespace và unknown label.
- Source lists có thể hiển thị cảnh báo cho label bị chặn.
- UI hiện tại chỉ cho bật/tắt source; không có control gán hoặc đổi privacy label.

Do đó privacy block đã tồn tại và được automated-test kỹ, nhưng owner không thể tạo trạng thái đó bằng thao tác UI bình thường.

Phân loại: Phase 2I micro-design. Hướng phù hợp là owner-facing setting như `Nguồn chỉ kiểm tra trên máy / không gửi AI`, mặc định an toàn, có copy dễ hiểu và mapping chính xác sang label bị backend chặn. Một test fixture chỉ nên là lựa chọn dev/smoke tạm thời; không được làm yếu fail-closed rules.

### 5.4 Có chức năng xóa sổ tài liệu không?

Kết luận: **Không**.

- Notebook list có create và open.
- `workspace_chat_store.py` có `load_notebooks()` và `save_notebook()`, nhưng không có `delete_notebook()`.
- Store chỉ có delete cho **notebook source**, không phải notebook.
- Không có delete-notebook callback, button hoặc tests cho lifecycle xóa notebook.

Phân loại: Phase 2I notebook-management design gate, không phải Phase 2H hotfix. Xóa notebook có quan hệ dữ liệu với conversations, messages, temporary sources, notebook sources và source selections; cần quyết định archive hay hard delete, confirmation, default notebooks, active session state, partial failure và recovery trước khi viết code.

## 6. Gap triage

| Gap | Phase 2H blocker? | Risk nếu bỏ qua ngắn hạn | Khuyến nghị |
|---|---|---|---|
| Provider success chưa manual-smoke | Không; automated paths pass và unconfigured path fail-safe | Trung bình: còn thiếu end-to-end evidence trong owner environment | Follow-up doc/test plan; chỉ smoke với provider đã được owner phê duyệt |
| Không tạo được blocked source qua UI | Không phải regression, nhưng là privacy UX/testability gap | Trung bình: owner khó tự xác nhận guard quan trọng | Phase 2I privacy-source micro-design |
| Không xóa được notebook | Không liên quan mục tiêu answer clarity của Phase 2H | Thấp ngắn hạn; tăng dần khi notebook rác tích tụ | Phase 2I notebook lifecycle design gate |

## 7. Risk assessment

- **Privacy risk:** thấp trong code hiện tại vì backend fail closed và một blocked source chặn toàn bộ request. Rủi ro chính là testability/understandability, không phải guard bị thiếu.
- **Provider risk:** thấp khi chưa cấu hình vì không có network call. Rủi ro tăng cao nếu hướng dẫn owner đặt cloud key/endpoint mà không quy định locality, secret handling và dữ liệu smoke.
- **Data-loss risk:** cao nếu vội thêm hard delete notebook. Cascade không được định nghĩa; không được implement như một nút đơn giản.
- **UX risk:** trung bình. Owner thấy cảnh báo privacy nhưng chưa có control tạo/sửa trạng thái; notebook management thiếu lifecycle cleanup.
- **Scope risk:** cao nếu gộp provider setup, privacy model và cascade delete vào một microfix. Cần tách design/tasks.

## 8. Khuyến nghị Phase 2I

Mở Phase 2I với tên đề xuất: **Workspace Chat owner controls and safe lifecycle**.

Scope thiết kế đề xuất:

1. Privacy-source control:
   - control owner-facing `Chỉ dùng trên máy / không gửi AI`;
   - mapping rõ sang existing fail-closed privacy semantics;
   - source create/edit flows và copy cảnh báo;
   - automated UI plus backend regression tests;
   - không có partial send hoặc blanket consent.
2. Notebook lifecycle:
   - ưu tiên archive/hide hoặc soft-delete design trước hard delete;
   - dependency inventory và policy cho conversations/messages/sources/selections;
   - confirmation bằng notebook title và recovery story;
   - bảo vệ default/active notebook.
3. Provider smoke enablement là workstream riêng:
   - ghi tài liệu local/dev setup dựa trên existing environment variables;
   - không lưu secret vào repo/runtime fixtures;
   - dùng synthetic data;
   - phân biệt local endpoint và cloud endpoint;
   - không xây settings UI hay đổi router/network nếu chưa có design approval.

Phase 2H không cần implementation follow-up để được ghi nhận `PASS_WITH_GAPS`.

## 9. Exact proposed next Gemini/Codex tasks

### Task A — Design privacy-source owner control

`DESIGN_WORKSPACE_CHAT_PHASE2I_PRIVACY_SOURCE_CONTROL`

Audit existing source create/edit paths and propose the smallest owner-facing `Chỉ dùng trên máy / không gửi AI` control. Define exact mapping to existing privacy labels, defaults, copy, source-list states, consent interaction and tests. Preserve fail-closed validation, exact-source consent and all-or-nothing blocking. Design/audit only; do not implement provider, store schema or network changes.

### Task B — Design notebook lifecycle

`DESIGN_WORKSPACE_CHAT_PHASE2I_NOTEBOOK_LIFECYCLE`

Inventory all records owned by or referencing a notebook and compare archive/soft-delete/hard-delete options. Specify confirmation, active-session behavior, default-notebook policy, cascade/retention rules, recovery and tests. Recommend one safe MVP. Design only; do not delete data or implement code.

### Task C — Document approved provider smoke path

`AUDIT_WORKSPACE_CHAT_LOCAL_DEV_PROVIDER_SMOKE_PATH`

Audit the existing `AIOS_LLM_*` configuration contract and create a secret-safe, synthetic-data smoke procedure for an owner-approved local/dev provider. Verify provider-unconfigured remains no-send and define evidence for the success badge/source summary. Do not add keys, install services, configure cloud, modify provider/router/network, or run a real provider without explicit owner approval.

Recommended order: A, B, then C independently when the owner has selected an approved provider target.

## 10. Forbidden scope

- no implementation in this audit;
- no delete/archive function;
- no provider setup, key, endpoint or cloud configuration;
- no provider/router/network changes;
- no weakening privacy labels, exact-source consent or all-or-nothing block;
- no direct edits to runtime JSONL data to manufacture a smoke case;
- no store/model/schema migration;
- no RAG/vector/embedding/retrieval/citation;
- no OCR or new file formats;
- no Case Cockpit redesign;
- no changes to `.ai` or `local_cases`;
- no stage, commit or push.

## 11. Validation commands

```powershell
py -3 -m pytest tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_source_selection_ui_copy.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_answer_preview.py -q
py -3 -m pytest tests/test_workspace_chat_ai_answer.py -q
py -3 -m pytest -q
py -3 -m aios_habit.cli audit
git diff --check
git status --short
git status --short .ai local_cases task.md walkthrough.md implementation_plan.md
```

Expected interpretation:

- tests and CLI audit must pass;
- only this report may be untracked/dirty;
- runtime dirty check must remain empty.

