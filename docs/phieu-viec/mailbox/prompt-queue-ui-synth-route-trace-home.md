# VÉ: UI-SYNTH-ROUTE-TRACE-HOME (truy vết đường tổng hợp thật của giao diện chat — chỉ đọc)

- Mã vé: `UI-SYNTH-ROUTE-TRACE-HOME`
- Role gợi ý: PLAN (truy vết kiến trúc, không code)
- Máy: nhà h410asrock (agy — thợ chính)
- Báo cáo: `docs/phieu-viec/ket-qua/ui-synth-route-trace-home.md`
- Căn cứ: vé `APP-E2E-POOL-HOME` (ĐẠT phần nghiệm thu, sản phẩm CHƯA ĐẠT): trên app thật, 3/3 câu LSU kết thúc "Dịch vụ AI chưa phản hồi" sau 475,59 / 315,11 / 174,94 giây — trong khi các lane đo bằng script sáng 08/10 qua pool Command Code chạy 50/50 câu bình thường. Điều phối đã kiểm sơ bộ trên VM và xác nhận có nhiều đường tổng hợp song song trong code:
  - `src/aios_habit/workspace_chat_router_adapter.py` dùng gói NGOÀI `nakazasen_ai_router.create_router_from_env()`; `workspace_chat_app.py` rẽ nhánh theo `selected_ai_backend == "nakazasen_router"` (UI hiển thị "Đang dùng: Nakazasen Router (ghim tay)").
  - `src/aios_habit/antigravity_bridge.py` chứa provider "Gemini Web Stream" / model `verified_gemini_stream` — đúng trường model mà file JSON kết quả của phiên E2E ghi lại, kèm lỗi timeout phía C-Agent >60s theo bản ghi phiên đo.
  - Đường `rag_v2` synthesis provider (đọc `AIOS_LOCAL_AI_ENDPOINT`/`AIOS_LOCAL_AI_API_KEY` từ `.env`) là đường các lane script dùng — chạy tốt với pool Command Code.

## Câu hỏi phải trả lời bằng bằng chứng code + log phiên thật (không suy luận)

1. **Bản đồ đường đi đầy đủ:** từ lúc user bấm gửi trong `workspace_chat_app.py` tới khi đáp án/lỗi hiện lên: hàm nào gọi hàm nào, backend nào được chọn theo điều kiện/cấu hình nào (ghim tay ở đâu, mặc định là gì, đổi được ở đâu). Liệt kê TẤT CẢ backend tổng hợp mà UI có thể rơi vào (router ngoài, antigravity bridge, rag_v2 provider, C-Agent...) và điều kiện kích hoạt từng đường.
2. **Gỡ mâu thuẫn MD ↔ JSON của vé E2E:** báo cáo MD nói model phục vụ `nakazasen_router` và lỗi do router ngoài dò key; JSON phiên đo ghi `verified_gemini_stream`/"Gemini Web Stream" + lỗi C-Agent >60s. Trong phiên đo thật đó, đường nào đã thực sự chạy cho từng câu? Dẫn log/bằng chứng cụ thể (log app, trường dữ liệu phiên, thứ tự fallback).
3. **Vì sao chờ 175–475 giây mới báo lỗi:** vòng lặp thử ứng viên/timeout nào tạo ra độ trễ đó (số ứng viên × timeout mỗi ứng viên)? Đường UI có cơ chế fallback trích cục bộ như đường lane script không — nếu không, vì sao?
4. **Pool Command Code ở đâu trong bản đồ:** cấu hình `.env` máy nhà hiện tại có được bất kỳ đường UI nào đọc không? Nếu muốn UI dùng đúng pool + fallback như lane script thì điểm nối là những file/hàm nào (chỉ chỉ ra, không sửa).
5. **Đề xuất vé sửa:** phạm vi tối thiểu để hợp nhất đường UI về một đường tổng hợp duy nhất đã kiểm chứng (pool + fallback trích cục bộ), kèm rủi ro và thứ tự việc.

## Rào cứng

- CHỈ ĐỌC + phân tích log/file kết quả có sẵn; không sửa code, không sửa `.env`, không chạy lại phiên đo dài (được chạy truy vấn ngắn ≤1 câu nếu cần xác minh log, phải ghi rõ).
- Mọi khẳng định trong báo cáo phải trỏ được vào file:dòng code hoặc dòng log cụ thể — phần nào không chứng minh được thì ghi "chưa xác minh", cấm lấp bằng suy luận.
- Không merge `main`.
