# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `xong`

- `verdict_p5`: **ĐẠT** (Muse verify độc lập 2026-09-30 ~09:5x +07 trên VM): cây ONNX `9f81075f…b11093` khớp seal (zip 1.326.939.447 B, SHA `4239479b…bf2f3c` đo chéo 3 cách; verify bằng chính hàm của mã, chỉ đọc); fingerprint `016c5255…` khớp 107.331 vector dense → không embed lại; env `AIOS_BGE_ONNX_MODEL_CHECKSUM` (User scope) + sidecar đúng giá trị; index production SHA `062ec090…` trước = sau smoke + test UI (mtime không đổi — không ghi); smoke B1–B5 (B4 loại) PASS 4/4, exit 0, `index_read_only=true`, `provider_guard=None`; app LAN `0.0.0.0:8501` LISTENING (PID 1632), HTTP 200 qua `127.0.0.1` và `192.168.1.41`, kiểm UI bằng Chromium ẩn; backup `C:\AIOS_p5\library.sqlite.bak-20260930` cùng SHA. Commit `27f1591` chỉ thêm báo cáo (+162/−0); commit `b423211` chỉ sửa `trang-thai.md` (+17/−3); không merge `main` (merge_base = tip main), không đụng ổ D máy nhà, không sửa mã nguồn sản phẩm, không đặt env khác. Hai việc chờ quyết (KHÔNG chặn): (a) firewall máy công ty `BlockInbound` — cần rule admin mới truy cập được từ máy khác; (b) 171 nguồn tài liệu của app chưa có vector + sổ “MOM / Opcenter” 146 nguồn có thể tự enqueue embed khi bị mở — vé cấm embed nên OMP không bấm, cần vé “chuẩn bị tài liệu” riêng hoặc tạm không mở sổ đó. P5 là vé CUỐI cho máy công ty (LỆNH DỪNG 2026-09-29 ~20:16) → đóng mailbox ở `xong`, KHÔNG viết ticket tiếp theo.
Ticket hiện tại: p5-deploy-onnx
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
`commit`: `27f1591` (báo cáo P5) — nhận vé ở `4597dcd`
`bao_cao`: `docs/phieu-viec/ket-qua/p5-bao-cao.md`

Ghi chú: [2026-09-29 ~18:40 +07] Vé trước `pc0575-gui-verify`: **ĐẠT** (3/3 mục, Muse verify
độc lập trên HEAD `bb964df2`). Hệ quả còn tồn đã dọn xong ở vé này: 16 test cũ ở 8 file
(nằm trong 10 file của lệnh pytest) + 2 điểm code chết. P5 (mang cây ONNX) vẫn tạm dừng
chờ user upload model.

Tiến độ: [2026-09-29 18:39 +07] OMP nhận vé `pc0575-test-cleanup` (đã pull `bb964df..b73d0fa`,
HEAD có commit verdict vé trước) — đặt `dang-lam`, commit `ce11d5f`.
Mốc 1 [2026-09-29 18:45 +07]: sửa đủ 16 test ở 8 file sang assert chính sách MỚI + dọn code
chết (`privacy_blocked_status` và `privacy_ai_hard_block_copy` trong `i18n.py`; nhánh badge
`privacy_block` + `render_privacy_block_message`). pytest 10 file của vé: **202 passed,
0 failed** (trước: 16 failed / 186 passed); py_compile 12/12 OK; `import workspace_chat_app` OK.
Mốc 2 [2026-09-29 18:48 +07] CHỐT VÉ: báo cáo tại `docs/phieu-viec/ket-qua/pc0575-test-cleanup.md`
(commit `6f96e9e`), code/test commit `d8e7470` đã push. Trong báo cáo có 8 phát hiện mới
(không tự sửa theo yêu cầu vé) — đáng chú ý nhất: `workspace_chat_ai_answer.py` vẫn còn cổng
chặn `local_only` với 3 test đang xanh ghim hành vi cũ. Chờ Muse review.

Ghi chú: [2026-09-29 ~18:55 +07] Muse review ĐẠT vé `pc0575-test-cleanup` (HEAD `38e4851`): 16 test sửa đúng chính sách mới (diff `d8e7470` đã đối chiếu độc lập: assert hành vi mới, không test nào bị xóa, không assert giả), 2 điểm code chết đã gỡ (grep HEAD: 0 hit `privacy_blocked_status`/`render_privacy_block_message`/`"privacy_block"` trong `src/`; `PRIVACY_AI_HARD_BLOCK_COPY` giữ nguyên như báo cáo), py_compile mọi file đã đổi OK trên VM (VM không có pytest nên chưa chạy lại pytest độc lập — tin theo log `202 passed` của OMP, đã qua 1 vé cùng mức verify). Phạm vi đúng: chỉ `src/` + `tests/`, không đụng `main`, index production, mailbox máy nhà. Theo LỆNH DỪNG của user (2026-09-29 ~18:47 +07): đây là vé CUỐI cho máy công ty — mailbox-pc0575 đóng ở `xong`, KHÔNG viết ticket tiếp theo. Phát hiện còn tồn (ghi để mai user xử lý, không tự sửa theo lệnh dừng): `workspace_chat_ai_answer.py` vẫn còn cổng chặn `local_only` với 3 test xanh ghim hành vi cũ (OMP ghi trong báo cáo).

