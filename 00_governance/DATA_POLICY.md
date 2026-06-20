# Data Policy

## Local First

Mọi dữ liệu mặc định được lưu local. Không đồng bộ cloud nếu chưa có quyết định riêng.

## Data Classes

| Class | Description | Default Handling |
|---|---|---|
| Raw source | Chat transcript, email, logs, files gốc | Không commit, không đưa vào memory vault |
| Evidence record | Metadata/source reference/summary/hash | Có thể commit nếu không chứa nội dung nhạy cảm |
| Candidate memory | Memory chưa review | Có thể lưu trong extraction workspace |
| Validated memory | Memory đã review | Có thể lưu trong memory vault |
| Export pack | Profile chuyển cho AI khác | Có thể tạo từ master profile |
| Secrets | Token, key, credential | Không commit |

## Retention Rules

- Raw source chỉ giữ khi cần audit và phải nằm ngoài git hoặc trong vùng local-only.
- Evidence record giữ lâu dài nếu không vi phạm privacy.
- Deprecated memory không xóa ngay nếu đã được tham chiếu; đánh dấu deprecated và ghi lý do.

## Sensitive Data Rule

Không lưu thông tin nhạy cảm nếu không có yêu cầu rõ ràng và không cần cho mục tiêu memory platform.

## Evidence Without Raw Storage

Ưu tiên lưu:

- Hash.
- Path cục bộ.
- Short summary.
- Line reference nếu có.
- Artifact ID.

Tránh lưu:

- Toàn văn hội thoại.
- Toàn văn email.
- Dữ liệu nhận dạng không cần thiết.
