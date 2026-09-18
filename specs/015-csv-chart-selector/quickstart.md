# Hướng dẫn kiểm chứng nhanh: Chọn biểu đồ khi nhập tệp CSV LSU

**Ngày**: 18/09/2026 | **Tính năng**: `015-csv-chart-selector`

## Chuẩn bị

- Dùng Python 3.11 qua `uv`.
- Chỉ dùng dữ liệu mẫu đã làm sạch, không mở tệp thật trong thư mục `D:\Sandbox\Iris LSU` khi chạy kiểm thử tự động.

## Kịch bản 1 — Ô chọn gọn ở Thẻ 1

1. Mở màn hình kiểm tra dữ liệu LSU, tải tệp mẫu hợp lệ.
2. Chờ báo dữ liệu hợp lệ.
3. Chọn mã JIG, chọn chỉ số độ lệch hoặc độ nghiêng, chọn 1 trong 3 loại biểu đồ, chọn loại ảnh.
4. Bấm xem trước.
5. **Đạt khi**: ảnh hiện đúng JIG, đúng chỉ số, đúng loại; đổi lựa chọn thì ảnh cập nhật mà không tải lại tệp.

## Kịch bản 2 — Câu chat tự nhiên

1. Khi đã có gói hợp lệ, gõ câu tiếng Việt yêu cầu vẽ biểu đồ cho một mã JIG.
2. **Đạt khi**: hệ thống trả về cùng ảnh như ô chọn kèm câu giải thích tiếng Việt.
3. Gõ câu thiếu mã JIG.
4. **Đạt khi**: hệ thống hỏi lại đúng phần thiếu, không tự đoán.

## Kịch bản 3 — Tệp đo sâu không tiêu đề và tệp lỗi

1. Nhập tệp mẫu 3 cột không tiêu đề đúng mẫu thường gặp.
2. **Đạt khi**: hệ thống tự nhận diện và vẽ được, không bắt xuất lại.
3. Nhập tệp trống hoặc vượt giới hạn.
4. **Đạt khi**: nhận thông báo tiếng Việt có bước xử lý, không có câu tiếng Anh hay chi tiết kỹ thuật thô.

## Lệnh kiểm tra

```text
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q tests/test_csv_chart_selector.py tests/test_csv_chart_selector_ui.py
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
```

**Đạt khi**: biên dịch sạch, kiểm thử mới và cũ đạt, cổng audit báo `PASS`, nhập giao diện chính thành công.
