# Báo cáo Kết quả Thực thi: DESKTOP-PC0575-CAGENT-RECONNECT-TERRA

- **Model thực thi**: `Gemini 4 Argon (Medium)`
- **Mã vé**: `DESKTOP-PC0575-CAGENT-RECONNECT-TERRA`
- **Tiêu đề**: Mở khung đăng nhập C-Agent cho người dùng → kiểm tra model mới `gpt 5.6 terra` → nối lại C-Agent làm đường tổng hợp & hỏi AI ngoài trên `PC0575`
- **Máy đích**: `KDTVN-PC0575` (`Intel Core i5-8265U @ 1.60GHz`, `16 GB RAM`, Windows 11 Pro 64-bit, `CPU-only`)
- **Nhánh làm việc (`AIOS_habbit`)**: `phieu-viec/rag-fix1`
- **Commit sửa tối thiểu định tuyến External AI qua C-Agent (`AIOS_habbit`)**: `e8a3e324beb9aba9d1ee42262ba84158fcddc752`
- **Thời điểm hoàn thành**: `2026-10-21 16:15 (UTC+7)`

---

## 1. Trạng thái phiên C-Agent trước và sau Bước A (Không lộ Token/Mật khẩu)

### 1.1. Trạng thái phiên trước Bước A
Kiểm tra bằng `python -m aios_habit.cagent_auth status` trên tệp phiên `~/.aios/cagent_session.json` trước khi người dùng đăng nhập lại:

```json
{
  "logged_in": false,
  "username": "tvn183660",
  "source": "expired",
  "expires_in_seconds": 0.0,
  "has_refresh_token": true,
  "message": "Phiên đăng nhập C-Agent đã hết hạn (tvn183660)"
}
```

- Thử làm mới tự động qua `refresh_cagent_token()` trả về `HTTP 401: Invalid or blacklisted refresh token` do phiên cũ từ ngày `2026-10-16` đã hết hạn hoàn toàn phía máy chủ C-Agent.
- Đã khởi chạy ứng dụng AIOS tại `http://127.0.0.1:8501`, mở khung popover **🔑 Đăng nhập C-Agent**, chụp ảnh trạng thái khung đăng nhập và tạm dừng để người dùng tự nhập tài khoản / mật khẩu.
- Ảnh chụp khung đăng nhập C-Agent trên giao diện thật:
  - `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\anh-pc0575-cagent-login-frame.png` (`81,092` bytes)

### 1.2. Trạng thái phiên sau khi người dùng đăng nhập (Sau Bước A)
Sau khi người dùng xác nhận `"Đã đăng nhập xong"`, kiểm tra lại trạng thái phiên qua `python -m aios_habit.cagent_auth status` (tuyệt đối không đọc/in `access_token` hay `refresh_token`):

```json
{
  "logged_in": true,
  "username": "tvn183660",
  "source": "session_file",
  "expires_in_seconds": 3565.747873067856,
  "has_refresh_token": true,
  "message": "Đã đăng nhập (tvn183660)"
}
```

Trong quá trình chạy kiểm chứng Bước D sau đó, cơ chế tự làm mới phiên (`get_valid_access_token` / `refresh_cagent_token`) cũng đã tự động gia hạn phiên mới thành công (`expires_in_seconds: 3321.65s`).

---

## 2. Kết quả thử kết nối trực tiếp ở Bước B (`gpt 5.6 terra`)

Sử dụng phiên hợp lệ vừa đăng nhập để gọi thử 1 lượt tối giản vào đúng địa chỉ cấu hình C-Agent trên `PC0575`:
- **Endpoint**: `https://kdtvn-ai.cmcts.vn/api/v1/prediction/1881aa32-c996-4e6f-9257-78246177ba9f`
- **Payload gửi đi**: `{"question": "1+1=?"}`
- **Mã phản hồi HTTP**: `200 OK`
- **Thời gian phản hồi**: `1.988s` (`1988 ms`)
- **Tệp lưu kết quả đo thô**: `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\probe_buoc_b_cagent_terra.json`

