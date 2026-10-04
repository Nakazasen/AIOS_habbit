# Ticket XẾP HÀNG: AUDIT-ENRICH-LSU — Audit 1.390 cặp LSU

> Role OMP gợi ý: DEFAULT. Chạy trên dữ liệu thật ở máy nhà.
> Nguồn: `docs/phieu-viec/chatgpt-enrichment-raw/lsu/` (30 file, 1.390 cặp, Q609–Q2008).
> Đích: `docs/phieu-viec/chatgpt-enrichment-fixed/lsu/` (cùng cấu trúc file).

## Rào cứng
- Chỉ sửa file trong `chatgpt-enrichment-fixed/`, không sửa thư mục raw.
- Mọi cặp giữ nhãn `LSU` + `Bản thảo — chưa qua chuyên gia duyệt`.
- Giá trị `999`/`9999`/`0`/`--` chỉ giữ là Raw value, không tự gán nghĩa OK/NG (đã đúng từ nguồn, kiểm tra lại không để lọt diễn giải sai).
- TUYỆT ĐỐI KHÔNG nhập vào kho tri thức chính. Không merge `main`.

## Việc cần làm
1. **Kiểm tra numbering/format toàn bộ 30 file**: mỗi file 50 cặp, Q liên tục (lưu ý Q639–648 bỏ trống có chủ đích vì `Thumbs.db`), đủ 6 trường + Nguồn file.
2. **Dedup mạnh theo nội dung** — các nhóm đã biết trùng nhiều:
   - ~30/50 cặp mẻ 39 lặp ý "Raw value 0" (Yellow/Magenta Profile toàn waveform 0);
   - các batch Sirius2 chỉ có `999`, `0` hoặc `--`;
   - các cặp hỏi cùng một record/ngưỡng chỉ khác cách diễn đạt.
   Giữ bản đầy đủ nhất, loại bản trùng, ghi log các cặp bị loại.
3. **Chấm M1–M5** bằng 6 module `src/aios_habit/golden_question_*.py`. Cặp điểm thấp: sửa rồi chấm lại; không sửa được thì loại. Ghi metric trước/sau.
4. **Vòng xem lại**: chạy lại scorer một lượt sau sửa để xác nhận không còn cặp điểm thấp.

## Báo cáo
`docs/phieu-viec/ket-qua/audit-enrich-lsu.md`: số cặp trước/sau, số cặp sửa, số cặp loại (+lý do), metric M1–M5 trước/sau, danh sách file đã fix. Commit lên `phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.
