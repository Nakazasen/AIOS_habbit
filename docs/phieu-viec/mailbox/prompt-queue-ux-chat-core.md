# Vé: UX-CHAT-CORE — chat nhiều ý định, biểu đồ trong chat, hết đổi luồng tay, hết báo lỗi ảo

Lane: [VM] Muse code+test trên VM → [NHÀ] OMP verify trên app thật (dữ liệu thật). Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh (user phản hồi 2026-10-02 ~22:00)

Trải nghiệm chat hiện tại rất tệ, 4 lỗi cụ thể user liệt kê:

1. Dán log/CSV vào ô chat chưa phân tích và vẽ biểu đồ được ngay trong câu trả lời.
2. Mỗi câu chat chỉ nhận 1 lệnh: khung chat quét theo thứ tự (dán log, nhập tệp, vẽ biểu đồ, đặt ngưỡng), gặp ý nào trước làm đúng ý đó rồi dừng — user phải tách nhỏ từng câu, rất phiền.
3. Phải đổi qua lại nhiều luồng (lane) bằng tay.
4. Báo lỗi ảo: báo lỗi nhưng thực tế không lỗi (hoặc lỗi đã tự khỏi).

## Việc Muse làm trên VM

1. **Intent đa ý định:** một câu chat có thể chứa nhiều ý định (ví dụ vừa dán log vừa yêu cầu vẽ biểu đồ và đặt ngưỡng) → tách tất cả ý định, thực hiện hết, trả lời gộp có cấu trúc trong một vùng trả lời. Không còn "gặp ý nào trước làm đúng ý đó rồi dừng".
2. **Nhúng log + sinh biểu đồ trong hỏi đáp:** dán log/CSV vào ô chat → phân tích + vẽ biểu đồ ngay trong câu trả lời, không bắt chuyển luồng/công cụ khác.
3. **Lane tự động:** hệ thống tự chọn lane phù hợp (C-Agent / Gemini / Router / cục bộ) theo tình huống và ghi nhớ lựa chọn; chỉ hỏi user khi thật sự mơ hồ. Không bắt đổi tay mỗi lần.
4. **Rà soát báo lỗi ảo:** liệt kê các chỗ báo lỗi nhưng không có lỗi thật; sửa thành chỉ báo khi chắc chắn, kèm nguyên nhân và cách xử lý bằng tiếng Việt, không lộ traceback thô.
5. Theo `AGENTS.md` 4.1: phần thay đổi hành vi UI công khai trình phương án cho user duyệt trước khi code (ghi phương án vào báo cáo vé, chờ user gật).

## Việc OMP verify [NHÀ]

- Chạy app thật: 1 câu nhiều ý định (dán log thật + vẽ biểu đồ + đặt ngưỡng) ra đủ 3 kết quả trong một câu trả lời; lane tự chọn đúng; các case báo lỗi ảo đã liệt kê không còn tái diễn.
- Báo cáo `docs/phieu-viec/ket-qua/ux-chat-core.md` + `xong-cho-duyet`.

## Tiêu chí ĐẠT

- Test đa ý định (2–3 ý định/câu) pass; test hồi quy 1 ý định/câu vẫn pass.
- `compileall` + `pytest` + `cli audit` PASS; không ghi index production.
- Commit riêng trên nhánh `phieu-viec/rag-fix1`, không đụng `main`.