### Nội dung trả lời nguyên văn từ máy chủ C-Agent (`gpt 5.6 terra`)
```json
{
  "text": "1 + 1 = 2",
  "question": "1+1=?",
  "chatId": "f5b93ca8-850e-4d8e-9b35-8cd8b4d30bdf",
  "metadataText": "",
  "chatMessageId": "2f9cfe36-76a8-4dcd-a9a0-ba116c5d132c",
  "sessionId": "f5b93ca8-850e-4d8e-9b35-8cd8b4d30bdf",
  "memoryType": "Agent Memory"
}
```

---

## 3. Cấu hình trước / sau và Sửa tối thiểu ở Bước C

### 3.1. Bảng cấu hình `D:\Sandbox\AIOS_habbit\.env` trước và sau Bước C

| Tên biến cấu hình | Giá trị trước Bước C | Giá trị sau Bước C | Ghi chú |
|---|---|---|---|
| `AIOS_AI_BACKEND` | `nakazasen_router` | `cagent_api` | Chuyển backend chính sang C-Agent (`gpt 5.6 terra`) |
| `AIOS_CAGENT_API_URL` | `https://kdtvn-ai.cmcts.vn/api/v1/prediction/1881aa32-c996-4e6f-9257-78246177ba9f` | `https://kdtvn-ai.cmcts.vn/api/v1/prediction/1881aa32-c996-4e6f-9257-78246177ba9f` | Giữ nguyên flow ID C-Agent |
| `AIOS_CAGENT_AUTH_URL` | `https://kdtvn-ai.cmcts.vn` | `https://kdtvn-ai.cmcts.vn` | Giữ nguyên |
| `AIOS_CAGENT_TIMEOUT_SECONDS` | `60` | `60` | Giữ nguyên hàng rào chờ 60s |
| `AIOS_CAGENT_MAX_HISTORY_MESSAGES` | `6` (mặc định trong `cagent_api.py`) | `6` (mặc định trong `cagent_api.py`) | Giữ nguyên hàng rào cắt gọn lịch sử 6 lượt |
| `AIOS_CAGENT_MAX_HISTORY_CHARS` | `4000` (mặc định trong `cagent_api.py`) | `4000` (mặc định trong `cagent_api.py`) | Giữ nguyên hàng rào cắt gọn 4000 ký tự |
| `AIOS_ROUTER_BASE_URL` | `https://api.commandcode.ai/v1` | `https://api.commandcode.ai/v1` | Giữ nguyên làm đường dự phòng tự động |
| `AIOS_ROUTER_MODEL` | `reflection/beam:free` | `reflection/beam:free` | Giữ nguyên làm đường dự phòng tự động |
| `AIOS_ROUTER_API_KEY` | `<ĐÃ_CẤU_HÌNH_ĐÃ_CHE>` | `<ĐÃ_CẤU_HÌNH_ĐÃ_CHE>` | Giữ nguyên, không lộ khóa |
| `AIOS_ROUTER_VERIFY_SSL` | `false` | `false` | Giữ nguyên cho mạng nội bộ `PC0575` |
| `AIOS_ROUTER_TIMEOUT_SECONDS` | `25` | `25` | Giữ nguyên |

### 3.2. Lý do và phạm vi sửa mã nguồn tối thiểu để nối chế độ "Hỏi AI ngoài" qua C-Agent
- **Phát hiện nguyên nhân**:
  Trong mã nguồn trước đó (từ vé `DESKTOP-PC0575-COMMANDCODE-EXTERNAL-MODE`), tại 2 vị trí:
  1. `src/aios_habit/workspace_chat_app.py` (hàm `_run_chat_turn_async`, dòng 1751): khi `ai_mode == "external"`, biến `ai_backend` bị gán cứng `ai_backend = "nakazasen_router"` bất kể người dùng/hệ thống đang chọn `cagent_api`.
  2. `src/aios_habit/antigravity_bridge.py` (hàm `route_workspace_chat_submission`, dòng 1219): khi `ai_mode == "external"`, biến `backend` cũng bị gán cứng `backend = "nakazasen_router"`, và hàm `_try_cagent_api()` chưa có nhánh xử lý `ai_mode == "external"` (không đính kèm tài liệu nội bộ, gắn provenance `operational_mode="external_ai"`, `provider_name="C-AGENT API"`, `source_count=0`).
