# Đặc tả kỹ thuật nối C-Agent cho vé WIRE-QA-CAGENT (PREP-WIRE-CAGENT-SPEC)

- **Người lập:** agy (Antigravity CLI) — Role: Architect / Technical Specifier
- **Máy thực hiện:** [CTY] KDTVN-PC0575 (CPU-only)
- **Ngày lập:** 2026-10-05
- **Mục tiêu:** Cung cấp đặc tả kỹ thuật chi tiết để vé `WIRE-QA-CAGENT-PC0575` triển khai tích hợp dữ liệu hỏi đáp 3.392 cặp (MOM, LSU, Điều-tra-lỗi) vào giao diện Workspace Chat thông qua lane C-Agent, đảm bảo hoạt động ổn định, an toàn và đúng rào chắn quy ước.
- **Căn cứ thực tế:**
  - Báo cáo probe: `docs/phieu-viec/ket-qua/probe-cagent-pc0575.md` (kết luận lane SỐNG, phản hồi thực tế 30,76 s).
  - Codebase: `src/aios_habit/cagent_api.py`, `src/aios_habit/ai_lane.py`, `src/aios_habit/antigravity_bridge.py`.
  - Dữ liệu tri thức staging: `docs/phieu-viec/chatgpt-enrichment-raw/` và `docs/phieu-viec/chatgpt-enrichment-fixed/` (3.393 cặp Q1–Q3406).

---

## 1. Hợp đồng giao tiếp API (API Contract)

### 1.1. Thông tin Endpoint & Giao thức
- **Endpoint URL:** `https://kdtvn-ai.cmcts.vn/api/v1/prediction/1881aa32-c996-4e6f-9257-78246177ba9f`
  - Được cấu hình mặc định trong `src/aios_habit/cagent_api.py::DEFAULT_CAGENT_API_URL`.
  - Hỗ trợ ghi đè qua biến môi trường `AIOS_CAGENT_API_URL` hoặc cấu hình giao diện.
- **HTTP Method:** `POST`
- **Headers:**
  ```http
  Content-Type: application/json
  Accept: application/json
  ```
  *(Lưu ý: Không gửi kèm token / API key client vì Flowise prediction endpoint đã tự sở hữu model credential nội bộ).*

### 1.2. Định dạng Request (Payload)
Flowise AgentFlow nhận payload JSON với trường `question`:
```json
{
  "question": "<system_prompt>\n\n<user_prompt>"
}
```

#### Quy cách lắp ghép ngữ cảnh từ 3.392 cặp Q&A:
Khi người dùng hỏi trên giao diện, worker trích xuất top 1–3 cặp Q&A liên quan từ kho staging (`docs/phieu-viec/chatgpt-enrichment-fixed/` hoặc `raw/`) theo từ khóa / mã lỗi / số hiệu JIG và ghép vào prompt:

- **System Prompt (Quy chuẩn hệ thống):**
  ```text
  Bạn là trợ lý AI chuyên môn kỹ thuật của KDTVN.
  Nhiệm vụ: Trả lời câu hỏi của kỹ sư dựa trên tài liệu kỹ thuật và các cặp Q&A tham khảo được cung cấp bên dưới.
  Quy tắc bắt buộc:
  1. Ưu tiên thông tin trong phần DỮ LIỆU THAM KHẢO.
  2. Giữ nguyên số liệu kỹ thuật, giá trị đo đạc (Raw value), mã lỗi, ký hiệu linh kiện (không tự suy diễn ngoài dữ liệu).
  3. Nếu không có thông tin trong tài liệu, hãy thông báo rõ ràng là tài liệu chưa ghi nhận, không tự bịa đặt câu trả lời.
  ```

- **User Prompt (Ngữ cảnh tham khảo + Câu hỏi người dùng):**
  ```text
  --- DỮ LIỆU THAM KHẢO (BẢN THẢO) ---
  [Nguồn: batch-{id}.md | CÂU HỎI {số} | Khối: {MOM/LSU/Điều-tra-lỗi}]
  - Bối cảnh: {bối cảnh gốc}
  - Câu hỏi gốc: {hỏi gốc}
  - Trả lời gốc: {đáp gốc}

  --- CÂU HỎI CỦA NGƯỜI DÙNG ---
  {câu hỏi người dùng nhập trên giao diện}
  ```

