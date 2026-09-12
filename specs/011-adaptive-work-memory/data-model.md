# Mô hình dữ liệu: Vòng trí nhớ công việc thích nghi

## 1. `WorkspaceMemoryRecallRequest`

| Trường | Kiểu | Bắt buộc | Quy tắc |
|---|---|---:|---|
| `question` | chuỗi | Có | Sau trim phải còn nội dung; không ghi nguyên văn vào audit log. |
| `workspace_id` | chuỗi | Có | Dùng để giới hạn phạm vi. |
| `collection_id` | chuỗi | Có | Xác định thư viện hiện hành; không yêu cầu Goal 010 đã đóng. |
| `provider_mode` | enum | Có | `local` hoặc `cloud`. |
| `include_local_only` | bool | Có | Mặc định `False`; chỉ có ý nghĩa với local mode. |
| `limit` | số nguyên | Có | `1..5`, mặc định `5`. |
| `char_budget` | số nguyên | Có | `1..4000`, mặc định `4000`. |

## 2. `WorkspaceMemoryRecallItem`

| Trường | Kiểu | Quy tắc |
|---|---|---|
| `memory_key` | chuỗi | Ổn định theo `source_kind:source_id:version`. |
| `source_kind` | enum | `memory_unit`, `senior_learning_card`, `case_lesson`, `published_artifact`, `user_memory`. |
| `source_id` | chuỗi | ID gốc; không dùng đường dẫn máy. |
| `title` | chuỗi | Bắt buộc, được cắt theo budget. |
| `statement` | chuỗi | Nội dung ngắn để đưa vào prompt. |
| `applies_when` | chuỗi | Có thể rỗng; dùng khi score và giải thích. |
| `does_not_apply_when` | chuỗi | Có thể rỗng; match mạnh thì item bị loại. |
| `scope` | chuỗi | Phải khớp workspace/collection/general theo contract. |
| `status` | chuỗi chuẩn hóa | Chỉ `verified` hoặc `confirmed` mới được trả về. |
| `evidence_refs` | tuple chuỗi | Ít nhất một ref hợp lệ. |
| `privacy_classification` | enum | `local_only` hoặc `cloud_allowed`. |
| `export_allowed` | bool | Cloud mode yêu cầu `True`. |
| `updated_at` | ISO-8601 | Dùng tie-break, không tự quyết độ đúng. |
| `score` | số | Tính lại mỗi truy vấn, không persist. |
| `match_reasons` | tuple mã | Ví dụ `title_token`, `keyword_token`, `scope_exact`. |
| `conflict_group` | chuỗi tùy chọn | Có giá trị khi hai item không thể cùng là đúng. |

### Bất biến

- Không có item thiếu evidence.
- Không có item revoked/deprecated/rejected/candidate/draft.
- Cloud result không chứa `local_only` hoặc `export_allowed=False`.
- `statement` không được chứa delimiter đóng block prompt.

## 3. `WorkspaceMemoryRecallResult`

| Trường | Kiểu | Quy tắc |
|---|---|---|
| `items` | tuple item | Tối đa request limit và char budget. |
| `excluded_counts` | map reason→count | Metadata, không lộ nội dung bị loại. |
| `has_conflict` | bool | `True` nếu item trả về có conflict group. |
| `consent_fingerprint` | digest | Bao phủ ID, digest nội dung và privacy của item được gửi. |
| `trace` | `MemoryRecallTrace` | Chỉ metadata an toàn. |
| `fallback_reason` | chuỗi tùy chọn | Mã ổn định khi một nguồn lỗi hoặc service fallback. |

## 4. `MemoryDecision`

| Trường | Kiểu | Quy tắc |
|---|---|---|
| `decision_id` | chuỗi | ID duy nhất. |
| `memory_id` | chuỗi | ID logic ổn định qua các phiên bản. |
| `action` | enum | `confirm`, `forget`, `revoke`, `supersede`, `merge`. |
| `statement` | chuỗi | Chỉ bắt buộc với confirm/supersede; chính là nội dung người dùng xem trước. |
| `scope` | chuỗi | Không được rỗng. |
| `evidence_refs` | tuple chuỗi | Factual memory phải có; preference có ref xác nhận người dùng. |
| `content_digest` | digest | Chống trùng và xác minh nội dung. |
| `actor_label` | chuỗi | Tự khai để truy vết, không phải xác thực. |
| `created_at` | ISO-8601 | Tự động. |
| `supersedes_decision_id` | chuỗi tùy chọn | Bắt buộc khi replace/merge. |
| `privacy_classification` | enum | Mặc định `local_only`. |
| `export_allowed` | bool | Mặc định `False`; không tự bật. |

### Chuyển trạng thái logic

```text
không tồn tại -> confirm -> confirmed
confirmed -> supersede -> confirmed phiên bản mới
confirmed -> merge -> confirmed phiên bản hợp nhất
confirmed -> forget|revoke -> inactive
inactive -> confirm mới -> confirmed phiên bản mới, không xóa lịch sử cũ
```

## 5. `CorrectionLessonCandidate`

Ứng viên nằm trong session, không persist trước xác nhận.

| Trường | Kiểu | Quy tắc |
|---|---|---|
| `candidate_id` | chuỗi | ID tạm. |
| `statement` | chuỗi | Phần sửa do người dùng nhập/chỉnh. |
| `applies_when` | chuỗi | Bắt buộc trước xác nhận. |
| `does_not_apply_when` | chuỗi | Có thể rỗng. |
| `message_ref` | chuỗi | ID metadata; không chứa raw answer. |
| `trace_ref` | chuỗi tùy chọn | Dẫn tới evidence trace nếu hợp lệ. |
| `similar_memory_ids` | tuple chuỗi | Kết quả dò trùng/xung đột. |
| `status` | enum | `candidate`, `confirmed`, `cancelled`. |

## 6. `MemoryRecallTrace`

Chỉ lưu metadata: `trace_id`, timestamp, hash của câu hỏi, provider mode, source IDs được chọn, reason codes bị loại, score đã làm tròn, tổng ký tự và fingerprint. Cấm lưu question, statement, transcript, secret hoặc đường dẫn tuyệt đối.
