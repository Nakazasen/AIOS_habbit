# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `xong-cho-duyet`
Ticket hiện tại: pc0575-gui-verify
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`

Ghi chú: [2026-09-29 ~18:20 +07] User yêu cầu máy công ty pull code chính sách/GUI mới
và xác nhận. P5 (cây ONNX) vẫn tạm dừng chờ upload model — ticket này độc lập.
Commit mới nhất: `8998fa1` (đã pull — đủ `f27081d` + `941c31c`)
Đường dẫn báo cáo: `docs/phieu-viec/ket-qua/pc0575-gui-verify.md`

Kết quả: 3/3 mục của vé ĐẠT — (1) `check_privacy_gate` hết nhánh chặn `local_only`
(smoke 5/5 đúng, kể cả provider EXTERNAL + pack `local_only` → cho phép); (2)
`workspace_chat_ui.py` 0 hit dòng cảnh báo chặn `privacy_blocked_status`; (3) `py_compile`
13/13 file OK. Phát hiện phụ (báo trong file kết quả): 16 test cũ ở 10 file liên quan còn
assert chính sách chặn CŨ nên FAIL (186 pass) — đề nghị Muse dọn ở vé riêng.

- Ghi chú: [2026-09-29 18:34 +07] XONG-CHO-DUYET — báo cáo tại `docs/phieu-viec/ket-qua/pc0575-gui-verify.md`; 3/3 mục ĐẠT, py_compile 13/13 OK, smoke hành vi 5/5; 16 test cũ FAIL do chưa cập nhật theo chính sách mới (OMP không sửa code). Chờ Muse review.

Tiến độ: [2026-09-29 18:30 +07] Nhận vé — điều kiện mở vé ĐÃ ĐỦ (2 commit có mặt sau pull).
Tiến độ: [2026-09-29 18:31 +07] Mốc 2 — kiểm chỉ-đọc + `py_compile` 13/13 OK + smoke hành vi 5/5 đúng; 2 test cũ của Muse FAIL do còn assert chính sách cũ.
Tiến độ: [2026-09-29 18:34 +07] Mốc 3 — chạy 10 file test liên quan (16 FAIL / 186 PASS, toàn bộ FAIL do test cũ), viết báo cáo, chốt `xong-cho-duyet`.