### 1.3. Định dạng Response (Kết quả trả về)
Server C-Agent trả về JSON object chứa chuỗi câu trả lời trong một trong các key `text`, `answer`, hoặc `response`:
```json
{
  "text": "Nội dung câu trả lời từ mô hình AI..."
}
```
Client Python (`cagent_api.py`) bóc tách chuỗi này và đóng gói vào `CAgentResponse`:
- `ok`: `True` nếu HTTP 200 và có chuỗi văn bản không rỗng; `False` nếu gặp lỗi.
- `text`: Nội dung câu trả lời đã làm sạch khoảng trắng thừa.
- `error_message`: Thông điệp lỗi tiếng Việt thân thiện khi `ok = False`.

---

## 2. Thông số Thời gian chờ, Thử lại và Giãn cách (Timeout / Retry / Backoff)

### 2.1. Căn cứ đo lường thực tế
- Tại báo cáo probe ngày 05/10/2026 trên KDTVN-PC0575: Thời gian gọi và nhận phản hồi cho 1 câu hỏi là **30,76 giây**.
- Tại phiên đo ngày 02/10/2026 trên KDTVN-PC0575: 6 câu hỏi đo được thời gian dao động từ **16,5 giây đến 45,8 giây** (trung bình ~30,2 giây).

### 2.2. Đề xuất thông số kỹ thuật cho vé WIRE
1. **Thời gian chờ (Timeout):**
   - **Ngưỡng HTTP client:** `timeout_seconds = 60` (khớp với `DEFAULT_TIMEOUT_SECONDS` trong `cagent_api.py`).
   - **Ngưỡng toàn trình UI (End-to-End SLA):** `< 60 giây`. Nếu sau 60 giây không có kết quả, UI hủy spinner và hiển thị thông báo quá hạn, giải phóng giao diện để người dùng không bị treo app.
2. **Số lần thử lại (Retry):**
   - **Tối đa 1 lần thử lại (`max_retries = 1`)**: Chỉ kích hoạt khi gặp lỗi mất kết nối mạng đột ngột hoặc HTTP 502/503/504 (server quá tải tạm thời).
   - **Không thử lại (`no-retry`)**: Khi gặp lỗi HTTP 4xx (400, 401, 404, 422) hoặc khi người dùng chủ động nhấn hủy (`cancellation_event.is_set()`).
3. **Giãn cách thử lại (Backoff):**
   - Thời gian chờ trước khi thử lại lần 2: Cố định **2,0 – 3,0 giây**. Không thử lại ngay lập tức để tránh làm trầm trọng thêm tình trạng nghẽn cổ chai của Flowise.

---

## 3. Xử lý sự cố và Thông báo người dùng (Error Handling)

### 3.1. Danh mục các lỗi đã biết & Cách phát hiện
| Tình huống lỗi | Dấu hiệu kỹ thuật | Nguyên nhân gốc |
|---|---|---|
| **Quá thời gian chờ (Timeout)** | `TimeoutError`, `socket.timeout`, `urlopen` vượt quá 60s | Mô hình xử lý prompt dài quá lâu hoặc đường truyền mạng chập chờn. |
| **Lỗi mạng nội bộ / DNS** | `urllib.error.URLError`, lỗi phân giải tên miền `kdtvn-ai.cmcts.vn` | PC0575 mất kết nối mạng công ty hoặc proxy công ty chặn kết nối. |
| **Máy chủ C-Agent lỗi** | HTTP 500, 502, 503, 504 | Tiến trình Flowise / backend server tại CMCTS bị treo hoặc khởi động lại. |
| **Chặn Cloud / Challenge** | `cloudflare_challenge`, `unknown_error`, mã 403 | Từng xảy ra ngày 02/10 và trong quá trình sinh dữ liệu do cơ chế chống bot / rate limit. |
| **Dữ liệu trả về rỗng / sai** | `json.JSONDecodeError` hoặc payload không có trường `text` | Server trả về HTML thông báo lỗi thay vì JSON. |

### 3.2. Quy tắc phát ngôn và thông báo người dùng
Tuân thủ tuyệt đối quy định ngôn ngữ tại `AGENTS.md` (Mục 9) và `CONSTITUTION.md`:
- **100% tiếng Việt dễ hiểu**, không dùng tiếng Anh kỹ thuật làm phương án dự phòng.
- **Không để lộ traceback thô**, không in đường dẫn file hệ thống `D:\...` hay thông số endpoint nội bộ.
- Bảng ánh xạ câu thông báo cho giao diện Workspace Chat:

