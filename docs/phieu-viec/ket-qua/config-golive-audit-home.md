# Báo cáo vé CONFIG-GOLIVE-AUDIT-HOME — rà cấu hình chạy thật máy nhà + sửa điểm lệch thời gian chờ

- **Mã vé:** `CONFIG-GOLIVE-AUDIT-HOME`
- **Máy thực hiện:** NHÀ `h410asrock` (OMP — thợ phụ, chế độ chỉ-CPU).
- **Thời điểm:** 2026-10-09 08:40 – 13:10 +07.
- **Căn cứ:** 3 quyết định đã chốt qua các vé gần đây — (1) chuỗi tổng hợp 3 tầng ở vé `CONFIG-SYNTH-TIERS-HOME`; (2) công tắc mở cổng tổng hợp cho sổ ở giao diện tại vé `UI-LOCALONLY-SYNTH-OPEN-HOME`; (3) tồn dư thời gian chờ 30 giây có thể cắt lượt thử lại ghi ở vé `SYNTH-DEEPSEEK-PROTOCOL-HOME` §7.1.
- **Cách làm:** đọc tệp `.env` thật của máy nhà (chỉ ghi tên biến + giá trị không nhạy cảm; khóa chỉ ghi "có mặt"), đối chiếu từng biến theo quyết định, sửa đúng điểm lệch thời gian chờ, xác minh hiệu lực bằng mã nguồn thật, rồi chứng minh bằng một lượt hỏi thật qua giao diện.
- **Rào cứng giữ nguyên:** không in ký tự nào của khóa truy cập; không commit `.env`; không ghi chỉ mục (băm trước/sau khớp); không merge `main`; không đổi model hay thứ tự chuỗi.

## 1. Bảng đối chiếu cấu hình (biến chạy thật của máy nhà)

Nguồn giá trị: tệp `.env` máy nhà (ngoài Git — đúng luật bảo mật) + các biến do lệnh chạy thật `RUN_AIOS_WORKSPACE_CHAT.bat` đặt ở mức tiến trình.

| Tên biến | Giá trị hiện tại | Giá trị theo quyết định đã chốt | Khớp/lệch |
|---|---|---|---|
| `AIOS_LOCAL_AI_ENDPOINT` | `https://api.commandcode.ai/provider/v1/chat/completions` | cổng pool Command Code (vé `ROUTER-POOL-COMMANDCODE-HOME`, `APP-E2E-POOL-HOME`) | KHỚP |
| `AIOS_LOCAL_AI_MODEL` | `inclusionai/ling-3.1-flash:free` | tầng 1 — model chính miễn phí | KHỚP |
| `AIOS_LOCAL_AI_FAILOVER_MODELS` | `poolside/laguna-s-2.1-free,deepseek/deepseek-v4.1-flash` | tầng 2 (dự phòng nhanh, miễn phí) → tầng 3 (dự phòng chất lượng, có phí), đúng thứ tự | KHỚP |
| `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS` | `1` (BẬT) | BẬT theo quyết định chủ sở hữu (mở cổng tổng hợp cho sổ ở giao diện) | KHỚP |
| `AIOS_LOCAL_AI_LOCALITY` | `cloud` | vùng chạy tuyến tổng hợp cloud | KHỚP |
| `AIOS_LOCAL_AI_TIMEOUT_SECONDS` | **vắng → mặc định 30 giây**; đã đặt **90** | đủ cho lượt thử lại 20–50 giây (tồn dư vé giao thức), không vô hạn (trần mã 120 giây) | **LỆCH → ĐÃ SỬA** |
| `AIOS_LOCAL_AI_MAX_TOKENS` | vắng → mặc định 2048 | 2048 như cấu hình đang chạy; cơ chế thử lại tự nâng ×2 (trần 8192) khi đáp án rỗng vì suy luận | KHỚP |
| `AIOS_SYNTHESIS_STRICT_CITATION_CONTRACT` | vắng → TẮT theo mã | giữ TẮT theo quyết định đã chốt (vé `AUDIT-ENV-FAILOVER-HOME` §5) | KHỚP |
| `AIOS_RAG_SYNTH_CONTEXT_TOPK` | vắng → mặc định 8 (trần 50) | biến truy hồi ngữ cảnh tổng hợp; dùng mặc định 8 | KHỚP |
| `AIOS_RETRIEVAL_DEVICE` | `cpu` | chế độ chỉ-CPU cho truy xuất | KHỚP |
| `AIOS_BGE_QUERY_TIMEOUT` (lệnh chạy) | `1200` | theo số đo thật máy CPU-only (gói trong `RUN_AIOS_WORKSPACE_CHAT.bat`) | KHỚP |
| `AIOS_BGE_INIT_TIMEOUT` (lệnh chạy) | `420` | theo số đo nạp model 246–302 giây (vé `BGE-WORKER-FIX-HOME`) | KHỚP |
| `AIOS_RAG_V2_NUMPY_DENSE` (lệnh chạy) | `1` | bật đường tìm kiếm numpy cho kho lớn (lệnh chạy thật) | KHỚP |
| Khóa truy cập | `AIOS_LOCAL_AI_API_KEY` + 8 khóa nhà cung cấp khác: **có mặt** (không in giá trị) | khóa nằm trong `.env` ngoài Git (đúng luật) | KHỚP |

