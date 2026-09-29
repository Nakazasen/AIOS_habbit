# Trạng thái mailbox

- Trạng thái: `xong-cho-duyet`
- Ticket hiện tại: Ticket xếp hàng 4 — `E3`: dọn XML thô ở extractor (code + test, không ghi index).
- `commit`: 0ec4c78 (báo cáo) — mã `58c4b67`, thêm test `77d4616`
- `bao_cao`: `docs/phieu-viec/ket-qua/e3-don-xml-extractor.md`
- `ghi_chu`: 2026-09-30 01:37 +07 — XONG vé E3, chờ Muse duyệt. Kết quả: rà 3 tệp, chỉ `document_extractors.py` có đường lọt XML thô; siết `_strip_xml_markup` (thẻ trải nhiều dòng, attribute giá trị trong nháy chứa `>`, `<!DOCTYPE ... [ ... ]>`); cờ `AIOS_DOCUMENT_EXTRACTOR_XML_CLEANUP` giữ mặc định TẮT, đường mặc định chứng minh không đổi (spy: 0 lần gọi). 4 test mới: lồng nhau/CDATA/entity/thẻ nhiều dòng/DOCTYPE, PPTX + XLSX XML truncated, luật "vất lại file cũ thì bỏ qua" khi bật cờ. Đỏ-trước-xanh-sau: lùi fix → đúng 3 test XML đỏ. Cổng: `compileall` đạt, `audit` PASS, import `workspace_chat_app` OK, 3 tệp liên quan 73 đạt, `pytest -q` toàn bộ 3.262 đạt/3 bỏ qua/37 lỗi/10 error (đối chứng A/B lùi fix: 40 lỗi → 37 lỗi còn lại có sẵn ở `HEAD`). Không ghi index/embed, không merge `main`, không ghi ổ D.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `verdict_onnx-upload-drive`: **ĐẠT** (Muse verify độc lập 2026-09-30 ~03:0x +07, HEAD `b44258b`): cây model khớp ghim `9f81075f…b11093`; commit `09768ec` chỉ thêm 1 file báo cáo (0 dòng xóa); zip 1.326.939.447 byte SHA-256 `4239479b…8bf2f3c` đúng 9/9 file, trích thử 3 file nhỏ SHA khớp; file công khai trên Drive với đúng tên `bge-m3-onnx-fp32.zip` (kiểm độc lập qua trang chia sẻ); xác minh đầu-cuối ẩn danh: tải đúng 1.326.939.447 byte, SHA trùng bản gốc. Ràng buộc vé: không ghi ổ D, không ghi index, không merge `main` — đều giữ.
- `verdict_stale-check`: **ĐẠT** (Muse verify độc lập 2026-09-29 ~23:1x +07 trên báo cáo `stale-check.md`, commit `76ba99d`): 0/496 document stale cần embed lại — 107.331/107.331 chunk `retrievable=1` đủ dense+sparse ONNX fingerprint `016c5255…`, 0 thiếu row, 0 hash lệch; đếm bằng 2 cách độc lập (SQL LEFT JOIN + quét Python) trùng khớp; 496/496 doc có ≥1 chunk retrievable; 340 row PyTorch cũ trùng chunk_id 100% (dead weight vô hại). Mở bản copy C `C:\\AIOS_p1_4\\tri_thuc\\library.sqlite` ở `mode=ro`, SHA `062ec090…` khớp ghim P1.3 — không đụng ổ D, không ghi index, không embed, không sửa code, không `functions.find`/mạng ngoài. Commit `76ba99d` chỉ thêm 1 file báo cáo, commit `9375c14` chỉ sửa `trang-thai.md`.
- `verdict_don-o-c`: **ĐẠT** (Muse verify độc lập 2026-09-30 ~00:1x +07, HEAD `8136376d` → parent `7fbe3a35` chỉ thêm 1 file báo cáo): 4 bước đúng thứ tự liệt kê→xác minh→xóa; B4 chạy `integrity_check=ok` trên cả 2 bản giữ lại trước khi xóa backup cũ; 4 file `.bak-*` đã xóa đều có SHA-256 ghi lại trước khi xóa; sau xóa vẫn còn ≥1 bản backup index production (bản giữ 32 MB SHA `eedf4bf…` + bản copy truy vấn C + production trên D); SHA bản canary giữ lại `062ec090…` khớp ghim P1.3 (băm lại trong vé); worktree vé 0.3 là clone độc lập, HEAD `c6aa083` là tổ tiên của origin, không commit chưa push/stash, dữ liệu cục bộ đã lưu zip; venv xóa chỉ trên ổ C, venv đang dùng giữ nguyên; không đụng ổ D, không ghi index, không embed, không sửa code. Thu hồi 9.352 MiB (~9,1 GiB) vượt mục tiêu ~8 GB; ổ C trống 12.884,6 MiB (từ 3.532,5 MiB).

- `hang-cho` (theo thứ tự, user yêu cầu 2026-09-29):
  5. `E4` (`prompt-queue-e4.md`) — default backend ONNX fp32 (giữ BGE_BACKEND override, fail-closed).
  6. `buoc0-deploy` (`prompt-queue-buoc0-deploy.md`) — deploy Bước 0–5 lên máy nhà (DEADLINE 30/09 23:59).
  7. `TOOL-1` (`prompt-queue-tool1.md`) — kiểm kê tool chưa nối vào chat.
  8. `TOOL-2` (`prompt-queue-tool2.md`) — khung action trong chat.
  9. `TOOL-3` (`prompt-queue-tool3.md`) — nối benchmark vào chat.
  10. `TOOL-4` (`prompt-queue-tool4.md`) — nối interview + prediction vào chat.
  11. `TOOL-5` (`prompt-queue-tool5.md`) — nối visual maps vào chat.
  (Mục 1 `stale-check` ĐẠT; mục 2 `don-o-c` ĐẠT; mục 3 `onnx-upload-drive` ĐẠT 2026-09-30 ~03:0x +07 — báo cáo `docs/phieu-viec/ket-qua/onnx-upload-drive.md`; mục 4 `E3` OMP báo XONG 2026-09-30 01:37 +07, chờ Muse duyệt — báo cáo `docs/phieu-viec/ket-qua/e3-don-xml-extractor.md`.)
