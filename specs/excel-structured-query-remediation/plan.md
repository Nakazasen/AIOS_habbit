# Kế Hoạch Triển Khai: Khắc Phục Lỗi Kiểm Toán 3 Truy Vấn Có Cấu Trúc Excel (Implementation Plan: Excel Structured Query Audit 3 Remediation)

## Các Thay Đổi Đề Xuất (Proposed Changes)

### `src/aios_habit/rag_v2/structured_query.py`

1. **Phát hiện tất cả các trang tính có giới hạn (Bounded all-sheets detection)**
   - Thêm hàm trợ giúp tập trung phát hiện cụm từ chuẩn tắc `tat ca` và token độc lập `all`.
   - Thay thế cả hai kiểm tra chuỗi con trong `plan_excel_query()` để các từ như `smallest` không thể kích hoạt `target_regions`.

2. **Các bản ghi nguồn gốc tổng hợp không mất mát (Lossless aggregate provenance records)**
   - Thay thế metadata tổng hợp được phân tách bằng dấu phẩy bằng một bản ghi nguồn gốc SQLite nội bộ:
     `sheet + ký-tự-phân-cách-trường + vùng-ô + ký-tự-phân-cách-trường + hàng`, được nối bởi ký tự phân cách bản ghi.
   - Sử dụng các ký tự phân cách điều khiển ASCII không thể xuất hiện trong tên sheet của Excel, sau đó phân tích cú pháp từng bản ghi thành `StructuredProvenance` riêng biệt của nó.
   - Bảo toàn các hàng và vùng chính xác cho từng sheet/vùng đóng góp, loại bỏ việc tái sử dụng danh sách hàng xuyên sheet trước đó.

### `src/aios_habit/workspace_chat_rag_v2_adapter.py`

- Không có thay đổi nào được mong đợi trên adapter sản xuất; giữ nguyên hành vi vị trí đa sheet bắt nguồn từ provenance của nó và bao phủ nó thông qua luồng tích hợp workbook được quản lý.

### Độ Bao Phủ Kiểm Thử & Vệ Sinh Mã Nguồn (Test Coverage & Hygiene)

#### `tests/test_rag_v2_structured_query.py`
- Thêm hồi quy cho `smallest Revenue` không khớp `all`.
- Thêm kiểm thử tổng hợp tên sheet hợp lệ có chứa dấu phẩy xác minh `East,West` vẫn là một sheet nguồn gốc duy nhất.

#### `tests/test_workspace_chat_rag_v2_adapter.py`
- Thêm độ bao phủ tích hợp đa sheet của workbook được quản lý xác minh `location_info == "Sheets: East, West"` và header được render đa vùng.

#### Vệ sinh tệp kiểm thử (Test file hygiene)
- Loại bỏ các dòng EOF trống thừa trong hai tệp kiểm thử đã được đánh dấu trước đó.

## Kế Hoạch Kiểm Chứng (Verification Plan)

```powershell
.venv\Scripts\python.exe -m py_compile `
  src/aios_habit/rag_v2/structured_query.py `
  src/aios_habit/workspace_chat_rag_v2_adapter.py

.venv\Scripts\python.exe -m pytest `
  tests/test_rag_v2_structured_query.py `
  tests/test_workspace_chat_rag_v2_adapter.py `
  tests/test_workspace_chat_ai_answer.py `
  tests/test_workspace_chat_multi_file_uploader.py -q

git diff --check -- tests/test_workspace_chat_multi_file_uploader.py tests/test_workspace_chat_rag_v2_adapter.py
graphify update .
```

### Các Thử Nghiệm Kiểm Toán (Audit Probes)
- `smallest Revenue` trên các schema `East`/`West` khớp nhau sẽ fail-soft như là mơ hồ, không bao giờ đặt `target_regions`.
- Tổng hợp trên `East,West` và `North` bảo tồn các sheet nguồn gốc chính xác dưới dạng `("East,West", "North")`.
- Luồng Managed Workbook phát ra vị trí trích dẫn đa sheet như kỳ vọng.

