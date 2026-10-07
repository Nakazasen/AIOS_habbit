# Báo cáo vé ROUTER-POOL-COMMANDCODE-HOME — Trỏ tuyến tổng hợp sang pool Command Code + đo lại

- **Máy thực hiện:** NHÀ `h410asrock` (thợ agy — `gemini-3.8-flash-high`).
- **Thời điểm thực hiện:** 2026-10-07 23:36 +07.
- **Mục tiêu:** Chuyển tuyến tổng hợp RAG từ một tuyến Gemini duy nhất (cầu 8585 cũ hay bị rate-limit) sang pool Command Code có failover tự động giữa model chính và các model dự phòng; chuẩn bị file cấu hình local an toàn cho user dán key tại máy.

---

## 1. Khảo sát chỗ cấu hình trên máy nhà (Bước 1 — Chỉ đọc)

Hệ thống AIOS WorkLens đọc cấu hình tuyến tổng hợp qua các biến môi trường:
- `AIOS_LOCAL_AI_ENDPOINT`: Đường dẫn endpoint OpenAI-compatible.
- `AIOS_LOCAL_AI_MODEL`: Tên mô hình chính (hoặc danh sách mô hình phân cách bằng dấu phẩy).
- `AIOS_LOCAL_AI_FAILOVER_MODELS`: Danh sách các mô hình dự phòng (failover) từ pool.
- `AIOS_LOCAL_AI_API_KEY`: Khóa API (do người dùng cung cấp tại máy, tuyệt đối không commit).
- `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS`: Công tắc cho phép tổng hợp qua cloud (1/true/yes/on).
- `AIOS_LOCAL_AI_LOCALITY`: Xác định vị trí endpoint (`local` hoặc `cloud`).
- `AIOS_LOCAL_AI_TIMEOUT_SECONDS`: Thời gian chờ gọi API (mặc định 30s).

### Vị trí các tệp cấu hình trên máy nhà:
1. `D:\Sandbox\AIOS_habbit\.env`:
   - Tệp cấu hình cục bộ được nạp tự động bởi `src/aios_habit/workspace_paths.py` (hàm `load_env_file()`) ngay khi khởi động ứng dụng.
   - **Tình trạng bảo mật:** Tệp đã được bảo vệ trong `.gitignore` (dòng 14: `*.env` và `.env`), hoàn toàn nằm ngoài Git, an toàn 100% để lưu trữ khóa cục bộ.
2. `D:\Sandbox\AIOS_habbit\RUN_AIOS_WORKSPACE_CHAT.bat`:
   - Trình khởi chạy giao diện Workspace Chat trên máy nhà, thiết lập các biến môi trường runtime BGE worker và profile hybrid.
