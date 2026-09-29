# P5 Phase 0 — Kiểm cổng nhận cây ONNX từ Drive (KDTVN-PC0575)

- Thời điểm: 2026-09-29 17:49 +07 (giờ máy `KDTVN-PC0575`)
- Vé: `docs/phieu-viec/mailbox-pc0575/prompt.md` (ticket `p5-mang-cay-onnx`, Muse viết 17:35)
- Lần mở OMP: **1/4** (watcher tự mở lúc 17:37 — log `D:\Sandbox\agent-mailbox\watcher-mailbox-pc0575.log`;
  state `launchStallCount=1`, sig `moi|p5-mang-cay-onnx||1c74ea6`)
- Kết luận: **CỔNG CHƯA MỞ — và OMP không thể kiểm tra/tải trên máy này vì vé không kèm đường dẫn Drive.**
  Lượt này KHÔNG tải, KHÔNG giải nén, KHÔNG tạo `models\`, KHÔNG đặt sidecar, KHÔNG đổi env, KHÔNG chạm index/worker.

## 1. Cổng yêu cầu gì

User upload lên Drive AIOS_Data: `model/bge-m3-onnx-fp32.zip` + `model/bge-m3-onnx-fp32.sha256`;
OMP tải về, giải nén vào `models\bge-m3-onnx-fp32`, rồi đối chiếu `sha256_model_tree` =
`9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093` mới được đi tiếp Phase 1.

## 2. Bằng chứng kiểm tra (chỉ đọc)

| Hạng mục | Kết quả |
|---|---|
| Link/ID Drive trong vé (`prompt.md`) | **Không có** — vé chỉ ghi "User sẽ upload"; không URL, không ID (grep `http|drive|link|id=` chỉ ra các dòng mô tả) |
| Google Drive client trên KDTVN-PC0575 | **Không có**: ổ đĩa chỉ có `C:`, `D:`, `Z:` (`\\fstvn01` = mạng công ty); không app/service Google; `rclone` có sẵn trong repo nhưng **chưa có config remote** (`rclone.conf` không tồn tại); bookmark Chrome/Edge không có link Drive nào |
| Cây/file đích trên máy | `models\` **không tồn tại**; không có file `bge-m3-onnx-fp32.zip` / `bge-m3-onnx-fp32.sha256` / `*onnx-fp32*` nào trong repo (`find`, không tính `.venv`) |
| Cây ONNX local hiện có | `local_runs\retrieval_models\bge-m3-5617a9f\onnx` (10 file, `model.onnx_data` 2.266.820.608 B) — là cây **sai** (`728c9eb7…`, xem P2/P4); **KHÔNG dùng** |
| Env máy (chỉ đọc, mức Machine + User) | `AIOS_BGE_ONNX_MODEL_PATH` = trống; `AIOS_BGE_ONNX_MODEL_CHECKSUM` = trống; `AIOS_RAG_INDEX_PATH` = trống → khi Phase 1 chạy sẽ **không bị chặn ở cổng env**, sidecar sẽ có hiệu lực |
| Index production (tham chiếu, chưa chạm) | `local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` — 2.552.659.968 B, mtime 2026-09-29 11:20:54 |

## 3. Vì sao chưa đặt `cho-muse` ngay ở lần mở 1/4

- Quy tắc cổng trong prompt watcher: "nếu 4 lần watcher tự mở OMP liên tiếp (mỗi lần cách nhau ~10 phút)
  mà vẫn chưa thấy điều kiện mở thì đặt `trang-thai.md` thành `cho-muse` + DỪNG, không quay no-op".
  Đây mới là lần **1/4**, vòng poll còn giá trị: mỗi lần mở OMP sẽ `git pull` lại — nếu user/Muse kịp bổ
  sung link vào `prompt.md` (hoặc thả file lên máy) thì lần mở kế tiếp bắt được ngay.
- Watcher có cơ chế code-level `$maxStallLaunches = 4`: đủ 4 lần mở mà sig trong `trang-thai.md` không đổi
  → tự ghi `cho-muse` + commit + push. Vì vậy các lần mở 1–3 **không được** sửa các trường
  `Trạng thái` / `Ticket hiện tại` / dòng `ghi_chú` / dòng `Commit` trong `trang-thai.md`
  (sửa là reset bộ đếm, vòng lặp sẽ không bao giờ escalate).
- Lượt này chỉ thêm **1 dòng `Tiến độ:`** (định dạng không bị watcher parse) + báo cáo này.

## 4. Cách mở cổng (chọn 1, chốt với Muse/user)

1. **Có link Drive**: upload `model/bge-m3-onnx-fp32.zip` + `model/bge-m3-onnx-fp32.sha256` lên Drive
   AIOS_Data, bật "anyone with the link", rồi ghi URL (dạng `https://drive.google.com/uc?id=…`) vào
   `docs/phieu-viec/mailbox-pc0575/prompt.md` — lần mở sau OMP tải bằng `gdown`, verify sha256 cây
   = `9f81075f…b11093` rồi mới sang Phase 1.
