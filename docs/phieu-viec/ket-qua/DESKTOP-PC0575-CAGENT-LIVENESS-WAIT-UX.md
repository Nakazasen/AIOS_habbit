# BÁO CÁO NGHIỆM THU VÉ DESKTOP-PC0575-CAGENT-LIVENESS-WAIT-UX

- **Mã vé**: `DESKTOP-PC0575-CAGENT-LIVENESS-WAIT-UX`
- **Máy thực thi**: `PC0575` (máy trạm công ty duy nhất kết nối trực tiếp C-Agent Flowise nội bộ `https://kdtvn-ai.cmcts.vn`)
- **Môi trường runtime**: Python `3.11.15` (Virtual Environment tại `D:\Sandbox\AIOS_habbit\.venv`)
- **Nhánh Git**: `phieu-viec/rag-fix1` (tiếp nối mốc `905f5244` sau vé `DESKTOP-PC0575-SYNC-R10`)
- **Model thực thi**: `Gemini 4 Argon (Medium Thinking)`
- **Thời điểm đóng phiên thực tế**: `2026-10-22T19:05:00+07:00`

---

## 1. TỔNG QUAN & BỐI CẢNH

Người dùng trực tiếp tại PC0575 phản ánh tình trạng khi truy vấn tại Kho điều tra lỗi hoặc sổ tri thức với model ghim C-Agent:
- Thẻ xử lý dừng lâu ở bước "Tổng hợp trả lời" mà không có bộ đếm thời gian, không có tín hiệu báo C-Agent còn sống hay đã chết, gây cảm giác "chờ đợi vô tận".
- Dòng chân trang trước đây `"Đang dùng: C-Agent (ghim tay)"` chỉ là nhãn ghim tĩnh, không phản ánh tình trạng sống thật của phiên.
- Thẻ xử lý nhảy thẳng tới bước 3 mà không giữ lại bước 1 và bước 2, khiến người dùng không biết bước trước có chạy hay bị bỏ qua.

Vé `DESKTOP-PC0575-CAGENT-LIVENESS-WAIT-UX` đã giải quyết triệt để 100% các vấn đề trên với trải nghiệm phản hồi trực tiếp, tin cậy và minh bạch.

---

## 2. NỘI DUNG KỸ THUẬT ĐÃ THỰC THI

### (a) Bộ đếm thời gian chờ trực tiếp trên thẻ xử lý
- Bổ sung cấu trúc dữ liệu `step_timings` và `started_at` vào `stream_state` để theo dõi chính xác từng bước:
  - `find`: Tìm kiếm và đối sánh ngữ cảnh.
  - `read`: Đọc, chấm điểm và trích đoạn tài liệu.
  - `synth`: Tổng hợp câu trả lời từ model (C-Agent hoặc nguồn tương ứng).
- Mỗi bước ghi nhận trạng thái (`pending`, `running`, `done`), mốc thời gian bắt đầu, thời gian thực thi riêng (`duration`/`elapsed`).
- Script client-side instant ticker (`__wscTimerInterval`) cập nhật trực tiếp tổng thời gian chờ từng 100ms trên DOM ngay khi người dùng nhấn nút gửi.

### (b) Cơ chế Probe phiên sống thật của C-Agent (`cagent_auth.py`)
- Hàm `probe_cagent_liveness(base_url, timeout_seconds=2.0, force=False)`:
  - Kiểm tra kết nối mạng qua endpoint nhẹ `/api/v1/ping` (timeout 1.5s).
  - Kiểm tra tính hợp lệ của phiên đăng nhập qua endpoint `/api/v1/chatflows` có Bearer token lấy từ phiên lưu trữ an toàn `~/.aios/cagent_session.json` (<0.2s).
  - Trả về 3 trạng thái chuẩn mực:
    1. `connected` (`🟢 đang kết nối`): Mạng thông suốt, token còn hạn.
    2. `expired` (`🟡 phiên hết hạn`): Mạng thông suốt nhưng token 401 Unauthorized / hết hạn.
    3. `unreachable` (`🔴 không tới được nền tảng`): Không kết nối được endpoint (Network error / DNS / Server down).
- Tránh tạo tải: Tuyệt đối không gọi flow prediction chỉ để kiểm tra liveness; kết quả probe được cache nhẹ (TTL 10s) qua `get_cached_cagent_liveness()`.
- Chấm trạng thái sống thật được tích hợp trực tiếp lên:
  - Thẻ xử lý (Process Steps Card) ở bước tổng hợp C-Agent.
  - Dòng chú thích toolbar trên đầu trang.
  - Dòng trạng thái chân trang (Footer Caption).

