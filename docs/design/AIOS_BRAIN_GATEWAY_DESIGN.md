# AIOS Brain Gateway Design

## Mục tiêu

Brain Gateway là boundary duy nhất để AIOS:

1. nhận task và context/evidence đã được chọn cục bộ;
2. chuẩn hóa privacy và consent;
3. chọn một trong ba brain;
4. chặn transmission không an toàn trước khi gọi adapter;
5. trả kết quả cùng provenance/audit metadata;
6. tái sử dụng module hiện có thay vì tạo thêm đường AI song song.

Gateway thuộc AIOS vì AIOS sở hữu case, evidence, privacy, consent và product behavior. Nakazasen Router chỉ là dependency provider-routing. IDE agent chỉ là executor.

## Non-goals

- Không triển khai runtime trong A15.
- Không tự động gửi tài liệu công ty, raw evidence hoặc raw source tới cloud.
- Không thay Nakazasen Router bằng code mới trong AIOS.
- Không biến IDE agent thành memory store hay autonomous daemon.
- Không xóa hoặc sửa các AI module cũ, Studio, Case Cockpit.
- Không tuyên bố NotebookLM parity.
- Không quản lý API key trong repo.

## Ba loại brain

### Local Brain

Xử lý hoàn toàn trong trust boundary của máy/endpoint nội bộ đã được owner phê duyệt. Có thể dùng:

- Workspace local retrieval;
- deterministic/local answer composers;
- RAG evidence/citation;
- local OpenAI-compatible adapter khi endpoint được xác minh local/private;
- local manual review.

Local Brain là mặc định khi privacy không rõ, có dữ liệu nhạy cảm, router lỗi, hoặc owner không consent.

### Router Brain

Nhận **sanitized prompt** và safe metadata qua Router Adapter. Router chọn provider/model, fallback và health. Router không nhận case object, raw company document, raw evidence store, local path hoặc secret do AIOS quản lý.

### IDE Agent Brain

Nhận task pack có scope rõ để audit/implement/smoke/push-safety. IDE agent là executor có báo cáo, không phải memory store. Coding task có thể dùng bridge khi repo/task policy cho phép; dữ liệu confidential/local-only chỉ đi local/manual.

## Request/decision/result đề xuất

```text
BrainRequest
  request_id, task_type, language
  privacy_inputs[], owner_consent
  question_or_instruction
  local_evidence_refs[]
  requested_capabilities

BrainDecision
  selected_brain
  normalized_privacy
  external_allowed
  reason_code
  sanitized_payload_hash
  consent_receipt_id

BrainResult
  status, answer_or_report
  evidence_refs, model/tool metadata
  audit_event_id, warnings
  fallback_used
```

Raw evidence text chỉ tồn tại trong local preparation object. Nó không mặc định thuộc `BrainRequest` gửi adapter.

## Bảng quyết định routing

| Điều kiện | Local Brain | Router Brain | IDE Agent Brain | Quyết định mặc định |
|---|---:|---:|---:|---|
| `local_only` | Có | Không | Chỉ local/manual, không cloud | Local only |
| `confidential` | Có | Không | Chỉ local/manual | Local only |
| `unknown` hoặc thiếu metadata | Có | Không | Không external | Deny cloud |
| `machine_only` | Có | Chỉ khi owner consent rõ và policy nâng cấp thành payload sanitized được phép | Chỉ local/manual nếu chưa consent | Default deny cloud |
| `cloud_safe` | Có | Có thể | Có thể nếu task phù hợp | Policy/capability quyết định |
| `public` | Có | Có thể | Có thể | Policy/capability quyết định |
| `coding_task` | Có thể cho planning/local tools | Có thể chỉ cho text reasoning sanitized | Có thể dùng IDE Agent Bridge | IDE bridge nếu scope/consent hợp lệ |

Điều kiện được cộng dồn. Ví dụ `coding_task + confidential` không cho phép cloud IDE agent.

## Chuẩn hóa privacy và strictest-wins

Thứ tự nghiêm ngặt:

```text
confidential/local_only > unknown > machine_only > cloud_safe > public
```

- Thiếu privacy metadata: coi là `unknown`, deny cloud.
- Nguồn hỗn hợp: nhãn nghiêm ngặt nhất thắng toàn request.
- Legacy `cloud_allowed`: map tạm sang `cloud_safe` nhưng ghi `legacy_label=true`.
- Legacy `machine_only`: giữ nguyên, default deny; không map thẳng thành `cloud_safe`.
- Metadata-only source không có classification: `unknown`.

Không được “lọc bỏ nguồn nhạy cảm rồi âm thầm gửi phần còn lại” nếu câu hỏi/answer phụ thuộc nguồn đó. Gateway phải trả local fallback hoặc yêu cầu owner tạo một sanitized derivative rõ ràng.

