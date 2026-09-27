# Vé P1 (mẫu) — Đóng dấu kho thử thành kho thật (máy nhà)

Trạng thái: **CHỜ** — chỉ chạy SAU khi migration 99.003 vector hoàn tất và Vé 0.3
được duyệt. **CẤM** đụng mẻ migration đang chạy.

Ngày viết: 2026-09-27 (Muse, theo lệnh user 22:43).

## Bối cảnh

- Kho canary `tri_thuc` đang migration 99.003 vector sang ONNX fp32 (Vé 0.3).
- App production đang đọc kho `workspace_chat_rag_v2_production/workspace_chat.sqlite`.
- **CẤM** app đọc kho đang nhúng dở — chỉ kho đã "đóng dấu" mới được coi là kho chạy thật.

## Cấm kỵ

- Không chạy khi migration chưa đạt 99.003/99.003 (pending 0) và Vé 0.3 chưa duyệt.
- Không ghi đè kho production khi chưa đủ "dấu" toàn vẹn.
- Không đụng `main`; commit riêng trên branch vé.

## Cách làm (đúng thứ tự)

1. Kiểm toàn vẹn kho canary `tri_thuc`:
   - `PRAGMA integrity_check` = `ok`.
   - Đếm vector ONNX = 99.003, pending = 0.
   - Fingerprint ONNX `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` khớp.
2. Backup kho production hiện tại (file sibling, `integrity_check=ok`) TRƯỚC khi thay.
3. Copy kho canary → `workspace_chat_rag_v2_production/workspace_chat.sqlite`
   (copy rồi so sha256 + kích thước hai bản — phải khớp 100%).
4. App trỏ sang kho mới, chạy thử B1–B5: đạt, không abstain/timeout bất thường,
   ghi nhận latency từng câu.
5. Chỉ khi B1–B5 đạt → **đóng dấu**: ghi commit SHA + sha256 file + ngày giờ
   vào báo cáo → từ đây mới coi là "kho chạy thật".

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE_P1_dong-dau-kho-that.md` gồm:
integrity, số vector/pending, fingerprint, sha256 trước/sau copy,
kết quả B1–B5 + latency, thời điểm đóng dấu, hostname máy chạy.
