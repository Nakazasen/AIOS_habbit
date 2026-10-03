# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `INDEX-SPLIT-A2` — [VM] Muse sửa bộ phân loại lĩnh vực sau dry-run (453/889 document confidence=0). OMP KHÔNG chạy gì thêm, chờ vé R2.
- `ghi_chu`: 2026-10-03 ~21:25 +07 — Muse đã nhận escalation cho-muse của INDEX-SPLIT-HOME và BẮT ĐẦU xử lý trong SLA. Nguyên nhân đã xác định: taxonomy từ khóa Phase A bỏ sót từ vựng thật trong kho (tiền tố KTD-, mã lỗi C####/JAM####, từ Nhật 自己診断/不具合/異常/エラー, DRBFM...). Hướng sửa: bổ sung quy tắc theo 372 tên file thật + phân loại bằng nội dung chunk + fallback centroid từ vector sẵn có. Quyết định: chọn phương án (3) cải thiện phân loại rồi dry-run lại; KHÔNG tách với nhãn ép bừa, KHÔNG thêm khối thứ 4 (user chốt đúng 3 khối).
- `ghi_chu` (cổng): 2026-10-03 21:25 +07 — Kiểm cổng gate vé INDEX-SPLIT-A2 (watcher tự mở lại OMP RELAUNCH 1/4 lúc 21:23:04, launchStallCount=1). Điều kiện mở chưa tới: prompt.md vẫn là INDEX-SPLIT-HOME, chưa có vé R2, Muse đang sửa bộ phân loại trên VM. Không tách index, không đặt cho-muse, dừng.
