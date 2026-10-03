# Vé: INDEX-SPLIT-R5 — chạy lại tách thật với bản vá giới hạn biến SQLite

Lane: [NHÀ] OMP chạy trên máy nhà. Không merge `main`. Không đụng PC0575.

## Bối cảnh

Vé R4 dừng vì bug thứ hai trong công cụ tách: `_verify_domain` dựng `IN (...)` với một placeholder cho mỗi chunk_id; khối LSU ~76k chunk vượt `MAX_VARIABLE_NUMBER=32766` của SQLite trên máy nhà → `OperationalError`, fail-closed sau khi đã copy xong khối LSU (chưa ghi manifest). Muse đã vá (commit `5043a42`): chia mẻ 10.000 chunk khi verify; có test hồi quy chứng minh logic cũ gãy và logic mới qua được dưới giới hạn biến thấp. Kho cũ `tri_thuc\library.sqlite` nguyên vẹn (SHA `45eb0e07…b7c0`).

Hiện trạng để lại sau R4: `D:\Sandbox\AIOS_index_split_new\lsu\library.sqlite` 1.155.637.248 byte — đã copy xong nhưng chưa verify, chưa có manifest. File này là sản phẩm dở, được phép ghi đè toàn bộ bằng `--overwrite` (script tự xóa và làm lại từ đầu, sạch hơn tiếp tục file dở).

## Việc OMP làm

### Bước 0 — Pull bản vá
1. Pull nhánh `phieu-viec/rag-fix1` mới nhất (phải có commit `5043a42`).
2. Kiểm tra nhanh (Python 3.11, trong repo):
   `PYTHONPATH=src python -m pytest tests/test_split_index_by_domain.py -q`
   phải pass hết (trong đó có test `test_verify_domain_batches_over_sqlite_variable_limit`).

### Bước 1 — Chạy lại tách thật
3. Chạy:
   `python -m aios_habit.split_index_by_domain --source "C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite" --out "D:\Sandbox\AIOS_index_split_new" --allow-production --overwrite`
   (`--overwrite` chỉ ghi đè thư mục đích của vé này trên ổ D; không đụng kho cũ.)
4. Đọc `D:\Sandbox\AIOS_index_split_new\domain_manifest.json`: `overall` phải `DAT`; tổng chunk 4 khối = 149.800; tổng document = 889; `overlapping_documents` rỗng; khối `tong_hop` chứa đúng các document `low_confidence=true`.

### Bước 2 — Kiểm kho cũ
5. Ghi SHA-256 + size + mtime của kho `tri_thuc` cũ SAU khi chạy (phải bằng trước: `45eb0e07…b7c0`, 2.942.201.856 byte, mtime 2026-10-01 08:27:27).

### Bước 3 — Đóng vé
6. Báo cáo `docs/phieu-viec/ket-qua/index-split-r5.md` (phân bố 4 khối + danh sách `tong_hop`) + `xong-cho-duyet`.

## Tiêu chí ĐẠT
- Manifest `overall: DAT`, đếm khớp 149.800 chunk / 889 document, không trùng document giữa các khối, vector nguyên vẹn.
- Kho `tri_thuc` cũ: SHA/size/mtime trước = sau.
- Không bật `AIOS_DOMAIN_ROUTING_ENABLED`, không dựng collection cho app trong vé này (làm ở vé sau).

## Kế hoạch rollback
Không có gì để rollback — vé này chỉ đọc kho cũ và ghi ra thư mục mới trên ổ D. Xóa `D:\Sandbox\AIOS_index_split_new` là sạch.

## Không làm
- Không embed lại, không ingest thêm.
- Không bật routing, không restart app, không hỏi đáp thử trong vé này.
