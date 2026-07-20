# AIOS Router Adapter Design

## Ownership boundary

AIOS gọi Nakazasen AI Router như một dependency. Router không sở hữu:

- case/evidence/notebook của AIOS;
- privacy classification và owner consent;
- retrieval, citation hoặc answer acceptance;
- business fallback và memory promotion;
- quyết định một tài liệu có được rời máy hay không.

AIOS Brain Gateway phải hoàn tất privacy decision và sanitization trước khi gọi adapter. Router chỉ sở hữu provider/model selection, retry/fallback, health/cooldown và safe attempt metadata.

Integration bị tắt mặc định. A16 chỉ dùng mock adapter, không provider thật.

## Contract đề xuất

```python
class RouterAdapter(Protocol):
    def generate(self, request: SanitizedRouterRequest) -> RouterAdapterResult:
        ...
```

```text
SanitizedRouterRequest
  request_id: str
  sanitized_prompt: str
  task_type: str
  language: str
  allowed_model_tier: str
  privacy_class: cloud_safe | public
  sanitizer_version: str
  payload_sha256: str
  max_attempts: int

RouterAdapterResult
  status: success | unavailable | exhausted | denied
  answer_text: str
  provider_id: str
  model_id: str
  attempt_metadata[]
  fallback_used: bool
  safe_error_code: str
```

Không có các trường `case`, `evidence`, `source_path`, `raw_document`, `api_key` hoặc Authorization header trong public adapter request.

## Metadata được phép

- task type;
- language;
- allowed model tier;
- privacy class;
- request/correlation ID ngẫu nhiên;
- sanitizer version và hash/length payload;
- attempt budget/capability hints không nhạy cảm.

Không gửi raw source text trừ khi nội dung đã được phân loại rõ là `cloud_safe`/`public`, owner action cho phép, và nó đã trở thành một phần của **sanitized prompt**. Adapter không nhận raw evidence object ngay cả trong trường hợp đó.

## Sanitization contract

Sanitizer thuộc AIOS và phải:

1. nhận local prompt draft cùng privacy provenance;
2. fail nếu có nguồn `local_only`, `confidential`, `unknown`, hoặc `machine_only` chưa có consent hợp lệ;
3. loại absolute path, internal storage ID, key/token/header, raw company identifier bị policy cấm;
4. giới hạn kích thước và số đoạn;
5. chống prompt injection bằng cách phân tách instruction/context;
6. tạo `SanitizationReceipt`:

```text
sanitizer_version
input_privacy_class
output_privacy_class
source_set_hash
payload_sha256
payload_chars
removed_categories[]
owner_consent_receipt_id
```

Receipt không chứa raw text. Adapter từ chối request nếu receipt thiếu, hash không khớp hoặc privacy class không thuộc `{cloud_safe, public}`.

## Tích hợp Nakazasen Router

Repo router hiện cung cấp `AIRequest`, `AIRouter`, provider registry, fake providers, no-network default, fallback/health và safe trace. Adapter nên là anti-corruption layer trong AIOS:

- chuyển `SanitizedRouterRequest` thành API ổn định của router;
- không import provider implementation vào domain/UI;
- không cho router tự suy luận privacy từ prompt;
- map router result/error sang reason code AIOS;
- không persist raw prompt/response trong health cache;
- giữ router repo độc lập và không sửa từ A15.

Nếu dùng Python package/path dependency, version/commit phải pin rõ. Nếu sau này dùng process/HTTP boundary, cùng contract và denial rule vẫn áp dụng.

## Disabled-by-default và mock-first

- Feature flag mặc định `False`.
- Không đọc provider key khi flag tắt.
- Constructor mặc định dùng `DisabledRouterAdapter`.
- Test dùng `MockRouterAdapter`/fake provider, không network.
- Việc bật network cần owner-approved configuration ngoài repo và gate riêng.
- Không có secret, key file hoặc example key thật trong repo.

## Failure behavior

- Adapter disabled: trả `denied/adapter_disabled`; gateway dùng Local Brain hoặc no-answer.
- Privacy/receipt invalid: fail trước router call.
- Router unavailable/exhausted: trả safe error metadata; không tự gửi sang endpoint khác ngoài router policy đã cấu hình.
- Empty/malformed answer: không coi là success.
- Audit event không ghi được: gateway deny call.
- Không bao giờ fallback từ local-only sang cloud.

## Test strategy A16+

### Mock router

- success, timeout, quota, exhausted và empty response;
- chứng minh không có network/provider thật;
- feature flag off không instantiate live transport.

### Metadata assertions

- request chỉ có allow-listed fields;
- task type/language/model tier/privacy đúng;
- payload hash khớp;
- không có local path, case object hoặc secret.

### Privacy denial

- `local_only`, `confidential`, `unknown` luôn deny;
- `machine_only` deny mặc định và deny khi consent receipt không khớp;
- mixed sources dùng strictest-wins;
- `cloud_safe/public` mới có thể tới mock.

### Không leak raw evidence

- dùng sentinel trong raw evidence/company doc;
- sanitizer output và request object không chứa sentinel khi input không external-safe;
- mock adapter capture toàn request để assertion;
- audit/trace/error cũng không chứa sentinel;
- test lỗi sanitizer không được gọi adapter.

### Compatibility

- reuse đường Workspace Chat AI answer hiện có qua gateway;
- local retrieval/citation không đổi;
- local fallback và user-facing error vẫn rõ;
- không sửa Case Cockpit trong A16 nếu không cần.

## Tiêu chí ra khỏi mock

Chỉ xem xét live adapter khi:

- denial/leak tests pass;
- direct Workspace Chat network call đã nằm sau gateway;
- audit receipt có test;
- router dependency được pin và security gaps liên quan error sanitization được xử lý;
- owner phê duyệt config/network gate riêng.
