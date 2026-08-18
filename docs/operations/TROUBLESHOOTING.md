# Hướng Dẫn Khắc Phục Sự Cố (Troubleshooting Guide)

Status: `ACTIVE`
Owner role: Operator / maintainer
Last reviewed: 2026-08-16
Review cadence: After recurring failure or release candidate

## Quy tắc Chẩn đoán An toàn (Safe Diagnostic Rule)

Thu thập trạng thái, kết quả đầu ra của lệnh và phiên bản mà tuyệt đối không sao chép văn bản nguồn, API key, header Authorization, prompt thô, đường dẫn tệp cục bộ hay tệp JSONL runtime riêng tư vào kênh chia sẻ chung.

## Các Tình Huống Thường Gặp (Common Conditions)

| Triệu chứng | Kiểm tra an toàn | Hành động tiếp theo |
|---|---|---|
| Lỗi trình khởi chạy / phụ thuộc | Xác nhận phiên bản Python; chạy cài đặt editable; thu thập traceback đã làm sạch | Cài đặt lại / sửa môi trường, sau đó chạy import gate |
| `uv sync --group dev` báo lỗi truy cập (access denied) trong `.venv` | Xác nhận không có tiến trình Python/Streamlit nào của dự án đang chạy ngầm; lưu lại đường dẫn đã làm sạch và loại lỗi | Tuyệt đối không tự ý chiếm quyền sở hữu hay xóa mù môi trường; chỉ sửa/tạo lại khi có sự đồng ý của chủ sở hữu, sau đó sync lại |
| Workspace Chat không thấy sổ ghi chép / nguồn mong muốn | Xác nhận kho lưu trữ cục bộ tồn tại và chủ sở hữu đã chọn đúng sổ ghi chép / cuộc trò chuyện | Dừng lại trước khi ghi đè; kiểm tra trạng thái sao lưu |
| Workspace Chat ghi log bản ghi JSONL cục bộ không hợp lệ | Chỉ ghi lại tên tệp kho lưu trữ và số dòng | Giữ nguyên tệp gốc, khôi phục từ bản sao lưu của chủ sở hữu nếu cần, và không dán hàng bị từ chối vào kênh chung |
| Trích xuất nguồn dữ liệu thất bại | Xác nhận loại tệp / kích thước và thông điệp hiển thị cho chủ sở hữu | Giữ hoàn toàn cục bộ; không gửi tệp tới provider như một phương án dự phòng |
| Provider AI không khả dụng | Xác nhận cấu hình router / kết nối mạng mà không in API key | Sử dụng luồng chỉ dùng cục bộ (local-only); xử lý theo quy trình sự cố provider nếu cần |
| CLI audit báo lỗi | Đọc chính xác phát hiện của audit | Sửa nguồn / fixture / quy tắc ignore; không bao giờ tắt quét trên diện rộng |
| Tìm kiếm chỉ mục cục bộ trống / sai | Xác nhận đường dẫn chỉ mục đã chọn, số lượng chunk và các thuật ngữ truy vấn | Chỉ xây dựng lại (rebuild) nếu có sẵn đầu vào nguồn/chunk |
| Reranker subprocess timeout / OOM / lỗi tải mô hình | Kiểm tra `audit_deployment --check-adaptive`; kiểm tra checksum mô hình | Hệ thống tự động hạ cấp về Hybrid và mở Circuit Breaker sau 3 lỗi; sau khi khắc phục RAM/tệp, hệ thống tự phục hồi sau 30s cooldown |
| Git hiển thị tệp runtime riêng tư | Gỡ bỏ khỏi chỉ mục Git, giữ nguyên tệp của chủ sở hữu, cập nhật quy tắc ignore | Xử lý sự cố lộ dữ liệu đã push như một sự cố bảo mật |


## Quy trình Kiểm Chứng Chuẩn (Standard Validation)

```powershell
uv run --no-sync --group dev python scripts/check_docs.py
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
```

Nếu một lệnh thất bại, hãy lưu giữ và đọc kỹ toàn bộ thông báo lỗi trước khi thay đổi mã nguồn hoặc cấu hình. Xem [cổng chất lượng (Quality gates)](../quality/QUALITY_GATES.md).

## Leo Thang Xử Lý (Escalation)

Sử dụng [quy trình phản ứng sự cố](INCIDENT_RESPONSE.md) cho các tình huống nghi ngờ lộ quyền riêng tư/thông tin xác thực, mất dữ liệu hoặc lộ dữ liệu ra công cộng. Sử dụng sổ đăng ký rủi ro cho các lỗ hổng vận hành lặp lại nhưng không gây tác động trực tiếp.

