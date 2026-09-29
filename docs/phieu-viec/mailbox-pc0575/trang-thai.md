# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `xong-cho-duyet`
Ticket hiện tại: pc0575-test-cleanup
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
`commit`: `6f96e9e` (báo cáo) — code/test ở `d8e7470`
`bao_cao`: `docs/phieu-viec/ket-qua/pc0575-test-cleanup.md`

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
