# Vé: INDEX-SPLIT-R3 — tách thật với khối dự phòng Tổng hợp, ra ổ D

Lane: [NHÀ] OMP chạy trên máy nhà. Không merge `main`. Không đụng PC0575.

## Bối cảnh

- Vé INDEX-SPLIT-R2 dry-run DỪNG đúng cổng (báo cáo `docs/phieu-viec/ket-qua/index-split-r2.md`): **72/889 document** độ tin cậy < 0,40 (chủ yếu `wsc-*.txt` mất tên gốc, ảnh `.png`, file `.msg` — nghèo tín hiệu, chênh cosine giữa các khối chỉ 0,005–0,09). Không tách thật ở R2.
- **Quyết định kỹ thuật của Muse (đã code + test xong trên VM):** không ép 72 document này vào 3 khối chính (ép sai khối sẽ làm bẩn chất lượng retrieval của khối chính). Thêm **khối dự phòng `tong_hop` ("Tổng hợp")**: document dưới ngưỡng vào đây, manifest ghi `low_confidence: true` + giữ nguyên khối gán gốc ở `assigned_domain` để đối soát. Phase A3, test VM: 11/11 pass (test chia kho) + 54/54 (test domain liên quan).
- **Ràng buộc ổ đĩa (OMP ghi nhận ở R2):** ổ C còn ~2,0 GB trống, tách thật cần ~2,94 GB. Vé này tách ra **ổ D** (`D:\Sandbox\AIOS_index_split_new`), KHÔNG ghi gì thêm lên ổ C.
- Backup lần 1 vẫn còn: `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre`. Kho cũ `tri_thuc\library.sqlite` chưa bị động đến (SHA `45eb0e07…b7c0`).

## Việc OMP làm

### Bước 0 — Chuẩn bị
1. Pull nhánh `phieu-viec/rag-fix1` mới nhất — BẮT BUỘC có commit Phase A3 của vé này (Muse ghi SHA tip ở mục `Ghi chú` khi phát hành vé; nếu pull chưa thấy commit đó thì DỪNG và báo).
2. Kiểm tra nhanh: `python -m aios_habit.split_index_by_domain --help` phải liệt kê được `--fallback-threshold` và `--no-fallback-domain`.
3. Ghi SHA-256 + size + mtime của `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` TRƯỚC khi làm (phải bằng `45eb0e07…b7c0`).
4. Kiểm tra dung lượng trống: ổ C và ổ D. **Cổng fail-closed:** chỉ làm tiếp khi ổ D còn trống ≥ 3,5 GB; nếu không đủ thì DỪNG, báo số liệu, đặt `cho-muse` (không tự xóa gì để lấy chỗ).

### Bước 1 — Tách thật ra ổ D
5. Chạy:
   `python -m aios_habit.split_index_by_domain --source "C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite" --out "D:\Sandbox\AIOS_index_split_new" --allow-production`
   (Nếu thư mục đích đã tồn tại từ lần chạy dở: thêm `--overwrite` sau khi xác nhận đó đúng là thư mục của vé này.)
6. Đọc `D:\Sandbox\AIOS_index_split_new\domain_manifest.json`:
   - `overall` phải `DAT`.
   - Đủ 4 khối: `lsu`, `dieu_tra_loi`, `mom`, `tong_hop`.
   - Tổng document 4 khối = **889**; tổng chunk = **149.800**; `overlapping_documents` rỗng.
   - Khối `tong_hop` khoảng ~72 document / ~2.402 chunk (dung sai ±5 document — phân loại lại trên máy có thể lệch nhẹ so với dry-run R2).
   - Mọi document trong `tong_hop` phải có `low_confidence: true` và `assigned_domain` khác rỗng.
7. **Cổng dừng:** nếu `overall` ≠ `DAT`, hoặc tổng số lệch, hoặc có document trùng giữa các khối → DỪNG, giữ nguyên hiện trạng, báo cáo chi tiết, đặt `cho-muse`. Không xóa, không chạy lại `--overwrite` mù.

### Bước 2 — Đóng vé
8. Ghi SHA-256/size/mtime kho `tri_thuc` cũ SAU khi làm (phải bằng TRƯỚC ở bước 3 — tách chỉ đọc nguồn).
9. **Không làm trong vé này:** không dựng collection cho app, không bật cờ routing, không hỏi đáp thử, không chuyển app sang kho mới. (Vé routing riêng sau khi Muse verdict manifest.)
10. Báo cáo `docs/phieu-viec/ket-qua/index-split-r3.md` + `xong-cho-duyet`.

## Tiêu chí ĐẠT
- Manifest `overall: DAT`, 4 khối, đếm khớp (889 document / 149.800 chunk), không trùng document giữa các khối.
- Khối `tong_hop` ≈ 72 document (±5), 100% có `low_confidence: true` + `assigned_domain`.
- Kho `tri_thuc` cũ: SHA/size/mtime trước = sau.
- Ổ C không bị ghi thêm file tách (toàn bộ output nằm trên ổ D).

## Kế hoạch rollback
Không cần rollback: vé này chỉ đọc kho cũ và ghi kho mới ra ổ D. Xóa `D:\Sandbox\AIOS_index_split_new` khi user duyệt là xong.

## Không làm
- Không embed lại, không ingest thêm, không sửa `tri_thuc\library.sqlite`.
- Không bật routing, không restart app trong vé này.
