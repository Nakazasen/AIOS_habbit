# Ticket XẾP HÀNG: f3b-backfill — backfill trường `fix` (gate F3b đang mở)

## Bối cảnh
Vé `buoc0-deploy` (ĐẠT, báo cáo `docs/phieu-viec/ket-qua/buoc0-deploy.md`):
gate F3b FAIL đúng thiết kế — trường lõi `fix` chỉ 56,7% < 90%
(đúng dự báo từ 27/09). Cần vé backfill riêng.

## Việc cần làm
1. Phân tích 43,3% ca thiếu `fix`: thiếu thật hay trích được từ cột khác
   (mô tả/đối sách/ghi chú) của `Loi KDTPS.xlsx`.
2. Viết script backfill (code + test; dry-run trước; backup DB + integrity ok
   trước apply): điền `fix` từ nguồn phụ, ghi rõ nguồn từng giá trị.
3. Chạy lại gate F3b trên DB đã backfill; báo cáo tỉ lệ mới.

## Tiêu chí ĐẠT
- Tỉ lệ `fix` ≥ 90% HOẶC báo cáo chứng minh phần còn thiếu là thiếu thật
  (không trích được từ dữ liệu hiện có) + đề xuất thu thập bổ sung.
- Mọi giá trị backfill có nguồn gốc rõ ràng, không bịa.

## Cấm
- Làm trên DB copy ổ C; chưa có backup mới + integrity ok thì chưa apply.
  Không đụng ổ D, không ghi index production.
- Không merge `main`. Không force-push.

## Báo cáo
`docs/phieu-viec/ket-qua/f3b-backfill.md`. Commit lên `phieu-viec/rag-fix1`,
`trang-thai.md` → `xong-cho-duyet`.