2. **Không dùng Drive trên PC0575**: user tự tải trên máy này (trình duyệt, tài khoản user) rồi thả đúng
   2 tên file vào `D:\Sandbox\AIOS_habbit\local_runs\p5-upload\`
   (`bge-m3-onnx-fp32.zip`, `bge-m3-onnx-fp32.sha256`) — lần mở sau OMP dùng luôn, vẫn phải khớp `9f81075f…b11093`.
3. **Đường khác do user/Muse chốt** (ví dụ copy qua `D:\Sandbox\agent-mailbox` nếu chia nhỏ được) — nhớ cập nhật vào `prompt.md`.

Trong mọi cách: hash cây giải nén **phải** bằng `9f81075f…b11093`; lệch → dừng, báo `cho-muse`
(cấm đặt checksum bừa — cây local `728c9eb7…` sẽ ra fingerprint `8274fbb0…` ≠ sealed, gây embed lại ~74 giờ).

## 5. Cam kết phạm vi

- Chỉ đọc + ghi 2 file markdown (báo cáo này + 1 dòng tiến độ trong `trang-thai.md`); commit + push
  nhánh `phieu-viec/rag-fix1`; **KHÔNG** đụng `main`, không force-push.
- Không tạo `models\`, không tải/giải nén, không đặt sidecar, không đổi env, không restart app,
  không chạm index/worker (đúng "dừng đúng gate, không làm gì thêm" của vé).

## Lần mở 2/4 — kiểm lại (2026-09-29 17:52 +07)

- Watcher tự mở OMP lần 2 lúc 17:50 (dòng `LAUNCH 2/4` trong
  `D:\Sandbox\agent-mailbox\watcher-mailbox-pc0575.log`; state `launchStallCount=2`,
  sig giữ nguyên `moi|p5-mang-cay-onnx||…`).
- Kiểm lại chỉ-đọc: **cổng vẫn đóng, không có tín hiệu mới** — `prompt.md` chưa có
  link/URL Drive (vẫn chỉ là câu mô tả); `local_runs\p5-upload\` chưa tồn tại;
  `models\` chưa tồn tại; không có file zip/sha256 model mới trong `D:\Sandbox`,
  Downloads, Desktop; `rclone` chưa có config; ổ đĩa vẫn chỉ `C:`, `D:`, `Z:`;
  nhánh remote chưa có push mới.
- Phạm vi lượt này: chỉ ghi markdown (1 dòng tiến độ trong `trang-thai.md` + mục này);
  không tạo `models\`, không tải/giải nén, không đặt sidecar, không đổi env, không chạm
  index/app. Giữ nguyên sig để bộ đếm N=4 escalate được; lượt 3/4 kiểm lại tương tự.
