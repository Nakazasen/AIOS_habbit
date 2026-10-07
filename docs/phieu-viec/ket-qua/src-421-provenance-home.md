# Báo cáo vé `SRC-421-PROVENANCE-HOME` — truy nguồn byte đúng lúc nạp chỉ mục cho 421 mã lệch băm

- Vé: `SRC-421-PROVENANCE-HOME` (máy nhà `h410asrock`).
- Đầu vào: `docs/phieu-viec/ket-qua/src-package-511-home.md` + `docs/phieu-viec/ket-qua/src-package-511-lech.csv` (421 mã lệch kèm băm thực tế + vân tay kỳ vọng) + `docs/phieu-viec/ket-qua/ban-ke-511.csv` (511 mã + vân tay kỳ vọng).
- Nhánh: `phieu-viec/rag-fix1`, không merge `main`.
- Mức hoàn thành: **đủ 3 việc của vé, chờ duyệt** — liệt kê kho + băm đối chiếu + kết luận theo số liệu. Không tự thực hiện hướng đóng gói hay nạp lại ở vé này.

## 1. Các kho ứng viên đã liệt kê (chỉ đọc)

| Kho | Đường dẫn | Thời điểm | Căn cứ có thể giữ bản đúng |
|---|---|---|---|
| Backup trước chia kho | `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\materialized_sources` | Thư mục 01/10/2026 07:33; tệp mẫu 31/08–04/09/2026 | Bản sao lưu ngay trước đợt chia kho đầu tháng 10 — thời điểm gần lúc dựng chỉ mục canary nhất còn sót ở máy nhà |
| Chỉ mục sao lưu kèm theo | `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\bge_m3_hybrid\collections\tri_thuc\library.sqlite` (2.942.201.856 B) | 01–02/10/2026 | Neo thời gian: bản backup pre-split đã kiểm ở vé `INDEX-VERIFY-HOME` (889 mã / 149.800 mảnh) — dùng đối chiếu mốc, không phải kho nguồn byte |
| Gốc canary hiện tại | `local_runs\workspace_chat_rag_v2_canary\materialized_sources` | Thư mục 27/09/2026 08:12; tệp mẫu 27/09/2026 07:39–08:04 | Gốc mà vé `PACKAGE` đã băm (530 tệp) — dùng làm baseline: 421 mã lệch chính là ở đây |
| Gốc production máy nhà | `local_runs\workspace_chat_rag_v2_production\materialized_sources` | 13/09/2026 21:12 | Kiểm chéo: loại trừ khả năng byte canary lạc sang production |
| Gốc production ổ C | `C:\AIOS_workspace_chat_rag_v2_production\materialized_sources` | 07/10/2026 22:59 | Kiểm chéo trên bản production thật app đang đọc |
| Đã kiểm và loại trừ | `local_runs\dieu_tra\` (chỉ docx/md nhật ký), `local_runs\rag_v2_dev\` (chỉ sqlite), `D:\Sandbox\AIOS_index_split_new\{lsu,dieu_tra_loi,mom,tong_hop}\` (chỉ `library.sqlite` từng khối + `domain_manifest.json`, không có `materialized_sources`) | — | Không chứa tệp `{mã}.txt`, không phải kho ứng viên |

## 2. Kết quả băm đối chiếu (chỉ đọc, Python 3.11 qua uv)

- Hàm băm: SHA-256 byte thô, đúng `_file_fingerprint` trong `src/aios_habit/rag_v2/pipeline.py:162` (đọc từng khối 1 MB).
- Đối chiếu: với mỗi kho, băm tệp `{mã}.txt` nếu có, so từng byte với vân tay kỳ vọng trong `ban-ke-511.csv`.

| Kho | Số tệp trong kho | Số mã trong 421 có tệp | Khớp vân tay kỳ vọng |
|---|---|---|---|
| Backup trước chia kho (75 tệp) | 75 | 0 | **0** |
| Canary hiện tại (530 tệp) | 530 | 421 | **0** |
| Production máy nhà (75 tệp) | 75 | 0 | **0** |
| Production ổ C (79 tệp) | 79 | 0 | **0** |

- Đối chiếu mở rộng trên toàn 511 mã (để khỏi sót nhầm tên): backup khớp 59/59 tệp có mặt (toàn mã ngoài 421 — 56 nhiều-mảnh + 3 một-mảnh, gồm cả production và canary-khớp cũ); canary hiện tại khớp 61 ngoài 421; production hai nơi khớp 59 ngoài 421. **Riêng 421 mã lệch: 0 khớp ở mọi kho.**

## 3. Kết luận + khuyến nghị theo số liệu

- Rơi vào nhánh (b) của vé: **không kho nào ở máy nhà còn giữ byte đúng lúc nạp cho 421 mã.**
- Bằng chứng phụ: tệp canary hiện tại mtime 27/09/2026 (sau tệp backup 31/08–04/09), nội dung đã đổi so với vân tay chỉ mục (mẫu `wsc-00428f` trong báo cáo `PACKAGE`); backup 75 tệp chỉ giữ 59 mã ngoài 421 nên không bù được.
- Khuyến nghị: **chấp nhận nạp lại 421 mã từ tệp hiện tại phía máy công ty** (hướng (b) trong vé).
- Hệ quả phải trình user quyết trước khi làm vé nối: phải dựng lại phần chỉ mục của đúng 421 mã đó từ byte hiện tại + kiểm chứng lại vân tay từng mã khớp bộ mới; 90 mã đã đóng gói không bị ảnh hưởng; không dùng byte hiện tại để nhận là khớp vân tay cũ.
- Vé này dừng ở khuyến nghị, không tự đóng gói bổ sung, không tự nạp lại, không ghi index.

## 4. Cổng kho (vé không sửa `src/`/`tests/`)

- `compileall src tests`: sạch.
- `cli audit`: `PASS`.
- `import aios_habit.workspace_chat_app`: thành công.
- Không chạy toàn bộ pytest vì vé không đụng mã nguồn (tiền lệ vé đo `INDEX-PROD-HOME`).
- Rào giữ: chỉ đọc mọi kho ứng viên và chỉ mục (mở sqlite ở chế độ chỉ đọc khi cần đếm, không áp dụng ghi); không sửa/xoá/di chuyển tệp ở bất cứ kho nào; không ghi index; không merge `main`; không secret.
