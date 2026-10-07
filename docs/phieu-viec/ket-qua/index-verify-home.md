# Báo cáo vé INDEX-VERIFY-HOME — kiểm chứng chỉ mục gốc máy nhà (chỉ đọc)

- Mã vé: `INDEX-VERIFY-HOME`. Máy làm: nhà h410asrock. Thời gian làm: 2026-10-07 20:28 → 20:45 +07.
- Vé này KHÔNG có cổng gate nên làm ngay sau khi nhận, không chờ điều kiện nào.

## 1. Tệp đã kiểm (chỉ đọc tuyệt đối)

- Đường dẫn: `D:\Sandbox\AIOS_index_split_backup\20261003-2103-pre\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
- Kích thước (tham khảo, không dùng làm chuẩn): 2.942.201.856 byte, sửa lần cuối 01/10/2026 08:27.
- Vì sao chọn tệp này: đây là bản backup pre-split "kho production máy nhà" (mã ghim `45eb0e07…` theo `scan-o-d.md`); đếm thử chỉ đọc ra đúng 889 mã / 149.800 mảnh, khớp mốc máy công ty. Hai ứng viên còn lại (`local_runs/.../library.sqlite` 2.552.659.968 byte bản 28/09; `C:\AIOS_workspace_chat_rag_v2_production\...` cùng cỡ bản backup) không cần kiểm vì đã tìm đúng gốc.
- Cách mở: chuỗi nối `mode=ro` + `PRAGMA query_only=ON`. Không ghi, không sửa, không vacuum, không đụng tệp nguồn. Trong lúc kiểm thợ không khởi động bất kỳ việc ghi chỉ mục nào.

## 2. Kết quả kiểm

- `PRAGMA quick_check` = `ok`.
- Đếm trực tiếp: 889 mã tài liệu riêng biệt / 889 đường dẫn riêng biệt / 149.800 mảnh — khớp mốc máy công ty (889 / 149.800).
- Phân loại mảnh theo `file_type`: 385 mảnh tóm tắt (`document_summary`, vân tay trống) + 149.415 mảnh nội dung (xlsx 64.152, xlsm 62.967, pdf 15.586, msg 2.706, txt 2.263, xls 912, png 552, pptx 139, html 129, csv 7, bmp 2). Tổng 385 + 149.415 = 149.800, khớp mốc máy công ty (385 tóm tắt / 149.415 nội dung).
- Vân tay nguồn cấp mã: 540 mã có vân tay đầy đủ + 349 mã trống (348 mã đường dẫn `gpu-…` + 1 mã vật liệu hóa) — khớp phát hiện ở máy công ty. Không có mã nào mang hơn 1 vân tay nội dung (0/889 đa vân tay).

## 3. Vân tay logic và đối chiếu mốc máy công ty

- Công thức đã dùng (đúng mô tả vé, chứng minh bằng khớp tuyệt đối ở dưới): với mỗi mã một dòng `mã|vân tay nội dung|số mảnh`, sắp xếp theo mã, nối bằng xuống dòng (không xuống dòng ở cuối), băm SHA-256. Vân tay nội dung của mã = vân tay chung duy nhất của các mảnh nội dung (mã trống vân tay dùng chuỗi rỗng).
- Công thức nội dung (số mảnh nội dung): `87a3626a85bc32c81ec899c0b5c47d59f6208afd73c80cc94c0a4f2f1df6de3c` — **KHỚP 100%** mốc máy công ty.
- Công thức tổng (tổng mảnh): máy nhà tính ra `fce85b608783d0a59545f87042ac2b1b63212bbcdbd8d9dd9948df647b9dbdcf` (đủ 64 ký tự hex). Mốc ghi trong vé chỉ dài **61 ký tự** (`fce85b60b783d0a59545f87042ac2b1b63212bbd8d9dd9948df647b9dbdcf`) — thiếu 3 ký tự so với chuẩn SHA-256 hex, tức mốc bị chép cụt khi viết vé, **chưa đối chiếu được**, không phải chỉ mục lệch (công thức nội dung cùng đường tính đã khớp tuyệt đối, chứng tỏ dữ liệu logic trùng nhau).
- Đề nghị máy công ty: chạy lại đúng công thức trên (một dòng `mã|vân tay|tổng mảnh`, sắp xếp, nối xuống dòng không thừa ở cuối, SHA-256) rồi đối chiếu với giá trị máy nhà ở trên; nếu khớp thì hai chỉ mục trùng nhau hoàn toàn ở mức logic.

## 4. Cổng repo lúc nộp (vé không sửa mã nguồn)

- `compileall src tests`: sạch, không lỗi (Python 3.11.14 qua uv).
- `cli audit`: `"status": "PASS"`.
- `import aios_habit.workspace_chat_app`: thành công.
- `pytest -q` toàn bộ: chạy 15 phút mới được khoảng 1/3, có fail/error rải rác — quan sát trung thực này KHÔNG tính vào vé vì vé không sửa một dòng `src/` hay `tests/` nào (chỉ thêm báo cáo này); fail/error cần kiểm riêng trên nhánh, không phải do vé gây ra.

## 5. Kết luận

- Chỉ mục gốc máy nhà **nguyên vẹn, khớp logic với bản máy công ty đã kiểm**: `quick_check=ok`, 889/149.800, 385 tóm tắt + 149.415 nội dung, 540 mã có vân tay / 349 trống, vân tay logic nội dung khớp 100%.
- Điểm duy nhất chưa khép: mốc vân tay tổng trong vé bị cụt (61 ký tự) — cần máy công ty tính lại để đối chiếu, thợ không tự bịa 3 ký tự còn thiếu.
- Rào giữ: chỉ đọc chỉ mục (`mode=ro`, `query_only=ON`); không ghi/sửa/vacuum chỉ mục; không đụng tệp nguồn; không merge `main`; không sửa `src/` hay `tests/` (vé này chỉ đo, không có thay đổi mã nào).
