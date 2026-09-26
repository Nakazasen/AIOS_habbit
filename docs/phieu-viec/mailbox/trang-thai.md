# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: D3 — baseline B1–B5 (+H3) trên corpus đầy đủ, worker ONNX fp32 (chỉ đọc)
- Ticket trước: D2 — ĐẠT (commit `20bce54`, Muse review 2026-09-26)
- Commit mới nhất: `0311665`
- Cập nhật lần cuối: 2026-09-26 16:27 +07 (OMP, máy `h410asrock` — đã chạy 6/6 câu ONNX trên corpus 74 tài liệu, đối chiếu index không đổi)
- Ghi chú: worker ONNX fp32 khởi tạo 27,46 giây (<300 giây); B1–B5 và H3 đều chạy xong, không abstain/timeout. Đang hoàn tất đối chiếu và báo cáo D3.
