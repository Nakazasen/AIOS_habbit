# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `dang-lam`
Ticket hiện tại: p4-deploy-constants
Ghi chú: [2026-09-29 17:16 +07] OMP nhận P4 — chỉ đọc + tính toán: (1) lấy fingerprint đầy đủ 64 hex từ index production (mode=ro), (2) dò provenance trong library.sqlite, (3) quét tổ hợp 9 trường SemanticModelDescriptor.fingerprint để tái tạo `016c5255…`, (4) kết luận manifest b1d887e0/728c9eb7. Không đổi env, không ghi index, không embed. | ĐỔI CŨ: [2026-09-29 17:14 +07] Verdict P3 của Muse: ĐẠT (chẩn đoán). Nguyên nhân gốc 0/171 = thiếu env ONNX → BGE worker chết → fail-closed; app đọc đúng index production (SHA 062ec090… khớp P2); 171 nguồn temporary thật sự chưa có vector; "68" là ảnh chụp giữa lượt. CẤM đặt env bừa: sai fingerprint → app coi 107.331 vector cũ hết hạn → embed lại hàng loạt. P4 (mới): chốt bộ hằng số deploy tái tạo đúng 016c5255… — chỉ đọc + tính toán, cấm đổi env máy, cấm ghi index, cấm embed.
Commit mới nhất: `489f3ff`
Đường dẫn báo cáo P3: `docs/phieu-viec/ket-qua/p3-bao-cao.md`
Đường dẫn prompt P4: `docs/phieu-viec/mailbox-pc0575/prompt.md`