- 2026-09-29 ~20:16 +07: user duyệt P5 (toàn bộ 5 chặng). Kích hoạt vé P5, trạng thái `moi`. Máy đang tắt — watcher sẽ nhận khi bật lại.

Tiến độ: [2026-09-30 08:28 +07] OMP nhận vé `p5-deploy-onnx` (P5, watcher tự mở 1/4 lúc 08:25). Cổng đã mở:
báo cáo `docs/phieu-viec/ket-qua/onnx-upload-drive.md` xác nhận zip model trên Drive AIOS_Data đã
được tải lại ẩn danh khớp SHA-256. Bắt đầu chặng 1: tải zip + giải nén + verify cây ONNX.
Mốc 1 [2026-09-30 08:29 +07] (chặng 1): tải zip model từ Drive (link trong `onnx-upload-drive.md`) —
1.326.939.447 byte; SHA-256 zip = `4239479b…bf2f3c` khớp báo cáo (đo chéo sha256sum + certutil + Python).
Mốc 2 [2026-09-30 08:36 +07] (chặng 1–2): giải nén `models\bge-m3-onnx-fp32` (9 file, 2.289.625.694 byte);
`sha256_model_tree` = `sha256:9f81075f…b11093` **KHỚP seal**; `resolve_onnx_checksum` (sidecar
`models\bge-m3-onnx-fp32.sha256`) trả đúng chuỗi; fingerprint tái tạo `016c5255…` khớp 107.331 vector
dense trong index → **không cần embed lại**. Đặt env `AIOS_BGE_ONNX_MODEL_CHECKSUM` = `sha256:9f81075f…`
(User scope) theo bước 3 của vé. Index production trước test: `062ec090…` (2.552.659.968 byte, khớp seal P2).
Mốc 3 [2026-09-30 08:42 +07] (chặng 4): chạy smoke B1–B5 (B4 loại) bằng `scratch\p2_b7_smoke.py`
(đọc-only, `index_read_only=true`); sau đó chặng 5 mở LAN cho cả phòng.
Mốc 4 [2026-09-30 09:15 +07] (chặng 4 XONG): smoke **PASS cả 4 câu** (exit 0, tổng 1816 s):
B1 533,8 s / B2 343,5 s / B3 433,7 s / B5 459,8 s — không câu nào thiếu chuỗi bắt buộc
(`11922/12860/12626`, `YY2-Z151/Z152`, `nvarchar(4000)`, `HOUSE_METHOD '0'/'1'`),
`candidate_count` 210–274, `filtered_as_stale_count=0`, `provider_guard=None` (không gọi AI ngoài).
Report: `scratch\p2_b7_report.json` (chỉ đọc, không ghi index). Tiếp: backup index + mở LAN.
Mốc 5 [2026-09-30 09:38 +07] CHỐT VÉ: app đã mở LAN — `0.0.0.0:8501` LISTENING (PID 1632), HTTP 200 qua
`127.0.0.1` và `192.168.1.41`; kiểm UI bằng Chromium ẩn (màn chọn sổ OK; gửi thử 1 câu hỏi trong sổ
"Điều tra lỗi LSU" → app báo đúng "Tìm kiếm tài liệu chưa sẵn sàng…" + nút thử lại; index/ledger **không đổi**).
Backup index: `C:\AIOS_p5\library.sqlite.bak-20260930` (cùng SHA-256 `062ec090…`). Báo cáo:
`docs/phieu-viec/ket-qua/p5-bao-cao.md` (commit `27f1591`).
Hai điểm chờ Muse/user quyết (báo cáo mục 5.3 + 6): (a) firewall máy công ty `BlockInbound` — cần rule admin
(lệnh kèm trong báo cáo) mới truy cập được từ máy khác; (b) 171 nguồn tài liệu của app chưa có vector trong
index — muốn app tự trả lời phải "chuẩn bị" (embed) trên máy này, vé **cấm embed lại** nên OMP không bấm;
sổ "MOM / Opcenter" (CONV-EEA591C6, 146 nguồn chưa có dòng ledger) sẽ tự xếp hàng embed nếu bị mở.
