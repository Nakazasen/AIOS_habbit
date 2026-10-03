# Vé: UX-INTERVIEW-FEEDBACK — phỏng vấn chuyên gia chạy được + vòng phản hồi tự cải thiện

Lane: [VM] Muse code+test trên VM → [NHÀ] OMP verify trên app thật (dữ liệu thật). Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh (user phản hồi 2026-10-02 ~22:00)

- Luồng phỏng vấn chuyên gia hiện mới là khung (đang phải nhờ Copilot đóng vai tạm); user muốn chạy thật được trong app.
- Feedback hiện chưa gắn theo từng gợi ý/câu trả lời; chưa có vòng lặp tự cải thiện — user mô tả "vòng lặp phản hồi tự cải thiện" vẫn còn thiếu.

## Việc Muse làm trên VM

1. **Phiên phỏng vấn chuyên gia trong app:** từ knowledge gap → sinh câu hỏi vàng (tái dùng bộ sinh của vé `KNOWLEDGE-ENRICH-PILOT`) → hỏi theo phiên → ghi đáp án vào form nhân quả chuẩn → lưu staging chờ duyệt. Không ghi thẳng DB/index production.
2. **Feedback theo từng gợi ý/câu trả lời:** mỗi gợi ý trong câu trả lời có đánh giá riêng (đúng / sai / một phần). Chọn "sai" hoặc "một phần" bắt buộc nhập được: lý do, nguyên nhân thật, nội dung nắn lại — ngay trong câu trả lời, không chuyển màn hình.
3. **Vòng lặp tự cải thiện:** feedback sai/một phần được lưu thành bài học có truy vết (tình huống → lỗi → cách sửa); lần sau gặp tình huống tương tự thì không lặp lại lỗi cũ. Có bộ đo: tỉ lệ lặp lại lỗi sau feedback giảm dần theo thời gian.
4. Theo `AGENTS.md` 4.1: phương án UI trình user duyệt trước khi code (ghi vào báo cáo vé, chờ user gật).

## Việc OMP verify [NHÀ]

- Chạy thử 1 phiên phỏng vấn ngắn trên dữ liệu thật (1 hiện tượng lỗi thật), đáp án vào staging đúng schema.
- Feedback 1 gợi ý "một phần" kèm lý do + nguyên nhân thật + nội dung nắn lại; hỏi lại tình huống tương tự, kiểm tra không lặp lỗi cũ.
- Báo cáo `docs/phieu-viec/ket-qua/ux-interview-feedback.md` + `xong-cho-duyet`.

## Tiêu chí ĐẠT

- Phiên phỏng vấn chạy trọn vòng gap → câu hỏi → đáp án → staging trên dữ liệu thật.
- Feedback sai/một phần bắt buộc đủ 3 trường (lý do, nguyên nhân thật, nội dung nắn lại); thiếu thì từ chối lưu.
- `compileall` + `pytest` + `cli audit` PASS; DB chính và index production không đổi.
- Commit riêng trên nhánh `phieu-viec/rag-fix1`, không đụng `main`.
