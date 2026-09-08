# Hợp đồng danh tính, đồng ý và quyền riêng tư

## 1. Danh tính

`IdentityProvider.resolve_current_principal()` phải trả principal từ phiên đăng nhập/OS đã xác thực. UI/prompt không được truyền `expert_id` để thay đổi danh tính hiện tại.

```text
Principal -> ExpertProfile(active) -> ScopeGrant(action, scope, time) -> Allow
          mọi mắt xích thiếu/hết hạn/revoked                 -> Deny
```

### Điều kiện fail-closed

- Adapter không hoạt động hoặc không xác minh được principal.
- Hai profile cùng ánh xạ một subject.
- Profile suspended/revoked/hết hạn.
- Action hoặc scope không khớp chính xác.
- Grant hết hạn/revoked hoặc người cấp không hợp lệ.
- Principal của phiên khác principal hiện tại khi resume.

### Chế độ một người dùng

`local_admin` do app cấp vẫn được dùng cho luồng cũ. Khi feature flag multi-user bật, không được fallback về `local_admin` sau lỗi identity.

## 2. Consent ghi âm

Consent phải lưu:

- Ai đồng ý, thời điểm, phiên và mục đích.
- Loại dữ liệu: audio, transcript máy, transcript đã sửa.
- Nơi lưu, ai được xem, lịch giữ/xóa và có dùng cho đánh giá hay không.
- Phiên bản nội dung consent.

Trước `granted`, API record phải deny. Trong khi ghi phải có chỉ báo nhìn thấy. Khi `withdrawn`, dừng capture ngay; hành vi với dữ liệu đã có tuân policy đã duyệt và tạo receipt.

Từ chối ghi âm không được chặn chat văn bản.

## 3. Nhãn và tuyến dữ liệu

| Dữ liệu | Nhãn mặc định | Đích được phép |
|---|---|---|
| Audio thô | `local_only` | Vùng interview local đã cấu hình |
| Transcript máy | `local_only` | Vùng interview local đã cấu hình |
| Transcript đã sửa | `local_only` cho tới khi duyệt | Vùng local; chỉ claim/artifact trích xuất đi tiếp |
| Gap/plan metadata | Nội bộ có kiểm soát | `workspace_cases.sqlite` |
| Claim/artifact candidate | Nội bộ có kiểm soát | Workflow store, không retrieval thường |
| Artifact đã duyệt | Theo classification của nội dung | Publication package và collection được phép |
| Receipt/digest | Local metadata | Workflow DB/audit log đã làm sạch |

Không đặt đường dẫn tuyệt đối, raw transcript, token hay traceback vào UI/log thông thường.

## 4. Provider route

- Nếu prompt chứa `local_only`, chỉ local model khi owner đã cấu hình rõ; nếu không có route an toàn thì chặn.
- Với dữ liệu được phép qua provider, chỉ gửi đoạn tối thiểu cần thiết và ghi route receipt đã làm sạch.
- Không gửi audio thô cho Gemini trong bản đầu. Gemini nhận text đã được policy cho phép hoặc làm việc hoàn toàn với fixture ở giai đoạn dev.
- Không dùng conversation/transcript làm dữ liệu huấn luyện nếu consent không nói rõ mục đích đó.

## 5. Kiểm thử bắt buộc

- Mạo danh bằng prompt/form/header tùy ý.
- Grant đúng action nhưng sai scope; đúng scope nhưng hết hạn.
- Revoke giữa phiên và giữa approval/publish.
- Identity provider lỗi rồi thử fallback.
- Record trước consent, sau withdraw và khi UI indicator lỗi.
- Secret/raw transcript trong error/stdout/provider payload.
- Restart đọc lại consent đúng phiên bản và không tự chuyển `declined` thành `granted`.
