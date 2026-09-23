# Hướng dẫn Kiểm chứng: Dự phòng Tổng hợp Cục bộ có Trích dẫn

**Spec**: [spec.md](spec.md) mục R6 | **Kế hoạch**: [plan.md](plan.md) mục 9
**Hợp đồng**: [contracts/local-grounded-fallback.md](contracts/local-grounded-fallback.md)

## Điều kiện trước

- Phụ thuộc dự án đã cài trong `.venv` (Python 3.11).
- Có ít nhất một nguồn đã sẵn sàng trong sổ đang mở.
- **Cầu nối Antigravity không chạy** — đây chính là điều kiện kiểm thử. Kiểm bằng `curl http://127.0.0.1:8585/health` phải thất bại.

## Kiểm tra tay

1. Mở Workspace Chat, vào một sổ có nguồn đã sẵn sàng.
2. Hỏi một câu trả lời được từ nguồn đó (dùng đúng từ có trong tài liệu để truy xuất trúng).
3. Xác nhận màn hình hiện **lỗi cầu nối** kèm nút `Xem tổng hợp cục bộ từ trích đoạn`, và **chưa** có tin nhắn trả lời nào trong hội thoại.
4. Bấm nút. Xác nhận:
   - hội thoại có câu hỏi và một đáp án;
   - đáp án mang nhãn `Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình`;
   - **không** có nhãn `Antigravity IDE`, không có tên mô hình;
   - có danh sách trích dẫn kèm số lượng;
   - nút `🕸️ Xem đồ thị bằng chứng` hoạt động và mở được canvas ba cột.
5. Rút mạng và lặp lại bước 2–4. Kết quả không đổi — nhánh này không cần mạng.
6. Bấm nút khi không có nguồn nào đã sẵn sàng: chỉ hiện lỗi cầu nối, **không** hiện nút.

## Kiểm tra tự động

```powershell
uv run --no-sync --group dev pytest tests/test_antigravity_bridge.py tests/test_antigravity_handoff_ui_flow.py -q
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
```

Kỳ vọng: các kiểm thử hợp đồng dự phòng đạt, biên dịch sạch, module Workspace Chat nhập được.

## Kiểm tra hợp đồng cụ thể

```powershell
# Điều kiện mời: chỉ khi có căn cứ và chưa tự chối
uv run --no-sync --group dev pytest tests/test_antigravity_bridge.py -q -k "local_fallback_offered"

# Từ chối khi rỗng hoặc đã tự chối trả lời
uv run --no-sync --group dev pytest tests/test_antigravity_bridge.py -q -k "commit_refuses"

# Dấu vết hợp lệ => đồ thị dựng được
uv run --no-sync --group dev pytest tests/test_antigravity_handoff_ui_flow.py -q -k "commit_local_grounded"

# Không có lời gọi nhà cung cấp nào
uv run --no-sync --group dev pytest tests/test_antigravity_bridge.py -q -k "zero_provider_calls"
```

## Bằng chứng cần ghi khi đóng

- Số kiểm thử đạt và thời gian chạy, kèm mã thoát.
- `compileall`, `IMPORT_OK`, `cli audit` `"status": "PASS"`.
- Ảnh chụp màn hình ca 3, 4 và 6 (không commit; để trong `local_runs/`).
- Xác nhận `git status --short` không có đường dẫn riêng tư nào.
