# Ticket hodap-lsu-loi — Thông luồng hỏi đáp LSU + lỗi trên chat (máy công ty)

## Bối cảnh
- App đang chạy LAN bình thường (P5/P5b ĐẠT, fix banner 0/494 ĐẠT).
- User (thợ máy công ty) báo: **chưa hỏi đáp được trên chat** — muốn hỏi đáp về LSU và về lỗi.
- Hiện trạng dữ liệu (theo vé dieutra-banner-0494): sổ "Điều tra lỗi LSU" có 494 notebook sources
  (262 document_id duy nhất), 0 nguồn đang bật, 0/262 có vector trong index đang chạy; ledger trống.

## Việc cần làm

### Pha 1 — Chẩn đoán (chỉ đọc, làm nhanh)
1. Xác định đúng luồng user dùng: chat trong sổ "Điều tra lỗi LSU" (workspace chat).
2. Kiểm tra: index production hiện chạy chứa tri thức gì (có LSU/lỗi không?);
   494 notebook sources ở trạng thái nào (có nội dung? enabled? vector?);
   thử hỏi 2–3 câu mẫu (1 câu LSU, 1 câu về lỗi) và ghi lại CHÍNH XÁC app trả lời gì /
   báo lỗi gì / có dùng nguồn nào không.
3. Kết luận nguyên nhân gốc: thiếu nguồn bật? thiếu vector? hay lỗi khác.

### Pha 2 — Thông luồng (làm theo kết quả Pha 1, OMP tự quyết kỹ thuật)
- Nếu nguyên nhân là nguồn chưa bật / chưa chuẩn bị: bật các nguồn LSU + lỗi cho cuộc
  trò chuyện rồi chạy chuẩn bị. Lưu ý máy CPU-only: ước tính thời gian trước khi chạy,
  chạy nền, không làm sập app đang phục vụ LAN.
- Nếu nguyên nhân khác: sửa đúng lỗi, không đoán mò, không sửa bừa.

## Tiêu chí ĐẠT
- Bộ câu hỏi mẫu (tối thiểu 3 câu LSU + 3 câu về lỗi) đều được trả lời **có căn cứ từ
  tài liệu** (báo cáo ghi rõ từng câu hỏi + đáp án + nguồn trích dẫn), không bịa đáp án.
- App vẫn phục vụ LAN bình thường sau khi xong.

## Cấm
- Không merge `main`. Không force-push.
- Không xóa nguồn/tài liệu nào khi chưa có lệnh user. (User từng bảo xóa vì tưởng trùng
  LSU máy nhà, nhưng vé này là làm cho hỏi đáp ĐƯỢC — nếu chẩn đoán thấy cần dọn thì ghi
  đề xuất vào báo cáo, không tự xóa.)
- Mọi ghi chép chỉ trong thư mục app `D:\Sandbox\AIOS_habbit` và báo cáo GitHub;
  không đụng ổ D máy nhà.

## Báo cáo
`docs/phieu-viec/ket-qua/hodap-lsu-loi.md`. Commit lên `phieu-viec/rag-fix1`,
`trang-thai.md` → `xong-cho-duyet`.

## BỔ SUNG KHẨN — 2026-09-30 14:40 +07 (theo lệnh user, chiến lược đổi)

1. **DỪNG NGAY worker nhúng CPU Phase 2.** Không nhúng tiếp trên PC0575.
   Lý do: chiến lược đã chốt — mọi vector hóa nặng chỉ chạy 1 lần trên máy nhà
   (có GPU), index dùng chung copy sang các máy công ty. Nhúng lại bằng CPU là
   trái ý muốn của user.
2. **Báo về 1 thông tin duy nhất:** `collection_id` mà sổ "Điều tra lỗi LSU"
   đang dùng (đọc từ notebook record; nếu rỗng thì ghi rõ "dùng mặc định tri_thuc").
   Thông tin này để vé máy nhà index đúng collection.
3. Giữ vé ở `dang-lam`. Sau khi index dùng chung từ máy nhà được copy sang,
   vé sẽ tiếp tục ở bước verify hỏi đáp (3 câu LSU + 3 câu lỗi).
