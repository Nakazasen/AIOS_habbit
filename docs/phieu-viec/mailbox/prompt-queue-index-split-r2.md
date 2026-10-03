# Vé: INDEX-SPLIT-R2 — dry-run lại với bộ phân loại A2, rồi tách thật nếu đạt

Lane: [NHÀ] OMP chạy trên máy nhà. Không merge `main`. Không đụng PC0575.

## Bối cảnh

Vé INDEX-SPLIT-HOME dry-run lần 1 dừng đúng: 453/889 document confidence=0 (bộ phân loại Phase A bỏ sót từ vựng thật: `KTD-`, mã lỗi `C####`/`JAM####`, từ Nhật `自己診断`/`不具合`/`異常`/`エラー`, `DRBFM`...). Muse đã sửa xong trên VM (Phase A2, remote tip `323860a` trở đi): ~30 quy tắc mới từ 372 tên file thật, phân loại bằng nội dung chunk, fallback centroid từ vector sẵn có, `--dry-run` không còn đòi `--allow-production`. Test: 79/79 pass trên VM.

Backup lần 1 vẫn còn: `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre` (SHA khớp từng byte). Kho cũ `tri_thuc\library.sqlite` chưa bị động đến.

## Việc OMP làm

### Bước 0 — Chuẩn bị
1. Pull nhánh `phieu-viec/rag-fix1` mới nhất (phải có commit Phase A2).
2. Kiểm tra nhanh: `python -m aios_habit.split_index_by_domain --help` phải liệt kê được `--dry-run` mà không yêu cầu `--allow-production`.
3. Ghi SHA-256 + size + mtime của `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` TRƯỚC khi làm (phải bằng `45eb0e07…b7c0`).

### Bước 1 — Dry-run lại
4. Chạy (không cần `--allow-production` nữa):
   `python -m aios_habit.split_index_by_domain --source "C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite" --out "C:\AIOS_index_split_preview" --dry-run`
5. Copy phân bố 3 khối (document/chunk/confidence TB + số document confidence < 0,40) vào báo cáo.
6. **Cổng dừng:** nếu số document confidence < 0,40 vẫn lớn bất thường (vài chục trở lên) → DỪNG, báo cáo danh sách, đặt `cho-muse`. Nếu chỉ còn vài document lẻ tẻ → ghi rõ tên từng file vào báo cáo rồi làm tiếp Bước 2.

### Bước 2 — Tách thật (chỉ khi qua cổng Bước 1)
7. Chạy tách thật với `--allow-production`, `--out` vào `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections_new`.
8. Đọc `collections_new\domain_manifest.json`: `overall` phải `DAT`; tổng chunk 3 khối = 149.800; tổng document = 889; `overlapping_documents` rỗng.

### Bước 3 — Chuyển app sang 3 kho mới
9. Dựng 3 collection `lsu`, `dieu_tra_loi`, `mom` trỏ tới 3 thư mục đã tách (giữ nguyên file `tri_thuc` cũ — KHÔNG xóa, KHÔNG ghi).
10. Bật `AIOS_DOMAIN_ROUTING_ENABLED=1`, restart app.
11. Hỏi đáp thử: 1 câu LSU, 1 câu điều tra lỗi, 1 câu MOM, 1 câu mơ hồ. Kiểm tra badge "Đang tra cứu khối X" và câu trả lời trích đúng khối.

### Bước 4 — Đóng vé
12. Ghi SHA/size/mtime kho `tri_thuc` cũ SAU khi làm (phải bằng TRƯỚC).
13. Rollback đã thử: tắt cờ → app về kho cũ, hỏi đáp bình thường.
14. Báo cáo `docs/phieu-viec/ket-qua/index-split-r2.md` + `xong-cho-duyet`.

## Tiêu chí ĐẠT
- Manifest `overall: DAT`, đếm khớp, không trùng document giữa các khối.
- Kho `tri_thuc` cũ: SHA/size/mtime trước = sau.
- 4 câu hỏi thử: mỗi câu tra đúng khối (badge hiển thị), câu mơ hồ ghi rõ khối đã chọn.
- Rollback đã thử thành công.

## Kế hoạch rollback
Tắt `AIOS_DOMAIN_ROUTING_ENABLED`, restart app → về kho `tri_thuc` cũ. Ba file kho mới nằm riêng, xóa khi user duyệt.

## Không làm
- Không embed lại, không ingest thêm trong vé này.