- **Sửa tối thiểu trong phạm vi (lối vào và đẩy)**:
  1. `src/aios_habit/workspace_chat_app.py`: Khi `ai_mode == "external"`, giữ nguyên `ai_backend` nếu đang là `("cagent_api", "cagent")`; chỉ chuyển sang `"nakazasen_router"` khi backend không phải C-Agent.
  2. `src/aios_habit/antigravity_bridge.py`: Giữ `backend = "cagent_api"` khi `ai_mode == "external"`; bổ sung nhánh `is_ext = (ai_mode == "external")` trong `_try_cagent_api()` đảm bảo tuyệt đối `0` tài liệu nội bộ gửi ra (`evidence_items = []`, `source_count = 0`), gắn đúng provenance `{"operational_mode": "external_ai", "provider_name": "C-AGENT API", "model_name": "configured_by_provider", "ai_mode": "external"}`, phát đầy đủ mốc đo `[CAGENT_SYNTH_START]` / `[CAGENT_SYNTH_DONE]` và giữ nguyên cơ chế tự động rơi sang Command Code (`_try_nakazasen_router`) nếu C-Agent lỗi hoặc quá hạn chờ.
  3. `tests/test_desktop_pc0575_cagent_fallback_notice.py`: Bổ sung bài kiểm thử đơn vị `test_cagent_external_mode_routes_to_cagent_with_zero_internal_sources` (`23/23` bài kiểm thử liên quan PASS).
- **Commit riêng trên nhánh từ xa (`origin/phieu-viec/rag-fix1`)**:
  - Mã commit: `e8a3e324beb9aba9d1ee42262ba84158fcddc752` (`fix(cagent): route external AI mode through C-Agent when cagent_api is active (DESKTOP-PC0575-CAGENT-RECONNECT-TERRA)`).

---

## 4. Kết quả Kiểm chứng sống trên Giao diện thật (Bước D - Playwright Computer-Use)

Kịch bản kiểm chứng tự động trên giao diện thật (`scripts/run_desktop_pc0575_cagent_reconnect_terra.py`) đã khởi chạy Streamlit server thật với `AIOS_AI_BACKEND=cagent_api`, điều khiển trình duyệt Chromium qua Playwright thực hiện 2 lượt hỏi liên tiếp và ghi nhận log/trace/ảnh chụp màn hình.
- **Trạng thái log server (`server_desktop_pc0575_cagent_reconnect_terra.log`)**: `0` lỗi `Traceback`, `0` lỗi `HTTP 401`, `0` cảnh báo rơi tuyến, `0` banner lỗi đỏ trên giao diện.

### 4.1. Bảng tổng hợp thời gian từng bước của 2 lượt kiểm chứng

