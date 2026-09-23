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

## Kiểm tra tay cho màn hình đáp án 2026-09-21

1. Mở hội thoại có sẵn một cặp hỏi đáp, xác nhận bong bóng hỏi và đáp khác màu/khung rõ rệt, đáp án mới nhất có dấu hiệu nhận biết.
2. Mở đáp án dài, xác nhận toàn bộ nội dung hiện đầy đủ, chữ không dàn full-width khó đọc.
3. Gửi câu hỏi và xác nhận 3 bước tìm nguồn, đọc trích đoạn, tổng hợp hiện theo đúng trạng thái chờ thật.
4. Mở đáp án có nhiều nguồn trích dẫn, xác nhận cụm gọn có đếm số lượng, khung chi tiết mặc định đóng.

## Kiểm tra tự động

```powershell
uv run --no-sync --group dev pytest tests/test_workspace_chat_composer_ui.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_multi_file_uploader.py tests/test_workspace_chat_ui_i18n.py tests/test_flowsint_evidence_atlas.py tests/test_streamlit_error_safety_config.py -q
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
```

Kỳ vọng: các test tập trung đều đạt, biên dịch sạch, module Workspace Chat nhập được.
Bằng chứng 2026-09-23: `135 passed` (21,73 s), `compileall` sạch, `IMPORT_OK`, `cli audit` `"status": "PASS"`.

## Smoke trình duyệt

Một lệnh, Chromium thật, không giả PASS:

```powershell
uv run --with playwright --no-sync python scripts/smoke_007_modern_chat_composer.py --headed
```

Hoặc `scripts/Chay_Smoke_007.bat`. Artifact ghi vào `local_runs/smoke_007/` (không commit).

### Mười hai kịch bản

| Kịch bản | Đo gì |
| --- | --- |
| S1 composer gọn | ô nhập, nút gửi, nút đính kèm, gợi ý `Ctrl+↵`, bộ chọn Mô hình AI |
| S2 hướng dẫn gửi rỗng | hướng dẫn hiện sau khi gửi trống |
| S3 bộ chọn Mô hình | ba lựa chọn Gemini Web / C-AGENT / Nakazasen |
| S4 gửi câu hỏi | nhánh chưa có nguồn hiện `Thiếu ngữ cảnh` |
| S5 đính kèm ảnh | chọn PNG, thumbnail, nút `Bỏ ảnh`, không traceback |
| S6 cửa sổ 360 px | ô nhập và nút gửi vẫn dùng được |
| S7 mặt sáng và điều hướng | `#F8FAFC` / `#020617`, chữ 16 px, không chữ từ mạng, `prefers-reduced-motion`, ba tên điều hướng tiếng Việt |
| S8 bong bóng và bề rộng dòng | hỏi khác đáp về nền và viền, huy hiệu `Câu trả lời mới nhất`, đoạn đáp ≤ 75ch, đáp án không cắt |
| S9 canvas đồ thị bằng chứng | nút `🕸️ Xem đồ thị bằng chứng`, canvas `.flowsint-layout`, SVG hiển thị, sidebar không phủ canvas, đủ nhóm thực thể, có bảng kiểm tra |
| S10 đóng đồ thị | canvas gỡ đi và nút mở trở lại |
| S11a giữ câu hỏi chờ nguồn | câu Việt `AIOS đang chuẩn bị tài liệu liên quan`, không phần trăm giả |
| S11b ba bước chờ | `Đang xử lý câu hỏi` với đúng một bước đang chạy theo trạng thái thật |

Kết quả 2026-09-23: **12/12 PASS** (`local_runs/smoke_007_t037/result.json`, không commit).

### Vì sao S8–S10 gieo dữ liệu trước

Vòng có trích dẫn cần một nhà cung cấp câu trả lời. Trên máy không chạy cầu nối Antigravity (`127.0.0.1:8585`), cả ba đường đều không tới được, nên smoke **gieo sẵn** một sổ, một hội thoại, một đáp án và một `EvidenceTrace` hợp lệ (`status=valid`, `cited_count=2`) vào kho cách ly trong thư mục tạm, rồi mở thẳng bằng `?nb=<sổ>&conv=<hội thoại>`. Nhờ vậy bong bóng, bề rộng dòng và canvas đồ thị được kiểm một cách tất định, không phụ thuộc mạng. Dữ liệu gieo chỉ nằm trong thư mục tạm và bị xóa cùng tiến trình.
