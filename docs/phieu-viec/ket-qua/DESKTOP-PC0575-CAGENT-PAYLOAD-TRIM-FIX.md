# BÁO CÁO THỰC THI VÉ DESKTOP-PC0575-CAGENT-PAYLOAD-TRIM-FIX

> **Trạm thực thi**: KDTVN-PC0575  
> **Kho mã nguồn**: `D:\Sandbox\AIOS_habbit`  
> **Nhánh**: `phieu-viec/rag-fix1`  
> **Thời điểm hoàn thành**: 2026-10-16T19:05:00+07:00  
> **Trạng thái**: HOÀN THÀNH (100% yêu cầu chất lượng)  

---

## 1. BỐI CẢNH & MỤC TIÊU VÉ

Theo kết quả từ vé chẩn đoán `DESKTOP-PC0575-CAGENT-LOCAL-FALLBACK-DIAG`:
- Lượt hỏi lúc 17:53 ngày 2026-10-16 gửi sang C-Agent một payload hơn 30.000 ký tự (chứa tới 50 tin nhắn lịch sử của hội thoại 73 tin nhắn cộng 20 đoạn trích tài liệu), khiến máy chủ Flowise C-Agent không phản hồi kịp trong 60 giây và hệ thống phải rơi làn xuống trích xuất cục bộ.
- Chẩn đoán cũng ghi nhận máy chủ C-Agent phản hồi chậm/lỗi cả với câu hỏi siêu ngắn.
- **Mục tiêu của vé**:
  - Giới hạn lịch sử hội thoại gửi kèm cuộc gọi tổng hợp C-Agent (`cagent_api`) tại đúng điểm dựng payload.
  - Chỉ gửi các lượt hội thoại gần nhất trong một ngân sách giới hạn rõ ràng (số lượt và tổng ký tự).
  - Luôn giữ nguyên vẹn 100% câu hỏi hiện tại và toàn bộ bằng chứng truy hồi của lượt.
  - Hội thoại ngắn dưới ngưỡng thì hành vi không đổi.
  - Không thay đổi logic định tuyến và không thay đổi giá trị timeout.

---

## 2. NGÂN SÁCH ĐÃ CHỌN (CHOSEN BUDGET) & CƠ SỞ KỸ THUẬT

Đã chọn và thiết lập ngân sách cắt tỉa lịch sử qua 2 hằng số (hỗ trợ ghi đè linh hoạt qua biến môi trường):

1. **Giới hạn số lượt/tin nhắn gần nhất**:
   - `DEFAULT_CAGENT_MAX_HISTORY_TURNS = 6` (cấu hình qua `AIOS_CAGENT_MAX_HISTORY_TURNS` hoặc `AIOS_CAGENT_MAX_HISTORY_MESSAGES`, mặc định: **6 tin nhắn**, tương đương **3 lượt hỏi-đáp gần nhất**).
   - **Cơ sở kỹ thuật**:
     - 6 tin nhắn gần nhất cung cấp đầy đủ ngữ cảnh trao đổi liền kề của người dùng và trợ lý AI về chủ đề đang thảo luận.
     - Đồng bộ và tương thích với quy chuẩn của `workspace_chat_router_adapter.py` (vốn đã lấy `chat_history[-6:]`).
     - Tách biệt và bảo toàn chỉ thị neo ngữ cảnh (anchor directive) nếu có ở cuối lịch sử để đảm bảo tính năng "Trả lời trực tiếp" (Reply) không bị mất.

2. **Giới hạn tổng ký tự lịch sử**:
   - `DEFAULT_CAGENT_MAX_HISTORY_CHARS = 4000` (cấu hình qua `AIOS_CAGENT_MAX_HISTORY_CHARS`, mặc định: **4.000 ký tự**).
   - **Cơ sở kỹ thuật**:
     - Trong trường hợp các câu trả lời trước đó của AI có nội dung dài (bảng biểu, mã nguồn, danh sách), ngân sách 4.000 ký tự đóng vai trò chốt chặn an toàn (circuit breaker) ngăn chặn lịch sử làm phình to payload vượt quá khả năng xử lý của Flowise.
     - Cơ chế duyệt ngược từ tin nhắn mới nhất về cũ nhất: ưu tiên giữ trọn vẹn tin nhắn mới nhất, chỉ loại bỏ dần các tin cũ hơn vượt ngân sách.