3. `C:\tmp\lsu-quality-rag-home\do_rag_50_synth.py` (và các script runner trong thư mục `C:\tmp\`):
   - Runner đo chất lượng lane RAG 50 câu LSU ngoài Git, đọc cấu hình từ `(ROOT / ".env")` qua `os.environ.setdefault(...)`.

---

## 2. Chuẩn bị chỗ nhập cho user & Cải tiến Router Failover (Bước 2)

### 2.1. Chuẩn bị tệp cấu hình cục bộ (`.env`)
Đã chuẩn bị sẵn mẫu cấu hình trong tệp `D:\Sandbox\AIOS_habbit\.env` (nằm ngoài Git):

```ini
# ROUTER-POOL-COMMANDCODE-HOME: Tuyen tong hop sang pool Command Code
AIOS_LOCAL_AI_ENDPOINT=https://api.commandcode.ai/provider/v1/chat/completions
AIOS_LOCAL_AI_MODEL=inclusionai/ling-3.1-flash:free
AIOS_LOCAL_AI_FAILOVER_MODELS=inclusionai/ling-3.0-flash-sante:free,poolside/laguna-s-2.1-free
AIOS_LOCAL_AI_API_KEY=
AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1
AIOS_LOCAL_AI_LOCALITY=cloud
```

- **Endpoint:** `https://api.commandcode.ai/provider/v1/chat/completions` (OpenAI-compatible Chat Completions theo tài liệu chuẩn Command Code Provider API).
- **Mô hình chính (Tầng 1 Free trên GOAT):** `inclusionai/ling-3.1-flash:free` (context 262K).
- **Mô hình dự phòng (Failover 1 & 2 Free trên GOAT):** `inclusionai/ling-3.0-flash-sante:free`, `poolside/laguna-s-2.1-free`.
- **Dòng để trống chờ user dán key:** `AIOS_LOCAL_AI_API_KEY=`
- **Công tắc cloud:** `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1`
- **Locality:** `AIOS_LOCAL_AI_LOCALITY=cloud`

> **Lưu ý bảo mật:** Tuyệt đối không dán API key vào mailbox, chat hay commit git. Người dùng chỉ cần mở tệp `D:\Sandbox\AIOS_habbit\.env` tại máy nhà và dán key vào sau dấu `=` của dòng `AIOS_LOCAL_AI_API_KEY=`.

### 2.2. Cải tiến kiến trúc Router hỗ trợ Pool Failover tự động
Để đáp ứng yêu cầu "tuyến chính bị rate-limit/5xx thì Router chuyển tuyến khác, thay vì harness rơi về trích cục bộ", đã thực hiện 2 cải tiến cốt lõi:

1. **Hỗ trợ Provider Variants trong `src/aios_habit/provider_catalog.py`:**
   - Cập nhật hàm `get_provider_profile` để hỗ trợ các variant phân tách bằng dấu `:` (ví dụ `openai_compatible_local:failover_1`), tự động kế thừa profile và chính sách bảo mật của `openai_compatible_local`.
   - Giúp mỗi mô hình trong pool có `provider_id` riêng biệt, tránh tình trạng khi một mô hình bị rate-limit (429) làm khóa oan toàn bộ các mô hình khác trong pool tại `ProviderHealthStore`.

2. **Nạp Model Pool & Tự động phát hiện Cloud Endpoint trong `src/aios_habit/ai_router.py`:**
   - Cập nhật hàm `provider_configs_from_env`:
     - Tự động phân tách danh sách mô hình từ `AIOS_LOCAL_AI_MODEL` và `AIOS_LOCAL_AI_FAILOVER_MODELS`.
     - Tự động nhận diện `trusted_internal` qua `is_local_endpoint(local_endpoint)`: nếu endpoint là URL cloud bên ngoài (như Command Code), `trusted_internal` tự động đặt là `False`, tránh bị cơ chế an toàn `blocked_non_local_endpoint` chặn nhầm.
     - Phân bổ thứ tự ưu tiên (`priority`): mô hình chính priority 10, failover 1 priority 12, failover 2 priority 14...
   - Cập nhật `provider_env_presence` theo dõi thêm `AIOS_LOCAL_AI_FAILOVER_MODELS`.

### 2.3. Bằng chứng kiểm thử tự động
- Đã bổ sung 3 unit tests mới trong `tests/test_ai_router.py`:
  1. `test_provider_configs_from_env_openai_compatible_pool`: Xác nhận nạp đủ 3 mô hình pool, priority tăng dần, phát hiện đúng endpoint cloud (`trusted_internal=False`).
  2. `test_openai_compatible_pool_failover_on_rate_limit`: Mô phỏng mô hình chính bị 429 rate limit -> Router tự động failover sang mô hình dự phòng thành công, không rơi về deterministic fallback.
  3. `test_openai_compatible_pool_failover_on_server_error`: Mô phỏng mô hình chính bị 502 Bad Gateway -> Router tự động failover sang mô hình dự phòng thành công.
- Kết quả chạy test: 71/71 tests liên quan PASS 100%.

---

## 3. Cổng kiểm tra chất lượng (Quality Gates)

- **`uv run --no-sync --group dev python -m compileall src tests`**:
  `Listing 'src'... Compiling 'tests\\test_ai_router.py'... Compiling 'tests\\test_rag_v2_synthesis_provider.py' -> SẠCH 100% (Exit Code 0)`.
- **`uv run --no-sync --group dev python -m aios_habit.cli audit`**:
  `{"errors": [], "status": "PASS", "warnings": []}`.
- **`uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"`**:
  `IMPORT_OK`.

---

## 4. Hướng dẫn cho User thực hiện bước tiếp theo

1. Mở tệp cục bộ: `D:\Sandbox\AIOS_habbit\.env` (hoặc mở bằng Notepad / VSCode).
2. Tìm dòng:
   ```ini
   AIOS_LOCAL_AI_API_KEY=
   ```
3. Dán Command Code API key của gói $10 vào sau dấu `=`, ví dụ:
   ```ini
   AIOS_LOCAL_AI_API_KEY=cmd_xxxxxxxxxxxxxxxxxxxxxxxx
   ```
4. Lưu tệp `.env`.
5. Sau khi lưu, thông báo cho điều phối / agent để tiếp tục thực hiện Bước 3 (Gọi thử kiểm chứng tuyến mới) và Bước 4 (Đo lại lane RAG 50 câu LSU).
