# Tham Chiếu CLI (CLI Reference)

Tất cả các lệnh đều có văn bản trợ giúp (`--help`).

- `aios-habit status`: Kiểm tra trạng thái hệ thống.
- `aios-habit discover --root [LOCAL_WORKSPACE] --dry-run`: Khám phá chỉ trích xuất metadata.
- `aios-habit evidence add/list/validate`: Quản lý con trỏ bằng chứng (evidence pointers), không lưu nội dung thô.
- `aios-habit memory add/list/validate/export`: Bộ nhớ đã xác thực (verified memory) bắt buộc phải có bằng chứng liên kết.
- `aios-habit extract`: Chỉ tạo các ứng viên để xem xét (review candidates); không tự động xác thực.
- `aios-habit workflow add/list/validate`: Quản lý quy trình làm việc.
- `aios-habit decision add/list/validate`: Quản lý nhật ký quyết định.
- `aios-habit profile build`: Chỉ sử dụng bộ nhớ đã xác thực / cho phép xuất.
- `aios-habit export --target generic|gpt|gemini|claude|grok`: Kiểm toán gói xuất trước khi sử dụng.
- `aios-habit audit`: Kiểm toán an toàn repository và tính toàn vẹn của bằng chứng.
- `aios-habit phase validate --phase N`: Kiểm chứng cổng giai đoạn N.
- `aios-habit handover build`: Xây dựng tài liệu bàn giao (handover).