3. **Nguyên tắc bất biến (Negative Guards)**:
   - **Câu hỏi hiện tại**: Giữ nguyên vẹn 100%, không cắt gọt bất kỳ ký tự nào.
   - **Bằng chứng truy hồi (retrieved sources)**: Giữ nguyên vẹn 100% toàn bộ các đoạn trích từ RAG.
   - **Hội thoại ngắn**: Nếu `len(chat_history) <= 6` và tổng ký tự `<= 4000`, trả về nguyên vẹn danh sách tin nhắn.

---

## 3. BẢNG SO SÁNH KÍCH THƯỚC PAYLOAD TRƯỚC / SAU CẮT TỈA TRÊN CONV-9C730D76

Đo đạc trực tiếp trên trường hợp hội thoại dài thực tế `CONV-9C730D76` (74 tin nhắn, lượt hỏi 17:53 `MSG-1EF1690E`: *"LSU là gì và gồm những bộ phận quang học chính nào?"*):

| Thành phần | Trước khi cắt (50 tin) | Sau khi cắt (ngân sách 6 tin / 4k ký tự) | Chênh lệch thay đổi | Đánh giá |
|:---|:---:|:---:|:---:|:---|
| **Số tin nhắn lịch sử** | 50 tin | **6 tin** | **-44 tin** (-88.0%) | Cắt đúng ngưỡng lượt gần nhất |
| **Ký tự lịch sử hội thoại** | 16.918 ký tự | **1.238 ký tự** | **-15.680 ký tự** (-92.7%) | Giảm hơn 92% tải lịch sử |
| **Câu hỏi hiện tại** | 51 ký tự | **51 ký tự** | **0 ký tự** (0.0%) | **Giữ nguyên vẹn 100%** |
| **Số đoạn bằng chứng truy hồi** | 20 đoạn | **20 đoạn** | **0 đoạn** (0.0%) | **Giữ nguyên vẹn 100%** |
| **Ký tự bằng chứng truy hồi** | 18.019 ký tự | **18.019 ký tự** | **0 ký tự** (0.0%) | **Giữ nguyên vẹn 100%** |
| **System Prompt** | 767 ký tự | **767 ký tự** | **0 ký tự** (0.0%) | **Giữ nguyên vẹn 100%** |
| **Tổng ký tự trường question (API)** | 38.925 ký tự | **22.563 ký tự** | **-16.362 ký tự** (-42.0%) | Giảm mạnh áp lực context |
| **Tổng dung lượng HTTP Body (UTF-8)** | 51.691 bytes | **30.773 bytes** | **-20.918 bytes** (-40.5%) | Tiết kiệm hơn 20 KB / request |

---

## 4. KẾT QUẢ ĐO ĐẠC MỘT LƯỢT HỎI THẬT TẠI PC0575

Đã chạy kiểm chứng thực tế đầu cuối với kịch bản `scripts/run_real_turn_measurement.py` trên hội thoại thực tế `CONV-9C730D76`:

- **Câu hỏi**: *"LSU là gì và gồm những bộ phận quang học chính nào?"*
- **Thời điểm bắt đầu**: `2026-10-16T12:02:28.737679+00:00` (19:02:28 +07:00)
- **Thời điểm kết thúc**: `2026-10-16T12:04:18.461501+00:00` (19:04:18 +07:00)
- **Thời gian xử lý**: 109.72s (trong đó truy hồi bằng chứng BGE-M3: 57.65s, gọi C-Agent: 60s)
- **Kích thước payload gửi tới C-Agent**: 22.524 ký tự (29.915 bytes UTF-8) — đã cắt tỉa lịch sử từ 17.135 ký tự xuống còn 1.937 ký tự (6 tin nhắn).
- **Phản hồi từ máy chủ C-Agent**:
  ```json
  C-AGENT API HTTP 500: {
    "statusCode": 500,
    "success": false,
    "message": "Error: predictionsServices.buildChatflow - Error buildAgentGraph - Error: 404 litellm.NotFoundError: BedrockException - {\"message\":\"This model version has reached the end of its life. Please refer to the AWS documentation for more details.\"}\n\nLiteLLM: model group 'claude-4-sonnet' failed with the error above. No fallback was attempted."
  }
  ```
  *(Ghi chú: Lỗi máy chủ phía AWS Bedrock / LiteLLM của C-Agent đúng như nhận định tại mục 1 của vé — vé này chỉ giảm payload phía app, không sửa server).*