Ghi chú kèm bảng:

- Không có biến tạm/sót (`broken`/`test`/`temp`/`sante`) trong tệp môi trường; không có tên biến trùng; chỉ một tệp `.env` duy nhất (không phân mảnh `.env.*`).
- Các khóa nhà cung cấp khác (Groq/OpenRouter/Mistral/DeepSeek/NVIDIA/ChatAnywhere/Gemini) có mặt trong `.env`: mã điều phối xếp chúng **sau** pool 3 tầng theo thứ tự ưu tiên (`priority` 10/12/14 cho pool, 100+ cho phần còn lại — `ai_router.py:530-577`), nên chuỗi 3 tầng vẫn đi trước; không đổi gì.
- Máy chạy lane tổng hợp qua router nội bộ (`AIOS_AI_BACKEND=nakazasen_router` ghim ở mức tiến trình khi đo — cùng cách vé `APP-E2E-POOL-HOME` đã ĐẠT; mặc định tự chọn của app ưu tiên C-Agent khi cầu Gemini không sống, mà endpoint C-Agent công ty không tới được từ mạng nhà — ghi nhận, ngoài phạm vi sửa của vé).

## 2. Sửa điểm lệch thời gian chờ (điểm 2 của vé)

- **Hiện trạng trước sửa:** biến `AIOS_LOCAL_AI_TIMEOUT_SECONDS` không có trong `.env` → mã dùng mặc định **30 giây** (`ai_router.py:507`; `ai_provider_bridge.py:166-171`; trần cứng 120 giây). Lượt thử lại DeepSeek đo được **20–50 giây** (vé `SYNTH-DEEPSEEK-PROTOCOL-HOME` §5/§7) → 30 giây có thể cắt ngang lượt thử lại khi chạy qua giao diện thật.
- **Mức chọn: 90 giây** — lớn hơn mức đo cao nhất 50 giây (dư địa ~1,8×) và nằm dưới trần mã 120 giây (không vô hạn).
- **Đã sửa:** thêm đúng một dòng `AIOS_LOCAL_AI_TIMEOUT_SECONDS=90` vào `.env` máy nhà (tệp ngoài Git). Sao lưu trước khi sửa: `C:/tmp/env-backup-config-golive-20261009-0856.bak`.
- **Xác minh hiệu lực (chạy mã thật):** `provider_configs_from_env()` → cả 3 tầng pool trả `timeout_seconds=90` (`90/90/90`); `load_provider_config_from_env_or_session()` → `timeout_seconds=90`, `max_tokens=2048`.
- **Không đổi model hay thứ tự chuỗi** (đúng rào vé), không đụng các biến khác.

## 3. Chứng minh bằng dùng thật (điểm 3 của vé)

**Thiết lập:** khởi động lại ứng dụng thật trên cổng tách 8551 bằng đúng môi trường chạy thật của máy nhà (các biến của `RUN_AIOS_WORKSPACE_CHAT.bat` + `.env` đã sửa), chế độ chỉ-CPU; trình duyệt tự động mở sổ `MOM / Opcenter` (kho `tri_thuc`, 889 tài liệu / 149.800 mảnh), hội thoại đo riêng `CONV-GOLIVE-90S7` bật 179 nguồn; lane tổng hợp ghim `nakazasen_router` (cùng cách vé `APP-E2E-POOL-HOME` đã ĐẠT).

