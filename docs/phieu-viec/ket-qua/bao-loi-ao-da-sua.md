# Danh sách báo lỗi ảo đã sửa

Ngày lập: 2026-10-03. Mục đích: để máy nhà đối chiếu lại từng case trên app thật.
Mỗi case ghi: hiện tượng → nguyên nhân → cách sửa → commit → cách kiểm lại.

## Case 1 — Radio giữ lựa chọn cũ, cổng LSU không đóng (đã sửa)

- Hiện tượng: mở cổng dữ liệu LSU bằng nút, sau đó bấm "Hỏi tài liệu" — cổng LSU
  vẫn mở, trạng thái điều hướng báo sai.
- Nguyên nhân: widget radio giữ `value` cũ trong `session_state` qua key
  `wsc_sidebar_nav_cluster`; bấm nhánh khác không có tác dụng vì giá trị đã
  được chọn sẵn.
- Cách sửa: bỏ key của radio điều hướng; trạng thái điều hướng được tính lại
  từ nav state thật mỗi lần render. Sau đó toàn bộ radio 3 nhánh bị loại bỏ,
  thay bằng router ý định trong câu chat.
- Commit: `928e242`.
- Kiểm lại trên app thật: trang không còn `st.radio(` điều hướng, không còn chữ
  "Điều hướng"; bấm các chức năng đều mở đúng cổng (OMP đã xác nhận ở
  `ux-chat-core.md` §2.1).

## Case 2 — Cảnh báo từ một điểm xấu đơn lẻ (đã sửa)

- Hiện tượng: một điểm dữ liệu xấu đơn lẻ cũng kích hoạt cảnh báo, gây báo động
  giả trong khi hệ thống vẫn ổn định.
- Nguyên nhân: luật cảnh báo chỉ so điểm mới nhất với ngưỡng cứng, không có
  cổng xu hướng.
- Cách sửa: cổng cảnh báo theo xu hướng + SMA(20) (`trend_alerts.py` /
  `threshold_alert_chat.py`): chỉ cảnh báo khi có xu hướng thật (≥3 điểm bất
  thường liên tiếp hoặc ≥3/5 điểm gần nhất lệch xa SMA(20) quá k·σ); một điểm
  đơn lẻ chỉ ghi "Cần quan sát", không cảnh báo.
- Commit: `846713e`.
- Kiểm lại trên app thật: chuỗi ổn định + 1 điểm xấu cuối → không cảnh báo;
  chuỗi `[70]*25 + [82, 84, 86, 88, 90]` → có cảnh báo kèm chữ SMA(20)
  (OMP đã xác nhận ở `ux-chat-core.md` §2.5).

## Case 3 — Đặt quy tắc cảnh báo khi chưa có dữ liệu lịch sử (không báo ảo)

- Hiện tượng: người dùng đặt "cảnh báo khi nhiệt độ vượt 80" trong khi thông số
  "nhiệt độ" chưa có lịch sử đo nào.
- Cách xử lý đúng (đã có): app lưu quy tắc `CB-...`, trả lời rõ "chưa có dữ liệu
  thông số này nên không đánh giá", tuyệt đối không tự bịa kết quả báo động.
- Commit: `9298ee6` (cảnh báo ngưỡng qua chat).
- Kiểm lại trên app thật: câu trả lời nói chưa có dữ liệu, không có cảnh báo giả
  (OMP đã xác nhận ở `ux-chat-core.md` §2.2, §2.5).

## Case 4 — Dán CSV thiếu matplotlib làm rơi cả bảng thống kê (đã sửa)

- Hiện tượng: máy chưa cài `matplotlib`, dán CSV để vẽ biểu đồ thì `ImportError`
  lan ra ngoài làm rơi toàn bộ khối phân tích — mất luôn bảng thống kê, người
  dùng không thấy gì và tưởng không có vấn đề.
- Nguyên nhân: `_draw_line_chart` import matplotlib trực tiếp, không có fallback;
  lỗi vẽ kéo theo cả outcome phân tích.
- Cách sửa: (1) thêm `matplotlib>=3.8.0` vào `dependencies` trong
  `pyproject.toml`; (2) tách `_draw_line_chart_matplotlib` và thêm fallback
  `_draw_line_chart_pillow` (máy nhà có sẵn Pillow); (3) wrapper
  `_draw_line_chart` không bao giờ ném lỗi ra ngoài; (4) điểm gọi trong
  `_analyze_csv_block` bọc thêm try/except — vẽ hỏng thì vẫn trả đủ bảng
  thống kê, cấm làm rơi cả khối phân tích.
- Commit: `c553b90` (vé UX-CHAT-CORE-FIX1).
- Kiểm lại trên app thật: dán CSV khi chưa cài matplotlib → vẫn thấy tóm tắt +
  bảng thống kê + biểu đồ (vẽ bằng Pillow).

## Case 5 — Một câu nhiều ý định chỉ chạy ý đầu, kết quả thiếu (đã sửa)

- Hiện tượng: câu "dán log + vẽ biểu đồ + cảnh báo khi nhiệt độ vượt 80" chỉ
  chạy ý cảnh báo ngưỡng rồi dừng; phần dán log / vẽ biểu đồ biến mất không
  một lời giải thích (dạng "báo thiếu").
- Nguyên nhân: router cũ `route()` chỉ trả một ý định duy nhất; hàm xử lý trả về
  ngay sau ý đầu.
- Cách sửa: `classify_all_intents()` tách tất cả ý định trong một câu (kể cả
  khối CSV/log dán kèm câu lệnh); `_xu_ly_y_dinh_chat` chạy hết các ý, gộp các
  đoạn trả lời thành một câu trả lời duy nhất có tiêu đề từng phần.
- Commit: `c553b90` (vé UX-CHAT-CORE-FIX1).
- Kiểm lại trên app thật: một câu gộp 3 ý → câu trả lời có đủ 3 phần
  (phân tích dữ liệu + biểu đồ + quy tắc cảnh báo đã lưu).

## Ghi chú cho OMP khi đối chiếu

- Chạy app bằng `RUN_AIOS_WORKSPACE_CHAT.bat` (đã bật sẵn cờ
  `AIOS_FEATURE_CHAT_ACTION=1` từ vé FIX1) để đường dán log/CSV hoạt động.
- Không dùng dữ liệu công ty thật cho case 4–5; dùng CSV/log giả lập.
- Case nào vẫn tái hiện trên app thật thì ghi lại hiện tượng + ảnh màn hình vào
  `docs/phieu-viec/ket-qua/`, đặt `trang-thai.md` mailbox máy nhà thành
  `cho-muse` để Muse xử lý tiếp.
