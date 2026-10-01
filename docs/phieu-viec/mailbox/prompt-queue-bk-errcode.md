# Vé BK-ERRCODE — Backfill mã thật cho 3.537 ca nhóm ERROR (nợ chính xác QĐ1)

LANE: [VM] — Muse code+test trên VM; OMP chạy backfill + verify trên máy nhà khi Muse báo xong.

## Bối cảnh
Quyết định QĐ1 (`docs/phieu-viec/ket-qua/b0-measure-quyet-dinh.md`): 3.537 ca nhóm
ERROR thiếu mã thật (cờ `code_missing=1`). Ca vẫn đủ chuẩn tra cứu nhờ hiện tượng +
nguyên nhân, nhưng thiếu mã làm giảm độ chính xác tra cứu theo mã (B0-DICT đã map
185/272 mã). Báo cáo B0-MEASURE đã xác định +531 dòng trích thêm được từ cột N/O/L/M/R.

## Việc cần làm
1. [VM] Mở rộng `extract_code_from_text` quét thêm cột N/O/L/M/R (nội dung điều tra /
   thao tác); test trên mẫu dữ liệu thật (không bịa).
2. [VM] Viết script backfill: đọc DB copy, dry-run đếm số ca match trước, apply có
   ghi nguồn từng mã: `extracted_them` / `ktd_matched` / `manual`; ca không tìm được
   mã → xuất danh sách (không bịa mã).
3. [NHÀ] OMP chạy script trên bản copy `C:/tmp/b0-dict/error_cases_dict.db`
   (backup + `integrity_check` trước/sau; KHÔNG đụng DB gốc).
4. Đối chiếu 217 file `KTD-*.xlsx` trong `Lịch sử lỗi/C Call/` (+ thư mục mã trong
   `C Call`/`Log`): mã trong tên file (vd `...-C7901.xlsx`) khớp ca theo line + ngày + máy.

## Tiêu chí ĐẠT
- Số ca ERROR còn thiếu mã thật giảm có đo được (báo cáo số trước/sau).
- Test mới cho extractor mở rộng pass; full suite không thoái lui so với nền.
- Báo cáo `docs/phieu-viec/ket-qua/bk-errcode.md`, commit riêng trên `phieu-viec/rag-fix1`.
- Không ghi DB gốc, không đụng ổ D, không merge `main`, không force-push.
