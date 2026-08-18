# Cổng Chất Lượng (Quality Gates)

Status: `ACTIVE`
Owner role: Maintainer / release reviewer
Last reviewed: 2026-08-16
Review cadence: Every Gate Card closure and release candidate

## Các Cổng Chất Lượng Cục Bộ Bắt Buộc (Required Local Gates)

```powershell
uv run --no-sync --group dev python scripts/check_docs.py
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
git diff --check
git diff --cached --check
git status --short --ignored
```

## Diễn Giải Ý Nghĩa Các Cổng (Gate Interpretation)

| Cổng | Bằng chứng | Hành động khi thất bại |
|---|---|---|
| Hợp đồng tài liệu (Doc contract) | Tài liệu bắt buộc, metadata và liên kết cục bộ | Sửa tài liệu / link; không bỏ qua kiểm tra |
| Biên dịch (Compile) | Biên dịch toàn bộ mã nguồn / kiểm thử Python | Đọc chính xác traceback; sửa nguyên nhân gốc rễ |
| Kiểm thử (Tests) | Hành vi thoái lui unit / integration | Thêm/sửa bài test hợp đồng; không xóa assertion |
| CLI audit | An toàn repository và tính toàn vẹn bằng chứng | Điều tra nguồn/fixture thay vì tắt quét |
| Import Workspace Chat | Khả năng bootstrap giao diện người dùng được hỗ trợ | Đọc lỗi import; bảo toàn trải nghiệm Tiếng Việt an toàn |
| Kiểm tra Git diff | An toàn về khoảng trắng (whitespace) và patch | Sửa diff trước khi review |
| Trạng thái Git | An toàn dữ liệu runtime riêng tư / thông tin xác thực | Gỡ bỏ khỏi chỉ mục; không xóa dữ liệu chủ sở hữu khi chưa có sự đồng ý |

## Tính Tương Đồng Với CI (CI Parity)

Quy trình CI cốt lõi bắt buộc phải chạy kiểm tra tài liệu, biên dịch, pytest, CLI audit và import Workspace Chat mà không cần thông tin xác thực provider. CI không được thực hiện các lệnh gọi AI trực tiếp hoặc tải lên dữ liệu runtime riêng tư. Quét cảnh báo lỗ hổng phụ thuộc vẫn mang tính khuyến cáo cho đến khi chủ sở hữu phê duyệt chính sách thực thi của chúng.

## Quy Tắc Hoàn Thành (Completion Rule)

Một Gate Card chỉ được chuyển sang trạng thái `DONE` sau khi toàn bộ bằng chứng lệnh hiện tại đạt (PASS) và phạm vi, hoàn tác cùng trạng thái roadmap/handover/changelog canonical đã được cập nhật.

Lệnh `pytest --collect-only` chỉ chứng minh rằng bộ test đã cấu hình có thể được phát hiện; nó không phải là bằng chứng cho thấy bộ test đã chạy đạt. Bắt buộc ghi nhận riêng biệt hai dữ kiện này trong Gate Card hoặc Handover.

