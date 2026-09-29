# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `dang-lam`
Ticket hiện tại: pc0575-gui-verify
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`

Ghi chú: [2026-09-29 ~18:20 +07] User yêu cầu máy công ty pull code chính sách/GUI mới
và xác nhận. P5 (cây ONNX) vẫn tạm dừng chờ upload model — ticket này độc lập.
Commit mới nhất: `8998fa1`

- Ghi chú: [2026-09-29 18:31 +07] Mốc 2 — kiểm xong 3/3 mục của vé: cổng `check_privacy_gate` hết nhánh chặn `local_only` (smoke 5/5 đúng, kể cả provider EXTERNAL + pack local_only → cho phép); `workspace_chat_ui.py` 0 hit dòng cảnh báo chặn; `py_compile` 13/13 file OK. Phát hiện phụ: `tests/test_provider_safety.py` còn 2 test khẳng định hành vi chặn CŨ nên giờ FAIL (2 failed / 1 passed) — cần Muse xử lý ở vé sau (OMP không sửa code theo đúng vé). Đang viết báo cáo.

Tiến độ: [2026-09-29 18:30 +07] Nhận vé — điều kiện mở vé ĐÃ ĐỦ (2 commit có mặt sau pull).
Tiến độ: [2026-09-29 18:31 +07] Mốc 2 — kiểm chỉ-đọc xong + `py_compile` 13/13 OK + smoke hành vi 5/5 đúng; 2 test cũ của Muse FAIL do còn assert chính sách cũ (ghi rõ trong báo cáo).
