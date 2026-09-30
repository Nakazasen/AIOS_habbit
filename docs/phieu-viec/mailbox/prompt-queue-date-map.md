# Ticket XẾP HÀNG: date-map — map cột ngày thật cho phân tích xu hướng

## Bối cảnh
Vé `buoc0-deploy` (ĐẠT) ghi nhận hạn chế: xu hướng/tái phát dùng `created_at`
(= lúc nhập) nên mọi bản ghi nằm cùng 1 bucket; chiều "Công đoạn" gom "(không rõ)".
Muốn phân tích theo ngày phát sinh thật cần map cột ngày X/Y của history_29.

## Việc cần làm
1. Khảo sát cột ngày trong `Loi KDTPS.xlsx` (cột X/Y theo ghi chú buoc0-deploy):
   định dạng, độ phủ, giá trị bất thường.
2. Mở rộng importer (code + test): trích ngày phát sinh thật vào trường riêng
   (vd `occurred_at`), giữ nguyên `created_at`.
3. Chạy lại Bước 4 (xu hướng) + tái phát Bước 5 trên DB đã có ngày thật;
   báo cáo so sánh trước/sau.

## Tiêu chí ĐẠT
- ≥95% bản ghi có `occurred_at` hợp lệ HOẶC báo cáo chứng minh phần thiếu
  là thiếu thật trong nguồn.
- Xu hướng theo ngày phát sinh render đúng, không gom 1 bucket.

## Cấm
- Làm trên DB copy ổ C; backup + integrity trước apply. Không đụng ổ D,
  không ghi index production. Không merge `main`. Không force-push.

## Báo cáo
`docs/phieu-viec/ket-qua/date-map.md`. Commit lên `phieu-viec/rag-fix1`,
`trang-thai.md` → `xong-cho-duyet`.
