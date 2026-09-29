# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: Ticket xếp hàng 1 — `stale-check`: đếm document stale thực tế (chỉ đọc, ~5 phút).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `verdict_e2v4`: **ĐẠT** (Muse verify độc lập 2026-09-29 ~22:45 +07 trên báo cáo `VE_E2_vong4_chon-dong.md` commit `fe409e9`): B1/B2/B3/B5 ĐẠT nội dung (B2 giữ `YY2-Z151.exe`/`YY2-Z152.exe`; B3 giữ `nvarchar(4000)`; B5 định nghĩa HOUSE_METHOD đúng ngữ cảnh), latency 26,8/10,6/10,7/12,9/10,7s (< 180s), không lỗi worker, không restart; B4 chạy nhưng loại khỏi chấm. Không ghi D: snapshot cây 114.055 tệp 0 thêm/0 xóa/0 đổi, SHA index `062ec090…` + mtime nguyên. Fail-closed: không công cụ AI/mạng ngoài nào được gọi trong lượt v4 (cấm `functions.find` từ đầu vé), 6 khóa cloud còn nguyên trong env, `provider_used=false`, worker stderr 0 dòng provider. Nguyên văn câu trả lời chỉ lưu local `C:/AIOS_p1_4/out/e2v4/`, không đưa vào Git — commit `fe409e9` chỉ đổi 2 tệp markdown, không code, không `main`.
- Điều tra sự cố `functions.find` vòng 3 (trung thực, không suy đoán): session log + kho log OMP cục bộ không lưu tên 19 tệp → không khôi phục được danh sách; 27 request đều HTTP 402 `insufficient credits`, `0 tokens` (không token nào được xử lý phía server). Từ vòng 4: **CẤM `functions.find` và mọi công cụ AI/mạng ngoài trong vé E-series** — tìm tệp chỉ dùng `ripgrep`/`grep`/`git ls-files` cục bộ. Rủi ro còn tồn đã ghi nhận (không che giấu): không loại trừ tuyệt đối được việc nội dung request đã rời máy ở vòng 3 — nhưng không còn hành động điều tra nào có thể làm thêm (log không có dữ liệu), nên không giữ E2 mở thêm vòng nữa.
- E2 series KHÉP: E2v2 CHƯA ĐẠT → fix `b8f06d6` → E2v3 CHƯA ĐẠT (B2 worker + functions.find) → fix `ada3ed5` (giữ nguyên, cổng Phase B) → E2v4 ĐẠT. Chuỗi E tiếp tục ở vé xếp hàng `E3`/`E4` theo thứ tự dưới.

- `hang-cho` (theo thứ tự, user yêu cầu 2026-09-29):
  2. `don-o-c` (`prompt-queue-don-o-c.md`) — dọn ổ C lấy chỗ trống TRƯỚC.
  3. `onnx-upload-drive` (`prompt-queue-onnx-upload.md`, user yêu cầu ~18:50 +07) — nén + upload model.
  4. `E3` (`prompt-queue-e3.md`) — dọn XML thô ở extractor (code + test).
  5. `E4` (`prompt-queue-e4.md`) — default backend ONNX fp32 (giữ BGE_BACKEND override, fail-closed).
  6. `buoc0-deploy` (`prompt-queue-buoc0-deploy.md`) — deploy Bước 0–5 lên máy nhà (DEADLINE 30/09 23:59).
  7. `TOOL-1` (`prompt-queue-tool1.md`) — kiểm kê tool chưa nối vào chat.
  8. `TOOL-2` (`prompt-queue-tool2.md`) — khung action trong chat.
  9. `TOOL-3` (`prompt-queue-tool3.md`) — nối benchmark vào chat.
  10. `TOOL-4` (`prompt-queue-tool4.md`) — nối interview + prediction vào chat.
  11. `TOOL-5` (`prompt-queue-tool5.md`) — nối visual maps vào chat.
  (Mục 1 `stale-check` đang chạy — phát hành từ vé này.)