**Một câu hỏi LSU thật gửi qua giao diện** (`C7620中Magenta相对Black的副扫描色差达到多少会成为NG？`):

| Chỉ số | Kết quả đo |
|---|---|
| Thời gian mở app → gõ được câu hỏi | **33,56 giây** |
| Thời gian từ lúc bấm Hỏi → đáp án hiện trên giao diện | **631,46 giây** (~10,5 phút) |
| Độ dài đáp án | **1.744 ký tự** (trọn vẹn, không cắt cụt, không rò rỉ prompt hệ thống) |
| **Model phục vụ (ghi trong hồ sơ nguồn gốc)** | **`inclusionai/ling-3.1-flash:free`** — tầng 1 của chuỗi 3 tầng, `operational_mode=external_api` |
| Dấu vết bằng chứng | `trc_09c2c471ba34` — `status=insufficient_evidence` ("No valid citations found in answer text from enabled sources") |
| Băm chỉ mục trước/sau | **khớp tuyệt đối** `45eb0e07…b7c0`, 2.942.201.856 byte (không ghi chỉ mục) |

Ghi nhận trung thực:

- Đáp án do **mô hình tầng 1 phục vụ thật** qua cổng pool (badge UI: “Đã nhận câu trả lời từ AI trong máy tương thích OpenAI (inclusionai/ling-3.1-flash:free)”); đây đúng là đường cần đo của vé (chuỗi 3 tầng + ghim lane tổng hợp).
- Câu hỏi này **không tự nhiên đi qua lượt thử lại** của DeepSeek (tầng 3) nên không có ca thử lại nào để ghi — đúng vé (“không ép tạo tình huống giả”).
- Bộ kiểm định trích dẫn chấm `insufficient_evidence` vì mô hình dẫn nguồn theo lối “NGUỒN 1 …” thay vì nhãn `[1]` — đây là **nút thắt thứ hai đã biết** (mục 7.3 vé `SYNTH-DEEPSEEK-PROTOCOL-HOME`), ngoài phạm vi vé; đáp án vẫn ra tới người dùng kèm dòng nhắc kiểm tra lại.
- Thời gian 631 giây bị đội vì **máy chạy song song một lượt kiểm thử full-suite của thợ khác** (bộ đọc BGE phải nạp lại model trên máy CPU-only đang tải nặng); số đo lấy trong điều kiện thật của máy, không tô hồng.
- Quan sát phụ ngoài phạm vi vé: ghi nhận một lượt dọn nguồn trong log worker cố ghi vào kho production chỉ-đọc bị chặn đúng bằng `sqlite3.OperationalError: attempt to write a readonly database` — khóa chỉ-đọc đang hoạt động tốt, ghi nhận để điều phối biết.

**Tệp bằng chứng đã nộp kho** (kích thước byte đo trên bản đã nộp):

| Tệp | Kích thước | Nội dung |
|---|---|---|
| `docs/phieu-viec/ket-qua/config-golive-audit-home-90s7-01-app-ready.png` | 102.050 byte | Ảnh giao diện sẵn sàng (hội thoại đo, 179 nguồn) |
| `docs/phieu-viec/ket-qua/config-golive-audit-home-90s7-02-answer.png` | 89.001 byte | Ảnh đáp án hiện trên giao diện + badge model |
| `docs/phieu-viec/ket-qua/config-golive-audit-home-do-90s7.json` | 3.857 byte | Số đo, đáp án nguyên văn, model/nguồn gốc, dấu vết, băm chỉ mục |

## 4. Rào cứng đã giữ

- Không in ký tự nào của khóa; chỉ ghi "có mặt/không có mặt".
- Không commit `.env` (đã kiểm tra `.gitignore` dòng 13–15).
- Băm chỉ mục trước khi đo: `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0`, 2.942.201.856 byte (sẽ chốt lại sau khi đo).
- Không merge `main`.