| Trường hợp | Thông báo hiển thị trên giao diện người dùng |
|---|---|
| **Quá hạn 60s** | `Dịch vụ C-Agent phản hồi quá 60 giây. Vui lòng thử lại với câu hỏi ngắn gọn hơn.` |
| **Mất kết nối mạng** | `Không thể kết nối đến máy chủ C-Agent. Vui lòng kiểm tra lại mạng nội bộ công ty.` |
| **Server bận / HTTP 5xx** | `Dịch vụ C-Agent đang bận hoặc bảo trì tạm thời (HTTP {code}). Vui lòng thử lại sau vài phút.` |
| **Dữ liệu rỗng** | `Máy chủ C-Agent không trả về nội dung hợp lệ cho câu hỏi này. Vui lòng thử lại.` |
| **Người dùng hủy** | `Đã dừng yêu cầu trả lời từ AI.` |

---

## 4. Quy định Nhãn Bản thảo (Draft Labeling Policy)

Để bảo đảm tính an toàn dữ liệu và tuân thủ nguyên tắc không trộn lẫn tri thức chưa thẩm định vào kho chính:

1. **Nhãn bắt buộc:**
   Mọi câu trả lời được sinh ra có sử dụng nguồn ngữ cảnh từ 3.392 cặp Q&A bắt buộc phải hiển thị nhãn:
   > ⚠️ **Bản thảo — chưa qua chuyên gia duyệt**

2. **Cách trình bày trên UI Chat:**
   - Đặt nhãn nổi bật ở đầu bong bóng tin nhắn (hoặc footer của khối trả lời).
   - Ví dụ định dạng Markdown chuẩn:
     ```markdown
     > ⚠️ **Bản thảo — chưa qua chuyên gia duyệt**  
     > *Nguồn dữ liệu tham khảo: Khối [MOM / LSU / Điều-tra-lỗi] — Cặp Q&A #{ID}*

     {Nội dung câu trả lời tổng hợp từ C-Agent}
     ```
3. **Rào cứng an toàn (Safety Gates):**
   - **Không nhập kho chính:** Dữ liệu 3.392 cặp chỉ lưu tại vùng staging/local, không được nạp vào vector DB production hoặc BM25 index chính thức của AIOS.
   - **Không ghi đè Case:** Không tự động tạo hay ghi đè case chính thức trong `workspace_case_repository` khi chưa có thao tác phê duyệt thủ công của kỹ sư chuyên môn.

---

## 5. Bộ 3 Câu hỏi Demo Mẫu cho Vé WIRE

Dưới đây là 3 câu hỏi mẫu đại diện cho 3 khối dữ liệu (Điều-tra-lỗi, MOM, LSU) kèm nguồn tham chiếu và kết quả kỳ vọng để vé `WIRE-QA-CAGENT-PC0575` dùng làm kịch bản kiểm thử nghiệm thu:

### Câu 1: Khối Điều-tra-lỗi — Tra cứu mã lỗi C0980
- **Nguồn tham chiếu:** `docs/phieu-viec/chatgpt-enrichment-fixed/dieuchinh/batch-88.md` (Q3401) & `batch-85.md` (Q3317).
- **Câu hỏi người dùng:**
  > *"Mã lỗi C0980 trên máy in/photocopy báo hiệu lỗi gì và các bước kiểm tra linh kiện thực tế theo tài liệu gồm những gì?"*
- **Kỳ vọng nội dung trả lời:**
  - **Định nghĩa:** `C0980: 24V電源断検知` (Phát hiện mất nguồn cấp 24V liên tục 1 giây, hoặc mất 24V kéo theo service call khác).
  - **Linh kiện & điểm đo kiểm tra thực tế:**
    - Kiểm tra cầu chì `F401` (xem có bị đứt/open hay không).
    - Đo kiểm tra cặp transistor `Q402 / Q403` (xác nhận xem có bị ngắn mạch/short 3 cực không).
    - Kiểm tra `IC401` (chân 10 và chân 11 về giá trị trở kháng bất thường).
    - Kiểm tra các diode liên quan như `D304` hoặc `D211` xem có hiện tượng hàn giả (未半田) hoặc tiếp xúc kém không.
  - **Nhãn hiển thị:** Có kèm nhãn `Bản thảo — chưa qua chuyên gia duyệt`.
  - **Thời gian phản hồi kỳ vọng:** `< 60 giây` (thực tế dự kiến 25–40s).

---

