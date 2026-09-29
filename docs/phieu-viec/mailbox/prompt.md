# Ticket XẾP HÀNG: Deploy Bước 0 lên máy nhà (DEADLINE 2026-09-30 23:59)

## Bối cảnh
Code/test Bước 0–5 xong từ 28/09 (commit f8eb879, 79 test pass trên Linux).
Chưa deploy lên máy nào. Deadline: 2026-09-30 23:59.

## Việc cần làm
1. Pull branch `phieu-viec/rag-fix1` mới nhất (đã gồm E3, E4 nếu xong).
2. Chạy lại 79 test trên Windows Python 3.11, tất cả phải pass.
3. Chạy pipeline Bước 0–5 với dữ liệu thật từ Drive (LSU + điều tra lỗi):
   - Dữ liệu mô phỏng PHẢI dựa trên dữ liệu thật, gắn mác `SIMULATED_*`, không bịa.
4. Kiểm tra output: đúng format, đủ 5 bước, không lỗi.
5. Ghi báo cáo nghiệm thu.

## Cấm
- Không merge `main` (chờ E-series xong, user đã duyệt merge sau khi verify).
- Không đụng index production RAG.
- Không đụng ổ D.

## Báo cáo
`docs/phieu-viec/ket-qua/buoc0-deploy.md`: số test pass/fail trên Windows,
kết quả chạy với dữ liệu thật, xác nhận đạt deadline.
Commit lên `phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.
