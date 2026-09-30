# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `xong-cho-duyet`
Ticket hiện tại: p5b-kiem-tra-mang-moi
`commit`: `f74508f`
`bao_cao`: `docs/phieu-viec/ket-qua/p5b-mang-moi.md`
`ghi_chu`: 2026-09-30 11:10 +07 — P5b xong phần máy này: mạng `KT_CHETAO` / IP `192.168.1.41` (profile Public); app chạy (PID 1632, `0.0.0.0:8501`) render OK qua `127.0.0.1` và `192.168.1.41`; **máy khác bị firewall chặn**: rule Block inbound TCP đang bật cho đúng python.exe của app (profile Public), không có rule mở 8501, mặc định inbound = Block. Máy không có admin → cần IT/user chạy mục 5 của báo cáo (xóa rule Block + thêm rule allow gồm profile `public`) rồi nhờ test lại từ điện thoại. Chưa test vật lý 2 thiết bị được từ phiên OMP.
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`

Lịch sử: P5 (deploy model ONNX + mở LAN) **ĐẠT** 2026-09-30 ~09:5x +07 (commit `97207d5`).
Máy chuyển sang mạng ngoài → phát hành vé P5b kiểm tra lại truy cập từ máy khác trên mạng mới.
