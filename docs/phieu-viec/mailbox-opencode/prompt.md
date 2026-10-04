# Ticket: AUDIT-ENRICH-LSU — Audit 1.790 cặp LSU (chuyển từ hàng chờ OMP sang opencode 22:45)

> opencode đã làm tốt vé AUDIT-ENRICH-MOM (verdict ĐẠT) nên nhận tiếp vé audit LSU.
> Nguồn: `docs/phieu-viec/chatgpt-enrichment-raw/lsu/` (54 file batch-01..54, 1.790 cặp, Q609–Q2408).
> Đích: `docs/phieu-viec/chatgpt-enrichment-fixed/lsu/` (cùng cấu trúc file).

## Rào cứng
- Chỉ sửa file trong `chatgpt-enrichment-fixed/`, không sửa thư mục raw.
- Mọi cặp giữ nhãn `LSU` + `Bản thảo — chưa qua chuyên gia duyệt`.
- Giá trị `999`/`9999`/`0`/`--` chỉ giữ là Raw value, không tự gán nghĩa OK/NG (đã đúng từ nguồn, kiểm tra lại không để lọt diễn giải sai).
- TUYỆT ĐỐI KHÔNG nhập vào kho tri thức chính. Không merge `main`.

## Việc cần làm
1. **Kiểm tra numbering/format toàn bộ 54 file**: Q liên tục từ Q609 đến Q2408 (lưu ý Q639–648 bỏ trống có chủ đích vì `Thumbs.db`), đủ 6 trường + Nguồn file mỗi cặp.
2. **Dedup mạnh theo nội dung** — các nhóm đã biết trùng nhiều:
   - ~30/50 cặp mẻ 39 lặp ý "Raw value 0" (Yellow/Magenta Profile toàn waveform 0);
   - các batch Sirius2 chỉ có `999`, `0` hoặc `--`;
   - các cặp hỏi cùng một record/ngưỡng chỉ khác cách diễn đạt.
   Giữ bản đầy đủ nhất, loại bản trùng, ghi log các cặp bị loại.
3. **Chấm M1–M5** bằng các module `src/aios_habit/golden_question_*.py` (repo hiện có 5 module, vé MOM ghi 6 — dùng đúng số module có thật, ghi rõ nếu thiếu). Cặp điểm thấp: sửa rồi chấm lại; không sửa được thì loại. Ghi metric trước/sau. (Rút kinh nghiệm vé MOM: M1/M2/M5 chưa đo được thì ghi rõ lý do, không bịa số.)
4. **Vòng xem lại**: chạy lại scorer một lượt sau sửa để xác nhận không còn cặp điểm thấp.

## Báo cáo
`docs/phieu-viec/ket-qua/audit-enrich-lsu.md`: số cặp trước/sau, số cặp sửa, số cặp loại (+lý do), metric M1–M5 trước/sau, danh sách file đã fix. Commit lên `phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.
