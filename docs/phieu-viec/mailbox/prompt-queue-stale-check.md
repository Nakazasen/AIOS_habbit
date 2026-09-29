# Ticket XẾP HÀNG (kiểm tra nhanh, chỉ đọc): Đếm document stale thực tế

## Bối cảnh
User và Muse không thống nhất về số document stale còn lại (Muse từng ghi 422/496
nhưng không truy được nguồn). Vé này kiểm tra thực tế, KHÔNG sửa gì.

## Việc cần làm (chỉ đọc, không ghi index)
1. Mở index production ở chế độ read-only (`mode=ro` hoặc copy sang ổ C rồi đọc).
2. Đếm và báo cáo:
   - Tổng số document trong index.
   - Số document có ít nhất 1 chunk thiếu embedding ONNX (dense hoặc sparse)
     mà `retrievable=1` (stale thực sự cần embed lại).
   - Số chunk `retrievable=1` thiếu dense ONNX.
   - Số chunk `retrievable=1` thiếu sparse ONNX.
   - Số chunk `retrievable=0` (không cần embed).
3. Đối chiếu fingerprint hiện tại của vector với `016c5255…`.

## Báo cáo
Ghi vào `docs/phieu-viec/ket-qua/stale-check.md`: các con số trên + kết luận
"có/không còn document stale cần embed". Commit lên `phieu-viec/rag-fix1`,
`trang-thai.md` → `xong-cho-duyet`.

## Cấm
- Chỉ đọc. Không ghi index, không embed, không sửa code.
- Không đụng ổ D.
