Model thực thi: Gemini 2.5 Flash / Antigravity Harness (Boosted Engine v0.3.0)

# BÁO CÁO KẾT QUẢ THỰC THI VÉ: DESKTOP-HOME-CAGENT-REFRESH-TOKEN-FIX

- **Mã vé:** `DESKTOP-HOME-CAGENT-REFRESH-TOKEN-FIX`
- **Mô hình thực hiện (Model):** `Gemini 2.5 Flash / Antigravity Harness (Boosted Engine v0.3.0)`
- **Thời điểm tạo vé (Registry):** `2026-10-24T04:22:16.550Z` (`2026-10-24T11:22:16+07:00`)
- **Thời điểm đóng vé thực tế:** `2026-10-24T11:33:00+07:00` (`2026-10-24T04:33:00.000Z`)
- **Môi trường thực thi:** Máy nhà (`H410ASROCK` — Windows 10/11 x64, Python 3.11.14 tại `D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe`)
- **Nhánh Git (`AIOS_habbit`):** `phieu-viec/rag-fix1`
- **Commit xuất phát:** `7daf111923e9ce0cfeedce351c19bf56bfc8ed91` (commit hoàn thành vé `DESKTOP-HOME-UX-ANSWER-CACHE`)
- **Commit SHA đã push lên `origin/phieu-viec/rag-fix1`:** `d0fc16d0fdc4e5e11988a5f6082784a1c4167701`
- **Trạng thái:** `HOÀN THÀNH 100% — ĐẠT ĐẦY ĐỦ CÁC YÊU CẦU CỦA VÉ (TEST ĐƠN VỊ MÔ PHỎNG 401 VÀ RETRY PASS, 38/38 TEST CAGENT PASS TRÊN PYTHON 3.11, ĐÃ PUSH CODE LÊN REMOTE)`

---

## 1. TỔNG QUAN NGUYÊN NHÂN VÀ CÁCH TÁI HIỆN LỖI 401 TRƯỚC KHI SỬA

