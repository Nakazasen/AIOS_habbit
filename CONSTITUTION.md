# AIOS Habit Constitution

## 1. Sứ mệnh

AIOS Habit tồn tại để bảo toàn **tri thức vận hành cá nhân** của người dùng dưới dạng có thể kiểm định, có thể kế thừa và không phụ thuộc vào một AI cụ thể.

Nền tảng này giúp tái tạo cách người dùng làm việc trên nhiều hệ AI khác nhau bằng cách lưu giữ:

- Cách người dùng ưu tiên công việc.
- Cách người dùng ra quyết định.
- Cách người dùng giao tiếp.
- Cách người dùng tổ chức tri thức.
- Workflow lặp lại.
- Tri thức dự án đã được kiểm chứng.

## 2. AIOS Habit không phải là gì

AIOS Habit **không phải**:

- Công cụ backup ChatGPT.
- Kho lưu toàn bộ lịch sử chat.
- Công cụ sao chép tài khoản AI.
- Hệ thống giám sát người dùng.
- Nơi lưu suy đoán không có bằng chứng.

## 3. Nguyên tắc tối cao

### Principle 1: Không lưu hội thoại, lưu tri thức

Raw conversation chỉ là nguồn tạm để trích xuất. Memory cuối cùng phải là tri thức đã được phân loại, tóm tắt và gắn evidence.

### Principle 2: Không lưu câu chữ, lưu pattern

Hệ thống không tối ưu cho việc nhớ từng câu. Hệ thống tối ưu cho việc nhớ quy luật, sở thích, hành vi, workflow và tiêu chuẩn đánh giá.

### Principle 3: Không lưu suy đoán, chỉ lưu evidence

Mọi memory phải có ít nhất một evidence record. Nếu chưa có evidence, memory phải ở trạng thái `candidate` và không được dùng như sự thật.

### Principle 4: AI phải thay được, tri thức không được mất

Không định dạng dữ liệu theo riêng một AI. Mọi memory lõi phải dùng Markdown, JSON hoặc YAML mở, có schema rõ ràng.

### Principle 5: Local First

Dữ liệu gốc thuộc người dùng. Mặc định lưu cục bộ. Không đồng bộ ra cloud nếu chưa có chính sách rõ ràng.

## 4. Quy tắc bắt buộc khi phát triển

1. Audit trước khi fix.
2. Thiết kế trước khi code.
3. Phase hiện tại phải được đóng trước khi mở phase tiếp theo.
4. Mọi thay đổi kiến trúc phải cập nhật `ARCHITECTURE.md`.
5. Mọi thay đổi roadmap phải cập nhật `ROADMAP.md`.
6. Mọi thay đổi hành vi hệ thống phải cập nhật `PROJECT_HANDOVER.md`.
7. Mọi memory mới phải có evidence hoặc được đánh dấu `candidate`.
8. Không merge dữ liệu raw chưa được phân loại vào memory vault.
9. Không dùng AI output như evidence nếu không có nguồn gốc kèm theo.
10. Không tự ý kết luận khi chưa đủ dữ liệu.

## 5. Định nghĩa PASS/FAIL

Một hạng mục chỉ được đánh dấu `PASS` khi:

- Có evidence hoặc artifact cụ thể.
- Có người/AI reviewer xác nhận.
- Có rollback hoặc cách sửa nếu phát hiện sai.
- Có trạng thái được ghi lại trong changelog hoặc handover.

Nếu thiếu một trong các điều trên, trạng thái phải là `FAIL`, `BLOCKED` hoặc `PARTIAL`, không được ghi `PASS`.

## 6. Chính sách raw data

Raw chat transcript, email, log cá nhân, tài liệu nhạy cảm không được đưa vào memory vault trực tiếp.

Quy trình đúng:

```text
Raw Source -> Evidence Record -> Extracted Pattern -> Validated Memory -> Export Profile
```

## 7. Chính sách chống lock-in AI

Mọi output dài hạn phải tồn tại được ngoài ChatGPT, Gemini, Claude, Grok. Không được phụ thuộc vào:

- Internal memory của một AI.
- Proprietary prompt format không có bản Markdown tương đương.
- Conversation history không export được.

## 8. Thứ tự ưu tiên khi xung đột

1. An toàn dữ liệu người dùng.
2. Evidence và tính đúng đắn.
3. Khả năng kế thừa dài hạn.
4. Tính mở rộng.
5. Tốc độ triển khai.

Tốc độ không được vượt lên trên evidence hoặc an toàn dữ liệu.
