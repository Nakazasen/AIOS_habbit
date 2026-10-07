# VÉ: SRC-PROBE-TAKEOVER-PC0575 (OMP công ty nhận nốt vé SRC-PROBE từ opencode)

- Mã vé: `SRC-PROBE-TAKEOVER-PC0575`
- Vai trò: thợ phụ (phân vai user chốt 2026-10-08 ~06:39 +07: agy = thợ chính, OMP = thợ phụ, opencode đóng băng)
- Máy: công ty KDTVN-PC0575 (CPU-only)
- Báo cáo: `docs/phieu-viec/ket-qua/src-probe-pc0575.md` (báo cáo opencode đã lập — bổ sung tiếp, không lập mới)
- Spec gốc: đọc nguyên văn vé `SRC-PROBE-PC0575` tại `docs/phieu-viec/mailbox-pc0575-opencode/prompt.md` — phạm vi và rào của vé này giữ nguyên, vé takeover chỉ đổi người làm nốt.

## Trạng thái khi nhận (theo mailbox-pc0575-opencode, mốc 07/10 18:22)

- Cổng bao phủ 29/29 PASS; đối chứng âm 5/5 chặn đúng; đối chứng dương 5/5 qua; kiểm nhẹ theo mã 29/29 trong 0,29 giây.
- Mẫu truy vấn đầy đủ 3 tệp (gồm tệp từng kẹt `wsc-015067b7`) bị HOÃN vì máy đang bận (15 tiến trình python tại thời điểm đó) — đây là phần còn lại duy nhất của vé.

## Việc phải làm

1. Kiểm tra hiện trạng: tiến trình mẫu nền có còn sống không, kết quả mẫu đã có phần nào chưa, tải máy lúc nhận (số tiến trình python / CPU). Ghi mốc nhận vé kèm hiện trạng vào trang-thai.
2. Nếu mẫu chưa xong và máy đủ rảnh: chạy nốt mẫu truy vấn đầy đủ đúng spec gốc — tiến trình nền tách phiên, trần 900 giây/truy vấn, có file tiến độ để sống sót qua các ca. Máy còn bận: ghi dòng `cho-cong` chờ máy rảnh (hạn cụ thể) và theo dõi, không ép chạy khi máy đang tải nặng.
3. Tổng hợp kết quả mẫu vào báo cáo + đúng 1 dòng kết luận việc kèm `FP-TOTAL-RECONCILE` như spec gốc đã định.
4. Ghi mốc **"mẫu xong"** vào trang-thai (mốc này mở đường cho vé `RETRIEVAL-PERF-DIAG-PC0575` của agy) rồi đặt `xong-cho-duyet`.

## Rào cứng

- Chỉ đọc là chính (mẫu truy vấn chỉ đọc); không ghi chỉ mục; không sửa `src/` ngoài phạm vi spec gốc cho phép; không merge `main`.
- Mạng theo quy ước `Chuyen-Mang.ps1` của PC0575; heartbeat mốc tối thiểu 15 phút/lần khi mẫu đang chạy.
