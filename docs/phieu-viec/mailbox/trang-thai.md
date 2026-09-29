# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: Ticket xếp hàng 5 — `E4`: chuyển default backend sang ONNX fp32 (giữ BGE_BACKEND override, fail-closed).
- `commit`: —
- `bao_cao`: —
- `ghi_chu`: 2026-09-30 01:52 +07 — Muse review độc lập vé E3: **ĐẠT**, phát hành vé E4 theo hàng-cho. Chờ OMP nhận vé.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `verdict_onnx-upload-drive`: **ĐẠT** (Muse verify độc lập 2026-09-30 ~03:0x +07, HEAD `b44258b`): cây model khớp ghim `9f81075f…b11093`; commit `09768ec` chỉ thêm 1 file báo cáo (0 dòng xóa); zip 1.326.939.447 byte SHA-256 `4239479b…8bf2f3c` đúng 9/9 file, trích thử 3 file nhỏ SHA khớp; file công khai trên Drive với đúng tên `bge-m3-onnx-fp32.zip` (kiểm độc lập qua trang chia sẻ); xác minh đầu-cuối ẩn danh: tải đúng 1.326.939.447 byte, SHA trùng bản gốc. Ràng buộc vé: không ghi ổ D, không ghi index, không merge `main` — đều giữ.
- `verdict_stale-check`: **ĐẠT** (Muse verify độc lập 2026-09-29 ~23:1x +07 trên báo cáo `stale-check.md`, commit `76ba99d`): 0/496 document stale cần embed lại — 107.331/107.331 chunk `retrievable=1` đủ dense+sparse ONNX fingerprint `016c5255…`, 0 thiếu row, 0 hash lệch; đếm bằng 2 cách độc lập (SQL LEFT JOIN + quét Python) trùng khớp; 496/496 doc có ≥1 chunk retrievable; 340 row PyTorch cũ trùng chunk_id 100% (dead weight vô hại). Mở bản copy C `C:\\AIOS_p1_4\\tri_thuc\\library.sqlite` ở `mode=ro`, SHA `062ec090…` khớp ghim P1.3 — không đụng ổ D, không ghi index, không embed, không sửa code, không `functions.find`/mạng ngoài. Commit `76ba99d` chỉ thêm 1 file báo cáo, commit `9375c14` chỉ sửa `trang-thai.md`.
- `verdict_don-o-c`: **ĐẠT** (Muse verify độc lập 2026-09-30 ~00:1x +07, HEAD `8136376d` → parent `7fbe3a35` chỉ thêm 1 file báo cáo): 4 bước đúng thứ tự liệt kê→xác minh→xóa; B4 chạy `integrity_check=ok` trên cả 2 bản giữ lại trước khi xóa backup cũ; 4 file `.bak-*` đã xóa đều có SHA-256 ghi lại trước khi xóa; sau xóa vẫn còn ≥1 bản backup index production (bản giữ 32 MB SHA `eedf4bf…` + bản copy truy vấn C + production trên D); SHA bản canary giữ lại `062ec090…` khớp ghim P1.3 (băm lại trong vé); worktree vé 0.3 là clone độc lập, HEAD `c6aa083` là tổ tiên của origin, không commit chưa push/stash, dữ liệu cục bộ đã lưu zip; venv xóa chỉ trên ổ C, venv đang dùng giữ nguyên; không đụng ổ D, không ghi index, không embed, không sửa code. Thu hồi 9.352 MiB (~9,1 GiB) vượt mục tiêu ~8 GB; ổ C trống 12.884,6 MiB (từ 3.532,5 MiB).
- `verdict_e3`: **ĐẠT** (Muse verify độc lập 2026-09-30 ~01:4x +07 trên VM Linux Python 3.12.3, commit `77d4616`): diff `58c4b67` chỉ đổi regex dọn XML (26 thêm/5 bớt ở `src/aios_habit/document_extractors.py`), cơ chế cờ không đổi; commit báo cáo `0ec4c78` chỉ thêm báo cáo + 9 dòng cập nhật `PROJECT_HANDOVER.md`; `tests/test_document_extractors.py` 30/30 pass (gồm 4 test mới); đỏ-trước-xanh-sau: lùi mã nguồn về trước fix → đúng 3 test XML đỏ; hiệu năng 272.000 ký tự/0,027s không cặn; cờ `AIOS_DOCUMENT_EXTRACTOR_XML_CLEANUP` mặc định TẮT; không ghi index/embed, không merge `main`, không đụng ổ D (test không chứa `D:`). Lỗi suite môi trường trên VM (thiếu `local_cases/.../collections.jsonl`) không liên quan fix.

- `hang-cho` (theo thứ tự, user yêu cầu 2026-09-29):
  6. `buoc0-deploy` (`prompt-queue-buoc0-deploy.md`) — deploy Bước 0–5 lên máy nhà (DEADLINE 30/09 23:59).
  7. `TOOL-1` (`prompt-queue-tool1.md`) — kiểm kê tool chưa nối vào chat.
  8. `TOOL-2` (`prompt-queue-tool2.md`) — khung action trong chat.
  9. `TOOL-3` (`prompt-queue-tool3.md`) — nối benchmark vào chat.
  10. `TOOL-4` (`prompt-queue-tool4.md`) — nối interview + prediction vào chat.
  11. `TOOL-5` (`prompt-queue-tool5.md`) — nối visual maps vào chat.
  (Mục 1 `stale-check` ĐẠT; mục 2 `don-o-c` ĐẠT; mục 3 `onnx-upload-drive` ĐẠT 2026-09-30 ~03:0x +07 — báo cáo `docs/phieu-viec/ket-qua/onnx-upload-drive.md`; mục 4 `E3` ĐẠT 2026-09-30 ~01:52 +07 — báo cáo `docs/phieu-viec/ket-qua/e3-don-xml-extractor.md`.)
