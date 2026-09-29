# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `xong-cho-duyet`
Ticket hiện tại: p3-app-readiness
Ghi chú: [2026-09-29 17:08 +07] P3 xong (chỉ đọc, không sửa gì): app đọc ĐÚNG index production (SHA 062ec090…ef8ca khớp P2, index không bị ghi). Nguyên nhân 0/171: thiếu env ONNX nên worker BGE chết → 171/171 ledger `failed`. CẢNH BÁO: đặt env 'cho chạy được' sẽ làm định danh kỳ vọng 8274fbb0… khác định danh vector trong index 016c5255… ⇒ nguy cơ embed lại toàn bộ 107.331 vector; cần Muse chốt bộ hằng số deploy trước.
Commit mới nhất: `489f3ff`
Đường dẫn báo cáo: `docs/phieu-viec/ket-qua/p3-bao-cao.md`
