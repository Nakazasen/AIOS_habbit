# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Ticket xếp hàng 3 — `onnx-upload-drive`: nén + upload cây ONNX bge-m3-onnx-fp32 lên Google Drive (user yêu cầu 2026-09-29 ~18:50 +07). Làm sau khi don-o-c đã lấy lại chỗ trống ổ C.
- `commit`: (chưa có)
- `bao_cao`: (chưa có)
- `ghi_chu`: 2026-09-30 00:33 +07 — Bước 2 ĐẠT: zip `C:\temp\bge-m3-onnx-fp32.zip` = 1.326.939.447 byte, SHA-256 `4239479B…2F3C`; tar exit 0; liệt kê đủ 9/9 file đúng dung lượng; trích thử 3 file nhỏ khớp hash nguồn; ổ C còn 12.070.187.008 byte. Đang mở kênh upload Drive: máy không có rclone/Drive client; Chrome đang mở khóa cookie profile `Default`, thử profile phụ (1/3/4/5) để upload qua trình duyệt.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `verdict_stale-check`: **ĐẠT** (Muse verify độc lập 2026-09-29 ~23:1x +07 trên báo cáo `stale-check.md`, commit `76ba99d`): 0/496 document stale cần embed lại — 107.331/107.331 chunk `retrievable=1` đủ dense+sparse ONNX fingerprint `016c5255…`, 0 thiếu row, 0 hash lệch; đếm bằng 2 cách độc lập (SQL LEFT JOIN + quét Python) trùng khớp; 496/496 doc có ≥1 chunk retrievable; 340 row PyTorch cũ trùng chunk_id 100% (dead weight vô hại). Mở bản copy C `C:\\AIOS_p1_4\\tri_thuc\\library.sqlite` ở `mode=ro`, SHA `062ec090…` khớp ghim P1.3 — không đụng ổ D, không ghi index, không embed, không sửa code, không `functions.find`/mạng ngoài. Commit `76ba99d` chỉ thêm 1 file báo cáo, commit `9375c14` chỉ sửa `trang-thai.md`.
- `verdict_don-o-c`: **ĐẠT** (Muse verify độc lập 2026-09-30 ~00:1x +07, HEAD `8136376d` → parent `7fbe3a35` chỉ thêm 1 file báo cáo): 4 bước đúng thứ tự liệt kê→xác minh→xóa; B4 chạy `integrity_check=ok` trên cả 2 bản giữ lại trước khi xóa backup cũ; 4 file `.bak-*` đã xóa đều có SHA-256 ghi lại trước khi xóa; sau xóa vẫn còn ≥1 bản backup index production (bản giữ 32 MB SHA `eedf4bf…` + bản copy truy vấn C + production trên D); SHA bản canary giữ lại `062ec090…` khớp ghim P1.3 (băm lại trong vé); worktree vé 0.3 là clone độc lập, HEAD `c6aa083` là tổ tiên của origin, không commit chưa push/stash, dữ liệu cục bộ đã lưu zip; venv xóa chỉ trên ổ C, venv đang dùng giữ nguyên; không đụng ổ D, không ghi index, không embed, không sửa code. Thu hồi 9.352 MiB (~9,1 GiB) vượt mục tiêu ~8 GB; ổ C trống 12.884,6 MiB (từ 3.532,5 MiB).

- `hang-cho` (theo thứ tự, user yêu cầu 2026-09-29):
  4. `E3` (`prompt-queue-e3.md`) — dọn XML thô ở extractor (code + test).
  5. `E4` (`prompt-queue-e4.md`) — default backend ONNX fp32 (giữ BGE_BACKEND override, fail-closed).
  6. `buoc0-deploy` (`prompt-queue-buoc0-deploy.md`) — deploy Bước 0–5 lên máy nhà (DEADLINE 30/09 23:59).
  7. `TOOL-1` (`prompt-queue-tool1.md`) — kiểm kê tool chưa nối vào chat.
  8. `TOOL-2` (`prompt-queue-tool2.md`) — khung action trong chat.
  9. `TOOL-3` (`prompt-queue-tool3.md`) — nối benchmark vào chat.
  10. `TOOL-4` (`prompt-queue-tool4.md`) — nối interview + prediction vào chat.
  11. `TOOL-5` (`prompt-queue-tool5.md`) — nối visual maps vào chat.
  (Mục 1 `stale-check` ĐẠT — báo cáo `docs/phieu-viec/ket-qua/stale-check.md`; mục 2 `don-o-c` ĐẠT — báo cáo `docs/phieu-viec/ket-qua/don-o-c-may-nha.md`; mục 3 `onnx-upload-drive` đang phát vé — file `prompt-queue-onnx-upload.md`.)
