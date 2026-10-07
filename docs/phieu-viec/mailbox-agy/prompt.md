# VÉ: BASELINE-USE-HOME (đo nền dùng thật trên máy nhà — đối tác của các vé hiệu năng máy công ty)

- Mã vé: `BASELINE-USE-HOME`
- Role gợi ý: DEFAULT (đo dùng thật, không code)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/baseline-use-home.md`

## Bối cảnh

User chốt hướng nghiệm thu bằng SỬ DỤNG THẬT (07/10) và chỉ đạo triển khai ngang các lỗi/phát hiện ở máy công ty sang máy nhà. Trên máy công ty đã phát hiện: mở sổ chờ mấy phút, các con số tài liệu mâu thuẫn (494/35/33), hỏi đáp chậm. Cần bộ số nền tương đương đo trên máy nhà (có GPU) để biết phần nào do máy, phần nào do code — làm mốc đối chiếu cho các vé `APP-SOURCE-MODEL-PC0575`, `APP-OPEN-PERF-PC0575` (code chung một nhánh, sửa xong áp cả hai máy).

## Việc phải làm (toàn bộ bằng dùng thật trên app đang chạy, tự động hoá thao tác)

1. Mở app trên máy nhà, đo thời gian mở sổ "Điều tra lỗi LSU": từ lúc bấm tới (a) thấy danh sách trò chuyện, (b) gõ được câu hỏi. Mở lạnh (app vừa khởi động) và mở lại (đã ấm), mỗi loại 2 lần.
2. Chụp màn hình sổ/trò chuyện: ghi lại mọi con số tài liệu app hiển thị (số tài liệu của sổ, đang bật, đã chuẩn bị...) để đối chiếu tính nhất quán với phía máy công ty.
3. Hỏi 3 câu kiểm ngay trong app, ghi đáp án + thời gian chờ từng câu:
   - "Mã C0030 là lỗi gì?" (đáp án đúng phải chứa: bất thường hệ thống bản mạch FAX)
   - "C7620中Magenta相对Black的副扫描色差达到多少会成为NG？" (phải nhắc ngưỡng 70 dot)
   - 1 câu tự chọn về lịch sử lỗi KDTPS (ghi rõ câu hỏi; đáp án phải nêu tên tệp nguồn cụ thể)
4. Ghi nhận mọi hiện tượng đơ/treo/chờ bất thường kèm thời gian và ngữ cảnh (máy lúc đó còn tiến trình nặng nào chạy song song không).

## Rào cứng

- Chỉ đo và ghi, KHÔNG sửa code, không ghi index, không đổi cấu hình app.
- Máy nhà đo không dùng GPU cho vé này ngoài những gì app tự dùng khi chạy bình thường (ghi rõ app đã dùng backend nào trong báo cáo).
- Không merge `main`.