| Chỉ số đo | Lượt 1: Hỏi trong sổ có tài liệu thật (`grounded`) | Lượt 2: Hỏi AI ngoài phạm vi kho kiến thức (`external`) |
|---|---|---|
| **Mã hội thoại (`conv_id`)** | `CONV-PC0575-TERRA-GND-4D8307` | `CONV-PC0575-TERRA-EXT-AEFB52` |
| **Sổ làm việc / Khối** | `NB-LAZY-DTL` (*Sổ Điều tra lỗi*, khối `dieu_tra_loi`) | `NB-LAZY-DTL` (chế độ `ai_mode="external"`, khối `auto`) |
| **Mã tin nhắn trả lời / Trace ID** | `MSG-093E2C80` / `trc_062ef98ab5a7` | `MSG-2F12D37D` / `trc_7d4902eb9aae` |
| **Backend hoàn tất (`STREAMING_QA_COMPLETE`)** | `C-AGENT API` (`ok=True`) | `C-AGENT API` (`ok=True`) |
| **Provenance (`operational_mode` / `provider_name`)** | `external_api` / `C-AGENT API` | `external_ai` / `C-AGENT API` |
| **Số tài liệu nội bộ gửi kèm** | `13` nguồn (`15` đoạn trích từ `dieu_tra_loi`) | **`0`** (`Nguồn gửi cùng câu hỏi: 0`, `evidence_items = []`) |
| **Thời gian truy hồi vi mô (`RETRIEVAL_MICRO_TIMING`)** | `pipe_wait=1.62ms`, `coverage=185.83ms`, `lexical=1473.29ms`, `embed=1299.69ms`, `dense=512.66ms`, `sparse=455.57ms`, `fuse=182.73ms` (tổng lõi worker `~4.11s`, lọc/đóng gói nguồn trên 679 tài liệu `~40.6s`) | `0.00s` (không truy hồi kho nội bộ) |
| **Độ trễ gọi C-Agent (`[CAGENT_SYNTH_DONE] latency_s`)** | **`2.578s`** | **`5.531s`** |
| **TTFT tầng C-Agent (`cagent_ttft_s`)** | **`2.578s`** | **`5.531s`** |
| **TTFT toàn lượt (`[STREAMING_QA_FIRST_TOKEN] ttft_s`)** | **`47.399s`** | **`5.612s`** |
| **Tổng thời gian toàn lượt (`[STREAMING_QA_COMPLETE] total_s`)** | **`47.422s`** (UI wall: `48.928s`) | **`5.786s`** (UI wall: `6.182s`) |
| **Cảnh báo rơi tuyến / Banner lỗi đỏ trên UI** | `Không` (`False` / `False`) | `Không` (`False` / `False`) |
| **Ảnh chụp màn hình sau khi render xong** | `anh-pc0575-cagent-reconnect-terra-01-jam4212.png` (`229,741` bytes) | `anh-pc0575-cagent-reconnect-terra-02-external.png` (`273,480` bytes) |

---

### 4.2. Chi tiết Lượt 1 — Câu hỏi trong sổ có tài liệu thật (`grounded`)
- **Câu hỏi**:
  > `Theo báo cáo điều tra KTD-2026-06-0647 trên máy Iris2024-C33 (lỗi JAM4212), thông tin model, item code, tên linh kiện PWB liên quan, mã lot và nhà cung cấp được ghi nhận trong báo cáo là gì?`
- **Dấu vết log server**:
  ```text
  [STREAMING_QA_START] conv=CONV-PC0575-TERRA-GND-4D8307 backend=cagent_api question=Theo báo cáo điều tra KTD-2026-06-0647 trên máy Iris2024-C33 timestamp=2026-10-21 16:11:50.665
  [RETRIEVAL_MICRO_TIMING] collection=dieu_tra_loi pipe_wait_ms=1.62 coverage_verify_ms=185.83 lexical_ms=1473.29 embed_ms=1299.69 embed_wait_ms=0.00 embed_compute_ms=1299.69 dense_ms=512.66 sparse_ms=455.57 fuse_ms=182.73 context_expand_ms=0.00 dense_resident=True dense_state=thuong_tru dense_load_ms=0.90 timestamp=2026-10-21 16:12:35.434
  [CAGENT_SYNTH_START] conv=CONV-PC0575-TERRA-GND-4D8307 backend=cagent_api ai_mode=grounded timestamp=2026-10-21 16:12:35.471
  [STREAMING_QA_FIRST_TOKEN] conv=CONV-PC0575-TERRA-GND-4D8307 ttft_s=47.399 ttft_ms=47399.0 timestamp=2026-10-21 16:12:38.059
  [CAGENT_SYNTH_DONE] conv=CONV-PC0575-TERRA-GND-4D8307 ok=True latency_s=2.578 ttft_s=2.578 duration_s=2.578 timestamp=2026-10-21 16:12:38.059
  [STREAMING_QA_COMPLETE] conv=CONV-PC0575-TERRA-GND-4D8307 total_s=47.422 total_ms=47421.8 backend=C-AGENT API ok=True timestamp=2026-10-21 16:12:38.086
  ```
