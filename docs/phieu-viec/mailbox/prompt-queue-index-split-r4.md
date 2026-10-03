# Vé: INDEX-SPLIT-R4 — chạy lại tách thật với bản vá Windows URI

Lane: [NHÀ] OMP chạy trên máy nhà. Không merge `main`. Không đụng PC0575.

## Bối cảnh

Vé R3 dừng vì bug trong công cụ tách: `ATTACH DATABASE 'file:C:/...?mode=ro'` trên kết nối không bật `uri=True` làm Windows mở thất bại (`unable to open database`). Muse đã vá (commit `98ba03b`): dùng `Path.as_uri()` ra dạng chuẩn `file:///C:/...?mode=ro` + bật `uri=True` cho kết nối đích; có test hồi quy. Kho cũ `tri_thuc\library.sqlite` nguyên vẹn (SHA `45eb0e07…b7c0` khớp ghim).

Hiện trạng để lại sau R3: chỉ có `D:\Sandbox\AIOS_index_split_new\lsu\library.sqlite` 86.016 byte (mới tạo lược đồ, chưa copy chunk nào) — đây là sản phẩm dở của lần chạy lỗi, được phép ghi đè. Chưa có thư mục `dieu_tra_loi`, `mom`, `tong_hop`, chưa có manifest.

## Việc OMP làm

### Bước 0 — Pull bản vá
1. Pull nhánh `phieu-viec/rag-fix1` mới nhất (phải có commit `98ba03b`).
2. Kiểm tra nhanh trên máy nhà (Python 3.11, trong repo):
   `PYTHONPATH=src python -c "from aios_habit.split_index_by_domain import _open_read_only; print('ok')"`
   phải in `ok`.

### Bước 1 — Chạy lại tách thật
3. Chạy đúng lệnh R3 (thêm `--overwrite` — CHỈ để ghi đè file `lsu\library.sqlite` 86KB dở dang; script tự xóa và tạo lại, không đụng gì khác):
   `python -m aios_habit.split_index_by_domain --source "C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite" --out "D:\Sandbox\AIOS_index_split_new" --allow-production --overwrite`
4. Đọc `D:\Sandbox\AIOS_index_split_new\domain_manifest.json`: `overall` phải `DAT`; tổng chunk 4 khối = 149.800; tổng document = 889; `overlapping_documents` rỗng; khối `tong_hop` chứa đúng các document `low_confidence=true`.

### Bước 2 — Kiểm kho cũ
5. Ghi SHA-256 + size + mtime của `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` SAU khi chạy (phải bằng trước: `45eb0e07…b7c0`, 2.942.201.856 byte).

### Bước 3 — Đóng vé
6. Báo cáo `docs/phieu-viec/ket-qua/index-split-r4.md` (phân bố 4 khối + danh sách `tong_hop`) + `xong-cho-duyet`.

## Tiêu chí ĐẠT
- Manifest `overall: DAT`, đếm khớp 149.800 chunk / 889 document, không trùng document giữa các khối.
- Kho `tri_thuc` cũ: SHA/size/mtime trước = sau.
- Không bật `AIOS_DOMAIN_ROUTING_ENABLED`, không dựng collection cho app trong vé này (làm ở vé sau).

## Kế hoạch rollback
Không có gì để rollback — vé này chỉ đọc kho cũ và ghi ra thư mục mới trên ổ D. Xóa `D:\Sandbox\AIOS_index_split_new` là sạch.

## Không làm
- Không embed lại, không ingest thêm.
- Không xóa file `lsu\library.sqlite` 86KB bằng tay — để `--overwrite` của script xử lý.
- Không bật routing, không restart app, không hỏi đáp thử trong vé này.
