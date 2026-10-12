# Báo cáo kết quả: Truyền số đo thời gian thật vào nhật ký sử dụng AI ngoài (Vé DESKTOP-EXTERNAL-USAGE-LOG-TIMING-FIX-HOME)

- **Mã vé**: `DESKTOP-EXTERNAL-USAGE-LOG-TIMING-FIX-HOME` (liên kết vé gốc `EXTERNAL-USAGE-LOG-TIMING-FIX-HOME`)
- **Thợ thực hiện**: Antigravity Desktop Engine
- **Thời gian hoàn thành**: 2026-10-12 16:35 +07
- **Trạng thái**: Hoàn thành 100% các yêu cầu của ticket.

---

## 1. Bối cảnh và nguyên nhân gốc
- **Bối cảnh**: Nhật ký sử dụng chế độ Hỏi AI ngoài (`local_cases/workspace_chat/external_ai_usage.jsonl`) trước đây luôn ghi hai trường `duration_sec` và `ttft_sec` bằng `0.0`.
- **Nguyên nhân gốc**:
  - Hàm `log_external_ai_usage` trong `src/aios_habit/workspace_chat_store.py` có hai tham số `duration_sec: float = 0.0, ttft_sec: float = 0.0`.
  - Điểm gọi duy nhất trong `src/aios_habit/antigravity_bridge.py` (hàm `_try_nakazasen_router`) chỉ truyền `conversation_id`, `message_id`, `model_name` mà không truyền hai số đo thời gian thực tế của lượt gọi.

---

## 2. Giải pháp thực hiện
1. **Tại điểm gọi `antigravity_bridge.py`**:
   - Sử dụng đồng hồ đơn điệu `time.monotonic()` quanh đoạn xử lý gọi Nakazasen Router để đo tổng thời gian hoàn tất (`measured_duration = t_router_end - t_router_start`).
   - Bọc callback `on_chunk` qua hàm bọc luồng an toàn (`_timed_on_chunk`) để ghi lại mốc xuất hiện ký tự/token đầu tiên (`ttft_recorded = time.monotonic() - t_router_start`).
   - Cho phép nhận số đo chỉ định/giả lập qua tham số mở rộng `duration_sec: float | None = None, ttft_sec: float | None = None` của `route_workspace_chat_submission`, đồng thời tự động đo lường bằng đồng hồ đơn điệu khi tham số là `None`.
   - Truyền đầy đủ `duration_sec=effective_duration_sec, ttft_sec=effective_ttft_sec` vào hàm `log_external_ai_usage` và cập nhật vào `badge` kết quả.
2. **Tại hàm ghi `workspace_chat_store.py`**:
   - Giữ nguyên chữ ký hàm `log_external_ai_usage` và cấu trúc bản ghi JSONL.
   - Ép kiểu an toàn `float(duration_sec if duration_sec is not None else 0.0)` và `float(ttft_sec if ttft_sec is not None else 0.0)`.
3. **Phân quyền và tính toàn vẹn**:
   - Chỉ sửa điểm gọi, hàm ghi và test liên quan; không đổi định dạng bản ghi nhật ký; không ảnh hưởng tới các luồng khác ngoài chế độ Hỏi AI ngoài.

---

## 3. Kiểm thử và 4 Cổng chất lượng

### 3.1. Các ca kiểm thử đơn vị & hồi quy
- `tests/test_workspace_chat_store.py`:
  - `test_log_external_ai_usage`: Kiểm tra ghi nhận đầy đủ khi có `duration_sec=3.5, ttft_sec=0.8`.
  - `test_log_external_ai_usage_defaults_to_zero_when_no_timings`: Kiểm tra ghi nhận `0.0` và `0.0` khi không truyền hoặc truyền `None`.
- `tests/test_antigravity_bridge.py`:
  - `test_route_external_ai_mode_records_real_timing_measurements`: Kiểm tra khi gọi `route_workspace_chat_submission` ở chế độ `ai_mode="external"`, hệ thống tự đo qua `time.monotonic()` và callback token streamer, khẳng định `duration_sec > 0.0` và `ttft_sec > 0.0` được ghi đúng vào tệp `external_ai_usage.jsonl`.
  - `test_route_external_ai_mode_records_explicit_and_zero_timings`: Kiểm thử 2 ca:
    - Ca 1: Truyền số đo giả lập khác 0 (`duration_sec=14.25, ttft_sec=3.80`) -> bản ghi ghi đúng `14.25` và `3.80`.
    - Ca 2: Truyền số đo bằng 0 (`duration_sec=0.0, ttft_sec=0.0`) -> bản ghi ghi đúng `0.0` và `0.0`.

### 3.2. 4 Cổng chất lượng của repo
1. **Cổng 1 (Biên dịch toàn bộ mã nguồn)**:
   - Lệnh: `python -m compileall src tests` -> **PASS (Exit code 0)**.
2. **Cổng 2 (Kiểm thử tự động)**:
   - Lệnh: `pytest tests/test_workspace_chat_store.py tests/test_antigravity_bridge.py -k "test_log_external_ai_usage or test_route_external_ai_mode"` -> **4/4 PASS (100%)**.
   - Kiểm thử toàn diện file store: `pytest tests/test_workspace_chat_store.py` -> **50/50 PASS (100%)**.
3. **Cổng 3 (Kiểm toán CLI)**:
   - Lệnh: `python -m aios_habit.cli audit` -> **PASS (`{"errors": [], "status": "PASS", "warnings": []}`)**.
4. **Cổng 4 (Kiểm tra nhập app)**:
   - Lệnh: `python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"` -> **`IMPORT_OK`**.