- **Nguyên văn đầy đủ câu trả lời của C-Agent (`gpt 5.6 terra`)**:
  ```markdown
  Theo báo cáo `KTD-2026-06-0647-Iris2024-C33-A-JAM4212.xlsx`:

  - Model: **Iris2024**
  - Item code - Rev: **3V2XC01050-5**
  - Tên linh kiện PWB: **PWB FRONT DRIVE ASSY**
  - Mã lot: **2XC-0-6616**
  - Nhà cung cấp: **KATOLEC VIET NAM CORPORATION**

  Owner nên kiểm tra lại thông tin trong báo cáo gốc trước khi sử dụng.

  Đây là câu trả lời do AI tạo, cần kiểm tra lại trước khi dùng.
  ```
- **Ảnh chụp màn hình**: `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\anh-pc0575-cagent-reconnect-terra-01-jam4212.png`

---

### 4.3. Chi tiết Lượt 2 — Câu hỏi ở chế độ "Hỏi AI ngoài phạm vi kho kiến thức" (`external`)
- **Câu hỏi**:
  > `Giải thích ngắn gọn nguyên lý hoạt động của cảm biến quang học và ứng dụng chính trong công nghiệp.`
- **Dấu vết log server**:
  ```text
  [STREAMING_QA_START] conv=CONV-PC0575-TERRA-EXT-AEFB52 backend=cagent_api question=Giải thích ngắn gọn nguyên lý hoạt động của cảm biến quang h timestamp=2026-10-21 16:12:51.932
  [CAGENT_SYNTH_START] conv=CONV-PC0575-TERRA-EXT-AEFB52 backend=cagent_api ai_mode=external timestamp=2026-10-21 16:12:52.002
  [STREAMING_QA_FIRST_TOKEN] conv=CONV-PC0575-TERRA-EXT-AEFB52 ttft_s=5.612 ttft_ms=5611.9 timestamp=2026-10-21 16:12:57.543
  [CAGENT_SYNTH_DONE] conv=CONV-PC0575-TERRA-EXT-AEFB52 ok=True latency_s=5.531 ttft_s=5.531 duration_s=5.531 timestamp=2026-10-21 16:12:57.543
  [STREAMING_QA_COMPLETE] conv=CONV-PC0575-TERRA-EXT-AEFB52 total_s=5.786 total_ms=5786.3 backend=C-AGENT API ok=True timestamp=2026-10-21 16:12:57.719
  ```
- **Kiểm tra nhãn nguồn ngoài và ranh giới dữ liệu trên giao diện**:
  - Hiển thị đầy đủ banner chuẩn `PC0575`: `🌐 Câu trả lời ngoài phạm vi kho kiến thức — không dựa trên dữ kiện trong kho. Kiểm chứng trước khi dùng.`
  - Footer xuất xứ: `🌐 Đích: C-AGENT API · Mô hình: configured_by_provider`
  - Ranh giới dữ liệu: `Nguồn gửi cùng câu hỏi: 0` (`evidence_items = []`, `0` tài liệu nội bộ gửi ra ngoài).