## Quy tắc dữ liệu

- Không gửi raw evidence tới Router Brain.
- Không gửi raw company docs tới Router Brain.
- Cloud prompt phải được sanitize tại AIOS trước router boundary.
- Local evidence và index luôn ở local.
- Không gửi absolute path, case storage path, notebook ID nội bộ, key, token hoặc Authorization header.
- Raw source text chỉ có thể xuất external khi từng nguồn là `cloud_safe`/`public`, task policy cho phép và owner consent còn hiệu lực. Router adapter vẫn nhận một prompt đã đóng gói, không nhận evidence store.
- Sanitization phải fail-closed: không chứng minh được safe thì không gửi.

## Owner consent model

Consent là per-action, không phải checkbox vĩnh viễn:

- gắn với request ID, source-set fingerprint, privacy snapshot, destination class và thời hạn ngắn;
- thay đổi source, privacy, prompt scope hoặc destination làm consent hết hiệu lực;
- `machine_only` cần lời xác nhận external transmission rõ ràng; mặc định deny;
- `cloud_safe/public` vẫn cần product-level action rõ (ví dụ bấm “Hỏi AI”), nhưng không cần override privacy;
- consent không thể hợp thức hóa `local_only/confidential`.

Gateway lưu receipt metadata, không lưu raw content:

```text
consent_receipt_id, timestamp, action, destination_class,
source_set_hash, privacy_class, owner_confirmed
```

## Audit log

Mỗi decision phải ghi event append-only hoặc equivalent:

- request ID, timestamp, task type, language;
- normalized privacy và các legacy labels;
- selected brain, reason code, external allowed/sent;
- adapter/provider/model identifiers an toàn;
- source count và source-set hash, không raw title/path khi nhạy cảm;
- sanitized payload hash/length, sanitizer version;
- consent receipt ID;
- fallback/error class và testable status;
- result/report ID.

Không log raw prompt, raw response, evidence, API key, header hoặc company document. Raw answer chỉ lưu trong local case store theo privacy policy hiện hữu.

## Failure behavior

| Failure | Hành vi bắt buộc |
|---|---|
| Thiếu privacy metadata | Deny cloud, Local Brain hoặc explicit no-answer |
| Nguồn hỗn hợp | Strictest privacy wins |
| Sanitizer không xác nhận safe | Deny external |
| Consent thiếu/hết hạn/source-set đổi | Deny external, yêu cầu xác nhận lại |
| Router unavailable/timeout/all providers fail | Local fallback nếu có; nếu không, explicit no-answer |
| Local Brain unavailable | Không tự chuyển cloud; báo rõ |
| IDE report malformed/scope violation | Import `FAIL/REVIEW_REQUIRED`, không tạo verified memory |
| Audit sink unavailable | Deny external vì không thể tạo evidence của decision |

## Boundary flow

```text
Workspace Chat / Case / CLI
          |
          v
 Local retrieval + evidence selection
          |
          v
 Brain Gateway: normalize privacy -> consent -> sanitize -> decide -> audit
       /             |                    \
 Local Brain   Router Adapter       IDE Agent Bridge
       \             |                    /
          BrainResult + provenance
                    |
          Case / chat / draft learning card
```

## Kế hoạch migration

1. **Characterize**: khóa hành vi hiện tại bằng test cho Workspace Chat, `llm_client`, provider bridge, router, prompt/export và IDE handoff.
2. **Introduce disabled gateway**: interface và fake/local adapters; không đổi default runtime.
3. **Workspace Chat first**: thay direct `RealWorkspaceAIProviderClient` bằng gateway adapter, vẫn dùng local retrieval hiện tại.
4. **Router mock**: A16 thêm mock Router Adapter, default disabled, denial/leak tests.
5. **Legacy adapter**: bọc `ai_provider_bridge`/`ai_router` sau gateway để không làm hỏng Case Cockpit; không mở feature mới ở legacy UI.
6. **Prompt/export**: chuyển decision/consent/audit về gateway, giữ formatter cũ.
7. **IDE bridge**: A17 thêm task pack/report import; giữ answer handoff compatibility.
8. **Deprecation**: cảnh báo direct call site; dependency test cấm UI/domain import network client mới.
9. **Delete gate riêng**: chỉ xem xét phần router/client trùng lặp sau parity tests, zero usage và rollback plan.

## Tiêu chí thiết kế hoàn tất

- Một request external không thể đi vòng qua gateway trong flow chính.
- Unknown/mixed/local-only/confidential đều fail-closed.
- Router chỉ thấy sanitized prompt và safe metadata.
- IDE result không được tin chỉ vì ghi `PASS`.
- Module cũ được reuse qua adapter; không có bản sao logic AI thứ hai.
