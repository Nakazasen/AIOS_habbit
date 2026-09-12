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
