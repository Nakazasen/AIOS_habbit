# Báo cáo vé INDEX-PROD-HOME — đúng tệp chỉ mục app máy nhà đang đọc thật (chỉ đọc)

- Mã vé: `INDEX-PROD-HOME`. Máy làm: nhà h410asrock. Thời gian làm: 2026-10-07 21:20 → 21:50 +07.
- Vé này KHÔNG có cổng gate nên làm ngay sau khi nhận, không chờ điều kiện nào.

## 1. App đang đọc tệp nào (bằng chứng cấu hình thật, không đoán)

- `config/workspace_chat_rag_v2.local.json`: `runtime.root = C:\AIOS_workspace_chat_rag_v2_production`, `requested_profile = bge_m3_hybrid`.
- `src/aios_habit/workspace_chat_rag_v2_deployment.py` (`load_workspace_chat_rag_v2_deployment`): `runtime_root` lấy từ `runtime.root` trong manifest → `C:\AIOS_workspace_chat_rag_v2_production`.
- `src/aios_habit/workspace_chat_rag_v2_adapter.py` (`_pipeline_config`): `profile_root = runtime_root / profile`, rồi `collection_runtime_layout` ghép tiếp `collections/tri_thuc`.
- `local_cases/workspace_chat/collections.jsonl`: mã `tri_thuc` có `storage_root = ""` (rỗng) → không dùng đĩa chia sẻ, dùng đúng đường `profile_root/collections/tri_thuc`.
- Kết luận: app mở `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`.
- Cách mở khi kiểm: chuỗi nối `mode=ro` + `PRAGMA query_only=ON`. Không ghi, không sửa, không vacuum, không đổi cấu hình app, không merge `main`.

## 2. Kết quả kiểm trên đúng tệp đó

- Đường dẫn: `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`.
- Kích thước: 2.942.201.856 byte, sửa lần cuối 01/10/2026 08:27. Trong thư mục không có `-wal`/`-shm` (không có tiến trình ghi đang mở).
- `PRAGMA quick_check` = `ok`.
- Đếm trực tiếp: 889 mã tài liệu / 889 đường dẫn / 149.800 mảnh — khớp mốc đã kiểm chứng.
- Phân loại theo `file_type`: xlsx 64.152, xlsm 62.967, pdf 15.586, msg 2.706, txt 2.263, xls 912, png 552, `document_summary` 385, pptx 139, html 129, csv 7, bmp 2. Tổng tóm tắt 385 + nội dung 149.415 = 149.800, khớp mốc.
- Vân tay nguồn cấp mã: 540 mã có vân tay + 348 mã trống vân tay + 1 mã chỉ có mảnh tóm tắt (= 349 trống), 0 mã đa vân tay — khớp mốc.
- Vân tay logic nội dung (công thức vé: mỗi mã một dòng `mã|vân tay|số mảnh nội dung`, sắp xếp, nối xuống dòng, SHA-256): `87a3626a85bc32c81ec899c0b5c47d59f6208afd73c80cc94c0a4f2f1df6de3c` — **KHỚP 100%** mốc.

## 3. Tệp app đọc có phải tệp đã kiểm chứng không

- **Phải, giống từng byte.** SHA-256 toàn file của tệp production: `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` — trùng tuyệt đối với bản backup pre-split `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\bge_m3_hybrid\collections\tri_thuc\library.sqlite` (cùng 2.942.201.856 byte, cùng mã ghim `45eb0e07…`).
- Chạy lại cùng công thức vân tay trên bản backup cho ra vân tay nội dung và vân tay tổng **giống hệt** bản production.
- Bản `local_runs/.../library.sqlite` (2.552.659.968 byte, bản 28/09) chỉ là bản dev cũ trong repo, app không đọc — không cần xử lý.
- Rủi ro khi dùng chính thức: **bằng 0 ở tầng chỉ mục** — app đang đọc đúng file đã kiểm chứng nguyên vẹn.

## 4. Phát hiện thêm (ngoài vé, không chặn)

- Chuỗi vân tay TỔNG trong báo cáo `index-verify-home.md` (`fce85b608783d0a…`) sai 1 ký tự ở vị trí 8 (thừa `8`, đúng là `b`). Giá trị đúng (tính lại bằng code trên cả hai file, cho ra giống hệt nhau): `fce85b60b783d0a59545f87042ac2b1b63212bbcdbd8d9dd9948df647b9dbdcf` (đủ 64 ký tự). Mốc 61 ký tự trong vé cũ là bản chép cụt của cùng chuỗi này. Đây là lỗi chép tay, không phải lệch dữ liệu (băm SHA-256 của dữ liệu khác nhau không thể chỉ lệch 1 ký tự). Đề nghị dùng chuỗi đúng ở trên cho mọi đối chiếu sau này.

## 5. Ghi chú trung thực

- Vé chỉ đọc, không sửa một dòng `src/` hay `tests/` nào (chỉ thêm báo cáo này).
- Commit `e96010a` (nhận vé) vô tình dính kèm 1 dòng cập nhật của thợ agy trong `mailbox-agy/trang-thai.md` (đổi `commit` từ `4b7619d` sang `16a0df8`) vì dòng đó đã staged sẵn trên máy trước khi thợ commit — nội dung là cập nhật đúng của agy, thợ giữ nguyên không hoàn tác để khỏi mất việc của bạn, ghi rõ ở đây để điều phối khỏi hiểu lầm.

## 6. Kết luận

- App máy nhà đang đọc đúng tệp chỉ mục đã kiểm chứng (`C:\AIOS_...\tri_thuc\library.sqlite`, giống từng byte bản backup): `quick_check=ok`, 889/149.800, vân tay nội dung khớp 100%.
- Không có tệp khác cần kiểm thêm, không cần đổi cấu hình — máy nhà sẵn sàng dùng chính thức ở tầng chỉ mục.
