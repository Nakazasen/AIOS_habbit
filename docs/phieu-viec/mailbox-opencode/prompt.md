# Vé: AUDIT-ENRICH-MOM — Audit 608 cặp MOM (thợ opencode)

> Thợ opencode (máy nhà, chế độ 4 watcher song song). Model: free muse-spark-1.3 / space-bunny.
> Mailbox này: `docs/phieu-viec/mailbox-opencode/`. Báo cáo của thợ vào `docs/phieu-viec/ket-qua/`,
> cập nhật `trang-thai.md` của mailbox này (không đụng mailbox khác).
> Nguồn: `docs/phieu-viec/chatgpt-enrichment-raw/mom/` (15 file, 608 cặp).
> Đích: `docs/phieu-viec/chatgpt-enrichment-fixed/mom/` (cùng cấu trúc file).

## Rào cứng
- Chỉ sửa file trong `chatgpt-enrichment-fixed/`, không sửa thư mục raw.
- Mọi cặp giữ nhãn `MOM` + `Bản thảo — chưa qua chuyên gia duyệt`.
- TUYỆT ĐỐI KHÔNG nhập vào kho tri thức chính. Không merge `main`.

## Việc cần làm
1. **Sửa lỗi đã biết** (ghi nhận từ quá trình thu thập):
   - `batch-04.md` Q183 → Hỏi: `Spec Name và WorkCenter Name được dùng khác nhau thế nào?` / Đáp: `Spec Name dùng cho 着完工/Line-Out; WorkCenter Name dùng cho xuất kho manual.`
   - Q853, Q1034, Q1076 → trường `Cách hỏi` sửa thành `直接`.
   - Q1128, Q1131, Q1132, Q1136 → các trường bị diễn giải lại khi thu hồi, khôi phục nguyên văn từ nguồn ChatGPT.
   - Q1124 → đáp án bổ sung đủ số liệu còn thiếu.
2. **Kiểm tra numbering/format toàn bộ 15 file**: mỗi file đủ số cặp, Q liên tục không trùng/khuyết, đủ 6 trường (Khối/Ngôn ngữ/Bối cảnh/Cách hỏi/Hỏi/Đáp + Nguồn file).
3. **Dedup theo nội dung**: các chủ đề đã biết trùng — Matecon, AGV communication, ERD, ORICON_STATUS, manual truyền phiếu, map/version, thống kê màu, CamError một record. Giữ bản đầy đủ nhất, loại bản trùng, ghi log các cặp bị loại.
4. **Chấm M1–M5** bằng 6 module `src/aios_habit/golden_question_*.py` (scorer + quality). Cặp điểm thấp: sửa rồi chấm lại; không sửa được thì loại. Ghi metric trước/sau.
5. **Vòng xem lại**: sau khi sửa, chạy lại scorer một lượt nữa để xác nhận không còn cặp điểm thấp.

## Báo cáo
`docs/phieu-viec/ket-qua/audit-enrich-mom.md`: số cặp trước/sau, số cặp sửa, số cặp loại (+lý do), metric M1–M5 trước/sau, danh sách file đã fix. Commit lên `phieu-viec/rag-fix1`, `docs/phieu-viec/mailbox-opencode/trang-thai.md` → `xong-cho-duyet`.

## Quy ước watcher (bắt buộc)
- Nhận vé: đặt `trang-thai.md` thành `dang-lam` NGAY LẬP TỨC (commit + push), kèm `ghi_chu` có timestamp giờ máy.
- Mỗi mốc quan trọng: cập nhật `ghi_chu` + timestamp rồi push. `dang-lam` quá 20 phút không tiến triển = kẹt.
