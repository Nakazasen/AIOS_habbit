# Vé: EXTERNAL-USAGE-LOG-TIMING-FIX-HOME — truyền số đo thời gian thật vào nhật ký sử dụng AI ngoài

- Thợ: agy (việc nhỏ, farm)
- Phát hành: điều phối Muse, 2026-10-12 ~03:1x +07, kèm verdict DESKTOP-EXTERNAL-AI-MODE-R2-HOME.
- Báo cáo: `docs/phieu-viec/ket-qua/external-usage-log-timing-fix-home.md`

## Bối cảnh (đã kiểm chứng tận mã tại commit `cc0eb75c`)
Nhật ký sử dụng chế độ Hỏi AI ngoài (`local_cases/workspace_chat/external_ai_usage.jsonl`) ghi hai trường `duration_sec` và `ttft_sec` luôn bằng 0.0. Gốc rễ đã xác định:
- Hàm `log_external_ai_usage` trong `src/aios_habit/workspace_chat_store.py` (dòng ~848) có hai tham số `duration_sec: float = 0.0, ttft_sec: float = 0.0`.
- Điểm gọi duy nhất trong `src/aios_habit/antigravity_bridge.py` (dòng ~1390-1394) chỉ truyền `conversation_id`, `message_id`, `model_name` — không truyền hai số đo.

## Việc phải làm
1. Tại điểm gọi trong `antigravity_bridge.py`, truyền số đo THẬT của chính lượt trả lời đó: thời gian tới ký tự đầu (TTFT) và tổng thời gian hoàn tất mà luồng streamer/router của lượt đã đo được. Rà trong cùng hàm/luồng để tìm biến mốc thời gian đã có sẵn (mốc bắt đầu lượt, mốc ký tự đầu, mốc hoàn tất); nếu một trong hai số chưa hề được đo ở đường này, đo bằng đồng hồ đơn điệu (monotonic) quanh đoạn xử lý của lượt tại điểm gần điểm gọi nhất mà không làm thay đổi hành vi trả lời. Cấm ghi số ước lượng hay số chép từ phiên khác.
2. Giữ nguyên định dạng bản ghi và các trường còn lại; không đổi chữ ký hàm ghi nhật ký trừ khi thật cần (ưu tiên chỉ sửa điểm gọi).
3. Test hồi quy: ca kiểm thử gọi đường external (hoặc điểm gọi) với số đo giả lập đã biết và khẳng định bản ghi ghi đúng hai số đó (khác 0); ca chứng minh khi không có số đo thì vẫn ghi 0.0 như cũ (không vỡ tương thích).
4. Đủ 4 cổng chất lượng của repo (compileall + pytest liên quan + cli audit + import app), tương thích Python 3.11.

## Nghiệm thu
- Điều phối rà diff tại commit: điểm gọi truyền đúng hai số đo lấy từ chính lượt chạy.
- Số thật trên tệp nhật ký thật sẽ được đối chiếu ở phiên Hỏi AI ngoài tiếp theo trên làn desktop (ghi nhận trong sổ cái khi có phiên đó) — vé này không cần tự chạy giao diện.