### Câu 2: Khối MOM — Quy trình vận hành & Tham số điều khiển Matecon
- **Nguồn tham chiếu:** `docs/phieu-viec/chatgpt-enrichment-raw/mom/batch-01.md` (Q1 & Q2), tài liệu `マテコン操作手順書_v001_生産技術 TV.xlsx`.
- **Câu hỏi người dùng:**
  > *"Trong file cấu hình Matecon điều khiển AGV/ACR trên dây chuyền, hai chế độ ctrlMode = 0 và ctrlMode = 1 khác nhau như thế nào?"*
- **Kỳ vọng nội dung trả lời:**
  - **Ý nghĩa `ctrlMode`:** Tham số quy định trạng thái truyền thông giao thức SLMP giữa phần mềm Matecon, hệ thống cấp trên MOM và các thiết bị tự hành (ACR/CTU).
  - **Sự khác biệt:**
    - `ctrlMode = 0`: Chế độ sản xuất tự động (自動生産モード), truyền thông được kích hoạt. Matecon nhận chỉ thị từ MOM cấp trên và gửi lệnh I/O tới ACR/CTU để vận hành tự động.
    - `ctrlMode = 1`: Chế độ thủ công (手動モード), truyền thông bị chặn. Dùng khi kỹ sư bảo trì di chuyển hoặc xử lý thiết bị tại chỗ, không nhận lệnh điều phối tự động từ MOM.
  - **Nhãn hiển thị:** Có kèm nhãn `Bản thảo — chưa qua chuyên gia duyệt`.
  - **Thời gian phản hồi kỳ vọng:** `< 60 giây`.

---

### Câu 3: Khối LSU — Thông số đo kiểm Jig 2ND-1004
- **Nguồn tham chiếu:** `docs/phieu-viec/chatgpt-enrichment-raw/lsu/batch-21.md` (Q825), dữ liệu `2026_08_UnitTest.csv` thuộc thư mục `Iris LSU/thu nghiem 6pcs do thong so va log/2ND-1004`.
- **Câu hỏi người dùng:**
  > *"Trong dữ liệu UnitTest của Jig 2ND-1004 tháng 8/2026, mẫu đo Serial 61C999999902 xuất hiện bao nhiêu lần và kết quả đánh giá OK/NG của từng màu như thế nào?"*
- **Kỳ vọng nội dung trả lời:**
  - **Số lần xuất hiện:** Serial `61C999999902` xuất hiện đúng `4 lần` trong file `2026_08_UnitTest.csv`.
  - **Kết quả đánh giá theo màu:** Cả 4 lần đo đều cho kết quả:
    - Tổng thể: `Total = NG`
    - Chi tiết từng màu: `Black = NG`, `Magenta = NG`, `Cyan = OK`, `Yellow = NG`.
  - **Nguyên tắc Raw value:** Trả lời chính xác số liệu ghi nhận trong log, không tự suy diễn hay phỏng đoán nguyên nhân khi tài liệu không nêu.
  - **Nhãn hiển thị:** Có kèm nhãn `Bản thảo — chưa qua chuyên gia duyệt`.
  - **Thời gian phản hồi kỳ vọng:** `< 60 giây`.

---

## 6. Kết luận & Sẵn sàng cho Vé WIRE-QA-CAGENT

Tài liệu đặc tả này đã hoàn thiện đầy đủ 5 yêu cầu cốt lõi theo ticket `PREP-WIRE-CAGENT-SPEC`:
1. ✅ **API Contract:** Endpoint, method, headers, request/response format và cơ chế đưa context Q&A vào prompt.
2. ✅ **Timeout / Retry:** Timeout 60s, max 1 retry với backoff 2–3s.
3. ✅ **Error Handling:** 5 kịch bản lỗi, thông báo tiếng Việt chuẩn mực, chặn hoàn toàn traceback thô.
4. ✅ **Nhãn Bản thảo:** Rào cứng gắn nhãn `Bản thảo — chưa qua chuyên gia duyệt`, bảo vệ index chính.
5. ✅ **Demo 3 câu mẫu:** 3 kịch bản kiểm thử rõ ràng cho 3 khối Điều-tra-lỗi (C0980), MOM (Matecon), và LSU (Jig 2ND-1004).

Thợ thực hiện vé `WIRE-QA-CAGENT-PC0575` chỉ cần bám sát đặc tả này để implement kết nối Q&A vào Workspace Chat mà không cần khảo sát lại API từ đầu.
