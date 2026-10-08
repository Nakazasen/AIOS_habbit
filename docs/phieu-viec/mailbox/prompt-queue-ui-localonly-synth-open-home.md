# VÉ: UI-LOCALONLY-SYNTH-OPEN-HOME (mở cổng tổng hợp mô hình cho sổ LSU ở đường giao diện — theo quyết định của user)

- Mã vé: `UI-LOCALONLY-SYNTH-OPEN-HOME`
- Role gợi ý: DEFAULT
- Máy: nhà h410asrock (agy — thợ chính, CPU-only khi nghiệm thu)
- Báo cáo: `docs/phieu-viec/ket-qua/ui-localonly-synth-open-home.md`
- Căn cứ: verdict vé `CONFIG-SYNTH-TIERS-HOME` ghi nhận: hỏi qua giao diện trên sổ `mom_opcenter` (mang nhãn bảo mật `local_only`) bị cổng chặn cứng không cho gửi dữ liệu ra mô hình bên ngoài — mọi câu đều rơi về trích xuất cục bộ, chuỗi tổng hợp 3 tầng vừa áp không phát huy được trên chính sổ LSU. **User đã quyết lúc 2026-10-08 ~23:52 +07: "Mở cổng tổng hợp cho sổ LSU ở giao diện".** Vé này thực thi quyết định đó tại máy nhà.

## Việc phải làm

1. **Xác định cơ chế chặn hiện tại** trong code: điểm chặn ở cổng điều phối (hằng số/hành vi kiểu `LOCAL_ONLY_HARD_DENY`) và công tắc chính sách hiện có (biến cho phép tổng hợp qua nhà cung cấp bên ngoài — mặc định tắt, fail-closed, được tôn trọng ở nhiều lớp). Mở cổng **bằng đúng cơ chế công tắc hiện có**, không phá cơ chế nhãn dữ liệu, không sửa nhãn của tài liệu.
2. **Nêu rõ phạm vi mở thực tế** trong báo cáo: công tắc hiện có mở ở mức nào (toàn cục cho mọi tài liệu mang nhãn trên máy này, hay giới hạn được theo sổ/phiên). Làm đúng phạm vi user đã quyết: đường hỏi đáp qua giao diện trên máy nhà cho sổ LSU. Nếu cơ chế chỉ có mức toàn cục thì khai rõ hệ quả đó, không tự thu hẹp hay mở rộng thêm.
3. **Áp cấu hình mở cổng tại máy nhà** (ghi lại cấu hình trước khi đổi ở dạng không chứa khóa; nêu cách hoàn lui = tắt công tắc về mặc định).
4. **Nghiệm thu bằng dùng thật trên giao diện (CPU-only):** khởi động app, mở sổ `mom_opcenter`, hỏi lại 3 câu chuẩn (C7620/Q0699, DMT–PMT/Q0718, Skew/Q0709). Cổng đạt: cả 3 câu có **model phục vụ thật thuộc chuỗi 3 tầng** (bằng chứng provenance/log ghi tên nhà cung cấp + model — không còn rơi về trích cục bộ vì lý do chặn chính sách), đáp án trọn vẹn có trích dẫn, không rò rỉ prompt, không cắt cụt. Ảnh chụp chứa đáp án trọn trong khung + file kết quả có mã phiên riêng như các vé trước. Nếu có câu vẫn rơi về trích cục bộ vì lý do KHÁC (trượt kiểm định, thiếu bằng chứng) thì khai đúng lý do đó — phân biệt rõ "còn bị chặn chính sách" (không được còn) với "bị trượt kiểm định nội dung" (chấp nhận được, khai rõ).
5. Ghi trong báo cáo: điểm code/cấu hình đã đổi, phạm vi mở, cách hoàn lui, kết quả 3 câu kèm model phục vụ từng câu.

## Rào cứng

- Không ghi chỉ mục (kiểm băm SHA-256 trước/sau phiên nghiệm thu). Không merge `main`.
- Không in bất kỳ ký tự nào của khóa/API key trong báo cáo, log đính kèm hay commit.
- Chỉ mở cổng cho đường tổng hợp hỏi đáp; không thay đổi các chính sách dữ liệu khác, không gửi dữ liệu ra bất kỳ đích nào ngoài tuyến tổng hợp đã cấu hình.
- Mốc tiến độ tối thiểu 15 phút/lần. Kích thước file bằng chứng trong báo cáo phải lấy bằng lệnh liệt kê file thật, không gõ tay.
