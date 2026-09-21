# Hướng dẫn kiểm chứng: Thanh nhập chat hiện đại

## Điều kiện trước

- Phụ thuộc dự án đã cài trong `.venv`.
- Mở Workspace Chat bằng `RUN_AIOS_WORKSPACE_CHAT.bat`.

## Kiểm tra tay

1. Mở một cuộc trò chuyện và xác nhận composer có ô nhập, nút đính kèm và nút gửi trong một vùng gọn.
2. Nhập câu hỏi nhiều dòng rồi gửi bằng nút gửi và Ctrl+Enter. Mỗi lần chỉ một lượt trả lời.
3. Mở đính kèm, chọn PNG hoặc JPG, gửi câu hỏi chỉ có ảnh. Luồng xử lý ảnh hiện có phải chạy.
4. Gửi composer trống, không ảnh, và xác nhận hướng dẫn hiện có xuất hiện.
5. Thu hẹp cửa sổ còn 360 px và xác nhận các điều khiển vẫn dùng được.

## Kiểm tra tay cho bản làm giàu nontech 2026-09-21

1. Mở cuộc trò chuyện mới và xác nhận ô nhập, nút đính kèm, nút gửi đều có nhãn tiếng Việt nhìn thấy được; nút đủ to để bấm.
2. Gửi composer trống và xác nhận hướng dẫn hiện ngay cạnh nút gửi.
3. Gửi câu hỏi khi tài liệu đang chuẩn bị, xác nhận nút gửi đổi thành nút dừng và bấm là hủy được.
4. Dán một dòng log JIG vượt ngưỡng vào Omnibar, xác nhận thẻ hiện kết luận Nguy cơ kèm tên JIG, thông số vi phạm và việc cần làm tiếp.
5. Mở biểu đồ trong thẻ, xác nhận điểm bất thường có hình và chữ kèm bảng số; bấm Tạm dừng thì dòng chat ngừng cập nhật.
6. Kích hoạt mail cảnh báo thử, xác nhận màn hình duyệt hiện trước và chỉ gửi khi đồng ý.

## Kiểm tra tự động

```powershell
uv run --no-sync --group dev pytest tests/test_workspace_chat_composer_ui.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_multi_file_uploader.py tests/test_workspace_chat_ui_i18n.py -q
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
```

Kỳ vọng: các test tập trung đều đạt, biên dịch sạch, module Workspace Chat nhập được.

## Smoke trình duyệt

Một lệnh, Chromium thật, không giả PASS:

```powershell
uv run --with playwright --no-sync python scripts/smoke_007_modern_chat_composer.py --headed
```

Hoặc `scripts/Chay_Smoke_007.bat`. Artifact ghi vào `local_runs/smoke_007/` (không commit). Sổ smoke không có tài liệu nên gửi câu hỏi hiện «Thiếu ngữ cảnh»; Streamlit có thể giữ text trong ô sau khi gửi. Dán ảnh clipboard cần thao tác người dùng.
