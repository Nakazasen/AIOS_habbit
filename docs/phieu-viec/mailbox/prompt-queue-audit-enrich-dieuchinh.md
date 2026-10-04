# Vé xếp hàng: AUDIT-ENRICH-DIEU-TRA-LOI — audit cặp Điều-tra-lỗi (khối dieuchinh)

> Role gợi ý: DEFAULT. Làm trên repo, không cần GPU.

> Nguồn: `docs/phieu-viec/chatgpt-enrichment-raw/dieuchinh/` (đếm thực tế số file/cặp, cấm hardcode — khoảng 34 file batch-55..88, ~995 cặp từ Q2409 trở đi).
> Đích: `docs/phieu-viec/chatgpt-enrichment-fixed/dieuchinh/` (cùng cấu trúc file; tạo thư mục nếu chưa có).

## Rào cứng (giống vé AUDIT-ENRICH-LSU)

- Chỉ sửa file trong `chatgpt-enrichment-fixed/`, không sửa thư mục raw.
- Mọi cặp giữ nhãn Điều-tra-lỗi + `Bản thảo — chưa qua chuyên gia duyệt`.
- Raw value (`0`, `--`, `---`, `999`, `9999`, `OPEN`, `0L`, `OL`, ô trống, `-`, v.v.) chỉ giữ nguyên, không tự gán nghĩa OK/NG, không tự sửa ký hiệu (kể cả `0L`→`OL`).
- Chỉ dùng OK/NG khi chính nguồn file định nghĩa.
- TUYỆT ĐỐI KHÔNG nhập vào kho tri thức chính. Không merge `main`.

## Việc cần làm

1. **Đếm thực tế**: số file, số cặp, Q min/max, Q liền mạch (lưu ý Q3206–Q3208 bỏ trống có chủ đích vì file `信号 7303.xlsx` không đọc được ô).
2. **Sửa 3 lỗi chép tay đã biết** (đối chiếu raw trước khi sửa):
   - `batch-60.md` Q2571: COLOR đúng `40/40=02YN` (đang ghi nhầm `02YT`).
   - `batch-62.md` Q2632: PWB đúng `7PA1170BCZ+GH01` (đang ghi nhầm `+AH01`).
   - `batch-64.md` Q2691: nguồn đúng `ENGINE_3V2XC47020_03.pdf` (đang ghi nhầm `XD`).
3. **Kiểm tra numbering/format toàn bộ file**: Q liên tục (trừ dải trống chủ đích), đủ 6 trường + Nguồn file, nhãn Cách hỏi thuộc đúng 5 nhãn (trực tiếp / tình huống / so sánh / xử lý sự cố / hỏi ngược kiểm tra hiểu), phân bố ngôn ngữ vi/zh/ja.
4. **Dedup theo nội dung**: giữ bản đầy đủ nhất, loại bản trùng, ghi log các cặp bị loại (0 loại cũng ghi rõ).
5. **Chấm M1–M5** bằng module `src/aios_habit/golden_question_*.py` (ghi rõ module nào tồn tại/thiếu — vé LSU đã ghi nhận kho chỉ có 5 module). Cặp điểm thấp: sửa rồi chấm lại; không sửa được thì loại. Ghi metric trước/sau.
6. **Vòng xem lại**: chạy lại scorer một lượt sau sửa để xác nhận không còn cặp điểm thấp.

## Báo cáo

`docs/phieu-viec/ket-qua/audit-enrich-dieuchinh.md`: số cặp trước/sau, số cặp sửa (+3 lỗi đã biết), số cặp loại (+lý do), metric M1–M5 trước/sau, danh sách file đã fix. Commit lên `phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.