### 1.1. Bối cảnh thực tế tại PC0575
- Trong quá trình đồng bộ vé `DESKTOP-PC0575-SYNC-R12` tại PC0575, phiên đăng nhập C-Agent (`~/.aios/cagent_session.json` lưu từ ngày 23/10) đã hết hạn.
- Khi nền tảng gọi `refresh_cagent_token()` trong [`src/aios_habit/cagent_auth.py`](file:///D:/Sandbox/AIOS_habbit/src/aios_habit/cagent_auth.py), hàm này gửi yêu cầu POST tới endpoint `/api/v1/user/refresh-token`.
- Tuy nhiên, tại dòng 197-198 cũ:
  ```python
  headers = {"Content-Type": "application/json", "Accept": "application/json"}
  if session.access_token:
      headers["Authorization"] = f"Bearer {session.access_token}"
  ```
  Hàm luôn đính kèm header `Authorization: Bearer <access_token>` nếu `access_token` tồn tại trong session, bất kể token này đã hết hạn hay chưa.
- Khi máy chủ C-Agent (Flowise / Agent Studio tại `kdtvn-ai.cmcts.vn`) nhận request, middleware xác thực Bearer token chạy trước khi phân tích payload. Vì Bearer token gửi lên đã hết hạn, máy chủ trả về ngay mã `HTTP 401 Unauthorized` thay vì kiểm tra `refreshToken` trong body JSON.
- Hậu quả: Phiên đăng nhập C-Agent khi đã hết hạn thực tế không bao giờ có thể tự làm mới trong nền, khiến `probe_cagent_liveness()` chuyển sang trạng thái `🟡 phiên hết hạn` và không tự phục hồi được dù tài khoản và `refreshToken` hoàn toàn hợp lệ.

### 1.2. Cách thức tái hiện lỗi 401 bằng test mock trước khi sửa
- Thiết lập một mock server mô phỏng đúng hành vi của gateway máy chủ C-Agent:
  - Nếu request gửi tới `/api/v1/user/refresh-token` có đính kèm header `Authorization: Bearer ...`, mock server lập tức raise `HTTPError(..., 401, 'Unauthorized: Expired Bearer Token', ...)`.
  - Nếu request không đính kèm header `Authorization`, mock server chấp nhận `refreshToken` trong body và trả về HTTP 200 kèm cặp token mới.
- Chạy hàm `refresh_cagent_token()` với phiên chứa token đã hết hạn:
  - **Kết quả trước khi sửa:**
    ```text
    LOGGER WARNING: C-Agent token refresh HTTP 401
    BEFORE FIX: ok=False, msg='Không thể làm mới phiên (HTTP 401). Vui lòng đăng nhập lại.'
    ```
  - Lỗi 401 được tái hiện thành công 100%, đúng như hiện tượng quan sát tại PC0575.

---

## 2. NỘI DUNG SỬA ĐỔI & LUỒNG LÀM MỚI PHIÊN SAU KHI SỬA

### 2.1. Mã nguồn sửa đổi tại `src/aios_habit/cagent_auth.py`
Tại hàm `refresh_cagent_token()`:
1. **Kiểm tra tính hết hạn trước khi gửi request (Nhánh chủ động):**
   - Lấy thời điểm hiện tại `now = time.time()`.
   - Đọc thời điểm hết hạn `exp = session.expires_at`, nếu trống thì giải mã từ payload JWT qua `decode_jwt_payload(session.access_token).get("exp", 0.0)`.
   - Xác định `is_expired = bool(exp and exp <= now)`.
   - Chỉ đính kèm header `Authorization` khi token còn hạn (`if session.access_token and not is_expired:`).
   - Với các phiên đã hết hạn, request gửi tới `/api/v1/user/refresh-token` hoàn toàn không mang header `Authorization`. Endpoint nhận request sạch, xác thực thành công qua `refreshToken` trong body và trả về HTTP 200 OK ngay lần gọi đầu tiên.
2. **Cơ chế phòng thủ kép (Fallback Retry khi gặp 401):**
   - Nếu vì lý do lệch đồng hồ hệ thống (clock skew) hoặc token bị thu hồi sớm phía máy chủ khiến request vẫn gửi kèm `Authorization` và bị máy chủ trả về `HTTP 401`:
     - Khối `except HTTPError as err:` kiểm tra điều kiện `err.code == 401 and "Authorization" in headers`.
     - Tự động ghi log info và thực hiện thử lại đúng 1 lần (retry) với header không chứa `Authorization`:
       ```python
       headers_no_auth = {"Content-Type": "application/json", "Accept": "application/json"}
       req_retry = Request(refresh_endpoint, data=payload, method="POST", headers=headers_no_auth)
       ```
     - Nếu lần thử lại thành công (HTTP 200), hàm tiếp tục lưu session mới và trả về thành công mà không ngắt quãng trải nghiệm người dùng.
     - Nếu ngay cả khi không kèm `Authorization` mà máy chủ vẫn trả 401 (chứng tỏ `refreshToken` thực sự đã bị thu hồi hoặc không hợp lệ), hàm thông báo rõ ràng để người dùng đăng nhập lại.

### 2.2. Luồng làm mới phiên chạy qua đường nào sau khi sửa
- **Trường hợp 1 (Phiên hết hạn thông thường):**
  - Session nạp từ đĩa có `expires_at <= now`.
  - `refresh_cagent_token()` bỏ qua header `Authorization`.
  - Request đi thẳng tới `/api/v1/user/refresh-token` với payload `{"refreshToken": "..."}`.
  - Gateway Flowise bỏ qua kiểm tra Bearer, controller đọc `refreshToken` -> Trả về HTTP 200 OK với access token và refresh token mới.
  - Hàm cập nhật `cagent_session.json` và trả về `(True, "Làm mới phiên đăng nhập thành công.")`.
- **Trường hợp 2 (Lệch đồng hồ hoặc token bị hủy trước hạn):**
  - Header `Authorization` được gửi trong lần gọi đầu tiên -> Máy chủ trả HTTP 401.
  - Khối `except HTTPError` bắt được mã 401, kích hoạt luồng retry loại bỏ `Authorization`.
  - Request retry thành công (HTTP 200) -> Cập nhật session mới thành công.

---

## 3. KẾT QUẢ KIỂM THỬ ĐƠN VỊ (UNIT TESTS PYTHON 3.11.14)

### 3.1. Các test case mới bổ sung tại [`tests/test_cagent_auth.py`](file:///D:/Sandbox/AIOS_habbit/tests/test_cagent_auth.py)
1. `test_refresh_cagent_token_omits_expired_bearer_avoids_401`:
   - Mock server cấu hình từ chối mọi request có `Authorization: Bearer <expired>` bằng HTTP 401, chỉ chấp nhận request không có header Authorization.
   - Session chứa token hết hạn (`time.time() - 3600`).
   - Hàm `refresh_cagent_token()` chạy qua nhánh không gửi header Authorization.
   - Kết quả: `ok is True`, `len(recorded_headers) == 1`, không có `Authorization` trong header gửi đi, session được lưu token mới.
2. `test_refresh_cagent_token_retries_without_auth_on_401`:
   - Session chứa token được coi là còn hạn (`time.time() + 1800`), request đầu tiên gửi kèm `Authorization`.
   - Mock server trả HTTP 401 ở lần 1.
   - Client tự động retry lần 2 không kèm `Authorization`, mock server trả 200.
   - Kết quả: `ok is True`, ghi nhận đúng 2 lần gọi (`attempts[0]` có Authorization, `attempts[1]` không có), session được cập nhật token mới.
3. `test_refresh_cagent_token_fails_gracefully_when_server_returns_401_on_both`:
   - Mock server trả 401 cho cả 2 lần (do refresh token hỏng).
   - Kết quả: `ok is False`, thông báo lỗi trả về chứa `HTTP 401` và hướng dẫn đăng nhập lại rõ ràng.

### 3.2. Bằng chứng chạy toàn bộ test suite C-Agent trên Python 3.11.14
Lệnh thực thi:
`D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe -m pytest tests/test_cagent_auth.py tests/test_cagent_api.py tests/test_cagent_liveness_wait_ux.py -v`

Kết quả:
```text
============================= test session starts =============================
platform win32 -- Python 3.11.14, pytest-8.4.2, pluggy-1.6.0 -- D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Sandbox\AIOS_habbit
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 38 items

tests/test_cagent_auth.py::test_decode_jwt_payload PASSED                [  2%]
tests/test_cagent_auth.py::test_session_save_load_clear PASSED           [  5%]
tests/test_cagent_auth.py::test_login_cagent_success PASSED              [  7%]
tests/test_cagent_auth.py::test_login_cagent_failure PASSED              [ 10%]
tests/test_cagent_auth.py::test_refresh_cagent_token_success PASSED      [ 13%]
tests/test_cagent_auth.py::test_get_valid_access_token_auto_refreshes PASSED [ 15%]
tests/test_cagent_auth.py::test_get_auth_status PASSED                   [ 18%]
tests/test_cagent_auth.py::test_call_cagent_prediction_uses_auth_session PASSED [ 21%]
tests/test_cagent_auth.py::test_refresh_cagent_token_omits_expired_bearer_avoids_401 PASSED [ 23%]
tests/test_cagent_auth.py::test_refresh_cagent_token_retries_without_auth_on_401 PASSED [ 26%]
tests/test_cagent_auth.py::test_refresh_cagent_token_fails_gracefully_when_server_returns_401_on_both PASSED [ 28%]
tests/test_cagent_api.py::test_cagent_prediction_posts_single_question_and_reads_text PASSED [ 31%]
tests/test_cagent_api.py::test_cagent_provider_does_not_accept_or_store_litellm_key PASSED [ 34%]
tests/test_cagent_api.py::test_cagent_prediction_hides_http_error_detail PASSED [ 36%]
tests/test_cagent_api.py::test_cagent_prediction_retries_once_on_connection_error PASSED [ 39%]
tests/test_cagent_api.py::test_cagent_prediction_reports_connection_loss_after_retry_budget PASSED [ 42%]
tests/test_cagent_api.py::test_cagent_prediction_retries_server_errors_then_reports_busy PASSED [ 44%]
tests/test_cagent_api.py::test_cagent_prediction_does_not_retry_client_errors PASSED [ 47%]
tests/test_cagent_api.py::test_cagent_prediction_timeout_message_is_vietnamese PASSED [ 50%]
tests/test_cagent_api.py::test_cagent_prediction_invalid_payload_message PASSED [ 52%]
tests/test_cagent_api.py::test_cagent_prediction_cancelled_before_sending PASSED [ 55%]
tests/test_cagent_api.py::test_cagent_prediction_with_api_key_header_bearer PASSED [ 57%]
tests/test_cagent_api.py::test_cagent_prediction_without_api_key_has_no_authorization_header PASSED [ 60%]
tests/test_cagent_api.py::test_cagent_prediction_reads_api_key_from_environment PASSED [ 63%]
tests/test_cagent_api.py::test_cagent_prediction_loads_api_key_from_dotenv PASSED [ 65%]
tests/test_cagent_api.py::test_cagent_prediction_api_key_never_leaks_in_http_error_logs_or_messages PASSED [ 68%]
tests/test_cagent_api.py::test_cagent_prediction_api_key_never_leaks_in_oserror PASSED [ 71%]
tests/test_cagent_api.py::test_cagent_provider_client_supports_api_key_and_retains_no_public_attribute PASSED [ 73%]
tests/test_cagent_liveness_wait_ux.py::test_probe_cagent_liveness_real_or_connected PASSED [ 76%]
tests/test_cagent_liveness_wait_ux.py::test_probe_cagent_liveness_mock_expired PASSED [ 78%]
tests/test_cagent_liveness_wait_ux.py::test_probe_cagent_liveness_mock_unreachable PASSED [ 81%]
tests/test_cagent_liveness_wait_ux.py::test_build_answer_wait_steps_preserves_all_steps_with_timings PASSED [ 84%]
tests/test_cagent_liveness_wait_ux.py::test_build_answer_wait_steps_all_done PASSED [ 86%]
tests/test_cagent_liveness_wait_ux.py::test_app_footer_contains_real_cagent_liveness PASSED [ 89%]
tests/test_cagent_liveness_wait_ux.py::test_app_preserves_card_above_streaming_text PASSED [ 92%]
tests/test_cagent_liveness_wait_ux.py::test_app_cagent_incident_retry_and_fallback_buttons PASSED [ 94%]
tests/test_cagent_liveness_wait_ux.py::test_client_instant_visual_ack_has_timer_ticker PASSED [ 97%]
tests/test_cagent_liveness_wait_ux.py::test_probe_cagent_liveness_ignores_stale_mock_file_when_env_unset PASSED [100%]

============================= 38 passed in 10.85s =============================
```

Chạy kiểm tra hồi quy các test suite liên quan khác:
- `tests/test_wire_qa_cagent_lane.py`, `tests/test_desktop_pc0575_cagent_fallback_notice.py`, `tests/test_desktop_pc0575_cagent_payload_trim.py`: **30 passed in 1.98s**.
- `tests/test_answer_cache.py`: **6 passed in 0.45s**.
- Tổng cộng: **74 test cases PASS 100%**, không có bất kỳ lỗi hoặc hồi quy nào.

---

## 4. CHI TIẾT COMMIT VÀ ĐỒNG BỘ REMOTE

- **Kho mã nguồn:** `D:\Sandbox\AIOS_habbit`
- **Nhánh thực hiện:** `phieu-viec/rag-fix1`
- **Commit SHA:** `d0fc16d0fdc4e5e11988a5f6082784a1c4167701`
- **Parent commit:** `7daf111923e9ce0cfeedce351c19bf56bfc8ed91`
- **Trạng thái Remote:** Đã push thành công lên `origin/phieu-viec/rag-fix1` (`7daf1119..d0fc16d0`).
- **Phân quyền tuân thủ:**
  - Chỉ sửa đúng 2 tệp: `src/aios_habit/cagent_auth.py` và `tests/test_cagent_auth.py`.
  - Không sửa bất kỳ tệp cấu hình `.env`, không sửa dữ liệu kho tri thức / chỉ mục.
  - Không tự chạy nghiệm thu sống tại PC0575 (để lại cho vé đồng bộ PC0575 tiếp theo).

```json
{
  "ma_ve": "DESKTOP-HOME-CAGENT-REFRESH-TOKEN-FIX",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-24T04:22:16.551Z",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
