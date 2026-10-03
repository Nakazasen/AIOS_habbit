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

## Phụ lục verify — đại tu vỏ chat V2 (Muse làm trên VM, commit 9298ee6, 2026-10-03)

Ngoài spec gốc, OMP kiểm thêm trên app thật (Streamlit máy nhà):

1. **Radio "Điều hướng" 3 nhánh đã biến mất.** Chỉ còn 1 ô chat + 1 vùng trả lời. Gõ thử các câu sau, chương trình tự điều phối đúng chỗ, không hỏi lại user đang ở nhánh nào:
   - "cảnh báo khi nhiệt độ vượt 80" → tạo quy tắc cảnh báo (không chui tab)
   - "tạo sổ BaoCaoTuan" / "mở sổ BaoCaoTuan" → sổ mở ra
   - câu hỏi tài liệu thường → trả lời RAG như cũ
2. **Sổ (notebook):** sidebar mỗi sổ chỉ hiện ĐÚNG 1 dòng "Sổ X — sẵn sàng, N tài liệu". Thoát app vào lại: không bắt "chuẩn bị tài liệu" lại, không còn text % khó hiểu.
3. **Cảnh báo ngưỡng qua chat:** đặt "cảnh báo khi X vượt Y" → quy tắc lưu được; kiểm tra ngay: 1 điểm xấu đơn lẻ KHÔNG báo, có xu hướng vượt ngưỡng mới báo (SMA20).
4. **Python 3.11:** chạy `py_compile` toàn bộ file mới/sửa trên Python 3.11 máy nhà trước khi đóng vé (VM chỉ có 3.12).
5. Chụp 2 ảnh màn hình: (a) giao diện chat sau khi bỏ radio, (b) dòng trạng thái sổ. Đính kèm báo cáo.

Rào: không đụng index production, không merge main, không gửi dữ liệu công ty ra ngoài.
