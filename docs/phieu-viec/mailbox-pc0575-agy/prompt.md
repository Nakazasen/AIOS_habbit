# Vé PREP-WIRE-CAGENT-SPEC — Đặc tả kỹ thuật nối C-Agent cho vé WIRE

**Thợ:** agy (Antigravity CLI)
**Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only)
**Thư mục làm việc DUY NHẤT:** `D:\Sandbox\AIOS_habbit`
**Role OMP gợi ý:** SMOL/TINY (viết đặc tả, không code).
**Mục đích:** có sẵn đặc tả kỹ thuật để vé `WIRE-QA-CAGENT-PC0575` implement nối hỏi đáp vào giao diện qua lane C-Agent, không phải mày mò API từ đầu.

## Bối cảnh

Vé `PROBE-CAGENT-PC0575` đã ĐẠT: C-Agent **sống** trên PC0575, gọi đúng `src/aios_habit/cagent_api.py::call_cagent_prediction`, endpoint `https://kdtvn-ai.cmcts.vn/api/v1/prediction/1881aa32-c996-4e6f-9257-78246177ba9f`, 1 câu kiểm tra phản hồi thành công trong 30,76 giây.
Báo cáo chi tiết: `docs/phieu-viec/ket-qua/probe-cagent-pc0575.md` — **đọc kỹ báo cáo này trước khi viết đặc tả.**

## Việc cần làm

### Bước 1 — Đọc báo cáo probe + code hiện tại
- Đọc `docs/phieu-viec/ket-qua/probe-cagent-pc0575.md` (toàn bộ).
- Đọc `src/aios_habit/cagent_api.py` (hàm `call_cagent_prediction`): tham số, format request/response, xử lý lỗi hiện có.

### Bước 2 — Viết đặc tả
Viết `docs/phieu-viec/ket-qua/wire-cagent-spec.md` gồm:
1. **API contract:** endpoint, method, headers, format request (lấy câu hỏi + context từ 3.392 cặp Q&A như thế nào), format response.
2. **Timeout/retry:** đề xuất timeout (dựa trên 30,76 giây đã đo), số lần retry, backoff.
3. **Error handling:** các lỗi đã gặp/biết (khóa cloud `unknown_error` từng xảy ra 02/10, timeout, mạng), cách phát hiện và thông báo cho user.
4. **Nhãn bản thảo:** yêu cầu hiển thị `Bản thảo — chưa qua chuyên gia duyệt` với mọi câu trả lời từ Q&A (theo rào đã chốt).
5. **Demo 3 câu:** đề xuất 3 câu hỏi mẫu + kỳ vọng để vé WIRE demo (lấy từ 3.392 cặp, mỗi category 1 câu).

### Bước 3 — Xong
- `xong-cho-duyet` khi đặc tả đủ 5 mục trên, không bịa thông số (mọi số phải dẫn từ báo cáo probe hoặc code).

## Cấm kỵ
- Chỉ viết đặc tả (.md), không sửa code.
- Không cần runtime/app — vé này thuần đọc + viết tài liệu.
- Commit riêng nhánh `phieu-viec/rag-fix1`, không đụng `main`, không force-push.
