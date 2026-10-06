# Vé ROUTER-POOL-COMMANDCODE-HOME — Trỏ tuyến tổng hợp sang pool Command Code + đo lại

**Máy thực hiện:** NHÀ h410asrock (thợ OMP).
**Role gợi ý:** DEFAULT (cấu hình + đo).
**Lệnh user (06:01 07/10):** đã kết nối thêm provider trên Command Code (gói $10) — trỏ Router sang pool mới và đo lại.

## Bối cảnh

- Tuyến tổng hợp hiện tại: harness → cầu `127.0.0.1:8585` → Nakazasen Router → **một tuyến Gemini duy nhất** (gemini-2.5-flash). Lượt đo đầu: 29/29 lượt gọi lỗi `rate_limited`; các lượt sau vẫn rớt câu vì limit + provider thiếu ổn định.
- User đã kết nối thêm provider trong tài khoản Command Code của user. Pool mới phải có **failover**: tuyến chính bị rate-limit/5xx thì Router chuyển tuyến khác, thay vì harness rơi về trích cục bộ.
- Vé này chạy SAU `RAG-CLAIM-BUDGET-HOME` (đang làm).

## Bước 1 — Khảo sát chỗ cấu hình (chỉ đọc)

Đã tra code (Muse): tuyến tổng hợp đọc cấu hình từ biến môi trường —
`AIOS_LOCAL_AI_ENDPOINT`, `AIOS_LOCAL_AI_MODEL`, `AIOS_LOCAL_AI_API_KEY`
(slot "OpenAI-compatible", `ai_provider_bridge.py` / `ai_router.py`), cộng công tắc
`AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS`. Command Code đi vào đúng slot này.
Việc của thợ: tìm trên máy nhà xem các biến này hiện đang được đặt ở đâu (file env/launcher
của app) — ghi vào báo cáo: đường dẫn file — **TUYỆT ĐỐI không ghi giá trị key**.

## Bước 2 — Chuẩn bị chỗ nhập cho user (key do user dán tại máy)

- Tạo/chuẩn bị **đúng 1 file cấu hình local** mà app thực sự đọc trên máy nhà (nằm ngoài Git
  hoặc đã gitignore — kiểm tra trước; chứa key thì KHÔNG commit trong mọi trường hợp).
- Điền sẵn 2 dòng endpoint + model của Command Code, để trống đúng 1 dòng
  `AIOS_LOCAL_AI_API_KEY=` cho user dán key. Bật công tắc cloud + failover:
  model chính + **ít nhất 1 model failover** từ pool user đã kết nối; Router chuyển tuyến
  khi rate-limit/5xx.
- Ghi đường dẫn file + tên 3 dòng vào mailbox để điều phối báo user mở đúng file đó.
  KHÔNG nhận key qua mailbox/chat/log.

## Bước 3 — Kiểm chứng tuyến mới

- Gọi thử vài lượt tổng hợp qua tuyến mới: ghi provider/model thực trả lời + độ trễ + lỗi nếu có (che key, không log payload chứa secret).
- Xác nhận đường fallback cục bộ vẫn nguyên (tuyến chết hẳn thì về trích cục bộ như cũ, không sập lane).

## Bước 4 — Đo lại

- Trọn lane RAG 50 câu, **CPU-only** (bằng chứng device = CPU), index chỉ-đọc + SHA trước/sau, cùng rubric, checkpoint từng câu, heartbeat 15 phút.
- Đối chiếu với FIX1 (GPA 1,29, validated 6) và SYNTH (GPA 1,22, validated 9): số validated, số lỗi provider, số fallback, GPA. Ghi rõ model nào trả lời từng câu nếu lấy được.

## Danh sách model — ĐÃ TRA GIÁ CHÍNH THỨC Command Code (trang GOAT, 07/10)

Nguồn: https://commandcode.ai/docs/plans/goat (Muse tra trực tiếp). Gói GOAT $10/tháng =
$70 credits (trần $14/5 giờ, $35/tuần); model tính phí trừ vào credits, hết trần thì **dừng**
— trừ model Free. Nhãn "free" trong danh sách OMP là của kết nối khác (Mistral/xAI/NVIDIA
trực tiếp), KHÔNG áp cho đường Command Code. `mistral-large-4` qua Command Code = $1,36/$4,18
mỗi 1M token — LOẠI. `gpt-6.1-sol` không có bản free trên GOAT — LOẠI.

**Tầng 1 — Free thật trên GOAT (chỉ 3 con, không trừ credits, chạy cả khi hết trần):**
- `inclusionai/ling-3.1-flash:free` — context 262K (chính).
- `inclusionai/ling-3.0-flash-sante:free` — 262K (failover 1).
- `poolside/laguna-s-2.1-free` — 256K (failover 2).
Cả 3 là model flash chưa có điểm benchmark — chất lượng do lượt đo quyết định.

**Tầng 2 — Giá rẻ (chỉ khi tầng 1 không tới được hoặc đo quá tệ; user đã duyệt hướng này):**
- DeepSeek V4.1 Flash — $0,15/$0,60 mỗi 1M (giờ cao điểm $0,30/$1,20), hạn mức ~30.800 lượt/5 giờ.
- Dự phòng: Muse Spark 1.3 Contributor — $0,10/$0,20 mỗi 1M.

**Điều kiện cứng:** gọi thử từng ứng viên QUA Provider API của Command Code (key của user)
trước khi đo; chỉ con trả lời thật mới vào pool; ghi rõ con bị loại và lý do. Loại hẳn model
không phải chat (image/TTS/STT). Đo bằng model tính phí phải ghi ước lượng credits tiêu thụ.

## Rào cứng

- Không merge `main`. Không ghi index. Python 3.11. Không nới chuẩn kiểm định để lấy điểm.
- Không để lộ key trong bất kỳ file/log/báo cáo/commit nào.

## Báo cáo

`docs/phieu-viec/ket-qua/router-pool-commandcode-home.md` — chỗ cấu hình (file + trường, không giá trị), cấu hình trước/sau, kết quả gọi thử, bảng đo lại đối chiếu.