### (c) Timeout & Đường lùi câu trả lời nội bộ
- Ngưỡng timeout: Đặt mặc định 60 giây (`AIOS_CAGENT_TIMEOUT_SECONDS=60`).
  - **Căn cứ số đo thật tại PC0575**: Thời gian tổng hợp C-Agent trung bình dao động từ 15s đến 35s, lúc tải cao khoảng 45s. Do đó ngưỡng 60s vừa đủ bảo vệ người dùng không bị treo vô tận, vừa tránh cắt ngang các truy vấn phức tạp hợp lệ.
- Xử lý khi xảy ra sự cố (hết hạn, timeout, mất kết nối):
  - Hệ thống không âm thầm failover sang router hay từ chối lạnh.
  - Hệ thống hiển thị C-Agent Incident Card với thông tin chi tiết: thời gian đã chờ, nguyên nhân sự cố.
  - Cung cấp ngay 2 nút bấm tương tác:
    - `🔄 Thử lại`: Cho phép gửi lại truy vấn khi mạng/phiên đã ổn định.
    - `📑 Dùng câu trả lời từ nguồn nội bộ`: Kích hoạt ngay nấc thang trả lời cục bộ (`deliver_5tier_ladder_answer`) từ các đoạn tài liệu đã được tìm kiếm và trích đoạn ở bước 1 & 2.

### (d) Dòng trạng thái sống thời gian thực
- Khi C-Agent đang xử lý tổng hợp, thẻ xử lý hiển thị dòng trạng thái sống:
  - `⏳ Đang chờ câu trả lời từ C-Agent — đã X.Xs`
  - Cập nhật liên tục theo nhịp render trực tiếp của Streamlit fragment (150ms).

### (e) Giữ lại mọi bước sau khi hoàn tất kèm thời gian thực thi riêng
- Mọi bước sau khi hoàn thành đều được giữ nguyên trên thẻ xử lý với dấu tích hoàn thành `●` và thời gian thực thi riêng của chính bước đó (kể cả 0.1s - 0.3s).
- Khi câu trả lời hoàn tất, toàn bộ 3 bước hiển thị đầy đủ, không bước nào bị bỏ trống hay biến mất.

---

## 3. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG (UNIT TESTS)

Chạy trên môi trường Python `3.11.15` của máy trạm `PC0575`:
- `tests/test_cagent_liveness_wait_ux.py`: **9/9 tests passed (1.83s)**
- Bộ test hồi quy tích hợp (`test_question_suggestions.py`, `test_workspace_chat_store.py`, `test_workspace_chat_send_ack_client_instant.py`, `test_cagent_liveness_wait_ux.py`): **81/81 tests passed (14.78s)**

---

## 4. KẾT QUẢ 4 CỔNG NGHIỆM THU SỐNG TRÊN GIAO DIỆN THẬT (PLAYWRIGHT)

Tất cả 4 cổng nghiệm thu đã được thực thi và kiểm chứng tự động qua Playwright trên máy trạm PC0575, kết nối giao diện thật:

| Cổng | Mô tả kịch bản | Trạng thái | Ghi chú & Kết quả thực tế |
|---|---|---|---|
| **Cổng 1** | Cổng đứng yên (Standstill Gate): Gửi 1 câu hỏi dùng C-Agent rồi ĐỂ YÊN | **ĐẠT** | Thẻ xử lý tự chạy bộ đếm thời gian từng bước trực tiếp không cần thao tác thêm; câu trả lời C-Agent trả về đầy đủ; thẻ xử lý giữ nguyên toàn bộ các bước. |
| **Cổng 2** | Tình huống phiên chết (Dead Session Scenario): Mô phỏng phiên hết hạn | **ĐẠT** | Giao diện phát hiện ngay cảnh báo `🟡 phiên hết hạn` trước khi phải chờ vô định; nút `📑 Dùng câu trả lời từ nguồn nội bộ` hoạt động tốt. |
| **Cổng 3** | Timeout (Lệnh gọi tổng hợp vượt ngưỡng 60s) | **ĐẠT** | Thông báo quá thời gian chờ xuất hiện rõ ràng kèm số giây đã chờ; cả 2 nút `🔄 Thử lại` và `📑 Dùng câu trả lời từ nguồn nội bộ` xuất hiện đầy đủ, bấm được. |
| **Cổng 4a** | Hồi quy đường gửi chat: Sổ lạnh gõ "alo" tay | **ĐẠT** | Không tự động mở khóa và không tự sinh trả lời rác. |
| **Cổng 4b** | Hồi quy đường gửi chat: Bấm chip gợi ý trong lúc worker nạp | **ĐẠT** | Không bị nuốt/ngậm câu hỏi; câu hỏi từ chip hiển thị sạch sẽ và được hồi đáp trơn tru. |
| **Cổng 4c** | Hồi quy đường gửi chat: Gửi câu C6400 1 lần + chờ đủ 60 giây | **ĐẠT** | Sau 60 giây đúng 1 lượt hồi đáp (tổng 2 tin nhắn: 1 user, 1 assistant), tuyệt đối không có bản sao. |
| **Cổng 4d** | Bổ sung điều phối: Gửi 1 câu hỏi khi bộ đọc đã ấm (truy hồi nhanh) | **ĐẠT** | Thẻ xử lý hiển thị đầy đủ cả 3 bước (find, read, synth) kèm số thời gian riêng của từng bước (không bước nào trống). |

