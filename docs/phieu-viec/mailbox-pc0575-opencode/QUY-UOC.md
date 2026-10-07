# Quy ước riêng — mailbox-pc0575-opencode — KDTVN-PC0575 (thợ opencode)

Quy ước chung của hệ mailbox: xem `docs/phieu-viec/mailbox/QUY-UOC.md`.
File này chỉ ghi phần RIÊNG của máy công ty KDTVN-PC0575.

## Công tắc mạng PC0575 (thợ tự chuyển, KHÔNG gọi user, KHÔNG chờ Muse xác nhận)

- Lệnh: `powershell -ExecutionPolicy Bypass -File "D:\Sandbox\agent-mailbox\Chuyen-Mang.ps1" -Mang ngoai|congty`
  - Không tham số = chỉ xem trạng thái hiện tại.
  - Output: `MANG=<SSID>`, `DRIVE=OK/FAIL`.
- Ý nghĩa:
  - `ngoai` = `KT_CHETAO`: ra được Google Drive, KHÔNG vào được LAN công ty
    (endpoint C-Agent `kdtvn-ai.cmcts.vn` KHÔNG chạy trên mạng này — cấm thử).
  - `congty` = `vn-kdwireless`: vào được LAN/C-Agent, Drive hên xui.
- Áp dụng cho MỌI vé trên PC0575:
  - Vé nào cần tải Drive: thợ TỰ mở đầu bằng `-Mang ngoai`, kiểm output `DRIVE=OK`
    rồi mới tải. `DRIVE=FAIL` thì ghi mốc mailbox và chờ nhịp sau — không tải bừa.
  - Tải xong: chuyển về `-Mang congty` nếu vé tiếp theo cần LAN/C-Agent.
  - Cơ chế này THAY cổng cũ "dừng chờ user chuyển mạng + Muse ghi dòng xác nhận"
    (user chốt 2026-10-07).

## Nghiệm thu bằng SỬ DỤNG THẬT (user chốt 2026-10-07 — chương trình sắp đưa vào sử dụng)

- Từ nay trọng tâm của mọi vé là: **hiệu suất khi dùng thật + giao diện**, không phải chỉ xanh file test.
- Nghiệm thu bắt buộc: thợ phải **tự dùng chương trình như người dùng cuối** — tự động hoá thao tác thật trên app đang chạy (mở sổ, mở trò chuyện, hỏi đáp đầu-cuối, đi hết luồng của tính năng) — và ghi vào báo cáo: số đo thật (thời gian mở, thời gian trả lời), ảnh chụp màn hình thật, đáp án thật nhận được.
- Chạy file test (pytest...) chỉ là phụ trợ để giữ hồi quy, **không thay thế** nghiệm thu sử dụng thật. Vé nào nộp mà chỉ có kết quả test file, không có bằng chứng dùng thật, điều phối sẽ chấm CHƯA ĐẠT.
- Gặp lỗi khi dùng thật (chậm, treo, xấu, khó hiểu): ghi thành phát hiện trong báo cáo kèm bằng chứng, không lấp liếm bằng kết quả test.