- **Làn sinh đáp án thực tế**: `Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình` (`operational_mode: local_grounded_fallback`).
- **Chuyển tuyến dự phòng (`fallback_used`)**: `True` (kích hoạt cảnh báo fallback theo vé trước).
- **Mã Trace ID sinh ra**: `trc_b7d04d9a4b87`.
- **Trạng thái cuộc gọi (`ok`)**: `True`.
- **Tệp dữ liệu đo đạc**: `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\ket-qua-do-desktop-pc0575-cagent-payload-trim.json`.

---

## 5. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG (PYTEST)

### 5.1. Bộ test chuyên biệt cho vé (`tests/test_desktop_pc0575_cagent_payload_trim.py`)
Đạt **10/10 test cases PASSED** (thời gian: 1.35s):
1. `test_trim_chat_history_empty_or_none`: PASSED
2. `test_trim_chat_history_short_conversation_kept_intact`: PASSED (Hội thoại ngắn giữ nguyên 100%)
3. `test_trim_chat_history_long_conversation_trimmed_to_max_turns`: PASSED (Cắt đúng 6 tin gần nhất)
4. `test_trim_chat_history_character_budget_capping`: PASSED (Chốt chặn 4.000 ký tự hoạt động chính xác)
5. `test_trim_chat_history_single_huge_message_truncation`: PASSED (Xử lý tin nhắn đơn cực lớn)
6. `test_trim_chat_history_preserves_anchor_directive`: PASSED (Bảo toàn chỉ thị neo ngữ cảnh)
7. `test_trim_chat_history_custom_budget_and_env`: PASSED (Hỗ trợ cấu hình qua biến môi trường / tham số)
8. `test_cagent_lane_trims_long_history_before_sending`: PASSED (Tích hợp `route_workspace_chat_submission`, cắt 50 tin xuống 6 tin)
9. `test_cagent_lane_short_history_kept_intact_in_submission`: PASSED (Hội thoại ngắn trong routing không đổi)
10. `test_cagent_lane_does_not_mutate_chat_history_for_failover`: PASSED (Không làm biến đổi tuple lịch sử gốc khi chuyển làn)

### 5.2. Kiểm thử hồi quy toàn bộ suite liên quan C-Agent
Chạy đồng thời 5 file test:
- `tests/test_desktop_pc0575_cagent_payload_trim.py`
- `tests/test_desktop_pc0575_cagent_fallback_notice.py`
- `tests/test_cagent_api.py`
- `tests/test_wire_qa_cagent_lane.py`
- `tests/test_synth_lane_failover.py`

**Kết quả: 53/53 PASSED (100%)**.

---

## 6. DANH SÁCH TỆP TIN THAY ĐỔI

1. `src/aios_habit/cagent_api.py`:
   - Định nghĩa `DEFAULT_CAGENT_MAX_HISTORY_TURNS = 6` và `DEFAULT_CAGENT_MAX_HISTORY_CHARS = 4000`.
   - Hàm `trim_chat_history_for_cagent()`.
2. `src/aios_habit/antigravity_bridge.py`:
   - Import và gọi `trim_chat_history_for_cagent(chat_history)` trước `build_workspace_ai_prompt` trong hàm `_try_cagent_api()`.
3. `tests/test_desktop_pc0575_cagent_payload_trim.py`:
   - 10 bài test tự động bao quát mọi điều kiện biên và tích hợp luồng định tuyến.
4. `scripts/verify_cagent_payload_trim.py`:
   - Kịch bản đo đạc trước/sau trên dữ liệu thực tế `CONV-9C730D76`.
5. `scripts/run_real_turn_measurement.py`:
   - Kịch bản chạy đo đạc một lượt hỏi thật tại PC0575.

---

```json
{
  "ma_ve": "DESKTOP-PC0575-CAGENT-PAYLOAD-TRIM-FIX",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-16T12:05:00.000Z",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
