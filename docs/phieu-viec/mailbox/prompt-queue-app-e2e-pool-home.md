# VÉ: APP-E2E-POOL-HOME (nghiệm thu dùng thật ở máy nhà: hỏi đáp đầu-cuối qua pool Command Code trên app thật)

- Mã vé: `APP-E2E-POOL-HOME`
- Role gợi ý: DEFAULT (tự động hoá thao tác thật trên app + đo)
- Máy: nhà h410asrock (agy — thợ chính)
- Báo cáo: `docs/phieu-viec/ket-qua/app-e2e-pool-home.md`
- Căn cứ: nghiệm thu bằng SỬ DỤNG THẬT (user chốt 18:42 07/10) + vé `ROUTER-POOL-COMMANDCODE-HOME` đã đấu pool vào cấu hình máy nhà nhưng mới đo ở cấp lane script — vé này kiểm chứng trải nghiệm thật trên chính giao diện người dùng sẽ dùng.

## Việc phải làm

1. Mở app thật ở máy nhà (đường chạy như user mở hằng ngày), chờ app sẵn sàng; ghi thời gian mở app tới lúc gõ được câu hỏi.
2. Qua giao diện thật, hỏi lần lượt 3 câu LSU mẫu (lấy từ bộ đề 50 câu — 1 câu thực thể mã lỗi, 1 câu nguyên nhân, 1 câu thông số) trên kho production máy nhà, tuyến tổng hợp = pool Command Code theo `.env` hiện hành. Với mỗi câu ghi: thời gian chờ toàn trình (từ lúc gửi tới lúc đáp án hiện đủ), model thực phục vụ (nếu app/log cho biết), trích đáp án thật nguyên văn, ảnh chụp màn hình có đáp án.
3. Ghi riêng thời gian chờ câu đầu (gồm khởi động worker BGE — căn cứ vé BGE-WORKER-FIX: kỳ vọng còn ~4–5 phút) và hai câu sau (đã ấm).
4. Báo cáo: bảng số đo từng câu + ảnh + đáp án; nhận xét trung thực trải nghiệm (chỗ nào chờ lâu, chỗ nào khó dùng) — chỉ ghi nhận, không sửa code ở vé này.

## Rào cứng

- Chỉ dùng app + đo + chụp ảnh; không sửa code/config (trừ thao tác người dùng bình thường trong app); không ghi chỉ mục ngoài thao tác hỏi đáp thường (kiểm băm chỉ mục trước/sau nếu hỏi đáp có nguy cơ ghi).
- Đáp án và ảnh phải là của phiên chạy thật ghi trong báo cáo — cấm dùng lại ảnh/số của vé khác.
- Không merge `main`.