- **Nguyên văn đầy đủ câu trả lời của C-Agent (`gpt 5.6 terra`)**:
  ```markdown
  **Cảm biến quang học** hoạt động bằng cách sử dụng ánh sáng (thường là LED, laser hoặc hồng ngoại) để phát hiện sự hiện diện, vị trí, khoảng cách, màu sắc hoặc đặc tính bề mặt của vật thể.

  ### Nguyên lý hoạt động
  Cảm biến thường gồm:
  - **Bộ phát**: phát tia sáng đến vùng cần giám sát.
  - **Bộ thu**: nhận ánh sáng phản xạ từ vật thể hoặc ánh sáng truyền qua vật thể.
  - **Mạch xử lý**: phân tích cường độ, thời gian phản hồi hoặc sự thay đổi của ánh sáng để đưa ra tín hiệu đầu ra.

  Các kiểu phổ biến:
  1. **Thu-phát độc lập (through-beam)**: vật thể chắn tia sáng giữa bộ phát và bộ thu → cảm biến phát hiện vật.
  2. **Phản xạ gương (retro-reflective)**: ánh sáng phản xạ từ gương phản xạ về cảm biến; khi vật che tia, cảm biến kích hoạt.
  3. **Phản xạ khuếch tán (diffuse reflective)**: cảm biến nhận ánh sáng phản xạ trực tiếp từ bề mặt vật thể.

  ### Ứng dụng chính trong công nghiệp
  - **Phát hiện vật thể** trên băng tải, dây chuyền lắp ráp.
  - **Đếm sản phẩm**, chai, hộp, linh kiện.
  - **Kiểm tra vị trí và định hướng** của chi tiết máy.
  - **Đo khoảng cách, chiều cao hoặc mức vật liệu** trong kho, bồn chứa.
  - **Phân loại theo màu sắc, nhãn, kích thước hoặc độ tương phản**.
  - **Kiểm tra lỗi bề mặt** như thiếu chi tiết, sai nhãn, vết nứt hoặc sai lệch lắp ráp.
  - **Tự động hóa robot và hệ thống đóng gói**, giúp định vị sản phẩm chính xác.

  Ưu điểm nổi bật là tốc độ phản hồi nhanh, không cần tiếp xúc vật thể, độ chính xác cao và phù hợp với môi trường sản xuất tự động.
  ```
- **Ảnh chụp màn hình**: `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\anh-pc0575-cagent-reconnect-terra-02-external.png`

---

## 5. Danh mục bằng chứng bàn giao

1. **Báo cáo chính**: `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\DESKTOP-PC0575-CAGENT-RECONNECT-TERRA.md`
2. **Ảnh chụp khung đăng nhập Bước A**: `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\anh-pc0575-cagent-login-frame.png`
3. **Kết quả probe Bước B**: `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\probe_buoc_b_cagent_terra.json`
4. **Ảnh chụp giao diện thật Bước D - Lượt 1 (`grounded`)**: `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\anh-pc0575-cagent-reconnect-terra-01-jam4212.png`
5. **Ảnh chụp giao diện thật Bước D - Lượt 2 (`external`)**: `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\anh-pc0575-cagent-reconnect-terra-02-external.png`
6. **Dữ liệu đo JSON Bước D**: `D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop-pc0575\ket-qua\ket-qua-do-desktop-pc0575-cagent-reconnect-terra.json`

```json
{
  "ma_ve": "DESKTOP-PC0575-CAGENT-RECONNECT-TERRA",
  "trang_thai": "HOAN_THANH",
  "tom_tat": "Da mo khung dang nhap C-Agent cho nguoi dung tren PC0575, xac nhan phien hop le (tvn183660), thu ket noi prediction endpoint voi model moi gpt 5.6 terra dat HTTP 200 (1.988s, tra loi '1 + 1 = 2'), chuyen AIOS_AI_BACKEND=cagent_api giu nguyen hang rao 60s/6 luot/4000 ky tu va duong du phong Command Code, sua toi thieu dinh tuyen External AI qua C-Agent (commit e8a3e324), va kiem chung song tren giao dien that 2 luot (Grounded JAM4212/KTD-2026-06-0647: C-Agent latency 2.578s, total 47.422s; External AI: C-Agent latency 5.531s, total 5.786s, 0 tai lieu noi bo) voi 0 banner loi do."
}
```
