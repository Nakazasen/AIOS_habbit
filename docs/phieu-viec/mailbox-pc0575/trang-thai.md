# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `moi`
Ticket hiện tại: p5-mang-cay-onnx
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
`verdict_p4`: **ĐẠT** (Muse verify độc lập 2026-09-29 ~17:35 +07 trên commit `1c74ea6`):
recompute sha256 tiền ảnh JSON khớp `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`;
script dùng đúng `SemanticModelDescriptor` của repo; output `REPRODUCED`,
648 tổ hợp → đúng 1 bộ giá trị hiệu dụng; các checksum "gần" đều trượt;
chuỗi commit tuyến tính `b767e35 → 1c74ea6 → a6fba85`; tuân thủ chỉ-đọc
(truy vấn `mode=ro`, không đổi env, không embed, không merge `main`).
Ghi chú: [2026-09-29 17:35 +07] Vé P5 đã viết (prompt.md trong push này).
P5 Phase 0 cần user upload `model/bge-m3-onnx-fp32.zip` +
`model/bge-m3-onnx-fp32.sha256` từ máy nhà lên Drive AIOS_Data
(cây đúng chỉ có trên máy nhà; bản cây trên Drive Muse kiểm được hash
`6a8d3a65…` — khác; cây local PC0575 hash `728c9eb7…` — khác).
Commit mới nhất: `1c74ea6`
Đường dẫn báo cáo P4: `docs/phieu-viec/ket-qua/p4-bao-cao.md`
Đường dẫn prompt P5: `docs/phieu-viec/mailbox-pc0575/prompt.md`
Tiến độ: [2026-09-29 17:50 +07] P5 Phase 0 — lần mở OMP 1/4 (watcher tự mở 17:37): cổng CHƯA mở và chưa thể mở trên máy này; vé không kèm link/ID Drive AIOS_Data, KDTVN-PC0575 không có Google Drive client/ổ mount (chỉ `C:`, `D:`, `Z:` mạng công ty; rclone chưa cấu hình remote) nên OMP không thể kiểm tra/tải. Đã kiểm chỉ-đọc: `models\` không tồn tại, không có file zip/sha256 model nào trên máy; cây ONNX local vẫn là cây sai `728c9eb7…` (KHÔNG dùng); env Machine/User `AIOS_BGE_ONNX_MODEL_PATH`/`AIOS_BGE_ONNX_MODEL_CHECKSUM` đều trống. Chi tiết + 3 cách mở cổng: `docs/phieu-viec/ket-qua/p5-phase0-gate.md`. Lưu ý cho các lần mở 2/4–3/4: giữ nguyên dòng Trạng thái/Ticket, KHÔNG thêm bullet dạng `- ghi chú` và KHÔNG gắn mã băm vào file này (đổi các trường đó sẽ reset bộ đếm N=4 của watcher); chỉ kiểm lại: prompt.md có link Drive mới chưa hoặc file local đã có chưa; tuyệt đối không tạo `models\`, không tải/giải nén, không đặt sidecar, không đổi env.
