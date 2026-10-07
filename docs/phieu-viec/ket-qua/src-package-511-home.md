# Báo cáo vé `SRC-PACKAGE-511-HOME` — đóng gói 511 tệp vật liệu hoá từ máy nhà

- Vé: `SRC-PACKAGE-511-HOME` (máy nhà `h410asrock`, máy giữ chỉ mục gốc).
- Đầu vào: `docs/phieu-viec/ket-qua/ban-ke-511.csv` (511 mã + đầu mục) + `docs/phieu-viec/ket-qua/src-sync-pc0575.md` mục 13.
- Nhánh: `phieu-viec/rag-fix1`, không merge `main`.
- Mức hoàn thành: **PARTIAL trung thực** — băm đối chiếu + đóng gói xong (90/511 khớp), **bước tải gói lên Drive còn chờ** (lý do ở mục 5).

## 1. Phương án

Việc này đơn giản (sao chép + băm, chỉ đọc) nên chỉ có một phương án:

- Đọc từng mã trong CSV, tìm tệp `{document_id}.txt` đúng gốc theo `source_path` (nhánh canary `local_runs/workspace_chat_rag_v2_canary/materialized_sources`, nhánh production `C:\AIOS_workspace_chat_rag_v2_production\materialized_sources`).
- Băm SHA-256 đúng hàm `_file_fingerprint` của chương trình (băm byte thô), đối chiếu `source_fingerprint`.
- **Chỉ đóng gói tệp KHỚP băm.** Tệp lệch/thiếu liệt kê riêng, không đoán, không thay thế.
- Không dùng GPU, không ghi chỉ mục, không sửa tệp gốc.

## 2. Kết quả băm đối chiếu (chỉ đọc, Python 3.11.14)

| Kết quả | Số mã | Ghi chú |
|---|---|---|
| Khớp băm | 90 | production 32/32, canary 58/479 |
| Lệch băm | 421 | toàn bộ ở gốc canary |
| Không tìm thấy | 0 | mọi mã đều có tệp đúng gốc, không lạc gốc |
| Tổng | 511 | 500 mã nhiều-mảnh + 11 mã một-mảnh-lệch |

Chi tiết từng mã: tệp `local_runs/src-package-511/verify.csv` (giữ ở máy, không commit).
Danh sách 421 mã lệch kèm băm thực tế + vân tay kỳ vọng: `docs/phieu-viec/ket-qua/src-package-511-lech.csv` (421 dòng + đầu mục).

## 3. Phát hiện chính: gốc canary đã tái vật liệu hoá sau khi dựng chỉ mục

- Vân tay trong CSV khớp từng byte với vân tay chỉ mục production đang lưu (kiểm 3 mẫu: 2 canary + 1 production, cả 3 trùng).
- 32/32 tệp production khớp → gốc production còn nguyên từ lúc dựng chỉ mục.
- 421/479 tệp canary lệch → các tệp này đã được tạo lại (vật liệu hoá lại) sau khi dựng chỉ mục, nội dung đổi.
- Bằng chứng mẫu `wsc-00428f9482636841c4638269`: chỉ mục lưu 5 mảnh với vân tay `20d0bbb6…`, byte tệp hiện tại băm ra `92c0fa7f…`; đầu mảnh 1 trong chỉ mục thiếu cụm đầu mục mà tệp hiện tại có (`P.W.BOARD ASSY FUSER 1.INDEX 2.CHANGE HISTORY 3.FUSER`).
- Hệ quả cho máy công ty: với 421 mã này, byte đúng lúc nạp chỉ mục **không còn ở máy nhà**; chép byte hiện tại sang rồi băm lại sẽ không khớp vân tay kỳ vọng. Cần hướng xử lý riêng (tìm bản đúng lúc nạp, hoặc chấp nhận nạp lại 421 mã này).

## 4. Gói đã đóng (90 tệp khớp)

- Cấu trúc trong gói: thư mục `canary/` (58 tệp) + `production/` (32 tệp) + `manifest.csv` (cột `document_id, duong_dan_tuong_doi, sha256`).
- Tổng byte 90 tệp: 1.681.194. Tệp zip: `local_runs/src-package-511/src-package-511-home-match90.zip` (430.510 byte).
- SHA-256 của tệp zip: `862CAD6EF5943678DA25424AF177DA8D66EE3B53FC4DADC87827836A37613403`.
- Tệp zip giữ ở máy (thư mục `local_runs/`, không commit theo luật an toàn dữ liệu).

## 5. Bước còn chờ: tải gói lên Drive (ghi trung thực, không báo xong bừa)

- Chưa tải vì phiên làm việc này không có công cụ tải Drive (không có `rclone`, không có thư mục Drive đồng bộ trên máy).
- Cách các vé trước dùng là điều khiển trình duyệt Chrome đang đăng nhập của user bằng tay. Phiên này không làm cách đó vì dễ chiếm cửa sổ, bấm nhầm trong Drive đang đăng nhập của user (nguy cơ mất an toàn dữ liệu, trong khi gói chỉ 430KB).
- Đề xuất: user hoặc Muse tải tệp zip ở đường dẫn mục 4 lên thư mục `AIOS_Data` (giữ nguyên tên tệp), rồi ghi link vào vé nhận phía công ty. Hoặc ra vé upload tiếp theo làm riêng bước này.

## 6. Cổng kho (vé không sửa `src/`/`tests/`)

- `compileall src tests`: sạch.
- `cli audit`: `PASS`.
- `import aios_habit.workspace_chat_app`: thành công.
- Không chạy toàn bộ pytest vì vé không đụng mã nguồn (tiền lệ vé đo `INDEX-PROD-HOME` cũng chỉ chạy 3 cổng này).
- Rào giữ: chỉ đọc tệp nguồn và chỉ mục (mở chỉ mục ở chế độ chỉ đọc), không ghi chỉ mục, không xóa/sửa tệp gốc, không merge `main`, không secret.
