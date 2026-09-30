# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `dang-lam`
Ticket hiện tại: p5b-kiem-tra-mang-moi
`commit`: `4ffbd59` (mốc 1)
`bao_cao`: `docs/phieu-viec/ket-qua/p5b-mang-moi.md` (đang viết)
`ghi_chu`: 2026-09-30 11:07 +07 — Xong bước 1–2: mạng `KT_CHETAO`, IP `192.168.1.41/24`, profile firewall Public; app vẫn chạy (PID 1632, `0.0.0.0:8501`), render đủ UI bằng trình duyệt thật qua `127.0.0.1:8501` và `192.168.1.41:8501`. Bước 3–4: có rule Block inbound TCP cho đúng python.exe của app (profile Public, đang bật), không có rule mở 8501, mặc định inbound = Block ⇒ máy khác dự kiến bị chặn; máy không có quyền admin để sửa. Đang viết báo cáo.
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`

Lịch sử: P5 (deploy model ONNX + mở LAN) **ĐẠT** 2026-09-30 ~09:5x +07 (commit `97207d5`).
Máy chuyển sang mạng ngoài → phát hành vé P5b kiểm tra lại truy cập từ máy khác trên mạng mới.