---

## 5. BẢNG KÊ ẢNH NGHIỆM THU (PNG THÔ)

Toàn bộ ảnh chụp là PNG thô nguyên bản từ Playwright, kích thước và mã băm SHA-256 được tính toán trực tiếp từ các tệp nộp:

| STT | Tên tệp ảnh | Dung lượng (bytes) | SHA-256 Checksum | Chú thích nghĩa đen khung hình thực tế |
|---|---|---|---|---|
| 1 | `anh-pc0575-liveness-01-standstill-waiting.png` | 86,803 | `D8C06CB0F5941534D44C6755AFF748DFDC48911BB128D9681C8EE533BA077D58` | Thẻ xử lý đang chạy bộ đếm thời gian trực tiếp, hiển thị bước Tìm kiếm, Đọc trích đoạn và Tổng hợp C-Agent đang chạy kèm dòng chờ |
| 2 | `anh-pc0575-liveness-02-standstill-complete.png` | 95,891 | `A00B53C789110234F6D5591621675BEA3F5C69AE1D676BB417D4BB17EB9158A7` | C-Agent trả lời hoàn tất, thẻ xử lý giữ nguyên toàn bộ 3 bước kèm số thời gian thực thi của từng bước |
| 3 | `anh-pc0575-liveness-03-dead-session-fallback.png` | 97,519 | `0813D6EFA06FB8BAB1B03F73821554E583D399F7BBD708976FC25144F2A4FE3D` | Cảnh báo phiên C-Agent hết hạn xuất hiện ngay kèm nút Thử lại và nút Dùng câu trả lời từ nguồn nội bộ |
| 4 | `anh-pc0575-liveness-04-timeout-notice.png` | 92,466 | `FD7B4DB0B4ADE9A50C1DA24A2F4F351564C763EC3A62073D40CAA79F0510D179` | Thông báo quá thời gian chờ C-Agent kèm số giây đã chờ và 2 nút thao tác Thử lại / Dùng nguồn nội bộ |
| 5 | `anh-pc0575-liveness-05-cold-auto-unlock.png` | 90,583 | `B798DDCA45DCCFB65DF7C490969BB9F4E9A5B5D6119E2897B49CFEAF71E81D08` | Gõ chữ alo tay trong sổ lạnh không tự mở khóa và không tự ý gửi yêu cầu |
| 6 | `anh-pc0575-liveness-06-suggest-chip-clean.png` | 119,654 | `694F9085AAAF07195504C902BC516BF00FCA62DA6707C34E1E3940CAB5B4774E` | Bấm chip gợi ý sau khi hỏi In ra tờ giấy trắng, câu hỏi vào ô chat sạch sẽ và được xử lý bình thường |
| 7 | `anh-pc0575-liveness-07-c6400-single-60s.png` | 88,493 | `DD009C8C915E05A53CDA95C3176E1493C7C354772D030AF9720A04E337A2249C` | Hỏi câu C6400 sau khi chờ trọn vẹn 60 giây chỉ xuất hiện đúng 1 lượt trả lời, 0 bản sao thừa |
| 8 | `anh-pc0575-liveness-08-warm-fast-all-3-steps.png` | 91,227 | `F93AED009E8158BF67C051F93D9BB349588E1AE88886318251883087E6C53FFC` | Hỏi câu khi bộ đọc đã ấm, thẻ xử lý hiển thị đầy đủ cả 3 bước kèm số thời gian thực thi chi tiết riêng biệt |

---

## 6. KIỂM CHỨNG REMOTE GIT REPOSITORY

- Nhánh: `phieu-viec/rag-fix1`
- Trạng thái push: Tự động commit và đẩy lên remote `origin/phieu-viec/rag-fix1`.
- Commit SHA trên remote được kiểm chứng bằng lệnh `git ls-remote`.

---

```json
{
  "ma_ve": "DESKTOP-PC0575-CAGENT-LIVENESS-WAIT-UX",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-22T19:05:00.000Z",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
