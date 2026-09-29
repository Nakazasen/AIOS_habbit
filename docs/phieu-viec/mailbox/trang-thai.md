# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Ticket xếp hàng 2 — `don-o-c`: dọn ổ C máy nhà lấy chỗ trống (user đã cho phép 2026-09-29 ~20:10 +07). OMP nhận vé khi máy nhà bật lại.
- `commit`:
- `bao_cao`: `docs/phieu-viec/ket-qua/don-o-c-may-nha.md` (chưa ghi xong)
- `ghi_chu`: 2026-09-29 23:33 +07 — OMP nhận vé don-o-c (máy nhà đang bật). Cổng gate chưa kích hoạt: watcher mới tự mở OMP 1/4 lần cho vé này, điều kiện mở đã có. Bắt đầu Bước 1: quét rác tmp.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `verdict_stale-check`: **ĐẠT** (Muse verify độc lập 2026-09-29 ~23:1x +07 trên báo cáo `stale-check.md`, commit `76ba99d`): 0/496 document stale cần embed lại — 107.331/107.331 chunk `retrievable=1` đủ dense+sparse ONNX fingerprint `016c5255…`, 0 thiếu row, 0 hash lệch; đếm bằng 2 cách độc lập (SQL LEFT JOIN + quét Python) trùng khớp; 496/496 doc có ≥1 chunk retrievable; 340 row PyTorch cũ trùng chunk_id 100% (dead weight vô hại). Mở bản copy C `C:\AIOS_p1_4\tri_thuc\library.sqlite` ở `mode=ro`, SHA `062ec090…` khớp ghim P1.3 — không đụng ổ D, không ghi index, không embed, không sửa code, không `functions.find`/mạng ngoài. Commit `76ba99d` chỉ thêm 1 file báo cáo, commit `9375c14` chỉ sửa `trang-thai.md`.

- `hang-cho` (theo thứ tự, user yêu cầu 2026-09-29):
  3. `onnx-upload-drive` (`prompt-queue-onnx-upload.md`, user yêu cầu ~18:50 +07) — nén + upload model.
  4. `E3` (`prompt-queue-e3.md`) — dọn XML thô ở extractor (code + test).
  5. `E4` (`prompt-queue-e4.md`) — default backend ONNX fp32 (giữ BGE_BACKEND override, fail-closed).
  6. `buoc0-deploy` (`prompt-queue-buoc0-deploy.md`) — deploy Bước 0–5 lên máy nhà (DEADLINE 30/09 23:59).
  7. `TOOL-1` (`prompt-queue-tool1.md`) — kiểm kê tool chưa nối vào chat.
  8. `TOOL-2` (`prompt-queue-tool2.md`) — khung action trong chat.
  9. `TOOL-3` (`prompt-queue-tool3.md`) — nối benchmark vào chat.
  10. `TOOL-4` (`prompt-queue-tool4.md`) — nối interview + prediction vào chat.
  11. `TOOL-5` (`prompt-queue-tool5.md`) — nối visual maps vào chat.
  (Mục 1 `stale-check` ĐẠT — báo cáo `docs/phieu-viec/ket-qua/stale-check.md`; mục 2 `don-o-c` đang phát vé — file `prompt-queue-don-o-c.md`.)
